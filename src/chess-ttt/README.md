# Chess (iterated from the checkers engine)

Third step in the game-agnostic-search progression:

    src/tic-tac-toe/  →  src/checkers/  →  src/chess-ttt/

Each step **reuses more of the engine** than the last, by design. The
previous README for this folder talked about bridging from Tic-Tac-Toe
directly; this version bridges from **checkers**, which means the
reusable primitives now include iterative deepening (not just the bare
depth-bounded search), the evaluator's *structure* (not just its shape),
and the `game.py` interface contract.

## The "same engine" claim, broadened

Two files are now **byte-identical** across projects, up from one:

```
$ md5 src/tic-tac-toe/src/search.py \
      src/checkers/src/search.py \
      src/chess-ttt/src/search.py
MD5 (src/tic-tac-toe/src/search.py) = 0abb839293a3f53c71be713a59e9cacb
MD5 (src/checkers/src/search.py)    = 0abb839293a3f53c71be713a59e9cacb
MD5 (src/chess-ttt/src/search.py)   = 0abb839293a3f53c71be713a59e9cacb

$ md5 src/checkers/src/deepening.py \
      src/chess-ttt/src/deepening.py
MD5 (src/checkers/src/deepening.py) = ec7dfeb23be4185d82d0ed0c4183f2ab
MD5 (src/chess-ttt/src/deepening.py) = ec7dfeb23be4185d82d0ed0c4183f2ab
```

`search.py` is the alpha-beta core (inherited from Tic-Tac-Toe).
`deepening.py` is the iterative-deepening wrapper with a wall-clock
budget (inherited from checkers, generalized on its way over). Chess
differs from checkers only in `game.py`, `evaluate.py`, and a UCI front
end.

## Architecture

```
chess-ttt/
├── engine/
│   └── run.sh        # elo-test entry point: `python3 -m src.uci`
├── src/
│   ├── search.py     # BYTE-IDENTICAL copy of TTT / checkers search
│   ├── deepening.py  # BYTE-IDENTICAL copy of the checkers deepening wrapper
│   ├── game.py       # ChessGame: thin python-chess wrapper, same generic
│   │                   interface as Tic-Tac-Toe's Game and checkers'
│   │                   CheckersGame (get_legal_moves / make_move /
│   │                   undo_move / is_terminal / current_player /
│   │                   is_maximizing_player)
│   ├── evaluate.py   # material + PSTs + *tapered king* + bishop pair +
│   │                   doubled pawns + mobility; same ± WIN_SCORE ∓ ply
│   │                   mate trick as in both earlier evaluators
│   ├── uci.py        # UCI protocol bridge that calls deepening.iterative_deepening
│   ├── cli.py        # human-vs-engine CLI (UCI and SAN move input)
│   └── main.py       # argparse entry
└── tests/
    ├── test_game.py      # interface contract + rule smoke
    ├── test_search.py    # tactics, iterative deepening, engine-vs-random
    ├── test_evaluate.py  # bishop pair, doubled pawns, tapered king, mate
    └── test_perft.py     # perft against known counts (move-gen + undo)
```

## What iterated vs. what was replaced

Compared to the **checkers** engine one folder over:

