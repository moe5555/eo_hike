"""One Landsat MSS orbital pass as a walker world: the satellite's own strip, cut into tiles.

    python data/landsat_pass.py list  --from 1972-07-25 --to 1973-07-31 [--platform landsat-1] [--top 20]
    python data/landsat_pass.py fetch --date 1972-11-22 --path 183 [--platform landsat-1]
    python data/landsat_pass.py build --pass LM01_183_19721122 [--cell-m 10680] [--tile-px 256] [--render cir]

`list` ranks the passes of a date range by number of daylight scenes (a pass = one WRS path on one day). `fetch` downloads the
pass's scenes (four bands, QA_PIXEL, MTL) to data/landsat/<pass>/scenes/ and writes pass.json. `build` cuts them into tiles and
writes a world folder data/landsat/<pass>/<world>/ with tiles.npy, index.parquet, world.json and two check images. A walk uses it
with `world: landsat_pass` and `pass_world: data/landsat/<pass>/<world>` (agent/walk.py, through data/tile_store.open_store).

Source: Landsat Collection 2 Level-1 (MSS, Landsat 1-5) on Microsoft Planetary Computer: STAC search without an account, and
files read with the anonymous SAS token of the container. Per scene ~33 MB; the 53 scenes of 22 Nov 1972 are ~1.7 GB.

Choices (defaults; each is a build option, recorded in world.json):
- Grid: per scene, in its own UTM zone, cells of cell_m aligned to multiples of cell_m in easting/northing, so scenes in one zone
  share one grid and their overlaps coincide. Scenes overlap along the track; each place is kept once: candidate cells (valid
  data <= max_nodata missing) are taken in order of distance to their own scene's centre, and one is dropped if a kept cell lies
  within 0.9 cell_m. Where the pass changes UTM zone the two grids do not line up, and the seam has small gaps.
- Scale: cell_m 10,680 m = 178 native 60 m pixels, resampled to 256 px (41.7 m/px): the same ground size and pixel size as the
  Major TOM low-res tiles, so crop_px 64 is still a ~2.7 km eye, and radius_min_km 15 / snap_floor_km 7.5 keep their meaning.
  MSS is 79 m native (60 m in the product); the 64 px crop, shrunk to 32 px, is ~83 m/px, so the eye loses almost nothing.
- Colour: top-of-atmosphere reflectance from the MTL (M * DN + A) / sin(sun elevation), then a tone curve, then one fixed linear
  stretch for the whole pass (per channel, percentiles 0.5-99.5 of a pixel sample of every scene), as Major TOM's one fixed scale.
  Tone `sqrt` (default): the square root of reflectance, the curve Major TOM's thumbnails follow (Pearson 0.99 with sqrt(band),
  notes/03_planet_walks/run_log.md). With `linear` the 22 Nov 1972 pass is dark (mean pixel 29 in the Caucasus against 92 on
  the global walker's tiles: clouds and desert set the top), the fresh network's latents of dark tiles nearly coincide, and
  the walker's offers become indistinguishable (2026-11-10 log). MSS has no
  blue band: `cir` is near-infrared / red / green (vegetation red, the 1970s false colour); `pseudo` is a synthetic natural
  colour (red / (3 green + nir) / 4 / green), not a measurement.
- Missing pixels inside a kept cell are black (as in Major TOM). cloud_cover per cell is the share of high-confidence cloud
  pixels (QA_PIXEL bit 3), in percent like Major TOM's column.
- Line defects: 1972 MSS scenes carry short bad scan-line segments in single bands, coloured stripes in the tiles (worst in the
  south of the 22 Nov 1972 pass). They are kept as they are and measured: `stripe` per cell is the share of pixels more than
  STRIPE_DN from their vertical 5-pixel median in any band. QA_RADSAT does not isolate them (it flags about half of a scene as
  saturated). --max-stripe drops cells above a share; the default keeps all. A curious walker may treat stripes as a noisy TV.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
LANDSAT = ROOT / "landsat"
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/{account}/{container}"
COLLECTION = "landsat-c2-l1"
BANDS = ("green", "red", "nir08", "nir09")  # MSS bands 4-7 on Landsat 1-3 (1-4 on Landsat 4-5); the files keep these names
ASSETS = BANDS + ("qa_pixel", "mtl.json")
NATIVE_M = 60.0
EARTH_R_KM = 6371.0088
QA_FILL, QA_CLOUD = 1 << 0, 1 << 3
STRIPE_DN = 25  # a pixel this far (8-bit DN) from its vertical 5-pixel median counts as a line defect (stripe_mask)
TONES = {
    "linear": lambda x: x,
    "sqrt": lambda x: np.sqrt(np.maximum(x, 0.0)),  # NaN (missing) stays NaN
}
RENDERS = {
    "cir": lambda b: (b["nir08"], b["red"], b["green"]),
    "pseudo": lambda b: (b["red"], 0.75 * b["green"] + 0.25 * b["nir08"], b["green"]),
}


# -- catalogue -------------------------------------------------------------------------------------------------------------
def _post(body: dict, tries: int = 6) -> dict:
    import requests

    for a in range(tries):
        try:
            r = requests.post(STAC, json=body, timeout=180)
            if r.status_code == 200:
                return r.json()
            err = f"HTTP {r.status_code}: {r.text[:200]}"
        except requests.RequestException as e:
            err = str(e)
        time.sleep(5 * (a + 1))
    raise RuntimeError(f"STAC search failed after {tries} tries: {err}")


def search(t0: str, t1: str, platform: str | None = None, path: int | None = None) -> list[dict]:
    """Every item of the collection in [t0, t1) (ISO dates or datetimes), optionally one platform and one WRS path."""
    args = []
    if platform:
        args.append({"op": "=", "args": [{"property": "platform"}, platform]})
    if path is not None:
        args.append({"op": "=", "args": [{"property": "landsat:wrs_path"}, f"{int(path):03d}"]})  # zero-padded strings
    iso = lambda s: s if "T" in s else f"{s}T00:00:00Z"  # noqa: E731
    body: dict = {"collections": [COLLECTION], "datetime": f"{iso(t0)}/{iso(t1)}", "limit": 1000}
    if args:
        body.update({"filter-lang": "cql2-json", "filter": args[0] if len(args) == 1 else {"op": "and", "args": args}})
    items = []
    while True:
        j = _post(body)
        items += j["features"]
        nxt = [l for l in j.get("links", []) if l.get("rel") == "next"]
        if not nxt or not j["features"]:
            return items
        body = nxt[0]["body"]


def _centroid(geom: dict) -> tuple[float, float]:
    """Mean of the footprint's outer-ring vertices (lat, lon): good enough to order cells by distance to a 185 km scene."""
    ring = geom["coordinates"][0] if geom["type"] == "Polygon" else geom["coordinates"][0][0]
    a = np.asarray(ring[:-1], dtype=float)
    return float(a[:, 1].mean()), float(a[:, 0].mean())


