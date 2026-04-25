"""Search + iterative-deepening tests.

Shape mirrors ``src/checkers/tests/test_search.py``: return-a-legal-move
smoke, evaluator sanity, tactical puzzles, iterative-deepening
instrumentation and time-limit behavior, and an engine-vs-random battery.

The search module under test here is byte-identical to the one used by
Tic-Tac-Toe and checkers. These tests validate that, layered on top of
the python-chess game wrapper and the chess-specific evaluator, the same
core finds tactics and beats uniform-random play.
"""

from __future__ import annotations

import random

import chess
import pytest

from src.deepening import iterative_deepening
from src.evaluate import WIN_SCORE, evaluate
from src.game import ChessGame
from src.search import search


# --- Legality / sanity -----------------------------------------------------


def test_search_returns_a_legal_move_from_start():
    g = ChessGame()
    result = search(g, max_depth=2)
    assert result.best_move in g.get_legal_moves()
    assert result.stats.nodes_searched > 0


def test_search_returns_legal_moves_from_random_positions():
    rng = random.Random(0xCAFE)
    for _ in range(10):
        g = ChessGame()
        n = rng.randint(0, 8)
        for _ in range(n):
            if g.is_terminal():
                break
            g.make_move(rng.choice(g.get_legal_moves()))
        if g.is_terminal():
            continue
        result = search(g, max_depth=2)
        assert result.best_move in g.get_legal_moves(), (
            f"engine returned illegal {result.best_move} in FEN={g.fen()}"
        )


def test_search_returns_none_on_terminal_position():
    g = ChessGame("R5k1/5ppp/8/8/8/8/8/7K b - - 0 1")  # black is mated
    result = search(g, max_depth=2)
    assert result.best_move is None


@pytest.mark.parametrize("depth", [1, 2, 3])
def test_search_runs_at_each_depth(depth):
    g = ChessGame()
    result = search(g, max_depth=depth)
    assert result.best_move in g.get_legal_moves()
    assert result.stats.nodes_searched > 0
    assert result.stats.depth_reached == depth


def test_higher_depth_searches_more_nodes():
    g = ChessGame()
    r1 = search(g, max_depth=1)
    r2 = search(g, max_depth=2)
    r3 = search(g, max_depth=3)
    assert (
        r1.stats.nodes_searched
        < r2.stats.nodes_searched
        < r3.stats.nodes_searched
    )


def test_alpha_beta_actually_prunes():
    g = ChessGame()
    result = search(g, max_depth=3)
    assert result.stats.cutoffs > 0


# --- Tactical puzzles ------------------------------------------------------


def test_engine_finds_scholars_mate():
    # White to move, Qxf7# is the single-move win.
    fen = "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 4"
    g = ChessGame(fen)
    result = search(g, max_depth=2)
    assert result.best_move == chess.Move.from_uci("h5f7")
    assert result.score > 50_000


def test_engine_finds_back_rank_mate():
    fen = "6k1/5ppp/8/8/8/8/8/R6K w - - 0 1"
    g = ChessGame(fen)
    result = search(g, max_depth=2)
    assert result.best_move == chess.Move.from_uci("a1a8")


def test_engine_as_black_finds_mate_in_one():
    # Black queen a8 -> a1#. White king on h1 with a pawn wall on f2/g2/h2.
    fen = "q5k1/8/8/8/8/8/5PPP/7K b - - 0 1"
    g = ChessGame(fen)
    move = chess.Move.from_uci("a8a1")
    assert move in g.get_legal_moves()
    g.make_move(move)
    assert g.is_checkmate()
    g.undo_move()

    result = search(g, max_depth=2)
    assert result.best_move == move
    assert result.score < -50_000


def test_engine_captures_hanging_queen():
    # White knight on e4 attacks undefended black queen on d6.
    fen = "4k3/8/3q4/p7/4N3/8/P7/4K3 w - - 0 1"
    g = ChessGame(fen)
    result = search(g, max_depth=2)
    assert result.best_move == chess.Move.from_uci("e4d6")
    assert result.score > 200


