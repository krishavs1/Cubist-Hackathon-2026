//! PeSTO tapered evaluation + the `reflexion_v1` additions.
//!
//! This is a faithful port of `Strategy1/engines/mve/search.py::pesto_evaluate`
//! plus the four corrections the Reflexion loop learned from loss PGNs:
//! development bonus, castling bonus/penalty, rim-knight penalty, early-queen
//! penalty. Returns centipawns from White's POV; the searcher negates.

use shakmaty::{Bitboard, Board, Chess, Color, File, Position, Rank, Role, Square};

pub const MATE: i32 = 30_000;
pub const MATE_IN_MAX: i32 = MATE - 512;
pub const INF: i32 = 32_000;

// PeSTO material values (midgame / endgame), indexed by role-1.
const MG_VALUE: [i32; 6] = [82, 337, 365, 477, 1025, 0];
pub const EG_VALUE: [i32; 6] = [94, 281, 297, 512, 936, 0];
const GAME_PHASE_INC: [i32; 6] = [0, 1, 1, 2, 4, 0];

// Piece-square tables are stored rank-8-first (top of array is rank 8 from
// White's view). For a White piece on square s we index with `s ^ 56` so
// that s=A1 (0) lands on table index 56 (row 7 = rank 1). Black pieces index
// with the raw `s` directly. Same convention as python-chess/PeSTO.