| Layer               | Checkers                           | Chess (this folder)                                        |
|---------------------|------------------------------------|------------------------------------------------------------|
| `search.py`         | from TTT, byte-identical           | **same file, byte-identical**                              |
| `deepening.py`      | iterative deepening wrapper        | **same file, byte-identical** (made generic when refactored) |
| `game.py`           | hand-written 8×8 with forced captures, multi-jumps, promotion, halfmove clock | thin wrapper over `python-chess` exposing the same interface |
| `evaluate.py` — material | man=100, king=160             | 6 piece types (100/320/330/500/900/0)                      |
| `evaluate.py` — positional | row-indexed man advancement + king PST | per-piece PSTs + **tapered king PST** (midgame back-rank → endgame center) |
| `evaluate.py` — structure | —                              | **bishop pair bonus** + **doubled pawn penalty**           |
| `evaluate.py` — mobility | side-to-move mobility           | same                                                        |
| `evaluate.py` — mate | ± WIN_SCORE ∓ ply                  | same (uses python-chess's checkmate / stalemate / draw detection) |
| Front end           | interactive CLI with checkers notation | UCI (for the elo-test arena) + a CLI with UCI / SAN input |

The "headline complexity" added on top of the checkers evaluator is the
**tapered king PST**. In checkers, the king's best square doesn't really
change with game phase; in chess it does, dramatically. The evaluator
computes a phase score (0..24 based on non-pawn, non-king material) and
blends the midgame and endgame king tables proportionally. Tests assert
that the phase computation is full-midgame at the start and full-endgame
with bare kings, and that the king prefers the back rank in a full-
material position and the center in an endgame position.

## Running

From `src/chess-ttt/`:

```bash
# Tests (fast — skips the depth-4 and depth-3 perft cases)
python3 -m pytest tests/ -v

# Tests including the slow perfts (depth 4 startpos, depth 3 Kiwipete)
CHESS_SLOW_TESTS=1 python3 -m pytest tests/ -v

# Play against the engine (White by default, 3s/move, depth 6)
python3 -m src.main
python3 -m src.main --play-as black --depth 7 --time 5

# UCI (what the elo-test arena uses)
python3 -m src.uci             # listens on stdin
python3 -m src.uci --debug     # also logs every command to stderr
```

Input in the CLI is UCI (`e2e4`, `g1f3`, `e7e8q`) or SAN (`e4`, `Nf3`,
`O-O`). The CLI prints depth, score, nodes, and cutoffs after each
engine move. The UCI backend emits `info depth N score cp S nodes N
time T` lines before each `bestmove`.

## Tests (52 active + 2 slow)

- **`test_game.py`** — Interface contract: 20 legal moves at start,
  turn rotation, illegal-move rejection, undo roundtrip, terminal
  detection for mate and stalemate, FEN and move-parser helpers.
- **`test_search.py`** — Tactical puzzles (Scholar's mate, back-rank mate,
  Black mate-in-1, captures hanging queens, avoids leaving pieces en
  prise), faster-mate preference (uses the ply-adjusted score),
  iterative deepening stats and zero-budget fallback, short-circuit on
  forced mate, engine beats random in 3/3 seeds as each color.
- **`test_evaluate.py`** — Starting-position |score| < 25 (symmetric),
  material-advantage detection for both sides, mate scoring with ply
  adjustment, stalemate → 0, bishop pair bonus for both colors, doubled
  pawn penalty for both colors, phase=24 at start and phase=0 for bare
  kings, tapered king prefers back rank in midgame and center in endgame.
- **`test_perft.py`** — Canonical move-gen correctness. Startpos
  perft(1..3) = 20 / 400 / 8902, Kiwipete perft(1..2) = 48 / 2039.
  The depth-3 Kiwipete (97862) and depth-4 startpos (197281) runs are
  gated behind `CHESS_SLOW_TESTS=1` because pure-Python `make_move` /
  `undo_move` over 100k+ nodes takes a few seconds. Also checks that
  the FEN is byte-identical before and after a perft(3) walk — proves
  the wrapper's undo fully restores castling rights, en passant file,
  halfmove clock, and full-move number.

## Limitations (honest notes)

- No transposition table, no move ordering heuristics, no quiescence,
  no null-move pruning. The search core is the same bare alpha-beta we
  verified on Tic-Tac-Toe; all strength comes from depth + evaluation.
  On a 3-second budget the engine typically reaches depth 3–4.
- The UCI time manager budgets ½ of the remaining clock for the current
  move and assumes 30 moves to go when given only `wtime`/`btime` —
  adequate for 5+0 or 10+0 matches, crude for blitz.
- `game.py` delegates legality / terminals / castling bookkeeping to
  `python-chess`. The perft tests are the check that we're using that
  machinery correctly.
- Mate scores don't currently round-trip through UCI's `mate N` info
  field; we report everything as `score cp`. Arenas accept this but a
  stronger engine would distinguish.
