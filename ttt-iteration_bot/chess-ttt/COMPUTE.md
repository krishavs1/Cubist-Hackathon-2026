# Compute Analysis — Chess-TTT Engine (`chess-ttt`)

This document mirrors the three-factor layout used for the [test-driven-development engine compute note](https://github.com/krishavs1/Cubist-Hackathon-2026/blob/main/src/test-driven-development/COMPUTE.md), but scoped to **`ttt-iteration_bot/chess-ttt/`** — the chess step of the Tic-Tac-Toe → Checkers → Chess scaling line.

**Ground truth in this repo:**

- Token estimates: `ttt-iteration_bot/chess-ttt/TOKEN_USAGE.md` (author-measured prompt/output sizes).
- Arena strength: `ttt-iteration_bot/chess-ttt/results.json` (`elo-test/`, 80 ms/move, Stockfish skill anchors).
- Search/eval gaps: `README.md` (“Limitations”) and `src/search.py` (game-agnostic alpha-beta, no TT / quiescence / null-move / LMR).

**Related:** End-to-end lineage cost (all three games) is summarized in `ttt-iteration_bot/SCALING_ANALYSIS.md`.

---

## 1. Compute Cost to Create the Initial MVP

The chess engine MVP was delivered in **one main scaling run** from checkers/TTT primitives: same `search.py` MD5 as TTT/checkers, shared `deepening.py`, new `game.py` / `evaluate.py` / UCI / tests / README.

| Resource | Amount |
| --- | --- |
| AI tokens (input) | ~1,600 |
| AI tokens (output) | ~12,000 |
| **Total tokens** | **~13,600** |
| Estimated API cost (Claude-class pricing, order-of-magnitude) | ~$0.05–0.08 |
| Local CPU — code generation / iteration | < 1 minute |
| Local CPU — test suite (~26 pytest tests) | ~0.4 seconds |
| Local CPU — UCI conformance (`elo-test/test_engine.py`, 6 checks) | ~15 seconds |
| Local CPU — Elo grading (example: 50 games vs Stockfish skill 1 only) | ~3–5 minutes |

**Baseline Elo (current arena calibration, `results.json`):** **779 Elo**, 95% CI **[615, 943]** (36 games across three anchors at 80 ms/move; not the same sample size as a 50-game skill-1-only run).

*If you count the **full lineage** (TTT + checkers + chess) as the “MVP of the scaling strategy,” use the stage table in `SCALING_ANALYSIS.md` (~33–42k output tokens total across stages).*

---

## 2. Expected Compute Cost to Optimize

Optimizing **chess-ttt** is harder than a free-standing TDD engine because **`search.py` is byte-identical across tic-tac-toe, checkers, and chess.** Real optimizations (TT, quiescence keyed by chess hash, LMR tuned on branching factor) either require **chess-specific forks** of `search.py` or a **refactor to a pluggable search backend** — extra design and regression testing across three folders. Budget **~15–25% more tokens per feature** than the TDD table below for the same Elo *intent*.

Each cycle is still: change code → run pytest → optional UCI smoke → re-grade.

| Optimization | Est. Elo gain | Tokens required (est.) | Est. API cost |
| --- | --- | --- | --- |
| Quiescence search (captures / promos; chess-tuned) | +80–140 | ~4,000 | ~$0.01 |
| Transposition table (Zobrist / polyglot; chess board) | +50–100 | ~5,000 | ~$0.02 |
| Move ordering (MVV-LVA, killers, history) | +30–60 | ~4,000 | ~$0.01 |
| Null-move pruning | +25–45 | ~3,500 | ~$0.01 |
| Pawn structure / passed pawns (eval) | +25–45 | ~5,500 | ~$0.02 |
| King safety (eval) | +15–35 | ~5,500 | ~$0.02 |
| Late move reductions | +15–35 | ~4,500 | ~$0.01 |
| Aspiration windows | +10–20 | ~2,500 | ~$0.01 |
| PVS / principal variation search | +20–40 | ~4,000 | ~$0.01 |
| **Total (stacked, optimistic independence)** | **+270–460** | **~38,000** | **~$0.12–0.18** |

Each grading run on the order of **50 games** at bullet TC: **~3–5 minutes** local CPU (similar to TDD doc). A full optimization campaign (many features × several re-grades): **~1–2 hours** of grading wall time, plus LLM iteration.

**Total estimated AI inference cost to “fully” optimize in Python while preserving the project’s invariants:** **< $0.35** (order-of-magnitude; depends on model and how often you re-prompt after failed tests).

---

## 3. Expected Ceiling Accuracy of the Optimized Strategy

**Projected Elo ceiling (Python, same repo / ~80 ms arena-style TC):** **~1,000–1,250** after the table in §2 is largely implemented *without* a full rewrite. That band sits **above** the current SF skill-1 anchor (~1000) but below a serious club player on long clocks.

| Benchmark | Context |
| --- | --- |
| Current calibrated baseline | **779** Elo [615, 943] |
| After quiescence + capture ordering only | ~880–980 Elo (est.) |
| After TT + null-move + LMR + aspiration + richer eval | ~1,000–1,250 Elo (est.) |
| Stockfish skill 1 (harness anchor) | 1000 Elo (label) |
| Casual human (online) | ~800–1000 Elo |
| Intermediate club player | ~1400–1600 Elo |

**Higher ceilings** (e.g. **~1800–2200+** in Python, or **stronger in native code**) require **breaking or generalizing** the “one `search.py` for three games” constraint, a much larger eval (e.g. tapered PeSTO everywhere), and/or a port — see `SCALING_ANALYSIS.md` §3 for that separate trajectory.

---

## Summary table

| Factor | Headline |
| --- | --- |
| **1. MVP compute** | ~**14k** tokens for the chess step; **~$0.05–0.08** API (est.); baseline **779** Elo in current harness. |
| **2. Optimize compute** | ~**38k** extra tokens (est.) + **1–2 h** grading if you chase the full stack; **< ~$0.35** API (est.). |
| **3. Ceiling** | **~1,000–1,250** Elo realistic for optimized **Python** chess-ttt at short TC without abandoning the shared-search design; beyond that needs architectural change. |
