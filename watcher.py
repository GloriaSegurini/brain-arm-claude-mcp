#!/usr/bin/env python3
"""
brain-arm watcher — one INTERACTIVE Claude Code arm per channel, each in its own tmux window.
Watch it live (tmux attach -t arms) and, if needed, answer prompts from there.
Defaults (config.py): Sonnet 5.5, medium effort, auto permission mode.

Safety limits:
  - 3 fast exits (<30 s) in a row for a channel → its pending tasks fail, channel paused 5 min
  - an arm working without a pause for more than 60 min → window closed, its tasks fail
  - an arm that picks up no task within 10 min → window closed, pending tasks fail
  - no pending/in_progress task for 1 hour → arm closed
  - at most 5 arms at the same time
"""
import json
import shlex
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

from config import BASE_DIR, CONFIG, DATA_DIR, LOGS_DIR
from store import read_json, update_json

TASKS_FILE    = DATA_DIR / "tasks.json"
WATCHER_LOG   = DATA_DIR / "watcher.log"
PROJECTS_FILE = CONFIG["projects_file"]
TMUX_SESSION  = CONFIG["tmux_session"]
STATUS_PY     = BASE_DIR / "status.py"
HELPER        = str(BASE_DIR / "arm_helper.py")
POLL          = CONFIG["poll_seconds"]

ARM_MODEL  = CONFIG["arm_model"]
ARM_EFFORT = CONFIG["arm_effort"]
ARM_PERM   = CONFIG["arm_permission_mode"]
CLAUDE_BIN = shutil.which("claude") or "claude"

MAX_FAILURES        = CONFIG["max_failures"]
FAST_EXIT_SEC       = CONFIG["fast_exit_sec"]
FAILURE_RESET_SEC   = CONFIG["failure_reset_sec"]
MAX_RUNTIME_SEC     = CONFIG["max_runtime_sec"]
STARTUP_TIMEOUT_SEC = CONFIG["startup_timeout_sec"]
IDLE_EXIT_SEC       = CONFIG["idle_exit_sec"]
MAX_CONCURRENT      = CONFIG["max_concurrent"]
STUCK_NUDGE_SEC     = CONFIG["stuck_nudge_sec"]
STUCK_RENUDGE_SEC   = CONFIG["stuck_renudge_sec"]
STUCK_MAX_NUDGES    = CONFIG["stuck_max_nudges"]

# First words of every arm prompt: stop-arms.sh and `pgrep -af` use them to find arm processes.
ARM_MARKER = "You are the ARM for project"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# (project, channel) -> {"win": "@id", "started": float, "busy_since": float|None, "idle_since": float|None, "notified": set}
running: dict = {}
# (project, channel) -> {"count": int, "last_fail": float}
failures: dict = {}


def ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def log(msg: str):
    line = f"[{ts()}] {msg}"
    print(line, flush=True)
    with WATCHER_LOG.open("a") as f:
        f.write(line + "\n")


def tmux(*args) -> subprocess.CompletedProcess:
    return subprocess.run(["tmux", *args], capture_output=True, text=True)


def load_projects() -> dict:
    if PROJECTS_FILE.exists():
        return json.loads(PROJECTS_FILE.read_text())
    return {}


def load_tasks() -> list:
    return read_json(TASKS_FILE, [])


def channel_counts() -> dict:
    result: dict = {}
    for t in load_tasks():
        if t["status"] in ("pending", "in_progress"):
            key = (t.get("project", "default"), t.get("channel", "default"))
            c = result.setdefault(key, {"pending": [], "in_progress": []})
            c[t["status"]].append(t["id"])
    return result


def fail_tasks(project: str, channel: str, statuses: tuple, reason: str):
    changed = 0
    with update_json(TASKS_FILE, []) as tasks:
        for t in tasks:
            if (t["status"] in statuses
                    and t.get("project", "default") == project
                    and t.get("channel", "default") == channel):
                t["status"] = "failed"
                t["result"] = reason
                t["updated_at"] = ts()
                changed += 1
    if changed:
        log(f"[FAIL] {changed} task(s) failed for {project}:{channel}: {reason}")


