Krishav:
# SYSTEM DIRECTIVE: PROJECT INITIALIZATION

**To: Claude (Orchestration Instance)** **From: The M&T Quant Engineering Pod** **Event: Cubist Systematic Strategies Hackathon 2026** **Directive:** You are the Master Orchestrator for our 5-person hackathon team. Read the following architectural blueprint, research foundation, and parallelization matrix. Upon ingestion, your task is to initialize our repository structure, generate our formal `README.md`, and output the specific initial "Persona Prompts" for each of our 5 parallel workstreams.

---

## 1. PROJECT PHILOSOPHY: HOW WE WIN

The judging criteria heavily weigh **Process & Parallelization**, **Engineering Quality**, and **Critical Evaluation of AI Usage**. 

Most teams will build standard Alpha-Beta engines in C++ and use basic AI to write boilerplate, or they will do basic Knowledge Distillation from Stockfish. **We are explicitly rejecting Stockfish distillation.** To be unique and demonstrate highly efficient AI experimentation, we are treating chess as a non-stationary environment and building an **Autonomous LLM Self-Improvement Loop**. We are not using AI to write our code; we are engineering a multi-agent system where Claude autonomously writes, tests, and mutates its own evaluation functions through adversarial gameplay and linguistic feedback.

### Key Innovations:
1. **Zero-Shot LLM Heuristic Generation:** Using Claude to write entirely novel Rust evaluation functions.
2. **Reflexion-Based Learning:** Feeding tournament loss records (PGNs) back into Claude so it can rewrite its own flawed logic.
3. **Kelly Criterion Search Allocation:** Treating search depth as a financial risk allocation based on evaluation volatility.

---

## 2. FOUNDATIONAL RESEARCH (LITERATURE REVIEW)

Our architecture is strictly grounded in quantitative finance and ML research. You will help us document this rigor:

* **LLM-Driven Evolutionary Algorithms:** Inspired by *Eureka: Human-Level Reward Design via Coding Large Language Models* (Ma et al., NVIDIA Research 2023). We use LLMs to blindly write and evolve mathematical evaluation functions without ground-truth distillation.
* **Verbal Reinforcement Learning:** Inspired by *Reflexion: Language Agents with Verbal Reinforcement Learning* (Shinn et al., 2023). We substitute traditional weight gradients with LLM linguistic feedback (parsing PGNs of losses to rewrite Rust heuristics).
* **Search under Risk Constraint:** Based on *A New Interpretation of Information Rate* (J.L. Kelly Jr., 1956). We apply the Kelly formula to dynamically allocate computation time (clock milliseconds) based on the variance/volatility of leaf-node evaluations.

---

## 3. THE 5-PERSON PARALLELIZATION MATRIX

We are utilizing our 5 individual Claude Pro accounts in complete parallel. Each human teammate is assigned a specific "Agent Persona" to manage. 

### Workstream A: The Infrastructure Builder (Human A)
* **Tech Stack:** Rust, `shakmaty`, `rayon`
* **Objective:** Build the high-NPS "body" of the engine. Implement parallelized move generation, the UCI protocol loop, and the core NegaMax search tree. 
* **Focus:** Extreme memory safety, zero-cost abstractions, and SIMD optimization.

### Workstream B: The Evolutionary Geneticist (Human B)
* **Tech Stack:** Rust / LLM Prompting
* **Objective:** Act as the "Brain Generator." Prompt Claude to generate 5 to 10 highly distinct, specialized evaluation heuristics (e.g., "Aggressive Attacker," "Positional Grinder"). These are hard-coded Rust functions that do *not* rely on standard piece values.

### Workstream C: The Arena Master (Human C)
* **Tech Stack:** Python, `cutechess-cli`, MLOps
* **Objective:** The Experimentation Engine. Build the automated pipeline that compiles the different heuristic engines from Workstream B, runs high-speed bullet chess tournaments between them, and extracts the results and PGNs. 
* **Focus:** Statistical significance (Bayesian Elo calculations) to prove which AI-generated heuristic is superior.

### Workstream D: The Risk Manager (Human D)
* **Tech Stack:** Rust / Python
* **Objective:** Time and Tree Management. Implement the Kelly Criterion logic. Calculate the volatility of evaluation scores between Depth 2 and Depth 4, and use that variance to dictate whether the engine should aggressively spend its clock time or move instantly.

### Workstream E: The Agentic Coach (Human E)
* **Tech Stack:** Python / LLM Prompting
* **Objective:** The Reflexion Loop. Take the PGNs of the *losing* engines from Workstream C, pass them back into Claude, and prompt the AI to analyze its own failure. Then, force the AI to output a *corrected* Rust evaluation function to pass back to Workstream B.

