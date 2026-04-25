"""Evaluation function.

For Tic-Tac-Toe the game is small enough to always search to terminal, so the
evaluator only needs to score terminal states. The signature mirrors what a
chess evaluator would look like: takes a game and a ply-from-root depth, and
returns a score from the perspective of X (positive = good for X).

The depth adjustment makes the engine prefer faster wins and slower losses —
without it, minimax is indifferent between mating in 1 and mating in 5.
"""

from __future__ import annotations

from .game import Game, X, O

# Large constant so terminal scores dominate anything a positional heuristic
# could return later when this evaluator is extended.
WIN_SCORE = 1000


def evaluate(game: Game, depth: int = 0) -> int:
    """Return a score from X's perspective.

    depth is plies searched from the root. Deeper wins are worth less, deeper
    losses are worth more (less negative), so the engine plays the quickest
    winning line and the most stubborn losing line.
    """
    winner = game.winner()
    if winner == X:
        return WIN_SCORE - depth
    if winner == O:
        return -WIN_SCORE + depth
    return 0
