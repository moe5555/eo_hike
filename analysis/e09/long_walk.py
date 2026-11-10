"""The long walk of walker v1 (log 2026-11-10): how the walk changes with age, in blocks of 1,000 steps.

    python analysis/e09/long_walk.py [run] [--against e09_ref_s0]     # default run e09_v1_long_s0

Per block of BLOCK steps (results/long_walk_blocks.csv): share at r_min and r_max, r_max episodes and the longest run at r_max, places
and their median dwell (places that start in the block), median chosen novelty and progress, the drive's SD, the radius of gyration of
the block and of the walk so far, continents, new cells and cells so far, the share of steps onto a cell visited before (any time
earlier in the walk), held-out error at the block's end, and the world-view readouts at the block's end where worldview.csv has them.
Also: the first steps against the walk of the same seed and config at 1,000 steps (`--against`): the step of the first different tile.
Figure: results/long_walk.png. Whole-walk readouts (revisits beyond blind, choice, taste, collapse) come from readouts.py --runs.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
import yaml
from e09_common import OUT, RUNS  # sets sys.path
from fetchcost import continent

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("e09_readouts", OUT.parents[2] / "analysis" / "e09" / "readouts.py")  # e08 has a readouts.py on the path too
_ro = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ro)
gyration_km, place_table, rmax_episodes = _ro.gyration_km, _ro.place_table, _ro.rmax_episodes

BLOCK = 1000


def blocks(run: str) -> pd.DataFrame:
    cfg = yaml.safe_load((RUNS / run / "config.yaml").read_text())
    r_min, r_max = float(cfg["radius_min_km"]), float(cfg["radius_max_km"])
    s = pd.read_parquet(RUNS / run / "steps.parquet")
    h = pd.read_parquet(RUNS / run / "heldout.parquet").set_index("step").heldout_mse
    pl = place_table(s, r_min)
    wv = pd.read_csv(OUT / "worldview.csv") if (OUT / "worldview.csv").exists() else pd.DataFrame(columns=["run", "step"])
    wv = wv[wv.run == run].set_index("step")
    cells = s.grid_cell.to_numpy()
    seen: set = set()
    before = np.zeros(len(s), bool)
    for i, c in enumerate(cells):
        before[i] = c in seen
        seen.add(c)
    rows = []
    for b0 in range(0, len(s), BLOCK):
        st = s.iloc[b0 : b0 + BLOCK]
        r = st.r_km.to_numpy()
        far = np.isclose(r, r_max)
        run_len = cur = 0
        for f in far:
            cur = cur + 1 if f else 0
            run_len = max(run_len, cur)
        p = pl[(pl.start >= b0) & (pl.start < b0 + BLOCK)]
        end = b0 + len(st)
        row = {"block_start": b0, "steps": len(st), "share_rmin": float(np.isclose(r, r_min).mean()), "share_rmax": float(far.mean()),
               **rmax_episodes(r, r_min, r_max), "longest_rmax": run_len, "places": len(p), "median_dwell": float(p.dwell.median()) if len(p) else np.nan,
               "n_chosen_median": float(st.n.median()), "g_chosen_median": float(st.g.median()), "drive_d_sd": float(st.drive_d.std()),
               "gyration_block_km": gyration_km(st.lat, st.lon), "gyration_sofar_km": gyration_km(s.lat[:end], s.lon[:end]),
               "continents_block": len(set(continent(st.lat, st.lon))), "continents_sofar": len(set(continent(s.lat[:end], s.lon[:end]))),
               "new_cells": int((~before[b0:end]).sum()), "cells_sofar": int(len(set(cells[:end]))), "onto_visited": float(before[b0:end].mean()),
               "heldout_end": float(h[h.index <= end].iloc[-1]) if (h.index <= end).any() else np.nan,
               "fetch_dropped": int(st.n_dropped.sum()), "sec": float(st.sec.sum())}
        if end in wv.index or (end - 1) in wv.index:
            w = wv.loc[end if end in wv.index else end - 1]
            row.update({k: float(w[k]) for k in ("probe_bacc", "probe_r2", "tobler_rho", "plateau_km", "knn_geo_excess", "probe_spread")})
        rows.append(row)
    return pd.DataFrame(rows)


def same_start(run: str, other: str) -> dict:
    a = pd.read_parquet(RUNS / run / "steps.parquet", columns=["step", "tile_idx", "r_km"])
    b = pd.read_parquet(RUNS / other / "steps.parquet", columns=["step", "tile_idx", "r_km"])
    n = min(len(a), len(b))
    diff = np.flatnonzero(a.tile_idx.to_numpy()[:n] != b.tile_idx.to_numpy()[:n])
    return {"against": other, "compared": n, "first_different_step": int(diff[0]) if len(diff) else None}


def plot(B: pd.DataFrame, run: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ks = [("share_rmax", "share of steps at r_max"), ("rmax_episodes_per_1000", "r_max episodes per 1,000 steps"), ("places", "places begun"),
          ("n_chosen_median", "median chosen novelty"), ("onto_visited", "steps onto a cell visited before"), ("cells_sofar", "cells so far"),
          ("gyration_sofar_km", "radius of gyration so far (km)"), ("heldout_end", "held-out error"), ("probe_bacc", "land-cover probe (balanced accuracy)")]
    fig, axs = plt.subplots(3, 3, figsize=(14, 10))
    x = (B.block_start + B.steps) / 1000
    for ax, (k, t) in zip(axs.flat, ks):
        if k in B:
            ax.plot(x, B[k], marker="o", lw=2, color="#2a6fb0")
        ax.set_title(t, fontsize=10)
        ax.set_xlabel("thousand steps (end of block)")
        ax.grid(alpha=0.3)
    fig.suptitle(f"{run}: the walk in blocks of {BLOCK} steps", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "long_walk.png", dpi=110)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", nargs="?", default="e09_v1_long_s0")
    ap.add_argument("--against", default="e09_ref_s0")
    a = ap.parse_args()
    B = blocks(a.run)
    B.to_csv(OUT / "long_walk_blocks.csv", index=False)
    plot(B, a.run)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(B.round(3).T.to_string())
    print(same_start(a.run, a.against))


if __name__ == "__main__":
    main()
