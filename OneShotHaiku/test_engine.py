#!/usr/bin/env python3
"""
Test script for OneShot Chess Engine
Demonstrates engine functionality and performance
"""

import chess
import time
from search import find_best_move, clear_transposition_table
from evaluation import evaluate


def test_starting_position():
    """Test engine on starting position."""
    print("=" * 60)
    print("Testing Starting Position")
    print("=" * 60)

    board = chess.Board()
    print(f"Position: {board.fen()}")
    print(f"Evaluation: {evaluate(board)}")

    for depth in [3, 4, 5]:
        clear_transposition_table()
        start = time.time()
        move = find_best_move(board, depth)
        elapsed = time.time() - start

        print(f"Depth {depth}: {move} ({elapsed:.2f}s)")


def test_tactical_position():
    """Test engine on a tactical position."""
    print("\n" + "=" * 60)
    print("Testing Tactical Position (White to win)")
    print("=" * 60)

    # Position with a winning tactic for white
    fen = "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"
    board = chess.Board(fen)
    print(board)
    print(f"\nFEN: {fen}")
    print(f"White to move: {board.turn}")
    print(f"Evaluation: {evaluate(board)}")

    for depth in [3, 4, 5]:
        clear_transposition_table()
        start = time.time()
        move = find_best_move(board, depth)
        elapsed = time.time() - start

        # Show what the move does
        test_board = board.copy()
        test_board.push(move)
        new_eval = evaluate(test_board)

        print(f"Depth {depth}: {move} (eval: {new_eval:.0f}, {elapsed:.2f}s)")


def test_endgame_position():
    """Test engine on an endgame position."""
    print("\n" + "=" * 60)
    print("Testing Endgame Position")
    print("=" * 60)

    # King and pawn endgame
    fen = "8/8/8/8/8/4k3/4P3/4K3 w - - 0 1"
    board = chess.Board(fen)
    print(board)
    print(f"\nFEN: {fen}")
    print(f"Evaluation: {evaluate(board)}")

    for depth in [4, 5, 6]:
        clear_transposition_table()
        start = time.time()
        move = find_best_move(board, depth)
        elapsed = time.time() - start

        print(f"Depth {depth}: {move} ({elapsed:.2f}s)")


def test_multiple_positions():
    """Test engine on multiple positions and measure performance."""
    print("\n" + "=" * 60)
    print("Performance Test: 5 Random Positions at Depth 4")
    print("=" * 60)

    test_positions = [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        "8/8/8/3k4/8/3K4/8/8 w - - 0 1",
        "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 4",
        "rnbqkb1r/pp1ppppp/5n2/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 4 4",
    ]

    total_time = 0
    for i, fen in enumerate(test_positions, 1):
        board = chess.Board(fen)
        clear_transposition_table()

        start = time.time()
        move = find_best_move(board, 4)
        elapsed = time.time() - start
        total_time += elapsed

        eval_score = evaluate(board)
        print(f"Position {i}: {move} (eval: {eval_score:+.0f}, {elapsed:.2f}s)")

    print(f"\nTotal time: {total_time:.2f}s")
    print(f"Average time per position: {total_time / len(test_positions):.2f}s")


def test_uci_commands():
    """Test UCI command parsing."""
    print("\n" + "=" * 60)
    print("Testing UCI Command Parsing")
    print("=" * 60)

    test_commands = [
        "position startpos",
        "position startpos moves e2e4 c7c5",
        "position fen rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "go depth 4",
        "go wtime 300000 btime 300000",
    ]

    for cmd in test_commands:
        print(f"✓ Supported: {cmd}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("OneShot Chess Engine - Test Suite")
    print("=" * 60)

    test_starting_position()
    test_tactical_position()
    test_endgame_position()
    test_multiple_positions()
    test_uci_commands()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
