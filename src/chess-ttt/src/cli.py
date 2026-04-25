"""Human-vs-engine command-line interface.

Accepts UCI-format moves (e.g. `e2e4`, `e7e8q` for promotion) and SAN as a
fallback (e.g. `Nf3`, `O-O`). UCI is the primary format because it makes a
future UCI-protocol bridge a one-line change.
"""

from __future__ import annotations

import time
from typing import Optional

import chess

from .game import ChessGame
from .search import search


DEFAULT_DEPTH = 3


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


def _print_board(game: ChessGame) -> None:
    print(game.render())
    print()
    print(f"FEN: {game.fen()}")


def play(human_color: chess.Color = chess.WHITE, depth: int = DEFAULT_DEPTH) -> None:
    game = ChessGame()
    print(f"You are {'White' if human_color == chess.WHITE else 'Black'}. "
          f"Engine searches to depth {depth}.")
    print("Enter moves in UCI (e2e4, g1f3) or SAN (e4, Nf3). 'quit' to exit.\n")

    while not game.is_terminal():
        _print_board(game)
        print()

        if game.current_player() == human_color:
            raw = input(f"Your move: ")
            if raw.strip().lower() in ("quit", "exit", "q"):
                print("Bye.")
                return
            move = _parse_move(game, raw)
            if move is None:
                print("Illegal or unparseable move. Try again.\n")
                continue
            game.make_move(move)
        else:
            t0 = time.time()
            result = search(game, max_depth=depth)
            dt = time.time() - t0
            assert result.best_move is not None, "engine produced no move"
            print(
                f"Engine plays {result.best_move.uci()}  "
                f"(score={result.score}, depth={result.stats.depth_reached}, "
                f"nodes={result.stats.nodes_searched}, "
                f"cutoffs={result.stats.cutoffs}, time={dt:.2f}s)"
            )
            game.make_move(result.best_move)
        print()

    _print_board(game)
    print()
    if game.is_checkmate():
        winner = "Black" if game.current_player() == chess.WHITE else "White"
        print(f"Checkmate. {winner} wins.")
    elif game.is_stalemate():
        print("Stalemate.")
    else:
        print("Draw.")
