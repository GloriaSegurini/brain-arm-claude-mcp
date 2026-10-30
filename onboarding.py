"""Setup helpers behind the setup_check / add_project / trust_folder tools.

Lets the brain finish the installation from the chat: map a project folder, trust it in Claude Code
(only with the user's explicit consent) and check that every piece is in place.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from config import BASE_DIR, CONFIG

PROJECTS_FILE = CONFIG["projects_file"]
KEY_RX = re.compile(r"^[a-z0-9][a-z0-9._-]*(:[a-z0-9][a-z0-9._-]*)?$")
CLAUDE_EXTRA_PATHS = ("~/.local/bin/claude", "/usr/local/bin/claude", "/opt/homebrew/bin/claude")


def is_wsl() -> bool:
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except OSError:
        return False


def normalize_folder(folder: str) -> Path:
    """Accept Linux/Mac paths, ~, and (inside WSL) Windows paths such as C:\\code\\app or \\\\wsl$\\Ubuntu\\home\\me."""
    f = folder.strip().strip('"').strip("'")
    if is_wsl():
        m = re.match(r"^\\\\wsl(?:\$|\.localhost)\\[^\\]+(\\.*)?$", f, re.I)
        if m:
            f = (m.group(1) or "\\").replace("\\", "/")
        m = re.match(r"^([A-Za-z]):[\\/]?(.*)$", f)
        if m:
            f = f"/mnt/{m.group(1).lower()}/" + m.group(2).replace("\\", "/")
    return Path(f).expanduser().resolve()


def load_projects() -> dict:
    return json.loads(PROJECTS_FILE.read_text()) if PROJECTS_FILE.exists() else {}


def _write_atomic(path: Path, data: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "w") as fh:
        json.dump(data, fh, indent=2)
    if path.exists():
        os.chmod(tmp, path.stat().st_mode & 0o777)
    os.replace(tmp, path)


def claude_config_file() -> Path:
    base = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(base).expanduser() / ".claude.json" if base else Path.home() / ".claude.json"


def is_trusted(folder: Path) -> bool:
    """Claude Code stores trust per folder; a trusted parent folder also covers its subfolders."""
    try:
        projects = json.loads(claude_config_file().read_text()).get("projects", {})
    except (OSError, ValueError):
        return False
    for p in (folder, *folder.parents):
        if projects.get(str(p), {}).get("hasTrustDialogAccepted"):
            return True
    return False


def find_claude() -> str | None:
    found = shutil.which("claude")
    if found:
        return found
    for p in CLAUDE_EXTRA_PATHS:
        if Path(p).expanduser().exists():
            return str(Path(p).expanduser())
    return None


def watcher_running() -> bool:
    r = subprocess.run(["pgrep", "-f", str(BASE_DIR / "watcher.py")], capture_output=True, text=True)
    return r.returncode == 0


def add_project(name: str, folder: str) -> str:
    key = name.strip().lower()
    if not KEY_RX.match(key):
        return ("NOT added: use a lowercase name with letters, digits, '-', '.', '_' "
                "(e.g. webshop, or webshop:checkout for a single channel).")
    if key.startswith("default"):
        return "NOT added: 'default' is reserved."
    path = normalize_folder(folder)
    if not path.is_dir():
        return f"NOT added: folder '{path}' does not exist (from '{folder}'). Ask the user to check the path."
    if path == Path.home() or path == Path("/"):
        return f"NOT added: '{path}' is the whole home/root folder. Ask the user for the project folder itself."
    data = load_projects()
    old = data.get(key)
    data[key] = str(path)
    PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(PROJECTS_FILE, data)
    msg = f"[ok] {key} → {path}" + (f"   (was {old})" if old and old != str(path) else "")
    if is_wsl() and str(path).startswith("/mnt/"):
        msg += "\nNote: this is a Windows folder; arms work there, but slower than in a folder inside Ubuntu."
    if is_trusted(path):
        msg += "\nThe folder is already trusted in Claude Code: the project is ready."
    else:
        msg += ("\nThe folder is NOT trusted in Claude Code yet, so arms would stop on the trust question. "
                "Explain to the user what trusting it allows, ask an explicit yes/no for this exact folder, "
                "and only on yes call trust_folder.")
    return msg


def trust_folder(folder: str, user_confirmed: bool) -> str:
    if not user_confirmed:
        return ("NOT trusted: the user has not explicitly confirmed. Ask the user a direct yes/no question "
                "naming this exact folder; call again with user_confirmed=True only if they say yes.")
    path = normalize_folder(folder)
    mapped = {Path(v) for v in load_projects().values()}
    if path not in mapped:
        return (f"NOT trusted: '{path}' is not a mapped project folder. "
                "Only folders added with add_project can be trusted from the chat.")
    if not path.is_dir():
        return f"NOT trusted: folder '{path}' does not exist."
    if is_trusted(path):
        return f"Already trusted: {path}"
    cfg_file = claude_config_file()
    if not cfg_file.exists():
        return ("NOT trusted: Claude Code's settings file was not found — Claude Code has never been started. "
                "Ask the user to run `claude` once in a terminal and sign in, then try again.")
    cfg = json.loads(cfg_file.read_text())
    backup = cfg_file.with_name(cfg_file.name + ".bak-brain-arm")
    if not backup.exists():
        shutil.copy2(cfg_file, backup)
    cfg.setdefault("projects", {}).setdefault(str(path), {})["hasTrustDialogAccepted"] = True
    _write_atomic(cfg_file, cfg)
    return f"[ok] trusted in Claude Code: {path}. Arms can now work there without the trust question."


def setup_check() -> str:
    ok, todo = [], []
    claude = find_claude()
    (ok if claude else todo).append(
        f"Claude Code: {claude}" if claude else
        "Claude Code not found: the user must install it and sign in (INSTALL.md, step A7 / B5).")
    (ok if shutil.which("tmux") else todo).append(
        "tmux: installed" if shutil.which("tmux") else
        "tmux not found: the user must install it (INSTALL.md, step A6 / B4).")
    running = watcher_running()
    (ok if running else todo).append(
        "watcher: running" if running else
        "watcher not running: the user must run `./install.sh` again in the brain-arm folder (it starts the "
        "watcher), or on Windows check that systemd is on (INSTALL.md, step A5).")
    projects = load_projects()
    if not projects:
        todo.append("no project connected yet: ask the user for a project folder and a short name, "
                    "then call add_project.")
    for key, folder in sorted(projects.items()):
        p = Path(folder)
        if not p.is_dir():
            todo.append(f"project {key}: folder {folder} no longer exists — ask the user for the new path.")
        elif not is_trusted(p):
            todo.append(f"project {key}: folder {folder} is not trusted — ask the user's explicit consent, "
                        "then trust_folder.")
        else:
            ok.append(f"project {key} → {folder} (trusted)")
    lines = ["brain-arm setup check", "OK:"] + [f"  ✓ {x}" for x in ok]
    if todo:
        lines += ["TO DO (one at a time, in this order):"] + [f"  • {x}" for x in todo]
    else:
        lines += ["Everything is ready. Offer a first read-only test task on a project."]
    return "\n".join(lines)
