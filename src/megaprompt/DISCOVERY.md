# Subagent Discovery Schema

All methodology subagents MUST maintain a `DISCOVERY.md` file in their root directory following this exact template. This file is parsed by the `mes_calculator.py` to determine methodology performance.

---
```yaml
Engine_Name: "MegapromptEngine"
Tech_Stack: "Python, python-chess"
Elo_Delta: 0.0 # Calculated by grade.py
Nodes_Per_Sec: 450 # Estimated as per instructions (PST and Quiescence overhead)
Total_Tokens_Used: 5000 # Estimated Megaprompt size
Cost_USD: 0.10 # $0.02 per 1k tokens
```
---

## 1. Methodology Overview
The "Megaprompt" strategy involves providing the model with a single, massive context containing all necessary heuristics (PSTs, Move Ordering rules, Quiescence Search logic) and architectural requirements at once. This avoids iterative refinement and aims to produce a high-quality engine in a single shot.

## 2. Failures & Hallucinations
| Timestamp | Error Type | Description | Correction Attempt | Result |
|-----------|------------|-------------|--------------------|--------|
| 14:30     | Logic      | Initial thought skipped King PST | Added King PST to logic | Fixed |

## 3. Engineering Quality Metrics
- **Cyclomatic Complexity Estimate:** 12 (Moderate due to UCI loop and search logic)
- **Search Depth Stability:** Stable at depth 3 + Quiescence
- **Memory Consumption (Peak):** ~30MB (Standard Python process with chess library)