def ensure_tmux_session():
    if tmux("has-session", "-t", TMUX_SESSION).returncode != 0:
        tmux("new-session", "-d", "-s", TMUX_SESSION, "-n", "status")
        tmux("send-keys", "-t", f"{TMUX_SESSION}:status", f"watch -n3 python3 {STATUS_PY}", "Enter")
        log(f"tmux session '{TMUX_SESSION}' created")


def window_alive(win: str) -> bool:
    r = tmux("list-windows", "-a", "-F", "#{window_id}")
    return win in r.stdout.split()


NOT_ARM_CMDS = {"tail", "watch", "less"}


def arm_windows() -> list:
    """'project:channel' tmux windows that really run an arm; closes leftovers (e.g. an old tail -f)."""
    r = tmux("list-windows", "-t", TMUX_SESSION, "-F", "#{window_id} #{pane_current_command} #{window_name}")
    result = []
    for line in r.stdout.strip().splitlines():
        win, cmd, name = (line.split(" ", 2) + ["", ""])[:3]
        if ":" not in name or name == "status":
            continue
        if cmd in NOT_ARM_CMDS:
            tmux("kill-window", "-t", win)
            log(f"[CLEAN] closed window {name} ({win}): not an arm ({cmd})")
            continue
        result.append((win, name))
    return result


def adopt_existing_windows():
    """After a watcher restart, take over the arms that are already open instead of duplicating them."""
    for win, name in arm_windows():
        project, _, channel = name.partition(":")
        running[(project, channel)] = {
            "win": win, "started": time.time(), "busy_since": None,
            "idle_since": None, "notified": set()
        }
        log(f"[ADOPT] arm already running {name} ({win})")


def arm_prompt(project: str, channel: str, work_dir: str) -> str:
    return (
        f'{ARM_MARKER} "{project}", chat "{channel}".\n'
        f'Working directory: {work_dir}. For temporary files use {work_dir}/.arm_scratch/\n'
        f'Manage tasks ONLY with this helper (do not use MCP):\n'
        f'  python3 {HELPER} get {project} {channel}\n'
        f'  python3 {HELPER} start TASK_ID\n'
        f'  python3 {HELPER} done TASK_ID "result"\n'
        f'  python3 {HELPER} fail TASK_ID "reason"\n'
        f'  cat result.txt | python3 {HELPER} done TASK_ID -   # long result from a file\n'
        f'  python3 {HELPER} write_context KEY "value"\n'
        f'  cat file.txt | python3 {HELPER} write_context KEY -\n\n'
        f'For each task: get → start → do the work → done (or fail). ALWAYS close every task with done or fail.\n'
        f'Do not ask questions or preferences: if in doubt, choose the safest option.\n'
        f'If a command is denied: fail TASK_ID "PERMISSION DENIED: <command> — needs explicit authorization".\n'
        f'The last command of every task is ALWAYS done or fail: a task left in_progress blocks the brain.\n'
        f'Write "ARM waiting" and stop only when there are no pending tasks AND you closed every task you started.\n'
        f'When you receive the message "new tasks", start again from get.'
    )


