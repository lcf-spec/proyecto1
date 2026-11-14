"""Smoke tests: the installed structural packages reproduce closed-form textbook results."""
import pytest

approx = pytest.approx


def test_pycba_two_span_continuous_beam():
    """Two equal spans with a UDL: support moment = -wL^2/8 (three-moment equation)."""
    pycba = pytest.importorskip("pycba")
    w, L = 10.0, 10.0
    ba = pycba.BeamAnalysis([L, L], 30e6, [-1, 0, -1, 0, -1, 0], [[1, 1, w, 0, 0], [2, 1, w, 0, 0]])
    ba.analyze()
    M = ba.beam_results.results.M
    assert M.min() == approx(-w * L**2 / 8, rel=1e-3)


def test_sectionproperties_rectangle():
    """Second moment of area of a 300 x 500 mm rectangle: b h^3 / 12."""
    pytest.importorskip("sectionproperties")
    from sectionproperties.analysis import Section
    from sectionproperties.pre.library import rectangular_section
    geom = rectangular_section(d=500, b=300)
    geom.create_mesh(mesh_sizes=[500])
    sec = Section(geom)
    sec.calculate_geometric_properties()
    ixx, iyy, _ = sec.get_ic()
    assert ixx == approx(300 * 500**3 / 12, rel=1e-6)
    assert iyy == approx(500 * 300**3 / 12, rel=1e-6)


def test_structuralcodes_ec2_concrete():
    """EN 1992-1-1 Table 3.1: C30/37 -> fctm = 0.30 fck^(2/3), Ecm = 22 (fcm/10)^0.3 GPa."""
    pytest.importorskip("structuralcodes")
    from structuralcodes.codes import ec2_2004 as ec2
    assert ec2.fctm(30) == approx(0.30 * 30 ** (2 / 3), rel=1e-6)
    assert ec2.Ecm(38) == approx(22000 * (38 / 10) ** 0.3, rel=1e-6)


def test_openseespy_cantilever_tip_deflection():
    """Elastic cantilever with a tip load: delta = P L^3 / (3 E I)."""
    ops = pytest.importorskip("openseespy.opensees")
    E, I, A, L, P = 200e6, 8e-5, 1e-2, 4.0, 50.0  # kN, m
    ops.wipe()
    ops.model("basic", "-ndm", 2, "-ndf", 3)
    ops.node(1, 0, 0); ops.node(2, L, 0)
    ops.fix(1, 1, 1, 1)
    ops.geomTransf("Linear", 1)
    ops.element("elasticBeamColumn", 1, 1, 2, A, E, I, 1)
    ops.timeSeries("Linear", 1); ops.pattern("Plain", 1, 1); ops.load(2, 0, -P, 0)
    for cmd in (("system", "BandGeneral"), ("numberer", "RCM"), ("constraints", "Plain"),
                ("integrator", "LoadControl", 1.0), ("algorithm", "Linear"), ("analysis", "Static")):
        getattr(ops, cmd[0])(*cmd[1:])
    ops.analyze(1)
    assert -ops.nodeDisp(2, 2) == approx(P * L**3 / (3 * E * I), rel=1e-9)
    ops.wipe()
