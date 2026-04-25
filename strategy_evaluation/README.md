# Strategy Evaluation Framework

## What This Is

We ran four parallel AI engineering strategies to build chess engines and needed a principled way to compare them — not just on raw chess strength, but on the full picture: how much it cost to build, how much it will cost to improve, and how well the methodology itself holds up against the hackathon's judging criteria.

This folder documents that evaluation framework end to end.

## The Four Strategies

| Strategy | Methodology in one sentence |
|---|---|
| **Strategy1** | Darwinian AI loop — generate multiple AI evaluation personalities, pit them in automated tournaments, keep survivors, feed losses back to Claude via Reflexion |
| **OneShotOpus** | Single prompt to Claude Opus 4.7 — no iteration, no tests, just ask for a full engine and accept what comes back |
| **TDD** | Test-Driven Development — write failing tests first, use AI to build implementations that make them pass, benchmark every change before accepting it |
| **chess-ttt** | Game-agnostic scaling — build a verified Tic-Tac-Toe engine, scale the same search core to Checkers, then scale again to Chess |

## Files in This Folder

| File | What it covers |
|---|---|
| `README.md` | This overview |
| `SCORING_FORMULA.md` | Full explanation of the six factors, how each is measured, how normalization works, and why the weights are what they are |
| `RESULTS.md` | The computed scores, factor-by-factor breakdown, final ranking, and key takeaways |

## The Short Answer

**Strategy1 scores highest (0.789/1.0)** and is the recommended strategy to build on. The full reasoning is in `RESULTS.md`.

The scoring uses six factors weighted 25/20/20/15/10/10. The first four factors — calibrated Elo, cross-validation performance, MVP build cost, and optimization cost — carry 80% of the total score because engine strength and compute efficiency are the primary axes that determine which methodology is worth scaling.
