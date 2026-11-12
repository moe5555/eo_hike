"""Lazy tile store over the Landsat 1 world (data/landsat1_world.py): COG windows read from Planetary Computer when a cell is offered.

    from data.landsat1_store import Landsat1TileStore
    store = Landsat1TileStore()            # data/landsat1/index.parquet, disk cache data/landsat1/cache/
    a = store.get_lowres(i)                # [256, 256, 3] uint8: the one view (CIR, sqrt tone, the fixed global stretch)
    b = store.bands(i)                     # float16 [4, 178, 178]: TOA reflectance of green, red, nir08, nir09 (nir09 is cached, not seen)
    q = store.quirks([i, j]); qc = store.crop_quirks([i])   # per cell, per 4 x 4 grid crop

    python data/landsat1_store.py baseline --n 2000      # random cells: quirk baselines and the pixel sample for the global stretch
    python data/landsat1_store.py stretch                # percentiles of the baseline sample -> the STRETCH constants to paste here

Same interface as data/tile_store.TileStore (get_many, get_lowres, prefetch, cached, summary, fetch_log), so agent/walk.py and the
viewers use it through data/tile_store.open_store (`world: landsat1`).

Reading (brief A4). Per cell: the 178 x 178 px window of the selected scene (index r0, c0) plus a 2 px margin for the stripe measure,
from the four band COGs and QA_PIXEL and QA_RADSAT. One STAC item and one MTL per scene, cached on disk. Anonymous SAS token,
renewed every 30 min and on any HTTP 403. Up to RETRIES attempts per cell with exponential backoff; WORKERS cells at once. Each cell
is cached as one .npz (~0.4 MB): TOA float16 for the four bands, the two QA windows, and its quirk shares.

Radiometry (brief A5). TOA reflectance from the MTL, (M * DN + A) / sin(sun elevation). Night scenes (sun elevation <= 0): M * DN + A
without the sun term (no infinities), flagged. Fill (QA_PIXEL bit 0, or DN 0 in any band) is NaN, black in the tile. Then the tone
(TONE, e10's sqrt) and one fixed linear stretch per channel for the whole world (STRETCH_LO/HI, from the baseline sample, percentiles
STRETCH_PCT), CIR = (nir08, red, green), uint8, then resized 178 -> 256 px bilinear as e10's build. Nothing is repaired or equalised:
low sun, offsets, stripes, saturation, clouds and night stay as stored.

Quirks (brief A6), measured from pixels, never shown to the walker; QA flags are separate columns, since their disagreement with the
pixels is itself a readout. Per cell and per grid crop (4 x 4, native bounds round(k * 178 / 4)):
    fill, cloud (QA_PIXEL bit 3), dropped (QA_RADSAT bit 9),
    stripe_<b>  e10's line-defect measure per band: |DN - vertical 5 px median| > STRIPE_DN, where all five are valid
    at255_<b>   share at DN 255
    satflag_<b> QA_RADSAT saturation bit of the band (MSS bands 4-7 = bits 3-6)
    disagree_<b> share where the flag and DN 255 disagree (flag xor at255)
Shares are of the window's pixels; band measures are of its valid pixels.
"""

from __future__ import annotations

import io
import json
import os
import sys
import threading
import time
from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor, wait
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
WORLD = ROOT / "landsat1"
INDEX_PQ = WORLD / "index.parquet"
CACHE = WORLD / "cache"
ITEM_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l1/items/{}"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/{account}/{container}"
BANDS = ("green", "red", "nir08", "nir09")  # MSS bands 4-7
QA = ("qa_pixel", "qa_radsat")
SAT_BIT = {"green": 3, "red": 4, "nir08": 5, "nir09": 6}
DROPPED_BIT = 9
NATIVE_PX, MARGIN, LOW_PX, GRID = 178, 2, 256, 4
STRIPE_DN = 25  # e10 (data/landsat_pass.STRIPE_DN)
WORKERS, RETRIES = 8, 6

# The one view. Tone and stretch are named constants; every rendering of this world goes through render().
TONE = "sqrt"
STRETCH_PCT = (0.5, 99.5)
# Channels (nir08, red, green), after the tone: percentiles STRETCH_PCT of 397,600 valid pixels (200 per cell) of the 1,988 daylit cells
# among 2,000 random cells of the world (`baseline`, then `stretch`, 2026-11-12). The top is set by snow, ice, cloud and saturation.
STRETCH_LO = (0.04825839400291443, 0.03737824037671089, 0.0)
STRETCH_HI = (0.9830099940299988, 0.9217425584793091, 0.9872243404388428)
STRETCH_SOURCE = "baseline 2,000 random cells, 2026-11-12"

