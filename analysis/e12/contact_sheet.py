"""Contact sheet of a two-eye walk (notes/brief_landsat_pipeline.md, E16): every visited tile in its one view, the top crop outlined,
and the step's interest decomposition.

    python analysis/e12/contact_sheet.py runs/e12_mission_smoke_s0 [--per-page 100]

Pages go to runs/<run>/contact/page_NN.png (git-ignored); the first page, at half size, to notes/12_two_eye/results/<run>_contact_p1.png.
Each step: the tile as the walker saw it (the store's render, no other stretch), the top crop (most novel of the 16) outlined in
white over black, and under it three bars, the shares of |contribution| to interest at the choice: glance (blue), grid (orange),
progress (green). The label is the step, the radius of the offers and the acquisition date; night cells say so.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
TH, BAR, LAB, PAD = 192, 12, 13, 6
COL = {"glance": (58, 110, 165), "grid": (208, 138, 44), "prog": (76, 145, 84)}
INK, BG = (43, 43, 42), (250, 250, 248)


def main() -> None:
    from data.tile_store import open_store

    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--per-page", type=int, default=100)
    a = ap.parse_args()
    run = Path(a.run)
    cfg = yaml.safe_load((run / "config.yaml").read_text())
    s = pd.read_parquet(run / "steps.parquet")
    store = open_store(cfg)
    idx = store.idx
    out = run / "contact"
    out.mkdir(exist_ok=True)
    cols = 10
    first = None
    for p0 in range(0, len(s), a.per_page):
        page = s.iloc[p0 : p0 + a.per_page]
        rows = int(np.ceil(len(page) / cols))
        cw, ch = TH + PAD, TH + BAR + 2 * LAB + PAD
        S = Image.new("RGB", (cols * cw + PAD, rows * ch + PAD + 22), BG)
        d = ImageDraw.Draw(S)
        d.text((PAD, 5), f"{run.name}: steps {p0}-{p0 + len(page) - 1}. Outline: top crop. Bars: share of interest at the choice, "
                         f"glance (blue) / grid (orange) / progress (green).", fill=INK)
        for k, r in enumerate(page.itertuples()):
            x0, y0 = PAD + (k % cols) * cw, 22 + PAD + (k // cols) * ch
            tile = Image.fromarray(store.get_lowres(int(r.tile_idx))).resize((TH, TH), Image.Resampling.BILINEAR)
            S.paste(tile, (x0, y0))
            q = TH // 4
            ty, tx = divmod(int(r.top_crop), 4)
            d.rectangle((x0 + tx * q, y0 + ty * q, x0 + (tx + 1) * q - 1, y0 + (ty + 1) * q - 1), outline=(0, 0, 0), width=3)
            d.rectangle((x0 + tx * q + 1, y0 + ty * q + 1, x0 + (tx + 1) * q - 2, y0 + (ty + 1) * q - 2), outline=(255, 255, 255), width=1)
            bx = x0
            for nm in ("glance", "grid", "prog"):
                v = getattr(r, f"share_{nm}")
                w = 0 if not np.isfinite(v) else int(round(v * TH))
                d.rectangle((bx, y0 + TH + 2, bx + w, y0 + TH + BAR), fill=COL[nm])
                bx += w
            row = idx.loc[int(r.tile_idx)] if "timestamp" in idx else None
            when = "" if row is None else str(pd.Timestamp(row.timestamp).date())
            night = row is not None and bool(row.get("night", False))
            d.text((x0, y0 + TH + BAR + 2), f"{r.step}  {r.r_km:.0f} km  {when}{'  NIGHT' if night else ''}", fill=INK)
            if row is not None and "level" in idx:
                d.text((x0, y0 + TH + BAR + 2 + LAB), f"{row.level} {row.grid_cell}", fill=(107, 106, 99))
        pth = out / f"page_{p0 // a.per_page + 1:02d}.png"
        S.save(pth, optimize=True)
        print(pth)
        if first is None:
            first = S
    res = ROOT / "notes" / "12_two_eye" / "results"
    res.mkdir(parents=True, exist_ok=True)
    first.resize((first.width // 2, first.height // 2), Image.Resampling.LANCZOS).save(res / f"{run.name}_contact_p1.png", optimize=True)


if __name__ == "__main__":
    main()
