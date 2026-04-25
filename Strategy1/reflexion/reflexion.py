#!/usr/bin/env python3
"""
Workstream E: Reflexion Loop
============================

Implements the Reflexion-based learning cycle described in DARWINIAN_AI.md:

  1. Collect PGNs where Strategy1's current champion LOST
  2. Have an AI analyst read them and propose a corrected evaluator
  3. Validate and append the new personality to heuristics.py + REGISTRY
  4. Re-run the internal tournament
  5. Log the result with a [REFLEXION] tag in ARENA_LOG.md
  6. If the new personality beats the current champion, promote it in run.sh

Based on: Reflexion: Language Agents with Verbal Reinforcement Learning
         (Shinn et al., 2023)

Two modes:
  --mode offline   Use a pre-analysed reflexion_v1 authored by Claude-in-Cursor
                   (see REFLEXION_ANALYSIS.md for the full thought process).
                   This is the default and requires no API key.
  --mode api       Call the Anthropic API directly. Requires ANTHROPIC_API_KEY.

Usage:
    python3 reflexion.py                          # offline mode, full cycle
    python3 reflexion.py --dry-run                # just collect PGNs + show plan
    python3 reflexion.py --mode api               # use Claude API
"""

import argparse
import ast
import os
import re
import sys
import textwrap
import time
from pathlib import Path

import chess.pgn

SCRIPT_DIR   = Path(__file__).resolve().parent
STRATEGY_DIR = SCRIPT_DIR.parent
REPO_ROOT    = STRATEGY_DIR.parent
ENGINE_DIR   = STRATEGY_DIR / "engines" / "mve"
HEURISTICS   = ENGINE_DIR / "heuristics.py"
RUN_SH       = STRATEGY_DIR / "engine" / "run.sh"
ARENA_LOG    = STRATEGY_DIR / "ARENA_LOG.md"
PGN_DIR      = REPO_ROOT / "pgns"
TOURNAMENT   = STRATEGY_DIR / "arena" / "tournament.py"
ANALYSIS_MD  = SCRIPT_DIR / "REFLEXION_ANALYSIS.md"


# ── The reflexion_v1 authored from the loss-PGN analysis ─────────────────────
#
# This is the concrete output of the Reflexion cycle. Claude (via Cursor)
# read engine_vs_stockfish-skill-1_game{1..5}.pgn, identified that
# positional_grinder has no concept of piece development / castling /
# knight-placement / tempo, and wrote this function as the correction.
#
# See REFLEXION_ANALYSIS.md for the full reasoning trace.
REFLEXION_V1_SOURCE = textwrap.dedent('''
    def reflexion_v1(board: chess.Board) -> int:
        """
        Reflexion cycle 1 — corrects positional_grinder's blind spots.

        positional_grinder lost games because it had no concept of:
          * piece development (minor pieces moving off starting squares)
          * castling (king stayed on e1/e8 and got mated on central files)
          * knight placement (knights wandered to a/h rim squares)
          * tempo (queen came out too early, same piece moved 5-7 times)

        This evaluator inherits positional_grinder's logic and adds:
          + bonus for each developed minor piece
          + large bonus for having castled; large penalty for not castling
          + penalty for knights on the a/h files
          + penalty for an early queen (moved before 4 minors are developed)

        All additions combined cap at ~120 cp so material remains dominant.
        """
        score = material_balance(board)

        for sq in CENTER_SQUARES:
            if board.is_attacked_by(chess.WHITE, sq):
                score += 25
            if board.is_attacked_by(chess.BLACK, sq):
                score -= 25

        for sq in EXTENDED_CENTER:
            piece = board.piece_at(sq)
            if piece:
                score += 8 if piece.color == chess.WHITE else -8

        score -= max(0, 3 - pawn_shield_count(board, chess.WHITE)) * 25
        score += max(0, 3 - pawn_shield_count(board, chess.BLACK)) * 25

        # -- REFLEXION ADDITIONS --

        # 1. Development: bonus for minor pieces off their starting squares
        white_minor_starts = (chess.B1, chess.G1, chess.C1, chess.F1)
        black_minor_starts = (chess.B8, chess.G8, chess.C8, chess.F8)
        dev_w = sum(
            1 for sq in white_minor_starts
            if board.piece_at(sq) is None
            or board.piece_at(sq).color != chess.WHITE
            or board.piece_at(sq).piece_type not in (chess.KNIGHT, chess.BISHOP)
        )
        dev_b = sum(
            1 for sq in black_minor_starts
            if board.piece_at(sq) is None
            or board.piece_at(sq).color != chess.BLACK
            or board.piece_at(sq).piece_type not in (chess.KNIGHT, chess.BISHOP)
        )
        score += dev_w * 15
        score -= dev_b * 15

        # 2. Castling: big reward for having castled
        wk_sq = board.king(chess.WHITE)
        bk_sq = board.king(chess.BLACK)
        if wk_sq in (chess.G1, chess.C1):
            score += 40
        elif wk_sq == chess.E1 and board.fullmove_number > 10:
            score -= 40  # king stuck in center past move 10
        if bk_sq in (chess.G8, chess.C8):
            score -= 40
        elif bk_sq == chess.E8 and board.fullmove_number > 10:
            score += 40

        # 3. Knight-on-rim penalty (a-file and h-file)
        rim_files = chess.BB_FILE_A | chess.BB_FILE_H
        w_rim_knights = chess.popcount(
            board.pieces_mask(chess.KNIGHT, chess.WHITE) & rim_files
        )
        b_rim_knights = chess.popcount(
            board.pieces_mask(chess.KNIGHT, chess.BLACK) & rim_files
        )
        score -= w_rim_knights * 20
        score += b_rim_knights * 20

        # 4. Early queen penalty (queen moved before 3 minors are developed)
        w_queen_home = board.piece_at(chess.D1) == chess.Piece(chess.QUEEN, chess.WHITE)
        b_queen_home = board.piece_at(chess.D8) == chess.Piece(chess.QUEEN, chess.BLACK)
        if not w_queen_home and dev_w < 3 and board.fullmove_number < 10:
            score -= 25
        if not b_queen_home and dev_b < 3 and board.fullmove_number < 10:
            score += 25

        return score
''').strip()


