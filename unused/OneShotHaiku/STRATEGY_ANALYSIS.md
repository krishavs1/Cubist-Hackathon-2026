# OneShotHaiku — Strategy Analysis

**Model:** claude-haiku-3-5 (claude-haiku-3-5-20241022)
**Methodology:** One-Shot (single conversational turn, no iteration)
**Date:** 2026-04-25

---

## 1. Compute Cost — MVP Creation

| | Tokens | Cost |
|---|---|---|
| Input | ~90 | ~$0.00007 |
| Output | ~13,355 | ~$0.054 |
| **Total** | **~13,445** | **~$0.054** |

**Pricing:** claude-haiku-3-5 at $0.80 input / $4.00 output per million tokens.

Generated in a single conversational turn with no reference files consumed — Haiku produced all 834 lines of Python code and 7 documentation files from model knowledge alone. The $0.054 total is essentially the floor cost for a functional chess engine MVP.

---

## 2. Expected Compute Cost — Strategy Optimization

The MVP is missing several key features relative to top performers:

**Missing:** quiescence search, null-move pruning, LMR, killer/history heuristics, Zobrist hashing (uses slow FEN-string TT keys), PVS

**Current depth:** ~4 plies in 5–10 seconds — limited largely by FEN-keyed transposition table overhead.

| Optimization Pass | Changes | Est. Output Tokens | Est. Cost (Haiku) |
|---|---|---|---|
| Pass 1: Quiescence search | Handles tactical explosions past search horizon | ~3,000 | ~$0.012 |
| Pass 2: Zobrist hashing | Replaces FEN-string TT keys — 10–20× TT speedup | ~2,000 | ~$0.008 |
| Pass 3: Killer + history heuristics | Better move ordering → deeper search in same time | ~2,500 | ~$0.010 |
| Pass 4: Null-move pruning + LMR | Prunes non-critical branches aggressively | ~3,000 | ~$0.012 |
| Pass 5: Aspiration windows + PVS | Faster search convergence | ~2,000 | ~$0.008 |
| Testing / debugging rounds | Tool results and chess output (input) | ~10,000 in | ~$0.008 |

**Estimated total optimization cost: ~$0.06–$0.12**

All optimization passes run on claude-haiku-3-5. At this price point, five complete optimization passes cost less than one page of Opus output.

---

## 3. Expected Ceiling Accuracy — Optimized Strategy

With the passes above, OneShotHaiku would achieve feature parity with `SimpleOneShot_bot` (benchmark leader at **1,195 Elo**).

| Configuration | Estimated Elo | Notes |
|---|---|---|
| MVP (current) | ~800–900 | Estimated; see §4 |
| + Quiescence search | ~950–1,000 | Eliminates horizon-effect blunders in tactics |
| + Zobrist TT + killer/history | ~1,050–1,100 | Faster TT → more depth; better move ordering |
| + Null-move + LMR + PVS | ~1,100–1,200 | Full feature parity with SimpleOneShot_bot |
| + Texel eval tuning | ~1,200–1,300 | Calibrated piece-square table weights |

**Projected ceiling: ~1,200–1,300 Elo**

The practical ceiling for a pure Python alpha-beta engine at 80 ms/move is roughly 1,200–1,400 Elo. Going beyond that requires either a compiled search core or a learned evaluation function (NNUE).

---

## 4. ELO Rating — MVP

**Status:** Not formally benchmarked via the Stockfish calibration harness.

**Estimate: ~800–900 Elo** (95% CI: approximately [700, 1,000])

Basis for estimate:

- Feature set is comparable to `test-driven-development` (formally rated **863 Elo** [737, 990] in the final calibration)
- Biggest absence is quiescence search — the single largest gap separating ~850-Elo from ~1,200-Elo engines at short time controls
- Reaches depth 4 in 5–10 seconds vs. OneShotOpus at depth 7 in 1.5 seconds
- FEN-keyed transposition table is ~10× slower than Zobrist, which limits effective search depth within the 80 ms movetime budget

To get a formal rating, run:

```bash
python3 elo-test/grade.py --engine OneShotHaiku/run.sh --games 36 --movetime 80
```
