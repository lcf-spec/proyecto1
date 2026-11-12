#!/usr/bin/env bash
# Rebuilds the Geotecnia II Python environment.
# Usage (from this folder):  bash setup.sh
set -euo pipefail
cd "$(dirname "$0")"

# System libraries needed by open3d (Debian/Ubuntu). Skipped if apt-get is unavailable.
if command -v apt-get >/dev/null 2>&1; then
  SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
  $SUDO apt-get update -q && $SUDO apt-get install -y -q libegl1 libgl1 libgomp1
fi

# julian (needed by pyswmm) fails with Debian's patched setuptools unless built in isolation.
pip install --use-pep517 julian==0.14

# Debian's own blinker can't be uninstalled by pip; install ours alongside it.
pip install --ignore-installed blinker || true

pip install -r requirements.txt
echo "Geotecnia II environment ready."
