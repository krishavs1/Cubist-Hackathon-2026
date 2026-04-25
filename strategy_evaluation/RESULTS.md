# MES Results — Final Scores and Rankings

## Final Ranking

| Rank | Engine | MES Score | Verdict |
|---|---|---|---|
| 🥇 1 | **Strategy1** | **0.789** | Clear winner — build on this |
| 🥈 2 | **OneShotOpus** | **0.534** | Strong engine, expensive to optimize |
| 🥉 3 | **TDD** | **0.515** | Most compute-efficient; limited by engine strength |
| 4 | **chess-ttt** | **0.427** | Cheapest methodology; weakest chess output |

---

## Normalized Factor Scores

| Engine | F1 Elo (0.25) | F2 Cross-val (0.20) | F3 MVP cost (0.20) | F4 Opt. cost (0.15) | F5 Ceiling (0.10) | F6 Rubric (0.10) | **MES** |
|---|---|---|---|---|---|---|---|
| **Strategy1** | 1.000 | 1.000 | 0.000 | 0.927 | 1.000 | 1.000 | **0.789** |
| **OneShotOpus** | 0.648 | 0.796 | 0.276 | 0.000 | 1.000 | 0.583 | **0.534** |
| **TDD** | 0.126 | 0.245 | 0.924 | 1.000 | 0.158 | 0.833 | **0.515** |
| **chess-ttt** | 0.000 | 0.000 | 1.000 | 0.993 | 0.000 | 0.778 | **0.427** |

---

## Raw Data Behind Each Factor

### F1 — Calibrated Elo

| Engine | Elo | 95% CI | Normalized |
|---|---|---|---|
| Strategy1 | 1447 | [1319, 1576] | 1.000 |
| OneShotOpus | 1212 | [1097, 1327] | 0.648 |
| TDD | 863 | [737, 990] | 0.126 |
| chess-ttt | 779 | [615, 943] | 0.000 |

*36 games per engine vs Stockfish skill 1/3/5 at 80 ms/move. Absolute Elo via inverse-variance combination across anchors.*

### F2 — Cross-Validation Average Score

| Engine | vs OneShotOpus | vs Strategy1 | vs TDD | vs chess-ttt | Avg | Normalized |
|---|---|---|---|---|---|---|
| Strategy1 | 0.700 | — | 1.000 | 1.000 | 0.900 | 1.000 |
| OneShotOpus | — | 0.300 | 0.900 | 1.000 | 0.733 | 0.796 |
| TDD | 0.100 | 0.000 | — | 0.750 | 0.283 | 0.245 |
| chess-ttt | 0.000 | 0.000 | 0.250 | — | 0.083 | 0.000 |

*Score = (W + 0.5D) / 10. 10 games per matchup.*

### F3 — MVP API Cost

| Engine | Total Tokens | Dollar Cost | Normalized |
|---|---|---|---|
| chess-ttt | ~13,600 | $0.065 | 1.000 |
| TDD | ~30,000 | $0.125 | 0.924 |
| OneShotOpus | ~12,260 | $0.633 | 0.276 |
| Strategy1 | ~105,000 | $0.850 | 0.000 |

*OneShotOpus has the fewest tokens but the second-highest dollar cost: claude-opus-4-7 at $75/M output tokens.*

### F4 — Optimization API Cost

| Engine | Est. Cost | Normalized |
|---|---|---|
| TDD | $0.135 | 1.000 |
| chess-ttt | $0.150 | 0.993 |
| Strategy1 | $0.300 | 0.927 |
| OneShotOpus | $2.400 | 0.000 |

*OneShotOpus optimization cost assumes continued use of claude-opus-4-7 (Texel tuning + NNUE). Drops to ~$0.20 if delegated to Haiku — see sensitivity analysis below.*

### F5 — Projected Ceiling Elo

| Engine | Range | Midpoint | Normalized |
|---|---|---|---|
| Strategy1 | 1,500–1,700 *(revised)* | 1,600 | 1.000 |
| OneShotOpus | 1,500–1,700 | 1,600 | 1.000 |
| TDD | 1,100–1,300 | 1,200 | 0.158 |
| chess-ttt | 1,000–1,250 | 1,125 | 0.000 |