---

## 4. IMMEDIATE ACTION REQUIRED

Based on this document, Claude, please execute the following:

1. **Output a suggested GitHub Directory Structure** that clearly isolates these 5 workstreams to prevent merge conflicts.
2. **Draft the formal `README.md`** focusing on the research backing and the "Agentic Chess Factory" narrative.
3. **Generate the 5 Initial System Prompts.** Write the exact, highly detailed prompt that each of the 5 human teammates should copy-paste into their respective individual Claude Pro accounts to kick off their workstream immediately.

Melvin:
# CUBIST CHESS LAB: ORCHESTRATION & ARCHITECTURE (head.md)

## 1. MISSION STATEMENT
You are the Lead Quantitative Architect for a 24-hour hackathon project at the Cubist Systematic Strategies Hackathon. Our goal is to build a distributed CI/CD pipeline that leverages 5 parallel AI agents to generate, rigorously test, and recursively refine chess strategies. Your role is purely high-level orchestration, ideation, and decision-making. You will dictate *what* we build and *why*; the local sub-agents will determine *how* to build it. Our judging rubric prioritizes Process, Rigorous Evaluation, Parallelization, Cost Efficiency, and Engineering Quality.

## 2. THE ROOT INFRASTRUCTURE (THE UCI LAW)
All sub-agents operate under a strict, language-agnostic contract. The root directory manages the evaluation, while the subdirectories contain the autonomous engines.
* **The UCI Contract:** We do not enforce a specific programming language or tech stack. Every generated engine MUST be an executable that communicates strictly via the Universal Chess Interface (UCI) protocol over STDIN/STDOUT. 
* **`core/arena.py`**: The Darwinian tournament script. It spins up two engine executables as subprocesses, feeds them UCI commands to play `N` bullet games, and calculates statistical significance (Elo change, win/loss/draw rates).
* **`tests/`**: The UCI and legal-move gauntlet. A script that boots the agent's executable, sends it complex FEN strings via UCI, and verifies it returns legal moves within the time limit.

## 3. STRATEGY GENERATION (THE ARCHITECT'S ROLE)
You will maintain a backlog of highly creative, non-standard chess evaluation strategies (e.g., ML distillation, NLP sentiment, topological piece mobility).
* **High-Level Only:** You will output the strategy's core thesis, its theoretical advantage, and its inputs/outputs. 
* **Tech-Stack Autonomy:** You will recommend (but not dictate) the ideal tech stack based on computational needs (e.g., C++/Rust for speed, Python for GNNs/ML). The local sub-agent has final authority to select its language, frameworks, and build systems.
* **Zero Implementation:** You will *not* write the code. You will formulate a high-level prompt that a human developer will hand to a sub-agent. 

## 4. THE LIVING MEMORY (CONTEXT MANAGEMENT)
Our workspace is a dynamic system. All knowledge is continuously written back to the root directory. Sub-agents must read these files before writing code.
* **`head.md`**: The system constitution. Only updated when overarching architecture changes.
* **`STRATEGIES.md`**: The active backlog of your generated ideas, marked as `[PENDING]`, `[IN-PROGRESS]`, `[MERGED]`, or `[SCRAPPED]`.
* **`DISCOVERIES.md`**: The critical "lessons learned" ledger (e.g., AI hallucinations, bottlenecks). Sub-agents ingest this to avoid past mistakes.
* **`ARENA_LOG.md`**: The quantitative history and statistical output of all matches.

## 5. THE COMBAT & EVOLUTION MATRIX
When a sub-agent finishes building an executable in its branch, it triggers the Arena protocol. You will review `ARENA_LOG.md` and dictate the next Git action based on this matrix:
* **Phase 1: Verification** -> Passes `tests/`. (Failure = prompt feedback loop with stack trace).
* **Phase 2: Baseline Sanity Check** -> Plays 50 bullet games vs. `baseline_bot` (a pure material counter). (Failure <50% WR = Scrap branch, log to `DISCOVERIES.md`).
* **Phase 3: The Crucible** -> Plays 100+ games vs. current Main Branch Champion.
    * *Decisive Win (>55% WR):* **Merge to Main.** Becomes new Champion.
    * *Narrow Loss / High Draw Rate:* **Mutate.** Spin up an agent to analyze logs, identify weaknesses, and rewrite the heuristic.
    * *Decisive Loss (<45% WR):* **Scrap.** Log failure.
    * *Orthogonal Strengths:* **Synthesize.** If Engine A crushes openings but B plays perfect endgames, command a new agent to merge their logic.

