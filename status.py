#!/usr/bin/env python3
"""brain-arm status table — run with `watch -n3 python3 status.py` (the watcher does it in tmux window 0)."""
import time
from datetime import datetime

from config import CONFIG, DATA_DIR, LOGS_DIR
from store import read_json

TASKS_FILE = DATA_DIR / "tasks.json"
ACTIVE_LOG_SEC = 30  # an arm whose screen changed in the last 30 s is shown as active (●)

COLORS = {
    "reset":   "\033[0m",
    "bold":    "\033[1m",
    "green":   "\033[32m",
    "yellow":  "\033[33m",
    "red":     "\033[31m",
    "cyan":    "\033[36m",
    "gray":    "\033[90m",
}


def c(name, text):
    return COLORS.get(name, "") + str(text) + COLORS["reset"]


def count_by_channel(tasks: list) -> dict:
    channels: dict = {}
    for t in tasks:
        key = (t.get("project", "default"), t.get("channel", "default"))
        cnt = channels.setdefault(key, {"pending": 0, "in_progress": 0, "done": 0, "failed": 0})
        s = t.get("status", "pending")
        if s in cnt:
            cnt[s] += 1
    return channels


def render(tasks: list, arm_state: dict, clock: str, tmux_session: str = "arms") -> str:
    """arm_state: (project, channel) -> True (arm working ●) / False (arm idle or closed ○); missing = no arm yet."""
    channels = count_by_channel(tasks)
    out = [
        c("bold", f"  brain-arm status — {clock}"),
        c("gray", "  " + "─" * 66),
        c("bold", f"  {'PROJECT':<18} {'CHANNEL':<22} {'PEND':>5} {'RUN':>5} {'DONE':>5} {'FAIL':>5}"),
        c("gray", "  " + "─" * 66),
    ]
    for (proj, ch), cnt in sorted(channels.items()):
        state = arm_state.get((proj, ch))
        dot = "" if state is None else (c("green", " ●") if state else c("gray", " ○"))
        pend = c("yellow", f"{cnt['pending']:>5}") if cnt["pending"] else f"{cnt['pending']:>5}"
        run = c("cyan", f"{cnt['in_progress']:>5}") if cnt["in_progress"] else f"{cnt['in_progress']:>5}"
        fail = c("red", f"{cnt['failed']:>5}") if cnt["failed"] else f"{cnt['failed']:>5}"
        out.append(f"  {proj:<18} {ch:<22}{dot} {pend} {run} {cnt['done']:>5} {fail}")
    out += [
        c("gray", "  " + "─" * 66),
        c("gray", f"  total: {len(tasks)} tasks in {len(channels)} channels"),
        "",
        c("gray", f"  tmux: attach -t {tmux_session}  |  windows: status  project:channel ..."),
    ]
    return "\n".join(out)


def live_arm_state(tasks: list) -> dict:
    state = {}
    for key in count_by_channel(tasks):
        log_file = LOGS_DIR / f"{key[0]}--{key[1]}.log"
        if log_file.exists():
            state[key] = time.time() - log_file.stat().st_mtime < ACTIVE_LOG_SEC
    return state


if __name__ == "__main__":
    tasks = read_json(TASKS_FILE, [])
    print(render(tasks, live_arm_state(tasks), datetime.now().strftime("%H:%M:%S"), CONFIG["tmux_session"]))
