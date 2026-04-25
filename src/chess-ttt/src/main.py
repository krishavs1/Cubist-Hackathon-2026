"""Entry point: ``python -m src.main [--play-as white|black] [--depth N] [--time S]``."""

from __future__ import annotations

import argparse

import chess

from .cli import DEFAULT_DEPTH, DEFAULT_TIME_LIMIT, play


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chess engine iterated on top of the checkers engine "
                    "(shared search.py and deepening.py)."
    )
    parser.add_argument(
        "--play-as",
        choices=["white", "black", "w", "b"],
        default="white",
        help="side the human plays (default: white, moves first)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=DEFAULT_DEPTH,
        help=f"iterative-deepening max depth (default: {DEFAULT_DEPTH})",
    )
    parser.add_argument(
        "--time",
        type=float,
        default=DEFAULT_TIME_LIMIT,
        help=f"wall-clock seconds per engine move "
             f"(default: {DEFAULT_TIME_LIMIT}; pass 0 to disable)",
    )
    args = parser.parse_args()

    color = chess.WHITE if args.play_as.startswith("w") else chess.BLACK
    time_limit = args.time if args.time > 0 else None
    play(human_color=color, depth=args.depth, time_limit=time_limit)


if __name__ == "__main__":
    main()
