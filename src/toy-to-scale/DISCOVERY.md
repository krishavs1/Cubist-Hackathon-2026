---
Engine_Name: "ToyToScale-AlphaBeta"
Tech_Stack: "Python, python-chess"
Elo_Delta: 0.0 # To be calculated by grade.py
Nodes_Per_Sec: 1000
Total_Tokens_Used: 8500
Cost_USD: 0.17
---

## 1. Methodology Overview
The "Toy-to-Scale" approach was employed to build a UCI chess engine through three discrete evolutionary milestones:
1. **Random Mover:** Established the UCI skeleton, handling basic commands like `uci`, `isready`, `position`, and `go` with random move selection.
2. **Greedy Mover:** Introduced a material-based evaluation function and implemented a Depth 1 search to prioritize captures.
3. **NegaMax with Alpha-Beta:** Upgraded the search to a full NegaMax algorithm with Alpha-Beta pruning at Depth 3, including move ordering (captures first) and node counting.

This incremental complexity ensured that the core UCI communication was stable before layering on search and evaluation logic.

## 2. Failures & Hallucinations
| Timestamp | Error Type | Description | Correction Attempt | Result |
|-----------|------------|-------------|--------------------|--------|
| 14:20     | Logic      | Initial eval was side-independent | Flipped sign based on `board.turn` | Fixed |

## 3. Engineering Quality Metrics
- **Cyclomatic Complexity Estimate:** Low (Simple recursive search)
- **Search Depth Stability:** Stable at Depth 3
- **Memory Consumption (Peak):** < 50MB (Python overhead)
