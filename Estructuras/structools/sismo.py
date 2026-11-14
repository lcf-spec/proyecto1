"""Seismic loads per NSR-10 Titulo A: site coefficients, design spectrum, ELF method.

Units: periods s, heights m, weights kN, Sa in g.
Fa / Fv tables reproduce NSR-10 Tables A.2.4-3 and A.2.4-4 - verify against your copy.
Aa and Av for each municipality come from NSR-10 Appendix A-4 (or the local microzonation).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

_LEVELS = [0.1, 0.2, 0.3, 0.4, 0.5]
FA = {"A": [0.8] * 5, "B": [1.0] * 5, "C": [1.2, 1.2, 1.1, 1.0, 1.0],
      "D": [1.6, 1.4, 1.2, 1.1, 1.0], "E": [2.5, 1.7, 1.2, 0.9, 0.9]}
FV = {"A": [0.8] * 5, "B": [1.0] * 5, "C": [1.7, 1.6, 1.5, 1.4, 1.3],
      "D": [2.4, 2.0, 1.8, 1.6, 1.5], "E": [3.5, 3.2, 2.8, 2.4, 2.4]}

# NSR-10 Table A.2.5-1: occupancy group -> importance coefficient I
IMPORTANCE = {"I": 1.00, "II": 1.10, "III": 1.25, "IV": 1.50}

# NSR-10 Table A.4.2-1: structural system -> (Ct, alpha)
PERIOD_PARAMS = {
    "concrete_moment_frame": (0.047, 0.9),
    "steel_moment_frame": (0.072, 0.8),
    "steel_braced_frame": (0.073, 0.75),
    "other": (0.049, 0.75),
}


def site_coefficients(soil: str, Aa: float, Av: float) -> tuple[float, float]:
    """Fa and Fv by linear interpolation (NSR-10 A.2.4.5). Soil F needs a site-specific study."""
    soil = soil.upper()
    if soil not in FA:
        raise ValueError("Soil profile F (or unknown) requires a site-specific study")
    return float(np.interp(Aa, _LEVELS, FA[soil])), float(np.interp(Av, _LEVELS, FV[soil]))


def spectrum_periods(Aa: float, Av: float, Fa: float, Fv: float) -> dict:
    """Corner periods T0, TC, TL (NSR-10 A.2.6)."""
    return {"T0": 0.1 * Av * Fv / (Aa * Fa), "TC": 0.48 * Av * Fv / (Aa * Fa), "TL": 2.4 * Fv}


def Sa(T, Aa: float, Av: float, soil: str = "D", I: float = 1.0, Fa: float | None = None,
       Fv: float | None = None, short_period_ramp: bool = False):
    """Elastic design spectral acceleration Sa [g], NSR-10 Eqs. A.2.6-1 to A.2.6-5.

    short_period_ramp=True uses Eq. A.2.6-7 below T0 (allowed for modal analysis only).
    """
    if Fa is None or Fv is None:
        Fa, Fv = site_coefficients(soil, Aa, Av)
    p = spectrum_periods(Aa, Av, Fa, Fv)
    T = np.asarray(T, dtype=float)
    plateau = 2.5 * Aa * Fa * I
    with np.errstate(divide="ignore"):
        out = np.where(T < p["TC"], plateau,
              np.where(T <= p["TL"], 1.2 * Av * Fv * I / np.maximum(T, 1e-9),
                       1.2 * Av * Fv * p["TL"] * I / np.maximum(T, 1e-9) ** 2))
    if short_period_ramp:
        out = np.where(T < p["T0"], plateau * (0.4 + 0.6 * T / p["T0"]), out)
    return float(out) if out.ndim == 0 else out


def approx_period(h: float, system: str = "concrete_moment_frame") -> float:
    """Approximate fundamental period Ta = Ct h^alpha, NSR-10 A.4.2.2 (h in m)."""
    Ct, alpha = PERIOD_PARAMS[system]
    return Ct * h**alpha


def period_limit(Ta: float, Av: float, Fv: float) -> float:
    """Upper limit Cu Ta with Cu = 1.75 - 1.2 Av Fv >= 1.2, NSR-10 A.4.2.1."""
    return max(1.2, 1.75 - 1.2 * Av * Fv) * Ta


def k_exponent(T: float) -> float:
    """Vertical distribution exponent k, NSR-10 A.4.3.2."""
    return 1.0 if T <= 0.5 else (2.0 if T > 2.5 else 0.75 + 0.5 * T)


def elf(weights, heights, Sa_g: float, T: float) -> pd.DataFrame:
    """Equivalent lateral force method, NSR-10 A.4.3: Vs = Sa W, Fx = Cvx Vs.

    weights [kN] and heights [m above base] per level, bottom to top.
    """
    w, hgt = np.asarray(weights, float), np.asarray(heights, float)
    k = k_exponent(T)
    Vs = Sa_g * w.sum()
    cvx = w * hgt**k / np.sum(w * hgt**k)
    F = cvx * Vs
    shear = np.cumsum(F[::-1])[::-1]
    df = pd.DataFrame({"level": np.arange(1, len(w) + 1), "h": hgt, "W": w, "Cvx": cvx,
                       "Fx": F, "story_shear": shear})
    df.attrs.update(Vs=Vs, k=k)
    return df
