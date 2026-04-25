"""Evaluator tests — targets the chess-specific terms that this engine
adds on top of the checkers evaluator structure:

    - Per-piece PSTs (existing, carried over in spirit from checkers).
    - Tapered king PST (midgame back-rank, endgame center).
    - Bishop pair bonus.
    - Doubled pawn penalty.
    - Mate score with ply adjustment.

Shape mirrors ``src/checkers/tests/test_search.py``'s evaluator block,
just scaled out since chess has more structural terms than checkers.
"""

from __future__ import annotations

import chess

from src.evaluate import (
    BISHOP_PAIR_BONUS,
    DOUBLED_PAWN_PENALTY,
    WIN_SCORE,
    _game_phase,
    evaluate,
)
from src.game import ChessGame


# --- Symmetry / sanity -----------------------------------------------------


def test_evaluate_starting_position_small_magnitude():
    # Start is symmetric; all terms except mobility cancel. Mobility for
    # the side-to-move is 20, so |score| should be near that.
    g = ChessGame()
    score = evaluate(g)
    assert abs(score) <= 25


def test_evaluate_material_advantage_for_white():
    # White up a queen: starting position minus the black queen on d8.
    g = ChessGame("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    assert evaluate(g) > 800


def test_evaluate_material_advantage_for_black():
    g = ChessGame("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1")
    assert evaluate(g) < -800


# --- Mate / stalemate / draw -----------------------------------------------


def test_evaluate_checkmate_against_black_is_win():
    # Black is mated.
    g = ChessGame("R5k1/5ppp/8/8/8/8/8/7K b - - 0 1")
    score = evaluate(g, ply=0)
    assert score >= WIN_SCORE - 10


def test_evaluate_checkmate_ply_adjustment():
    # Deeper mate (larger ply) scores slightly lower, so the engine
    # prefers shorter mates.
    g = ChessGame("R5k1/5ppp/8/8/8/8/8/7K b - - 0 1")
    s0 = evaluate(g, ply=0)
    s5 = evaluate(g, ply=5)
    assert s0 > s5


def test_evaluate_stalemate_is_zero():
    # Black to move, stalemated (classic K + Q setup).
    g = ChessGame("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    assert g.is_stalemate()
    assert evaluate(g) == 0


# --- Bishop pair -----------------------------------------------------------


def test_bishop_pair_bonus_applies_to_white():
    # White: K + 2B; Black: K + 2N. If the eval has no bishop-pair bonus
    # this is ~0 (two minor pieces each). With the bonus, White is ahead.
    g_pair = ChessGame("4k3/8/8/8/8/1n3n2/8/1B3B1K w - - 0 1")
    g_no_pair = ChessGame("4k3/8/8/8/8/1n3n2/8/1N3N1K w - - 0 1")
    # White has bishops in pair-case, knights in no-pair-case.
    # Piece values + PSTs are roughly equal (BISHOP=330 vs KNIGHT=320, so
    # bishops are 20 cp more each -> +40 without the bonus); bonus adds
    # BISHOP_PAIR_BONUS on top.
    delta = evaluate(g_pair) - evaluate(g_no_pair)
    assert delta >= BISHOP_PAIR_BONUS - 5


def test_bishop_pair_bonus_applies_to_black():
    # Mirror: Black has the pair.
    g_pair = ChessGame("1b3b1k/8/8/8/8/1N3N2/8/4K3 w - - 0 1")
    g_no_pair = ChessGame("1n3n1k/8/8/8/8/1N3N2/8/4K3 w - - 0 1")
    delta = evaluate(g_no_pair) - evaluate(g_pair)
    assert delta >= BISHOP_PAIR_BONUS - 5


# --- Doubled pawns ---------------------------------------------------------


def test_doubled_pawn_penalty_applies_to_white():
    # Compare white pawns on a2+a3 (doubled) vs a2+b2 (spread). Both pawn
    # positions have similar PST values (a2=5, a3=5, b2=10) so the PST
    # component doesn't swamp the penalty. Choosing c2+c4 vs d2+c4 would
    # not work: d2 has PST -20 (center pawn pushed backward is bad in
    # Michniewski's table), which cancels the doubled-pawn penalty.
    g_doubled = ChessGame("4k3/4p3/8/8/8/P7/P7/4K3 w - - 0 1")
    g_spread = ChessGame("4k3/4p3/8/8/8/8/PP6/4K3 w - - 0 1")
    delta = evaluate(g_spread) - evaluate(g_doubled)
    assert delta >= DOUBLED_PAWN_PENALTY - 5


def test_doubled_pawn_penalty_applies_to_black():
    g_doubled = ChessGame("4k3/5p2/8/5p2/8/8/4P3/4K3 w - - 0 1")
    g_spread = ChessGame("4k3/5p2/8/4p3/8/8/4P3/4K3 w - - 0 1")
    delta = evaluate(g_doubled) - evaluate(g_spread)
    assert delta >= DOUBLED_PAWN_PENALTY - 5


# --- Tapered king PST ------------------------------------------------------


def test_game_phase_starting_position_is_full_midgame():
    g = ChessGame()
    assert _game_phase(g.board) == 24


def test_game_phase_bare_kings_is_full_endgame():
    g = ChessGame("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
    assert _game_phase(g.board) == 0


def test_tapered_king_prefers_back_rank_in_midgame():
    # Midgame: full material on board except the white king, which sits on
    # e1 (back-rank) vs e4 (exposed center). Back rank must score higher.
    g_back = ChessGame("rnbq1bnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQK1NR w - - 0 1")
    g_center = ChessGame("rnbq1bnr/pppppppp/8/8/4K3/8/PPPPPPPP/RNBQ2NR w - - 0 1")
    # g_back should score higher for White (smaller penalty on king).
    assert evaluate(g_back) > evaluate(g_center)


def test_tapered_king_prefers_center_in_endgame():
    # Endgame: bare kings + a pawn each, white king on e4 (center) beats
    # white king on h1 (corner). The endgame king PST rewards centralization.
    g_center = ChessGame("8/8/3k4/8/4K3/4P3/8/8 w - - 0 1")
    g_corner = ChessGame("8/8/3k4/8/4P3/8/8/7K w - - 0 1")
    assert evaluate(g_center) > evaluate(g_corner)
