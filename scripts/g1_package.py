"""The generation-1 path packages (notes/brief_landsat_v2_run.md, the handoff: "The path package (one per condition)").

    python scripts/g1_package.py build curious                  # runs/gen1/curious/w*/ -> paths/g1/curious/
    python scripts/g1_package.py build null
    python scripts/g1_package.py build curious --runs runs/smoke --out runs/g1/test/paths --n 60 --label TEST   # a throwaway test package

What it does, in the brief's words:
- Encounters in walk order (w000, w001, ...): each walk's start tile first (step -1; never an offer, so its interest components are
  empty), then every step. The package stops at the step where the N-th unique tile (cell, acquisition date) is reached; where it was
  cut (walk, step, clock) goes into the manifest. Every walk was run to its own end: only the package is cut.
- tiles/: N PNGs, 128 x 128, 8-bit RGB, <grid cell>_<YYYYMMDD>.png. Rendered by the walker's own code (Landsat1ClockStore.get_lowres:
  data/landsat1_store.render, three-band CIR nir08 / red / green, square-root tone, the fixed stretch, the walker's 256 px tile), then
  area-resampled (PIL BOX, exactly 2 x 2 pixels each) to 128 px, the grid eye's ground resolution (~83 m per pixel). No eye sees the
  128 px image itself. Nothing is cut or repaired: fill, stripes, saturation, cloud, night and the black green channel of 1977 stay.
- tiles.parquet: one row per unique tile: cell, date, level, night, quirk shares from the e12 detectors (the store's quirk row, from the
  raw bands and QA, the values the walks log), brightness (mean pixel of the rendered 256 px tile, e12's definition), encounters.
- encounters.parquet: one row per encounter up to the cut: walk id, step, clock, tile, wait or move, and the chosen offer's logged
  interest components (z glance, z grid, z progress, total I: the value the softmax chose by, not I_long). Null rows are filled too.
- manifest.json: condition, N, q, the walks in order (start cell, steps, end reason), the cut, the start list and its seed, the walker's
  git hash and the config hash, a SHA-256 for every file, and the render check: 20 random package tiles re-rendered from a fresh store
  (an empty cache, so fetched again from Planetary Computer) and compared byte for byte (the PNG files and the pixel arrays).

Packages are never repaired: if one fails verification, it is rebuilt from the walk logs (the run instruction, 2026-11-13).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

N_DEFAULT = 10_000
START_LIST = ROOT / "configs" / "gen1" / "start_list.csv"
START_SEED = 20261112  # data/landsat1_world.py cmd_startlist
RENDER_CHECK_N, RENDER_CHECK_SEED = 20, 20261113
PKG_PX = 128
SEEN = ("green", "red", "nir08")  # the bands of the one view (CIR nir08 / red / green)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def png_bytes(tile256: np.ndarray) -> bytes:
    """The walker's 256 px tile -> 128 px by area (BOX), as PNG bytes (deterministic for one PIL build)."""
    assert tile256.shape == (256, 256, 3) and tile256.dtype == np.uint8, (tile256.shape, tile256.dtype)
    im = Image.fromarray(tile256, "RGB").resize((PKG_PX, PKG_PX), Image.Resampling.BOX)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=False, compress_level=6)
    return buf.getvalue()


def walks_of(runs: Path, cond: str, partial: bool = False) -> list[Path]:
    """Finished walks of a condition in walk order (w000, w001, ...). A gap or an unfinished walk before a finished one is an error.
    partial (TEST packages only): running walks count too, with the steps flushed at their checkpoints (parts/)."""
    ds = sorted((runs / cond).glob("w[0-9][0-9][0-9]"))
    fin = [d for d in ds if (d / "walk.json").exists() or (partial and list((d / "parts").glob("steps_*.parquet")))]
    assert fin, f"no finished walk in {runs / cond}"
    assert [int(d.name[1:]) for d in fin] == list(range(len(fin))), f"walks not consecutive from w000: {[d.name for d in fin]}"
    return fin


