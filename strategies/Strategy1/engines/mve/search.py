#!/usr/bin/env python3
"""
search -- modern search core for the Darwinian AI engine.

Implements the textbook strong-engine recipe:
  * Negamax with Principal Variation Search (PVS)
  * Iterative deepening with aspiration windows
  * Quiescence search (captures, MVV-LVA ordered, with delta pruning)
  * Transposition table (Zobrist-keyed, with bound flags)
  * Null-move pruning (with non-pawn-material guard)
  * Late move reductions (LMR)
  * Check extensions
  * Killer moves + history heuristic
  * Reverse-futility pruning + razoring + futility pruning

The evaluation function is injected by the caller so every Darwinian
personality (heuristics.REGISTRY) drives the same search core. This is the
core architectural separation: search is fixed, evaluation is the mutation
surface.

Eval contract (matches heuristics.py): eval_fn(board) -> int centipawns
from White's perspective. The Searcher converts to side-to-move POV.

PeSTO tables stay embedded because:
  1. They drive the default 'pesto' personality (strongest baseline).
  2. The quiescence delta-pruning threshold uses EG_VALUE[piece] for
     capture value -- independent of which personality is driving eval.
"""

import sys
import time
from typing import Callable, Optional

import chess


sys.setrecursionlimit(10000)

MATE = 30000
MATE_IN_MAX = MATE - 512
INF = 32000

MG_VALUE = (82, 337, 365, 477, 1025, 0)
EG_VALUE = (94, 281, 297, 512, 936, 0)
GAME_PHASE_INC = (0, 1, 1, 2, 4, 0)

