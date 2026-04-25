# Checkers

Third iteration of the game-agnostic-search experiment that started in
`ttt-iteration_bot/tic-tac-toe/` and continued in `ttt-iteration_bot/chess-ttt/`. The idea of this
branch is: write the search core **once**, against a small interface, and
then scale it to progressively more complex games by swapping out `game.py`
and `evaluate.py` without touching the search.

## The "same engine" claim, verified

```
$ md5 ttt-iteration_bot/tic-tac-toe/src/search.py \
      ttt-iteration_bot/chess-ttt/src/search.py \
      ttt-iteration_bot/checkers/src/search.py
MD5 (ttt-iteration_bot/tic-tac-toe/src/search.py) = 0abb839293a3f53c71be713a59e9cacb
MD5 (ttt-iteration_bot/chess-ttt/src/search.py)   = 0abb839293a3f53c71be713a59e9cacb
MD5 (ttt-iteration_bot/checkers/src/search.py)    = 0abb839293a3f53c71be713a59e9cacb
```

The alpha-beta core is byte-identical across all three projects. The
complexity added here lives above and below it:

| Layer              | Tic-Tac-Toe               | Checkers                                       |
|--------------------|---------------------------|------------------------------------------------|
| `search.py`        | alpha-beta                | **same file, byte-identical**                  |
| `game.py`          | 9-cell board, 0..8 moves  | 8×8 board, forced captures, multi-jumps, promotion, 40-move draw |
| `evaluate.py`      | terminal-only             | material + advancement + king centralization + mobility |
| `deepening.py`     | (not needed)              | iterative deepening wrapper around depth-bounded search |
| `cli.py` / `main.py` | play by typing 0..8     | standard checkers notation (`11-15`, `22x18`, `22x15x6`) |

## Rules (American / English draughts)

- 8×8 board, pieces on the dark squares.
- Red is the maximizer, starts at the bottom, moves first.
- Men move diagonally forward one square; kings move in all four
  diagonal directions.
- **Captures are mandatory.** If you can jump, you must.
- **Multi-jumps are mandatory.** After a jump, if the same piece can jump
  again, it must keep going.
- Reaching the opponent's back rank promotes a man to a king.
  Under ACF rules, promotion in the middle of a multi-jump **ends the
  move** (`test_promotion_ends_multi_jump` verifies this).
- A side with no legal moves loses.
- A 40-move (80-ply) no-capture / no-man-move counter yields a draw, so
  the search has a stable terminal condition in king-and-king endgames.

## Search stack

`search.py` is depth-bounded negamax-in-minmax form with alpha-beta pruning,
inherited unchanged from the Tic-Tac-Toe MVP.

`deepening.py` wraps it with iterative deepening and a wall-clock budget:

```
iterative_deepening(game, max_depth=10, time_limit=3.0)
  -> DeepeningResult(best_move, score, depth_reached,
                     total_nodes, total_cutoffs, per_depth=[...])
```

It runs depth 1, 2, 3, … and returns the last **completed** iteration's
best move. A crude branching-factor predictor skips a depth if it clearly
won't fit in the remaining budget.

## Evaluator (from Red's perspective)

- Man value: 100; king value: 160.
- Row-indexed advancement bonus for men
  (`0, 40, 28, 20, 14, 8, 4, 6` for Red from row 0 to row 7; Black is the
  vertical mirror). Using a 1-D advancement table rather than an 8×8 PST
  makes the evaluator intrinsically color-symmetric — an earlier 2-D
  version placed its bonuses on the wrong parity of column on every other
  row and produced a phantom 65-point asymmetry at the start of the game.
- 8×8 king PST that prefers the center and punishes the corners.
- Small mobility tie-breaker (signed by side-to-move).
- Depth-adjusted mate scoring: `+WIN_SCORE - ply` on a Red win and
  `-WIN_SCORE + ply` on a Black win, so the engine prefers faster wins
  and slower losses — same trick the TTT evaluator uses.

## Running

Tests:

```
cd ttt-iteration_bot/checkers
python3 -m pytest tests/ -v
```

Play against the engine (human moves first as Red by default):

```
cd ttt-iteration_bot/checkers
python3 -m src.main                       # play as Red, 3s/move, depth 8
python3 -m src.main --play-as black       # play as Black
python3 -m src.main --depth 10 --time 5   # deeper & longer
```

At any prompt:

- `11-15`, `22x18`, `22x15x6` — play a move in standard notation.
- `moves` — list the currently legal moves.
- `help` — notation legend.
- `quit` — exit.

## What was reused vs. replaced

**Reused verbatim from Tic-Tac-Toe:**

- `search.py` — depth-bounded alpha-beta (md5 match above).
- The shape of the game interface: `get_legal_moves / make_move / undo_move
  / is_terminal / current_player / is_maximizing_player / winner`.
- The mate-score trick in `evaluate.py` (`±WIN_SCORE ∓ ply`).

**New for checkers:**

- `game.py` — real game state with a full make/undo stack, including
  captured-piece restoration, promotion reversal, and halfmove-clock
  restoration. Multi-jump generation mutates the board temporarily and
  restores it before returning (exercised by
  `test_capture_sequence_restores_board_on_generation`).
- A proper `Move` dataclass, because an integer is no longer enough:
  moves carry `(from_sq, path, captures)`. `parse_move` turns
  human-entered `11x18x25` strings into the matching `Move`.
- `evaluate.py` — material + row-indexed advancement + king PST + mobility.
- `deepening.py` — iterative deepening with a wall-clock budget.
- `cli.py` / `main.py` — interactive play with standard notation,
  a legible ASCII board that shows empty-square numbers for
  ease of input, and per-move engine telemetry.

## Limitations (honest notes)

- `is_terminal()` calls `get_legal_moves()` internally, and so does
  `evaluate()`, so at search leaves legal moves are generated twice.
  Noticeable but tolerable; caching on the game object would require
  invalidation logic on make/undo.
- No transposition table, no move ordering, no quiescence extension.
  In American checkers, mandatory captures already push the capture-heavy
  horizon outward for free, so quiescence is less critical than in chess.
- The 40-move draw rule is a simple ply counter, not the ACF "after the
  first piece is reached" variant used in some competitive rulesets.
- Move ordering is whatever order `get_legal_moves()` happens to produce.
  Alpha-beta still cuts well because captures are returned first
  (and are forced anyway when available).

## Tests

33 tests, run in <1s:

- Rule correctness: initial setup, turn rotation, forced captures,
  double-jumps, promotion, promotion-ends-multi-jump, king backwards
  captures, make/undo round-trips for every move kind, terminal detection
  for no-pieces and blocked-side cases, halfmove clock behavior,
  notation parsing.
- Search behavior: returns legal moves, deeper searches visit more
  nodes, evaluator symmetry at start, material-advantage detection,
  terminal scoring with ply adjustment, finds free captures, finds
  double-jump tactics, prefers faster wins, iterative deepening reports
  and respects time budget, beats uniform-random play as both Red and
  Black (3/3 seeds each side at depth 3).
