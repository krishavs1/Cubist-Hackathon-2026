Initial Prompting:

I am currently at a hackathon for Cubist Technologies. Our task is to simply build a chess engine using AI. We are currently brainstorming possible routes to make the most interesting engine that will impress the judges. Please think of some ideas based on the slideshow pictures I inputted, and optimize for the rubric.

After speaking with a dev, I learned that they only care about how we use AI + how we used Claude to parallelize our work and all work on stuff at the same time. We are looking to just create a chess engine that is a distilled version of stockfish(similar to how Deepseek is a distilled version of ChatGPT). We also are thinking of adding a step that allows the engine to compare different strategies(similar to idea 1). However, the more important thing is how we actually go about using AI and how we work together with separate claude agents. We are also thinking of some way to have AI brainstorm multiple ideas and score these ideas based on how effective they are and in the end, pick the most efficient strategy. Can you make sense of all these ideas and give some sort of feedback.

Overall Plan: 

---

**STEP 0: Build the Mega Prompt**

One person (or collaboratively) assembles a single, comprehensive markdown prompt file that gives any team member (or Claude agent) all the context needed to independently propose a strong chess engine strategy. This file should include:

- Full hackathon context: what Cubist cares about (AI usage, Claude parallelization, multi-agent collaboration)
- The core goal: a distilled chess engine (Stockfish-inspired) built with AI
- Key constraints: time, team size (5), judging rubric criteria
- Background on the two main technical directions being considered:
  1. Strategy comparison loop — engine evaluates multiple move strategies and scores them
  2. Distillation approach — use a strong existing engine (Stockfish) as a teacher for a leaner AI model
- Relevant technical context: what tools/models are available (Claude API, Python, etc.)
- A clear ask: "Given all of the above, propose a complete end-to-end strategy for building this chess engine, including architecture, AI usage patterns, and how the team can work in parallel."

The output of Step 0 is a single file (e.g. `mega_prompt.md`) that anyone can paste into Claude and immediately get a coherent, well-informed strategy back.

---

**STEP 1: 5 Parallel Strategies**

Each of the 5 team members independently feeds the mega prompt into Claude (or their own reasoning) and produces a distinct strategy doc. Each strategy should cover:

- High-level architecture of the engine
- How AI/Claude is used (training, inference, multi-agent orchestration, etc.)
- How the distillation from Stockfish works
- How move strategies are generated and evaluated
- Parallelization plan — what each team member builds simultaneously
- Estimated complexity and feasibility within the hackathon timeframe

The goal is divergence — each person should try to push in a different direction rather than converge prematurely. At the end of Step 1, the team has 5 distinct strategy documents.

---

**STEP 2: Benchmark & Synthesize**

Develop a rubric to score each of the 5 strategies and extract the best ideas into one final unified plan. The benchmark should evaluate each strategy across dimensions like:

- **Impressiveness to judges**: How clearly does this demonstrate novel AI usage and Claude parallelization?
- **Technical feasibility**: Can this realistically be built in the hackathon window?
- **Distillation quality**: How well does the engine learn from Stockfish?
- **Multi-agent design**: Does the architecture show meaningful collaboration between Claude agents?
- **Strategy evaluation loop**: Is there a mechanism for the engine to score and select between competing move strategies?
- **Code parallelizability**: Can all 5 team members contribute simultaneously without blocking each other?

Each strategy gets scored per dimension. Then, rather than picking one winner wholesale, the team identifies the strongest element of each strategy and assembles a hybrid final plan — the best architecture from one, the best multi-agent design from another, etc.

The output of Step 2 is a single `final_strategy.md` that the whole team aligns on before building.

---