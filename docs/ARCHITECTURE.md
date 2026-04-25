# ARCHITECTURE: CUBIST SYSTEMATIC HACKATHON

## 1. MISSION PROTOCOL
This repository is a quantitative research experiment. We are evaluating autonomous AI software engineering methodologies through the lens of chess engine development.

## 2. THE TWO-PART PIVOT
1. **The Research Phase (Current):** Parallel dispatch of four methodologies (Zero-Shot, TDD, Toy-to-Scale, Megaprompt) in Python. Goal: Deterministic selection of the optimal AI workflow using the AMES calculator.
2. **The Optimization Phase (Upcoming):** Pivot the winning logic to Rust/C++ for maximum NPS and implement risk-managed search tree allocation.

## 3. ROLES & BOUNDARIES
- **Lead Architect (Gemini CLI):**
  - Defines `STRATEGY.md` briefs.
  - Enforces infrastructure hardening and resource limits.
  - Performs AMES efficacy analysis.
  - **STRICT RULE:** Architect NEVER writes implementation code.
- **Subagents (Implementation Agents):**
  - Receive a `STRATEGY.md` and a subagent template.
  - Have total tech-stack autonomy (Python, Rust, Go, etc.).
  - MUST fulfill the `build.sh` and `run.sh` execution contract.
  - MUST update their `DISCOVERY.md` using the YAML schema after every match.

## 4. ENGINEERING GUARDRAILS (HARD LIMITS)
- **Time:** Hard 2.0s per-move timeout (Instant forfeit on breach).
- **Memory:** 256MB peak consumption cap.
- **Math:** Ratings use the Fishtest Trinomial Model with Multi-Anchor calibration (1000, 1200, 1500 Elo).

## 5. THE ROADMAP
- **[Phase 1] Automated Combat:** Subagents implementation -> Hardened Arena -> AMES Score.
- **[Phase 2] Alpha Capture:** Winning logic -> Rust/C++ rewrite -> High NPS.
- **[Phase 3] Risk Management:** Clock ms as capital -> Search depth as risk allocation.
