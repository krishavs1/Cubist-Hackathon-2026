"""Tests for alpha-beta search."""

import random

import pytest

from src.game import Game, X, O, EMPTY
from src.search import search


def _set_board(cells, turn):
    """Build a Game from a 9-cell list and whose turn it is.

    History is left empty — tests should not rely on undoing past the
    constructed root.
    """
    return Game(board=list(cells), turn=turn)


# --- Returns a winning move when one exists ---------------------------------


def test_search_takes_immediate_win_for_x():
    # X to move with two in a row on the top.
    # X X .
    # O O .
    # . . .
    g = _set_board([X, X, EMPTY, O, O, EMPTY, EMPTY, EMPTY, EMPTY], turn=X)
    result = search(g)
    assert result.best_move == 2


def test_search_takes_immediate_win_for_o():
    # O to move with two in a column.
    # X . O
    # X . O
    # . . .
    g = _set_board([X, EMPTY, O, X, EMPTY, O, EMPTY, EMPTY, EMPTY], turn=O)
    result = search(g)
    assert result.best_move == 8


def test_search_prefers_faster_win():
    # X has both a mate-in-1 (square 2) and other moves.
    # The depth-adjusted evaluator should pick the mate-in-1.
    # X X .
    # . O .
    # O . .
    g = _set_board([X, X, EMPTY, EMPTY, O, EMPTY, O, EMPTY, EMPTY], turn=X)
    result = search(g)
    assert result.best_move == 2


# --- Blocks an opponent's immediate win -------------------------------------


def test_search_blocks_opponent_win_x_to_move():
    # O threatens to complete the top row; X must block at 2.
    # O O .
    # X . .
    # X . .
    g = _set_board([O, O, EMPTY, X, EMPTY, EMPTY, X, EMPTY, EMPTY], turn=X)
    result = search(g)
    assert result.best_move == 2


def test_search_blocks_opponent_win_o_to_move():
    # X threatens column 0; O must block at 6.
    # X . .
    # X . .
    # . O O
    g = _set_board([X, EMPTY, EMPTY, X, EMPTY, EMPTY, EMPTY, O, O], turn=O)
    result = search(g)
    assert result.best_move == 6


# --- Legality ---------------------------------------------------------------


def test_engine_never_returns_illegal_move_random_positions():
    rng = random.Random(0xC0FFEE)
    for _ in range(50):
        g = Game()
        # Play 0..6 random legal moves to reach an arbitrary non-terminal
        # position.
        n = rng.randint(0, 6)
        for _ in range(n):
            if g.is_terminal():
                break
            move = rng.choice(g.get_legal_moves())
            g.make_move(move)
        if g.is_terminal():
            continue
        legal = set(g.get_legal_moves())
        result = search(g)
        assert result.best_move in legal, (
            f"engine returned {result.best_move}, legal were {legal}, "
            f"board={g.board}"
        )


def test_search_returns_none_on_terminal_position():
    # No legal moves should produce no move.
    g = _set_board([X, X, X, O, O, EMPTY, EMPTY, EMPTY, EMPTY], turn=O)
    assert g.is_terminal()
    result = search(g)
    assert result.best_move is None


# --- Optimal play: never loses ---------------------------------------------


def _play_engine_vs_engine() -> str:
    """Engine plays both sides. Should always draw under perfect play."""
    g = Game()
    while not g.is_terminal():
        result = search(g)
        assert result.best_move in g.get_legal_moves()
        g.make_move(result.best_move)
    return g.winner()  # None == draw


def test_engine_vs_engine_is_draw():
    assert _play_engine_vs_engine() is None


def _play_against_random(engine_side: str, seed: int) -> str:
    rng = random.Random(seed)
    g = Game()
    while not g.is_terminal():
        if g.current_player() == engine_side:
            result = search(g)
            move = result.best_move
        else:
            move = rng.choice(g.get_legal_moves())
        assert move in g.get_legal_moves()
        g.make_move(move)
    return g.winner()


@pytest.mark.parametrize("seed", range(20))
def test_engine_as_x_never_loses_to_random(seed):
    winner = _play_against_random(engine_side=X, seed=seed)
    assert winner != O, f"engine playing X lost to random opponent (seed={seed})"


@pytest.mark.parametrize("seed", range(20))
def test_engine_as_o_never_loses_to_random(seed):
    winner = _play_against_random(engine_side=O, seed=seed)
    assert winner != X, f"engine playing O lost to random opponent (seed={seed})"


# --- Instrumentation --------------------------------------------------------


def test_search_reports_instrumentation():
    g = Game()
    result = search(g)
    assert result.stats.nodes_searched > 0
    assert result.stats.cutoffs >= 0
    assert result.stats.best_move == result.best_move
    assert result.stats.score == result.score


def test_alpha_beta_actually_prunes():
    # Searching from the empty board should produce at least one cutoff.
    # If alpha-beta is doing nothing, this would still be 0.
    g = Game()
    result = search(g)
    assert result.stats.cutoffs > 0
