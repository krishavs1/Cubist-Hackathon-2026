# Four-Engine Chess Elo Evaluation — Final Report

> **Scope (current):** calibrate and compare four engines — **`Strategy1`**, **`OneShotOpus`**, **`test-driven-development`**, and **`chess-ttt`** — in the shared `elo-test/` arena, report absolute Elo from Stockfish anchors, and cross-check with head-to-head play. This revision replaces an earlier edition that used `SimpleOneShot_bot` instead of `OneShotOpus` and predates the **Strategy1** upgrade (PeSTO + persistent TT + time budget fixes).  
> **Companion:** `FINAL_REPORT_4ENGINE.md` is a concise duplicate of the leaderboard, matrix, and engine blurbs for the same four engines.

---

## 1. Engines under test

| Engine | Location | Entry point | Short description |
| --- | --- | --- | --- |
| `Strategy1` | `Strategy1/` | `engine/run.sh` | Darwinian MVE: **PVS**, iterative deepening, aspiration windows, **TT**, null-move, **LMR**, killers, history, delta-pruned **quiescence**. Arena build uses **`pesto`** (tapered PeSTO PSTs), **persistent `Searcher`** (TT/killers/history survive between moves; cleared on `ucinewgame`), and tightened **movetime** usage (~86% soft / ~97% hard). |
| `OneShotOpus` | `OneShotOpus/` | `engine/run.sh` | One-shot Opus prompt: negamax + TT + quiescence + null-move + LMR + killers + history + tapered **PeSTO**; solid UCI time handling. |
| `test-driven-development` | `src/test-driven-development/` | `engine/run.sh` | TDD-authored engine: iterative deepening, lighter eval and search than the top two. |
| `chess-ttt` | `ttt-iteration_bot/chess-ttt/` | `engine/run.sh` | Lineage from tic-tac-toe → checkers → chess; minimal chess-specific search/eval. |

Discovery: `elo-test/grade.py` registers **`DIRECT_ENGINES`** at repo root (`Strategy1`, `OneShotOpus`, `SimpleOneShot_bot`, …) and scans **`ENGINE_ROOTS`** (`src/`, `ttt-iteration_bot/`, …) for `<name>/engine/run.sh`.

---

## 2. Arena setup (the physical substrate)

Defined in `elo-test/arena.py` and called by `elo-test/grade.py`.

