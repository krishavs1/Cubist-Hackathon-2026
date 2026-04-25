"""
Negamax search with alpha-beta, iterative deepening, quiescence,
transposition table, and move ordering (TT move, MVV-LVA, killers, history).
"""

import time
import chess
import chess.polyglot

from evaluation import evaluate, MG_VALUE

MATE = 30000
MATE_BOUND = MATE - 1000  # scores >= this are considered mate scores
INF = 32000

# TT entry flags
EXACT = 0
LOWERBOUND = 1
UPPERBOUND = 2

# MVV-LVA piece values for capture ordering
CAPTURE_VAL = [0, 100, 320, 330, 500, 900, 20000]


class SearchAborted(Exception):
    """Raised mid-search when the time budget is exceeded."""


class Searcher:
    def __init__(self):
        self.tt: dict = {}
        # killers[ply] = [move1, move2]
        self.killers = [[None, None] for _ in range(128)]
        # history[color][from_sq][to_sq]
        self.history = [[[0] * 64 for _ in range(64)] for _ in range(2)]
        self.nodes = 0
        self.deadline = 0.0
        self.aborted = False
        self.root_best = None

    # ----- Public API -----

    def reset(self):
        self.tt.clear()
        self.killers = [[None, None] for _ in range(128)]
        self.history = [[[0] * 64 for _ in range(64)] for _ in range(2)]

    def search(self, board: chess.Board, max_depth: int = 64,
               time_limit_ms: int | None = None,
               info_callback=None) -> chess.Move | None:
        """Iterative-deepening search. Returns the best move found."""
        self.nodes = 0
        self.aborted = False
        self.root_best = None
        if time_limit_ms is None:
            self.deadline = float("inf")
        else:
            self.deadline = time.time() + time_limit_ms / 1000.0

        legal = list(board.legal_moves)
        if not legal:
            return None
        # Trivial: only one legal move; return immediately.
        if len(legal) == 1:
            return legal[0]

        best_move = legal[0]
        best_score = 0

        for depth in range(1, max_depth + 1):
            try:
                score, move = self._root_search(board, depth)
            except SearchAborted:
                break
            if move is not None:
                best_move = move
                best_score = score
                self.root_best = move
            if info_callback:
                info_callback(depth, best_score, best_move, self.nodes,
                              time.time() - (self.deadline - (time_limit_ms or 0) / 1000.0)
                              if time_limit_ms else 0.0)
            # Early exit on forced mate.
            if abs(best_score) >= MATE_BOUND:
                break
            # Stop if we've used most of our time; the next depth likely won't finish.
            if time_limit_ms is not None:
                remaining = self.deadline - time.time()
                if remaining <= (time_limit_ms / 1000.0) * 0.4:
                    break

        return best_move

    # ----- Internals -----

    def _check_time(self):
        # Check every 2048 nodes to amortise time syscalls.
        if (self.nodes & 2047) == 0 and time.time() >= self.deadline:
            self.aborted = True
            raise SearchAborted()

    def _root_search(self, board: chess.Board, depth: int):
        alpha, beta = -INF, INF
        best_score = -INF
        best_move = None

        moves = self._order_moves(board, list(board.legal_moves), 0,
                                  self.root_best)
        for move in moves:
            board.push(move)
            try:
                score = -self._negamax(board, depth - 1, -beta, -alpha, 1)
            except SearchAborted:
                board.pop()
                # Propagate, but only if we don't already have a complete result
                # for this depth.
                if best_move is None:
                    raise
                return best_score, best_move
            board.pop()
            if score > best_score:
                best_score = score
                best_move = move
            if score > alpha:
                alpha = score
        return best_score, best_move

    def _negamax(self, board: chess.Board, depth: int,
                 alpha: int, beta: int, ply: int) -> int:
        self.nodes += 1
        self._check_time()

        # Draw detection (cheap repetition / 50-move).
        if ply > 0 and (board.is_repetition(2) or board.halfmove_clock >= 100
                        or board.is_insufficient_material()):
            return 0

        in_check = board.is_check()
        # Check extension: avoid horizon when in check.
        if in_check:
            depth += 1

        if depth <= 0:
            return self._quiescence(board, alpha, beta, ply)

        alpha_orig = alpha

        # Transposition table probe.
        key = chess.polyglot.zobrist_hash(board)
        tt_move = None
        entry = self.tt.get(key)
        if entry is not None:
            tt_depth, tt_score, tt_flag, tt_move = entry
            if tt_depth >= depth:
                # Adjust mate scores stored in TT.
                s = tt_score
                if s >= MATE_BOUND:
                    s -= ply
                elif s <= -MATE_BOUND:
                    s += ply
                if tt_flag == EXACT:
                    return s
                if tt_flag == LOWERBOUND and s > alpha:
                    alpha = s
                elif tt_flag == UPPERBOUND and s < beta:
                    beta = s
                if alpha >= beta:
                    return s

        # Null-move pruning. Skip in check, in pawn-only endings, and at low depth.
        if (depth >= 3 and not in_check and ply > 0
                and self._has_non_pawn_material(board)
                and beta < MATE_BOUND):
            board.push(chess.Move.null())
            R = 2 + (depth >= 6)
            try:
                null_score = -self._negamax(board, depth - 1 - R,
                                            -beta, -beta + 1, ply + 1)
            finally:
                board.pop()
            if null_score >= beta:
                return beta  # fail-hard

        moves = list(board.legal_moves)
        if not moves:
            # Checkmate or stalemate.
            if in_check:
                return -MATE + ply
            return 0

        moves = self._order_moves(board, moves, ply, tt_move)

        best_score = -INF
        best_move = None
        move_count = 0

        for move in moves:
            move_count += 1
            is_capture = board.is_capture(move)
            is_promo = move.promotion is not None
            gives_check = board.gives_check(move)

            board.push(move)

            # Late move reductions on quiet, non-tactical moves.
            new_depth = depth - 1
            if (depth >= 3 and move_count > 3
                    and not in_check and not is_capture
                    and not is_promo and not gives_check):
                reduction = 1
                try:
                    score = -self._negamax(board, new_depth - reduction,
                                           -alpha - 1, -alpha, ply + 1)
                except SearchAborted:
                    board.pop()
                    raise
                if score > alpha:
                    score = -self._negamax(board, new_depth,
                                           -beta, -alpha, ply + 1)
            else:
                score = -self._negamax(board, new_depth,
                                       -beta, -alpha, ply + 1)

            board.pop()

            if score > best_score:
                best_score = score
                best_move = move
            if score > alpha:
                alpha = score
            if alpha >= beta:
                # Beta cutoff: update killer / history for quiet moves.
                if not is_capture and not is_promo:
                    if self.killers[ply][0] != move:
                        self.killers[ply][1] = self.killers[ply][0]
                        self.killers[ply][0] = move
                    color = 0 if board.turn == chess.WHITE else 1
                    # board.turn was already flipped after push/pop, so this is
                    # the side that just moved. Use that side's history table.
                    self.history[color][move.from_square][move.to_square] += depth * depth
                break

        # Store in TT (adjust mate scores so they're ply-independent).
        store_score = best_score
        if store_score >= MATE_BOUND:
            store_score += ply
        elif store_score <= -MATE_BOUND:
            store_score -= ply
        if best_score <= alpha_orig:
            flag = UPPERBOUND
        elif best_score >= beta:
            flag = LOWERBOUND
        else:
            flag = EXACT
        self.tt[key] = (depth, store_score, flag, best_move)

        return best_score

    def _quiescence(self, board: chess.Board, alpha: int, beta: int,
                    ply: int) -> int:
        self.nodes += 1
        self._check_time()

        if board.is_repetition(2) or board.halfmove_clock >= 100 \
                or board.is_insufficient_material():
            return 0

        stand = evaluate(board)
        # Convert from white-POV to side-to-move POV.
        if board.turn == chess.BLACK:
            stand = -stand

        if stand >= beta:
            return beta
        if stand > alpha:
            alpha = stand

        # Generate captures and queen promotions.
        moves = []
        for move in board.legal_moves:
            if board.is_capture(move) or move.promotion == chess.QUEEN:
                moves.append(move)
        moves = self._order_captures(board, moves)

        for move in moves:
            # Delta pruning: skip captures that can't raise alpha enough.
            if not move.promotion:
                victim = board.piece_type_at(move.to_square)
                if victim is None:  # en passant
                    victim_val = MG_VALUE[chess.PAWN]
                else:
                    victim_val = MG_VALUE[victim]
                if stand + victim_val + 200 < alpha:
                    continue

            board.push(move)
            score = -self._quiescence(board, -beta, -alpha, ply + 1)
            board.pop()

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

        return alpha

    # ----- Move ordering -----

    def _order_moves(self, board: chess.Board, moves: list,
                     ply: int, tt_move):
        scored = []
        killer1, killer2 = self.killers[ply] if ply < len(self.killers) else (None, None)
        color = 0 if board.turn == chess.WHITE else 1
        for move in moves:
            score = 0
            if tt_move is not None and move == tt_move:
                score = 1_000_000
            elif board.is_capture(move):
                victim_pt = board.piece_type_at(move.to_square)
                victim_val = CAPTURE_VAL[victim_pt] if victim_pt else CAPTURE_VAL[chess.PAWN]
                attacker_pt = board.piece_type_at(move.from_square) or chess.PAWN
                score = 100_000 + victim_val * 10 - CAPTURE_VAL[attacker_pt]
                if move.promotion:
                    score += CAPTURE_VAL[move.promotion]
            elif move.promotion:
                score = 90_000 + CAPTURE_VAL[move.promotion]
            elif move == killer1:
                score = 80_000
            elif move == killer2:
                score = 79_000
            else:
                score = self.history[color][move.from_square][move.to_square]
            scored.append((score, move))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored]

    def _order_captures(self, board: chess.Board, moves: list):
        scored = []
        for move in moves:
            victim_pt = board.piece_type_at(move.to_square)
            victim_val = CAPTURE_VAL[victim_pt] if victim_pt else CAPTURE_VAL[chess.PAWN]
            attacker_pt = board.piece_type_at(move.from_square) or chess.PAWN
            score = victim_val * 10 - CAPTURE_VAL[attacker_pt]
            if move.promotion:
                score += CAPTURE_VAL[move.promotion]
            scored.append((score, move))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored]

    @staticmethod
    def _has_non_pawn_material(board: chess.Board) -> bool:
        side = board.turn
        return bool(board.knights & board.occupied_co[side]
                    or board.bishops & board.occupied_co[side]
                    or board.rooks & board.occupied_co[side]
                    or board.queens & board.occupied_co[side])
