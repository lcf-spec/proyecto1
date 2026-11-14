# proyecto1 — civil / geotechnical engineering workspace

The owner is a civil engineering student (Geotecnia II) building a toolkit for coursework and professional practice.

## Layout
- `Geotecnia_II/` — Python workspace. Read its `README.md` first.
  - `geotools/` — our tested calculation library (kN, m, kPa, kN/m³, degrees).
  - `tests/` — run `pytest` from `Geotecnia_II/`. Every new calculation needs a test against a
    textbook value, a closed-form result, or another library (e.g. `geofound`, `pyslope`).
  - `notebooks/` — worked calculations; keep them runnable top to bottom
    (`jupyter nbconvert --to notebook --execute`).
  - `data/` — input files (AGS4, GEF/CPT, LAS, DWG/DXF, spreadsheets).
  - `outputs/` — generated files, not committed.

- `Estructuras/` — structural design per **NSR-10 (Colombia) and ACI 318**, the codes the owner uses.
  - `structools/concreto.py` — Título C (based on ACI 318-08): flexure, shear, P-M diagrams.
  - `structools/sismo.py` — Título A: Fa/Fv, design spectrum, Ta, equivalent lateral force.
  - Units here are **mm, MPa, kN, kN·m** (the NSR-10 convention); seismic uses m, s, g.
  - Cite the NSR-10 clause in every docstring, and note where ACI 318-19 differs.
  - Run its tests with `pytest` from `Estructuras/`.

## Environment
- Rebuild with `bash Geotecnia_II/setup.sh` (also installs `geotools` and `structools`) (pinned `requirements.txt`, plus fixes for open3d,
  julian/pyswmm and Debian's blinker).
- pandas is held below 3.0 because of `python-ags4`.
- Aspose.CAD is commercial; never commit `.lic` files.

## Conventions
- State the method and reference (author, year) in every function docstring.
- Use SI units throughout; convert at the edges only.
- Engineering results must be checkable: show inputs, intermediate factors and the final value.
