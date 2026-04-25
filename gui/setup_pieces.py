"""One-time setup: download Cburnett chess piece PNGs from Wikimedia
into ``gui/assets/pieces/``.

These are the same pieces python-chess and Lichess use (Cburnett, CC-BY-SA).
Run once:

    python3 gui/setup_pieces.py
"""

from __future__ import annotations

import hashlib
import os
import sys
import time
import urllib.request


PIECE_SIZE = 256  # source PNG resolution; scaled down at render time

# Map our (color, piece-letter) -> Wikimedia filename (Cburnett, transparent bg).
# 'l' = light/white silhouette, 'd' = dark/black silhouette.
WIKIMEDIA = {
    ("w", "K"): "Chess_klt45.svg",
    ("w", "Q"): "Chess_qlt45.svg",
    ("w", "R"): "Chess_rlt45.svg",
    ("w", "B"): "Chess_blt45.svg",
    ("w", "N"): "Chess_nlt45.svg",
    ("w", "P"): "Chess_plt45.svg",
    ("b", "K"): "Chess_kdt45.svg",
    ("b", "Q"): "Chess_qdt45.svg",
    ("b", "R"): "Chess_rdt45.svg",
    ("b", "B"): "Chess_bdt45.svg",
    ("b", "N"): "Chess_ndt45.svg",
    ("b", "P"): "Chess_pdt45.svg",
}

# Wikimedia requires an identifying User-Agent.
USER_AGENT = "ChessGUI/0.1 (https://github.com/Cubist-Hackathon-2026)"


def thumbnail_url(svg_filename: str, size: int) -> str:
    h = hashlib.md5(svg_filename.encode()).hexdigest()
    return (
        f"https://upload.wikimedia.org/wikipedia/commons/thumb/"
        f"{h[0]}/{h[:2]}/{svg_filename}/{size}px-{svg_filename}.png"
    )


def main() -> int:
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "pieces")
    os.makedirs(out_dir, exist_ok=True)

    for (color, piece), svg_name in WIKIMEDIA.items():
        out_path = os.path.join(out_dir, f"{color}{piece}.png")
        if os.path.exists(out_path):
            print(f"  skip {color}{piece} (exists)")
            continue
        url = thumbnail_url(svg_name, PIECE_SIZE)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
        except Exception as e:
            print(f"  FAIL {color}{piece}: {e}", file=sys.stderr)
            return 1
        with open(out_path, "wb") as f:
            f.write(data)
        print(f"  got  {color}{piece}  ({len(data)} bytes)")
        time.sleep(0.5)  # be polite to Wikimedia's edge cache

    print(f"Done. {len(WIKIMEDIA)} pieces in {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
