"""Two-player local chess GUI.

No engine yet — this is the pure display + interaction layer. Once a
`Player` abstraction exists, the move-input branch (mouse clicks) becomes
one implementation and an engine `Player` becomes another.

Run from the repo root:
    pip install pygame
    python3 gui/chess_gui.py

Controls:
    Click a piece, then click a target square.
    U  undo last move
    R  reset to starting position
"""

from __future__ import annotations

import os

import pygame
import chess


SQUARE = 72
BOARD_PX = SQUARE * 8
SIDEBAR_PX = 240
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


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("Chess")
    clock = pygame.time.Clock()

    piece_cache = build_piece_cache()
    status_font = pygame.font.SysFont("Helvetica,Arial,sans-serif", 18)
    coord_font = pygame.font.SysFont("Helvetica,Arial,sans-serif", 12, bold=True)

    board = chess.Board()
    selected: chess.Square | None = None
    legal_targets: dict[chess.Square, chess.Move] = {}
    last_move: chess.Move | None = None
    move_history: list[str] = []

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
        nonlocal last_move, selected, legal_targets
        move = legal_targets.get(target)
        if move is None:
            return False
        san = board.san(move)
        board.push(move)
        last_move = move
        move_history.append(san)
        selected = None
        legal_targets = {}
        return True

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False

            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_u and board.move_stack:
                    board.pop()
                    if move_history:
                        move_history.pop()
                    last_move = board.peek() if board.move_stack else None
                    selected = None
                    legal_targets = {}
                elif ev.key == pygame.K_r:
                    board.reset()
                    move_history.clear()
                    last_move = None
                    selected = None
                    legal_targets = {}

            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if board.is_game_over():
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
        y = 16
        screen.blit(status_font.render(status_text(board), True, TEXT), (x0, y))
        y += 32
        screen.blit(status_font.render(f"Move {board.fullmove_number}", True, TEXT_DIM), (x0, y))
        y += 28

        screen.blit(status_font.render("Moves", True, TEXT_DIM), (x0, y))
        y += 22
        # Show last ~14 plies, paired by move number.
        recent = move_history[-28:]
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
            screen.blit(status_font.render(line, True, TEXT), (x0, y))
            y += 20
            if y > BOARD_PX - 60:
                break

        help_y = BOARD_PX - 44
        screen.blit(status_font.render("U: undo   R: reset", True, TEXT_DIM), (x0, help_y))
        screen.blit(status_font.render("Click piece, then target", True, TEXT_DIM), (x0, help_y + 20))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
