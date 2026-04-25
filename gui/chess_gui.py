"""Local chess GUI with human and engine player modes.

Run from the repo root:
    pip install pygame python-chess
    python3 gui/chess_gui.py

Controls:
    Click a piece, then click a target square.
    U  undo last move
    R  reset to starting position
"""

from __future__ import annotations

import os
import queue
import sys
import time
from dataclasses import dataclass

import pygame
import chess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from PlayerClass import Engine, User, discover_engines


SQUARE = 72
BOARD_PX = SQUARE * 8
SIDEBAR_PX = 360
WINDOW_W = BOARD_PX + SIDEBAR_PX
WINDOW_H = BOARD_PX

LIGHT = (240, 217, 181)
DARK = (181, 136, 99)
SELECTED_RGBA = (246, 246, 105, 170)
LEGAL_RGBA = (106, 168, 79, 110)
CAPTURE_RGBA = (200, 60, 60, 130)
LASTMOVE_RGBA = (255, 255, 0, 70)
SIDEBAR_BG = (28, 28, 32)
TEXT = (220, 220, 220)
TEXT_DIM = (140, 140, 150)
BUTTON_BG = (46, 48, 55)
BUTTON_ACTIVE = (70, 98, 140)
BUTTON_HOVER = (58, 62, 72)
BUTTON_BORDER = (95, 98, 110)
ENGINE_DELAY_SECONDS = 2.0
HUMAN_ENGINE_DELAY_SECONDS = 0.35
ENGINE_MOVETIME_MS = 5000

PIECES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "pieces")

# Map (color, piece_type) -> filename stem (e.g. (WHITE, KING) -> 'wK').
_PIECE_FILES = {
    (chess.WHITE, chess.KING):   "wK",
    (chess.WHITE, chess.QUEEN):  "wQ",
    (chess.WHITE, chess.ROOK):   "wR",
    (chess.WHITE, chess.BISHOP): "wB",
    (chess.WHITE, chess.KNIGHT): "wN",
    (chess.WHITE, chess.PAWN):   "wP",
    (chess.BLACK, chess.KING):   "bK",
    (chess.BLACK, chess.QUEEN):  "bQ",
    (chess.BLACK, chess.ROOK):   "bR",
    (chess.BLACK, chess.BISHOP): "bB",
    (chess.BLACK, chess.KNIGHT): "bN",
    (chess.BLACK, chess.PAWN):   "bP",
}


@dataclass
class Button:
    key: str
    rect: pygame.Rect
    label: str
    active: bool = False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, mouse_pos: tuple[int, int]) -> None:
        color = BUTTON_ACTIVE if self.active else BUTTON_HOVER if self.rect.collidepoint(mouse_pos) else BUTTON_BG
        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        pygame.draw.rect(surface, BUTTON_BORDER, self.rect, width=1, border_radius=6)
        label = font.render(self.label, True, TEXT)
        surface.blit(
            label,
            (
                self.rect.centerx - label.get_width() // 2,
                self.rect.centery - label.get_height() // 2,
            ),
        )


def square_to_xy(sq: chess.Square) -> tuple[int, int]:
    """Square 0..63 (a1=0, h8=63) -> top-left pixel (white POV)."""
    f = chess.square_file(sq)
    r = chess.square_rank(sq)
    return f * SQUARE, (7 - r) * SQUARE


