"""Contact sheet of a two-eye walk (notes/brief_landsat_pipeline.md, E16): every visited tile in its one view, the top crop outlined,
and the step's interest decomposition.

    python analysis/e12/contact_sheet.py runs/e12_mission_smoke_s0 [--per-page 100]

Pages go to runs/<run>/contact/page_NN.png (git-ignored); the first page, at half size, to notes/12_two_eye/results/<run>_contact_p1.png.
Each step: the tile as the walker saw it (the store's render, no other stretch), the top crop (most novel of the 16) outlined in
white over black, and under it three bars, the shares of |contribution| to interest at the choice: glance (blue), grid (orange),
progress (green). The label is the step, the radius of the offers, the acquisition date (and, under the revisit rule, which acquisition
of the cell, #1 = the earliest); night images say so.
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


def sheet(store, page: pd.DataFrame, title: str, th: int = TH, cols: int = 10) -> Image.Image:
    """One contact sheet of the steps in `page` (rows of steps.parquet, or the walker's step records during a walk). Under the clock
    rule (brief v2) the label is the step, the radius (or WAIT for a time offer), the tile's date and its offset from the clock."""
    idx = store.idx
    bar, lab = max(4, BAR * th // TH), LAB
    rows = int(np.ceil(len(page) / cols))
    cw, ch = th + PAD, th + bar + 2 * lab + PAD
    S = Image.new("RGB", (cols * cw + PAD, rows * ch + PAD + 22), BG)
    d = ImageDraw.Draw(S)
    d.text((PAD, 5), title, fill=INK)
    for k, r in enumerate(page.itertuples()):
        x0, y0 = PAD + (k % cols) * cw, 22 + PAD + (k // cols) * ch
        img_id = int(r.image_key) if hasattr(r, "image_key") else int(r.tile_idx)  # the revisit rule: the image this step showed
        tile = Image.fromarray(store.get_lowres(img_id)).resize((th, th), Image.Resampling.BILINEAR)
        S.paste(tile, (x0, y0))
        q = th // 4
        ty, tx = divmod(int(r.top_crop), 4)
        d.rectangle((x0 + tx * q, y0 + ty * q, x0 + (tx + 1) * q - 1, y0 + (ty + 1) * q - 1), outline=(0, 0, 0), width=max(1, 3 * th // TH))
        d.rectangle((x0 + tx * q + 1, y0 + ty * q + 1, x0 + (tx + 1) * q - 2, y0 + (ty + 1) * q - 2), outline=(255, 255, 255), width=1)
        bx = x0
        for nm in ("glance", "grid", "prog"):
            v = getattr(r, f"share_{nm}")
            w = 0 if not np.isfinite(v) else int(round(v * th))
            d.rectangle((bx, y0 + th + 2, bx + w, y0 + th + bar), fill=COL[nm])
            bx += w
        row = idx.loc[int(r.tile_idx)] if "timestamp" in idx else None
        if hasattr(r, "tile_date"):  # the clock rule: the tile's date, and its offset from the clock
            move = "WAIT" if r.offer_kind == "time" else f"{r.r_km:.0f} km"
            off = f" {int(r.offset_days):+d}d" if int(r.offset_days) else ""
            d.text((x0, y0 + th + bar + 2), f"{r.step} {move}", fill=INK)
            d.text((x0, y0 + th + bar + 2 + lab), f"{r.tile_date}{off}{' N' if r.night else ''}", fill=(107, 106, 99))
            continue
        if hasattr(r, "acq_date"):  # the acquisition the step showed, as the walk logged it
            when, night, level, rank = str(pd.Timestamp(r.acq_date).date()), bool(r.acq_night), r.acq_level, f" #{int(r.acq_rank) + 1}"
        else:
            when = "" if row is None else str(pd.Timestamp(row.timestamp).date())
            night = row is not None and bool(row.get("night", False))
            level, rank = (row.level if row is not None and "level" in idx else ""), ""
        d.text((x0, y0 + th + bar + 2), f"{r.step}  {r.r_km:.0f} km  {when}{rank}{'  NIGHT' if night else ''}", fill=INK)
        if row is not None:
            d.text((x0, y0 + th + bar + 2 + lab), f"{level} {row.grid_cell}", fill=(107, 106, 99))
    return S


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
    out = run / "contact"
    out.mkdir(exist_ok=True)
    first = None
    for p0 in range(0, len(s), a.per_page):
        page = s.iloc[p0 : p0 + a.per_page]
        S = sheet(store, page, f"{run.name}: steps {p0}-{p0 + len(page) - 1}. Outline: top crop. Bars: share of interest at the choice, "
                               f"glance (blue) / grid (orange) / progress (green).")
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
