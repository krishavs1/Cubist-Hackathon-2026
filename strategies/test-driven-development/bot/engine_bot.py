import chess
from bot.base import BaseBot
from engine.search import best_move


class EngineBot(BaseBot):
    def __init__(self, depth: int = 3):
        self.depth = depth

    def choose_move(self, board: chess.Board) -> chess.Move:
        move = best_move(board, self.depth)
        if move is None:
            raise ValueError("No legal moves available")
        return move