- **Resource limits per engine process:** `RLIMIT_AS = 512 MB` (virtual memory cap enforced via `resource.setrlimit` in a `preexec_fn`).
- **Move time cap:** `movetime = 80 ms` per move for the runs summarized below. A **hard wall-clock ceiling of 2.0 s** per move is enforced by the arena regardless of what the engine is sent; overshooting = lost on time.
- **Opening book:** 8 balanced opening positions (startpos, Sicilian, French, Modern, Open Game, English, Queen's Gambit, Caro-Kann). Each pair cycles through them.
- **Color alternation:** engines swap colors every game (odd games → A is White, even → A is Black) so opening color bias cancels over enough games.
- **Per-game outcomes:** the arena prints `Game N/M: [W|B|D] <result>` (letter is the *winner's color*, `D` = draw) and a final `Final: {W}W-{L}L-{D}D` summary from **engine A’s** perspective.
- **Memory isolation:** PGNs are written under `pgns/`; engines that crash or return illegal moves are logged but do not poison other matchups.

---

## 3. Stockfish anchors (why calibration is absolute, not relative)

The grader does *not* start everyone at 1200 and let them drift. Instead it uses three Stockfish skill levels pegged to chosen Elo values.

```python
ANCHORS = {
    1: 1000.0,   # Stockfish skill 1  → ~1000 Elo
    3: 1200.0,   # Stockfish skill 3  → ~1200 Elo
    5: 1500.0,   # Stockfish skill 5  → ~1500 Elo
}
```

Each candidate plays one matchup block per anchor. `StockfishWrapper` injects `setoption name Skill Level value <n>` after `uci`.

---

## 4. How an Elo is computed (with equations)

All equations live in `fishtest_stats(w, l, d)` in `grade.py` and the "Recompute Absolute Elo" block. Below, `n = w + l + d`.

### 4.1. Empirical score and variance

Score is the standard chess convention (win = 1, draw = ½, loss = 0):

$$s = \frac{w + 0.5\,d}{n}$$

Because outcomes are trinomial (W/D/L), the correct point variance is:

$$\mathrm{Var}(s) = \frac{w}{n}(1 - s)^2 + \frac{d}{n}(0.5 - s)^2 + \frac{l}{n}(0 - s)^2$$

And the standard error of the mean score:

$$\mathrm{SE}(s) = \sqrt{\frac{\mathrm{Var}(s)}{n}}$$

The code clamps `s` into `[0.0001, 0.9999]` to keep the logit defined when an engine scores 0% or 100%.

### 4.2. Score → Elo difference

Bradley-Terry / logistic Elo:

$$\Delta\mathrm{Elo} = -400 \cdot \log_{10}\!\left(\frac{1}{s} - 1\right)$$

This is the signed Elo difference of the candidate *relative to the opponent*. Positive means the candidate is rated above the anchor.

### 4.3. Absolute Elo against one anchor

$$\hat{E}_i \;=\; E_{\mathrm{anchor},i} + \Delta\mathrm{Elo}_i$$

### 4.4. Propagating the error from score-space to Elo-space

Elo is nonlinear in score, so we use the delta method:

$$\frac{dE}{ds} = \frac{400}{\ln(10)\cdot s\,(1 - s)}$$

$$\mathrm{SE}(\hat{E}_i) = \mathrm{SE}(s) \cdot \frac{400}{\ln(10)\cdot s\,(1-s)}$$

### 4.5. Combining multiple anchors (inverse-variance weighting)

With three anchor estimates $\hat{E}_1, \hat{E}_2, \hat{E}_3$ and their errors $\mathrm{SE}_1, \mathrm{SE}_2, \mathrm{SE}_3$:

$$w_i = \frac{1}{\mathrm{SE}_i^2}, \qquad E_{\text{final}} = \frac{\sum_i w_i \hat{E}_i}{\sum_i w_i}$$

$$\mathrm{SE}_{\text{final}} = \frac{1}{\sqrt{\sum_i w_i}}, \qquad \text{95% CI} = E_{\text{final}} \pm 1.96 \cdot \mathrm{SE}_{\text{final}}$$

---

## 5. Cross-validation — what it does and does NOT do

After calibration, `grade.py --cross-validate` runs head-to-head matchups between pairs of engines. **It does not update** any engine's `elo`, `elo_ci_lower`, or `elo_ci_upper`. It only writes the `cross_validation` field in each engine's `results.json`.

The Elo comes **entirely** from the Stockfish anchors (§4). Cross-validation is a **sanity check** on relative strength and style. At **10 games per pair**, implied gaps have large sampling error (often ±150 Elo or more near 50% scores).

---

## 6. Calibration and cross-validation parameters (this snapshot)

| Parameter | Value |
| --- | --- |
| Engines in leaderboard | `Strategy1`, `OneShotOpus`, `test-driven-development`, `chess-ttt` |
| Stockfish anchors | skill 1 (1000), skill 3 (1200), skill 5 (1500) |
| Games per anchor (full calibration) | **12** per anchor → **36** games per engine when all three anchors are run |
| Cross-validation | **10** games per unordered pair (among engines selected in a `--only` run) |
| Movetime per move | **80 ms** |
| Hard wall clock per move | 2.0 s |
| Memory ceiling per engine | 512 MB |

**Note:** `Strategy1` anchors and Elo were **recomputed** after the engine upgrade (same protocol). `OneShotOpus`, `test-driven-development`, and `chess-ttt` anchor blocks in `results.json` may carry **older `graded_at` timestamps**; cross-validation involving **Strategy1** was re-run so Strategy1 ↔ others H2H counts match the matrix in §8.

---

## 7. Harness setup — the shared `.venv` launcher

### 7.1. The problem

Engines must launch with a Python that has **`python-chess`** and (for some codebases) **Python ≥ 3.10**. Using system `python3` or the wrong venv produced `ModuleNotFoundError: No module named 'chess'` or syntax errors.

### 7.2. The fix

Repo-root `.venv` with `python-chess`, and `grade.py` invoking `arena.py` via **`sys.executable -u`**. Each engine’s `engine/run.sh` should prefer **`$REPO_ROOT/.venv/bin/python`** (several engines also use **`python -u`** for unbuffered UCI).

### 7.3. UCI smoke identifiers (examples)

| Engine | Example `id name` |
| --- | --- |
| `Strategy1/engine/run.sh` | `CubistDarwin-pesto` (when launched with `--heuristic pesto`) |
| `OneShotOpus/engine/run.sh` | `OneShotOpus 1.0` |
| `src/test-driven-development/engine/run.sh` | (engine’s declared name) |
| `ttt-iteration_bot/chess-ttt/engine/run.sh` | (engine’s declared name) |

### 7.4. Stockfish

`grade.py` `ensure_stockfish()` locates or installs Stockfish; skill levels are set through the wrapper’s UCI shim.

---

## 8. Final results (current four engines)

### 8.1. Calibration table

| Rank | Engine | Elo | 95% CI | vs SF-1 (W-L-D) | vs SF-3 | vs SF-5 |
| ---: | --- | ---: | --- | :---: | :---: | :---: |
| 1 | `Strategy1` | **1447** | [1319, 1576] | 11-1-0 | 10-2-0 | 3-5-4 |
| 2 | `OneShotOpus` | **1212** | [1097, 1327] | 10-2-0 | 2-7-3 | 2-7-3 |
| 3 | `test-driven-development` | **863** | [737, 990] | 2-6-4 | 0-10-2 | 0-11-1 |
| 4 | `chess-ttt` | **779** | [615, 943] | 1-8-3 | 0-12-0 | 0-11-1 |

**Strategy1** at 80 ms now scores heavily against SF-1 and SF-3; **SF-5** still anchors the high end and pulls the combined estimate down from the mid-anchor ceiling. **OneShotOpus** remains clearly above TDD and chess-ttt but below Strategy1 on this snapshot.

### 8.2. Cross-validation matrix (row vs column, 10 games; row’s W-L-D)

| | OneShotOpus | Strategy1 | TDD | chess-ttt |
| --- | :---: | :---: | :---: | :---: |
| **OneShotOpus** | — | 0-4-6 | 8-0-2 | 10-0-0 |
| **Strategy1** | 4-0-6 | — | 10-0-0 | 10-0-0 |
| **TDD** | 0-8-2 | 0-10-0 | — | 5-0-5 |
| **chess-ttt** | 0-10-0 | 0-10-0 | 0-5-5 | — |

**Ordinal:** calibration says **Strategy1 > OneShotOpus > TDD > chess-ttt**. Cross-val agrees on **Strategy1 vs OneShotOpus** (Strategy1 ahead), **OneShotOpus vs the bottom two**, and **TDD vs chess-ttt** (TDD ahead on wins, 5-0-5).

### 8.3. Prediction vs observation (illustrative)

Using $E_A = 1/(1 + 10^{(E_B - E_A)/400})$ with the §8.1 point Elos:

| Pair (row vs col) | Cal. Δ (col − row) | Predicted $s_{\text{row}}$ | Observed $s_{\text{row}}$ |
| --- | ---: | ---: | ---: |
| Strategy1 vs OneShotOpus | −235 | ~0.79 | 0.70 |
| OneShotOpus vs TDD | −349 | ~0.89 | 0.90 |
| Strategy1 vs TDD | −584 | ~0.96 | 1.00 |
| TDD vs chess-ttt | +84 | ~0.38 | 0.50 |

Strategy1 vs OneShotOpus: observed score is **slightly below** the logistic prediction from anchor-only Elos — plausible for **10 games** and style variance. Shutouts (10-0) are informative but inflate implied gaps; treat as “large edge,” not a precise Elo difference.

### 8.4. Do the matches change the Elos?

**No.** §8.1 Elos come only from anchor calibration. §8.2 is diagnostic.

---

## 9. Timeline (high level)

1. **Harness:** `grade.py` engine discovery (`DIRECT_ENGINES`, `ENGINE_ROOTS`), `--only`, incremental `results.json` writes, `sys.executable -u` for `arena.py`, outcome parsing for `[W]/[B]/[D]` and `Final:`.
2. **OneShotOpus** integrated as a direct engine; calibrated and cross-validated vs peers.
3. **Strategy1 upgrade:** `run.sh` switched to **`pesto`**; UCI uses one **`Searcher`** per session (persistent TT / killers / history); **time budget** and **TT mate** / **qsearch promotion** fixes in `search.py`.
4. **Strategy1** recalibrated (36 games, 80 ms); **cross-validation** refreshed for pairs involving Strategy1 alongside the other three engines.
5. **Reports:** `FINAL_REPORT_4ENGINE.md` and this file updated to the four-engine lineup and numbers above.

---

## 10. Limitations and next steps

- **80 ms** is a very fast control; rerun at 200–1000 ms to see scaling and shrink noise.
- **Anchor skill levels** are not literal FIDE ratings; use them as **consistent relative yardsticks**.
- **10 games per H2H pair** is noisy; 40+ games per pair would tighten §8.3.
- **Recalibrate all four in one batch** if you need perfectly aligned `graded_at` timestamps and identical session conditions for every anchor block.
- **Optional:** a second stage (e.g. BayesElo) that updates beliefs from H2H data — not implemented in `grade.py` today.
