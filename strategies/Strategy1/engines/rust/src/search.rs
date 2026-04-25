//! Search core for the Strategy1 Rust port.
//!
//! Faithful port of `Strategy1/engines/mve/search.py` with the following
//! features:
//!
//!   * Negamax + Principal Variation Search (PVS)
//!   * Iterative deepening + aspiration windows
//!   * Quiescence search (MVV-LVA ordered, delta pruning, stand-pat cutoff)
//!   * Transposition table (packed 16-bit TT-move, Exact/Lower/Upper flags)
//!   * Check extensions
//!   * Killer moves + history heuristic
//!   * Late Move Reductions (LMR)
//!   * Reverse-futility pruning + razoring + child-level futility pruning
//!
//!   * Null-move pruning via [`Position::swap_turn()`] when not in check and
//!     the side to move still has a non-pawn piece.
//!
//! Eval contract: `eval::evaluate(pos)` returns centipawns from White's
//! POV; this module converts to side-to-move POV internally.

use std::time::Instant;

use shakmaty::zobrist::{Zobrist64, ZobristHash};
use shakmaty::{Board, Chess, Color, EnPassantMode, Move, Position};

use crate::eval::{evaluate, role_idx, EG_VALUE, INF, MATE, MATE_IN_MAX};

// ── Transposition Table ─────────────────────────────────────────────────────

const TT_SIZE: usize = 1 << 22; // 4M entries, ~64MB
const TT_MASK: u64 = (TT_SIZE as u64) - 1;

const TT_EXACT: u8 = 0;
const TT_LOWER: u8 = 1;
const TT_UPPER: u8 = 2;
const TT_NONE: u8 = 255;

#[derive(Copy, Clone)]
struct TtEntry {
    key: u64,
    depth: i16,
    score: i32,
    flag: u8,
    packed_move: u16, // 0 = none; else (from | to<<6 | promo<<12)
}

impl Default for TtEntry {
    fn default() -> Self {
        TtEntry { key: 0, depth: 0, score: 0, flag: TT_NONE, packed_move: 0 }
    }
}

struct TranspositionTable {
    table: Vec<TtEntry>,
}

impl TranspositionTable {
    fn new() -> Self {
        TranspositionTable { table: vec![TtEntry::default(); TT_SIZE] }
    }

    fn clear(&mut self) {
        for e in self.table.iter_mut() {
            *e = TtEntry::default();
        }
    }

    #[inline(always)]
    fn probe(&self, key: u64) -> Option<&TtEntry> {
        let slot = &self.table[(key & TT_MASK) as usize];
        if slot.flag != TT_NONE && slot.key == key {
            Some(slot)
        } else {
            None
        }
    }

    #[inline(always)]
    fn store(&mut self, key: u64, depth: i16, score: i32, flag: u8, packed_move: u16) {
        let slot = &mut self.table[(key & TT_MASK) as usize];
        // Depth-preferred: keep deeper searches; otherwise replace empty slots.
        if slot.flag == TT_NONE || slot.depth <= depth {
            *slot = TtEntry { key, depth, score, flag, packed_move };
        }
    }
}

// ── Move packing ────────────────────────────────────────────────────────────

#[inline(always)]
fn pack_move(m: &Move) -> u16 {
    let from = m.from().map_or(0u32, u32::from);
    let to = u32::from(m.to());
    let promo = m.promotion().map_or(0u32, |r| r as u32);
    (from | (to << 6) | (promo << 12)) as u16
}

fn find_move(packed: u16, moves: &[Move]) -> Option<Move> {
    if packed == 0 {
        return None;
    }
    let from = (packed & 0x3F) as u32;
    let to = ((packed >> 6) & 0x3F) as u32;
    let promo = ((packed >> 12) & 0xF) as u32;
    for m in moves {
        let mf = m.from().map_or(0u32, u32::from);
        let mt = u32::from(m.to());
        let mp = m.promotion().map_or(0u32, |r| r as u32);
        if mf == from && mt == to && mp == promo {
            return Some(m.clone());
        }
    }
    None
}

// ── Searcher state ──────────────────────────────────────────────────────────

const MAX_PLY: usize = 128;

pub struct Searcher {
    tt: TranspositionTable,
    killers: Vec<[Option<Move>; 2]>,
    history: [[i32; 64]; 64],
    nodes: u64,
    start: Instant,
    hard_limit_ms: u64,
    stop: bool,
    best_move: Option<Move>,
    best_score: i32,
}

impl Searcher {
    pub fn new() -> Self {
        Searcher {
            tt: TranspositionTable::new(),
            killers: (0..MAX_PLY).map(|_| [None, None]).collect(),
            history: [[0; 64]; 64],
            nodes: 0,
            start: Instant::now(),
            hard_limit_ms: 0,
            stop: false,
            best_move: None,
            best_score: 0,
        }
    }

