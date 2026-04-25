# Four-Engine Chess Elo Evaluation — Final Report

> Scope: calibrate and compare four chess engines — `SimpleOneShot_bot`, `test-driven-development`, `chess-ttt`, and `megaprompt` — within a single repeatable arena, recover an absolute Elo rating for each, and cross-check those ratings against head-to-head play. Includes the full equations used, what the cross-validation numbers actually mean (and don't mean), and the bug fix applied to `megaprompt` along the way.

---

## 1. Engines under test

| Engine | Location | Entry point | Short description |
| --- | --- | --- | --- |
| `SimpleOneShot_bot` | `SimpleOneShot_bot/` | `engine/run.sh` | Negamax-alphabeta with PVS, iterative deepening, transposition table, quiescence, null-move pruning, LMR, check extensions, killer + history heuristics, tapered PeSTO eval. |
| `test-driven-development` | `src/test-driven-development/` | `engine/run.sh` | TDD-authored negamax engine with basic ordering and PST eval. |
| `chess-ttt` | `ttt-iteration_bot/chess-ttt/` | `engine/run.sh` | Iteration from the tic-tac-toe / checkers lineage (search-agnostic core, extended for chess). |
| `megaprompt` | `src/megaprompt/` | `engine/run.sh` | Minimal negamax + PeSTO eval, no TT, no pruning tricks. **Originally buggy** (see §7). |

All four engines speak UCI over stdin/stdout and are discovered by the grader via the `<dir>/engine/run.sh` convention.

---

## 2. Arena setup (the physical substrate)

Defined in `elo-test/arena.py` and called by `elo-test/grade.py`.

- **Resource limits per engine process:** `RLIMIT_AS = 512 MB` (virtual memory cap enforced via `resource.setrlimit` in a `preexec_fn`).
- **Move time cap:** `movetime = 80 ms` per move for this run. A **hard wall-clock ceiling of 2.0 s** per move is enforced by the arena regardless of what the engine is sent; overshooting = lost on time.
- **Opening book:** 8 balanced opening positions (startpos, Sicilian, French, Modern, Open Game, English, Queen's Gambit, Caro-Kann). Each pair cycles through them.
- **Color alternation:** engines swap colors every game (odd games → A is White, even → A is Black) so opening color bias cancels over enough games.
- **Per-game outcomes:** the arena prints `Game N/M: [W|B|D] <result>` (letter is the *winner's color*, `D` = draw) and a final `Final: {W}W-{L}L-{D}D` summary from A's perspective.
- **Memory isolation:** PGNs are written under `pgns/`; engines that crash or return illegal moves are logged but do not poison other matchups.

---

## 3. Stockfish anchors (why calibration is absolute, not relative)

The grader does *not* start everyone at 1200 and let them drift. Instead it reaches for an external ground truth: three Stockfish skill levels pegged to hand-chosen Elo values.

```python
ANCHORS = {
    1: 1000.0,   # Stockfish skill 1  → ~1000 Elo
    3: 1200.0,   # Stockfish skill 3  → ~1200 Elo
    5: 1500.0,   # Stockfish skill 5  → ~1500 Elo
}
```

These base Elos are the scaffolding — the `StockfishWrapper` in `grade.py` spins up a Stockfish process and injects `setoption name Skill Level value <n>` right after `uci`. Each candidate plays one matchup against each anchor.

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

For example, scoring 0.25 vs the 1200-Elo anchor gives ΔElo = `-400·log10(1/0.25 − 1) = -400·log10(3) ≈ -190.8`, so the candidate is at about **1009 Elo** on that one anchor.

### 4.4. Propagating the error from score-space to Elo-space

Elo is nonlinear in score, so we use the delta method:

$$\frac{dE}{ds} = \frac{400}{\ln(10)\cdot s\,(1 - s)}$$

$$\mathrm{SE}(\hat{E}_i) = \mathrm{SE}(s) \cdot \frac{400}{\ln(10)\cdot s\,(1-s)}$$

This gives a per-anchor uncertainty that correctly inflates when scores approach 0 or 1 (where a single extra win can swing Elo by hundreds of points).

### 4.5. Combining multiple anchors (inverse-variance weighting)

With three anchor estimates $\hat{E}_1, \hat{E}_2, \hat{E}_3$ and their errors $\mathrm{SE}_1, \mathrm{SE}_2, \mathrm{SE}_3$:

$$w_i = \frac{1}{\mathrm{SE}_i^2}, \qquad E_{\text{final}} = \frac{\sum_i w_i \hat{E}_i}{\sum_i w_i}$$

$$\mathrm{SE}_{\text{final}} = \frac{1}{\sqrt{\sum_i w_i}}, \qquad \text{95% CI} = E_{\text{final}} \pm 1.96 \cdot \mathrm{SE}_{\text{final}}$$

Inverse-variance weighting is optimal (minimum-variance unbiased) when the estimates are independent and approximately Gaussian. The practical effect: an anchor where the engine went 0-12-0 gets almost no weight because `s·(1-s)` blows up the SE; an anchor with a mix of outcomes gets most of the weight.

---

## 5. Cross-validation — what it does and does NOT do

After calibration, `grade.py --cross-validate` runs head-to-head matchups between every pair of registered engines. **Critically, it does not update any engine's `elo`, `elo_ci_lower`, or `elo_ci_upper`.** It only writes into the `cross_validation` field of each engine's `results.json`:

```json
"cross_validation": {
  "chess-ttt": {"wins": 9, "losses": 0, "draws": 1, "total": 10}
}
```

The Elo comes **entirely** from the Stockfish anchors (§4). Cross-validation is a **sanity check**: given the calibrated Elos, the logistic model predicts each pair's score as

$$E_A = \frac{1}{1 + 10^{(E_B - E_A)/400}}$$

We then ask whether the observed score matches. Large discrepancies flag either (a) a miscalibrated engine, (b) non-transitive pairings (A's style exploits B but not C), or (c) small-sample noise — at 10 games per pair the 1-σ noise is already ±150 Elo in the implied-gap space.

In other words: **the arena is a validation tool, not a ladder**. No ratings drift.

---

## 6. Calibration and cross-validation parameters for this run

| Parameter | Value |
| --- | --- |
| Candidates | `SimpleOneShot_bot`, `test-driven-development`, `chess-ttt`, `megaprompt` |
| Stockfish anchors | skill 1 (1000), skill 3 (1200), skill 5 (1500) |
| Games per anchor | 12 (36 per candidate × 4 candidates = **144 calibration games**) |
| Cross-validation pairs | all 6 unordered pairs |
| Games per cross-val pair | 10 (60 **cross-validation games**) |
| Movetime per move | **80 ms** |
| Hard wall clock per move | 2.0 s |
| Memory ceiling per engine | 512 MB |
| Total arena games | **204** |
| Wall clock | ≈30 min for full run; ≈10 min for the megaprompt-only rerun |

---

## 7. The `megaprompt` bug — diagnosis and fix

### 7.1. Symptoms

UCI conformance (`elo-test/test_engine.py`) on `megaprompt` was failing **20/20 random-position legality checks**. In actual matches, megaprompt would regularly lose on time and occasionally emit illegal moves. The initial calibration gave it an Elo of **518** with a 95% CI of **[285, 752]** — a width of 467 Elo, which signals an engine whose scores against the anchors were so extreme (essentially 0-all) that the delta method blew up the standard error.

### 7.2. Root cause

In `src/megaprompt/engine/engine.py`, the `search()` method literally ignored the UCI time control:

```python
def search(self, cmd):
    ...
    depth = 3                              # hardcoded
    if "depth" in cmd:
        depth = int(cmd[cmd.index("depth") + 1])

    for move in moves:                     # full depth-3 root loop
        ...
```

`go movetime 80` was silently dropped. A full depth-3 negamax in a busy middlegame position easily takes far more than 80 ms — often more than the arena's 2-second hard ceiling — and the arena then records a loss on time (and/or an illegal fallback move).

### 7.3. Fix (three surgical edits)

1. **Module-level deadline + `SearchAborted` exception.**

    ```python
    _search_deadline = 0.0
    class SearchAborted(Exception): ...
    def _time_is_up(): return time.time() >= _search_deadline
    ```

2. **Time checks inside the search.** `negamax` and `quiescence_search` check the deadline once every 2048 nodes (cheap bitmask `nodes & 2047 == 0`) and raise `SearchAborted` to bail out cleanly.

3. **Root rewrite — proper iterative deepening.** `search()` now parses `movetime`, `wtime`/`btime`/`winc`/`binc`, and `depth` from the `go` command, computes a budget (`movetime_ms` directly, or `my_clock/30 + my_inc`, or 1.0 s for bare `go`), keeps **85% of the budget in reserve** for safety, and deepens one ply at a time. It commits a new `best_move` *only* when an iteration completes fully, so an aborted partial iteration never regresses the returned move. A fast path returns immediately when there is exactly one legal move.

Also added `flush=True` to the UCI handshake prints so the fix is robust even without `python -u`.

### 7.4. Verification

- UCI conformance: **6/6 PASS** (was 5/6 — the 20 random-position legality check now passes, was 0/20).
- Direct UCI probe on startpos with `go movetime 80`: completes depths 1/2/3 in 22 ms, returns `bestmove g1f3`.
- Direct UCI probe on a busy middlegame FEN with `go movetime 80`: completes depth 1 in 11 ms, depth 2 aborts cleanly, returns the depth-1 best. No illegal moves, no timeouts.

### 7.5. Before vs after (megaprompt only)

| Metric | Before fix | After fix | Δ |
| --- | ---: | ---: | ---: |
| UCI random-position legality | 0/20 | 20/20 | +20 |
| Calibrated Elo | 518 | **694** | **+176** |
| 95% CI | [285, 752] | [524, 864] | width 467 → 340 |
| Anchor record vs SF-1 | (forfeits) | 0-10-2 | meaningful signal |
| H2H vs test-driven-development | near-zero | 1-3-6 (40%) | competitive |
| H2H vs chess-ttt | near-zero | 1-5-4 (30%) | close |
| H2H vs SimpleOneShot_bot | near-zero | 0-9-1 (5%) | as predicted |

The remaining performance gap is now **real playing strength**, not a forfeit artifact — megaprompt only reaches depth 2-3 at 80 ms because it lacks a transposition table, null-move pruning, PVS/LMR, and tapered eval.

---

## 8. Final results

### 8.1. Calibration table

| Rank | Engine | Elo | 95% CI | vs SF-1 (W-L-D) | vs SF-3 | vs SF-5 |
| ---: | --- | ---: | --- | :---: | :---: | :---: |
| 1 | `SimpleOneShot_bot` | **1195** | [1087, 1303] | 9-2-1 | 4-6-2 | 0-8-4 |
| 2 | `test-driven-development` | **863** | [737, 990] | 2-6-4 | 0-10-2 | 0-11-1 |
| 3 | `chess-ttt` | **779** | [615, 943] | 1-8-3 | 0-12-0 | 0-11-1 |
| 4 | `megaprompt` (fixed) | **694** | [524, 864] | 0-10-2 | 0-11-1 | 0-11-1 |

`SimpleOneShot_bot` is the only engine in this set that plays competitively with Stockfish skill 3; it *beats* SF-1 and splits SF-3. The other three are all below the weakest anchor.

### 8.2. Cross-validation matrix (A-perspective, 10 games per pair)

Reading row A vs column B as `W-L-D` for A:

|                             | SimpleOneShot | TDD | chess-ttt | megaprompt |
| --- | :---: | :---: | :---: | :---: |
| `SimpleOneShot_bot`         |    —     | 9-1-0 | 9-0-1 | 9-0-1 |
| `test-driven-development`   | 1-9-0 |    —     | 5-0-5 | 3-1-6 |
| `chess-ttt`                 | 0-9-1 | 0-5-5 |    —     | 5-1-4 |
| `megaprompt`                | 0-9-1 | 1-3-6 | 1-5-4 |    —     |

### 8.3. Prediction vs observation

Using $E_A = 1/(1 + 10^{(E_B - E_A)/400})$ with the calibrated Elos above, and the implied Elo gap from an observed score of $400\cdot\log_{10}((1-s)/s)$:

| Pair (A vs B) | Cal. ΔE (B−A) | Predicted $E_A$ | Observed $s_A$ | Implied ΔE from play | Residual |
| --- | ---: | ---: | ---: | ---: | ---: |
| TDD vs SimpleOneShot        | +332 | 0.129 | 0.100 |  +382 |  +50  |
| chess-ttt vs SimpleOneShot  | +416 | 0.084 | 0.050 |  +512 |  +96  |
| megaprompt vs SimpleOneShot | +501 | 0.053 | 0.050 |  +512 | **+11** |
| TDD vs chess-ttt            |  −84 | 0.619 | 0.750 |  −191 | −107 |
| TDD vs megaprompt           | −169 | 0.726 | 0.600 |   −70 |  +99 |
| chess-ttt vs megaprompt     |  −85 | 0.620 | 0.700 |  −147 |  −62 |

**Interpretation:**

- The `megaprompt` vs `SimpleOneShot_bot` prediction is almost exactly right (residual 11 Elo), which suggests both endpoints of the ladder are well-calibrated despite megaprompt's wide CI.
- The mid-table three-way between TDD / chess-ttt / megaprompt has larger residuals (up to ±107 Elo). That is within the 1-σ shot noise of a 10-game sample (≈150 Elo at a score of 0.5), so I would *not* reorder anyone on that evidence.
- The clearest real signal in the residuals is that `test-driven-development` and `chess-ttt` both **overperform their calibration against megaprompt** (+99 and +62 Elo respectively), suggesting megaprompt's true strength is probably near the *top* of its CI rather than its point estimate, i.e. closer to 800 Elo than 694. That tracks — an engine that finishes every Stockfish matchup 0-11-1 saturates the logit and produces an optimistically low point estimate.

### 8.4. What this means for "do the matches change the Elos?"

**No.** The final Elos in §8.1 are fixed by the Stockfish calibration; the cross-validation numbers in §8.2 are diagnostic only. If I wanted a ladder that *does* update after head-to-head games, the right move would be a Bayesian-updating implementation (e.g. BayesElo / Ordo / Davidson trinomial likelihood) that takes the calibration priors and conditions on the cross-validation outcomes. That's not what `grade.py` does today.

---

## 9. Timeline of what I did

1. **Wire up `SimpleOneShot_bot` for the arena.** Wrote `SimpleOneShot_bot/engine/run.sh` that `exec`s `.venv/bin/python engine.py` so `python-chess` is available regardless of what `python3` is on PATH.
2. **Extend engine discovery.** Added a `DIRECT_ENGINES` list to `grade.py` so top-level engine folders (`SimpleOneShot_bot/`, `Strategy1/`) are scanned the same way `src/<name>/` and `ttt-iteration_bot/<name>/` are.
3. **Add an `--only` filter** to `grade.py`. Restricts a run to a comma-separated set of engine names so I could re-run just `megaprompt` without touching the other three engines' data.
4. **Make the grader resilient.** `results.json` is now written after *every* Stockfish anchor matchup completes (not just at the end), so an interrupted run never loses more than one anchor's worth of games.
5. **Fix the `arena.py` subprocess launch** in `grade.py` to use `sys.executable -u` instead of a raw `python3`, so the child process gets the same venv (fixes `ModuleNotFoundError: No module named 'chess'`) and unbuffered output.
6. **Rewrite the `run_matchup` output parser** to understand the arena's actual `Game N/M: [W|B|D]` format (was looking for `[+] / [-] / [=]`, which the arena never prints) and the `Final: {W}W-{L}L-{D}D` summary line, with color-alternation tracking so outcomes are recorded from engine A's perspective.
7. **Fix `.venv` interpreter in engine run.sh scripts** for `src/test-driven-development`, `src/megaprompt`, and `ttt-iteration_bot/chess-ttt`. Added `-u` to `megaprompt`'s launcher so `print()` without `flush=True` wouldn't deadlock the UCI handshake.
8. **Repo hygiene.** Added a comprehensive `.gitignore` (Python bytecode, `.DS_Store`, venvs, pytest caches, scratch `.tmp_stockfish/`), then `git rm -r --cached` the previously-tracked `__pycache__/` and `.DS_Store` files.
9. **Full calibration + cross-validation for all four engines.** 144 calibration games + 60 cross-validation games, ≈30 min wall clock at `movetime=80`.
10. **Diagnose megaprompt.** Ran the failing UCI tests, traced to the hardcoded `depth = 3` and the missing `movetime` handling.
11. **Fix megaprompt** (§7.3): module-level deadline, `SearchAborted`, time checks every 2048 nodes in `negamax` + `quiescence_search`, full iterative-deepening root with an 85% safety margin on the budget, forced-move fast path, explicit flushes.
12. **Re-run megaprompt only.** Wiped `src/megaprompt/results.json`; stripped only the `megaprompt` entry from the `cross_validation` field of the other three engines' result files (so the already-completed 3 non-megaprompt pairs were *not* re-run). Re-calibrated with 36 games × 3 anchors and re-ran cross-validation (3 pairs × 10 games). Total wall clock ≈10 min.
13. **Aggregate + write this report.**

---

## 10. Limitations and next steps

- **80 ms is a short time control.** At this budget `megaprompt` only reaches depth 2-3; `SimpleOneShot_bot`'s advantage comes largely from its pruning and TT letting it search deeper in the same wall-clock. Re-running at `movetime ∈ {200, 500, 1000}` would show how each engine scales with time and reduce the noise in the cross-validation residuals.
- **Three anchors, skill levels 1/3/5.** Stockfish skill level 5 (≈1500) already crushes the bottom three engines 0-11-1; adding a 900-Elo anchor (e.g. `UCI_LimitStrength` with a specific rating) would give the weak engines a non-saturating reference and tighten their CIs dramatically.
- **10 games per cross-validation pair** is noisy (1-σ ≈150 Elo near 50%). Bumping to 40+ games per pair would materially sharpen §8.3, at a roughly linear cost in wall clock.
- **`grade.py` could do Bayesian updating** after cross-validation to refine Elos with head-to-head data, rather than treating it purely as diagnosis. Would need care to handle the non-transitivity visible in the TDD/chess-ttt/megaprompt cluster.
- **megaprompt's search itself is still the weakest of the four** even with a correct time manager. The obvious next upgrades, in order of expected Elo gain per line of code: transposition table, move ordering by TT hit + MVV-LVA + killers, null-move pruning, LMR.
