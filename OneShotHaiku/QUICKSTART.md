# OneShot Chess Engine - Quick Start Guide

## Installation

```bash
cd OneShot2
pip install -r requirements.txt
```

## Quick Testing

### 1. Run Basic Tests (Verify Engine Works)
```bash
python3 << 'EOF'
import chess
from evaluation import evaluate
from search import find_best_move, clear_transposition_table

board = chess.Board()
clear_transposition_table()
move = find_best_move(board, 3)
print(f"Best opening move: {move}")
EOF
```

### 2. UCI Protocol Test
```bash
echo -e "uci\nposition startpos\ngo depth 4\nquit" | python3 chess_engine.py
```

Expected output:
```
id name OneShot 1.0
id author Chess Engine
option name Depth type spin default 4 min 1 max 20
uciok
bestmove e2e4
```

### 3. Interactive Play
```bash
python3 interactive.py
```

Then select "Play against the engine" and make moves in algebraic notation.

## Files Overview

| File | Purpose |
|------|---------|
| `chess_engine.py` | UCI protocol handler & main engine |
| `evaluation.py` | Position evaluation (material + piece-square tables) |
| `search.py` | Minimax with alpha-beta pruning |
| `interactive.py` | Play and analyze positions interactively |
| `test_engine.py` | Full test suite |

## Using with Chess GUIs

The engine is compatible with any UCI-supporting chess application:

1. **Arena Chess GUI**: Engine → Manage Engines → Add → Point to `chess_engine.py`
2. **Chess.com**: Import as UCI engine
3. **Lichess**: Upload to bot account
4. **Command line**: `echo "position startpos\ngo depth 6" | python3 chess_engine.py`

## UCI Commands Quick Reference

```
uci                          - Initialize engine
isready                      - Check engine ready
setoption name Depth value 5 - Set search depth
position startpos            - Set starting position
position fen <fen>           - Set custom position
go depth 6                   - Search 6 plies deep
go wtime 300000 btime 300000 - Search with time (5min each)
quit                         - Exit
```

## Performance Tuning

### Adjust Depth
- Depth 3: ~1400 Elo (fast, ~1-2s per move)
- Depth 4: ~1600 Elo (standard, ~5-10s per move)
- Depth 5: ~1800 Elo (strong, ~30s+ per move)
- Depth 6+: ~2000+ Elo (very strong, 2+ minutes per move)

### Adjust Time Management
```
setoption name Depth value 3  # Faster
go wtime 60000 btime 60000     # 1 minute per side
```

## Example Game Session

```bash
$ python3 chess_engine.py
uci
position startpos
go depth 4
bestmove e2e4
position startpos moves e2e4 c7c5
go depth 4
bestmove g1f3
quit
```

## Analysis Mode

Analyze a specific position:

```python
from chess import Board
from evaluation import evaluate
from search import find_best_move

board = Board("r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4")

for depth in range(3, 6):
    move = find_best_move(board, depth)
    print(f"Depth {depth}: {move}")
```

## Troubleshooting

**Engine too slow?**
- Reduce depth: `setoption name Depth value 3`
- Use time limits: `go wtime 5000 btime 5000` (5 seconds each)

**Invalid moves?**
- Use UCI format: `e2e4` (not `e4`)
- Or algebraic: `e4` (when unambiguous)

**Engine crashes?**
- Check python-chess is installed: `pip install python-chess==1.10.0`
- Check UCI format of commands

## Next Steps

1. **Play a game**: Use `interactive.py`
2. **Integrate with GUI**: Point Arena/Chess.com to `chess_engine.py`
3. **Analyze games**: Use custom FEN positions
4. **Improve engine**: See README.md for enhancement ideas
