#!/usr/bin/env python3
"""
Helper per arm: legge e aggiorna la coda senza MCP (scritture con lock, vedi store.py).
Uso:
  arm_helper.py get PROJECT CHANNEL           → lista task pending (JSON)
  arm_helper.py start TASK_ID                 → marca in_progress
  arm_helper.py done  TASK_ID "risultato"     → marca done   ('-' = risultato da stdin)
  arm_helper.py fail  TASK_ID "motivo"        → marca failed ('-' = motivo da stdin)
  arm_helper.py write_context KEY VALUE       → scrive in context.json ('-' o assente = da stdin)
"""
import json
import sys
from datetime import datetime

from store import DATA_DIR, read_json, update_json

TASKS_FILE = DATA_DIR / "tasks.json"
CTX_FILE   = DATA_DIR / "context.json"


def now():
    return datetime.now().isoformat(timespec="seconds")


def text_arg(i: int) -> str:
    """Argomento di testo; '-' = leggi da stdin, per testi lunghi."""
    if len(sys.argv) <= i:
        return ""
    return sys.stdin.read() if sys.argv[i] == "-" else sys.argv[i]


def set_status(task_id: str, status: str, result=None) -> bool:
    with update_json(TASKS_FILE, []) as tasks:
        task = next((t for t in tasks if t["id"] == task_id), None)
        if task is not None:
            task["status"] = status
            if result is not None:
                task["result"] = result
            task["updated_at"] = now()
    if task is None:
        print(f"errore: task {task_id} non trovato", file=sys.stderr)
        sys.exit(1)
    return True


cmd = sys.argv[1] if len(sys.argv) > 1 else ""

if cmd == "get":
    project, channel = sys.argv[2], sys.argv[3]
    pending = [
        t for t in read_json(TASKS_FILE, [])
        if t["status"] == "pending"
        and t.get("project", "default") == project
        and t.get("channel", "default") == channel
    ]
    print(json.dumps(pending, indent=2, ensure_ascii=False))

elif cmd == "start":
    set_status(sys.argv[2], "in_progress")
    print(f"ok: {sys.argv[2]} → in_progress")

elif cmd == "done":
    result = text_arg(3)
    set_status(sys.argv[2], "done", result)
    print(f"ok: {sys.argv[2]} → done ({len(result)} caratteri di risultato)")

elif cmd == "fail":
    result = text_arg(3)
    set_status(sys.argv[2], "failed", result)
    print(f"ok: {sys.argv[2]} → failed")

elif cmd == "write_context":
    key = sys.argv[2]
    value = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "-" else sys.stdin.read()
    with update_json(CTX_FILE, {}) as ctx:
        ctx[key] = {"value": value, "updated_at": now()}
    print(f"ok: context[{key}] scritto ({len(value)} chars)")

else:
    print(f"Comando sconosciuto: {cmd}", file=sys.stderr)
    sys.exit(1)
