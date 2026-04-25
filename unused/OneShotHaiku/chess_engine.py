#!/usr/bin/env python3
"""
OneShot Chess Engine - UCI Protocol Implementation
A well-performing chess engine MVP using python-chess
"""

import chess
import sys
from search import find_best_move, find_best_move_iterative, clear_transposition_table
from evaluation import evaluate

# Engine metadata
ENGINE_NAME = "OneShot"
ENGINE_VERSION = "1.0"
ENGINE_AUTHOR = "Chess Engine"

# Configuration
DEFAULT_DEPTH = 4
MAX_DEPTH = 20


class ChessEngine:
    def __init__(self):
        self.board = chess.Board()
        self.search_depth = DEFAULT_DEPTH
        self.time_limit_ms = None
        self.is_ready = True

    def handle_uci(self):
        """Handle UCI initialization."""
        print(f"id name {ENGINE_NAME} {ENGINE_VERSION}")
        print(f"id author {ENGINE_AUTHOR}")
        print("option name Depth type spin default 4 min 1 max 20")
        print("uciok")

    def handle_is_ready(self):
        """Handle readiness check."""
        print("readyok")

    def handle_set_option(self, option_name, option_value):
        """Handle engine options."""
        if option_name.lower() == "depth":
            try:
                depth = int(option_value)
                self.search_depth = min(max(depth, 1), MAX_DEPTH)
            except ValueError:
                pass

    def handle_new_game(self):
        """Initialize new game."""
        self.board = chess.Board()
        clear_transposition_table()

    def handle_position(self, tokens):
        """
        Handle position command.
        Format: position [fen <fenstring>] | startpos [moves <move1> <move2> ...]
        """
        if "startpos" in tokens:
            self.board = chess.Board()
            moves_idx = tokens.index("startpos") + 1
        elif "fen" in tokens:
            fen_idx = tokens.index("fen")
            fen_end = tokens.index("moves") if "moves" in tokens else len(tokens)
            fen = " ".join(tokens[fen_idx + 1:fen_end])
            self.board = chess.Board(fen)
            moves_idx = fen_end + 1 if "moves" in tokens else len(tokens)
        else:
            return

        # Apply moves
        if moves_idx < len(tokens) and tokens[moves_idx - 1] == "moves":
            for move_uci in tokens[moves_idx:]:
                try:
                    move = self.board.push_san(move_uci)
                except:
                    try:
                        move = self.board.push_uci(move_uci)
                    except:
                        pass

    def handle_go(self, tokens):
        """
        Handle go command.
        Format: go [depth <depth>] [wtime <ms>] [btime <ms>] [movestogo <num>] ...
        """
        search_depth = self.search_depth
        time_limit_ms = None

        # Parse go parameters
        i = 0
        while i < len(tokens):
            if tokens[i] == "depth" and i + 1 < len(tokens):
                search_depth = int(tokens[i + 1])
                i += 2
            elif tokens[i] == "wtime" and i + 1 < len(tokens):
                wtime = int(tokens[i + 1])
                if self.board.turn == chess.WHITE:
                    time_limit_ms = max(wtime // 25, 100)
                i += 2
            elif tokens[i] == "btime" and i + 1 < len(tokens):
                btime = int(tokens[i + 1])
                if self.board.turn == chess.BLACK:
                    time_limit_ms = max(btime // 25, 100)
                i += 2
            elif tokens[i] == "infinite":
                time_limit_ms = None
                i += 1
            else:
                i += 1

        # Find best move
        if time_limit_ms:
            move = find_best_move_iterative(self.board, time_limit_ms)
        else:
            move = find_best_move(self.board, search_depth)

        if move:
            print(f"bestmove {move.uci()}")
        else:
            print("bestmove 0000")

    def handle_display(self):
        """Display the current board."""
        print(self.board)

    def handle_evaluate(self):
        """Display evaluation of current position."""
        score = evaluate(self.board)
        print(f"Evaluation: {score}")

    def run(self):
        """Main UCI protocol loop."""
        while True:
            try:
                command = input().strip()
            except EOFError:
                break

            if not command:
                continue

            tokens = command.split()
            cmd = tokens[0].lower()

            if cmd == "uci":
                self.handle_uci()
            elif cmd == "isready":
                self.handle_is_ready()
            elif cmd == "setoption":
                # setoption name <name> value <value>
                if "name" in tokens and "value" in tokens:
                    name_idx = tokens.index("name")
                    value_idx = tokens.index("value")
                    option_name = " ".join(tokens[name_idx + 1:value_idx])
                    option_value = " ".join(tokens[value_idx + 1:])
                    self.handle_set_option(option_name, option_value)
            elif cmd == "ucinewgame":
                self.handle_new_game()
            elif cmd == "position":
                self.handle_position(tokens[1:])
            elif cmd == "go":
                self.handle_go(tokens[1:])
            elif cmd == "quit":
                break
            elif cmd == "d":
                self.handle_display()
            elif cmd == "eval":
                self.handle_evaluate()
            elif cmd == "help":
                print("UCI commands: uci, isready, setoption, ucinewgame, position, go, quit")
                print("Debug commands: d (display), eval (evaluate), help")


def main():
    engine = ChessEngine()
    engine.run()


if __name__ == "__main__":
    main()
