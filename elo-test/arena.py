"""
Arena — the central benchmarking tool.
Harden with strict resource limits and crash handling.
"""

import argparse
import math
import os
import queue
import subprocess
import sys
import threading
import time
import resource
from datetime import datetime

import chess
import chess.pgn

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
ARENA_LOG = os.path.join(REPO_ROOT, "ARENA_LOG.md")
PGNS_DIR = os.path.join(REPO_ROOT, "pgns")
MOVE_TIMEOUT = 2.0  # HARD LIMIT
MEMORY_LIMIT_MB = 512

# Standard opening FENs for balanced testing
OPENING_BOOK = [
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", # Startpos
    "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2", # Sicilian
    "rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2", # French
    "rnbqkbnr/pppppp1p/8/6p1/4P3/8/PPPP1PPP/RNBQKBNR w KQkq g6 0 2", # Modern
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2", # Open Game
    "rnbqkbnr/pp1ppppp/8/2p5/2P5/8/PP1PPPPP/RNBQKBNR b KQkq c3 0 2", # English
    "rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq d6 0 2", # Queen's Gambit
    "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2", # Caro-Kann
]

def set_resource_limits():
    """Limit subprocess memory for safety. Wrapped in try-except for compatibility."""
    try:
        mem_bytes = MEMORY_LIMIT_MB * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    except Exception as e:
        pass

def log_failure(engine_name, fen, error_type, details):
    """Log crashes and illegal moves to the methodology's DISCOVERY.md."""
    src_path = os.path.join(REPO_ROOT, "src")
    if not os.path.exists(src_path): return
    
    for folder in os.listdir(src_path):
        if folder == engine_name:
            discovery_path = os.path.join(src_path, folder, "DISCOVERY.md")
            timestamp = datetime.now().strftime("%H:%M")
            entry = f"| {timestamp} | {error_type} | FEN: {fen} | {details} | Fixed (Ref) |\n"
            
            if os.path.exists(discovery_path):
                with open(discovery_path, "a") as f:
                    f.write(entry)
            break

