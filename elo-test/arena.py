"""
Arena — the central benchmarking tool.

Runs two UCI engines against each other and reports results.

Usage:
    python core/arena.py --engine-a core/baseline/run.sh --engine-b engines/my-engine/run.sh --games 50 --movetime 100
"""

import argparse
import math
import os
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime

import chess
import chess.pgn


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
ARENA_LOG = os.path.join(REPO_ROOT, "ARENA_LOG.md")
PGNS_DIR = os.path.join(REPO_ROOT, "pgns")


class UCIEngine:
    """Manages a UCI engine subprocess."""

    def __init__(self, path, movetime):
        self.path = path
        self.name = os.path.basename(os.path.dirname(os.path.abspath(path)))
        self.movetime = movetime
        self.timeout = movetime / 1000.0 * 2 + 2  # 2x movetime + 2s buffer
        self.proc = None

    def start(self):
        self.proc = subprocess.Popen(
            ["bash", self.path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        # Thread-based reader to avoid select() issues on macOS pipes
        self._queue = queue.Queue()

        def reader():
            try:
                for line in self.proc.stdout:
                    self._queue.put(line)
            except ValueError:
                pass

        t = threading.Thread(target=reader, daemon=True)
        t.start()

    def send(self, command):
        try:
            self.proc.stdin.write(command + "\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError):
            return False
        return True

    def read_until(self, target, timeout):
        start = time.time()
        while time.time() - start < timeout:
            try:
                line = self._queue.get(timeout=0.1).strip()
                if target in line:
                    return True
            except queue.Empty:
                if self.proc.poll() is not None:
                    return False
        return False

    def read_bestmove(self):
        start = time.time()
        while time.time() - start < self.timeout:
            try:
                line = self._queue.get(timeout=0.1).strip()
                if line.startswith("bestmove"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[1]
            except queue.Empty:
                if self.proc.poll() is not None:
                    return None
        return None

    def init_uci(self):
        self.send("uci")
        if not self.read_until("uciok", 5):
            return False
        self.send("isready")
        if not self.read_until("readyok", 5):
            return False
        return True

    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.send("quit")
                self.proc.wait(timeout=2)
            except (subprocess.TimeoutExpired, OSError):
                self.proc.kill()
                self.proc.wait()

    @property
    def alive(self):
        return self.proc is not None and self.proc.poll() is None


def play_game(white_engine, black_engine, movetime, game_num):
    """Play a single game. Returns ('white', 'black', or 'draw') and the chess.pgn.Game."""
    board = chess.Board()
    game = chess.pgn.Game()
    game.headers["White"] = white_engine.name
    game.headers["Black"] = black_engine.name
    game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
    game.headers["Round"] = str(game_num)

    node = game
    moves_uci = []

    while not board.is_game_over(claim_draw=True):
        engine = white_engine if board.turn == chess.WHITE else black_engine

        if not engine.alive:
            # Engine crashed — other side wins
            result = "black" if board.turn == chess.WHITE else "white"
            game.headers["Result"] = "0-1" if result == "black" else "1-0"
            game.headers["Termination"] = "engine crash"
            return result, game

        pos_cmd = "position startpos"
        if moves_uci:
            pos_cmd += " moves " + " ".join(moves_uci)

        if not engine.send(pos_cmd):
            result = "black" if board.turn == chess.WHITE else "white"
            game.headers["Result"] = "0-1" if result == "black" else "1-0"
            game.headers["Termination"] = "engine crash"
            return result, game

        engine.send(f"go movetime {movetime}")
        move_str = engine.read_bestmove()

        if move_str is None:
            # Timeout or crash — forfeit
            result = "black" if board.turn == chess.WHITE else "white"
            game.headers["Result"] = "0-1" if result == "black" else "1-0"
            game.headers["Termination"] = "timeout"
            return result, game

        # Validate move
        try:
            move = chess.Move.from_uci(move_str)
        except ValueError:
            result = "black" if board.turn == chess.WHITE else "white"
            game.headers["Result"] = "0-1" if result == "black" else "1-0"
            game.headers["Termination"] = "illegal move"
            return result, game

        if move not in board.legal_moves:
            result = "black" if board.turn == chess.WHITE else "white"
            game.headers["Result"] = "0-1" if result == "black" else "1-0"
            game.headers["Termination"] = "illegal move"
            return result, game

        board.push(move)
        moves_uci.append(move_str)
        node = node.add_variation(move)

    # Game ended naturally
    outcome = board.outcome(claim_draw=True)
    if outcome.winner is None:
        game.headers["Result"] = "1/2-1/2"
        return "draw", game
    elif outcome.winner == chess.WHITE:
        game.headers["Result"] = "1-0"
        return "white", game
    else:
        game.headers["Result"] = "0-1"
        return "black", game


def compute_elo_delta(wins, losses, draws):
    """Compute Elo delta using standard 400-based logistic formula."""
    total = wins + losses + draws
    if total == 0:
        return 0
    score = (wins + 0.5 * draws) / total
    # Clamp to avoid log(0)
    score = max(0.001, min(0.999, score))
    elo_delta = -400 * math.log10(1 / score - 1)
    return round(elo_delta)


def main():
    parser = argparse.ArgumentParser(description="Arena — chess engine matchmaker")
    parser.add_argument("--engine-a", required=True, help="Path to engine A run.sh")
    parser.add_argument("--engine-b", required=True, help="Path to engine B run.sh")
    parser.add_argument("--games", type=int, default=50, help="Number of games (default 50)")
    parser.add_argument("--movetime", type=int, default=100, help="Movetime in ms (default 100)")
    args = parser.parse_args()

    os.makedirs(PGNS_DIR, exist_ok=True)

    name_a = os.path.basename(os.path.dirname(os.path.abspath(args.engine_a)))
    name_b = os.path.basename(os.path.dirname(os.path.abspath(args.engine_b)))

    print(f"\n{'='*60}")
    print(f"  Arena: {name_a} vs {name_b}")
    print(f"  Games: {args.games} | Movetime: {args.movetime}ms")
    print(f"{'='*60}\n")

    wins_a = 0
    losses_a = 0
    draws = 0

    for game_num in range(1, args.games + 1):
        # Alternate colors: engine-a plays white in odd games, black in even
        if game_num % 2 == 1:
            white_path, black_path = args.engine_a, args.engine_b
            a_is_white = True
        else:
            white_path, black_path = args.engine_b, args.engine_a
            a_is_white = False

        white_engine = UCIEngine(white_path, args.movetime)
        black_engine = UCIEngine(black_path, args.movetime)

        white_engine.start()
        black_engine.start()

        w_ok = white_engine.init_uci()
        b_ok = black_engine.init_uci()

        if not w_ok or not b_ok:
            # Engine failed to init — count as loss for the failing engine
            if not w_ok and a_is_white:
                losses_a += 1
            elif not w_ok and not a_is_white:
                wins_a += 1
            elif not b_ok and a_is_white:
                wins_a += 1
            else:
                losses_a += 1

            white_engine.stop()
            black_engine.stop()
            status = f"Game {game_num}/{args.games}: init failure"
            print(f"  {status}")
            continue

        result, pgn_game = play_game(white_engine, black_engine, args.movetime, game_num)

        white_engine.stop()
        black_engine.stop()

        # Track from engine-a's perspective
        if result == "draw":
            draws += 1
            symbol = "="
        elif (result == "white" and a_is_white) or (result == "black" and not a_is_white):
            wins_a += 1
            symbol = "+"
        else:
            losses_a += 1
            symbol = "-"

        # Save PGN
        pgn_filename = f"{name_a}_vs_{name_b}_game{game_num}.pgn"
        pgn_path = os.path.join(PGNS_DIR, pgn_filename)
        with open(pgn_path, "w") as f:
            print(pgn_game, file=f)

        print(f"  Game {game_num}/{args.games}: [{symbol}] {pgn_game.headers['Result']}", end="")
        if "Termination" in pgn_game.headers:
            print(f" ({pgn_game.headers['Termination']})", end="")
        print()

    # Summary
    elo_delta = compute_elo_delta(wins_a, losses_a, draws)

    print(f"\n{'='*60}")
    print(f"  Results ({name_a} perspective):")
    print(f"  {wins_a}W-{losses_a}L-{draws}D | Elo delta: {elo_delta:+d}")
    print(f"{'='*60}\n")

    # Append to ARENA_LOG.md
    timestamp = datetime.now().strftime("%H:%M")
    log_entry = (
        f"[{timestamp}] {name_a} vs {name_b} | "
        f"{args.games} games | "
        f"{wins_a}W-{losses_a}L-{draws}D | "
        f"Elo delta: {elo_delta:+d} | "
        f"outcome: PENDING REVIEW\n"
    )

    with open(ARENA_LOG, "a") as f:
        f.write(log_entry)

    print(f"  Results appended to ARENA_LOG.md")
    print(f"  PGNs saved to pgns/\n")


if __name__ == "__main__":
    main()