const MG_PAWN: [i32; 64] = [
     0,   0,   0,   0,   0,   0,  0,   0,
    98, 134,  61,  95,  68, 126, 34, -11,
    -6,   7,  26,  31,  65,  56, 25, -20,
   -14,  13,   6,  21,  23,  12, 17, -23,
   -27,  -2,  -5,  12,  17,   6, 10, -25,
   -26,  -4,  -4, -10,   3,   3, 33, -12,
   -35,  -1, -20, -23, -15,  24, 38, -22,
     0,   0,   0,   0,   0,   0,  0,   0,
];
const EG_PAWN: [i32; 64] = [
     0,   0,   0,   0,   0,   0,   0,   0,
   178, 173, 158, 134, 147, 132, 165, 187,
    94, 100,  85,  67,  56,  53,  82,  84,
    32,  24,  13,   5,  -2,   4,  17,  17,
    13,   9,  -3,  -7,  -7,  -8,   3,  -1,
     4,   7,  -6,   1,   0,  -5,  -1,  -8,
    13,   8,   8,  10,  13,   0,   2,  -7,
     0,   0,   0,   0,   0,   0,   0,   0,
];
const MG_KNIGHT: [i32; 64] = [
  -167, -89, -34, -49,  61, -97, -15, -107,
   -73, -41,  72,  36,  23,  62,   7,  -17,
   -47,  60,  37,  65,  84, 129,  73,   44,
    -9,  17,  19,  53,  37,  69,  18,   22,
   -13,   4,  16,  13,  28,  19,  21,   -8,
   -23,  -9,  12,  10,  19,  17,  25,  -16,
   -29, -53, -12,  -3,  -1,  18, -14,  -19,
  -105, -21, -58, -33, -17, -28, -19,  -23,
];
const EG_KNIGHT: [i32; 64] = [
   -58, -38, -13, -28, -31, -27, -63, -99,
   -25,  -8, -25,  -2,  -9, -25, -24, -52,
   -24, -20,  10,   9,  -1,  -9, -19, -41,
   -17,   3,  22,  22,  22,  11,   8, -18,
   -18,  -6,  16,  25,  16,  17,   4, -18,
   -23,  -3,  -1,  15,  10,  -3, -20, -22,
   -42, -20, -10,  -5,  -2, -20, -23, -44,
   -29, -51, -23, -15, -22, -18, -50, -64,
];
const MG_BISHOP: [i32; 64] = [
   -29,   4, -82, -37, -25, -42,   7,  -8,
   -26,  16, -18, -13,  30,  59,  18, -47,
   -16,  37,  43,  40,  35,  50,  37,  -2,
    -4,   5,  19,  50,  37,  37,   7,  -2,
    -6,  13,  13,  26,  34,  12,  10,   4,
     0,  15,  15,  15,  14,  27,  18,  10,
     4,  15,  16,   0,   7,  21,  33,   1,
   -33,  -3, -14, -21, -13, -12, -39, -21,
];
const EG_BISHOP: [i32; 64] = [
   -14, -21, -11,  -8, -7,  -9, -17, -24,
    -8,  -4,   7, -12, -3, -13,  -4, -14,
     2,  -8,   0,  -1, -2,   6,   0,   4,
    -3,   9,  12,   9, 14,  10,   3,   2,
    -6,   3,  13,  19,  7,  10,  -3,  -9,
   -12,  -3,   8,  10, 13,   3,  -7, -15,
   -14, -18,  -7,  -1,  4,  -9, -15, -27,
   -23,  -9, -23,  -5, -9, -16,  -5, -17,
];
const MG_ROOK: [i32; 64] = [
    32,  42,  32,  51, 63,  9,  31,  43,
    27,  32,  58,  62, 80, 67,  26,  44,
    -5,  19,  26,  36, 17, 45,  61,  16,
   -24, -11,   7,  26, 24, 35,  -8, -20,
   -36, -26, -12,  -1,  9, -7,   6, -23,
   -45, -25, -16, -17,  3,  0,  -5, -33,
   -44, -16, -20,  -9, -1, 11,  -6, -71,
   -19, -13,   1,  17, 16,  7, -37, -26,
];
const EG_ROOK: [i32; 64] = [
   13, 10, 18, 15, 12,  12,   8,   5,
   11, 13, 13, 11, -3,   3,   8,   3,
    7,  7,  7,  5,  4,  -3,  -5,  -3,
    4,  3, 13,  1,  2,   1,  -1,   2,
    3,  5,  8,  4, -5,  -6,  -8, -11,
   -4,  0, -5, -1, -7, -12,  -8, -16,
   -6, -6,  0,  2, -9,  -9, -11,  -3,
   -9,  2,  3, -1, -5, -13,   4, -20,
];
const MG_QUEEN: [i32; 64] = [
   -28,   0,  29,  12,  59,  44,  43,  45,
   -24, -39,  -5,   1, -16,  57,  28,  54,
   -13, -17,   7,   8,  29,  56,  47,  57,
   -27, -27, -16, -16,  -1,  17,  -2,   1,
    -9, -26,  -9, -10,  -2,  -4,   3,  -3,
   -14,   2, -11,  -2,  -5,   2,  14,   5,
   -35,  -8,  11,   2,   8,  15,  -3,   1,
    -1, -18,  -9,  10, -15, -25, -31, -50,
];
const EG_QUEEN: [i32; 64] = [
    -9,  22,  22,  27,  27,  19,  10,  20,
   -17,  20,  32,  41,  58,  25,  30,   0,
   -20,   6,   9,  49,  47,  35,  19,   9,
     3,  22,  24,  45,  57,  40,  57,  36,
   -18,  28,  19,  47,  31,  34,  39,  23,
   -16, -27,  15,   6,   9,  17,  10,   5,
   -22, -23, -30, -16, -16, -23, -36, -32,
   -33, -28, -22, -43,  -5, -32, -20, -41,
];
const MG_KING: [i32; 64] = [
   -65,  23,  16, -15, -56, -34,   2,  13,
    29,  -1, -20,  -7,  -8,  -4, -38, -29,
    -9,  24,   2, -16, -20,   6,  22, -22,
   -17, -20, -12, -27, -30, -25, -14, -36,
   -49,  -1, -27, -39, -46, -44, -33, -51,
   -14, -14, -22, -46, -44, -30, -15, -27,
     1,   7,  -8, -64, -43, -16,   9,   8,
   -15,  36,  12, -54,   8, -28,  24,  14,
];
const EG_KING: [i32; 64] = [
   -74, -35, -18, -18, -11,  15,   4, -17,
   -12,  17,  14,  17,  17,  38,  23,  11,
    10,  17,  23,  15,  20,  45,  44,  13,
    -8,  22,  24,  27,  26,  33,  26,   3,
   -18,  -4,  21,  24,  27,  23,   9, -11,
   -19,  -3,  11,  21,  23,  16,   7,  -9,
   -27, -11,   4,  13,  14,   4,  -5, -17,
   -53, -34, -21, -11, -28, -14, -24, -43,
];

