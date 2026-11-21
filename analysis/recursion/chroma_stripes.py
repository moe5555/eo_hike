"""Chromatic stripes across the recursion: a statistic added after looking at the G3 samples (2026-11-21), post hoc, not a test.

Why: the existing banding statistic (row_roughness in gen/g1_gan.py) differences the brightness averaged along each pixel row. The scan
lines in the G3-curious samples are coloured (one band at a time) and run at an angle to the pixel rows, so both the brightness
average and the row average wash them out. This script leaves row_roughness unchanged and adds, labelled as colour and texture
statistics of the rendered 128 px images:
- chroma_y: mean |vertical difference| of each channel minus brightness (luma), averaged over the three channels;
- chroma_x: the same, horizontal;
- chroma_aniso: chroma_y / chroma_x (stripes that run near the horizontal raise it above 1; terrain edges keep it near 1).
Terrain colour edges contribute too: compare sets, not absolute values.

Sets per condition: the real G1 package (paths/g1/<cond>), each later package (paths/g<g>/<cond>, the latent walk that trained G<g>),
and each generation's samples (runs/g<g>/gan/<cond>/samples, psi 1, the same seeds). n = 2,000 per set (seed 0 draw; samples 0-1999).

    scripts/sg.bat analysis/recursion/chroma_stripes.py   ->  notes/recursion/chroma_stripes.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notes" / "recursion"
N = 2000


def read(files):
    return np.stack([np.asarray(Image.open(f).convert("RGB")) for f in files]).astype(np.float32)


def stats(a: np.ndarray) -> dict:
    luma = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    ch = a - luma[..., None]
    cy = np.abs(np.diff(ch, axis=1)).mean((1, 2, 3))
    cx = np.abs(np.diff(ch, axis=2)).mean((1, 2, 3))
    return {"chroma_y": float(cy.mean()), "chroma_x": float(cx.mean()), "chroma_aniso": float((cy / np.maximum(cx, 1e-6)).mean()),
            "chroma_y_p90": float(np.percentile(cy, 90))}


def main() -> None:
    rows = []
    for cond in ("curious", "null"):
        for g in range(1, 20):
            pk = ROOT / "paths" / f"g{g}" / cond / "tiles"
            if pk.exists():
                files = sorted(pk.glob("*.png"))
                pick = np.sort(np.random.default_rng(0).choice(len(files), min(N, len(files)), replace=False))
                rows.append({"cond": cond, "gen": g, "set": "package (trained G%d)" % g, **stats(read([files[i] for i in pick]))})
            sd = ROOT / "runs" / f"g{g}" / "gan" / cond / "samples"
            if sd.exists() and (sd / f"seed{N - 1:05d}.png").exists():
                rows.append({"cond": cond, "gen": g, "set": "samples G%d" % g, **stats(read([sd / f"seed{s:05d}.png" for s in range(N)]))})
            print(cond, g, flush=True)
    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "chroma_stripes.csv", index=False, float_format="%.4f")
    print(df.to_string(index=False, float_format=lambda v: f"{v:.3f}"))


if __name__ == "__main__":
    sys.exit(main())