def test_engine_avoids_leaving_queen_hanging():
    fen = "4k2b/8/8/8/3Q4/8/8/4K3 w - - 0 1"
    g = ChessGame(fen)
    result = search(g, max_depth=3)
    assert result.best_move is not None
    g.make_move(result.best_move)
    qs = [
        s for s, p in g.board.piece_map().items()
        if p.piece_type == chess.QUEEN and p.color == chess.WHITE
    ]
    if qs:
        qsq = qs[0]
        attackers = g.board.attackers(chess.BLACK, qsq)
        defenders = g.board.attackers(chess.WHITE, qsq)
        assert (not attackers) or (len(defenders) >= len(attackers)), (
            f"queen left hanging on {chess.square_name(qsq)} "
            f"FEN={g.fen()}"
        )


def test_engine_prefers_faster_mate():
    # Black is mated by Ra8# at depth 1. An engine that understands
    # mate-score ply adjustment scores this faster than any alternative.
    fen = "6k1/5ppp/8/8/8/8/8/R6K w - - 0 1"
    g = ChessGame(fen)
    result = search(g, max_depth=3)
    assert result.best_move == chess.Move.from_uci("a1a8")
    assert result.score > WIN_SCORE - 10


# --- Iterative deepening ---------------------------------------------------


def test_iterative_deepening_reports_stats():
    g = ChessGame()
    result = iterative_deepening(
        g, max_depth=3, time_limit=None, branching_estimate=6.0
    )
    assert result.best_move in g.get_legal_moves()
    assert result.depth_reached == 3
    assert result.total_nodes > 0
    assert len(result.per_depth) == 3


def test_iterative_deepening_respects_zero_time_budget():
    # With a zero budget the wrapper should still fall back to a legal move.
    g = ChessGame()
    result = iterative_deepening(
        g, max_depth=20, time_limit=0.0, branching_estimate=6.0
    )
    assert result.best_move in g.get_legal_moves()


def test_iterative_deepening_short_circuits_on_forced_mate():
    fen = "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 4"
    g = ChessGame(fen)
    result = iterative_deepening(
        g, max_depth=5, time_limit=None, branching_estimate=6.0
    )
    # Should stop early once mate is found.
    assert result.depth_reached <= 2
    assert result.best_move == chess.Move.from_uci("h5f7")


# --- Engine vs. random -----------------------------------------------------


def _play_engine_vs_random(
    engine_side: chess.Color, seed: int, max_depth: int = 2, max_plies: int = 160
):
    rng = random.Random(seed)
    g = ChessGame()
    plies = 0
    while not g.is_terminal() and plies < max_plies:
        moves = g.get_legal_moves()
        if g.current_player() == engine_side:
            result = search(g, max_depth=max_depth)
            mv = result.best_move or moves[0]
        else:
            mv = rng.choice(moves)
        g.make_move(mv)
        plies += 1
    if g.is_checkmate():
        # Side to move is mated -> the other side won.
        return not g.current_player()
    return None  # draw or cutoff — don't count as an engine win


def test_engine_beats_random_as_white():
    wins = 0
    for seed in range(3):
        winner = _play_engine_vs_random(chess.WHITE, seed=seed, max_depth=2)
        if winner == chess.WHITE:
            wins += 1
    assert wins >= 2, f"engine only beat random {wins}/3 as White"


def test_engine_beats_random_as_black():
    wins = 0
    for seed in range(3):
        winner = _play_engine_vs_random(chess.BLACK, seed=seed, max_depth=2)
        if winner == chess.BLACK:
            wins += 1
    assert wins >= 2, f"engine only beat random {wins}/3 as Black"


# --- Instrumentation -------------------------------------------------------


def test_search_reports_full_instrumentation():
    g = ChessGame()
    result = search(g, max_depth=2)
    s = result.stats
    assert s.nodes_searched > 0
    assert s.cutoffs >= 0
    assert s.best_move == result.best_move
    assert s.score == result.score
    assert s.depth_reached == 2
