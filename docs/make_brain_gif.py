#!/usr/bin/env python3
"""Generate docs/brain-wait-demo.gif: what you actually see in the brain chat (Claude Desktop) while an arm works.
One compact tool row with a running timer; expanded once to show the few lines the brain exchanges with brain-arm;
the optional status table; then the brain's checked answer.
Made-up example, no real data. Requires Pillow. Run: python3 docs/make_brain_gif.py
"""
import re
import sys
from pathlib import Path

from PIL import Image

from gifkit import SCALE, Draw, Font, new_image, save_gif

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(1, str(ROOT))  # for status.py (the real table renderer)
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

W, H = 880, 640
BG, FG, MUTED, BUBBLE = (27, 27, 26), (236, 234, 230), (150, 148, 142), (48, 48, 46)
CARD, CARD_LINE, CODE_BG = (32, 32, 31), (60, 60, 57), (27, 27, 26)
GREEN, GREEN_DIM, KEY = (125, 205, 125), (70, 120, 70), (150, 190, 230)
TERM, TERM_FG = (36, 12, 30), (225, 225, 222)

f_body = Font(SANS, 15)
f_bold = Font(SANS_B, 15)
f_row = Font(SANS, 14)
f_small = Font(SANS, 12)
f_mono = Font(MONO, 12.5)

TASK_ID = "task_20261031_101203_042"
USER = "Add input validation to the signup form and make sure the tests still pass."
INTRO = "I'll send this to the arm for webshop / checkout-redesign and wait for it to finish."
CREATE_REQ = [
    ('"title"', '"Signup form: input validation, tests must pass"'),
    ('"project"', '"webshop"'),
    ('"channel"', '"checkout-redesign"'),
    ('"priority"', '"normal"'),
]
CREATE_RESP = [
    f"Task created: {TASK_ID} [project=webshop channel=checkout-redesign]",
    "→ Signup form: input validation, tests must pass",
    f"NEXT STEP: call wait_for_task('{TASK_ID}') now and call it",
    "again until it answers done/failed/needs_clarification. Do not ask the user",
    "to tell you when it's finished.",
]
FINAL = [
    ("p", "Done. Signup validation is in place and all 48 tests pass."),
    ("h", "What changed"),
    ("li", "Signup.tsx: email format and password length (at least 12 characters) are checked before submit."),
    ("li", "validation.ts: a shared EMAIL_RE, reused by the profile form."),
    ("li", "Tests: 3 new cases for the validation; 48 passed, 48 total."),
    ("h", "Checked"),
    ("li", "I read the result against the goal: only these two files changed, no test was skipped."),
]


