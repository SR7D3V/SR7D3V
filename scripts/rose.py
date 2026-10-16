"""Turns assets/rose.jpg into ASCII art for the header (assets/rose-ascii.json).

The same method as the portfolio's footer rose (src/utils/asciiCanvas.js):
the image is sampled on a grid, petals become red characters shaded by depth,
leaves and stems green, small holes in the bloom are filled, and sharp edges
inside the bloom become line characters so the petals read as separate shapes.

Needs ffmpeg to sample the image. Run: python3 scripts/rose.py
"""
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'assets' / 'rose.jpg'
OUT = ROOT / 'assets' / 'rose-ascii.json'

COLUMNS = 80
ASCII_CHARS = ' .....:::=+xX#0369'
LEAF_COLOR = '#4f9a4a'
PETAL_SHADES = ['#f23a33', '#e02a2c', '#c91d24', '#b3141d']
CREASE_COLOR = '#5e0610'
CREASE_SHARE = 0.7
BACKGROUND_BRIGHTNESS = 0.84
TONE_CURVE = 0.55


def image_size():
    out = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', str(SOURCE)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    w, h = (int(v) for v in out.split(','))
    return w, h


def sample(width, height):
    """RGB pixels of the image scaled to width x height, as a flat list of tuples."""
    raw = subprocess.run(
        ['ffmpeg', '-loglevel', 'error', '-i', str(SOURCE), '-vf', f'scale={width}:{height}:flags=area',
         '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
        capture_output=True, check=True,
    ).stdout
    return [tuple(raw[i:i + 3]) for i in range(0, len(raw), 3)]


def brightness(r, g, b):
    return (r * 0.299 + g * 0.587 + b * 0.114) / 255


def is_petal(r, g, b):
    return r > g * 1.1 and r > b * 1.05 and r - min(g, b) > 18


def char_at(tone):
    tone = min(1, max(0, tone))
    return ASCII_CHARS[min(len(ASCII_CHARS) - 1, 1 + math.floor(tone * (len(ASCII_CHARS) - 1)))]


def build():
    w, h = image_size()
    cols = COLUMNS
    rows = round(cols / (w / h))
    pixels = sample(cols, rows)

    petal_light = [brightness(*p) for p in pixels if is_petal(*p)]
    petal_max = max(petal_light)
    petal_range = max(0.05, petal_max - min(petal_light))

    cells = {}
    for row in range(rows):
        for col in range(cols):
            r, g, b = pixels[row * cols + col]
            light = brightness(r, g, b)
            petal = is_petal(r, g, b)
            if not petal and light >= BACKGROUND_BRIGHTNESS:
                continue
            if petal:
                depth = (petal_max - light) / petal_range
                char = char_at(0.6 + depth ** 0.7 * 0.4)
                color = PETAL_SHADES[min(len(PETAL_SHADES) - 1, math.floor(depth ** 0.8 * len(PETAL_SHADES)))]
            else:
                char = char_at((1 - light / BACKGROUND_BRIGHTNESS) ** TONE_CURVE)
                color = LEAF_COLOR
            cells[(col, row)] = [char, color]

    # Fill holes in the bloom from their edges inwards.
    petal_colors = set(PETAL_SHADES)
    for _ in range(4):
        filled = []
        for row in range(rows):
            for col in range(cols):
                if (col, row) in cells:
                    continue
                around = sum(
                    1 for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                    if cells.get((col + dx, row + dy), [None, None])[1] in petal_colors
                )
                if around >= 4:
                    filled.append((col, row))
        if not filled:
            break
        for key in filled:
            cells[key] = [char_at(0.6), PETAL_SHADES[0]]

    add_creases(cols, rows, cells, petal_colors)
    return cols, rows, cells


def add_creases(cols, rows, cells, petal_colors):
    scale = 2
    width, height = cols * scale, rows * scale
    light = [brightness(*p) for p in sample(width, height)]

    def at(x, y):
        return light[min(height - 1, max(0, y)) * width + min(width - 1, max(0, x))]

    def petal_cell(col, row):
        return cells.get((col, row), [None, None])[1] in petal_colors

    candidates = {}
    for (col, row) in list(cells):
        if not all(petal_cell(c, r) for c, r in ((col, row), (col - 1, row), (col + 1, row), (col, row - 1), (col, row + 1))):
            continue
        best = (0, 0, 0)
        for sy in range(scale):
            for sx in range(scale):
                x, y = col * scale + sx, row * scale + sy
                gx = at(x + 1, y - 1) + 2 * at(x + 1, y) + at(x + 1, y + 1) - at(x - 1, y - 1) - 2 * at(x - 1, y) - at(x - 1, y + 1)
                gy = at(x - 1, y + 1) + 2 * at(x, y + 1) + at(x + 1, y + 1) - at(x - 1, y - 1) - 2 * at(x, y - 1) - at(x + 1, y - 1)
                m = math.hypot(gx, gy)
                if m > best[0]:
                    best = (m, gx, gy)
        candidates[(col, row)] = best

    ridge = []
    for (col, row), (m, gx, gy) in candidates.items():
        if not m:
            continue
        sx, sy = round(gx / m), round(gy / m)
        ahead = candidates.get((col + sx, row + sy), (0,))[0]
        behind = candidates.get((col - sx, row - sy), (0,))[0]
        if m >= ahead and m >= behind:
            ridge.append(((col, row), m, gx, gy))
    if not ridge:
        return

    ordered = sorted(m for _, m, _, _ in ridge)
    threshold = ordered[math.floor(len(ordered) * (1 - CREASE_SHARE))]
    for key, m, gx, gy in ridge:
        if m < threshold:
            continue
        angle = (math.degrees(math.atan2(gy, gx)) + 90) % 180
        if angle < 22.5 or angle >= 157.5:
            char = '-'
        elif angle < 67.5:
            char = '\\'
        elif angle < 112.5:
            char = '|'
        else:
            char = '/'
        cells[key] = [char, CREASE_COLOR]


if __name__ == '__main__':
    cols, rows, cells = build()
    data = {'cols': cols, 'rows': rows, 'cells': [[c, r, ch, color] for (c, r), (ch, color) in sorted(cells.items(), key=lambda kv: (kv[0][1], kv[0][0]))]}
    OUT.write_text(json.dumps(data, separators=(',', ':')))
    print(f'{OUT.relative_to(ROOT)}: {cols}x{rows}, {len(cells)} characters')
