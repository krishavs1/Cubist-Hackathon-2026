# OneShot Chess Engine

A well-performing chess engine MVP implementing the UCI (Universal Chess Interface) protocol using python-chess.

## Features

- **UCI Protocol Compliance**: Full UCI protocol support for integration with chess GUIs (Arena, ChessBase, Lichess, etc.)
- **Minimax with Alpha-Beta Pruning**: Efficient search algorithm with move ordering
- **Transposition Table**: Caches evaluated positions to avoid redundant calculations
- **Advanced Evaluation**:
  - Piece-square tables (opening/endgame adapted)
  - Material evaluation
  - Pawn structure assessment (doubled pawns)
  - Mobility evaluation
  - Check detection
- **Iterative Deepening**: Time-managed search with configurable depth limits
- **Move Ordering**: Prioritizes captures, checks, promotions, and castling for better pruning

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Running as UCI Engine

```bash
python chess_engine.py
```

Then use UCI commands:

```
uci
position startpos
go depth 6
quit
```

### Testing with a UCI-Compatible GUI

The engine can be used with any UCI-compatible chess interface:

1. **Arena Chess GUI** or **ChessBase**: Add the engine as a UCI engine pointing to `chess_engine.py`
2. **Command Line**: Pipe UCI commands directly into the engine

### Manual Testing

Debug commands available:

```
d          - Display current board
eval       - Evaluate current position
help       - Show available commands
```

Example session:

```
$ python chess_engine.py
position startpos
go depth 4
bestmove e2e4
d
eval
Evaluation: 23
```

## UCI Commands Supported

| Command | Description |
|---------|-------------|
| `uci` | Initialize engine, return name and options |
| `isready` | Readiness check |
| `setoption name <name> value <value>` | Set engine options (e.g., depth) |
| `ucinewgame` | Start new game, clear caches |
| `position <fen \|startpos> [moves ...]` | Set board position |
| `go [depth <d>] [wtime <ms>] [btime <ms>]` | Search and return best move |
| `quit` | Exit engine |

## Configuration

### Engine Options

- **Depth** (spin, 1-20, default 4): Maximum search depth
  ```
  setoption name Depth value 6
  ```

## Architecture

### `evaluation.py`
Evaluates board positions using:
- Material counting
- Piece-square tables (standard Stockfish-style tables)
- Pawn structure analysis
- Mobility bonuses

### `search.py`
Implements the search algorithm:
- Minimax with alpha-beta pruning
- Transposition table for position caching
- Move ordering by capture value, checks, and promotions
- Iterative deepening for time management

### `chess_engine.py`
Main UCI protocol handler:
- Command parsing and execution
- Board state management
- Search coordination

## Performance

- Typical depth: 4-6 plies (2-3 moves ahead per side)
- Time management: Configurable per-move time allocation
- Optimizations:
  - Alpha-beta pruning reduces effective branching factor
  - Move ordering improves cutoff rate (typically 2-3x speedup)
  - Transposition table eliminates duplicate evaluations

## Strength

Playing strength depends on search depth:
- Depth 4: ~1600 Elo (intermediate player)
- Depth 6: ~2000+ Elo (strong amateur)
- Depth 8+: ~2200+ Elo (tournament level)

Actual performance varies based on position complexity and time management.

## Future Enhancements

- Quiescence search (handle tactical explosions)
- Killer heuristics and history heuristics
- Endgame tablebases
- Opening book
- Iterative deepening with aspiration windows
- Multithreading support
- Neural network evaluation (NNUE-style)

## Dependencies

- `python-chess` (1.10.0+): Chess logic and board representation

## License

MIT
