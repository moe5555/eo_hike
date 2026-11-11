"""PNGs of Landsat 1 MSS cells with their quirks, and the resolution against Sentinel-2 (research, notes/11_landsat1_mission/research.md).

    python analysis/landsat1/render_quirks.py      # -> notes/11_landsat1_mission/figures/quirks_*.png, resolution_paris.png

Rendering as e10's world (data/landsat_pass.py): TOA reflectance from the MTL, (M * DN + A) / sin(sun elevation), square root, then the
fixed per-channel stretch of the e10 world (LM01_183_19721122/c10680m_256px_cir/world.json), CIR (nir08 / red / green). A cell is
178 x 178 native 60 m px = 10.68 km; the walker's tile is that cell resized to 256 px (bilinear, as e10's build). Night scenes have no
TOA reflectance (sun below the horizon): they are shown as DN with a per-tile 1-99 % stretch, and say so.

Per scene, a 512 px window at the scene centre is read (as analysis/landsat1/quirk_probe.py), and inside it the 178 px cell where the
quirk is strongest. Flags: e10's stripe mask (|DN - vertical 5-px median| > 25 in any band), QA_RADSAT saturation bits 3-6 (any band),
pixels at DN 255 (any band), QA_PIXEL cloud (bit 3), fill (bit 0). Nothing is repaired.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw
from scipy.ndimage import median_filter, uniform_filter

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "notes" / "11_landsat1_mission" / "figures"
E10 = json.loads((ROOT / "data" / "landsat" / "LM01_183_19721122" / "c10680m_256px_cir" / "world.json").read_text())
LO, HI = np.array(E10["stretch_lo"]), np.array(E10["stretch_hi"])  # (nir08, red, green), after sqrt
ITEM = "https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l1/items/{}"
BANDS = ("green", "red", "nir08", "nir09")
CELL = 178
INK = (43, 43, 42)

PICKS = [  # (scene, what it shows, how to choose the cell inside the window)
    ("LM01_L1TP_186044_19750514_02_T1", "clean: Tier 1, no cloud, no stripes (Eastern Desert, 23° N 34.5° E)", "centre"),
    ("LM01_L1TP_029039_19740417_02_T2", "line defects: 43 % of window pixels on bad scan-line segments", "stripe"),
    ("LM01_L1TP_154049_19720918_02_T2", "line defects, 1972 (29 %)", "stripe"),
    ("LM01_L1GS_014034_19750521_02_T2", "saturation flag without saturation: 52 % flagged, 0.002 % at DN 255", "satflag"),
    ("LM01_L1GS_130005_19740517_02_T2", "real saturation: 91 % at DN 255 (high Arctic)", "at255"),
    ("LM01_L1GS_011023_19730510_02_T2", "snow and cloud in May: QA cloud on half the cell, DN 255 on a quarter, stripes", "cloudedge"),
    ("LM01_L1TP_212021_19760428_02_T2", "missing data: a band of fill inside the scene", "fill"),
    ("LM01_L1GS_124224_19720906_02_T2", "night scene (sun -15°): DN, per-tile stretch", "centre"),
]


def token() -> str:
    return requests.get("https://planetarycomputer.microsoft.com/api/sas/v1/token/landsateuwest/landsat-c2", timeout=60).json()["token"]


def read(scene: str, tok: str, centre_xy=None, size: int = 512) -> dict:
    """Bands (DN), QA_PIXEL, QA_RADSAT and the MTL of a size px window: at the scene centre, or centred on (x, y) in the scene's CRS."""
    import rasterio
    from rasterio.windows import Window

    it = requests.get(ITEM.format(scene), timeout=120).json()
    mtl = requests.get(it["assets"]["mtl.json"]["href"] + "?" + tok, timeout=120).json()["LANDSAT_METADATA_FILE"]
    out = {"item": it, "mtl": mtl}
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES"):
        for k in (*BANDS, "qa_pixel", "qa_radsat"):
            with rasterio.open(it["assets"][k]["href"] + "?" + tok) as ds:
                if centre_xy is None:
                    r0, c0 = ds.height // 2 - size // 2, ds.width // 2 - size // 2
                else:
                    r, c = ds.index(*centre_xy)
                    r0, c0 = r - size // 2, c - size // 2
                out[k] = ds.read(1, window=Window(c0, r0, size, size), boundless=True, fill_value=0)
                out["crs"] = ds.crs
    files = mtl["PRODUCT_CONTENTS"]
    out["num"] = {b: next(k for k, v in files.items() if k.startswith("FILE_NAME_BAND_") and v == Path(it["assets"][b]["href"]).name).rsplit("_", 1)[1]
                  for b in BANDS}
    return out


