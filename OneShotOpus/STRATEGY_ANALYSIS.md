# OneShotOpus — Strategy Analysis

**Model:** claude-opus-4-7
**Methodology:** One-Shot (single conversational turn, no iteration)
**Date:** 2026-04-25

---

## 1. Compute Cost — MVP Creation

| | Tokens | Cost |
|---|---|---|
| Input | ~4,777 | ~$0.072 |
| Output | ~7,483 | ~$0.561 |
| **Total** | **~12,260** | **~$0.633** |

**Pricing:** claude-opus-4-7 at ~$15 input / ~$75 output per million tokens.

Opus consumed the project README and three Haiku source files as context (~3,420 input tokens), which is why its input cost is non-trivial. Despite referencing prior work, it independently produced a more sophisticated engine (Negamax + PVS, Zobrist TT with EXACT/LOWER/UPPER bounds, quiescence with delta pruning, null-move, LMR, tapered PeSTO eval) in a single pass — at ~12× the total cost of OneShotHaiku.

---

## 2. Expected Compute Cost — Strategy Optimization

The MVP already implements the full modern search recipe. Optimization is primarily an eval-layer and time-management problem, not a search restructuring problem.

| Optimization Pass | Changes | Est. Tokens | Est. Cost (Opus) |
|---|---|---|---|
| Texel eval tuning | Generate training positions, optimize PST weights | ~5,000 out + ~5,000 in | ~$0.45 |
| Opening book integration | Compact PGN book probe in engine.py | ~3,000 out | ~$0.23 |
| Endgame tablebases | Syzygy DTZ probe integration | ~4,000 out | ~$0.30 |
| Time management calibration | Soft/hard limit tuning for tournament play | ~2,000 out | ~$0.15 |
| NNUE-style evaluation | Replace hand-crafted PSTs with a small learned net | ~8,000 out + ~3,000 in | ~$0.65 |

**Estimated total optimization cost: ~$1.80–$3.00 on Opus; ~$0.15–$0.25 if implementation passes are delegated to Haiku.**

The core search is already near its ceiling — incremental Elo gains require eval investment, not search restructuring.

---

## 3. Expected Ceiling Accuracy — Optimized Strategy

| Configuration | Estimated Elo | Notes |
|---|---|---|
| MVP (current) | ~1,100–1,200 | Estimated; see §4 |
| + Texel eval tuning | ~1,200–1,350 | Calibrated PST values instead of standard hand-coded weights |
| + Opening book | ~1,300–1,400 | Avoids early theory blunders |
| + Endgame tablebases | ~1,400–1,500 | Perfect play in ≤7-piece endings |
| + NNUE evaluation | ~1,500–1,700 | Replaces PSTs with a learned positional model |

**Projected ceiling: ~1,500–1,700 Elo** — approaching the Stockfish skill 5 anchor (~1,500 Elo).

The practical ceiling for a pure Python UCI engine at 80 ms/move with a NNUE evaluator is approximately 1,600–1,800 Elo. Exceeding that requires a compiled search core (Rust or C++).
