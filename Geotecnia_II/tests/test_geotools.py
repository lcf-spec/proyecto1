"""Checks against textbook values (Das, Coduto, Craig, Taylor) and against geofound."""
import math

import pytest
from scipy.integrate import quad

from geotools import bearing, classification as cl, consolidation as co
from geotools import earth_pressure as ep, piles, slopes, stresses as st

approx = pytest.approx


# --- classification -------------------------------------------------------
def test_phase_relations():
    p = cl.phase_relations(Gs=2.7, e=0.6, w=0.2)
    assert p["S"] == approx(0.9)
    assert p["gamma_d"] == approx(2.7 * 9.81 / 1.6)
    assert p["gamma_sat"] == approx(3.3 * 9.81 / 1.6)


@pytest.mark.parametrize("kw,expected", [
    (dict(F200=60, LL=45, PL=20), "CL"),
    (dict(F200=60, LL=60, PL=25), "CH"),
    (dict(F200=60, LL=60, PL=40), "MH"),
    (dict(F200=60, LL=30, PL=27), "ML"),
    (dict(F200=60, LL=25, PL=19), "CL-ML"),
    (dict(F200=3, F4=40, Cu=5, Cc=2), "GW"),
    (dict(F200=3, F4=90, Cu=4, Cc=2), "SP"),
    (dict(F200=20, F4=80, LL=30, PL=15), "SC"),
    (dict(F200=8, F4=85, Cu=7, Cc=1.5, LL=30, PL=25), "SW-SM"),
])
def test_uscs(kw, expected):
    assert cl.uscs(**kw) == expected


# --- stresses ---------------------------------------------------------------
def test_vertical_stress_layers_and_water_table():
    layers = [{"thickness": 3, "gamma": 17, "gamma_sat": 19},
              {"thickness": 5, "gamma": 18, "gamma_sat": 20}]
    s, u, se = st.vertical_stress(layers, 6, water_table=2)
    assert s == approx(2 * 17 + 1 * 19 + 3 * 20)
    assert u == approx(4 * 9.81)
    assert se == approx(s - u)


def test_boussinesq_point():
    assert st.boussinesq_point(100, 2) == approx(3 * 100 / (2 * math.pi * 4))


def test_newmark_corner_factor():
    assert st.rect_corner_influence(1, 1, 1) == approx(0.1752, abs=1e-4)
    assert st.rect_corner_influence(1000, 1000, 1) == approx(0.25, abs=1e-3)


def test_rect_stress_superposition():
    q, z = 100, 2
    assert st.rect_stress(q, 2, 2, z) == approx(4 * q * st.rect_corner_influence(1, 1, z))
    assert st.rect_stress(q, 2, 2, z, x=1, y=1) == approx(q * st.rect_corner_influence(2, 2, z))
    outside = st.rect_stress(q, 2, 2, z, x=2, y=0)  # 1 m outside the edge
    expected = q * (2 * st.rect_corner_influence(3, 1, z) - 2 * st.rect_corner_influence(1, 1, z))
    assert outside == approx(expected)


def test_circle_large_radius_tends_to_q():
    assert st.circle_center_stress(100, 1000, 1) == approx(100, rel=1e-3)


# --- consolidation ------------------------------------------------------------
def test_nc_settlement():
    assert co.consolidation_settlement(3, 1.0, 0.3, 100, 100) == approx(1.5 * 0.3 * math.log10(2))


def test_oc_settlement_crossing_sigma_p():
    s = co.consolidation_settlement(3, 1.0, 0.3, 100, 100, Cs=0.05, sigma_p=150)
    assert s == approx(1.5 * (0.05 * math.log10(1.5) + 0.3 * math.log10(200 / 150)))


@pytest.mark.parametrize("U,Tv", [(0.5, 0.197), (0.9, 0.848), (0.6, 0.287)])
def test_time_factor_table(U, Tv):
    assert co.time_factor(U) == approx(Tv, abs=1e-3)


