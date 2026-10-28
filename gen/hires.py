"""Dreams v2 data: native-10 m tiles for the training sets, and fixed crop banks.

    python -m gen.hires data/sets/baseline_s0                 # hires cache + 64 px banks (10 m and 40 m)
    python -m gen.hires data/sets/baseline_s0 --px 128        # Step B bank

RGB source: the cached Major TOM `thumbnail` PNGs are the full 1068x1068 B04/B03/B02 grid at
10 m under the archive's one fixed (roughly square-root) scale, which is exactly the "global
stretch" v1 used (v1 box-downsampled them to 256 px). Checked on tile 300 against freshly
fetched bands: byte-identical to the archive's thumbnail column, r = 0.99 with sqrt(band),
same adjacent-pixel detail as B04. So data/hires/<tile_idx>.npy is that PNG as uint8, and the
only change from v1 is metres per pixel.

Banks: 64 random crops per tile, positions seeded by (tile_idx, px), so every set that contains
a tile gets the identical crops. Crops with > 5 % no-data (all-zero pixels) are dropped.
Flips and 90-degree rotations are applied at training time.

Writes data/hires/<tile_idx>.npy, data/crops/<res>_<px>.npz (crops uint8 [M,px,px,3], tile_idx [M]).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
THUMBS = ROOT / "data" / "raw" / "majortom_thumbs" / "thumbs"
HIRES = ROOT / "data" / "hires"
CROPS = ROOT / "data" / "crops"
N_CROPS = 64
MAX_NODATA = 0.05


def hires_tile(r) -> np.ndarray:
    p = HIRES / f"{r.idx}.npy"
    if p.exists():
        return np.load(p)
    ts = pd.Timestamp(r.timestamp).strftime("%Y%m%dT%H%M%S")
    a = np.asarray(Image.open(THUMBS / f"{r.grid_cell}_{ts}.png").convert("RGB"))
    np.save(p, a)
    return a


def bank(tiles: dict[int, np.ndarray], px: int, res: str) -> dict:
    crops, tids, dropped = [], [], 0
    for t, img in tiles.items():
        H = img.shape[0]
        rng = np.random.default_rng([t, px])
        oy = rng.integers(0, H - px + 1, N_CROPS)
        ox = rng.integers(0, H - px + 1, N_CROPS)
        for y, x in zip(oy, ox):
            c = img[y : y + px, x : x + px]
            if (c.max(axis=2) == 0).mean() > MAX_NODATA:
                dropped += 1
                continue
            crops.append(c)
            tids.append(t)
    out = CROPS / f"{res}_{px}.npz"
    np.savez(out, crops=np.stack(crops), tile_idx=np.array(tids, dtype=np.int64))
    info = {"bank": out.name, "tiles": len(tiles), "crops": len(crops), "dropped_nodata": dropped}
    print(f"[hires] {info}")
    return info


def main(sets_dir: Path, px: int) -> None:
    sets = pd.read_parquet(sets_dir / "sets.parquet")
    idx = pd.read_parquet(ROOT / "data" / "tiles.parquet")
    ids = np.unique(sets.tile_idx.to_numpy())
    HIRES.mkdir(parents=True, exist_ok=True)
    CROPS.mkdir(parents=True, exist_ok=True)
    hi = {int(t): hires_tile(idx.iloc[t]) for t in ids}
    infos = [bank(hi, px, "10m")]
    if px == 64:  # v1-resolution bank of the same shape, for nn_train_dist of the 40 m models
        lo = np.load(ROOT / "data" / "tiles.npy", mmap_mode="r")
        infos.append(bank({int(t): np.asarray(lo[t]) for t in ids}, px, "40m"))
    (CROPS / f"info_{px}.json").write_text(json.dumps({"sets": str(sets_dir), "n_tiles": int(len(ids)), "banks": infos}, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("sets_dir", type=Path)
    ap.add_argument("--px", type=int, default=64)
    a = ap.parse_args()
    main(a.sets_dir, a.px)
