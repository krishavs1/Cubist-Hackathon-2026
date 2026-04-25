"""Tests for the chess search.

This file mirrors the structure of the Tic-Tac-Toe search tests: legality,
tactical correctness (mate-in-1, captures), and instrumentation.

Crucially, the *search module* under test here is byte-identical to the one
verified on Tic-Tac-Toe — only the game and evaluator have changed. These
tests are therefore validating that the architecture transferred cleanly.
"""

import random

import chess
import pytest

from src.game import ChessGame
from src.search import search


# --- Engine returns only legal moves ---------------------------------------


def test_engine_returns_legal_move_from_start():
    g = ChessGame()
    result = search(g, max_depth=2)
    assert result.best_move in g.get_legal_moves()


def test_engine_returns_legal_move_from_random_positions():
    rng = random.Random(0xCAFE)
    for trial in range(10):
        g = ChessGame()
        # Play 0..8 random legal moves to reach an arbitrary non-terminal
        # position.
        n = rng.randint(0, 8)
        for _ in range(n):
            if g.is_terminal():
                break
            move = rng.choice(g.get_legal_moves())
            g.make_move(move)
        if g.is_terminal():
            continue
        result = search(g, max_depth=2)
        assert result.best_move in g.get_legal_moves(), (
            f"engine returned {result.best_move} which is not legal in "
            f"FEN={g.fen()}"
        )


def test_engine_returns_none_on_terminal_position():
    fen = "R5k1/5ppp/8/8/8/8/8/7K b - - 0 1"  # black is mated
    g = ChessGame(fen)
    result = search(g, max_depth=2)
    assert result.best_move is None


# --- Mate-in-one (white) ---------------------------------------------------


def test_engine_finds_scholars_mate():
    # Position right before Qxf7#. White to move. Legendary one-move mate.
    fen = "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 4"
    g = ChessGame(fen)
    result = search(g, max_depth=2)
    assert result.best_move == chess.Move.from_uci("h5f7"), (
        f"expected Qxf7# (h5f7), got {result.best_move}"
    )
    # And the score should be a huge positive (mate-in-1 from White's POV).
    assert result.score > 50_000


def test_engine_finds_back_rank_mate():
    # White to move with rook lift available: Ra1 -> Ra8#.
    # Setup: black king g8 with own pawns, white rook a1, white king h1.
    fen = "6k1/5ppp/8/8/8/8/8/R6K w - - 0 1"
    g = ChessGame(fen)
    result = search(g, max_depth=2)
    assert result.best_move == chess.Move.from_uci("a1a8"), (
        f"expected Ra8# (a1a8), got {result.best_move}"
    )


# --- Mate-in-one (black) — exercises the minimizing side ------------------


def test_engine_as_black_finds_mate_in_one():
    # Mirror of the back-rank mate: black to deliver, white king boxed in.
    fen = "1k5R/8/8/8/8/8/5PPP/6K1 b - - 0 1"
    # Wait: the side delivering mate must be black. Let me set up so Black
    # has Ra-something#. Easier: use the symmetric "fool's mate"-style
    # position where black has Qh4# already played — but that's terminal.
    # Instead: black to move with rook on a-file ready to swing.
    fen = "6k1/8/8/8/8/8/5PPP/r5K1 b - - 0 1"
    # Black: Ra1-h1 isn't legal (rook has to go to file h), but Rg1+ is mate?
    # White king on g1 — wait white king on g1, rook capturing? Let me just
    # construct a different position.
    # White king on h1, all white pawns f2,g2,h2 boxing it in; black queen
    # on a8 swings to a1#.
    fen = "q5k1/8/8/8/8/8/5PPP/7K b - - 0 1"
    g = ChessGame(fen)
    # Verify Black can play Qa1#: queen a8 to a1 along the a-file, then
    # delivers mate on rank 1.
    move = chess.Move.from_uci("a8a1")
    assert move in g.get_legal_moves(), (
        f"Qa1 should be legal; legal moves: "
        f"{[m.uci() for m in g.get_legal_moves()]}"
    )
    # Confirm it's actually mate by playing it.
    g.make_move(move)
    assert g.is_checkmate(), f"Qa1 should be mate, FEN now: {g.fen()}"
    g.undo_move()

    result = search(g, max_depth=2)
    assert result.best_move == move, (
        f"expected Qa1# (a8a1), got {result.best_move}"
    )
    # Score from White's perspective should be hugely negative (Black wins).
    assert result.score < -50_000


# --- Captures hanging material ---------------------------------------------


def test_engine_captures_hanging_queen():
    # White knight on e4, black queen on d6 (undefended, attacked by
    # knight). Pawns are added on both sides so the post-capture position
    # is not insufficient material (which would score 0 and mask the win).
    fen = "4k3/8/3q4/p7/4N3/8/P7/4K3 w - - 0 1"
    g = ChessGame(fen)
    result = search(g, max_depth=2)
    assert result.best_move == chess.Move.from_uci("e4d6"), (
        f"expected Nxd6 (e4d6), got {result.best_move}"
    )
    # The captured queen is worth ~900 cp; even after black's reply the
    # evaluation should swing strongly positive. (Won't equal +900 because
    # the position before already had black up material in PST/mobility.)
    assert result.score > 200


def test_engine_avoids_giving_up_queen_for_free():
    # White queen on d4, attacked by black bishop on h8 along the diagonal.
    # White's other moves are unforced. Engine must NOT move queen to e5
    # (still attacked) — but it can, e.g., move the queen safely or play
    # something else. We assert: engine doesn't leave queen hanging on a
    # square attacked by the bishop with no defender.
    fen = "4k2b/8/8/8/3Q4/8/8/4K3 w - - 0 1"
    g = ChessGame(fen)
    result = search(g, max_depth=3)
    move = result.best_move
    assert move is not None
    # Apply the move and verify white's queen is not en prise without
    # compensation.
    g.make_move(move)
    # Find white's queen.
    queen_squares = [s for s, p in g.board.piece_map().items()
                     if p.piece_type == chess.QUEEN and p.color == chess.WHITE]
    if queen_squares:
        qsq = queen_squares[0]
        attackers = g.board.attackers(chess.BLACK, qsq)
        defenders = g.board.attackers(chess.WHITE, qsq)
        # If queen is attacked, it must be defended (or about to capture
        # the attacker on the next move — but a depth-3 engine should have
        # avoided the situation).
        assert (not attackers) or (len(defenders) >= len(attackers)), (
            f"engine left queen on {chess.square_name(qsq)} hanging, FEN={g.fen()}"
        )


# --- Search works at depth 1, 2, 3 -----------------------------------------


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
    assert r1.stats.nodes_searched < r2.stats.nodes_searched < r3.stats.nodes_searched


def test_alpha_beta_prunes_at_depth_3():
    g = ChessGame()
    result = search(g, max_depth=3)
    # If alpha-beta is doing nothing, this would be 0.
    assert result.stats.cutoffs > 0


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