def flags(w: dict) -> dict:
    qp, qr = w["qa_pixel"].astype(np.uint16), w["qa_radsat"].astype(np.uint16)
    fill = (qp & 1) > 0
    stripe = np.zeros_like(fill)
    for b in BANDS:
        dn = w[b]
        stripe |= np.abs(dn.astype(np.int16) - median_filter(dn, size=(5, 1)).astype(np.int16)) > 25
    return {"fill": fill, "cloud": (qp >> 3 & 1) > 0, "stripe": stripe & ~fill, "satflag": ((qr >> 3) & 0b1111) > 0,
            "at255": np.any([w[b] == 255 for b in BANDS], 0)}


def cir(w: dict, night: bool) -> np.ndarray:
    """CIR float [H, W, 3] in [0, 1]: e10's tone and stretch, or for a night scene DN with a per-tile stretch."""
    ch = ("nir08", "red", "green")
    if night:
        x = np.stack([w[b].astype(np.float32) for b in ch], -1)
        lo, hi = np.percentile(x, 1, (0, 1)), np.percentile(x, 99, (0, 1))
        return np.clip((x - lo) / np.maximum(hi - lo, 1), 0, 1)
    resc = w["mtl"]["LEVEL1_RADIOMETRIC_RESCALING"]
    sin_e = np.sin(np.radians(float(w["mtl"]["IMAGE_ATTRIBUTES"]["SUN_ELEVATION"])))
    out = []
    for k, b in enumerate(ch):
        n = w["num"][b]
        refl = (float(resc[f"REFLECTANCE_MULT_BAND_{n}"]) * w[b].astype(np.float32) + float(resc[f"REFLECTANCE_ADD_BAND_{n}"])) / sin_e
        out.append(np.clip((np.sqrt(np.maximum(refl, 0)) - LO[k]) / (HI[k] - LO[k]), 0, 1))
    x = np.stack(out, -1)
    x[w["qa_pixel"] & 1 > 0] = 0  # fill is black, as in the tiles
    return x


def pick_cell(f: dict, how: str, size: int) -> tuple[int, int]:
    """Top-left (r, c) of the CELL px cell in the window where the quirk is strongest."""
    if how == "centre":
        return (size - CELL) // 2, (size - CELL) // 2
    score = {"stripe": f["stripe"], "satflag": f["satflag"] & ~f["at255"], "at255": f["at255"],
             "fill": f["fill"], "cloudedge": f["cloud"]}[how].astype(float)
    m = uniform_filter(score, CELL, mode="constant")
    if how == "cloudedge":
        m = np.minimum(m, 1 - m)  # half cloud, half not
    if how == "fill":
        m = np.minimum(m, 0.35)  # some fill, mostly image
    h = CELL // 2
    r, c = np.unravel_index(np.argmax(m[h : size - h, h : size - h]), (size - CELL, size - CELL))
    return int(r), int(c)


def u8(x: np.ndarray) -> Image.Image:
    return Image.fromarray((np.clip(x, 0, 1) * 255).astype(np.uint8))


def overlay(rgb: np.ndarray, f: dict) -> np.ndarray:
    g = rgb.mean(-1, keepdims=True).repeat(3, -1) * 0.55 + 0.2
    for k, col in (("satflag", (1.0, 0.8, 0.0)), ("at255", (1.0, 1.0, 1.0)), ("cloud", (0.35, 0.85, 1.0)), ("stripe", (0.95, 0.2, 0.1)),
                   ("fill", (0.85, 0.2, 0.85))):
        g[f[k]] = col
    return g


