"""The retaining-wall workbook reproduces the worked example in the course notes
(Muros de Contención, G. A. Chang Nieto, based on Das 7th ed. Example 8.1).

Reads the cached values of the committed, recalculated workbook. After changing
excel/build_muros.py, rebuild and recalculate the workbook before running this.
"""
from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl")
XLSX = Path(__file__).resolve().parents[1] / "excel" / "MEMORIA_CALCULO_MUROS.xlsx"


@pytest.fixture(scope="module")
def m1():
    ws = openpyxl.load_workbook(XLSX, data_only=True)["M1"]
    vals = {}
    for row in ws.iter_rows(min_row=7, max_row=ws.max_row, min_col=2, max_col=13):
        for i in (0, 4, 8):
            lab, val = row[i].value, row[i + 1].value
            if isinstance(lab, str) and val is not None:
                vals.setdefault(lab.strip(), []).append(val)
    return vals


# label in the sheet -> value in the course notes (tolerance covers the notes' rounding)
EXPECTED = [
    ("H' = H1 + H2 + H3", 7.158, 0.002),
    ("Pa = ½ γ1 H'² Ka", 162.9, 0.1),
    ("Pv = Pa sen(ángulo)", 28.29, 0.01),
    ("Ph = Pa cos(ángulo)", 160.43, 0.02),
    ("ΣMo = Ph·H'/3 (ec. 8.3)", 382.79, 0.02),
    ("Opción 1: ΣMR / ΣMo", 2.95, 0.005),
    ("Pp = ½Kpγ2D² + 2c'2√Kp D", 215.0, 0.05),
    ("FS con Pp", 2.70, 0.005),
    ("e = B/2 − (ΣMR−ΣMo)/ΣV", 0.411, 0.002),
    ("q punta = ΣV/B (1+6e/B)", 190.2, 0.5),
    ("q talón = ΣV/B (1−6e/B)", 45.13, 0.5),
    ("Mu = 1.6·ΣMo", 612.46, 0.02),
    ("Vu = 1.6·Ph", 256.69, 0.03),
    ("Vc = 0.17λ√f'c b d", 566.72, 0.01),
    ("Mu talón", -295.50, 1.0),      # notes round e to 0.40
    ("Vu talón (− hacia abajo)", -163.10, 0.1),
]


@pytest.mark.parametrize("label,expected,tol", EXPECTED)
def test_matches_course_example(m1, label, expected, tol):
    assert m1[label][0] == pytest.approx(expected, abs=tol)


def test_reinforcement_matches_notes(m1):
    assert m1["ρ requerida"][0] == pytest.approx(0.00424, abs=2e-5)       # stem
    assert m1["As = ρ b d"][0] == pytest.approx(26.71, abs=0.02)          # stem, cm²/m
    assert m1["As = ρ b d"][1] == pytest.approx(11.34, abs=0.01)          # toe (ρmin)
    assert m1["As = ρ b d"][2] == pytest.approx(12.66, abs=0.02)          # heel
    assert m1["Refuerzo opción 1"][0] == "1 No.6 @ 0.10 m"
    assert m1["Refuerzo opción 2"][0] == "1 No.7 @ 0.14 m"
