#!/bin/bash
# UCI launcher for the Strategy1 Rust engine.
# Builds on first run, then executes the release binary.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CRATE_DIR="$SCRIPT_DIR/.."
BIN="$CRATE_DIR/target/release/strategy1-rust"

if [ ! -x "$BIN" ]; then
    cargo build --release --manifest-path "$CRATE_DIR/Cargo.toml" >&2
fi

exec "$BIN"