const MG_TABLES: [&[i32; 64]; 6] = [
    &MG_PAWN, &MG_KNIGHT, &MG_BISHOP, &MG_ROOK, &MG_QUEEN, &MG_KING,
];
const EG_TABLES: [&[i32; 64]; 6] = [
    &EG_PAWN, &EG_KNIGHT, &EG_BISHOP, &EG_ROOK, &EG_QUEEN, &EG_KING,
];

#[inline(always)]
pub fn role_idx(r: Role) -> usize {
    match r {
        Role::Pawn => 0,
        Role::Knight => 1,
        Role::Bishop => 2,
        Role::Rook => 3,
        Role::Queen => 4,
        Role::King => 5,
    }
}

/// Fast PeSTO tapered evaluation -- material + piece-square tables with a
/// midgame/endgame phase interpolation.
#[inline]
pub fn pesto(pos: &Chess) -> i32 {
    let board: &Board = pos.board();
    let mut mg_w = 0i32;
    let mut mg_b = 0i32;
    let mut eg_w = 0i32;
    let mut eg_b = 0i32;
    let mut phase = 0i32;

    for sq in board.occupied() {
        let piece = match board.piece_at(sq) {
            Some(p) => p,
            None => continue,
        };
        let pt = role_idx(piece.role);
        let s = u32::from(sq) as usize;
        if piece.color == Color::White {
            let idx = s ^ 56;
            mg_w += MG_VALUE[pt] + MG_TABLES[pt][idx];
            eg_w += EG_VALUE[pt] + EG_TABLES[pt][idx];
        } else {
            mg_b += MG_VALUE[pt] + MG_TABLES[pt][s];
            eg_b += EG_VALUE[pt] + EG_TABLES[pt][s];
        }
        phase += GAME_PHASE_INC[pt];
    }

    let mg_score = mg_w - mg_b;
    let eg_score = eg_w - eg_b;
    let mg_phase = phase.min(24);
    let eg_phase = 24 - mg_phase;
    let mut score = (mg_score * mg_phase + eg_score * eg_phase) / 24;

    // Small tempo bonus for the side to move.
    if pos.turn() == Color::White {
        score += 10;
    } else {
        score -= 10;
    }
    score
}

// ── reflexion_v1 additions ──────────────────────────────────────────────────

const CENTER_SQUARES: [Square; 4] = [Square::D4, Square::E4, Square::D5, Square::E5];
const EXTENDED_CENTER: [Square; 12] = [
    Square::C3, Square::D3, Square::E3, Square::F3,
    Square::C4, Square::F4,
    Square::C5, Square::F5,
    Square::C6, Square::D6, Square::E6, Square::F6,
];

// Minor-piece starting squares used for the development bonus.
const WHITE_MINOR_STARTS: [Square; 4] = [Square::B1, Square::G1, Square::C1, Square::F1];
const BLACK_MINOR_STARTS: [Square; 4] = [Square::B8, Square::G8, Square::C8, Square::F8];

