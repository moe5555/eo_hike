"""Chosen minus offered, per step, for the G<gen> latent walks: mean and a bootstrap 95 % interval over steps (compass offers only).

Colour and texture statistics of the 128 px renders, labelled as such (not the quirk detectors). The interval describes one walk:
steps are resampled, so it says how stable the gap is within the walk, not across walks or GANs (one walk per condition: hints).

    python analysis/gen1/latent_taste_ci.py [--gen 1]  ->  notes/gen<gen>/latent/taste_ci.csv
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
STATS = ["brightness", "white_share", "black_share", "green_band_dark", "mean_r_nir", "mean_g_red", "mean_b_green", "grad", "row_roughness"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", type=int, default=1)
    ap.add_argument("--boot", type=int, default=2000)
    a = ap.parse_args()
    rng = np.random.default_rng(0)
    rows = []
    for cond in ("curious", "null"):
        o = pd.read_parquet(ROOT / "runs" / f"g{a.gen}" / "latent" / cond / "offers.parquet")
        o = o[o.kind == "compass"]
        for st in STATS:
            v = o[st].astype(float)
            d = (v[o.chosen.to_numpy()].groupby(o.step[o.chosen]).mean() - v.groupby(o.step).mean()).dropna().to_numpy()
            bs = np.array([rng.choice(d, len(d)).mean() for _ in range(a.boot)])
            rows.append({"cond": cond, "stat": st, "chosen_minus_offered": d.mean(), "ci_lo": np.percentile(bs, 2.5), "ci_hi": np.percentile(bs, 97.5),
                         "sd_offered": v.std(), "gap_in_sd": d.mean() / v.std() if v.std() > 0 else np.nan, "n_steps": len(d)})
    out = ROOT / "notes" / f"gen{a.gen}" / "latent" / "taste_ci.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(pd.DataFrame(rows).round(5).to_string(index=False))


if __name__ == "__main__":
    main()