def load_walk(d: Path, partial: bool) -> tuple[dict, pd.DataFrame]:
    if (d / "walk.json").exists():
        return json.loads((d / "walk.json").read_text()), pd.read_parquet(d / "steps.parquet")
    assert partial
    m = json.loads((d / "meta.json").read_text())
    s = pd.concat([pd.read_parquet(f) for f in sorted((d / "parts").glob("steps_*.parquet"))], ignore_index=True)
    c = m["clock"]
    return {"walk_id": c["walk_id"], "start_idx": c["start_idx"], "start_cell": c["start_cell"], "start_clock": c["start_clock"],
            "steps": len(s), "end_reason": "PARTIAL (running)", "time_offer_p": c["time_offer_p"], "git": m.get("git")}, s


def encounters(runs: Path, cond: str, partial: bool = False) -> tuple[pd.DataFrame, list[dict]]:
    from data.landsat1_store import image_key
    from agent import clock as CL

    rows, walks = [], []
    for d in walks_of(runs, cond, partial):
        w, s = load_walk(d, partial)
        walks.append({**w, "dir": str(d.relative_to(ROOT)) if d.is_relative_to(ROOT) else str(d)})
        start_key = int(image_key(int(w["start_idx"]), 0))
        rows.append(pd.DataFrame({"walk_id": [w["walk_id"]], "step": [-1], "clock": [w["start_clock"]], "image_key": [start_key],
                                  "tile_idx": [int(w["start_idx"])], "kind": ["start"], "wait": [False],
                                  "z_glance": [np.nan], "z_grid": [np.nan], "z_prog": [np.nan], "I": [np.nan]}))
        rows.append(pd.DataFrame({"walk_id": w["walk_id"], "step": s.step.astype(int), "clock": s.clock.astype(str), "image_key": s.image_key.astype(np.int64),
                                  "tile_idx": s.tile_idx.astype(np.int64), "kind": np.where(s.offer_kind == "time", "wait", "move"),
                                  "wait": (s.offer_kind == "time").to_numpy(), "z_glance": s.z_glance, "z_grid": s.z_grid, "z_prog": s.z_prog, "I": s.I}))
        assert CL.to_date(CL.to_day(w["start_clock"])) == w["start_clock"]
    e = pd.concat(rows, ignore_index=True)
    e["move"] = e.kind == "move"
    return e, walks


def cut(e: pd.DataFrame, n: int) -> tuple[pd.DataFrame, dict]:
    first = ~e.image_key.duplicated()
    k = np.cumsum(first.to_numpy())
    if k[-1] < n:
        raise SystemExit(f"only {k[-1]} unique tiles over all finished walks, fewer than N = {n}: no package")
    stop = int(np.flatnonzero(k == n)[0])  # the encounter at which the N-th unique tile is reached
    c = e.iloc[: stop + 1].copy()
    r = c.iloc[-1]
    return c, {"walk_id": r.walk_id, "step": int(r.step), "clock": str(r.clock), "encounter_row": stop, "encounters": len(c),
               "unique_tiles_total_all_walks": int(k[-1]), "encounters_total_all_walks": len(e)}


