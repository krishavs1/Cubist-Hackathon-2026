# CUBIST HACKATHON 2026: CONSOLIDATED RESEARCH & ARCHITECTURE

---

## 1. MISSION STATEMENT

Build a chess engine whose primary innovation is the **AI-assisted engineering pipeline**, not raw engine strength. The chess engine is the product; the AI workflow is what we are being judged on.

> "We treated AI as an engineering team, not just an autocomplete tool."
> "Every AI-generated change went through tests and benchmarks."
> "We built a human-AI engineering loop: prompt, proposal, review, implementation, evaluation, iteration."

---

## 2. JUDGING CRITERIA

1. **Process & Parallelization** — How well 5 developers work concurrently using AI without stepping on each other. *(Highest weight)*
2. **AI Tooling & Creativity** — Using LLMs for critical evaluation, ideation, and code generation rather than boilerplate copying.
3. **Engineering Quality** — Proper testing (perft tests, legal-move gauntlet), documentation, clean architecture.
4. **Compute Efficiency** — Balancing cost and accuracy.
---

## 4. CORE ARCHITECTURE PHILOSOPHY

The engine is **language-agnostic** at the top level. Every generated engine must be an executable communicating strictly via the **UCI protocol** over STDIN/STDOUT. This means:
- Sub-agents can choose Python, C++, or Rust independently
- All engines plug into the same Arena tournament runner
- No merge conflicts across workstreams

Key innovations to differentiate from other teams:
1. **Zero-Shot LLM Heuristic Generation** — Claude writes novel evaluation functions, not standard piece tables
2. **Reflexion-Based Learning** — Tournament loss PGNs are fed back to Claude so it rewrites its own flawed heuristics
3. **Kelly Criterion Search Allocation** — Search depth treated as a financial risk allocation based on evaluation score volatility

---

## 5. REQUIRED TOOLING & TECH STACK

