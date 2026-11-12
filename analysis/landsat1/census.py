"""Census of the Landsat 1 mission in Collection 2 Level-1 (research for a Landsat 1 world, notes/11_landsat1_mission/research.md).

    python analysis/landsat1/census.py items      # every Landsat 1 STAC item on Planetary Computer, month by month -> data/landsat/
    python analysis/landsat1/census.py coverage   # footprints on a 0.25° land grid: scenes per place, per year, by level
    python analysis/landsat1/census.py items_proj # the raster geometry of every item (proj:transform, proj:shape) -> data/landsat/
    python analysis/landsat1/census.py map        # notes/11_landsat1_mission/figures/coverage_map.png

Metadata and footprints only; no image is read. The quirk probe (windows of image data) is analysis/landsat1/quirk_probe.py.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
ITEMS = ROOT / "data" / "landsat" / "landsat1_c2l1_items.parquet"
COVER = ROOT / "data" / "landsat" / "landsat1_coverage_025deg.npz"
PROJ = ROOT / "data" / "landsat" / "landsat1_c2l1_proj.parquet"
FIG = ROOT / "notes" / "11_landsat1_mission" / "figures" / "coverage_map.png"
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
PROPS = ["datetime", "eo:cloud_cover", "landsat:cloud_cover_land", "landsat:wrs_path", "landsat:wrs_row", "landsat:correction",
         "landsat:collection_category", "view:sun_elevation", "proj:epsg"]
RES = 0.25
REGIONS = {"N America": (15, 75, -170, -50), "S America": (-56, 15, -82, -34), "Europe": (35, 72, -10, 40), "Africa": (-35, 37, -18, 52),
           "Asia": (5, 78, 40, 180), "Oceania": (-48, 0, 110, 180)}


def _post(body: dict) -> dict:
    for a in range(8):
        try:
            r = requests.post(STAC, json=body, timeout=240)
            if r.status_code == 200:
                return r.json()
        except requests.RequestException:
            pass
        time.sleep(3 * 2**a)
    raise RuntimeError(body)


def items() -> None:
    """Month by month (an unbounded query times out with HTTP 504)."""
    rows = []
    months = pd.date_range("1972-07-01", "1978-02-01", freq="MS")
    for m0, m1 in zip(months[:-1], months[1:]):
        body = {"collections": ["landsat-c2-l1"], "datetime": f"{m0.date()}/{(m1 - pd.Timedelta(seconds=1)).isoformat()}Z",
                "query": {"platform": {"eq": "landsat-1"}}, "limit": 1000,
                "fields": {"include": ["id", "bbox", "geometry"] + [f"properties.{p}" for p in PROPS], "exclude": ["assets", "links"]}}
        n = 0
        while True:
            j = _post(body)
            for f in j["features"]:
                p = f["properties"]
                rows.append({"id": f["id"], **{k: p.get(k) for k in PROPS}, "bbox": f.get("bbox"), "geom": json.dumps(f.get("geometry"))})
                n += 1
            nxt = [link for link in j.get("links", []) if link.get("rel") == "next"]
            if not nxt:
                break
            body = nxt[0]["body"]
        print(m0.date(), n, flush=True)
    ITEMS.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(ITEMS)
    print("total", len(rows))


def items_proj() -> None:
    """The raster geometry of every Landsat 1 item (proj:transform, proj:shape), which `items` did not keep, for the pixel windows
    of the world's candidate table (data/landsat1_world.py). Month by month, as `items`."""
    rows = []
    months = pd.date_range("1972-07-01", "1978-02-01", freq="MS")
    for m0, m1 in zip(months[:-1], months[1:]):
        body = {"collections": ["landsat-c2-l1"], "datetime": f"{m0.date()}/{(m1 - pd.Timedelta(seconds=1)).isoformat()}Z",
                "query": {"platform": {"eq": "landsat-1"}}, "limit": 1000,
                "fields": {"include": ["id", "properties.proj:transform", "properties.proj:shape", "properties.proj:epsg"],
                           "exclude": ["assets", "links", "geometry", "bbox"]}}
        n = 0
        while True:
            j = _post(body)
            for f in j["features"]:
                p = f["properties"]
                t, s = p.get("proj:transform"), p.get("proj:shape")
                rows.append({"id": f["id"], "epsg": p.get("proj:epsg"), "x0": t[2], "px": t[0], "y0": t[5], "py": t[4], "rot": t[1] + t[3],
                             "height": s[0], "width": s[1]})
                n += 1
            nxt = [link for link in j.get("links", []) if link.get("rel") == "next"]
            if not nxt:
                break
            body = nxt[0]["body"]
        print(m0.date(), n, flush=True)
    pd.DataFrame(rows).to_parquet(PROJ)
    print("total", len(rows))


