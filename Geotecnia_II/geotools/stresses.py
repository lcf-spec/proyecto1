"""In-situ stresses and stress increase from surface loads."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

GAMMA_W = 9.81


def vertical_stress(layers: list[dict], z: float, water_table: float = math.inf,
                    gamma_w: float = GAMMA_W) -> tuple[float, float, float]:
    """Total, pore and effective vertical stress at depth z (hydrostatic).

    layers: top-down list of {"thickness": m, "gamma": kN/m3 above WT, "gamma_sat": kN/m3 below WT}.
    Returns (sigma_v, u, sigma_v_eff) in kPa.
    """
    sigma, top = 0.0, 0.0
    for lay in layers:
        bot = top + lay["thickness"]
        if z <= top:
            break
        seg_bot = min(z, bot)
        dry = max(0.0, min(seg_bot, water_table) - top)
        wet = (seg_bot - top) - dry
        sigma += dry * lay["gamma"] + wet * lay.get("gamma_sat", lay["gamma"])
        top = bot
    if z > top + 1e-9:
        raise ValueError(f"z = {z} m is below the last layer ({top} m)")
    u = max(0.0, z - water_table) * gamma_w
    return sigma, u, sigma - u


def stress_profile(layers: list[dict], water_table: float = math.inf, dz: float = 0.5,
                   gamma_w: float = GAMMA_W) -> pd.DataFrame:
    """Table of sigma_v, u, sigma_v' with depth (including every layer boundary and the WT)."""
    total = sum(l["thickness"] for l in layers)
    zs = set(np.round(np.arange(0, total + 1e-9, dz), 6))
    acc = 0.0
    for l in layers:
        acc += l["thickness"]
        zs.add(round(acc, 6))
    if water_table < total:
        zs.add(round(water_table, 6))
    rows = [(z, *vertical_stress(layers, z, water_table, gamma_w)) for z in sorted(zs)]
    return pd.DataFrame(rows, columns=["z", "sigma_v", "u", "sigma_v_eff"])


def boussinesq_point(P: float, z: float, r: float = 0.0) -> float:
    """Vertical stress increase under a point load P [kN] at depth z, radial offset r."""
    return 3 * P / (2 * math.pi * z**2) / (1 + (r / z) ** 2) ** 2.5


def rect_corner_influence(B: float, L: float, z: float) -> float:
    """Newmark influence factor under the corner of a uniformly loaded B x L rectangle."""
    m, n = B / z, L / z
    m2, n2 = m * m, n * n
    root = math.sqrt(m2 + n2 + 1)
    t1 = 2 * m * n * root / (m2 + n2 + m2 * n2 + 1) * (m2 + n2 + 2) / (m2 + n2 + 1)
    t2 = math.atan2(2 * m * n * root, m2 + n2 + 1 - m2 * n2)
    return (t1 + t2) / (4 * math.pi)


def rect_stress(q: float, B: float, L: float, z: float, x: float | None = None,
                y: float | None = None) -> float:
    """Stress increase under a uniformly loaded B x L rectangle at depth z.

    (x, y) is the point in plan, measured from the rectangle's centre (default: centre).
    Uses superposition of corner rectangles, so points outside the footprint work too.
    """
    x = 0.0 if x is None else x
    y = 0.0 if y is None else y
    total = 0.0
    for a in (B / 2 - x, B / 2 + x):
        for b in (L / 2 - y, L / 2 + y):
            if a != 0 and b != 0:
                total += math.copysign(1, a) * math.copysign(1, b) * rect_corner_influence(abs(a), abs(b), z)
    return q * total


def circle_center_stress(q: float, R: float, z: float) -> float:
    """Stress increase under the centre of a uniformly loaded circle of radius R."""
    return q * (1 - 1 / (1 + (R / z) ** 2) ** 1.5)


def two_to_one(q: float, B: float, L: float, z: float) -> float:
    """Approximate 2:1 stress distribution under a B x L footing."""
    return q * B * L / ((B + z) * (L + z))
