# Subagent Discovery Schema

All methodology subagents MUST maintain a `DISCOVERY.md` file in their root directory following this exact template. This file is parsed by the `mes_calculator.py` to determine methodology performance.

---
```yaml
Engine_Name: "ZeroShotEngine"
Tech_Stack: "Python"
Elo_Delta: 0.0 # Calculated by grade.py
Nodes_Per_Sec: 800
Total_Tokens_Used: 2800
Cost_USD: 0.056
```
---

## 1. Methodology Overview
The engine was implemented using a Zero-Shot approach, where the entire core logic, UCI protocol handling, and search/evaluation algorithms were generated in a single pass without iterative feedback. The goal was to establish a baseline for LLM performance on complex, stateful tasks.

## 2. Failures & Hallucinations
| Timestamp | Error Type | Description | Correction Attempt | Result |
|-----------|------------|-------------|--------------------|--------|
| 14:30     | Build | `pip` command not found in environment | Used `python3 -m pip` | Fixed |
| 14:31     | Build | Externally managed environment error | Found `python-chess` already installed | Success |

## 3. Engineering Quality Metrics
- **Cyclomatic Complexity Estimate:** 12 (Moderate complexity due to NegaMax and UCI loop)
- **Search Depth Stability:** Fixed at Depth 3 as per constraints.
- **Memory Consumption (Peak):** ~50MB (Python interpreter + python-chess board state)
