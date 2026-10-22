#!/usr/bin/env python3
"""Misura brain-arm: token consumati dagli arm vs testo che arriva alla brain, ed esito dei task. Sola lettura."""
import collections
import glob
import json
import re
import statistics as st
from pathlib import Path

from config import DATA_DIR as DATA

HOME = Path.home()


def first_text(content):
    if isinstance(content, list):
        content = " ".join(b.get("text", "") for b in content if isinstance(b, dict))
    return content if isinstance(content, str) else ""


# ---------- arm: sessioni Claude Code il cui primo messaggio è il prompt ARM ----------
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
    if not first_user or "ARM del progetto" not in first_user[:400] or not usage:
        continue
    per_turn = [u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                + u.get("cache_read_input_tokens", 0) for u in usage.values()]
    cache_read = sum(u.get("cache_read_input_tokens", 0) for u in usage.values())
    m = re.search(r'progetto "([^"]+)", chat "([^"]+)"', first_user)
    sessions.append({
        "chan": f"{m.group(1)}:{m.group(2)}" if m else "?",
        "turns": len(per_turn), "processed": sum(per_turn), "peak": max(per_turn),
        "cache_read": cache_read, "out": sum(u.get("output_tokens", 0) for u in usage.values()),
        "models": models, "start": min(ts) if ts else "",
        "mode": "interattivo" if "ricomincia da get" in first_user else "claude -p",
    })

print(f"=== ARM: {len(sessions)} sessioni trovate ===")
if sessions:
    since = min(s["start"] for s in sessions)[:10]
    tot_proc = sum(s["processed"] for s in sessions)
    print("periodo dal", since, "| modalità:", dict(collections.Counter(s["mode"] for s in sessions)))
    print("modelli:", dict(sum((s["models"] for s in sessions), collections.Counter())))
    print(f"token processati in input (tutti i turni): {tot_proc:,}  di cui da cache: {sum(s['cache_read'] for s in sessions)/max(tot_proc,1):.0%}")
    print(f"token generati in output: {sum(s['out'] for s in sessions):,}")
    print(f"contesto massimo per sessione: mediana {st.median(s['peak'] for s in sessions):,.0f}  max {max(s['peak'] for s in sessions):,}")
    print(f"turni per sessione: mediana {st.median(s['turns'] for s in sessions):.0f}")
else:
    since = "0000"

# ---------- brain: cosa vede (specifica + risultato), stimato a 4 caratteri per token ----------
tasks = json.loads((DATA / "tasks.json").read_text())
arch = DATA / "tasks_archive_default.json"
tasks += json.loads(arch.read_text()) if arch.exists() else []
tok = lambda s: len(s or "") / 4
period = [t for t in tasks if (t.get("created_at") or "") >= since]
spec = [tok(t.get("description")) for t in period]
res = [tok(t.get("result")) for t in period if t.get("result")]
print(f"\n=== BRAIN: {len(period)} task nello stesso periodo (stima 4 caratteri = 1 token) ===")
if spec:
    print(f"specifica scritta dalla brain: mediana {st.median(spec):,.0f} token, totale {sum(spec):,.0f}")
if res:
    print(f"risultato letto dalla brain:   mediana {st.median(res):,.0f} token, totale {sum(res):,.0f}")
if sessions and spec:
    brain_tot = sum(spec) + sum(res)
    print(f"\n>>> testo che passa per la brain: {brain_tot:,.0f} token  vs  token processati dagli arm: {tot_proc:,}")
    print(f">>> rapporto: gli arm hanno processato ~{tot_proc / max(brain_tot,1):,.0f} volte quello che è arrivato alla brain")

# ---------- confronto pulito: solo sessioni di lavoro reale ----------
real = [s for s in sessions if s["turns"] >= 3 and s["models"].get("<synthetic>", 0) == 0]
inter = [s for s in real if s["mode"] == "interattivo"]
print(f"\n=== CONFRONTO PULITO: {len(real)} sessioni arm di lavoro reale (>=3 turni, nessun errore API), "
      f"{len(inter)} interattive ===")
if real and spec:
    peaks = [s["peak"] for s in real]
    brain_med = st.median(spec) + (st.median(res) if res else 0)
    print(f"contesto massimo di una sessione arm: mediana {st.median(peaks):,.0f} token, p90 "
          f"{sorted(peaks)[int(len(peaks)*0.9)-1]:,}")
    print(f"testo per task che passa dalla brain (spec+risultato): mediana {brain_med:,.0f} token")
    print(f">>> per un task tipico l'arm ha in contesto ~{st.median(peaks)/brain_med:,.0f}x quello che arriva alla brain")
    print(f"token in input da cache (più economici) nelle sessioni reali: "
          f"{sum(s['cache_read'] for s in real)/max(sum(s['processed'] for s in real),1):.0%}")

# ---------- esiti ----------
print(f"\n=== ESITI: {len(tasks)} task totali ===")
print(dict(collections.Counter(t["status"] for t in tasks)))
groups = {
    "setup/infrastruttura (MCP, crash, task annullati, routing)": r"MCP|crashat|annullat|manca project|pre-migrazione|arm uscito|bloccato all",
    "permessi / sicurezza": r"PERMESSO NEGATO|classificat|permess|autorizzazion|Denied",
    "timeout": r"timeout",
}
fails = [t for t in tasks if t["status"] == "failed"]
counted = collections.Counter()
other = []
for t in fails:
    r = t.get("result") or ""
    for name, rx in groups.items():
        if re.search(rx, r, re.I):
            counted[name] += 1
            break
    else:
        other.append(t)
for name in groups:
    print(f"  failed per {name}: {counted[name]}")
print(f"  failed per il contenuto del task: {len(other)}")
for t in other[:5]:
    print("     -", t["id"], "|", (t.get("result") or "")[:110].replace("\n", " "))
