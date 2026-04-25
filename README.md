# Cubist Systematic Hackathon: AI Methodology Research Lab

This repository is a quantitative research environment designed to evaluate AI-assisted software engineering methodologies through the lens of chess engine development.

## 1. THE EVALUATION SUITE (`elo-test/`)

We use a three-stage evaluation pipeline to determine the winning methodology.

### Stage 1: Absolute Elo Calibration
Every engine is tested against a **Stockfish Calibration Curve** (Skill Levels 1, 3, and 5). 
- **Rigor**: Balanced Opening Pairs (colors swapped for the same position).
- **Math**: Fishtest Trinomial Model (Standard Error calculation).
- **Run**: `python3 elo-test/grade.py --games 60 --movetime 100`

### Stage 2: Cross-Validation (Battle Royale)
Engines in `src/` play directly against each other to verify that absolute Elo gaps translate to real-world performance.
- **Run**: `python3 elo-test/grade.py --games 60 --cross-validate --movetime 100`

### Stage 3: AMES Efficacy Analysis
The **Alpha Methodology Efficiency Score (AMES)** is calculated based on:
1.  **SF Alpha (40%)**: Absolute performance vs. Stockfish.
2.  **Beta Alpha (30%)**: Relative performance in direct combat.
3.  **Token Efficiency (30%)**: Elo gained per 1,000 tokens used.
- **Run**: `python3 elo-test/mes_calculator.py`

---

## 2. THE WORKSTREAMS (`src/`)

- **`zero-shot/`**: Control group (single-pass implementation).
- **`tdd/`**: Engineering rigor (test-first implementation).
- **`toy-to-scale/`**: Evolutionary complexity (staged scaling).
- **`megaprompt/`**: Knowledge injection (high-heuristic injection).

---

## 3. HOW TO RUN THE FULL EVALUATION

To generate the final leaderboard for the judges, execute this sequence:

```bash
# 1. Calibrate Absolute Elos
python3 elo-test/grade.py --games 30

# 2. Run Engine vs Engine Battle Royale
python3 elo-test/grade.py --games 30 --cross-validate

# 3. Calculate Final Methodology Efficacy
python3 elo-test/mes_calculator.py
```

Results are stored in `src/<methodology>/results.json` and `src/<methodology>/DISCOVERY.md`.
