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
STOCKFISH_DIR = os.path.join(SCRIPT_DIR, "stockfish_bin")
STOCKFISH_PATH = os.path.join(STOCKFISH_DIR, "stockfish")

# Stockfish Calibration Settings
STOCKFISH_ANCHOR_ELO = 1000.0  # Assumed Elo for Skill Level 1
STOCKFISH_SKILL_LEVEL = 1

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

def fishtest_elo(w, l, d):
    """Calculates Elo and 95% CI using Fishtest trinomial logic."""
    n = w + l + d
    if n == 0: return 0, -1000, 1000
    
    score = (w + 0.5 * d) / n
    score = max(0.0001, min(0.9999, score))
    mu = score
    var = max((w/n * (1-mu)**2 + d/n * (0.5-mu)**2 + l/n * (0-mu)**2), 1e-6)
    se = math.sqrt(var / n)
    
    score_low = max(0.0001, mu - 1.96 * se)
    score_high = min(0.9999, mu + 1.96 * se)
    
    def score_to_elo(s):
        return -400 * math.log10(1/s - 1)
    
    return score_to_elo(mu), score_to_elo(score_low), score_to_elo(score_high)

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
    parser.add_argument("--games", type=int, default=50)
    parser.add_argument("--movetime", type=int, default=100)
    args = parser.parse_args()

    sf_path = ensure_stockfish()
    anchor = StockfishWrapper(STOCKFISH_SKILL_LEVEL, sf_path)
    methods = discover_methodologies()
    
    if not methods:
        print("No engines found in src/. Add your methodology folder with an 'engine/run.sh' to start.")
        return

    print(f"\nEngine Benchmarking (Anchor: Stockfish Skill {STOCKFISH_SKILL_LEVEL} = {STOCKFISH_ANCHOR_ELO} Elo)")
    print(f"{'Name':<18} {'Elo':<6} {'95% CI':<14}")
    print("-" * 40)

    for name in methods:
        results_path = os.path.join(SRC_DIR, name, "results.json")
        data = {"name": name, "matchups": {}}
        if os.path.exists(results_path):
            with open(results_path, "r") as f:
                try: data.update(json.load(f))
                except: pass

        if "stockfish_anchor" not in data["matchups"]:
            outcomes = run_matchup(name, methods[name], anchor.name, anchor.run_sh, args.games, args.movetime)
            if outcomes:
                data["matchups"]["stockfish_anchor"] = {"wins": outcomes.count(1.0), "losses": outcomes.count(0.0), "draws": outcomes.count(0.5), "total": len(outcomes)}
        
        if "stockfish_anchor" in data["matchups"]:
            m = data["matchups"]["stockfish_anchor"]
            elo, low, high = fishtest_elo(m["wins"], m["losses"], m["draws"])
            data.update({"elo": STOCKFISH_ANCHOR_ELO + elo, "elo_ci_lower": STOCKFISH_ANCHOR_ELO + low, "elo_ci_upper": STOCKFISH_ANCHOR_ELO + high, "graded_at": datetime.now().isoformat()})
            with open(results_path, "w") as f: json.dump(data, f, indent=2)
            
            print(f"{name:<18} {data.get('elo', 0):.0f} [{data.get('elo_ci_lower', 0):.0f}, {data.get('elo_ci_upper', 0):.0f}]")

if __name__ == "__main__":
    main()
