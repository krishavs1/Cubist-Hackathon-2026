# Reflexion Cycle 1 — Analysis of `positional_grinder` Losses

**Analyst:** Claude (via Cursor IDE, 2026-04-25)
**Source PGNs:** `pgns/engine_vs_stockfish-skill-1_game{1,2,3,4,5}.pgn`
**Losing evaluator:** `positional_grinder`

This is the artifact of one complete Reflexion cycle — an AI agent (Claude)
read the champion's loss PGNs and proposed a corrected evaluator. The fix
is implemented as `reflexion_v1` in `engines/mve/heuristics.py`.

---

## Observed Failure Modes

### 1. No concept of piece development

Across all 5 loss games, the engine makes 5–7 opening moves with the
**same piece** while leaving other pieces on their starting squares.

- **Game 1:** `1.Nh3 2.Ng5 3.Rg1 4.Rh1` — Knight + rook shuffled to rim; queenside undeveloped; engine is mated on move 13.
- **Game 3:** `2.Bb5 3.Bc4 4.Bd5 5.Bc4 6.Bb3 7.Qf3 8.Ba4 9.Bb3` — Same bishop moved **7 times** in the opening.
- **Game 5:** `2.Bb5 3.Bc4 4.Bd3 5.Be2 6.Bh5 7.Bg4 8.Bxh5 9.Bf3` — Bishop again moved 7 times, never castled, king stuck on e1, mated on move 33.

### 2. No king-safety via castling

In all 5 games, the losing side never castled. The king remained on
e1 / e8 for the entire game. Stockfish exploited this by opening central
lines and delivering a central-file checkmate.

### 3. Knight-on-rim weakness

Knights wander to a-file or h-file squares (`Nh3, Nh6, Ng4, Nf4`) without
any central purpose. "A knight on the rim is dim."

### 4. Repeated-move tempo loss

The engine moves the same piece back and forth (`Kf8→Kg8→Kf8→Kg8` in
Game 2). It has no penalty for re-moving a piece in the opening.

---

## Root Cause in `positional_grinder`

Looking at the source (`heuristics.py:142-166`), `positional_grinder` scores:
- Material
- Center-square *attack* (is e4/d4/e5/d5 attacked?)
- Extended-center *piece presence*
- Pawn shield around the king

It does **NOT** score:
- Whether minor pieces have moved off their starting squares
- Whether the king has castled
- Where on the board minor pieces actually sit
- Tempo (moving the same piece twice)

The evaluator is statically correct but dynamically blind — it will reward
a knight that attacks e5 equally whether it sits on f3 (good) or h3 (bad).

---

## Correction Philosophy (→ `reflexion_v1`)

The new evaluator inherits everything `positional_grinder` does and adds:

1. **Development bonus** — big bonus for each minor piece that has moved off
   its starting square during the opening/middlegame.
2. **Castling bonus** — large fixed bonus if the king has castled; large
   penalty if it hasn't and it's past move 15.
3. **Knight-on-rim penalty** — knights on a/h files receive a penalty.
4. **Early queen penalty** — if the queen has moved from d1/d8 before 4
   minor pieces are developed, penalize it (this stops `Qf3` jumps).

The material-dominant invariant is preserved — all positional bonuses
together cap at ~120 cp, well below a pawn.

---

## Expected Outcome

`reflexion_v1` should:
- Beat `positional_grinder` head-to-head (direct fix of its blind spots)
- Tie or beat the other 6 personalities (they have the same blind spots
  to a lesser degree)
- Become the new Champion in `engine/run.sh` if it wins the round-robin

Result logged to `ARENA_LOG.md` under a `[REFLEXION]` tag.
