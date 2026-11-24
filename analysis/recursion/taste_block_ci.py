"""Taste intervals with a moving-block bootstrap, for the latent walks of every generation (owed since the G2 latent report).

The G2-G4 latent reports used an iid bootstrap over steps (analysis/gen1/latent_taste_ci.py) and called it "too narrow" because the
Null's interval sometimes cleared zero although its choice is uniform. This script checks that claim: the per-step gap
d_t = chosen - mean(offered) (compass offers, colour and texture statistics of the 128 px renders) is resampled
- iid over steps (as before),
- in moving blocks of 50 and of 200 consecutive steps (keeps the walk's autocorrelation),
and reports the lag-1 autocorrelation of d_t. If the block intervals are no wider than the iid ones, the steps' gaps are nearly
independent and the Null's exclusions are what 9 statistics x several walks give by chance at 95 %. Nothing in the walks changes.

    .venv/Scripts/python.exe analysis/recursion/taste_block_ci.py   ->  notes/recursion/taste_block_ci.csv
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
STATS = ["brightness", "white_share", "black_share", "green_band_dark", "mean_r_nir", "mean_g_red", "mean_b_green", "grad", "row_roughness"]
BOOT = 2000


def block_boot(d: np.ndarray, L: int, rng) -> np.ndarray:
    n = len(d)
    k = int(np.ceil(n / L))
    starts = rng.integers(0, n - L + 1, size=(BOOT, k))
    idx = (starts[:, :, None] + np.arange(L)[None, None, :]).reshape(BOOT, -1)[:, :n]
    return d[idx].mean(1)


def main() -> None:
    rng = np.random.default_rng(0)
    rows = []
    for g in range(1, 20):
        for cond in ("curious", "null"):
            f = ROOT / "runs" / f"g{g}" / "latent" / cond / "offers.parquet"
            if not f.exists():
                continue
            o = pd.read_parquet(f)
            o = o[o.kind == "compass"]
            for st in STATS:
                v = o[st].astype(float)
                d = (v[o.chosen.to_numpy()].groupby(o.step[o.chosen]).mean() - v.groupby(o.step).mean()).dropna().sort_index().to_numpy()
                iid = np.array([rng.choice(d, len(d)).mean() for _ in range(BOOT)])
                b50, b200 = block_boot(d, 50, rng), block_boot(d, 200, rng)
                ac1 = np.corrcoef(d[:-1], d[1:])[0, 1] if d.std() > 0 else np.nan
                r = {"gen": g, "cond": cond, "stat": st, "gap": d.mean(), "lag1_autocorr": ac1}
                for name, bs in (("iid", iid), ("block50", b50), ("block200", b200)):
                    lo, hi = np.percentile(bs, [2.5, 97.5])
                    r[f"{name}_lo"], r[f"{name}_hi"] = lo, hi
                    r[f"{name}_excl0"] = bool(lo > 0 or hi < 0)
                r["width_ratio_block200_iid"] = (r["block200_hi"] - r["block200_lo"]) / max(r["iid_hi"] - r["iid_lo"], 1e-12)
                rows.append(r)
            print(g, cond, flush=True)
    df = pd.DataFrame(rows)
    out = ROOT / "notes" / "recursion" / "taste_block_ci.csv"
    df.to_csv(out, index=False, float_format="%.5f")
    s = df.groupby("cond")[["iid_excl0", "block50_excl0", "block200_excl0"]].sum()
    s["n"] = df.groupby("cond").size()
    print(s.to_string())
    print("median lag-1 autocorr:", df.groupby("cond").lag1_autocorr.median().round(3).to_dict())
    print("median width ratio block200/iid:", df.groupby("cond").width_ratio_block200_iid.median().round(2).to_dict())


if __name__ == "__main__":
    main()
