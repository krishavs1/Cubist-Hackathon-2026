# Scoring Formula — Full Explanation

## The Problem

Raw chess Elo alone doesn't answer "which methodology should we invest in." A strategy that produces a 1400-Elo engine in one prompt is different from one that produces the same Elo after 50 iterations and $10 in API costs. We need a score that captures performance, efficiency, and process quality simultaneously.

The **Methodology Evaluation Score (MES)** does this by combining six factors into a single number between 0 and 1.

---

## The Formula

$$\text{MES} = w_1 F_1 + w_2 F_2 + w_3 F_3 + w_4 F_4 + w_5 F_5 + w_6 F_6$$

Six factors, six weights, all normalized to the same [0, 1] scale so they're comparable.

---

## The Six Factors

### Factor 1 — Performance vs Stockfish (weight: 25%)

**What it measures:** Each engine plays 36 games against three Stockfish skill levels (skill 1 ≈ 1000 Elo, skill 3 ≈ 1200, skill 5 ≈ 1500) at 80 ms per move. An absolute Elo is computed using inverse-variance weighting across the three anchors, with a 95% confidence interval from the trinomial variance of the win/draw/loss outcomes.

**Why it's the highest weight:** This is the most objective, reproducible measure of engine quality. It's calibrated against a fixed external reference (Stockfish), not just relative to the other strategies.

**Data source:** Each engine's `results.json` → `elo` field.

**Normalization:** Min-max across the four engines.
$$F_1 = \frac{\text{Elo} - 779}{1447 - 779}$$

---

### Factor 2 — Performance vs Other Strategies (weight: 20%)

**What it measures:** Each engine plays 10 games against each of the three other engines (30 cross-validation games total). The score for each matchup is `(W + 0.5D) / 10`, then averaged across opponents.

**Why it matters:** Calibration tells you absolute strength; cross-validation tells you relative strength and style. An engine that is calibrated at 900 Elo but beats the 863-Elo engine 9/10 gives us more information than calibration alone. It also catches cases where calibration noise misleads — if two engines have overlapping confidence intervals, head-to-head breaks the tie.

**Why it's slightly lower than F1:** Cross-validation at 10 games per pair has large sampling error (±150+ Elo implied gap). It's informative but noisier than the 36-game Stockfish calibration.

**Data source:** Cross-validation matrix from `FINAL_REPORT_4ENGINE.md`, verified against each engine's `results.json` → `cross_validation` field.

**Normalization:** Min-max on the raw average score.
$$F_2 = \frac{s_{\text{avg}} - 0.083}{0.900 - 0.083}$$

---

### Factor 3 — API Cost to Build the MVP (weight: 20%)

**What it measures:** The total dollar cost of AI inference to produce a working, UCI-compliant chess engine from scratch. Includes all prompts, iterations, model outputs, and any multi-model routing.

**Why it matters:** The hackathon rubric explicitly weights cost efficiency. A methodology that produces a good engine for $0.10 is more transferable than one that needs $1.00 of Opus credits to get started. Compute costs are a real constraint on how often you can iterate.

**Why it matches F1's weight:** The judging criteria treat "compute efficiency" as co-equal with engine quality. A methodology that scores 900 Elo for $0.10 is arguably more impressive than one that scores 1000 Elo for $5.00.

**Data source:** Each strategy's `COMPUTE.md` or `STRATEGY_ANALYSIS.md` → Section 1.

**Direction:** Lower cost = higher score. Normalized as:
$$F_3 = \frac{\$0.850 - \text{cost}}{\$0.850 - \$0.065}$$

**Note on OneShotOpus:** Its token count (~12,260) is the lowest of the four, but claude-opus-4-7 pricing ($15 input / $75 output per million tokens) makes the dollar cost $0.633 — second-highest. The methodology is cheap in compute but expensive in dollars because of the model choice.

---

### Factor 4 — Expected API Cost to Fully Optimize (weight: 15%)

**What it measures:** The projected dollar cost to close the gap between the current MVP and the strategy's projected Elo ceiling, following the same methodology (same AI workflow, same testing loop, same model tier).

**Why it matters:** An MVP is just the starting line. If a strategy scores 800 Elo today but costs $3.00 per optimization pass, it's less viable to iterate on than a strategy that scores 750 Elo but costs $0.15 per pass. The methodology's marginal cost determines how many iterations you can afford.

**Why it's weighted at 15%:** Slightly less than MVP cost because it's a projection, not a measurement. The optimization roadmaps are well-reasoned estimates, not empirical numbers.

**Data source:** Each strategy's `COMPUTE.md` or `STRATEGY_ANALYSIS.md` → Section 2.

**Direction:** Lower cost = higher score. Normalized as:
$$F_4 = \frac{\$2.40 - \text{cost}}{\$2.40 - \$0.135}$$