def tile_table(store, c: pd.DataFrame, grid_cell: np.ndarray, q: np.ndarray) -> pd.DataFrame:
    """q: the quirk rows of the keys in first-encounter order (read by render_all as each tile is rendered)."""
    from data.landsat1_store import QUIRK_COLS

    keys = c.image_key.drop_duplicates().to_numpy(np.int64)  # first-encounter order
    a = store.acquisitions(keys)
    t = pd.DataFrame({"image_key": keys, "tile_idx": a.cell.to_numpy(np.int64), "grid_cell": grid_cell[a.cell.to_numpy(np.int64)],
                      "acq_rank": a["rank"].to_numpy(), "date": pd.to_datetime(a.timestamp).dt.strftime("%Y-%m-%d").to_numpy(),
                      "timestamp": pd.to_datetime(a.timestamp).to_numpy(), "scene": a.scene.to_numpy(), "level": a.level.astype(str).to_numpy(),
                      "tier": a.tier.astype(str).to_numpy(), "night": a.night.astype(bool).to_numpy(), "sun_elevation": a.sun_elevation.to_numpy()})
    for j, col in enumerate(QUIRK_COLS):
        t[f"q_{col}"] = q[:, j]
    # the e12 summaries: per quirk, the maximum over the three bands the eye sees (analysis/e12/readouts.py)
    for qq in ("stripe", "at255", "satflag"):
        t[qq] = t[[f"q_{qq}_{b}" for b in SEEN]].max(axis=1)
    t["fill"], t["cloud"] = t.q_fill, t.q_cloud
    t["n_encounters"] = t.image_key.map(c.image_key.value_counts()).astype(int)
    t["first_walk"] = t.image_key.map(c.drop_duplicates("image_key").set_index("image_key").walk_id)
    t["first_step"] = t.image_key.map(c.drop_duplicates("image_key").set_index("image_key").step).astype(int)
    t["tile"] = t.grid_cell + "_" + t.date.str.replace("-", "")
    assert t.tile.is_unique, "two unique tiles with one name"
    return t


def render_all(store, keys: np.ndarray) -> tuple[list[bytes], np.ndarray, np.ndarray]:
    """PNG bytes, brightness (mean pixel of the 256 px tile) and the quirk row of every key; the quirk row is read right after the
    tile (the store keeps it in memory once it has read the tile)."""
    failed = store.fetch_all([int(k) for k in keys], desc="package tiles")
    if failed:
        print(f"[package] {len(failed)} tiles failed to prefetch; fetched again one by one", flush=True)
    pngs, bright, q = [], np.empty(len(keys)), []
    for i, k in enumerate(keys):
        a = store.get_lowres(int(k))
        bright[i] = float(a.mean())
        pngs.append(png_bytes(a))
        q.append(store.quirk_row(int(k)))
        assert np.isfinite(q[-1][0]), f"no quirk row for {k}"
        if (i + 1) % 1000 == 0:
            print(f"[package] rendered {i + 1:,} / {len(keys):,}", flush=True)
    return pngs, bright, np.stack(q)


def render_check(t: pd.DataFrame, tiles_dir: Path) -> dict:
    """20 random package tiles re-rendered from a fresh store (an empty cache: fetched again from Planetary Computer, scene
    metadata too), compared byte for byte with the package's PNG files, and as pixel arrays."""
    from data.landsat1_store import Landsat1ClockStore

    rng = np.random.default_rng(RENDER_CHECK_SEED)
    pick = np.sort(rng.choice(len(t), min(RENDER_CHECK_N, len(t)), replace=False))
    tmp = Path(tempfile.mkdtemp(prefix="g1_render_check_"))
    out = []
    try:
        fresh = Landsat1ClockStore(cache_dir=tmp)
        for i in pick:
            k, name = int(t.image_key.iloc[i]), t.tile.iloc[i]
            b = png_bytes(fresh.get_lowres(k))
            f = (tiles_dir / f"{name}.png").read_bytes()
            px = np.array_equal(np.asarray(Image.open(io.BytesIO(b))), np.asarray(Image.open(io.BytesIO(f))))
            out.append({"tile": name, "image_key": k, "bytes_equal": b == f, "pixels_equal": bool(px)})
        n_remote = int(fresh.stats.get("remote", 0))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    ok = all(o["bytes_equal"] and o["pixels_equal"] for o in out)
    return {"passed": bool(ok), "n": len(out), "seed": RENDER_CHECK_SEED, "fetched_remote": n_remote,
            "method": "re-rendered from a fresh Landsat1ClockStore with an empty cache (fetched again from Planetary Computer), "
                      "get_lowres -> BOX 128 px -> PNG; compared with the package file byte for byte and as pixels",
            "device": "the PC (Windows), generation 1 (run instruction 2026-11-13: the render check runs here, before freezing)",
            "tiles": out}