def describe(it: dict) -> dict:
    p = it["properties"]
    la, lo = _centroid(it["geometry"])
    return {"id": it["id"], "datetime": p["datetime"], "platform": p["platform"], "path": int(p["landsat:wrs_path"]),
            "row": int(p["landsat:wrs_row"]), "cloud_cover": float(p.get("eo:cloud_cover", -1)), "sun_elevation": float(p.get("view:sun_elevation", np.nan)),
            "correction": p.get("landsat:correction"), "category": p.get("landsat:collection_category"), "epsg": p.get("proj:epsg"),
            "centre_lat": la, "centre_lon": lo}


def pass_id(scenes: list[dict]) -> str:
    s = scenes[0]
    return f"{s['id'][:4]}_{s['path']:03d}_{s['datetime'][:10].replace('-', '')}"


def cmd_list(a) -> None:
    """Rank passes (one path on one day, daylight scenes only) in a date range by scene count."""
    rows = []
    d0, d1 = date.fromisoformat(a.date_from), date.fromisoformat(a.date_to)
    m = d0
    while m < d1:  # month by month: pages of 1,000 items, a few thousand items per month for one satellite
        n = min((m.replace(day=1) + timedelta(days=32)).replace(day=1), d1)
        its = search(m.isoformat(), n.isoformat(), a.platform)
        rows += [describe(it) for it in its]
        print(f"[list] {m} .. {n}: {len(its)} scenes", flush=True)
        m = n
    d = pd.DataFrame(rows)
    d = d[d.sun_elevation > 0]
    d["day"] = d.datetime.str[:10]
    g = d.groupby(["day", "path"]).agg(scenes=("id", "size"), row_min=("row", "min"), row_max=("row", "max"), cloud_median=("cloud_cover", "median"),
                                       lat_max=("centre_lat", "max"), lat_min=("centre_lat", "min"), lon_mean=("centre_lon", "mean"),
                                       l1tp=("correction", lambda s: float((s == "L1TP").mean())))
    g["row_gaps"] = g.row_max - g.row_min + 1 - g.scenes
    print(g.sort_values("scenes", ascending=False).head(a.top).round(2).to_string())


