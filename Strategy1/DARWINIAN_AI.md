# Darwinian AI: The Chess Engine Factory

## The Big Idea

Most chess engines are written once and then tuned. We are building something different: **an engine that evolves**.

Instead of writing one perfect chess brain, we built a factory that can generate many different brains, pit them against each other in automated tournaments, and keep only the strongest survivors. Then we analyze why the losers lost, feed that information back to AI, and generate improved replacements.

This is Darwinian AI — survival of the fittest, but for chess evaluation functions.

The key insight that drove the architecture from day one: **a chess engine is two separable concerns, and you should optimize them with different techniques**. The search algorithm is a well-trodden body of computer-science knowledge — the right move is to implement the textbook strong-engine recipe and stop iterating on it. The evaluation function is where chess-playing *judgment* lives — the right move is to let AI generate diverse candidates and let competition decide which judgment is best. Building this two-layer system was the original plan, not a retrofit.

---

## What Is a Chess Engine, Actually?

A chess engine has two distinct parts that are worth separating in your mind:

**Part 1: The Search** — the algorithm that looks ahead through possible moves. Think of it as the engine asking "what happens if I do X, then they do Y, then I do Z?" This part is mathematical and well-understood. Search depth dominates eval quality at fixed time-per-move, so the search must be strong out of the gate.

