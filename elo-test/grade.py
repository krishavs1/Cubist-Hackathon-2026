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
    methods = {}
    if os.path.exists(SRC_DIR):
        for name in os.listdir(SRC_DIR):
            if name.startswith("_"): continue
            run_sh = os.path.join(SRC_DIR, name, "engine", "run.sh")
            if os.path.exists(run_sh):
                methods[name] = run_sh
    return methods

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
    print(f"\n>>> Matchup: {name_a} vs {name_b} ({games} games)")
    cmd = ["python3", os.path.join(SCRIPT_DIR, "arena.py"), "--engine-a", path_a, "--engine-b", path_b, "--games", str(games), "--movetime", str(movetime)]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    game_outcomes = []
    for line in process.stdout:
        print(line, end="")
        if "Game" in line and "[" in line and "]" in line:
            if "[+]" in line: game_outcomes.append(1.0)
            elif "[-]" in line: game_outcomes.append(0.0)
            elif "[=]" in line: game_outcomes.append(0.5)
    process.wait()
    return game_outcomes

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=60, help="Games per matchup")
    parser.add_argument("--movetime", type=int, default=100)
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--cross-validate", action="store_true", help="Test engines against each other")
    args = parser.parse_args()

    sf_path = ensure_stockfish()
    methods = discover_methodologies()
    method_names = list(methods.keys())
    
    if not methods:
        print("No engines found in src/. Add your methodology folder with an 'engine/run.sh' to start.")
        return

    # Load all existing data
    all_data = {}
    for name in method_names:
        rp = os.path.join(SRC_DIR, name, "results.json")
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
                                with open(os.path.join(SRC_DIR, n, "results.json"), "w") as f:
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
                    with open(os.path.join(SRC_DIR, name, "results.json"), "w") as f:
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
