"""Axial capacity of single piles (API RP 2A static method)."""
from __future__ import annotations

import math

import pandas as pd

from .stresses import vertical_stress

# API RP 2A-WSD (2000) Table 6.4.3-1 for siliceous soils:
# class: (description, delta [deg], f_max [kPa], Nq, q_max [kPa])
API_SAND = {
    1: ("Very loose sand / loose sand-silt / medium silt", 15, 47.8, 8, 1900),
    2: ("Loose sand / medium sand-silt / dense silt", 20, 67.0, 12, 2900),
    3: ("Medium sand / sand-silt", 25, 81.3, 20, 4800),
    4: ("Dense sand / dense sand-silt", 30, 95.7, 40, 9600),
    5: ("Dense gravel / very dense sand", 35, 114.8, 50, 12000),
}


def alpha_api(cu: float, sigma_v_eff: float) -> float:
    """API adhesion factor alpha (<= 1) from psi = cu / sigma_v'."""
    psi = cu / sigma_v_eff
    a = 0.5 * psi**-0.5 if psi <= 1 else 0.5 * psi**-0.25
    return min(a, 1.0)


def pile_capacity(D: float, L: float, layers: list[dict], water_table: float = math.inf,
                  K: float = 0.8, shape: str = "circular", dz: float = 0.05) -> dict:
    """Ultimate axial compression capacity of a closed-end / plugged pile [kN].

    layers: top-down list of {"thickness", "gamma", "gamma_sat", and either "cu" (clay, kPa)
    or "sand" (API class 1-5)}. K: lateral earth pressure coefficient (0.8 open-ended,
    1.0 displacement piles). Returns shaft, base and total capacity plus a per-layer table.
    """
    perim = math.pi * D if shape == "circular" else 4 * D
    Ab = math.pi * D**2 / 4 if shape == "circular" else D**2
    bounds, top = [], 0.0
    for lay in layers:
        bounds.append((top, top + lay["thickness"], lay))
        top += lay["thickness"]
    if L > top:
        raise ValueError("Pile is longer than the soil profile")

    def layer_at(z):
        for i, (t, b, lay) in enumerate(bounds):
            if t <= z < b:
                return i, lay
        return len(bounds) - 1, bounds[-1][2]

    shaft = [0.0] * len(layers)
    n = max(1, round(L / dz))
    step = L / n
    for k in range(n):
        z = (k + 0.5) * step
        i, lay = layer_at(z)
        sv = vertical_stress(layers, z, water_table)[2]
        if "cu" in lay:
            f = alpha_api(lay["cu"], sv) * lay["cu"]
        else:
            _, delta, fmax, _, _ = API_SAND[lay["sand"]]
            f = min(K * sv * math.tan(math.radians(delta)), fmax)
        shaft[i] += f * perim * step

    _, tip = layer_at(L - 1e-9)
    sv_tip = vertical_stress(layers, L, water_table)[2]
    if "cu" in tip:
        qb = 9 * tip["cu"]
    else:
        _, _, _, Nq, qmax = API_SAND[tip["sand"]]
        qb = min(Nq * sv_tip, qmax)
    Qs, Qb = sum(shaft), qb * Ab
    table = pd.DataFrame({"layer": range(1, len(layers) + 1),
                          "type": ["clay" if "cu" in l else f"sand {l['sand']}" for l in layers],
                          "Qs [kN]": shaft})
    return {"Qs": Qs, "Qb": Qb, "Qult": Qs + Qb, "qb": qb, "table": table}
