"""Chess evaluator — structurally the checkers evaluator with more pieces.

Same shape ``evaluate(game, ply) -> int`` and ``WIN_SCORE`` constant that
both the TTT and checkers evaluators export, so the inherited ``search.py``
keeps its contract. Returns centipawns from White's (the maximizer's)
perspective.

What iterates forward from the checkers evaluator:

    checkers                     chess (this file)
    -------------------------    --------------------------------
    man / king values          → PIECE_VALUES (6 piece types)
    advancement / king PST     → per-piece PSTs + *tapered* king PST
                                  (the king's "best square" depends on
                                  game phase in a way a checkers piece's
                                  doesn't — hence the midgame/endgame
                                  blend)
    mobility (side-to-move)    → same
    mate score ± ply           → same
    halfmove-clock draw        → python-chess terminals
    —                          → bishop pair bonus (new)
    —                          → doubled pawn penalty (new)

Those last two are the headline chess-specific additions: they exercise
the evaluator's extensibility without requiring a full tapered PeSTO.
"""

from __future__ import annotations

import chess

from .game import ChessGame


WIN_SCORE = 100_000


# --- Material (centipawns) -------------------------------------------------

PIECE_VALUES = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:   0,
}


# --- Piece-square tables ---------------------------------------------------
# Written from White's perspective with rank 8 at the top (natural chess
# reading order). ``_pst_value`` translates to python-chess's a1=0, h8=63
# indexing, and mirrors the square for Black.
#
# These are the standard Michniewski "simplified evaluation function"
# tables. They're used by every tutorial-grade chess engine because the
# numbers are sensible and the source is reproducible.

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

# Midgame king: want to tuck behind pawns on the back rank.
_KING_MG_PST = [
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -20,-30,-30,-40,-40,-30,-30,-20,
   -10,-20,-20,-20,-20,-20,-20,-10,
    20, 20,  0,  0,  0,  0, 20, 20,
    20, 30, 10,  0,  0, 10, 30, 20,
]

# Endgame king: want to march to the center to support pawns / deliver mate.
_KING_EG_PST = [
   -50,-40,-30,-20,-20,-30,-40,-50,
   -30,-20,-10,  0,  0,-10,-20,-30,
   -30,-10, 20, 30, 30, 20,-10,-30,
   -30,-10, 30, 40, 40, 30,-10,-30,
   -30,-10, 30, 40, 40, 30,-10,-30,
   -30,-10, 20, 30, 30, 20,-10,-30,
   -30,-30,  0,  0,  0,  0,-30,-30,
   -50,-30,-30,-30,-30,-30,-30,-50,
]

_PST_BY_TYPE = {
    chess.PAWN:   _PAWN_PST,
    chess.KNIGHT: _KNIGHT_PST,
    chess.BISHOP: _BISHOP_PST,
    chess.ROOK:   _ROOK_PST,
    chess.QUEEN:  _QUEEN_PST,
}


def _pst_index(square: int, color: chess.Color) -> int:
    """Map python-chess square (a1=0, h8=63) to table index (a8=0, h1=63).

    For Black, mirror the square vertically first so the same table works.
    """
    if color == chess.WHITE:
        rank = chess.square_rank(square)
        file = chess.square_file(square)
    else:
        mirrored = chess.square_mirror(square)
        rank = chess.square_rank(mirrored)
        file = chess.square_file(mirrored)
    return (7 - rank) * 8 + file


# --- Game phase for tapered king PST ---------------------------------------

# Phase weights. Summing across the starting position gives 24:
#   2 * (4 * knights=1 + 4 * bishops=1 + 4 * rooks=2 + 2 * queens=4) = 24.
# The game-phase number tracks how far we are from endgame: 24 = opening,
# 0 = bare kings.
_PHASE_WEIGHTS = {
    chess.KNIGHT: 1,
    chess.BISHOP: 1,
    chess.ROOK:   2,
    chess.QUEEN:  4,
}
_PHASE_MAX = 24


def _game_phase(board: chess.Board) -> int:
    phase = 0
    for piece_type, weight in _PHASE_WEIGHTS.items():
        phase += weight * len(board.pieces(piece_type, chess.WHITE))
        phase += weight * len(board.pieces(piece_type, chess.BLACK))
    return min(phase, _PHASE_MAX)


def _king_pst_tapered(square: int, color: chess.Color, phase: int) -> int:
    idx = _pst_index(square, color)
    mg = _KING_MG_PST[idx]
    eg = _KING_EG_PST[idx]
    # Blend: phase=24 -> 100% midgame; phase=0 -> 100% endgame.
    return (mg * phase + eg * (_PHASE_MAX - phase)) // _PHASE_MAX


# --- Structural terms ------------------------------------------------------

BISHOP_PAIR_BONUS = 30
DOUBLED_PAWN_PENALTY = 12


def _doubled_pawn_penalty(board: chess.Board, color: chess.Color) -> int:
    penalty = 0
    pawns = board.pieces(chess.PAWN, color)
    for file in range(8):
        count = sum(1 for sq in pawns if chess.square_file(sq) == file)
        if count > 1:
            penalty += DOUBLED_PAWN_PENALTY * (count - 1)
    return penalty


def _bishop_pair_bonus(board: chess.Board, color: chess.Color) -> int:
    return BISHOP_PAIR_BONUS if len(board.pieces(chess.BISHOP, color)) >= 2 else 0


# --- Public evaluation -----------------------------------------------------


def evaluate(game: ChessGame, ply: int = 0) -> int:
    """Score in centipawns from White's perspective.

    ``ply`` is plies-from-root; used for depth-adjusted mate scoring so
    the engine prefers faster mates and slower losses — same trick as in
    the TTT and checkers evaluators.
    """
    if game.is_checkmate():
        if game.current_player() == chess.WHITE:
            return -WIN_SCORE + ply
        return WIN_SCORE - ply
    if game.is_stalemate() or game.is_draw_by_rule():
        return 0

    board = game.board
    phase = _game_phase(board)

    score = 0
    for square, piece in board.piece_map().items():
        value = PIECE_VALUES[piece.piece_type]
        if piece.piece_type == chess.KING:
            positional = _king_pst_tapered(square, piece.color, phase)
        else:
            positional = _PST_BY_TYPE[piece.piece_type][
                _pst_index(square, piece.color)
            ]
        if piece.color == chess.WHITE:
            score += value + positional
        else:
            score -= value + positional

    # Structural: bishop pair and doubled pawns.
    score += _bishop_pair_bonus(board, chess.WHITE)
    score -= _bishop_pair_bonus(board, chess.BLACK)
    score -= _doubled_pawn_penalty(board, chess.WHITE)
    score += _doubled_pawn_penalty(board, chess.BLACK)

    # Mobility tie-breaker, signed by side to move. Same shape as checkers.
    mobility = board.legal_moves.count()
    if board.turn == chess.WHITE:
        score += mobility
    else:
        score -= mobility

    return score
