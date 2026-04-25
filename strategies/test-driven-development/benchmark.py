import chess
import time
import argparse
from bot.random_bot import RandomBot
from bot.engine_bot import EngineBot


def play_game(white_bot, black_bot, max_moves: int = 200) -> str:
    """Play a game to completion. Returns 'white', 'black', or 'draw'."""
    board = chess.Board()
    for _ in range(max_moves):
        if board.is_game_over():
            break
        bot = white_bot if board.turn == chess.WHITE else black_bot
        board.push(bot.choose_move(board))

    if board.is_checkmate():
        return "black" if board.turn == chess.WHITE else "white"
    return "draw"


def run_benchmark(games: int = 20, depth: int = 2) -> None:
    engine = EngineBot(depth=depth)
    random_bot = RandomBot()

    wins = losses = draws = 0

    print(f"Benchmarking engine (depth={depth}) vs random bot over {games} games...\n")
    start = time.time()

    for i in range(games):
        if i % 2 == 0:
            result = play_game(engine, random_bot)
            if result == "white":
                wins += 1
            elif result == "black":
                losses += 1
            else:
                draws += 1
        else:
            result = play_game(random_bot, engine)
            if result == "black":
                wins += 1
            elif result == "white":
                losses += 1
            else:
                draws += 1

        color = "W" if i % 2 == 0 else "B"
        print(f"  Game {i+1:>3}/{games} (engine={color}): {result}")

    elapsed = time.time() - start
    win_rate = (wins + 0.5 * draws) / games * 100

    print(f"\n{'='*40}")
    print(f"Results ({elapsed:.1f}s total, {elapsed/games:.1f}s/game)")
    print(f"  Wins:   {wins}")
    print(f"  Losses: {losses}")
    print(f"  Draws:  {draws}")
    print(f"  Score:  {win_rate:.1f}%")
    print(f"{'='*40}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark engine vs random bot")
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--depth", type=int, default=2)
    args = parser.parse_args()
    run_benchmark(args.games, args.depth)
