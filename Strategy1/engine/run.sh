#!/bin/bash
# Darwinian AI Engine — UCI entry point for elo-test/arena.py and grade.py.
#
# Default: positional_grinder personality on the v2 search core
# (PVS + TT + null-move + LMR + killers + history + aspiration windows).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENGINE_DIR="$SCRIPT_DIR/../engines/mve"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$ENGINE_DIR"

if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    exec "$REPO_ROOT/.venv/bin/python" engine.py --heuristic pesto
else
    exec /usr/bin/python3 engine.py --heuristic pesto
fi
