#!/usr/bin/env python3
"""
Cubist Hackathon 2026 - Darwinian AI Engine
============================================

Strategy: Darwinian AI.

Search substrate is fixed (NegaMax + Alpha-Beta + Iterative Deepening +
Quiescence). The *evaluator* is swappable -- multiple "personality"
heuristics live in heuristics.py and compete in the Arena tournament.
The winning personality becomes the Champion.

Run as a UCI engine:
    python3 engine.py                            # default 'balanced' heuristic
    python3 engine.py --heuristic aggressive_attacker

Use programmatically:
    from engine import search
    from heuristics import get
    move = search(board, time_limit_ms=1000, eval_fn=get('fortress'))
"""

import argparse
import random
import sys
import time
from typing import Callable, Iterable, List, Optional

import chess

from heuristics import REGISTRY, balanced, get


# ============================================================
# SEARCH CONSTANTS
# ============================================================

INF = 1_000_000
MAX_DEPTH = 64
QUIESCENCE_DEPTH = 4
TIME_CHECK_INTERVAL = 2048  # power of 2 for fast bitmask check

PIECE_VALUES = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:   20000,
}


# ============================================================
# MOVE ORDERING
# ============================================================

def score_move(board: chess.Board, move: chess.Move) -> int:
    """MVV-LVA + promotion bonus. Used to order moves for better cutoffs."""
    score = 0
    if board.is_capture(move):
        victim = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        if victim is not None and attacker is not None:
            score = PIECE_VALUES[victim.piece_type] * 10 - PIECE_VALUES[attacker.piece_type]
        else:
            score = PIECE_VALUES[chess.PAWN] * 10 - PIECE_VALUES[chess.PAWN]
    if move.promotion:
        score += PIECE_VALUES.get(move.promotion, 0)
    return score


def order_moves(board: chess.Board, moves: Iterable[chess.Move]) -> List[chess.Move]:
    return sorted(moves, key=lambda m: score_move(board, m), reverse=True)


# ============================================================
# SEARCH STATE
# ============================================================

class SearchState:
    """Per-search state including the swappable evaluator."""
    __slots__ = ("start_time", "time_limit_ms", "nodes", "stopped", "eval_fn")

    def __init__(self, time_limit_ms: int, eval_fn: Callable[[chess.Board], int]):
        self.start_time = time.time()
        self.time_limit_ms = time_limit_ms
        self.nodes = 0
        self.stopped = False
        self.eval_fn = eval_fn

    def check_time(self) -> None:
        if self.nodes & (TIME_CHECK_INTERVAL - 1) == 0:
            elapsed_ms = (time.time() - self.start_time) * 1000.0
            if elapsed_ms >= self.time_limit_ms:
                self.stopped = True


# ============================================================
# SEARCH
# ============================================================

def quiescence(board: chess.Board, alpha: int, beta: int, depth: int, state: SearchState) -> int:
    """Captures-only extension to avoid the horizon effect."""
    state.nodes += 1
    state.check_time()
    if state.stopped:
        return 0

    if board.is_checkmate():
        return -INF + board.ply()
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    raw = state.eval_fn(board)
    stand_pat = raw if board.turn == chess.WHITE else -raw

    if stand_pat >= beta:
        return beta
    if stand_pat > alpha:
        alpha = stand_pat

    if depth == 0:
        return alpha

    captures = order_moves(board, (m for m in board.legal_moves if board.is_capture(m)))
    for move in captures:
        board.push(move)
        score = -quiescence(board, -beta, -alpha, depth - 1, state)
        board.pop()
        if state.stopped:
            return alpha
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score

    return alpha


def negamax(board: chess.Board, depth: int, alpha: int, beta: int, state: SearchState) -> int:
    """NegaMax with fail-hard alpha-beta pruning."""
    state.nodes += 1
    state.check_time()
    if state.stopped:
        return 0

    if board.is_checkmate():
        return -INF + board.ply()
    if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
        return 0

    if depth == 0:
        return quiescence(board, alpha, beta, QUIESCENCE_DEPTH, state)

    for move in order_moves(board, board.legal_moves):
        board.push(move)
        score = -negamax(board, depth - 1, -beta, -alpha, state)
        board.pop()
        if state.stopped:
            return alpha
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score

    return alpha


def search(
    board: chess.Board,
    time_limit_ms: int,
    eval_fn: Optional[Callable[[chess.Board], int]] = None,
    verbose: bool = True,
) -> Optional[chess.Move]:
    """
    Iterative Deepening search with a swappable evaluator.

    Args:
        board: position to search from
        time_limit_ms: time budget in milliseconds
        eval_fn: evaluator from heuristics.py; defaults to 'balanced'
        verbose: print UCI 'info' lines to stdout (False for tournament mode)
    """
    if eval_fn is None:
        eval_fn = balanced

    legal = list(board.legal_moves)
    if not legal:
        return None

    best_move = random.choice(legal)
    state = SearchState(time_limit_ms, eval_fn)

    for depth in range(1, MAX_DEPTH + 1):
        if state.stopped:
            break

        alpha = -INF
        depth_best: Optional[chess.Move] = None

        for move in order_moves(board, board.legal_moves):
            if state.stopped:
                break
            board.push(move)
            score = -negamax(board, depth - 1, -INF, -alpha, state)
            board.pop()
            if score > alpha:
                alpha = score
                depth_best = move

        if not state.stopped and depth_best is not None:
            best_move = depth_best
            if verbose:
                elapsed_ms = int((time.time() - state.start_time) * 1000)
                print(
                    f"info depth {depth} score cp {alpha} nodes {state.nodes} "
                    f"time {elapsed_ms} pv {best_move.uci()}",
                    flush=True,
                )

        if alpha >= INF - MAX_DEPTH:
            break

    return best_move


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
        return max(10, params["movetime"] - 50)

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
    """Main UCI loop. Each personality runs as its own UCI engine."""
    board = chess.Board()

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

        elif cmd == "position":
            board = parse_position(tokens[1:])

        elif cmd == "go":
            time_limit_ms = parse_time_limit(tokens[1:], board.turn)
            try:
                move = search(board, time_limit_ms, eval_fn=eval_fn, verbose=True)
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
        default="balanced",
        choices=list(REGISTRY.keys()),
        help="Which evaluation personality to use",
    )
    args = parser.parse_args()

    eval_fn = get(args.heuristic)
    engine_name = f"CubistMVE-{args.heuristic}"
    uci_loop(eval_fn, engine_name)


if __name__ == "__main__":
    main()
