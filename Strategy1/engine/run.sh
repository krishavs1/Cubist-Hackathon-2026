#!/bin/bash
# Darwinian AI Engine — UCI entry point for elo-test/arena.py and grade.py.
#
# Champion: 'fortress' — selected by the internal round-robin Darwinian
# tournament (Elo 1226, 66.7% win rate, beat all other personalities).
# This personality is NOT hand-picked; it is what the tournament chose.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENGINE_DIR="$SCRIPT_DIR/../engines/mve"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$ENGINE_DIR"

if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    exec "$REPO_ROOT/.venv/bin/python" engine.py --heuristic fortress
else
    exec /usr/bin/python3 engine.py --heuristic fortress
fi