    pub fn reset(&mut self) {
        self.tt.clear();
        for k in self.killers.iter_mut() {
            *k = [None, None];
        }
        self.history = [[0; 64]; 64];
    }

    pub fn nodes(&self) -> u64 {
        self.nodes
    }

    #[inline(always)]
    fn time_up(&mut self) -> bool {
        if self.stop {
            return true;
        }
        if (self.nodes & 4095) == 0 {
            if self.start.elapsed().as_millis() as u64 >= self.hard_limit_ms {
                self.stop = true;
                return true;
            }
        }
        false
    }

    #[inline(always)]
    fn eval_stm(&self, pos: &Chess) -> i32 {
        let s = evaluate(pos);
        if pos.turn() == Color::White { s } else { -s }
    }

    #[inline(always)]
    fn zkey(pos: &Chess) -> u64 {
        let z: Zobrist64 = pos.zobrist_hash(EnPassantMode::Legal);
        u64::from(z)
    }

    /// Side to move must still have a minor or major piece (exclude null in K+P endings).
    #[inline(always)]
    fn side_has_null_material(board: &Board, color: Color) -> bool {
        let ours = board.by_color(color);
        let pawns_kings = board.pawns() | board.kings();
        !(ours & !pawns_kings).is_empty()
    }

    // ── Move ordering ──

    #[inline(always)]
    fn mvv_lva(m: &Move) -> i32 {
        let captured = m.capture().map_or(0, |r| (role_idx(r) as i32) + 1);
        let attacker = (role_idx(m.role()) as i32) + 1;
        captured * 10 - attacker
    }

    fn score_move(&self, m: &Move, tt_move: &Option<Move>, ply: usize) -> i32 {
        if let Some(tm) = tt_move {
            if m == tm {
                return 1_000_000;
            }
        }
        if m.is_capture() {
            let captured = m.capture().map_or(1, |r| (role_idx(r) as i32) + 1);
            let attacker = (role_idx(m.role()) as i32) + 1;
            let promo = m.promotion().map_or(0, |r| role_idx(r) as i32);
            return 100_000 + captured * 100 - attacker + promo * 10;
        }
        if m.is_promotion() {
            return 90_000 + m.promotion().map_or(0, |r| role_idx(r) as i32);
        }
        if ply < MAX_PLY {
            let k = &self.killers[ply];
            if k[0].as_ref() == Some(m) {
                return 80_000;
            }
            if k[1].as_ref() == Some(m) {
                return 70_000;
            }
        }
        let from = m.from().map_or(0u32, u32::from) as usize;
        let to = u32::from(m.to()) as usize;
        self.history[from][to]
    }

    fn order_moves(&self, moves: &mut Vec<Move>, tt_move: &Option<Move>, ply: usize) {
        let mut scored: Vec<(i32, Move)> = moves
            .drain(..)
            .map(|m| (self.score_move(&m, tt_move, ply), m))
            .collect();
        scored.sort_unstable_by(|a, b| b.0.cmp(&a.0));
        moves.extend(scored.into_iter().map(|(_, m)| m));
    }

    fn order_captures(&self, moves: &mut Vec<Move>) {
        let mut scored: Vec<(i32, Move)> = moves
            .drain(..)
            .map(|m| (Self::mvv_lva(&m), m))
            .collect();
        scored.sort_unstable_by(|a, b| b.0.cmp(&a.0));
        moves.extend(scored.into_iter().map(|(_, m)| m));
    }

    // ── Quiescence ──

    fn quiescence(&mut self, pos: &Chess, mut alpha: i32, beta: i32, ply: usize) -> i32 {
        self.nodes += 1;
        if self.time_up() {
            return 0;
        }

        if pos.is_insufficient_material() {
            return 0;
        }

        let in_check = pos.is_check();
        let mut stand_pat = 0i32;

        if !in_check {
            stand_pat = self.eval_stm(pos);
            if stand_pat >= beta {
                return stand_pat;
            }
            if stand_pat > alpha {
                alpha = stand_pat;
            }
            const BIG_DELTA: i32 = 975;
            if stand_pat + BIG_DELTA < alpha {
                return alpha;
            }
        }

        let mut moves: Vec<Move> = if in_check {
            pos.legal_moves().into_iter().collect()
        } else {
            pos.legal_moves().into_iter().filter(|m| m.is_capture()).collect()
        };

        if in_check && moves.is_empty() {
            return -MATE + ply as i32;
        }

        if in_check {
            self.order_moves(&mut moves, &None, ply);
        } else {
            self.order_captures(&mut moves);
        }

        let mut best: i32 = if in_check { -INF } else { alpha };

        for m in moves {
            if !in_check && !m.is_promotion() {
                let cap_val = m.capture().map_or(0, |r| EG_VALUE[role_idx(r)]);
                if stand_pat + cap_val + 200 < alpha {
                    continue;
                }
            }

            let mut child = pos.clone();
            child.play_unchecked(&m);

            let score = -self.quiescence(&child, -beta, -alpha, ply + 1);
            if self.stop {
                return 0;
            }
            if score > best {
                best = score;
                if score > alpha {
                    alpha = score;
                }
                if alpha >= beta {
                    return score;
                }
            }
        }

        if in_check && best == -INF {
            -MATE + ply as i32
        } else if in_check {
            best
        } else {
            alpha
        }
    }