MG_PAWN = (
      0,   0,   0,   0,   0,   0,  0,   0,
     98, 134,  61,  95,  68, 126, 34, -11,
     -6,   7,  26,  31,  65,  56, 25, -20,
    -14,  13,   6,  21,  23,  12, 17, -23,
    -27,  -2,  -5,  12,  17,   6, 10, -25,
    -26,  -4,  -4, -10,   3,   3, 33, -12,
    -35,  -1, -20, -23, -15,  24, 38, -22,
      0,   0,   0,   0,   0,   0,  0,   0,
)
EG_PAWN = (
      0,   0,   0,   0,   0,   0,   0,   0,
    178, 173, 158, 134, 147, 132, 165, 187,
     94, 100,  85,  67,  56,  53,  82,  84,
     32,  24,  13,   5,  -2,   4,  17,  17,
     13,   9,  -3,  -7,  -7,  -8,   3,  -1,
      4,   7,  -6,   1,   0,  -5,  -1,  -8,
     13,   8,   8,  10,  13,   0,   2,  -7,
      0,   0,   0,   0,   0,   0,   0,   0,
)
MG_KNIGHT = (
   -167, -89, -34, -49,  61, -97, -15, -107,
    -73, -41,  72,  36,  23,  62,   7,  -17,
    -47,  60,  37,  65,  84, 129,  73,   44,
     -9,  17,  19,  53,  37,  69,  18,   22,
    -13,   4,  16,  13,  28,  19,  21,   -8,
    -23,  -9,  12,  10,  19,  17,  25,  -16,
    -29, -53, -12,  -3,  -1,  18, -14,  -19,
   -105, -21, -58, -33, -17, -28, -19,  -23,
)
EG_KNIGHT = (
    -58, -38, -13, -28, -31, -27, -63, -99,
    -25,  -8, -25,  -2,  -9, -25, -24, -52,
    -24, -20,  10,   9,  -1,  -9, -19, -41,
    -17,   3,  22,  22,  22,  11,   8, -18,
    -18,  -6,  16,  25,  16,  17,   4, -18,
    -23,  -3,  -1,  15,  10,  -3, -20, -22,
    -42, -20, -10,  -5,  -2, -20, -23, -44,
    -29, -51, -23, -15, -22, -18, -50, -64,
)
MG_BISHOP = (
    -29,   4, -82, -37, -25, -42,   7,  -8,
    -26,  16, -18, -13,  30,  59,  18, -47,
    -16,  37,  43,  40,  35,  50,  37,  -2,
     -4,   5,  19,  50,  37,  37,   7,  -2,
     -6,  13,  13,  26,  34,  12,  10,   4,
      0,  15,  15,  15,  14,  27,  18,  10,
      4,  15,  16,   0,   7,  21,  33,   1,
    -33,  -3, -14, -21, -13, -12, -39, -21,
)
EG_BISHOP = (
    -14, -21, -11,  -8, -7,  -9, -17, -24,
     -8,  -4,   7, -12, -3, -13,  -4, -14,
      2,  -8,   0,  -1, -2,   6,   0,   4,
     -3,   9,  12,   9, 14,  10,   3,   2,
     -6,   3,  13,  19,  7,  10,  -3,  -9,
    -12,  -3,   8,  10, 13,   3,  -7, -15,
    -14, -18,  -7,  -1,  4,  -9, -15, -27,
    -23,  -9, -23,  -5, -9, -16,  -5, -17,
)
MG_ROOK = (
     32,  42,  32,  51, 63,  9,  31,  43,
     27,  32,  58,  62, 80, 67,  26,  44,
     -5,  19,  26,  36, 17, 45,  61,  16,
    -24, -11,   7,  26, 24, 35,  -8, -20,
    -36, -26, -12,  -1,  9, -7,   6, -23,
    -45, -25, -16, -17,  3,  0,  -5, -33,
    -44, -16, -20,  -9, -1, 11,  -6, -71,
    -19, -13,   1,  17, 16,  7, -37, -26,
)
EG_ROOK = (
    13, 10, 18, 15, 12,  12,   8,   5,
    11, 13, 13, 11, -3,   3,   8,   3,
     7,  7,  7,  5,  4,  -3,  -5,  -3,
     4,  3, 13,  1,  2,   1,  -1,   2,
     3,  5,  8,  4, -5,  -6,  -8, -11,
    -4,  0, -5, -1, -7, -12,  -8, -16,
    -6, -6,  0,  2, -9,  -9, -11,  -3,
    -9,  2,  3, -1, -5, -13,   4, -20,
)
MG_QUEEN = (
    -28,   0,  29,  12,  59,  44,  43,  45,
    -24, -39,  -5,   1, -16,  57,  28,  54,
    -13, -17,   7,   8,  29,  56,  47,  57,
    -27, -27, -16, -16,  -1,  17,  -2,   1,
     -9, -26,  -9, -10,  -2,  -4,   3,  -3,
    -14,   2, -11,  -2,  -5,   2,  14,   5,
    -35,  -8,  11,   2,   8,  15,  -3,   1,
     -1, -18,  -9,  10, -15, -25, -31, -50,
)
EG_QUEEN = (
     -9,  22,  22,  27,  27,  19,  10,  20,
    -17,  20,  32,  41,  58,  25,  30,   0,
    -20,   6,   9,  49,  47,  35,  19,   9,
      3,  22,  24,  45,  57,  40,  57,  36,
    -18,  28,  19,  47,  31,  34,  39,  23,
    -16, -27,  15,   6,   9,  17,  10,   5,
    -22, -23, -30, -16, -16, -23, -36, -32,
    -33, -28, -22, -43,  -5, -32, -20, -41,
)
MG_KING = (
    -65,  23,  16, -15, -56, -34,   2,  13,
     29,  -1, -20,  -7,  -8,  -4, -38, -29,
     -9,  24,   2, -16, -20,   6,  22, -22,
    -17, -20, -12, -27, -30, -25, -14, -36,
    -49,  -1, -27, -39, -46, -44, -33, -51,
    -14, -14, -22, -46, -44, -30, -15, -27,
      1,   7,  -8, -64, -43, -16,   9,   8,
    -15,  36,  12, -54,   8, -28,  24,  14,
)
EG_KING = (
    -74, -35, -18, -18, -11,  15,   4, -17,
    -12,  17,  14,  17,  17,  38,  23,  11,
     10,  17,  23,  15,  20,  45,  44,  13,
     -8,  22,  24,  27,  26,  33,  26,   3,
    -18,  -4,  21,  24,  27,  23,   9, -11,
    -19,  -3,  11,  21,  23,  16,   7,  -9,
    -27, -11,   4,  13,  14,   4,  -5, -17,
    -53, -34, -21, -11, -28, -14, -24, -43,
)

