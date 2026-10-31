#!/usr/bin/env python3
"""Generate docs/status-demo.gif from the real status.py renderer with made-up projects (no real data).
Requires Pillow (python3 -m pip install pillow). Run: python3 docs/make_status_gif.py
"""
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from gifkit import SCALE, save_gif

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from status import render  # noqa: E402

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
BG, FG = (38, 38, 36), (236, 234, 230)
ANSI = {"1": None, "32": (125, 195, 125), "33": (230, 180, 90), "31": (230, 110, 100),
        "36": (140, 185, 220), "90": (150, 148, 142)}
SIZE, PAD = 17 * SCALE, 18 * SCALE


def task(p, ch, status, n):
    return [{"project": p, "channel": ch, "status": status} for _ in range(n)]


def scene(checkout, ingestion, reporting=None):
    tasks = []
    for (p, ch), counts in ((("webshop", "checkout-redesign"), checkout),
                            (("data-platform", "ingestion"), ingestion),
                            (("data-platform", "reporting"), reporting)):
        if counts:
            for status, n in zip(("pending", "in_progress", "done", "failed"), counts):
                tasks += task(p, ch, status, n)
    return tasks


W, I, R = ("webshop", "checkout-redesign"), ("data-platform", "ingestion"), ("data-platform", "reporting")
FRAMES = [  # (clock, checkout counts, ingestion counts, reporting counts, arm state, duration ms)
    ("10:14:03", (0, 0, 12, 0), (0, 0, 7, 1), None,         {W: False, I: False},           2600),
    ("10:14:06", (1, 0, 12, 0), (0, 0, 7, 1), None,         {W: False, I: False},           2600),
    ("10:14:09", (1, 0, 12, 0), (0, 0, 7, 1), None,         {W: True, I: False},            2600),
    ("10:14:12", (0, 1, 12, 0), (0, 0, 7, 1), None,         {W: True, I: False},            2800),
    ("10:14:15", (0, 1, 12, 0), (0, 0, 7, 1), (1, 0, 0, 0), {W: True, I: False},            2800),
    ("10:14:18", (0, 1, 12, 0), (0, 0, 7, 1), (0, 1, 0, 0), {W: True, I: False, R: True},   2800),
    ("10:14:21", (0, 0, 13, 0), (0, 0, 7, 1), (0, 1, 0, 0), {W: True, I: False, R: True},   2800),
    ("10:14:24", (0, 0, 13, 0), (0, 0, 7, 1), (0, 0, 1, 0), {W: False, I: False, R: True},  2800),
    ("10:14:27", (0, 0, 13, 0), (0, 0, 7, 1), (0, 0, 1, 0), {W: False, I: False, R: False}, 3600),
]


def spans(line):
    color, bold, out = FG, False, []
    for part in re.split(r"(\x1b\[[0-9;]*m)", line):
        m = re.fullmatch(r"\x1b\[([0-9;]*)m", part)
        if not m:
            if part:
                out.append((part, color, bold))
            continue
        for code in (m.group(1) or "0").split(";"):
            if code == "0":
                color, bold = FG, False
            elif code == "1":
                bold = True
            elif code in ANSI:
                color = ANSI[code]
    return out


def draw(text, header):
    font = ImageFont.truetype(FONT, SIZE)
    cw = font.getlength("M")
    lh = int(SIZE * 1.45)
    lines = [header, ""] + text.split("\n")
    img = Image.new("RGB", (int(cw * 74 + 2 * PAD), lh * len(lines) + 2 * PAD), BG)
    d = ImageDraw.Draw(img)
    for row, line in enumerate(lines):
        x, y = PAD, PAD + row * lh
        for chunk, color, bold in spans(line):
            d.text((x, y), chunk, font=font, fill=color, stroke_width=1 if bold else 0, stroke_fill=color)
            x += cw * len(chunk)
    return img


def main():
    images, durations = [], []
    for clock, ck, ing, rep, state, ms in FRAMES:
        header = f"Every 3.0s: python3 status.py{' ' * 22}demo-host: {clock}"
        images.append(draw(render(scene(ck, ing, rep), state, clock), header))
        durations.append(ms)
    out = ROOT / "docs" / "status-demo.gif"
    save_gif(images, durations, out)
    print(f"written {out} ({len(images)} frames)")


if __name__ == "__main__":
    main()
