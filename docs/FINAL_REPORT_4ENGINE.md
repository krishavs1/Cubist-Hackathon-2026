# 4-Engine Elo Shootout — Final Report

**Engines compared:** `Strategy1`, `OneShotOpus`, `test-driven-development` (TDD), `ttt-iteration_bot/chess-ttt`  
**Evaluator:** `elo-test/` (hardened arena + calibrator)  
**Report updated:** 2026-04-25 (reflects Strategy1 engine upgrade + fresh Strategy1 calibration and cross-validation)

---

## 1. TL;DR — Final Leaderboard

| Rank | Engine | Calibrated Elo | 95% CI | Methodology (short) |
| :-: | --- | ---: | :-: | --- |
| **1** | `Strategy1` | **1447** | [1319, 1576] | Darwinian MVE stack: shared PVS search + **PeSTO** eval, persistent TT, tuned time use |
| **2** | `OneShotOpus` | **1212** | [1097, 1327] | One-shot Opus prompt — full modern search + tapered PeSTO |
| **3** | `test-driven-development` | **863** | [737, 990] | TDD — tests first, engine built to pass tests |
| **4** | `chess-ttt` | **779** | [615, 943] | TTT → Checkers → Chess scaling (game-agnostic search) |

**Spread:** 668 Elo between first and fourth. **Head-to-head:** Strategy1 beats OneShotOpus **4–0–6** in 10 games at 80 ms/move; Strategy1 **shut out** TDD and chess-ttt **10–0–0** each. Ordinal from anchors (**Strategy1 > OneShotOpus > TDD > chess-ttt**) matches cross-val among the top two and the weaker pair.

---

## 2. Arena & Calibration Setup

All numbers use the same harness (`elo-test/arena.py` + `elo-test/grade.py`).

**Arena (`arena.py`):**

- UCI over stdio via each engine’s `engine/run.sh`.
- **512 MB** RAM cap, **2.0 s** hard per-move timeout.
- Eight balanced opening FENs; colors alternate each game.
- PGNs under `pgns/` (naming depends on caller).
- Log lines use `[W]` / `[B]` / `[D]` for **game result** (white win / black win / draw), not “which color engine A played.” `Final: NW-NL-ND` is **engine A’s** wins / losses / draws.

**Calibration (`grade.py`, default for this report):**

- Three Stockfish anchors: skill **1 → 1000**, **3 → 1200**, **5 → 1500** Elo (mapping used by the harness).
- **12 games per anchor per engine** (36 games total per full calibration), **80 ms** `movetime`.
- Per-anchor Elo estimate, then **inverse-variance** combination (see §3).
- Incremental writes to each engine’s `results.json` after each anchor block.

**Cross-validation (`grade.py --cross-validate`):**

- **10 games** per unordered pair, **80 ms** `movetime`.
- Does **not** change stored calibration Elo; it checks head-to-head consistency.

---

## 3. Elo Math (what the numbers mean)

For `W` / `L` / `D` against anchor Elo `E_a`:

**Score:** \(S = (W + 0.5 D) / (W + L + D)\)

**Engine Elo vs that anchor:** \(E = E_a + 400 \log_{10}\bigl(S / (1-S)\bigr)\)

**Trinomial variance of** \(S\), then **delta method** for \(\mathrm{SE}(E)\).

**Combine anchors:** \(\hat E = \sum_i (E_i / \sigma_i^2) \big/ \sum_i (1/\sigma_i^2)\), \(\mathrm{SE}(\hat E) = 1 / \sqrt{\sum_i 1/\sigma_i^2}\).

**95% CI:** \(\hat E \pm 1.96 \,\mathrm{SE}(\hat E)\).

---

## 4. Calibration Raw Data (vs Stockfish anchors)

12 games per cell. Score = \((W + 0.5 D) / 12\).

