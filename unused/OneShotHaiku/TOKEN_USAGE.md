# TOKEN_USAGE — OneShotHaiku

**Model:** `claude-haiku-3-5` (claude-haiku-3-5-20241022)  
**Methodology:** One-Shot (single conversational turn, no iteration)  
**Date:** 2026-04-25

---

## Prompt

Reconstructed from project artifacts. Approximate prompt:

> "Build a well-performing MVP chess engine using python-chess and UCI guidelines. Include search, evaluation, UCI protocol, interactive mode, and tests."

~40 input tokens (user prompt only, no reference files consumed).

---

## Token Breakdown

Token estimates use the ~4 chars/token heuristic for Python/English mixed content.

### Input Tokens

| Source | Chars | Est. Tokens |
|--------|-------|-------------|
| User prompt (reconstructed) | ~160 | ~40 |
| Shell output / tool results | ~200 | ~50 |
| **Total Input** | | **~90** |

*Note: No reference files were read from the repo — Haiku generated all content from model knowledge alone.*

### Output Tokens

| File | Lines | Chars | Est. Tokens |
|------|-------|-------|-------------|
| `chess_engine.py` | 181 | 5,760 | ~1,440 |
| `search.py` | 173 | 4,716 | ~1,179 |
| `evaluation.py` | 166 | 4,599 | ~1,150 |
| `interactive.py` | 170 | 5,041 | ~1,260 |
| `test_engine.py` | 144 | 4,093 | ~1,023 |
| `ARCHITECTURE.md` | 294 | 8,794 | ~2,199 |
| `PROJECT_SUMMARY.txt` | 290 | 10,220 | ~2,555 |
| `README.md` | 148 | 3,662 | ~916 |
| `QUICKSTART.md` | 142 | 3,448 | ~862 |
| `run.sh` | 78 | 1,862 | ~466 |
| `requirements.txt` | 1 | 21 | ~5 |
| Chat commentary | — | ~1,200 | ~300 |
| **Total Output** | **1,787** | **53,416** | **~13,355** |

### Summary

| | Tokens |
|---|---|
| Input | ~90 |
| Output | ~13,355 |
| **Total** | **~13,445** |

---

## Files Generated

| File | Purpose |
|------|---------|
| `chess_engine.py` | UCI driver — command loop, board state, search dispatch |
| `search.py` | Minimax with alpha-beta pruning, transposition table, iterative deepening |
| `evaluation.py` | Material counting, piece-square tables, pawn structure, mobility |
| `interactive.py` | Human-vs-engine play interface with algebraic notation |
| `test_engine.py` | Validation suite covering positions, tactics, and UCI commands |
| `ARCHITECTURE.md` | Technical documentation — algorithms, data flow, design decisions |
| `QUICKSTART.md` | 5-minute getting-started guide |
| `README.md` | Feature overview, UCI command reference, installation |
| `PROJECT_SUMMARY.txt` | Deliverables checklist, performance estimates, usage examples |
| `run.sh` | Launcher script with path setup |
| `requirements.txt` | `python-chess==1.10.0` |

**Total Python code:** 834 lines / 24,209 bytes across 5 source files.

---

## Algorithm Features per Token

Algorithms packed into ~13,355 output tokens:

- Minimax with alpha-beta pruning (white-maximizing, black-minimizing frame)
- Move ordering: captures > checks > promotions > castling
- Transposition table (FEN-keyed dict, depth-bounded)
- Iterative deepening with time-based abort
- Material evaluation (standard piece values)
- Six static piece-square tables (one per piece type)
- Pawn structure penalty (doubled pawns)
- Mobility bonus (legal move count)
- Endgame-aware king table

**Notable absences vs. Opus:** No quiescence search, no null-move pruning, no LMR, no killer/history heuristics, no tapered (mg/eg blended) evaluation, FEN-string TT keys (slow) vs. Zobrist hashing.

**Depth reached from startpos:** 4 plies in ~5–10 seconds (default config)