# ── helpers ──────────────────────────────────────────────────────────────────

def collect_loss_pgns(pgn_dir: Path, champion: str, max_pgns: int = 10) -> list[str]:
    """PGNs where our engine (the 'engine' tag) was on the losing side."""
    losses = []
    for pgn_file in sorted(pgn_dir.glob("*.pgn")):
        with open(pgn_file) as f:
            game = chess.pgn.read_game(f)
        if game is None:
            continue
        white = game.headers.get("White", "").lower()
        black = game.headers.get("Black", "").lower()
        result = game.headers.get("Result", "*")

        is_ours = lambda n: any(t in n for t in ["cubistdarwin", "strategy1", champion.lower(), "engine"])

        if is_ours(white) and not is_ours(black) and result == "0-1":
            losses.append((pgn_file.name, str(game)))
        elif is_ours(black) and not is_ours(white) and result == "1-0":
            losses.append((pgn_file.name, str(game)))

        if len(losses) >= max_pgns:
            break
    return losses


def validate_function(fn_source: str) -> None:
    """Syntactic + contract validation of the reflexion_v1 body."""
    tree = ast.parse(fn_source)
    funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    if not any(f.name == "reflexion_v1" for f in funcs):
        raise ValueError("No function named 'reflexion_v1' in source")

    fn = next(f for f in funcs if f.name == "reflexion_v1")
    if len(fn.args.args) != 1 or fn.args.args[0].arg != "board":
        raise ValueError("reflexion_v1 must take one argument named 'board'")


def append_to_heuristics(fn_source: str, heuristics_path: Path) -> None:
    """Append function + register it in REGISTRY. Idempotent."""
    src = heuristics_path.read_text()

    if "def reflexion_v1(" in src:
        src = re.sub(
            r"\n\ndef reflexion_v1\(.*?(?=\n\ndef |\n\n# =+\n# REGISTRY|\Z)",
            "\n\n" + fn_source,
            src,
            flags=re.DOTALL,
        )
    else:
        registry_marker = "# ============================================================\n# REGISTRY"
        src = src.replace(registry_marker, fn_source + "\n\n\n" + registry_marker)

    if '"reflexion_v1"' not in src:
        src = src.replace(
            'REGISTRY: Dict[str, Callable[[chess.Board], int]] = {',
            'REGISTRY: Dict[str, Callable[[chess.Board], int]] = {\n    "reflexion_v1":        reflexion_v1,',
        )

    heuristics_path.write_text(src)


