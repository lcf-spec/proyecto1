"""structools checks: hand calculations (shown in comments) and NSR-10 / ACI 318 formulas."""
import math

import pytest
from scipy.optimize import brentq

from structools import concreto as rc, sismo

approx = pytest.approx


# --- materials ----------------------------------------------------------------
def test_materials():
    assert rc.beta1(21) == 0.85 and rc.beta1(28) == 0.85
    assert rc.beta1(35) == approx(0.80) and rc.beta1(70) == 0.65
    assert rc.Ec(28) == approx(4700 * math.sqrt(28))
    assert rc.As_min(300, 500, 28, 420) == approx(1.4 / 420 * 300 * 500)  # 1.4/fy governs at 28 MPa


def test_phi_transition():
    assert rc.phi_flexure_axial(0.006) == 0.90
    assert rc.phi_flexure_axial(0.0015) == 0.65
    assert rc.phi_flexure_axial(0.0021 + (0.005 - 0.0021) / 2) == approx(0.775)


# --- flexure ------------------------------------------------------------------
def test_flexure_hand_calc():
    # b=300, d=500, As=1500, f'c=28, fy=420:
    # a = 1500*420/(0.85*28*300) = 88.24 mm; c = 103.8 mm; eps_t = 0.01145
    # Mn = 1500*420*(500 - 44.12) = 287.2 kN*m; phi = 0.90 -> phiMn = 258.5 kN*m
    r = rc.flexure_rect(300, 500, 1500, 28, 420)
    assert r["a"] == approx(88.235, abs=0.01)
    assert r["eps_t"] == approx(0.01145, abs=1e-5)
    assert r["Mn"] == approx(287.206, abs=0.01)
    assert r["phiMn"] == approx(258.49, abs=0.01)
    assert r["tension_controlled"]


def test_flexure_over_reinforced():
    r = rc.flexure_rect(300, 500, 5000, 28, 420)
    assert r["eps_t"] < 420 / rc.ES and r["phi"] == 0.65 and not r["eps_t_ok"]


def test_design_round_trip():
    d = rc.design_flexure(258.49, 300, 500, 28, 420)
    assert d["As"] == approx(1500, rel=1e-3) and d["ok"]


def test_design_uses_minimum_steel():
    d = rc.design_flexure(20, 300, 500, 28, 420)
    assert d["As"] == approx(rc.As_min(300, 500, 28, 420))


# --- shear --------------------------------------------------------------------
def test_shear_hand_calc():
    # Vc = 0.17*sqrt(28)*300*500 = 134.9 kN; Vs = 333.33 - 134.93 = 198.40 kN
    # s = 142*420*500/198 400 = 150.3 mm (< d/2 = 250, < 568 for Av,min)
    r = rc.shear_design(250, 300, 500, 28, 420, Av=142)
    assert r["Vc"] == approx(134.94, abs=0.01)
    assert r["Vs_req"] == approx(198.40, abs=0.01)
    assert r["s"] == approx(150.3, abs=0.1)
    assert r["s_max"] == 250


def test_shear_too_high():
    with pytest.raises(ValueError):
        rc.shear_design(1500, 300, 500, 28, 420, Av=142)


# --- columns ------------------------------------------------------------------
BARS = rc.rect_bars(400, 400, 60, 4, 4, 0, 510)


def test_column_squash_and_tension():
    df = rc.interaction_diagram(400, 400, BARS, 28, 420)
    # P0 = 0.85*28*(160000 - 4080) + 420*4080 = 5424.5 kN
    assert df.attrs["P0"] == approx(5424.5, abs=0.1)
    assert df["phiPn"].max() == approx(0.65 * 0.80 * 5424.5, abs=0.1)
    assert df["Pn"].min() == approx(-420 * 4080 / 1e3)


def test_column_balanced_point():
    cb = 0.003 / (0.003 + 420 / rc.ES) * 340
    _, _, eps_t = rc.column_point(cb, 400, 400, BARS, 28, 420)
    assert eps_t == approx(420 / rc.ES)


def test_column_matches_beam_at_zero_axial_load():
    bars = [(500, 1500)]
    c0 = brentq(lambda c: rc.column_point(c, 300, 550, bars, 28, 420)[0], 1, 500)
    Mn = rc.column_point(c0, 300, 550, bars, 28, 420)[1]
    assert Mn == approx(rc.flexure_rect(300, 500, 1500, 28, 420)["Mn"], rel=1e-6)


def test_column_check():
    df = rc.interaction_diagram(400, 400, BARS, 28, 420)
    cap = df["phiPn"].max()
    assert rc.column_check(0.5 * cap, 0, df)["ratio"] == approx(0.5, rel=1e-3)
    assert rc.column_check(1000, 100, df)["ok"]
    assert not rc.column_check(1000, 500, df)["ok"]


# --- seismic (NSR-10 Titulo A) ------------------------------------------------
def test_site_coefficients_interpolation():
    assert sismo.site_coefficients("D", 0.15, 0.20) == approx((1.5, 2.0))
    assert sismo.site_coefficients("E", 0.25, 0.25)[0] == approx(1.45)
    with pytest.raises(ValueError):
        sismo.site_coefficients("F", 0.2, 0.2)


def test_spectrum_branches():
    Aa, Av = 0.15, 0.20  # soil D -> Fa = 1.5, Fv = 2.0
    p = sismo.spectrum_periods(Aa, Av, 1.5, 2.0)
    assert p["TC"] == approx(0.48 * 0.4 / 0.225) and p["TL"] == approx(4.8)
    assert sismo.Sa(0.5, Aa, Av, "D") == approx(2.5 * 0.15 * 1.5)
    assert sismo.Sa(1.0, Aa, Av, "D") == approx(1.2 * 0.20 * 2.0 / 1.0)
    assert sismo.Sa(6.0, Aa, Av, "D") == approx(1.2 * 0.20 * 2.0 * 4.8 / 36)
    # continuity at TC and TL
    for T in (p["TC"], p["TL"]):
        assert sismo.Sa(T * (1 - 1e-9), Aa, Av, "D") == approx(sismo.Sa(T * (1 + 1e-9), Aa, Av, "D"), rel=1e-6)
    assert sismo.Sa(0.0, Aa, Av, "D", short_period_ramp=True) == approx(0.4 * 2.5 * 0.15 * 1.5)
    assert sismo.Sa(0.5, Aa, Av, "D", I=sismo.IMPORTANCE["IV"]) == approx(1.5 * 2.5 * 0.15 * 1.5)


def test_period_and_elf():
    Ta = sismo.approx_period(30)
    assert Ta == approx(0.047 * 30**0.9)
    assert sismo.period_limit(Ta, 0.2, 2.0) == approx(1.27 * Ta)
    assert sismo.k_exponent(0.4) == 1 and sismo.k_exponent(1.0) == 1.25 and sismo.k_exponent(3) == 2
    df = sismo.elf([1000] * 4, [3, 6, 9, 12], Sa_g=0.5, T=0.4)
    assert df.attrs["Vs"] == approx(2000)
    assert df["Cvx"].sum() == approx(1)
    assert df["Fx"].tolist() == approx([200, 400, 600, 800])  # k = 1 -> proportional to h
    assert df["story_shear"].iloc[0] == approx(2000)
