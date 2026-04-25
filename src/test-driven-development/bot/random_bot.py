import random
import chess
from bot.base import BaseBot


class RandomBot(BaseBot):
    def choose_move(self, board: chess.Board) -> chess.Move:
        moves = list(board.legal_moves)
        if not moves:
            raise ValueError("No legal moves available")
        return random.choice(moves)
