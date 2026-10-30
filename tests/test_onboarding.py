#!/usr/bin/env python3
"""Checks add_project / trust_folder / setup_check against temporary files (your real config is not touched).
Run: .venv/bin/python tests/test_onboarding.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import onboarding  # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix="brain-arm-onboarding-"))
os.environ["CLAUDE_CONFIG_DIR"] = str(tmp)
onboarding.PROJECTS_FILE = tmp / "projects.json"
(tmp / ".claude.json").write_text(json.dumps({"projects": {"/elsewhere": {"hasTrustDialogAccepted": True}}}))
code = tmp / "code" / "webshop"
code.mkdir(parents=True)
failures = 0


def check(label, cond, detail=""):
    global failures
    failures += not cond
    print(f"[{'ok' if cond else 'FAIL'}] {label}" + (f"\n       {detail}" if not cond else ""))


r = onboarding.add_project("Bad Name", str(code))
check("invalid name refused", r.startswith("NOT added"), r)
r = onboarding.add_project("default", str(code))
check("'default' refused", r.startswith("NOT added"), r)
r = onboarding.add_project("webshop", str(tmp / "missing"))
check("missing folder refused", r.startswith("NOT added"), r)
r = onboarding.add_project("webshop", str(code))
check("project added", r.startswith("[ok]") and "NOT trusted" in r, r)
check("map written", json.loads(onboarding.PROJECTS_FILE.read_text()) == {"webshop": str(code)})

r = onboarding.trust_folder(str(code), user_confirmed=False)
check("trust refused without consent", r.startswith("NOT trusted"), r)
r = onboarding.trust_folder(str(tmp), user_confirmed=True)
check("trust refused for an unmapped folder", r.startswith("NOT trusted"), r)
r = onboarding.trust_folder(str(code), user_confirmed=True)
check("trust granted with consent", r.startswith("[ok]"), r)
cfg = json.loads((tmp / ".claude.json").read_text())
check("trust flag written, other entries kept",
      cfg["projects"][str(code)]["hasTrustDialogAccepted"] and "/elsewhere" in cfg["projects"])
check("backup made", (tmp / ".claude.json.bak-brain-arm").exists())
check("is_trusted sees subfolders", onboarding.is_trusted(code / "src"))

r = onboarding.setup_check()
check("setup_check lists the project as trusted", "project webshop" in r and "(trusted)" in r, r)

if onboarding.is_wsl():
    p = onboarding.normalize_folder(r"C:\code\webshop")
    check("Windows path converted", str(p) == "/mnt/c/code/webshop", p)
    p = onboarding.normalize_folder(r"\\wsl$\Ubuntu-24.04" + str(code).replace("/", "\\"))
    check("\\\\wsl$ path converted", p == code, p)

print("\nALL OK" if not failures else f"\n{failures} FAILED")
sys.exit(1 if failures else 0)
