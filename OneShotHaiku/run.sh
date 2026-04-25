#!/bin/bash
# OneShot Chess Engine Launcher Script

set -e

echo "OneShot Chess Engine Launcher"
echo "=============================="
echo ""

# Check if python-chess is installed
if ! python3 -c "import chess" 2>/dev/null; then
    echo "Installing required dependencies..."
    pip install -r requirements.txt
fi

echo "Options:"
echo "1. Run UCI Engine (for chess GUIs)"
echo "2. Interactive Mode (play against engine)"
echo "3. Run Tests"
echo "4. Quick Benchmark"
echo ""

read -p "Select option (1-4) [1]: " option
option=${option:-1}

case $option in
    1)
        echo "Starting UCI Engine..."
        echo "Connect your chess GUI and send UCI commands"
        echo ""
        python3 chess_engine.py
        ;;
    2)
        echo "Starting Interactive Mode..."
        python3 interactive.py
        ;;
    3)
        echo "Running Test Suite..."
        python3 test_engine.py
        ;;
    4)
        echo "Running Quick Benchmark..."
        python3 << 'EOF'
import chess
import time
from evaluation import evaluate
from search import find_best_move, clear_transposition_table

positions = [
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
    "rnbqkbnr/pp1ppppp/8/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 3",
]

print("\nBenchmark (Depth 4):")
print("-" * 50)
total = 0
for i, fen in enumerate(positions, 1):
    board = chess.Board(fen)
    clear_transposition_table()

    start = time.time()
    move = find_best_move(board, 4)
    elapsed = time.time() - start
    total += elapsed

    score = evaluate(board)
    print(f"Position {i}: {move} (eval: {score:+.0f}) - {elapsed:.2f}s")

print("-" * 50)
print(f"Average time per position: {total/len(positions):.2f}s")
EOF
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac
