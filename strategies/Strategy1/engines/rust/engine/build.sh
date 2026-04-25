#!/bin/bash
# Build the Strategy1 Rust engine in release mode.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."
cargo build --release
