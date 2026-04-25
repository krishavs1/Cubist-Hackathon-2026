# Token Usage Log

A running log of Claude Code prompts/runs against this project, with rough
token estimates (Claude Code does not surface exact per-turn counts in the
CLI; numbers below are author estimates from the prompt and output sizes).

---

## Run 1 — 2026-04-24 — Initial Tic-Tac-Toe MVP

**Prompt summary:** Build a Tic-Tac-Toe engine using minimax + alpha-beta,
modular file layout, scalable to chess. Include unit tests, instrumentation,
CLI, and an explanation of the abstraction bridge to chess.

**Approximate token usage:**
- Input: ~1.6k tokens (project prompt + system context)
- Output: ~6k tokens (code + tests + README + this file)

**Files created:**
- `src/__init__.py`
- `src/game.py` — board, legal moves, make/undo, terminal detection
- `src/evaluate.py` — depth-adjusted terminal scoring
- `src/search.py` — generic alpha-beta + instrumentation
- `src/cli.py` — human-vs-engine CLI
- `src/main.py` — entry point with `--play-as` flag
- `tests/__init__.py`
- `tests/test_game.py` — 19 tests on rules
- `tests/test_search.py` — 50 tests on search (winning, blocking, legality,
  unloseable play, instrumentation, parametrized)
- `README.md` — usage, test list, architecture bridge to chess
- `TOKEN_USAGE.md` — this file

**Outcome:**
- 69 tests pass (`python3 -m pytest tests/ -v` runs in ~1.2s).
- Engine vs. engine draws (perfect play). Engine never loses to a random
  opponent across 40 seeded games (20 as X, 20 as O).
- From the empty board: 20,866 nodes searched, 7,692 cutoffs, score 0.
- CLI launches and reports `(score, nodes, cutoffs)` per engine move.

**Notes / debugging:**
- `pytest` was not installed in the system Python; installed via
  `python3 -m pip install pytest` before running the suite.
- No bugs encountered in the initial implementation; all tests passed on
  first run.

---

## Run 2 — 2026-04-24 — Search generalization for chess reuse

**Prompt summary:** As part of scaling to chess, the TTT search needed to
become fully game-agnostic so the same file could be used by both projects
unchanged.

**Approximate token usage:**
- Input: ~0.4k tokens (prompt fragment for this refactor)
- Output: ~0.3k tokens (small edits)

**Files changed:**
- `src/game.py` — added `is_maximizing_player()` method on `Game`.
- `src/search.py` — removed `from .game import Game, X`; replaced
  `current_player() == X` with `game.is_maximizing_player()`; loosened
  type hints to `Optional[Any]` for `best_move`; added `depth_reached`
  field to `SearchStats`.

**Outcome:**
- All 69 TTT tests still pass.
- After the refactor, `src/tic-tac-toe/src/search.py` is byte-identical
  to `src/chess/src/search.py`. Verified with `diff`. This is the
  primary architectural result of the methodology test.

---

<!--
Template for future runs:

## Run N — YYYY-MM-DD — Short title

**Prompt summary:**
**Approximate token usage:** input ~?k, output ~?k
**Files changed:**
**Outcome:**
**Notes / debugging:**
-->
