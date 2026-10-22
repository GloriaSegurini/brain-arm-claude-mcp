"""Shared JSON state for brain-arm: one inter-process lock and atomic writes.

Every process that writes data/*.json (MCP server, watcher, arm_helper, stop-arms)
must go through update_json / write_json so concurrent read-modify-write cycles
never overwrite each other and readers never see a half-written file.
"""
import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from config import DATA_DIR

LOCK_FILE = DATA_DIR / ".lock"


@contextmanager
def locked():
    """Exclusive lock across processes. Not re-entrant: never nest it."""
    DATA_DIR.mkdir(exist_ok=True)
    with open(LOCK_FILE, "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def read_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data) -> None:
    """Atomic replace. Call it inside locked() when the write depends on a previous read."""
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


@contextmanager
def update_json(path, default):
    """Locked read-modify-write: mutate the yielded object in place; it is saved on exit.
    If the block raises, nothing is written."""
    with locked():
        data = read_json(path, default)
        yield data
        write_json(path, data)
