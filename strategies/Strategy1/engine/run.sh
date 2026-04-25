#!/bin/bash
# Darwinian AI Engine — UCI entry point for elo-test/arena.py and grade.py.
#
# Arena default: 'pesto' (tapered PeSTO) + unbuffered Python — matches the
# calibration in Strategy1/results.json and search.py pruning constants.
# Upstream main may use other champions (e.g. reflexion_v1); see ARENA_LOG.md.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENGINE_DIR="$SCRIPT_DIR/../engines/mve"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$ENGINE_DIR"

if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    exec "$REPO_ROOT/.venv/bin/python" -u engine.py --heuristic pesto
else
    exec /usr/bin/python3 -u engine.py --heuristic pesto
fi
