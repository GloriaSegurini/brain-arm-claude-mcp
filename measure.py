#!/usr/bin/env python3
"""Measure brain-arm: tokens processed by the arms vs. text that reaches the brain, and task outcomes. Read-only."""
import collections
import glob
import json
import re
import statistics as st
from pathlib import Path

from config import DATA_DIR as DATA

HOME = Path.home()
ARM_MARKERS = ("You are the ARM for project", "ARM del progetto")  # current and legacy prompt
CHANNEL_RX = re.compile(r'(?:project|progetto) "([^"]+)", chat "([^"]+)"')


def first_text(content):
    if isinstance(content, list):
        content = " ".join(b.get("text", "") for b in content if isinstance(b, dict))
    return content if isinstance(content, str) else ""


# ---------- arms: Claude Code sessions whose first message is the ARM prompt ----------
sessions = []
for f in glob.glob(str(HOME / ".claude/projects/*/*.jsonl")):
    first_user, usage, models, ts = None, {}, collections.Counter(), []
    with open(f, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if o.get("type") == "user" and first_user is None:
                txt = first_text(o.get("message", {}).get("content"))
                if txt.strip():
                    first_user = txt
            elif o.get("type") == "assistant":
                m = o.get("message", {})
                if m.get("usage") and m.get("id"):
                    usage[m["id"]] = m["usage"]
                    models[m.get("model", "?")] += 1
                if o.get("timestamp"):
                    ts.append(o["timestamp"])
    if not first_user or not any(k in first_user[:400] for k in ARM_MARKERS) or not usage:
        continue
    per_turn = [u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                + u.get("cache_read_input_tokens", 0) for u in usage.values()]
    m = CHANNEL_RX.search(first_user)
    interactive = "start again from get" in first_user or "ricomincia da get" in first_user
    sessions.append({
        "chan": f"{m.group(1)}:{m.group(2)}" if m else "?",
        "turns": len(per_turn), "processed": sum(per_turn), "peak": max(per_turn),
        "cache_read": sum(u.get("cache_read_input_tokens", 0) for u in usage.values()),
        "out": sum(u.get("output_tokens", 0) for u in usage.values()),
        "models": models, "start": min(ts) if ts else "",
        "mode": "interactive" if interactive else "claude -p",
    })

print(f"=== ARMS: {len(sessions)} sessions found (raw, includes failed starts) ===")
since = "0000"
if sessions:
    since = min(s["start"] for s in sessions)[:10]
    tot_proc = sum(s["processed"] for s in sessions)
    print("since", since, "| modes:", dict(collections.Counter(s["mode"] for s in sessions)))
    print("models:", dict(sum((s["models"] for s in sessions), collections.Counter())))
    print(f"input tokens processed (all turns): {tot_proc:,}  of which from cache: "
          f"{sum(s['cache_read'] for s in sessions) / max(tot_proc, 1):.0%}")
    print(f"output tokens: {sum(s['out'] for s in sessions):,}")

# ---------- brain: what it sees (spec + result), estimated at 4 characters per token ----------
tasks = json.loads((DATA / "tasks.json").read_text())
arch = DATA / "tasks_archive_default.json"
tasks += json.loads(arch.read_text()) if arch.exists() else []
tok = lambda s: len(s or "") / 4
period = [t for t in tasks if (t.get("created_at") or "") >= since]
spec = [tok(t.get("description")) for t in period]
res = [tok(t.get("result")) for t in period if t.get("result")]
print(f"\n=== BRAIN: {len(period)} tasks in the same period (estimate: 4 characters = 1 token) ===")
if spec:
    print(f"spec written by the brain: median {st.median(spec):,.0f} tokens, total {sum(spec):,.0f}")
if res:
    print(f"result read by the brain:  median {st.median(res):,.0f} tokens, total {sum(res):,.0f}")

# ---------- clean comparison: real work sessions only ----------
real = [s for s in sessions if s["turns"] >= 3 and s["models"].get("<synthetic>", 0) == 0]
print(f"\n=== CLEAN COMPARISON: {len(real)} real arm work sessions (>=3 turns, no API errors), "
      f"{sum(s['mode'] == 'interactive' for s in real)} interactive ===")
if real and spec:
    peaks = sorted(s["peak"] for s in real)
    brain_med = st.median(spec) + (st.median(res) if res else 0)
    print(f"peak context of an arm session: median {st.median(peaks):,.0f} tokens, "
          f"p90 {peaks[max(int(len(peaks) * 0.9) - 1, 0)]:,}")
    print(f"text per task through the brain (spec + result): median {brain_med:,.0f} tokens")
    print(f">>> for a typical task the arm holds ~{st.median(peaks) / brain_med:,.0f}x what reaches the brain")
    print(f"share of arm input tokens read from cache (cheaper): "
          f"{sum(s['cache_read'] for s in real) / max(sum(s['processed'] for s in real), 1):.0%}")

# ---------- outcomes ----------
print(f"\n=== OUTCOMES: {len(tasks)} tasks in total ===")
print(dict(collections.Counter(t["status"] for t in tasks)))
groups = {
    "setup/infrastructure (MCP, crashes, cancelled, routing)":
        r"MCP|crash|annullat|cancelled|manca project|missing project|pre-migrazione|arm uscito|arm exited|stuck|bloccato all|no folder",
    "permissions / safety":
        r"PERMESSO NEGATO|PERMISSION DENIED|classifi|permess|permission|autorizzazion|authoriz|Denied",
    "timeout": r"timeout|runtime limit",
}
other = []
counted = collections.Counter()
for t in (t for t in tasks if t["status"] == "failed"):
    r = t.get("result") or ""
    name = next((n for n, rx in groups.items() if re.search(rx, r, re.I)), None)
    if name:
        counted[name] += 1
    else:
        other.append(t)
for name in groups:
    print(f"  failed — {name}: {counted[name]}")
print(f"  failed — task content: {len(other)}")
