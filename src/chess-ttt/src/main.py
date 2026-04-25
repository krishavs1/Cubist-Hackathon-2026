"""Entry point: `python -m src.main` from the project root."""

from __future__ import annotations

import argparse

import chess

from .cli import play, DEFAULT_DEPTH


def main() -> None:
    parser = argparse.ArgumentParser(description="Chess engine with alpha-beta search")
    parser.add_argument(
        "--play-as",
        choices=["white", "black", "w", "b"],
        default="white",
        help="Side the human plays (default: white)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=DEFAULT_DEPTH,
        help=f"Search depth in plies (default: {DEFAULT_DEPTH}). Higher = stronger and slower.",
    )
    args = parser.parse_args()
    color = chess.WHITE if args.play_as.startswith("w") else chess.BLACK
    play(human_color=color, depth=args.depth)


if __name__ == "__main__":
    main()
