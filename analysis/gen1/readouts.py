"""Readouts of the clock-world walks (notes/brief_landsat_v2_run.md, 6 and 7): time, length and yield, movement, compute, coverage.

    python analysis/gen1/readouts.py dryrun       # runs/dryrun/<condition>/w*/ -> notes/gen1/dryrun/ (tables .csv, figures .png)
    python analysis/gen1/readouts.py coverage     # the coverage curve of the world (cells with an acquisition, against date)

Every table reports the clock next to the step. Definitions (named, so the report can quote them):
- wait: a step that took the time offer. P(wait | offered) is over the steps where the time offer was available (fetched); the Null's
  expectation there is mean(1 / n_offers).
- unique tiles: distinct images (cell, acquisition) a walk stood on; a wait onto a new date is a new tile.
- revisit: a step onto a cell visited before (any date); repeat: onto an image seen before.
- edge pull: the share of steps whose top crop (most novel of the 16) is on the tile's border ring (12 of 16 crops: chance 0.75).
- projected steps to T_end: for a walk that ended by the clock, its length; for a capped one, its length plus the days still to go at
  its rate over its last 1,000 steps (days of clock per step). Uncertain: the rate changes as the walker moves between dense and sparse
  coverage. Projections are capped at the generation-1 step cap.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from agent import clock as CL  # noqa: E402
from agent.eyes import EDGE  # noqa: E402

GEN1_CAP = 15000
PARALLEL = 3
TARGETS = (5000, 10000, 20000)


def load(phase: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for w in sorted((ROOT / "runs" / phase).glob("*/w*/walk.json")):
        d = w.parent
        out.setdefault(d.parent.name, []).append({"dir": d, "walk": json.loads(w.read_text()), "s": pd.read_parquet(d / "steps.parquet"),
                                                   "c": pd.read_parquet(d / "candidates.parquet")})
    return out


def per_walk(W: dict[str, list[dict]], t_end: int) -> pd.DataFrame:
    rows = []
    for cond, ws in W.items():
        for w in ws:
            s, c, j = w["s"], w["c"], w["walk"]
            n = len(s)
            wait = s.offer_kind == "time"
            avail = s.time_available.astype(bool)
            tail = s.iloc[-min(1000, n):]
            rate = (tail.clock_day.iloc[-1] - tail.clock_day.iloc[0]) / max(len(tail) - 1, 1)
            left = max(t_end - int(s.clock_day.iloc[-1]), 0)
            proj = n if j["end_reason"] == "time" else (n + left / rate if rate > 0 else np.inf)
            seen_cell = s.tile_idx.duplicated()
            seen_img = s.image_key.duplicated()
            top_edge = EDGE[s.top_crop.to_numpy().astype(int)]
            rows.append({
                "condition": cond, "walk": j["walk_id"], "start_cell": j["start_cell"], "start_clock": j["start_clock"], "end_clock": j["end_clock"],
                "end_reason": j["end_reason"], "steps": n, "unique_tiles": j["unique_tiles"], "unique_cells": j["unique_cells"],
                "tiles_per_step": j["unique_tiles"] / n, "waits": int(wait.sum()), "wait_share": wait.mean(),
                "time_offered_share": s.time_offered.mean(), "time_available_share": avail.mean(),
                "p_wait_given_offer": wait[avail].mean() if avail.any() else np.nan,
                "null_p_wait_given_offer": (1.0 / s.n_offers[avail]).mean() if avail.any() else np.nan,
                "dt_median": s.wait_days[wait].median(), "dt_mean": s.wait_days[wait].mean(),
                "longest_no_time_offer": int(max_run(~s.time_offered.to_numpy(bool))),
                "clock_days_per_step_last1000": rate, "projected_steps_to_t_end": min(proj, GEN1_CAP) if np.isfinite(proj) else GEN1_CAP,
                "projected_capped": not (np.isfinite(proj) and proj <= GEN1_CAP),
                "revisit_share": seen_cell.mean(), "repeat_share": seen_img.mean(), "edge_pull": top_edge.mean(),
                "r_max_share": (s.r_km >= 0.99 * s.r_km.max()).mean() if s.r_km.max() > 100 else 0.0, "median_move_km": s.dist_km[~wait].median(),
                "night_share": s.night.mean(), "cloud_mean": s.q_cloud.mean(), "fill_mean": s.q_fill.mean(),
                "sec_per_step": s.sec.mean(), "sec_per_step_last500": s.sec.iloc[-500:].mean(), "fetch_sec": s.fetch_sec.mean(),
                "offers_dropped": int(s.n_dropped.sum()), "offers_total": int(s.n_fetch.sum()), "wall_s": j["seconds"],
                "share_glance": s.share_glance.mean(), "share_grid": s.share_grid.mean(), "share_prog": s.share_prog.mean(),
            })
    return pd.DataFrame(rows)


def max_run(x: np.ndarray) -> int:
    best = cur = 0
    for v in x:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best


def waits_vs_moves(W) -> pd.DataFrame:
    """Chosen tiles of waits against sideways moves, per condition: cloud, night, fill, |cloud change| from the tile before, and the
    interest components at the choice (z and raw): novelty that came from waiting against novelty that came from moving."""
    rows = []
    for cond, ws in W.items():
        s = pd.concat([w["s"].assign(dcloud=(w["s"].q_cloud - w["s"].q_cloud.shift(1)).abs()) for w in ws], ignore_index=True)
        for kind, g in s.groupby(np.where(s.offer_kind == "time", "wait", "move")):
            rows.append({"condition": cond, "kind": kind, "n": len(g), "cloud": g.q_cloud.mean(), "night": g.night.mean(), "fill": g.q_fill.mean(),
                         "abs_dcloud": g.dcloud.mean(), "z_glance": g.z_glance.mean(), "z_grid": g.z_grid.mean(), "z_prog": g.z_prog.mean(),
                         "n_glance": g.n_glance.mean(), "n_grid": g.n_grid.mean(), "I": g.I.mean()})
    return pd.DataFrame(rows)


def offer_selection(W) -> pd.DataFrame:
    """Chosen against offered, per condition and offer kind: cloud and night (the brief: cloud and night of waits against moves)."""
    rows = []
    for cond, ws in W.items():
        c = pd.concat([w["c"] for w in ws])
        for kind, g in c.groupby("kind"):
            ch = g[g.chosen]
            rows.append({"condition": cond, "kind": kind, "offered": len(g), "chosen": len(ch), "take_rate": len(ch) / len(g),
                         "cloud_offered": g.q_cloud.mean(), "cloud_chosen": ch.q_cloud.mean(), "night_offered": g.night.mean(), "night_chosen": ch.night.mean()})
    return pd.DataFrame(rows)


def dt_table(W) -> pd.DataFrame:
    rows = []
    for cond, ws in W.items():
        d = pd.concat([w["s"].wait_days.dropna() for w in ws])
        rows.append({"condition": cond, "waits": len(d), **{f"p{q}": d.quantile(q / 100) for q in (10, 25, 50, 75, 90)}, "mean": d.mean(),
                     "share_1d": (d <= 1).mean(), "share_18d": (d == 18).mean(), "share_le_18d": (d <= 18).mean(), "share_gt_180d": (d > 180).mean()})
    return pd.DataFrame(rows)


def offer_histogram(W) -> pd.DataFrame:
    rows = []
    for cond, ws in W.items():
        s = pd.concat([w["s"] for w in ws])
        k = np.where(s.offer_kind == "time", "time", np.where(s.compass_slot >= 0, "compass", "fallback"))
        v = pd.Series(k).value_counts()
        rows.append({"condition": cond, **{f"n_{x}": int(v.get(x, 0)) for x in ("compass", "time", "fallback")},
                     "n_offers_mean": s.n_offers.mean(), **{f"slot_{i}": int((s.compass_slot == i).sum()) for i in range(8)}})
    return pd.DataFrame(rows)


def projection(P: pd.DataFrame) -> pd.DataFrame:
    """Walks and wall time for generation 1 at each N: per condition, from the dry runs' tiles per walk (projected to the end by the
    clock, capped at 15,000 steps) and seconds per step; three walkers side by side. Range = the dry runs' smallest and largest walk."""
    rows = []
    for cond, g in P.groupby("condition"):
        steps = g.projected_steps_to_t_end.to_numpy(float)
        tiles = steps * g.tiles_per_step.to_numpy(float)
        sps = g.sec_per_step_last500.to_numpy(float)
        for N in TARGETS:
            mid, lo, hi = N / tiles.mean(), N / tiles.max(), N / tiles.min()
            st = np.ceil(mid) * steps.mean()
            rows.append({"condition": cond, "N": N, "tiles_per_walk_mean": tiles.mean(), "tiles_per_walk_min": tiles.min(), "tiles_per_walk_max": tiles.max(),
                         "walks_mid": int(np.ceil(mid)), "walks_range": f"{int(np.ceil(lo))}-{int(np.ceil(hi))}", "steps_total": int(st),
                         "wall_h_at_dryrun_rate": st * sps.mean() / PARALLEL / 3600})
    out = pd.DataFrame(rows)
    tot = out.groupby("N").wall_h_at_dryrun_rate.sum().rename("wall_h_both_conditions")
    return out.merge(tot, on="N")


