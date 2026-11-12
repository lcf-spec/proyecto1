"""Consolidation and elastic settlement."""
from __future__ import annotations

import math

from scipy.optimize import brentq


def consolidation_settlement(H: float, e0: float, Cc: float, sigma0: float, dsigma: float,
                             Cs: float = 0.0, sigma_p: float | None = None) -> float:
    """Primary consolidation settlement [m] of a clay layer of thickness H.

    sigma0: initial effective stress at mid-layer; dsigma: stress increase; sigma_p: preconsolidation
    pressure (None or <= sigma0 means normally consolidated). Cs: swelling/recompression index.
    """
    sf = sigma0 + dsigma
    k = H / (1 + e0)
    if sigma_p is None or sigma_p <= sigma0:
        return k * Cc * math.log10(sf / sigma0)
    if sf <= sigma_p:
        return k * Cs * math.log10(sf / sigma0)
    return k * (Cs * math.log10(sigma_p / sigma0) + Cc * math.log10(sf / sigma_p))


def degree_of_consolidation(Tv: float, terms: int = 200) -> float:
    """Average degree of consolidation U (0-1) for time factor Tv (Terzaghi, uniform initial u)."""
    if Tv <= 0:
        return 0.0
    s = 0.0
    for m in range(terms):
        M = math.pi * (2 * m + 1) / 2
        s += 2 / M**2 * math.exp(-M * M * Tv)
    return 1 - s


def time_factor(U: float) -> float:
    """Time factor Tv for an average degree of consolidation U (0-1)."""
    if not 0 < U < 1:
        raise ValueError("U must be between 0 and 1")
    return brentq(lambda t: degree_of_consolidation(t) - U, 1e-8, 10)


def consolidation_time(U: float, cv: float, Hdr: float) -> float:
    """Time to reach degree U, in the time unit of cv (e.g. cv in m2/year -> years)."""
    return time_factor(U) * Hdr**2 / cv


def elastic_settlement(q: float, B: float, Es: float, nu: float, If: float = 1.0) -> float:
    """Immediate settlement s = q B (1 - nu^2) / Es * If  [m].

    Typical If: flexible square centre 1.12, corner 0.56, average 0.95; rigid square 0.82.
    """
    return q * B * (1 - nu**2) / Es * If
