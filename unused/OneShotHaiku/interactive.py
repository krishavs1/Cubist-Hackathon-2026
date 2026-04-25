#!/usr/bin/env python3
"""
Interactive mode for OneShot Chess Engine
Allows playing against the engine or analyzing positions
"""

import chess
import chess.pgn
from search import find_best_move, clear_transposition_table
from evaluation import evaluate


def print_board(board):
    """Print the board in a nice format."""
    print("\n" + str(board))
    print(f"\nFEN: {board.fen()}")


def engine_vs_human():
    """Play as human against the engine."""
    board = chess.Board()
    engine_color = chess.BLACK
    depth = 4

    print("=" * 60)
    print("OneShot Chess Engine - Interactive Play")
    print("=" * 60)
    print(f"You play as {'White' if engine_color == chess.BLACK else 'Black'}")
    print(f"Engine plays as {'Black' if engine_color == chess.BLACK else 'White'}")
    print(f"Engine depth: {depth} plies")
    print("\nType moves in algebraic notation (e.g., e2e4, Nf3)")
    print("Commands: 'd' (display), 'eval' (evaluate), 'undo', 'quit'\n")

    print_board(board)

    move_count = 0
    while not board.is_game_over():
        move_count += 1

        if board.turn == engine_color:
            # Engine's turn
            print(f"\nEngine thinking (depth {depth})...")
            clear_transposition_table()
            move = find_best_move(board, depth)

            if move:
                board.push(move)
                print(f"Engine plays: {board.peek()} (score: {evaluate(board):+.0f})")
                print_board(board)
            else:
                print("No legal moves - game over!")
                break
        else:
            # Human's turn
            print(f"Move {move_count} - Your turn:")
            while True:
                user_input = input("> ").strip().lower()

                if user_input == "quit":
                    return
                elif user_input == "d":
                    print_board(board)
                    continue
                elif user_input == "eval":
                    print(f"Position evaluation: {evaluate(board):+.0f}")
                    continue
                elif user_input == "undo":
                    if board.move_stack:
                        board.pop()
                        print("Move undone.")
                        print_board(board)
                    continue

                # Try to parse the move
                try:
                    move = board.push_san(user_input)
                    print_board(board)
                    break
                except ValueError:
                    try:
                        move = board.push_uci(user_input)
                        print_board(board)
                        break
                    except:
                        print("Invalid move. Try again (e.g., e2e4 or e4)")

    # Game over
    print("\n" + "=" * 60)
    if board.is_checkmate():
        print(f"Checkmate! {'White' if not board.turn else 'Black'} wins!")
    elif board.is_stalemate():
        print("Stalemate - Draw!")
    elif board.is_insufficient_material():
        print("Insufficient material - Draw!")
    elif board.is_fivefold_repetition():
        print("Fivefold repetition - Draw!")
    else:
        print("Game over!")

    print(f"Final evaluation: {evaluate(board):+.0f}")
    print("=" * 60)


def analyze_position(fen=None):
    """Analyze a position."""
    if fen:
        board = chess.Board(fen)
    else:
        board = chess.Board()

    print("\n" + "=" * 60)
    print("OneShot Chess Engine - Position Analyzer")
    print("=" * 60)
    print_board(board)

    print("\nAnalyzing...")
    print("\nMove rankings by depth:\n")
    print("Depth | Best Move | Score")
    print("-" * 40)

    for depth in range(2, 6):
        clear_transposition_table()
        move = find_best_move(board, depth)
        score = evaluate(board)

        test_board = board.copy()
        if move:
            test_board.push(move)
            new_score = evaluate(test_board)
        else:
            new_score = score

        print(f"{depth:5d} | {str(move):9s} | {new_score:+.0f}")


def main():
    """Main interactive menu."""
    print("\n" + "=" * 60)
    print("OneShot Chess Engine - Interactive Mode")
    print("=" * 60)

    while True:
        print("\nOptions:")
        print("1. Play against the engine")
        print("2. Analyze a position")
        print("3. Quit")

        choice = input("\nSelect (1-3): ").strip()

        if choice == "1":
            try:
                engine_vs_human()
            except KeyboardInterrupt:
                print("\n\nGame interrupted.")
        elif choice == "2":
            fen_input = input("Enter FEN (or press Enter for starting position): ").strip()
            fen = fen_input if fen_input else None
            try:
                analyze_position(fen)
            except Exception as e:
                print(f"Error: {e}")
        elif choice == "3":
            print("Goodbye!")
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
