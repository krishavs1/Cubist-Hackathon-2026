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

# Module-level deadline used by the search to abort cleanly when the time
# budget is exhausted. Set by search() before every go, then checked inside
# negamax/quiescence every few thousand nodes.
_search_deadline = 0.0


class SearchAborted(Exception):
    """Raised from inside negamax/quiescence when the time budget expires.

    The root search catches this and keeps whatever best move was returned
    by the last fully-completed iterative-deepening iteration.
    """


def _time_is_up():
    return time.time() >= _search_deadline


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
    # Periodic time check. 2047 is chosen so the mask is cheap and the
    # check fires often enough to keep latency bounded.
    if nodes & 2047 == 0 and _time_is_up():
        raise SearchAborted()
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
    if nodes & 2047 == 0 and _time_is_up():
        raise SearchAborted()
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
                print("id name MegapromptEngine", flush=True)
                print("id author GeminiCLI", flush=True)
                print("uciok", flush=True)
            elif cmd[0] == "isready":
                print("readyok", flush=True)
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
        """Iterative-deepening search that honors UCI time controls.

        Supports: ``go movetime <ms>``, ``go wtime <ms> btime <ms> [winc
        <ms>] [binc <ms>]``, ``go depth <n>``, and bare ``go``. The
        search deepens one ply at a time and aborts cleanly when the
        deadline is reached (via SearchAborted). We always keep the best
        move from the last FULLY completed iteration, so a partial
        search never regresses the returned move.
        """
        global nodes, _search_deadline
        nodes = 0
        start_time = time.time()

        # ---- Parse the go command ----
        movetime_ms = None
        depth_limit = None
        wtime = btime = winc = binc = None
        i = 1
        while i < len(cmd):
            tok = cmd[i]
            nxt = cmd[i + 1] if i + 1 < len(cmd) else None
            try:
                if tok == "movetime" and nxt is not None:
                    movetime_ms = int(nxt); i += 2; continue
                if tok == "depth" and nxt is not None:
                    depth_limit = int(nxt); i += 2; continue
                if tok == "wtime" and nxt is not None:
                    wtime = int(nxt); i += 2; continue
                if tok == "btime" and nxt is not None:
                    btime = int(nxt); i += 2; continue
                if tok == "winc" and nxt is not None:
                    winc = int(nxt); i += 2; continue
                if tok == "binc" and nxt is not None:
                    binc = int(nxt); i += 2; continue
            except (TypeError, ValueError):
                pass
            i += 1

        # ---- Compute the time budget ----
        if movetime_ms is not None:
            budget_s = movetime_ms / 1000.0
        elif wtime is not None or btime is not None:
            # Cheap clock allocation: give ourselves ~1/30th of our
            # remaining clock plus one increment. Leaves comfortable
            # headroom for the rest of the game.
            my_time = (wtime if self.board.turn == chess.WHITE else btime) or 0
            my_inc = (winc if self.board.turn == chess.WHITE else binc) or 0
            budget_s = max(0.01, (my_time / 30.0 + my_inc) / 1000.0)
        elif depth_limit is not None:
            budget_s = 1e9  # effectively unlimited when a depth is given
        else:
            budget_s = 1.0  # sane default for bare `go`

        # Keep 15% in reserve so we never miss the wall-clock deadline.
        # Arena uses a 2s hard timeout per move; overshooting is a loss.
        _search_deadline = start_time + budget_s * 0.85
        max_depth = depth_limit if depth_limit is not None else 64

        # ---- Handle trivial cases ----
        moves = list(self.board.legal_moves)
        if not moves:
            print("bestmove 0000", flush=True)
            return
        if len(moves) == 1:
            print(f"info depth 0 string forced move", flush=True)
            print(f"bestmove {moves[0].uci()}", flush=True)
            return

        # Fallback move so we always have something to return.
        best_move = moves[0]
        best_score = 0

        # ---- Iterative deepening ----
        for depth in range(1, max_depth + 1):
            iter_best_move = None
            iter_best_score = -999999
            alpha, beta = -999999, 999999
            aborted = False

            # Put the previous best move first for better alpha-beta pruning.
            ordered = [best_move] + [m for m in moves if m != best_move]
            ordered.sort(
                key=lambda m: (
                    0 if m == best_move else 1,
                    -move_ordering(self.board, m),
                )
            )

            for move in ordered:
                # Check deadline before each root move; if time's up and
                # we already completed depth>=1, keep that result.
                if depth > 1 and _time_is_up():
                    aborted = True
                    break
                self.board.push(move)
                try:
                    score = -negamax(self.board, depth - 1, -beta, -alpha)
                except SearchAborted:
                    self.board.pop()
                    aborted = True
                    break
                self.board.pop()

                if score > iter_best_score:
                    iter_best_score = score
                    iter_best_move = move
                if score > alpha:
                    alpha = score

            # Only commit the iteration's result if we completed it fully.
            if not aborted and iter_best_move is not None:
                best_move = iter_best_move
                best_score = iter_best_score
                elapsed = time.time() - start_time
                nps = int(nodes / elapsed) if elapsed > 0 else 0
                print(
                    f"info depth {depth} score cp {best_score} "
                    f"nodes {nodes} nps {nps} time {int(elapsed * 1000)}",
                    flush=True,
                )
            else:
                break

            if _time_is_up():
                break

        print(f"bestmove {best_move.uci()}", flush=True)

if __name__ == "__main__":
    engine = Engine()
    engine.uci_loop()
