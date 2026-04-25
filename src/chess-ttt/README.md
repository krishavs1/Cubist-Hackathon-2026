# Chess Engine (scaled from the verified Tic-Tac-Toe MVP)

A working chess engine using the **same alpha-beta search code** that was
verified on Tic-Tac-Toe. The only things that changed are the game module
(now wraps `python-chess`) and the evaluator (now computes material +
piece-square tables + mobility, with depth-adjusted mate scoring).

The architecture is deliberately identical to the Tic-Tac-Toe project:

```
src/
  game.py       # ChessGame wrapping python-chess; same generic interface as TTT Game
  search.py     # BYTE-IDENTICAL copy of the TTT search.py
  evaluate.py   # material + PST + mobility, with mate-score depth adjustment
  cli.py        # human-vs-engine CLI (accepts UCI and SAN moves)
  main.py       # entry point with --play-as / --depth flags
tests/
  test_game.py
  test_search.py
README.md
TOKEN_USAGE.md
```

`search.py` here and `search.py` in the Tic-Tac-Toe project are the same
file. We verified this with `diff`:

```bash
diff src/tic-tac-toe/src/search.py src/chess/src/search.py  # no output
```

That is the headline result of the experiment: the verified search code
transferred unchanged.

## Requirements

- Python 3.9+
- `python-chess` (`pip install python-chess`)
- `pytest` (only for running tests)

## Running

From `src/chess/`:

```bash
# Play as White at default depth (3)
python3 -m src.main

# Play as Black, deeper search (4 plies — slower)
python3 -m src.main --play-as black --depth 4
```

You enter moves in either UCI (`e2e4`, `g1f3`, `e7e8q` for promotion) or
SAN (`e4`, `Nf3`, `O-O`). The CLI prints the engine's score, depth,
nodes searched, and cutoffs after each engine move.

## Tests

```bash
python3 -m pytest tests/ -v
```

26 tests covering:

- **Generic interface.** Initial position has 20 legal moves; `current_player`
  and `is_maximizing_player` agree with `python-chess`; `make_move` rejects
  illegal moves; `undo_move` round-trips state including castling.
- **Terminal detection.** Back-rank checkmate, fool's mate, classic
  stalemate. `get_legal_moves()` returns `[]` at terminal nodes.
