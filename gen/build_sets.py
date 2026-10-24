"""Path -> three equal-size training sets with per-tile weights.

    python -m gen.build_sets runs/baseline_s0                    # alpha_s=1, alpha_b=0.5
    python -m gen.build_sets runs/baseline_s0 --alpha_b -0.5     # the other reading of "weighted by boredom"

Per unique visited tile i (first visit): surprise_i = z-scored e, boredom_i = B on arrival,
w_i = clip(exp(alpha_s * surprise_i - alpha_b * boredom_i), 0.2, 5.0).
Noisy-TV tiles are not Earth and are dropped from all sets (count printed and saved).

Writes data/sets/<run_id>[_tag]/sets.parquet with columns set, tile_idx, weight.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def build(run: Path, alpha_s: float, alpha_b: float, seed: int, tag: str | None) -> Path:
    steps = pd.read_parquet(run / "steps.parquet")
    idx = pd.read_parquet(ROOT / "data" / "tiles.parquet")
    first = steps.sort_values("step").drop_duplicates("tile_idx", keep="first")
    n_tv = int(first.tv.sum())
    first = first[~first.tv]
    surprise = first.e_z.to_numpy()
    boredom = first.B.to_numpy()
    w = np.clip(np.exp(alpha_s * surprise - alpha_b * boredom), 0.2, 5.0)
    ids = first.tile_idx.to_numpy()
    rng = np.random.default_rng(seed)
    pool = np.flatnonzero(~idx.tv.to_numpy())
    rand_ids = np.sort(rng.choice(pool, size=len(ids), replace=False))
    sets = pd.concat(
        [
            pd.DataFrame({"set": "path_weighted", "tile_idx": ids, "weight": w, "surprise": surprise, "boredom": boredom}),
            pd.DataFrame({"set": "path_uniform", "tile_idx": ids, "weight": 1.0}),
            pd.DataFrame({"set": "random_uniform", "tile_idx": rand_ids, "weight": 1.0}),
        ],
        ignore_index=True,
    )
    out = ROOT / "data" / "sets" / (run.name + (f"_{tag}" if tag else ""))
    out.mkdir(parents=True, exist_ok=True)
    sets.to_parquet(out / "sets.parquet")
    info = {
        "run": run.name, "alpha_s": alpha_s, "alpha_b": alpha_b, "seed": seed, "n_tiles": int(len(ids)), "n_tv_dropped": n_tv,
        "weight_min": float(w.min()), "weight_max": float(w.max()), "weight_mean": float(w.mean()),
        "frac_clipped_low": float((w <= 0.2).mean()), "frac_clipped_high": float((w >= 5.0).mean()),
        "effective_n": float(w.sum() ** 2 / (w**2).sum()),
        "overlap_path_random": int(len(np.intersect1d(ids, rand_ids))),
    }
    (out / "info.json").write_text(json.dumps(info, indent=2))
    print(json.dumps(info, indent=2))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--alpha_s", type=float, default=1.0)
    ap.add_argument("--alpha_b", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tag")
    a = ap.parse_args()
    build(a.run, a.alpha_s, a.alpha_b, a.seed, a.tag)
