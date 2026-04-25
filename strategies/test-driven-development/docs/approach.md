# Test-Driven AI Engineering — A Chess Engine Case Study

---

## The Methodology

The core idea is simple: AI should be a disciplined engineering collaborator, not just a code generator. That means before any feature gets committed, it has to earn its place through a defined loop.

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   Define Success        Write the         Generate             │
│     Criteria    ──────►  Test First  ────► Implementation      │
│                                                                 │
│        ▲                                       │               │
│        │                                       ▼               │
│     Iterate             Benchmark           Tests              │
│     Feature   ◄──────   for Impact  ◄────   Pass              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

The loop starts with defining what success looks like before a single line of implementation is written. That definition becomes a test — a concrete, executable specification. Only then is AI used to generate the implementation. If the tests pass, the feature moves to benchmarking, where its real-world impact is measured against a known reference. If the numbers improve, it gets committed. If they don't, the iteration continues.

What makes this different from typical AI-assisted development is the direction. Most workflows start with code and ask whether it works afterward. This one starts with the question of what "working" even means, and uses that answer to constrain everything that follows. The AI writes the implementation — but the tests and benchmarks decide whether it was right.

---

## What We Built

The engine is built in Python using `python-chess` for move generation, with all chess logic handled in three layers.

The first layer is evaluation. Given any board position, the evaluation function returns a score in centipawns — positive means white is winning, negative means black is winning. It combines raw material counts (a queen is worth 900 points, a pawn 100) with piece-square tables that reward positional play: knights score higher in the center, kings score higher behind a pawn shield. The starting position evaluates to exactly zero — a property verified by a test before the function was accepted.

The second layer is search. The engine uses a negamax algorithm with alpha-beta pruning, which systematically looks ahead several moves and picks the one that leads to the best position, assuming the opponent always plays optimally. Captures are searched first to focus computation where it matters most. Given a time budget, the engine uses iterative deepening — searching at depth 1, then 2, then 3, and so on — returning the best move found before time runs out.

The third layer is the UCI interface. UCI (Universal Chess Interface) is the standard protocol that chess engines use to communicate with GUIs and testing frameworks. The adapter handles commands like `position startpos moves e2e4` and responds with `bestmove g1f3`. Critically, the adapter is written to be I/O-free and directly unit-testable — the same code that runs in production is the code the tests exercise.

---

## The Results

The MVP was graded against Stockfish Skill Level 1, a fixed reference point calibrated at 1000 Elo, using the Fishtest trinomial model — the same statistical method used by the official Stockfish project. Across 50 games, the engine finished with a record of 7 wins, 34 losses, and 9 draws, producing a baseline rating of **790 Elo** with a 95% confidence interval of [669, 878].

The full test suite — 27 tests across evaluation, search, bot logic, and UCI parsing — runs in 0.05 seconds and passes cleanly. All 6 UCI conformance checks pass, meaning the engine can be dropped into any standard chess GUI or testing framework without modification.

The total AI inference cost to generate the MVP from scratch, including all iterations and fixes, was approximately 30,000 tokens — under $0.20.

---

## What Comes Next

The 790 Elo baseline is a starting point, not a ceiling. Each of the following improvements is a defined next iteration: a failing test written first, an implementation generated, and a re-grade run to measure the delta.

The single highest-impact addition is quiescence search. Right now, the engine evaluates positions at a fixed depth even if a capture sequence is still unfolding — it might think it's winning after taking a queen, not realizing the queen is immediately recaptured on the next move. Quiescence search extends the search until no captures remain before evaluating, eliminating this class of blunder. Alone, it is expected to add 100–150 Elo points.

Beyond that, a transposition table would cache positions the engine has already evaluated, effectively giving deeper search for free. Better move ordering, null move pruning, and improved evaluation terms for pawn structure and king safety each contribute smaller but compounding gains. Together, the full optimization roadmap is projected to bring the engine to roughly 1,100–1,300 Elo — a level competitive with casual to intermediate human players — at under $0.30 in additional AI compute.

The ceiling is ultimately set by Python's runtime speed, not the algorithms. A pure Python move generator is significantly slower than a native implementation, which caps how deep the engine can search within practical time controls. Pushing beyond ~1,300 Elo would require rewriting the core in a compiled language — a different project with a different scope.
