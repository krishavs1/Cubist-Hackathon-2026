# Tic-Tac-Toe Engine (MVP for a Chess Engine)

A clean, fully-tested Tic-Tac-Toe engine using minimax with alpha-beta
pruning. The architecture is intentionally written as a miniature chess
engine: the search code is game-agnostic and only talks to the game through
a small generic interface (`get_legal_moves`, `make_move`, `undo_move`,
`is_terminal`, `current_player`). When we scale to chess, the search and
evaluation skeletons stay; only the game representation, move generator,
and evaluation function change.

## Layout

```
src/
  game.py       # board, legal moves, make/undo, terminal detection
  search.py     # generic minimax + alpha-beta + instrumentation
  evaluate.py   # depth-adjusted terminal scoring
  cli.py        # human-vs-engine CLI
  main.py       # entry point
tests/
  test_game.py
  test_search.py
README.md
TOKEN_USAGE.md
```

## Running

From `src/tic-tac-toe/`:

```bash
# Play as X (human moves first)
python3 -m src.main

# Play as O (engine moves first)
python3 -m src.main --play-as O
```

Squares are entered by index `0..8`:

```
 0 | 1 | 2
---+---+---
 3 | 4 | 5
---+---+---
 6 | 7 | 8
```

## Tests

```bash
python3 -m pytest tests/ -v
```

The suite (69 tests) covers:
- legal-move generation, occupancy, and turn alternation
- win detection across rows, columns, both diagonals, for both X and O
- draw detection, non-terminal detection
- `make_move` / `undo_move` round-trip correctness
- alpha-beta plays a winning move when one is available (X and O)
- alpha-beta blocks an opponent's immediate win (X and O)
- alpha-beta prefers faster wins (depth adjustment works)
- engine never returns an illegal move from random reachable positions
- engine vs. engine always draws (perfect play)
- engine never loses to a random opponent (20 seeded games on each side)
- alpha-beta actually produces cutoffs

## Instrumentation

`search.search(game)` returns a `SearchResult` with a `stats` field:

- `nodes_searched` — total nodes visited
- `cutoffs` — alpha-beta cutoffs taken
- `best_move` — selected move
- `score` — final score from X's perspective

From the empty board the engine searches ~20.9k nodes with ~7.7k cutoffs
and scores 0 (drawn with perfect play).

## Architecture: How This Bridges to Chess

### Mapping

| Tic-Tac-Toe component        | Chess equivalent                                        |
|------------------------------|---------------------------------------------------------|
| `Game` (9-cell list)         | `Board` (bitboards or 8x8 mailbox + side-to-move + castling rights + en-passant + halfmove clock) |
| `get_legal_moves()`          | Pseudo-legal generation + king-safety filter            |
| `make_move(int)` / `undo_move()` | `make_move(Move)` / `undo_move()` with full state stack (captured piece, castling, ep, halfmove) |
| `is_terminal()`              | Checkmate / stalemate / 50-move / threefold / insufficient material |
| `winner()` returning X/O/None | Result enum: white-wins / black-wins / draw           |
| `evaluate()` (terminal-only)  | Material + piece-square tables + king safety + mobility, plus mate scoring |
| `search()` (alpha-beta)       | The same alpha-beta — extended with iterative deepening, transposition table, quiescence, move ordering |
| Move = `int 0..8`             | `Move` with from/to/promotion/flags (or 16-bit packed) |

### What's reused directly

- **`search.py` is essentially complete.** The alpha-beta loop, alpha/beta
  bookkeeping, depth/ply tracking, maximize/minimize structure, and stats
  collection all carry over unchanged.
- **The `SearchStats` / `SearchResult` interface.**
- **The `evaluate(game, depth)` signature.** The depth-adjusted "prefer
  faster wins" trick is the same one chess engines use for mate scoring.
- **The make/undo discipline** (rather than copying the position each ply).

### What must be replaced

- **`game.py`.** Chess needs a real board representation (bitboards are
  ideal for performance), full move encoding, and the long list of state
  that has to be preserved on the undo stack: captured piece, castling
  rights, en-passant target, halfmove clock, Zobrist hash.
- **Move generation.** Sliding-piece attacks, pinned-piece handling,
  castling legality, en-passant edge cases. This is the hardest part.
- **`evaluate.py`.** Replace terminal-only scoring with material +
  piece-square tables + (later) mobility / king safety / pawn structure.
  Mate scores still get the depth adjustment.
- **`is_terminal()`.** Add stalemate, 50-move rule, threefold repetition,
  insufficient material.
- **Search extensions.** Tic-Tac-Toe is small enough to brute-force; chess
  needs iterative deepening, a transposition table, move ordering (MVV-LVA,
  killer moves, history heuristic), null-move pruning, and quiescence
  search to handle the horizon effect.

### Why Tic-Tac-Toe is a useful MVP before chess

1. **Decoupling is testable.** If `search.py` accidentally hard-codes
   anything Tic-Tac-Toe-specific, you'll feel it the moment you try to swap
   in a chess `Game`. Keeping the interface clean is much easier to enforce
   on a 9-square game.
2. **Search correctness is verifiable.** Tic-Tac-Toe is small enough to
   solve exactly. "Engine vs. engine always draws" and "engine never loses
   to random" are end-to-end correctness tests for alpha-beta. If those
   pass, the search logic itself is sound — when chess plays badly later,
   you know the bug is in eval / move-gen / extensions, not in the core
   minimax.
3. **The depth-adjusted scoring lesson is identical.** "Prefer mate-in-1
   over mate-in-3, and prefer mate-in-7 over mate-in-1 when losing" is the
   same arithmetic you'll write into the chess evaluator.
4. **The instrumentation generalizes.** `nodes_searched` and `cutoffs` are
   exactly the metrics you'll watch in chess to validate that move ordering
   and pruning are working.
5. **Cheap iteration.** A Tic-Tac-Toe search runs in ~1 second; a buggy
   chess search can take minutes per move. You catch architectural mistakes
   in the cheap iteration loop, not the expensive one.

### Suggested next prompt (scaling to chess)

> Extend the engine in this repo to play standard 8x8 chess, keeping the
> `search.py` interface unchanged. Replace `game.py` with a chess board
> representation that exposes the same generic interface
> (`get_legal_moves`, `make_move`, `undo_move`, `is_terminal`,
> `current_player`). Use either a mailbox or bitboard representation —
> recommend bitboards for performance. Move encoding must include
> from-square, to-square, promotion piece, and flags for castling /
> en-passant / capture. The undo stack must restore captured piece,
> castling rights, en-passant target, halfmove clock, and Zobrist hash.
> Replace `evaluate.py` with material + piece-square tables; keep mate
> scoring depth-adjusted. Extend `search.py` only by adding iterative
> deepening, a transposition table, MVV-LVA move ordering, and a
> quiescence search; do **not** modify the alpha-beta core. Add tests
> mirroring the Tic-Tac-Toe suite: legality (perft to depth 4 against
> known node counts), known mate-in-N puzzles for "engine finds the win",
> and "engine doesn't blunder mate-in-1 defenses". Update TOKEN_USAGE.md
> with each run.