def wrap(text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if font.getlength(t) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + [cur] if cur else lines


def elapsed(s):
    return f"{s}s" if s < 60 else f"{s // 60}min {s % 60}s"


def dots(d, x, y, phase, done=False):
    """The activity indicator next to a tool row: three dots that pulse while working."""
    for i in range(3):
        on = done or (phase % 3) == i
        d.text((x + 7 * i, y), "•", font=f_row, fill=GREEN if on else GREEN_DIM)


def cursor(img, x, y):
    s = SCALE
    pts = [(x, y), (x, y + 17), (x + 4.5, y + 13), (x + 7.5, y + 20), (x + 10, y + 19), (x + 7, y + 12), (x + 12.5, y + 12)]
    from PIL import ImageDraw
    ImageDraw.Draw(img).polygon([(px * s, py * s) for px, py in pts], fill=(250, 250, 250), outline=(20, 20, 20))


def header(d, label, secs, phase, y, open_=False, done=False):
    dots(d, 150, y, phase, done)
    d.text((182, y), label, font=f_row, fill=MUTED)
    t = elapsed(secs)
    x = 182 + f_row.getlength(label) + 8
    d.text((x, y), t, font=f_row, fill=MUTED)
    d.text((x + f_row.getlength(t) + 8, y + 1), "▾" if open_ else "▸", font=f_small, fill=MUTED)
    return y + 30


def base(intro=True):
    img = new_image(W, H, BG)
    d = Draw(img)
    lines = wrap(USER, f_body, 420)
    h = 24 * len(lines) + 20
    d.rounded_rectangle([W - 40 - 450, 20, W - 40, 20 + h], 14, fill=BUBBLE)
    for i, ln in enumerate(lines):
        d.text((W - 40 - 432, 30 + 24 * i), ln, font=f_body, fill=FG)
    y = 20 + h + 26
    if intro:
        for ln in wrap(INTRO, f_body, W - 190):
            d.text((150, y), ln, font=f_body, fill=FG)
            y += 24
        y += 14
    return img, d, y


def collapsed(label, secs, phase, click=False):
    img, d, y = base()
    header(d, label, secs, phase, y)
    if click:
        cursor(img, 250, y + 12)
    return img


def expanded(secs, phase):
    img, d, y = base()
    y = header(d, "Wait for task", secs, phase, y, open_=True)
    x0, x1 = 150, W - 40
    d.rounded_rectangle([x0, y, x1, y + 425], 10, fill=CARD, outline=CARD_LINE)
    yy = y + 14
    d.text((x0 + 16, yy), "Create task  ▾", font=f_row, fill=MUTED)
    yy += 28
    d.text((x0 + 16, yy), "Request", font=f_small, fill=MUTED)
    yy += 20
    d.text((x0 + 16, yy), "{", font=f_mono, fill=FG)
    yy += 18
    for k, v in CREATE_REQ:
        d.text((x0 + 32, yy), k, font=f_mono, fill=KEY)
        kx = x0 + 32 + f_mono.getlength(k + ": ")
        d.text((x0 + 32 + f_mono.getlength(k), yy), ": ", font=f_mono, fill=FG)
        d.text((kx, yy), v + ",", font=f_mono, fill=GREEN)
        yy += 18
    d.text((x0 + 16, yy), "}", font=f_mono, fill=FG)
    yy += 28
    d.text((x0 + 16, yy), "Response", font=f_small, fill=MUTED)
    yy += 20
    for ln in CREATE_RESP:
        d.text((x0 + 16, yy), ln, font=f_mono, fill=FG)
        yy += 18
    yy += 12
    d.line([(x0, yy), (x1, yy)], fill=CARD_LINE)
    yy += 14
    d.text((x0 + 16, yy), "Wait for task  ▾", font=f_row, fill=MUTED)
    yy += 28
    d.text((x0 + 16, yy), "Request", font=f_small, fill=MUTED)
    yy += 20
    d.text((x0 + 16, yy), "{", font=f_mono, fill=FG)
    d.text((x0 + 32, yy + 18), '"task_id"', font=f_mono, fill=KEY)
    d.text((x0 + 32 + f_mono.getlength('"task_id"'), yy + 18), ": ", font=f_mono, fill=FG)
    d.text((x0 + 32 + f_mono.getlength('"task_id": '), yy + 18), f'"{TASK_ID}"', font=f_mono, fill=GREEN)
    d.text((x0 + 16, yy + 36), "}", font=f_mono, fill=FG)
    cursor(img, 300, y + 300)
    return img


def with_status(secs, phase):
    """The chat keeps waiting; the user glances at the optional status table in a terminal."""
    from make_status_gif import ANSI, scene
    from status import render
    img, d, y = base()
    header(d, "Wait for task", secs, phase, y)
    colors = dict(ANSI, **{"33": GREEN})  # running rows in green, as in the rest of this GIF
    view = render(scene((0, 1, 12, 0), (0, 0, 7, 1)),
                  {("webshop", "checkout-redesign"): True, ("data-platform", "ingestion"): False}, "10:12:53")
    x0, y0, x1, y1 = 24, 300, W - 24, H - 40
    d.rounded_rectangle([x0, y0, x1, y1], 10, fill=TERM, outline=(90, 55, 80), width=1.5)
    d.rounded_rectangle([x0, y0, x1, y0 + 30], 10, fill=(30, 30, 30))
    d.rectangle([x0, y0 + 20, x1, y0 + 30], fill=(30, 30, 30))
    d.text((x0 + 16, y0 + 8), "Ubuntu  ·  watch -n3 python3 ~/brain-arm/status.py   (optional)", font=f_small, fill=MUTED)
    yy = y0 + 42
    for line in view.split("\n"):
        x, color = x0 + 8, TERM_FG
        for part in re.split(r"(\x1b\[[0-9;]*m)", line):
            m = re.fullmatch(r"\x1b\[([0-9;]*)m", part)
            if m:
                code = m.group(1) or "0"
                color = TERM_FG if code in ("0", "1") else colors.get(code, TERM_FG)
            elif part:
                d.text((x, yy), part, font=f_mono, fill=color)
                x += f_mono.getlength(part)
        yy += 19
    return img


def final():
    img, d, y = base()
    dots(d, 150, y, 0, done=True)
    d.text((182, y), "Thought for 1min 10s", font=f_row, fill=MUTED)
    d.text((182 + f_row.getlength("Thought for 1min 10s") + 8, y + 1), "▸", font=f_small, fill=MUTED)
    y += 38
    for kind, text in FINAL:
        if kind == "h":
            y += 6
            d.text((150, y), text, font=f_bold, fill=FG)
            y += 28
            continue
        indent = 172 if kind == "li" else 150
        for i, ln in enumerate(wrap(text, f_body, W - 40 - indent)):
            if kind == "li" and i == 0:
                d.text((156, y), "•", font=f_body, fill=FG)
            d.text((indent, y), ln, font=f_body, fill=FG)
            y += 24
        y += 6
    return img


def main():
    frames = []  # (image, ms)
    frames.append((base(intro=False)[0], 1800))
    frames.append((base()[0], 1600))
    frames += [(collapsed("Create task", 1, ph), 450) for ph in range(3)]
    frames += [(collapsed("Wait for task", s, s), 500) for s in range(3, 15)]
    frames.append((collapsed("Wait for task", 15, 0, click=True), 700))
    frames += [(expanded(s, s), 650) for s in range(16, 26)]
    frames += [(collapsed("Wait for task", s, s), 450) for s in range(26, 60, 2)]
    frames += [(with_status(s, s), 600) for s in range(60, 70)]
    frames += [(collapsed("Get result", s, s), 450) for s in range(70, 73)]
    frames.append((final(), 6500))
    out = ROOT / "docs" / "brain-wait-demo.gif"
    save_gif([f for f, _ in frames], [ms for _, ms in frames], out)
    print(f"written {out} ({len(frames)} frames, {W * SCALE}x{H * SCALE})")


if __name__ == "__main__":
    main()
