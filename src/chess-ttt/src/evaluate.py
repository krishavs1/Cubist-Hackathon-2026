"""Chess evaluation function.

Same shape as the Tic-Tac-Toe evaluator: `evaluate(game, ply) -> int`,
returning a score from the maximizer's (White's) perspective. Mate scores
are depth-adjusted so the engine prefers faster mates and slower losses,
exactly as in Tic-Tac-Toe.

Components:
- Material balance (centipawns)
- Piece-square tables (PSTs) — small positional adjustments
- Mobility bonus (legal-move count) as a tie-breaker

This is intentionally a basic evaluator; it is *not* meant to play strong
chess. It is meant to verify that the verified search architecture
transfers cleanly. Strength would come from a stronger evaluator and from
search extensions (move ordering, transposition tables, quiescence) — none
of which are required to validate the architecture.
"""

from __future__ import annotations

import chess

from .game import ChessGame


# WIN_SCORE is exposed under the same name as in the TTT evaluator so the
# search module can import it identically. Value is centipawns; chosen big
# enough to dominate any positional score the evaluator can return.
WIN_SCORE = 100_000


# --- Material values (centipawns) ------------------------------------------

PIECE_VALUES = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:   0,    # king's value is irrelevant; capture is illegal
}


# --- Piece-square tables ---------------------------------------------------
# Tables are written from White's perspective with rank 1 at the bottom.
# python-chess square indexing puts a1 = 0 and h8 = 63, so the table below
# is laid out with index 0 = a8 (top-left when written out) for readability;
# we map to python-chess indexing below. We use chess.square_mirror() for
# the Black perspective.
#
# Values are small (in centipawns) — a pawn on its starting square is 0,
# pushed to the center is +20 or so. These are standard "simplified
# evaluation function" tables (Tomasz Michniewski).

_PAWN_PST = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
]
_KNIGHT_PST = [
   -50,-40,-30,-30,-30,-30,-40,-50,
   -40,-20,  0,  0,  0,  0,-20,-40,
   -30,  0, 10, 15, 15, 10,  0,-30,
   -30,  5, 15, 20, 20, 15,  5,-30,
   -30,  0, 15, 20, 20, 15,  0,-30,
   -30,  5, 10, 15, 15, 10,  5,-30,
   -40,-20,  0,  5,  5,  0,-20,-40,
   -50,-40,-30,-30,-30,-30,-40,-50,
]
_BISHOP_PST = [
   -20,-10,-10,-10,-10,-10,-10,-20,
   -10,  0,  0,  0,  0,  0,  0,-10,
   -10,  0,  5, 10, 10,  5,  0,-10,
   -10,  5,  5, 10, 10,  5,  5,-10,
   -10,  0, 10, 10, 10, 10,  0,-10,
   -10, 10, 10, 10, 10, 10, 10,-10,
   -10,  5,  0,  0,  0,  0,  5,-10,
   -20,-10,-10,-10,-10,-10,-10,-20,
]
_ROOK_PST = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0,
]
_QUEEN_PST = [
   -20,-10,-10, -5, -5,-10,-10,-20,
   -10,  0,  0,  0,  0,  0,  0,-10,
   -10,  0,  5,  5,  5,  5,  0,-10,
    -5,  0,  5,  5,  5,  5,  0, -5,
     0,  0,  5,  5,  5,  5,  0, -5,
   -10,  5,  5,  5,  5,  5,  0,-10,
   -10,  0,  5,  0,  0,  0,  0,-10,
   -20,-10,-10, -5, -5,-10,-10,-20,
]
_KING_PST = [
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -20,-30,-30,-40,-40,-30,-30,-20,
   -10,-20,-20,-20,-20,-20,-20,-10,
    20, 20,  0,  0,  0,  0, 20, 20,
    20, 30, 10,  0,  0, 10, 30, 20,
]

PST = {
    chess.PAWN:   _PAWN_PST,
    chess.KNIGHT: _KNIGHT_PST,
    chess.BISHOP: _BISHOP_PST,
    chess.ROOK:   _ROOK_PST,
    chess.QUEEN:  _QUEEN_PST,
    chess.KING:   _KING_PST,
}


def _pst_value(piece_type: int, square: int, color: chess.Color) -> int:
    """Look up a PST value for a piece on a square, from White's perspective.

    The tables above are indexed 0..63 with index 0 = a8, 7 = h8, 56 = a1,
    63 = h1 — the natural reading order of a chessboard written with White
    at the bottom. python-chess uses index 0 = a1, 63 = h8. We translate.
    For Black we mirror the square vertically so the same table applies.
    """
    if color == chess.WHITE:
        # python-chess square -> table index
        # python-chess: rank = square // 8, file = square % 8, rank 0 = rank 1
        # table:        rank 0 of table = rank 8, file unchanged
        # so table_index = (7 - rank) * 8 + file
        rank = chess.square_rank(square)
        file = chess.square_file(square)
        idx = (7 - rank) * 8 + file
    else:
        mirrored = chess.square_mirror(square)
        rank = chess.square_rank(mirrored)
        file = chess.square_file(mirrored)
        idx = (7 - rank) * 8 + file
    return PST[piece_type][idx]


# --- Public evaluation -----------------------------------------------------


def evaluate(game: ChessGame, ply: int = 0) -> int:
    """Return a score in centipawns from White's perspective.

    `ply` is plies-from-root; used for depth-adjusted mate scoring so that
    faster mates score higher (and slower losses score higher / less
    negative), exactly as in the Tic-Tac-Toe evaluator.
    """
    # Terminal handling first. python-chess distinguishes the kinds of draws
    # we care about; mate is signed depending on whose turn it is to move.
    if game.is_checkmate():
        # The side to move has been checkmated and lost.
        if game.current_player() == chess.WHITE:
            return -WIN_SCORE + ply        # White is mated -> bad for White
        else:
            return WIN_SCORE - ply         # Black is mated -> good for White
    if game.is_stalemate() or game.is_draw_by_rule():
        return 0

    board = game.board
    score = 0

    # Material + PST in one piece-map pass.
    for square, piece in board.piece_map().items():
        value = PIECE_VALUES[piece.piece_type]
        positional = _pst_value(piece.piece_type, square, piece.color)
        if piece.color == chess.WHITE:
            score += value + positional
        else:
            score -= value + positional

    # Mobility: small bonus per legal move, signed by side to move. Cheap
    # tie-breaker that nudges the engine to develop pieces. We measure both
    # sides' mobility by temporarily flipping turn — but doing that is
    # surprisingly expensive (it interacts with castling-rights bookkeeping
    # in python-chess). Instead, count only the side to move's mobility and
    # let the search's depth supply the symmetry — at ply N+1 the other
    # side's mobility is what's measured.
    mobility = board.legal_moves.count()
    if board.turn == chess.WHITE:
        score += mobility
    else:
        score -= mobility

    return score
