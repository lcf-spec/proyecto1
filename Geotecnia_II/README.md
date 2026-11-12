# Geotecnia II

Python workspace for the Geotecnia II course: geotechnical, structural, hydraulic, GIS and CAD tools,
all pinned to versions that are known to install and import together on Python 3.13.

## Folder layout

| Path | Contents |
|---|---|
| `geotools/` | Our own tested library of geotechnical calculations (see below) |
| `tests/` | `pytest` checks of `geotools` against textbook values |
| `requirements.txt` | Pinned package list (~50 packages) |
| `setup.sh` | One-command environment rebuild, including the special cases below |
| `notebooks/` | Calculation notebooks |
| `data/` | Input files: borehole logs (AGS4, GEF), CPTs, DWG/DXF drawings, spreadsheets |
| `outputs/` | Generated plots and drawings (not committed; recreated by running the notebooks) |

## Setup

```bash
cd Geotecnia_II
bash setup.sh
jupyter lab
```

`setup.sh` takes care of three problems you would otherwise hit with a plain `pip install -r requirements.txt`:

1. **open3d** needs the system libraries `libegl1 libgl1 libgomp1` (installed through `apt-get`).
2. **pyswmm** depends on `julian`, which fails to build with Debian's patched setuptools
   (`AttributeError: install_layout`). The fix is `pip install --use-pep517 julian`.
3. **blinker** installed by Debian can't be uninstalled by pip. The fix is `pip install --ignore-installed blinker`.

### Notes

- **pandas is held at 2.3.3** because `python-ags4==1.2.0` requires `pandas<3.0`.
- **Aspose.CAD is commercial.** Without a license it runs in evaluation mode, which adds watermarks.
  Keep any `.lic` file outside the repo; `*.lic` is already in `.gitignore`.
- `pyslope` also installs Django, gunicorn and pytest. They are harmless, just extra weight.

## `geotools` library

Units: kN, m, kPa, kN/m³, degrees. Run the checks with `pytest` from this folder.

| Module | Contents | Checked against |
|---|---|---|
| `classification` | Phase relationships, USCS group symbol (ASTM D2487) | Hand calculations, USCS rules |
| `stresses` | σv, u, σ'v profiles with layers and water table; Boussinesq; Newmark rectangle (any point); circle; 2:1 | Newmark I = 0.1752 (m = n = 1) |
| `consolidation` | NC/OC consolidation settlement, U ↔ Tv, time to consolidate, elastic settlement | Tv(50%) = 0.197, Tv(90%) = 0.848 |
| `earth_pressure` | K0, Rankine and Coulomb Ka/Kp (inclined wall/backfill), active thrust with c, q and tension crack | Das tables |
| `bearing` | Terzaghi; general equation with shape, depth, inclination factors and eccentricity | Das factor tables, `geofound` |
| `slopes` | Infinite slope with seepage; Fellenius and Bishop simplified circles; critical-circle search | Taylor's chart (Ns = 0.191 at 60°, 0.261 vertical) |
| `piles` | Axial pile capacity, API RP 2A (α-method in clay, sand classes 1–5) | Closed-form integrals |

## Notebooks

| Notebook | Topic |
|---|---|
| `02_geotools_tour.ipynb` | One worked example per `geotools` module: stress profile, settlement, wall thrust, bearing capacity, critical slip circle, pile capacity |
| `01_bearing_capacity.ipynb` | Shallow footing bearing capacity: Terzaghi by hand, checked against `geofound` (Terzaghi, Vesic, Meyerhof), q_u vs B plot, footing plan exported to DXF |
