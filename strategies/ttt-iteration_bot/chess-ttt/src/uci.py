"""UCI bridge — sits on top of the shared ``deepening`` wrapper.

The iterative-deepening loop used to live in this file. It was pulled out
into ``src/checkers/src/deepening.py`` as a game-agnostic primitive; this
file now just translates UCI commands to ``iterative_deepening`` calls
and UCI ``info`` / ``bestmove`` lines back out.

Supported commands (the subset the elo-test arena uses):

    uci                 -> id / uciok
    isready             -> readyok
    ucinewgame          -> reset game state
    position startpos [moves ...]
    position fen <fen>  [moves ...]
    go [movetime <ms>] [depth <d>] [wtime ...] [btime ...]
    stop                -> no-op (we don't run searches concurrently)
    quit

Unknown commands are silently ignored, per the UCI spec.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Callable, Optional

import chess

from .deepening import iterative_deepening
from .game import ChessGame


ENGINE_NAME = "chess-from-checkers"
ENGINE_AUTHOR = "checkers-iterated alpha-beta"

# Branching estimate used by the shared deepening wrapper. ~6 is
# conservative for chess without strong move ordering — measured numbers
# on this engine sit between 5 and 8.
CHESS_BRANCHING = 6.0

# Search caps / safety margins.
MAX_DEPTH = 6                 # absolute ceiling regardless of time
DEFAULT_DEPTH_NO_TIME = 3     # used if the GUI provides no timing info
SAFETY_FRACTION = 0.5         # spend at most this fraction of remaining budget
PER_MOVE_FRACTION = 1 / 30.0  # if only wtime/btime given, assume 30 moves left


def _choose_time_limit_s(go_args: dict, game: ChessGame) -> Optional[float]:
    """Translate UCI go-arguments into a wall-clock budget in seconds.

    Returns None if the caller supplied no time control (caller should
    fall back to a depth-only search).
    """
    if "movetime" in go_args:
        return (int(go_args["movetime"]) / 1000.0) * SAFETY_FRACTION

    side_key = "wtime" if game.current_player() == chess.WHITE else "btime"
    if side_key in go_args:
        remaining_s = int(go_args[side_key]) / 1000.0
        return max(0.02, remaining_s * PER_MOVE_FRACTION)

    return None


def _parse_position(parts: list[str]) -> ChessGame:
    if not parts:
        return ChessGame()

    if parts[0] == "startpos":
        game = ChessGame()
        moves_idx = 1
    elif parts[0] == "fen":
        fen_parts = parts[1:7]
        game = ChessGame(" ".join(fen_parts))
        moves_idx = 7
    else:
        return ChessGame()

    if moves_idx < len(parts) and parts[moves_idx] == "moves":
        for uci in parts[moves_idx + 1:]:
            try:
                move = chess.Move.from_uci(uci)
            except ValueError:
                break
            if move in game.board.legal_moves:
                game.make_move(move)
            else:
                break

    return game


def _parse_go_args(parts: list[str]) -> dict:
    args: dict = {}
    int_keys = {
        "movetime", "depth", "wtime", "btime", "winc", "binc",
        "movestogo", "nodes",
    }
    flag_keys = {"infinite", "ponder"}
    i = 0
    while i < len(parts):
        key = parts[i]
        if key in int_keys and i + 1 < len(parts):
            try:
                args[key] = int(parts[i + 1])
            except ValueError:
                pass
            i += 2
        elif key in flag_keys:
            args[key] = True
            i += 1
        else:
            i += 1
    return args


def _handle_go(game: ChessGame, go_args: dict, log: Callable[[str], None]) -> str:
    if game.is_terminal():
        return "bestmove 0000"

    if "depth" in go_args:
        max_depth = min(int(go_args["depth"]), MAX_DEPTH)
        time_limit: Optional[float] = None
    else:
        max_depth = MAX_DEPTH
        time_limit = _choose_time_limit_s(go_args, game)
        if time_limit is None:
            max_depth = DEFAULT_DEPTH_NO_TIME

    t0 = time.time()
    result = iterative_deepening(
        game,
        max_depth=max_depth,
        time_limit=time_limit,
        branching_estimate=CHESS_BRANCHING,
    )
    elapsed_ms = int((time.time() - t0) * 1000)

    best_move = result.best_move
    if best_move is None:
        legal = game.get_legal_moves()
        if legal:
            best_move = legal[0]
        else:
            return "bestmove 0000"

    print(
        f"info depth {result.depth_reached} score cp {result.score} "
        f"nodes {result.total_nodes} time {elapsed_ms}",
        flush=True,
    )
    log(
        f"GO -> bestmove {best_move.uci()} depth={result.depth_reached} "
        f"score={result.score} nodes={result.total_nodes} "
        f"cutoffs={result.total_cutoffs} time={elapsed_ms}ms"
    )
    return f"bestmove {best_move.uci()}"


def main(stderr_log: bool = False) -> None:
    """Run the UCI loop on stdin/stdout."""
    game = ChessGame()

    def log(msg: str) -> None:
        if stderr_log:
            print(msg, file=sys.stderr, flush=True)

    log(f"{ENGINE_NAME} UCI started (PID {os.getpid()})")

    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        log(f"<< {line}")
        parts = line.split()
        cmd = parts[0]

        if cmd == "uci":
            print(f"id name {ENGINE_NAME}", flush=True)
            print(f"id author {ENGINE_AUTHOR}", flush=True)
            print("uciok", flush=True)
        elif cmd == "isready":
            print("readyok", flush=True)
        elif cmd == "ucinewgame":
            game = ChessGame()
        elif cmd == "position":
            game = _parse_position(parts[1:])
        elif cmd == "go":
            print(_handle_go(game, _parse_go_args(parts[1:]), log), flush=True)
        elif cmd == "stop":
            pass
        elif cmd == "quit":
            log("quit received, exiting")
            return
        else:
            log(f"(ignored) {line}")


if __name__ == "__main__":
    main(stderr_log="--debug" in sys.argv)
