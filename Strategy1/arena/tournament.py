#!/usr/bin/env python3
"""
Darwinian Arena: round-robin tournament between heuristic personalities.

Every personality plays every other personality N times, alternating
colors. We track W/D/L, compute Elo ratings (iterative K-factor), and
crown the personality with the highest Elo as the Champion.

The Champion is the engine variant submitted for cross-strategy
comparison against other teams' MVPs.

Why in-process (not subprocess)?
- 10x faster: no process spawn or pipe IPC per move
- Easier to debug a hung tournament
- We've already validated UCI compliance via tests/uci_test.py, so
  external arenas (cutechess-cli) work too if we need them later

Run:
    python3 tournament.py                    # default: 2 games/pair, 100ms/move
    python3 tournament.py --games 4 --time 200
    python3 tournament.py --personalities balanced aggressive_attacker fortress
"""

import argparse
import os
import sys
import time
from itertools import combinations
from typing import Callable, Dict, List, Tuple

import chess

# Make the engine package importable.
sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engines", "mve"),
)
import engine as mve  # noqa: E402
import heuristics as hh  # noqa: E402


# ============================================================
# GAME PLAYING
# ============================================================

def play_game(
    white_eval: Callable, black_eval: Callable,
    time_ms: int, max_plies: int = 200,
) -> Tuple[str, int]:
    """
    Play one game between two evaluators.
    Returns (result, plies) where result is '1-0', '0-1', or '1/2-1/2'.
    """
    board = chess.Board()
    while not board.is_game_over(claim_draw=True) and board.ply() < max_plies:
        eval_fn = white_eval if board.turn == chess.WHITE else black_eval
        move = mve.search(board, time_ms, eval_fn=eval_fn, verbose=False)
        if move is None or move not in board.legal_moves:
            break
        board.push(move)

    if board.is_checkmate():
        return ("0-1" if board.turn == chess.WHITE else "1-0"), board.ply()
    return "1/2-1/2", board.ply()


# ============================================================
# ELO CALCULATION
# ============================================================

def update_elo(rating_a: float, rating_b: float, score_a: float, k: float = 32.0) -> Tuple[float, float]:
    """
    Update Elo ratings after one game.
    score_a: 1.0 for A win, 0.5 for draw, 0.0 for A loss.
    """
    expected_a = 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400))
    expected_b = 1.0 - expected_a
    score_b = 1.0 - score_a
    new_a = rating_a + k * (score_a - expected_a)
    new_b = rating_b + k * (score_b - expected_b)
    return new_a, new_b


# ============================================================
# TOURNAMENT
# ============================================================

class Standings:
    """Tracks W/D/L and Elo for each personality."""

    def __init__(self, names: List[str], starting_elo: float = 1200.0):
        self.names = names
        self.elo: Dict[str, float] = {n: starting_elo for n in names}
        self.wins: Dict[str, int] = {n: 0 for n in names}
        self.draws: Dict[str, int] = {n: 0 for n in names}
        self.losses: Dict[str, int] = {n: 0 for n in names}

    def record(self, white: str, black: str, result: str) -> None:
        if result == "1-0":
            self.wins[white] += 1
            self.losses[black] += 1
            self.elo[white], self.elo[black] = update_elo(self.elo[white], self.elo[black], 1.0)
        elif result == "0-1":
            self.wins[black] += 1
            self.losses[white] += 1
            self.elo[white], self.elo[black] = update_elo(self.elo[white], self.elo[black], 0.0)
        else:
            self.draws[white] += 1
            self.draws[black] += 1
            self.elo[white], self.elo[black] = update_elo(self.elo[white], self.elo[black], 0.5)

    def games_played(self, name: str) -> int:
        return self.wins[name] + self.draws[name] + self.losses[name]

    def score(self, name: str) -> float:
        return self.wins[name] + 0.5 * self.draws[name]

    def ranked(self) -> List[str]:
        return sorted(self.names, key=lambda n: (-self.elo[n], -self.score(n)))

    def print_table(self) -> None:
        print()
        print("=" * 78)
        print(f"{'Rank':<5}{'Personality':<22}{'Elo':>8}  {'W':>4} {'D':>4} {'L':>4}  {'Score':>8}  {'WR%':>7}")
        print("-" * 78)
        for rank, name in enumerate(self.ranked(), 1):
            gp = self.games_played(name)
            wr = (self.score(name) / gp * 100) if gp else 0
            print(
                f"{rank:<5}{name:<22}{self.elo[name]:>8.0f}  "
                f"{self.wins[name]:>4} {self.draws[name]:>4} {self.losses[name]:>4}  "
                f"{self.score(name):>5.1f}/{gp:<2}  {wr:>6.1f}%"
            )
        print("=" * 78)


