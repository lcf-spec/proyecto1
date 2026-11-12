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

## Environment
- Rebuild with `bash Geotecnia_II/setup.sh` (pinned `requirements.txt`, plus fixes for open3d,
  julian/pyswmm and Debian's blinker).
- pandas is held below 3.0 because of `python-ags4`.
- Aspose.CAD is commercial; never commit `.lic` files.

## Conventions
- State the method and reference (author, year) in every function docstring.
- Use SI units throughout; convert at the edges only.
- Engineering results must be checkable: show inputs, intermediate factors and the final value.
