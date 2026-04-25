"""Tests for game rules and terminal detection."""

import pytest

from src.game import Game, X, O, EMPTY


# --- Move generation --------------------------------------------------------


def test_initial_board_has_nine_legal_moves():
    g = Game()
    assert sorted(g.get_legal_moves()) == list(range(9))


def test_legal_moves_excludes_occupied_squares():
    g = Game()
    g.make_move(4)
    g.make_move(0)
    legal = set(g.get_legal_moves())
    assert 4 not in legal
    assert 0 not in legal
    assert legal == {1, 2, 3, 5, 6, 7, 8}


def test_legal_moves_empty_after_terminal_win():
    g = Game()
    # X wins on the top row
    for m in [0, 3, 1, 4, 2]:
        g.make_move(m)
    assert g.is_terminal()
    assert g.get_legal_moves() == []


def test_make_move_rejects_out_of_range():
    g = Game()
    with pytest.raises(ValueError):
        g.make_move(9)
    with pytest.raises(ValueError):
        g.make_move(-1)


def test_make_move_rejects_occupied_square():
    g = Game()
    g.make_move(0)
    with pytest.raises(ValueError):
        g.make_move(0)


def test_undo_restores_state_exactly():
    g = Game()
    for m in [4, 0, 8, 1]:
        g.make_move(m)
    snapshot_board = list(g.board)
    snapshot_turn = g.current_player()

    g.make_move(2)
    g.undo_move()

    assert g.board == snapshot_board
    assert g.current_player() == snapshot_turn


def test_undo_to_empty():
    g = Game()
    moves = [4, 0, 8, 1, 7]
    for m in moves:
        g.make_move(m)
    for _ in moves:
        g.undo_move()
    assert g.board == [EMPTY] * 9
    assert g.current_player() == X
    with pytest.raises(ValueError):
        g.undo_move()


# --- Win detection ----------------------------------------------------------


@pytest.mark.parametrize("row", [0, 1, 2])
def test_row_wins(row):
    # X plays row r, O plays the row below (or above) but never completes it.
    base = row * 3
    other = 0 if row != 0 else 3
    g = Game()
    g.make_move(base + 0)        # X
    g.make_move(other + 0)       # O
    g.make_move(base + 1)        # X
    g.make_move(other + 1)       # O
    g.make_move(base + 2)        # X wins
    assert g.is_terminal()
    assert g.winner() == X


@pytest.mark.parametrize("col", [0, 1, 2])
def test_column_wins(col):
    other = 1 if col != 1 else 0
    g = Game()
    g.make_move(col)             # X
    g.make_move(other)           # O
    g.make_move(col + 3)         # X
    g.make_move(other + 3)       # O
    g.make_move(col + 6)         # X wins
    assert g.is_terminal()
    assert g.winner() == X


def test_diagonal_main_win():
    g = Game()
    # X: 0,4,8 ; O: 1,2
    for m in [0, 1, 4, 2, 8]:
        g.make_move(m)
    assert g.winner() == X


def test_diagonal_anti_win():
    g = Game()
    # X: 2,4,6 ; O: 0,1
    for m in [2, 0, 4, 1, 6]:
        g.make_move(m)
    assert g.winner() == X


def test_o_can_also_win():
    g = Game()
    # X plays poorly: 0, 3, 7 ; O wins on the second row 4,5 then... build it:
    # X:0  O:4  X:1  O:5  X:7  O:3 -> O completes middle row 3,4,5
    for m in [0, 4, 1, 5, 7, 3]:
        g.make_move(m)
    assert g.winner() == O


# --- Draw -------------------------------------------------------------------


def test_draw_position():
    g = Game()
    # Classic drawn game:
    # X O X
    # X O O
    # O X X
    # Move order:
    for m in [0, 1, 2, 4, 3, 6, 7, 5, 8]:
        g.make_move(m)
    assert g.is_terminal()
    assert g.winner() is None


def test_non_terminal_position():
    g = Game()
    g.make_move(0)
    g.make_move(4)
    assert not g.is_terminal()
    assert g.winner() is None


# --- Turn alternation -------------------------------------------------------


def test_turn_alternates():
    g = Game()
    assert g.current_player() == X
    g.make_move(0)
    assert g.current_player() == O
    g.make_move(1)
    assert g.current_player() == X
