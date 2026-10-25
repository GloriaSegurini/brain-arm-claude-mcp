"""End-to-end check of the brain side: talks to server.py over stdio (like Claude Desktop),
creates a trivial task, waits with wait_for_task until an arm (launched by the real watcher)
closes it, then reads the result. Requires the watcher running and the project/channel mapped.

Usage: .venv/bin/python tests/e2e_brain_wait.py PROJECT CHANNEL
"""
import asyncio
import json
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent


def text(res) -> str:
    return "".join(getattr(c, "text", "") for c in res.content)


async def main(project: str, channel: str):
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")])
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        print("mode:", text(await s.call_tool("get_mode", {})))

        rej = text(await s.call_tool("create_task", {
            "title": "x", "description": "x", "project": "default", "channel": channel}))
        print("project=default ->", "RIFIUTATO" if rej.startswith("Task NON creato") else f"ACCETTATO (errore!) {rej}")

        slow = "--slow" in sys.argv
        work = ("Prima esegui: python3 -c \"import time; time.sleep(75)\" (simula un lavoro lungo). "
                if slow else "")
        created = text(await s.call_tool("create_task", {
            "title": "selftest: rispondi ok" + (" (lento)" if slow else ""),
            "description": "Test automatico di brain-arm. Non leggere né modificare file. " + work +
                           "Poi chiudi il task con: arm_helper.py done TASK_ID \"ok\"",
            "project": project, "channel": channel}))
        print(created)
        task_id = created.split("Task creato: ")[1].split()[0]

        t0 = time.time()
        calls = 0
        while True:
            calls += 1
            out = text(await s.call_tool("wait_for_task", {"task_id": task_id}))
            print(f"[{time.time()-t0:5.0f}s] wait_for_task #{calls}: {out[:150]}")
            if not out.startswith("wait"):
                break
            if time.time() - t0 > 900:
                print("TIMEOUT del test (15 min)")
                return 1
        print("get_result:", text(await s.call_tool("get_result", {"task_id": task_id}))[:200])
        print(f"totale {time.time()-t0:.0f}s, {calls} chiamate a wait_for_task")
        return 0 if out.startswith("done") else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1], sys.argv[2])))
