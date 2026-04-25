import chess
import sys

# Material weights
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

def evaluate(board):
    if board.is_checkmate():
        # The side to move is in checkmate, so it's a loss for them
        return -30000
    if board.is_stalemate() or board.is_insufficient_material() or board.is_fivefold_repetition():
        return 0

    score = 0
    # Material score
    for piece_type in PIECE_VALUES:
        score += len(board.pieces(piece_type, chess.WHITE)) * PIECE_VALUES[piece_type]
        score -= len(board.pieces(piece_type, chess.BLACK)) * PIECE_VALUES[piece_type]

    # Mobility score
    # We'll compute it from white's perspective first
    white_mobility = 0
    black_mobility = 0
    
    current_turn = board.turn
    
    board.turn = chess.WHITE
    white_mobility = board.legal_moves.count()
    
    board.turn = chess.BLACK
    black_mobility = board.legal_moves.count()
    
    board.turn = current_turn
    
    score += 10 * (white_mobility - black_mobility)

    # Return score relative to the side whose turn it is
    return score if board.turn == chess.WHITE else -score

def negamax(board, depth, alpha, beta):
    if depth == 0 or board.is_game_over():
        return evaluate(board)

    max_score = -float('inf')
    for move in board.legal_moves:
        board.push(move)
        score = -negamax(board, depth - 1, -beta, -alpha)
        board.pop()
        
        max_score = max(max_score, score)
        alpha = max(alpha, score)
        if alpha >= beta:
            break
    return max_score

def search(board, depth):
    best_move = None
    max_score = -float('inf')
    alpha = -float('inf')
    beta = float('inf')

    for move in board.legal_moves:
        board.push(move)
        score = -negamax(board, depth - 1, -beta, -alpha)
        board.pop()
        
        if score > max_score:
            max_score = score
            best_move = move
        
        alpha = max(alpha, score)
    
    return best_move

class Engine:
    def __init__(self):
        self.board = chess.Board()

    def handle_command(self, command):
        parts = command.strip().split()
        if not parts:
            return ""
        
        cmd = parts[0]
        
        if cmd == "uci":
            return "id name TDD_Engine\nid author GeminiCLI\nuciok"
        elif cmd == "isready":
            return "readyok"
        elif cmd == "ucinewgame":
            self.board = chess.Board()
            return ""
        elif cmd == "position":
            if "startpos" in parts:
                self.board = chess.Board()
                if "moves" in parts:
                    moves_idx = parts.index("moves")
                    for move_uci in parts[moves_idx+1:]:
                        self.board.push_uci(move_uci)
            elif "fen" in parts:
                fen_idx = parts.index("fen")
                fen = " ".join(parts[fen_idx+1:fen_idx+7])
                self.board = chess.Board(fen)
                if "moves" in parts:
                    moves_idx = parts.index("moves")
                    for move_uci in parts[moves_idx+1:]:
                        self.board.push_uci(move_uci)
            return ""
        elif cmd == "go":
            # Default depth 3 as per requirements
            move = search(self.board, depth=3)
            if move:
                return f"bestmove {move.uci()}"
            return "bestmove 0000"
        elif cmd == "quit":
            sys.exit(0)
        
        return ""

def main():
    engine = Engine()
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        response = engine.handle_command(line)
        if response:
            print(response)
            sys.stdout.flush()

if __name__ == "__main__":
    main()
