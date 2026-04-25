import chess
import sys
import random
import time

# Piece values for material evaluation
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

nodes_searched = 0

def evaluate_board(board):
    if board.is_checkmate():
        # If the side whose turn it is is in checkmate, they lose.
        return -30000
    if board.is_stalemate() or board.is_insufficient_material() or board.is_seventyfive_moves() or board.is_fivefold_repetition():
        return 0
    
    score = 0
    for piece_type, value in PIECE_VALUES.items():
        score += len(board.pieces(piece_type, board.turn)) * value
        score -= len(board.pieces(piece_type, not board.turn)) * value
    
    return score

def negamax(board, depth, alpha, beta):
    global nodes_searched
    nodes_searched += 1
    
    if depth == 0 or board.is_game_over():
        return evaluate_board(board)
    
    max_eval = -float('inf')
    # Simple move ordering: captures first
    moves = sorted(board.legal_moves, key=lambda m: board.is_capture(m), reverse=True)
    
    for move in moves:
        board.push(move)
        eval = -negamax(board, depth - 1, -beta, -alpha)
        board.pop()
        
        max_eval = max(max_eval, eval)
        alpha = max(alpha, eval)
        if alpha >= beta:
            break
            
    return max_eval

def main():
    global nodes_searched
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
            print("id name ToyToScale-Final")
            print("id author GeminiCLI")
            print("uciok")
            sys.stdout.flush()
        elif command == "isready":
            print("readyok")
            sys.stdout.flush()
        elif command == "ucinewgame":
            board = chess.Board()
        elif command == "position":
            if len(parts) > 1 and parts[1] == "startpos":
                board = chess.Board()
                if "moves" in parts:
                    move_index = parts.index("moves")
                    for move in parts[move_index+1:]:
                        board.push_uci(move)
            elif len(parts) > 1 and parts[1] == "fen":
                fen_parts = []
                for p in parts[2:]:
                    if p == "moves":
                        break
                    fen_parts.append(p)
                board = chess.Board(" ".join(fen_parts))
                if "moves" in parts:
                    move_index = parts.index("moves")
                    for move in parts[move_index+1:]:
                        board.push_uci(move)
        elif command == "go":
            depth = 3
            best_move = None
            max_eval = -float('inf')
            alpha = -float('inf')
            beta = float('inf')
            
            nodes_searched = 0
            start_time = time.time()
            
            moves = list(board.legal_moves)
            # Shuffle to avoid deterministic behavior among equal moves
            random.shuffle(moves)
            # Order captures first
            moves.sort(key=lambda m: board.is_capture(m), reverse=True)
            
            for move in moves:
                board.push(move)
                eval = -negamax(board, depth - 1, -beta, -alpha)
                board.pop()
                
                if eval > max_eval:
                    max_eval = eval
                    best_move = move
                
                alpha = max(alpha, eval)
            
            end_time = time.time()
            duration = end_time - start_time
            nps = int(nodes_searched / duration) if duration > 0 else 0
            
            if best_move:
                print(f"info depth {depth} nodes {nodes_searched} nps {nps} score cp {max_eval}")
                print(f"bestmove {best_move.uci()}")
            else:
                print("bestmove 0000")
            sys.stdout.flush()
        elif command == "quit":
            break

if __name__ == "__main__":
    main()
