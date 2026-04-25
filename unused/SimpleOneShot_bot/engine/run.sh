#!/bin/bash
# UCI entry point for SimpleOneShot. Discovered by elo-test/grade.py via
# ENGINE_ROOTS. SimpleOneShot_bot/engine.py is a single-file UCI engine
# (PVS + TT + quiescence + null-move + LMR + tapered PeSTO eval).
#
# We prefer the repo's .venv python so python-chess is guaranteed available.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$PROJECT_ROOT/.." && pwd)"

cd "$PROJECT_ROOT"

if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
  exec "$REPO_ROOT/.venv/bin/python" engine.py
else
  exec python3 engine.py
fi
