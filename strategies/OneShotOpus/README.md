# OneShotOpus

A UCI-compatible chess engine built in one shot using `python-chess`. Targets the
Cubist Hackathon `elo-test/` evaluation harness (cutechess-style match runner).

## Features

**Search** — negamax + alpha-beta with:
- Iterative deepening (depths 1..N) with soft time control
- Quiescence search (stand-pat + delta pruning) over captures and queen promotions
- Transposition table keyed on Zobrist hash, with EXACT/LOWER/UPPER bound flags
- Null-move pruning (R = 2..3, disabled in check / pawn-only endings)
- Late move reductions on quiet moves after the first few tries
- Check extensions
- Move ordering: TT move > MVV-LVA captures > queen promotions > killers > history

**Evaluation** — tapered eval blending middlegame and endgame:
- PeSTO-style material values and 12 piece-square tables (mg + eg per piece)
- Phase counter weighted by remaining minor/major pieces
- Bishop pair bonus
- Tempo bonus

**UCI** — standard subset:
- `uci`, `isready`, `ucinewgame`, `position [startpos|fen ...] [moves ...]`,
  `go [depth|movetime|wtime/btime/winc/binc/movestogo|infinite]`, `stop`, `quit`
- Streams `info depth ... score cp ... nodes ... nps ... pv ...` per ID iteration
- Debug helpers: `d` (display board + FEN) and `eval` (static evaluation)

## Run

```bash
pip install -r requirements.txt
./run.sh                   # interactive UCI
echo -e "position startpos\ngo movetime 1000\nquit" | ./run.sh
```

Plug into cutechess-cli:

```bash
cutechess-cli \
  -engine cmd=./OneShotOpus/run.sh name=OneShotOpus \
  -engine cmd=./OneShotHaiku/run.sh name=OneShotHaiku \
  -each proto=uci tc=10+0.1 \
  -rounds 20 -repeat -concurrency 2
```

## Files

- `engine.py` — UCI driver / stdin loop
- `search.py` — negamax, quiescence, TT, move ordering
- `evaluation.py` — tapered material + PSTs
- `run.sh` — launcher
