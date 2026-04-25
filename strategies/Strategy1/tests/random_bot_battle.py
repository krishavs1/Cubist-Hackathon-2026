#!/usr/bin/env python3
"""
Arena Phase 2 sanity check: MVE vs RandomBot.

Per head.md Section 8, every engine must clear >50% win rate against a
baseline before it can enter the Crucible. RandomBot is even weaker than
the material counter -- if the MVE can't beat random consistently, the
search/eval pipeline is broken.

Plays N games (alternating colors) and reports W/D/L + score. Uses the
engine programmatically (no subprocess) since we own both sides.
"""

import os
import random
import sys
import time
from typing import Tuple

import chess

# Make the engine importable.
sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engines", "mve"),
)
import engine as mve  # noqa: E402


def random_move(board: chess.Board) -> chess.Move:
    return random.choice(list(board.legal_moves))


def mve_move(board: chess.Board, time_ms: int) -> chess.Move:
    move = mve.search(board, time_ms)
    return move if move is not None else random_move(board)


def play_game(mve_is_white: bool, time_ms: int, max_plies: int = 200) -> str:
    """Returns 'W', 'D', or 'L' from MVE's perspective."""
    board = chess.Board()
    while not board.is_game_over(claim_draw=True) and board.ply() < max_plies:
        mve_to_move = (board.turn == chess.WHITE) == mve_is_white
        if mve_to_move:
            move = mve_move(board, time_ms)
        else:
            move = random_move(board)
        board.push(move)

    if board.is_checkmate():
        # The side that JUST moved delivered mate.
        winner_was_white = not board.turn
        if winner_was_white == mve_is_white:
            return "W"
        return "L"
    return "D"


def run(num_games: int = 10, time_ms: int = 300) -> int:
    print(f"MVE vs RandomBot: {num_games} games, {time_ms}ms/move")
    print("-" * 60)
    wins = draws = losses = 0
    start = time.time()

    for i in range(num_games):
        mve_is_white = (i % 2 == 0)
        result = play_game(mve_is_white, time_ms)
        color = "W" if mve_is_white else "B"
        if result == "W":
            wins += 1
        elif result == "D":
            draws += 1
        else:
            losses += 1
        print(f"  game {i+1:>2} (MVE as {color}): {result}  "
              f"[running: {wins}W {draws}D {losses}L]")

    elapsed = time.time() - start
    score = wins + 0.5 * draws
    win_rate = score / num_games * 100

    print("-" * 60)
    print(f"Final: {wins}W {draws}D {losses}L  "
          f"score {score}/{num_games} ({win_rate:.1f}%)  "
          f"time {elapsed:.1f}s")

    # Pass condition from head.md Section 8.
    if win_rate >= 90:
        print("PASS: dominant vs random (expected for any working engine)")
        return 0
    if win_rate >= 50:
        print("WARN: only marginally beating random -- search or eval may be weak")
        return 0
    print("FAIL: losing to random -- engine is broken")
    return 1


if __name__ == "__main__":
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    time_ms = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    sys.exit(run(games, time_ms))