# -- download --------------------------------------------------------------------------------------------------------------
class Signer:
    """Planetary Computer SAS tokens, one per storage container, renewed well before they expire."""

    def __init__(self) -> None:
        self.tok: dict[tuple[str, str], tuple[str, float]] = {}

    def __call__(self, href: str) -> str:
        import requests

        acct, cont = href.split("//")[1].split(".")[0], href.split(".net/")[1].split("/")[0]
        t = self.tok.get((acct, cont))
        if t is None or time.time() - t[1] > 1800:
            r = requests.get(SAS.format(account=acct, container=cont), timeout=60)
            r.raise_for_status()
            t = (r.json()["token"], time.time())
            self.tok[(acct, cont)] = t
        return f"{href}?{t[0]}"


def download(url: str, dst: Path, tries: int = 6) -> int:
    import requests

    if dst.exists():
        return 0
    part = dst.with_suffix(dst.suffix + ".part")
    for a in range(tries):
        try:
            with requests.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                want = int(r.headers.get("Content-Length", -1))
                with open(part, "wb") as fh:
                    for chunk in r.iter_content(1 << 20):
                        fh.write(chunk)
            if want >= 0 and part.stat().st_size != want:
                raise OSError(f"short read {part.stat().st_size} of {want}")
            part.replace(dst)
            return dst.stat().st_size
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(min(2.0**a, 30.0))
    raise RuntimeError(f"{dst.name}: {err}")


def cmd_fetch(a) -> None:
    day = date.fromisoformat(a.date)
    its = search(day.isoformat(), (day + timedelta(days=1)).isoformat(), a.platform, a.path)
    its = [it for it in its if it["properties"].get("view:sun_elevation", -1) > 0]  # daylight: night rows are calibration/dark scenes
    if not its:
        sys.exit(f"no daylight scenes for path {a.path} on {a.date} ({a.platform or 'any platform'})")
    if len({it["properties"]["platform"] for it in its}) > 1:
        sys.exit("more than one platform flew this path that day: pass --platform")
    its.sort(key=lambda it: it["properties"]["datetime"])
    scenes = [describe(it) for it in its]
    pid = pass_id(scenes)
    pd_dir = LANDSAT / pid
    sign = Signer()
    nbytes = 0
    for k, it in enumerate(its):
        sd = pd_dir / "scenes" / it["id"]
        sd.mkdir(parents=True, exist_ok=True)
        (sd / "item.json").write_text(json.dumps(it))
        for name in ASSETS:
            ext = ".json" if name == "mtl.json" else ".tif"
            nbytes += download(sign(it["assets"][name]["href"]), sd / f"{name.replace('.json', '')}{ext}")
        print(f"[fetch] {k + 1}/{len(its)} {it['id']}  ({nbytes / 1e9:.2f} GB so far)", flush=True)
    rows = [s["row"] for s in scenes]
    info = {"pass": pid, "date": a.date, "path": a.path, "platform": scenes[0]["platform"], "collection": COLLECTION, "n_scenes": len(scenes),
            "rows": [min(rows), max(rows)], "row_gaps": [[r0, r1] for r0, r1 in zip(rows[:-1], rows[1:]) if r1 - r0 > 1],
            "first": scenes[0]["datetime"], "last": scenes[-1]["datetime"], "fetched": time.strftime("%Y-%m-%d %H:%M:%S"), "scenes": scenes}
    (pd_dir / "pass.json").write_text(json.dumps(info, indent=1))
    print(f"[fetch] {pid}: {len(scenes)} scenes, rows {min(rows)}-{max(rows)}, gaps {info['row_gaps']} -> {pd_dir}")


