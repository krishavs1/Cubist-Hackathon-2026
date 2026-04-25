#!/usr/bin/env python3
"""
UCI compliance gauntlet for the MVE.

Spawns the engine as a subprocess and feeds it a sequence of UCI commands,
asserting that responses match the protocol. Any failure here would hang
or confuse the Arena tournament runner.
"""

import os
import subprocess
import sys

ENGINE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "engines", "mve", "engine.py",
)
PYTHON = sys.executable


def run_uci(commands: list, timeout: float = 8.0) -> str:
    """Send commands to the engine and return its full stdout."""
    script = "\n".join(commands) + "\nquit\n"
    proc = subprocess.run(
        [PYTHON, ENGINE],
        input=script,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.stdout


def expect(label: str, output: str, must_contain: list) -> bool:
    missing = [s for s in must_contain if s not in output]
    if missing:
        print(f"[FAIL] {label}")
        print(f"       missing: {missing}")
        print(f"       output:\n{output}")
        return False
    print(f"[OK  ] {label}")
    return True


def main() -> int:
    failures = 0

    # 1. Handshake
    out = run_uci(["uci"])
    if not expect("uci handshake", out, ["id name", "id author", "uciok"]):
        failures += 1

    # 2. isready
    out = run_uci(["uci", "isready"])
    if not expect("isready -> readyok", out, ["readyok"]):
        failures += 1

    # 3. Startpos search
    out = run_uci(["uci", "isready", "position startpos", "go movetime 200"])
    if not expect("startpos returns bestmove", out, ["bestmove "]):
        failures += 1

    # 4. Position with moves
    out = run_uci([
        "uci", "isready",
        "position startpos moves e2e4 e7e5",
        "go movetime 200",
    ])
    if not expect("position+moves returns bestmove", out, ["bestmove "]):
        failures += 1

    # 5. FEN position
    out = run_uci([
        "uci", "isready",
        "position fen rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        "go movetime 200",
    ])
    if not expect("FEN parsing returns bestmove", out, ["bestmove "]):
        failures += 1

    # 6. Mate-in-1 detection (Black to move, but white delivers mate next)
    # Position: Fool's mate end state. Black just played; white now has Qh5#.
    # Simpler: give a forced mate-in-1 for the side to move.
    # White: Kb1, Qa7. Black: Ka8. White Qa7-a8 is mate? No, that's not legal.
    # Use a known mate-in-1: 6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1, Re8 is mate.
    out = run_uci([
        "uci", "isready",
        "position fen 6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1",
        "go movetime 1000",
    ])
    if not expect("mate-in-1 finds Re8", out, ["bestmove e1e8"]):
        failures += 1

    # 7. Stalemate / no legal moves -- engine should not crash; bestmove 0000 OK.
    # Position: Black to move, stalemate. Black king a8, white king c7, white queen c8.
    # Wait, that's mate. Use: 7k/5Q2/6K1/8/8/8/8/8 b - - 0 1 -- this is stalemate.
    out = run_uci([
        "uci", "isready",
        "position fen 7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",
        "go movetime 200",
    ])
    if not expect("stalemate -> bestmove 0000 (no crash)", out, ["bestmove "]):
        failures += 1

    # 8. ucinewgame resets cleanly
    out = run_uci([
        "uci", "isready",
        "position startpos moves e2e4",
        "ucinewgame",
        "position startpos",
        "go movetime 200",
    ])
    if not expect("ucinewgame resets", out, ["bestmove "]):
        failures += 1

    # 9. Clock-based time control (wtime/btime)
    out = run_uci([
        "uci", "isready",
        "position startpos",
        "go wtime 5000 btime 5000 winc 100 binc 100",
    ])
    if not expect("clock-based go returns bestmove", out, ["bestmove "]):
        failures += 1

    print()
    if failures:
        print(f"{failures} UCI test(s) FAILED")
        return 1
    print("All UCI tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
