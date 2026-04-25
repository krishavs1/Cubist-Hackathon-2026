#!/bin/bash
# Megaprompt UCI entry. Prefer the repo's .venv interpreter because the
# system python3 does not have python-chess installed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$PROJECT_ROOT/../.." && pwd)"

ENGINE_PY="$SCRIPT_DIR/engine.py"

# -u forces unbuffered stdout/stderr. The engine's UCI loop uses plain
# print() without flush=True; without -u, 'uciok' would sit in Python's
# stdout buffer forever when stdin is a pipe and UCI handshakes hang.
if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
  exec "$REPO_ROOT/.venv/bin/python" -u "$ENGINE_PY"
else
  exec python3 -u "$ENGINE_PY"
fi
