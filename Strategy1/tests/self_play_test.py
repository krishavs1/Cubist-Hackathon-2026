#!/usr/bin/env python3
"""
Self-play smoke test: MVE plays both sides of a single game to completion.

If the engine loops, returns illegal moves, or crashes against itself,
the Darwinian Arena (which pits engine variants against each other in
self-play tournaments) will hang. This test catches that early.

A draw is the expected outcome when an engine plays itself with a weak
eval (no transposition table = many positions repeat).
"""

import os
import sys
import time

import chess

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engines", "mve"),
)
import engine as mve  # noqa: E402


def main() -> int:
    board = chess.Board()
    moves_played = []
    start = time.time()
    time_per_move_ms = 100  # fast: this is just a smoke test

    while not board.is_game_over(claim_draw=True) and board.ply() < 200:
        move = mve.search(board, time_per_move_ms)
        if move is None or move not in board.legal_moves:
            print(f"FAIL: engine returned invalid move {move} at ply {board.ply()}")
            print(f"FEN: {board.fen()}")
            return 1
        board.push(move)
        moves_played.append(move.uci())

    elapsed = time.time() - start
    result = board.result(claim_draw=True)
    print(f"Self-play complete in {elapsed:.1f}s, {board.ply()} plies, result: {result}")
    print(f"Final FEN: {board.fen()}")
    print(f"Outcome: ", end="")
    if board.is_checkmate():
        winner = "Black" if board.turn == chess.WHITE else "White"
        print(f"{winner} wins by checkmate")
    elif board.is_stalemate():
        print("stalemate")
    elif board.is_insufficient_material():
        print("insufficient material")
    elif board.can_claim_draw():
        print("draw by repetition or 50-move rule")
    else:
        print(f"max plies reached ({board.ply()})")

    print(f"\nFirst 20 moves: {' '.join(moves_played[:20])}")
    print("PASS: engine completed a self-play game without errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
