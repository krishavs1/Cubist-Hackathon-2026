#!/usr/bin/env python3
"""
Heuristic personalities for the Darwinian AI engine.

Each function is a complete `evaluate(board) -> int` implementation
returning a centipawn score from White's perspective. The search engine
calls one of these via SearchState.eval_fn.

These are the "genomes" that compete in the Arena tournament. New
personalities (Claude-generated via Workstream B, or Reflexion-rewritten
via Workstream E) can be added here without touching the search code.

Contract for all personalities:
- Signature: fn(board: chess.Board) -> int
- Returns: centipawns from White's perspective (positive = White better)
- Must NOT call board.push/pop or mutate board state
- Should NOT handle terminal states (checkmate/stalemate) -- the search
  handles those before calling evaluate
- Material should always dominate so the engine doesn't trade pieces away
"""

from typing import Callable, Dict

import chess

# Standard piece values used as a baseline by most personalities.
STANDARD_VALUES = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:   20000,
}

CENTER_SQUARES = (chess.E4, chess.D4, chess.E5, chess.D5)
EXTENDED_CENTER = (
    chess.C3, chess.D3, chess.E3, chess.F3,
    chess.C4, chess.D4, chess.E4, chess.F4,
    chess.C5, chess.D5, chess.E5, chess.F5,
    chess.C6, chess.D6, chess.E6, chess.F6,
)


# ============================================================
# HELPER FUNCTIONS (shared building blocks)
# ============================================================

def material_balance(board: chess.Board, values: Dict[int, int] = STANDARD_VALUES) -> int:
    """Sum of material in centipawns from White's perspective."""
    score = 0
    for piece_type, value in values.items():
        score += len(board.pieces(piece_type, chess.WHITE)) * value
        score -= len(board.pieces(piece_type, chess.BLACK)) * value
    return score


def king_attack_pressure(board: chess.Board, attacker_color: chess.Color) -> int:
    """Count attacker_color pieces attacking squares around the enemy king."""
    enemy_king = board.king(not attacker_color)
    if enemy_king is None:
        return 0
    zone = chess.SquareSet(chess.BB_KING_ATTACKS[enemy_king])
    return sum(1 for sq in zone if board.is_attacked_by(attacker_color, sq))


def pawn_shield_count(board: chess.Board, color: chess.Color) -> int:
    """Number of own pawns adjacent to own king (pawn shield strength)."""
    king_sq = board.king(color)
    if king_sq is None:
        return 0
    adjacent = chess.SquareSet(chess.BB_KING_ATTACKS[king_sq])
    own_pawn = chess.Piece(chess.PAWN, color)
    return sum(1 for sq in adjacent if board.piece_at(sq) == own_pawn)


def advanced_pawn_score(board: chess.Board, color: chess.Color) -> int:
    """Sum of how far each pawn has advanced past its starting rank."""
    score = 0
    for sq in board.pieces(chess.PAWN, color):
        rank = chess.square_rank(sq)
        if color == chess.WHITE:
            score += max(0, rank - 1)  # White pawns start on rank 1
        else:
            score += max(0, 6 - rank)  # Black pawns start on rank 6
    return score


# ============================================================
# PERSONALITIES
# ============================================================

def balanced(board: chess.Board) -> int:
    """
    The default seed evaluator.
    Equal weight on material, mobility, center, and king safety.
    """
    score = material_balance(board)

    # Mobility (one-sided proxy: count side-to-move legal moves and sign it)
    mobility = board.legal_moves.count()
    score += mobility * 10 * (1 if board.turn == chess.WHITE else -1)

    # Center control
    for sq in CENTER_SQUARES:
        if board.is_attacked_by(chess.WHITE, sq):
            score += 15
        if board.is_attacked_by(chess.BLACK, sq):
            score -= 15

    # King safety (pawn shield)
    score -= max(0, 3 - pawn_shield_count(board, chess.WHITE)) * 20
    score += max(0, 3 - pawn_shield_count(board, chess.BLACK)) * 20

    return score


