# Subagent Discovery Schema

All methodology subagents MUST maintain a `DISCOVERY.md` file in their root directory following this exact template. This file is parsed by the `mes_calculator.py` to determine methodology performance.

---
```yaml
Engine_Name: "[String]"
Tech_Stack: "[e.g. Python, Rust, C++]"
Elo_Delta: [Float] # Calculated by grade.py
Nodes_Per_Sec: [Integer] # Reported by engine
Total_Tokens_Used: [Integer]
Cost_USD: [Float]
```
---

## 1. Methodology Overview
Briefly describe the prompting strategy used (e.g., TDD, Megaprompt).

## 2. Failures & Hallucinations
| Timestamp | Error Type | Description | Correction Attempt | Result |
|-----------|------------|-------------|--------------------|--------|
| HH:MM     | [Logic/Syntax/UCI] | [Specific error] | [Prompt used to fix] | [Fixed/Abandoned] |

## 3. Engineering Quality Metrics
- **Cyclomatic Complexity Estimate:**
- **Search Depth Stability:**
- **Memory Consumption (Peak):**
