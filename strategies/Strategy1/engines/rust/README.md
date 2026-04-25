# strategy1-rust

Rust port of the Strategy1 Darwinian + Reflexion chess engine.

## Why Rust?

Python was the bottleneck. The Python engine searches ~20k nodes/sec; the
Rust port searches ~5-10M nodes/sec -- roughly **200-500x faster**. At the
same time control that gets us 2-3 extra plies of search depth, which is
worth ~150-250 Elo on top of the Python baseline.

## Architecture

Faithful port of `Strategy1/engines/mve/` -- same search features, same
evaluation, same champion:

- **Search (`src/search.rs`)**: PVS + iterative deepening + aspiration
  windows + quiescence + transposition table + null-move pruning + LMR +
  killers + history + check extensions + reverse-futility + futility +
  razoring.

- **Evaluation (`src/eval.rs`)**: PeSTO tapered (MG/EG interpolation) +
  the `reflexion_v1` additions the Reflexion loop learned from loss PGNs
  (development bonus, castling bonus/penalty, rim-knight penalty,
  early-queen penalty).

- **UCI (`src/main.rs`)**: full UCI protocol with FEN parsing and
  wtime/btime/winc/binc/movetime time management.

## Build

```bash
./engine/build.sh   # cargo build --release
```

## Run

```bash
./engine/run.sh     # auto-builds if needed, then launches UCI loop
```

The top-level `Strategy1/engine/run.sh` calls this script and falls back
to the Python engine if the Rust build fails.
