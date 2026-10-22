"""20 processes x 50 locked increments on the same JSON file: no update may be lost."""
import json
import multiprocessing as mp
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from store import read_json, update_json  # noqa: E402

PROCS, ITERS = 20, 50


def worker(path):
    for _ in range(ITERS):
        with update_json(path, {"n": 0, "ids": []}) as d:
            d["n"] += 1
            d["ids"].append(1)


def main():
    path = Path(tempfile.mkdtemp()) / "counter.json"
    procs = [mp.Process(target=worker, args=(path,)) for _ in range(PROCS)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    d = read_json(path, {})
    expected = PROCS * ITERS
    ok = d["n"] == expected and len(d["ids"]) == expected
    print(f"atteso {expected}, contatore {d['n']}, elementi {len(d['ids'])} -> {'OK' if ok else 'PERSE MODIFICHE'}")
    leftovers = [p.name for p in path.parent.iterdir() if p.suffix == ".tmp"]
    print("file temporanei rimasti:", leftovers or "nessuno")
    sys.exit(0 if ok and not leftovers else 1)


if __name__ == "__main__":
    main()
