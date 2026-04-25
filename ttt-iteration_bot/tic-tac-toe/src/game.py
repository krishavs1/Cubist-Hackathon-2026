"""Game rules for Tic-Tac-Toe.

Designed as a scaled-down analog of a chess game state. The public interface
(`get_legal_moves`, `make_move`, `undo_move`, `is_terminal`, `current_player`,
`winner`) is the contract the search layer depends on. Swapping in a chess
`Game` class with the same interface should leave `search.py` unchanged.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

EMPTY = "."
X = "X"
O = "O"

# All eight winning lines on a 3x3 board. Computed once at import time.
WIN_LINES: Tuple[Tuple[int, int, int], ...] = (
    (0, 1, 2), (3, 4, 5), (6, 7, 8),   # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),   # columns
    (0, 4, 8), (2, 4, 6),              # diagonals
)


class Game:
    """Mutable game state with make/undo semantics.

    Moves are integers 0..8 indexing into a flat board. Using make/undo rather
    than copy-on-move matches how chess engines manage search — the same
    object is mutated as the search walks the tree.
    """

    __slots__ = ("board", "_turn", "history")

    def __init__(self, board: Optional[List[str]] = None, turn: str = X):
        if board is None:
            self.board = [EMPTY] * 9
        else:
            if len(board) != 9:
                raise ValueError("board must have exactly 9 cells")
            self.board = list(board)
        if turn not in (X, O):
            raise ValueError("turn must be 'X' or 'O'")
        self._turn = turn
        self.history: List[int] = []

    # --- Generic interface used by search -----------------------------------

    def current_player(self) -> str:
        return self._turn

    def is_maximizing_player(self) -> bool:
        """True iff the side to move is the maximizer.

        This is the generic hook the search uses instead of comparing the
        current player against a game-specific constant. For Tic-Tac-Toe X
        is the maximizer; for chess it would be White.
        """
        return self._turn == X

    def get_legal_moves(self) -> List[int]:
        if self._terminal_winner() is not None:
            return []
        return [i for i, cell in enumerate(self.board) if cell == EMPTY]

    def make_move(self, move: int) -> None:
        if not (0 <= move < 9):
            raise ValueError(f"move {move} out of range")
        if self.board[move] != EMPTY:
            raise ValueError(f"square {move} is already occupied")
        self.board[move] = self._turn
        self.history.append(move)
        self._turn = O if self._turn == X else X

    def undo_move(self) -> None:
        if not self.history:
            raise ValueError("no moves to undo")
        move = self.history.pop()
        self.board[move] = EMPTY
        self._turn = O if self._turn == X else X

    def is_terminal(self) -> bool:
        if self._terminal_winner() is not None:
            return True
        return EMPTY not in self.board

    def winner(self) -> Optional[str]:
        """Return 'X', 'O', or None. None covers both draws and ongoing games."""
        return self._terminal_winner()

    # --- Internal ------------------------------------------------------------

    def _terminal_winner(self) -> Optional[str]:
        b = self.board
        for a, b2, c in WIN_LINES:
            if b[a] != EMPTY and b[a] == b[b2] == b[c]:
                return b[a]
        return None

    # --- Conveniences for CLI / debugging -----------------------------------

    def render(self) -> str:
        rows = []
        for r in range(3):
            rows.append(" " + " | ".join(self.board[r * 3 + c] for c in range(3)))
        return ("\n---+---+---\n").join(rows)

    def clone(self) -> "Game":
        g = Game(self.board, self._turn)
        g.history = list(self.history)
        return g