def xy_to_square(x: int, y: int) -> chess.Square | None:
    if not (0 <= x < BOARD_PX and 0 <= y < BOARD_PX):
        return None
    return chess.square(x // SQUARE, 7 - (y // SQUARE))


def draw_board(surface: pygame.Surface) -> None:
    for r in range(8):
        for f in range(8):
            color = LIGHT if (r + f) % 2 == 0 else DARK
            pygame.draw.rect(surface, color, (f * SQUARE, r * SQUARE, SQUARE, SQUARE))


def fill_square(surface: pygame.Surface, sq: chess.Square, rgba: tuple[int, int, int, int]) -> None:
    x, y = square_to_xy(sq)
    s = pygame.Surface((SQUARE, SQUARE), pygame.SRCALPHA)
    s.fill(rgba)
    surface.blit(s, (x, y))


def draw_legal_marker(surface: pygame.Surface, sq: chess.Square, is_capture: bool) -> None:
    """Lichess-style: dot on empty, ring on capture."""
    x, y = square_to_xy(sq)
    cx, cy = x + SQUARE // 2, y + SQUARE // 2
    s = pygame.Surface((SQUARE, SQUARE), pygame.SRCALPHA)
    if is_capture:
        pygame.draw.circle(s, (0, 0, 0, 90), (SQUARE // 2, SQUARE // 2), SQUARE // 2 - 2, width=4)
    else:
        pygame.draw.circle(s, (0, 0, 0, 80), (SQUARE // 2, SQUARE // 2), SQUARE // 7)
    surface.blit(s, (x, y))


def build_piece_cache() -> dict:
    """Load each piece PNG from gui/assets/pieces/ and scale to SQUARE px.

    Pieces are drawn slightly inset so they don't crowd the square edges.
    """
    if not os.path.isdir(PIECES_DIR):
        raise FileNotFoundError(
            f"piece assets not found at {PIECES_DIR}. "
            f"Run: python3 gui/setup_pieces.py"
        )
    inset = max(2, SQUARE // 12)
    target = SQUARE - 2 * inset
    cache: dict = {}
    for key, stem in _PIECE_FILES.items():
        path = os.path.join(PIECES_DIR, f"{stem}.png")
        raw = pygame.image.load(path).convert_alpha()
        scaled = pygame.transform.smoothscale(raw, (target, target))
        # Center the scaled piece on a transparent SQUARE×SQUARE tile so we
        # can blit at the square's top-left without offsetting per-piece.
        tile = pygame.Surface((SQUARE, SQUARE), pygame.SRCALPHA)
        tile.blit(scaled, (inset, inset))
        cache[key] = tile
    return cache


def draw_pieces(surface: pygame.Surface, board: chess.Board, cache: dict) -> None:
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if not piece:
            continue
        x, y = square_to_xy(sq)
        surface.blit(cache[(piece.color, piece.piece_type)], (x, y))


def draw_coords(surface: pygame.Surface, font: pygame.font.Font) -> None:
    for f in range(8):
        c = LIGHT if (f + 7) % 2 == 0 else DARK
        label = font.render("abcdefgh"[f], True, _contrast(c))
        surface.blit(label, (f * SQUARE + SQUARE - label.get_width() - 4, BOARD_PX - label.get_height() - 2))
    for r in range(8):
        c = LIGHT if (7 - r) % 2 == 0 else DARK
        label = font.render(str(8 - r), True, _contrast(c))
        surface.blit(label, (3, r * SQUARE + 2))


def _contrast(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    r, g, b = rgb
    return (40, 40, 40) if (r + g + b) > 450 else (230, 230, 230)


def status_text(board: chess.Board) -> str:
    if board.is_checkmate():
        winner = "Black" if board.turn == chess.WHITE else "White"
        return f"Checkmate — {winner} wins"
    if board.is_stalemate():
        return "Stalemate"
    if board.is_insufficient_material():
        return "Draw — insufficient material"
    if board.is_seventyfive_moves():
        return "Draw — 75-move rule"
    if board.is_fivefold_repetition():
        return "Draw — fivefold repetition"
    side = "White" if board.turn == chess.WHITE else "Black"
    return f"{side} to move" + (" (check)" if board.is_check() else "")


def draw_text(surface: pygame.Surface, font: pygame.font.Font, text: str, color: tuple[int, int, int], pos: tuple[int, int], max_width: int) -> None:
    """Render one clipped text line so long engine output stays in the sidebar."""
    clipped = text
    while clipped and font.size(clipped)[0] > max_width:
        clipped = clipped[:-2]
    if clipped != text:
        clipped = clipped.rstrip() + "…"
    surface.blit(font.render(clipped, True, color), pos)


def player_for_turn(board: chess.Board, mode: str, white_engine: Engine, black_engine: Engine) -> User | Engine:
    if mode == "two_players":
        return User("White") if board.turn == chess.WHITE else User("Black")
    if mode == "human_engine":
        return User("White") if board.turn == chess.WHITE else black_engine
    return white_engine if board.turn == chess.WHITE else black_engine


def mode_label(mode: str) -> str:
    return {
        "two_players": "2 Players",
        "human_engine": "1 Player + Engine",
        "engine_engine": "2 Engines",
    }[mode]


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("Chess")
    clock = pygame.time.Clock()

    piece_cache = build_piece_cache()
    status_font = pygame.font.SysFont("Helvetica,Arial,sans-serif", 18)
    coord_font = pygame.font.SysFont("Helvetica,Arial,sans-serif", 12, bold=True)

    board = chess.Board()
    engine_options = discover_engines(REPO_ROOT)
    white_engine = Engine(engine_options, 0, "White engine")
    black_engine = Engine(engine_options, 1 if len(engine_options) > 1 else 0, "Black engine")
    mode = "two_players"
    selected: chess.Square | None = None
    legal_targets: dict[chess.Square, chess.Move] = {}
    last_move: chess.Move | None = None
    move_history: list[str] = []
    pending_engine_results: queue.Queue[tuple[Engine, chess.Move | None, str | None]] = queue.Queue()
    next_engine_at = 0.0
    engine_request_fen: str | None = None
    dropdown_open: str | None = None
    engines_paused = False

    def reset_game() -> None:
        nonlocal selected, legal_targets, last_move, next_engine_at, engine_request_fen
        board.reset()
        move_history.clear()
        last_move = None
        selected = None
        legal_targets = {}
        next_engine_at = time.time() + 0.15
        engine_request_fen = None

    def set_mode(new_mode: str) -> None:
        nonlocal mode, engines_paused, dropdown_open
        mode = new_mode
        engines_paused = False
        dropdown_open = None
        reset_game()

    def push_move(move: chess.Move) -> None:
        nonlocal last_move, selected, legal_targets, next_engine_at
        san = board.san(move)
        board.push(move)
        last_move = move
        move_history.append(san)
        selected = None
        legal_targets = {}
        delay = ENGINE_DELAY_SECONDS if mode == "engine_engine" else HUMAN_ENGINE_DELAY_SECONDS
        next_engine_at = time.time() + delay

    def select(sq: chess.Square) -> None:
        nonlocal selected, legal_targets
        piece = board.piece_at(sq)
        if piece and piece.color == board.turn:
            selected = sq
            legal_targets = {}
            for m in board.legal_moves:
                if m.from_square == sq:
                    # Collapse promotion variants — auto-queen on click. A
                    # promotion picker is the natural follow-up.
                    if m.to_square not in legal_targets or m.promotion == chess.QUEEN:
                        legal_targets[m.to_square] = m
        else:
            selected = None
            legal_targets = {}

    def attempt_move(target: chess.Square) -> bool:
        move = legal_targets.get(target)
        if move is None:
            return False
        push_move(move)
        return True

    def request_engine_move(engine: Engine) -> None:
        nonlocal engine_request_fen
        engine_request_fen = board.fen()

        def on_result(move: chess.Move | None, error: str | None) -> None:
            pending_engine_results.put((engine, move, error))

        engine.request_move(board.copy(stack=False), ENGINE_MOVETIME_MS, on_result)

    def engine_name(engine: Engine) -> str:
        return engine.current_option.name if engine.current_option else "none"

    def build_sidebar_buttons() -> list[Button]:
        x0 = BOARD_PX + 16
        y = 86
        w = SIDEBAR_PX - 32
        buttons = [
            Button("mode_two_players", pygame.Rect(x0, y, w, 28), "2 Players", mode == "two_players"),
            Button("mode_human_engine", pygame.Rect(x0, y + 34, w, 28), "1 Player + Engine", mode == "human_engine"),
            Button("mode_engine_engine", pygame.Rect(x0, y + 68, w, 28), "2 Engines", mode == "engine_engine"),
        ]
        y += 114
        buttons.append(Button("white_engine", pygame.Rect(x0, y, w, 28), f"White: {engine_name(white_engine)}"))
        buttons.append(Button("black_engine", pygame.Rect(x0, y + 34, w, 28), f"Black: {engine_name(black_engine)}"))
        buttons.append(Button("pause_engines", pygame.Rect(x0, y + 68, w, 28), "Resume Engines" if engines_paused else "Pause Engines", mode == "engine_engine" and engines_paused))
        return buttons

    def build_dropdown_buttons() -> list[Button]:
        if dropdown_open is None:
            return []
        x0 = BOARD_PX + 16
        w = SIDEBAR_PX - 32
        start_y = 314
        selected_index = white_engine.index if dropdown_open == "white_engine" else black_engine.index
        buttons: list[Button] = []
        for i, option in enumerate(engine_options):
            buttons.append(Button(f"engine_option:{i}", pygame.Rect(x0, start_y + i * 26, w, 24), option.name, i == selected_index))
        return buttons

    def handle_sidebar_click(pos: tuple[int, int]) -> bool:
        nonlocal next_engine_at, engine_request_fen, dropdown_open, engines_paused
        for button in build_dropdown_buttons():
            if button.rect.collidepoint(pos):
                index = int(button.key.split(":", 1)[1])
                if dropdown_open == "white_engine":
                    white_engine.set_index(index)
                elif dropdown_open == "black_engine":
                    black_engine.set_index(index)
                dropdown_open = None
                reset_game()
                return True

        for button in build_sidebar_buttons():
            if not button.rect.collidepoint(pos):
                continue
            if button.key == "mode_two_players":
                set_mode("two_players")
            elif button.key == "mode_human_engine":
                set_mode("human_engine")
            elif button.key == "mode_engine_engine":
                set_mode("engine_engine")
            elif button.key == "white_engine":
                dropdown_open = None if dropdown_open == "white_engine" else "white_engine"
            elif button.key == "black_engine":
                dropdown_open = None if dropdown_open == "black_engine" else "black_engine"
            elif button.key == "pause_engines" and mode == "engine_engine":
                engines_paused = not engines_paused
                dropdown_open = None
            next_engine_at = time.time() + 0.15
            engine_request_fen = None
            return True
        if pos[0] >= BOARD_PX:
            dropdown_open = None
            return True
        return pos[0] >= BOARD_PX

    running = True
    while running:
        while True:
            try:
                result_engine, result_move, result_error = pending_engine_results.get_nowait()
            except queue.Empty:
                break
            if result_error:
                result_engine.add_log(f"! {result_error}")
                next_engine_at = time.time() + ENGINE_DELAY_SECONDS
            elif result_move and not board.is_game_over() and board.fen() == engine_request_fen and result_move in board.legal_moves:
                push_move(result_move)
            engine_request_fen = None

        current_player = player_for_turn(board, mode, white_engine, black_engine)
        if (
            current_player.is_engine()
            and not board.is_game_over()
            and not current_player.thinking()
            and engine_request_fen is None
            and time.time() >= next_engine_at
            and not (mode == "engine_engine" and engines_paused)
        ):
            request_engine_move(current_player)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False

            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_u and board.move_stack:
                    if current_player.is_engine() and current_player.thinking():
                        continue
                    board.pop()
                    if move_history:
                        move_history.pop()
                    last_move = board.peek() if board.move_stack else None
                    selected = None
                    legal_targets = {}
                elif ev.key == pygame.K_r:
                    reset_game()

            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if handle_sidebar_click(ev.pos):
                    continue
                if board.is_game_over():
                    continue
                if player_for_turn(board, mode, white_engine, black_engine).is_engine():
                    continue
                sq = xy_to_square(*ev.pos)
                if sq is None:
                    continue
                if selected is None:
                    select(sq)
                elif sq == selected:
                    selected = None
                    legal_targets = {}
                elif sq in legal_targets:
                    attempt_move(sq)
                else:
                    select(sq)

        board_surf = pygame.Surface((BOARD_PX, BOARD_PX))
        draw_board(board_surf)
        if last_move:
            fill_square(board_surf, last_move.from_square, LASTMOVE_RGBA)
            fill_square(board_surf, last_move.to_square, LASTMOVE_RGBA)
        if selected is not None:
            fill_square(board_surf, selected, SELECTED_RGBA)
            for t in legal_targets:
                draw_legal_marker(board_surf, t, board.is_capture(legal_targets[t]))
        draw_pieces(board_surf, board, piece_cache)
        draw_coords(board_surf, coord_font)

        screen.fill(SIDEBAR_BG)
        screen.blit(board_surf, (0, 0))

        x0 = BOARD_PX + 16
        max_text_width = SIDEBAR_PX - 32
        y = 16
        draw_text(screen, status_font, status_text(board), TEXT, (x0, y), max_text_width)
        y += 32
        draw_text(screen, status_font, f"Move {board.fullmove_number} • {mode_label(mode)}", TEXT_DIM, (x0, y), max_text_width)
        y += 28

        buttons = build_sidebar_buttons()
        mouse_pos = pygame.mouse.get_pos()
        for button in buttons:
            button.draw(screen, status_font, mouse_pos)
        y = 306

        active_player = player_for_turn(board, mode, white_engine, black_engine)
        if mode == "engine_engine" and engines_paused:
            draw_text(screen, status_font, "Engine match paused", TEXT, (x0, y), max_text_width)
        elif active_player.is_engine() and active_player.thinking():
            draw_text(screen, status_font, "Engine thinking…", TEXT, (x0, y), max_text_width)
        else:
            draw_text(screen, status_font, f"Turn: {active_player.label()}", TEXT, (x0, y), max_text_width)
        y += 30

        screen.blit(status_font.render("Moves", True, TEXT_DIM), (x0, y))
        y += 22
        # Show last ~8 plies, paired by move number.
        recent = move_history[-16:]
        start_full_move = (len(move_history) - len(recent)) // 2 + 1
        # If we trimmed an odd number of plies, the first shown ply is Black's.
        first_is_black = (len(move_history) - len(recent)) % 2 == 1
        i = 0
        n = start_full_move
        while i < len(recent):
            if i == 0 and first_is_black:
                line = f"{n}. ... {recent[i]}"
                i += 1
            else:
                white = recent[i]
                black = recent[i + 1] if i + 1 < len(recent) else ""
                line = f"{n}. {white}  {black}".rstrip()
                i += 2
            n += 1
            draw_text(screen, status_font, line, TEXT, (x0, y), max_text_width)
            y += 20
            if y > 410:
                break

        y = 420
        screen.blit(status_font.render("Engine output", True, TEXT_DIM), (x0, y))
        y += 22
        log_sources = [white_engine, black_engine] if mode == "engine_engine" else [black_engine]
        if mode == "two_players":
            log_sources = [white_engine, black_engine]
        lines: list[str] = []
        for engine in log_sources:
            for line in engine.log_lines(5):
                lines.append(f"{engine.name[:1]} {line}")
        if not lines:
            lines = ["No engine output yet"]
        for line in lines[-6:]:
            draw_text(screen, coord_font, line, TEXT if line != "No engine output yet" else TEXT_DIM, (x0, y), max_text_width)
            y += 17

        help_y = BOARD_PX - 44
        draw_text(screen, status_font, "U: undo   R: reset", TEXT_DIM, (x0, help_y), max_text_width)
        draw_text(screen, status_font, "Use dropdowns to pick engines", TEXT_DIM, (x0, help_y + 20), max_text_width)

        for button in build_dropdown_buttons():
            button.draw(screen, coord_font, mouse_pos)

        pygame.display.flip()
        clock.tick(60)

    white_engine.stop()
    black_engine.stop()
    pygame.quit()


if __name__ == "__main__":
    main()
