#!/bin/bash
# Launch the chess-ttt UCI engine. The grader (elo-test/grade.py) discovers
# this file by globbing src/<name>/engine/run.sh and invokes it as a UCI
# subprocess.
#
# We run from the chess-ttt project root so the `src` package import works.
set -e
cd "$(dirname "$0")/.."
exec python3 -m src.uci
