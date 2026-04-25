# STRATEGY: TOY-TO-SCALE (EVOLUTIONARY COMPLEXITY)

## 1. OBJECTIVE
Build a sequence of increasing complexity. This workstream tests whether starting with a "Toy" version (random moves) and scaling up reduces the total token cost and error rate.

## 2. TECHNICAL REQUIREMENTS
- **Language:** Python 3.x
- **Evolutionary Path:** 
  1. Random Mover (UCI skeleton)
  2. Greedy Material Capturer (Depth 1)
  3. Minimax (Depth 2)
  4. NegaMax with Alpha-Beta (Final)

## 3. SUBAGENT INSTRUCTIONS
1.  Establish the UCI skeleton first.
2.  Commit each "Evolution" step to the directory.
3.  Log the cost (tokens) for each scaling step in `DISCOVERY.md`.
