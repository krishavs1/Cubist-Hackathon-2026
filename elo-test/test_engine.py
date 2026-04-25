"""
UCI conformance + legality checker.

Usage:
    python core/test_engine.py --engine engines/your-engine/run.sh

Tests:
  1. UCI handshake (uci → uciok)
  2. Ready check (isready → readyok)
  3. Legal move on 20 random positions
  4. Startpos test
  5. Moves parsing test
  6. Quit (process exits cleanly)
"""

import argparse
import os
import subprocess
import sys
import time
import random
import threading
import queue

import chess


TIMEOUT = 5  # seconds for most commands
MOVE_TIMEOUT = 5  # seconds for bestmove responses


def start_engine(engine_path):
    """Start engine subprocess."""
    proc = subprocess.Popen(
        ["bash", engine_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    # Attach a threaded line reader to avoid select() issues on macOS pipes
    q = queue.Queue()

    def reader():
        try:
            for line in proc.stdout:
                q.put(line)
        except ValueError:
            pass

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    proc._line_queue = q
    return proc


def send(proc, command):
    """Send a command to the engine."""
    proc.stdin.write(command + "\n")
    proc.stdin.flush()


def read_until(proc, target, timeout):
    """Read stdout lines until one contains target or timeout."""
    start = time.time()
    lines = []
    while time.time() - start < timeout:
        try:
            line = proc._line_queue.get(timeout=0.1)
            lines.append(line.strip())
            if target in line:
                return True, lines
        except queue.Empty:
            if proc.poll() is not None:
                break
    return False, lines


def read_bestmove(proc, timeout):
    """Read until bestmove line, return the move string."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            line = proc._line_queue.get(timeout=0.1).strip()
            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1]
        except queue.Empty:
            if proc.poll() is not None:
                break
    return None


def random_position():
    """Generate a random position by playing random moves from startpos."""
    board = chess.Board()
    num_moves = random.randint(5, 40)
    for _ in range(num_moves):
        if board.is_game_over():
            break
        move = random.choice(list(board.legal_moves))
        board.push(move)
    if board.is_game_over():
        board = chess.Board()
        for _ in range(random.randint(2, 10)):
            if board.is_game_over():
                break
            board.push(random.choice(list(board.legal_moves)))
    return board


def test_uci_handshake(engine_path):
    """Test 1: Send uci, expect uciok within 5s."""
    proc = start_engine(engine_path)
    try:
        send(proc, "uci")
        found, _ = read_until(proc, "uciok", TIMEOUT)
        return found, "uci → uciok"
    finally:
        proc.kill()
        proc.wait()


def test_isready(engine_path):
    """Test 2: Send isready, expect readyok within 5s."""
    proc = start_engine(engine_path)
    try:
        send(proc, "uci")
        read_until(proc, "uciok", TIMEOUT)
        send(proc, "isready")
        found, _ = read_until(proc, "readyok", TIMEOUT)
        return found, "isready → readyok"
    finally:
        proc.kill()
        proc.wait()


def test_random_positions(engine_path, count=20):
    """Test 3: Generate random positions, verify bestmove is legal."""
    proc = start_engine(engine_path)
    try:
        send(proc, "uci")
        read_until(proc, "uciok", TIMEOUT)
        send(proc, "isready")
        read_until(proc, "readyok", TIMEOUT)

        failures = []
        for i in range(count):
            board = random_position()
            if board.is_game_over():
                continue

            fen = board.fen()
            send(proc, f"position fen {fen}")
            send(proc, "go movetime 500")
            move_str = read_bestmove(proc, MOVE_TIMEOUT)

            if move_str is None:
                failures.append(f"  Position {i + 1}: no bestmove response (timeout)")
                continue

            try:
                move = chess.Move.from_uci(move_str)
            except ValueError:
                failures.append(f"  Position {i + 1}: invalid UCI move '{move_str}'")
                continue

            if move not in board.legal_moves:
                failures.append(f"  Position {i + 1}: illegal move {move_str} in FEN {fen}")

        if failures:
            return False, "Legal moves on random positions\n" + "\n".join(failures)
        return True, f"Legal moves on {count} random positions"
    finally:
        proc.kill()
        proc.wait()


def test_startpos(engine_path):
    """Test 4: position startpos + go movetime, verify legal move."""
    proc = start_engine(engine_path)
    try:
        send(proc, "uci")
        read_until(proc, "uciok", TIMEOUT)
        send(proc, "isready")
        read_until(proc, "readyok", TIMEOUT)

        send(proc, "position startpos")
        send(proc, "go movetime 500")
        move_str = read_bestmove(proc, MOVE_TIMEOUT)

        if move_str is None:
            return False, "startpos bestmove: no response"

        board = chess.Board()
        try:
            move = chess.Move.from_uci(move_str)
        except ValueError:
            return False, f"startpos bestmove: invalid UCI '{move_str}'"

        if move not in board.legal_moves:
            return False, f"startpos bestmove: illegal move {move_str}"

        return True, f"startpos bestmove: {move_str}"
    finally:
        proc.kill()
        proc.wait()


def test_moves_parsing(engine_path):
    """Test 5: position startpos moves e2e4 e7e5 + go, verify legal."""
    proc = start_engine(engine_path)
    try:
        send(proc, "uci")
        read_until(proc, "uciok", TIMEOUT)
        send(proc, "isready")
        read_until(proc, "readyok", TIMEOUT)

        send(proc, "position startpos moves e2e4 e7e5")
        send(proc, "go movetime 500")
        move_str = read_bestmove(proc, MOVE_TIMEOUT)

        if move_str is None:
            return False, "moves parsing: no response"

        board = chess.Board()
        board.push_uci("e2e4")
        board.push_uci("e7e5")

        try:
            move = chess.Move.from_uci(move_str)
        except ValueError:
            return False, f"moves parsing: invalid UCI '{move_str}'"

        if move not in board.legal_moves:
            return False, f"moves parsing: illegal move {move_str}"

        return True, f"moves parsing: {move_str}"
    finally:
        proc.kill()
        proc.wait()


def test_quit(engine_path):
    """Test 6: Send quit, verify process exits within 2s."""
    proc = start_engine(engine_path)
    try:
        send(proc, "uci")
        read_until(proc, "uciok", TIMEOUT)
        send(proc, "quit")
        try:
            proc.wait(timeout=2)
            return True, "quit → process exited"
        except subprocess.TimeoutExpired:
            return False, "quit → process did not exit within 2s"
    finally:
        proc.kill()
        proc.wait()


def main():
    parser = argparse.ArgumentParser(description="UCI conformance + legality checker")
    parser.add_argument("--engine", required=True, help="Path to engine run.sh")
    args = parser.parse_args()

    tests = [
        ("UCI handshake", test_uci_handshake),
        ("Ready check", test_isready),
        ("Random positions", test_random_positions),
        ("Startpos", test_startpos),
        ("Moves parsing", test_moves_parsing),
        ("Quit", test_quit),
    ]

    all_passed = True
    print(f"\n{'='*60}")
    print(f"  UCI Conformance Test — {args.engine}")
    print(f"{'='*60}\n")

    for name, test_fn in tests:
        try:
            passed, detail = test_fn(args.engine)
        except Exception as e:
            passed, detail = False, f"Exception: {e}"

        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {detail}")
        if not passed:
            all_passed = False

    print(f"\n{'='*60}")
    if all_passed:
        print("  ALL TESTS PASSED")
    else:
        print("  SOME TESTS FAILED")
    print(f"{'='*60}\n")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