# -- build -----------------------------------------------------------------------------------------------------------------
def read_scene(sd: Path) -> dict:
    """Bands as TOA reflectance (float32, NaN where missing), the QA array, the transform and CRS of one scene."""
    import rasterio

    mtl = json.loads((sd / "mtl.json").read_text())["LANDSAT_METADATA_FILE"]
    resc, attr = mtl["LEVEL1_RADIOMETRIC_RESCALING"], mtl["IMAGE_ATTRIBUTES"]
    sin_e = np.sin(np.radians(float(attr["SUN_ELEVATION"])))
    files, assets = mtl["PRODUCT_CONTENTS"], json.loads((sd / "item.json").read_text())["assets"]
    num = {}
    for name in BANDS:  # the MTL names bands by number (4-7 on Landsat 1-3, 1-4 on 4-5): match on the file names it lists
        fn = Path(assets[name]["href"]).name
        num[name] = next(k for k, v in files.items() if k.startswith("FILE_NAME_BAND_") and v == fn).rsplit("_", 1)[1]
    with rasterio.open(sd / "qa_pixel.tif") as q:
        qa = q.read(1)
        transform, crs = q.transform, q.crs
    out, dns = {}, {}
    valid = (qa & QA_FILL) == 0
    for name in BANDS:
        with rasterio.open(sd / f"{name}.tif") as src:
            assert src.transform == transform and src.shape == qa.shape, f"{sd.name}: {name} grid differs from QA_PIXEL"
            dn = src.read(1)
        valid &= dn > 0
        m, b = float(resc[f"REFLECTANCE_MULT_BAND_{num[name]}"]), float(resc[f"REFLECTANCE_ADD_BAND_{num[name]}"])
        out[name] = ((m * dn.astype(np.float32) + b) / sin_e).astype(np.float32)
        dns[name] = dn
    for name in BANDS:
        out[name][~valid] = np.nan
    return {"bands": out, "valid": valid, "cloud": (qa & QA_CLOUD) != 0, "stripe": stripe_mask(dns, valid), "transform": transform, "crs": crs}


def stripe_mask(dns: dict, valid: np.ndarray) -> np.ndarray:
    """Pixels on a defective scan-line segment: in any band, more than STRIPE_DN away from the median of the 2 pixels above, itself
    and the 2 below (MSS lines run along the rows, tilted by a few degrees in UTM). Only where all five are valid, so the scene's
    edge is not counted. Measured, not repaired: a vertical-median repair removed some lines and drew others (2026-11-10 log)."""
    from scipy.ndimage import binary_erosion, median_filter

    inner = binary_erosion(valid, structure=np.ones((5, 1), bool))
    bad = np.zeros_like(valid)
    for dn in dns.values():
        bad |= np.abs(dn.astype(np.int16) - median_filter(dn, size=(5, 1)).astype(np.int16)) > STRIPE_DN
    return bad & inner


def scene_cells(sc: dict, cell_m: float) -> pd.DataFrame:
    """Cells of one scene on the UTM grid of multiples of cell_m, with valid and cloud shares; whole cells inside the raster only."""
    from rasterio.warp import transform as warp

    T, (H, W) = sc["transform"], sc["valid"].shape
    left, top, px = T.c, T.f, T.a
    n = int(round(cell_m / NATIVE_M))
    right, bottom = left + W * px, top - H * px
    ix = np.arange(int(np.ceil(left / cell_m)), int(np.floor(right / cell_m)))
    iy = np.arange(int(np.ceil(bottom / cell_m)), int(np.floor(top / cell_m)))
    IX, IY = (a.ravel() for a in np.meshgrid(ix, iy))
    c0 = np.rint((IX * cell_m - left) / px).astype(int)
    r0 = np.rint((top - (IY + 1) * cell_m) / px).astype(int)
    ok = (c0 >= 0) & (r0 >= 0) & (c0 + n <= W) & (r0 + n <= H)
    IX, IY, c0, r0 = IX[ok], IY[ok], c0[ok], r0[ok]
    # shares per cell from a summed-area table (one pass over the scene, not one slice per cell)
    def box(mask):
        s = np.zeros((H + 1, W + 1), np.int64)
        s[1:, 1:] = mask.cumsum(0).cumsum(1)
        return (s[r0 + n, c0 + n] - s[r0, c0 + n] - s[r0 + n, c0] + s[r0, c0]) / (n * n)
    xs, ys = (IX + 0.5) * cell_m, (IY + 0.5) * cell_m
    lon, lat = warp(sc["crs"], "EPSG:4326", xs.tolist(), ys.tolist())
    return pd.DataFrame({"ix": IX, "iy": IY, "c0": c0, "r0": r0, "x": xs, "y": ys, "lat": lat, "lon": lon,
                         "valid": box(sc["valid"]), "cloud": box(sc["cloud"] & sc["valid"]), "stripe": box(sc["stripe"])})


