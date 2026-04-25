import sys
import chess
import time

# Piece-Square Tables
# Values are from the perspective of White. For Black, they are mirrored.
PST = {
    chess.PAWN: [
        0,  0,  0,  0,  0,  0,  0,  0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
        5,  5, 10, 25, 25, 10,  5,  5,
        0,  0,  0, 20, 20,  0,  0,  0,
        5, -5,-10,  0,  0,-10, -5,  5,
        5, 10, 10,-20,-20, 10, 10,  5,
        0,  0,  0,  0,  0,  0,  0,  0
    ],
    chess.KNIGHT: [
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50
    ],
    chess.BISHOP: [
        -20,-10,-10,-10,-10,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5, 10, 10,  5,  0,-10,
        -10,  5,  5, 10, 10,  5,  5,-10,
        -10,  0, 10, 10, 10, 10,  0,-10,
        -10, 10, 10, 10, 10, 10, 10,-10,
        -10,  5,  0,  0,  0,  0,  5,-10,
        -20,-10,-10,-10,-10,-10,-10,-20
    ],
    chess.ROOK: [
        0,  0,  0,  0,  0,  0,  0,  0,
        5, 10, 10, 10, 10, 10, 10,  5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        0,  0,  0,  5,  5,  0,  0,  0
    ],
    chess.QUEEN: [
        -20,-10,-10, -5, -5,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5,  5,  5,  5,  0,-10,
        -5,  0,  5,  5,  5,  5,  0, -5,
        0,  0,  5,  5,  5,  5,  0, -5,
        -10,  5,  5,  5,  5,  5,  0,-10,
        -10,  0,  5,  0,  0,  0,  0,-10,
        -20,-10,-10, -5, -5,-10,-10,-20
    ],
    chess.KING: [
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -20,-30,-30,-40,-40,-30,-30,-20,
        -10,-20,-20,-20,-20,-20,-20,-10,
        20, 20,  0,  0,  0,  0, 20, 20,
        20, 30, 10,  0,  0, 10, 30, 20
    ]
}

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

nodes = 0

def evaluate_board(board):
    if board.is_checkmate():
        if board.turn:
            return -99999
        else:
            return 99999
    if board.is_stalemate() or board.is_insufficient_material() or board.is_seventyfive_moves() or board.is_fivefold_repetition():
        return 0

    score = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            val = PIECE_VALUES[piece.piece_type]
            pst_val = PST[piece.piece_type][square if piece.color == chess.WHITE else chess.square_mirror(square)]
            if piece.color == chess.WHITE:
                score += val + pst_val
            else:
                score -= val + pst_val
    
    return score if board.turn == chess.WHITE else -score

def move_ordering(board, move):
    # Basic move ordering: Captures first
    if board.is_capture(move):
        return 10
    return 0

def quiescence_search(board, alpha, beta):
    global nodes
    nodes += 1
    stand_pat = evaluate_board(board)
    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat

    moves = [move for move in board.legal_moves if board.is_capture(move)]
    moves.sort(key=lambda m: move_ordering(board, m), reverse=True)

    for move in moves:
        board.push(move)
        score = -quiescence_search(board, -beta, -alpha)
        board.pop()

        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
    return alpha

def negamax(board, depth, alpha, beta):
    global nodes
    nodes += 1
    if depth == 0:
        return quiescence_search(board, alpha, beta)

    if board.is_game_over():
        return evaluate_board(board)

    best_score = -999999
    moves = list(board.legal_moves)
    moves.sort(key=lambda m: move_ordering(board, m), reverse=True)

    for move in moves:
        board.push(move)
        score = -negamax(board, depth - 1, -beta, -alpha)
        board.pop()

        if score >= beta:
            return beta
        if score > best_score:
            best_score = score
        if score > alpha:
            alpha = score
    return best_score

class Engine:
    def __init__(self):
        self.board = chess.Board()

    def uci_loop(self):
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            cmd = line.strip().split()
            if not cmd:
                continue

            if cmd[0] == "uci":
                print("id name MegapromptEngine")
                print("id author GeminiCLI")
                print("uciok")
            elif cmd[0] == "isready":
                print("readyok")
            elif cmd[0] == "ucinewgame":
                self.board = chess.Board()
            elif cmd[0] == "position":
                if len(cmd) > 1 and cmd[1] == "startpos":
                    self.board = chess.Board()
                    if "moves" in cmd:
                        moves_idx = cmd.index("moves")
                        for move_str in cmd[moves_idx+1:]:
                            self.board.push_uci(move_str)
                elif len(cmd) > 1 and cmd[1] == "fen":
                    fen = " ".join(cmd[2:8])
                    self.board = chess.Board(fen)
                    if "moves" in cmd:
                        moves_idx = cmd.index("moves")
                        for move_str in cmd[moves_idx+1:]:
                            self.board.push_uci(move_str)
            elif cmd[0] == "go":
                self.search(cmd)
            elif cmd[0] == "quit":
                break

    def search(self, cmd):
        global nodes
        nodes = 0
        start_time = time.time()
        best_move = None
        best_score = -999999
        
        depth = 3
        # Simple depth handling
        if "depth" in cmd:
            depth = int(cmd[cmd.index("depth") + 1])

        moves = list(self.board.legal_moves)
        moves.sort(key=lambda m: move_ordering(self.board, m), reverse=True)

        alpha = -999999
        beta = 999999

        for move in moves:
            self.board.push(move)
            score = -negamax(self.board, depth - 1, -beta, -alpha)
            self.board.pop()
            if score > best_score:
                best_score = score
                best_move = move
            if score > alpha:
                alpha = score

        elapsed = time.time() - start_time
        nps = int(nodes / elapsed) if elapsed > 0 else 0
        
        if best_move:
            print(f"info depth {depth} score cp {best_score} nodes {nodes} nps {nps}")
            print(f"bestmove {best_move.uci()}")
        else:
            # Fallback for game over or no legal moves
            if list(self.board.legal_moves):
                print(f"bestmove {list(self.board.legal_moves)[0].uci()}")
            else:
                print("bestmove 0000")

if __name__ == "__main__":
    engine = Engine()
    engine.uci_loop()
