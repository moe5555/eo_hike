"""Do the latent walks dwell on chromatic stripes? Post hoc (2026-11-21), after chroma_stripes.py showed the packages to be stripier
than the GAN they were walked in.

For each latent walk (runs/g<g>/latent/<cond>), per step: chroma_y of the tile it stands on (see chroma_stripes.py), its interest I,
and the offer radius alpha of the next step. Spearman correlations, and the share of steps at alpha_min and at 90 degrees for tiles in
the top and bottom fifth of chroma_y. The radius rule is a premise (set by hand); the correlation is what emerged.
Steps are autocorrelated: correlations describe the walk, they are not tests.

    .venv/Scripts/python.exe analysis/recursion/stripes_in_walks.py   ->  notes/recursion/stripes_in_walks.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notes" / "recursion"


def chroma_y(f: Path) -> float:
    a = np.asarray(Image.open(f).convert("RGB")).astype(np.float32)
    luma = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    return float(np.abs(np.diff(a - luma[..., None], axis=0)).mean())


def main() -> None:
    rows = []
    gens = [int(x) for x in sys.argv[1:]] or list(range(1, 20))
    for g in gens:
        for cond in ("curious", "null"):
            d = ROOT / "runs" / f"g{g}" / "latent" / cond
            if not (d / "steps.parquet").exists() or not (d / "walk.json").exists():
                continue
            s = pd.read_parquet(d / "steps.parquet").sort_values("step").reset_index(drop=True)
            s["cy"] = [chroma_y(d / "tiles" / f"k{int(k):06d}_s{int(sn):04d}.png") for k, sn in zip(s["key"], s["snapshot"])]
            s["alpha_next"] = s["alpha_deg"].shift(-1)
            s = s.dropna(subset=["alpha_next"])
            amin = s["alpha_deg"].min()
            q20, q80 = s["cy"].quantile([0.2, 0.8])
            lo, hi = s[s.cy <= q20], s[s.cy >= q80]
            rows.append({
                "gen": g, "cond": cond, "steps": len(s), "alpha_min": round(amin, 2),
                "rho_cy_I": s["cy"].corr(s["I"], method="spearman"),
                "rho_cy_alpha_next": s["cy"].corr(s["alpha_next"], method="spearman"),
                "at_min_next_top20": (hi["alpha_next"] <= amin + 1e-6).mean(), "at_min_next_bottom20": (lo["alpha_next"] <= amin + 1e-6).mean(),
                "at_90_next_top20": (hi["alpha_next"] >= 89.99).mean(), "at_90_next_bottom20": (lo["alpha_next"] >= 89.99).mean(),
                "cy_mean": s["cy"].mean(),
            })
            print(rows[-1], flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "stripes_in_walks.csv", index=False, float_format="%.4f")
    print(df.to_string(index=False, float_format=lambda v: f"{v:.3f}"))


if __name__ == "__main__":
    sys.exit(main())
