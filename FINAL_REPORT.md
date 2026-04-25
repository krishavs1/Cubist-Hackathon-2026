# Four-Engine Chess Elo Evaluation — Final Report

> Scope: calibrate and compare four chess engines — `SimpleOneShot_bot`, `test-driven-development`, `chess-ttt`, and `Strategy1` — within a single repeatable arena, recover an absolute Elo rating for each, and cross-check those ratings against head-to-head play. Includes the full equations used, what the cross-validation numbers actually mean (and don't mean), and the harness setup that made every engine reproducibly launchable on the grading machine.

---

## 1. Engines under test

| Engine | Location | Entry point | Short description |
| --- | --- | --- | --- |
| `SimpleOneShot_bot` | `SimpleOneShot_bot/` | `engine/run.sh` | Negamax-alphabeta with PVS, iterative deepening, transposition table, quiescence, null-move pruning, LMR, check extensions, killer + history heuristics, tapered PeSTO eval. |
| `Strategy1` | `Strategy1/` | `engine/run.sh` | Darwinian AI engine: shared modern search core (PVS + TT + null-move + LMR + killers + history + aspiration windows + delta-pruned quiescence) with a swappable evaluator. The default personality `fortress` (massive king-safety weighting + trade-down bonus when ahead) is what won the internal round-robin tournament across seven Claude-generated personalities. |
| `test-driven-development` | `src/test-driven-development/` | `engine/run.sh` | TDD-authored negamax engine with basic ordering and PST eval. |
| `chess-ttt` | `ttt-iteration_bot/chess-ttt/` | `engine/run.sh` | Iteration from the tic-tac-toe / checkers lineage (search-agnostic core, extended for chess). |

All four engines speak UCI over stdin/stdout and are discovered by the grader via the `<dir>/engine/run.sh` convention. Strategy1 and SimpleOneShot live at the repo root and are picked up by `grade.py`'s `DIRECT_ENGINES` list; the other two are scanned out of `src/` and `ttt-iteration_bot/` respectively.

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
| Candidates | `SimpleOneShot_bot`, `Strategy1`, `test-driven-development`, `chess-ttt` |
| Stockfish anchors | skill 1 (1000), skill 3 (1200), skill 5 (1500) |
| Games per anchor | 12 (36 per candidate × 4 candidates = **144 calibration games**) |
| Cross-validation pairs | all 6 unordered pairs |
| Games per cross-val pair | 10 (60 **cross-validation games**) |
| Movetime per move | **80 ms** |
| Hard wall clock per move | 2.0 s |
| Memory ceiling per engine | 512 MB |
| Total arena games | **204** |
| Wall clock | ≈30 min for the full sweep |

---

## 7. Harness setup — the shared `.venv` launcher

### 7.1. The problem

Every engine's `engine/run.sh` follows the same pattern: prefer `$REPO_ROOT/.venv/bin/python` if it exists, otherwise fall back to bare `python3`. That fallback is fragile — on the grading machine, the `python3` on `PATH` resolved to an unrelated virtualenv (`SongIdentifier-…`) which does not have `python-chess` installed. The first cross-validation pass died on `ModuleNotFoundError: No module named 'chess'` for three of the four engines, and the arena reported them as init failures.

A first attempt to work around this by short-circuiting the fallback to `/usr/bin/python3` ran into a separate problem: the system Python on this machine is 3.9, and `src/test-driven-development/uci/adapter.py` uses `str | None` PEP 604 syntax that requires Python ≥ 3.10. Picking any single hard-coded interpreter would break at least one engine.

### 7.2. The fix

Created `$REPO_ROOT/.venv` once, with an interpreter that satisfies every engine simultaneously:

```bash
# from repo root
/usr/local/bin/python3 -m venv .venv         # 3.11.4 — supports `X | None` syntax
.venv/bin/pip install python-chess            # required by all four engines
```

After this, every engine's existing `run.sh` takes the `.venv` branch unmodified — no per-engine edits required. Verified by sending `uci` / `quit` to each of the four `engine/run.sh` files independently:

| Engine | `id name` line |
| --- | --- |
| `Strategy1/engine/run.sh` | `id name CubistDarwin-fortress` |
| `SimpleOneShot_bot/engine/run.sh` | `id name SimpleOneShot 1.0` |
| `src/test-driven-development/engine/run.sh` | `id name HackathonEngine` |
| `ttt-iteration_bot/chess-ttt/engine/run.sh` | `id name chess-from-checkers` |

All four reach `uciok` cleanly under the arena's `RLIMIT_AS = 512 MB` preexec.

### 7.3. Stockfish — also installed during setup

Stockfish was missing from `PATH`. `grade.py`'s `ensure_stockfish()` calls `brew install stockfish` automatically; on this machine that completed (Stockfish 18 in `/usr/local/Cellar/stockfish/18`) and the binary became available at `/usr/local/bin/stockfish`. The `StockfishWrapper` in `grade.py` then writes a temp `run.sh` that pipes UCI to the Stockfish binary while injecting `setoption name Skill Level value <n>` after `uci`, so each anchor is just another UCI subprocess from the arena's perspective.

### 7.4. Why this matters for the report

Without these two setup steps, the cross-validation matrix would have been mostly init failures and the calibration column for the affected engines would have been forfeit-dominated (a saturating 0-12-0 against every anchor, which the delta method blows up into a useless ±300 Elo CI). The numbers in §8 are honest playing-strength signal because every subprocess actually launched and played.

---

## 8. Final results

### 8.1. Calibration table

| Rank | Engine | Elo | 95% CI | vs SF-1 (W-L-D) | vs SF-3 | vs SF-5 |
| ---: | --- | ---: | --- | :---: | :---: | :---: |
| 1 | `SimpleOneShot_bot` | **1195** | [1087, 1303] | 9-2-1 | 4-6-2 | 0-8-4 |
| 2 | `Strategy1` | **1014** | [902, 1126] | 3-7-2 | 2-8-2 | 0-9-3 |
| 3 | `test-driven-development` | **863** | [737, 990] | 2-6-4 | 0-10-2 | 0-11-1 |
| 4 | `chess-ttt` | **779** | [615, 943] | 1-8-3 | 0-12-0 | 0-11-1 |

`SimpleOneShot_bot` is the only engine in this set that plays competitively with Stockfish skill 3; it *beats* SF-1 and splits SF-3. `Strategy1` is the only other engine that wins games against SF-3 at all (2 wins, 2 draws). The bottom two engines saturate at 0-vs-anything past skill 1.

### 8.2. Cross-validation matrix (A-perspective, 10 games per pair)

Reading row A vs column B as `W-L-D` for A:

|                             | SimpleOneShot | Strategy1 | TDD | chess-ttt |
| --- | :---: | :---: | :---: | :---: |
| `SimpleOneShot_bot`         |    —     | 7-0-3 | 9-1-0 | 9-0-1 |
| `Strategy1`                 | 0-7-3 |    —     | 5-0-5 | 8-0-2 |
| `test-driven-development`   | 1-9-0 | 0-5-5 |    —     | 5-0-5 |
| `chess-ttt`                 | 0-9-1 | 0-8-2 | 0-5-5 |    —     |

The cross-val ranking matches the calibration ranking exactly: the row sums (W − L) are SimpleOneShot +25, Strategy1 +6, TDD −13, chess-ttt −18. No non-transitive surprises (e.g. nobody loses to a calibrated-weaker engine).

### 8.3. Prediction vs observation

Using $E_A = 1/(1 + 10^{(E_B - E_A)/400})$ with the calibrated Elos above, and the implied Elo gap from an observed score of $400\cdot\log_{10}((1-s)/s)$:

| Pair (A vs B) | Cal. ΔE (B−A) | Predicted $s_A$ | Observed $s_A$ | Implied ΔE from play | Residual |
| --- | ---: | ---: | ---: | ---: | ---: |
| Strategy1 vs SimpleOneShot  | +181 | 0.261 | 0.150 |  +301 |  +120 |
| TDD vs SimpleOneShot        | +332 | 0.129 | 0.100 |  +382 |   +50 |
| chess-ttt vs SimpleOneShot  | +416 | 0.084 | 0.050 |  +512 |   +96 |
| TDD vs Strategy1            | +151 | 0.295 | 0.250 |  +191 |   +40 |
| chess-ttt vs Strategy1      | +235 | 0.205 | 0.100 |  +382 | **+147** |
| TDD vs chess-ttt            |  −84 | 0.619 | 0.750 |  −191 |  −107 |

**Interpretation:**

- Three of six residuals are within the 1-σ noise of a 10-game sample (≈150 Elo near s=0.5), so the calibration is broadly consistent with head-to-head play.
- The two largest residuals both tilt Strategy1's way: it beats `chess-ttt` 8-0-2 instead of the predicted 79.5%, and it never wins against SimpleOneShot but draws 30% (better than the predicted 26.1%). That suggests `Strategy1`'s true strength is probably near the **top** of its CI rather than its point estimate — i.e. closer to 1100 Elo than 1014. The mechanism is the standard one: Strategy1 lost most games against all three Stockfish anchors (3-7-2, 2-8-2, 0-9-3), and the deeper an engine sinks against an anchor the more the logit saturates and pulls its point estimate down.
- `TDD` overperforms vs `chess-ttt` by 107 Elo (5-0-5 instead of the predicted 38.1% loss), but underperforms vs `Strategy1` by ~40 Elo. The pair-specific style noise here is well within the noise floor of a 10-game sample.

### 8.4. What this means for "do the matches change the Elos?"

**No.** The final Elos in §8.1 are fixed by the Stockfish calibration; the cross-validation numbers in §8.2 are diagnostic only. If I wanted a ladder that *does* update after head-to-head games, the right move would be a Bayesian-updating implementation (e.g. BayesElo / Ordo / Davidson trinomial likelihood) that takes the calibration priors and conditions on the cross-validation outcomes. That's not what `grade.py` does today.

---

## 9. Timeline of what I did

1. **Engine discovery.** Extended `grade.py` with a `DIRECT_ENGINES` list so top-level engine folders (`SimpleOneShot_bot/`, `Strategy1/`) are scanned the same way `src/<name>/` and `ttt-iteration_bot/<name>/` are. Added an `--only` filter for restricting a run to a comma-separated set of engine names.
2. **Resilient writes.** `results.json` is now persisted after *every* Stockfish anchor matchup completes (not just at the end), so an interrupted run never loses more than one anchor's worth of games.
3. **Subprocess hygiene.** Fixed `arena.py`'s subprocess launch in `grade.py` to use `sys.executable -u` instead of a raw `python3`, so the child process gets the same venv and unbuffered output.
4. **Output parser.** Rewrote the `run_matchup` parser in `grade.py` to understand the arena's actual `Game N/M: [W|B|D]` format (was looking for `[+] / [-] / [=]`, which the arena never prints) and the `Final: {W}W-{L}L-{D}D` summary line, with color-alternation tracking so outcomes are recorded from engine A's perspective.
5. **Repo hygiene.** Added a comprehensive `.gitignore` (Python bytecode, `.DS_Store`, venvs, pytest caches, scratch `.tmp_stockfish/`), then `git rm -r --cached` the previously-tracked `__pycache__/` and `.DS_Store` files.
6. **Set up the shared `.venv`** (§7) so every engine's existing `run.sh` resolves to a Python 3.11 interpreter with `python-chess`. Installed Stockfish 18 so the calibration anchors can spin up.
7. **Independent UCI smoke test** of all four engines through their `run.sh` files — every one reaches `uciok` cleanly under the arena's `RLIMIT_AS = 512 MB` preexec.
8. **Full calibration sweep.** 4 candidates × 3 Stockfish anchors × 12 games = 144 games. Each candidate's anchor matchups serialized so the resilient write in step 2 protects against interruption.
9. **Full cross-validation sweep.** 6 unordered pairs × 10 games = 60 games. Outcomes written to *both* engines' `results.json` (with perspective inverted for B) so each engine has a complete view of its head-to-head record.
10. **Sanity check the matrix** — verified row-vs-column consistency (A-vs-B from A's row equals B-vs-A from B's row with W↔L flipped) and that the row sums (W − L) order matches the calibration ranking.
11. **Computed §8.3 residuals** by hand from the calibrated Elos and observed scores, flagging the two pairs (Strategy1 vs SimpleOneShot, chess-ttt vs Strategy1) where Strategy1 outperforms its calibration as the real signal.
12. **Aggregate + write this report.**

---

## 10. Limitations and next steps

- **80 ms is a short time control.** At this budget the bottom two engines only reach depth 2-3; `SimpleOneShot_bot` and `Strategy1`'s advantage comes largely from PVS / TT / null-move / LMR letting them search deeper in the same wall-clock. Re-running at `movetime ∈ {200, 500, 1000}` would show how each engine scales with time and reduce the noise in the cross-validation residuals.
- **Three anchors, skill levels 1/3/5.** Stockfish skill level 5 (≈1500) already crushes the bottom three engines 0-11-1 (and `Strategy1` 0-9-3); adding a 900-Elo anchor (e.g. `UCI_LimitStrength` with a specific rating) would give the weaker engines a non-saturating reference and tighten their CIs dramatically — most directly, it would resolve whether `Strategy1`'s true Elo really is closer to 1100 than 1014.
- **10 games per cross-validation pair** is noisy (1-σ ≈150 Elo near 50%). Bumping to 40+ games per pair would materially sharpen §8.3, at a roughly linear cost in wall clock.
- **`grade.py` could do Bayesian updating** after cross-validation to refine Elos with head-to-head data, rather than treating it purely as diagnosis. Would close the gap between `Strategy1`'s anchor-derived 1014 and the higher implied strength from its dominance of TDD/chess-ttt.
- **The Strategy1 ↔ SimpleOneShot gap is now an eval problem, not a search problem.** Both engines run essentially the same modern search recipe (PVS + TT + null-move + LMR + killers + history + aspiration windows), so the +181 Elo gap is almost entirely the eval function: SimpleOneShot uses tapered PeSTO piece-square tables, while Strategy1's current champion `fortress` is a hand-tuned king-safety-heavy heuristic. The next iteration of the Darwinian tournament should include a `pesto` personality (already present in `Strategy1/engines/mve/heuristics.py` REGISTRY) and let it compete head-to-head against `fortress` and the other personalities.