def launch_arm(project: str, channel: str, pending_ids: list):
    key = (project, channel)

    if len(running) >= MAX_CONCURRENT:
        log(f"[SKIP] {MAX_CONCURRENT} arms already running, skipping {project}:{channel}")
        return

    f = failures.get(key, {"count": 0, "last_fail": 0.0})
    if f["count"] >= MAX_FAILURES:
        if time.time() - f["last_fail"] > FAILURE_RESET_SEC:
            failures.pop(key, None)
            log(f"[RESET] failure counter reset for {project}:{channel}")
        else:
            return

    wname = f"{project}:{channel}"
    for win, name in arm_windows():
        if name == wname:
            running[key] = {"win": win, "started": time.time(), "busy_since": time.time(),
                            "idle_since": None, "notified": set()}
            log(f"[ADOPT] window {wname} already open ({win}), reusing it")
            notify_new_tasks(key, pending_ids)
            return

    projects = load_projects()
    work_dir = projects.get(f"{project}:{channel}") or projects.get(project)
    if not work_dir or not Path(work_dir).is_dir():
        fail_tasks(project, channel, ("pending",),
                   f"project '{project}' has no folder in the projects map ({PROJECTS_FILE}): "
                   f"check project/channel in the brain chat or add the project to the map")
        return
    log_file = LOGS_DIR / f"{project}--{channel}.log"

    scratch = Path(work_dir) / ".arm_scratch"
    scratch.mkdir(exist_ok=True)
    exclude = Path(work_dir) / ".git" / "info" / "exclude"
    if exclude.exists() and ".arm_scratch/" not in exclude.read_text():
        with exclude.open("a") as ex:
            ex.write("\n.arm_scratch/\n")

    cmd = " ".join(shlex.quote(x) for x in [
        CLAUDE_BIN,
        "--model", ARM_MODEL,
        "--effort", ARM_EFFORT,
        "--permission-mode", ARM_PERM,
        arm_prompt(project, channel, work_dir),
    ])

    r = tmux("new-window", "-d", "-t", f"{TMUX_SESSION}:", "-n", f"{project}:{channel}",
             "-c", work_dir, "-P", "-F", "#{window_id}", cmd)
    win = r.stdout.strip()
    if r.returncode != 0 or not win:
        log(f"[ERR] cannot open a tmux window for {project}:{channel}: {r.stderr.strip()}")
        return

    with log_file.open("a") as lf:
        lf.write(f"\n[{ts()}] === arm started (project={project} channel={channel}) ===\n")
    tmux("pipe-pane", "-o", "-t", win, f"cat >> {shlex.quote(str(log_file))}")

    running[key] = {"win": win, "started": time.time(), "busy_since": time.time(),
                    "idle_since": None, "notified": set(pending_ids)}
    log(f"[ARM] started {project}:{channel} window={win} model={ARM_MODEL} perm={ARM_PERM}")


DIALOG_MARKERS = ("Do you want", "Esc to cancel", "Enter to confirm", "trust this folder", "❯ 1.")


def dialog_open(win: str) -> bool:
    """True if the arm shows a question/permission dialog: typing into it could pick an option."""
    try:
        screen = subprocess.run(["tmux", "capture-pane", "-p", "-t", win],
                                capture_output=True, text=True, timeout=5).stdout
    except subprocess.TimeoutExpired:
        return True
    return any(m in screen for m in DIALOG_MARKERS)


def send_to_arm(key: tuple, text: str) -> bool:
    v = running[key]
    if dialog_open(v["win"]):
        if not v.get("dialog_logged"):
            log(f"[WAIT-USER] {key[0]}:{key[1]} is waiting for your confirmation in its tmux window")
            v["dialog_logged"] = True
        return False
    v["dialog_logged"] = False
    tmux("send-keys", "-t", v["win"], "-l", text)
    tmux("send-keys", "-t", v["win"], "Enter")
    return True


def notify_new_tasks(key: tuple, pending_ids: list):
    v = running[key]
    new = [i for i in pending_ids if i not in v["notified"]]
    if not new:
        return
    if send_to_arm(key, f"new tasks ({len(new)}): start again from get"):
        v["notified"].update(new)
        log(f"[NOTIFY] {key[0]}:{key[1]} — {len(new)} new task(s) passed to the arm")


def nudge_stuck(counts: dict):
    """Task in_progress but the arm's screen hasn't changed for a while: it probably forgot done/fail."""
    now = time.time()
    for key, v in list(running.items()):
        c = counts.get(key)
        if not c or not c["in_progress"]:
            v["nudges"] = 0
            continue
        try:
            quiet = now - (LOGS_DIR / f"{key[0]}--{key[1]}.log").stat().st_mtime
        except FileNotFoundError:
            continue
        nudges = v.get("nudges", 0)
        if (quiet < STUCK_NUDGE_SEC or nudges >= STUCK_MAX_NUDGES
                or (nudges and now - v.get("last_nudge", 0) < STUCK_RENUDGE_SEC)):
            continue
        ids = ", ".join(c["in_progress"])
        msg = (f"Reminder from the watcher: {ids} is still in_progress but the session is idle. "
               f"If the work is finished, close it NOW with arm_helper.py done (or fail) and the result. "
               f"If you are waiting for a background process, just answer: waiting")
        if send_to_arm(key, msg):
            v["nudges"] = nudges + 1
            v["last_nudge"] = now
            log(f"[NUDGE] {key[0]}:{key[1]} reminder {v['nudges']}/{STUCK_MAX_NUDGES} for {ids}")


