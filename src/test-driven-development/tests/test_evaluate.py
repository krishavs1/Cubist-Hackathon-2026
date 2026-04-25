import chess
from engine.evaluate import evaluate, CHECKMATE_SCORE


def test_starting_position_is_zero():
    assert evaluate(chess.Board()) == 0


def test_up_a_queen_is_positive():
    board = chess.Board()
    board.remove_piece_at(chess.D8)
    assert evaluate(board) > 0


def test_down_a_queen_is_negative():
    board = chess.Board()
    board.remove_piece_at(chess.D1)
    assert evaluate(board) < 0


def test_symmetric_material_removal_stays_zero():
    board = chess.Board()
    board.remove_piece_at(chess.D1)
    board.remove_piece_at(chess.D8)
    assert evaluate(board) == 0


def test_white_mated_returns_negative_checkmate():
    # Fool's mate — black wins
    board = chess.Board()
    board.push_san("f3")
    board.push_san("e5")
    board.push_san("g4")
    board.push_san("Qh4#")
    assert board.is_checkmate()
    assert evaluate(board) == -CHECKMATE_SCORE


def test_black_mated_returns_positive_checkmate():
    # Scholar's mate — white wins
    board = chess.Board()
    board.push_san("e4")
    board.push_san("e5")
    board.push_san("Qh5")
    board.push_san("Nc6")
    board.push_san("Bc4")
    board.push_san("Nf6")
    board.push_san("Qxf7#")
    assert board.is_checkmate()
    assert evaluate(board) == CHECKMATE_SCORE


def test_stalemate_is_zero():
    # Classic stalemate: black king on a8, white queen on c7, white king on a1
    board = chess.Board("k7/2Q5/8/8/8/8/8/K7 b - - 0 1")
    assert board.is_stalemate()
    assert evaluate(board) == 0


def test_insufficient_material_is_zero():
    board = chess.Board("k7/8/8/8/8/8/8/K7 w - - 0 1")
    assert board.is_insufficient_material()
    assert evaluate(board) == 0
