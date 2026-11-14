# Estructuras — NSR-10 / ACI 318

`structools`: tested structural design calculations for Colombia's **NSR-10** (and ACI 318, on which
Título C is based). Installed automatically by `../Geotecnia_II/setup.sh`; run the checks with `pytest` here.

Units: **mm, MPa, kN, kN·m**. Seismic module: m, s, kN, g.

| Module | NSR-10 | Contents |
|---|---|---|
| `concreto` | Título C | β1, Ec, fr, φ from net tensile strain; As,min; flexure by strain compatibility (with optional compression steel); flexural design; Vc, stirrup spacing (strength, max spacing, Av,min); P–M interaction diagram with φ and the axial cap; column check |
| `sismo` | Título A | Fa / Fv (Tables A.2.4-3 and A.2.4-4), importance coefficient, design spectrum (A.2.6), Ta = Ct h^α, Cu Ta limit, k exponent, equivalent lateral force distribution |

Notebook `notebooks/01_nsr10_ejemplo.ipynb` works a 5-storey RC frame building through spectrum → ELF →
beam flexure and shear → column interaction diagram.

## Excel: memoria de cálculo de muros de contención

`excel/MEMORIA_CALCULO_MUROS.xlsx` predimensiona y diseña muros en voladizo siguiendo las notas
*Muros de Contención* (Diseño de Concreto II, basadas en Das 7ed) y NSR-10, con el mismo formato de la
memoria de zapatas: hoja `INPUTS` (una fila por muro), una hoja de memoria por muro y `TABLAS`.
El muro M1 reproduce el ejemplo del documento (`tests/test_muros_excel.py`). Para regenerarlo:
`python excel/build_muros.py excel/MEMORIA_CALCULO_MUROS.xlsx` y ábralo en Excel para recalcular.

## Limits — read before using results for real work

- **Not yet covered:** seismic detailing for DES/DMO (Título C.21: confinement, strong column–weak beam,
  capacity-design shear), slenderness, biaxial bending, T-beams, development length, deflections,
  two-way slabs, and steel (Título F / AISC 360).
- **Aa, Av** come from NSR-10 Appendix A-4 or the local microzonation study; the code does not look them up.
- The Fa/Fv tables and the spiral φ = 0.75 were entered from the code text — check them against your copy
  of NSR-10 (see the docstrings).
- `shear_design` excludes C.21 confinement rules, which usually govern near supports in seismic frames.
- The ELF function returns elastic forces Fs; design forces are E = Fs / R.