def run_tournament(personalities: list[str], time_ms: int) -> tuple[str, dict, str]:
    """Run internal tournament; return (champion, elo_table, full_output)."""
    import subprocess
    result = subprocess.run(
        [sys.executable, "-u", str(TOURNAMENT),
         "--games", "2", "--time", str(time_ms),
         "--personalities", *personalities],
        capture_output=True, text=True, cwd=str(STRATEGY_DIR),
    )
    output = result.stdout + result.stderr

    if result.returncode != 0:
        raise RuntimeError(
            f"Tournament subprocess failed (exit {result.returncode}).\n"
            f"Output tail:\n{output[-2000:]}"
        )

    champion_match = re.search(r">>> CHAMPION: (\S+)", output)
    if not champion_match:
        raise RuntimeError(
            "Tournament produced no CHAMPION line (probably no games completed).\n"
            f"Output tail:\n{output[-2000:]}"
        )
    champion = champion_match.group(1)

    # Parse the standings table printed by tournament.py
    # Format:  "1    reflexion_v1          1253    4    6    0    5.0/10   50.0%"
    elo = {}
    for line in output.splitlines():
        m = re.match(r"\s*\d+\s+(\S+)\s+(-?\d+)\s+\d+\s+\d+\s+\d+\s", line)
        if m and m.group(1) in personalities:
            elo[m.group(1)] = float(m.group(2))

    if len(elo) < len(personalities):
        raise RuntimeError(
            f"Failed to parse Elo table (got {len(elo)}/{len(personalities)}).\n"
            f"Output tail:\n{output[-2000:]}"
        )

    return champion, elo, output


def log_reflexion_result(champion_before, champion_after, elo, output, promoted, loss_files):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    status = (f"PROMOTED -- `{champion_after}` is new champion in run.sh" if promoted
              else f"NOT PROMOTED -- `{champion_before}` remains champion")

    elo_lines = "\n".join(
        f"{i+1}. **{name}** -- Elo {score:.0f}"
        for i, (name, score) in enumerate(sorted(elo.items(), key=lambda x: -x[1]))
    )

    block = f"""
## [REFLEXION] cycle 1 -- {timestamp}

**Analyst:** Claude (via Cursor IDE, offline mode)
**Champion before:** `{champion_before}`
**Loss PGNs analysed:** {len(loss_files)} games
**Champion after:** `{champion_after}`
**Outcome:** {status}

### Observed failure modes
1. No concept of piece development (5-7 opening moves with the same piece)
2. No castling -- king stuck on e1/e8 and mated on central files
3. Knights wandered to rim squares (a/h files)
4. Tempo loss from repeated same-piece moves

### Correction (`reflexion_v1`)
Inherits `positional_grinder` and adds: development bonus, castling
bonus/penalty, knight-on-rim penalty, early-queen penalty.
See `reflexion/REFLEXION_ANALYSIS.md` for the full reasoning trace.

### Post-Reflexion Elo Standings
{elo_lines}

<details>
<summary>Full tournament output</summary>

```
{output.strip()}
```

</details>

---
"""
    with open(ARENA_LOG, "a") as f:
        f.write(block)


def update_run_sh(new_champion: str) -> None:
    """Rewrite engine/run.sh so both the header block and the --heuristic flag
    reference the promoted champion."""
    header = textwrap.dedent(f'''\
        #!/bin/bash
        # Darwinian AI Engine -- UCI entry point for elo-test/arena.py and grade.py.
        #
        # Champion: '{new_champion}' -- promoted by the Reflexion loop
        # (Workstream E) on {time.strftime('%Y-%m-%d')}. See ARENA_LOG.md for the
        # tournament block that produced this selection. The tournament
        # picked this personality; it is not a human override.
        set -euo pipefail

        SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
        ENGINE_DIR="$SCRIPT_DIR/../engines/mve"
        REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

        cd "$ENGINE_DIR"

        if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
            exec "$REPO_ROOT/.venv/bin/python" engine.py --heuristic {new_champion}
        else
            exec /usr/bin/python3 engine.py --heuristic {new_champion}
        fi
        ''')
    RUN_SH.write_text(header)


