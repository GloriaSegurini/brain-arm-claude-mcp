#!/usr/bin/env python3
"""Token and outcome report for brain-arm. Read-only.

Arm side: exact token counts from Claude Code's local transcripts (~/.claude/projects/*/*.jsonl).
Brain side: Claude Desktop does not expose token counts, so the brain is measured indirectly:
text it exchanges with the arms, and wait_for_task calls (exact if data/metrics.jsonl exists,
otherwise estimated from task durations).

Token categories (Anthropic API usage fields): uncached input, cache write, cache read, output.
"input-equivalent" weights them with the usual price ratios relative to normal input
(cache write 1.25x, cache read 0.1x, output 5x) — check current pricing for your model.
"""
import collections
import glob
import json
import math
import re
import statistics as st
from datetime import datetime, timedelta
from pathlib import Path

from config import CONFIG, DATA_DIR

HOME = Path.home()
ARM_MARKERS = ("You are the ARM for project", "ARM del progetto")  # current and legacy prompt
CHANNEL_RX = re.compile(r'(?:project|progetto) "([^"]+)", chat "([^"]+)"')
NOTIFY_RX = re.compile(r"^(new tasks|nuovi task)", re.I)
NUDGE_RX = re.compile(r"^(Reminder from the watcher|Promemoria del watcher)", re.I)
W = {"input": 1.0, "cache_write": 1.25, "cache_read": 0.1, "output": 5.0}
DONE = ("done", "failed", "needs_clarification")


def text_of(content):
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return content if isinstance(content, str) else ""


def ts(s):  # transcript timestamps are UTC ("...Z"); tasks use local time
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)


def eq(u):
    return (u["input"] * W["input"] + u["cache_write"] * W["cache_write"]
            + u["cache_read"] * W["cache_read"] + u["output"] * W["output"])


def pct(values, p):
    v = sorted(values)
    return v[min(len(v) - 1, max(0, math.ceil(p / 100 * len(v)) - 1))] if v else 0


def fmt(n):
    return f"{n:,.0f}"