**Note on OneShotOpus:** The STRATEGY_ANALYSIS.md gives two estimates: $1.80–3.00 if optimization is done on Opus (consistent with the one-shot methodology), or $0.15–0.25 if passed off to Haiku. The primary Opus estimate ($2.40 midpoint) is used here, which drops OneShotOpus's F4 to zero. This is the correct interpretation of the methodology — if you commit to one-shot Opus as your workflow, optimization on the same model is the fair cost.

---

### Factor 5 — Projected Elo Ceiling (weight: 10%)

**What it measures:** The highest Elo the strategy is expected to reach after the full optimization roadmap in Section 2 of each COMPUTE.md is implemented, assuming Python as the runtime and the same time control (80 ms/move).

**Why it's a lower weight:** This is the most speculative of the six factors. Projected ceilings depend on assumptions about search depth, Python speed limits, and how well each optimization stacks. The numbers are well-reasoned but not empirical.

**Why it still matters:** Two strategies with similar current Elo but very different ceilings represent different long-term bets. If we're choosing what to build on, the ceiling is part of the answer.

**Data source:** Each strategy's `COMPUTE.md` → Section 3. Strategy1's ceiling is revised upward from the COMPUTE.md's original 1,300–1,400 projection because the PeSTO upgrade already pushed it to 1,447, exceeding that projection. The revised ceiling of 1,500–1,700 reflects post-upgrade architectural parity with OneShotOpus.

**Normalization:** Midpoints of each range, then min-max.
$$F_5 = \frac{\text{ceiling} - 1125}{1600 - 1125}$$

---

### Factor 6 — Methodology Quality Score (weight: 10%)

**What it measures:** How well each strategy's AI engineering process aligns with the hackathon's four judging criteria, scored 0–10 on each:

1. **Chess Engine Quality** — Does the engine play legal, strategic chess? Is it robust?
2. **AI Usage** — Was AI used creatively and critically? Did the team evaluate and iterate on AI output rather than blindly accept it?
3. **Process & Parallelization** — Is there evidence of parallel workstreams, code review, structured integration?
4. **Engineering Quality** — Is there documentation, testing (unit/perft/self-play), and research into prior art?

**Why it's a lower weight:** This is the most subjective factor. It's included because the rubric explicitly judges process, not just output — but its lower weight reflects the fact that it's assessed qualitatively rather than measured.

**How it was scored:** Each engine was scored 0–10 on all four criteria, summed (0–40), then normalized to 0–1 by dividing by the highest raw score (Strategy1 at 36/40).

| Engine | Chess Quality | AI Usage | Process | Engineering | Total |
|---|---|---|---|---|---|
| Strategy1 | 10 | 9 | 9 | 8 | **36** |
| TDD | 5 | 9 | 6 | 10 | **30** |
| chess-ttt | 4 | 8 | 7 | 9 | **28** |
| OneShotOpus | 8 | 5 | 3 | 5 | **21** |

**Key distinctions:**
- Strategy1 leads on Chess Quality (highest Elo) and AI Usage (Darwinian loop, Reflexion cycles, personality registry, multi-model routing)
- TDD leads on Engineering Quality: 27 unit tests, 6 UCI conformance checks, benchmark suite, and workflow documentation. Its AI Usage score ties Strategy1 because the TDD loop is the most rigorous evaluation of AI output — every AI-generated feature is gated behind a failing test
- chess-ttt leads on Engineering Quality for a different reason: 52+ tests, perft verification, and byte-identical MD5 checks across three games prove the search core is correct
- OneShotOpus is penalized on AI Usage (no evaluation, no iteration) and Process (single person, one prompt, no parallelization)

---

## Normalization — Why Min-Max?

Each factor uses a different unit: Elo points, win rates, dollars, and dimensionless rubric scores. Min-max normalization converts everything to the same [0, 1] scale while preserving the relative gaps between strategies.

The alternative — normalizing to an external standard (e.g., "800 Elo = 0, 2800 Elo = 1") — would make most scores cluster near zero and be less meaningful for comparing these four strategies against each other.

The tradeoff: min-max normalization means "1.0" always belongs to the best performer on that factor, not to some absolute benchmark. This is intentional — we are ranking these four strategies against each other, not against all possible chess engines.

---

## Weight Rationale

The weights were set to reflect the user's explicit prioritization — "compute cost and performance are the most important aspects" — with the four primary factors carrying 80% of total weight combined.

| Cluster | Factors | Combined Weight | Rationale |
|---|---|---|---|
| **Performance** | F1 + F2 | 45% | How good is the engine, both absolutely and relatively? This is the primary output metric. |
| **Compute efficiency** | F3 + F4 | 35% | How expensive is this methodology? Drives whether it's practical to iterate and scale. |
| **Future potential** | F5 + F6 | 20% | Tie-breakers: ceiling and process quality matter, but they're projections. |

Within performance, F1 (25%) outweighs F2 (20%) because the Stockfish calibration is a more statistically robust measurement than 10-game cross-validation matches.

Within compute, F3 (20%) outweighs F4 (15%) because the MVP cost is an empirical measurement while optimization cost is a projection.