def call_claude_api(champion: str, loss_pgns: list[str]) -> str:
    """Optional: hit the Anthropic API for a reflexion_v1 instead of using the offline source."""
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    heuristics_src = HEURISTICS.read_text()
    champion_fn = re.search(
        rf"def {re.escape(champion)}\(.*?(?=\ndef |\nREGISTRY|\Z)",
        heuristics_src, re.DOTALL,
    )
    champion_src = champion_fn.group(0) if champion_fn else heuristics_src[:2000]

    pgn_block = "\n\n---\n\n".join(pgn for _, pgn in loss_pgns[:5])
    prompt = textwrap.dedent(f"""
        You are an expert chess programmer. We lost the following games with
        the `{champion}` evaluator:

        ```python
        {champion_src}
        ```

        Losing games:
        {pgn_block}

        Propose a NEW Python function `reflexion_v1(board: chess.Board) -> int`
        that corrects the weaknesses. Return centipawns from White's POV.
        Don't call board.push/pop. Don't handle terminal states.
        Use only the `chess` module. Keep material dominant.
        Output ONLY the function, starting with `def reflexion_v1`.
    """).strip()

    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    text = re.sub(r"^```python\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```\s*$", "", text, flags=re.MULTILINE).strip()
    m = re.search(r"(def reflexion_v1\b.*)", text, re.DOTALL)
    if not m:
        raise ValueError("Claude response did not contain def reflexion_v1")
    return m.group(1)


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Reflexion loop -- Workstream E")
    parser.add_argument("--champion", default="positional_grinder")
    parser.add_argument("--pgn-dir", default=str(PGN_DIR))
    parser.add_argument("--max-pgns", type=int, default=10)
    parser.add_argument("--tournament-time", type=int, default=50)
    parser.add_argument("--mode", choices=["offline", "api"], default="offline",
                        help="offline uses pre-analysed reflexion_v1; api calls Claude")
    parser.add_argument("--personalities", nargs="+", default=None,
                        help="Subset of personalities for the verification tournament. "
                             "Defaults to the full REGISTRY.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("=" * 62)
    print("WORKSTREAM E: REFLEXION LOOP")
    print("=" * 62)
    print(f"Mode: {args.mode}")

    # ── Step 1: collect loss PGNs ───────────────────────────────
    print(f"\n[1/6] Collecting loss PGNs for '{args.champion}'...")
    loss_pgns = collect_loss_pgns(Path(args.pgn_dir), args.champion, args.max_pgns)
    print(f"  Found {len(loss_pgns)} loss PGN(s)")
    for name, _ in loss_pgns[:5]:
        print(f"    - {name}")

    if args.dry_run:
        print("\nDry run -- stopping here.")
        return

    # ── Step 2: obtain the reflexion_v1 source ─────────────────
    print(f"\n[2/6] Obtaining reflexion_v1 ({args.mode} mode)...")
    if args.mode == "offline":
        fn_source = REFLEXION_V1_SOURCE
        print(f"  Using offline reflexion_v1 (authored by Claude-in-Cursor)")
        print(f"  Analysis: {ANALYSIS_MD}")
    else:
        fn_source = call_claude_api(args.champion, loss_pgns)
        print(f"  Claude API returned {len(fn_source)} chars")

    # ── Step 3: validate ─────────────────────────────────────
    print(f"\n[3/6] Validating reflexion_v1 source...")
    validate_function(fn_source)
    print(f"  Function validated ({len(fn_source.splitlines())} lines)")

    # ── Step 4: inject into heuristics.py ────────────────────
    print(f"\n[4/6] Injecting into heuristics.py...")
    append_to_heuristics(fn_source, HEURISTICS)
    print(f"  reflexion_v1 appended + registered in REGISTRY")

    # ── Step 5: run tournament ───────────────────────────────
    print(f"\n[5/6] Running post-reflexion tournament ({args.tournament_time}ms/move)...")
    if args.personalities:
        personalities = args.personalities
        if "reflexion_v1" not in personalities:
            personalities = ["reflexion_v1"] + personalities
    else:
        registry_src = HEURISTICS.read_text()
        personalities = [p for p in re.findall(r'"(\w+)":\s+\w+', registry_src) if p != "pesto"]
    print(f"  Personalities: {personalities}")

    champion_after, elo, output = run_tournament(personalities, args.tournament_time)
    print(f"\n  Champion before: {args.champion}")
    print(f"  Champion after:  {champion_after}")
    print(f"  Post-reflexion Elo table:")
    for name, score in sorted(elo.items(), key=lambda x: -x[1]):
        marker = " <<<" if name == champion_after else ""
        print(f"    {name:22} Elo {score:.0f}{marker}")

    # ── Step 6: promote if better ────────────────────────────
    print(f"\n[6/6] Logging result and updating run.sh if needed...")
    promoted = (champion_after == "reflexion_v1")
    log_reflexion_result(args.champion, champion_after, elo, output, promoted,
                          [name for name, _ in loss_pgns])
    print(f"  [REFLEXION] block appended to ARENA_LOG.md")

    if promoted:
        update_run_sh("reflexion_v1")
        print(f"  run.sh updated -> reflexion_v1")
        print(f"\n  reflexion_v1 is the new champion!")
    else:
        print(f"\n  '{args.champion}' remains champion. reflexion_v1 logged for analysis.")

    print("\n" + "=" * 62)
    print("REFLEXION CYCLE COMPLETE")
    print("=" * 62)


if __name__ == "__main__":
    main()