MG_TABLES = (MG_PAWN, MG_KNIGHT, MG_BISHOP, MG_ROOK, MG_QUEEN, MG_KING)
EG_TABLES = (EG_PAWN, EG_KNIGHT, EG_BISHOP, EG_ROOK, EG_QUEEN, EG_KING)


def pesto_evaluate(board: chess.Board) -> int:
    """Tapered PeSTO evaluation. Returns centipawns from White's POV
    (matches Strategy1 heuristic contract; Searcher negates as needed)."""
    mg_w = mg_b = eg_w = eg_b = phase = 0
    for sq, piece in board.piece_map().items():
        pt = piece.piece_type - 1
        if piece.color:
            idx = sq ^ 56
            mg_w += MG_VALUE[pt] + MG_TABLES[pt][idx]
            eg_w += EG_VALUE[pt] + EG_TABLES[pt][idx]
        else:
            mg_b += MG_VALUE[pt] + MG_TABLES[pt][sq]
            eg_b += EG_VALUE[pt] + EG_TABLES[pt][sq]
        phase += GAME_PHASE_INC[pt]

    mg_score = mg_w - mg_b
    eg_score = eg_w - eg_b
    mg_phase = phase if phase < 24 else 24
    eg_phase = 24 - mg_phase
    score = (mg_score * mg_phase + eg_score * eg_phase) // 24
    # Small tempo bonus for the side to move (encourages activity)
    score += 10 if board.turn else -10
    return score


TT_EXACT = 0
TT_LOWER = 1
TT_UPPER = 2


