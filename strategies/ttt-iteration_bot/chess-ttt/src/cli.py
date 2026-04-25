"""Human-vs-engine CLI for chess.

Mirrors the shape of ``src/checkers/src/cli.py``: prompts the user on
their turn, parses a move (UCI like ``e2e4`` or SAN like ``Nf3``), runs
the shared iterative-deepening wrapper on the engine's turn, and prints
per-move telemetry (depth reached, score, nodes, cutoffs).

Commands at any prompt:

    <move>     play a legal move (UCI or SAN)
    moves      list legal moves (UCI)
    help       notation legend
    quit       exit
"""

from __future__ import annotations

from typing import Optional

import chess

from .deepening import iterative_deepening
from .game import ChessGame


DEFAULT_DEPTH = 6
DEFAULT_TIME_LIMIT = 3.0
CHESS_BRANCHING = 6.0


def _parse_move(game: ChessGame, raw: str) -> Optional[chess.Move]:
    raw = raw.strip()
    if not raw:
        return None
    move = game.parse_uci(raw)
    if move is not None and move in game.board.legal_moves:
        return move
    move = game.parse_san(raw)
    if move is not None and move in game.board.legal_moves:
        return move
    return None


def _prompt_human(game: ChessGame) -> Optional[chess.Move]:
    while True:
        raw = input("Your move: ").strip()
        if not raw:
            continue
        lower = raw.lower()
        if lower in {"quit", "exit", "q"}:
            return None
        if lower in {"help", "?"}:
            print("  UCI: e2e4, g1f3, e7e8q (promotion)")
            print("  SAN: e4, Nf3, O-O")
            print("  Commands: moves | help | quit")
            continue
        if lower == "moves":
            print("  Legal:", " ".join(m.uci() for m in game.board.legal_moves))
            continue
        move = _parse_move(game, raw)
        if move is None:
            print("  Illegal or unparseable move. Type 'moves' for legal moves.")
            continue
        return move


def _print_board(game: ChessGame) -> None:
    print()
    print(game.render())
    print()
    print(f"FEN: {game.fen()}")


def play(
    human_color: chess.Color = chess.WHITE,
    depth: int = DEFAULT_DEPTH,
    time_limit: Optional[float] = DEFAULT_TIME_LIMIT,
) -> None:
    game = ChessGame()
    you = "White" if human_color == chess.WHITE else "Black"
    them = "Black" if human_color == chess.WHITE else "White"
    print(f"You are {you}. Engine is {them}.")
    print("Type 'help' for notation, 'moves' for legal moves, 'quit' to exit.")

    while not game.is_terminal():
        _print_board(game)
        if game.current_player() == human_color:
            move = _prompt_human(game)
            if move is None:
                print("Bye.")
                return
            game.make_move(move)
        else:
            result = iterative_deepening(
                game,
                max_depth=depth,
                time_limit=time_limit,
                branching_estimate=CHESS_BRANCHING,
            )
            move = result.best_move
            if move is None:
                print("Engine has no move (should not happen before terminal).")
                break
            print(
                f"Engine plays {move.uci()}  "
                f"(depth={result.depth_reached}, score={result.score}, "
                f"nodes={result.total_nodes}, cutoffs={result.total_cutoffs})"
            )
            game.make_move(move)

    _print_board(game)
    if game.is_checkmate():
        winner = "Black" if game.current_player() == chess.WHITE else "White"
        print(f"Checkmate. {winner} wins.")
    elif game.is_stalemate():
        print("Stalemate.")
    else:
        print("Draw.")