class UCIEngine:
    """Manages a UCI engine subprocess with strict limits."""

    def __init__(self, path, movetime):
        self.path = path
        self.name = os.path.basename(os.path.dirname(os.path.abspath(path)))
        self.movetime = min(movetime, int(MOVE_TIMEOUT * 1000))
        self.proc = None

    def start(self):
        self.proc = subprocess.Popen(
            ["bash", self.path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            preexec_fn=set_resource_limits
        )
        self._queue = queue.Queue()

        def reader():
            try:
                for line in self.proc.stdout:
                    self._queue.put(line)
            except: pass

        t = threading.Thread(target=reader, daemon=True)
        t.start()

    def send(self, command):
        try:
            self.proc.stdin.write(command + "\n")
            self.proc.stdin.flush()
        except: return False
        return True

    def read_bestmove(self):
        wait_time = MOVE_TIMEOUT
        start = time.time()
        while time.time() - start < wait_time:
            try:
                line = self._queue.get(timeout=0.1).strip()
                if line.startswith("bestmove"):
                    parts = line.split()
                    return parts[1] if len(parts) >= 2 else None
            except queue.Empty:
                if self.proc.poll() is not None: return None
        return None

    def init_uci(self):
        if not self.send("uci"):
            print(f"  [DEBUG] {self.name} failed to send 'uci'")
            return False
        
        start = time.time()
        found_ok = False
        while time.time() - start < 10.0:
            try:
                line = self._queue.get(timeout=0.1).strip()
                if "uciok" in line:
                    found_ok = True
                    break
            except queue.Empty: pass
        
        if not found_ok:
            print(f"  [DEBUG] {self.name} timed out waiting for 'uciok'")
            return False
        self.send("isready")
        
        start = time.time()
        found_ready = False
        while time.time() - start < 10.0:
            try:
                line = self._queue.get(timeout=0.1).strip()
                if "readyok" in line:
                    found_ready = True
                    break
            except queue.Empty: pass
            
        if not found_ready:
            print(f"  [DEBUG] {self.name} timed out waiting for 'readyok'")
            return False
            
        return True

    def stop(self):
        if self.proc:
            try:
                if self.proc.poll() is None:
                    self.send("quit")
                    self.proc.wait(timeout=1.0)
            except:
                pass
            finally:
                if self.proc and self.proc.poll() is None:
                    self.proc.kill()
                    self.proc.wait()
                try:
                    if self.proc and self.proc.stdin: self.proc.stdin.close()
                except: pass
                try:
                    if self.proc and self.proc.stdout: self.proc.stdout.close()
                except: pass
                try:
                    if self.proc and self.proc.stderr: self.proc.stderr.close()
                except: pass

    @property
    def alive(self):
        return self.proc is not None and self.proc.poll() is None

def play_game(white_engine, black_engine, movetime, fen):
    board = chess.Board(fen)
    game = chess.pgn.Game()
    game.headers["White"] = white_engine.name
    game.headers["Black"] = black_engine.name
    game.headers["FEN"] = fen
    game.setup(board)
    
    node = game
    while not board.is_game_over(claim_draw=True):
        engine = white_engine if board.turn == chess.WHITE else black_engine
        if not engine.alive:
            log_failure(engine.name, board.fen(), "Logic/UCI", "Engine process died unexpectedly.")
            return ("black" if board.turn == chess.WHITE else "white"), game

        if not engine.send(f"position fen {board.fen()}"):
            return ("black" if board.turn == chess.WHITE else "white"), game

        engine.send(f"go movetime {movetime}")
        move_str = engine.read_bestmove()

        if move_str is None:
            log_failure(engine.name, board.fen(), "Logic/UCI", f"Move timeout (>{MOVE_TIMEOUT}s)")
            game.headers["Termination"] = "timeout"
            return ("black" if board.turn == chess.WHITE else "white"), game

        try:
            move = board.parse_uci(move_str)
            if move not in board.legal_moves:
                log_failure(engine.name, board.fen(), "Logic/UCI", f"Illegal move: {move_str}")
                game.headers["Termination"] = "illegal move"
                return ("black" if board.turn == chess.WHITE else "white"), game
            node = node.add_main_variation(move)
            board.push(move)
        except:
            log_failure(engine.name, board.fen(), "Logic/UCI", f"Unparseable move: {move_str}")
            game.headers["Termination"] = "illegal move"
            return ("black" if board.turn == chess.WHITE else "white"), game
    else:
        res = board.result(claim_draw=True)
        if res == "1-0": result = "white"
        elif res == "0-1": result = "black"
        else: result = "draw"

    game.headers["Result"] = "1-0" if result == "white" else ("0-1" if result == "black" else "1/2-1/2")
    return result, game

def main():
    parser = argparse.ArgumentParser(description="Hardened Arena")
    parser.add_argument("--engine-a", required=True)
    parser.add_argument("--engine-b", required=True)
    parser.add_argument("--games", type=int, default=50)
    parser.add_argument("--movetime", type=int, default=100)
    args = parser.parse_args()

    os.makedirs(PGNS_DIR, exist_ok=True)
    name_a = os.path.basename(os.path.dirname(os.path.abspath(args.engine_a)))
    name_b = os.path.basename(os.path.dirname(os.path.abspath(args.engine_b)))

    print(f"\n[HARDENED ARENA] {name_a} vs {name_b} | Memory: {MEMORY_LIMIT_MB}MB | Timeout: {MOVE_TIMEOUT}s")

    wins_a = 0
    losses_a = 0
    draws = 0

    for game_num in range(1, args.games + 1):
        pair_num = (game_num - 1) // 2
        fen = OPENING_BOOK[pair_num % len(OPENING_BOOK)]
        
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

        if not white_engine.init_uci() or not black_engine.init_uci():
            losses_a += 1 if a_is_white else 0
            wins_a += 1 if not a_is_white else 0
            white_engine.stop()
            black_engine.stop()
            print(f"  Game {game_num}/{args.games}: init failure")
            continue

        result, pgn_game = play_game(white_engine, black_engine, args.movetime, fen)
        white_engine.stop()
        black_engine.stop()

        if result == "draw": draws += 1
        elif (result == "white" and a_is_white) or (result == "black" and not a_is_white): wins_a += 1
        else: losses_a += 1

        pgn_filename = f"{name_a}_vs_{name_b}_game{game_num}.pgn"
        with open(os.path.join(PGNS_DIR, pgn_filename), "w") as f: print(pgn_game, file=f)
        print(f"  Game {game_num}/{args.games}: [{result[0].upper()}] {pgn_game.headers['Result']}")

    print(f"\nFinal: {wins_a}W-{losses_a}L-{draws}D")

if __name__ == "__main__":
    main()
