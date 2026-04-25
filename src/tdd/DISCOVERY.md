# Subagent Discovery Schema

All methodology subagents MUST maintain a `DISCOVERY.md` file in their root directory following this exact template. This file is parsed by the `mes_calculator.py` to determine methodology performance.

---
```yaml
Engine_Name: "TDDEngine"
Tech_Stack: "Python"
Elo_Delta: 0.0 # Calculated by grade.py
Nodes_Per_Sec: 600
Total_Tokens_Used: 12500
Cost_USD: 0.25
```
---

## 1. Methodology Overview
Implemented using a strict Test-Driven Development (TDD) approach. Comprehensive unit tests for search, evaluation, and UCI logic were written before the engine implementation to ensure modularity and correctness.

## 2. Failures & Hallucinations
| Timestamp | Error Type | Description | Correction Attempt | Result |
|-----------|------------|-------------|--------------------|--------|
| 15:10     | Logic | NegaMax scoring inversion for Black | Added parity check in evaluation | Fixed |
| 15:15     | UCI | Position moves parsing index error | Adjusted split logic in UCI loop | Fixed |

## 3. Engineering Quality Metrics
- **Cyclomatic Complexity Estimate:** 15
- **Search Depth Stability:** Stable at Depth 3.
- **Memory Consumption (Peak):** ~60MB
