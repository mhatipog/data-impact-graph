#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
. .venv/bin/activate
python -m pip install -q -r requirements.txt
if [ ! -s data/sample.rl ]; then
  python -m data_impact_graph seed
fi
exec python -m data_impact_graph "${@:-serve}"