#[inline(always)]
fn pawn_shield_count(board: &Board, color: Color) -> u32 {
    let king = match board.king_of(color) {
        Some(k) => k,
        None => return 0,
    };
    let kf: i32 = king.file() as i32;
    let kr: i32 = king.rank() as i32;
    let dir: i32 = if color == Color::White { 1 } else { -1 };
    let own_pawns = board.pawns() & board.by_color(color);
    let mut count = 0u32;
    for df in -1..=1 {
        let f = kf + df;
        let r = kr + dir;
        if (0..8).contains(&f) && (0..8).contains(&r) {
            let sq = Square::from_coords(
                File::try_from(f as u32).unwrap(),
                Rank::try_from(r as u32).unwrap(),
            );
            if own_pawns.contains(sq) {
                count += 1;
            }
        }
    }
    count
}

fn material_balance(board: &Board) -> i32 {
    let mut score = 0i32;
    // Uses midgame values for the material component.
    for sq in board.occupied() {
        if let Some(piece) = board.piece_at(sq) {
            let v = MG_VALUE[role_idx(piece.role)];
            if piece.color == Color::White { score += v; } else { score -= v; }
        }
    }
    score
}

fn square_attacked_by(pos: &Chess, sq: Square, attacker: Color) -> bool {
    // In shakmaty 0.27, Position::attacks_to takes the board, square, color, occupied.
    let board = pos.board();
    let occ = board.occupied();
    !board.attacks_to(sq, attacker, occ).is_empty()
}

/// The Reflexion-v1 evaluator promoted by Workstream E.
///
/// Inherits PeSTO as the dominant material/positional term, plus the four
/// corrections the Reflexion loop learned from loss PGNs against Stockfish:
///   1. development bonus for minor pieces off their starting squares
///   2. castling reward / king-in-center penalty
///   3. knight-on-rim (a/h file) penalty
///   4. early-queen penalty
///
/// All `reflexion_v1` additions together cap at ~200cp so material stays
/// dominant.
pub fn reflexion_v1(pos: &Chess) -> i32 {
    let board = pos.board();

    // Start from the classic positional_grinder body (material + center attack
    // + extended-center presence + pawn-shield), then add the reflexion terms.
    let mut score = material_balance(board);

    for &sq in &CENTER_SQUARES {
        if square_attacked_by(pos, sq, Color::White) {
            score += 25;
        }
        if square_attacked_by(pos, sq, Color::Black) {
            score -= 25;
        }
    }

    for &sq in &EXTENDED_CENTER {
        if let Some(piece) = board.piece_at(sq) {
            if piece.color == Color::White { score += 8; } else { score -= 8; }
        }
    }

    let wshield = pawn_shield_count(board, Color::White);
    let bshield = pawn_shield_count(board, Color::Black);
    score -= 25 * (3i32.saturating_sub(wshield as i32)).max(0);
    score += 25 * (3i32.saturating_sub(bshield as i32)).max(0);

    // ── REFLEXION ADDITIONS ─────────────────────────────────────────────

    // 1. Development: count how many minor-piece start squares are empty
    //    (or hold something other than their original piece).
    let count_developed = |starts: &[Square; 4], color: Color| -> i32 {
        let mut n = 0i32;
        for &sq in starts {
            let p = board.piece_at(sq);
            let home = match p {
                None => false,
                Some(pc) => {
                    pc.color == color
                        && (pc.role == Role::Knight || pc.role == Role::Bishop)
                }
            };
            if !home { n += 1; }
        }
        n
    };
    let dev_w = count_developed(&WHITE_MINOR_STARTS, Color::White);
    let dev_b = count_developed(&BLACK_MINOR_STARTS, Color::Black);
    score += dev_w * 15;
    score -= dev_b * 15;

    // 2. Castling / king-in-center.
    let fullmove = u32::from(pos.fullmoves()) as i32;
    if let Some(wk) = board.king_of(Color::White) {
        if wk == Square::G1 || wk == Square::C1 {
            score += 40;
        } else if wk == Square::E1 && fullmove > 10 {
            score -= 40;
        }
    }
    if let Some(bk) = board.king_of(Color::Black) {
        if bk == Square::G8 || bk == Square::C8 {
            score -= 40;
        } else if bk == Square::E8 && fullmove > 10 {
            score += 40;
        }
    }

    // 3. Knight-on-rim penalty (a/h files).
    let rim: Bitboard = Bitboard::from(File::A) | Bitboard::from(File::H);
    let white_knights = board.knights() & board.by_color(Color::White);
    let black_knights = board.knights() & board.by_color(Color::Black);
    let w_rim = (white_knights & rim).count() as i32;
    let b_rim = (black_knights & rim).count() as i32;
    score -= w_rim * 20;
    score += b_rim * 20;

    // 4. Early-queen penalty (queen off its home before 3 minors developed
    //    and before move 10).
    let w_queen_home = board.piece_at(Square::D1).map_or(false, |p| {
        p.color == Color::White && p.role == Role::Queen
    });
    let b_queen_home = board.piece_at(Square::D8).map_or(false, |p| {
        p.color == Color::Black && p.role == Role::Queen
    });
    if !w_queen_home && dev_w < 3 && fullmove < 10 { score -= 25; }
    if !b_queen_home && dev_b < 3 && fullmove < 10 { score += 25; }

    score
}

