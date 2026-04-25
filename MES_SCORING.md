# Methodology Evaluation Score (MES) — 4-Strategy Ranking

**Purpose:** Quantitatively rank the four AI engineering strategies on six factors to identify the optimal one to build upon.

---

## 1. Scoring Formula

Each of the six factors is normalized to **[0, 1]** using min-max scaling, then combined via a weighted sum:

$$\text{MES} = w_1 F_1 + w_2 F_2 + w_3 F_3 + w_4 F_4 + w_5 F_5 + w_6 F_6$$

### Weights

| Factor | Description | Weight | Direction |
|---|---|---|---|
| F1 | Calibrated Elo vs Stockfish anchors | **0.25** | Higher = better |
| F2 | Cross-validation score vs other strategies | **0.20** | Higher = better |
| F3 | API cost to create MVP | **0.20** | Lower = better |
| F4 | Expected API cost to fully optimize | **0.15** | Lower = better |
| F5 | Projected Elo ceiling of optimized strategy | **0.10** | Higher = better |
| F6 | Methodology quality score (hackathon rubric) | **0.10** | Higher = better |

Factors 1–4 carry 80% of the total weight. Factors 5–6 are tie-breakers.

### Normalization

For higher-is-better factors (F1, F2, F5, F6):
$$F_i = \frac{x_i - \min(x)}{\max(x) - \min(x)}$$

For lower-is-better factors (F3, F4):
$$F_i = \frac{\max(x) - x_i}{\max(x) - \min(x)}$$

---

## 2. Raw Data

### F1 — Calibrated Elo (from `results.json`, 36 games vs Stockfish skill 1/3/5 at 80 ms/move)

| Engine | Calibrated Elo | 95% CI |
|---|---|---|
| Strategy1 | **1447** | [1319, 1576] |
| OneShotOpus | **1212** | [1097, 1327] |
| TDD | **863** | [737, 990] |
| chess-ttt | **779** | [615, 943] |

### F2 — Cross-Validation Average Score (`(W + 0.5D) / total` across 3 opponents, 10 games each)

| Engine | vs OneShotOpus | vs Strategy1 | vs TDD | vs chess-ttt | Avg Score |
|---|---|---|---|---|---|
| Strategy1 | 0.700 | — | 1.000 | 1.000 | **0.900** |
| OneShotOpus | — | 0.300 | 0.900 | 1.000 | **0.733** |
| TDD | 0.100 | 0.000 | — | 0.750 | **0.283** |
| chess-ttt | 0.000 | 0.000 | 0.250 | — | **0.083** |

### F3 — MVP API Cost (from COMPUTE.md / STRATEGY_ANALYSIS.md)

| Engine | Total Tokens | API Cost (midpoint) | Source |
|---|---|---|---|
| chess-ttt | ~13,600 | **$0.065** | `chess-ttt/COMPUTE.md` |
| TDD | ~30,000 | **$0.125** | `test-driven-development/COMPUTE.md` |
| OneShotOpus | ~12,260 | **$0.633** | `OneShotOpus/STRATEGY_ANALYSIS.md` (Opus pricing) |
| Strategy1 | ~205,000 | **$0.850** | `Strategy1/COMPUTE.md` |

*OneShotOpus has the lowest token count but the highest $/token cost due to claude-opus-4-7 pricing ($15 input / $75 output per million tokens).*

### F4 — Optimization API Cost (from COMPUTE.md files)

| Engine | Est. Optimization Cost | Source |
|---|---|---|
| TDD | **$0.135** | ~35K tokens, `test-driven-development/COMPUTE.md` |
| chess-ttt | **$0.150** | ~38K tokens, `chess-ttt/COMPUTE.md` |
| Strategy1 | **$0.300** | ~76K tokens, `Strategy1/COMPUTE.md` |
| OneShotOpus | **$2.400** | Texel tuning + NNUE on Opus; `OneShotOpus/STRATEGY_ANALYSIS.md` |

*Note: OneShotOpus optimization cost drops to ~$0.20 if implementation passes are delegated to Haiku. The primary stated cost (Opus throughout) is used here for consistency with the stated methodology.*

### F5 — Projected Ceiling Elo (from COMPUTE.md files; Strategy1 ceiling revised to match OneShotOpus given post-upgrade architecture parity)

| Engine | Ceiling Range | Midpoint Used |
|---|---|---|
| Strategy1 | ~1,500–1,700 *(revised from 1,300–1,400 in COMPUTE.md; engine already at 1,447 post-PeSTO upgrade)* | **1,600** |
| OneShotOpus | ~1,500–1,700 | **1,600** |
| TDD | ~1,100–1,300 | **1,200** |
| chess-ttt | ~1,000–1,250 | **1,125** |

### F6 — Methodology Score (hackathon rubric: Chess Quality, AI Usage, Process & Parallelization, Engineering Quality — scored 0–10 each)

