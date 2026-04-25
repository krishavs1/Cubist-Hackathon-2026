# Cubist Systematic Hackathon: Optimizing AI-driven Strategies 

## 1. Introduction

Yesterday at 6:00 pm, we were given an open-ended prompt to build a chess engine. However, being research-oriented students, we decided to approach the challenge not as a standard software engineering sprint, but as a rigorous quantitative research project. We realized that simply asking a Large Language Model to generate code would yield average results at best. Instead, we wanted to empirically discover the optimal way for human developers to collaborate with AI.

Our plan was to formulate four entirely distinct, AI-driven development strategies and use them in parallel to generate prototype engines. To evaluate them, we built a custom tournament arena to force these prototypes to compete against each other. By treating the prompting methodologies themselves as variables in a measurable experiment, we could systematically evaluate their logic, code stability, and compute efficiency. Only after cross-validating their performance and identifying the statistically superior approach would we use those insights to optimize our final, battle-tested chess engine.

```mermaid
graph TD
    %% Define styles for a quantitative/research aesthetic
    classDef strategy fill:#f9f9f9,stroke:#333,stroke-width:1px;
    classDef arena fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef winner fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
    classDef final fill:#fff3e0,stroke:#f57c00,stroke-width:3px;

    subgraph Phase 1: Parallel AI Development
        direction TB
        S1[Strategy 1:<br>Megaprompt]:::strategy
        S2[Strategy 2:<br>Test-Driven Dev]:::strategy
        S3[Strategy 3:<br>TTT Scaler]:::strategy
        S4[Strategy 4:<br>Simple One-Shot]:::strategy
    end

    AM[Arena Maker:<br>Tournament Infrastructure]:::arena

    subgraph Phase 2: Empirical Evaluation
        Arena{Custom Python<br>Tournament Arena}:::arena
    end

    subgraph Phase 3: Selection & Execution
        Win[Winning Methodology:<br>Megaprompt]:::winner
        Opt[Team Parallel Optimization]:::strategy
        Final((Final Battle-Tested<br>Chess Engine)):::final
    end

    %% Connections
    AM -->|Builds| Arena

    S1 -->|Prototype 1| Arena
    S2 -->|Prototype 2| Arena
    S3 -->|Prototype 3| Arena
    S4 -->|Prototype 4| Arena

    Arena -->|Statistical Cross-Validation| Win
    Win -->|Logic Translation| Opt
    Opt --> Final

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
