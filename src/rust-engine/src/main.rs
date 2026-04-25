use shakmaty::{Chess, Move, Position, Role, Color};
use shakmaty::uci::Uci;
use std::io::{self, BufRead};

fn evaluate(pos: &Chess) -> i32 {
    if pos.is_game_over() {
        if pos.is_checkmate() {
            return -30000;
        }
        return 0; // Draw/Stalemate
    }

    let board = pos.board();
    let mut score = 0;
    
    for (square, piece) in board.pieces() {
        let val = match piece.role {
            Role::Pawn => 100,
            Role::Knight => 320,
            Role::Bishop => 330,
            Role::Rook => 500,
            Role::Queen => 900,
            Role::King => 20000,
        };
        if piece.color == pos.turn() {
            score += val;
        } else {
            score -= val;
        }
    }
    
    // Add a tiny bit of mobility bonus
    score += pos.legal_moves().len() as i32;
    
    score
}

fn negamax(pos: &Chess, depth: i32, mut alpha: i32, beta: i32) -> i32 {
    if depth <= 0 || pos.is_game_over() {
        return evaluate(pos);
    }

    let moves = pos.legal_moves();
    let mut best_score = i32::MIN + 1000;

    for m in moves {
        let mut next_pos = pos.clone();
        next_pos.play_unchecked(&m);
        let score = -negamax(&next_pos, depth - 1, -beta, -alpha);
        
        if score > best_score {
            best_score = score;
        }
        if score > alpha {
            alpha = score;
        }
        if alpha >= beta {
            break;
        }
    }
    best_score
}

fn main() {
    let mut pos = Chess::default();
    let stdin = io::stdin();
    let mut lines = stdin.lock().lines();

    while let Some(Ok(line)) = lines.next() {
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.is_empty() { continue; }

        match parts[0] {
            "uci" => {
                println!("id name ZeroShotRustEngine");
                println!("id author GeminiCLI");
                println!("uciok");
            }
            "isready" => println!("readyok"),
            "ucinewgame" => pos = Chess::default(),
            "position" => {
                if parts.len() > 1 && parts[1] == "startpos" {
                    pos = Chess::default();
                    if parts.len() > 2 && parts[2] == "moves" {
                        for m_str in &parts[3..] {
                            if let Ok(uci_move) = m_str.parse::<Uci>() {
                                if let Ok(m) = uci_move.to_move(&pos) {
                                    pos.play_unchecked(&m);
                                }
                            }
                        }
                    }
                } else if parts.len() > 1 && parts[1] == "fen" {
                    // Simplified FEN parsing for this example
                    let fen_str = parts[2..].join(" ");
                    // Note: This would need more robust parsing if we had multiple "moves" after FEN
                }
            }
            "go" => {
                let moves = pos.legal_moves();
                if moves.is_empty() {
                    println!("bestmove (none)");
                    continue;
                }

                let mut best_move = moves[0].clone();
                let mut best_score = i32::MIN + 1000;
                let depth = 4; // Sufficient for a zero-shot demo

                for m in moves {
                    let mut next_pos = pos.clone();
                    next_pos.play_unchecked(&m);
                    let score = -negamax(&next_pos, depth - 1, i32::MIN + 1000, i32::MAX - 1000);
                    if score > best_score {
                        best_score = score;
                        best_move = m;
                    }
                }
                println!("bestmove {}", Uci::from_move(&best_move));
            }
            "quit" => break,
            _ => {}
        }
    }
}