### Core Libraries
- **`python-chess`** ([docs](https://python-chess.readthedocs.io/)) — board representation, legal move generation, FEN/PGN support, check/checkmate/stalemate. Do not reimplement chess rules from scratch.
- **`shakmaty` + `rayon`** (Rust) — high-NPS move generation with SIMD optimization, if using Rust.
- **`cutechess-cli`** — automated tournament runner between engine executables.

### Reference Engine
- **Stockfish** ([site](https://stockfishchess.org/) | [UCI docs](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-%26-Commands.html)) — used as benchmark and oracle for position evaluation. **Not** our submitted engine.

### Engine Concepts to Implement
- Alpha-Beta Pruning ([wiki](https://www.chessprogramming.org/Alpha-Beta))
- Quiescence Search ([wiki](https://www.chessprogramming.org/Quiescence_Search)) — resolve capturing sequences before returning eval
- Move Ordering ([wiki](https://www.chessprogramming.org/Move_Ordering))
- Iterative Deepening ([wiki](https://www.chessprogramming.org/Iterative_Deepening))
- Transposition Tables ([wiki](https://www.chessprogramming.org/Transposition_Table)) — cache previously seen board states
- UCI Protocol ([spec](https://www.chessprogramming.org/UCI)) — `uci`, `isready`, `position`, `go`, `bestmove` at minimum

---

## 6. FIVE-PERSON PARALLELIZATION PLAN

Each workstream builds an independently testable module. Integration happens only at the UCI boundary.

| Role | Owner | Tech | Owns |
|---|---|---|---|
| **Infrastructure Builder** | Dev 1 | Rust (`shakmaty`, `rayon`) | UCI loop, parallelized move generation, NegaMax search tree, memory safety |
| **Evolutionary Geneticist** | Dev 2 | Rust / LLM Prompting | Prompt Claude to generate 5–10 distinct evaluation heuristics (e.g. "Aggressive Attacker," "Positional Grinder") as Rust functions; no standard piece values |
| **Arena Master** | Dev 3 | Python, `cutechess-cli` | Automated tournament pipeline: compile engines, run bullet games, extract PGNs, calculate Bayesian Elo |
| **Risk Manager** | Dev 4 | Rust / Python | Kelly Criterion time management: measure eval volatility between depth 2 and 4, allocate clock time accordingly |
| **Agentic Coach** | Dev 5 | Python / LLM Prompting | Reflexion loop: take losing PGNs from Arena, prompt Claude to analyze failures, output corrected Rust eval functions back to Dev 2 |

---

## 7. AI WORKFLOW PROCESS (TEST-DRIVEN LOOP)

```
AI proposes idea
→ human reviews
→ write or generate tests
→ implement
→ run tests
→ benchmark in Arena
→ keep or reject
→ document decision
```

**Success criteria (all engines must pass):**
- Never makes an illegal move
- Correctly detects checkmate and stalemate
- Beats a random-move bot in a statistically significant sample
- New version beats current champion before replacing it
- AI-generated heuristic must improve at least one benchmark metric

**Token Economy (compute routing):**
- **Tier 1** (Claude Pro): complex heuristics, novel architectures, reflexion analysis
- **Tier 2** (Copilot / local LLMs): boilerplate, tests, build scripts, UCI scaffolding

**Circuit Breaker:** If a sub-agent fails tests or produces bugs after 3 iterations, the branch is scrapped or flagged for human override.

---

## 8. ARENA / COMBAT MATRIX

When a sub-agent's engine passes tests, it enters the Arena:

| Phase | Action | Pass Condition |
|---|---|---|
| **1. Verification** | Run legal-move gauntlet (`tests/`) | All FEN positions return legal moves within time limit |
| **2. Baseline** | 50 bullet games vs. `baseline_bot` (pure material counter) | Win rate > 50% |
| **3. Crucible** | 100+ games vs. current Main Branch Champion | See matrix below |

**Crucible outcomes:**
- **Decisive Win (>55% WR)** → Merge to Main. New Champion.
- **Narrow Loss / High Draw Rate** → Mutate. Spin up Agent to analyze logs and rewrite heuristic.
- **Decisive Loss (<45% WR)** → Scrap. Log to `DISCOVERIES.md`.
- **Orthogonal Strengths** → Synthesize. If Engine A dominates openings and B dominates endgames, spin up a new agent to merge their logic.

---

## 9. LIVING MEMORY (FILE STRUCTURE)

All agents read these files before writing code:

| File | Purpose |
|---|---|
| `head.md` | System constitution. Only updated on major architecture changes. |
| `STRATEGIES.md` | Active backlog: `[PENDING]`, `[IN-PROGRESS]`, `[MERGED]`, `[SCRAPPED]` |
| `DISCOVERIES.md` | Lessons learned ledger — AI hallucinations, bugs, bottlenecks. Agents ingest this to avoid past mistakes. |
| `ARENA_LOG.md` | Quantitative tournament history and Elo records |
| `core/arena.py` | Darwinian tournament script. Spins up two engine executables, feeds UCI commands, runs N bullet games, outputs Elo and PGNs. |
| `tests/` | UCI and legal-move gauntlet scripts |

**GitHub structure:** Each workstream lives in its own subdirectory (`/infra`, `/heuristics`, `/arena`, `/risk`, `/coach`) to prevent merge conflicts.

---

## 10. SEED STRATEGY IDEAS

Use these as starting points — do not copy wholesale:

1. **Heuristic Distillation** — Generate 10,000 mid-game positions, have Stockfish evaluate them, use Claude to write a lightweight C++/Python eval function that mimics Stockfish's scoring without the compute.
2. **Darwinian Genetic AI** — Alpha-Beta search tree + 50 AI-generated eval functions playing an automated tournament. Winners "breed" (combine parameters) and mutate.
3. **Polyglot Pipeline** — Prototype in Python (fast dev), use AI to translate bottlenecks (move gen, eval) to C++/Rust binaries interfaced via UCI.
4. **Explainable AI Hybrid** — Lightweight traditional search + LLM layer that streams natural-language reasoning for why it chose a move. Strong for the demo.
5. **Engine Personalities** — Multiple specialized agents: Aggressive Attacker, Positional Grinder, Gambit Player, Defensive Fortress. Arena determines which personality wins.

---

## 11. RESEARCH REFERENCES

| Paper | Use |
|---|---|
| Shannon, "Programming a Computer for Playing Chess" ([link](https://vision.unipv.it/IA1/ProgrammingaComputerforPlayingChess.pdf)) | Foundational minimax/search framing, README background |
| AlphaZero, "Mastering Chess by Self-Play" ([arxiv](https://arxiv.org/abs/1712.01815)) | Inspiration for self-play and iterative improvement only — do not implement |
| Eureka, Ma et al. NVIDIA 2023 | LLMs writing and evolving mathematical reward/eval functions |
| Reflexion, Shinn et al. 2023 | Verbal RL: substitute gradient updates with LLM linguistic feedback |
| Kelly Criterion, J.L. Kelly Jr. 1956 | Dynamic compute allocation based on evaluation variance |
| ReAct Prompting ([arxiv](https://arxiv.org/abs/2210.03629)) | AI reasons → acts → observes results → revises; maps to code/test/debug loops |
| Self-Consistency ([arxiv](https://arxiv.org/abs/2203.11171)) | Ask AI for multiple candidates, compare and select — do not trust one response |
| The Prompt Report ([arxiv](https://arxiv.org/abs/2406.06608)) | Role prompting, structured prompting, prompt chaining, evaluation-driven prompting |

---

## 12. CODE FREEZE PROTOCOL

~2 hours before judging:
1. Cease all strategy generation.
2. Ingest `ARENA_LOG.md` and `DISCOVERIES.md`.
3. Synthesize `README.md` as a whitepaper covering: parallel architecture, AI triage process, UCI integration, cost-efficiency routing, and statistical evolution of the Champion engine.

**Final framing for README and demo:**
- "The chess engine was the product; the AI workflow was the innovation."
- "We used Stockfish as a benchmark, not as our submitted engine."
- Frame the project as an **AI-native engine experimentation platform**, not "just a chess bot."

---

## 13. STRATEGY DOCUMENT OUTPUT REQUIREMENTS

Each of the 5 individually generated strategies must contain:

1. **Title & Executive Summary** — Name the architecture and core philosophy
2. **CAPE Score** — Exact math with per-dimension justification
3. **Technical Architecture** — Language choice, search algorithm, evaluation function design
4. **5-Person Parallelization Plan** — What each dev builds simultaneously, which AI tools they use, how the 5 pieces merge cleanly
5. **AI Prompting Strategy** — 3 exact prompts the team should use for the hardest parts of that specific architecture
6. **Spike Checkpoint** — One sentence: the single riskiest assumption in this strategy that should be validated first before full implementation
