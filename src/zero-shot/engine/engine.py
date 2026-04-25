import sys
import chess
import time

# Material weights as specified
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

def evaluate_board(board):
    """
    Simple material evaluation.
    Positive for the side to move, negative for the opponent.
    """
    if board.is_checkmate():
        return -30000
    if board.is_stalemate() or board.is_insufficient_material() or board.is_seventyfive_moves() or board.is_fivefold_repetition():
        return 0

    score = 0
    for pt in PIECE_VALUES:
        score += len(board.pieces(pt, chess.WHITE)) * PIECE_VALUES[pt]
        score -= len(board.pieces(pt, chess.BLACK)) * PIECE_VALUES[pt]
    
    return score if board.turn == chess.WHITE else -score

def negamax(board, depth, alpha, beta):
    if depth == 0 or board.is_game_over():
        return evaluate_board(board)

    max_val = -float('inf')
    for move in board.legal_moves:
        board.push(move)
        val = -negamax(board, depth - 1, -beta, -alpha)
        board.pop()
        if val > max_val:
            max_val = val
        alpha = max(alpha, val)
        if alpha >= beta:
            break
    return max_val

def get_best_move(board, depth=3):
    best_move = None
    max_val = -float('inf')
    alpha = -float('inf')
    beta = float('inf')

    # Sort moves slightly? For zero-shot, let's keep it simple.
    for move in board.legal_moves:
        board.push(move)
        val = -negamax(board, depth - 1, -beta, -alpha)
        board.pop()
        if val > max_val:
            max_val = val
            best_move = move
        alpha = max(alpha, val)
    
    return best_move

def main():
    board = chess.Board()
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        
        parts = line.strip().split()
        if not parts:
            continue
            
        command = parts[0]
        
        if command == "uci":
            print("id name ZeroShotEngine")
            print("id author GeminiCLI")
            print("uciok")
            sys.stdout.flush()
        elif command == "isready":
            print("readyok")
            sys.stdout.flush()
        elif command == "ucinewgame":
            board = chess.Board()
        elif command == "position":
            if "startpos" in parts:
                board = chess.Board()
                if "moves" in parts:
                    move_index = parts.index("moves") + 1
                    for move_str in parts[move_index:]:
                        board.push_uci(move_str)
            elif "fen" in parts:
                fen_index = parts.index("fen")
                fen_str = " ".join(parts[fen_index+1 : fen_index+7])
                board = chess.Board(fen_str)
                if "moves" in parts:
                    move_index = parts.index("moves") + 1
                    for move_str in parts[move_index:]:
                        board.push_uci(move_str)
        elif command == "go":
            # Simple fixed depth 3 as per constraints
            move = get_best_move(board, depth=3)
            if move:
                print(f"bestmove {move.uci()}")
            else:
                # Should not happen if game is not over
                legal_moves = list(board.legal_moves)
                if legal_moves:
                    print(f"bestmove {legal_moves[0].uci()}")
            sys.stdout.flush()
        elif command == "quit":
            break

if __name__ == "__main__":
    main()