# --- earth pressure -----------------------------------------------------------
def test_rankine_and_coulomb_basic():
    assert ep.rankine_ka(30) == approx(1 / 3)
    assert ep.rankine_kp(30) == approx(3)
    assert ep.coulomb_ka(30) == approx(1 / 3)
    assert ep.coulomb_kp(30) == approx(3)
    assert ep.k0_jaky(30) == approx(0.5)


def test_tabulated_coefficients():
    assert ep.coulomb_ka(30, delta=20) == approx(0.2973, abs=1e-3)   # Das, Coulomb Ka table
    assert ep.rankine_ka(30, beta=10) == approx(0.3495, abs=1e-3)    # Das, Rankine inclined backfill


def test_active_thrust():
    r = ep.rankine_active_thrust(6, 18, 30)
    assert r["Pa"] == approx(108) and r["y"] == approx(2)
    r = ep.rankine_active_thrust(6, 18, 0, c=20)
    assert r["zc"] == approx(40 / 18)
    assert r["Pa"] == approx(68 * (6 - 40 / 18) / 2)


# --- bearing capacity ---------------------------------------------------------
def test_bearing_factors_tables():
    assert bearing.general_factors(30) == approx((30.14, 18.40, 22.40), abs=0.01)
    Nc, Nq, _ = bearing.terzaghi_factors(30)
    assert (Nc, Nq) == approx((37.16, 22.46), abs=0.01)


def test_terzaghi_matches_geofound():
    gf = pytest.importorskip("geofound")
    sl = gf.create_soil(phi=30, cohesion=10e3, unit_dry_weight=18e3)
    fd = gf.create_foundation(length=2, width=2, depth=1.5)
    assert bearing.terzaghi(10, 30, 18, 2, 1.5, "square") == approx(
        gf.capacity_terzaghi_1943(sl, fd) / 1e3, rel=1e-6)


def test_general_undrained_square():
    r = bearing.general(c=50, phi=0, gamma=18, B=2, Df=1, L=2)
    assert r["qu"] == approx(50 * 5.14 * (1 + 1 / 5.14) * 1.2 + 18, rel=1e-6)


# --- slopes -----------------------------------------------------------------
def test_infinite_slope_dry_sand():
    assert slopes.infinite_slope(20, 30) == approx(math.tan(math.radians(30)) / math.tan(math.radians(20)))


@pytest.mark.parametrize("beta,Ns", [(60, 0.191), (89.9, 0.261)])
def test_taylor_chart_undrained(beta, Ns):
    H, gamma, c = 10, 20, 50
    r = slopes.critical_circle(H, beta, c, 0, gamma)
    assert c / (r["FS"] * gamma * H) == approx(Ns, rel=0.03)


def test_bishop_vs_fellenius():
    args = (10, 45, 15, 25, 19, 3, 16, 17)
    assert slopes.circle_fs(*args) > slopes.circle_fs(*args, method="fellenius")


# --- piles ------------------------------------------------------------------
def test_alpha_api():
    assert piles.alpha_api(50, 100) == approx(0.5 / math.sqrt(0.5))
    assert piles.alpha_api(50, 25) == approx(0.5 * 2 ** -0.25)


def test_pile_in_sand():
    r = piles.pile_capacity(0.5, 10, [{"thickness": 15, "gamma": 18, "sand": 3}])
    shaft = math.pi * 0.5 * 0.8 * 18 * math.tan(math.radians(25)) * 10**2 / 2
    assert r["Qs"] == approx(shaft, rel=1e-6)
    assert r["Qb"] == approx(20 * 180 * math.pi * 0.25 / 4)


def test_pile_in_clay():
    r = piles.pile_capacity(0.5, 10, [{"thickness": 15, "gamma": 18, "cu": 50}])
    exact, _ = quad(lambda z: piles.alpha_api(50, 18 * z) * 50, 0, 10, points=[50 / 18])
    assert r["Qs"] == approx(exact * math.pi * 0.5, rel=1e-3)
    assert r["Qb"] == approx(9 * 50 * math.pi * 0.25 / 4)
