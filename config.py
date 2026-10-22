"""brain-arm configuration: defaults here, personal overrides in config.local.json (git-ignored).

Example config.local.json:
    {"arm_model": "claude-sonnet-5-5", "max_concurrent": 3, "idle_exit_sec": 1800}
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
LOCAL_CONFIG = BASE_DIR / "config.local.json"

DEFAULTS = {
    "arm_model": "claude-sonnet-5-5",
    "arm_effort": "medium",
    "arm_permission_mode": "auto",
    "tmux_session": "arms",
    "projects_file": "~/.brain-arm-projects.json",
    "poll_seconds": 5,
    "max_concurrent": 5,
    "max_failures": 3,
    "fast_exit_sec": 30,
    "failure_reset_sec": 300,
    "startup_timeout_sec": 600,
    "max_runtime_sec": 3600,
    "idle_exit_sec": 3600,
}


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    if LOCAL_CONFIG.exists():
        overrides = json.loads(LOCAL_CONFIG.read_text(encoding="utf-8"))
        unknown = set(overrides) - set(DEFAULTS)
        if unknown:
            raise ValueError(f"config.local.json: unknown keys {sorted(unknown)}")
        cfg.update(overrides)
    cfg["projects_file"] = Path(cfg["projects_file"]).expanduser()
    return cfg


CONFIG = load_config()
