# TOKEN_USAGE — OneShotOpus

**Model:** `claude-opus-4-7`  
**Methodology:** One-Shot (single conversational turn, no iteration)  
**Date:** 2026-04-25

---

## Prompt

> "Add a OneShotOpus folder in Cubist-Hackathon. Build a well-performing mvp for a chess engine using python chess and UCI guidelines"

~33 input tokens (user prompt only).

---

## Token Breakdown

Token estimates use the ~4 chars/token heuristic for Python/English mixed content.

### Input Tokens

| Source | Chars | Est. Tokens |
|--------|-------|-------------|
| User prompt | 133 | ~33 |
| `Cubist-Hackathon-2026/README.md` (read for context) | ~3,400 | ~850 |
| `OneShotHaiku/chess_engine.py` (read as reference) | 5,760 | ~1,440 |
| `OneShotHaiku/search.py` (read as reference) | 4,716 | ~1,179 |
| `OneShotHaiku/evaluation.py` (read as reference) | 4,599 | ~1,150 |
| Shell output / tool results | ~500 | ~125 |
| **Total Input** | | **~4,777** |

### Output Tokens

| File | Lines | Chars | Est. Tokens |
|------|-------|-------|-------------|
| `evaluation.py` | 194 | 6,921 | ~1,730 |
| `search.py` | 356 | 12,688 | ~3,172 |
| `engine.py` | 209 | 6,779 | ~1,695 |
| `README.md` | 52 | 1,841 | ~460 |
| `run.sh` | 4 | 185 | ~46 |
| `requirements.txt` | 1 | 19 | ~5 |
| Chat commentary & debugging | — | ~1,500 | ~375 |
| **Total Output** | **816** | **29,933** | **~7,483** |

### Summary

| | Tokens |
|---|---|
| Input | ~4,777 |
| Output | ~7,483 |
| **Total** | **~12,260** |

---

## Files Generated

| File | Purpose |
|------|---------|
| `engine.py` | UCI driver — command parsing, time management, threaded search dispatch |
| `search.py` | Negamax + alpha-beta, iterative deepening, quiescence, TT, null-move, LMR, move ordering |
| `evaluation.py` | Tapered material + PeSTO piece-square tables (mg/eg blend), bishop pair, tempo |
| `README.md` | Feature overview and usage guide |
| `run.sh` | Launcher for cutechess-cli / GUI integration |
| `requirements.txt` | `python-chess>=1.10` |

**Total Python code:** 759 lines / 26,388 bytes across 3 source files.

---

## Algorithm Features per Token

Algorithms packed into ~7,483 output tokens:

- Negamax with fail-hard alpha-beta
- Iterative deepening (depths 1–64) with soft/hard time management
- Quiescence search with stand-pat and delta pruning
- Transposition table (Zobrist hash, EXACT/LOWER/UPPER bounds, ply-adjusted mate scores)
- Null-move pruning (R=2–3, disabled in check / pawn-only positions)
- Late move reductions on quiet moves
- Check extensions
- Move ordering: TT move → MVV-LVA → queen promotions → killer heuristic → history heuristic
- Tapered evaluation with 12 PeSTO piece-square tables (middlegame + endgame per piece)
- Bishop pair and tempo bonuses
- Phase-weighted score interpolation

**Depth reached from startpos:** 7 plies in 1.5 seconds (~30,000 nodes/sec)
