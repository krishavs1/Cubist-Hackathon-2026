"""Human and UCI engine player types for the pygame chess GUI."""

from __future__ import annotations

from dataclasses import dataclass
import os
import queue
import subprocess
import sys
import threading
import time
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    import chess


@dataclass(frozen=True)
class EngineOption:
    """A runnable chess engine discovered in the repository."""

    name: str
    root: str
    command: tuple[str, ...]


def _repo_name_for(path: str, repo_root: str) -> str:
    rel = os.path.relpath(path, repo_root)
    parts = rel.split(os.sep)
    if len(parts) >= 3 and parts[-1] == "engine":
        return parts[-2]
    if len(parts) >= 2 and parts[-1] == "engine":
        return parts[-2]
    return parts[-1]


def _command_for_engine_dir(path: str, repo_root: str) -> tuple[str, ...] | None:
    run_sh = os.path.join(path, "run.sh")
    chess_engine = os.path.join(path, "chess_engine.py")
    engine_py = os.path.join(path, "engine.py")

    if os.path.basename(path) == "engine" and os.path.isfile(run_sh):
        return ("bash", run_sh)

    if os.path.isfile(chess_engine):
        return (sys.executable, chess_engine)

    if os.path.isfile(engine_py):
        return (sys.executable, engine_py)

    if os.path.isfile(run_sh):
        return ("bash", run_sh)

    return None


def discover_engines(repo_root: str) -> list[EngineOption]:
    """Find folders that look like runnable chess engines.

    The hackathon repo has a mix of `engine/run.sh`, top-level `run.sh`,
    `engine.py`, and `chess_engine.py` entries. Prefer direct Python entry
    points for top-level folders with interactive launcher scripts.
    """

    ignored = {
        ".git",
        ".venv",
        "__pycache__",
        "node_modules",
        "pgns",
        "gui",
        "PlayerClass",
        "strategies",
        "unused",
        "subagent_template",
    }
    candidates: dict[str, EngineOption] = {}

    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in ignored and not d.startswith(".tmp")]
        if not ({"run.sh", "engine.py", "chess_engine.py"} & set(filenames)):
            continue

        command = _command_for_engine_dir(dirpath, repo_root)
        if command is None:
            continue

        rel = os.path.relpath(dirpath, repo_root)
        if os.path.isfile(os.path.join(dirpath, "engine", "run.sh")):
            continue
        if rel == os.path.join("src", "rust-engine", "engine"):
            binary = os.path.join(repo_root, "src", "rust-engine", "target", "release", "rust-engine")
            if not os.path.isfile(binary):
                continue
        # Skip supporting engine packages when their parent exposes a run.sh
        # contract, except for Strategy1/engines/mve where the wrapper lives
        # elsewhere and can be selected as Strategy1.
        if os.sep in rel and rel.endswith(os.path.join("engines", "mve")):
            continue

        name = _repo_name_for(dirpath, repo_root)
        key = os.path.abspath(dirpath)
        candidates[key] = EngineOption(name=name, root=dirpath, command=command)

    return sorted(candidates.values(), key=lambda e: e.name.lower())


class User:
    kind = "user"

    def __init__(self, name: str = "Human"):
        self.name = name

    def is_engine(self) -> bool:
        return False

    def label(self) -> str:
        return self.name