def cleanup_finished():
    for key in [k for k, v in running.items() if not window_alive(v["win"])]:
        runtime = time.time() - running[key]["started"]
        log(f"[ARM] closed {key[0]}:{key[1]} runtime={runtime:.0f}s")
        if runtime < FAST_EXIT_SEC:
            f = failures.setdefault(key, {"count": 0, "last_fail": 0.0})
            f["count"] += 1
            f["last_fail"] = time.time()
            log(f"[WARN] {key[0]}:{key[1]} exited after {runtime:.0f}s — attempt {f['count']}/{MAX_FAILURES}")
            if f["count"] >= MAX_FAILURES:
                log(f"[STOP] {key[0]}:{key[1]} paused after {MAX_FAILURES} fast exits")
                fail_tasks(key[0], key[1], ("pending",),
                           f"arm exited {MAX_FAILURES} times in a row at startup — check its tmux window/log")
        del running[key]


def kill_stale(counts: dict):
    for key, v in list(running.items()):
        if v["busy_since"] is None:
            continue
        busy = time.time() - v["busy_since"]
        c = counts.get(key, {"pending": [], "in_progress": []})
        if busy > STARTUP_TIMEOUT_SEC and not c["in_progress"]:
            log(f"[KILL] {key[0]}:{key[1]} picked up no task in {busy/60:.0f} min — stuck, closing")
            tmux("kill-window", "-t", v["win"])
            fail_tasks(key[0], key[1], ("pending",),
                       f"arm stuck at startup (no task picked up in {STARTUP_TIMEOUT_SEC // 60} min): check the channel log")
            del running[key]
        elif busy > MAX_RUNTIME_SEC:
            log(f"[KILL] {key[0]}:{key[1]} working for {busy/60:.0f} min without a pause — closing")
            tmux("kill-window", "-t", v["win"])
            fail_tasks(key[0], key[1], ("in_progress", "pending"),
                       f"arm closed by the runtime limit ({MAX_RUNTIME_SEC // 60} min)")
            del running[key]


def close_idle(counts: dict):
    now = time.time()
    for key, v in list(running.items()):
        c = counts.get(key)
        if c and (c["pending"] or c["in_progress"]):
            v["idle_since"] = None
            if v["busy_since"] is None:
                v["busy_since"] = now
            continue
        v["busy_since"] = None
        if v["idle_since"] is None:
            v["idle_since"] = now
        elif now - v["idle_since"] > IDLE_EXIT_SEC:
            log(f"[IDLE] {key[0]}:{key[1]} no tasks for {IDLE_EXIT_SEC}s — closing")
            tmux("kill-window", "-t", v["win"])
            del running[key]


log(f"watcher started — interactive arms in tmux, model={ARM_MODEL} effort={ARM_EFFORT} perm={ARM_PERM}")
ensure_tmux_session()
adopt_existing_windows()

while True:
    try:
        cleanup_finished()
        counts = channel_counts()
        kill_stale(counts)
        counts = channel_counts()
        close_idle(counts)
        nudge_stuck(counts)
        for key, c in counts.items():
            if not c["pending"]:
                continue
            if "default" in key:
                fail_tasks(key[0], key[1], ("pending",),
                           "missing project/channel: in the brain chat call "
                           "write_context('__brain__', 'project=X channel=Y') and send the task again")
                continue
            if key in running:
                notify_new_tasks(key, c["pending"])
            else:
                log(f"[NEW] {len(c['pending'])} pending task(s) on {key[0]}:{key[1]}")
                launch_arm(key[0], key[1], c["pending"])
    except Exception as e:
        log(f"[ERR] {e}")
    time.sleep(POLL)
