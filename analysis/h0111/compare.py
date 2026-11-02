"""Tasks 3, 6 and 9: the new Paris walks side by side, with the same statistics as analysis/h2910_compare.py plus how teleports bunch up.

    python analysis/h0111/compare.py

Writes h0111_summary.csv (one row per walk), task3_null_vs_reference.csv, task6_landings.csv, task6_table.csv, task9_eye.csv, and
task6_rhythm.png, task9_eye.png.

A teleport is "in a burst" if another teleport comes within BURST_GAP steps of it. A "rejected landing" is a teleport whose place lasted
at most BURST_GAP steps and ended with another teleport. A burst is a chain of teleports with gaps of at most BURST_GAP steps.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from common import OUT, ROOT, RUNS, heldout, places, steps

sys.path.insert(0, str(ROOT / "analysis"))
from h2910_compare import stats  # noqa: E402

BURST_GAP = 30
SEEDS = (0, 1, 2, 3)
GROUPS = {"Null": "h0111_null", "Reference": "h0111_reference", "Reference k=3": "h0111_reference_k3", "Reference k=8": "h0111_reference_k8",
          "Bored": "h0111_bored", "Bored k=3": "h0111_bored_k3", "Bored k=8": "h0111_bored_k8"}
# categorical slots 1-3 of the dataviz reference palette, in fixed order; validated adjacent pairs
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def burst_stats(s: pd.DataFrame) -> dict:
    tele = s.step[s.bored_event].to_numpy()
    gaps = np.diff(tele)
    close = gaps <= BURST_GAP
    in_burst = (np.r_[False, close] | np.r_[close, False]).sum() if len(tele) > 1 else 0
    chains, cur = [], 1
    for c in close:
        cur = cur + 1 if c else 1
        chains.append(cur)
    p = places(s)
    land = p[p.jump_type == "bored"]
    # the place a teleport lands in: did it end quickly, in another teleport?
    ends_bored = p.groupby("place").bored_event.last()
    rejected = sum(1 for _, r in land.iterrows() if r.place_len <= BURST_GAP and ends_bored[r.place])
    return {"share_in_burst": in_burst / max(len(tele), 1), "largest_burst": max(chains, default=1 if len(tele) else 0), "bursts": int(sum(1 for i, c in enumerate(close) if c and (i == 0 or not close[i - 1]))),
            "rejected_landings": rejected, "rejected_share": rejected / max(len(land), 1), "median_stay_after_landing": float(land.place_len.median()) if len(land) else np.nan,
            "landing_ocean_share": float((land.cover == "ocean").mean()) if len(land) else np.nan, "max_gap": int(gaps.max()) if len(gaps) else 0}


def walks() -> pd.DataFrame:
    rows = []
    for g, stem in GROUPS.items():
        for sd in SEEDS:
            r = RUNS / f"{stem}_s{sd}"
            if not (r / "final.pt").exists():
                continue
            s = steps(r.name)
            rows.append({**stats(g, sd, r), "group": g, **burst_stats(s)})
    return pd.DataFrame(rows)


def ranges(t: pd.DataFrame, cols: list[str], groups: list[str]) -> pd.DataFrame:
    def fmt(v: pd.Series) -> str:
        return f"{v.mean():.3g} ({v.min():.3g}–{v.max():.3g})"

    return pd.DataFrame({g: {c: fmt(t[t.group == g][c]) for c in cols} for g in groups if (t.group == g).any()})


def landings() -> pd.DataFrame:
    """For best_of_k: what the chosen landing is like against the first draw, which is the tile a blind teleport would have taken."""
    from data.tile_store import TileStore

    store, rows = TileStore(), []

    def texture(i: int) -> float:
        g = store.get_lowres(int(i)).astype(float).mean(2)
        gy, gx = np.gradient(g)
        return float(np.hypot(gx, gy).mean())

    idx_cover = store.idx.cover.to_numpy()
    for g, stem in GROUPS.items():
        if "k=" not in g:
            continue
        for sd in SEEDS:
            p = RUNS / f"{stem}_s{sd}" / "landings.parquet"
            if not p.exists():
                continue
            d = pd.read_parquet(p)
            for st, x in d.groupby("step"):
                b, f = x[x.landed].iloc[0], x.iloc[0]
                rows.append({"group": g, "seed": sd, "step": st, "n_best": b.n, "n_first": f.n, "grad_best": texture(b.tile_idx), "grad_first": texture(f.tile_idx),
                             "ocean_best": idx_cover[int(b.tile_idx)] == "ocean", "ocean_first": idx_cover[int(f.tile_idx)] == "ocean"})
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "task6_landings.csv", index=False)
    if len(t):
        print(t.groupby("group")[["n_best", "n_first", "grad_best", "grad_first", "ocean_best", "ocean_first"]].mean().round(3).assign(landings=t.groupby("group").size()).to_string())
    return t


def rhythm_figure(t: pd.DataFrame) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    groups = [g for g in GROUPS if (t.group == g).any()]
    fig, axs = plt.subplots(len(groups), 1, figsize=(11, 1.05 * len(groups) + 1), sharex=True)
    for ax, g in zip(np.atleast_1d(axs), groups):
        for sd in SEEDS:
            r = f"{GROUPS[g]}_s{sd}"
            if not (RUNS / r / "final.pt").exists():
                continue
            s = steps(r)
            ax.eventplot(s.step[s.jump_type == "long"], lineoffsets=sd, linelengths=0.62, colors=SERIES[1], linewidths=1.6)
            ax.eventplot(s.step[s.bored_event], lineoffsets=sd, linelengths=0.82, colors=SERIES[0], linewidths=1.6)
        ax.set_ylim(3.7, -0.7)
        ax.set_yticks([])
        ax.set_ylabel(g, rotation=0, ha="right", va="center", fontsize=9, color=INK)
        ax.set_xlim(0, 1000)
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(colors=MUTED, length=0)
    np.atleast_1d(axs)[-1].set_xlabel("step (four rows per setting, one per seed)", color=MUTED)
    handles = [plt.Line2D([], [], color=SERIES[0], lw=2, label="boredom teleport"), plt.Line2D([], [], color=SERIES[1], lw=2, label="long jump taken")]
    fig.legend(handles=handles, loc="upper right", frameon=False, ncol=2, fontsize=9)
    fig.suptitle("When each walk jumped", x=0.01, ha="left", fontsize=11, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(OUT / "task6_rhythm.png", dpi=130)
    plt.close(fig)


def eye() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    runs = {"half (68k weights)": "h0111_eye_half_s0", "current (272k)": "h0111_reference_s0", "double (1.09M)": "h0111_eye_double_s0"}
    runs = {k: v for k, v in runs.items() if (RUNS / v / "final.pt").exists()}
    if len(runs) < 3:
        print("eye: not all runs present", list(runs))
        return
    rows = []
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    for col, (lab, r) in zip(SERIES, runs.items()):
        h = heldout(r)
        v = h.set_index("step").heldout_mse
        sm = v.rolling(5, center=True, min_periods=1).median()
        final = v[v.index >= 800].median()
        flat = int(sm[sm <= 1.2 * final].index[0])
        late = np.polyfit(np.log(h.step[h.step >= 500]), np.log(h.heldout_mse[h.step >= 500]), 1)[0]
        import json

        rows.append({"eye": lab, "run": r, "mse_100": v[100], "mse_250": v[250], "mse_500": v[500], "mse_1000": v[1000], "median_last_200": final, "within_20pct_of_final_at": flat, "loglog_slope_500_1000": late, "seconds": json.loads((RUNS / r / "meta.json").read_text())["seconds"],
                     "unique_tiles": steps(r).tile_idx.nunique(), "teleports": int(steps(r).bored_event.sum())})
        ax.plot(h.step.clip(lower=25), sm, color=col, lw=2, label=lab)
    ax.set(xscale="log", yscale="log", xlabel="step", ylabel="held-out error", xlim=(25, 1000))
    ax.set_title("Eye size: held-out error, rolling median of 5 logged values", loc="left", fontsize=10.5)
    ax.grid(color=GRID, lw=0.7)
    ax.set_xticks([25, 50, 100, 200, 500, 1000], labels=["25", "50", "100", "200", "500", "1,000"])
    ax.set_yticks([0.003, 0.005, 0.01, 0.02], labels=["0.003", "0.005", "0.01", "0.02"])
    ax.minorticks_off()
    ax.legend(frameon=False, loc="lower left", fontsize=8.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "task9_eye.png", dpi=130)
    plt.close(fig)
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "task9_eye.csv", index=False)
    print(t.round(5).T.to_string())


def main() -> None:
    t = walks()
    t.to_csv(OUT / "h0111_summary.csv", index=False)
    base = ["unique_tiles", "revisit_share", "back_step_share", "bored_teleports", "long_offered", "long_taken", "long_accept_rate", "places", "median_steps_per_place", "longest_place_steps", "ocean_share_unique", "colour_diversity_unique", "heldout_mse_last200", "max_I_below_0_share", "sec_per_step"]
    n = ranges(t, base, ["Null", "Reference"])
    n.to_csv(OUT / "task3_null_vs_reference.csv")
    with pd.option_context("display.width", 200, "display.max_rows", 60):
        print(n.to_string())
        ls = ["bored_teleports", "share_in_burst", "bursts", "largest_burst", "rejected_landings", "rejected_share", "median_stay_after_landing", "landing_ocean_share", "longest_place_steps", "ocean_share_unique", "places", "median_steps_per_place", "unique_tiles", "colour_diversity_unique", "heldout_mse_last200"]
        g = ranges(t, ls, [x for x in GROUPS if x != "Null"])
        g.to_csv(OUT / "task6_table.csv")
        print(g.T.to_string())
        spread = t.groupby("group", sort=False)[["ocean_share_unique", "places", "median_steps_per_place", "bored_teleports", "longest_place_steps"]].agg(lambda v: v.max() - v.min()).round(2)
        print("\nrange across seeds (max - min)\n", spread.to_string())
        spread.to_csv(OUT / "task6_spread.csv")
    landings()
    rhythm_figure(t)
    eye()


if __name__ == "__main__":
    main()
