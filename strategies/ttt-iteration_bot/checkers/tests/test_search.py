"""Tests for the search behavior on checkers.

The search itself is BYTE-IDENTICAL to the Tic-Tac-Toe one — what we test
here is that it does the right thing on top of the checkers game and
evaluator: returns legal moves, finds free captures, prefers faster wins,
and beats a uniform-random mover."""

from __future__ import annotations

import random

import pytest

from src.deepening import iterative_deepening
from src.evaluate import WIN_SCORE, evaluate
from src.game import (
    BLACK,
    BLACK_KING,
    BLACK_MAN,
    CheckersGame,
    EMPTY,
    RED,
    RED_KING,
    RED_MAN,
)
from src.search import search


def _empty_board():
    return [[EMPTY] * 8 for _ in range(8)]


# --- Sanity ----------------------------------------------------------------


def test_search_returns_a_legal_move_from_start():
    g = CheckersGame()
    result = search(g, max_depth=4)
    assert result.best_move is not None
    assert result.best_move in g.get_legal_moves()
    assert result.stats.nodes_searched > 0


def test_search_respects_max_depth():
    g = CheckersGame()
    r1 = search(g, max_depth=1)
    r4 = search(g, max_depth=4)
    # Deeper searches visit strictly more nodes on the opening position.
    assert r4.stats.nodes_searched > r1.stats.nodes_searched


# --- Evaluation sanity -----------------------------------------------------


def test_evaluate_symmetric_on_start():
    # The starting position is symmetric, so material & advancement tables
    # should balance; only the mobility tie-breaker can shift it.
    g = CheckersGame()
    score = evaluate(g)
    assert abs(score) <= len(g.get_legal_moves()) + 1


def test_evaluate_favors_material_advantage_for_red():
    board = _empty_board()
    board[5][0] = RED_MAN
    board[5][2] = RED_MAN
    board[0][1] = BLACK_MAN  # Red up by a man
    g = CheckersGame(board=board, turn=RED)
    assert evaluate(g) > 50  # noticeable Red advantage


def test_evaluate_terminal_loss_for_side_to_move():
    # Black to move with no Black pieces -> Black loses -> score is +WIN_SCORE-ish
    board = _empty_board()
    board[5][0] = RED_MAN
    g = CheckersGame(board=board, turn=BLACK)
    score = evaluate(g)
    assert score >= WIN_SCORE - 10  # faster-win adjustment


# --- Tactical tests --------------------------------------------------------


def test_search_finds_free_capture():
    # Red to move, obvious free capture: 5,2 jumps 4,3 to 3,4.
    board = _empty_board()
    board[5][2] = RED_MAN
    board[4][3] = BLACK_MAN
    # Give Black a piece far away so the game isn't already over.
    board[0][1] = BLACK_MAN
    g = CheckersGame(board=board, turn=RED)
    result = search(g, max_depth=3)
    assert result.best_move is not None
    assert result.best_move.is_capture
    assert result.best_move.captures == ((4, 3),)


def test_search_finds_double_jump():
    board = _empty_board()
    board[5][0] = RED_MAN
    board[4][1] = BLACK_MAN
    board[2][3] = BLACK_MAN
    board[0][7] = BLACK_MAN  # extra black piece to keep game alive
    g = CheckersGame(board=board, turn=RED)
    result = search(g, max_depth=4)
    assert result.best_move is not None
    assert result.best_move.captures == ((4, 1), (2, 3))


def test_search_prefers_faster_win():
    # Position where Red has no Black pieces to capture and Black has no
    # moves at all -> Red should recognize the win. Use a slightly deeper
    # setup: Black has exactly one piece and Red can capture it next move
    # for a mate-in-1 (no Black pieces left -> Black's turn -> Black has
    # no moves -> Red wins).
    board = _empty_board()
    board[5][2] = RED_MAN
    board[4][3] = BLACK_MAN  # only black piece; will be captured
    g = CheckersGame(board=board, turn=RED)
    result = search(g, max_depth=4)
    assert result.best_move is not None
    assert result.best_move.captures == ((4, 3),)
    # Score should reflect a win for Red.
    assert result.score > 50_000


# --- Iterative deepening ---------------------------------------------------


def test_iterative_deepening_reports_depth_and_nodes():
    g = CheckersGame()
    result = iterative_deepening(g, max_depth=4, time_limit=None)
    assert result.best_move is not None
    assert result.depth_reached == 4
    assert result.total_nodes > 0
    assert len(result.per_depth) == 4


def test_iterative_deepening_respects_time_limit():
    g = CheckersGame()
    # 0-budget run should still fall back to a legal first move.
    result = iterative_deepening(g, max_depth=20, time_limit=0.0)
    assert result.best_move in g.get_legal_moves()


# --- Engine vs. random -----------------------------------------------------


def _play_engine_vs_random(
    engine_side: str, seed: int, max_depth: int = 3, max_plies: int = 120
):
    rng = random.Random(seed)
    g = CheckersGame()
    plies = 0
    while not g.is_terminal() and plies < max_plies:
        moves = g.get_legal_moves()
        if g.current_player() == engine_side:
            result = search(g, max_depth=max_depth)
            mv = result.best_move
            if mv is None:
                mv = moves[0]
        else:
            mv = rng.choice(moves)
        g.make_move(mv)
        plies += 1
    return g.winner()


def test_engine_beats_random_as_red():
    # A shallow engine should still reliably beat uniform-random play.
    wins = 0
    for seed in range(3):
        w = _play_engine_vs_random(RED, seed=seed, max_depth=3)
        if w == RED:
            wins += 1
    assert wins >= 2, f"engine only beat random {wins}/3 times as Red"


def test_engine_beats_random_as_black():
    wins = 0
    for seed in range(3):
        w = _play_engine_vs_random(BLACK, seed=seed, max_depth=3)
        if w == BLACK:
            wins += 1
    assert wins >= 2, f"engine only beat random {wins}/3 times as Black"
