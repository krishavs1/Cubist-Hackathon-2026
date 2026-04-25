# STRATEGY: TEST-DRIVEN DEVELOPMENT (ENGINEERING RIGOR)

## 1. OBJECTIVE
Implement the engine by first writing a comprehensive test suite. This workstream evaluates the impact of regression testing and modular design on the final Elo and Iteration Friction.

## 2. TECHNICAL REQUIREMENTS
- **Language:** Python 3.x
- **Test Framework:** `pytest`
- **Search:** NegaMax with Alpha-Beta pruning.
- **Evaluation:** Material weights + simple mobility heuristic.

## 3. SUBAGENT INSTRUCTIONS
1.  Initialize a `tests/` directory.
2.  Write unit tests for: `handshake`, `legal_move_generation`, and `evaluation_consistency`.
3.  Implement `engine.py` logic only after tests are passing.
4.  Log all failed test iterations and their fixes in `DISCOVERY.md`.
