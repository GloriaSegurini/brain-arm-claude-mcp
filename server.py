#!/usr/bin/env python3
"""
brain-arm MCP server (stdio transport).
Shared state between the brain (Claude Desktop) and the arms (Claude Code).
Claude Desktop launches this process; shared data lives in data/*.json (see store.py).
"""

import asyncio
import json
import time as _time
from datetime import datetime
from typing import Literal, Optional

from mcp.server import MCPServer

import onboarding
from config import BASE_DIR, CONFIG
from store import DATA_DIR, locked, read_json as load, update_json, write_json

WAIT_WINDOW_SEC = CONFIG["wait_window_sec"]

DATA_DIR.mkdir(exist_ok=True)

CONTEXT_FILE = DATA_DIR / "context.json"
TASKS_FILE   = DATA_DIR / "tasks.json"
LOG_FILE     = DATA_DIR / "log.json"
MODE_FILE    = DATA_DIR / "mode.json"


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def brain_instructions() -> str:
    """The block after the first '---' line of docs/brain-instructions.md (single source for docs and server)."""
    text = (BASE_DIR / "docs" / "brain-instructions.md").read_text(encoding="utf-8")
    return text.split("\n---\n", 1)[-1].strip()


server = MCPServer(
    "brain-arm",
    description="Shared queue and context between the brain (Claude Desktop) and the arms (Claude Code)",
    instructions=brain_instructions(),
)


# ── Setup ───────────────────────────────────────────────────────────────────

@server.tool()
def setup_check() -> str:
    """Check that brain-arm is ready: Claude Code, tmux, watcher, connected projects and folder trust.
    Call it when the user asks to set up brain-arm or when something does not work; then guide the user
    through the TO DO items one at a time.
    """
    return onboarding.setup_check()


@server.tool()
def add_project(name: str, folder: str) -> str:
    """Connect a project: map a short name to the folder with its code, so arms for that project work there.
    'name': lowercase, e.g. "webshop" (or "webshop:checkout" to give one channel its own folder).
    'folder': the folder the user gave you; Linux/Mac paths, ~ and Windows paths (C:\\code\\app) are accepted.
    Ask the user for both; never guess a folder.
    """
    return onboarding.add_project(name, folder)


@server.tool()
def trust_folder(folder: str, user_confirmed: bool = False) -> str:
    """Mark a connected project folder as trusted in Claude Code, so arms don't stop on the trust question.
    Trusting lets arms read, write and run commands in that folder.
    REQUIRES THE USER'S EXPLICIT CONSENT: first tell the user the exact folder and what trusting allows, ask a
    direct yes/no question, and set user_confirmed=True only if the user answered yes for that exact folder
    in this chat. Never assume or infer consent.
    """
    return onboarding.trust_folder(folder, user_confirmed)


# ── Mode ────────────────────────────────────────────────────────────────────

@server.tool()
def set_mode(mode: Literal["brainstorm", "implement"]) -> str:
    """Set the session mode.
    • brainstorm → ideas and shared context only; tasks are disabled.
    • implement  → the brain creates tasks, the arms execute them.
    """
    with locked():
        write_json(MODE_FILE, {"mode": mode, "updated_at": now()})
    return f"Mode → {mode}"


@server.tool()
def get_mode() -> str:
    """Return the current session mode (brainstorm or implement)."""
    data = load(MODE_FILE, {"mode": "brainstorm"})
    return f"Current mode: {data['mode']}"


# ── Shared context ───────────────────────────────────────────────────────────

@server.tool()
def write_context(key: str, value: str) -> str:
    """Save an entry in the shared context (readable by brain and arms).
    Use it for: architecture, decisions, constraints, glossary, ideas.
    """
    with update_json(CONTEXT_FILE, {}) as ctx:
        ctx[key] = {"value": value, "updated_at": now()}
    return f"Context '{key}' saved."


@server.tool()
def read_context(key: Optional[str] = None) -> str:
    """Read the shared context. Omit 'key' to read everything."""
    ctx = load(CONTEXT_FILE, {})
    if key:
        val = ctx.get(key)
        if val is None:
            return f"Key '{key}' not found."
        return json.dumps(val["value"], ensure_ascii=False, indent=2)
    out = {k: v["value"] for k, v in ctx.items()}
    if not out:
        return "Context is empty."
    return json.dumps(out, ensure_ascii=False, indent=2)


@server.tool()
def clear_context(key: Optional[str] = None) -> str:
    """Remove a key from the context, or clear everything if 'key' is omitted."""
    if key:
        with update_json(CONTEXT_FILE, {}) as ctx:
            ctx.pop(key, None)
        return f"Key '{key}' removed."
    with locked():
        write_json(CONTEXT_FILE, {})
    return "Context cleared."


# ── Task queue ───────────────────────────────────────────────────────────────