def aggressive_attacker(board: chess.Board) -> int:
    """
    Loves attacking the enemy king. Willing to sacrifice king safety and
    material for kingside attacks. Queen valued slightly higher.
    """
    attacker_values = dict(STANDARD_VALUES)
    attacker_values[chess.QUEEN] = 950  # Queen is the attack workhorse
    score = material_balance(board, attacker_values)

    # Big bonus for attacking the enemy king zone
    score += king_attack_pressure(board, chess.WHITE) * 35
    score -= king_attack_pressure(board, chess.BLACK) * 35

    # Mobility matters (active pieces attack)
    mobility = board.legal_moves.count()
    score += mobility * 8 * (1 if board.turn == chess.WHITE else -1)

    # Almost ignore own king safety -- we attack, not defend
    score -= max(0, 3 - pawn_shield_count(board, chess.WHITE)) * 5
    score += max(0, 3 - pawn_shield_count(board, chess.BLACK)) * 5

    return score


def positional_grinder(board: chess.Board) -> int:
    """
    Slow strategic play. Heavy weight on center control and extended
    center occupation. Low mobility weight (no flashy tactics).
    """
    score = material_balance(board)

    # Strong center control
    for sq in CENTER_SQUARES:
        if board.is_attacked_by(chess.WHITE, sq):
            score += 25
        if board.is_attacked_by(chess.BLACK, sq):
            score -= 25

    # Bonus for piece presence in extended center
    for sq in EXTENDED_CENTER:
        piece = board.piece_at(sq)
        if piece:
            score += 8 if piece.color == chess.WHITE else -8

    # Solid king safety
    score -= max(0, 3 - pawn_shield_count(board, chess.WHITE)) * 25
    score += max(0, 3 - pawn_shield_count(board, chess.BLACK)) * 25

    return score


def material_hawk(board: chess.Board) -> int:
    """
    Pure greed. Only material counts. No positional understanding.
    Useful as a baseline -- if a personality can't beat material_hawk,
    its positional theory isn't worth the complexity.
    """
    # Slightly tweaked piece values: bishops and knights equal,
    # rooks slightly less, queen slightly more.
    hawk_values = {
        chess.PAWN:   100,
        chess.KNIGHT: 325,
        chess.BISHOP: 325,
        chess.ROOK:   490,
        chess.QUEEN:  920,
        chess.KING:   20000,
    }
    return material_balance(board, hawk_values)


def fortress(board: chess.Board) -> int:
    """
    Defensive, risk-averse. Maximum king safety. Penalizes any pawn
    advances near our own king. Will trade pieces to simplify.
    """
    score = material_balance(board)

    # Massive king safety weight
    score -= max(0, 3 - pawn_shield_count(board, chess.WHITE)) * 50
    score += max(0, 3 - pawn_shield_count(board, chess.BLACK)) * 50

    # Trade-down bonus: fewer pieces on the board is good when ahead
    white_material = material_balance(board)
    if white_material > 100:
        # We're ahead -- prefer fewer pieces (easier to convert)
        total_pieces = chess.popcount(board.occupied)
        score += (32 - total_pieces) * 3
    elif white_material < -100:
        # We're behind -- prefer more pieces (more chances)
        total_pieces = chess.popcount(board.occupied)
        score -= (32 - total_pieces) * 3

    # Mild center control
    for sq in CENTER_SQUARES:
        if board.is_attacked_by(chess.WHITE, sq):
            score += 8
        if board.is_attacked_by(chess.BLACK, sq):
            score -= 8

    return score


def pawn_storm(board: chess.Board) -> int:
    """
    Loves pushing pawns. Bonus for advanced pawns, especially passed ones.
    Sacrifices own king safety to crash through.
    """
    score = material_balance(board)

    # Big bonus for advanced pawns
    score += advanced_pawn_score(board, chess.WHITE) * 12
    score -= advanced_pawn_score(board, chess.BLACK) * 12

    # Mobility
    mobility = board.legal_moves.count()
    score += mobility * 8 * (1 if board.turn == chess.WHITE else -1)

    # Minimal king safety -- pawns are stormed forward, not held back
    score -= max(0, 3 - pawn_shield_count(board, chess.WHITE)) * 10
    score += max(0, 3 - pawn_shield_count(board, chess.BLACK)) * 10

    return score


# ============================================================
# TAPERED PIECE-SQUARE EVALUATOR (the "pesto" personality)
# ============================================================
#
# Smoothly interpolates between midgame and endgame piece-square tables
# based on remaining material. This is the strongest baseline personality
# and reflects modern engine design (per Chess Programming Wiki / PeSTO).
# Imported from the search module so the same numbers drive both the eval
# and the search's capture-value bookkeeping.

from search import pesto_evaluate as pesto  # noqa: E402  (module-level for hot path)