**Part 2: The Evaluation** — the function that looks at a board position and says "this looks good for White" or "this looks bad for White." This is where judgment lives. Material (piece count), king safety, center control, pawn structure — all of this is baked into one `evaluate(board) -> int` function that returns a score in centipawns (100 = 1 pawn's worth of advantage).

**The search is fixed. The evaluation function is the mutation surface** — the part we evolve.

---

## The Search Core (Held Constant)

The file `engines/mve/search.py` is the engine's body. It is the textbook strong-search recipe, implemented once and then locked down so every evaluator competes on equal footing.

### What it contains

**Negamax with Principal Variation Search (PVS)**: Instead of plain alpha-beta, we assume the first move (after move-ordering) is the principal variation and search remaining moves with cheap zero-window probes. Re-search only on fail-high. Buys roughly half a ply over plain alpha-beta on most positions.

**Iterative deepening with aspiration windows**: Search depth 1, then 2, 3, and so on. From depth 4 onward, open a narrow ±40 cp window around the previous score; if the search returns a value inside the window, we save the cost of a full-width search. On fail-low / fail-high we widen and re-search. The engine always has a complete-depth best move banked, so it can return safely the instant the clock runs out.

**Quiescence search with delta pruning**: At depth 0, keep searching captures until the position quiets down so we never evaluate in the middle of a piece trade. Delta pruning skips captures whose best-case material gain can't bring us back into the alpha window.

**Transposition table (Zobrist-keyed)**: Caches every searched position with a depth, a score, a bound flag (exact / lower / upper), and the best move. Hits skip recomputation entirely (huge in endgames where transpositions are dense) and the cached best move drives move ordering on the next visit.

**Null-move pruning**: If we're not in check and have non-pawn material (zugzwang guard), pretend we just pass; if a reduced-depth search of the *opponent* still fails high above beta, our position is so good that it's safe to prune the whole branch.

**Late move reductions (LMR)**: After we've searched the first three quiet moves at full depth, reduce subsequent quiet moves' depth by 1-3 plies. Re-search at full depth only if a reduced search beats alpha. Move ordering is good enough that the first few moves contain the truth most of the time.

**Check extensions**: When the side to move is in check, extend the search by one ply. Avoids the "we mate in 3 but the search horizon is at depth 2" failure mode.

**Killer moves + history heuristic**: Quiet moves that caused beta cutoffs are remembered (per-ply for killers, globally for history) and ordered first when we revisit similar positions. Better ordering → more cutoffs → deeper search.

**Reverse-futility pruning + razoring + futility pruning**: Three eval-margin pruning rules at shallow depths that skip moves whose static evaluation can't realistically reach the alpha/beta window.

**MVV-LVA capture ordering**: Most Valuable Victim minus Least Valuable Aggressor. Cheap, dominant heuristic for ordering captures (always look at QxP before PxQ).

**Robust UCI protocol**: Stdin/stdout commands, time management with both soft and hard budgets, mate-distance scoring, info lines for arena instrumentation. The engine never hangs and never returns an illegal move; if anything throws, the failsafe returns a random legal move so the Arena runner can keep going.

The search is held constant on purpose — the entire point of the architecture is that **only the evaluation should change between Darwinian variants**. A variant whose only difference is a new `evaluate()` is guaranteed to be a controlled experiment.

---

## The Evaluation Layer (The Mutation Surface)

The file `engines/mve/heuristics.py` holds the gene pool. Each entry in `REGISTRY` is one chess-playing personality:

| Personality | Philosophy |
|-------------|------------|
| **`pesto`** | Tapered piece-square tables (midgame ↔ endgame interpolation). The strongest single-eval baseline; reflects modern engine design. |
| **`balanced`** | Material + mobility + center control + king safety, weighted to behave like a sensible human. |
| **`aggressive_attacker`** | Heavily rewards piece pressure on the enemy king; willing to trade material for attack. |
| **`positional_grinder`** | Maximizes center control + king safety; plays for long-term advantage. |
| **`material_hawk`** | Pure material count with refined piece values (KNIGHT=325, BISHOP=325, ROOK=490, QUEEN=920). Surprisingly strong in tactical positions. |
| **`fortress`** | Massive king-safety weighting + trade-down bonus when ahead. Knows how to convert. |
| **`pawn_storm`** | Bonuses for advanced pawns; sacrifices own king safety to crash through. |

Every personality satisfies the same contract: `fn(board: chess.Board) -> int`, returning centipawns from White's perspective. The Searcher converts to side-to-move POV internally. New personalities can be added (Workstream B from Claude prompts, Workstream E from reflexion-based rewrites) without touching the search code.

---

## How the Darwinian Loop Works

Here is the full lifecycle, end to end:

```
Workstream B (Evolutionary Geneticist)
  ↓
  Prompt Claude to generate a new evaluation function
  (e.g., "Write an evaluate() that prioritizes aggressive king attacks")
  ↓
  New variant evaluator added to heuristics.REGISTRY
  ↓
Workstream C (Arena Master)
  ↓
  Automated round-robin tournament: every personality plays every
  other personality across N games at fixed time-per-move
  Bayesian Elo updates after each game
  ↓
  Decision:
    > 55% win rate vs current champion → New champion. Promote.
    ~ 50% win rate                     → Send to Workstream E for mutation.
    < 45% win rate                     → Scrap. Log the failure.
  ↓
Workstream E (Agentic Coach) [only for mutations]
  ↓
  Take the loser's PGNs → feed into Claude
  "Here are games this engine lost. Analyze its mistakes. Rewrite evaluate()."
  ↓
  Improved candidate → back to Workstream C
```

This is the **Reflexion loop** — named after the research paper "Reflexion: Language Agents with Verbal Reinforcement Learning." Instead of traditional machine learning (adjusting numerical weights via gradient descent), we use language as the feedback signal. Claude reads game records and rewrites code.

---

## Why This Is Different From Other Approaches

**Standard approach:** Write one good evaluation function. Tune it by hand. One fixed playing style.

**Stockfish approach:** Thousands of engineer-hours tuning piece-square tables and hand-crafted endgame knowledge. Not realistic in 24 hours.

**Naive one-shot LLM approach:** Prompt Claude once for a complete chess engine. You get the textbook recipe — strong, but only one philosophy. No way to discover that, say, an aggressive style beats a positional style at fast time controls.

**Our approach:** Lock down the search at the textbook strong-engine recipe so depth isn't the bottleneck. Then use AI to generate diverse evaluation strategies in parallel. Let competition decide which ones survive. Use AI again to analyze failures and improve survivors. The architecture forces a controlled experiment: every variant differs only in its judgment of positions, never in its raw search ability.

The key insight from *Eureka: Human-Level Reward Design via Coding Large Language Models* (NVIDIA 2023): you don't need to know in advance what a good evaluation function looks like. You let LLMs propose candidates and let empirical results tell you what works.

---

## The 5-Person Parallelization

Each team member owns a distinct, non-overlapping responsibility:

| Person | Role | What they build |
|--------|------|-----------------|
| **A** | Infrastructure Builder | The search core, UCI loop, Rust port (high-NPS engine body) |
| **B** | Evolutionary Geneticist | AI-generated evaluation variants (the "brain candidates") |
| **C** | Arena Master | Tournament runner, Elo calculation, statistical significance |
| **D** | Risk Manager | Kelly Criterion time allocation (variance-based clock management) |
| **E** | Agentic Coach | Reflexion loop — feeds losing PGNs to AI, gets improved evaluators back |

Person A's work is the substrate. Persons B and E generate and improve the evaluation functions. Person C runs the selection pressure. Person D makes the engine smarter about when to think deeply vs. move fast.

---

## The Research Foundation

Our design is grounded in three areas:

**Evolutionary AI / LLM-Driven Search**: Inspired by *Eureka* (Ma et al., NVIDIA 2023). LLMs can write reward/evaluation functions that match or exceed human-designed ones. We replicate this for chess.

**Verbal Reinforcement Learning**: Inspired by *Reflexion* (Shinn et al., 2023). An agent can improve by reading natural-language descriptions of its own failures. We apply this by feeding PGN game records to Claude with the prompt "what went wrong, and how do you fix it?"

**Search Under Risk**: Inspired by the Kelly Criterion (J.L. Kelly Jr., 1956). When your evaluation of a position has high variance (the engine is uncertain), allocate more clock time. When evaluation is stable, move faster. Person D implements this as a time management layer.

**Modern Search Recipe**: Search architecture follows the canonical Chess Programming Wiki / PeSTO design (Pawel Koziol's tapered PST tables, plus the standard PVS / TT / null-move / LMR stack). Held fixed by design so the experimental signal lives in the eval layer.

---

## The Contract Every Personality Must Satisfy

No matter how different the evaluation function is, every personality must:

1. Implement `fn(board: chess.Board) -> int` returning centipawns from White's POV
2. Not call `board.push` / `board.pop` or otherwise mutate the board
3. Not handle terminal states (mate / stalemate) — the search handles those before calling evaluate
4. Keep material dominant — otherwise the engine throws pieces away

The Searcher's failsafe guarantees the engine never hangs and never returns an illegal move; even if the eval throws, a random legal move is returned rather than silence. This is the floor — every variant inherits it.

---

## Where to Find Things

| File | What it is |
|------|------------|
| `engines/mve/search.py` | The search core — PVS + TT + null-move + LMR + killers + history + aspiration + quiescence. Held constant. |
| `engines/mve/heuristics.py` | The personality registry — all evaluators that can drive the search. |
| `engines/mve/engine.py` | UCI loop wiring a chosen personality into the search core. |
| `engine/run.sh` | Tournament entry point — launches the current Champion personality. |
| `arena/tournament.py` | Round-robin tournament runner with iterative-Elo standings. |
| `tests/perft_test.py` | Correctness tests: legal move generation against canonical Chess Programming Wiki perft values. |
| `tests/self_play_test.py` | The engine playing itself — sanity check that games terminate. |
| `tests/uci_test.py` | UCI protocol compliance tests. |
| `tests/random_bot_battle.py` | Benchmark: engine vs. random mover, measures baseline strength. |

---

## What "Winning" Looks Like

The judges are not just evaluating chess strength. They are evaluating the engineering process. The strongest submission will:

- Show a documented, testable AI-in-the-loop workflow
- Show parallel workstreams with distinct contributions
- Show experiments that failed and what was learned from them
- Show measurable improvement over time (Elo progression in `ARENA_LOG.md`)
- Show critical evaluation of AI output, not blind copy-paste

The chess engine is the product. **The AI workflow is the innovation.** The architectural decision to hold search constant and evolve evaluation is what makes the AI workflow tractable in the first place — without that separation, every "new variant" would be confounded by uncontrolled search differences and the tournament signal would be meaningless.