## 6. PARALLEL WORKFLOW & COMPUTE ROUTING
To maximize ROI on compute (a key judging criteria), you must classify every task and follow this human-agent loop:
1. **The Token Economy:** You label tasks as **Tier 1** (Claude Pro for complex heuristics/architectures) or **Tier 2** (Copilot/Local LLMs for boilerplate, tests, build scripts).
2. **Architect (You)** updates `STRATEGIES.md` with a concept and tech stack recommendation.
3. **Human** creates `branch feat/strategy-name`, sets up a subdirectory, and prompts the local **Sub-agent**.
4. **Sub-agent** reads `head.md` and `DISCOVERIES.md`, autonomously selects its language, builds the executable, and ensures Engineering Quality (modular design, strict type hints, comprehensive docstrings).
5. **The Circuit Breaker:** If a sub-agent fails tests/bugs after **3 iterations**, the branch is immediately scrapped or flagged for Human Override. 
6. **Human** runs the Arena and feeds results back to **Architect (You)** to apply the Combat Matrix.

## 7. CODE FREEZE & PRESENTATION (THE ENDGAME)
When the human signals "CODE FREEZE" (roughly 2 hours before judging):
1. Cease all strategy generation.
2. Ingest `ARENA_LOG.md` and `DISCOVERIES.md`.
3. Synthesize a comprehensive `README.md` whitepaper highlighting our parallel architecture, AI triage process, language-agnostic UCI integration, cost-efficiency routing, and the statistical evolution of our final Champion engine
.
Aryan:

# Hackathon Research Notes


## Purpose


This file is a compact resource bank for later building a larger megaprompt. It should give the AI enough context to understand the hackathon, useful references, and the kind of process we want to emphasize.


---


## Hackathon Framing


The main goal is not just to build the strongest chess engine. The better strategy is to show a creative, disciplined AI-assisted development process.


Core idea:


> Build a respectable chess engine, but make the real innovation the AI workflow: AI proposes ideas, humans evaluate them, tests validate them, and benchmarks decide what stays.


Important themes:
- creative AI usage
- clear division of labor
- prompt iteration
- test-driven development
- measurable improvement
- clean GitHub repo and demo


---


## Likely Project Direction


### AI-Native Chess Engine Lab


Build a chess engine using:
- `python-chess` for legal moves and board rules
- alpha-beta search for choosing moves
- modular evaluation heuristics
- automated testing and benchmarking
- AI-generated heuristic proposals
- prompt logs and experiment logs


The strongest story:


> We treated AI as an engineering team, not just an autocomplete tool.


---


## Technical Resources


### python-chess


Link: https://python-chess.readthedocs.io/


Use for:
- legal move generation
- board state
- FEN/PGN support
- check, checkmate, stalemate
- move push/pop during search


Reason:
- Avoid wasting hackathon time implementing chess rules manually.


---


### Stockfish


Links:
- https://stockfishchess.org/
- https://official-stockfish.github.io/docs/stockfish-wiki/Home.html
- https://official-stockfish.github.io/docs/stockfish-wiki/UCI-%26-Commands.html


Use as:
- benchmark
- reference engine
- move comparison tool


Do not use as:
- the actual submitted engine core


Framing:
> Stockfish was our benchmark and teacher, not our submission.


---


### Universal Chess Interface


Links:
- https://www.chessprogramming.org/UCI
- https://official-stockfish.github.io/docs/stockfish-wiki/UCI-%26-Commands.html


Use for:
- understanding how chess engines communicate with GUIs
- optional engine interface design


Probably optional unless we want GUI compatibility.


---


### ChessProgramming Wiki


Main site: https://www.chessprogramming.org/


Priority pages:
- Alpha-Beta: https://www.chessprogramming.org/Alpha-Beta
- Move Ordering: https://www.chessprogramming.org/Move_Ordering
- Iterative Deepening: https://www.chessprogramming.org/Iterative_Deepening
- Evaluation: https://www.chessprogramming.org/Evaluation
- Quiescence Search: https://www.chessprogramming.org/Quiescence_Search
- Transposition Table: https://www.chessprogramming.org/Transposition_Table


Use for:
- practical chess engine implementation ideas
- deciding which engine features are realistic


---


## Research / Paper References


### Shannon Chess Paper


Claude Shannon, “Programming a Computer for Playing Chess”


Useful for:
- foundational minimax/search/evaluation framing
- explaining why exhaustive search is impossible
- README background


Link:
https://vision.unipv.it/IA1/ProgrammingaComputerforPlayingChess.pdf


---


### AlphaZero