def unit(lat, lon) -> np.ndarray:
    la, lo = np.radians(lat), np.radians(lon)
    return np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], -1)


def dedupe(c: pd.DataFrame, min_sep_km: float) -> np.ndarray:
    """Greedy: cells nearest their own scene's centre first; a cell is dropped if a kept one lies within min_sep_km."""
    order = np.argsort(c.d_own.to_numpy(), kind="stable")
    P = unit(c.lat.to_numpy(), c.lon.to_numpy()) * EARTH_R_KM  # chord ~ arc at these distances
    key = np.floor(P / min_sep_km).astype(np.int64)
    bins: dict[tuple, list[int]] = {}
    keep = np.zeros(len(c), bool)
    nb = [(i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)]
    for o in order:
        kx, ky, kz = key[o]
        hit = False
        for di, dj, dk in nb:
            for q in bins.get((kx + di, ky + dj, kz + dk), ()):
                if np.sum((P[o] - P[q]) ** 2) < min_sep_km**2:
                    hit = True
                    break
            if hit:
                break
        if not hit:
            keep[o] = True
            bins.setdefault((kx, ky, kz), []).append(o)
    return keep


def cover_class(lat: np.ndarray, lon: np.ndarray, half_km: float) -> np.ndarray:
    """As data/global_index.cover_class, with the 5x5 samples spread over this cell size: land / coast / ocean (reporting only)."""
    from global_land_mask import globe

    off = np.linspace(-half_km, half_km, 5)
    dy, dx = np.meshgrid(off, off, indexing="ij")
    dy, dx = dy.ravel() / 110.57, dx.ravel()
    la, lo = lat[:, None], lon[:, None]
    pla = np.clip(la + dy, -89.99, 89.99)
    plo = (lo + dx / (111.32 * np.cos(np.radians(la))) + 180.0) % 360.0 - 180.0
    frac = globe.is_land(pla.ravel(), plo.ravel()).reshape(pla.shape).mean(1)
    return np.where(frac == 1.0, "land", np.where(frac == 0.0, "ocean", "coast"))


