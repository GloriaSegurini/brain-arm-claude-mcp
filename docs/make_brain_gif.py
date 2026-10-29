#!/usr/bin/env python3
"""Generate docs/brain-wait-demo.gif: what you actually see in the brain chat (Claude Desktop) while an arm works —
a few compact tool lines and a verified answer — and, at the end, where the noise lives (the arm's tmux window).
Made-up example, no real data. Requires Pillow. Run: python3 docs/make_brain_gif.py
"""
from pathlib import Path

from PIL import Image

from gifkit import SCALE, Draw, Font, new_image, save_gif

ROOT = Path(__file__).resolve().parent.parent
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

W, H = 880, 640
BG, FG, MUTED, BUBBLE = (38, 38, 36), (236, 234, 230), (150, 148, 142), (60, 59, 56)
CHIP, CHIP_LINE, CLAY, OK = (46, 46, 43), (74, 73, 68), (217, 119, 87), (125, 195, 125)
TERM, TERM_FG, TERM_DIM, TERM_ADD, TERM_DEL = (40, 12, 32), (225, 225, 222), (140, 140, 135), (120, 200, 110), (230, 110, 100)

f_body = Font(SANS, 17)
f_bold = Font(SANS_B, 16)
f_small = Font(SANS, 14)
f_mono = Font(MONO, 13)
f_cap = Font(SANS_B, 17)

USER = "Add input validation to the signup form and make sure the tests still pass."
INTRO = "Sure — I'll hand this to the arm working on webshop / checkout-redesign."
FINAL = ("Done. Email and password validation is now in Signup.tsx and all 48 tests pass. "
         "I checked the result: only that file changed.")
NOISE = [
    ("$ arm_helper.py get webshop checkout-redesign", TERM_DIM),
    ("● Read src/forms/Signup.tsx (212 lines)", TERM_FG),
    ("● Read src/forms/validation.ts (88 lines)", TERM_FG),
    ("● Update src/forms/Signup.tsx", TERM_FG),
    ("+  const emailOk = EMAIL_RE.test(values.email);", TERM_ADD),
    ("+  if (values.password.length < 12) {", TERM_ADD),
    ("+    errors.password = 'At least 12 characters';", TERM_ADD),
    ("-  // TODO: validation", TERM_DEL),
    ("● Bash(npm test -- --runInBand)", TERM_FG),
    ("  PASS src/forms/Signup.test.tsx (4.1 s)", TERM_ADD),
    ("  PASS src/api/session.test.ts (2.7 s)", TERM_ADD),
    ("  … 46 more suites", TERM_DIM),
    ("  Tests: 48 passed, 48 total", TERM_ADD),
    ('$ arm_helper.py done task_042 "Validation added…"', TERM_DIM),
    ("ARM waiting", TERM_DIM),
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


def chip(d, y, name, state, phase):
    """A collapsed tool call, the way a chat app shows it."""
    d.rounded_rectangle([40, y, W - 40, y + 40], 9, fill=CHIP, outline=CHIP_LINE)
    if state == "run":
        d.text((58, y + 11), "●", font=f_small, fill=CLAY)
        d.text((W - 60, y + 12), "waiting" + "." * (phase % 3 + 1), font=f_small, fill=CLAY, anchor="ra")
    else:
        d.text((56, y + 10), "✓", font=f_bold, fill=OK)
    d.text((82, y + 11), "brain-arm", font=f_small, fill=MUTED)
    d.text((82 + f_small.getlength("brain-arm") + 8, y + 10), name, font=f_bold, fill=FG)
    if state != "run":
        d.text((W - 58, y + 9), "›", font=f_bold, fill=MUTED, anchor="ra")
    return y + 50


def chat(items, phase):
    img = new_image(W, H, BG)
    d = Draw(img)
    d.text((40, 22), "Claude Desktop", font=f_bold, fill=FG)
    d.text((40 + f_bold.getlength("Claude Desktop") + 10, 23), "· Webshop project · checkout-redesign",
           font=f_small, fill=MUTED)
    d.line([(40, 54), (W - 40, 54)], fill=CHIP_LINE)
    y = 74
    for kind, *rest in items:
        if kind == "user":
            lines = wrap(USER, f_body, 470)
            h = 26 * len(lines) + 22
            d.rounded_rectangle([W - 40 - 510, y, W - 40, y + h], 16, fill=BUBBLE)
            for i, ln in enumerate(lines):
                d.text((W - 40 - 490, y + 11 + 26 * i), ln, font=f_body, fill=FG)
            y += h + 18
        elif kind == "text":
            for ln in wrap(rest[0], f_body, W - 80):
                d.text((40, y), ln, font=f_body, fill=FG)
                y += 26
            y += 12
        elif kind == "chip":
            y = chip(d, y, rest[0], rest[1], phase)
    return img


def with_noise(base):
    """Dim the chat and show where the noise lives: the arm's tmux window."""
    img = Image.blend(base, Image.new("RGB", base.size, (0, 0, 0)), 0.55)
    d = Draw(img)
    x0, y0, x1 = 150, 130, W - 30
    y1 = y0 + 48 + 21 * len(NOISE) + 14
    d.rounded_rectangle([x0, y0, x1, y1], 12, fill=TERM, outline=(110, 60, 95), width=1.5)
    d.text((x0 + 18, y0 + 14), "tmux attach -t arms", font=f_bold, fill=TERM_FG)
    d.text((x0 + 18 + f_bold.getlength("tmux attach -t arms") + 10, y0 + 15), "— only if you want to look",
           font=f_small, fill=TERM_DIM)
    y = y0 + 48
    for text, color in NOISE:
        d.text((x0 + 18, y), text, font=f_mono, fill=color)
        y += 21
    d.rounded_rectangle([40, H - 56, W - 40, H - 16], 10, fill=(28, 28, 26))
    d.text((W / 2, H - 37), "The noise stays in the arm's session — your chat stays clean.",
           font=f_cap, fill=FG, anchor="mm")
    return img


def main():
    seq = [  # (items to append, spinning?, duration ms)
        ([("user",)], False, 1700),
        ([("text", INTRO)], False, 1200),
        ([("chip", "create_task", "done")], False, 900),
        ([("chip", "wait_for_task", "run")], True, 1800),
        ([("chip", "wait_for_task", "run")], True, 1800),
        ([("chip", "get_result", "done")], False, 900),
        ([("text", FINAL)], False, 2600),
    ]
    items, images, durations = [], [], []
    for new, spinning, ms in seq:
        for it in new:
            if it[0] == "chip" and items and items[-1][0] == "chip" and items[-1][2] == "run":
                items[-1] = ("chip", items[-1][1], "done")
            items.append(it)
        if spinning:
            for ph in range(3):
                images.append(chat(items, ph))
                durations.append(ms // 3)
        else:
            images.append(chat(items, 0))
            durations.append(ms)
    clean = chat(items, 0)
    images += [with_noise(clean), clean]
    durations += [4200, 1800]
    out = ROOT / "docs" / "brain-wait-demo.gif"
    save_gif(images, durations, out)
    print(f"written {out} ({len(images)} frames, {W * SCALE}x{H * SCALE})")


if __name__ == "__main__":
    main()
