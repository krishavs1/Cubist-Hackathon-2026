"""Checkers evaluator.

Same interface as the Tic-Tac-Toe and chess evaluators::

    evaluate(game, ply=0) -> int      # from the maximizer's (Red's) POV
    WIN_SCORE                         # constant used by search for +/- inf

Components:
- Material (man=100, king=160).
- Advancement piece-square table for men (closer to king row = worth more).
- Centralization table for kings.
- Small mobility bonus as a tie-breaker.
- Depth-adjusted mate scoring (same ``+/- WIN_SCORE -/+ ply`` trick used on
  Tic-Tac-Toe and chess, so the engine prefers faster wins and slower losses).
"""

from __future__ import annotations

from typing import List, Tuple

from .game import (
    BLACK,
    BLACK_KING,
    BLACK_MAN,
    CheckersGame,
    EMPTY,
    RED,
    RED_KING,
    RED_MAN,
)


WIN_SCORE = 100_000

MAN_VALUE = 100
KING_VALUE = 160


# Row-indexed advancement bonus for a Red man. Checkers advancement only
# depends on how far a man has walked toward its king row, so a 1-D table is
# both simpler *and* intrinsically color-symmetric (earlier I used 2-D PSTs
# and the dark/light column parity flipped between rows, which put the
# bonuses on squares men never sit on).
#
# Row 0 is Red's king row (men never sit there as men).
# Row 7 is Red's back rank — small bonus to reward keeping anchors early.
_MAN_ADVANCEMENT_RED_BY_ROW: tuple = (0, 40, 28, 20, 14, 8, 4, 6)

# Black is the vertical mirror.
_MAN_ADVANCEMENT_BLACK_BY_ROW: tuple = tuple(reversed(_MAN_ADVANCEMENT_RED_BY_ROW))


# King centralization table: kings prefer the middle, away from corners.
_KING_PST: List[List[int]] = [
    [-12, 0, -6, 0, -6, 0, -6, -12],
    [  0, 4,  0, 6,  0, 6,  0,   0],
    [ -6, 0,  8, 0,  8, 0,  8,  -6],
    [  0, 6,  0, 10, 0, 10, 0,   6],
    [  0, 6,  0, 10, 0, 10, 0,   6],
    [ -6, 0,  8, 0,  8, 0,  8,  -6],
    [  0, 4,  0, 6,  0, 6,  0,   0],
    [-12, 0, -6, 0, -6, 0, -6, -12],
]


def evaluate(game: CheckersGame, ply: int = 0) -> int:
    """Return a score in centipawn-ish units from Red's perspective.

    ``ply`` is plies-from-root; used for the faster-win / slower-loss
    adjustment on mate scores, same as in the TTT evaluator.
    """
    # Draws are a first-class terminal outcome here (the 40-move rule).
    if game.halfmove_clock >= game.DRAW_HALFMOVES:
        return 0

    legal = game.get_legal_moves()
    if not legal:
        # Side to move has no legal moves → they lose.
        if game.current_player() == RED:
            return -WIN_SCORE + ply
        return WIN_SCORE - ply

    score = 0
    board = game.board
    for r in range(8):
        row = board[r]
        for c in range(8):
            piece = row[c]
            if piece == EMPTY:
                continue
            if piece == RED_MAN:
                score += MAN_VALUE + _MAN_ADVANCEMENT_RED_BY_ROW[r]
            elif piece == RED_KING:
                score += KING_VALUE + _KING_PST[r][c]
            elif piece == BLACK_MAN:
                score -= MAN_VALUE + _MAN_ADVANCEMENT_BLACK_BY_ROW[r]
            elif piece == BLACK_KING:
                score -= KING_VALUE + _KING_PST[r][c]

    # Mobility tie-breaker. ``legal`` already reflects forced captures, so
    # when capture-heavy lines are available this gives a large swing in the
    # right direction for free.
    mobility = len(legal)
    if game.current_player() == RED:
        score += mobility
    else:
        score -= mobility

    return score