def cmd_build(a) -> None:
    from PIL import Image
    from tqdm import tqdm

    pdir = LANDSAT / a.pass_id
    info = json.loads((pdir / "pass.json").read_text())
    scenes = info["scenes"]
    n_native = int(round(a.cell_m / NATIVE_M))
    if abs(n_native * NATIVE_M - a.cell_m) > 1e-6:
        sys.exit(f"--cell-m must be a multiple of {NATIVE_M:.0f} m (got {a.cell_m})")
    tone = TONES[a.tone]
    render = lambda b: tuple(tone(x) for x in RENDERS[a.render](b))  # noqa: E731
    world = a.name or f"c{int(a.cell_m)}m_{a.tile_px}px_{a.render}" + ("" if a.tone == "linear" else f"_{a.tone}")
    wdir = pdir / world
    wdir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    # 1. candidate cells of every scene, and a pixel sample for the stretch
    cands, sample = [], []
    rng = np.random.default_rng(0)
    for k, s in enumerate(tqdm(scenes, desc="cells")):
        sc = read_scene(pdir / "scenes" / s["id"])
        c = scene_cells(sc, a.cell_m)
        c["scene"] = k
        cands.append(c[(c.valid >= 1.0 - a.max_nodata) & (c.stripe <= a.max_stripe)])
        ch = render(sc["bands"])
        v = np.flatnonzero(sc["valid"].ravel())
        pick = rng.choice(v, size=min(len(v), a.sample_per_scene), replace=False) if len(v) else v
        sample.append(np.stack([x.ravel()[pick] for x in ch], 1))
    C = pd.concat(cands, ignore_index=True)
    sc_lat = np.array([s["centre_lat"] for s in scenes])[C.scene]
    sc_lon = np.array([s["centre_lon"] for s in scenes])[C.scene]
    C["d_own"] = haversine_km(C.lat.to_numpy(), C.lon.to_numpy(), sc_lat, sc_lon)
    keep = dedupe(C, 0.9 * a.cell_m / 1000.0)
    n_cand = len(C)
    C = C[keep].copy()
    C = C.sort_values(["lat", "lon"], ascending=[False, True]).reset_index(drop=True)  # tile ids: north to south, as the global index
    smp = np.concatenate(sample)
    lo, hi = np.nanpercentile(smp, a.stretch[0], axis=0), np.nanpercentile(smp, a.stretch[1], axis=0)
    print(f"[build] {n_cand} candidate cells -> {len(C)} kept after the overlap rule; stretch {a.render} lo {np.round(lo, 4)} hi {np.round(hi, 4)}")

    # 2. render the kept cells, scene by scene, into the memmap
    N, P = len(C), a.tile_px
    tiles = np.lib.format.open_memmap(wdir / "tiles.npy.part", mode="w+", dtype=np.uint8, shape=(N, P, P, 3))
    for k, s in enumerate(tqdm(scenes, desc="tiles")):
        rows = np.flatnonzero(C.scene.to_numpy() == k)
        if not len(rows):
            continue
        sc = read_scene(pdir / "scenes" / s["id"])
        ch = np.stack(render(sc["bands"]), -1)
        rgb = np.clip((ch - lo) / (hi - lo), 0.0, 1.0) * 255.0
        rgb = np.where(np.isfinite(rgb), rgb, 0.0).astype(np.uint8)  # missing pixels black
        for i in rows:
            r0, c0 = int(C.r0[i]), int(C.c0[i])
            im = Image.fromarray(rgb[r0 : r0 + n_native, c0 : c0 + n_native])
            tiles[i] = np.asarray(im.resize((P, P), Image.Resampling.BILINEAR if P >= n_native else Image.Resampling.BOX))
    tiles.flush()
    del tiles
    (wdir / "tiles.npy.part").replace(wdir / "tiles.npy")

    # 3. the index the walker reads (data/tile_store.World and agent/walk.py use idx, grid_cell, lat, lon, cover, cloud_cover)
    sc_df = pd.DataFrame(scenes)
    epsg = sc_df.epsg.to_numpy()[C.scene]
    zone = [f"{e % 100:02d}{'N' if e // 100 == 326 else 'S'}" for e in epsg]
    idx = pd.DataFrame({
        "idx": np.arange(N, dtype=np.int64),
        "grid_cell": [f"{z}_{x}E_{y}N" for z, x, y in zip(zone, C.ix, C.iy)],
        "lat": C.lat.to_numpy(), "lon": C.lon.to_numpy(),
        "timestamp": pd.to_datetime(sc_df.datetime.to_numpy()[C.scene], format="ISO8601").tz_localize(None),  # UTC, naive like the global index
        "cloud_cover": 100.0 * C.cloud.to_numpy(), "nodata": 1.0 - C.valid.to_numpy(), "stripe": C.stripe.to_numpy(),
        "scene": sc_df.id.to_numpy()[C.scene], "wrs_row": sc_df.row.to_numpy()[C.scene],
        "sun_elevation": sc_df.sun_elevation.to_numpy()[C.scene], "correction": sc_df.correction.to_numpy()[C.scene],
        "category": sc_df.category.to_numpy()[C.scene], "epsg": epsg, "x": C.x.to_numpy(), "y": C.y.to_numpy(),
        "d_scene_km": C.d_own.to_numpy(),
    })
    idx["cover"] = cover_class(idx.lat.to_numpy(), idx.lon.to_numpy(), a.cell_m / 2000.0)
    idx.to_parquet(wdir / "index.parquet")
    meta = {"pass": a.pass_id, "world": world, "n_tiles": N, "n_candidates": n_cand, "cell_m": a.cell_m, "tile_px": P, "m_per_px": a.cell_m / P,
            "native_px": n_native, "render": a.render, "tone": a.tone, "stretch_pct": list(a.stretch), "stretch_lo": lo.tolist(), "stretch_hi": hi.tolist(),
            "max_nodata": a.max_nodata, "max_stripe": a.max_stripe, "stripe_dn": STRIPE_DN, "min_sep_m": 0.9 * a.cell_m, "cover": idx.cover.value_counts().to_dict(),
            "cloud_cover_mean": float(idx.cloud_cover.mean()), "stripe_quantiles": {q: float(idx.stripe.quantile(q)) for q in (0.5, 0.9, 0.99)}, "lat": [float(idx.lat.min()), float(idx.lat.max())],
            "built": time.strftime("%Y-%m-%d %H:%M:%S"), "seconds": round(time.time() - t0, 1), "pass_info": {k: v for k, v in info.items() if k != "scenes"}}
    (wdir / "world.json").write_text(json.dumps(meta, indent=1))
    print(f"[build] {N} tiles of {a.cell_m / 1000:.2f} km at {P} px ({a.cell_m / P:.1f} m/px), cover {meta['cover']}, "
          f"mean cloud {meta['cloud_cover_mean']:.1f} %, {(wdir / 'tiles.npy').stat().st_size / 1e9:.2f} GB -> {wdir}")
    check(wdir)


