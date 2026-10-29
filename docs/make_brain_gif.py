#!/usr/bin/env python3
"""Generate docs/brain-wait-demo.gif: the brain chat waiting on wait_for_task (left) while the arm works (right).
Made-up example, no real data. Requires Pillow. Run: python3 docs/make_brain_gif.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

W, H = 1240, 600
SPLIT = 700
CHAT_BG, CHAT_FG, MUTED, BUBBLE = (38, 38, 36), (232, 230, 227), (154, 152, 147), (58, 57, 54)
CHIP_BG, CHIP_LINE, CLAY, OK = (46, 46, 43), (78, 77, 72), (217, 119, 87), (120, 190, 120)
TERM_BG, TERM_FG, TERM_GREEN, TERM_GRAY, TERM_CYAN = (48, 10, 36), (238, 238, 236), (138, 226, 52), (136, 138, 133), (52, 226, 226)

f_sans = ImageFont.truetype(SANS, 15)
f_small = ImageFont.truetype(SANS, 13)
f_bold = ImageFont.truetype(SANS_B, 15)
f_mono = ImageFont.truetype(MONO, 14)
f_mono_s = ImageFont.truetype(MONO, 13)

TID = "task_042"

# Each step: (chat items, arm lines, spinner?, duration ms). Items accumulate.
STEPS = [
    ([("user", "Add input validation to the signup form and make sure the tests still pass.")], [], False, 1600),
    ([("brain", "I'll hand this to the arm working on webshop / checkout-redesign.")], [], False, 1100),
    ([("tool", "create_task", "project=webshop  channel=checkout-redesign",
       f"Task created: {TID} — NEXT STEP: call wait_for_task now", "done")],
     [("watch", "[watcher] new task on webshop:checkout-redesign → starting arm")], False, 1400),
    ([("tool", "wait_for_task", TID, None, "run")],
     [("cmd", f"arm_helper.py get webshop checkout-redesign"), ("cmd", f"arm_helper.py start {TID}")], True, 1300),
    ([], [("act", "Reading src/forms/Signup.tsx")], True, 1100),
    ([], [("act", "Editing src/forms/Signup.tsx  (+38 −4)")], True, 1100),
    ([("result", f"wait {TID}: in_progress for 0 min, the arm is working on it. Call wait_for_task again now."),
      ("tool", "wait_for_task", TID, None, "run")],
     [("act", "Running npm test")], True, 1500),
    ([], [("out", "  Tests: 48 passed, 0 failed")], True, 1100),
    ([], [("cmd", f'arm_helper.py done {TID} "Validation added…"'), ("out", "ARM waiting")], True, 1200),
    ([("result", f"done {TID} — now call get_result, check the outcome and report it."),
      ("tool", "get_result", TID,
       "Email + password (min 12 chars) validation in Signup.tsx; 48/48 tests pass; no other files changed.", "done")],
     [], False, 1500),
    ([("brain", "Done. The arm added email and password validation to Signup.tsx and all 48 tests pass. "
                "I checked the result: only that file changed.")], [], False, 3600),
]

CAPTION = ("wait_for_task blocks up to ~50 s per call with no tokens spent while waiting, "
           "then tells the brain to call again — the user never has to say “it's done”.")


def wrap(text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if font.getlength(trial) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_chat(d, items, spin_phase):
    """Draw chat items bottom-anchored inside the left panel; returns nothing."""
    blocks = []  # (height, draw_fn)
    for it in items:
        kind = it[0]
        if kind == "user":
            lines = wrap(it[1], f_sans, 420)
            h = 22 * len(lines) + 20
            blocks.append((h, lambda y, lines=lines, h=h: (
                d.rounded_rectangle([SPLIT - 40 - 450, y, SPLIT - 40, y + h], 14, fill=BUBBLE),
                [d.text((SPLIT - 40 - 435, y + 10 + 22 * i), ln, font=f_sans, fill=CHAT_FG) for i, ln in enumerate(lines)])))
        elif kind == "brain":
            lines = wrap(it[1], f_sans, 600)
            h = 22 * len(lines) + 8
            blocks.append((h, lambda y, lines=lines: [d.text((40, y + 22 * i), ln, font=f_sans, fill=CHAT_FG)
                                                       for i, ln in enumerate(lines)]))
        elif kind == "result":
            lines = wrap(it[1], f_small, 580)
            h = 19 * len(lines) + 4
            blocks.append((h, lambda y, lines=lines: [d.text((56, y + 19 * i), ln, font=f_small, fill=MUTED)
                                                       for i, ln in enumerate(lines)]))
        elif kind == "tool":
            _, name, args, result, state = it
            res_lines = wrap(result, f_small, 560) if result else []
            h = 36 + 19 * len(res_lines) + (8 if res_lines else 0)

            def draw_tool(y, name=name, args=args, res_lines=res_lines, state=state, h=h):
                d.rounded_rectangle([40, y, SPLIT - 40, y + h], 10, fill=CHIP_BG, outline=CHIP_LINE)
                if state == "run":
                    d.text((57, y + 10), "●", font=f_small, fill=CLAY)
                    label = "waiting" + "." * (spin_phase % 3 + 1)
                    d.text((SPLIT - 56 - f_small.getlength("waiting..."), y + 11), label, font=f_small, fill=CLAY)
                else:
                    d.text((56, y + 9), "✓", font=f_bold, fill=OK)
                d.text((84, y + 9), name, font=f_bold, fill=CHAT_FG)
                d.text((84 + f_bold.getlength(name) + 10, y + 11), args, font=f_mono_s, fill=MUTED)
                for i, ln in enumerate(res_lines):
                    d.text((84, y + 34 + 19 * i), ln, font=f_small, fill=MUTED)
            blocks.append((h, draw_tool))
    gap, top, bottom = 14, 64, H - 70
    total = sum(h for h, _ in blocks) + gap * max(len(blocks) - 1, 0)
    y = max(top, bottom - total) if total > bottom - top else top
    if total > bottom - top:
        y = bottom - total
    for h, fn in blocks:
        if y + h > top - 4:
            fn(y)
        y += h + gap
    d.rectangle([0, 0, SPLIT, top - 8], fill=CHAT_BG)
    d.text((40, 22), "Brain", font=f_bold, fill=CHAT_FG)
    d.text((95, 23), "· Claude Desktop chat", font=f_sans, fill=MUTED)


def render_arm(d, lines):
    d.rectangle([SPLIT, 0, W, H], fill=TERM_BG)
    d.text((SPLIT + 24, 22), "Arm", font=f_bold, fill=TERM_FG)
    d.text((SPLIT + 64, 23), "· Claude Code in tmux (webshop:checkout-redesign)", font=f_small, fill=TERM_GRAY)
    y = 64
    for kind, text in lines[-17:]:
        if kind == "cmd":
            d.text((SPLIT + 24, y), "$", font=f_mono, fill=TERM_GREEN)
            for i, ln in enumerate(wrap(text, f_mono, W - SPLIT - 70)):
                d.text((SPLIT + 42, y), ln, font=f_mono, fill=TERM_FG)
                y += 22
        elif kind == "act":
            d.text((SPLIT + 24, y), "●", font=f_mono, fill=TERM_CYAN)
            d.text((SPLIT + 42, y), text, font=f_mono, fill=TERM_FG)
            y += 22
        elif kind == "out":
            d.text((SPLIT + 24, y), text, font=f_mono, fill=TERM_GREEN if "ARM" not in text else TERM_GRAY)
            y += 22
        else:
            for ln in wrap(text, f_mono_s, W - SPLIT - 50):
                d.text((SPLIT + 24, y), ln, font=f_mono_s, fill=TERM_GRAY)
                y += 20
        y += 4


def frame(items, arm, spin_phase):
    img = Image.new("RGB", (W, H), CHAT_BG)
    d = ImageDraw.Draw(img)
    render_chat(d, items, spin_phase)
    render_arm(d, arm)
    d.rectangle([0, H - 52, W, H], fill=(28, 28, 26))
    for i, ln in enumerate(wrap(CAPTION, f_small, W - 60)):
        d.text((30, H - 44 + 18 * i), ln, font=f_small, fill=MUTED)
    return img


def main():
    items, arm, images, durations = [], [], [], []
    for new_items, new_arm, spinning, ms in STEPS:
        for it in new_items:
            if it[0] == "result":  # the previous running tool call has returned
                for j in range(len(items) - 1, -1, -1):
                    if items[j][0] == "tool" and items[j][4] == "run":
                        items[j] = items[j][:4] + ("done",)
                        break
            items.append(it)
        arm.extend(new_arm)
        if spinning:
            for phase in range(3):
                images.append(frame(items, arm, phase))
                durations.append(ms // 3)
        else:
            images.append(frame(items, arm, 0))
            durations.append(ms)
    out = ROOT / "docs" / "brain-wait-demo.gif"
    images[0].save(out, save_all=True, append_images=images[1:], duration=durations, loop=0, optimize=True)
    print(f"written {out} ({len(images)} frames)")


if __name__ == "__main__":
    main()
