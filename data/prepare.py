"""Session 1: subset Major TOM Core-S2L2A, fetch RGB thumbnails, cache 256 px tiles, neighbours.

    python data/prepare.py            # fetch (cached), build tiles.npy / tiles.parquet / neighbours
    python data/prepare.py --check    # also draw notes/img/prepare_check.png

Choices (see notes/expectations.md for why):
- Region: Northern Italy, lat 43.5-47.0, lon 6.5-12.6 (~1,850 cells on the 10 km grid):
  Alps, Po valley farmland, Milan/Turin, the lakes, Ligurian + Adriatic coast, Apennine forest.
- Major TOM Core keeps one product per cell and caps cloud cover at 25 %, so the brief's
  "keep tiles up to 60-70 % cloud" is moot: we keep everything up to 65 % (= all of it).
  Real clouds are rare here (~90 cells > 10 %), so we add a flagged synthetic "noisy TV":
  a cluster of cells whose content is fresh random noise every time the agent looks.
  The agent generates that noise itself (agent/walk.py); tiles.npy holds one realisation
  for display only.
- RGB comes from the archive's `thumbnail` column, a fixed-scale B04/B03/B02 composite
  (same scale for every tile, so brightness stays comparable; no per-tile stretch).
"""

from __future__ import annotations

import argparse
import io
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw" / "majortom_thumbs"
META = RAW / "metadata.parquet"
THUMBS = RAW / "thumbs"
TILES_NPY = ROOT / "tiles.npy"
TILES_PQ = ROOT / "tiles.parquet"
NEIGH_NPZ = ROOT / "neighbours_15km.npz"

BBOX = dict(lat_min=43.5, lat_max=47.0, lon_min=6.5, lon_max=12.6)
MAX_CLOUD = 65.0      # percent; moot, Major TOM Core caps at 25
MAX_NODATA = 0.10     # fraction
TILE_PX = 256
TV_CENTRE = (45.40, 8.55)   # Po plain west of Milan (Novara), ~50 km from the default start
TV_RADIUS_KM = 16.0         # ~10 cells
EARTH_R_KM = 6371.0088


def load_subset() -> pd.DataFrame:
    if not META.exists():
        from huggingface_hub import hf_hub_download

        hf_hub_download("Major-TOM/Core-S2L2A", "metadata.parquet", repo_type="dataset", local_dir=str(RAW))
    cols = ["grid_cell", "product_id", "timestamp", "cloud_cover", "nodata", "centre_lat", "centre_lon", "parquet_url", "parquet_row"]
    m = pd.read_parquet(META, columns=cols)
    s = m[m.centre_lat.between(BBOX["lat_min"], BBOX["lat_max"]) & m.centre_lon.between(BBOX["lon_min"], BBOX["lon_max"])]
    n_box = len(s)
    s = s[(s.cloud_cover <= MAX_CLOUD) & (s.nodata <= MAX_NODATA)]
    # a handful of cells have two products; keep the earliest so one cell = one tile
    s = s.sort_values(["grid_cell", "timestamp"]).drop_duplicates("grid_cell", keep="first")
    s = s.sort_values(["centre_lat", "centre_lon"], ascending=[False, True]).reset_index(drop=True)
    print(f"[prepare] bbox rows {n_box} -> {len(s)} tiles (cloud <= {MAX_CLOUD}%, nodata <= {MAX_NODATA})")
    return s


def thumb_path(r) -> Path:
    return THUMBS / f"{r.grid_cell}_{r.timestamp}.png"


