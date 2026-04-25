"""Entry point: `python -m src.main` from the project root."""

from __future__ import annotations

import argparse

from .cli import play
from .game import X, O


def main() -> None:
    parser = argparse.ArgumentParser(description="Tic-Tac-Toe with alpha-beta engine")
    parser.add_argument(
        "--play-as",
        choices=[X, O],
        default=X,
        help="Which side the human plays (default: X moves first)",
    )
    args = parser.parse_args()
    play(human=args.play_as)


if __name__ == "__main__":
    main()
