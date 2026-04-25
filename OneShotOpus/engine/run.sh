#!/bin/bash
# UCI entry point for OneShotOpus. Discovered by elo-test/grade.py via
# DIRECT_ENGINES (OneShotOpus/engine/run.sh). engine.py does `from search
# import Searcher`, so we cd into the project root before exec'ing.
#
# We prefer the repo's .venv python because the system python3 on the
# grading machine does not have python-chess installed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$PROJECT_ROOT/.." && pwd)"

cd "$PROJECT_ROOT"

if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    exec "$REPO_ROOT/.venv/bin/python" -u engine.py
else
    exec python3 -u engine.py
fi
