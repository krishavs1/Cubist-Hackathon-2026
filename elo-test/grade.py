import argparse
import json
import os
import subprocess
import sys
import platform
import shutil
import math
from datetime import datetime

# Path setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
SRC_DIR = os.path.join(REPO_ROOT, "src")
# Additional discovery roots. Each directory here is scanned with the same
# `<name>/engine/run.sh` convention as SRC_DIR. This lets us host engines
# grouped by lineage (e.g. ttt-iteration_bot/ for the
# tic-tac-toe → checkers → chess-ttt iteration) without forcing every
# engine to live under src/.
ENGINE_ROOTS = [
    SRC_DIR,
    os.path.join(REPO_ROOT, "ttt-iteration_bot"),
]
# Engines that live at the repo root and already have their own
# engine/run.sh (i.e. the folder itself IS the engine, not a container of
# engines). These get registered under the folder's basename.
DIRECT_ENGINES = [
    os.path.join(REPO_ROOT, "SimpleOneShot_bot"),
    os.path.join(REPO_ROOT, "Strategy1"),
]
LEADERBOARD_PATH = os.path.join(REPO_ROOT, "LEADERBOARD.md")
STOCKFISH_DIR = os.path.join(SCRIPT_DIR, "stockfish_bin")
STOCKFISH_PATH = os.path.join(STOCKFISH_DIR, "stockfish")

# Pro-Level Calibration Settings (The Curve)
ANCHORS = {
    1: 1000.0,
    3: 1200.0,
    5: 1500.0
}

def ensure_stockfish():
    """Detects or installs Stockfish."""
    which_sf = shutil.which("stockfish")
    if which_sf: return which_sf
    if os.path.exists(STOCKFISH_PATH): return STOCKFISH_PATH

    print("Stockfish not found. Attempting to install...")
    system = platform.system().lower()
    try:
        if system == "darwin":
            subprocess.run(["brew", "install", "stockfish"], check=True)
            which_sf = shutil.which("stockfish")
            if which_sf: return which_sf
    except Exception as e:
        print(f"Auto-install failed: {e}")

    print("Please install stockfish manually and ensure it is on your PATH.")
    sys.exit(1)

class StockfishWrapper:
    def __init__(self, skill_level, path):
        self.skill_level = skill_level
        self.path = path
        self.name = f"stockfish-skill-{skill_level}"
        self.temp_dir = os.path.join(REPO_ROOT, ".tmp_stockfish", self.name)
        os.makedirs(self.temp_dir, exist_ok=True)
        self.run_sh = os.path.join(self.temp_dir, "run.sh")
        
        with open(self.run_sh, "w") as f:
            f.write(f"#!/bin/bash\n")
            f.write(f"python3 -c \"\n")
            f.write(f"import sys, subprocess, threading\n")
            f.write(f"p = subprocess.Popen(['{self.path}'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)\n")
            f.write(f"def relay(src, dst, inject=None):\n")
            f.write(f"    try:\n")
            f.write(f"        for line in src:\n")
            f.write(f"            dst.write(line); dst.flush()\n")
            f.write(f"            if inject and line.strip() == 'uci':\n")
            f.write(f"                dst.write(inject); dst.flush()\n")
            f.write(f"    except: pass\n")
            f.write(f"threading.Thread(target=relay, args=(sys.stdin, p.stdin, 'setoption name Skill Level value {skill_level}\\n'), daemon=True).start()\n")
            f.write(f"relay(p.stdout, sys.stdout)\n")
            f.write(f"\"\n")
        os.chmod(self.run_sh, 0o755)

def discover_methodologies():
    """Scan ENGINE_ROOTS (containers) + DIRECT_ENGINES (single engines).

    ENGINE_ROOTS are directories that contain multiple engine folders; we
    look for ``<root>/<name>/engine/run.sh`` and register the engine
    under ``<name>``.

    DIRECT_ENGINES are directories that are themselves an engine; we look
    for ``<dir>/engine/run.sh`` and register under ``basename(<dir>)``.

    First hit wins, so SRC_DIR / ttt-iteration_bot take precedence over
    DIRECT_ENGINES if a name collision ever happens.
    """
    methods = {}
    for root in ENGINE_ROOTS:
        if not os.path.exists(root):
            continue
        for name in os.listdir(root):
            if name.startswith("_") or name.startswith("."):
                continue
            run_sh = os.path.join(root, name, "engine", "run.sh")
            if os.path.exists(run_sh) and name not in methods:
                methods[name] = run_sh
    for engine_dir in DIRECT_ENGINES:
        if not os.path.exists(engine_dir):
            continue
        run_sh = os.path.join(engine_dir, "engine", "run.sh")
        if os.path.exists(run_sh):
            name = os.path.basename(engine_dir.rstrip(os.sep))
            if name not in methods:
                methods[name] = run_sh
    return methods


