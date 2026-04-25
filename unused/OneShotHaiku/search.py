import chess
from evaluation import evaluate
from typing import Tuple

# Transposition table to cache evaluated positions
transposition_table = {}
tt_hits = 0
tt_cutoffs = 0


def clear_transposition_table():
    """Clear the transposition table."""
    global transposition_table, tt_hits, tt_cutoffs
    transposition_table = {}
    tt_hits = 0
    tt_cutoffs = 0


def order_moves(board, moves):
    """Order moves to improve alpha-beta pruning efficiency."""
    def move_score(move):
        # Captures first
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            victim_value = 0 if victim is None else {
                chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0
            }.get(victim.piece_type, 0)
            attacker_value = {
                chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0
            }.get(attacker.piece_type, 0)
            return 10000 + (victim_value - attacker_value)

        # Promotions
        if move.promotion:
            return 8000 + {
                chess.QUEEN: 900, chess.ROOK: 500,
                chess.BISHOP: 330, chess.KNIGHT: 320
            }.get(move.promotion, 0)

        # Checks
        if board.gives_check(move):
            return 1000

        # Castling
        if board.is_castling(move):
            return 500

        return 0

    return sorted(moves, key=move_score, reverse=True)


def minimax(board, depth, alpha, beta, is_maximizing, max_depth):
    """
    Minimax with alpha-beta pruning.
    is_maximizing: True when it's white's turn to maximize score.
    """
    global tt_hits, tt_cutoffs

    # Transposition table lookup
    tt_key = (board.fen(), depth)
    if tt_key in transposition_table:
        tt_hits += 1
        return transposition_table[tt_key]

    # Terminal node
    if depth == 0 or board.is_game_over():
        score = evaluate(board)
        transposition_table[tt_key] = score
        return score

    moves = list(board.legal_moves)
    if not moves:
        score = evaluate(board)
        transposition_table[tt_key] = score
        return score

    # Move ordering for better pruning
    moves = order_moves(board, moves)

    if is_maximizing:
        max_eval = float('-inf')
        for move in moves:
            board.push(move)
            eval_score = minimax(board, depth - 1, alpha, beta, False, max_depth)
            board.pop()

            max_eval = max(max_eval, eval_score)
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                tt_cutoffs += 1
                break

        transposition_table[tt_key] = max_eval
        return max_eval
    else:
        min_eval = float('inf')
        for move in moves:
            board.push(move)
            eval_score = minimax(board, depth - 1, alpha, beta, True, max_depth)
            board.pop()

            min_eval = min(min_eval, eval_score)
            beta = min(beta, eval_score)
            if beta <= alpha:
                tt_cutoffs += 1
                break

        transposition_table[tt_key] = min_eval
        return min_eval


def find_best_move(board, depth=4):
    """
    Find the best move for the current position using minimax with alpha-beta pruning.
    """
    moves = list(board.legal_moves)

    if not moves:
        return None

    # Move ordering
    moves = order_moves(board, moves)

    best_move = moves[0]
    best_score = float('-inf') if board.turn else float('inf')

    for move in moves:
        board.push(move)
        score = minimax(board, depth - 1, float('-inf'), float('inf'),
                       not board.turn, depth)
        board.pop()

        if board.turn:  # White's turn (maximizing)
            if score > best_score:
                best_score = score
                best_move = move
        else:  # Black's turn (minimizing)
            if score < best_score:
                best_score = score
                best_move = move

    return best_move


def find_best_move_iterative(board, time_limit_ms=1000):
    """
    Iterative deepening with time limit.
    Tries deeper searches until time runs out.
    """
    import time

    start_time = time.time()
    best_move = None
    depth = 1

    while True:
        elapsed = (time.time() - start_time) * 1000
        if elapsed > time_limit_ms:
            break

        try:
            move = find_best_move(board, depth)
            if move:
                best_move = move
            depth += 1
        except:
            break

    return best_move
