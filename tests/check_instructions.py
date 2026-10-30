#!/usr/bin/env python3
"""Starts server.py over stdio like Claude Desktop does and prints what the client receives at handshake:
the server instructions and the tool list. Read-only. Run: .venv/bin/python tests/check_instructions.py
"""
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BASE = Path(__file__).resolve().parent.parent


async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(BASE / "server.py")])
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        init = await s.initialize()
        text = init.instructions or ""
        print(f"instructions sent at handshake: {len(text)} chars")
        print("  " + (text.splitlines()[0] if text else "(none)"))
        tools = sorted(t.name for t in (await s.list_tools()).tools)
        print(f"tools ({len(tools)}): {', '.join(tools)}")
        ok = "trust_folder" in text and {"setup_check", "add_project", "trust_folder"} <= set(tools)
        print("OK" if ok else "MISSING something")
        return 0 if ok else 1


sys.exit(asyncio.run(main()))
