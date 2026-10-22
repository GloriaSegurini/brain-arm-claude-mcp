#!/usr/bin/env python3
"""
brain-arm MCP server — stdio transport
Contesto condiviso tra Claude for Windows (brain) e Claude Code / WSL (arm).
Ogni client lancia il processo; i dati condivisi vivono in data/*.json (vedi store.py).
"""

import asyncio
import json
import time as _time
from datetime import datetime
from typing import Literal, Optional

from mcp.server import MCPServer

from store import DATA_DIR, locked, read_json as load, update_json, write_json

DATA_DIR.mkdir(exist_ok=True)

CONTEXT_FILE = DATA_DIR / "context.json"
TASKS_FILE   = DATA_DIR / "tasks.json"
LOG_FILE     = DATA_DIR / "log.json"
MODE_FILE    = DATA_DIR / "mode.json"


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


server = MCPServer(
    "brain-arm",
    description="Contesto condiviso brain (Claude for Windows) <-> arm (Claude Code)",
)


# ── Modalità ────────────────────────────────────────────────────────────────

@server.tool()
def set_mode(mode: Literal["brainstorm", "implement"]) -> str:
    """Imposta la modalità della sessione.
    • brainstorm → solo ideazione e contesto condiviso; i task sono bloccati.
    • implement  → brain crea task, arm li esegue.
    """
    with locked():
        write_json(MODE_FILE, {"mode": mode, "updated_at": now()})
    return f"Modalità → {mode}"


@server.tool()
def get_mode() -> str:
    """Restituisce la modalità corrente della sessione (brainstorm o implement)."""
    data = load(MODE_FILE, {"mode": "brainstorm"})
    return f"Modalità corrente: {data['mode']}"


# ── Contesto condiviso ───────────────────────────────────────────────────────

@server.tool()
def write_context(key: str, value: str) -> str:
    """Salva una voce nel contesto condiviso (leggibile da brain e arm).
    Usalo per: architettura, decisioni, vincoli, glossario, idee emerse.
    """
    with update_json(CONTEXT_FILE, {}) as ctx:
        ctx[key] = {"value": value, "updated_at": now()}
    return f"Contesto '{key}' salvato."


@server.tool()
def read_context(key: Optional[str] = None) -> str:
    """Legge il contesto condiviso. Ometti 'key' per leggere tutto."""
    ctx = load(CONTEXT_FILE, {})
    if key:
        val = ctx.get(key)
        if val is None:
            return f"Chiave '{key}' non trovata."
        return json.dumps(val["value"], ensure_ascii=False, indent=2)
    out = {k: v["value"] for k, v in ctx.items()}
    if not out:
        return "Contesto vuoto."
    return json.dumps(out, ensure_ascii=False, indent=2)


@server.tool()
def clear_context(key: Optional[str] = None) -> str:
    """Rimuove una chiave dal contesto, o svuota tutto se 'key' è omessa."""
    if key:
        with update_json(CONTEXT_FILE, {}) as ctx:
            ctx.pop(key, None)
        return f"Chiave '{key}' rimossa."
    with locked():
        write_json(CONTEXT_FILE, {})
    return "Contesto svuotato."


# ── Task queue ───────────────────────────────────────────────────────────────

@server.tool()
def create_task(
    title: str,
    description: str,
    files: Optional[str] = None,
    priority: Literal["low", "normal", "high"] = "normal",
    project: str = "default",
    channel: str = "default",
) -> str:
    """[SOLO modalità implement] Brain invia un task a Claude Code.
    Includi nella description: cosa fare, logica da applicare, file da modificare.
    'files': path separati da virgola (opzionale).
    'project': nome del progetto (raggruppa più chat). Es: "webshop", "data-platform".
    'channel': identifica la singola chat/sessione brain dentro il progetto.
               Ogni arm loop va configurato con project+channel della sua brain chat.
    """
    mode = load(MODE_FILE, {"mode": "brainstorm"})["mode"]
    if mode != "implement":
        return "I task sono disabilitati in modalità 'brainstorm'. Chiama set_mode('implement') prima."
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
    return f"Task creato: {task_id} [project={project} channel={channel}]\n→ {title}"


