"""Human-vs-engine CLI for checkers.

Accepts standard checkers notation:

    11-15          simple move
    22x18          single capture
    22x15x6        double capture
    22x15x6x13     triple capture (etc.)

At any point the user can type ``help`` for a legend, ``quit`` to exit,
or ``moves`` to list the currently legal moves.
"""

from __future__ import annotations

from typing import Optional

from .deepening import iterative_deepening
from .game import (
    BLACK,
    CheckersGame,
    Move,
    RED,
    parse_move,
)


def _describe_turn(game: CheckersGame) -> str:
    return "Red (r/R)" if game.current_player() == RED else "Black (b/B)"


def _print_board(game: CheckersGame) -> None:
    print()
    print(game.render())
    print()


def _prompt_human(game: CheckersGame) -> Optional[Move]:
    legal = game.get_legal_moves()
    while True:
        raw = input(f"{_describe_turn(game)} to move: ").strip()
        if not raw:
            continue
        lower = raw.lower()
        if lower in {"quit", "exit", "q"}:
            return None
        if lower in {"help", "?"}:
            print("  Moves are in standard checkers notation:")
            print("    11-15        simple move")
            print("    22x18        single capture")
            print("    22x15x6      multi-jump (chained captures)")
            print("  Commands: moves | help | quit")
            continue
        if lower == "moves":
            print("  Legal:")
            for m in legal:
                print(f"    {m.notation()}")
            continue
        move = parse_move(raw, legal)
        if move is None:
            print("  Illegal or unparseable move. Type 'moves' to list legal ones.")
            continue
        return move


def play(
    human: str = RED,
    depth: int = 8,
    time_limit: Optional[float] = 3.0,
) -> None:
    """Play one interactive game of human vs. engine.

    ``human`` is ``RED`` or ``BLACK``. ``depth`` is the iterative-deepening
    ceiling. ``time_limit`` (seconds) caps engine thinking per move.
    """
    if human not in (RED, BLACK):
        raise ValueError("human must be RED or BLACK")

    game = CheckersGame()
    print(f"You are {human}. Engine is {RED if human == BLACK else BLACK}.")
    print("Type 'help' at any prompt for notation, 'moves' to list legal moves.")

    while not game.is_terminal():
        _print_board(game)
        if game.current_player() == human:
            move = _prompt_human(game)
            if move is None:
                print("Quit.")
                return
            game.make_move(move)
        else:
            result = iterative_deepening(
                game, max_depth=depth, time_limit=time_limit
            )
            if result.best_move is None:
                print("Engine has no legal move (should not happen before terminal).")
                break
            print(
                f"Engine plays {result.best_move.notation()} "
                f"(depth={result.depth_reached}, score={result.score}, "
                f"nodes={result.total_nodes}, cutoffs={result.total_cutoffs})"
            )
            game.make_move(result.best_move)

    _print_board(game)
    w = game.winner()
    if w is None:
        print("Draw.")
    elif w == human:
        print("You win.")
    else:
        print("Engine wins.")