class Engine:
    kind = "engine"

    def __init__(self, options: list[EngineOption], index: int = 0, name: str = "Engine"):
        self.options = options
        self.index = index if options else -1
        self.name = name
        self.proc: subprocess.Popen[str] | None = None
        self._stdout: queue.Queue[str] = queue.Queue()
        self._thinking = False
        self._last_error: str | None = None
        self._log: list[str] = []

    def is_engine(self) -> bool:
        return True

    @property
    def current_option(self) -> EngineOption | None:
        if not self.options or self.index < 0:
            return None
        return self.options[self.index % len(self.options)]

    def label(self) -> str:
        option = self.current_option
        if option is None:
            return f"{self.name}: no engine"
        return f"{self.name}: {option.name}"

    def cycle(self, step: int = 1) -> None:
        if not self.options:
            return
        self.stop()
        self.index = (self.index + step) % len(self.options)
        self._log.clear()
        self._last_error = None

    def thinking(self) -> bool:
        return self._thinking

    def log_lines(self, limit: int = 10) -> list[str]:
        lines = self._log[-limit:]
        if self._last_error:
            lines = lines + [self._last_error]
        return lines[-limit:]

    def add_log(self, line: str) -> None:
        self._append_log(line)

    def _append_log(self, line: str) -> None:
        line = line.strip()
        if not line:
            return
        self._log.append(line)
        self._log = self._log[-80:]

    def _reader(self) -> None:
        assert self.proc is not None and self.proc.stdout is not None
        for line in self.proc.stdout:
            self._stdout.put(line.rstrip("\n"))

    def start(self) -> bool:
        option = self.current_option
        if option is None:
            self._last_error = "No engine folders found"
            return False
        if self.proc and self.proc.poll() is None:
            return True

        try:
            env = os.environ.copy()
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            venv_bin = os.path.join(repo_root, ".venv", "bin")
            if os.path.isdir(venv_bin):
                env["PATH"] = venv_bin + os.pathsep + env.get("PATH", "")

            self.proc = subprocess.Popen(
                list(option.command),
                cwd=option.root,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            self._last_error = f"Could not start {option.name}: {exc}"
            return False

        threading.Thread(target=self._reader, daemon=True).start()
        self._append_log(f"started {option.name}")
        return self._handshake()

    def _send(self, command: str) -> bool:
        if not self.proc or self.proc.poll() is not None or not self.proc.stdin:
            return False
        self._append_log(f"> {command}")
        try:
            self.proc.stdin.write(command + "\n")
            self.proc.stdin.flush()
            return True
        except OSError as exc:
            self._last_error = f"send failed: {exc}"
            return False

    def _read_until(self, predicate: Callable[[str], bool], timeout: float) -> str | None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc and self.proc.poll() is not None:
                self._last_error = "engine exited"
                return None
            try:
                line = self._stdout.get(timeout=0.05)
            except queue.Empty:
                continue
            self._append_log(line)
            if predicate(line):
                return line
        return None

    def _handshake(self) -> bool:
        if not self._send("uci"):
            return False
        if self._read_until(lambda line: "uciok" in line, 5.0) is None:
            self._last_error = "UCI handshake timed out"
            return False
        self._send("setoption name Depth value 2")
        self._send("isready")
        if self._read_until(lambda line: "readyok" in line, 5.0) is None:
            self._last_error = "isready timed out"
            return False
        self._send("ucinewgame")
        return True

    def request_move(
        self,
        board: chess.Board,
        movetime_ms: int,
        callback: Callable[[chess.Move | None, str | None], None],
    ) -> None:
        if self._thinking:
            return

        board_fen = board.fen()
        legal_uci = {move.uci(): move for move in board.legal_moves}
        self._thinking = True

        def worker() -> None:
            move: chess.Move | None = None
            error: str | None = None
            try:
                if not self.start():
                    error = self._last_error or "engine failed to start"
                    return
                if not self._send(f"position fen {board_fen}"):
                    error = "could not send position"
                    return
                if not self._send(f"go movetime {movetime_ms}"):
                    error = "could not start search"
                    return

                line = self._read_until(lambda text: text.startswith("bestmove"), max(8.0, movetime_ms / 1000 + 6.0))
                if line is None:
                    error = "move timed out"
                    return
                parts = line.split()
                move_uci = parts[1] if len(parts) > 1 else ""
                move = legal_uci.get(move_uci)
                if move is None:
                    error = f"illegal bestmove: {move_uci or '(empty)'}"
            finally:
                self._thinking = False
                callback(move, error)

        threading.Thread(target=worker, daemon=True).start()

    def stop(self) -> None:
        if not self.proc:
            return
        try:
            if self.proc.poll() is None:
                self._send("quit")
                self.proc.wait(timeout=0.5)
        except Exception:
            if self.proc.poll() is None:
                self.proc.kill()
        finally:
            self.proc = None
            while not self._stdout.empty():
                try:
                    self._stdout.get_nowait()
                except queue.Empty:
                    break
