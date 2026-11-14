"""Reinforced concrete per NSR-10 Titulo C (based on ACI 318-08).

Units: lengths mm, stresses MPa, forces kN, moments kN*m.
Where ACI 318-19 differs, the docstring says so.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.optimize import brentq

ES = 200_000.0   # MPa, NSR-10 C.8.5.2
EPS_CU = 0.003   # NSR-10 C.10.2.3


# --- materials -----------------------------------------------------------------
def beta1(fc: float) -> float:
    """Whitney block depth factor, NSR-10 C.10.2.7.3."""
    return 0.85 if fc <= 28 else max(0.65, 0.85 - 0.05 * (fc - 28) / 7)


def Ec(fc: float) -> float:
    """Elastic modulus of normal-weight concrete, NSR-10 C.8.5.1: 4700 sqrt(f'c) [MPa]."""
    return 4700 * math.sqrt(fc)


def fr(fc: float, lam: float = 1.0) -> float:
    """Modulus of rupture, NSR-10 C.9.5.2.3: 0.62 lambda sqrt(f'c) [MPa]."""
    return 0.62 * lam * math.sqrt(fc)


def phi_flexure_axial(eps_t: float, fy: float = 420, transverse: str = "tied") -> float:
    """Strength reduction factor from net tensile strain, NSR-10 C.9.3.2.

    Compression-controlled limit taken as eps_y = fy / Es (ACI 318-19 21.2.2; NSR-10 permits
    0.002 for fy = 420). Spiral value 0.75 follows ACI 318-11 and later - check it against
    your NSR-10 edition (ACI 318-08 used 0.70).
    """
    eps_y = fy / ES
    phic = 0.65 if transverse == "tied" else 0.75
    if eps_t >= 0.005:
        return 0.90
    if eps_t <= eps_y:
        return phic
    return phic + (0.90 - phic) * (eps_t - eps_y) / (0.005 - eps_y)


# --- flexure -------------------------------------------------------------------
def As_min(b: float, d: float, fc: float, fy: float) -> float:
    """Minimum flexural steel, NSR-10 C.10.5.1: max(0.25 sqrt(f'c)/fy, 1.4/fy) b d [mm2]."""
    return max(0.25 * math.sqrt(fc) / fy, 1.4 / fy) * b * d


def flexure_rect(b: float, d: float, As: float, fc: float, fy: float,
                 As_comp: float = 0.0, d_comp: float = 0.0) -> dict:
    """Nominal flexural strength of a rectangular beam by strain compatibility (NSR-10 C.10.2).

    Optional compression steel As_comp at depth d_comp. Returns a, c, eps_t, phi, Mn, phiMn
    (kN*m) and whether the section is tension-controlled and meets C.10.3.5 (eps_t >= 0.004).
    """
    b1 = beta1(fc)

    def forces(c):
        a = b1 * c
        Cc = 0.85 * fc * a * b
        eps_s = EPS_CU * (d - c) / c
        T = As * min(fy, ES * eps_s) if eps_s > 0 else -As * min(fy, ES * -eps_s)
        Cs = 0.0
        if As_comp > 0:
            fs = float(np.clip(ES * EPS_CU * (c - d_comp) / c, -fy, fy))
            if a > d_comp:
                fs -= 0.85 * fc
            Cs = As_comp * fs
        return Cc, Cs, T, a, eps_s

    c = brentq(lambda c: (lambda Cc, Cs, T, *_: Cc + Cs - T)(*forces(c)), 1e-6, 10 * d)
    Cc, Cs, T, a, eps_t = forces(c)
    Mn = (Cc * (d - a / 2) + Cs * (d - d_comp)) / 1e6
    phi = phi_flexure_axial(eps_t, fy)
    return {"a": a, "c": c, "eps_t": eps_t, "phi": phi, "Mn": Mn, "phiMn": phi * Mn,
            "tension_controlled": eps_t >= 0.005, "eps_t_ok": eps_t >= 0.004,
            "As_min": As_min(b, d, fc, fy), "As_min_ok": As >= As_min(b, d, fc, fy)}


def design_flexure(Mu: float, b: float, d: float, fc: float, fy: float) -> dict:
    """Required tension steel for a singly reinforced rectangular beam, Mu in kN*m.

    Assumes phi = 0.90 and then verifies it by strain compatibility.
    """
    Rn = Mu * 1e6 / (0.90 * b * d**2)
    disc = 1 - 2 * Rn / (0.85 * fc)
    if disc < 0:
        raise ValueError("Section too small for Mu: enlarge it or add compression steel")
    rho = 0.85 * fc / fy * (1 - math.sqrt(disc))
    As = max(rho * b * d, As_min(b, d, fc, fy))
    check = flexure_rect(b, d, As, fc, fy)
    return {"As": As, "rho": As / (b * d), "Rn": Rn, "check": check,
            "ok": check["phiMn"] >= Mu * (1 - 1e-9) and check["eps_t_ok"]}


# --- shear ---------------------------------------------------------------------
def Vc_beam(bw: float, d: float, fc: float, lam: float = 1.0) -> float:
    """Concrete shear strength, NSR-10 C.11.2.1.1: 0.17 lambda sqrt(f'c) bw d [kN].

    ACI 318-19 replaced this with a size-effect / rho_w formula (Table 22.5.5.1).
    """
    return 0.17 * lam * math.sqrt(fc) * bw * d / 1e3


def shear_design(Vu: float, bw: float, d: float, fc: float, fyt: float, Av: float,
                 lam: float = 1.0) -> dict:
    """Stirrup spacing for Vu [kN] with stirrup area Av [mm2] (all legs), NSR-10 C.11.

    Gives the governing spacing from strength (C.11.4.7.2), maximum spacing (C.11.4.5) and
    minimum shear steel (C.11.4.6.3). Seismic (DES/DMO) confinement rules in C.21 are NOT
    included - they usually govern near supports.
    """
    phi = 0.75
    Vc = Vc_beam(bw, d, fc, lam)
    Vs_req = max(0.0, Vu / phi - Vc)
    Vs_max = 0.66 * math.sqrt(fc) * bw * d / 1e3
    if Vs_req > Vs_max:
        raise ValueError(f"Vs required {Vs_req:.0f} kN > {Vs_max:.0f} kN: enlarge the section")
    s_strength = Av * fyt * d / (Vs_req * 1e3) if Vs_req > 0 else math.inf
    tight = Vs_req > 0.33 * math.sqrt(fc) * bw * d / 1e3
    s_max = min(d / 4, 300) if tight else min(d / 2, 600)
    s_avmin = Av * fyt / max(0.062 * math.sqrt(fc) * bw, 0.35 * bw)
    needs = Vu > 0.5 * phi * Vc
    s = min(s_strength, s_max, s_avmin) if needs else None
    return {"phiVc": phi * Vc, "Vc": Vc, "Vs_req": Vs_req, "Vs_max": Vs_max,
            "s_strength": s_strength, "s_max": s_max, "s_Avmin": s_avmin,
            "stirrups_required": needs, "s": s}


# --- columns -------------------------------------------------------------------
def column_point(c: float, b: float, h: float, bars: list[tuple[float, float]], fc: float,
                 fy: float) -> tuple[float, float, float]:
    """Nominal (Pn [kN], Mn [kN*m], eps_t) for neutral-axis depth c.

    bars: list of (depth from compression face [mm], area [mm2]). Compression positive,
    moments about the gross-section centroid.
    """
    a = min(beta1(fc) * c, h)
    Cc = 0.85 * fc * a * b
    P, M = Cc, Cc * (h / 2 - a / 2)
    for y, A in bars:
        fs = float(np.clip(ES * EPS_CU * (c - y) / c, -fy, fy))
        if y < a:
            fs -= 0.85 * fc  # concrete displaced by the bar
        P += fs * A
        M += fs * A * (h / 2 - y)
    dt = max(y for y, _ in bars)
    return P / 1e3, M / 1e6, EPS_CU * (dt - c) / c


def interaction_diagram(b: float, h: float, bars: list[tuple[float, float]], fc: float,
                        fy: float, transverse: str = "tied", n: int = 80) -> pd.DataFrame:
    """P-M interaction diagram for uniaxial bending, NSR-10 C.10.2-C.10.3.

    Includes the phi factor and the C.10.3.6 cap on axial load (0.80 phi P0 tied,
    0.85 phi P0 spiral). Returns nominal and design values.
    """
    Ast = sum(A for _, A in bars)
    P0 = (0.85 * fc * (b * h - Ast) + fy * Ast) / 1e3
    cap = (0.80 if transverse == "tied" else 0.85) * P0
    phic = phi_flexure_axial(-1.0, fy, transverse)
    rows = [(math.inf, P0, 0.0, -math.inf, phic, phic * cap, 0.0)]  # pure compression
    for c in np.concatenate([np.geomspace(0.02 * h, h, n // 2), np.linspace(h, 5 * h, n // 2)[1:]]):
        Pn, Mn, eps_t = column_point(c, b, h, bars, fc, fy)
        phi = phi_flexure_axial(eps_t, fy, transverse)
        rows.append((c, Pn, Mn, eps_t, phi, min(phi * Pn, phi * cap), phi * Mn))
    Pt = -fy * Ast / 1e3
    Mt = -fy * sum(A * (h / 2 - y) for y, A in bars) / 1e6
    rows.append((0.0, Pt, Mt, math.inf, 0.90, 0.90 * Pt, 0.90 * Mt))
    df = pd.DataFrame(rows, columns=["c", "Pn", "Mn", "eps_t", "phi", "phiPn", "phiMn"])
    df.attrs.update(P0=P0, Pn_max=cap)
    return df.sort_values("c", ascending=False).reset_index(drop=True)  # compression -> tension


def column_check(Pu: float, Mu: float, diagram: pd.DataFrame) -> dict:
    """Check (Pu [kN], Mu [kN*m]) against a symmetric section's design diagram.

    ratio = demand / capacity along the line from the origin (< 1 means OK).
    """
    from shapely.geometry import Point, Polygon

    pts = list(zip(diagram["phiMn"].abs(), diagram["phiPn"]))
    poly = Polygon(pts + [(-m, p) for m, p in reversed(pts)]).buffer(0)
    if Pu == 0 and Mu == 0:
        return {"ok": True, "ratio": 0.0}
    lo, hi = 0.0, 1.0
    while poly.contains(Point(abs(Mu) * hi, Pu * hi)):
        hi *= 2
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if poly.contains(Point(abs(Mu) * mid, Pu * mid)) else (lo, mid)
    ratio = 1 / lo if lo > 0 else math.inf
    return {"ok": ratio <= 1.0, "ratio": ratio}


def rect_bars(b: float, h: float, cover: float, n_top: int, n_bot: int, n_side: int,
              bar_area: float) -> list[tuple[float, float]]:
    """Bar layers for a rectangular column: n_top / n_bot bars on the faces, n_side bars on
    each side face between them. cover is measured to the bar centre."""
    layers = [(cover, n_top * bar_area), (h - cover, n_bot * bar_area)]
    if n_side:
        for y in np.linspace(cover, h - cover, n_side + 2)[1:-1]:
            layers.append((float(y), 2 * bar_area))
    return layers
