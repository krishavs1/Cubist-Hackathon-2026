#!/usr/bin/env python3
"""
Perft (PERformance Test) for move generation correctness.

Perft counts the number of leaf nodes at a given depth. Since python-chess
provides legal move generation, this test really validates that:
  (a) python-chess matches the canonical perft node counts (sanity check)
  (b) our position parsing and move-pushing is consistent with the standard

The canonical values below are from the Chess Programming Wiki:
https://www.chessprogramming.org/Perft_Results

Run:  python3 perft_test.py
"""

import sys
import time

import chess


# (FEN, depth, expected_node_count)
PERFT_CASES = [
    # Starting position
    (chess.STARTING_FEN, 1, 20),
    (chess.STARTING_FEN, 2, 400),
    (chess.STARTING_FEN, 3, 8902),
    (chess.STARTING_FEN, 4, 197281),
    # Kiwipete -- tactical middlegame, exposes most edge cases
    ("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 1, 48),
    ("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 2, 2039),
    ("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 3, 97862),
    # Position 3 -- endgame with promotions and en passant
    ("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 1, 14),
    ("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 2, 191),
    ("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 3, 2812),
    ("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 4, 43238),
]


def perft(board: chess.Board, depth: int) -> int:
    """Recursively count leaf nodes at the given depth."""
    if depth == 0:
        return 1
    count = 0
    for move in board.legal_moves:
        board.push(move)
        count += perft(board, depth - 1)
        board.pop()
    return count


def run() -> int:
    failures = 0
    for fen, depth, expected in PERFT_CASES:
        board = chess.Board(fen)
        start = time.time()
        actual = perft(board, depth)
        elapsed = time.time() - start
        status = "OK  " if actual == expected else "FAIL"
        print(
            f"[{status}] depth={depth} expected={expected:>8} "
            f"actual={actual:>8}  ({elapsed:5.2f}s)  fen={fen[:40]}..."
        )
        if actual != expected:
            failures += 1

    print()
    if failures:
        print(f"{failures} perft case(s) FAILED")
        return 1
    print("All perft cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
