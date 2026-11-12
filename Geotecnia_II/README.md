# Geotecnia II

Python workspace for the Geotecnia II course: geotechnical, structural, hydraulic, GIS and CAD tools,
all pinned to versions that are known to install and import together on Python 3.13.

## Folder layout

| Path | Contents |
|---|---|
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

## Notebooks

| Notebook | Topic |
|---|---|
| `01_bearing_capacity.ipynb` | Shallow footing bearing capacity: Terzaghi by hand, checked against `geofound` (Terzaghi, Vesic, Meyerhof), q_u vs B plot, footing plan exported to DXF |
