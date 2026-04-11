#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ ! -d "venv" ]]; then
  echo "venv/ not found. Create it first (see scripts/run_demo.sh)."
  exit 1
fi

source venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q