# Image keys (the revisit rule, data/landsat1_world.py `stack`): image = cell + rank * KEY_STRIDE, rank 0 = the earliest acquisition,
# so rank-0 keys are the cell ids of the index and every earlier use of the store is unchanged.
KEY_STRIDE = 1 << 21  # > 1,466,863 cells
STACK = WORLD / "stack"
SCENES_PQ = WORLD / "scenes.parquet"


def image_key(cell, rank):
    return np.asarray(cell, np.int64) + np.asarray(rank, np.int64) * KEY_STRIDE


def split_key(key) -> tuple[np.ndarray, np.ndarray]:
    key = np.asarray(key, np.int64)
    return key % KEY_STRIDE, key // KEY_STRIDE


QUIRK_BANDS = ("stripe", "at255", "satflag", "disagree")
QUIRK_COLS = ("fill", "cloud", "dropped") + tuple(f"{q}_{b}" for q in QUIRK_BANDS for b in BANDS)


def crop_bounds(n: int = NATIVE_PX, k: int = GRID) -> np.ndarray:
    """Native pixel bounds of the k x k grid crops: round(j * n / k), j = 0..k (0, 44, 89, 134, 178 for 178 px)."""
    return np.rint(np.arange(k + 1) * n / k).astype(int)


def stripe_mask(dn: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """e10's line-defect measure on one band (data/landsat_pass.stripe_mask): more than STRIPE_DN from the vertical 5 px median,
    counted only where the five pixels are valid."""
    from scipy.ndimage import binary_erosion, median_filter

    inner = binary_erosion(valid, structure=np.ones((5, 1), bool))
    return (np.abs(dn.astype(np.int16) - median_filter(dn, size=(5, 1)).astype(np.int16)) > STRIPE_DN) & inner


def quirk_arrays(dn: dict, qa_pixel: np.ndarray, qa_radsat: np.ndarray | None, margin: int = MARGIN) -> tuple[np.ndarray, np.ndarray]:
    """Quirk shares (QUIRK_COLS) of one cell and of its 4 x 4 grid crops. dn: band -> uint8 window with `margin` px on every side
    (for the stripe median), qa arrays the same shape. Returns (cell [Q], crops [16, Q]) as float32; NaN where a band measure has no
    valid pixel. Without QA_RADSAT (the e10 pass did not download it) the flag columns are NaN."""
    qp = qa_pixel.astype(np.uint16)
    valid = (qp & 1) == 0
    for b in BANDS:
        valid &= dn[b] > 0
    m = {"fill": ~valid, "cloud": ((qp >> 3) & 1).astype(bool) & valid}
    qr = None if qa_radsat is None else qa_radsat.astype(np.uint16)
    m["dropped"] = None if qr is None else ((qr >> DROPPED_BIT) & 1).astype(bool)
    for b in BANDS:
        m[f"stripe_{b}"] = stripe_mask(dn[b], valid)
        m[f"at255_{b}"] = dn[b] == 255
        if qr is not None:
            m[f"satflag_{b}"] = ((qr >> SAT_BIT[b]) & 1).astype(bool)
            m[f"disagree_{b}"] = m[f"satflag_{b}"] ^ m[f"at255_{b}"]
    sl = slice(margin, margin + NATIVE_PX)
    v = valid[sl, sl]
    bnd = crop_bounds()

    def share(a: np.ndarray, vv: np.ndarray, per_valid: bool) -> float:
        if not per_valid:
            return float(a.mean())
        n = vv.sum()
        return float((a & vv).sum() / n) if n else np.nan

    def shares(a: np.ndarray, per_valid: bool) -> tuple[float, np.ndarray]:
        a = a[sl, sl]
        out = np.empty(GRID * GRID, np.float32)
        for k in range(GRID * GRID):
            r, c = divmod(k, GRID)
            s = (slice(bnd[r], bnd[r + 1]), slice(bnd[c], bnd[c + 1]))
            out[k] = share(a[s], v[s], per_valid)
        return share(a, v, per_valid), out

    cell, crops = np.full(len(QUIRK_COLS), np.nan, np.float32), np.full((GRID * GRID, len(QUIRK_COLS)), np.nan, np.float32)
    for j, q in enumerate(QUIRK_COLS):
        a = m.get(q)
        if a is None:
            continue
        per_valid = q not in ("fill", "dropped")
        cell[j], crops[:, j] = shares(a, per_valid)
    return cell, crops


def toa(dn: np.ndarray, mult: float, add: float, sun_elevation: float) -> np.ndarray:
    """TOA reflectance (M * DN + A) / sin(sun elevation); at night (sun <= 0) M * DN + A, without the sun term."""
    r = mult * dn.astype(np.float32) + add
    return r / np.float32(np.sin(np.radians(sun_elevation))) if sun_elevation > 0 else r


def render(bands: np.ndarray, lo=STRETCH_LO, hi=STRETCH_HI, out_px: int = LOW_PX) -> np.ndarray:
    """The one view: TOA [4, n, n] (green, red, nir08, nir09; NaN = fill) -> CIR uint8 [out_px, out_px, 3]. Tone, the fixed stretch,
    fill black, then bilinear to out_px (e10's build)."""
    from PIL import Image

    ch = np.stack([bands[2], bands[1], bands[0]], -1).astype(np.float32)  # nir08, red, green
    if TONE == "sqrt":
        ch = np.sqrt(np.maximum(ch, 0.0))  # NaN (fill) stays NaN
    lo, hi = np.asarray(lo, np.float32), np.asarray(hi, np.float32)
    rgb = np.clip((ch - lo) / (hi - lo), 0.0, 1.0) * 255.0
    rgb = np.where(np.isfinite(rgb), rgb, 0.0).astype(np.uint8)
    im = Image.fromarray(rgb)
    n = rgb.shape[0]
    return np.asarray(im.resize((out_px, out_px), Image.Resampling.BILINEAR if out_px >= n else Image.Resampling.BOX))


# GDAL settings for the COG reads. GDAL_CACHEMAX must be an int (rasterio sets it through its own call; a string fails every read)
GDAL_ENV = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES", "GDAL_HTTP_MAX_RETRY": "2",
            "GDAL_HTTP_RETRY_DELAY": "1", "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".TIF,.tif",
            "GDAL_HTTP_TIMEOUT": "60", "GDAL_HTTP_CONNECTTIMEOUT": "20",  # a stalled read fails and is retried, never hangs
            "GDAL_CACHEMAX": 64}  # MB; GDAL's default (5 % of RAM per process) made three walkers swap


