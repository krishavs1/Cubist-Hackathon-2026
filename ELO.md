# Chess Engine Elo Benchmark

This repository is a lean framework for measuring the absolute Elo of chess engines using **Stockfish Calibration**.

### 1. The UCI Contract
Your engine must be a standalone executable that speaks the UCI protocol.
- **Entry Point**: `src/<your-name>/engine/run.sh`
- **Handshake**: Must respond to `uci` with `uciok` and `isready` with `readyok`.
- **Search**: Must respond to `go movetime <ms>` with `bestmove <move>`.

### 2. Validation
Before grading, ensure your engine is UCI-compliant and produces legal moves:
```bash
python3 elo-test/test_engine.py --engine src/<your-name>/engine/run.sh
```

### 3. Grading (Elo Calibration)
We measure "True Elo" by playing matches against **Stockfish Skill Level 1** (Fixed Anchor: 1000 Elo).

```bash
# Run 100 games to get a tight 95% Confidence Interval
python3 elo-test/grade.py --games 100 --movetime 100
```

### 4. Mathematical Rigor
The grading tool uses the **Fishtest Trinomial Model** (the same math used by the official Stockfish project):
1. **Absolute Scale**: Reported as `1000 + EloDelta`.
2. **95% Confidence Interval**: Exact error bars are calculated based on the Win/Loss/Draw distribution.
3. **Statistical Significance**: A result is considered a "True" rating increase if the 95% CI does not overlap with the previous version.

### 5. Results
Detailed game statistics (W/L/D) and the calculated Elo range are stored in `src/<your-name>/results.json`.