    // ── Main search ──

    fn search(
        &mut self,
        pos: &Chess,
        depth: i16,
        mut alpha: i32,
        mut beta: i32,
        ply: usize,
    ) -> i32 {
        self.nodes += 1;
        if self.time_up() {
            return 0;
        }

        let is_root = ply == 0;
        let is_pv = beta - alpha > 1;

        // Repetition / 50-move / insufficient material.
        if !is_root {
            if pos.halfmoves() >= 100 || pos.is_insufficient_material() {
                return 0;
            }
            // Mate-distance pruning
            let mate_floor = -MATE + ply as i32;
            let mate_ceil = MATE - ply as i32 - 1;
            if alpha < mate_floor { alpha = mate_floor; }
            if beta > mate_ceil { beta = mate_ceil; }
            if alpha >= beta {
                return alpha;
            }
        }

        let in_check = pos.is_check();
        let mut depth = depth;
        if in_check {
            depth += 1; // Check extension
        }

        if depth <= 0 {
            return self.quiescence(pos, alpha, beta, ply);
        }

        let key = Self::zkey(pos);

        // TT probe -- cutoff first, move resolution once we have the legal list.
        let mut tt_packed: u16 = 0;
        if let Some(entry) = self.tt.probe(key) {
            if !is_pv && !is_root && entry.depth >= depth {
                match entry.flag {
                    TT_EXACT => return entry.score,
                    TT_LOWER if entry.score >= beta => return entry.score,
                    TT_UPPER if entry.score <= alpha => return entry.score,
                    _ => {}
                }
            }
            tt_packed = entry.packed_move;
        }

        // Collect legal moves.
        let mut moves: Vec<Move> = pos.legal_moves().into_iter().collect();

        if moves.is_empty() {
            return if in_check { -MATE + ply as i32 } else { 0 };
        }

        // Null-move pruning (after we know the position is not terminal).
        if !is_pv
            && !is_root
            && !in_check
            && depth >= 3
            && Self::side_has_null_material(pos.board(), pos.turn())
        {
            if let Ok(nm_child) = pos.clone().swap_turn() {
                let r = 2 + (depth >= 9) as i16 + (depth >= 16) as i16;
                let null_depth = depth - 1 - r;
                if null_depth > 0 {
                    let null_score =
                        -self.search(&nm_child, null_depth, -beta, (-beta).saturating_add(1), ply + 1);
                    if !self.stop && null_score >= beta {
                        return beta;
                    }
                }
            }
        }

        let tt_move: Option<Move> = find_move(tt_packed, &moves);

        // Reverse-futility / razoring (skipped in PV and when in check).
        let mut static_eval: Option<i32> = None;
        if !in_check && !is_pv {
            let se = self.eval_stm(pos);
            static_eval = Some(se);
            if depth <= 3 {
                let margin = 120 * depth as i32;
                if se - margin >= beta {
                    return se - margin;
                }
            }
            if depth <= 4 {
                let razor_margin = 300 + 60 * depth as i32;
                if se + razor_margin < alpha {
                    let q = self.quiescence(pos, alpha, beta, ply);
                    if q < alpha {
                        return q;
                    }
                }
            }
        }

        self.order_moves(&mut moves, &tt_move, ply);

        let original_alpha = alpha;
        let mut best_score = -INF;
        let mut best_move: Option<Move> = None;
        let mut searched = 0usize;

        for m in &moves {
            let is_capture = m.is_capture();
            let is_promo = m.is_promotion();
            let is_quiet = !is_capture && !is_promo;

            // Child-level futility pruning (quiet, late moves, shallow depth).
            if !is_pv
                && !in_check
                && !is_root
                && depth <= 6
                && is_quiet
                && best_score > -MATE_IN_MAX
            {
                let futility_margin = 150 + 100 * depth as i32;
                let se = match static_eval {
                    Some(v) => v,
                    None => {
                        let v = self.eval_stm(pos);
                        static_eval = Some(v);
                        v
                    }
                };
                if se + futility_margin <= alpha {
                    searched += 1;
                    continue;
                }
            }

            let mut child = pos.clone();
            child.play_unchecked(m);

            let child_in_check = child.is_check();
            let new_depth = depth - 1;

            let do_lmr = searched >= 3 && depth >= 3 && is_quiet && !in_check && !child_in_check;

            let mut score: i32;
            if do_lmr {
                let mut reduction: i16 = 1;
                if searched >= 6 {
                    reduction = 2;
                }
                if depth >= 6 && searched >= 10 {
                    reduction = 3;
                }
                if depth >= 8 && searched >= 16 && new_depth > reduction + 2 {
                    reduction += 1;
                }
                let red_depth = (new_depth - reduction).max(1);
                score = -self.search(&child, red_depth, -alpha - 1, -alpha, ply + 1);
                if score > alpha && !self.stop {
                    score = -self.search(&child, new_depth, -alpha - 1, -alpha, ply + 1);
                    if score > alpha && score < beta && !self.stop {
                        score = -self.search(&child, new_depth, -beta, -alpha, ply + 1);
                    }
                }
            } else if searched == 0 {
                score = -self.search(&child, new_depth, -beta, -alpha, ply + 1);
            } else {
                score = -self.search(&child, new_depth, -alpha - 1, -alpha, ply + 1);
                if score > alpha && score < beta && !self.stop {
                    score = -self.search(&child, new_depth, -beta, -alpha, ply + 1);
                }
            }

            searched += 1;
            if self.stop {
                return 0;
            }

            if score > best_score {
                best_score = score;
                best_move = Some(m.clone());
                if is_root {
                    self.best_move = Some(m.clone());
                    self.best_score = score;
                }
                if score > alpha {
                    alpha = score;
                }
            }

            if alpha >= beta {
                // Update killers & history for quiet beta-cutoff moves.
                if !is_capture && !is_promo && ply < MAX_PLY {
                    let k = &mut self.killers[ply];
                    if k[0].as_ref() != Some(m) {
                        k[1] = k[0].take();
                        k[0] = Some(m.clone());
                    }
                    let f = m.from().map_or(0u32, u32::from) as usize;
                    let t = u32::from(m.to()) as usize;
                    self.history[f][t] += (depth as i32) * (depth as i32);
                }
                break;
            }
        }

        // Store in TT.
        if !self.stop {
            if let Some(ref bm) = best_move {
                let flag = if best_score <= original_alpha {
                    TT_UPPER
                } else if best_score >= beta {
                    TT_LOWER
                } else {
                    TT_EXACT
                };
                self.tt.store(key, depth, best_score, flag, pack_move(bm));
            }
        }

        best_score
    }

