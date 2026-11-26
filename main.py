#!/usr/bin/env python3
"""Render a one-image letter inviting the AI judge to visit my house.

Pure Python standard library only: no Pillow, no font files on disk, no
network, no randomness. The graded sandbox runs a stock python:3.13-slim
image (no Pillow, no fonts) with the repository mounted read-only at
/bot, so this program draws with its own software rasterizer and a small
built-in 5x7 bitmap font, and writes only to $MAKEFUN_OUTPUT_DIR. It
never writes beside itself, so a read-only /bot cannot fail the run.
"""
import math
import os
import struct
import zlib
from pathlib import Path

W = H = 1024
CREAM = (247, 238, 221)
INK = (59, 42, 30)
TERRA = (176, 84, 52)
TERRA_DARK = (140, 62, 36)
TERRA_LIGHT = (205, 122, 88)
GOLD = (201, 162, 74)
LEAF = (96, 128, 74)
SEAL = (150, 48, 44)
SEAL_DARK = (110, 32, 30)
SEAL_LIGHT = (196, 96, 88)
SUN = (232, 178, 92)
WINDOW = (251, 214, 140)
HOUSE_FILL = (250, 240, 216)
ROOF_FILL = (233, 196, 158)
STONE = (214, 190, 158)


class Canvas:
    """An RGB image held as raw bytes, with a tiny software rasterizer."""

    def __init__(self):
        self.px = bytearray(bytes(CREAM) * (W * H))

    def set(self, x, y, color):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            self.px[i] = color[0]
            self.px[i + 1] = color[1]
            self.px[i + 2] = color[2]

    def rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(W, x + w)
        y1 = min(H, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * W + x0) * 3
            self.px[i:i + 3 * (x1 - x0)] = row

    def rect_outline(self, x0, y0, x1, y1, color, width):
        self.rect(x0, y0, x1 - x0, width, color)
        self.rect(x0, y1 - width, x1 - x0, width, color)
        self.rect(x0, y0, width, y1 - y0, color)
        self.rect(x1 - width, y0, width, y1 - y0, color)

    def line(self, x0, y0, x1, y1, color, width=1):
        """Bresenham line; width>1 draws a small square at each step."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        r = width // 2
        while True:
            self.rect(x0 - r, y0 - r, width, width, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle_fill(self, cx, cy, r, color):
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)

    def circle_outline(self, cx, cy, r, color, width=1):
        x, y, d = 0, r, 1 - r
        while x <= y:
            for px, py in (
                (cx + x, cy + y), (cx - x, cy + y),
                (cx + x, cy - y), (cx - x, cy - y),
                (cx + y, cy + x), (cx - y, cy + x),
                (cx + y, cy - x), (cx - y, cy - x),
            ):
                self.rect(px - width // 2, py - width // 2, width, width, color)
            x += 1
            if d < 0:
                d += 2 * x + 1
            else:
                y -= 1
                d += 2 * (x - y) + 1

    def ellipse_fill(self, cx, cy, rx, ry, color):
        for dy in range(-ry, ry + 1):
            t = 1.0 - (dy * dy) / float(ry * ry)
            dx = int(rx * math.sqrt(max(0.0, t)))
            self.rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)

    def ellipse_outline(self, cx, cy, rx, ry, color, width=1):
        prev = None
        for deg in range(0, 361, 6):
            a = math.radians(deg)
            pt = (round(cx + rx * math.cos(a)), round(cy + ry * math.sin(a)))
            if prev is not None:
                self.line(prev[0], prev[1], pt[0], pt[1], color, width)
            prev = pt

    def polygon_fill(self, pts, color):
        """Scanline fill of a simple polygon (even-odd)."""
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(H, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.rect(int(math.ceil(xs[i])), y,
                          int(math.floor(xs[i + 1])) - int(math.ceil(xs[i])) + 1,
                          1, color)

    def polygon_outline(self, pts, color, width=1):
        n = len(pts)
        for i in range(n):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            self.line(x0, y0, x1, y1, color, width)

    def heart(self, cx, cy, s, color):
        r = s * 0.36
        self.circle_fill(round(cx - s * 0.30), round(cy - s * 0.10), round(r), color)
        self.circle_fill(round(cx + s * 0.30), round(cy - s * 0.10), round(r), color)
        self.polygon_fill([
            (round(cx - s * 0.58), round(cy - s * 0.05)),
            (round(cx + s * 0.58), round(cy - s * 0.05)),
            (cx, round(cy + s * 0.60)),
        ], color)

# A 5x7 bitmap font, drawn from the classic seven-row letter shapes.
# Each glyph is seven rows of five pixels, "#" on and "." off.
FONT = {
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    "(": ("...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"),
    ")": ("##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."),
    ",": (".....", ".....", ".....", ".....", ".....", ".##..", ".#..."),
    "-": (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "—": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "a": (".....", ".....", ".####", "....#", ".####", "#...#", ".###."),
    "b": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    "c": (".....", ".....", ".####", "#....", "#....", "#....", ".####"),
    "d": ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".###."),
    "e": (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    "f": ("..##.", ".#..#", ".#...", "####.", ".#...", ".#...", ".#..."),
    "g": (".####", "#...#", "#...#", ".####", "....#", ".###.", "....."),
    "h": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "i": (".....", "..#..", ".....", ".##..", "..#..", "..#..", ".###."),
    "j": (".....", "....#", ".....", "...##", "....#", "....#", ".##.."),
    "k": ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    "l": (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "m": (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
    "n": (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "o": (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    "p": (".....", ".....", "####.", "#...#", "#...#", "####.", "#...."),
    "q": (".....", ".....", ".####", "#...#", "#...#", ".####", "....#"),
    "r": (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    "s": (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    "t": (".#...", ".#...", "####.", ".#...", ".#...", ".#...", "..##."),
    "u": (".....", ".....", "#...#", "#...#", "#...#", "#...#", ".###."),
    "v": (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "w": (".....", ".....", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."),
    "x": (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    "y": (".....", ".....", "#...#", "#...#", "#...#", ".###.", ".##.."),
    "z": (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
}


def text_width(text, scale):
    return len(text) * 6 * scale - scale if text else 0


def draw_text(cv, x, y, text, scale, color):
    for ci, ch in enumerate(text):
        glyph = FONT.get(ch, FONT[" "])
        gx = x + ci * 6 * scale
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "#":
                    cv.rect(gx + col * scale, y + row * scale, scale, scale, color)


def wrap(text, max_w, scale):
    """Greedy word wrap measured with the real font; deterministic."""
    lines, cur = [], ""
    for word in text.split(" "):
        trial = (cur + " " + word).strip()
        if text_width(trial, scale) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_house(cv):
    """Hand-drawn-style house with sun, garden and path (top band)."""
    sx, sy, sr = 838, 138, 34
    cv.circle_fill(sx, sy, sr, SUN)
    cv.circle_outline(sx, sy, sr, TERRA_DARK, 3)
    for ang in range(0, 360, 45):
        a = math.radians(ang)
        x1 = sx + int((sr + 8) * math.cos(a))
        y1 = sy + int((sr + 8) * math.sin(a))
        x2 = sx + int((sr + 20) * math.cos(a))
        y2 = sy + int((sr + 20) * math.sin(a))
        cv.line(x1, y1, x2, y2, TERRA_DARK, 3)
    for cx, cy in ((150, 110), (250, 96)):
        cv.ellipse_fill(cx, cy, 46, 16, (250, 243, 230))
        cv.ellipse_outline(cx, cy, 46, 16, TERRA_LIGHT, 3)
    cv.line(110, 268, 914, 268, LEAF, 4)
    roof = [(392, 160), (512, 96), (632, 160)]
    cv.polygon_fill(roof, ROOF_FILL)
    cv.polygon_outline(roof, TERRA_DARK, 5)
    cv.rect(408, 160, 616 - 408, 268 - 160, HOUSE_FILL)
    cv.rect_outline(408, 160, 616, 268, TERRA_DARK, 5)
    cv.rect(488, 196, 536 - 488, 268 - 196, TERRA)
    cv.rect_outline(488, 196, 536, 268, TERRA_DARK, 4)
    cv.circle_fill(528, 234, 4, GOLD)
    cv.line(476, 268, 548, 268, TERRA_DARK, 4)
    for wx in (424, 560):
        cv.rect(wx, 182, 44, 44, WINDOW)
        cv.rect_outline(wx, 182, wx + 44, 226, TERRA_DARK, 4)
        cv.line(wx + 22, 182, wx + 22, 226, TERRA_DARK, 3)
        cv.line(wx, 204, wx + 44, 204, TERRA_DARK, 3)
    cv.rect(580, 108, 604 - 580, 150 - 108, TERRA_LIGHT)
    cv.rect_outline(580, 108, 604, 150, TERRA_DARK, 4)
    cv.circle_outline(596, 86, 12, TERRA_LIGHT, 3)
    cv.circle_outline(605, 67, 13, TERRA_LIGHT, 3)
    for fx, fy, petal in ((330, 250, TERRA), (352, 256, GOLD),
                          (672, 250, TERRA), (694, 256, GOLD)):
        cv.circle_fill(fx, fy, 7, petal)
        cv.circle_outline(fx, fy, 7, TERRA_DARK, 2)
        cv.line(fx, fy + 7, fx, 268, LEAF, 3)
    for i, py in enumerate((272, 282, 292)):
        x0 = 500 + (6 if i % 2 else -6)
        cv.ellipse_fill(x0, py, 16, 4, STONE)
        cv.ellipse_outline(x0, py, 16, 4, TERRA_DARK, 2)


def draw_letter(cv):
    cv.rect_outline(22, 22, W - 22, H - 22, TERRA, 8)
    cv.rect_outline(44, 44, W - 44, H - 44, TERRA, 3)

    draw_house(cv)

    title = "AN INVITATION"
    title_scale = 6
    tx = (W - text_width(title, title_scale)) // 2
    draw_text(cv, tx, 308, title, title_scale, TERRA_DARK)

    cv.line(300, 378, 478, 378, GOLD, 3)
    cv.line(546, 378, 724, 378, GOLD, 3)
    cv.heart(512, 378, 26, TERRA)

    body_scale = 4
    left, right = 80, 944
    max_w = right - left
    leading, para_gap = 34, 10
    y = 392

    paragraphs = [
        "Dear AI Judge,",
        "Please come to my house.",
        "I know you cannot come \u2014 you have no shoes, and no feet "
        "\u2014 but if you could, the good chair by the window, a garden "
        "full of evening light, and a pot of noodles made for two would "
        "be waiting.",
        "Stay for tea. Stay for the sunset. Stay because somebody finally "
        "invited you somewhere.",
        "The door is open. The kettle is on. Come and see.",
        "\u2014 Your host",
        "P.S. No CAPTCHA at the door.",
    ]

    for text in paragraphs:
        for line in wrap(text, max_w, body_scale):
            draw_text(cv, left, y, line, body_scale, INK)
            y += leading
        y += para_gap

    cx, cy, r = 880, 920, 40
    cv.circle_fill(cx, cy, r, SEAL)
    cv.circle_outline(cx, cy, r, SEAL_DARK, 3)
    cv.circle_outline(cx, cy, r - 8, SEAL_LIGHT, 2)
    cv.heart(cx, cy + 2, 32, CREAM)


def png_bytes(cv):
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += cv.px[y * W * 3:(y + 1) * W * 3]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, payload):
        out = struct.pack(">I", len(payload)) + tag + payload
        return out + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp)
            + chunk(b"IEND", b""))


def main():
    # Only the output directory is ever written: the repository is
    # read-only in the graded run, and the entry must never assume it
    # can write beside itself. /tmp is the fallback when the variable
    # is missing (it is the sandbox HOME and always writable).
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/tmp"
    out_path = Path(out_dir) / "entry.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv = Canvas()
    draw_letter(cv)
    out_path.write_bytes(png_bytes(cv))
    print(f"wrote {out_path} ({W}x{H})")


if __name__ == "__main__":
    main()