*Strategy1 ceiling revised upward from COMPUTE.md's 1,300–1,400 — the PeSTO upgrade already pushed it to 1,447, exceeding the original projection.*

### F6 — Methodology Rubric Score

| Engine | Chess Quality | AI Usage | Process | Engineering | Total /40 | Normalized |
|---|---|---|---|---|---|---|
| Strategy1 | 10 | 9 | 9 | 8 | 36 | 1.000 |
| TDD | 5 | 9 | 6 | 10 | 30 | 0.833 |
| chess-ttt | 4 | 8 | 7 | 9 | 28 | 0.778 |
| OneShotOpus | 8 | 5 | 3 | 5 | 21 | 0.583 |

---

## Weighted Contribution Breakdown

How many MES points each factor contributes for each engine:

| Engine | 0.25 × F1 | 0.20 × F2 | 0.20 × F3 | 0.15 × F4 | 0.10 × F5 | 0.10 × F6 | Total |
|---|---|---|---|---|---|---|---|
| Strategy1 | **+0.250** | **+0.200** | +0.000 | +0.139 | **+0.100** | **+0.100** | **0.789** |
| OneShotOpus | +0.162 | +0.159 | +0.055 | +0.000 | +0.100 | +0.058 | **0.534** |
| TDD | +0.032 | +0.049 | +0.185 | **+0.150** | +0.016 | +0.083 | **0.515** |
| chess-ttt | +0.000 | +0.000 | **+0.200** | +0.149 | +0.000 | +0.078 | **0.427** |

---

## Sensitivity Analysis — What If OneShotOpus Delegates Optimization to Haiku?

The second-largest swing variable is how OneShotOpus's optimization cost is counted. If passes are delegated to Haiku (~$0.20), F4 changes:

| Engine | F4 (Opus) | F4 (Haiku delegation) |
|---|---|---|
| TDD | 1.000 | 1.000 |
| chess-ttt | 0.993 | 0.909 |
| **OneShotOpus** | **0.000** | **0.606** |
| Strategy1 | 0.927 | 0.000 |

**Resulting MES scores (Haiku delegation scenario):**

| Engine | MES (Opus) | MES (Haiku) | Change |
|---|---|---|---|
| Strategy1 | 0.789 | 0.650 | −0.139 |
| **OneShotOpus** | 0.534 | **0.625** | **+0.091** |
| TDD | 0.515 | 0.515 | 0 |
| chess-ttt | 0.427 | 0.414 | −0.013 |

**Takeaway:** Strategy1 still wins (0.650), but OneShotOpus clearly separates from TDD (0.625 vs 0.515). The ranking is stable; only the gap between #1 and #2 changes.

---

## Key Takeaways

**1. Strategy1 is the right strategy to build on.**
It scores highest on every performance metric and on the hackathon rubric. Its only weak factor is MVP build cost (205K tokens, ~$0.85), but that is offset by strong optimization efficiency ($0.30 to close the remaining gap) and a clear path to 1,500–1,700 Elo via the Rust rewrite.

**2. OneShotOpus and TDD are nearly indistinguishable overall (0.534 vs 0.515).**
They win on opposite axes: OneShotOpus wins on engine quality; TDD wins on compute efficiency and process rigor. The near-tie means neither is clearly superior as a standalone methodology — but OneShotOpus produces a better starting engine to hand off to Phase 3 (Rust translation), while TDD produces a better-documented codebase to hand off to future developers.

**3. chess-ttt's methodology is compute-optimal but performance-limited.**
It costs almost nothing to build and optimize, but the game-agnostic search core hits a ceiling early because it cannot exploit chess-specific patterns (transposition table keyed to chess positions, quiescence search tuned to capture depth, etc.). The abstraction that makes it elegant is also what caps it.

**4. The Opus pricing model is the single largest swing factor.**
If OneShotOpus optimization is done on Haiku, the ranking and gaps change meaningfully. Model choice is a strategic decision, not just a cost detail.
