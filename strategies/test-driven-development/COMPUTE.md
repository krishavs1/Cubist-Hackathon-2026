# Compute Analysis — Test-Driven Chess Engine

## 1. Compute Cost to Create the Initial MVP

| Resource | Amount |
|---|---|
| AI tokens (input) | ~20,000 |
| AI tokens (output) | ~10,000 |
| Total tokens | ~30,000 |
| Estimated API cost | ~$0.10–0.15 |
| Local CPU — code generation | < 5 seconds |
| Local CPU — test suite (27 tests) | 0.05 seconds |
| Local CPU — UCI conformance (6 tests) | ~15 seconds |
| Local CPU — ELO grading (50 games vs Stockfish Skill 1) | ~4 minutes |

**Baseline ELO result: 790 [669, 878] at 95% confidence**

---

## 2. Expected Compute Cost to Optimize

Each optimization follows the same TDD loop: write test → implement → re-grade.

| Optimization | Est. ELO Gain | Tokens Required | Est. API Cost |
|---|---|---|---|
| Quiescence search | +100–150 | ~3,000 | ~$0.01 |
| Transposition table | +50–100 | ~4,000 | ~$0.01 |
| Better move ordering (killers, history heuristic) | +30–60 | ~3,000 | ~$0.01 |
| Null move pruning | +30–50 | ~3,000 | ~$0.01 |
| Pawn structure evaluation | +30–50 | ~5,000 | ~$0.02 |
| King safety evaluation | +20–40 | ~5,000 | ~$0.02 |
| Late move reductions | +20–40 | ~4,000 | ~$0.01 |
| Aspiration windows | +10–20 | ~2,000 | ~$0.01 |
| Endgame table integration | +20–30 | ~6,000 | ~$0.02 |
| **Total** | **+310–540** | **~35,000** | **~$0.12–0.15** |

Each grading run (50 games): ~4 minutes of local CPU. Full optimization cycle across all features: ~1–2 hours of grading time.

**Total estimated cost to fully optimize: < $0.30 in AI inference.**

---

## 3. Expected Ceiling Accuracy of the Optimized Strategy

**Projected ELO ceiling: ~1,100–1,300**

| Benchmark | Context |
|---|---|
| Current baseline | 790 Elo |
| After quiescence search | ~900–950 Elo |
| After full optimization | ~1,100–1,300 Elo |
| Stockfish Skill Level 1 (anchor) | 1,000 Elo |
| Casual human player | ~800–1,000 Elo |
| Intermediate club player | ~1,400–1,600 Elo |