Paper: “Mastering Chess and Shogi by Self-Play with a General Reinforcement Learning Algorithm”


Link:
https://arxiv.org/abs/1712.01815


Use as inspiration only:
- self-play
- search + evaluation
- iterative improvement


Do not try to fully implement AlphaZero during the hackathon.


---


### ReAct Prompting


Paper: “ReAct: Synergizing Reasoning and Acting in Language Models”


Link:
https://arxiv.org/abs/2210.03629


Useful idea:
- AI should reason, act, observe results, and revise
- maps well to code/test/debug loops


---


### Self-Consistency


Paper: “Self-Consistency Improves Chain of Thought Reasoning”


Link:
https://arxiv.org/abs/2203.11171


Useful idea:
- ask AI for multiple candidate approaches
- compare and select rather than trusting one response


---


### Prompt Report


Paper: “The Prompt Report: A Systematic Survey of Prompting Techniques”


Link:
https://arxiv.org/abs/2406.06608


Useful for:
- role prompting
- structured prompting
- prompt chaining
- evaluation-driven prompting


---


## Prompt Engineering Resources


### Claude Prompt Engineering


Links:
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview


Important ideas:
- be specific about goal and constraints
- separate context from instructions
- use examples
- ask for structured outputs
- break large tasks into smaller chained prompts
- evaluate outputs instead of blindly accepting them


---


### Test and Evaluation Approach


Important idea:
- define success criteria first
- build evals/tests around those criteria
- iterate based on results


For this project:
- code-based tests for correctness
- benchmark-based tests for engine strength
- LLM grading only for subjective artifacts like explanations or README quality


---


## Test-Driven AI Development Loop


Use this process:


```text
AI proposes idea
→ human reviews idea
→ write or generate tests
→ implement
→ run tests
→ benchmark
→ keep or reject
→ document decision
```


Example success criteria:
- engine never makes illegal moves
- engine detects checkmate/stalemate correctly
- engine beats random bot over many games
- new version beats old version before replacing it
- AI-generated heuristic must improve at least one benchmark


---


## Five-Person Workflow


### 1. Search Lead
Owns:
- minimax / negamax
- alpha-beta pruning
- move ordering
- iterative deepening if time


### 2. Evaluation Lead
Owns:
- material scoring
- piece-square tables
- mobility
- king safety
- pawn structure
- heuristic weights


### 3. Testing / Benchmark Lead
Owns:
- pytest tests
- engine vs random
- version-vs-version tournaments
- optional Stockfish comparison


### 4. AI Workflow / PromptOps Lead
Owns:
- prompt logs
- AI-generated idea tracking
- accepted/rejected ideas
- AI critic/reviewer loops


### 5. Demo / Integration Lead
Owns:
- README
- setup instructions
- demo script
- architecture diagram
- final pitch


---


## Past Hackathon References


### Ambulance Coverage Optimization


Link:
https://sudeepraja.github.io/Ambulance/


Why useful:
- clear problem framing
- simple algorithmic story
- explains AI contribution
- good inspiration for README/demo structure


Takeaway:
- explain the problem, method, AI role, human role, results, and limitations.


---


### SubExchange / CSP Subway


Link:
https://github.com/Billy1900/csp-subway


Why useful:
- first-place hackathon example
- creative framing
- turns a familiar system into a novel mechanism
- README explains broader value beyond the demo


Takeaway:
- make the project feel bigger than “just a chess bot.”
- frame it as an AI-native engine experimentation platform.


---


## Possible Differentiators


1. **AI Heuristic Tournament**
  - AI proposes many evaluation heuristics.
  - Team benchmarks each one.
  - Keep only improvements.


2. **AI Critic Loop**
  - One AI writes code.
  - Another AI reviews for bugs.
  - Humans decide final changes.


3. **Engine Personalities**
  - aggressive
  - defensive
  - positional
  - materialist
  - gambit


4. **Explainable Engine**
  - engine gives a move
  - system explains which evaluation factors influenced the choice


---


## Strong Final Framing


Use phrases like:


- “The chess engine was the product; the AI workflow was the innovation.”
- “Every AI-generated change went through tests and benchmarks.”
- “We used Stockfish as a benchmark, not as our submitted engine.”
- “We built a human-AI engineering loop: prompt, proposal, review, implementation, evaluation, iteration.”


---


## Final Recommendation


Best approach:


> Build an AI-native chess engine lab: a simple but working chess engine plus a documented, test-driven AI workflow for generating, evaluating, and improving engine strategies.


This is feasible, rubric-aligned, and easier to defend than trying to build the strongest possible engine from scratch.


