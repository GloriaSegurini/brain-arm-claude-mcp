#!/usr/bin/env python3
"""Generate docs/architecture-demo.gif: the architecture diagram walking through the life of a task,
highlighting the components involved in each step. Requires Pillow. Run: python3 docs/make_architecture_gif.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

S, OX, OY = 1.3, 20, 10          # scale and offset of the 680x390 layout
W, H = 920, 700
BG, CARD, FG, MUTED, LINE, HI = (31, 30, 28), (42, 41, 38), (236, 235, 232), (163, 161, 155), (70, 69, 64), (217, 119, 87)
BRAIN, BRAIN_S = (60, 52, 137), (175, 169, 236)
INFRA, INFRA_S = (68, 68, 65), (180, 178, 169)

f_t = ImageFont.truetype(SANS_B, 18)
f_s = ImageFont.truetype(MONO, 14)
f_z = ImageFont.truetype(SANS, 15)
f_h = ImageFont.truetype(SANS_B, 20)
f_p = ImageFont.truetype(SANS, 16)
f_k = ImageFont.truetype(SANS, 14)

NODES = {  # id: (x, y, w, h, title, subtitle, is_claude)
    "brain":   (40, 28, 240, 58, "Brain", "Claude Desktop chat", True),
    "mcp":     (60, 152, 180, 58, "MCP server", "server.py (stdio)", False),
    "queue":   (280, 152, 160, 58, "Task queue", "data/tasks.json", False),
    "status":  (480, 152, 150, 58, "Status table", "status.py", False),
    "watcher": (60, 280, 180, 58, "Watcher", "every 5 s", False),
    "arm":     (280, 280, 160, 58, "Arm", "Claude Code in tmux", True),
    "repo":    (480, 280, 150, 58, "Repository", "projects map", False),
}
EDGES = [  # polylines in layout coordinates; (points, arrow at start?)
    ([(150, 86), (150, 150)], False),
    ([(240, 181), (278, 181)], False),
    ([(440, 181), (478, 181)], False),
    ([(300, 210), (300, 244), (170, 244), (170, 278)], False),
    ([(380, 278), (380, 212)], True),
    ([(240, 309), (278, 309)], False),
    ([(440, 309), (478, 309)], False),
]
STEPS = [
    ("Decide with the brain", ["brain"],
     "You discuss the change in the Claude Desktop chat. When there's something to do, the brain writes a precise task."),
    ("create_task", ["brain", "mcp", "queue"],
     "The brain calls create_task(project, channel, …). The server stores it in the queue as pending and tells the brain: call wait_for_task now."),
    ("The brain waits — for free", ["brain", "mcp"],
     "wait_for_task waits inside the server for up to ~50 s (no tokens). If the task isn't done it answers \"wait, call again\" and the brain calls again."),
    ("The watcher sees the task", ["queue", "watcher", "status"],
     "Within 5 s the watcher (plain Python, no tokens) reads the pending task. The status table shows it in PEND."),
    ("An arm starts", ["watcher", "arm"],
     "The watcher opens a tmux window and starts Claude Code in the project's folder — or tells the already-open arm: new tasks."),
    ("The arm takes the task", ["arm", "queue", "status"],
     "arm_helper.py get, then start: the task becomes in_progress (RUN) and the dot turns ●."),
    ("The arm works", ["arm", "repo"],
     "It reads, edits and tests in the repository, under Claude Code's permissions and auto mode."),
    ("The arm closes the task", ["arm", "queue", "status"],
     "arm_helper.py done with the result. Then it writes \"ARM waiting\" and stops: an idle arm costs nothing."),
    ("The brain reports", ["brain", "mcp", "queue"],
     "wait_for_task answers done; the brain reads the result with get_result, checks it and reports to you."),
    ("Housekeeping", ["watcher", "arm"],
     "Idle arms close after 1 h; arms stuck or working too long are closed; at most 5 arms at once."),
]


def p(x, y):
    return OX + x * S, OY + y * S


def mix(c, t=0.72):
    return tuple(int(a * (1 - t) + b * t) for a, b in zip(c, BG))


def arrow(d, a, b, color):
    import math
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for da in (2.6, -2.6):
        d.line([b, (b[0] + 9 * math.cos(ang + da), b[1] + 9 * math.sin(ang + da))], fill=color, width=2)


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


def frame(n):
    title, active, text = STEPS[n]
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text(p(300, 52), "Windows / Mac · Claude Desktop", font=f_z, fill=MUTED)
    x0, y0 = p(30, 116)
    x1, y1 = p(650, 366)
    for x in range(int(x0), int(x1), 14):
        d.line([(x, y0), (min(x + 7, x1), y0)], fill=LINE)
        d.line([(x, y1), (min(x + 7, x1), y1)], fill=LINE)
    for y in range(int(y0), int(y1), 14):
        d.line([(x0, y), (x0, min(y + 7, y1))], fill=LINE)
        d.line([(x1, y), (x1, min(y + 7, y1))], fill=LINE)
    d.text(p(46, 346), "Your machine (WSL2 on Windows, or macOS)", font=f_z, fill=MUTED)
    for pts, both in EDGES:
        q = [p(*pt) for pt in pts]
        d.line(q, fill=MUTED, width=2)
        arrow(d, q[-2], q[-1], MUTED)
        if both:
            arrow(d, q[1], q[0], MUTED)
    for nid, (x, y, w, h, t, s, claude) in NODES.items():
        fill, stroke = (BRAIN, BRAIN_S) if claude else (INFRA, INFRA_S)
        on = nid in active
        if not on:
            fill, stroke = mix(fill), mix(stroke)
        a, b = p(x, y), p(x + w, y + h)
        d.rounded_rectangle([a, b], 10, fill=fill, outline=HI if on else stroke, width=3 if on else 1)
        cx = (a[0] + b[0]) / 2
        d.text((cx, a[1] + 22), t, font=f_t, fill=FG if on else mix(FG), anchor="mm")
        d.text((cx, a[1] + 50), s, font=f_s, fill=MUTED if on else mix(MUTED), anchor="mm")
    top = OY + 395 * S + 6
    d.rounded_rectangle([20, top, W - 20, H - 20], 12, fill=CARD)
    d.text((40, top + 14), f"Step {n + 1} of {len(STEPS)}", font=f_k, fill=MUTED)
    d.text((40, top + 36), title, font=f_h, fill=FG)
    for i, ln in enumerate(wrap(text, f_p, W - 90)):
        d.text((40, top + 68 + 23 * i), ln, font=f_p, fill=FG)
    d.text((W - 40, top + 14), "purple = Claude at work · gray = plain code, no tokens", font=f_k, fill=MUTED, anchor="ra")
    return img


def main():
    images = [frame(n) for n in range(len(STEPS))]
    out = ROOT / "docs" / "architecture-demo.gif"
    images[0].save(out, save_all=True, append_images=images[1:], duration=4200, loop=0, optimize=True)
    print(f"written {out} ({len(images)} frames)")


if __name__ == "__main__":
    main()
