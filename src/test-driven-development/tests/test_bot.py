import chess
import pytest
from bot.random_bot import RandomBot
from bot.engine_bot import EngineBot


def test_random_bot_returns_legal_move():
    board = chess.Board()
    bot = RandomBot()
    move = bot.choose_move(board)
    assert move in board.legal_moves


def test_random_bot_plays_full_game_without_error():
    board = chess.Board()
    bot = RandomBot()
    for _ in range(50):
        if board.is_game_over():
            break
        move = bot.choose_move(board)
        board.push(move)


def test_engine_bot_returns_legal_move():
    board = chess.Board()
    bot = EngineBot(depth=1)
    move = bot.choose_move(board)
    assert move in board.legal_moves


def test_engine_bot_finds_mate_in_one():
    board = chess.Board("7k/8/6K1/8/8/8/8/R7 w - - 0 1")
    bot = EngineBot(depth=1)
    move = bot.choose_move(board)
    board.push(move)
    assert board.is_checkmate()


def test_engine_bot_raises_on_no_moves():
    board = chess.Board("k7/2Q5/8/8/8/8/8/K7 b - - 0 1")
    assert board.is_stalemate()
    bot = EngineBot(depth=1)
    with pytest.raises(ValueError):
        bot.choose_move(board)