def run_tournament(
    personalities: List[str],
    games_per_pair: int,
    time_ms: int,
    log_path: str = None,
) -> Tuple[str, Standings]:
    """
    Run a round-robin tournament.
    Each pair plays `games_per_pair` games, alternating colors.
    Returns (champion_name, standings).
    """
    if len(personalities) < 2:
        raise ValueError("Need at least 2 personalities for a tournament")

    standings = Standings(personalities)
    pairs = list(combinations(personalities, 2))
    total_games = len(pairs) * games_per_pair
    game_num = 0
    start = time.time()

    print(f"Tournament: {len(personalities)} personalities, "
          f"{len(pairs)} pairs, {games_per_pair} games/pair = {total_games} games")
    print(f"Time control: {time_ms}ms per move")
    print("-" * 78)

    log_lines = [f"# Tournament started {time.strftime('%Y-%m-%d %H:%M:%S')}",
                 f"# {len(personalities)} personalities, {games_per_pair} games/pair, {time_ms}ms/move",
                 ""]

    for p1, p2 in pairs:
        eval1 = hh.get(p1)
        eval2 = hh.get(p2)
        for g in range(games_per_pair):
            game_num += 1
            # Alternate colors so neither personality has a permanent advantage
            if g % 2 == 0:
                white, black = p1, p2
                we, be = eval1, eval2
            else:
                white, black = p2, p1
                we, be = eval2, eval1

            game_start = time.time()
            result, plies = play_game(we, be, time_ms)
            game_time = time.time() - game_start
            standings.record(white, black, result)

            line = (f"  game {game_num:>3}/{total_games}: "
                    f"{white:>20} (W) vs {black:<20} (B)  "
                    f"-> {result:>7}  ({plies} plies, {game_time:.1f}s)")
            print(line)
            log_lines.append(line.strip())

    elapsed = time.time() - start
    print(f"\nTournament complete in {elapsed:.1f}s ({elapsed/total_games:.1f}s per game avg)")

    standings.print_table()

    champion = standings.ranked()[0]
    print(f"\n>>> CHAMPION: {champion}  (Elo {standings.elo[champion]:.0f}) <<<\n")

    # Persist log to ARENA_LOG.md per head.md Section 9
    log_lines.append("")
    log_lines.append(f"## Final Standings")
    for rank, name in enumerate(standings.ranked(), 1):
        log_lines.append(
            f"{rank}. **{name}** -- Elo {standings.elo[name]:.0f}, "
            f"{standings.wins[name]}W/{standings.draws[name]}D/{standings.losses[name]}L"
        )
    log_lines.append("")
    log_lines.append(f"**Champion: `{champion}`**")
    log_lines.append("")

    if log_path:
        with open(log_path, "a") as f:
            f.write("\n".join(log_lines) + "\n")
        print(f"Results appended to {log_path}")

    return champion, standings


def main() -> int:
    parser = argparse.ArgumentParser(description="Darwinian Arena tournament runner")
    parser.add_argument("--games", "-g", type=int, default=2,
                        help="Games per pair (split between colors)")
    parser.add_argument("--time", "-t", type=int, default=100,
                        help="Time per move in milliseconds")
    parser.add_argument("--personalities", "-p", nargs="+",
                        default=list(hh.REGISTRY.keys()),
                        help="Which personalities to enter (default: all)")
    parser.add_argument("--log", default="ARENA_LOG.md",
                        help="Path to append results (default: ARENA_LOG.md)")
    args = parser.parse_args()

    # Resolve log path relative to Strategy1 root
    log_path = args.log
    if not os.path.isabs(log_path):
        log_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", log_path
        )

    champion, _ = run_tournament(
        personalities=args.personalities,
        games_per_pair=args.games,
        time_ms=args.time,
        log_path=log_path,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
