"""Dreams v3 GAN data: 256x256 crops at native 10 m from the agent's path (weighted) and from a global base sample.

    python -m gen.v3_datasets agent runs/global_baseline_s0            # data/v3/global_baseline_s0/agent_path{/,.zip}
    python -m gen.v3_datasets base  runs/global_baseline_s0            # data/v3/base_global{/,.zip}, excluding that path
    python -m gen.v3_datasets agent runs/global_baseline_s0 --crop_sampling heatmap

agent_path: every unique visited tile, round(16 * w_i) crops with w_i the v1 tile weight (gen/build_sets.tile_weights,
alpha_s = 1, alpha_b = 0.5, clipped to [0.2, 5] -> 3..80 crops). Repetition is how the weighting reaches StyleGAN.
base_global: 4,000 tiles drawn uniformly from the whole filtered global index minus every tile on the agent's path,
16 crops each. Same RGB source as the walker (the archive thumbnail at 10 m; see data/tile_store.py).

Crop positions are random; a horizontal flip (p = 0.5) and a 90-degree rotation (k uniform in 0..3) are baked in.
Crops with > 5 % no-data pixels (all channels 0) are redrawn up to 20 times, then skipped (counted).
`--crop_sampling heatmap` draws positions in proportion to the learning progress inside each crop, from
runs/<run>/lp_maps/<tile_idx>.npy (any 2-D map over the tile); tiles without a map fall back to uniform (counted).

Writes, per dataset: png/<crop_id:08d>.png (temporary), <name>.zip via third_party/stylegan3/dataset_tool.py,
crops.parquet (crop_id -> tile, lat, lon, x, y, flip, rot), small64.npy (uint8 [M, 64, 64, 3], 4x area-downsampled
crops for the nearest-neighbour searches), tiles.parquet, info.json, and for the base a world map of its tiles.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from gen.build_sets import tile_weights

ROOT = Path(__file__).resolve().parents[1]
V3 = ROOT / "data" / "v3"
SG = ROOT / "third_party" / "stylegan3"
SG_PY = ROOT / ".venv-sg" / "Scripts" / "python.exe"
PX, BASE_TILES, BASE_CROPS, MAX_NODATA, TRIES = 256, 4000, 16, 0.05, 20


def crop_positions(H: int, W: int, n: int, rng: np.random.Generator, heat: np.ndarray | None) -> tuple[np.ndarray, np.ndarray]:
    if heat is None:
        return rng.integers(0, H - PX + 1, n), rng.integers(0, W - PX + 1, n)
    # integral of the map over every PX window, resampled to tile pixels -> sampling distribution over top-left corners
    hm = np.asarray(Image.fromarray(heat.astype(np.float32)).resize((W, H), Image.Resampling.BILINEAR), dtype=np.float64)
    hm = np.clip(hm, 0, None)
    ii = np.pad(hm.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    win = ii[PX:, PX:] - ii[:-PX, PX:] - ii[PX:, :-PX] + ii[:-PX, :-PX]
    p = win.ravel() + 1e-12
    k = rng.choice(len(p), size=n, p=p / p.sum())
    return k // win.shape[1], k % win.shape[1]


def export(name: str, tiles: pd.DataFrame, out: Path, seed: int, sampling: str, lp_dir: Path | None) -> dict:
    from data.tile_store import TileStore
    from tqdm import tqdm

    store = TileStore()
    failed = store.fetch_all(tiles.tile_idx, desc=f"{name} tiles")
    if failed:
        print(f"[v3data] {len(failed)} tiles could not be fetched and are skipped: {failed[:10]}")
        tiles = tiles[~tiles.tile_idx.isin(failed)]
    png = out / "png"
    shutil.rmtree(png, ignore_errors=True)
    png.mkdir(parents=True)
    rng = np.random.default_rng(seed)
    rows, small, n_skip, n_redraw, n_heat_missing = [], [], 0, 0, 0
    lat, lon = store.idx.lat.to_numpy(), store.idx.lon.to_numpy()
    cid = 0
    for r in tqdm(tiles.itertuples(index=False), total=len(tiles), desc=f"{name} crops"):
        t = int(r.tile_idx)
        img = store.get_hires(t)
        H, W = img.shape[:2]
        heat = None
        if sampling == "heatmap":
            p = lp_dir / f"{t}.npy" if lp_dir else None
            if p is not None and p.exists():
                heat = np.load(p)
            else:
                n_heat_missing += 1
        n = int(r.n_crops)
        ys, xs = crop_positions(H, W, n * TRIES, rng, heat)
        k = 0
        for c in range(n):
            ok = False
            while k < len(ys):
                y, x = int(ys[k]), int(xs[k])
                k += 1
                a = img[y : y + PX, x : x + PX]
                if (a.max(axis=2) == 0).mean() <= MAX_NODATA:
                    ok = True
                    break
                n_redraw += 1
            if not ok:
                n_skip += 1
                continue
            flip, rot = bool(rng.random() < 0.5), int(rng.integers(4))
            if flip:
                a = a[:, ::-1]
            a = np.ascontiguousarray(np.rot90(a, rot))
            Image.fromarray(a).save(png / f"{cid:08d}.png", compress_level=1)
            small.append(np.asarray(Image.fromarray(a).resize((64, 64), Image.Resampling.BOX)))
            rows.append({"crop_id": cid, "tile_idx": t, "lat": lat[t], "lon": lon[t], "y": y, "x": x, "flip": flip, "rot": rot, "weight": float(r.weight)})
            cid += 1
    crops = pd.DataFrame(rows)
    crops.to_parquet(out / "crops.parquet")
    np.save(out / "small64.npy", np.stack(small))
    tiles.to_parquet(out / "tiles.parquet")

    zp = out / f"{name}.zip"
    zp.unlink(missing_ok=True)
    cmd = [str(SG_PY), str(SG / "dataset_tool.py"), f"--source={png}", f"--dest={zp}", f"--resolution={PX}x{PX}"]
    subprocess.run(cmd, check=True, cwd=SG)
    shutil.rmtree(png)
    info = {
        "dataset": name, "n_tiles": int(tiles.tile_idx.nunique()), "n_crops": len(crops), "crop_px": PX, "metres_per_px": 10,
        "crops_per_tile_min": int(crops.groupby("tile_idx").size().min()), "crops_per_tile_max": int(crops.groupby("tile_idx").size().max()),
        "skipped_nodata": n_skip, "redrawn_nodata": n_redraw, "fetch_failed": len(failed), "crop_sampling": sampling,
        "heatmap_missing_tiles": n_heat_missing if sampling == "heatmap" else None, "seed": seed, "zip": str(zp.relative_to(ROOT)),
    }
    (out / "info.json").write_text(json.dumps(info, indent=2))
    print(json.dumps(info, indent=2))
    return info


def agent(run: Path, seed: int, sampling: str) -> None:
    tw, n_tv = tile_weights(pd.read_parquet(run / "steps.parquet"))
    tw["n_crops"] = np.round(16 * tw.weight).astype(int)
    out = V3 / run.name / "agent_path"
    out.mkdir(parents=True, exist_ok=True)
    info = export("agent_path", tw, out, seed, sampling, run / "lp_maps")
    info.update(run=run.name, weight_mean=float(tw.weight.mean()), effective_n=float(tw.weight.sum() ** 2 / (tw.weight**2).sum()))
    (out / "info.json").write_text(json.dumps(info, indent=2))


def base(run: Path, seed: int) -> None:
    from data.global_index import world_axes

    idx = pd.read_parquet(ROOT / "data" / "global" / "index.parquet", columns=["idx", "lat", "lon", "cover"])
    path = np.unique(pd.read_parquet(run / "steps.parquet").tile_idx.to_numpy())
    pool = np.setdiff1d(idx.idx.to_numpy(), path)
    ids = np.sort(np.random.default_rng(seed).choice(pool, BASE_TILES, replace=False))
    tiles = pd.DataFrame({"tile_idx": ids, "weight": 1.0, "n_crops": BASE_CROPS})
    out = V3 / "base_global"
    out.mkdir(parents=True, exist_ok=True)
    info = export("base_global", tiles, out, seed, "uniform", None)
    sel = idx.set_index("idx").loc[tiles.tile_idx]
    info.update(excluded_run=run.name, n_excluded_path_tiles=int(len(path)), cover_share=sel.cover.value_counts(normalize=True).round(4).to_dict())
    (out / "info.json").write_text(json.dumps(info, indent=2))

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(16, 8.5))
    world_axes(ax, f"base_global: {len(sel):,} tiles drawn uniformly from the filtered global index (minus {len(path):,} tiles on {run.name}'s path)")
    col = {"land": "#2f6b3a", "coast": "#d08a1e", "ocean": "#1f5fbf"}
    for k, c in col.items():
        s = sel[sel.cover == k]
        ax.scatter(s.lon, s.lat, s=4, c=c, lw=0, label=f"{k} ({len(s):,})")
    ax.legend(loc="lower left", fontsize=8, markerscale=3)
    fig.tight_layout()
    fig.savefig(out / "map_base_global.png", dpi=130)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("which", choices=["agent", "base"])
    ap.add_argument("run", type=Path)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--crop_sampling", choices=["uniform", "heatmap"], default="uniform")
    a = ap.parse_args()
    if a.which == "agent":
        agent(a.run, a.seed, a.crop_sampling)
    else:
        base(a.run, a.seed)
    sys.exit(0)
