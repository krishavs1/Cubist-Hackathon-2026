#!/bin/bash
# UCI entry for the test-driven-development chess engine. Discovered by
# elo-test/grade.py via ENGINE_ROOTS (src/). We prefer the repo's .venv
# interpreter because the system python3 on the grading machine does not
# have python-chess installed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$PROJECT_ROOT/../.." && pwd)"

cd "$PROJECT_ROOT"

if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
  exec "$REPO_ROOT/.venv/bin/python" main.py
else
  exec python3 main.py
fi
