"""Dreams v3 world: the whole of Major TOM Core-S2L2A as one filtered index + one haversine BallTree.

    python data/global_index.py            # data/global/index.parquet, coverage.json, notes/dreams_v3/world_coverage.png

Same filters as v1 (no-data <= 10 %, cloud cover <= 70 %; Core itself caps cloud at 25 %), and the
same one-cell-one-tile rule (earliest product per grid cell). Tile indices into this file are the
global tile ids used by the walks, the tile store and the GAN datasets.

Coverage classes come from a coarse 1 km land mask (global-land-mask, GLOBE) sampled on a 5x5 grid
over each ~10.7 km tile: all land -> land, all water -> ocean, mixed -> coast. Reporting only; the
walker never sees it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from prepare import BBOX, EARTH_R_KM, MAX_NODATA, META  # noqa: E402

OUT = ROOT / "global"
INDEX_PQ = OUT / "index.parquet"
MAX_CLOUD = 70.0
COLS = ["grid_cell", "product_id", "timestamp", "cloud_cover", "nodata", "centre_lat", "centre_lon", "parquet_url", "parquet_row"]
HALF_KM = 5.0


def build_index() -> pd.DataFrame:
    m = pd.read_parquet(META, columns=COLS)
    n_all = len(m)
    m = m[(m.cloud_cover <= MAX_CLOUD) & (m.nodata <= MAX_NODATA)]
    n_filt = len(m)
    m = m.sort_values(["grid_cell", "timestamp"]).drop_duplicates("grid_cell", keep="first")
    m = m.sort_values(["centre_lat", "centre_lon"], ascending=[False, True]).reset_index(drop=True)
    idx = pd.DataFrame(
        {
            "idx": np.arange(len(m), dtype=np.int64),
            "grid_cell": m.grid_cell.to_numpy(),
            "lat": m.centre_lat.to_numpy(),
            "lon": m.centre_lon.to_numpy(),
            "timestamp": pd.to_datetime(m.timestamp, format="%Y%m%dT%H%M%S").to_numpy(),
            "cloud_cover": m.cloud_cover.to_numpy(),
            "nodata": m.nodata.to_numpy(),
            "product_id": m.product_id.to_numpy(),
            "parquet_url": m.parquet_url.to_numpy(),
            "parquet_row": m.parquet_row.to_numpy().astype(np.int32),
        }
    )
    idx["cover"] = cover_class(idx.lat.to_numpy(), idx.lon.to_numpy())
    idx["regional"] = idx.lat.between(BBOX["lat_min"], BBOX["lat_max"]) & idx.lon.between(BBOX["lon_min"], BBOX["lon_max"])
    idx.attrs.update(n_all=n_all, n_filtered=n_filt)
    print(f"[global] metadata rows {n_all} -> filtered {n_filt} -> one per cell {len(idx)}")
    return idx


def cover_class(lat: np.ndarray, lon: np.ndarray, chunk: int = 200_000) -> np.ndarray:
    from global_land_mask import globe

    off = np.linspace(-HALF_KM, HALF_KM, 5)
    dy, dx = np.meshgrid(off, off, indexing="ij")
    dy, dx = dy.ravel() / 110.57, dx.ravel()
    out = np.empty(len(lat), dtype=object)
    for s in range(0, len(lat), chunk):
        la, lo = lat[s : s + chunk, None], lon[s : s + chunk, None]
        pla = np.clip(la + dy, -89.99, 89.99)
        plo = (lo + dx / (111.32 * np.cos(np.radians(la))) + 180.0) % 360.0 - 180.0
        frac = globe.is_land(pla.ravel(), plo.ravel()).reshape(pla.shape).mean(1)
        out[s : s + chunk] = np.where(frac == 1.0, "land", np.where(frac == 0.0, "ocean", "coast"))
    return out


def ball_tree(lat: np.ndarray, lon: np.ndarray):
    from sklearn.neighbors import BallTree

    return BallTree(np.radians(np.stack([lat, lon], 1)), metric="haversine")


def load_index() -> pd.DataFrame:
    return pd.read_parquet(INDEX_PQ)


def world_axes(ax, title: str = "") -> None:
    """Equirectangular world with a light land background from the same coarse mask."""
    from global_land_mask import globe

    la = np.arange(89.75, -90, -0.5)
    lo = np.arange(-179.75, 180, 0.5)
    LO, LA = np.meshgrid(lo, la)
    land = globe.is_land(LA, LO)
    ax.imshow(np.where(land, 0.86, 0.97), cmap="gray", vmin=0, vmax=1, extent=(-180, 180, -90, 90), interpolation="nearest")
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.set_aspect("equal")
    ax.set_xticks(range(-180, 181, 60))
    ax.set_yticks(range(-90, 91, 30))
    ax.tick_params(labelsize=7)
    if title:
        ax.set_title(title, fontsize=10)


def report(idx: pd.DataFrame) -> dict:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    share = idx.cover.value_counts(normalize=True).round(4).to_dict()
    counts = idx.cover.value_counts().to_dict()
    cov = {
        "n_metadata_rows": int(idx.attrs.get("n_all", 0)),
        "n_after_filters": int(idx.attrs.get("n_filtered", 0)),
        "n_tiles": len(idx),
        "n_regional_dev_subset": int(idx.regional.sum()),
        "cover_counts": {k: int(v) for k, v in counts.items()},
        "cover_share": share,
        "lat_range": [float(idx.lat.min()), float(idx.lat.max())],
        "area_km2_approx": round(len(idx) * 10.68**2),
        "filters": {"nodata_max": MAX_NODATA, "cloud_cover_max": MAX_CLOUD, "one_product_per_cell": "earliest"},
        "land_mask": "global-land-mask (GLOBE 1 km), 5x5 samples per tile",
    }
    (OUT / "coverage.json").write_text(json.dumps(cov, indent=2))

    fig, ax = plt.subplots(figsize=(16, 8.5))
    world_axes(ax, f"Major TOM Core-S2L2A after filters: {len(idx):,} tiles  "
                   f"(land {share.get('land', 0):.1%}, coast {share.get('coast', 0):.1%}, open ocean {share.get('ocean', 0):.1%})")
    # 0.25 deg raster: each bin takes the colour of its most common class
    col = {"land": (0.18, 0.42, 0.23), "coast": (0.82, 0.54, 0.12), "ocean": (0.12, 0.37, 0.75)}
    bins = [np.arange(-180, 180.01, 0.25), np.arange(-90, 90.01, 0.25)]
    H = np.stack([np.histogram2d(idx.lon[idx.cover == k], idx.lat[idx.cover == k], bins=bins)[0] for k in col])
    rgba = np.zeros(H.shape[1:] + (4,))
    rgba[..., :3] = np.array(list(col.values()))[H.argmax(0)]
    rgba[..., 3] = (H.sum(0) > 0) * 0.9
    ax.imshow(rgba.transpose(1, 0, 2)[::-1], extent=(-180, 180, -90, 90), interpolation="nearest")
    for k, c in col.items():
        ax.scatter([], [], c=[c], s=30, marker="s", label=f"{k} ({int((idx.cover == k).sum()):,})")
    ax.legend(loc="lower left", fontsize=8)
    out = ROOT.parent / "notes" / "dreams_v3" / "world_coverage.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    print(f"[global] coverage {json.dumps(cov['cover_share'])} -> {out}")
    return cov


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    idx = build_index()
    idx.to_parquet(INDEX_PQ)
    cov = report(idx)
    print(json.dumps(cov, indent=2))
    t = ball_tree(idx.lat.to_numpy(), idx.lon.to_numpy())
    i0 = int(t.query(np.radians([[45.46, 9.19]]), k=1)[1][0, 0])
    nb = t.query_radius(np.radians([[idx.lat[i0], idx.lon[i0]]]), r=15.0 / EARTH_R_KM)[0]
    print(f"[global] probe tile near Milan: {i0} {idx.grid_cell[i0]}; {len(nb) - 1} neighbours <= 15 km")