def fetch_file(url: str, rows: list) -> int:
    """Read the thumbnail column for some row groups of one remote parquet file."""
    import fsspec
    import pyarrow.parquet as pq

    fs = fsspec.filesystem("https")
    with fs.open(url, "rb", block_size=1 << 20, cache_type="none") as f:
        pf = pq.ParquetFile(f)
        for r in rows:
            tbl = pf.read_row_group(int(r.parquet_row), columns=["thumbnail", "grid_cell"])
            row = tbl.to_pylist()[0]
            if row["grid_cell"] != r.grid_cell:
                raise RuntimeError(f"row mismatch {r.grid_cell} vs {row['grid_cell']}")
            tmp = thumb_path(r).with_suffix(".part")
            tmp.write_bytes(row["thumbnail"])
            tmp.replace(thumb_path(r))
    return len(rows)


def fetch(s: pd.DataFrame, workers: int = 12) -> None:
    from tqdm import tqdm

    THUMBS.mkdir(parents=True, exist_ok=True)
    missing = [r for r in s.itertuples(index=False) if not thumb_path(r).exists()]
    if not missing:
        return
    by_url: dict[str, list] = {}
    for r in missing:
        by_url.setdefault(r.parquet_url, []).append(r)
    print(f"[prepare] fetching {len(missing)} thumbnails from {len(by_url)} parquet files")
    errors = []
    with ThreadPoolExecutor(max_workers=workers) as ex, tqdm(total=len(missing), desc="thumbnails") as bar:
        futs = {ex.submit(fetch_file, u, rs): u for u, rs in by_url.items()}
        for fut in as_completed(futs):
            try:
                bar.update(fut.result())
            except Exception as e:  # noqa: BLE001
                errors.append(f"{futs[fut]}: {e}")
    if errors:
        raise RuntimeError(f"{len(errors)} files failed (rerun to resume): {errors[:2]}")


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_R_KM * np.arcsin(np.sqrt(a))


def neighbours(lat: np.ndarray, lon: np.ndarray, radius_km: float) -> list[np.ndarray]:
    """Haversine BallTree radius query; excludes the tile itself. Used by the walk too."""
    from sklearn.neighbors import BallTree

    X = np.radians(np.stack([lat, lon], 1))
    tree = BallTree(X, metric="haversine")
    ind = tree.query_radius(X, r=radius_km / EARTH_R_KM)
    return [np.sort(nb[nb != i]).astype(np.int32) for i, nb in enumerate(ind)]