| Engine | Chess Quality | AI Usage | Process & Parallelization | Engineering Quality | Raw (0–40) | Normalized |
|---|---|---|---|---|---|---|
| Strategy1 | 10 | 9 | 9 | 8 | 36 | **0.900** |
| TDD | 5 | 9 | 6 | 10 | 30 | **0.750** |
| chess-ttt | 4 | 8 | 7 | 9 | 28 | **0.700** |
| OneShotOpus | 8 | 5 | 3 | 5 | 21 | **0.525** |

**Rubric rationale:**
- **Strategy1:** Full marks on chess quality (highest Elo) and strong on AI usage (Darwinian loop, reflexion cycles, multiple models, personality registry). High on parallelization (5-person workstream structure documented in `head.md`).
- **TDD:** Leads on engineering quality (27 tests, UCI conformance, benchmark suite, docs). Top AI usage score because every AI-generated feature is gated behind a failing test before acceptance — the most rigorous evaluation loop.
- **chess-ttt:** Strong engineering quality (52+ tests, perft, MD5 cross-verification). High AI creativity (game-agnostic abstraction, byte-identical search reuse). Penalized on chess quality (lowest Elo).
- **OneShotOpus:** Strong chess quality output and clean code, but no iteration, no evaluation of AI output, no parallelization — weakest on process criteria.

---

## 3. Normalized Scores

| Engine | F1 (Elo) | F2 (Cross-val) | F3 (MVP cost) | F4 (Opt. cost) | F5 (Ceiling) | F6 (Rubric) |
|---|---|---|---|---|---|---|
| Strategy1 | **1.000** | **1.000** | 0.000 | 0.927 | **1.000** | **1.000** |
| OneShotOpus | 0.648 | 0.796 | 0.276 | 0.000 | **1.000** | 0.583 |
| TDD | 0.126 | 0.245 | 0.924 | **1.000** | 0.158 | 0.833 |
| chess-ttt | 0.000 | 0.000 | **1.000** | 0.993 | 0.000 | 0.778 |

**Normalization details:**

| Factor | Min | Max | Range |
|---|---|---|---|
| F1 | 779 Elo | 1447 Elo | 668 |
| F2 | 0.083 | 0.900 | 0.817 |
| F3 | $0.065 | $0.850 | $0.785 |
| F4 | $0.135 | $2.400 | $2.265 |
| F5 | 1125 Elo | 1600 Elo | 475 |
| F6 | 0.525 | 0.900 | 0.375 |

---

## 4. Final MES Scores

$$\text{MES} = 0.25 F_1 + 0.20 F_2 + 0.20 F_3 + 0.15 F_4 + 0.10 F_5 + 0.10 F_6$$

| Engine | 0.25·F1 | 0.20·F2 | 0.20·F3 | 0.15·F4 | 0.10·F5 | 0.10·F6 | **MES** |
|---|---|---|---|---|---|---|---|
| **Strategy1** | 0.250 | 0.200 | 0.000 | 0.139 | 0.100 | 0.100 | **0.789** |
| **OneShotOpus** | 0.162 | 0.159 | 0.055 | 0.000 | 0.100 | 0.058 | **0.534** |
| **TDD** | 0.032 | 0.049 | 0.185 | 0.150 | 0.016 | 0.083 | **0.515** |
| **chess-ttt** | 0.000 | 0.000 | 0.200 | 0.149 | 0.000 | 0.078 | **0.427** |

---

## 5. Final Ranking

| Rank | Engine | MES Score | Key Strength | Key Weakness |
|---|---|---|---|---|
| 🥇 1 | **Strategy1** | **0.789** | Dominates on performance (F1+F2) and rubric (F6) | Most expensive MVP to build (F3=0) |
| 🥈 2 | **OneShotOpus** | **0.534** | Strong performance, tied ceiling with Strategy1 | Optimization on Opus is cost-prohibitive (F4=0) |
| 🥉 3 | **TDD** | **0.515** | Cheapest to optimize, strong engineering quality | Weakest performance (F1+F2) |
| 4 | **chess-ttt** | **0.427** | Cheapest MVP, near-zero optimization cost | No performance against either peer |

---

## 6. Key Insights

**Strategy1 wins clearly** (0.789 vs 0.534), driven by its dominant performance scores. It loses points only on MVP compute cost — 205K tokens and ~$0.85 to build — but that is offset by strong scores everywhere else.

**OneShotOpus and TDD are nearly tied** (0.534 vs 0.515). The gap between them is almost entirely explained by F4: OneShotOpus optimization on Opus costs ~$2.40, dropping F4 to zero. If optimization passes were delegated to Haiku (~$0.20), OneShotOpus's MES rises to **~0.625**, pulling clearly ahead of TDD.

**chess-ttt is the most compute-efficient** methodology (cheapest MVP, cheapest optimization) but that efficiency doesn't translate to Elo — it scores zero on both performance factors.

**The strategy to build upon is Strategy1.** Its architecture (PVS + persistent TT + PeSTO + LMR + null-move) is already at the ceiling of what Python can sustain at 80 ms/move. The next meaningful delta comes from a Rust rewrite of the search core.
