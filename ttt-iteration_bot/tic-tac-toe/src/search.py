"""Generic alpha-beta search.

This module is intentionally game-agnostic. It only talks to the game through:
    - get_legal_moves()
    - make_move(move)
    - undo_move()
    - is_terminal()
    - is_maximizing_player()

The same search function should work unchanged on a chess `Game` that exposes
the same interface — only `evaluate` and the underlying `Game` change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .evaluate import evaluate, WIN_SCORE


@dataclass
class SearchStats:
    nodes_searched: int = 0
    cutoffs: int = 0
    best_move: Optional[Any] = None
    score: int = 0
    depth_reached: int = 0


@dataclass
class SearchResult:
    best_move: Optional[Any]
    score: int
    stats: SearchStats = field(default_factory=SearchStats)


def search(game, max_depth: int = 64) -> SearchResult:
    """Find the best move for the player to move.

    Returns the move and the score from the maximizer's perspective.
    `max_depth` is large enough by default that Tic-Tac-Toe is solved
    exactly; for chess the caller should pass a smaller cap (e.g. 3-5).
    """
    stats = SearchStats()
    stats.depth_reached = max_depth
    maximizing = game.is_maximizing_player()

    score, best = _alphabeta(
        game,
        depth=max_depth,
        ply=0,
        alpha=-10 * WIN_SCORE,
        beta=10 * WIN_SCORE,
        maximizing=maximizing,
        stats=stats,
    )

    stats.best_move = best
    stats.score = score
    return SearchResult(best_move=best, score=score, stats=stats)


def _alphabeta(
    game,
    depth: int,
    ply: int,
    alpha: int,
    beta: int,
    maximizing: bool,
    stats: SearchStats,
):
    """Returns (score, best_move_at_this_node).

    `ply` is plies from the root; passed to evaluate() so faster wins score
    higher than slower wins. `depth` is the remaining search depth budget.
    """
    stats.nodes_searched += 1

    if game.is_terminal() or depth == 0:
        return evaluate(game, ply), None

    legal = game.get_legal_moves()
    # Defensive: get_legal_moves on a non-terminal node should always be
    # non-empty for Tic-Tac-Toe, but keep the guard for safety.
    if not legal:
        return evaluate(game, ply), None

    best_move: Optional[int] = None

    if maximizing:
        best_score = -10 * WIN_SCORE
        for move in legal:
            game.make_move(move)
            score, _ = _alphabeta(game, depth - 1, ply + 1, alpha, beta, False, stats)
            game.undo_move()

            if score > best_score:
                best_score = score
                best_move = move
            if best_score > alpha:
                alpha = best_score
            if alpha >= beta:
                stats.cutoffs += 1
                break
        return best_score, best_move
    else:
        best_score = 10 * WIN_SCORE
        for move in legal:
            game.make_move(move)
            score, _ = _alphabeta(game, depth - 1, ply + 1, alpha, beta, True, stats)
            game.undo_move()

            if score < best_score:
                best_score = score
                best_move = move
            if best_score < beta:
                beta = best_score
            if alpha >= beta:
                stats.cutoffs += 1
                break
        return best_score, best_move
