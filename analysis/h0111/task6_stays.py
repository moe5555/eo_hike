"""Task 6, second look: what decides whether a teleport landing is kept, and where in a walk the rejections fall.

    python analysis/h0111/task6_stays.py

Writes task6_stays.csv (one row per teleport), task6_stays_summary.csv, task6_when.csv and task3_freshness.csv.

A landing is "rejected" as in compare.py: its place lasted at most BURST_GAP steps and ended with another teleport. Landings in the last
BURST_GAP steps of a walk are left out of the rejected share, because the walk ended before they could be kept or rejected.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from common import OUT, RUNS, places, steps
from compare import BURST_GAP, GROUPS, SEEDS
from data.tile_store import TileStore

LOOK = 5  # steps after a landing used for "was anything nearby interesting?"; the shortest possible Bored stay
EARLY = 150


def landings_of(run: str, store: TileStore) -> pd.DataFrame:
    s = steps(run)
    p = places(s)
    ends = p.groupby("place").bored_event.last()
    cover = store.idx.cover.to_numpy()
    k = RUNS / run / "landings.parquet"
    chosen = pd.read_parquet(k).query("landed").set_index("step").n if k.exists() else pd.Series(dtype=float)
    rows = []
    for _, r in p[p.jump_type == "bored"].iterrows():
        after = p[(p.place == r.place) & (p.step <= r.step + LOOK)]
        g = store.get_lowres(int(r.tile_idx)).astype(float).mean(2)
        gy, gx = np.gradient(g)
        rows.append({"run": run, "step": int(r.step), "stay": int(r.place_len), "ended_by_teleport": bool(ends[r.place]), "censored": bool(r.step + BURST_GAP >= s.step.max()),
                     "rejected": bool(r.place_len <= BURST_GAP and ends[r.place]), "ocean": bool(cover[int(r.tile_idx)] == "ocean"), "grad": float(np.hypot(gx, gy).mean()),
                     "n_landing": float(chosen.get(int(r.step), np.nan)), "nothing_interesting": float((after.max_I < 0).mean())})
    return pd.DataFrame(rows)


def freshness(run: str) -> dict:
    """How often the walker stands among neighbours it has never stood on, and how often nothing on offer beats the recent baseline."""
    s = steps(run)
    c = pd.read_parquet(RUNS / run / "candidates.parquet")
    c = c[(c.kind == "neighbour") & (c.step >= 50)]
    first = s.drop_duplicates("tile_idx").set_index("tile_idx").step
    seen = c.tile_idx.map(first).fillna(np.inf).to_numpy() < c.step.to_numpy()
    p = s[s.step >= 50]
    return {"run": run, "neighbours_never_visited": 1 - seen.mean(), "bored_step_share": (p.max_I < 0).mean(), "mean_max_I": p.max_I.mean(), "mean_chosen_n_z": p.n_z.mean(), "mean_offered_n_z": c.n_z.mean()}


def main() -> None:
    store = TileStore()
    t = []
    for g, stem in GROUPS.items():
        for sd in SEEDS:
            d = landings_of(f"{stem}_s{sd}", store)
            t.append(d.assign(group=g, seed=sd))
    t = pd.concat([d for d in t if len(d)], ignore_index=True)  # a walk without a teleport has no rows
    t.to_csv(OUT / "task6_stays.csv", index=False)

    def summary(x: pd.DataFrame) -> pd.Series:
        y = x[~x.censored]
        kept, rej = y[~y.rejected], y[y.rejected]
        return pd.Series({"landings": len(x), "rejected_share": y.rejected.mean(), "ocean_of_rejected": rej.ocean.mean(), "ocean_of_kept": kept.ocean.mean(), "grad_rejected": rej.grad.median(), "grad_kept": kept.grad.median(),
                          "n_rejected": rej.n_landing.median(), "n_kept": kept.n_landing.median(), "nothing_interesting_rejected": rej.nothing_interesting.mean(), "nothing_interesting_kept": kept.nothing_interesting.mean(),
                          "stay_vs_grad": y.stay.corr(y.grad, method="spearman"), "stay_vs_n": y.stay.corr(y.n_landing, method="spearman"), "first_150_share": (x.step < EARLY).mean()})

    s = pd.DataFrame({g: summary(x) for g, x in t.groupby("group", sort=False)}).T.round(3)
    s.to_csv(OUT / "task6_stays_summary.csv")
    with pd.option_context("display.width", 250, "display.max_columns", 40):
        print(s.T.to_string())
        w = t.assign(when=pd.cut(t.step, [0, EARLY, 500, 1000], labels=[f"<{EARLY}", f"{EARLY}-500", "500-1000"])).groupby(["group", "when"], sort=False, observed=True).agg(landings=("step", "size"), rejected=("rejected", "mean"), median_stay=("stay", "median")).round(2)
        w.to_csv(OUT / "task6_when.csv")
        print(w.to_string())
        f = pd.DataFrame([freshness(f"{GROUPS[g]}_s{sd}") | {"group": g, "seed": sd} for g in ("Null", "Reference") for sd in SEEDS])
        f.to_csv(OUT / "task3_freshness.csv", index=False)
        print(f.round(3).drop(columns="run").to_string())


if __name__ == "__main__":
    main()