def quirk_sheet(tok: str) -> None:
    rows = []
    for scene, what, how in PICKS:
        w = read(scene, tok)
        night = float(w["mtl"]["IMAGE_ATTRIBUTES"]["SUN_ELEVATION"]) <= 0
        f = flags(w)
        r, c = pick_cell(f, how, 512)
        sl = (slice(r, r + CELL), slice(c, c + CELL))
        img = cir(w, night)[sl]
        fc = {k: v[sl] for k, v in f.items()}
        tile = u8(img).resize((256, 256), Image.Resampling.BILINEAR)  # the walker's tile
        # native pixels: the 48 px (2.9 km) where the quirk is densest in the cell, x 5 nearest
        z = np.ones((CELL, CELL)) if how in ("centre",) else uniform_filter(fc[{"stripe": "stripe", "satflag": "satflag", "at255": "at255",
                                                                              "fill": "fill", "cloudedge": "cloud"}[how]].astype(float), 48)
        if how == "cloudedge":
            z = np.minimum(z, 1 - z)
        zr, zc = np.unravel_index(np.argmax(z[24:-24, 24:-24]), (CELL - 48, CELL - 48))
        zoom = u8(img[zr : zr + 48, zc : zc + 48]).resize((256, 256), Image.Resampling.NEAREST)
        ov = u8(overlay(img, fc)).resize((256, 256), Image.Resampling.NEAREST)
        stats = {k: float(v.mean()) for k, v in fc.items()}
        rows.append((scene, what, tile, zoom, ov, stats, night))
        print(scene, {k: round(v, 3) for k, v in stats.items()}, flush=True)
    W, H, pad, head = 3 * 256 + 2 * 6, 256, 14, 34
    S = Image.new("RGB", (W + 2 * pad, len(rows) * (H + head + pad) + 40), (252, 252, 251))
    d = ImageDraw.Draw(S)
    d.text((pad, 10), "Landsat 1 MSS cells (10.68 km, 178 native 60 m px). Left: the walker's tile (CIR, e10's tone and stretch, 256 px). "
                      "Middle: 48 native px (2.9 km) x5, no smoothing. Right: flags.", fill=INK)
    d.text((pad, 24), "Flags, each drawn over the one before: yellow = QA_RADSAT saturation flag, white = DN 255, cyan = QA cloud, "
                      "red = line defect (e10 stripe measure), magenta = fill.", fill=INK)
    y = 44
    for scene, what, tile, zoom, ov, st, night in rows:
        d.text((pad, y), f"{scene}  -  {what}", fill=INK)
        d.text((pad, y + 14), "cell: " + "  ".join(f"{k} {100 * v:.1f} %" for k, v in st.items()), fill=(107, 106, 99))
        for k, im in enumerate((tile, zoom, ov)):
            S.paste(im, (pad + k * 262, y + head))
        y += H + head + pad
    S.save(FIG / "quirks_sheet.png", optimize=True)
    for scene, what, tile, zoom, ov, st, night in rows:  # the walker's tiles alone, at 512 px, for looking closely
        tile.resize((512, 512), Image.Resampling.NEAREST).save(FIG / f"quirks_tile_{scene[:25]}.png", optimize=True)