def coverage() -> pd.DataFrame:
    """Cells with an acquisition in each 18-day cycle, and cells with any acquisition on or after the cycle (where a wait is still possible)."""
    d = ROOT / "data" / "landsat1" / "clock"
    start, day = np.load(d / "start.npy"), np.load(d / "day.npy")
    cell = np.repeat(np.arange(len(start) - 1), np.diff(start))
    d0 = int(day.min())
    cyc = (day - d0) // 18
    n_cyc = int(cyc.max()) + 1
    per = pd.Series(cell).groupby(cyc).nunique().reindex(range(n_cyc), fill_value=0)
    last = np.maximum.reduceat(day, start[:-1])
    last_cyc = (last - d0) // 18
    alive = (len(last_cyc) - np.searchsorted(np.sort(last_cyc), np.arange(n_cyc), side="left"))
    return pd.DataFrame({"cycle": np.arange(n_cyc), "date": [CL.to_date(d0 + 18 * k) for k in range(n_cyc)], "cells_imaged": per.to_numpy(),
                         "cells_with_a_later_pass": alive})


def figures(W, out: Path, cov: pd.DataFrame) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    col = {"curious": "#c2622d", "null": "#5b6770"}
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for cond, ws in W.items():
        for k, w in enumerate(ws):
            s = w["s"]
            ax.plot(s.step, pd.to_datetime(s.clock), color=col.get(cond, "k"), lw=1.2, alpha=0.9, label=cond if k == 0 else None)
    ax.axhline(pd.Timestamp("1977-12-20"), color="k", lw=0.6, ls="--")
    ax.set_xlabel("step")
    ax.set_ylabel("clock")
    ax.set_title("Clock against step (dashed: T_end)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out / "clock_vs_step.png", dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 3.6))
    for cond, ws in W.items():
        d = pd.concat([w["s"].wait_days.dropna() for w in ws])
        if len(d):
            ax.hist(np.log10(d.clip(lower=1)), bins=np.linspace(0, 3.3, 34), histtype="step", lw=1.5, color=col.get(cond, "k"), label=f"{cond} ({len(d)} waits)")
    ax.set_xticks(np.log10([1, 2, 5, 18, 36, 90, 180, 365, 730, 1500]), ["1", "2", "5", "18", "36", "90", "180", "365", "730", "1500"])
    ax.set_xlabel("Δt of a wait, days (log)")
    ax.set_ylabel("waits")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out / "wait_dt.png", dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 3.6))
    dt = pd.to_datetime(cov.date)
    ax.plot(dt, cov.cells_imaged / 1e3, color="#3a6ea5", lw=1.2, label="cells imaged in the 18-day cycle")
    ax.plot(dt, cov.cells_with_a_later_pass / 1e3, color="#7a7a7a", lw=1.2, label="cells with a pass on or after it")
    ax.axvline(pd.Timestamp("1977-12-20"), color="k", lw=0.6, ls="--")
    ax.set_ylabel("thousand cells")
    ax.set_title("Coverage of the Landsat 1 world against date")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out / "coverage.png", dpi=130)
    plt.close(fig)


def main() -> None:
    what = sys.argv[1]
    out = ROOT / "notes" / "gen1" / what
    out.mkdir(parents=True, exist_ok=True)
    cov = coverage()
    cov.to_csv(out / "coverage.csv", index=False)
    if what == "coverage":
        print(cov.iloc[::10].to_string())
        return
    W = load(what)
    P = per_walk(W, CL.to_day("1977-12-20"))
    tabs = {"walks": P, "waits_vs_moves": waits_vs_moves(W), "offer_selection": offer_selection(W), "dt": dt_table(W),
            "offer_histogram": offer_histogram(W), "projection": projection(P)}
    for k, v in tabs.items():
        v.to_csv(out / f"{k}.csv", index=False)
    figures(W, out, cov)
    pd.set_option("display.width", 250)
    for k, v in tabs.items():
        print(f"\n## {k}\n{v.round(3).to_string(index=False)}")


if __name__ == "__main__":
    main()