| Engine | SF-1 (1000) | SF-3 (1200) | SF-5 (1500) | Calibrated Elo |
| --- | :-: | :-: | :-: | ---: |
| **Strategy1** | 11-1-0 (0.917) | 10-2-0 (0.833) | 3-5-4 (0.417) | **1447** [1319, 1576] |
| **OneShotOpus** | 10-2-0 (0.833) | 2-7-3 (0.292) | 2-7-3 (0.292) | **1212** [1097, 1327] |
| **TDD** | 2-6-4 (0.333) | 0-10-2 (0.083) | 0-11-1 (0.042) | **863** [737, 990] |
| **chess-ttt** | 1-8-3 (0.208) | 0-12-0 (0.000) | 0-11-1 (0.042) | **779** [615, 943] |

**Strategy1** (post-upgrade calibration) scores heavily against SF-1 and SF-3 at 80 ms, then **SF-5** pulls the combined estimate back toward realism (still a strong net). **OneShotOpus** remains clearly above the two lighter engines but below Strategy1 on both anchors and combined Elo.

*TDD and chess-ttt anchor blocks are from earlier calibration runs (same protocol); Strategy1 and OneShotOpus anchor rows above match current `results.json`.*

---

## 5. Cross-Validation Matrix

Cells: **row vs column**, `W-L-D` from the **row** engine’s perspective (10 games).

| | OneShotOpus | Strategy1 | TDD | chess-ttt |
| --- | :-: | :-: | :-: | :-: |
| **OneShotOpus** | — | 0-4-6 | 8-0-2 | 10-0-0 |
| **Strategy1** | 4-0-6 | — | 10-0-0 | 10-0-0 |
| **TDD** | 0-8-2 | 0-10-0 | — | 5-0-5 |
| **chess-ttt** | 0-10-0 | 0-10-0 | 0-5-5 | — |

**Takeaways**

- **Strategy1 vs OneShotOpus:** no losses, four wins, six draws — confirms Strategy1 &gt; OneShotOpus at this TC in direct play (aligned with +235 Elo from anchors).
- **OneShotOpus** still dominates **TDD** and **chess-ttt** (same as before).
- **TDD vs chess-ttt:** 5-0-5 — even on wins, TDD ahead on calibration by ~84 Elo.

---

## 6. Cross-Val vs Calibration (sanity check)

Approximate **row** score \(S = (W + 0.5D) / 10\) and implied \(\Delta E \approx 400 \log_{10}(S/(1-S))\) for the row player vs column:

| Matchup (row vs col) | \(S\) | Implied \(\Delta\) (row − col) | Anchor \(\Delta\) (row − col) |
| --- | :-: | ---: | ---: |
| Strategy1 vs OneShotOpus | 0.70 | ~+148 | +235 |
| OneShotOpus vs TDD | 0.90 | ~+382 | +349 |
| Strategy1 vs TDD | 1.00 | large (shutout) | +584 |
| TDD vs chess-ttt | 0.50 | ~0 | +84 |

The Strategy1–OneShotOpus H2H implies a smaller gap than the anchor blend; that is normal for **10 games** (wide sampling error) plus possible style effects. The **direction** (Strategy1 ahead) is stable.

---

## 7. What Each Engine Does (current)

### `Strategy1` — 1447 Elo

**Codebase:** `Strategy1/engines/mve/` — shared **search core** (`search.py`: PVS, iterative deepening, aspiration windows, TT, null-move, LMR, killers, history, quiescence with delta pruning) plus swappable **personalities** in `heuristics.py`.

**Upgrade that changed results:** Arena entry now uses the **`pesto`** personality (tapered PeSTO PSTs) instead of **`positional_grinder`** (material + center only). UCI keeps **one `Searcher` per session** so the **transposition table and killer/history tables persist between moves**; `ucinewgame` clears them. **Time management** uses a soft stop (~86% of budget) and a hard deadline (~97%), with early exit when too little time remains for another full iteration. **TT mate scores** are stored/loaded with ply correction; quiescence includes **quiet queen promotions**.