def results_path_for(run_sh_path):
    """Return the results.json path next to the engine this run.sh belongs to.

    ``run.sh`` lives at ``<root>/<name>/engine/run.sh``; results.json sits
    at ``<root>/<name>/results.json`` regardless of which root contributed
    the engine.
    """
    engine_dir = os.path.dirname(os.path.dirname(run_sh_path))
    return os.path.join(engine_dir, "results.json")

def fishtest_stats(w, l, d):
    """Calculates relative Elo and Standard Error using trinomial logic."""
    n = w + l + d
    if n == 0: return 0, 1000.0 # Infinite error for 0 games
    
    score = (w + 0.5 * d) / n
    score = max(0.0001, min(0.9999, score))
    mu = score
    var = max((w/n * (1-mu)**2 + d/n * (0.5-mu)**2 + l/n * (0-mu)**2), 1e-6)
    se_score = math.sqrt(var / n)
    
    def score_to_elo(s):
        return -400 * math.log10(1/s - 1)
    
    elo = score_to_elo(mu)
    derivative = 400 / (math.log(10) * mu * (1 - mu))
    se_elo = se_score * derivative
    
    return elo, se_elo

def run_matchup(name_a, path_a, name_b, path_b, games, movetime):
    """Run an arena matchup and return per-game outcomes from A's perspective.

    Arena prints two kinds of lines we care about:
      - Per-game: ``  Game N/M: [W|B|D] <pgn result>`` where the letter is
        the winner's color (W, B, or D for draw).
      - Final:    ``Final: {W}W-{L}L-{D}D`` with totals already reduced to
        A's perspective (arena tracks color alternation internally).

    We track color-alternation here too (odd games => A is white) to convert
    each per-game letter into an A-perspective outcome, but we also fall back
    to the Final line if parsing diverges. Returns a list of floats
    (1.0 win, 0.0 loss, 0.5 draw) for A.
    """
    print(f"\n>>> Matchup: {name_a} vs {name_b} ({games} games)", flush=True)
    # Use the same interpreter as the parent (e.g. .venv/bin/python) so
    # arena.py's `import chess` doesn't break if system python3 lacks it.
    cmd = [sys.executable, "-u", os.path.join(SCRIPT_DIR, "arena.py"),
           "--engine-a", path_a, "--engine-b", path_b,
           "--games", str(games), "--movetime", str(movetime)]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, bufsize=1)

    game_outcomes = []
    final_w = final_l = final_d = None
    import re
    game_re = re.compile(r"Game\s+(\d+)/\d+:\s*\[([WBD])\]")
    final_re = re.compile(r"Final:\s*(\d+)W-(\d+)L-(\d+)D")

    for line in process.stdout:
        print(line, end="", flush=True)
        m = game_re.search(line)
        if m:
            game_num = int(m.group(1))
            winner = m.group(2)
            a_is_white = (game_num % 2 == 1)
            if winner == "D":
                game_outcomes.append(0.5)
            elif (winner == "W" and a_is_white) or (winner == "B" and not a_is_white):
                game_outcomes.append(1.0)
            else:
                game_outcomes.append(0.0)
            continue
        fm = final_re.search(line)
        if fm:
            final_w, final_l, final_d = (int(x) for x in fm.groups())
    process.wait()

    # Prefer the Final: totals if both are present and they disagree, or
    # reconstruct from Final: if per-game parsing missed anything.
    if final_w is not None and final_l is not None and final_d is not None:
        reconstructed = [1.0] * final_w + [0.0] * final_l + [0.5] * final_d
        if len(reconstructed) != len(game_outcomes) or (
            reconstructed.count(1.0) != game_outcomes.count(1.0)
            or reconstructed.count(0.0) != game_outcomes.count(0.0)
            or reconstructed.count(0.5) != game_outcomes.count(0.5)
        ):
            return reconstructed
    return game_outcomes

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=60, help="Games per matchup")
    parser.add_argument("--movetime", type=int, default=100)
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--cross-validate", action="store_true", help="Test engines against each other")
    parser.add_argument(
        "--only",
        default=None,
        help="Comma-separated list of engine names to restrict the run to. "
             "If omitted, every discovered engine participates.",
    )
    args = parser.parse_args()

    sf_path = ensure_stockfish()
    methods = discover_methodologies()

    if args.only:
        wanted = {n.strip() for n in args.only.split(",") if n.strip()}
        unknown = wanted - set(methods.keys())
        if unknown:
            print(f"Warning: --only listed unknown engines: {sorted(unknown)}")
            print(f"Discovered engines: {sorted(methods.keys())}")
        methods = {n: p for n, p in methods.items() if n in wanted}

    method_names = list(methods.keys())

    if not methods:
        print("No engines found in src/. Add your methodology folder with an 'engine/run.sh' to start.")
        return
    print(f"Engines selected for this run: {method_names}")

    # Load all existing data
    all_data = {}
    for name in method_names:
        rp = results_path_for(methods[name])
        all_data[name] = {"name": name, "anchors": {}, "cross_validation": {}}
        if os.path.exists(rp):
            with open(rp, "r") as f:
                try: all_data[name].update(json.load(f))
                except: pass

    if not args.report:
        if args.cross_validate:
            # Engine vs Engine Mode
            for i, name_a in enumerate(method_names):
                for name_b in method_names[i+1:]:
                    if name_b not in all_data[name_a]["cross_validation"]:
                        outcomes = run_matchup(name_a, methods[name_a], name_b, methods[name_b], args.games, args.movetime)
                        if outcomes:
                            # Perspective of A
                            w = outcomes.count(1.0)
                            l = outcomes.count(0.0)
                            d = outcomes.count(0.5)
                            all_data[name_a]["cross_validation"][name_b] = {"wins": w, "losses": l, "draws": d, "total": len(outcomes)}
                            # Perspective of B
                            all_data[name_b]["cross_validation"][name_a] = {"wins": l, "losses": w, "draws": d, "total": len(outcomes)}
                            
                            for n in [name_a, name_b]:
                                with open(results_path_for(methods[n]), "w") as f:
                                    json.dump(all_data[n], f, indent=2)
        else:
            # Stockfish Calibration Mode (Default)
            games_per_anchor = max(2, args.games // len(ANCHORS))
            if games_per_anchor % 2 != 0: games_per_anchor += 1

            for name in method_names:
                for skill, base_elo in ANCHORS.items():
                    anchor_key = f"skill_{skill}"
                    if anchor_key not in all_data[name]["anchors"]:
                        anchor = StockfishWrapper(skill, sf_path)
                        outcomes = run_matchup(name, methods[name], anchor.name, anchor.run_sh, games_per_anchor, args.movetime)
                        if outcomes:
                            all_data[name]["anchors"][anchor_key] = {
                                "wins": outcomes.count(1.0),
                                "losses": outcomes.count(0.0),
                                "draws": outcomes.count(0.5),
                                "total": len(outcomes),
                                "base_elo": base_elo
                            }
                            # Persist immediately so an interrupted run never
                            # loses more than the games for a single anchor.
                            # We only have partial anchor data here, so we
                            # skip the Elo computation until all anchors
                            # have been collected (or re-done on resume).
                            with open(results_path_for(methods[name]), "w") as f:
                                json.dump(all_data[name], f, indent=2)

                # Recompute Absolute Elo
                if all_data[name]["anchors"]:
                    estimates, variances = [], []
                    for anchor_key, m in all_data[name]["anchors"].items():
                        rel_elo, se_elo = fishtest_stats(m["wins"], m["losses"], m["draws"])
                        estimates.append(m["base_elo"] + rel_elo)
                        variances.append(se_elo**2)
                    
                    weights = [1/v for v in variances]
                    total_weight = sum(weights)
                    combined_elo = sum(e * w for e, w in zip(estimates, weights)) / total_weight
                    combined_se = 1 / math.sqrt(total_weight)
                    
                    all_data[name].update({
                        "elo": combined_elo,
                        "elo_ci_lower": combined_elo - 1.96 * combined_se,
                        "elo_ci_upper": combined_elo + 1.96 * combined_se,
                        "graded_at": datetime.now().isoformat()
                    })
                    with open(results_path_for(methods[name]), "w") as f:
                        json.dump(all_data[name], f, indent=2)

    # Reporting
    if args.cross_validate:
        print(f"\nCross-Validation Matrix (Engine vs Engine Outcomes)")
        print(f"{'Name':<18} | " + " | ".join(f"{n[:8]:<8}" for n in method_names))
        print("-" * (21 + 11 * len(method_names)))
        for name_a in method_names:
            row = f"{name_a[:18]:<18} | "
            for name_b in method_names:
                if name_a == name_b: row += f"{'-':^8} | "
                elif name_b in all_data[name_a]["cross_validation"]:
                    m = all_data[name_a]["cross_validation"][name_b]
                    row += f"{m['wins']}-{m['losses']}-{m['draws']}^8 | ".replace("^8", "").ljust(8) + " | "
                else: row += f"{'?':^8} | "
            print(row)
    else:
        print(f"\nEngine Performance (Absolute Calibration Curve)")
        print(f"{'Name':<18} {'Elo':<6} {'95% CI':<14}")
        print("-" * 40)
        sorted_res = sorted([d for d in all_data.values() if "elo" in d], key=lambda x: x['elo'], reverse=True)
        for d in sorted_res:
            print(f"{d['name']:<18} {d.get('elo', 0):.0f} [{d.get('elo_ci_lower', 0):.0f}, {d.get('elo_ci_upper', 0):.0f}]")

if __name__ == "__main__":
    main()
