#!/usr/bin/env python3
"""brain-arm status — usato da `watch -n3 python3 status.py` nella finestra tmux."""
from datetime import datetime

from config import CONFIG, DATA_DIR, LOGS_DIR
from store import read_json

TASKS_FILE = DATA_DIR / "tasks.json"

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


if not TASKS_FILE.exists():
    print("tasks.json non trovato")
    raise SystemExit

tasks = read_json(TASKS_FILE, [])

channels: dict = {}
for t in tasks:
    key = (t.get("project", "default"), t.get("channel", "default"))
    if key not in channels:
        channels[key] = {"pending": 0, "in_progress": 0, "done": 0, "failed": 0}
    s = t.get("status", "pending")
    if s in channels[key]:
        channels[key][s] += 1

print(c("bold", f"  brain-arm status — {datetime.now().strftime('%H:%M:%S')}"))
print(c("gray", "  " + "─" * 66))
print(c("bold", f"  {'PROJECT':<18} {'CHANNEL':<22} {'PEND':>5} {'RUN':>5} {'DONE':>5} {'FAIL':>5}"))
print(c("gray", "  " + "─" * 66))

for (proj, ch), cnt in sorted(channels.items()):
    # controlla se c'è un log attivo (arm in esecuzione)
    log_file = LOGS_DIR / f"{proj}--{ch}.log"
    arm_active = ""
    if log_file.exists():
        import time as _t
        age = _t.time() - log_file.stat().st_mtime
        arm_active = c("green", " ●") if age < 30 else c("gray", " ○")

    pend_str  = c("yellow", f"{cnt['pending']:>5}") if cnt["pending"] else f"{cnt['pending']:>5}"
    run_str   = c("cyan",   f"{cnt['in_progress']:>5}") if cnt["in_progress"] else f"{cnt['in_progress']:>5}"
    fail_str  = c("red",    f"{cnt['failed']:>5}") if cnt["failed"] else f"{cnt['failed']:>5}"

    print(f"  {proj:<18} {ch:<22}{arm_active} {pend_str} {run_str} {cnt['done']:>5} {fail_str}")

print(c("gray", "  " + "─" * 66))
print(c("gray", f"  totale: {len(tasks)} task in {len(channels)} canali"))
print()
print(c("gray", f"  tmux: attach -t {CONFIG['tmux_session']}  |  finestre: status  proj:channel ..."))
