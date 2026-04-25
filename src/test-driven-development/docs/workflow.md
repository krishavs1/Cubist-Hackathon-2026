# TDD + AI Engineering Workflow

This document describes the development loop used to build this chess engine.

## The Loop

```
success criteria → tests → implementation → test results → benchmark → iterate
```

Each feature added to the engine follows this sequence:

1. **Define success criteria** — what does "correct" look like? (e.g., "engine finds mate in 1")
2. **Write the test first** — encode the criteria as a pytest test before writing any implementation
3. **Implement minimally** — write only enough code to make the test pass
4. **Run tests** — verify correctness at the unit level
5. **Run benchmark** — verify improvement at the system level (win rate vs random bot)
6. **Log the prompt** — record the AI prompt used to generate or modify the feature (see `docs/prompts/`)
7. **Commit** — the commit message references the test and benchmark delta

## Directory Structure

```
engine/       Core logic — evaluation and search. All functions are pure and testable.
bot/          Player abstractions. Bots wrap the engine for use in games.
uci/          UCI protocol adapter. Separates I/O from logic.
tests/        One test file per module. Tests are the spec.
docs/prompts/ Log of AI prompts used at each iteration.
benchmark.py  Plays engine vs random bot and reports win rate.
main.py       UCI entry point for connecting to chess GUIs.
```

## Adding a Feature (example: alpha-beta pruning)

1. Write a test verifying the engine finds the same move as brute-force minimax
2. Implement alpha-beta in `engine/search.py`
3. Run `pytest` — both old and new tests must pass
4. Run `python benchmark.py --games 40` — win rate should not drop
5. Log the AI prompt in `docs/prompts/`

## Benchmark Interpretation

| Win rate vs random | Interpretation |
|---|---|
| < 60% | Engine is weak — likely a bug |
| 60–80% | Material evaluation working |
| 80–95% | Search depth and ordering helping |
| > 95% | Strong for this level — consider Stockfish comparison |

## Planned Iterations

- [ ] Move ordering improvements (history heuristic, killer moves)
- [ ] Quiescence search (avoid horizon effect on captures)
- [ ] Transposition table (cache repeated positions)
- [ ] Iterative deepening with time control
- [ ] UCI `go movetime` support
- [ ] Stockfish comparison via `chess.engine`
- [ ] Engine personalities via evaluation weight tuning
