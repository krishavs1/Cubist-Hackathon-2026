# Chess Engine Elo Benchmark (Pro-Level Rigor)

This repository is a professional-grade framework for measuring the absolute Elo of chess engines using **Balanced Multi-Anchor Calibration**.

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

### 3. Pro-Level Grading
We measure "True Elo" using a **Calibration Curve** against multiple Stockfish skill levels.

```bash
# Run 60 games (20 games per anchor x 3 anchors)
python3 elo-test/grade.py --games 60 --movetime 100
```

### 4. Cross-Validation (Optional)
To validate the estimated Elos, you can run engines in `src/` against each other.

```bash
# Run 60 games between all methodology engines
python3 elo-test/grade.py --cross-validate --games 60
```

### 5. Rigorous Mechanisms
1.  **Balanced Opening Pairs**: Every game is played as a pair from a standard opening (Sicilian, French, etc.). Colors are swapped for the second game. This eliminates "White advantage" and "Opening bias."
2.  **Multi-Anchor Calibration**: Your engine is tested against Stockfish Skill 1 (1000 Elo), Skill 3 (1200 Elo), and Skill 5 (1500 Elo). This eliminates "Style bias."
3.  **Maximum Likelihood Estimation (MLE)**: Instead of a simple average, we use **Inverse-Variance Weighting** to aggregate the results into a single absolute Elo with a unified 95% Confidence Interval.

### 5. Results
Detailed game statistics and the rigorous Elo range are stored in `src/<your-name>/results.json`.