def check(wdir: Path, deg_per_px: float = 0.02) -> None:
    """check_mosaic.png: every tile shrunk and placed at its centre (seams and the stretch at a glance);
    check_tiles.png: 24 random tiles at full size."""
    from PIL import Image

    idx = pd.read_parquet(wdir / "index.parquet")
    tiles = np.load(wdir / "tiles.npy", mmap_mode="r")
    meta = json.loads((wdir / "world.json").read_text())
    lat, lon = idx.lat.to_numpy(), idx.lon.to_numpy()
    lon0 = float(np.median(lon))
    lonw = (lon - lon0 + 180.0) % 360.0 - 180.0  # unwrapped around the pass, so a pass over the antimeridian stays in one piece
    cell_deg = meta["cell_m"] / 1000.0 / 111.0
    s = max(1, int(round(cell_deg / deg_per_px)))
    sx_max = int(np.ceil(cell_deg / np.cos(np.radians(np.abs(lat).max())) / deg_per_px))
    H = int((lat.max() - lat.min()) / deg_per_px) + 2 * s + 1
    W = int((lonw.max() - lonw.min()) / deg_per_px) + 2 * sx_max + 1
    canvas = np.full((H, W, 3), 255, np.uint8)
    for i in range(len(idx)):
        sx = max(1, int(np.ceil(cell_deg / np.cos(np.radians(lat[i])) / deg_per_px)))  # a cell spans more degrees of longitude away from the equator
        t = np.asarray(Image.fromarray(np.asarray(tiles[i])).resize((sx, s), Image.Resampling.BOX))
        y = int((lat.max() - lat[i]) / deg_per_px)
        x = int((lonw[i] - lonw.min()) / deg_per_px) + sx_max - sx // 2
        canvas[y : y + s, x : x + sx] = t
    Image.fromarray(canvas).save(wdir / "check_mosaic.png", optimize=True)
    pick = np.sort(np.random.default_rng(0).choice(len(idx), size=min(24, len(idx)), replace=False))
    P = tiles.shape[1]
    sheet = np.full((4 * P, 6 * P, 3), 255, np.uint8)
    for k, i in enumerate(pick):
        sheet[(k // 6) * P : (k // 6 + 1) * P, (k % 6) * P : (k % 6 + 1) * P] = tiles[i]
    Image.fromarray(sheet).save(wdir / "check_tiles.png", optimize=True)
    print(f"[check] {wdir / 'check_mosaic.png'} ({W}x{H}), {wdir / 'check_tiles.png'} (tiles {pick.tolist()})")


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_R_KM * np.arcsin(np.sqrt(a))


# -- the walker's store ----------------------------------------------------------------------------------------------------
class PassStore:
    """A built pass world with the interface agent/walk.py and the viewers use on data/tile_store.TileStore. Everything is local:
    tiles.npy is memory-mapped, nothing is fetched, nothing is ever dropped."""

    def __init__(self, world_dir: Path | str) -> None:
        d = Path(world_dir)
        self.dir = d if d.is_absolute() else ROOT.parent / d
        if not (self.dir / "tiles.npy").exists():
            raise FileNotFoundError(f"{self.dir}: no tiles.npy; run `python data/landsat_pass.py fetch` and `build` first")
        self.idx = pd.read_parquet(self.dir / "index.parquet")
        self.N = len(self.idx)
        self.tiles = np.load(self.dir / "tiles.npy", mmap_mode="r")
        self.meta = json.loads((self.dir / "world.json").read_text())
        self.fetch_log: list[tuple[int, float, int]] = []  # same columns as TileStore's; always empty
        self.n_reads = 0

    def get_lowres(self, i: int) -> np.ndarray:
        self.n_reads += 1
        return np.array(self.tiles[int(i)])

    get_hires = get_lowres  # the stored tile is already finer than the 60 m product

    def get_many(self, ids, timeout: float | None = None) -> tuple[dict[int, np.ndarray], list[int], dict]:
        out = {i: self.get_lowres(i) for i in dict.fromkeys(map(int, ids))}
        return out, [], {"wait_sec": 0.0, "n": len(out), "cache_hits": len(out)}

    def prefetch(self, ids) -> None:
        pass

    def cached(self, i: int) -> bool:
        return True

    def fetch_all(self, ids, desc: str = "fetch") -> list[int]:
        return []

    def summary(self) -> dict:
        return {"pass_world": str(self.dir.relative_to(ROOT.parent)) if self.dir.is_relative_to(ROOT.parent) else str(self.dir),
                "n_tiles": self.N, "reads": self.n_reads, "cell_m": self.meta["cell_m"], "tile_px": self.meta["tile_px"], "render": self.meta["render"],
                "tone": self.meta.get("tone", "linear")}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list", help="rank the passes of a date range by daylight scene count")
    p.add_argument("--from", dest="date_from", required=True)
    p.add_argument("--to", dest="date_to", required=True)
    p.add_argument("--platform", default="landsat-1")
    p.add_argument("--top", type=int, default=20)
    p = sub.add_parser("fetch", help="download one pass (one WRS path on one day)")
    p.add_argument("--date", required=True)
    p.add_argument("--path", type=int, required=True)
    p.add_argument("--platform", default=None, help="e.g. landsat-1; needed only if two satellites flew the path that day")
    p = sub.add_parser("build", help="cut a fetched pass into a walker world")
    p.add_argument("--pass", dest="pass_id", required=True, help="e.g. LM01_183_19721122 (printed by fetch)")
    p.add_argument("--cell-m", type=float, default=10680.0, help="ground size of a cell, a multiple of 60 m (default 178 px = Major TOM's tile)")
    p.add_argument("--tile-px", type=int, default=256, help="stored tile size (default 256: 41.7 m/px at the default cell)")
    p.add_argument("--render", choices=sorted(RENDERS), default="cir")
    p.add_argument("--tone", choices=sorted(TONES), default="sqrt", help="curve on reflectance before the stretch (sqrt = Major TOM's thumbnails)")
    p.add_argument("--stretch", type=float, nargs=2, default=(0.5, 99.5), metavar=("LO", "HI"), help="percentiles of the pass-wide stretch")
    p.add_argument("--max-nodata", type=float, default=0.10, help="share of missing pixels a cell may have (as data/prepare.MAX_NODATA)")
    p.add_argument("--max-stripe", type=float, default=1.0, help="share of line-defect pixels a cell may have (default 1: keep all, measure only)")
    p.add_argument("--sample-per-scene", type=int, default=200_000)
    p.add_argument("--name", default=None, help="world folder name (default c<cell>m_<px>px_<render>)")
    p = sub.add_parser("check", help="redraw the check images of a built world")
    p.add_argument("world_dir")
    a = ap.parse_args()
    if a.cmd == "check":
        d = Path(a.world_dir)
        check(d if d.is_absolute() else ROOT.parent / d)
    else:
        {"list": cmd_list, "fetch": cmd_fetch, "build": cmd_build}[a.cmd](a)


if __name__ == "__main__":
    main()