@server.tool()
def get_tasks(
    status: Literal["pending", "in_progress", "done", "failed", "all"] = "pending",
    project: Optional[str] = None,
    channel: Optional[str] = None,
) -> str:
    """[ARM] Recupera i task filtrati per status, project e/o channel.
    • project only  → tutti i task del progetto (utile per un arm che copre tutto il progetto)
    • project+channel → solo i task di quella specifica chat brain (un arm per chat)
    • nessun filtro  → tutti i task (sconsigliato con più progetti paralleli)
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
        return f"Nessun task con status='{status}'{label}."
    return json.dumps(tasks, ensure_ascii=False, indent=2)


@server.tool()
def list_channels(project: Optional[str] = None) -> str:
    """Elenca i canali (chat brain) attivi, raggruppati per progetto.
    Passa 'project' per filtrare su un solo progetto.
    Mostra per ogni canale: quanti task pending, in_progress, done.
    Utile per sapere su quale channel avviare un loop arm.
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
        return "Nessun canale trovato." + (f" (project='{project}')" if project else "")
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
    """[ARM] Aggiorna lo stato di un task dopo l'esecuzione."""
    with update_json(TASKS_FILE, []) as tasks:
        task = next((t for t in tasks if t["id"] == task_id), None)
        if task is not None:
            task["status"]     = status
            task["result"]     = result
            task["updated_at"] = now()
    if task is None:
        return f"Task '{task_id}' non trovato."
    return f"Task {task_id} → {status}"


# ── Log condiviso ────────────────────────────────────────────────────────────

@server.tool()
def log(message: str, source: Literal["brain", "arm", "user"] = "brain") -> str:
    """Aggiunge un messaggio al log condiviso."""
    with update_json(LOG_FILE, []) as logs:
        logs.append({"message": message, "source": source, "timestamp": now()})
    return "Log aggiunto."


@server.tool()
def get_log(last_n: int = 30) -> str:
    """Legge gli ultimi N messaggi del log condiviso."""
    recent = load(LOG_FILE, [])[-last_n:]
    if not recent:
        return "Log vuoto."
    return "\n".join(f"[{e['timestamp']}] [{e['source'].upper():5}] {e['message']}" for e in recent)


# ── Tools di sincronizzazione brain ─────────────────────────────────────────

DONE_STATES = ("done", "failed", "needs_clarification")


def _get_task_by_id(task_id: str):
    """Rilegge TASKS_FILE a ogni chiamata per vedere le scritture degli altri processi."""
    return next((t for t in load(TASKS_FILE, []) if t["id"] == task_id), None)


@server.tool()
async def wait_for_task(task_id: str) -> str:
    """[BRAIN] Attende l'esito di un task ARM. Ritorna 'wait' se non è ancora
    pronto: in quel caso richiamami subito, senza scrivere nulla all'utente.
    Altrimenti ritorna '<status> <task_id>'."""
    try:
        deadline = _time.time() + 50
        while _time.time() < deadline:
            try:
                t = _get_task_by_id(task_id)
            except Exception:
                await asyncio.sleep(3)
                continue
            if t is None:
                return f"unknown {task_id}"
            if t["status"] in DONE_STATES:
                return f'{t["status"]} {task_id}'
            await asyncio.sleep(3)
        return "wait"
    except Exception as e:
        return f"error {type(e).__name__}: {e}"


@server.tool()
def get_result(task_id: str) -> str:
    """[BRAIN] Output completo di un task concluso."""
    try:
        t = _get_task_by_id(task_id)
        if t is None:
            return f"unknown {task_id}"
        return t.get("result") or "(nessun result)"
    except Exception as e:
        return f"error {type(e).__name__}: {e}"


@server.tool()
def check_updates(
    ack: bool = True,
    project: Optional[str] = None,
    channel: Optional[str] = None,
) -> str:
    """[BRAIN] Task conclusi da ARM e non ancora visti dal brain. '0' se nulla di nuovo.
    ack=False per lettura non distruttiva.
    Filtra per 'project' e/o 'channel' per vedere solo i propri aggiornamenti.
    Il cursore è per-canale: due brain chat non si sovrascrivono mai.
    """
    try:
        cursor_key = "brain_cursor"
        if project:
            cursor_key += f"_{project}"
        if channel:
            cursor_key += f"_{channel}"
        cursor_entry = load(CONTEXT_FILE, {}).get(cursor_key)
        cursor = cursor_entry["value"] if cursor_entry else ""
        nuovi = [
            t for t in load(TASKS_FILE, [])
            if t["status"] in DONE_STATES
            and (t.get("updated_at") or "") > cursor
            and (project is None or t.get("project", "default") == project)
            and (channel is None or t.get("channel", "default") == channel)
        ]
        if not nuovi:
            return "0"
        if ack:
            with update_json(CONTEXT_FILE, {}) as ctx:
                ctx[cursor_key] = {"value": max(t["updated_at"] for t in nuovi), "updated_at": now()}
        return "\n".join(f'{t["id"]} {t["status"]} {t["title"][:60]}' for t in nuovi)
    except Exception as e:
        return f"error {type(e).__name__}: {e}"


# ── Avvio ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    server.run(transport="stdio")