Net: Strategy1 and OneShotOpus are now in the **same league** architecturally; Strategy1’s configuration and persistence pushed it ahead at **80 ms** in this harness.

### `OneShotOpus` — 1212 Elo

Single-instruction-style build: `engine.py` + `search.py` + `evaluation.py`. Negamax, TT, quiescence, null-move, LMR, killers, history, tapered PeSTO, solid UCI time handling. **Anchors not re-run** in the same session as Strategy1’s last calibration; `graded_at` on file may predate the new Strategy1 cross-val — only the **Strategy1 ↔ OneShotOpus** H2H block was refreshed when cross-validation was re-run.

### `test-driven-development` — 863 Elo

TDD workflow; simpler search (iterative deepening, lighter eval). **Cross-val vs Strategy1** is now **0-10-0** (earlier run had many draws vs a weaker Strategy1 configuration).

### `chess-ttt` — 779 Elo

Scaled minimal search from the TTT/checkers line; weak at 80 ms against any engine with TT + quiescence + strong eval. **0-10-0** vs both Strategy1 and OneShotOpus in this matrix.

---

## 8. Methodological Ranking (revised headline)

| Lineage | Calibrated Elo | Note |
| --- | ---: | --- |
| **Strategy1** (Darwinian repo + **PeSTO** + persistent TT) | 1447 | Same *class* of engine as a strong one-shot build once eval and session state match. |
| **One-shot Opus** (OneShotOpus) | 1212 | Still the cleanest “single prompt → shipped stack” reference. |
| **TDD** | 863 | Tests help legality and structure, not search depth. |
| **TTT scaling → chess** | 779 | Abstraction without chess-specific search/eval hits a ceiling early. |

**Headline:** at this time control, **configuration and session-wide search state matter as much as “which folder the code came from.”** Strategy1 overtook OneShotOpus after **PeSTO + persistent TT + time budget** alignment, not after replacing the search algorithm wholesale.

---

## 9. Timeline (this report’s data)

1. Earlier same day: OneShotOpus calibrated; cross-val vs prior Strategy1, TDD, chess-ttt.
2. **Strategy1 code path updated:** `run.sh` → `pesto`, `-u`; UCI **persistent `Searcher`**; search fixes (TT mate, qsearch promos, time split).
3. **Strategy1** recalibrated: **36 games** vs anchors (12 each), 80 ms → **1447** Elo.
4. **Cross-validation** re-run for the four engines (10 games / pair where missing): new **Strategy1** rows vs OneShotOpus, TDD, chess-ttt; other pairs unchanged if already present in `results.json`.
5. This document replaced the previous 4-engine snapshot (Strategy1 at ~911 Elo, OneShotOpus ranked first).

---

## 10. Files & Where to Look

| Path | Role |
| --- | --- |
| `elo-test/arena.py` | Match runner |
| `elo-test/grade.py` | Calibration + cross-val orchestration |
| `Strategy1/results.json` | Strategy1 anchors, Elo, cross-val |
| `OneShotOpus/results.json` | OneShotOpus anchors, Elo, cross-val |
| `src/test-driven-development/results.json` | TDD |
| `ttt-iteration_bot/chess-ttt/results.json` | chess-ttt |
| `Strategy1/engine/run.sh` | Launches `engines/mve/engine.py --heuristic pesto` |

---

## 11. Caveats

- **10-game** H2H has large error bars; shutouts (10-0) are informative, but **4-0-6** should be read as “clear edge,” not exact Elo difference.
- **80 ms** favors engines that return a stable depth quickly and use hash well — rankings can shift at longer `movetime`.
- Stockfish **skill** levels are not full Elo-matched opponents; treat anchor labels as **consistent yardsticks**, not FIDE truth.
- **TDD / chess-ttt** calibrations were not all re-run in lockstep with Strategy1’s latest anchor session; cross-val against Strategy1 **is** current for those six games each.