def resolution_paris(tok: str) -> None:
    """The Paris cell of the e09 walkers (Major TOM 543U_17R, Sentinel-2, 22 Sep 2020) against Landsat 1 on 21 Sep 1976 (L1TP) and on
    30 Apr 1976 (L1GS: the same coordinates, systematic geometry), each as the 10.68 km cell, the walker's 2.67 km eye (the 64 px crop of
    the 256 px tile) and the 32 x 32 px the network gets."""
    import pandas as pd
    from rasterio.warp import transform as warp

    idx = pd.read_parquet(ROOT / "data" / "global" / "index.parquet", columns=["idx", "grid_cell", "lat", "lon", "timestamp"])
    r = idx[idx.grid_cell == "543U_17R"].iloc[0]
    s2 = Image.open(io.BytesIO((ROOT / "data" / "global" / "cache" / "png" / str(r.idx // 10000) / f"{r.idx}.png").read_bytes())).convert("RGB")
    panels = [("Sentinel-2 L2A, 22 Sep 2020 (Major TOM 543U_17R): 10 m, 1068 px a cell", s2.resize((CELL * 6, CELL * 6), Image.Resampling.BOX))]
    for scene, lab in (("LM01_L1TP_214026_19760921_02_T2", "Landsat 1 MSS, 21 Sep 1976, L1TP: 60 m (79 m native), 178 px a cell"),
                       ("LM01_L1GS_214026_19760430_02_T2", "Landsat 1 MSS, 30 Apr 1976, L1GS: same coordinates, systematic geometry")):
        it = requests.get(ITEM.format(scene), timeout=120).json()
        (x,), (y,) = warp("EPSG:4326", f"EPSG:{it['properties']['proj:epsg']}", [r.lon], [r.lat])
        w = read(scene, tok, centre_xy=(x, y), size=CELL)
        panels.append((lab, u8(cir(w, False))))
    D = 356  # display px per panel
    rows = []
    for lab, im in panels:
        n = im.size[0]
        cell = im.resize((D, D), Image.Resampling.NEAREST if n < D else Image.Resampling.BOX)
        tile = im.resize((256, 256), Image.Resampling.BILINEAR if n < 256 else Image.Resampling.BOX)  # the walker's tile
        eye = tile.crop((96, 96, 160, 160))  # a 64 px crop at the centre: the walker's eye, 2.67 km
        rows.append((lab, cell, eye.resize((D, D), Image.Resampling.NEAREST), eye.resize((32, 32), Image.Resampling.BOX).resize((D, D), Image.Resampling.NEAREST)))
    pad, head = 14, 18
    S = Image.new("RGB", (3 * D + 2 * 8 + 2 * pad, len(rows) * (D + head + pad) + 58), (252, 252, 251))
    d = ImageDraw.Draw(S)
    d.text((pad, 10), "Paris, the e09 walkers' start. Columns: the 10.68 km cell  |  the walker's eye (64 px crop of the 256 px tile, 2.67 km)  |  "
                      "what the network gets (that crop at 32 x 32).", fill=INK)
    d.text((pad, 24), "Sentinel-2 shown in the archive's true colour; Landsat 1 in CIR (nir / red / green), e10's tone and stretch. "
                      "Pixels shown without smoothing.", fill=INK)
    d.text((pad, 38), "At 32 x 32 px the network sees ~83 m per pixel: finer than MSS's 79 m only just, far coarser than Sentinel-2's 10 m.", fill=INK)
    y = 58
    for lab, a, b, c in rows:
        d.text((pad, y), lab, fill=INK)
        for k, im in enumerate((a, b, c)):
            S.paste(im, (pad + k * (D + 8), y + head))
        y += D + head + pad
    S.save(FIG / "resolution_paris.png", optimize=True)


def offset_paris(tok: str) -> None:
    """The L1GS geolocation offset over Paris: phase correlation of nir08 between the L1TP (21 Sep 1976) and L1GS (30 Apr 1976) scenes
    in a 1536 px (92 km) window centred on the Paris cell's coordinates, then the cell at those coordinates in L1TP, in L1GS, and in L1GS
    moved by the measured shift."""
    import pandas as pd
    from rasterio.warp import transform as warp

    idx = pd.read_parquet(ROOT / "data" / "global" / "index.parquet", columns=["grid_cell", "lat", "lon"])
    r = idx[idx.grid_cell == "543U_17R"].iloc[0]
    W = {}
    for sc in ("LM01_L1TP_214026_19760921_02_T2", "LM01_L1GS_214026_19760430_02_T2"):
        it = requests.get(ITEM.format(sc), timeout=120).json()
        (x,), (y,) = warp("EPSG:4326", f"EPSG:{it['properties']['proj:epsg']}", [r.lon], [r.lat])
        W[sc] = read(sc, tok, centre_xy=(x, y), size=1536)
    tp, gs = W["LM01_L1TP_214026_19760921_02_T2"], W["LM01_L1GS_214026_19760430_02_T2"]
    a, b = (w["nir08"].astype(float) for w in (tp, gs))
    a, b = a - a.mean(), b - b.mean()
    F = np.fft.fft2(a) * np.conj(np.fft.fft2(b))
    c = np.fft.ifft2(F / np.maximum(np.abs(F), 1e-9)).real
    dy, dx = np.unravel_index(c.argmax(), c.shape)
    dy, dx = (dy - 1536 if dy > 768 else dy), (dx - 1536 if dx > 768 else dx)
    c0 = 768 - CELL // 2
    A = tp["nir08"][c0 : c0 + CELL, c0 : c0 + CELL].astype(float)
    r0, cc = c0 - dy, c0 - dx
    B = gs["nir08"][r0 : r0 + CELL, cc : cc + CELL].astype(float)
    rho = np.corrcoef(A.ravel(), B.ravel())[0, 1]
    rho0 = np.corrcoef(A.ravel(), gs["nir08"][c0 : c0 + CELL, c0 : c0 + CELL].astype(float).ravel())[0, 1]
    km = 60 * np.hypot(dy, dx) / 1000
    D = 356
    ims = [u8(cir(tp, False)[c0 : c0 + CELL, c0 : c0 + CELL]), u8(cir(gs, False)[c0 : c0 + CELL, c0 : c0 + CELL]),
           u8(cir(gs, False)[r0 : r0 + CELL, cc : cc + CELL])]
    labs = ["L1TP, 21 Sep 1976, at Paris's coordinates", "L1GS, 30 Apr 1976, at Paris's coordinates",
            f"L1GS moved {-dy * 60 / 1000:+.1f} km N, {-dx * 60 / 1000:+.1f} km E"]
    S = Image.new("RGB", (3 * D + 2 * 8 + 28, D + 70), (252, 252, 251))
    d = ImageDraw.Draw(S)
    d.text((14, 8), f"Geolocation of a systematic (L1GS) scene: Paris is drawn {km:.1f} km from where it is. Phase correlation (nir, 92 km window): "
                    f"shift {-dy} rows, {-dx} cols of 60 m; cell correlation {rho:.2f} moved, {rho0:.2f} in place.", fill=INK)
    for k, (im, lab) in enumerate(zip(ims, labs)):
        d.text((14 + k * (D + 8), 28), lab, fill=INK)
        S.paste(im.resize((D, D), Image.Resampling.NEAREST), (14 + k * (D + 8), 46))
    S.save(FIG / "offset_paris.png", optimize=True)
    print(f"offset {km:.1f} km, rows {-dy}, cols {-dx}, rho {rho:.2f} (in place {rho0:.2f})")


if __name__ == "__main__":
    import sys

    FIG.mkdir(parents=True, exist_ok=True)
    t = token()
    if "--resolution-only" not in sys.argv:
        quirk_sheet(t)
    resolution_paris(t)
    offset_paris(t)
