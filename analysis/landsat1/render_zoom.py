"""One place at several zoom levels: where Landsat 1 MSS starts to look sharp (research, notes/11_landsat1_mission/research.md).

    python analysis/landsat1/render_zoom.py

Per place, frames of 1080 x 1080 px (the height of a 1080p frame) showing a square of ground from the walker's eye (2.67 km = 45 native
60 m px, enlarged x24) to 64.8 km (1080 px: one data pixel per screen pixel). Enlargement with Lanczos, as a film would; rendering as
render_quirks.py (TOA, sqrt, e10's stretch, CIR). Full frames go to data/landsat/zoom/ (git-ignored); the sheet
notes/11_landsat1_mission/figures/zoom_levels.png shows, per place and zoom, the whole frame shrunk (what it covers) and its central
300 px at screen size (what a viewer sees of the pixels).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_quirks as R  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "landsat" / "zoom"
FRAME = 1080
NATIVE_M = 60.0
WIDTHS_PX = (45, 89, 178, 360, 540, 1080)  # native 60 m px across the frame: eye, 2 x eye, cell, 2 cells, 3 cells, 1:1
DETAIL, SMALL = 300, 300


def places():
    idx = pd.read_parquet(ROOT / "data" / "global" / "index.parquet", columns=["grid_cell", "lat", "lon"])
    paris = idx[idx.grid_cell == "543U_17R"].iloc[0]
    return [("Paris, 21 Sep 1976 (L1TP; haze over the city)", "LM01_L1TP_214026_19760921_02_T2", (paris.lon, paris.lat)),
            ("Eastern Desert, 23° N 34.5° E, 14 May 1975 (Tier 1, scene centre)", "LM01_L1TP_186044_19750514_02_T1", None)]


def main() -> None:
    from rasterio.warp import transform as warp

    OUT.mkdir(parents=True, exist_ok=True)
    tok = R.token()
    rows = []
    for label, scene, lonlat in places():
        xy = None
        if lonlat is not None:
            it = requests.get(R.ITEM.format(scene), timeout=120).json()
            (x,), (y,) = warp("EPSG:4326", f"EPSG:{it['properties']['proj:epsg']}", [lonlat[0]], [lonlat[1]])
            xy = (x, y)
        w = R.read(scene, tok, centre_xy=xy, size=FRAME)
        img = R.cir(w, False)
        frames = []
        for n in WIDTHS_PX:
            c0 = (FRAME - n) // 2
            fr = R.u8(img[c0 : c0 + n, c0 : c0 + n]).resize((FRAME, FRAME), Image.Resampling.LANCZOS)
            km = n * NATIVE_M / 1000
            fr.save(OUT / f"{scene[:25]}_{km:05.1f}km.png", optimize=True)
            frames.append((km, FRAME / n, fr))
            print(scene, f"{km:.1f} km  x{FRAME / n:.1f}", flush=True)
        rows.append((label, frames))
    gap, pad, head = 8, 14, 34
    W = len(WIDTHS_PX) * (SMALL + gap) - gap + 2 * pad
    S = Image.new("RGB", (W, 62 + len(rows) * (2 * (SMALL + 6) + head + 28)), (252, 252, 251))
    d = ImageDraw.Draw(S)
    d.text((pad, 10), "Landsat 1 MSS at six zoom levels. Each column is one 1080 x 1080 frame: the ground across it, and how much each 60 m data pixel is enlarged.",
           fill=R.INK)
    d.text((pad, 24), "Upper row: the whole frame, shrunk to 300 px (what it covers). Lower row: its central 300 px at screen size (how sharp it looks "
                      "on a 1080p screen).", fill=R.INK)
    d.text((pad, 38), "Enlarged with Lanczos. CIR (nir / red / green), e10's tone and stretch. MSS saw ~79 m; below about x2 the frame shows the data, "
                      "above it the interpolation.", fill=R.INK)
    y = 62
    for label, frames in rows:
        d.text((pad, y), label, fill=R.INK)
        y += 18
        for k, (km, f, fr) in enumerate(frames):
            x = pad + k * (SMALL + gap)
            d.text((x, y), f"{km:.1f} km across, x{f:.1f}" + ("  (the walker's eye)" if k == 0 else "  (one cell)" if k == 2 else "  (1:1)" if f == 1 else ""),
                   fill=(107, 106, 99))
            S.paste(fr.resize((SMALL, SMALL), Image.Resampling.BOX), (x, y + 16))
            c = (FRAME - DETAIL) // 2
            S.paste(fr.crop((c, c, c + DETAIL, c + DETAIL)), (x, y + 16 + SMALL + 6))
        y += 16 + 2 * (SMALL + 6) + 24
    out = ROOT / "notes" / "11_landsat1_mission" / "figures" / "zoom_levels.png"
    S.save(out, optimize=True)
    print("sheet", out)


if __name__ == "__main__":
    main()
