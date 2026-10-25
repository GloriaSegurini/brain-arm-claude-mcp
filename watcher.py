#!/usr/bin/env python3
"""
brain-arm watcher v6 — un arm Claude Code INTERATTIVO per canale, ognuno in una finestra tmux.
Lo vedi in diretta (tmux attach -t arms) e, se serve, approvi i permessi da lì.
Arm: sonnet 5.5, effort medium, permission-mode auto.

Protezioni:
  - 3 uscite rapide (<30s) di fila per canale → task pending marcati failed, canale in pausa 5 min
  - arm al lavoro senza pause da più di 60 min → finestra chiusa, task in_progress marcati failed
  - nessun task pending/in_progress per 1 ora → arm chiuso
  - max 5 arm contemporanei
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

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# (project, channel) -> {"win": "@id", "started": float, "idle_since": float|None, "notified": set}
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
        log(f"[FAIL] {changed} task marcati failed per {project}:{channel}: {reason}")


def ensure_tmux_session():
    if tmux("has-session", "-t", TMUX_SESSION).returncode != 0:
        tmux("new-session", "-d", "-s", TMUX_SESSION, "-n", "status")
        tmux("send-keys", "-t", f"{TMUX_SESSION}:status", f"watch -n3 python3 {STATUS_PY}", "Enter")
        log(f"tmux session '{TMUX_SESSION}' creata")


def window_alive(win: str) -> bool:
    r = tmux("list-windows", "-a", "-F", "#{window_id}")
    return win in r.stdout.split()


NOT_ARM_CMDS = {"tail", "watch", "less"}


def arm_windows() -> list:
    """Finestre tmux 'progetto:canale' in cui gira davvero un arm; chiude quelle vecchie (es. tail -f)."""
    r = tmux("list-windows", "-t", TMUX_SESSION, "-F", "#{window_id} #{pane_current_command} #{window_name}")
    result = []
    for line in r.stdout.strip().splitlines():
        win, cmd, name = (line.split(" ", 2) + ["", ""])[:3]
        if ":" not in name or name == "status":
            continue
        if cmd in NOT_ARM_CMDS:
            tmux("kill-window", "-t", win)
            log(f"[CLEAN] chiusa finestra {name} ({win}): non è un arm ({cmd})")
            continue
        result.append((win, name))
    return result


def adopt_existing_windows():
    """Dopo un riavvio del watcher, riconosce gli arm già aperti invece di duplicarli."""
    for win, name in arm_windows():
        project, _, channel = name.partition(":")
        running[(project, channel)] = {
            "win": win, "started": time.time(), "busy_since": None,
            "idle_since": None, "notified": set()
        }
        log(f"[ADOPT] arm già attivo {name} ({win})")


def arm_prompt(project: str, channel: str, work_dir: str) -> str:
    return (
        f'Sei l\'ARM del progetto "{project}", chat "{channel}".\n'
        f'Cartella di lavoro: {work_dir}. Per file temporanei usa {work_dir}/.arm_scratch/\n'
        f'I task si gestiscono SOLO con questo helper (non usare MCP):\n'
        f'  python3 {HELPER} get {project} {channel}\n'
        f'  python3 {HELPER} start TASK_ID\n'
        f'  python3 {HELPER} done TASK_ID "risultato"\n'
        f'  python3 {HELPER} fail TASK_ID "motivo"\n'
        f'  cat risultato.txt | python3 {HELPER} done TASK_ID -   # risultato lungo da file\n'
        f'  python3 {HELPER} write_context KEY "valore"\n'
        f'  cat file.txt | python3 {HELPER} write_context KEY -\n\n'
        f'Per ogni task: get → start → esegui → done (o fail). Chiudi SEMPRE ogni task con done o fail.\n'
        f'Non fare domande e non chiedere preferenze: se hai un dubbio scegli l\'opzione più sicura.\n'
        f'Se un comando viene negato: fail TASK_ID "PERMESSO NEGATO: <comando> — richiede autorizzazione esplicita".\n'
        f'L\'ultimo comando di ogni task è SEMPRE done o fail: un task lasciato in_progress blocca la brain.\n'
        f'Scrivi "ARM in attesa" e fermati solo quando non ci sono più task pending E hai chiuso tutti quelli avviati.\n'
        f'Se ricevi il messaggio "nuovi task", ricomincia da get.'
    )


def launch_arm(project: str, channel: str, pending_ids: list):
    key = (project, channel)

    if len(running) >= MAX_CONCURRENT:
        log(f"[SKIP] max {MAX_CONCURRENT} arm contemporanei, skip {project}:{channel}")
        return

    f = failures.get(key, {"count": 0, "last_fail": 0.0})
    if f["count"] >= MAX_FAILURES:
        if time.time() - f["last_fail"] > FAILURE_RESET_SEC:
            failures.pop(key, None)
            log(f"[RESET] fallimenti resettati per {project}:{channel}")
        else:
            return

    wname = f"{project}:{channel}"
    for win, name in arm_windows():
        if name == wname:
            running[key] = {"win": win, "started": time.time(), "busy_since": time.time(),
                            "idle_since": None, "notified": set()}
            log(f"[ADOPT] finestra {wname} già aperta ({win}), la riuso invece di duplicarla")
            notify_new_tasks(key, pending_ids)
            return

    projects = load_projects()
    work_dir = projects.get(f"{project}:{channel}") or projects.get(project)
    if not work_dir or not Path(work_dir).is_dir():
        fail_tasks(project, channel, ("pending",),
                   f"progetto '{project}' senza cartella in ~/.brain-arm-projects.json: "
                   f"controlla project/channel nella chat brain o aggiungi il progetto alla mappa")
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
        log(f"[ERR] impossibile aprire finestra tmux per {project}:{channel}: {r.stderr.strip()}")
        return

    with log_file.open("a") as lf:
        lf.write(f"\n[{ts()}] === arm avviato (project={project} channel={channel}) ===\n")
    tmux("pipe-pane", "-o", "-t", win, f"cat >> {shlex.quote(str(log_file))}")

    running[key] = {"win": win, "started": time.time(), "busy_since": time.time(),
                    "idle_since": None, "notified": set(pending_ids)}
    log(f"[ARM] avviato {project}:{channel} finestra={win} model={ARM_MODEL} perm={ARM_PERM}")


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
            log(f"[WAIT-USER] {key[0]}:{key[1]} aspetta una tua conferma nella finestra tmux")
            v["dialog_logged"] = True
        return False
    v["dialog_logged"] = False
    tmux("send-keys", "-t", v["win"], "-l", text)
    tmux("send-keys", "-t", v["win"], "Enter")
    return True


def notify_new_tasks(key: tuple, pending_ids: list):
    v = running[key]
    nuovi = [i for i in pending_ids if i not in v["notified"]]
    if not nuovi:
        return
    if send_to_arm(key, f"nuovi task ({len(nuovi)}): ricomincia da get"):
        v["notified"].update(nuovi)
        log(f"[NOTIFY] {key[0]}:{key[1]} — {len(nuovi)} nuovi task segnalati all'arm")


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
        msg = (f"Promemoria del watcher: {ids} risulta ancora in_progress ma la sessione e' ferma. "
               f"Se il lavoro e' finito chiudilo ORA con arm_helper.py done (o fail) e il risultato. "
               f"Se stai aspettando un processo in background rispondi solo: in attesa")
        if send_to_arm(key, msg):
            v["nudges"] = nudges + 1
            v["last_nudge"] = now
            log(f"[NUDGE] {key[0]}:{key[1]} promemoria {v['nudges']}/{STUCK_MAX_NUDGES} per {ids}")


def cleanup_finished():
    for key in [k for k, v in running.items() if not window_alive(v["win"])]:
        runtime = time.time() - running[key]["started"]
        log(f"[ARM] chiuso {key[0]}:{key[1]} runtime={runtime:.0f}s")
        if runtime < FAST_EXIT_SEC:
            f = failures.setdefault(key, {"count": 0, "last_fail": 0.0})
            f["count"] += 1
            f["last_fail"] = time.time()
            log(f"[WARN] {key[0]}:{key[1]} uscito in {runtime:.0f}s — tentativo {f['count']}/{MAX_FAILURES}")
            if f["count"] >= MAX_FAILURES:
                log(f"[STOP] {key[0]}:{key[1]} in pausa dopo {MAX_FAILURES} uscite rapide")
                fail_tasks(key[0], key[1], ("pending",),
                           f"arm uscito {MAX_FAILURES} volte di fila all'avvio — controlla la finestra tmux/log")
        del running[key]


def kill_stale(counts: dict):
    for key, v in list(running.items()):
        if v["busy_since"] is None:
            continue
        busy = time.time() - v["busy_since"]
        c = counts.get(key, {"pending": [], "in_progress": []})
        if busy > STARTUP_TIMEOUT_SEC and not c["in_progress"]:
            log(f"[KILL] {key[0]}:{key[1]} non ha preso nessun task in {busy/60:.0f}min — bloccato, chiudo")
            tmux("kill-window", "-t", v["win"])
            fail_tasks(key[0], key[1], ("pending",),
                       "arm bloccato all'avvio (nessun task preso in 10 min): guarda il log del canale")
            del running[key]
        elif busy > MAX_RUNTIME_SEC:
            log(f"[KILL] {key[0]}:{key[1]} al lavoro da {busy/60:.0f}min senza pause — chiudo")
            tmux("kill-window", "-t", v["win"])
            fail_tasks(key[0], key[1], ("in_progress", "pending"), "arm chiuso per timeout (60 min)")
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
            log(f"[IDLE] {key[0]}:{key[1]} senza task da {IDLE_EXIT_SEC}s — chiudo")
            tmux("kill-window", "-t", v["win"])
            del running[key]


log(f"watcher v6 avviato — interattivo in tmux, model={ARM_MODEL} effort={ARM_EFFORT} perm={ARM_PERM}")
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
                           "manca project/channel: nella chat brain chiama "
                           "write_context('__brain__', 'project=X channel=Y') e reinvia il task")
                continue
            if key in running:
                notify_new_tasks(key, c["pending"])
            else:
                log(f"[NEW] {len(c['pending'])} task pending su {key[0]}:{key[1]}")
                launch_arm(key[0], key[1], c["pending"])
    except Exception as e:
        log(f"[ERR] {e}")
    time.sleep(POLL)