class Searcher:
    """PVS + TT + null-move + LMR + killers + history + aspiration windows.

    The eval function is injected at construction time. It must return
    centipawns from White's POV; this class converts to side-to-move POV
    internally (where positive = good for the side about to move).
    """

    def __init__(self, eval_fn: Callable[[chess.Board], int] = pesto_evaluate):
        self.eval_fn = eval_fn
        self.nodes = 0
        self.tt = {}
        self.killers = [[None, None] for _ in range(256)]
        self.history = {}
        self.stop = False
        self.start_time = 0.0
        self.time_limit = 0.0
        self.hard_limit = 0.0
        self.root_best_move = None
        self.root_best_score = 0

    def reset(self):
        self.tt.clear()
        self.killers = [[None, None] for _ in range(256)]
        self.history.clear()

    def _eval_stm(self, board: chess.Board) -> int:
        """Side-to-move POV wrapper around the white-POV eval_fn."""
        s = self.eval_fn(board)
        return s if board.turn else -s

    def _time_up(self):
        if self.stop:
            return True
        if (self.nodes & 2047) == 0:
            if time.time() - self.start_time >= self.hard_limit:
                self.stop = True
                return True
        return False

    def _has_non_pawn_material(self, board):
        side = board.turn
        friendly = board.occupied_co[side]
        return bool((board.knights | board.bishops | board.rooks | board.queens) & friendly)

    def _mvv_lva(self, board, move):
        captured = board.piece_type_at(move.to_square)
        if captured is None:
            captured = 1
        attacker = board.piece_type_at(move.from_square)
        if attacker is None:
            attacker = 1
        return captured * 10 - attacker

    def _score_move(self, board, move, tt_move, ply):
        if tt_move is not None and move == tt_move:
            return 1_000_000
        if board.is_capture(move):
            captured = board.piece_type_at(move.to_square)
            if captured is None:
                captured = 1
            attacker = board.piece_type_at(move.from_square)
            if attacker is None:
                attacker = 1
            promo = move.promotion or 0
            return 100_000 + captured * 100 - attacker + promo * 10
        if move.promotion:
            return 90_000 + move.promotion
        if 0 <= ply < 256:
            k = self.killers[ply]
            if k[0] == move:
                return 80_000
            if k[1] == move:
                return 70_000
        return self.history.get((move.from_square, move.to_square), 0)

    def _order_moves(self, board, moves, tt_move, ply):
        scored = [(self._score_move(board, m, tt_move, ply), m) for m in moves]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored]

    def _order_captures(self, board, moves):
        scored = [(self._mvv_lva(board, m), m) for m in moves]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored]

    def quiescence(self, board, alpha, beta, ply):
        self.nodes += 1
        if self._time_up():
            return 0

        if board.is_insufficient_material():
            return 0

        in_check = board.is_check()

        if not in_check:
            stand_pat = self._eval_stm(board)
            if stand_pat >= beta:
                return stand_pat
            if stand_pat > alpha:
                alpha = stand_pat
            big_delta = 975
            if stand_pat + big_delta < alpha:
                return alpha

        if in_check:
            moves = list(board.legal_moves)
            if not moves:
                return -MATE + ply
            ordered = self._order_moves(board, moves, None, ply)
        else:
            caps = list(board.generate_legal_captures())
            ordered = self._order_captures(board, caps)

        best = -INF if in_check else alpha
        for move in ordered:
            if not in_check and move.promotion is None:
                captured = board.piece_type_at(move.to_square)
                cap_val = EG_VALUE[(captured or 1) - 1]
                if stand_pat + cap_val + 200 < alpha:
                    continue

            board.push(move)
            score = -self.quiescence(board, -beta, -alpha, ply + 1)
            board.pop()

            if self.stop:
                return 0
            if score > best:
                best = score
                if score > alpha:
                    alpha = score
                if alpha >= beta:
                    return score
        if in_check and best == -INF:
            return -MATE + ply
        return alpha if not in_check else best

    def search(self, board, depth, alpha, beta, ply, can_null):
        self.nodes += 1
        if self._time_up():
            return 0

        is_root = (ply == 0)
        is_pv = (beta - alpha > 1)

        if not is_root:
            if board.is_repetition(2) or board.halfmove_clock >= 100 or board.is_insufficient_material():
                return 0
            alpha = max(alpha, -MATE + ply)
            beta = min(beta, MATE - ply - 1)
            if alpha >= beta:
                return alpha

        in_check = board.is_check()
        if in_check:
            depth += 1

        if depth <= 0:
            return self.quiescence(board, alpha, beta, ply)

        key = board._transposition_key()
        tt_move = None
        tt_entry = self.tt.get(key)
        if tt_entry is not None:
            tt_depth, tt_score, tt_flag, tt_move = tt_entry
            if not is_root and tt_depth >= depth and not is_pv:
                if tt_flag == TT_EXACT:
                    return tt_score
                if tt_flag == TT_LOWER and tt_score >= beta:
                    return tt_score
                if tt_flag == TT_UPPER and tt_score <= alpha:
                    return tt_score

        static_eval = None
        if not in_check and not is_pv:
            static_eval = self._eval_stm(board)
            if depth <= 3:
                margin = 120 * depth
                if static_eval - margin >= beta:
                    return static_eval - margin
            if depth <= 4:
                razor_margin = 300 + 60 * depth
                if static_eval + razor_margin < alpha:
                    q = self.quiescence(board, alpha, beta, ply)
                    if q < alpha:
                        return q

        if (can_null and not in_check and not is_pv and depth >= 3
                and self._has_non_pawn_material(board)
                and (static_eval is None or static_eval >= beta)):
            R = 2 + (depth // 4)
            if R > depth - 1:
                R = depth - 1
            board.push(chess.Move.null())
            score = -self.search(board, depth - 1 - R, -beta, -beta + 1, ply + 1, False)
            board.pop()
            if self.stop:
                return 0
            if score >= beta:
                if score >= MATE_IN_MAX:
                    score = beta
                return score

        moves = list(board.legal_moves)
        if not moves:
            if in_check:
                return -MATE + ply
            return 0

        moves = self._order_moves(board, moves, tt_move, ply)

        best_score = -INF
        best_move = None
        original_alpha = alpha
        searched = 0

        for move in moves:
            is_capture = board.is_capture(move)
            is_promo = move.promotion is not None
            gives_check = board.gives_check(move)
            is_quiet = not is_capture and not is_promo and not gives_check

            if (not is_pv and not in_check and not is_root
                    and depth <= 6 and is_quiet and best_score > -MATE_IN_MAX):
                futility_margin = 150 + 100 * depth
                if static_eval is None:
                    static_eval = self._eval_stm(board)
                if static_eval + futility_margin <= alpha:
                    searched += 1
                    continue

            board.push(move)

            new_depth = depth - 1
            score = 0

            do_lmr = (searched >= 3 and depth >= 3 and is_quiet and not in_check)
            if do_lmr:
                reduction = 1
                if searched >= 6:
                    reduction = 2
                if depth >= 6 and searched >= 10:
                    reduction = 3
                red_depth = new_depth - reduction
                if red_depth < 1:
                    red_depth = 1
                score = -self.search(board, red_depth, -alpha - 1, -alpha, ply + 1, True)
                if score > alpha and not self.stop:
                    score = -self.search(board, new_depth, -alpha - 1, -alpha, ply + 1, True)
                    if score > alpha and score < beta and not self.stop:
                        score = -self.search(board, new_depth, -beta, -alpha, ply + 1, True)
            elif searched == 0:
                score = -self.search(board, new_depth, -beta, -alpha, ply + 1, True)
            else:
                score = -self.search(board, new_depth, -alpha - 1, -alpha, ply + 1, True)
                if score > alpha and score < beta and not self.stop:
                    score = -self.search(board, new_depth, -beta, -alpha, ply + 1, True)

            board.pop()
            searched += 1

            if self.stop:
                return 0

            if score > best_score:
                best_score = score
                best_move = move
                if is_root:
                    self.root_best_move = move
                    self.root_best_score = score
                if score > alpha:
                    alpha = score

            if alpha >= beta:
                if not is_capture and not is_promo:
                    k = self.killers[ply] if ply < 256 else None
                    if k is not None and k[0] != move:
                        k[1] = k[0]
                        k[0] = move
                    hk = (move.from_square, move.to_square)
                    self.history[hk] = self.history.get(hk, 0) + depth * depth
                break

        if not self.stop and best_move is not None:
            if best_score <= original_alpha:
                flag = TT_UPPER
            elif best_score >= beta:
                flag = TT_LOWER
            else:
                flag = TT_EXACT
            self.tt[key] = (depth, best_score, flag, best_move)

        return best_score

    def go(self, board, soft_time, hard_time, max_depth, verbose=True):
        self.nodes = 0
        self.stop = False
        self.start_time = time.time()
        self.time_limit = soft_time
        self.hard_limit = hard_time
        self.root_best_move = None
        self.root_best_score = 0

        legal = list(board.legal_moves)
        if not legal:
            return None

        best_move = legal[0]
        prev_score = 0

        for depth in range(1, max_depth + 1):
            if self.stop:
                break
            elapsed = time.time() - self.start_time
            if depth > 1 and elapsed >= soft_time:
                break

            if depth < 4:
                score = self.search(board, depth, -INF, INF, 0, True)
            else:
                window = 40
                alpha = prev_score - window
                beta = prev_score + window
                while True:
                    score = self.search(board, depth, alpha, beta, 0, True)
                    if self.stop:
                        break
                    if score <= alpha:
                        alpha = -INF
                    elif score >= beta:
                        beta = INF
                    else:
                        break

            if self.stop:
                break

            if self.root_best_move is not None:
                best_move = self.root_best_move
                prev_score = self.root_best_score

            if verbose:
                elapsed = time.time() - self.start_time
                ms = int(elapsed * 1000)
                nps = int(self.nodes / elapsed) if elapsed > 0 else 0
                if score >= MATE_IN_MAX:
                    score_str = f"mate {(MATE - score + 1) // 2}"
                elif score <= -MATE_IN_MAX:
                    score_str = f"mate {-((MATE + score) // 2)}"
                else:
                    score_str = f"cp {score}"
                try:
                    sys.stdout.write(
                        f"info depth {depth} score {score_str} nodes {self.nodes} "
                        f"nps {nps} time {ms} pv {best_move.uci()}\n"
                    )
                    sys.stdout.flush()
                except Exception:
                    pass

            if abs(score) >= MATE_IN_MAX:
                break

        return best_move


def search(
    board: chess.Board,
    time_limit_ms: int,
    eval_fn: Optional[Callable[[chess.Board], int]] = None,
    verbose: bool = True,
) -> Optional[chess.Move]:
    """Top-level search entry point. Constructs a Searcher driven by the
    chosen evaluator and runs iterative deepening within the time budget."""
    if eval_fn is None:
        eval_fn = pesto_evaluate
    s = Searcher(eval_fn)
    soft = max(time_limit_ms / 1000.0 - 0.03, 0.01)
    hard = soft
    return s.go(board, soft, hard, 64, verbose=verbose)