@server.tool()
def create_task(
    title: str,
    description: str,
    project: str,
    channel: str,
    files: Optional[str] = None,
    priority: Literal["low", "normal", "high"] = "normal",
) -> str:
    """[implement mode only] The brain sends a task to an ARM (Claude Code).
    In the description state: what to do, the logic to apply, files or area, and how to tell it worked.
    'project': REQUIRED, the project key as in the projects map. E.g. "webshop", "data-platform".
    'channel': REQUIRED, this brain chat in kebab-case (always the same for this chat).
    'files': comma-separated paths (optional).
    After creating it, call wait_for_task(task_id) IMMEDIATELY and repeat until it is closed.
    """
    if "default" in (project, channel) or not project.strip() or not channel.strip():
        return ("Task NOT created: project and channel must be this chat's ones, not 'default'. "
                "If you don't know them, propose them to the user, ask for confirmation, then use them "
                "for the whole chat. setup_check() lists the connected projects.")
    mode = load(MODE_FILE, {"mode": "brainstorm"})["mode"]
    if mode != "implement":
        return "Tasks are disabled in 'brainstorm' mode. Call set_mode('implement') first."
    with update_json(TASKS_FILE, []) as tasks:
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(tasks):03d}"
        tasks.append({
            "id":          task_id,
            "project":     project,
            "channel":     channel,
            "title":       title,
            "description": description,
            "files":       [f.strip() for f in files.split(",")] if files else [],
            "priority":    priority,
            "status":      "pending",
            "created_at":  now(),
            "updated_at":  None,
            "result":      None,
        })
    return (f"Task created: {task_id} [project={project} channel={channel}]\n→ {title}\n"
            f"NEXT STEP: call wait_for_task('{task_id}') now and call it again until it answers "
            f"done/failed/needs_clarification. Do not ask the user to tell you when it's finished.")


@server.tool()
def get_tasks(
    status: Literal["pending", "in_progress", "done", "failed", "all"] = "pending",
    project: Optional[str] = None,
    channel: Optional[str] = None,
) -> str:
    """List tasks filtered by status, project and/or channel.
    • project only    → every task of the project
    • project+channel → only the tasks of that brain chat
    • no filter       → all tasks (not recommended with several projects)
    """
    tasks = load(TASKS_FILE, [])
    if status != "all":
        tasks = [t for t in tasks if t["status"] == status]
    if project is not None:
        tasks = [t for t in tasks if t.get("project", "default") == project]
    if channel is not None:
        tasks = [t for t in tasks if t.get("channel", "default") == channel]
    if not tasks:
        label = "".join([
            f" project='{project}'" if project else "",
            f" channel='{channel}'" if channel else "",
        ])
        return f"No tasks with status='{status}'{label}."
    return json.dumps(tasks, ensure_ascii=False, indent=2)


@server.tool()
def list_channels(project: Optional[str] = None) -> str:
    """List the channels (brain chats) grouped by project, with pending / in_progress / done / failed counts.
    Pass 'project' to filter on one project.
    """
    tasks = load(TASKS_FILE, [])
    if project is not None:
        tasks = [t for t in tasks if t.get("project", "default") == project]
    groups: dict = {}
    for t in tasks:
        key = (t.get("project", "default"), t.get("channel", "default"))
        if key not in groups:
            groups[key] = {"pending": 0, "in_progress": 0, "done": 0, "failed": 0}
        s = t.get("status", "pending")
        if s in groups[key]:
            groups[key][s] += 1
    if not groups:
        return "No channels found." + (f" (project='{project}')" if project else "")
    lines = []
    for (proj, ch), counts in sorted(groups.items()):
        lines.append(
            f"project={proj!r:20} channel={ch!r:20} "
            f"pending={counts['pending']} in_progress={counts['in_progress']} "
            f"done={counts['done']} failed={counts['failed']}"
        )
    return "\n".join(lines)


@server.tool()
def update_task(
    task_id: str,
    status: Literal["in_progress", "done", "failed", "needs_clarification"],
    result: Optional[str] = None,
) -> str:
    """Update a task's status (normally done by the arm through arm_helper.py)."""
    with update_json(TASKS_FILE, []) as tasks:
        task = next((t for t in tasks if t["id"] == task_id), None)
        if task is not None:
            task["status"]     = status
            task["result"]     = result
            task["updated_at"] = now()
    if task is None:
        return f"Task '{task_id}' not found."
    return f"Task {task_id} → {status}"


# ── Shared log ───────────────────────────────────────────────────────────────

@server.tool()
def log(message: str, source: Literal["brain", "arm", "user"] = "brain") -> str:
    """Append a message to the shared log."""
    with update_json(LOG_FILE, []) as logs:
        logs.append({"message": message, "source": source, "timestamp": now()})
    return "Log entry added."


