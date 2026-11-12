"""Lateral earth pressure coefficients and wall thrust."""
from __future__ import annotations

import math

r = math.radians


def k0_jaky(phi: float, OCR: float = 1.0) -> float:
    """At-rest coefficient K0 = (1 - sin phi) * OCR^sin(phi) (Jaky; Mayne & Kulhawy)."""
    s = math.sin(r(phi))
    return (1 - s) * OCR**s


def rankine_ka(phi: float, beta: float = 0.0) -> float:
    """Rankine active coefficient; beta = backfill slope angle."""
    b, p = r(beta), r(phi)
    root = math.sqrt(math.cos(b) ** 2 - math.cos(p) ** 2)
    return math.cos(b) * (math.cos(b) - root) / (math.cos(b) + root)


def rankine_kp(phi: float, beta: float = 0.0) -> float:
    """Rankine passive coefficient; beta = backfill slope angle."""
    b, p = r(beta), r(phi)
    root = math.sqrt(math.cos(b) ** 2 - math.cos(p) ** 2)
    return math.cos(b) * (math.cos(b) + root) / (math.cos(b) - root)


def coulomb_ka(phi: float, delta: float = 0.0, theta: float = 0.0, beta: float = 0.0) -> float:
    """Coulomb active coefficient.

    delta: wall friction; theta: wall back inclination from vertical; beta: backfill slope.
    """
    p, d, t, b = r(phi), r(delta), r(theta), r(beta)
    root = math.sqrt(math.sin(d + p) * math.sin(p - b) / (math.cos(d + t) * math.cos(t - b)))
    return math.cos(p - t) ** 2 / (math.cos(t) ** 2 * math.cos(d + t) * (1 + root) ** 2)


def coulomb_kp(phi: float, delta: float = 0.0, theta: float = 0.0, beta: float = 0.0) -> float:
    """Coulomb passive coefficient (unconservative for delta > phi/2)."""
    p, d, t, b = r(phi), r(delta), r(theta), r(beta)
    root = math.sqrt(math.sin(p + d) * math.sin(p + b) / (math.cos(d - t) * math.cos(b - t)))
    return math.cos(p + t) ** 2 / (math.cos(t) ** 2 * math.cos(d - t) * (1 - root) ** 2)


def rankine_active_thrust(H: float, gamma: float, phi: float, c: float = 0.0,
                          q: float = 0.0) -> dict:
    """Rankine active thrust per metre of wall (vertical back, level backfill, dry).

    Tension above the tension-crack depth is ignored. Returns Pa [kN/m], its height above
    the base [m], the crack depth zc [m], and the pressures at top/bottom [kPa].
    """
    Ka = rankine_ka(phi)
    s0 = Ka * q - 2 * c * math.sqrt(Ka)
    sH = Ka * (gamma * H + q) - 2 * c * math.sqrt(Ka)
    if s0 >= 0:
        Pa = (s0 + sH) / 2 * H
        ybar = H * (2 * s0 + sH) / (3 * (s0 + sH)) if Pa > 0 else 0.0
        zc = 0.0
    else:
        zc = -s0 / (Ka * gamma)
        if zc >= H:
            return {"Ka": Ka, "Pa": 0.0, "y": 0.0, "zc": zc, "sigma_top": s0, "sigma_base": sH}
        Pa = sH * (H - zc) / 2
        ybar = (H - zc) / 3
    return {"Ka": Ka, "Pa": Pa, "y": ybar, "zc": zc, "sigma_top": s0, "sigma_base": sH}
