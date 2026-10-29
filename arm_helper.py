#!/usr/bin/env python3
"""
The arms' interface to the task queue (no MCP needed; writes are locked, see store.py).
Usage:
  arm_helper.py get PROJECT CHANNEL           → list pending tasks (JSON)
  arm_helper.py start TASK_ID                 → mark in_progress
  arm_helper.py done  TASK_ID "result"        → mark done   ('-' = read the result from stdin)
  arm_helper.py fail  TASK_ID "reason"        → mark failed ('-' = read the reason from stdin)
  arm_helper.py write_context KEY VALUE       → write to context.json ('-' or missing = from stdin)
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
    """Text argument; '-' means read it from stdin (for long texts)."""
    if len(sys.argv) <= i:
        return ""
    return sys.stdin.read() if sys.argv[i] == "-" else sys.argv[i]


def set_status(task_id: str, status: str, result=None) -> None:
    with update_json(TASKS_FILE, []) as tasks:
        task = next((t for t in tasks if t["id"] == task_id), None)
        if task is not None:
            task["status"] = status
            if result is not None:
                task["result"] = result
            task["updated_at"] = now()
    if task is None:
        print(f"error: task {task_id} not found", file=sys.stderr)
        sys.exit(1)


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
    print(f"ok: {sys.argv[2]} → done ({len(result)} characters of result)")

elif cmd == "fail":
    result = text_arg(3)
    set_status(sys.argv[2], "failed", result)
    print(f"ok: {sys.argv[2]} → failed")

elif cmd == "write_context":
    key = sys.argv[2]
    value = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "-" else sys.stdin.read()
    with update_json(CTX_FILE, {}) as ctx:
        ctx[key] = {"value": value, "updated_at": now()}
    print(f"ok: context[{key}] written ({len(value)} chars)")

else:
    print(f"Unknown command: {cmd}", file=sys.stderr)
    sys.exit(1)