- **Search correctness.** Engine returns only legal moves (from the start
  and from random positions). Engine finds Scholar's mate (Qxf7#),
  back-rank mate (Ra8#), and a black mate-in-1 (Qa1#). Engine captures a
  hanging queen with the knight. Engine does not leave its own queen
  hanging.
- **Depth and instrumentation.** Search returns at depths 1, 2, 3.
  `nodes_searched` grows monotonically with depth. Alpha-beta cutoffs > 0.

## Performance

From the starting position (single-threaded, no move ordering):

| Depth | Nodes searched | Cutoffs | Time   |
|-------|---------------:|--------:|-------:|
| 1     | 21             | 0       | <1 ms  |
| 2     | 84             | 18      | ~10 ms |
| 3     | 805            | 54      | ~50 ms |

This is *not* a strong engine. Without move ordering, transposition
tables, or quiescence, depth 3-4 is the practical ceiling for an
interactive CLI. The point of this code is architectural correctness,
not playing strength.

## Comparison: Tic-Tac-Toe → Chess

| TTT component       | Chess equivalent                               | Reused? | Changed? | Why |
|---------------------|------------------------------------------------|:-------:|:--------:|-----|
| `game.py` `Game`    | `game.py` `ChessGame` wrapping `chess.Board`   | ❌      | ✅        | Chess rules (sliding pieces, castling, en passant, promotion, draw rules) are far beyond what we want to hand-roll. Delegated to `python-chess`. |
| 9-cell list         | 8×8 board + side-to-move + castling rights + en-passant target + halfmove clock + Zobrist hash | ❌      | ✅        | Chess state is much larger. Encapsulated inside `chess.Board`. |
| `int 0..8` move     | `chess.Move` (from-square, to-square, promotion piece) | ❌      | ✅        | Move encoding has to express promotion + special moves. `chess.Move` already does this and serializes to/from UCI strings. |
| Make/undo via history list | `chess.Board.push` / `chess.Board.pop` | ❌      | ✅        | Same discipline (mutate one shared object as the search walks down/up the tree); python-chess implements it. |
| `get_legal_moves`   | `list(board.legal_moves)`                      | ❌      | ✅        | Replaced with python-chess's legal generator. Output type changes from `int` to `chess.Move` but the *interface* is identical. |
| `is_terminal`       | `board.is_game_over(claim_draw=False)`          | ❌      | ✅        | Now covers checkmate + stalemate + insufficient material + 75-move + fivefold repetition. |
| `is_maximizing_player()` | `board.turn == chess.WHITE`               | ✅      | ⚠️ trivial | One-line change inside the wrapper; the *interface name* is the same one the TTT search calls. |
| `evaluate.py`       | Material + PST + mobility, mate scoring        | ❌      | ✅        | Tic-Tac-Toe is solved at terminal; chess is not. Needs a heuristic for non-terminal positions. |
| Depth-adjusted mate scoring (`±WIN_SCORE ∓ ply`) | Same trick: `±WIN_SCORE ∓ ply` for `is_checkmate()` | ✅      | ❌        | Identical arithmetic. Lifted from the TTT evaluator as a pattern. |
| `WIN_SCORE`         | `WIN_SCORE` (now in centipawns)                | ✅      | ⚠️ value-only | Constant rescaled (1000 → 100 000 cp) so material can't drown out a mate score. |
| `search.py` (alpha-beta) | `search.py` — **byte-identical copy**     | ✅      | ❌        | This is the whole point of the exercise. The TTT-verified code works on chess unchanged. |
| `SearchStats`       | `SearchStats` — same dataclass                 | ✅      | ⚠️ added field | Added `depth_reached` because chess can't search to terminal. `nodes_searched`, `cutoffs`, `best_move`, `score` are unchanged. |
| `cli.py`            | `cli.py` — same shape, takes UCI/SAN strings   | ✅      | ⚠️ I/O    | Same loop; only the move-parsing front-end changed. |
| Tests               | Same shape (legality / mate detection / mate-in-1 / "engine doesn't blunder") | ✅      | ⚠️ scenarios | Test *patterns* reused; test *positions* are obviously chess-specific. |

Legend: ✅ reused / unchanged · ❌ replaced · ⚠️ small change

## Did the small-game-first methodology help?

**Yes.** Three things became visible because TTT was small enough to debug
end-to-end before chess existed:

1. **The interface contract surfaced bugs early.** When I first wrote the
   TTT search, I had `from .game import X` and `current_player() == X` —
   a TTT-specific reference inside what was supposed to be game-agnostic
   code. That coupling was invisible until I tried to scale: the cleanest
   way to point chess at the same search was to refactor that one line
   into `game.is_maximizing_player()`. **One small change to the search,
   then byte-identical reuse.** That refactor would have been much harder
   to identify — and easier to get wrong — if I'd jumped straight to
   chess.

2. **Mate-score depth adjustment was already proven.** Without TTT I'd
   have implemented `+WIN_SCORE` flat and discovered later that the engine
   plays mate-in-5 instead of mate-in-1 because both score the same. With
   TTT the lesson and the implementation pattern were already there.
   `evaluate.py` for chess just dropped the same `±WIN_SCORE ∓ ply` trick
   into its checkmate branch.

3. **Search instrumentation paid off immediately.** When the
   "captures hanging queen" test failed, the score being `0` was
   diagnostic: it pointed straight at insufficient-material handling, not
   at the search. **The bug was in the test design, not the engine** —
   exactly the diagnosis you can't make confidently if you don't trust
   your search.

## What did *not* transfer cleanly

A few rough edges where TTT didn't prepare the ground:

- **Game-over detection is genuinely more complicated.** `is_terminal` for
  TTT is a single `WIN_LINES` scan plus an "is the board full?" check.
  For chess it's checkmate + stalemate + insufficient material + 75-move
  + fivefold repetition, with `claim_draw` semantics that differ from
  forced terminations. TTT gave no preparation for this — but
  `python-chess` absorbed the complexity, which is precisely why the
  prompt said to use a library.

- **Insufficient material was a surprise.** A TTT-trained intuition says
  "if the engine wins material, the eval goes up." In chess, capturing
  the *only* opposing piece can collapse the position into KN-vs-K, which
  is a forced draw under FIDE rules — eval 0. The first hanging-queen
  test failed for exactly this reason. Lesson: chess has a richer notion
  of "draw by rule" that TTT doesn't even hint at.

- **Search depth is no longer "infinity."** TTT's default `max_depth=64`
  was effectively unlimited because the tree is tiny. Chess needs a
  finite depth budget that the caller chooses, plus iterative deepening
  in any serious version. The `max_depth` parameter and `depth_reached`
  stat were already in place from TTT, but they shifted from "set once
  and forget" to "the most important tunable in the system."

- **No quiescence search means the engine has the horizon effect.** TTT
  doesn't have this problem — every leaf is terminal. In chess, depth-N
  search will sometimes evaluate a position right after a capture but
  before the recapture, vastly mis-scoring material. This is a known
  next-step extension; it had no analog in TTT and would not have been
  designed for in advance.

- **Move ordering matters.** TTT's branching factor (~9 → 1) is small
  enough that pruning is effective without sorting moves. Chess
  branching is ~35; without MVV-LVA / killer moves, alpha-beta cutoffs
  are far below their potential. The current depth-3 numbers (54 cutoffs
  on 805 nodes) leave a lot of pruning on the table.

None of these issues are fatal — they're follow-on work. But they're
honest about the limits of small-game-first verification: it gives you
a verified core, not a finished product.

## Future work

Cleanly hooking this up to a UCI front-end is mostly plumbing — the
engine already speaks UCI move format, and `ChessGame` round-trips FEN.
After that: move ordering (cheap and high-impact), transposition table,
iterative deepening with a time budget, then quiescence. None of these
require touching the alpha-beta core inherited from TTT.