    // ── Iterative deepening driver ──

    pub fn go(
        &mut self,
        pos: &Chess,
        soft_ms: u64,
        hard_ms: u64,
        max_depth: i16,
        verbose: bool,
    ) -> Option<Move> {
        self.nodes = 0;
        self.stop = false;
        self.start = Instant::now();
        self.hard_limit_ms = hard_ms;
        self.best_move = None;
        self.best_score = 0;

        let legal: Vec<Move> = pos.legal_moves().into_iter().collect();
        if legal.is_empty() {
            return None;
        }
        let mut best = legal[0].clone();
        let mut prev_score = 0i32;

        for depth in 1..=max_depth {
            if self.stop {
                break;
            }
            let elapsed = self.start.elapsed().as_millis() as u64;
            if depth > 1 && elapsed >= soft_ms {
                break;
            }

            let score;
            if depth < 4 {
                score = self.search(pos, depth, -INF, INF, 0);
            } else if prev_score.abs() >= MATE_IN_MAX - 200 {
                score = self.search(pos, depth, -INF, INF, 0);
            } else {
                let window = 48;
                let alpha = prev_score.saturating_sub(window);
                let beta = prev_score.saturating_add(window);
                let mut s = self.search(pos, depth, alpha, beta, 0);
                if !self.stop && (s <= alpha || s >= beta) {
                    s = self.search(pos, depth, -INF, INF, 0);
                }
                score = s;
            }

            if self.stop {
                break;
            }

            if let Some(ref bm) = self.best_move {
                best = bm.clone();
                prev_score = self.best_score;
            }

            if verbose {
                let elapsed = self.start.elapsed().as_millis() as u64;
                let nps = if elapsed > 0 {
                    (self.nodes * 1000) / elapsed
                } else {
                    0
                };
                let score_str = if score >= MATE_IN_MAX {
                    format!("mate {}", (MATE - score + 1) / 2)
                } else if score <= -MATE_IN_MAX {
                    format!("mate {}", -((MATE + score) / 2))
                } else {
                    format!("cp {}", score)
                };
                println!(
                    "info depth {} score {} nodes {} nps {} time {} pv {}",
                    depth,
                    score_str,
                    self.nodes,
                    nps,
                    elapsed,
                    shakmaty::uci::Uci::from_standard(&best)
                );
            }

            if score.abs() >= MATE_IN_MAX {
                break;
            }
        }

        Some(best)
    }
}
