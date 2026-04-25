#!/usr/bin/env bash
# Launch OneShotOpus as a UCI engine. Suitable for cutechess-cli, Arena, etc.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$DIR/engine.py" "$@"