@server.tool()
def get_log(last_n: int = 30) -> str:
    """Read the last N messages of the shared log."""
    recent = load(LOG_FILE, [])[-last_n:]
    if not recent:
        return "Log is empty."
    return "\n".join(f"[{e['timestamp']}] [{e['source'].upper():5}] {e['message']}" for e in recent)


# ── Brain synchronization tools ─────────────────────────────────────────────

DONE_STATES = ("done", "failed", "needs_clarification")


def _get_task_by_id(task_id: str):
    """Re-read TASKS_FILE on every call to see the other processes' writes."""
    return next((t for t in load(TASKS_FILE, []) if t["id"] == task_id), None)


def _minutes_since(iso: Optional[str]) -> int:
    try:
        return int((datetime.now() - datetime.fromisoformat(iso)).total_seconds() // 60)
    except (TypeError, ValueError):
        return 0


METRICS_FILE = DATA_DIR / "metrics.jsonl"


@server.tool()
async def wait_for_task(task_id: str) -> str:
    """[BRAIN] Wait for an ARM task to finish (up to about a minute per call; no tokens are spent while it waits).
    If it answers 'wait …', call it again IMMEDIATELY with the same task_id, without writing to the user
    and without asking them to tell you when it's done: waiting is this tool's job.
    When it answers 'done/failed/needs_clarification …', read the outcome with get_result(task_id)."""
    started = _time.time()
    answer = await _wait(task_id)
    try:  # one line per call: lets measure.py count the brain's wait steps exactly
        with METRICS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": now(), "task": task_id, "answer": answer.split()[0],
                                "waited_s": round(_time.time() - started)}) + "\n")
    except OSError:
        pass
    return answer


async def _wait(task_id: str) -> str:
    t = None
    deadline = _time.time() + WAIT_WINDOW_SEC
    while _time.time() < deadline:
        try:
            t = _get_task_by_id(task_id)
        except Exception:
            await asyncio.sleep(3)
            continue
        if t is None:
            return f"unknown {task_id}: no such id, check you copied the id returned by create_task."
        if t["status"] in DONE_STATES:
            return (f'{t["status"]} {task_id} — now call get_result("{task_id}"), '
                    f"check the outcome and report it to the user.")
        await asyncio.sleep(3)
    again = f"Call wait_for_task('{task_id}') again now, without writing to the user."
    if t is None:
        return f"wait {task_id}: queue temporarily unreadable. {again}"
    if t["status"] == "pending":
        mins = _minutes_since(t.get("created_at"))
        if mins >= 3:
            return (f"wait {task_id}: still pending after {mins} min, no arm has picked it up. Likely causes: "
                    f"project/channel ('{t.get('project')}'/'{t.get('channel')}') has no folder in the projects "
                    f"map, or the watcher is not running. Tell the user ONCE with this diagnosis, then call "
                    f"wait_for_task('{task_id}') again.")
        return f"wait {task_id}: pending for {mins} min, an arm is about to pick it up. {again}"
    mins = _minutes_since(t.get("updated_at"))
    return f"wait {task_id}: in_progress for {mins} min, the arm is working on it. {again}"


@server.tool()
def get_result(task_id: str) -> str:
    """[BRAIN] Full output of a closed task."""
    try:
        t = _get_task_by_id(task_id)
        if t is None:
            return f"unknown {task_id}"
        return t.get("result") or "(no result)"
    except Exception as e:
        return f"error {type(e).__name__}: {e}"


@server.tool()
def check_updates(
    ack: bool = True,
    project: Optional[str] = None,
    channel: Optional[str] = None,
) -> str:
    """[BRAIN] Tasks closed by arms and not yet seen by the brain. '0' if nothing new.
    ack=False for a non-destructive read. Filter by 'project' and/or 'channel' to see only your own.
    The cursor is per channel: two brain chats never overwrite each other.
    """
    try:
        cursor_key = "brain_cursor"
        if project:
            cursor_key += f"_{project}"
        if channel:
            cursor_key += f"_{channel}"
        cursor_entry = load(CONTEXT_FILE, {}).get(cursor_key)
        cursor = cursor_entry["value"] if cursor_entry else ""
        new = [
            t for t in load(TASKS_FILE, [])
            if t["status"] in DONE_STATES
            and (t.get("updated_at") or "") > cursor
            and (project is None or t.get("project", "default") == project)
            and (channel is None or t.get("channel", "default") == channel)
        ]
        if not new:
            return "0"
        if ack:
            with update_json(CONTEXT_FILE, {}) as ctx:
                ctx[cursor_key] = {"value": max(t["updated_at"] for t in new), "updated_at": now()}
        return "\n".join(f'{t["id"]} {t["status"]} {t["title"][:60]}' for t in new)
    except Exception as e:
        return f"error {type(e).__name__}: {e}"


# ── Start ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    server.run(transport="stdio")