/// Combines the fast PeSTO evaluator with the reflexion_v1 corrections.
/// This is the default evaluator used by the Rust port.
#[inline]
pub fn evaluate(pos: &Chess) -> i32 {
    // The PeSTO PST term subsumes most of positional_grinder's material and
    // center logic; the reflexion additions add the missing concepts
    // (development, castling, rim-knight, early-queen). We combine them
    // with PeSTO as the dominant term.
    pesto(pos) + reflexion_additions(pos)
}

/// Just the reflexion_v1 corrective terms (no PeSTO / no material).
fn reflexion_additions(pos: &Chess) -> i32 {
    let board = pos.board();
    let mut score = 0i32;

    let count_developed = |starts: &[Square; 4], color: Color| -> i32 {
        let mut n = 0i32;
        for &sq in starts {
            let p = board.piece_at(sq);
            let home = match p {
                None => false,
                Some(pc) => {
                    pc.color == color
                        && (pc.role == Role::Knight || pc.role == Role::Bishop)
                }
            };
            if !home { n += 1; }
        }
        n
    };
    let dev_w = count_developed(&WHITE_MINOR_STARTS, Color::White);
    let dev_b = count_developed(&BLACK_MINOR_STARTS, Color::Black);
    score += dev_w * 15;
    score -= dev_b * 15;

    let fullmove = u32::from(pos.fullmoves()) as i32;
    if let Some(wk) = board.king_of(Color::White) {
        if wk == Square::G1 || wk == Square::C1 {
            score += 40;
        } else if wk == Square::E1 && fullmove > 10 {
            score -= 40;
        }
    }
    if let Some(bk) = board.king_of(Color::Black) {
        if bk == Square::G8 || bk == Square::C8 {
            score -= 40;
        } else if bk == Square::E8 && fullmove > 10 {
            score += 40;
        }
    }

    let rim: Bitboard = Bitboard::from(File::A) | Bitboard::from(File::H);
    let white_knights = board.knights() & board.by_color(Color::White);
    let black_knights = board.knights() & board.by_color(Color::Black);
    let w_rim = (white_knights & rim).count() as i32;
    let b_rim = (black_knights & rim).count() as i32;
    score -= w_rim * 20;
    score += b_rim * 20;

    let w_queen_home = board.piece_at(Square::D1).map_or(false, |p| {
        p.color == Color::White && p.role == Role::Queen
    });
    let b_queen_home = board.piece_at(Square::D8).map_or(false, |p| {
        p.color == Color::Black && p.role == Role::Queen
    });
    if !w_queen_home && dev_w < 3 && fullmove < 10 { score -= 25; }
    if !b_queen_home && dev_b < 3 && fullmove < 10 { score += 25; }

    score
}
