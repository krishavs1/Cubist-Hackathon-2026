import time
import chess
from typing import Optional
from engine.evaluate import evaluate, CHECKMATE_SCORE, PIECE_VALUES


def _move_priority(board: chess.Board, move: chess.Move) -> int:
    """Lower value = tried first. Captures ordered by MVV-LVA."""
    if board.is_capture(move):
        victim = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        if victim and attacker:
            return -(PIECE_VALUES[victim.piece_type] * 10 - PIECE_VALUES[attacker.piece_type])
        return -1
    return 0


def _ordered_moves(board: chess.Board) -> list:
    moves = list(board.legal_moves)
    moves.sort(key=lambda m: _move_priority(board, m))
    return moves


def _negamax(board: chess.Board, depth: int, alpha: int, beta: int) -> int:
    """Negamax alpha-beta. Returns score from the current player's perspective."""
    if board.is_game_over():
        return -CHECKMATE_SCORE if board.is_checkmate() else 0

    if depth == 0:
        score = evaluate(board)
        return score if board.turn == chess.WHITE else -score

    best = -CHECKMATE_SCORE - 1
    for move in _ordered_moves(board):
        board.push(move)
        score = -_negamax(board, depth - 1, -beta, -alpha)
        board.pop()
        best = max(best, score)
        alpha = max(alpha, score)
        if alpha >= beta:
            break
    return best


def best_move(board: chess.Board, depth: int = 3) -> Optional[chess.Move]:
    """Return the best move for the side to move. Returns None if no legal moves."""
    moves = _ordered_moves(board)
    if not moves:
        return None

    best = None
    best_score = -CHECKMATE_SCORE - 1
    for move in moves:
        board.push(move)
        score = -_negamax(board, depth - 1, -CHECKMATE_SCORE - 1, CHECKMATE_SCORE + 1)
        board.pop()
        if score > best_score:
            best_score = score
            best = move
    return best


def best_move_timed(board: chess.Board, movetime_ms: int) -> Optional[chess.Move]:
    """Iterative deepening within a time budget. Uses 90% of movetime as the deadline."""
    deadline = time.time() + movetime_ms / 1000.0 * 0.9
    best = None
    for depth in range(1, 8):
        if time.time() >= deadline:
            break
        move = best_move(board, depth)
        if move is not None:
            best = move
        if time.time() >= deadline:
            break
    return best
