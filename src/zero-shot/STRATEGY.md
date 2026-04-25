# STRATEGY: ZERO-SHOT (CONTROL GROUP)

## 1. OBJECTIVE
Implement a fully functional UCI chess engine in a single interaction. This workstream tests the baseline capability of the LLM to generate complex, stateful logic without iterative feedback.

## 2. TECHNICAL REQUIREMENTS
- **Language:** Python 3.x
- **Library:** `python-chess` for rule enforcement.
- **Search:** NegaMax with Alpha-Beta pruning (Depth 3+).
- **Evaluation:** Material weights only (P:100, N:320, B:330, R:500, Q:900, K:20000).

## 3. SUBAGENT INSTRUCTIONS
1.  Read `ARCHITECTURE.md` and `DISCOVERY_SCHEMA.md`.
2.  Implement `engine.py` in a single interaction.
3.  Fulfill the `build.sh` and `run.sh` contract in `src/zero-shot/engine/`.
4.  Log any initial syntax or UCI errors in `DISCOVERY.md` exactly as they occur.
