# Compute Analysis — Strategy1 (Darwinian Chess Engine)

## 1. Compute Cost to Create the Initial MVP

| Resource | Amount |
| --- | --- |
| AI tokens (input) | ~92,000 |
| AI tokens (output) | ~113,000 |
| Total tokens | ~205,000 |
| Estimated API cost | ~$0.70–$1.00 |
| Local CPU — code generation | < 10 seconds |
| Local CPU — perft / UCI / self-play test suite | ~12 seconds |
| Local CPU — internal round-robin (6 personalities, 30 games, 50ms/move) | ~18 minutes |
| Local CPU — ELO grading (36 games vs Stockfish Skills 1/3/5) | ~6 minutes |
| Local CPU — cross-validation vs 3 rival strategies (30 games) | ~12 minutes |

Baseline ELO result: **1014 [902, 1126]** at 95% confidence (Champion personality: `reflexion_v1`, derived from `positional_grinder` via one Reflexion cycle).

Cross-validation record (30 games, 3 rival strategies): 13W / 10D / 7L (57% score).

---

## 2. Expected Compute Cost to Optimize

Each optimization follows the Darwinian loop: prompt Claude for a new evaluator → register in `heuristics.REGISTRY` → run round-robin tournament → promote if it beats the current Champion. Search core (`search.py`) is held constant so each variant is a controlled experiment.

| Optimization | Est. ELO Gain | Tokens Required | Est. API Cost |
| --- | --- | --- | --- |
| Reflexion v2 (tempo + repetition penalty on v1's losses) | +40–80 | ~10,000 | ~$0.04 |
| Tapered PST personality (NNUE-inspired midgame/endgame interpolation) | +60–100 | ~12,000 | ~$0.05 |
| Endgame-aware evaluator (KPK, rook activity, passed pawns) | +50–80 | ~10,000 | ~$0.04 |
| Mobility-density evaluator | +30–60 | ~10,000 | ~$0.04 |
| Reflexion v3 on the new Champion | +30–60 | ~10,000 | ~$0.04 |
| King-safety personality (attack-table weighting) | +20–40 | ~8,000 | ~$0.03 |
| Aspiration-window tuning (search-core one-shot edit) | +20–40 | ~5,000 | ~$0.02 |
| Time-management pass (proper `wtime`/`btime` use) | +30–50 | ~8,000 | ~$0.03 |
| Null-move reduction tuning | +10–20 | ~3,000 | ~$0.01 |
| **Total** | **+290–530** | **~76,000** | **~$0.30** |

Each grading run (36 games vs Stockfish anchors): ~6 minutes of local CPU. Each internal tournament re-run (N personalities, 50ms/move): ~2–5 minutes. Full optimization cycle across all features: ~1–2 hours of grading time.

Total estimated cost to fully optimize: **< $0.35** in AI inference.

---

## 3. Expected Ceiling Accuracy of the Optimized Strategy

Projected ELO ceiling: **~1,300–1,400**

| Benchmark | Context |
| --- | --- |
| Current baseline | 1014 Elo |
| After Reflexion v2 | ~1,100 Elo |
| After tapered-PST personality | ~1,200 Elo |
| After full optimization | ~1,300–1,400 Elo |
| Stockfish Skill Level 1 (anchor) | 1,000 Elo |
| Stockfish Skill Level 3 (anchor) | 1,200 Elo |
| Stockfish Skill Level 5 (anchor) | 1,500 Elo |
| Casual human player | ~800–1,000 Elo |
| Intermediate club player | ~1,400–1,600 Elo |