def tv_noise(rng: np.random.Generator, n: int = 1) -> np.ndarray:
    """One display realisation of the noisy TV: uniform RGB noise in 4x4 px blocks (~160 m)."""
    small = rng.integers(0, 256, size=(n, TILE_PX // 4, TILE_PX // 4, 3), dtype=np.uint8)
    return small.repeat(4, axis=1).repeat(4, axis=2)


def build(s: pd.DataFrame) -> None:
    from tqdm import tqdm

    n = len(s)
    tiles = np.lib.format.open_memmap(TILES_NPY, mode="w+", dtype=np.uint8, shape=(n, TILE_PX, TILE_PX, 3))
    black = np.zeros(n)
    for i, r in enumerate(tqdm(s.itertuples(index=False), total=n, desc="resize")):
        img = Image.open(thumb_path(r)).convert("RGB")
        # BOX = area averaging (1068 -> 256, ~41.7 m/px)
        a = np.asarray(img.resize((TILE_PX, TILE_PX), Image.Resampling.BOX))
        tiles[i] = a
        black[i] = float((a.max(axis=2) == 0).mean())
    d_tv = haversine_km(s.centre_lat.to_numpy(), s.centre_lon.to_numpy(), *TV_CENTRE)
    tv = d_tv <= TV_RADIUS_KM
    tiles[tv] = tv_noise(np.random.default_rng(0), int(tv.sum()))
    tiles.flush()
    idx = pd.DataFrame(
        {
            "idx": np.arange(n),
            "grid_cell": s.grid_cell.to_numpy(),
            "lat": s.centre_lat.to_numpy(),
            "lon": s.centre_lon.to_numpy(),
            "cloud_cover": s.cloud_cover.to_numpy(),
            "timestamp": pd.to_datetime(s.timestamp, format="%Y%m%dT%H%M%S").to_numpy(),
            "nodata": s.nodata.to_numpy(),
            "black_frac": black,
            "tv": tv,
            "product_id": s.product_id.to_numpy(),
        }
    )
    idx.to_parquet(TILES_PQ)
    nb = neighbours(idx.lat.to_numpy(), idx.lon.to_numpy(), 15.0)
    counts = np.array([len(x) for x in nb])
    np.savez(NEIGH_NPZ, indptr=np.concatenate([[0], np.cumsum(counts)]), indices=np.concatenate(nb))
    print(f"[prepare] {n} tiles -> {TILES_NPY.name} ({tiles.nbytes / 1e6:.0f} MB); noisy TV tiles: {int(tv.sum())}")
    print(f"[prepare] neighbours at 15 km: mean {counts.mean():.2f}, min {counts.min()}, max {counts.max()}, isolated {(counts == 0).sum()}")


def check(probe_latlon=(45.46, 9.19)) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    idx = pd.read_parquet(TILES_PQ)
    tiles = np.load(TILES_NPY, mmap_mode="r")
    z = np.load(NEIGH_NPZ)
    i0 = int(np.argmin(haversine_km(idx.lat.to_numpy(), idx.lon.to_numpy(), *probe_latlon)))
    nb = z["indices"][z["indptr"][i0] : z["indptr"][i0 + 1]]

    fig = plt.figure(figsize=(16, 8))
    ax = fig.add_subplot(1, 2, 1)
    # every tile as its own thumbnail, placed at its centre: a mosaic of the region
    small = 0.05
    for i in range(0, len(idx)):
        la, lo = idx.lat[i], idx.lon[i]
        w = small / np.cos(np.radians(la)) * 1.4
        ax.imshow(tiles[i, ::8, ::8], extent=(lo - w, lo + w, la - small * 1.0, la + small * 1.0), interpolation="nearest")
    ax.scatter(idx.lon[nb], idx.lat[nb], s=30, facecolors="none", edgecolors="red", lw=1)
    ax.scatter(idx.lon[i0], idx.lat[i0], s=60, c="yellow", edgecolors="k", zorder=5)
    tv = idx.tv.to_numpy()
    ax.scatter(idx.lon[tv], idx.lat[tv], s=8, c="magenta", marker="x")
    ax.set_xlim(BBOX["lon_min"] - 0.1, BBOX["lon_max"] + 0.1)
    ax.set_ylim(BBOX["lat_min"] - 0.1, BBOX["lat_max"] + 0.1)
    ax.set_aspect(1 / np.cos(np.radians(45.3)))
    ax.set_title(f"{len(idx)} tiles; yellow = tile {i0} ({idx.grid_cell[i0]}), red = its {len(nb)} neighbours <= 15 km, magenta x = noisy TV")

    # 3x3-ish layout of the probe tile and its neighbours by relative position
    ax2 = fig.add_subplot(1, 2, 2)
    for j in [i0, *nb]:
        dx = (idx.lon[j] - idx.lon[i0]) * np.cos(np.radians(idx.lat[i0])) * 111.32
        dy = (idx.lat[j] - idx.lat[i0]) * 110.57
        ax2.imshow(tiles[j], extent=(dx - 5.3, dx + 5.3, dy - 5.3, dy + 5.3))
        ax2.text(dx - 5, dy + 4, f"{j}", color="yellow" if j == i0 else "white", fontsize=8)
    ax2.set_xlim(-22, 22)
    ax2.set_ylim(-22, 22)
    ax2.set_title("probe tile and neighbours placed by haversine offset (km); edges should continue")
    out = ROOT.parent / "notes" / "img" / "prepare_check.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    print(f"[prepare] wrote {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    s = load_subset()
    fetch(s, a.workers)
    build(s)
    if a.check:
        check()
    sys.exit(0)
