"""Perft — "performance test" — counts the exact number of legal
leaf positions at each search depth from a given root. It's the gold
standard for verifying chess move-gen correctness.

We're not implementing move generation (python-chess does that), so this
battery primarily verifies that our ``ChessGame`` make/undo wrapper
behaves correctly under the same heavy move/undo patterns the search
uses: apply N plies, reach a leaf, rewind. Any bookkeeping bug in the
wrapper (castling-rights leakage, en-passant state drift, turn desync)
would show up as a count mismatch against the well-known reference
numbers.

Reference positions and counts:

- Startpos (the standard opening position):
    perft(1) = 20
    perft(2) = 400
    perft(3) = 8902
    (perft(4) = 197281, kept behind a slow marker for reasonable CI time.)

- Kiwipete (Chess Programming Wiki position 2):
    FEN: r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq -
    perft(1) = 48
    perft(2) = 2039
    perft(3) = 97862  (slow-marker)
"""

from __future__ import annotations

import os

import pytest

from src.game import ChessGame


# Slow perft is expensive (depth 4 startpos ≈ 200k nodes, takes several
# seconds with pure-Python make/undo). Gate behind an env var so normal
# `pytest tests/` stays fast; run them explicitly with
# ``CHESS_SLOW_TESTS=1 pytest tests/``.
_RUN_SLOW = os.environ.get("CHESS_SLOW_TESTS") == "1"
_slow = pytest.mark.skipif(not _RUN_SLOW, reason="slow; set CHESS_SLOW_TESTS=1")


def _perft(game: ChessGame, depth: int) -> int:
    """Recursive perft using the generic game interface (not python-chess's
    own perft helper), so we exercise *our* make/undo wrapper."""
    if depth == 0:
        return 1
    moves = game.get_legal_moves()
    if depth == 1:
        return len(moves)
    count = 0
    for move in moves:
        game.make_move(move)
        count += _perft(game, depth - 1)
        game.undo_move()
    return count


# --- Startpos --------------------------------------------------------------


@pytest.mark.parametrize("depth,expected", [(1, 20), (2, 400), (3, 8902)])
def test_perft_startpos(depth, expected):
    g = ChessGame()
    assert _perft(g, depth) == expected


@_slow
def test_perft_startpos_depth_4():
    g = ChessGame()
    assert _perft(g, 4) == 197281


# --- Kiwipete --------------------------------------------------------------


KIWIPETE = (
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
)


@pytest.mark.parametrize("depth,expected", [(1, 48), (2, 2039)])
def test_perft_kiwipete(depth, expected):
    g = ChessGame(KIWIPETE)
    assert _perft(g, depth) == expected


@_slow
def test_perft_kiwipete_depth_3():
    g = ChessGame(KIWIPETE)
    assert _perft(g, 3) == 97862


# --- Position after moves / roundtrip ---------------------------------------


def test_perft_startpos_leaves_board_unchanged():
    """After perft(3), the board state must be byte-identical to the start
    — proves our undo_move fully restores everything perft touches
    (turn, castling rights, en passant file, halfmove clock, full move
    number)."""
    g = ChessGame()
    fen_before = g.fen()
    _perft(g, 3)
    assert g.fen() == fen_before
