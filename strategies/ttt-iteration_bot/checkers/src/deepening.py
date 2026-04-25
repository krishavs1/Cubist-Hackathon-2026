"""Iterative deepening wrapper around the depth-bounded search.

Game-agnostic by design: works for any game whose object exposes the same
interface the inherited ``search.py`` depends on
(``get_legal_moves / make_move / undo_move / is_terminal / current_player /
is_maximizing_player``). This keeps the "same engine" property of the
branch extending past the search core: this file is byte-identical across
every game that wants iterative deepening on top of the inherited
alpha-beta.

The only knob that varies by game is ``branching_estimate``, used by the
predictor to decide whether to start the next iteration given remaining
time. Tic-Tac-Toe doesn't need this wrapper at all; checkers uses ~4;
chess uses ~6.

The search itself is depth-bounded, not time-bounded. We run depth 1, 2,
3, ... up to either ``max_depth`` or a wall-clock ``time_limit``, and
return the last **completed** iteration's move. A partial iteration never
leaks a half-baked move.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, List, Optional

from .search import SearchResult, search


@dataclass
class DeepeningResult:
    best_move: Optional[Any]
    score: int
    depth_reached: int
    total_nodes: int
    total_cutoffs: int
    per_depth: List[SearchResult] = field(default_factory=list)


def iterative_deepening(
    game: Any,
    max_depth: int = 10,
    time_limit: Optional[float] = None,
    branching_estimate: float = 4.0,
) -> DeepeningResult:
    """Run iterative deepening from depth 1 up to ``max_depth``.

    If ``time_limit`` (seconds) is given, abort *before* starting an
    iteration that is predicted to blow the remaining budget.

    ``branching_estimate`` is the expected cost multiplier per additional
    ply after alpha-beta pruning. Used only by the predictor; lower values
    make the wrapper more willing to start deeper iterations.

    Always returns the last completed iteration's result. If not even
    depth 1 finishes, ``best_move`` falls back to the first legal move and
    ``score`` to 0.
    """
    start = time.time()
    deadline = start + time_limit if time_limit is not None else None

    best_move: Optional[Any] = None
    score = 0
    depth_reached = 0
    total_nodes = 0
    total_cutoffs = 0
    per_depth: List[SearchResult] = []

    last_iter_time = 1e-4

    legal = game.get_legal_moves()
    if legal:
        best_move = legal[0]

    for depth in range(1, max_depth + 1):
        if deadline is not None:
            now = time.time()
            remaining = deadline - now
            if remaining <= 0:
                break
            predicted = last_iter_time * branching_estimate
            if depth > 1 and predicted > remaining:
                break

        t0 = time.time()
        result = search(game, max_depth=depth)
        last_iter_time = max(time.time() - t0, 1e-4)

        per_depth.append(result)
        total_nodes += result.stats.nodes_searched
        total_cutoffs += result.stats.cutoffs

        if result.best_move is not None:
            best_move = result.best_move
            score = result.score
            depth_reached = depth

        # Short-circuit on forced wins / losses (score saturates near WIN_SCORE).
        if abs(score) > 50_000:
            break

    return DeepeningResult(
        best_move=best_move,
        score=score,
        depth_reached=depth_reached,
        total_nodes=total_nodes,
        total_cutoffs=total_cutoffs,
        per_depth=per_depth,
    )
