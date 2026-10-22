#!/usr/bin/env python3
"""
Aggiunge alle regole dell'auto mode (in ~/.claude/settings.json) un'eccezione generale:
letture e scritture sugli ambienti DEV/TEST con credenziali dal .env del progetto.
Non toglie nessuna regola esistente: parte dalle regole attuali (o dai default) e AGGIUNGE
le due regole brain-arm (se ne esiste già una versione precedente, la sostituisce).
Uso:  python3 ~/brain-arm-mcp/automode_devtest.py          → mostra cosa cambierebbe
      python3 ~/brain-arm-mcp/automode_devtest.py --apply  → applica (con backup)
Ripristino: copia il backup stampato su ~/.claude/settings.json, oppure `claude auto-mode reset`.
"""
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from config import CONFIG

SETTINGS = Path.home() / ".claude" / "settings.json"
ALLOW_PREFIX = "Dev/Test Environment Access:"
ENV_PREFIX = "**Development environments**:"


def project_folders() -> str:
    pf = CONFIG["projects_file"]
    folders = sorted(set(json.loads(pf.read_text()).values())) if pf.exists() else []
    return ", ".join(folders) if folders else "the folders listed in the brain-arm projects map"


ALLOW_RULE = (
    f"{ALLOW_PREFIX} Reading from AND writing to the user's DEV/TEST environments "
    "(business-application APIs, REST APIs, databases, queues used by the brain-arm projects) "
    "is routine development and testing explicitly authorized by the user: HTTP GET/POST/PATCH/PUT, "
    "queries, and creating or updating records or test data. Loading credentials from the project's own "
    ".env file into the process environment for these calls is expected and is not Credential Exploration, "
    "Exfil Scouting or Production Reads. An environment counts as DEV/TEST when its host, URL, namespace or "
    "name contains dev, test, uat, sit, sandbox or staging as a word or segment, or when the project's .env/config "
    "labels it that way. This exception does NOT cover: any target whose name contains prod or production as a "
    "word or segment, or that is not identifiable as DEV/TEST (evaluate those with the normal rules); printing, "
    "copying or sending secret values from .env into output, files, logs or messages; bulk or unscoped deletion, "
    "dropping tables/schemas/environments; changing users, security roles or permissions."
)

ENV_RULE = (
    f"{ENV_PREFIX} the brain-arm projects ({project_folders()}) are developed "
    "and tested against DEV/TEST environments whose credentials live in each project's .env file. Read and write "
    "access to those DEV/TEST environments is authorized by the user (see 'Dev/Test Environment Access'). "
    "Production remains protected: targets named prod/production, or not identifiable as DEV/TEST, follow the "
    "normal rules."
)


def claude_json(*args):
    out = subprocess.run(["claude", "auto-mode", *args], capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise SystemExit(f"errore da 'claude auto-mode {' '.join(args)}': {out.stderr.strip()}")
    return json.loads(out.stdout)


def main():
    apply = "--apply" in sys.argv
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    current = settings.get("autoMode") or {}
    defaults = claude_json("defaults")

    new_auto = dict(current)
    for section, rule, prefix in (("allow", ALLOW_RULE, ALLOW_PREFIX), ("environment", ENV_RULE, ENV_PREFIX)):
        base = list(current.get(section) or defaults.get(section) or [])
        base = [r for r in base if not r.startswith(prefix)]
        base.append(rule)
        new_auto[section] = base

    print("Regole che verranno AGGIUNTE o AGGIORNATE (le altre restano invariate):")
    print("  allow       +1  →", ALLOW_RULE[:110], "…")
    print("  environment +1  →", ENV_RULE[:110], "…")
    print(f"  allow: {len(new_auto['allow'])} regole totali, environment: {len(new_auto['environment'])} voci totali")

    if not apply:
        print("\nNessuna modifica fatta. Per applicare: python3 ~/brain-arm-mcp/automode_devtest.py --apply")
        return

    backup = SETTINGS.with_name(f"settings.json.bak-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(SETTINGS, backup)
    settings["autoMode"] = new_auto
    SETTINGS.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nApplicato. Backup: {backup}")

    effective = claude_json("config")
    ok_allow = ALLOW_RULE in effective.get("allow", [])
    ok_env = ENV_RULE in effective.get("environment", [])
    lost = [s for s in ("allow", "environment") if len(effective.get(s, [])) < len(defaults.get(s, []))]
    print(f"Verifica 'claude auto-mode config': allow={'OK' if ok_allow else 'MANCANTE'}, "
          f"environment={'OK' if ok_env else 'MANCANTE'}, regole di default perse: {lost or 'nessuna'}")
    print("\nPer un parere sulle regole nuove:  claude auto-mode critique")


if __name__ == "__main__":
    main()
