"""Is novelty high where the walker has never been? (2026-11-11, a question in review; no prediction, a description of one walk.)

    python analysis/e09/novelty_unseen.py [run]          # default e09_v1_long_s0

For the offers of every EVERY-th step from step 500 (and every third step at r >= 1,000 km, so far offers are not too few), the ground
distance from the offered cell to the nearest cell the walker stood on before that step (`gap_km`), and how often it stood on the
offered cell itself (`visits`). Prints the median raw novelty n (agent/signals.novelty: mean distance to the 10 nearest archive latents,
L2-normalised) by gap band, the Spearman rho of gap and n among far offers and by age, and n of near offers by visits.
Then, within a tile: the median novelty of each tile offered both before and after its first visit, and chosen against declined offers.
The across-tile tables are confounded by selection (the walker visits what was novel, and novelty is largely a stable property of a
tile's look); the within-tile comparison is the one that says what a visit does.
Writes notes/09_compass/results/novelty_unseen_<run>.csv (one row per offer read).
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from e09_common import OUT, ROOT, RUNS  # sets sys.path
from scipy.stats import spearmanr
from sklearn.neighbors import BallTree

EVERY = 50
BANDS = [-1, 5, 20, 100, 500, 2000, 20000]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run", nargs="?", default="e09_v1_long_s0")
    a = ap.parse_args()
    ix = pd.read_parquet(ROOT / "data" / "global" / "index.parquet", columns=["idx", "lat", "lon", "cover"]).set_index("idx")
    s = pd.read_parquet(RUNS / a.run / "steps.parquet", columns=["step", "tile_idx", "r_km"])
    c = pd.read_parquet(RUNS / a.run / "candidates.parquet", columns=["step", "tile_idx", "n"]).merge(s[["step", "r_km"]], on="step")
    c = c.join(ix, on="tile_idx")
    seq = s.tile_idx.to_numpy()
    far_steps = sorted(set(c.step[c.r_km >= 1000]))[::3]
    rows = []
    for t in sorted(set(range(500, len(s), EVERY)) | set(far_steps)):
        d = c[c.step == t]
        if d.empty:
            continue
        past = seq[:t]
        tree = BallTree(np.radians(ix.loc[np.unique(past), ["lat", "lon"]].to_numpy()), metric="haversine")
        dist, _ = tree.query(np.radians(d[["lat", "lon"]].to_numpy()), k=1)
        counts = pd.Series(past).value_counts()
        rows.append(d.assign(gap_km=dist[:, 0] * 6371.0, visits=counts.reindex(d.tile_idx).fillna(0).astype(int).to_numpy()))
    r = pd.concat(rows, ignore_index=True)
    r["band"] = pd.cut(r.gap_km, BANDS, labels=["< 5 (stood on)", "5-20", "20-100", "100-500", "500-2,000", "> 2,000"])
    OUT.mkdir(parents=True, exist_ok=True)
    r.drop(columns=["band"]).to_csv(OUT / f"novelty_unseen_{a.run}.csv", index=False)
    print("median novelty by ground distance to the nearest cell stood on (km)")
    print(r.groupby("band", observed=True).n.agg(["count", "median"]).round(3).to_string())
    far, near = r[r.r_km >= 1000], r[r.r_km < 20]
    print(f"far offers (r >= 1,000 km): {len(far)}, Spearman rho(gap, n) {spearmanr(far.gap_km, far.n)[0]:.3f}")
    for lo, hi in ((500, 3000), (3000, 8000), (8000, 10**9)):
        q = r[(r.step >= lo) & (r.step < hi)]
        print(f"steps {lo}-{min(hi, len(s))}: rho(gap, n) {spearmanr(q.gap_km, q.n)[0]:.3f} ({len(q)} offers)")
    print("near offers (r < 20 km): median novelty by prior visits to the offered cell (across tiles: confounded by selection)")
    print(near.groupby(pd.cut(near.visits, [-1, 0, 1, 3, 10, 10**6]), observed=True).n.agg(["count", "median"]).round(3).to_string())
    # within a tile (added 2026-11-11 after review): the same tile offered before and after its first visit, all offers from step 500
    allc = pd.read_parquet(RUNS / a.run / "candidates.parquet", columns=["step", "tile_idx", "n", "chosen"])
    allc = allc[allc.step >= 500].assign(first_visit=lambda d: d.tile_idx.map(s.groupby("tile_idx").step.min()))
    v = allc[allc.first_visit.notna()]
    both = pd.concat([v[v.step <= v.first_visit].groupby("tile_idx").n.median().rename("before"),
                      v[v.step > v.first_visit].groupby("tile_idx").n.median().rename("after")], axis=1).dropna()
    print(f"same tile, before and after its first visit: {len(both)} tiles, median novelty {both.before.median():.3f} -> {both.after.median():.3f},"
          f" lower after in {(both.after < both.before).mean():.2f}")
    print(f"chosen against declined offers: median novelty {allc[allc.chosen].n.median():.3f} against {allc[~allc.chosen].n.median():.3f}")


if __name__ == "__main__":
    main()
