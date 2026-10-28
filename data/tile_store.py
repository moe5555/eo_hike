"""Lazy global tile store over Major TOM Core-S2L2A (dreams v3).

    from data.tile_store import TileStore, World
    store = TileStore()                       # global index, on-disk LRU cache (50 GB default)
    a = store.get_lowres(i)                   # [256, 256, 3] uint8, ~41.7 m/px: what the walker sees
    b = store.get_hires(i)                    # [1068, 1068, 3] uint8, native 10 m: GAN crops

RGB source: the archive's `thumbnail` column, i.e. the full 1068x1068 B04/B03/B02 grid under the
archive's one fixed scale (see gen/hires.py; data/global_stretch.py documents it on a global sample).
Low-res = BOX resize to 256 px, exactly as v1's tiles.npy.

Cache layout (cache_dir, default data/global/cache):
    png/<idx // 10000>/<idx>.png   thumbnail bytes (~150-250 kB), LRU-evicted to `cache_gb`
    low/<idx // 10000>/<idx>.npy   256 px low-res (196 kB), evicted together with the png
    meta/<part>.meta + .json       parquet footers (~1 MB each), so a file's footer is read once
v1's cached regional thumbnails (data/raw/majortom_thumbs/thumbs) are used as a read-only seed.

Remote reads fetch only the `thumbnail` column chunk of one row group, from the file's signed CDN URL (resolved
once per file, see TileStore._signed; a Hugging Face token is sent if one is set: HF_TOKEN or `hf auth login`). Up to 8 attempts per tile with
exponential backoff; an HTTP 429 (Hugging Face rate limit) pauses every thread of the store for 15 s,
doubling while 429s keep coming (cap 5 min). Every fetch is timed. World = the walker's view of the store: a pool of tile ids (global,
regional or a confinement circle), a BallTree over that pool and random long-jump targets.
"""

from __future__ import annotations

import io
import json
import os
import threading
import time
from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor, wait
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parent
GLOBAL = ROOT / "global"
INDEX_PQ = GLOBAL / "index.parquet"
V1_THUMBS = ROOT / "raw" / "majortom_thumbs" / "thumbs"
EARTH_R_KM = 6371.0088
LOW_PX = 256


