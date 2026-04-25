#!/usr/bin/env python3
"""
OneShotOpus — UCI chess engine.

Runs a standard UCI loop on stdin/stdout. Supported commands:
    uci, isready, setoption, ucinewgame, position, go, stop, quit
Plus debug helpers: d (display), eval (static eval).
"""

import sys
import time
import threading
import chess

from search import Searcher

ENGINE_NAME = "OneShotOpus"
ENGINE_VERSION = "1.0"
ENGINE_AUTHOR = "Cubist Hackathon 2026"

DEFAULT_DEPTH = 64
DEFAULT_MOVETIME_MS = 1000


def emit(line: str) -> None:
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


class UCIEngine:
    def __init__(self) -> None:
        self.board = chess.Board()
        self.searcher = Searcher()
        self.search_thread: threading.Thread | None = None

    # ----- UCI handlers -----

    def cmd_uci(self) -> None:
        emit(f"id name {ENGINE_NAME} {ENGINE_VERSION}")
        emit(f"id author {ENGINE_AUTHOR}")
        emit("option name Hash type spin default 16 min 1 max 1024")
        emit("uciok")

    def cmd_isready(self) -> None:
        emit("readyok")

    def cmd_ucinewgame(self) -> None:
        self.board = chess.Board()
        self.searcher.reset()

    def cmd_position(self, args: list[str]) -> None:
        if not args:
            return
        if args[0] == "startpos":
            self.board = chess.Board()
            rest = args[1:]
        elif args[0] == "fen":
            # FEN occupies the next 6 tokens.
            if len(args) < 7:
                return
            fen = " ".join(args[1:7])
            try:
                self.board = chess.Board(fen)
            except ValueError:
                return
            rest = args[7:]
        else:
            return

        if rest and rest[0] == "moves":
            for uci in rest[1:]:
                try:
                    move = chess.Move.from_uci(uci)
                except ValueError:
                    break
                if move in self.board.legal_moves:
                    self.board.push(move)
                else:
                    break

    def cmd_go(self, args: list[str]) -> None:
        depth: int | None = None
        movetime: int | None = None
        wtime = btime = winc = binc = 0
        movestogo: int | None = None
        infinite = False

        i = 0
        while i < len(args):
            tok = args[i]
            if tok == "depth" and i + 1 < len(args):
                depth = int(args[i + 1]); i += 2
            elif tok == "movetime" and i + 1 < len(args):
                movetime = int(args[i + 1]); i += 2
            elif tok == "wtime" and i + 1 < len(args):
                wtime = int(args[i + 1]); i += 2
            elif tok == "btime" and i + 1 < len(args):
                btime = int(args[i + 1]); i += 2
            elif tok == "winc" and i + 1 < len(args):
                winc = int(args[i + 1]); i += 2
            elif tok == "binc" and i + 1 < len(args):
                binc = int(args[i + 1]); i += 2
            elif tok == "movestogo" and i + 1 < len(args):
                movestogo = int(args[i + 1]); i += 2
            elif tok == "infinite":
                infinite = True; i += 1
            else:
                i += 1

        time_limit_ms: int | None
        if infinite:
            time_limit_ms = None
        elif movetime is not None:
            # Spend ~95% of allotted move time, leaving slack for the GUI.
            time_limit_ms = max(int(movetime * 0.95), 10)
        elif wtime or btime:
            remaining = wtime if self.board.turn == chess.WHITE else btime
            inc = winc if self.board.turn == chess.WHITE else binc
            moves_left = movestogo if movestogo else 30
            # Soft target: remaining/moves_left + 0.75*inc, capped at remaining/2.
            budget = remaining // max(moves_left, 1) + (inc * 3) // 4
            budget = min(budget, max(remaining // 2, 50))
            time_limit_ms = max(budget, 30)
        else:
            time_limit_ms = DEFAULT_MOVETIME_MS

        max_depth = depth if depth is not None else DEFAULT_DEPTH

        # Run search in a background thread so a future "stop" could interrupt.
        def run() -> None:
            start = time.time()

            def info(d: int, score: int, move: chess.Move, nodes: int, _elapsed: float) -> None:
                ms = max(int((time.time() - start) * 1000), 1)
                nps = (nodes * 1000) // ms
                emit(f"info depth {d} score cp {score} nodes {nodes} "
                     f"nps {nps} time {ms} pv {move.uci()}")

            best = self.searcher.search(
                self.board, max_depth=max_depth,
                time_limit_ms=time_limit_ms, info_callback=info)
            if best is None:
                emit("bestmove 0000")
            else:
                emit(f"bestmove {best.uci()}")

        # If a prior search is still running, abort and wait for it.
        self._abort_and_wait()
        self.search_thread = threading.Thread(target=run, daemon=True)
        self.search_thread.start()

    def cmd_stop(self) -> None:
        # Force the searcher to abort on its next time check, then wait.
        self._abort_and_wait()

    def _abort_and_wait(self) -> None:
        thread = self.search_thread
        if thread is not None and thread.is_alive():
            self.searcher.deadline = 0.0
            thread.join(timeout=5.0)

    def _wait_for_search(self) -> None:
        thread = self.search_thread
        if thread is not None and thread.is_alive():
            thread.join()

    # ----- Loop -----

    def run(self) -> None:
        for raw in sys.stdin:
            line = raw.strip()
            if not line:
                continue
            tokens = line.split()
            cmd = tokens[0].lower()
            args = tokens[1:]

            if cmd == "uci":
                self.cmd_uci()
            elif cmd == "isready":
                self.cmd_isready()
            elif cmd == "ucinewgame":
                self.cmd_ucinewgame()
            elif cmd == "position":
                self.cmd_position(args)
            elif cmd == "go":
                self.cmd_go(args)
            elif cmd == "stop":
                self.cmd_stop()
            elif cmd == "setoption":
                pass  # No tunable options that affect search yet.
            elif cmd == "d":
                emit(str(self.board))
                emit(f"FEN: {self.board.fen()}")
            elif cmd == "eval":
                from evaluation import evaluate
                emit(f"eval (white POV, cp): {evaluate(self.board)}")
            elif cmd == "quit":
                self._abort_and_wait()
                break
        self._wait_for_search()


def main() -> None:
    UCIEngine().run()


if __name__ == "__main__":
    main()