def reflexion_v1(board: chess.Board) -> int:
    """
    Reflexion cycle 1 — corrects positional_grinder's blind spots.

    positional_grinder lost games because it had no concept of:
      * piece development (minor pieces moving off starting squares)
      * castling (king stayed on e1/e8 and got mated on central files)
      * knight placement (knights wandered to a/h rim squares)
      * tempo (queen came out too early, same piece moved 5-7 times)

    This evaluator inherits positional_grinder's logic and adds:
      + bonus for each developed minor piece
      + large bonus for having castled; large penalty for not castling
      + penalty for knights on the a/h files
      + penalty for an early queen (moved before 4 minors are developed)

    All additions combined cap at ~120 cp so material remains dominant.
    """
    score = material_balance(board)

    for sq in CENTER_SQUARES:
        if board.is_attacked_by(chess.WHITE, sq):
            score += 25
        if board.is_attacked_by(chess.BLACK, sq):
            score -= 25

    for sq in EXTENDED_CENTER:
        piece = board.piece_at(sq)
        if piece:
            score += 8 if piece.color == chess.WHITE else -8

    score -= max(0, 3 - pawn_shield_count(board, chess.WHITE)) * 25
    score += max(0, 3 - pawn_shield_count(board, chess.BLACK)) * 25

    # -- REFLEXION ADDITIONS --

    # 1. Development: bonus for minor pieces off their starting squares
    white_minor_starts = (chess.B1, chess.G1, chess.C1, chess.F1)
    black_minor_starts = (chess.B8, chess.G8, chess.C8, chess.F8)
    dev_w = sum(
        1 for sq in white_minor_starts
        if board.piece_at(sq) is None
        or board.piece_at(sq).color != chess.WHITE
        or board.piece_at(sq).piece_type not in (chess.KNIGHT, chess.BISHOP)
    )
    dev_b = sum(
        1 for sq in black_minor_starts
        if board.piece_at(sq) is None
        or board.piece_at(sq).color != chess.BLACK
        or board.piece_at(sq).piece_type not in (chess.KNIGHT, chess.BISHOP)
    )
    score += dev_w * 15
    score -= dev_b * 15

    # 2. Castling: big reward for having castled
    wk_sq = board.king(chess.WHITE)
    bk_sq = board.king(chess.BLACK)
    if wk_sq in (chess.G1, chess.C1):
        score += 40
    elif wk_sq == chess.E1 and board.fullmove_number > 10:
        score -= 40  # king stuck in center past move 10
    if bk_sq in (chess.G8, chess.C8):
        score -= 40
    elif bk_sq == chess.E8 and board.fullmove_number > 10:
        score += 40

    # 3. Knight-on-rim penalty (a-file and h-file)
    rim_files = chess.BB_FILE_A | chess.BB_FILE_H
    w_rim_knights = chess.popcount(
        board.pieces_mask(chess.KNIGHT, chess.WHITE) & rim_files
    )
    b_rim_knights = chess.popcount(
        board.pieces_mask(chess.KNIGHT, chess.BLACK) & rim_files
    )
    score -= w_rim_knights * 20
    score += b_rim_knights * 20

    # 4. Early queen penalty (queen moved before 3 minors are developed)
    w_queen_home = board.piece_at(chess.D1) == chess.Piece(chess.QUEEN, chess.WHITE)
    b_queen_home = board.piece_at(chess.D8) == chess.Piece(chess.QUEEN, chess.BLACK)
    if not w_queen_home and dev_w < 3 and board.fullmove_number < 10:
        score -= 25
    if not b_queen_home and dev_b < 3 and board.fullmove_number < 10:
        score += 25

    return score

# ============================================================
# REGISTRY -- name -> evaluator function
# ============================================================

REGISTRY: Dict[str, Callable[[chess.Board], int]] = {
    "reflexion_v1":        reflexion_v1,
    "pesto":               pesto,
    "balanced":            balanced,
    "aggressive_attacker": aggressive_attacker,
    "positional_grinder":  positional_grinder,
    "material_hawk":       material_hawk,
    "fortress":            fortress,
    "pawn_storm":          pawn_storm,
}


def get(name: str) -> Callable[[chess.Board], int]:
    """Look up an evaluator by name. Raises KeyError if unknown."""
    if name not in REGISTRY:
        raise KeyError(f"Unknown heuristic '{name}'. Available: {list(REGISTRY)}")
    return REGISTRY[name]