def build(cond: str, runs: Path, out_root: Path, n: int, label: str | None, partial: bool = False) -> Path:
    from data.landsat1_store import Landsat1ClockStore

    t0 = time.time()
    out = out_root / cond
    if out.exists():
        shutil.rmtree(out)  # never repaired: rebuilt whole from the walk logs
    out.mkdir(parents=True)
    assert not partial or label == "TEST", "partial walks only make TEST packages"
    e, walks = encounters(runs, cond, partial)
    c, cut_info = cut(e, n)
    store = Landsat1ClockStore()
    grid_cell = store.idx.grid_cell.to_numpy()
    c.insert(3, "grid_cell", grid_cell[c.tile_idx.to_numpy()])
    keys = c.image_key.drop_duplicates().to_numpy(np.int64)
    pngs, bright, q = render_all(store, keys)
    t = tile_table(store, c, grid_cell, q)
    c = c.merge(t[["image_key", "tile", "date"]].rename(columns={"date": "tile_date"}), on="image_key", how="left", validate="many_to_one")
    assert c.tile.notna().all()
    t["brightness"] = bright
    (out / "tiles").mkdir()
    for name, b in zip(t.tile.to_numpy(), pngs):
        (out / "tiles" / f"{name}.png").write_bytes(b)
    assert len(t) == n and len(list((out / "tiles").glob("*.png"))) == n
    t.to_parquet(out / "tiles.parquet")
    c.to_parquet(out / "encounters.parquet")
    rc = render_check(t, out / "tiles")
    cfg = ROOT / "configs" / "gen1" / f"{cond}.yaml"
    files = sorted(p for p in out.rglob("*") if p.is_file())
    man = {
        "label": label or "generation 1",
        "condition": cond, "N": n, "q": float(walks[0].get("time_offer_p")),
        "walks": [{k: w.get(k) for k in ("walk_id", "start_idx", "start_cell", "start_clock", "end_clock", "steps", "end_reason", "unique_tiles",
                                          "unique_cells", "waits", "linger_entry_step", "linger_steps", "seconds", "git", "dir")} for w in walks],
        "cut": cut_info,
        "start_list": {"path": "configs/gen1/start_list.csv", "seed": START_SEED, "sha256": sha256(START_LIST),
                       "first_rows": pd.read_csv(START_LIST).head(len(walks)).grid_cell.tolist()},
        "walker": {"git": sorted({w.get("git") for w in walks}), "config": f"configs/gen1/{cond}.yaml", "config_sha256": sha256(cfg)},
        "rendering": {"source": "data/landsat1_store.Landsat1ClockStore.get_lowres (render: CIR nir08/red/green, sqrt tone, fixed stretch, 256 px)",
                      "resample": "PIL BOX 256 -> 128 px (area, 2 x 2)", "png": "PIL, compress_level 6", "pil": Image.__version__},
        "interest_columns": "encounters.parquet z_glance, z_grid, z_prog, I (the chosen offer's interest as the softmax used it; not I_long); start rows empty",
        "render_check": rc,
        "built": time.strftime("%Y-%m-%d %H:%M:%S"), "build_seconds": round(time.time() - t0, 1),
        "files": {str(p.relative_to(out)).replace("\\", "/"): sha256(p) for p in files},
    }
    (out / "manifest.json").write_text(json.dumps(man, indent=1, default=str))
    print(f"[package] {cond}: {n:,} tiles, {len(c):,} encounters, cut at {cut_info['walk_id']} step {cut_info['step']} (clock {cut_info['clock']}); "
          f"render check {'passed' if rc['passed'] else 'FAILED'} ({rc['n']} tiles); {time.time() - t0:.0f} s -> {out}", flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build"])
    ap.add_argument("cond", choices=["curious", "null"])
    ap.add_argument("--runs", default=str(ROOT / "runs" / "gen1"))
    ap.add_argument("--out", default=str(ROOT / "paths" / "g1"))
    ap.add_argument("--n", type=int, default=N_DEFAULT)
    ap.add_argument("--label")
    ap.add_argument("--partial", action="store_true", help="TEST packages only: include running walks' checkpointed steps")
    a = ap.parse_args()
    build(a.cond, Path(a.runs), Path(a.out), a.n, a.label, a.partial)


if __name__ == "__main__":
    main()
