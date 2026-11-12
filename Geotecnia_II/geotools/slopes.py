"""Slope stability: infinite slope and circular slip surfaces (Fellenius / Bishop simplified).

Geometry for circular analysis: toe at (0, 0), slope rising to the right at angle beta up to
height H, level ground on both sides. Homogeneous soil; pore pressure via ru = u / (gamma h).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.optimize import brentq

GAMMA_W = 9.81


def infinite_slope(beta: float, phi: float, c: float = 0.0, gamma: float = 18.0, z: float = 1.0,
                   m: float = 0.0, gamma_w: float = GAMMA_W) -> float:
    """FS of an infinite slope. z: depth of slip plane; m: fraction of z below the seepage line
    (flow parallel to slope). Use gamma = gamma_sat when m > 0."""
    b, p = math.radians(beta), math.radians(phi)
    resisting = c + (gamma - m * gamma_w) * z * math.cos(b) ** 2 * math.tan(p)
    return resisting / (gamma * z * math.sin(b) * math.cos(b))


def _ground(x, H, xcrest):
    return np.clip(np.asarray(x, dtype=float) * H / xcrest, 0.0, H)


def _root(g, a, b):
    """Entry/exit point of the circle; falls back to the bracket end when g touches zero."""
    ga, gb = g(a), g(b)
    if ga == 0 or gb == 0 or ga * gb > 0:
        return a if abs(ga) <= abs(gb) else b
    return brentq(g, a, b)


def slices(H, beta, xc, yc, R, n=40):
    """Slice geometry for the circle (xc, yc, R). Returns a DataFrame or None if no valid slip."""
    xcrest = H / math.tan(math.radians(beta))
    xs = np.linspace(xc - R, xc + R, 4001)[1:-1]
    base = yc - np.sqrt(R**2 - (xs - xc) ** 2)
    f = _ground(xs, H, xcrest) - base
    inside = f > 1e-9
    if not inside.any() or inside[0] or inside[-1]:
        return None
    idx = np.flatnonzero(inside)
    if np.any(np.diff(idx) > 1):  # more than one sliding block - not a simple mechanism
        return None
    g = lambda x: float(_ground(x, H, xcrest)) - (yc - math.sqrt(max(R**2 - (x - xc) ** 2, 0.0)))
    xl = _root(g, xs[idx[0] - 1], xs[idx[0]])
    xr = _root(g, xs[idx[-1]], xs[idx[-1] + 1])
    # Toe circle: the slip surface ends at the toe instead of running on below the toe level.
    if xl < 0 < xr and abs(yc - math.sqrt(max(R**2 - xc**2, 0.0))) < 1e-6 * max(H, 1.0):
        xl = 0.0
    edges = np.linspace(xl, xr, n + 1)
    edges = np.unique(np.concatenate([edges, [k for k in (0.0, xcrest) if xl < k < xr]]))
    mid, b = (edges[:-1] + edges[1:]) / 2, np.diff(edges)
    ybase = yc - np.sqrt(R**2 - (mid - xc) ** 2)
    h = _ground(mid, H, xcrest) - ybase
    sin_a = (mid - xc) / R
    return pd.DataFrame({"x": mid, "b": b, "h": h, "y_base": ybase,
                         "alpha": np.degrees(np.arcsin(sin_a))})


def circle_fs(H, beta, c, phi, gamma, xc, yc, R, ru=0.0, method="bishop", n=40,
              min_m_alpha=0.2):
    """Factor of safety for one circle. Returns NaN when the circle is not a valid mechanism."""
    s = slices(H, beta, xc, yc, R, n)
    if s is None:
        return math.nan
    a = np.radians(s["alpha"].to_numpy())
    b, h = s["b"].to_numpy(), s["h"].to_numpy()
    W, u, tp = gamma * b * h, ru * gamma * h, math.tan(math.radians(phi))
    driving = np.sum(W * np.sin(a))
    if driving <= 1e-9:
        return math.nan
    fs = np.sum(c * b / np.cos(a) + (W * np.cos(a) - u * b / np.cos(a)) * tp) / driving
    if method == "fellenius":
        return fs
    for _ in range(100):
        m_a = np.cos(a) + np.sin(a) * tp / fs
        if np.any(m_a[a < 0] < min_m_alpha):  # Whitman & Bailey (1967) check at the toe
            return math.nan
        new = np.sum((c * b + (W - u * b) * tp) / m_a) / driving
        if abs(new - fs) < 1e-6:
            return new
        fs = new
    return fs


def critical_circle(H, beta, c, phi, gamma, ru=0.0, method="bishop", depth=None,
                    n_grid=21, n_radii=15) -> dict:
    """Grid search (with one refinement pass) for the minimum-FS circle.

    depth: how far below the toe circles may go (default H; use a firm-layer depth if known).
    """
    depth = H if depth is None else depth
    xcrest = H / math.tan(math.radians(beta))

    def search(xr, yr):
        best = (math.inf, None)
        for xc in np.linspace(*xr, n_grid):
            for yc in np.linspace(*yr, n_grid):
                radii = list(yc - np.linspace(-depth, 0.6 * H, n_radii)) + [math.hypot(xc, yc)]
                for R in radii:
                    if R <= 0:
                        continue
                    fs = circle_fs(H, beta, c, phi, gamma, xc, yc, R, ru, method)
                    if fs < best[0]:
                        best = (fs, (xc, yc, R))
        return best

    fs, (xc, yc, R) = search((-H, xcrest + 0.5 * H), (0.5 * H, 3 * H))
    dx, dy = (xcrest + 1.5 * H) / (n_grid - 1), 2.5 * H / (n_grid - 1)
    fs2, best2 = search((xc - dx, xc + dx), (yc - dy, yc + dy))
    if fs2 < fs:
        fs, (xc, yc, R) = fs2, best2
    return {"FS": fs, "xc": xc, "yc": yc, "R": R, "slices": slices(H, beta, xc, yc, R)}
