# STRATEGY: MEGAPROMPT (KNOWLEDGE INJECTION)

## 1. OBJECTIVE
Use a massive, information-dense prompt to "over-engineer" the MVP. This workstream tests whether providing specific heuristics (PSTs, Move Ordering) in the initial prompt results in a higher Elo/Cost ratio.

## 2. TECHNICAL REQUIREMENTS
- **Language:** Python 3.x
- **Injected Heuristics:**
  - Piece-Square Tables (PST) for all pieces.
  - Basic Move Ordering (Captures first).
  - Quiescence Search (Simple).

## 3. SUBAGENT INSTRUCTIONS
1.  Construct a single "Megaprompt" containing all technical heuristics.
2.  Implement the entire engine in one interaction based on the Megaprompt.
3.  Log the exact token count of the Megaprompt in `DISCOVERY.md`.