class TileStore:
    def __init__(self, cache_dir: Path | str = GLOBAL / "cache", cache_gb: float = 50.0, workers: int = 16,
                 retries: int = 8, mem_low: int = 20000, index: pd.DataFrame | None = None) -> None:
        self.idx = index if index is not None else pd.read_parquet(INDEX_PQ)
        self.N = len(self.idx)
        self.url = self.idx.parquet_url.to_numpy()
        self.row = self.idx.parquet_row.to_numpy()
        self.cell = self.idx.grid_cell.to_numpy()
        self.cache = Path(cache_dir)
        for d in ("png", "low", "meta"):
            (self.cache / d).mkdir(parents=True, exist_ok=True)
        self.cap = int(cache_gb * 1e9)
        self.retries = retries
        self.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="tile")
        self.lock = threading.Lock()
        self.inflight: dict[int, Future] = {}
        self.meta_locks: dict[str, threading.Lock] = {}
        self.meta_mem: dict[str, tuple] = {}
        self.mem: OrderedDict[int, np.ndarray] = OrderedDict()
        self.mem_cap = mem_low
        self.stats = {"hit_mem": 0, "hit_disk": 0, "hit_seed": 0, "remote": 0, "fail": 0, "retry": 0, "rate_limited": 0, "remote_sec": 0.0}
        self.cool_until, self.n429, self.last429 = 0.0, 0, 0.0
        self.signed: dict[str, tuple[str, float]] = {}
        self.fetch_log: list[tuple[int, float, int]] = []  # (idx, seconds, attempts)
        self._seed = self._v1_seed()
        self._scan_disk()

    # -- paths / disk LRU ------------------------------------------------------------------
    def _p(self, kind: str, i: int) -> Path:
        return self.cache / kind / str(i // 10000) / f"{i}.{'png' if kind == 'png' else 'npy'}"

    def _v1_seed(self) -> dict[str, Path]:
        if not V1_THUMBS.exists():
            return {}
        return {p.stem: p for p in V1_THUMBS.glob("*.png")}

    def _scan_disk(self) -> None:
        """Rebuild the LRU order from file mtimes (touched on every hit)."""
        files = []
        for p in (self.cache / "png").glob("*/*.png"):
            st = p.stat()
            files.append((st.st_mtime, int(p.stem), st.st_size))
        files.sort()
        self.lru: OrderedDict[int, int] = OrderedDict((i, s + LOW_PX * LOW_PX * 3 + 128) for _, i, s in files)
        self.used = sum(self.lru.values())

    def _touch(self, i: int) -> None:
        with self.lock:
            if i in self.lru:
                self.lru.move_to_end(i)
        try:
            os.utime(self._p("png", i))
        except OSError:
            pass

    def _admit(self, i: int, nbytes: int) -> None:
        with self.lock:
            self.lru[i] = nbytes
            self.lru.move_to_end(i)
            self.used += nbytes
            victims = []
            while self.used > self.cap and len(self.lru) > 1:
                j, s = self.lru.popitem(last=False)
                self.used -= s
                victims.append(j)
        for j in victims:
            for k in ("png", "low"):
                self._p(k, j).unlink(missing_ok=True)

    def cached(self, i: int) -> bool:
        return i in self.mem or self._p("low", i).exists()

    # -- remote ----------------------------------------------------------------------------
    def _footer(self, url: str):
        import pyarrow.parquet as pq

        if url in self.meta_mem:
            return self.meta_mem[url]
        with self.lock:
            lk = self.meta_locks.setdefault(url, threading.Lock())
        with lk:
            if url in self.meta_mem:
                return self.meta_mem[url]
            name = url.rsplit("/", 1)[-1].replace(".parquet", "")
            mp, jp = self.cache / "meta" / f"{name}.meta", self.cache / "meta" / f"{name}.json"
            if mp.exists() and jp.exists():
                md, size = pq.read_metadata(mp), json.loads(jp.read_text())["size"]
            else:
                f = self._fs().open(self._signed(url), "rb", block_size=1 << 20, cache_type="none")
                size = f.size
                md = pq.ParquetFile(f).metadata
                md.write_metadata_file(str(mp) + ".part")
                os.replace(str(mp) + ".part", mp)
                jp.write_text(json.dumps({"size": size}))
            self.meta_mem[url] = (md, size)
            return md, size

    _local = threading.local()

    def _fs(self):
        if not hasattr(self._local, "fs"):
            import fsspec

            self._local.fs = fsspec.filesystem("https", skip_instance_cache=True)
        return self._local.fs

    def _signed(self, url: str, refresh: bool = False) -> str:
        """Resolve a Hub file URL once to its signed CDN location. Range reads against the CDN URL do not count
        towards the Hub's per-IP "resolvers" rate limit (3,000 per 5 min anonymously); re-resolved after 40 min."""
        import requests

        with self.lock:
            e = self.signed.get(url)
        if e is not None and not refresh and time.time() - e[1] < 2400:
            return e[0]
        from huggingface_hub import get_token

        tok = get_token()  # HF_TOKEN env var, else the token saved by `hf auth login`
        r = requests.head(url, allow_redirects=False, timeout=30, headers={"Authorization": f"Bearer {tok}"} if tok else {})
        if r.status_code == 429:
            raise RuntimeError(f"429 resolver rate limit (Retry-After {r.headers.get('Retry-After')})")
        if r.status_code not in (200, 301, 302, 303, 307, 308):
            raise RuntimeError(f"resolve {url}: HTTP {r.status_code}")
        loc = r.headers.get("Location", url) if r.is_redirect else url
        if loc.startswith("/"):
            loc = "https://huggingface.co" + loc
        with self.lock:
            self.signed[url] = (loc, time.time())
        return loc

    def _remote_png(self, i: int) -> bytes:
        import pyarrow.parquet as pq

        url, r = self.url[i], int(self.row[i])
        md, size = self._footer(url)
        try:
            with self._fs().open(self._signed(url), "rb", block_size=1 << 20, cache_type="none", size=size) as f:
                tbl = pq.ParquetFile(f, metadata=md).read_row_group(r, columns=["thumbnail", "grid_cell"])
        except Exception:
            with self.lock:
                self.signed.pop(url, None)  # expired or bad signed URL: resolve again on the next attempt
            raise
        if tbl.column("grid_cell")[0].as_py() != self.cell[i]:
            raise RuntimeError(f"row mismatch for tile {i}: {self.cell[i]} vs {tbl.column('grid_cell')[0].as_py()}")
        return tbl.column("thumbnail")[0].as_py()

    def _load(self, i: int) -> np.ndarray:
        """Make sure tile i is in the disk cache (png + low); return its low-res array."""
        lp = self._p("low", i)
        if lp.exists():
            self.stats["hit_disk"] += 1
            self._touch(i)
            return np.load(lp)
        r = self.idx.iloc[i]
        seed = self._seed.get(f"{r.grid_cell}_{pd.Timestamp(r.timestamp).strftime('%Y%m%dT%H%M%S')}")
        if seed is not None:
            png = seed.read_bytes()
            self.stats["hit_seed"] += 1
        else:
            t0, err = time.time(), None
            for a in range(self.retries):
                wait_s = self.cool_until - time.time()
                if wait_s > 0:  # the whole store is backing off after a 429
                    time.sleep(wait_s)
                try:
                    png = self._remote_png(i)
                    err = None
                    break
                except Exception as e:  # noqa: BLE001
                    err = e
                    self.stats["retry"] += 1
                    if "429" in str(e):
                        # Hugging Face rate limit: pause every thread, longer each time it repeats
                        self.stats["rate_limited"] += 1
                        with self.lock:
                            self.n429 = self.n429 + 1 if time.time() - self.last429 < 300 else 1
                            self.last429 = time.time()
                            self.cool_until = max(self.cool_until, time.time() + min(15.0 * 2 ** (self.n429 - 1), 300.0))
                    else:
                        time.sleep(min(2.0**a, 30.0) * (1 + 0.25 * np.random.rand()))
            dt = time.time() - t0
            self.fetch_log.append((i, dt, a + 1))
            if err is not None:
                self.stats["fail"] += 1
                raise err
            self.stats["remote"] += 1
            self.stats["remote_sec"] += dt
        low = np.asarray(Image.open(io.BytesIO(png)).convert("RGB").resize((LOW_PX, LOW_PX), Image.Resampling.BOX))
        pp = self._p("png", i)
        pp.parent.mkdir(parents=True, exist_ok=True)
        lp.parent.mkdir(parents=True, exist_ok=True)
        pp.with_suffix(".part").write_bytes(png)
        os.replace(pp.with_suffix(".part"), pp)
        with open(lp.with_suffix(".part"), "wb") as fh:
            np.save(fh, low)
        os.replace(lp.with_suffix(".part"), lp)
        self._admit(i, len(png) + low.nbytes + 128)
        return low

    def _submit(self, i: int) -> Future:
        with self.lock:
            fut = self.inflight.get(i)
            if fut is None:
                fut = self.pool.submit(self._load, i)
                self.inflight[i] = fut
                fut.add_done_callback(lambda _f, i=i: self._done(i))
            return fut

    def _done(self, i: int) -> None:
        with self.lock:
            self.inflight.pop(i, None)

    def _remember(self, i: int, a: np.ndarray) -> None:
        with self.lock:
            self.mem[i] = a
            self.mem.move_to_end(i)
            while len(self.mem) > self.mem_cap:
                self.mem.popitem(last=False)

    # -- public ----------------------------------------------------------------------------
    def get_lowres(self, i: int) -> np.ndarray:
        i = int(i)
        a = self.mem.get(i)
        if a is not None:
            self.stats["hit_mem"] += 1
            with self.lock:
                self.mem.move_to_end(i)
            return a
        a = self._submit(i).result()
        self._remember(i, a)
        return a

    def get_many(self, ids, timeout: float = 30.0) -> tuple[dict[int, np.ndarray], list[int], dict]:
        """Low-res for several tiles in parallel. Returns (arrays, dropped ids, per-call stats)."""
        out, futs, n_hit = {}, {}, 0
        for i in map(int, ids):
            a = self.mem.get(i)
            if a is not None:
                out[i] = a
                n_hit += 1
                self.stats["hit_mem"] += 1
            elif i not in futs:
                n_hit += self._p("low", i).exists()
                futs[i] = self._submit(i)
        t0 = time.time()
        if futs:
            wait(list(futs.values()), timeout=timeout)
        dropped = []
        for i, f in futs.items():
            if f.done() and f.exception() is None:
                out[i] = f.result()
                self._remember(i, out[i])
            else:
                dropped.append(i)
        return out, dropped, {"wait_sec": time.time() - t0, "n": len(set(map(int, ids))), "cache_hits": n_hit}

    def prefetch(self, ids) -> None:
        for i in map(int, ids):
            if i not in self.mem and not self._p("low", i).exists():
                self._submit(i)

    def get_png(self, i: int) -> bytes:
        i = int(i)
        p = self._p("png", i)
        if not p.exists():
            self._submit(i).result()
        self._touch(i)
        return p.read_bytes()

    def get_hires(self, i: int) -> np.ndarray:
        """Native 10 m RGB, ~1068x1068 uint8."""
        return np.asarray(Image.open(io.BytesIO(self.get_png(i))).convert("RGB"))

    def fetch_all(self, ids, desc: str = "fetch") -> list[int]:
        """Blocking bulk fill of the disk cache. Returns ids that failed."""
        from tqdm import tqdm

        ids = [int(i) for i in ids if not self._p("png", int(i)).exists()]
        futs = {self._submit(i): i for i in ids}
        failed = []
        for f in tqdm(futs, total=len(futs), desc=desc):
            try:
                f.result()
            except Exception:  # noqa: BLE001
                failed.append(futs[f])
        return failed

    def summary(self) -> dict:
        s = dict(self.stats)
        lat = np.array([d for _, d, _ in self.fetch_log]) if self.fetch_log else np.zeros(1)
        s.update(remote_p50=float(np.median(lat)), remote_p95=float(np.percentile(lat, 95)), cache_used_gb=round(self.used / 1e9, 2))
        return s


class World:
    """The walker's world: a pool of global tile ids, its BallTree and blind long-jump targets."""

    def __init__(self, store: TileStore, pool: np.ndarray | None = None, name: str = "global") -> None:
        from sklearn.neighbors import BallTree

        self.store, self.name = store, name
        self.pool = np.arange(store.N) if pool is None else np.sort(np.asarray(pool, dtype=np.int64))
        self.lat = store.idx.lat.to_numpy()
        self.lon = store.idx.lon.to_numpy()
        self.tree = BallTree(np.radians(np.stack([self.lat[self.pool], self.lon[self.pool]], 1)), metric="haversine")

    @classmethod
    def from_config(cls, store: TileStore, cfg: dict) -> "World":
        idx = store.idx
        if cfg.get("confine_center") is not None:
            la, lo = cfg["confine_center"]
            d = haversine_km(idx.lat.to_numpy(), idx.lon.to_numpy(), la, lo)
            return cls(store, np.flatnonzero(d <= float(cfg["confine_radius_km"])), "confined")
        if cfg.get("world") == "regional_lazy":
            return cls(store, np.flatnonzero(idx.regional.to_numpy()), "regional_lazy")
        return cls(store, None, "global")

    def neighbours(self, i: int, radius_km: float) -> np.ndarray:
        ind = self.tree.query_radius(np.radians([[self.lat[i], self.lon[i]]]), r=radius_km / EARTH_R_KM)[0]
        nb = self.pool[ind]
        return np.sort(nb[nb != i])

    def nearest(self, lat: float, lon: float) -> int:
        return int(self.pool[self.tree.query(np.radians([[lat, lon]]), k=1)[1][0, 0]])

    def random_tile(self, rng: np.random.Generator) -> int:
        return int(self.pool[rng.integers(len(self.pool))])


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_R_KM * np.arcsin(np.sqrt(a))
