# Chess Engine MVP — Cubist Hackathon 2026

A test-driven chess engine built with AI as an engineering collaborator.

## Setup

```bash
cd src/test-driven-development
pip install -r requirements.txt
```

## Run Tests

```bash
pytest
```

Expected output: all tests pass across `test_evaluate`, `test_search`, `test_bot`, `test_uci`.

## Run Benchmark (engine vs random bot)

```bash
python benchmark.py --games 20 --depth 2
```

Plays 20 games alternating colors and reports win/loss/draw rate.

## Use as UCI Engine

```bash
python main.py --depth 3
```

Then communicate over stdin/stdout using the UCI protocol. Compatible with Arena, Cute Chess, and Lichess bot API.

Example session:
```
uci
→ id name HackathonEngine
→ id author Cubist Hackathon 2026
→ uciok
isready
→ readyok
position startpos moves e2e4 e7e5
go depth 3
→ bestmove g1f3
quit
```

## Architecture

| Layer | File(s) | Responsibility |
|---|---|---|
| Evaluation | `engine/evaluate.py` | Material + piece-square tables → centipawn score |
| Search | `engine/search.py` | Negamax alpha-beta, move ordering |
| Bots | `bot/` | `RandomBot` and `EngineBot` share a `BaseBot` interface |
| UCI | `uci/adapter.py` | Parses UCI commands, drives search, returns responses |
| Benchmark | `benchmark.py` | Plays engine vs random, reports win rate |

## TDD Workflow

See [docs/workflow.md](docs/workflow.md) for the full development loop.

The engineering story: every feature is introduced by writing a failing test first, implementing the minimum to pass it, and then verifying no benchmark regression. AI prompts that generated each feature are logged in `docs/prompts/`.

## Extending the Engine

The clean layering makes each of these straightforward next steps:

- **Quiescence search** — extend `_negamax` in `engine/search.py`
- **Transposition table** — add a dict cache keyed by `board.zobrist_hash()`
- **New evaluation term** — add a function to `engine/evaluate.py` and write a test for it
- **Stockfish comparison** — use `chess.engine.SimpleEngine` in the benchmark
- **Engine personality** — tune `PIECE_VALUES` weights and run a tournament
