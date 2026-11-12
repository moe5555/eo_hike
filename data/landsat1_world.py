"""The Landsat 1 world: the whole MSS mission (1972-78) on the Major TOM grid, one acquisition per cell (notes/brief_landsat_pipeline.md, A).

    python data/landsat1_world.py grid         # Major TOM 10 km grid, land mask -> data/landsat1/grid.parquet
    python data/landsat1_world.py candidates   # every Landsat 1 acquisition covering each land cell -> candidates.parquet, scenes.parquet
    python data/landsat1_world.py index        # the selection rule (earliest) -> index.parquet, world.json
    python data/landsat1_world.py stack        # every cell's acquisitions in date order, one per day -> stack/ (the revisit rule)
    python data/landsat1_world.py check        # the grid against the Major TOM cells of data/global/index.parquet

The tiles themselves are read lazily by data/landsat1_store.Landsat1TileStore; the portrait of the world is analysis/landsat1/portrait.py.

Choices, each named here and recorded in world.json:
- Grid. Major TOM's (Francis & Czerwinska 2024, github.com/ESA-PhiLab/Major-TOM, src/grid.py): rows every 10 km of the equatorial
  arc (radius 6378.137 km), each row cut into ceil(circumference / 10 km) columns, labelled like 543U_17R. A grid point is a cell's
  bottom-left corner. The cell's centre is the point + CENTRE_OFFSET_M east and north in the point's UTM zone: measured against
  Major TOM cells, the archive's 10.68 km crop is centred on the 10 km cell: +5.0 km (`check`).
- Land mask. global-land-mask (GLOBE, 1 km) on 5 x 5 points over the 10.68 km cell, as data/global_index.cover_class: a cell with
  at least one land point is kept (land or coast); open ocean is not part of the world.
- Coverage. An acquisition covers a cell when the cell's centre and its four corners lie inside the scene's STAC footprint. Cells
  only partly inside every scene are left out (counted in world.json). Fill inside a footprint is kept and measured from pixels.
- Candidates keep every processing level and tier, and night scenes (sun elevation <= 0), flagged.
- Selection (a premise): `earliest`, the first day the satellite imaged the cell; ties on one day (overlapping scenes of a pass) go
  to the scene whose centre is nearest (e10's tie-break). Selection is a function, so other rules can be added (SELECT).
- EPSG. Planetary Computer's proj:epsg drops the zero of UTM zones 1-9 (3265 for 32605); read as the zone it names, kept as
  epsg_catalogue.
- Revisits (`stack`, Moe 2026-11-12): a cell's acquisitions in date order, one per day (overlapping scenes of one pass are the same
  scan lines cut twice: the scene with the nearest centre stands for that day, e10's tie-break). The first visit shows the earliest,
  each revisit the next; when a cell's stack runs out, it is no longer offered (agent/walk.py, `stack: revisit_next`). Rank 0 of the
  stack is the earliest rule's acquisition.
- Pixel window. 178 x 178 native 60 m pixels (10.68 km) centred on the cell's centre, in the scene's own projection and pixel grid,
  not rotated into the cell's UTM zone and not resampled: the archive as stored.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "landsat1"
ITEMS = ROOT / "landsat" / "landsat1_c2l1_items.parquet"
PROJ = ROOT / "landsat" / "landsat1_c2l1_proj.parquet"
GRID_PQ, CAND_PQ, SCENES_PQ, INDEX_PQ = (OUT / f for f in ("grid.parquet", "candidates.parquet", "scenes.parquet", "index.parquet"))
GRID_KM = 10.0
R_EQ_KM = 6378.137  # Major TOM's grid radius
EARTH_R_KM = 6371.0088  # the walker's haversine radius (data/tile_store)
CELL_M = 10680.0
NATIVE_PX = 178
NATIVE_M = 60.0
CENTRE_OFFSET_M = 5000.0  # grid point -> cell centre, east and north in the point's UTM zone: the 10.68 km crop is centred on the 10 km cell (`check`)
HALF_KM = CELL_M / 2000.0
LAT_RANGE = (-85.0, 85.0)  # Major TOM's default; Landsat 1 reaches about 81.5 degrees


# -- the Major TOM grid ------------------------------------------------------------------------------------------------------
def grid_rows() -> tuple[np.ndarray, np.ndarray]:
    """Row labels and latitudes (south to north), as Major TOM's Grid.get_rows."""
    n = math.ceil(math.pi * R_EQ_KM / GRID_KM)
    lats = np.sort(np.mod(np.linspace(-90, 90, n + 1)[:-1], 180) - 90)
    z = int(np.searchsorted(lats, 0))
    rows = np.array([f"{abs(i - z)}D" for i in range(z)] + [f"{i}U" for i in range(len(lats) - z)])
    keep = (lats >= LAT_RANGE[0]) & (lats <= LAT_RANGE[1])
    return rows[keep], lats[keep]


