"""ChessGame: a thin wrapper around python-chess that exposes the same
generic interface as the Tic-Tac-Toe `Game`:

    - get_legal_moves()
    - make_move(move)
    - undo_move()
    - is_terminal()
    - current_player()
    - is_maximizing_player()

The internal `chess.Board` from python-chess provides legal move generation,
make/undo (`push` / `pop`), and terminal detection. We delegate to it but
expose the same interface the search depends on, so the alpha-beta module
can be reused unchanged.

The interface is also UCI-friendly by design: moves are `chess.Move`
objects, which serialize to / from UCI strings (`move.uci()`,
`chess.Move.from_uci(...)`). A future UCI front-end can sit in front of
this class without modification.
"""

from __future__ import annotations

from typing import List, Optional

import chess


WHITE = chess.WHITE
BLACK = chess.BLACK


class ChessGame:
    """Wrapper exposing the generic Game interface over `python-chess`."""

    __slots__ = ("board",)

    def __init__(self, fen: Optional[str] = None):
        if fen is None:
            self.board = chess.Board()
        else:
            self.board = chess.Board(fen)

    # --- Generic interface used by search -----------------------------------

    def current_player(self) -> chess.Color:
        """Returns chess.WHITE (True) or chess.BLACK (False)."""
        return self.board.turn

    def is_maximizing_player(self) -> bool:
        """White is the maximizer (positive eval favors White)."""
        return self.board.turn == WHITE

    def get_legal_moves(self) -> List[chess.Move]:
        # python-chess returns a LegalMoveGenerator; materialize so the
        # search can iterate over a stable list.
        return list(self.board.legal_moves)

    def make_move(self, move: chess.Move) -> None:
        if move not in self.board.legal_moves:
            raise ValueError(f"illegal move: {move.uci()} in {self.board.fen()}")
        self.board.push(move)

    def undo_move(self) -> None:
        if not self.board.move_stack:
            raise ValueError("no moves to undo")
        self.board.pop()

    def is_terminal(self) -> bool:
        # is_game_over covers checkmate, stalemate, insufficient material,
        # 75-move rule, fivefold repetition. claim_draw=False to keep it
        # deterministic for the search (we don't ask whether a player
        # *could* claim a draw, only whether the game has ended).
        return self.board.is_game_over(claim_draw=False)

    # --- Chess-specific accessors used by the evaluator ---------------------

    def is_checkmate(self) -> bool:
        return self.board.is_checkmate()

    def is_stalemate(self) -> bool:
        return self.board.is_stalemate()

    def is_draw_by_rule(self) -> bool:
        """Insufficient material, 75-move, fivefold repetition. Stalemate
        excluded so the evaluator can score it explicitly."""
        return (
            self.board.is_insufficient_material()
            or self.board.is_seventyfive_moves()
            or self.board.is_fivefold_repetition()
        )

    # --- Conveniences for CLI / debugging -----------------------------------

    def fen(self) -> str:
        return self.board.fen()

    def render(self) -> str:
        return str(self.board)

    def parse_uci(self, uci: str) -> Optional[chess.Move]:
        """Parse a UCI move string. Returns None if invalid syntax."""
        try:
            return chess.Move.from_uci(uci)
        except ValueError:
            return None

    def parse_san(self, san: str) -> Optional[chess.Move]:
        """Parse a SAN move (e.g. 'Nf3'). Returns None if invalid."""
        try:
            return self.board.parse_san(san)
        except (ValueError, chess.IllegalMoveError, chess.AmbiguousMoveError, chess.InvalidMoveError):
            return None
