"""Bearing capacity of shallow foundations."""
from __future__ import annotations

import math

r = math.radians


def terzaghi_factors(phi: float) -> tuple[float, float, float]:
    """Terzaghi (1943) Nc, Nq, Ngamma. Ngamma uses Coduto's approximation."""
    p = r(phi)
    if p == 0:
        return 5.7, 1.0, 0.0
    a = math.exp((0.75 * math.pi - p / 2) * math.tan(p))
    Nq = a**2 / (2 * math.cos(r(45) + p / 2) ** 2)
    Nc = (Nq - 1) / math.tan(p)
    Ng = 2 * (Nq + 1) * math.tan(p) / (1 + 0.4 * math.sin(4 * p))
    return Nc, Nq, Ng


def terzaghi(c: float, phi: float, gamma: float, B: float, Df: float,
             shape: str = "strip") -> float:
    """Terzaghi ultimate bearing capacity q_u [kPa]; shape = 'strip', 'square' or 'circular' (B = diameter)."""
    Nc, Nq, Ng = terzaghi_factors(phi)
    sc, sg = {"strip": (1.0, 0.5), "square": (1.3, 0.4), "circular": (1.3, 0.3)}[shape]
    return sc * c * Nc + gamma * Df * Nq + sg * gamma * B * Ng


def general_factors(phi: float) -> tuple[float, float, float]:
    """Nc, Nq, Ngamma of the general bearing capacity equation (Reissner/Prandtl, Vesic Ngamma)."""
    p = r(phi)
    if p == 0:
        return 5.14, 1.0, 0.0
    Nq = math.exp(math.pi * math.tan(p)) * math.tan(r(45) + p / 2) ** 2
    return (Nq - 1) / math.tan(p), Nq, 2 * (Nq + 1) * math.tan(p)


def general(c: float, phi: float, gamma: float, B: float, Df: float, L: float | None = None,
            load_incl: float = 0.0, eB: float = 0.0, eL: float = 0.0) -> dict:
    """General (Meyerhof 1963) bearing capacity with shape, depth and inclination factors.

    Shape: De Beer (1970); depth: Hansen (1970); inclination: Meyerhof (1963).
    L=None -> strip footing (per metre). load_incl: load inclination from vertical [deg].
    eB, eL: load eccentricities -> effective dimensions B' = B - 2eB, L' = L - 2eL.
    gamma should already be the effective unit weight if the water table is near the footing.
    """
    Nc, Nq, Ng = general_factors(phi)
    p = r(phi)
    Bp = B - 2 * eB
    Lp = None if L is None else L - 2 * eL
    if Lp is not None and Bp > Lp:
        Bp, Lp = Lp, Bp
    BL = 0.0 if Lp is None else Bp / Lp

    Fcs = 1 + BL * Nq / Nc
    Fqs = 1 + BL * math.tan(p)
    Fgs = 1 - 0.4 * BL

    k = Df / B if Df <= B else math.atan(Df / B)
    Fqd = 1 + 2 * math.tan(p) * (1 - math.sin(p)) ** 2 * k
    Fcd = 1 + 0.4 * k if p == 0 else Fqd - (1 - Fqd) / (Nc * math.tan(p))
    Fgd = 1.0

    Fci = Fqi = (1 - load_incl / 90) ** 2
    Fgi = 1.0 if p == 0 else max(0.0, 1 - load_incl / phi) ** 2

    q = gamma * Df
    qu = (c * Nc * Fcs * Fcd * Fci + q * Nq * Fqs * Fqd * Fqi
          + 0.5 * gamma * Bp * Ng * Fgs * Fgd * Fgi)
    area = Bp if Lp is None else Bp * Lp
    return {"qu": qu, "Qu": qu * area, "B_eff": Bp, "L_eff": Lp, "Nc": Nc, "Nq": Nq, "Ngamma": Ng,
            "Fcs": Fcs, "Fqs": Fqs, "Fgs": Fgs, "Fcd": Fcd, "Fqd": Fqd, "Fgd": Fgd,
            "Fci": Fci, "Fqi": Fqi, "Fgi": Fgi}
