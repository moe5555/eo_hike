"""Dreams v3: document the one fixed global RGB scale, from a global random sample of tiles.

    python data/global_stretch.py            # -> data/global_stretch.json (+ notes/dreams_v3/global_stretch.png)

v3 takes RGB from the archive's `thumbnail` column for both the walker and the GAN crops (decided with the
artist, 2026-10-28), so no stretch is applied by this project: the thumbnail already is B04/B03/B02 under one
fixed scale for every tile on Earth. This script makes that explicit and checks it globally:
- 5,000 tiles drawn uniformly from the filtered global index (seed 0): per-channel 0.5/2/50/98/99.5 % percentiles
  of the thumbnail RGB and the share of saturated (255) and black (0) pixels;
- 40 of them with raw B04/B03/B02 fetched as well: the band -> thumbnail mapping per channel (rank correlation
  with the band and with sqrt(band), and the band values at thumbnail 2 % / 98 %), i.e. what a fixed
  2-98 % band stretch computed from this sample would have been. These band values are stored as
  `band_stretch_2_98` for reference; nothing in the pipeline uses them.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from data.tile_store import TileStore  # noqa: E402

N_THUMB, N_BANDS, PIX_PER_TILE = 5000, 40, 4096


def read_band(b: bytes) -> np.ndarray:
    return np.asarray(Image.open(io.BytesIO(b)), dtype=np.float64)


def main() -> None:
    store = TileStore()
    rng = np.random.default_rng(0)
    ids = np.sort(rng.choice(store.N, N_THUMB, replace=False))
    failed = store.fetch_all(ids, desc="stretch sample")
    ids = np.array([i for i in ids if i not in set(failed)])
    pix = []
    for i in ids:
        a = store.get_hires(int(i)).reshape(-1, 3)
        pix.append(a[rng.integers(0, len(a), PIX_PER_TILE)])
    pix = np.concatenate(pix).astype(np.float64)
    qs = [0.5, 2, 50, 98, 99.5]
    thumb = {c: {f"p{q:g}": float(np.percentile(pix[:, k], q)) for q in qs} | {"share_255": float((pix[:, k] == 255).mean()), "share_0": float((pix[:, k] == 0).mean())}
             for k, c in enumerate("RGB")}

    # raw bands for a subset: what the archive's fixed scale is
    import pyarrow.parquet as pq
    from scipy.stats import spearmanr

    sub = ids[rng.choice(len(ids), N_BANDS, replace=False)]
    band_pix, th_pix = {b: [] for b in ("B04", "B03", "B02")}, []
    for i in sub:
        url, r = store.url[i], int(store.row[i])
        md, size = store._footer(url)
        with store._fs().open(url, "rb", block_size=1 << 20, cache_type="none", size=size) as f:
            tbl = pq.ParquetFile(f, metadata=md).read_row_group(r, columns=["B04", "B03", "B02"])
        th = store.get_hires(int(i)).reshape(-1, 3).astype(np.float64)
        sel = rng.integers(0, len(th), PIX_PER_TILE)
        for b in band_pix:
            arr = read_band(tbl.column(b)[0].as_py())
            if arr.shape[0] * arr.shape[1] != len(th):
                arr = np.asarray(Image.fromarray(arr.astype(np.float32)).resize((1068, 1068), Image.Resampling.NEAREST), dtype=np.float64)
            band_pix[b].append(arr.reshape(-1)[sel])
        th_pix.append(th[sel])
    th_pix = np.concatenate(th_pix)
    rel, band_stretch = {}, {}
    for k, b in enumerate(("B04", "B03", "B02")):
        v = np.concatenate(band_pix[b])
        ok = th_pix[:, k] > 0
        rel[b] = {"spearman_band": float(spearmanr(v[ok], th_pix[ok, k])[0]), "pearson_sqrt_band": float(np.corrcoef(np.sqrt(v[ok]), th_pix[ok, k])[0, 1]),
                  "band_at_thumb_p2": float(np.percentile(v[ok], 2)), "band_at_thumb_p98": float(np.percentile(v[ok], 98))}
        band_stretch[b] = [float(np.percentile(v[ok], 2)), float(np.percentile(v[ok], 98))]
    out = {
        "rgb_source": "Major TOM Core-S2L2A `thumbnail` column: full 1068x1068 B04/B03/B02 at 10 m under the archive's one fixed scale",
        "applied_by_this_project": "none (thumbnail bytes are used as they are; low-res = BOX resize to 256 px)",
        "decided": "2026-10-28 with the artist: thumbnail for both walker views and GAN crops, so the agent's model and its dreams share one colour mapping",
        "sample": {"n_tiles": int(len(ids)), "seed": 0, "pixels_per_tile": PIX_PER_TILE, "failed": len(failed)},
        "thumbnail_rgb_percentiles": thumb,
        "band_check": {"n_tiles": N_BANDS, "per_band": rel},
        "band_stretch_2_98": band_stretch,
    }
    (ROOT / "global_stretch.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(1, 4, figsize=(18, 4))
    for k, (c, b) in enumerate(zip("RGB", ("B04", "B03", "B02"))):
        axs[0].hist(pix[:, k], bins=256, range=(0, 256), histtype="step", color=c.lower() if c != "G" else "green", label=c)
        v = np.concatenate(band_pix[b])
        axs[k + 1].hexbin(v, th_pix[:, k], gridsize=80, bins="log", extent=(0, np.percentile(v, 99.5), 0, 255))
        axs[k + 1].set_xlabel(f"{b} (L2A reflectance x 1e4)")
        axs[k + 1].set_ylabel(f"thumbnail {c}")
    axs[0].legend()
    axs[0].set_title(f"thumbnail RGB, {len(ids):,} random global tiles")
    fig.tight_layout()
    p = ROOT.parent / "notes" / "dreams_v3" / "global_stretch.png"
    fig.savefig(p, dpi=110)
    print(f"[stretch] -> {p}")


if __name__ == "__main__":
    main()
