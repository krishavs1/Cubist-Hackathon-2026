#!/usr/bin/env python3
"""
Cubist Hackathon 2026 - Darwinian AI Engine
============================================

Strategy: Darwinian AI.

Architecture is split into two pieces:

  * SEARCH (search.py) -- a fixed, modern search core: PVS + transposition
    table + null-move pruning + late move reductions + killers + history +
    aspiration windows + quiescence. This part is held constant so that
    different evaluators are compared on equal footing.

  * EVALUATION (heuristics.py) -- the mutation surface. Multiple
    "personality" heuristics (pesto, balanced, aggressive_attacker,
    positional_grinder, material_hawk, fortress, pawn_storm) compete in
    the Arena tournament; the winning personality is the Champion.

Run as a UCI engine:
    python3 engine.py                            # default 'pesto' personality
    python3 engine.py --heuristic aggressive_attacker

Use programmatically:
    from search import Searcher
    from heuristics import get
    s = Searcher(get("fortress"))
    move = s.go_ms(board, time_limit_ms=1000)
"""

import argparse
import random
import sys
from typing import Callable, List

import chess

from heuristics import REGISTRY, get
from search import Searcher, search as run_search

# Backwards-compat alias so arena/tournament.py can call `engine.search(...)`.
search = run_search


# ============================================================
# UCI PROTOCOL
# ============================================================

def parse_position(tokens: List[str]) -> chess.Board:
    """Parse 'startpos [moves ...]' or 'fen <fen> [moves ...]'."""
    board = chess.Board()
    if not tokens:
        return board

    idx = 0
    if tokens[idx] == "startpos":
        idx += 1
    elif tokens[idx] == "fen":
        idx += 1
        fen_parts = []
        while idx < len(tokens) and tokens[idx] != "moves":
            fen_parts.append(tokens[idx])
            idx += 1
        try:
            board = chess.Board(" ".join(fen_parts))
        except ValueError:
            return chess.Board()

    if idx < len(tokens) and tokens[idx] == "moves":
        idx += 1
        for uci_str in tokens[idx:]:
            try:
                move = chess.Move.from_uci(uci_str)
            except ValueError:
                break
            if move not in board.legal_moves:
                break
            board.push(move)

    return board


def parse_time_limit(tokens: List[str], turn: chess.Color) -> int:
    """Extract a safe time budget (ms) from 'go' command parameters."""
    params: dict = {}
    i = 0
    while i < len(tokens) - 1:
        try:
            params[tokens[i]] = int(tokens[i + 1])
            i += 2
        except ValueError:
            i += 1

    if "movetime" in params:
        # search.py applies its own ~30ms safety margin; pass through raw
        return max(10, params["movetime"])

    if turn == chess.WHITE:
        time_left = params.get("wtime")
        increment = params.get("winc", 0)
    else:
        time_left = params.get("btime")
        increment = params.get("binc", 0)

    if time_left is not None:
        allocated = time_left // 30 + int(increment * 0.8)
        return max(50, min(allocated, max(time_left - 100, 50)))

    return 2000


def uci_loop(eval_fn: Callable[[chess.Board], int], engine_name: str) -> None:
    """Main UCI loop. The chosen personality drives the shared search core."""
    board = chess.Board()
    # One Searcher per session: TT / killers / history persist between moves.
    searcher = Searcher(eval_fn)

    while True:
        try:
            line = sys.stdin.readline()
        except KeyboardInterrupt:
            break
        if not line:
            break

        line = line.strip()
        if not line:
            continue

        tokens = line.split()
        cmd = tokens[0]

        if cmd == "uci":
            print(f"id name {engine_name}")
            print("id author CubistTeam")
            print("uciok")
            sys.stdout.flush()

        elif cmd == "isready":
            print("readyok")
            sys.stdout.flush()

        elif cmd == "ucinewgame":
            board = chess.Board()
            searcher.reset()

        elif cmd == "position":
            board = parse_position(tokens[1:])

        elif cmd == "go":
            time_limit_ms = parse_time_limit(tokens[1:], board.turn)
            try:
                move = searcher.go_ms(board, time_limit_ms, verbose=True)
            except Exception as e:
                print(f"info string SEARCH ERROR: {e}", flush=True)
                legal = list(board.legal_moves)
                move = random.choice(legal) if legal else None

            print(f"bestmove {move.uci() if move else '0000'}")
            sys.stdout.flush()

        elif cmd == "quit":
            break

        elif cmd == "stop":
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Cubist Darwinian AI Engine")
    parser.add_argument(
        "--heuristic", "-H",
        default="pesto",
        choices=list(REGISTRY.keys()),
        help="Which evaluation personality to use",
    )
    args = parser.parse_args()

    eval_fn = get(args.heuristic)
    engine_name = f"CubistDarwin-{args.heuristic}"
    uci_loop(eval_fn, engine_name)


if __name__ == "__main__":
    main()