def _grid():
    from global_land_mask import globe

    lats, lons = np.arange(-90 + RES / 2, 90, RES), np.arange(-180 + RES / 2, 180, RES)
    LA, LO = np.meshgrid(lats, lons, indexing="ij")
    return lats, lons, LA, LO, globe.is_land(LA, LO)


def _rasterise(geoms, lats, lons, LA, LO):
    """Yield (index of the geometry, row slice, col slice, mask of grid points inside the footprint)."""
    from matplotlib.path import Path as MPath

    for k, g in enumerate(geoms):
        ring = np.array(json.loads(g)["coordinates"][0])
        (x0, y0), (x1, y1) = ring.min(0), ring.max(0)
        i0, i1 = np.searchsorted(lats, [y0, y1])
        j0, j1 = np.searchsorted(lons, [x0, x1])
        if i1 <= i0 or j1 <= j0:
            continue
        pts = np.stack([LO[i0:i1, j0:j1].ravel(), LA[i0:i1, j0:j1].ravel()], 1)
        yield k, slice(i0, i1), slice(j0, j1), MPath(ring).contains_points(pts).reshape(i1 - i0, j1 - j0)


def coverage() -> None:
    d = pd.read_parquet(ITEMS)
    d = d[d["view:sun_elevation"] > 0].reset_index(drop=True)
    years = d.datetime.str[:4].astype(int).to_numpy()
    lats, lons, LA, LO, land = _grid()
    cnt, clear, tp, t1 = (np.zeros(LA.shape, np.int32) for _ in range(4))
    yc = {y: np.zeros(LA.shape, bool) for y in range(1972, 1979)}
    for k, si, sj, m in _rasterise(d.geom, lats, lons, LA, LO):
        cnt[si, sj] += m
        clear[si, sj] += m * (d["eo:cloud_cover"].iat[k] <= 20)
        tp[si, sj] += m * (d["landsat:correction"].iat[k] == "L1TP")
        t1[si, sj] += m * (d["landsat:collection_category"].iat[k] == "T1")
        yc[years[k]][si, sj] |= m
    np.savez(COVER, cnt=cnt, clear=clear, tp=tp, t1=t1, land=land, lats=lats, lons=lons, **{f"y{y}": v for y, v in yc.items()})
    w, noant = np.cos(np.radians(LA)), land & (LA > -60)

    def share(m, base):
        return float((w * (m & base)).sum() / (w * base).sum())

    print(f"items {len(pd.read_parquet(ITEMS, columns=['id']))}, daylit {len(d)}")
    for nm, c in (("any", cnt), ("cloud<=20", clear), ("L1TP", tp), ("T1", t1)):
        print(f"{nm:10s} land {share(c > 0, land):.3f}  land excl. Antarctica {share(c > 0, noant):.3f}")
    for y, m in yc.items():
        print(y, "land (excl. Antarctica) imaged that year", round(share(m, noant), 3))
    early = (yc[1972] | yc[1973]) & ~(yc[1975] | yc[1976] | yc[1977])
    print("land imaged in 1972-73 and never in 1975-77", round(share(early, noant), 3))
    for r, (a, b, c0, c1) in REGIONS.items():
        m = noant & (LA >= a) & (LA < b) & (LO >= c0) & (LO < c1)
        print(f"{r:10s} covered {share(cnt > 0, m):.2f}  clear {share(clear > 0, m):.2f}  L1TP {share(tp > 0, m):.2f}  "
              f"median scenes {np.median(cnt[(cnt > 0) & m]):.0f}")


def draw_map() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm

    z = np.load(COVER)
    land, c = z["land"], z["cnt"].astype(float)
    ext = (-180, 180, -90, 90)
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.imshow(np.where(land, 0.92, 1.0)[::-1], extent=ext, cmap="gray", vmin=0, vmax=1)
    im = ax.imshow(np.where(land & (c >= 1), c, np.nan)[::-1], extent=ext, cmap="Blues", norm=LogNorm(1, 300))
    ax.imshow(np.where(land & (c == 0), 1, np.nan)[::-1], extent=ext, cmap="Oranges", vmin=0, vmax=1.3)
    ax.set_title(f"Landsat 1 MSS, Collection 2 (Planetary Computer): daylit scenes per place, 1972-07-25 to 1978-01-07", loc="left", fontsize=10)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01, label="scenes covering the place (log)")
    fig.text(0.01, 0.02, "Orange: land never imaged in Collection 2 (south of 81° S: beyond the orbit). Grid 0.25°. Land mask: global-land-mask (GLOBE).",
             fontsize=8, color="#6b6a63")
    fig.tight_layout()
    fig.savefig(FIG, dpi=130)


if __name__ == "__main__":
    {"items": items, "items_proj": items_proj, "coverage": coverage, "map": draw_map}[sys.argv[1]]()
