import abc
import chess


class BaseBot(abc.ABC):
    @abc.abstractmethod
    def choose_move(self, board: chess.Board) -> chess.Move:
        pass