def grid_cols(lat: float) -> tuple[np.ndarray, np.ndarray]:
    """Column labels and longitudes of one row, as Major TOM's Grid.subdivide_circumference."""
    circ = 2 * math.pi * R_EQ_KM * math.cos(math.radians(lat))
    m = math.ceil(circ / GRID_KM)
    lons = np.sort(np.mod(np.linspace(-180, 180, m + 1)[:-1], 360) - 180)
    z = int(np.flatnonzero(lons == 0)[0])
    cols = np.array([f"{abs(i - z)}L" for i in range(z)] + [f"{i}R" for i in range(len(lons) - z)])
    return cols, lons


def utm_epsg(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    zone = (np.floor((np.asarray(lon) + 180.0) / 6.0).astype(int) % 60) + 1
    return np.where(np.asarray(lat) >= 0, 32600, 32700) + zone


def centres(plat: np.ndarray, plon: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Cell centres (lat, lon) from grid points: + CENTRE_OFFSET_M east and north in each point's UTM zone."""
    from rasterio.warp import transform

    epsg = utm_epsg(plat, plon)
    clat, clon = np.empty(len(plat)), np.empty(len(plat))
    for e in np.unique(epsg):
        m = epsg == e
        x, y = transform("EPSG:4326", f"EPSG:{e}", plon[m].tolist(), plat[m].tolist())
        lo, la = transform(f"EPSG:{e}", "EPSG:4326", (np.array(x) + CENTRE_OFFSET_M).tolist(), (np.array(y) + CENTRE_OFFSET_M).tolist())
        clat[m], clon[m] = la, lo
    return clat, clon


def land_share(lat: np.ndarray, lon: np.ndarray, chunk: int = 250_000) -> np.ndarray:
    """Share of 5 x 5 points over the cell that are land (global-land-mask), as data/global_index.cover_class."""
    from global_land_mask import globe

    off = np.linspace(-HALF_KM, HALF_KM, 5)
    dy, dx = np.meshgrid(off, off, indexing="ij")
    dy, dx = dy.ravel() / 110.57, dx.ravel()
    out = np.empty(len(lat))
    for s in range(0, len(lat), chunk):
        la, lo = lat[s : s + chunk, None], lon[s : s + chunk, None]
        pla = np.clip(la + dy, -89.99, 89.99)
        plo = (lo + dx / (111.32 * np.cos(np.radians(la))) + 180.0) % 360.0 - 180.0
        out[s : s + chunk] = globe.is_land(pla.ravel(), plo.ravel()).reshape(pla.shape).mean(1)
    return out


def cmd_grid() -> None:
    t0 = time.time()
    rows, lats = grid_rows()
    rl, cl, pla, plo = [], [], [], []
    for r, la in zip(rows, lats):
        c, lo = grid_cols(float(la))
        rl.append(np.full(len(c), r))
        cl.append(c)
        pla.append(np.full(len(c), la))
        plo.append(lo)
    g = pd.DataFrame({"row": np.concatenate(rl), "col": np.concatenate(cl), "point_lat": np.concatenate(pla), "point_lon": np.concatenate(plo)})
    print(f"[grid] {len(g):,} Major TOM cells in {LAT_RANGE}", flush=True)
    clat, clon = centres(g.point_lat.to_numpy(), g.point_lon.to_numpy())
    share = land_share(clat, clon)
    g["lat"], g["lon"], g["land_share"] = clat, clon, share
    g = g[share > 0].copy()
    g["grid_cell"] = g.row + "_" + g.col
    g["cover"] = np.where(g.land_share == 1.0, "land", "coast")
    g = g.sort_values(["lat", "lon"], ascending=[False, True]).reset_index(drop=True)
    g.insert(0, "cell", np.arange(len(g), dtype=np.int32))
    OUT.mkdir(parents=True, exist_ok=True)
    g.to_parquet(GRID_PQ)
    print(f"[grid] {len(g):,} cells with land ({(g.cover == 'land').sum():,} land, {(g.cover == 'coast').sum():,} coast) in {time.time() - t0:.0f} s -> {GRID_PQ}")


def cmd_check() -> None:
    """The grid against Major TOM: every global-index cell that is in our grid must sit at the same centre."""
    g = pd.read_parquet(GRID_PQ, columns=["grid_cell", "lat", "lon"])
    m = pd.read_parquet(ROOT / "global" / "index.parquet", columns=["grid_cell", "lat", "lon", "cover"])
    j = m.merge(g, on="grid_cell", suffixes=("_mt", ""))
    d = haversine_km(j.lat_mt.to_numpy(), j.lon_mt.to_numpy(), j.lat.to_numpy(), j.lon.to_numpy())
    mt_land = m[m.cover != "ocean"]
    print(f"[check] Major TOM land/coast cells {len(mt_land):,}; in our grid {mt_land.grid_cell.isin(g.grid_cell).mean():.4f}")
    print(f"[check] centre distance to Major TOM's, km: p50 {np.median(d):.3f}  p95 {np.percentile(d, 95):.3f}  p99.9 {np.percentile(d, 99.9):.3f}  max {d.max():.3f}")


# -- candidates --------------------------------------------------------------------------------------------------------------
def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_R_KM * np.arcsin(np.sqrt(a))


def _ring(geom: str) -> np.ndarray:
    g = json.loads(geom)
    ring = g["coordinates"][0] if g["type"] == "Polygon" else max((p[0] for p in g["coordinates"]), key=len)
    return np.asarray(ring, float)


def _wrap(lon: np.ndarray, ref: float) -> np.ndarray:
    return (lon - ref + 180.0) % 360.0 - 180.0


def scene_table() -> pd.DataFrame:
    d = pd.read_parquet(ITEMS)
    p = pd.read_parquet(PROJ)
    d = d.merge(p.drop(columns="epsg"), on="id", how="left", validate="one_to_one")
    assert d.x0.notna().all(), f"{d.x0.isna().sum()} items without raster geometry"
    rings = [_ring(g) for g in d.geom]
    # scene centre: mean of the footprint's vertices (e10's _centroid), with longitudes unwrapped around the first vertex
    clat, clon = np.empty(len(d)), np.empty(len(d))
    for k, r in enumerate(rings):
        lo = _wrap(r[:-1, 0], r[0, 0]) + r[0, 0]
        clat[k], clon[k] = r[:-1, 1].mean(), (lo.mean() + 180) % 360 - 180
    t = pd.DataFrame({
        "scene": np.arange(len(d), dtype=np.int32), "id": d.id.to_numpy(),
        "datetime": pd.to_datetime(d.datetime, format="ISO8601").dt.tz_localize(None).to_numpy(),
        "path": d["landsat:wrs_path"].astype(int).to_numpy(), "wrs_row": d["landsat:wrs_row"].astype(int).to_numpy(),
        "level": d["landsat:correction"].to_numpy(), "tier": d["landsat:collection_category"].to_numpy(),
        "scene_cloud": d["eo:cloud_cover"].astype(float).to_numpy(), "scene_cloud_land": d["landsat:cloud_cover_land"].astype(float).to_numpy(),
        "sun_elevation": d["view:sun_elevation"].astype(float).to_numpy(), "epsg": d["proj:epsg"].astype(int).to_numpy(),
        "x0": d.x0.to_numpy(), "y0": d.y0.to_numpy(), "px": d.px.to_numpy(), "py": d.py.to_numpy(),
        "height": d.height.astype(int).to_numpy(), "width": d.width.astype(int).to_numpy(), "centre_lat": clat, "centre_lon": clon})
    # a quirk of the catalogue: UTM zones 1-9 lose their zero padding in proj:epsg (3265 for 32605; 27,171 Landsat 1 items). The COGs
    # carry the right CRS; the catalogue's value is kept as epsg_catalogue
    t["epsg_catalogue"] = t.epsg
    short = (t.epsg > 3260) & (t.epsg < 3270)  # 3031 (Antarctic polar stereographic) is a real code
    t.loc[short, "epsg"] = (t.epsg[short] // 10) * 100 + t.epsg[short] % 10
    t["night"] = t.sun_elevation <= 0
    t["day"] = t.datetime.dt.floor("D")
    return t, rings


def cmd_candidates() -> None:
    from matplotlib.path import Path as MPath
    from rasterio.warp import transform
    from sklearn.neighbors import BallTree
    from tqdm import tqdm

    t0 = time.time()
    sc, rings = scene_table()
    g = pd.read_parquet(GRID_PQ, columns=["cell", "lat", "lon"])
    glat, glon = g.lat.to_numpy(), g.lon.to_numpy()
    tree = BallTree(np.radians(np.stack([glat, glon], 1)), metric="haversine")
    # the cell's centre and four corners, as offsets in degrees (local; the cell is ~north-up in its UTM zone)
    dlat = HALF_KM / 110.57
    dlon = HALF_KM / (111.32 * np.cos(np.radians(glat)))
    corner = np.array([[0, 0], [-1, -1], [-1, 1], [1, -1], [1, 1]], float)
    cells, scenes, dcen = [], [], []
    rad = np.array([np.max(haversine_km(r[:, 1], r[:, 0], la, lo)) for r, la, lo in zip(rings, sc.centre_lat, sc.centre_lon)])
    B = 2000
    for s0 in tqdm(range(0, len(sc), B), desc="scenes"):
        sl = slice(s0, min(s0 + B, len(sc)))
        hits = tree.query_radius(np.radians(np.stack([sc.centre_lat[sl], sc.centre_lon[sl]], 1)), r=(rad[sl] + 1.0) / EARTH_R_KM)
        for k, h in zip(range(sl.start, sl.stop), hits):
            if not len(h):
                continue
            r = rings[k]
            ref = float(sc.centre_lon[k])
            path = MPath(np.stack([_wrap(r[:, 0], ref), r[:, 1]], 1))
            pla = glat[h, None] + corner[None, :, 0] * dlat
            plo = _wrap(glon[h], ref)[:, None] + corner[None, :, 1] * dlon[h, None]
            inside = path.contains_points(np.stack([plo.ravel(), pla.ravel()], 1)).reshape(len(h), 5).all(1)
            h = h[inside]
            cells.append(h.astype(np.int32))
            scenes.append(np.full(len(h), k, np.int32))
            dcen.append(haversine_km(glat[h], glon[h], sc.centre_lat[k], sc.centre_lon[k]).astype(np.float32))
    c = pd.DataFrame({"cell": np.concatenate(cells), "scene": np.concatenate(scenes), "d_centre_km": np.concatenate(dcen)})
    print(f"[candidates] {len(c):,} (cell, scene) pairs, {c.cell.nunique():,} cells covered, {time.time() - t0:.0f} s", flush=True)
    # the pixel window: 178 px centred on the cell's centre in the scene's pixel grid
    r0 = np.empty(len(c), np.int32)
    c0 = np.empty(len(c), np.int32)
    ep = sc.epsg.to_numpy()[c.scene.to_numpy()]
    for e in tqdm(np.unique(ep), desc="windows"):
        m = np.flatnonzero(ep == e)
        x, y = transform("EPSG:4326", f"EPSG:{e}", glon[c.cell.to_numpy()[m]].tolist(), glat[c.cell.to_numpy()[m]].tolist())
        s = c.scene.to_numpy()[m]
        col = (np.array(x) - sc.x0.to_numpy()[s]) / sc.px.to_numpy()[s]
        row = (np.array(y) - sc.y0.to_numpy()[s]) / sc.py.to_numpy()[s]
        c0[m] = np.rint(col - NATIVE_PX / 2).astype(np.int32)
        r0[m] = np.rint(row - NATIVE_PX / 2).astype(np.int32)
    c["r0"], c["c0"] = r0, c0
    s = c.scene.to_numpy()
    inr = (r0 >= 0) & (c0 >= 0) & (r0 + NATIVE_PX <= sc.height.to_numpy()[s]) & (c0 + NATIVE_PX <= sc.width.to_numpy()[s])
    c["in_raster"] = inr
    # the scene's attributes the selection and the portrait need, denormalised (categoricals keep it small)
    for k in ("day", "level", "tier", "scene_cloud", "sun_elevation", "night", "path", "wrs_row"):
        v = sc[k].to_numpy()[s]
        c[k] = pd.Categorical(v) if k in ("level", "tier") else v
    sc.to_parquet(SCENES_PQ)
    c.to_parquet(CAND_PQ)
    print(f"[candidates] window outside the raster for {(~inr).sum():,} pairs (dropped at selection); {time.time() - t0:.0f} s -> {CAND_PQ}")


# -- selection ---------------------------------------------------------------------------------------------------------------
def select_earliest(c: pd.DataFrame) -> pd.DataFrame:
    """One acquisition per cell: the earliest day; ties on one day to the scene whose centre is nearest (e10's tie-break)."""
    return c.sort_values(["cell", "day", "d_centre_km"], kind="stable").drop_duplicates("cell", keep="first")


SELECT = {"earliest": select_earliest}
STACK_DIR = OUT / "stack"  # start.npy, scene.npy, r0.npy, c0.npy (memory-mapped by the store)


def cmd_stack() -> None:
    """Every cell's acquisitions, ordered as select_earliest orders them, one per (cell, day): CSR arrays over the world's idx
    (index.parquet), so stack entry k of cell i is at start[i] + k. Rank 0 is checked against the index."""
    t0 = time.time()
    x = pd.read_parquet(INDEX_PQ, columns=["idx", "cell", "scene_idx", "r0", "c0"])
    c = pd.read_parquet(CAND_PQ, columns=["cell", "scene", "day", "d_centre_km", "r0", "c0", "in_raster"])
    c = c[c.in_raster].drop(columns="in_raster")
    n0 = len(c)
    c = c.sort_values(["cell", "day", "d_centre_km"], kind="stable").drop_duplicates(["cell", "day"], keep="first")
    pos = pd.Series(x.idx.to_numpy(), index=x.cell.to_numpy())
    c["idx"] = pos.reindex(c.cell.to_numpy()).to_numpy()
    c = c.sort_values(["idx", "day", "d_centre_km"], kind="stable")
    n = np.bincount(c.idx.to_numpy(), minlength=len(x))
    start = np.zeros(len(x) + 1, np.int64)
    start[1:] = np.cumsum(n)
    sc, r0, c0 = c.scene.to_numpy(np.int32), c.r0.to_numpy(np.int32), c.c0.to_numpy(np.int32)
    first = start[:-1]
    assert np.array_equal(sc[first], x.scene_idx.to_numpy()) and np.array_equal(r0[first], x.r0.to_numpy()) and np.array_equal(c0[first], x.c0.to_numpy()), \
        "rank 0 of the stack differs from the earliest rule's index"
    STACK_DIR.mkdir(parents=True, exist_ok=True)
    for k, v in (("start", start), ("scene", sc), ("r0", r0), ("c0", c0)):
        np.save(STACK_DIR / f"{k}.npy", v)
    print(f"[stack] {n0:,} in-raster pairs -> {len(c):,} (cell, day) acquisitions; per cell median {np.median(n):.0f}, "
          f"p90 {np.percentile(n, 90):.0f}, max {n.max()}; cells with one only {np.mean(n == 1):.3f}; rank 0 = index: ok; "
          f"{time.time() - t0:.0f} s -> {STACK_DIR}")


def cmd_index(rule: str = "earliest") -> None:
    t0 = time.time()
    g = pd.read_parquet(GRID_PQ)
    sc = pd.read_parquet(SCENES_PQ)
    c = pd.read_parquet(CAND_PQ)
    n_pairs, n_cov = len(c), c.cell.nunique()
    c = c[c.in_raster]
    sel = SELECT[rule](c)
    n_cand = c.groupby("cell").size()
    w = g.merge(sel, on="cell", how="inner")
    s = sc.set_index("scene").loc[w.scene.to_numpy()]
    idx = pd.DataFrame({
        "cell": w.cell.to_numpy(), "grid_cell": w.grid_cell.to_numpy(), "lat": w.lat.to_numpy(), "lon": w.lon.to_numpy(),
        "cover": w.cover.to_numpy(), "land_share": w.land_share.to_numpy(),
        "scene": s.id.to_numpy(), "scene_idx": w.scene.to_numpy(), "timestamp": s.datetime.to_numpy(), "path": s.path.to_numpy(),
        "wrs_row": s.wrs_row.to_numpy(), "level": s.level.to_numpy(), "tier": s.tier.to_numpy(), "scene_cloud": s.scene_cloud.to_numpy(),
        "sun_elevation": s.sun_elevation.to_numpy(), "night": s.night.to_numpy(), "epsg": s.epsg.to_numpy(),
        "d_centre_km": w.d_centre_km.to_numpy(), "r0": w.r0.to_numpy(), "c0": w.c0.to_numpy(),
        "n_candidates": n_cand.reindex(w.cell).to_numpy()})
    idx["cloud_cover"] = idx.scene_cloud  # the walker's log column (steps.parquet); per-cell QA cloud is in the quirk table
    idx = idx.sort_values(["lat", "lon"], ascending=[False, True]).reset_index(drop=True)
    idx.insert(0, "idx", np.arange(len(idx), dtype=np.int64))
    idx.to_parquet(INDEX_PQ)
    info = {"world": "landsat1", "rule": rule, "n_cells": len(idx), "n_grid_cells_land": len(g), "n_cells_covered_by_a_footprint": int(n_cov),
            "n_pairs": int(n_pairs), "n_pairs_in_raster": int(len(c)), "cell_m": CELL_M, "native_px": NATIVE_PX, "tile_px": 256,
            "centre_offset_m": CENTRE_OFFSET_M, "lat_range": LAT_RANGE, "built": time.strftime("%Y-%m-%d %H:%M:%S"),
            "cover": idx.cover.value_counts().to_dict(), "levels": idx.level.value_counts().to_dict(), "tiers": idx.tier.value_counts().to_dict(),
            "night": int(idx.night.sum()), "dates": [str(idx.timestamp.min()), str(idx.timestamp.max())]}
    (OUT / "world.json").write_text(json.dumps(info, indent=1, default=str))
    print(json.dumps(info, indent=1, default=str))
    print(f"[index] {time.time() - t0:.0f} s -> {INDEX_PQ}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"grid": cmd_grid, "check": cmd_check, "candidates": cmd_candidates, "stack": cmd_stack, "index": lambda: cmd_index(*(sys.argv[2:3] or ["earliest"]))}[cmd]()
