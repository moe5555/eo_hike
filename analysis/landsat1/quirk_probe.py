"""Quirk probe (research for a Landsat 1 world, notes/11_landsat1_mission/research.md): a stratified sample of Landsat 1 scenes, a 512 x 512 px (30.7 km) window at the scene centre of every band and both QA
bands, read from the Planetary Computer COGs. Per scene: fill, cloud (QA_PIXEL bit 3, high confidence bits 8-9 = 11), dropped pixels
(QA_RADSAT bit 9), saturation per band (bits 3-6: MSS bands 4-7), distinct DN levels per band, e10's stripe share (|DN - vertical
5-px median| > 25 in any band). Sample: up to 4 daylit scenes per year and correction level (L1TP / L1GS), seed 0.
The band6_* columns (a 6-line detector-banding ratio) are not robust: they divide by ~0 on flat windows. Not used.

    python analysis/landsat1/quirk_probe.py data/landsat/landsat1_c2l1_items.parquet notes/11_landsat1_mission/results/quirk_probe.csv
"""

import sys
import time

import numpy as np
import pandas as pd
import requests
import rasterio
from rasterio.windows import Window
from scipy.ndimage import median_filter

items = pd.read_parquet(sys.argv[1])
out = sys.argv[2]
rng = np.random.default_rng(0)
items["year"] = items.datetime.str[:4]
day = items[items["view:sun_elevation"] > 0]
sample = day.sample(frac=1, random_state=0).groupby(["year", "landsat:correction"]).head(4)
tok = requests.get("https://planetarycomputer.microsoft.com/api/sas/v1/token/landsateuwest/landsat-c2", timeout=60).json()["token"]
S = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
BANDS = ("green", "red", "nir08", "nir09")
rows = []
env = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES")
for _, it in sample.iterrows():
    try:
        f = requests.get(f"https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l1/items/{it.id}", timeout=120).json()
        t0 = time.time()
        a = {}
        with rasterio.Env(**env):
            for k in (*BANDS, "qa_pixel", "qa_radsat"):
                with rasterio.open(f["assets"][k]["href"] + "?" + tok) as ds:
                    H, W = ds.shape
                    a[k] = ds.read(1, window=Window(W // 2 - 256, H // 2 - 256, 512, 512))
        qp, qr = a["qa_pixel"].astype(np.uint16), a["qa_radsat"].astype(np.uint16)
        fill = (qp & 1) > 0
        valid = ~fill
        nv = max(valid.sum(), 1)
        r = {"id": it.id, "year": it["datetime"][:4], "correction": it["landsat:correction"], "tier": it["landsat:collection_category"],
             "scene_cloud": it["eo:cloud_cover"], "sun_elev": it["view:sun_elevation"], "fill": fill.mean(),
             "cloud": ((qp >> 3 & 1) > 0)[valid].sum() / nv, "cloud_high": (((qp >> 8) & 3) == 3)[valid].sum() / nv,
             "dropped": ((qr >> 9 & 1) > 0)[valid].sum() / nv, "sec": time.time() - t0}
        stripe = np.zeros_like(fill)
        for b, bit in zip(BANDS, (3, 4, 5, 6)):
            x = a[b]
            r[f"sat_{b}"] = ((qr >> bit & 1) > 0)[valid].sum() / nv
            r[f"at255_{b}"] = (x[valid] == 255).mean() if valid.any() else np.nan
            r[f"levels_{b}"] = len(np.unique(x[valid])) if valid.any() else 0
            r[f"zero_{b}"] = (x[valid] == 0).mean() if valid.any() else np.nan
            stripe |= np.abs(x.astype(int) - median_filter(x, size=(5, 1)).astype(int)) > 25
            rm = x.astype(float).mean(1)
            if valid.all():
                rm = rm - np.convolve(rm, np.ones(25) / 25, "same")
                ph = np.array([rm[k::6].mean() for k in range(6)])
                r[f"band6_{b}"] = float(ph.std() / (rm[12:-12].std() + 1e-9))
        r["stripe"] = stripe[valid].mean() if valid.any() else np.nan
        rows.append(r)
        print(it.id, f"{r['sec']:.1f}s", flush=True)
    except Exception as e:  # noqa: BLE001
        print("fail", it.id, e, flush=True)
pd.DataFrame(rows).to_csv(out, index=False)
