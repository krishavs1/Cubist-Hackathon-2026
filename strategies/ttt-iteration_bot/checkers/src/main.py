"""Entry point: ``python -m src.main [--play-as red|black] [--depth N] [--time S]``."""

from __future__ import annotations

import argparse

from .cli import play
from .game import BLACK, RED


def main() -> None:
    parser = argparse.ArgumentParser(description="Play checkers against the engine")
    parser.add_argument(
        "--play-as",
        choices=["red", "black"],
        default="red",
        help="which side the human plays (default: red, which moves first)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=8,
        help="iterative-deepening max depth (default: 8)",
    )
    parser.add_argument(
        "--time",
        type=float,
        default=3.0,
        help="wall-clock seconds per engine move (default: 3.0)",
    )
    args = parser.parse_args()

    human = RED if args.play_as == "red" else BLACK
    play(human=human, depth=args.depth, time_limit=args.time)


if __name__ == "__main__":
    main()
