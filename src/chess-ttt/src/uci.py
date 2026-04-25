"""UCI protocol bridge for the chess-ttt engine.

Speaks the subset of UCI that the elo-test arena uses:

    uci                 -> id name / id author / uciok
    isready             -> readyok
    ucinewgame          -> reset game state
    position startpos [moves m1 m2 ...]
    position fen <fen> [moves m1 m2 ...]
    go [movetime <ms>] [depth <d>] [wtime ... btime ...]
    quit

Time management:
The underlying alpha-beta search (`search.search`) is depth-bounded, not
time-bounded. Rather than modify the verified search core, we wrap it with
iterative deepening here in the UCI layer: search depth=1, then depth=2,
... until either the next depth would blow the time budget or we hit the
configured max depth. The last completed depth's best move is returned.

This keeps `search.py` byte-identical to the Tic-Tac-Toe original while
giving the arena a real-time engine.
"""

from __future__ import annotations

import sys
import time
from typing import Optional

import chess

from .game import ChessGame
from .search import search


ENGINE_NAME = "chess-ttt"
ENGINE_AUTHOR = "TTT-bridged alpha-beta"

# Search caps / safety margins.
MAX_DEPTH = 6                 # absolute ceiling regardless of time
DEFAULT_DEPTH_NO_TIME = 3     # used if the GUI doesn't provide any timing
SAFETY_FRACTION = 0.5         # spend at most this fraction of remaining budget
PER_MOVE_FRACTION = 1 / 30.0  # if only wtime/btime given, assume 30 moves left


def _branching_factor_estimate() -> float:
    """Rough effective branching factor after alpha-beta with no move ordering.

    Used by the iterative-deepening time manager to predict whether the
    next depth is worth attempting. ~6 is a conservative estimate for
    chess without move ordering — real numbers measured on this engine
    sit between 5 and 8.
    """
    return 6.0


def _choose_movetime(go_args: dict, game: ChessGame) -> Optional[int]:
    """Translate UCI go-arguments into a movetime budget in milliseconds.

    Returns None if no time control is given (caller should fall back to
    a default depth).
    """
    if "movetime" in go_args:
        return int(go_args["movetime"])

    side_key = "wtime" if game.current_player() == chess.WHITE else "btime"
    if side_key in go_args:
        remaining = int(go_args[side_key])
        # Leave a safety margin and budget per-move share.
        return max(20, int(remaining * PER_MOVE_FRACTION))

    return None


def _iterative_deepening(game: ChessGame, deadline: Optional[float],
                          max_depth: int) -> tuple[Optional[chess.Move], int, int, int, int]:
    """Run iterative deepening up to `deadline` (epoch seconds) or max_depth.

    Returns (best_move, score, depth_reached, total_nodes, total_cutoffs).
    Always returns the result of the last *completed* iteration — partial
    results from an aborted iteration are discarded so the engine never
    returns a half-baked move.
    """
    best_move = None
    best_score = 0
    depth_reached = 0
    total_nodes = 0
    total_cutoffs = 0
    last_iter_time = 0.001  # seconds; used to extrapolate next iteration cost

    for depth in range(1, max_depth + 1):
        # Predict whether the next depth will fit in the budget. Skip if not.
        if deadline is not None:
            now = time.time()
            remaining = deadline - now
            if remaining <= 0:
                break
            predicted = last_iter_time * _branching_factor_estimate()
            if depth > 1 and predicted > remaining:
                break

        t0 = time.time()
        result = search(game, max_depth=depth)
        last_iter_time = max(time.time() - t0, 1e-4)

        # Even at depth 1 we accept the result; deeper iterations overwrite
        # only after they complete.
        if result.best_move is not None:
            best_move = result.best_move
            best_score = result.score
            depth_reached = depth
            total_nodes += result.stats.nodes_searched
            total_cutoffs += result.stats.cutoffs

        # If we found a forced mate we can stop — deeper search won't change it.
        if abs(best_score) > 50_000:
            break

    return best_move, best_score, depth_reached, total_nodes, total_cutoffs


def _parse_position(parts: list[str]) -> ChessGame:
    """Parse a UCI 'position ...' command's arguments into a ChessGame."""
    if not parts:
        return ChessGame()

    if parts[0] == "startpos":
        game = ChessGame()
        moves_idx = 1
    elif parts[0] == "fen":
        # FEN is six space-separated fields.
        fen_parts = parts[1:7]
        game = ChessGame(" ".join(fen_parts))
        moves_idx = 7
    else:
        # Unknown — fall back to startpos.
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
    """Parse 'go ...' arguments into a dict of recognised keys."""
    args = {}
    i = 0
    int_keys = {"movetime", "depth", "wtime", "btime", "winc", "binc",
                "movestogo", "nodes"}
    flag_keys = {"infinite", "ponder"}
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


def _handle_go(game: ChessGame, go_args: dict, log) -> str:
    """Run a search for the current position and return a UCI bestmove string."""
    if game.is_terminal():
        return "bestmove 0000"

    # Determine depth and time budget.
    if "depth" in go_args:
        max_depth = min(int(go_args["depth"]), MAX_DEPTH)
        deadline = None
    else:
        max_depth = MAX_DEPTH
        movetime = _choose_movetime(go_args, game)
        if movetime is None:
            # No timing info → fixed conservative depth.
            max_depth = DEFAULT_DEPTH_NO_TIME
            deadline = None
        else:
            deadline = time.time() + (movetime / 1000.0) * SAFETY_FRACTION

    t0 = time.time()
    best_move, score, depth, nodes, cutoffs = _iterative_deepening(
        game, deadline=deadline, max_depth=max_depth
    )
    elapsed_ms = int((time.time() - t0) * 1000)

    if best_move is None:
        # Defensive: if for some reason we found nothing, play the first legal
        # move rather than crashing or sending an illegal "0000" mid-game.
        legal = game.get_legal_moves()
        if legal:
            best_move = legal[0]
        else:
            return "bestmove 0000"

    # Emit a UCI 'info' line so GUIs / arenas can display search stats.
    print(f"info depth {depth} score cp {score} nodes {nodes} time {elapsed_ms}",
          flush=True)
    log(f"GO -> bestmove {best_move.uci()} depth={depth} score={score} "
        f"nodes={nodes} cutoffs={cutoffs} time={elapsed_ms}ms")
    return f"bestmove {best_move.uci()}"


def main(stderr_log: bool = False) -> None:
    """Run the UCI loop on stdin/stdout.

    If `stderr_log` is True, also write a copy of every command and the
    chosen move to stderr — useful when debugging the arena.
    """
    game = ChessGame()

    def log(msg: str) -> None:
        if stderr_log:
            print(msg, file=sys.stderr, flush=True)

    log(f"chess-ttt UCI started (PID {__import__('os').getpid()})")

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
            response = _handle_go(game, _parse_go_args(parts[1:]), log)
            print(response, flush=True)
        elif cmd == "stop":
            # We don't run searches concurrently; a 'stop' between commands
            # is a no-op. If a search were running we'd cancel it here.
            pass
        elif cmd == "quit":
            log("quit received, exiting")
            return
        else:
            # Unknown commands are ignored per UCI spec.
            log(f"(ignored) {line}")


if __name__ == "__main__":
    # Allow `python -m src.uci --debug` for stderr logging during development.
    debug = "--debug" in sys.argv
    main(stderr_log=debug)
