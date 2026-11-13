"""A size cap for the Landsat 1 tile cache (data/landsat1/cache), with LRU eviction (STATE backlog 1; Moe 2026-11-12: cap + LRU).

    python data/cache_cap.py --cap-gb 10            # evict once, down to the cap
    python data/cache_cap.py --cap-gb 10 --every 60 # keep doing it (the batch scripts run this beside the walkers)
    python data/cache_cap.py --report               # size, files, pinned

- Recency is the file's mtime: the store touches a file whenever it reads it (data/landsat1_store._load), and writes it when fetched.
- Pinned files are never evicted: every path listed in cache/pins/*.txt. A running walk lists there every tile it has visited
  (re-embedding reads them all every 100 steps) and removes its pin file when it ends. A stale pin file (a killed walk) only pins.
- Files younger than MIN_AGE_S are not evicted either (offers just fetched or prefetched, not yet read).
- Scene metadata (cache/scenes/*.json) is never evicted. Evicted tiles can be fetched again: the cache holds no state of its own.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "landsat1" / "cache"
PINS = CACHE / "pins"
MIN_AGE_S = 900


def scan(cache: Path = CACHE) -> list[tuple[float, int, str]]:
    """(mtime, bytes, path relative to the cache) of every tile file."""
    out = []
    for d in os.scandir(cache):
        if not d.is_dir() or d.name in ("scenes", "pins"):
            continue
        for f in os.scandir(d.path):
            if f.name.endswith(".npz") and ".part" not in f.name:
                try:
                    st = f.stat()
                except FileNotFoundError:
                    continue
                out.append((st.st_mtime, st.st_size, f"{d.name}/{f.name}"))
    return out


def pinned(cache: Path = CACHE) -> set[str]:
    out: set[str] = set()
    for p in (cache / "pins").glob("*.txt"):
        try:
            out.update(x.replace("\\", "/") for x in p.read_text().split() if x)  # Windows pin files carry backslashes (the PC, generation 1)
        except FileNotFoundError:
            continue
    return out


def enforce(cap_gb: float, cache: Path = CACHE, min_age_s: float = MIN_AGE_S) -> dict:
    files = scan(cache)
    total = sum(b for _, b, _ in files)
    cap = cap_gb * 1e9
    pins = pinned(cache)
    out = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "files": len(files), "gb": round(total / 1e9, 2), "pinned": len(pins), "evicted": 0, "evicted_gb": 0.0}
    if total <= cap:
        return out
    now = time.time()
    freed = 0
    for mt, b, rel in sorted(files):
        if total - freed <= cap:
            break
        if rel in pins or now - mt < min_age_s:
            continue
        try:
            os.remove(cache / rel)
        except FileNotFoundError:
            continue
        except OSError:  # Windows: a file open in a walker can't be removed; it is skipped this pass
            continue
        freed += b
        out["evicted"] += 1
    out["evicted_gb"] = round(freed / 1e9, 2)
    out["gb_after"] = round((total - freed) / 1e9, 2)
    if total - freed > cap:
        out["warning"] = "still above the cap: everything left is pinned or younger than min_age_s"
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap-gb", type=float, default=10.0)
    ap.add_argument("--every", type=float, default=0.0, help="seconds between passes; 0 = once")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report:
        f = scan()
        print(json.dumps({"files": len(f), "gb": round(sum(b for _, b, _ in f) / 1e9, 2), "pinned": len(pinned())}))
        return
    while True:
        r = enforce(a.cap_gb)
        if r["evicted"] or "warning" in r or not a.every:
            print(json.dumps(r), flush=True)
        if not a.every:
            return
        time.sleep(a.every)


if __name__ == "__main__":
    main()
