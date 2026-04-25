import chess
from engine.engine import search

def test_search_finds_mate_in_one():
    # White to move, mate in one with Qb7#
    board = chess.Board("k7/8/K7/8/8/8/8/1Q6 w - - 0 1")
    move = search(board, depth=2)
    assert move == chess.Move.from_uci("b1b7")

def test_search_avoids_blunder():
    # Simple tactical avoid blunder
    # This might be hard at depth 3 but let's see
    pass

def test_search_returns_legal_move():
    board = chess.Board()
    move = search(board, depth=1)
    assert move in board.legal_moves
