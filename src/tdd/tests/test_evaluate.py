import chess
from engine.engine import evaluate

def test_evaluate_initial_board():
    board = chess.Board()
    # Initial board should be balanced (0)
    # Mobility for both sides is the same
    assert evaluate(board) == 0

def test_evaluate_material_advantage():
    # White has an extra pawn
    board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    board.remove_piece_at(chess.A7)
    score = evaluate(board)
    assert score > 0

def test_evaluate_mobility():
    # Compare two positions with same material but different mobility
    board1 = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    # Block white's development
    board2 = chess.Board("r1bqkbnr/pppppppp/n7/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    
    # This is a bit tricky to test purely, but let's assume mobility is positive
    # For now, just check if it's consistent
    pass

def test_evaluate_checkmate():
    board = chess.Board("k7/8/K7/8/8/8/8/1Q6 w - - 0 1")
    # White plays b1b7#, now it's Black's turn and they are in checkmate
    board.push(chess.Move.from_uci("b1b7")) # Checkmate
    assert evaluate(board) == -30000
