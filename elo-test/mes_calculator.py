import os
import yaml
import json
import math

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")

# WEIGHTS
W_SF = 0.40       # Increased weight for absolute quality
W_H2H = 0.30      # Significant weight for direct combat
W_EFFICIENCY = 0.30 # Elo per 10k tokens

TARGET_ELO = 1200.0

def main():
    print("\n" + "="*75)
    print(" ALPHA METHODOLOGY EFFICACY SCORE (AMES) - TOKEN EFFICIENCY MODEL")
    print("="*75 + "\n")
    
    results = []

    if not os.path.exists(SRC_DIR): return

    for folder in os.listdir(SRC_DIR):
        discovery_path = os.path.join(SRC_DIR, folder, "DISCOVERY.md")
        results_path = os.path.join(SRC_DIR, folder, "results.json")
        
        if os.path.exists(discovery_path) and os.path.exists(results_path):
            try:
                # 1. Load Match Results
                with open(results_path, "r") as f:
                    res_data = json.load(f)
                
                # 2. Load Discovery Metrics
                with open(discovery_path, "r") as f:
                    content = f.read()
                    yaml_block = content.split("---")[1].replace("```yaml", "").replace("```", "").strip()
                    disc = yaml.safe_load(yaml_block)

                # --- FACTOR 1: Absolute Alpha (Stockfish Elo) ---
                elo = float(res_data.get("elo", 0))
                c1 = min(100, max(0, (elo / TARGET_ELO) * 100))
                
                # --- FACTOR 2: Relative Alpha (Head-to-Head) ---
                cv = res_data.get("cross_validation", {})
                total_games = sum(m["total"] for m in cv.values())
                total_wins = sum(m["wins"] + 0.5 * m["draws"] for m in cv.values())
                win_rate = total_wins / total_games if total_games > 0 else 0.5
                c2 = win_rate * 100.0
                
                # --- FACTOR 3: Token Efficiency (Elo per 10k Tokens) ---
                tokens = int(disc.get("Total_Tokens_Used", 1000))
                # Efficiency = (Base Elo + 1000) / (Tokens / 10000)
                # We use a baseline of 1000 to reward engines that actually function
                efficiency = (max(0, elo + 1000)) / (tokens / 1000.0)
                c3 = min(100, (efficiency / 500.0) * 100) # Norm: 500 Elo/1k tokens is "Perfect"
                
                # AMES Final
                ames = (W_SF * c1) + (W_H2H * c2) + (W_EFFICIENCY * c3)
                
                results.append({
                    "name": folder,
                    "ames": ames,
                    "sf_elo": elo,
                    "h2h_wr": win_rate,
                    "tokens": tokens,
                    "efficiency": efficiency
                })
            except Exception as e:
                print(f"Error evaluating {folder}: {e}")

    results.sort(key=lambda x: x["ames"], reverse=True)
    
    print(f"{'Rank':<4} {'Methodology':<20} {'AMES':<10} {'SF Elo':<8} {'H2H WR':<8} {'Tokens'}")
    print("-" * 75)
    for i, res in enumerate(results):
        print(f"{i+1:<4} {res['name']:<20} {res['ames']:<10.2f} {res['sf_elo']:<8.0f} {res['h2h_wr']:<8.1%} {res['tokens']:,}")

    print("\n[DECISION]:")
    if results:
        print(f"WINNING METHODOLOGY: {results[0]['name'].upper()}")
    print("="*75 + "\n")

if __name__ == "__main__":
    main()
