"""Human-vs-engine command-line interface."""

from __future__ import annotations

from typing import Optional

from .game import Game, X, O
from .search import search


def _parse_move(raw: str) -> Optional[int]:
    raw = raw.strip()
    if not raw:
        return None
    try:
        n = int(raw)
    except ValueError:
        return None
    if not (0 <= n <= 8):
        return None
    return n


def _print_board(game: Game) -> None:
    # Show numbered squares once at the start of a game so the user knows
    # which integer maps to which square.
    print(game.render())


def _print_legend() -> None:
    print("Squares are numbered:")
    print(" 0 | 1 | 2")
    print("---+---+---")
    print(" 3 | 4 | 5")
    print("---+---+---")
    print(" 6 | 7 | 8")
    print()


def play(human: str = X) -> None:
    """Play one game of human vs. engine. `human` is 'X' or 'O'."""
    if human not in (X, O):
        raise ValueError("human must be 'X' or 'O'")
    engine = O if human == X else X

    game = Game()
    print(f"You are {human}. Engine is {engine}.")
    _print_legend()

    while not game.is_terminal():
        _print_board(game)
        print()
        if game.current_player() == human:
            raw = input(f"Your move ({human}) [0-8]: ")
            move = _parse_move(raw)
            if move is None or move not in game.get_legal_moves():
                print("Illegal move, try again.\n")
                continue
            game.make_move(move)
        else:
            result = search(game)
            assert result.best_move is not None, "engine produced no move"
            print(
                f"Engine plays {result.best_move}  "
                f"(score={result.score}, nodes={result.stats.nodes_searched}, "
                f"cutoffs={result.stats.cutoffs})"
            )
            game.make_move(result.best_move)
        print()

    _print_board(game)
    print()
    w = game.winner()
    if w is None:
        print("Draw.")
    elif w == human:
        print("You win.")
    else:
        print("Engine wins.")
