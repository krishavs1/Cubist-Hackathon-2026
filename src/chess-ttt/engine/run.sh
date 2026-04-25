#!/bin/bash
# Launch the chess-ttt UCI engine. The grader (elo-test/grade.py) discovers
# this file by globbing src/<name>/engine/run.sh and invokes it as a UCI
# subprocess.
#
# We run from the chess-ttt project root so the `src` package import works,
# and prefer the repo's .venv interpreter if present (the system python3 on
# this machine does not have python-chess installed).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$PROJECT_ROOT/../.." && pwd)"

cd "$PROJECT_ROOT"

if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
  exec "$REPO_ROOT/.venv/bin/python" -m src.uci
else
  exec python3 -m src.uci
fi
