import chess
from engine.search import best_move


def test_returns_legal_move_from_start():
    board = chess.Board()
    move = best_move(board, depth=1)
    assert move is not None
    assert move in board.legal_moves


def test_finds_mate_in_one():
    # White: Rook a1, King g6. Black: King h8. Ra8 is checkmate.
    board = chess.Board("7k/8/6K1/8/8/8/8/R7 w - - 0 1")
    move = best_move(board, depth=1)
    assert move is not None
    board.push(move)
    assert board.is_checkmate()


def test_returns_none_when_no_legal_moves():
    # Stalemate position — no legal moves
    board = chess.Board("k7/2Q5/8/8/8/8/8/K7 b - - 0 1")
    assert board.is_stalemate()
    assert best_move(board, depth=1) is None


def test_prefers_capture_over_nothing():
    # White queen can take a free black rook
    board = chess.Board("7k/8/8/8/3r4/8/8/3Q3K w - - 0 1")
    move = best_move(board, depth=1)
    assert move is not None
    # The engine should take the rook (d1d4)
    assert move.to_square == chess.D4


def test_depth_2_returns_legal_move():
    board = chess.Board()
    move = best_move(board, depth=2)
    assert move is not None
    assert move in board.legal_moves
