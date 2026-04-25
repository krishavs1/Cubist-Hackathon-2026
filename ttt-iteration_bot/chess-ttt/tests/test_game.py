"""Tests for the ChessGame wrapper: terminal detection, legality, and the
generic interface that the search depends on.
"""

import chess
import pytest

from src.game import ChessGame


# --- Generic interface contract --------------------------------------------


def test_initial_position_has_20_legal_moves():
    g = ChessGame()
    assert len(g.get_legal_moves()) == 20


def test_initial_position_white_to_move():
    g = ChessGame()
    assert g.current_player() == chess.WHITE
    assert g.is_maximizing_player() is True


def test_after_one_move_black_to_move():
    g = ChessGame()
    g.make_move(chess.Move.from_uci("e2e4"))
    assert g.current_player() == chess.BLACK
    assert g.is_maximizing_player() is False


def test_make_move_rejects_illegal():
    g = ChessGame()
    with pytest.raises(ValueError):
        g.make_move(chess.Move.from_uci("e2e5"))  # pawn can't jump 3 squares


def test_undo_restores_position():
    g = ChessGame()
    fen0 = g.fen()
    moves = ["e2e4", "e7e5", "g1f3", "b8c6"]
    for u in moves:
        g.make_move(chess.Move.from_uci(u))
    fen_mid = g.fen()
    for _ in moves:
        g.undo_move()
    assert g.fen() == fen0
    # Sanity: redo to the mid-state
    for u in moves:
        g.make_move(chess.Move.from_uci(u))
    assert g.fen() == fen_mid


def test_undo_on_empty_history_raises():
    g = ChessGame()
    with pytest.raises(ValueError):
        g.undo_move()


# --- Checkmate detection ----------------------------------------------------


def test_back_rank_mate_is_terminal():
    # Black king on g8 boxed in by own pawns; white rook on a8 mates.
    fen = "R5k1/5ppp/8/8/8/8/8/7K b - - 0 1"
    g = ChessGame(fen)
    assert g.is_terminal()
    assert g.is_checkmate()
    assert not g.is_stalemate()
    assert g.get_legal_moves() == []


def test_fools_mate_position_is_checkmate():
    # Quickest possible mate from start: 1.f3 e5 2.g4 Qh4#
    g = ChessGame()
    for u in ["f2f3", "e7e5", "g2g4", "d8h4"]:
        g.make_move(chess.Move.from_uci(u))
    assert g.is_checkmate()
    assert g.is_terminal()


# --- Stalemate detection ---------------------------------------------------


def test_classic_stalemate_is_terminal_and_not_checkmate():
    # Black king on h8, no legal moves, not in check.
    # White Kg6, Qf7, Black Kh8. Black to move.
    fen = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
    g = ChessGame(fen)
    assert g.is_terminal()
    assert g.is_stalemate()
    assert not g.is_checkmate()
    assert g.get_legal_moves() == []


# --- Round-trip with make/undo across many moves ---------------------------


def test_long_make_undo_chain_preserves_state():
    g = ChessGame()
    moves_uci = [
        "e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "g8f6",
        "e1g1",  # white short castles
        "f8e7",
        "d2d3", "e8g8",  # black short castles
    ]
    fen0 = g.fen()
    for u in moves_uci:
        g.make_move(chess.Move.from_uci(u))
    castled_fen = g.fen()
    for _ in moves_uci:
        g.undo_move()
    assert g.fen() == fen0
    for u in moves_uci:
        g.make_move(chess.Move.from_uci(u))
    assert g.fen() == castled_fen


# --- Parsing helpers (for CLI / future UCI) --------------------------------


def test_parse_uci_valid_and_invalid():
    g = ChessGame()
    assert g.parse_uci("e2e4") == chess.Move.from_uci("e2e4")
    # Garbage strings shouldn't raise; they should return None.
    assert g.parse_uci("zzz") is None


def test_parse_san_valid_and_invalid():
    g = ChessGame()
    assert g.parse_san("e4") == chess.Move.from_uci("e2e4")
    assert g.parse_san("Nxe5") is None  # no knight can capture on e5 from start
