"""Phase relationships and USCS classification (ASTM D2487, group symbol only)."""
from __future__ import annotations

GAMMA_W = 9.81


def phase_relations(Gs: float, e: float, w: float, gamma_w: float = GAMMA_W) -> dict:
    """Soil phase relationships from specific gravity Gs, void ratio e and water content w (decimal)."""
    S = w * Gs / e
    return {
        "e": e,
        "n": e / (1 + e),
        "w": w,
        "S": S,
        "gamma_d": Gs * gamma_w / (1 + e),
        "gamma": Gs * gamma_w * (1 + w) / (1 + e),
        "gamma_sat": (Gs + e) * gamma_w / (1 + e),
        "gamma_sub": (Gs - 1) * gamma_w / (1 + e),
    }


def a_line(LL: float) -> float:
    """Casagrande A-line: PI = 0.73 (LL - 20)."""
    return 0.73 * (LL - 20)


def fine_symbol(LL: float, PL: float) -> str:
    """Classify fines from Atterberg limits: CL, ML, CL-ML, CH or MH (inorganic)."""
    PI = LL - PL
    above = PI >= a_line(LL)
    if LL < 50:
        if PI > 7 and above:
            return "CL"
        if 4 <= PI <= 7 and above:
            return "CL-ML"
        return "ML"
    return "CH" if above else "MH"


def uscs(F200: float, F4: float = 100.0, LL: float | None = None, PL: float | None = None,
         Cu: float | None = None, Cc: float | None = None) -> str:
    """USCS group symbol.

    F200: % passing No. 200 sieve (fines); F4: % passing No. 4 sieve.
    LL, PL: Atterberg limits (needed when F200 >= 5). Cu, Cc: needed when F200 <= 12.
    """
    if F200 >= 50:
        if LL is None or PL is None:
            raise ValueError("Fine-grained soil: LL and PL are required")
        return fine_symbol(LL, PL)

    gravel, sand = 100 - F4, F4 - F200
    p = "G" if gravel > sand else "S"

    def grading() -> str:
        if Cu is None or Cc is None:
            raise ValueError("Coarse soil with < 12% fines: Cu and Cc are required")
        cu_min = 4 if p == "G" else 6
        return f"{p}W" if (Cu >= cu_min and 1 <= Cc <= 3) else f"{p}P"

    def fines() -> str:
        if LL is None or PL is None:
            raise ValueError("Coarse soil with >= 5% fines: LL and PL are required")
        f = fine_symbol(LL, PL)
        return {"CL": f"{p}C", "CH": f"{p}C", "CL-ML": f"{p}C-{p}M"}.get(f, f"{p}M")

    if F200 < 5:
        return grading()
    if F200 > 12:
        return fines()
    f = fines()
    return f"{grading()}-{p}C" if f.startswith(f"{p}C") else f"{grading()}-{p}M"
