//! UCI entry point for the Strategy1 Rust port.
//!
//! Implements the subset of UCI that the arena actually uses:
//!   uci / isready / ucinewgame / position (startpos | fen) [moves ...] /
//!   go (wtime/btime/winc/binc/movetime/depth) / stop / quit

mod eval;
mod search;

use std::io::{self, BufRead, Write};

use shakmaty::fen::Fen;
use shakmaty::uci::Uci;
use shakmaty::{CastlingMode, Chess, Color, Position};

use crate::search::Searcher;

const ENGINE_NAME: &str = "Strategy1-Rust";
const ENGINE_AUTHOR: &str = "CubistTeam";
const DEFAULT_TIME_MS: u64 = 2000;

struct Engine {
    pos: Chess,
    searcher: Searcher,
}

impl Engine {
    fn new() -> Self {
        Engine { pos: Chess::default(), searcher: Searcher::new() }
    }

    fn handle_uci(&self) {
        println!("id name {}", ENGINE_NAME);
        println!("id author {}", ENGINE_AUTHOR);
        println!("uciok");
        io::stdout().flush().ok();
    }

    fn handle_isready(&self) {
        println!("readyok");
        io::stdout().flush().ok();
    }

    fn handle_ucinewgame(&mut self) {
        self.pos = Chess::default();
        self.searcher.reset();
    }

    fn handle_position(&mut self, tokens: &[&str]) {
        if tokens.is_empty() {
            return;
        }

        let mut idx = 0usize;
        if tokens[idx] == "startpos" {
            self.pos = Chess::default();
            idx += 1;
        } else if tokens[idx] == "fen" {
            idx += 1;
            let mut fen_parts = Vec::new();
            while idx < tokens.len() && tokens[idx] != "moves" {
                fen_parts.push(tokens[idx]);
                idx += 1;
            }
            let fen_str = fen_parts.join(" ");
            match fen_str.parse::<Fen>() {
                Ok(fen) => match fen.into_position::<Chess>(CastlingMode::Standard) {
                    Ok(pos) => self.pos = pos,
                    Err(_) => return,
                },
                Err(_) => return,
            }
        } else {
            return;
        }

        if idx < tokens.len() && tokens[idx] == "moves" {
            idx += 1;
            while idx < tokens.len() {
                let tok = tokens[idx];
                if let Ok(uci) = tok.parse::<Uci>() {
                    if let Ok(m) = uci.to_move(&self.pos) {
                        self.pos.play_unchecked(&m);
                    }
                }
                idx += 1;
            }
        }
    }

    fn parse_time(&self, tokens: &[&str]) -> (u64, u64, i16) {
        // Returns (soft_ms, hard_ms, max_depth).
        let mut params: std::collections::HashMap<&str, i64> =
            std::collections::HashMap::new();
        let mut i = 0;
        while i + 1 < tokens.len() {
            if let Ok(v) = tokens[i + 1].parse::<i64>() {
                params.insert(tokens[i], v);
                i += 2;
            } else {
                i += 1;
            }
        }

        if let Some(&d) = params.get("depth") {
            return (10_000_000, 10_000_000, d.max(1) as i16);
        }

        if let Some(&mt) = params.get("movetime") {
            let t = (mt as u64).max(10);
            // Small safety margin so we don't overrun the arena's clock.
            let hard = t.saturating_sub(30).max(10);
            return (hard, hard, 64);
        }

        let (time_left, incr) = match self.pos.turn() {
            Color::White => (
                params.get("wtime").copied().unwrap_or(0),
                params.get("winc").copied().unwrap_or(0),
            ),
            Color::Black => (
                params.get("btime").copied().unwrap_or(0),
                params.get("binc").copied().unwrap_or(0),
            ),
        };

        if time_left > 0 {
            // Same time-split recipe as the Python engine: 1/30th of remaining
            // + 80% of increment, hard-capped under the total clock.
            let alloc = (time_left / 30) + (incr as f64 * 0.8) as i64;
            let capped = alloc.min((time_left - 100).max(50));
            let soft = capped.max(50) as u64;
            return (soft, soft, 64);
        }

        (DEFAULT_TIME_MS, DEFAULT_TIME_MS, 64)
    }

    fn handle_go(&mut self, tokens: &[&str]) {
        let (soft, hard, max_depth) = self.parse_time(tokens);
        match self.searcher.go(&self.pos, soft, hard, max_depth, true) {
            Some(m) => println!("bestmove {}", Uci::from_standard(&m)),
            None => println!("bestmove 0000"),
        }
        io::stdout().flush().ok();
    }
}

fn main() {
    let mut engine = Engine::new();
    let stdin = io::stdin();

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => break,
        };
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let tokens: Vec<&str> = line.split_whitespace().collect();
        let cmd = tokens[0];
        match cmd {
            "uci" => engine.handle_uci(),
            "isready" => engine.handle_isready(),
            "ucinewgame" => engine.handle_ucinewgame(),
            "position" => engine.handle_position(&tokens[1..]),
            "go" => engine.handle_go(&tokens[1..]),
            "stop" => {} // we don't support async stop; ignore
            "quit" => break,
            _ => {} // ignore unknown commands
        }
    }
}
