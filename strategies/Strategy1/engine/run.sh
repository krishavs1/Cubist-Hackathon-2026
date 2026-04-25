#!/bin/bash
# Darwinian AI Engine -- UCI entry point for elo-test/arena.py and grade.py.
#
# Champion: 'reflexion_v1' -- promoted by the Reflexion loop (Workstream E)
# on 2026-04-25. See ARENA_LOG.md for the tournament block that produced this
# selection. The tournament picked this personality; it is not a human override.
#
# Lineage:
#   * Phase 1: Darwinian tournament picked 'positional_grinder' (undefeated
#     in 30-game round-robin, ARENA_LOG.md block dated 2026-04-24).
#   * Phase 2: Reflexion loop (Workstream E) read 10 loss PGNs vs Stockfish,
#     wrote reflexion_v1 (adds development + castling + rim-knight + early-queen
#     heuristics on top of positional_grinder), and the verification tournament
#     crowned reflexion_v1 as the new champion (Elo 1213 vs positional_grinder
#     1187 and fortress 1200).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENGINE_DIR="$SCRIPT_DIR/../engines/mve"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$ENGINE_DIR"

if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    exec "$REPO_ROOT/.venv/bin/python" engine.py --heuristic reflexion_v1
else
    exec /usr/bin/python3 engine.py --heuristic reflexion_v1
fi