class Signer:
    """Planetary Computer SAS tokens per storage container, renewed after 30 min or when forced (HTTP 403)."""

    def __init__(self) -> None:
        self.tok: dict[tuple[str, str], tuple[str, float]] = {}
        self.lock = threading.Lock()
        self.n_renew = 0

    def __call__(self, href: str, force: bool = False) -> str:
        import requests

        acct, cont = href.split("//")[1].split(".")[0], href.split(".net/")[1].split("/")[0]
        with self.lock:
            t = self.tok.get((acct, cont))
            if force or t is None or time.time() - t[1] > 1800:
                r = requests.get(SAS.format(account=acct, container=cont), timeout=60)
                r.raise_for_status()
                t = (r.json()["token"], time.time())
                self.tok[(acct, cont)] = t
                self.n_renew += 1
        return f"{href}?{t[0]}"


class Landsat1TileStore:
    _meta_from_stack = False  # the clock store takes every image's metadata from its own lists

    def __init__(self, cache_dir: Path | str = CACHE, workers: int = WORKERS, retries: int = RETRIES, mem_low: int = 20000,
                 index: pd.DataFrame | None = None) -> None:
        self.idx = index if index is not None else pd.read_parquet(INDEX_PQ)
        self.N = len(self.idx)
        self.cache = Path(cache_dir)
        (self.cache / "scenes").mkdir(parents=True, exist_ok=True)
        self.retries = retries
        self.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="l1")
        self.lock = threading.RLock()  # reentrant: a done-callback may run in the thread that holds it (dry run 2026-11-12: a walk hung)
        self.inflight: dict[int, Future] = {}
        self.scene_locks: dict[str, threading.Lock] = {}
        self.scene_mem: dict[str, dict] = {}
        self.mem: OrderedDict[int, np.ndarray] = OrderedDict()
        self.mem_cap = mem_low
        self.sign = Signer()
        self.stats = {"hit_mem": 0, "hit_disk": 0, "remote": 0, "fail": 0, "retry": 0, "remote_sec": 0.0, "scene_meta": 0}
        self.fetch_log: list[tuple[int, float, int]] = []
        self.qmem: OrderedDict[int, tuple] = OrderedDict()  # (cell, crop) quirk shares per image key, filled whenever a tile is read
        self.qmem_cap = 20000
        self.fail_log: list[tuple[int, str]] = []
        self._scene = self.idx.scene.to_numpy()
        self._win = self.idx[["r0", "c0"]].to_numpy()
        self._sun = self.idx.sun_elevation.to_numpy()
        self._stack = None  # memory-mapped on first use of a rank above 0
        self._scenes = None

    # -- the stack of acquisitions per cell ----------------------------------------------------------------------------------
    def _load_stack(self) -> None:
        if self._stack is None:
            self._stack = {k: np.load(STACK / f"{k}.npy", mmap_mode="r") for k in ("start", "scene", "r0", "c0")}
            self._scenes = pd.read_parquet(SCENES_PQ, columns=["scene", "id", "datetime", "level", "tier", "night", "sun_elevation", "scene_cloud",
                                                                 "path", "wrs_row"]).set_index("scene")

    def stack_len(self, cell: int) -> int:
        """Number of acquisitions (one per day) of a cell."""
        self._load_stack()
        st = self._stack["start"]
        return int(st[int(cell) + 1] - st[int(cell)])

    def _resolve(self, key: int) -> tuple[str, int, int, float]:
        """(scene id, r0, c0, sun elevation) of an image key."""
        cell, rank = (int(v) for v in split_key(key))
        if rank == 0:
            r0, c0 = (int(v) for v in self._win[cell])
            return str(self._scene[cell]), r0, c0, float(self._sun[cell])
        self._load_stack()
        e = int(self._stack["start"][cell]) + rank
        assert e < int(self._stack["start"][cell + 1]), f"cell {cell} has no acquisition of rank {rank}"
        sc = int(self._stack["scene"][e])
        row = self._scenes.loc[sc]
        return str(row.id), int(self._stack["r0"][e]), int(self._stack["c0"][e]), float(row.sun_elevation)

    def acquisitions(self, keys) -> pd.DataFrame:
        """Per image key: cell, rank, scene, date, level, tier, night, sun elevation, scene cloud."""
        keys = np.asarray(list(keys), np.int64)
        cell, rank = split_key(keys)
        self._load_stack()
        st = self._stack["start"]
        sc = np.asarray(self._stack["scene"])[st[cell] + rank] if len(keys) else np.zeros(0, int)
        m = self._scenes.loc[sc].reset_index(drop=True)
        return pd.concat([pd.DataFrame({"tile_idx": keys, "cell": cell, "rank": rank}), m.rename(columns={"id": "scene", "datetime": "timestamp"})], axis=1)

    # -- paths ---------------------------------------------------------------------------------------------------------------
    def _p(self, i: int) -> Path:
        """Cache file of an image key; rank 0 (the earliest) keeps the cell's own path."""
        cell, rank = (int(v) for v in split_key(i))
        return self.cache / str(cell // 10000) / (f"{cell}.npz" if rank == 0 else f"{cell}_r{rank}.npz")

    def cached(self, i: int) -> bool:
        return int(i) in self.mem or self._p(int(i)).exists()

    # -- remote --------------------------------------------------------------------------------------------------------------
    def _scene_meta(self, sid: str) -> dict:
        """Asset hrefs and the MTL's reflectance rescaling of one scene, from disk or once from Planetary Computer."""
        import requests

        if sid in self.scene_mem:
            return self.scene_mem[sid]
        with self.lock:
            lk = self.scene_locks.setdefault(sid, threading.Lock())
        with lk:
            if sid in self.scene_mem:
                return self.scene_mem[sid]
            p = self.cache / "scenes" / f"{sid}.json"
            if p.exists():
                meta = json.loads(p.read_text())
            else:
                it = requests.get(ITEM_URL.format(sid), timeout=60)
                it.raise_for_status()
                it = it.json()
                href = {k: it["assets"][k]["href"] for k in BANDS + QA + ("mtl.json",)}
                mtl = requests.get(self.sign(href["mtl.json"]), timeout=60)
                if mtl.status_code == 403:
                    mtl = requests.get(self.sign(href["mtl.json"], force=True), timeout=60)
                mtl.raise_for_status()
                L = mtl.json()["LANDSAT_METADATA_FILE"]
                resc, files = L["LEVEL1_RADIOMETRIC_RESCALING"], L["PRODUCT_CONTENTS"]
                num = {b: next(k for k, v in files.items() if k.startswith("FILE_NAME_BAND_") and v == Path(href[b]).name).rsplit("_", 1)[1]
                       for b in BANDS}
                meta = {"href": href, "num": num, "sun_elevation": float(L["IMAGE_ATTRIBUTES"]["SUN_ELEVATION"]),
                        "mult": {b: float(resc[f"REFLECTANCE_MULT_BAND_{num[b]}"]) for b in BANDS},
                        "add": {b: float(resc[f"REFLECTANCE_ADD_BAND_{num[b]}"]) for b in BANDS}}
                tmp = p.with_suffix(f".part{os.getpid()}{threading.get_ident()}")
                tmp.write_text(json.dumps(meta))
                os.replace(tmp, p)
                self.stats["scene_meta"] += 1
            self.scene_mem[sid] = meta
            return meta

    def _read_remote(self, i: int) -> dict:
        import rasterio
        from rasterio.windows import Window

        sid, r0, c0, _ = self._resolve(i)
        meta = self._scene_meta(sid)
        n = NATIVE_PX + 2 * MARGIN
        win = Window(c0 - MARGIN, r0 - MARGIN, n, n)
        out = {}
        with rasterio.Env(**GDAL_ENV):
            for k in BANDS + QA:
                try:
                    with rasterio.open(self.sign(meta["href"][k])) as ds:
                        out[k] = ds.read(1, window=win, boundless=True, fill_value=0)
                except rasterio.errors.RasterioIOError as e:
                    if "403" in str(e):
                        self.sign(meta["href"][k], force=True)
                    raise
        out["meta"] = meta
        return out

    def _adopt(self, i: int, p: Path) -> None:
        """Hook: move an existing cache file of the same window into place (Landsat1ClockStore). Nothing here."""

    def _load(self, i: int) -> np.ndarray:
        """Make sure cell i is in the disk cache; return its 256 px tile. A disk hit touches the file's mtime (the cache cap's LRU,
        data/cache_cap.py); a file evicted between the check and the read is fetched again."""
        p = self._p(i)
        if not p.exists():
            self._adopt(i, p)
        if p.exists():
            try:
                with np.load(p) as z:
                    a, q = render(z["toa"]), (z["q_cell"], z["q_crop"])
                self._remember_q(i, q)
                self.stats["hit_disk"] += 1
                try:
                    os.utime(p)
                except OSError:
                    pass
                return a
            except (FileNotFoundError, OSError, ValueError):  # evicted (or cut short) under our feet: fetch again
                self.stats["evicted_reload"] = self.stats.get("evicted_reload", 0) + 1
        t0, err = time.time(), None
        for a in range(self.retries):
            try:
                w = self._read_remote(i)
                err = None
                break
            except Exception as e:  # noqa: BLE001
                err = e
                self.stats["retry"] += 1
                kind = type(e).__name__
                self.stats[f"err_{kind}"] = self.stats.get(f"err_{kind}", 0) + 1
                if self.stats["retry"] <= 10 or self.stats["retry"] % 50 == 0:  # into the walk's log, so a stall names its cause
                    print(f"[store] {time.strftime('%H:%M:%S')} retry {self.stats['retry']} key {i} attempt {a + 1}: {repr(e)[:300]}", file=sys.stderr, flush=True)
                time.sleep(min(2.0**a, 30.0) * (1 + 0.25 * np.random.default_rng().random()))  # its own generator: no walker stream is touched
        dt = time.time() - t0
        self.fetch_log.append((i, dt, a + 1))
        if err is not None:
            self.stats["fail"] += 1
            self.fail_log.append((i, repr(err)[:300]))
            raise err
        self.stats["remote"] += 1
        self.stats["remote_sec"] += dt
        meta, sun = w["meta"], self._resolve(i)[3]
        sl = slice(MARGIN, MARGIN + NATIVE_PX)
        valid = (w["qa_pixel"][sl, sl] & 1) == 0
        for b in BANDS:
            valid &= w[b][sl, sl] > 0
        bands = np.stack([toa(w[b][sl, sl], meta["mult"][b], meta["add"][b], sun) for b in BANDS])
        bands[:, ~valid] = np.nan
        # the one view is rendered from what the cache stores (float16), so a tile fetched now and the same tile read from disk later are
        # the same pixels (before 2026-11-12 the fresh read rendered float32: a cold and a warm cache gave walks different views)
        bands = bands.astype(np.float16)
        qc, qk = quirk_arrays({b: w[b] for b in BANDS}, w["qa_pixel"], w["qa_radsat"])
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(f"{p.stem}.part{os.getpid()}_{threading.get_ident()}.npz")
        np.savez(tmp, toa=bands, qa_pixel=w["qa_pixel"][sl, sl], qa_radsat=w["qa_radsat"][sl, sl], q_cell=qc, q_crop=qk,
                 fetched=np.array(time.time()))
        os.replace(tmp, p)
        self._remember_q(i, (qc, qk))
        return render(bands)

    def _submit(self, i: int) -> Future:
        with self.lock:
            fut = self.inflight.get(i)
            new = fut is None
            if new:
                fut = self.pool.submit(self._load, i)
                self.inflight[i] = fut
        if new:  # outside the lock: a future already done runs its callback here, at once
            fut.add_done_callback(lambda _f, i=i: self._done(i))
        return fut

    def _done(self, i: int) -> None:
        with self.lock:
            self.inflight.pop(i, None)

    def _remember_q(self, i: int, q: tuple) -> None:
        with self.lock:
            self.qmem[i] = q
            self.qmem.move_to_end(i)
            while len(self.qmem) > self.qmem_cap:
                self.qmem.popitem(last=False)

    def _remember(self, i: int, a: np.ndarray) -> None:
        with self.lock:
            self.mem[i] = a
            self.mem.move_to_end(i)
            while len(self.mem) > self.mem_cap:
                self.mem.popitem(last=False)

    # -- public --------------------------------------------------------------------------------------------------------------
    def get_lowres(self, i: int) -> np.ndarray:
        i = int(i)
        a = self.mem.get(i)
        if a is not None:
            self.stats["hit_mem"] += 1
            return a
        a = self._submit(i).result()
        self._remember(i, a)
        return a

    get_hires = get_lowres  # the 256 px tile is already finer than the 60 m product

    def get_many(self, ids, timeout: float = 30.0) -> tuple[dict[int, np.ndarray], list[int], dict]:
        out, futs, n_hit = {}, {}, 0
        for i in map(int, ids):
            a = self.mem.get(i)
            if a is not None:
                out[i] = a
                n_hit += 1
                self.stats["hit_mem"] += 1
                if i in self.qmem:
                    with self.lock:
                        self.qmem.move_to_end(i)
            elif i not in futs:
                n_hit += self._p(i).exists()
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
            if i not in self.mem and not self._p(i).exists():
                self._submit(i)

    def fetch_all(self, ids, desc: str = "fetch") -> list[int]:
        from tqdm import tqdm

        ids = [int(i) for i in ids if not self._p(int(i)).exists()]
        futs = {self._submit(i): i for i in ids}
        failed = []
        for f in tqdm(futs, total=len(futs), desc=desc, mininterval=10):
            try:
                f.result()
            except Exception:  # noqa: BLE001
                failed.append(futs[f])
        return failed

    def bands(self, i: int) -> np.ndarray:
        """TOA float16 [4, 178, 178] (green, red, nir08, nir09), NaN = fill."""
        i = int(i)
        if not self._p(i).exists():
            self._submit(i).result()
        with np.load(self._p(i)) as z:
            return z["toa"]

    def quirks(self, ids) -> pd.DataFrame:
        """Quirk shares of cached cells, with the index's scene columns. Cells not yet fetched are left out."""
        rows = []
        for i in map(int, ids):
            p = self._p(i)
            if p.exists():
                with np.load(p) as z:
                    rows.append((i, *z["q_cell"].tolist()))
        q = pd.DataFrame(rows, columns=["tile_idx", *QUIRK_COLS])
        if len(q) and (self._meta_from_stack or (split_key(q.tile_idx.to_numpy())[1] > 0).any()):  # later acquisitions (or the clock world): metadata from the stack
            a = self.acquisitions(q.tile_idx.to_numpy())
            a["grid_cell"] = self.idx.grid_cell.to_numpy()[a.cell.to_numpy()]
            meta = a[["grid_cell", "cell", "rank", "scene", "timestamp", "level", "tier", "night", "sun_elevation", "scene_cloud", "path", "wrs_row"]]
        else:
            meta = self.idx.loc[q.tile_idx, ["grid_cell", "scene", "timestamp", "level", "tier", "night", "sun_elevation", "scene_cloud", "path", "wrs_row"]]
        return pd.concat([q.reset_index(drop=True), meta.reset_index(drop=True)], axis=1)

    def crop_quirks(self, ids) -> pd.DataFrame:
        rows = []
        for i in map(int, ids):
            p = self._p(i)
            if p.exists():
                with np.load(p) as z:
                    for k, v in enumerate(z["q_crop"]):
                        rows.append((i, k, *v.tolist()))
        return pd.DataFrame(rows, columns=["tile_idx", "crop", *QUIRK_COLS])

    def cached_ids(self) -> np.ndarray:
        """Image keys in the cache."""
        out = []
        for p in self.cache.glob("*/*.npz"):
            if ".part" in p.name:
                continue
            c, _, r = p.stem.partition("_r")
            out.append(int(image_key(int(c), int(r) if r else 0)))
        return np.array(sorted(out), dtype=np.int64)

    def summary(self) -> dict:
        s = dict(self.stats)
        lat = np.array([d for _, d, _ in self.fetch_log]) if self.fetch_log else np.zeros(1)
        s.update(remote_p50=float(np.median(lat)), remote_p95=float(np.percentile(lat, 95)), sas_renewals=self.sign.n_renew,
                 n_failed=len(self.fail_log), stretch_source=STRETCH_SOURCE, tone=TONE)
        return s


CLOCK = WORLD / "clock"


class Landsat1ClockStore(Landsat1TileStore):
    """The clock world of brief v2 (data/landsat1_world.py `clock`): every cell's acquisitions, one product per date, in date order.
    Image key = idx + rank * KEY_STRIDE, rank in the cell's clock list (rank 0 = its first date). Cache files are named by scene,
    <idx>_s<scene>.npz, so a file always names the window it holds; on a miss, a file of the same (cell, scene) from the e12 cache
    (<idx>.npz or <idx>_r<rank>.npz) is moved into place instead of being fetched again (the windows are identical)."""

    _meta_from_stack = True

    def __init__(self, *a, **k) -> None:
        super().__init__(*a, **k)
        self.ck = {n: np.load(CLOCK / f"{n}.npy", mmap_mode="r") for n in ("start", "day", "scene", "r0", "c0", "night")}
        self.ck_start = np.asarray(self.ck["start"])
        self.ck_day = np.asarray(self.ck["day"])
        self._load_stack()
        self._scene_id = self._scenes.id.reindex(np.arange(int(self._scenes.index.max()) + 1)).to_numpy()
        self._scene_sun = self._scenes.sun_elevation.reindex(np.arange(int(self._scenes.index.max()) + 1)).to_numpy()

    # -- the clock ---------------------------------------------------------------------------------------------------------
    def days(self, cell: int) -> np.ndarray:
        """Acquisition days (since 1970-01-01) of a cell, strictly increasing."""
        c = int(cell)
        return self.ck_day[self.ck_start[c] : self.ck_start[c + 1]]

    def stack_len(self, cell: int) -> int:
        c = int(cell)
        return int(self.ck_start[c + 1] - self.ck_start[c])

    def _entry(self, key) -> np.ndarray:
        cell, rank = split_key(key)
        e = self.ck_start[cell] + rank
        assert np.all(rank < self.ck_start[cell + 1] - self.ck_start[cell]), "rank beyond the cell's acquisitions"
        return e

    def day_of(self, key) -> np.ndarray:
        return self.ck_day[self._entry(key)]

    def night_of(self, key) -> np.ndarray:
        return np.asarray(self.ck["night"])[self._entry(key)]

    def _resolve(self, key: int) -> tuple[str, int, int, float]:
        e = int(self._entry(int(key)))
        sc = int(self.ck["scene"][e])
        return str(self._scene_id[sc]), int(self.ck["r0"][e]), int(self.ck["c0"][e]), float(self._scene_sun[sc])

    def acquisitions(self, keys) -> pd.DataFrame:
        keys = np.asarray(list(keys), np.int64)
        cell, rank = split_key(keys)
        e = self._entry(keys) if len(keys) else np.zeros(0, int)
        sc = np.asarray(self.ck["scene"])[e]
        m = self._scenes.loc[sc].reset_index(drop=True)
        return pd.concat([pd.DataFrame({"tile_idx": keys, "cell": cell, "rank": rank, "day": self.ck_day[e]}),
                          m.rename(columns={"id": "scene", "datetime": "timestamp"})], axis=1)

    # -- cache ---------------------------------------------------------------------------------------------------------------
    def _p(self, i: int) -> Path:
        cell = int(split_key(int(i))[0])
        sc = int(self.ck["scene"][int(self._entry(int(i)))])
        return self.cache / str(cell // 10000) / f"{cell}_s{sc}.npz"

    def _adopt(self, i: int, p: Path) -> None:
        cell = int(split_key(int(i))[0])
        sc = int(self.ck["scene"][int(self._entry(int(i)))])
        old = []
        if str(self._scene[cell]) == str(self._scene_id[sc]):  # the earliest rule's acquisition (e12 rank 0)
            old.append(self.cache / str(cell // 10000) / f"{cell}.npz")
        st = self._stack
        s0, s1 = int(st["start"][cell]), int(st["start"][cell + 1])
        hit = np.flatnonzero(np.asarray(st["scene"][s0:s1]) == sc)
        old += [self.cache / str(cell // 10000) / f"{cell}_r{int(r)}.npz" for r in hit if r > 0]
        for o in old:
            try:
                os.replace(o, p)
                self.stats["adopted"] = self.stats.get("adopted", 0) + 1
                return
            except FileNotFoundError:
                continue

    def cached_ids(self) -> np.ndarray:
        raise NotImplementedError("clock cache files are named by scene; list them with data/cache_cap.py")

    def quirk_row(self, key: int) -> np.ndarray:
        """Quirk shares (QUIRK_COLS) of an image already read; NaN if this store has not read it (or forgot it)."""
        q = self.qmem.get(int(key))
        return np.full(len(QUIRK_COLS), np.nan, np.float32) if q is None else q[0]

    def crop_quirk_rows(self, key: int) -> np.ndarray:
        """[16, QUIRK_COLS] of an image already read; NaN if not."""
        q = self.qmem.get(int(key))
        return np.full((GRID * GRID, len(QUIRK_COLS)), np.nan, np.float32) if q is None else q[1]

    def cache_path(self, key: int) -> str:
        """The cache file of an image key, relative to the cache root (pin files, data/cache_cap.py)."""
        return str(self._p(int(key)).relative_to(self.cache))


# -- offline: baselines and the stretch ----------------------------------------------------------------------------------------
BASELINE = WORLD / "baseline.parquet"
SAMPLE = WORLD / "stretch_sample.npy"


def cmd_baseline(n: int, seed: int = 20261112) -> None:
    """n random cells of the world (uniform over cells): fetched into the cache, their quirks -> baseline.parquet, and a pixel
    sample of the tone-curved CIR channels (daylit cells, valid pixels, 200 per cell) -> stretch_sample.npy."""
    st = Landsat1TileStore()
    rng = np.random.default_rng(seed)
    ids = np.sort(rng.choice(st.N, n, replace=False))
    t0 = time.time()
    failed = st.fetch_all(ids, desc="baseline")
    ok = [i for i in ids if i not in set(failed)]
    q = st.quirks(ok)  # rank-0 keys are cell ids
    q.to_parquet(BASELINE)
    smp = []
    for i in ok:
        if st.idx.night.iat[i]:
            continue
        b = st.bands(i).astype(np.float32)
        ch = np.stack([b[2], b[1], b[0]], -1).reshape(-1, 3)
        ch = ch[np.isfinite(ch).all(1)]
        if len(ch):
            pick = rng.choice(len(ch), min(200, len(ch)), replace=False)
            smp.append(np.sqrt(np.maximum(ch[pick], 0)))
    np.save(SAMPLE, np.concatenate(smp))
    print(json.dumps({"n": n, "fetched": len(ok), "failed": len(failed), "sec": round(time.time() - t0), **st.summary()}, indent=1))


def cmd_stretch() -> None:
    s = np.load(SAMPLE)
    lo, hi = np.percentile(s, STRETCH_PCT[0], 0), np.percentile(s, STRETCH_PCT[1], 0)
    print(f"{len(s):,} pixels (nir08, red, green, after the tone)\nSTRETCH_LO = {tuple(map(float, lo))}\nSTRETCH_HI = {tuple(map(float, hi))}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("baseline")
    p.add_argument("--n", type=int, default=2000)
    sub.add_parser("stretch")
    a = ap.parse_args()
    cmd_baseline(a.n) if a.cmd == "baseline" else cmd_stretch()
