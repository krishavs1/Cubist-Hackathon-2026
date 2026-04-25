# Darwinian AI: The Chess Engine Factory

## The Big Idea

Most chess engines are written once and then tuned. We are building something different: **an engine that evolves**.

Instead of writing one perfect chess brain, we built a factory that can generate many different brains, pit them against each other in automated tournaments, and keep only the strongest survivors. Then we analyze why the losers lost, feed that information back to AI, and generate improved replacements.

This is Darwinian AI — survival of the fittest, but for chess evaluation functions.

---

## What Is a Chess Engine, Actually?

A chess engine has two distinct parts that are worth separating in your mind:

**Part 1: The Search** — the algorithm that looks ahead through possible moves. Think of it as the engine asking "what happens if I do X, then they do Y, then I do Z?" This part is mathematical and well-understood. Our search uses Alpha-Beta pruning (a smarter version of exhaustive search) with Iterative Deepening (start shallow and go deeper as time permits).

**Part 2: The Evaluation** — the function that looks at a board position and says "this looks good for White" or "this looks bad for White." This is where judgment lives. Material (piece count), king safety, center control, pawn structure — all of this is baked into one `evaluate(board) -> int` function that returns a score in centipawns (100 = 1 pawn's worth of advantage).

The search is fixed. **The evaluation function is the mutation surface** — the part we evolve.

---

## The Minimum Viable Engine (MVE)

The file `engines/mve/engine.py` is the seed organism — the starting point that every evolved engine descends from.

### What it contains

**Evaluation constants** (`engine.py:34-45`): The baseline weights. A pawn is worth 100 centipawns, a knight 320, a bishop 330, a rook 500, a queen 900. Mobility bonuses, center control bonuses, and king safety penalties are defined here. These are the numbers that AI variants will mutate.

**Move ordering** (`engine.py:64-85`): Before searching, we sort moves so we look at captures first and promotions next. This matters enormously for speed — good ordering means Alpha-Beta prunes more branches and searches the same depth much faster. The algorithm is MVV-LVA (Most Valuable Victim minus Least Valuable Aggressor).

**Evaluation function** (`engine.py:92-134`): The heart of the engine. Scores four things:
1. Material balance (do you have more pieces?)
2. Mobility (do you have more legal moves?)
3. Center control (are you attacking e4, d4, e5, d5?)
4. King safety (does your king have pawns shielding it?)

**Quiescence search** (`engine.py:159-203`): Solves the "horizon effect" — if you stop searching in the middle of a piece trade, your evaluation will be wrong. This extension keeps searching captures until the position settles into a "quiet" state before returning a score.

**NegaMax search** (`engine.py:206-239`): The recursive look-ahead algorithm. Searches to a given depth, always from the perspective of whoever's turn it is (that's what "Nega" means — negate and recurse). Alpha-Beta pruning skips branches that can't possibly change the outcome.

**Iterative Deepening** (`engine.py:242-289`): Search depth 1, then 2, then 3, and so on. Always keep the best move from the last fully completed depth. If the clock runs out mid-search, return something safe. The engine is never left without a move.

**UCI protocol** (`engine.py:295-434`): The Universal Chess Interface — how chess engines talk to tournament runners and GUIs. Commands come in over stdin, responses go out over stdout. This is what lets our engine compete against any other UCI-compatible engine automatically.

---

## How the Darwinian Loop Works

Here is the full lifecycle, end to end:

```
Workstream B (Evolutionary Geneticist)
  ↓
  Prompt Claude to generate a new evaluation function
  (e.g., "Write an evaluate() that prioritizes aggressive king attacks")
  ↓
  New variant engine is created (same search, different evaluate())
  ↓
Workstream C (Arena Master)
  ↓
  Automated tournament: new variant vs. current champion
  100 bullet games, Bayesian Elo calculated
  ↓
  Decision:
    > 55% win rate → Merge to main. New champion.
    ~ 50% win rate → Send to Workstream E for mutation.
    < 45% win rate → Scrap. Log the failure.
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

**Standard approach:** Write one good evaluation function. Tune it by hand.

**Stockfish approach:** Thousands of engineer-hours tuning piece-square tables and hand-crafted endgame knowledge. Not realistic in 24 hours.

**Our approach:** Use AI to generate diverse evaluation strategies in parallel. Let competition decide which ones survive. Use AI again to analyze failures and improve survivors.

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

## What Makes Each Engine Variant Different

All variants share the same `engine.py` search code. Only the `evaluate()` function and its constants change. Examples of distinct personalities being generated:

- **Aggressive Attacker**: Heavily penalizes king exposure. Prioritizes piece activity near the enemy king. Willing to sacrifice material for attack.
- **Positional Grinder**: Rewards pawn structure integrity. Penalizes isolated and doubled pawns. Plays for long-term advantage.
- **Center Controller**: Maximizes control of central squares. Prioritizes piece development and space.
- **Materialist**: Pure piece-count evaluation. Simple, fast, sometimes surprisingly strong in tactical positions.
- **Endgame Specialist**: Adjusts weights dynamically based on remaining material — becomes more king-active and pawn-focused as pieces come off.

---

## The Research Foundation

Our design is grounded in three areas:

**Evolutionary AI / LLM-Driven Search**: Inspired by *Eureka* (Ma et al., NVIDIA 2023). LLMs can write reward/evaluation functions that match or exceed human-designed ones. We replicate this for chess.

**Verbal Reinforcement Learning**: Inspired by *Reflexion* (Shinn et al., 2023). An agent can improve by reading natural-language descriptions of its own failures. We apply this by feeding PGN game records to Claude with the prompt "what went wrong, and how do you fix it?"

**Search Under Risk**: Inspired by the Kelly Criterion (J.L. Kelly Jr., 1956). When your evaluation of a position has high variance (the engine is uncertain), allocate more clock time. When evaluation is stable, move faster. Person D implements this as a time management layer.

---

## The Contract Every Engine Must Satisfy

No matter how different the evaluation function is, every engine must:

1. Accept UCI commands over stdin
2. Respond with legal moves only
3. Not crash or hang (the Arena runner cannot recover from a frozen engine)
4. Respond within its time budget

The MVE's failsafe at `engine.py:415-420` ensures that even if the search throws an unexpected exception, a random legal move is returned rather than silence. This is the floor — every variant inherits it.

---

## Where to Find Things

| File | What it is |
|------|------------|
| `engines/mve/engine.py` | The seed engine — baseline search + evaluation |
| `tests/perft_test.py` | Correctness tests: verifies legal move generation against known positions |
| `tests/self_play_test.py` | The engine playing itself — sanity check that games terminate |
| `tests/uci_test.py` | UCI protocol compliance tests |
| `tests/random_bot_battle.py` | Benchmark: engine vs. random mover, measures baseline strength |

---

## What "Winning" Looks Like

The judges are not just evaluating chess strength. They are evaluating the engineering process. The strongest submission will:

- Show a documented, testable AI-in-the-loop workflow
- Show parallel workstreams with distinct contributions
- Show experiments that failed and what was learned from them
- Show measurable improvement over time (Elo progression in `ARENA_LOG.md`)
- Show critical evaluation of AI output, not blind copy-paste

The chess engine is the product. **The AI workflow is the innovation.**
