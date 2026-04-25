"""Checkers game rules.

American (English) draughts on an 8x8 board:

- 12 pieces per side on the dark squares of the first three rows.
- Red (``r`` / ``R`` for king) is the maximizer, starts at the bottom
  (rows 5-7) and moves toward row 0.
- Black (``b`` / ``B``) is the minimizer, starts at the top (rows 0-2)
  and moves toward row 7.
- Red moves first.
- Men move diagonally forward one square; kings move/capture in all four
  diagonal directions.
- Captures are mandatory. Multi-jumps with the same piece are mandatory:
  after a jump, if the same piece can jump again, it must.
- Promotion happens when a man reaches the opposing back rank; under ACF
  rules, reaching the king row *during* a multi-jump ENDS the move.
- A side with no legal moves loses (captured or blocked).
- A soft draw rule (``DRAW_HALFMOVES``) is used so the search has a stable
  terminal condition in quiet king-and-king endgames; this maps to the
  40-move rule used in many competitive checkers settings.

The public interface is the same one the Tic-Tac-Toe search depends on::

    get_legal_moves() -> list[Move]
    make_move(Move) -> None
    undo_move() -> None
    is_terminal() -> bool
    current_player() -> str                # RED or BLACK
    is_maximizing_player() -> bool
    winner() -> Optional[str]              # RED / BLACK / None

Moves are :class:`Move` instances (frozen dataclass) rather than integers,
but the search is already generic over the move type so this is fine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple


# Piece encoding -------------------------------------------------------------

EMPTY = "."
RED_MAN = "r"
RED_KING = "R"
BLACK_MAN = "b"
BLACK_KING = "B"

RED = "red"
BLACK = "black"

RED_PIECES = frozenset({RED_MAN, RED_KING})
BLACK_PIECES = frozenset({BLACK_MAN, BLACK_KING})
KINGS = frozenset({RED_KING, BLACK_KING})
MEN = frozenset({RED_MAN, BLACK_MAN})


# Diagonal direction tables --------------------------------------------------
# Row indices go *down* the board (row 0 = top = Black's home rank,
# row 7 = bottom = Red's home rank), so "Red moves forward" means decreasing
# row and "Black moves forward" means increasing row.

_RED_MAN_DIRS: Tuple[Tuple[int, int], ...] = ((-1, -1), (-1, 1))
_BLACK_MAN_DIRS: Tuple[Tuple[int, int], ...] = ((1, -1), (1, 1))
_KING_DIRS: Tuple[Tuple[int, int], ...] = ((-1, -1), (-1, 1), (1, -1), (1, 1))


def _directions_for(piece: str) -> Tuple[Tuple[int, int], ...]:
    if piece == RED_MAN:
        return _RED_MAN_DIRS
    if piece == BLACK_MAN:
        return _BLACK_MAN_DIRS
    if piece in KINGS:
        return _KING_DIRS
    raise ValueError(f"not a piece: {piece!r}")


# Coordinate <-> standard checkers notation ----------------------------------
# Standard American notation numbers the 32 dark squares 1..32 from the top
# (Black's side). Row 0 is squares 1-4, row 1 is 5-8, ..., row 7 is 29-32.

def _pos_to_num(pos: Tuple[int, int]) -> int:
    r, c = pos
    return r * 4 + c // 2 + 1


def _num_to_pos(num: int) -> Tuple[int, int]:
    if not 1 <= num <= 32:
        raise ValueError(f"square number {num} out of range (1..32)")
    idx = num - 1
    r = idx // 4
    col_in_row = idx % 4
    c = 2 * col_in_row + (1 if r % 2 == 0 else 0)
    return (r, c)


# Move type ------------------------------------------------------------------


@dataclass(frozen=True)
class Move:
    """A single checkers move.

    ``from_sq``: starting square of the piece.
    ``path``: landing squares in order. For a simple move this has length 1;
              for multi-jumps it contains each intermediate landing square.
    ``captures``: squares of the enemy pieces captured, in capture order.
    """

    from_sq: Tuple[int, int]
    path: Tuple[Tuple[int, int], ...]
    captures: Tuple[Tuple[int, int], ...]

    @property
    def to_sq(self) -> Tuple[int, int]:
        return self.path[-1]

    @property
    def is_capture(self) -> bool:
        return bool(self.captures)

    def notation(self) -> str:
        """Standard notation: ``11-15`` for simple, ``11x18x25`` for jumps."""
        sep = "x" if self.is_capture else "-"
        parts = [_pos_to_num(self.from_sq)] + [_pos_to_num(p) for p in self.path]
        return sep.join(str(p) for p in parts)

    def __repr__(self) -> str:
        return self.notation()


def parse_move(text: str, legal: Sequence[Move]) -> Optional[Move]:
    """Parse ``11-15`` or ``11x18`` or ``11x18x25`` into one of the legal moves.

    Returns ``None`` if the text doesn't match any legal move.
    """
    text = text.strip().lower().replace(" ", "")
    if not text:
        return None
    # Normalize capture separator so "11-18" and "11x18" both work as long
    # as the move happens to be legal.
    tokens = text.replace("x", "-").split("-")
    try:
        nums = [int(t) for t in tokens]
    except ValueError:
        return None
    if len(nums) < 2:
        return None
    try:
        from_sq = _num_to_pos(nums[0])
        path = tuple(_num_to_pos(n) for n in nums[1:])
    except ValueError:
        return None
    for move in legal:
        if move.from_sq == from_sq and move.path == path:
            return move
    return None


# Game state -----------------------------------------------------------------


@dataclass
class _HistoryEntry:
    move: Move
    captured_pieces: Tuple[str, ...]
    was_promoted: bool
    from_piece: str
    prev_halfmove_clock: int


class CheckersGame:
    """Checkers game state with make/undo semantics.

    Turn rotation, captured-piece bookkeeping, and promotion are all
    reversible via :meth:`undo_move`, so the search can mutate a single
    shared object as it walks the tree.
    """

    __slots__ = ("board", "_turn", "history", "halfmove_clock")

    #: Number of plies (half-moves) without a capture or a man move before the
    #: game is declared drawn. 80 plies = 40 moves per side. This is a simple
    #: analogue of the ACF "40-move rule"; the exact counting differs in
    #: competitive play but this is adequate for search-stable terminals.
    DRAW_HALFMOVES = 80

    def __init__(
        self,
        board: Optional[List[List[str]]] = None,
        turn: str = RED,
        halfmove_clock: int = 0,
    ) -> None:
        if board is None:
            self.board = self._initial_board()
        else:
            self.board = [list(row) for row in board]
            if len(self.board) != 8 or any(len(row) != 8 for row in self.board):
                raise ValueError("board must be 8x8")
        if turn not in (RED, BLACK):
            raise ValueError("turn must be RED or BLACK")
        self._turn = turn
        self.history: List[_HistoryEntry] = []
        self.halfmove_clock = halfmove_clock

    @staticmethod
    def _initial_board() -> List[List[str]]:
        board = [[EMPTY] * 8 for _ in range(8)]
        for r in range(3):
            for c in range(8):
                if (r + c) % 2 == 1:
                    board[r][c] = BLACK_MAN
        for r in range(5, 8):
            for c in range(8):
                if (r + c) % 2 == 1:
                    board[r][c] = RED_MAN
        return board

    # --- Generic interface used by search ----------------------------------

    def current_player(self) -> str:
        return self._turn

    def is_maximizing_player(self) -> bool:
        return self._turn == RED

    def get_legal_moves(self) -> List[Move]:
        captures = self._find_all_captures()
        if captures:
            return captures
        return self._find_all_simple_moves()

    def make_move(self, move: Move) -> None:
        from_r, from_c = move.from_sq
        from_piece = self.board[from_r][from_c]
        if from_piece == EMPTY:
            raise ValueError(f"no piece at {move.from_sq}")
        if not self._piece_belongs_to_turn(from_piece):
            raise ValueError(
                f"piece {from_piece!r} at {move.from_sq} is not {self._turn}'s"
            )

        captured_pieces = tuple(self.board[cr][cc] for (cr, cc) in move.captures)
        prev_halfmove = self.halfmove_clock

        self.board[from_r][from_c] = EMPTY
        for (cr, cc) in move.captures:
            self.board[cr][cc] = EMPTY

        to_r, to_c = move.to_sq
        was_promoted = False
        if from_piece == RED_MAN and to_r == 0:
            self.board[to_r][to_c] = RED_KING
            was_promoted = True
        elif from_piece == BLACK_MAN and to_r == 7:
            self.board[to_r][to_c] = BLACK_KING
            was_promoted = True
        else:
            self.board[to_r][to_c] = from_piece

        if move.is_capture or from_piece in MEN:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        self.history.append(
            _HistoryEntry(
                move=move,
                captured_pieces=captured_pieces,
                was_promoted=was_promoted,
                from_piece=from_piece,
                prev_halfmove_clock=prev_halfmove,
            )
        )
        self._turn = BLACK if self._turn == RED else RED

    def undo_move(self) -> None:
        if not self.history:
            raise ValueError("no moves to undo")
        entry = self.history.pop()
        move = entry.move

        self._turn = RED if self._turn == BLACK else BLACK

        to_r, to_c = move.to_sq
        self.board[to_r][to_c] = EMPTY
        for (cr, cc), piece in zip(move.captures, entry.captured_pieces):
            self.board[cr][cc] = piece
        from_r, from_c = move.from_sq
        self.board[from_r][from_c] = entry.from_piece

        self.halfmove_clock = entry.prev_halfmove_clock

    def is_terminal(self) -> bool:
        if self.halfmove_clock >= self.DRAW_HALFMOVES:
            return True
        return not self.get_legal_moves()

    def winner(self) -> Optional[str]:
        """Return ``RED``, ``BLACK``, or ``None`` (draw or ongoing)."""
        if self.halfmove_clock >= self.DRAW_HALFMOVES:
            return None
        if not self.get_legal_moves():
            return BLACK if self._turn == RED else RED
        return None

    # --- Convenience accessors used by the evaluator / tests ---------------

    def piece_count(self, player: str) -> Tuple[int, int]:
        """Return ``(men, kings)`` for ``player`` (``RED`` or ``BLACK``)."""
        if player == RED:
            man, king = RED_MAN, RED_KING
        elif player == BLACK:
            man, king = BLACK_MAN, BLACK_KING
        else:
            raise ValueError(f"unknown player: {player!r}")
        men = sum(row.count(man) for row in self.board)
        kings = sum(row.count(king) for row in self.board)
        return men, kings

    def clone(self) -> "CheckersGame":
        g = CheckersGame.__new__(CheckersGame)
        g.board = [list(row) for row in self.board]
        g._turn = self._turn
        g.history = list(self.history)
        g.halfmove_clock = self.halfmove_clock
        return g

    # --- Internal ----------------------------------------------------------

    def _piece_belongs_to_turn(self, piece: str) -> bool:
        if self._turn == RED:
            return piece in RED_PIECES
        return piece in BLACK_PIECES

    def _is_opponent_piece(self, piece: str) -> bool:
        if piece == EMPTY:
            return False
        if self._turn == RED:
            return piece in BLACK_PIECES
        return piece in RED_PIECES

    @staticmethod
    def _in_bounds(r: int, c: int) -> bool:
        return 0 <= r < 8 and 0 <= c < 8

    def _find_all_simple_moves(self) -> List[Move]:
        moves: List[Move] = []
        board = self.board
        for r in range(8):
            row = board[r]
            for c in range(8):
                piece = row[c]
                if not self._piece_belongs_to_turn(piece):
                    continue
                for dr, dc in _directions_for(piece):
                    nr, nc = r + dr, c + dc
                    if not self._in_bounds(nr, nc):
                        continue
                    if board[nr][nc] != EMPTY:
                        continue
                    moves.append(
                        Move(from_sq=(r, c), path=((nr, nc),), captures=())
                    )
        return moves

    def _find_all_captures(self) -> List[Move]:
        moves: List[Move] = []
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if not self._piece_belongs_to_turn(piece):
                    continue
                moves.extend(self._capture_sequences_from(r, c, piece))
        return moves

    def _capture_sequences_from(
        self, start_r: int, start_c: int, start_piece: str
    ) -> List[Move]:
        """Return every maximal capture sequence starting at ``(start_r, start_c)``.

        The board is mutated during the walk (pieces lifted onto landing
        squares, captured pieces removed) so that the "landing must be empty"
        rule stays self-consistent. The original board is fully restored
        before this returns.
        """
        results: List[Move] = []
        board = self.board

        board[start_r][start_c] = EMPTY  # lift the moving piece

        def recurse(
            r: int,
            c: int,
            cur_piece: str,
            path: List[Tuple[int, int]],
            captures: List[Tuple[int, int]],
        ) -> None:
            extended = False
            for dr, dc in _directions_for(cur_piece):
                jr, jc = r + dr, c + dc
                lr, lc = r + 2 * dr, c + 2 * dc
                if not self._in_bounds(lr, lc):
                    continue
                if (jr, jc) in captures:
                    continue
                jumped = board[jr][jc]
                if jumped == EMPTY:
                    continue
                if not _is_opponent_of(cur_piece, jumped):
                    continue
                if board[lr][lc] != EMPTY:
                    continue

                will_promote = (
                    (cur_piece == RED_MAN and lr == 0)
                    or (cur_piece == BLACK_MAN and lr == 7)
                )

                extended = True
                board[jr][jc] = EMPTY  # remove jumped piece for deeper search
                new_path = path + [(lr, lc)]
                new_captures = captures + [(jr, jc)]

                if will_promote:
                    # ACF: crowning stops the move.
                    results.append(
                        Move(
                            from_sq=(start_r, start_c),
                            path=tuple(new_path),
                            captures=tuple(new_captures),
                        )
                    )
                    board[jr][jc] = jumped
                    continue

                board[lr][lc] = cur_piece  # land
                recurse(lr, lc, cur_piece, new_path, new_captures)
                board[lr][lc] = EMPTY
                board[jr][jc] = jumped

            if not extended and path:
                results.append(
                    Move(
                        from_sq=(start_r, start_c),
                        path=tuple(path),
                        captures=tuple(captures),
                    )
                )

        recurse(start_r, start_c, start_piece, [], [])
        board[start_r][start_c] = start_piece  # put the lifted piece back
        return results

    # --- Display -----------------------------------------------------------

    def render(self) -> str:
        """Return a human-readable ASCII board.

        Empty dark squares show their standard-notation number so that the
        CLI user can move by entering ``11-15`` etc.
        """
        lines: List[str] = []
        lines.append("     a   b   c   d   e   f   g   h")
        lines.append("   +---+---+---+---+---+---+---+---+")
        for r in range(8):
            rank = 8 - r
            cells: List[str] = []
            for c in range(8):
                piece = self.board[r][c]
                if (r + c) % 2 == 0:
                    cells.append("   ")
                elif piece == EMPTY:
                    sq = _pos_to_num((r, c))
                    cells.append(f"{sq:>2} ")
                else:
                    cells.append(f" {piece} ")
            lines.append(f" {rank} |" + "|".join(cells) + "|")
            lines.append("   +---+---+---+---+---+---+---+---+")
        return "\n".join(lines)


def _is_opponent_of(my_piece: str, other: str) -> bool:
    if my_piece in RED_PIECES:
        return other in BLACK_PIECES
    if my_piece in BLACK_PIECES:
        return other in RED_PIECES
    return False
