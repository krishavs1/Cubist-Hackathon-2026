import sys
import chess
from engine.search import best_move

ENGINE_NAME = "HackathonEngine"
ENGINE_AUTHOR = "Cubist Hackathon 2026"


class UCIAdapter:
    def __init__(self, depth: int = 3):
        self.board = chess.Board()
        self.depth = depth

    def handle(self, command: str) -> str | None:
        """Process a single UCI command and return the response string, or None."""
        parts = command.strip().split()
        if not parts:
            return None
        cmd = parts[0]

        if cmd == "uci":
            return f"id name {ENGINE_NAME}\nid author {ENGINE_AUTHOR}\nuciok"

        if cmd == "isready":
            return "readyok"

        if cmd == "ucinewgame":
            self.board = chess.Board()
            return None

        if cmd == "position":
            self._handle_position(parts[1:])
            return None

        if cmd == "go":
            depth = self.depth
            for i, p in enumerate(parts):
                if p == "depth" and i + 1 < len(parts):
                    depth = int(parts[i + 1])
            move = best_move(self.board, depth)
            return f"bestmove {move.uci()}" if move else "bestmove 0000"

        if cmd == "quit":
            return "__quit__"

        return None

    def _handle_position(self, args: list) -> None:
        if not args:
            return

        if args[0] == "startpos":
            self.board = chess.Board()
            moves_start = 2 if len(args) > 1 and args[1] == "moves" else len(args)
            for uci_move in args[moves_start:]:
                self.board.push_uci(uci_move)

        elif args[0] == "fen":
            fen_parts = []
            i = 1
            while i < len(args) and args[i] != "moves":
                fen_parts.append(args[i])
                i += 1
            self.board = chess.Board(" ".join(fen_parts))
            if i < len(args) and args[i] == "moves":
                for uci_move in args[i + 1:]:
                    self.board.push_uci(uci_move)

    def run(self) -> None:
        """Start the blocking UCI event loop reading from stdin."""
        for line in sys.stdin:
            response = self.handle(line)
            if response == "__quit__":
                break
            if response:
                print(response, flush=True)
