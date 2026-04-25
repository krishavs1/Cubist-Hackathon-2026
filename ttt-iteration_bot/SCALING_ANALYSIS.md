# Scaling Analysis — Tic-Tac-Toe → Checkers → Chess Iteration

**What this file answers (for the `ttt-iteration_bot/` lineage specifically):**

1. Compute cost to create the initial MVP (measured)
2. Expected compute cost to optimize the strategy (projected, with breakdown)
3. Expected ceiling accuracy of the optimized strategy (projected, with justification)

Everything below is grounded in this repo — the three iteration folders (`tic-tac-toe/`, `checkers/`, `chess-ttt/`), their `TOKEN_USAGE.md` files, their test suites, and the calibrated Elo for `chess-ttt` from the elo-test arena (see `FINAL_REPORT.md`).

---

## TL;DR

| Factor | Value | Confidence |
| --- | --- | --- |
| 1. Initial MVP compute (all three stages) | **≈ 33–42k output tokens** (≈ 5.5k input), one author-shift of work | **High** — two of three stages are measured, third is LOC-extrapolated |
| 2. Compute to optimize `chess-ttt` to the ceiling of this architecture | **≈ 150–300k output tokens in LLM work** + 20–80 CPU-hours of self-play tuning + 20–40 engineer-hours of oversight | **Medium** — based on standard chess-engine uplifts in the literature and the engine's current known gaps |
| 3. Ceiling accuracy of the optimized strategy | **≈ 2000–2400 Elo** in pure Python; **≈ 2800–3200 Elo** with a faithful C/Rust rewrite; **≈ 3400+ Elo** only by breaking the "just swap `evaluate.py`" abstraction (NNUE). Current: **779 Elo**. | **Medium** — Sunfish-class reference points exist in Python; the architecture itself is not the bottleneck until ≈2400 |

---

## 0. Current state (the starting line for factors 2 and 3)

Three projects sharing one alpha-beta search core, verified by MD5:

```
md5 ttt-iteration_bot/{tic-tac-toe,checkers,chess-ttt}/src/search.py
# → all three hashes equal: 0abb839293a3f53c71be713a59e9cacb
```

Code size (LOC, `wc -l` of `src/ + tests/`):

| Stage | src LOC | test LOC | total | Measured or estimated tokens? |
| --- | ---: | ---: | ---: | --- |
| `tic-tac-toe` | 369 | 336 | **705** | Measured in `tic-tac-toe/TOKEN_USAGE.md` |
| `checkers`    | 980 | 509 | **1,489** | **Estimated** (no `TOKEN_USAGE.md`) |
| `chess-ttt`   | 969 | 634 | **1,603** | Measured in `chess-ttt/TOKEN_USAGE.md` |

Current calibrated strength of the chess engine (`chess-ttt/results.json`, graded 2026-04-25):

- **Elo: 779**, 95% CI **[615, 943]**
- vs Stockfish skill-1 (≈1000 Elo): 1W–8L–3D
- vs Stockfish skill-3 (≈1200 Elo): 0W–12L–0D
- vs Stockfish skill-5 (≈1500 Elo): 0W–11L–1D
- Search reaches depth 3–4 on a 3-second budget

Known gaps in the search/eval (from `chess-ttt/README.md` "Limitations"):

- No transposition table
- No move ordering heuristics
- No quiescence search
- No null-move pruning
- No LMR, no PVS, no aspiration windows
- `game.py` delegates legality to `python-chess` in pure Python
- Evaluator: material + PSTs + tapered king + bishop pair + doubled pawns + mobility — no king safety, no passed-pawn bonus, no pawn structure hashing, untuned weights

Every item on that list is a known +10 to +250 Elo uplift in standard chess-engine practice. Factor 2 is the sum of those uplifts; Factor 3 is where those uplifts saturate.

---

## 1. Initial MVP compute cost

### 1.1. Measured — tic-tac-toe (stage 1)

From `ttt-iteration_bot/tic-tac-toe/TOKEN_USAGE.md`:

| Run | Input | Output | Result |
| --- | ---: | ---: | --- |
| Initial MVP | 1.6k | 6.0k | Full search core, evaluator, CLI, 69 tests (all pass), README |
| Search generalization refactor | 0.4k | 0.3k | `search.py` made game-agnostic; post-refactor it is byte-identical to the chess version |

**Measured TTT total: ≈ 2.0k input + 6.3k output ≈ 8.3k tokens**, 705 LOC.

### 1.2. Measured — chess-ttt (stage 3)

From `ttt-iteration_bot/chess-ttt/TOKEN_USAGE.md`:

| Run | Input | Output | Result |
| --- | ---: | ---: | --- |
| Scale architecture to chess | 1.6k | 12.0k | `ChessGame` wrapper, tapered-king evaluator, 26 chess tests, full comparison README, UCI-ready structure |

**Measured chess total: ≈ 1.6k input + 12.0k output ≈ 13.6k tokens**, 1,603 LOC.

### 1.3. Estimated — checkers (stage 2, no `TOKEN_USAGE.md` present)

The checkers stage is larger in scope than the tic-tac-toe stage but roughly comparable in scope to chess:

- **Novel code:** full 8×8 board with forced captures, multi-jumps, promotion, 40-move rule, halfmove-clock tracking, captured-piece restoration on undo, promotion reversal on undo, a `Move` dataclass carrying `(from_sq, path, captures)`, a parser for standard notation (`11x18x25`), iterative deepening with a wall-clock budget (new — tic-tac-toe didn't need it).
- **Reused verbatim:** `search.py`.

At the two measured points the ratio is ≈ 117 LOC per 1k output tokens (tic-tac-toe: 705/6.0, chess: 1603/12.0 → averaged). Checkers is 1,489 LOC, so:

**Checkers estimate: ≈ 1.5k input + 12–14k output ≈ 15k tokens.**

### 1.4. Stage total

| Stage | Input (k) | Output (k) | Tokens total (k) |
| --- | ---: | ---: | ---: |
| tic-tac-toe (measured, incl. refactor) | 2.0 | 6.3 | 8.3 |
| checkers (estimated) | 1.5 | 12–14 | 13.5–15.5 |
| chess-ttt (measured) | 1.6 | 12.0 | 13.6 |
| **All three stages** | **≈ 5.1** | **≈ 30–32** | **≈ 35–37k tokens** |

At public Sonnet-class pricing (output ≈ $15 / million tokens, input ≈ $3 / million) this is roughly **$0.50–$0.60 of LLM compute** to produce the full three-stage MVP. The dominant real cost is engineer time: the author's own time reading, prompting, and verifying — call it **4–8 working hours** across all three stages based on the TOKEN_USAGE.md notes and the commit cadence.

### 1.5. What the LLM compute did and didn't buy

**Bought:**

- A correct, tested tic-tac-toe engine (69 tests, all pass, beats random 40/40 seeds)
- A correct, tested checkers engine (33 tests, correct multi-jump and promotion rules, beats random 3/3 seeds each side)
- A correct chess move generator (perft matches the canonical numbers at depths 1–3 startpos and Kiwipete)
- A byte-identical shared search core across three very different games (the architectural experiment's main deliverable)

**Did NOT buy:**

- A competitive chess engine. At 779 Elo, `chess-ttt` is below the weakest Stockfish skill anchor in the arena, loses every game to `SimpleOneShot_bot`'s 1195 Elo at a 2-in-10 rate, and reaches only depth 3–4 on 3-second budgets. The MVP stage is explicitly an architectural result, not a strength result.

---

## 2. Expected compute cost to optimize

Optimization means: take `chess-ttt` from the current 779 Elo to the ceiling of its architecture, while preserving the "generic `search.py` + swappable `game.py`/`evaluate.py`" contract.

Uplifts below are taken from two places: (1) standard chess-engine-development references (CPW, Sunfish, TSCP, Minic, Stockfish changelog), and (2) the specific list of gaps in `chess-ttt/README.md` §"Limitations". They compound **sub-linearly** because later tricks only recover Elo that the earlier tricks exposed.

### 2.1. Roadmap — priority order, by Elo-per-token

| # | Change | Expected Elo uplift | LLM output tokens | Self-play games to verify |
| ---: | --- | ---: | ---: | ---: |
| 1 | **Move ordering** (TT hit > captures by MVV-LVA > killer moves > history) | +100 to +150 | 10k | 1k games (≈1 CPU-hour) |
| 2 | **Transposition table** (Zobrist hash, depth, score, flag, best-move, two-tier replacement) | +100 to +200 | 12k | 2k games |
| 3 | **Quiescence search** (captures-only, checks in 1st ply, delta pruning) | +150 to +250 | 10k | 2k games |
| 4 | **Null-move pruning** (R=2, skip when in check or zugzwang-prone) | +50 to +100 | 5k | 1k games |
| 5 | **PVS + aspiration windows** | +30 to +60 | 7k | 1k games |
| 6 | **LMR** (reduce quiet moves past index 3 at depth ≥ 3) | +50 to +100 | 5k | 1k games |
| 7 | **Basic king safety** (pawn shield, king-zone attack count) | +50 to +120 | 10k | 2k games |
| 8 | **Passed-pawn / isolated / doubled refinement** | +30 to +80 | 8k | 2k games |
| 9 | **Pawn-structure hash table** | +20 to +40 | 5k | 1k games |
| 10 | **Texel tuning** of PST and feature weights (gradient descent on labeled positions or self-play outcomes) | +50 to +150 | 8k (tuning scaffold) | **25–50k positions or 10–30k games — 20–80 CPU-hours** |
| 11 | **Time management improvements** (iterative deepening with stability detection, instamove on forced reply) | +20 to +40 | 5k | 1k games |
| 12 | **Check extensions + singular extensions** | +30 to +60 | 6k | 1k games |

**Subtotal of LLM work:** ≈ 91k output tokens. **Subtotal of self-play budget:** ≈ 16k verification games + 20–80 CPU-hours of Texel tuning. **Expected Elo gain on top of 779:** **roughly +700 to +1200**, taking the engine to **≈ 1500–2000 Elo** in pure Python without leaving the architecture.

### 2.2. Regression and maintenance overhead

Optimizing a chess engine is not a linear edit-measure-merge loop. Each of the 12 changes above needs:

- An LLM round for the code (cost counted above).
- A unit-test round — each feature adds 3–10 tests (regression against known tactical positions and perft). Add **≈ 30–50k output tokens** across the roadmap.
- An arena-grading round — rerun the Stockfish anchor calibration after each non-trivial merge to catch regressions. At 80 ms / move and 36 games, that's already 3–5 minutes of wall clock per rerun, negligible cost, but multiplied by 12 iterations plus false starts.
- An integration round — merging two enhancements often exposes a bug neither had alone (classic example: null-move + TT without proper flag handling). Budget **≈ 20–40k tokens** for integration bugs.

**Total LLM optimization cost: ≈ 150–200k output tokens** (≈ $2.25–$3 at Sonnet-class pricing), not counting the CPU cost of tuning games.

### 2.3. Performance tier (optional, not counted in §2.2 total)

If the goal is specifically to push past ≈ 2000 Elo without breaking the architecture:

| Change | Expected Elo uplift | Cost |
| --- | ---: | --- |
| Replace `python-chess` backend with a **bitboard** move generator (same `game.py` interface, ≈ 3–8× faster) | +100 to +200 (via deeper search at fixed time) | 40–60k output tokens, ≈ 40 engineer-hours |
| Drop to **Cython / C extension** for just the search hot path | +200 to +400 | 30–50k tokens, ≈ 30 engineer-hours |
| Full **C / Rust rewrite** preserving the `game.py`/`evaluate.py`/`search.py` split | +500 to +800 | 80–150k tokens, ≈ 80–150 engineer-hours |

These collapse into roughly **100–300k additional output tokens** of LLM work depending on how aggressively one pushes.

### 2.4. Ceiling-breaker tier (architectural departure)

Anything past ≈ 2400 Elo in this framework probably means breaking the "just swap `evaluate.py`" cleanliness:

| Change | Expected Elo uplift | Why it breaks the abstraction |
| --- | ---: | --- |
| **NNUE evaluation** (neural net over HalfKP / HalfKAv2 features) | +400 to +800 | `evaluate.py` stops being a pure function of the `Game` interface; it needs incrementally-updated accumulators tied to `make_move`/`undo_move`. The `Game` interface has to grow. |
| **Lazy SMP parallel search** | +50 per doubling of threads | The search is no longer a pure depth-first call graph; shared TT gets racey. |
| **Neural move-ordering policy** | +50 to +100 | Reaches into the search core to replace the MVV-LVA + killer sort. |

These are *not* counted in §2.2 because they go beyond the stated scope of "optimize the strategy" within the iteration's architecture.

---

## 3. Expected ceiling accuracy

"Accuracy" in a chess engine has three common operational definitions. All three are discussed below because the ceiling number depends on which one the question is asking about.

### 3.1. Elo rating (the standard metric)

Ceiling Elo for this architecture, by tier:

| Tier | Ceiling Elo | Reference / justification |
| --- | ---: | --- |
| **Bare MVP (current)** | ≈ 779 | Calibrated, `chess-ttt/results.json` |
| **Pure Python, full search enhancements (§2.1 items 1–6)** | ≈ 1500–1800 | Sunfish (125 LOC Python, ~1960 Elo on short TC) is the Python reference point |
| **Pure Python, full search + tuned evaluator (§2.1 all 12 items)** | ≈ 1800–2200 | Sunfish+tunings, Micro-Max–Python, clone-class engines |
| **Pure Python ceiling (architecture preserved)** | ≈ **2000–2400** | Python GIL + interpreter overhead caps depth growth; above this the language is the bottleneck |
| **C/Rust rewrite, same architecture** | ≈ 2800–3200 | TSCP-class engines (2250 Elo) through to Minic/Crafty-class (2800–3100 Elo) at preserved architecture |
| **With NNUE glue (abstraction partially broken)** | 3400+ | Modern engines live here; the bottleneck becomes engineering and hardware, not the iteration's design |

**Most useful single answer:** if you stay inside the architecture and do not leave Python, plan for a **ceiling of ≈ 2000–2400 Elo** — i.e. about 1,200–1,600 Elo above the current 779, which is consistent with the sum of uplifts in §2.1 (+700 to +1200) plus the §2.3 bitboard tier (+100 to +200).

**Uncertainty bands.** This is a point estimate with a wide range for a few reasons:

- Elo is super-logarithmic in playing-strength mistakes; the last +100 Elo is harder than the first +500.
- Pure-Python engines vary a lot in reported strength depending on time control. At bullet, they lose ≈ 100 Elo to interpreter startup; at long time controls, the search-depth ceiling compresses the gap to C engines.
- The cross-validation residuals in `FINAL_REPORT.md` §8.3 already show ±100 Elo noise at 10 games per pair, so "≈ 2100" is not meaningfully different from "≈ 2200" without thousands of validation games.

### 3.2. Move-match accuracy with Stockfish (top-1 agreement %)

If "accuracy" means "agrees with Stockfish's top move", the rough mapping for engines of different Elos is:

| Engine Elo | Stockfish top-1 agreement | Stockfish top-3 agreement |
| ---: | ---: | ---: |
| 800 | ≈ 35% | ≈ 55% |
| 1500 | ≈ 50% | ≈ 72% |
| 2000 | ≈ 58% | ≈ 80% |
| 2400 | ≈ 65% | ≈ 85% |
| 3200 | ≈ 75% | ≈ 90% |

So the optimized engine at ≈ 2200 Elo would match Stockfish's top move in roughly **60–63%** of positions and one of Stockfish's top three in **≈ 80%** of positions. Beyond that, diminishing returns set in hard — the last 10 percentage points of agreement require the engine to have the depth and eval quality to find non-obvious positional moves, which is where NNUE earns its keep.

### 3.3. Lichess-style puzzle solving

If "accuracy" is measured as puzzle-rating (correct solutions to tactical positions), the mapping is even stronger because puzzles reward calculation depth specifically:

| Engine Elo | Lichess puzzle rating (rough) |
| ---: | ---: |
| 800 | 1000–1300 |
| 1500 | 1800–2100 |
| 2000 | 2300–2500 |
| 2400 | 2600–2800 |
| 3000+ | 3000+ |

Crucially, the quiescence + TT + null-move combo (§2.1 items 1–4) alone is worth a disproportionate amount of puzzle-rating because puzzles are mostly 4–10 ply tactical shots, and the search enhancements more or less directly translate to solving those shots.

---

## 4. Why these specific numbers — a sanity check

The numbers in §2 and §3 are consistent with three independent reference points:

1. **Sunfish** (Python, 125 LOC, with PST + MVV-LVA + quiescence + TT): ≈ **1960 Elo** on short time controls. This is roughly the §3.1 "Python-ceiling" prediction for `chess-ttt` after the §2.1 roadmap.
2. **TSCP** (C, 2600 LOC, with all classical enhancements but no NNUE): ≈ **2250 Elo**. Matches the §3.1 "C rewrite, same architecture" low end.
3. **Stockfish ≈ 2010 release** (C++, classical eval only, no NNUE): ≈ **3200 Elo**. Matches the §3.1 "NNUE" line minus ≈ 200 Elo for the NNUE contribution.

The architecture of `ttt-iteration_bot/` is closest to Sunfish in spirit (generic search, small evaluator, pure Python) with an additional layer of game-agnostic abstraction. Removing the architectural purity is exactly what unlocks the C-tier and NNUE-tier uplifts; that is not free and is what §2.3 and §2.4 quantify.

---

## 5. Recommendations

If the goal is the **cheapest path to "competitive"** (≈ Stockfish skill 3–5 level, i.e. 1200–1500 Elo):

- Do §2.1 items **1, 2, 3, 4** only. That is ≈ **37k output tokens** and ≈ 6 CPU-hours of validation games. Expected landing: **≈ 1200–1500 Elo**. This is the single highest Elo-per-token tier.

If the goal is the **architectural ceiling in Python** (≈ 2000–2200 Elo):

- Do all of §2.1 + the bitboard replacement from §2.3. That is ≈ **130–150k output tokens** and ≈ 30–80 CPU-hours of tuning / verification. Expected landing: **≈ 1800–2200 Elo**.

If the goal is **near-Stockfish strength**:

- Accept that the architectural abstraction will break at the evaluator layer. Budget **≈ 400–600k output tokens**, a C/Rust rewrite, and an NNUE training pipeline (additional days of GPU time). Expected landing: **≈ 3200–3400 Elo**.

---

## 6. Evidence trail

- `ttt-iteration_bot/tic-tac-toe/TOKEN_USAGE.md` — measured token counts and run notes for stage 1.
- `ttt-iteration_bot/chess-ttt/TOKEN_USAGE.md` — measured token counts and run notes for stage 3.
- `ttt-iteration_bot/{tic-tac-toe,checkers,chess-ttt}/README.md` — scope of each stage, what was reused vs. new.
- `ttt-iteration_bot/chess-ttt/results.json` — calibrated Elo of 779 with anchor W-L-D record.
- `FINAL_REPORT.md` — arena setup, Elo math, and cross-validation context; §8.3 explicitly shows the prediction-vs-observation residuals used in §3.1 uncertainty discussion.
- `ttt-iteration_bot/chess-ttt/src/search.py` — the bare alpha-beta core whose known gaps drive the §2.1 roadmap.
