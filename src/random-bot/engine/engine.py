import sys
import chess

def main():
    board = chess.Board()
    while True:
        line = sys.stdin.readline()
        if not line: break
        parts = line.strip().split()
        if not parts: continue
        
        cmd = parts[0]
        if cmd == "uci":
            print("id name RigorousBot")
            print("uciok")
        elif cmd == "isready":
            print("readyok")
        elif cmd == "ucinewgame":
            board = chess.Board()
        elif cmd == "position":
            if len(parts) > 1:
                if parts[1] == "startpos":
                    board = chess.Board()
                    idx = 2
                elif parts[1] == "fen":
                    # Reconstruct FEN
                    fen_parts = []
                    idx = 2
                    while idx < len(parts) and parts[idx] != "moves":
                        fen_parts.append(parts[idx])
                        idx += 1
                    board = chess.Board(" ".join(fen_parts))
                
                if idx < len(parts) and parts[idx] == "moves":
                    for move in parts[idx+1:]:
                        board.push_uci(move)
        elif cmd == "go":
            import random
            moves = list(board.legal_moves)
            if moves:
                print(f"bestmove {random.choice(moves).uci()}")
            else:
                print("bestmove 0000")
        elif cmd == "quit":
            break
        sys.stdout.flush()

if __name__ == "__main__":
    main()