# ---------------------------------------------------------------- read arm transcripts
sessions = []
for f in glob.glob(str(HOME / ".claude/projects/*/*.jsonl")):
    entries = []
    with open(f, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            try:
                entries.append(json.loads(line))
            except ValueError:
                pass
    first_user = next((text_of(e.get("message", {}).get("content")) for e in entries
                       if e.get("type") == "user" and text_of(e.get("message", {}).get("content")).strip()), "")
    if not any(k in first_user[:400] for k in ARM_MARKERS):
        continue
    calls, seen, last_input_ts, boundaries, nudges = [], set(), None, [], 0
    for e in entries:
        t = e.get("timestamp")
        if e.get("type") == "user" and t:
            last_input_ts = ts(t)
            txt = text_of(e.get("message", {}).get("content")).strip()
            if NOTIFY_RX.match(txt):
                boundaries.append(ts(t))
            if NUDGE_RX.match(txt):
                nudges += 1
        m = e.get("message", {})
        if e.get("type") == "assistant" and m.get("usage") and m.get("id") not in seen and t:
            seen.add(m["id"])
            u = m["usage"]
            calls.append({
                "t": ts(t), "after_input": (ts(t) - last_input_ts).total_seconds() if last_input_ts else None,
                "model": m.get("model", "?"),
                "input": u.get("input_tokens", 0), "cache_write": u.get("cache_creation_input_tokens", 0),
                "cache_read": u.get("cache_read_input_tokens", 0), "output": u.get("output_tokens", 0),
            })
    if not calls:
        continue
    m = CHANNEL_RX.search(first_user)
    sessions.append({
        "key": (m.group(1), m.group(2)) if m else ("?", "?"),
        "interactive": "start again from get" in first_user or "ricomincia da get" in first_user,
        "calls": calls, "boundaries": boundaries, "nudges": nudges,
        "start": calls[0]["t"], "end": calls[-1]["t"],
    })

real = [s for s in sessions if s["interactive"] and len(s["calls"]) >= 3
        and not any(c["model"] == "<synthetic>" for c in s["calls"])]
since = min((s["start"] for s in real), default=datetime.max)

tasks = json.loads((DATA_DIR / "tasks.json").read_text())
arch = DATA_DIR / "tasks_archive_default.json"
tasks += json.loads(arch.read_text()) if arch.exists() else []

print("brain-arm token report")
print("=" * 72)
print(f"Interactive arm sessions with real work: {len(real)}"
      + (f"  (since {since:%Y-%m-%d})" if real else ""))
if not real:
    raise SystemExit("No interactive arm sessions found yet.")

# ---------------------------------------------------------------- 1. idle = zero calls?
gaps_between_calls = []
unprompted = []
for s in real:
    for a, b in zip(s["calls"], s["calls"][1:]):
        gaps_between_calls.append((b["t"] - a["t"]).total_seconds())
    unprompted += [c for c in s["calls"] if c["after_input"] is not None and c["after_input"] > 300]
idle_hours = sum(g for g in gaps_between_calls if g > 300) / 3600
print("\n1. IDLE COST")
print(f"   model calls made more than 5 min after the last input (task, notice, tool result): {len(unprompted)}")
print(f"   idle time observed between calls (gaps > 5 min): {idle_hours:.1f} h; longest gap: "
      f"{max(gaps_between_calls, default=0) / 60:.0f} min")
print("   → an idle arm makes no model calls: it only works when something is sent to it.")

# ---------------------------------------------------------------- 2. arm tokens
cat = collections.Counter()
for s in real:
    for c in s["calls"]:
        for k in W:
            cat[k] += c[k]
total_in = cat["input"] + cat["cache_write"] + cat["cache_read"]
print("\n2. ARM TOKENS (all real sessions)")
for k, label in (("input", "uncached input"), ("cache_write", "cache write"),
                 ("cache_read", "cache read"), ("output", "output")):
    share = f"{cat[k] / total_in:5.1%} of input" if k != "output" else ""
    print(f"   {label:15} {fmt(cat[k]):>14}   {share}")
print(f"   input-equivalent total: {fmt(eq(cat))}")

startup = [s["calls"][0]["input"] + s["calls"][0]["cache_write"] + s["calls"][0]["cache_read"] for s in real]
peaks = [max(c["input"] + c["cache_write"] + c["cache_read"] for c in s["calls"]) for s in real]
print(f"   startup context of an arm (system prompt, tools, project files, arm prompt): "
      f"median {fmt(st.median(startup))} tokens")
print(f"   peak context per session: median {fmt(st.median(peaks))}, p90 {fmt(pct(peaks, 90))}, "
      f"max {fmt(max(peaks))}")

# ---------------------------------------------------------------- 3. per task
per_task, carry = [], []
for s in real:
    closed = [t for t in tasks if (t.get("project"), t.get("channel")) == s["key"] and t["status"] in DONE
              and t.get("updated_at") and s["start"] <= datetime.fromisoformat(t["updated_at"])
              <= s["end"] + timedelta(minutes=5)]
    if closed:
        per_task.append(eq({k: sum(c[k] for c in s["calls"]) for k in W}) / len(closed))
    for b in s["boundaries"]:
        nxt = next((c for c in s["calls"] if c["t"] >= b), None)
        if nxt:
            carry.append(nxt["input"] + nxt["cache_write"] + nxt["cache_read"])
print("\n3. PER TASK (arm)")
if per_task:
    print(f"   input-equivalent tokens per task: median {fmt(st.median(per_task))}, "
          f"p90 {fmt(pct(per_task, 90))}  ({len(per_task)} sessions with closed tasks)")
if carry:
    print(f"   context already loaded when a later task starts in the same arm: median {fmt(st.median(carry))}, "
          f"p90 {fmt(pct(carry, 90))}  ({len(carry)} follow-up tasks)")
print(f"   watcher reminders to arms that forgot to close a task: {sum(s['nudges'] for s in real)}")

# ---------------------------------------------------------------- 4. brain
period = [t for t in tasks if t.get("created_at") and datetime.fromisoformat(t["created_at"]) >= since]
spec = [len(t.get("description") or "") / 4 for t in period]
res = [len(t.get("result") or "") / 4 for t in period if t.get("result")]
win = CONFIG["wait_window_sec"]
durations = [(datetime.fromisoformat(t["updated_at"]) - datetime.fromisoformat(t["created_at"])).total_seconds()
             for t in period if t["status"] in DONE and t.get("updated_at")]
durations = [d for d in durations if d >= 0]
est_steps = [max(1, math.ceil(d / win)) for d in durations]
print("\n4. BRAIN (Claude Desktop does not expose tokens; measured indirectly)")
print(f"   tasks in the period: {len(period)}")
print(f"   task spec written by the brain: median {fmt(st.median(spec))} tokens, p90 {fmt(pct(spec, 90))} (≈4 chars/token)")
if res:
    print(f"   result read back:               median {fmt(st.median(res))} tokens, p90 {fmt(pct(res, 90))}, "
          f"max {fmt(max(res))}")
if durations:
    print(f"   task duration (created → closed): median {st.median(durations) / 60:.1f} min, "
          f"p90 {pct(durations, 90) / 60:.1f} min")
    print(f"   wait_for_task calls per task (estimated from durations, window {win} s): "
          f"median {st.median(est_steps):.0f}, p90 {pct(est_steps, 90)}")
metrics = DATA_DIR / "metrics.jsonl"
if metrics.exists():
    by_task = collections.Counter(json.loads(l)["task"] for l in metrics.read_text().splitlines() if l.strip())
    if by_task:
        print(f"   wait_for_task calls per task (measured, {len(by_task)} tasks): "
              f"median {st.median(by_task.values()):.0f}, p90 {pct(list(by_task.values()), 90)}")

# ---------------------------------------------------------------- 5. outcomes
print(f"\n5. OUTCOMES: {len(tasks)} tasks in total")
print("  ", dict(collections.Counter(t["status"] for t in tasks)))
groups = {
    "setup/infrastructure (MCP, crashes, cancelled, routing)":
        r"MCP|crash|annullat|cancelled|manca project|missing project|pre-migrazione|arm uscito|arm exited|stuck|bloccato all|no folder",
    "permissions / safety blocks":
        r"PERMESSO NEGATO|PERMISSION DENIED|classifi|permess|permission|autorizzazion|authoriz|Denied",
    "timeouts": r"timeout|runtime limit",
}
counted, other = collections.Counter(), 0
for t in (t for t in tasks if t["status"] == "failed"):
    name = next((n for n, rx in groups.items() if re.search(rx, t.get("result") or "", re.I)), None)
    if name:
        counted[name] += 1
    else:
        other += 1
for name in groups:
    print(f"   failed — {name}: {counted[name]}")
print(f"   failed — task content: {other}")
