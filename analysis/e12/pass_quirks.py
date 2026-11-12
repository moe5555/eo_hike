"""Quirk table of the e10 pass world (the test bed of the two-eye walker, notes/brief_landsat_pipeline.md, A6 and E14).

    python analysis/e12/pass_quirks.py [world]   # default c10680m_256px_cir_sqrt; -> <pass world>/quirks.parquet (per cell) and crop_quirks.parquet (per 4 x 4 grid crop)

The e10 build kept one stripe share per cell and did not download QA_RADSAT. Here QA_RADSAT is downloaded for the pass's scenes (into
their scene folders) and every cell gets the quirk columns of data/landsat1_store.quirk_arrays, computed from the same native window
the tile was cut from (index x, y -> r0, c0 on the scene's grid), with the same 2 px margin as the mission store.

Also a check of the one view: data/landsat1_store.render (TOA, sqrt, the e10 stretch, bilinear to 256 px) on that window must give the
stored tile. Reported as the share of identical pixels and the largest difference.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from data import landsat1_store as L  # noqa: E402
from data.landsat_pass import Signer, download  # noqa: E402

PASS = ROOT / "data" / "landsat" / "LM01_183_19721122"
WORLD = PASS / (sys.argv[1] if len(sys.argv) > 1 else "c10680m_256px_cir_sqrt")


def main() -> None:
    import rasterio
    from tqdm import tqdm

    idx = pd.read_parquet(WORLD / "index.parquet")
    wj = json.loads((WORLD / "world.json").read_text())
    lo, hi, cell_m = wj["stretch_lo"], wj["stretch_hi"], wj["cell_m"]
    tiles = np.load(WORLD / "tiles.npy", mmap_mode="r")
    sign = Signer()
    rows, crows, same, maxd = [], [], [], 0
    M, n = L.MARGIN, L.NATIVE_PX
    for sid, grp in tqdm(idx.groupby("scene"), desc="scenes"):
        sd = PASS / "scenes" / sid
        it = json.loads((sd / "item.json").read_text())
        download(sign(it["assets"]["qa_radsat"]["href"]), sd / "qa_radsat.tif")
        mtl = json.loads((sd / "mtl.json").read_text())["LANDSAT_METADATA_FILE"]
        resc, files = mtl["LEVEL1_RADIOMETRIC_RESCALING"], mtl["PRODUCT_CONTENTS"]
        sun = float(mtl["IMAGE_ATTRIBUTES"]["SUN_ELEVATION"])
        num = {b: next(k for k, v in files.items() if k.startswith("FILE_NAME_BAND_") and v == Path(it["assets"][b]["href"]).name).rsplit("_", 1)[1] for b in L.BANDS}
        arr = {}
        for k in L.BANDS + L.QA:
            with rasterio.open(sd / f"{k}.tif") as ds:
                arr[k] = np.pad(ds.read(1), M)  # zero margin outside the raster, as a boundless read
                T = ds.transform
        for r in grp.itertuples():
            c0 = int(np.rint((r.x - cell_m / 2 - T.c) / T.a))
            r0 = int(np.rint((T.f - (r.y + cell_m / 2)) / -T.e))
            w = {k: a[r0 : r0 + n + 2 * M, c0 : c0 + n + 2 * M] for k, a in arr.items()}  # padded array: index r0 is native r0 - M
            qc, qk = L.quirk_arrays({b: w[b] for b in L.BANDS}, w["qa_pixel"], w["qa_radsat"])
            rows.append((r.idx, *qc.tolist()))
            crows.extend((r.idx, k, *v.tolist()) for k, v in enumerate(qk))
            if r.idx % 25 == 0:  # the one-view check on every 25th cell
                sl = slice(M, M + n)
                valid = (w["qa_pixel"][sl, sl] & 1) == 0
                for b in L.BANDS:
                    valid &= w[b][sl, sl] > 0
                bands = np.stack([L.toa(w[b][sl, sl], float(resc[f"REFLECTANCE_MULT_BAND_{num[b]}"]), float(resc[f"REFLECTANCE_ADD_BAND_{num[b]}"]), sun) for b in L.BANDS])
                bands[:, ~valid] = np.nan
                d = np.abs(L.render(bands, lo, hi).astype(int) - np.asarray(tiles[r.idx]).astype(int))
                same.append(float((d == 0).mean()))
                maxd = max(maxd, int(d.max()))
    q = pd.DataFrame(rows, columns=["tile_idx", *L.QUIRK_COLS]).sort_values("tile_idx")
    q.to_parquet(WORLD / "quirks.parquet")
    pd.DataFrame(crows, columns=["tile_idx", "crop", *L.QUIRK_COLS]).sort_values(["tile_idx", "crop"]).to_parquet(WORLD / "crop_quirks.parquet")
    j = q.merge(idx[["idx", "stripe"]], left_on="tile_idx", right_on="idx")
    j["stripe_any"] = j[[f"stripe_{b}" for b in L.BANDS]].max(axis=1)
    print(f"[quirks] {len(q)} cells; one view: {len(same)} cells checked, identical pixels {np.mean(same):.4f} (min {np.min(same):.4f}), max |diff| {maxd}")
    print(f"[quirks] e10 stripe (any band, all pixels) vs max per-band stripe here: Spearman {j[['stripe', 'stripe_any']].corr('spearman').iloc[0, 1]:.3f}")
    print(q.describe().T[["mean", "50%", "max"]].round(4).to_string())


if __name__ == "__main__":
    main()
