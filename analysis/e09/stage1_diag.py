"""Stage 1 diagnosis: why the compass walkers never went far.

    python analysis/e09/stage1_diag.py

On the 12 Stage 1 walks (closed loop, compass mode) and the 8 old Reference walks (open loop, the Stage 0 mapping):
- trend: the chosen value of each signal, median over steps 50-150 and over steps 900-1000, in SDs of the whole walk;
- the drive and radius as the Stage 0 mapping computes them (mapping.stats), for each signal at Delta 0.175, 0.35 and 0.7, and for
  interest_long with a faster long average (0.005, 0.01), whose lag behind a trend is shorter.
Mapping the compass logs is again open loop: after the first far step the walker would have stood elsewhere. A signal that never falls
far below its usual level here cannot send a compass walker far; one that does might.

Writes results/stage1_diag.csv and results/stage1_trend.csv.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from e09_common import OUT, old_runs  # sets sys.path
from mapping import SIGNALS, signals, stats

from agent.compass import Drive

STAGE1 = {"compass Reference (0.35)": "e09_reference", "delta 0.175": "e09_delta_0175", "delta 0.7": "e09_delta_07"}
DELTAS = (0.175, 0.35, 0.7)
LONG_RATES = (0.002, 0.005, 0.01)


def drive(x: np.ndarray, a_long: float) -> np.ndarray:
    D = Drive(0.02, a_long)
    return np.array([D.update(float(v)) for v in x])


def main() -> None:
    runs = [(g, sd, f"{stem}_s{sd}", "compass") for g, stem in STAGE1.items() for sd in range(4)]
    runs += [(g, sd, run, "classic") for g, sd, run in old_runs() if g == "Reference"]
    rows, trend = [], []
    for g, sd, run, nav in runs:
        S = signals(run)
        for sig in SIGNALS:
            x = S[sig].to_numpy(float)
            sdv = np.nanstd(x[50:]) or np.nan
            trend.append({"group": g, "seed": sd, "run": run, "nav": nav, "signal": sig,
                          "early": float(np.nanmedian(x[50:150])), "late": float(np.nanmedian(x[900:1000])),
                          "rise_sd": float((np.nanmedian(x[900:1000]) - np.nanmedian(x[50:150])) / sdv)})
            for a in LONG_RATES if sig == "interest_long" else (0.002,):
                d = drive(x, a)
                for de in DELTAS:
                    rows.append({"group": g, "seed": sd, "run": run, "nav": nav, "signal": sig, "a_long": a, "delta": de,
                                 "d_p5": float(np.nanpercentile(d[50:], 5)), "d_median": float(np.nanmedian(d[50:])),
                                 **stats(d, S.bored.to_numpy(), de)})
    A, T = pd.DataFrame(rows), pd.DataFrame(trend)
    A.to_csv(OUT / "stage1_diag.csv", index=False)
    T.to_csv(OUT / "stage1_trend.csv", index=False)
    pd.set_option("display.width", 250)
    print(T.groupby(["nav", "signal"])[["early", "late", "rise_sd"]].mean().round(2))
    print(A.groupby(["nav", "signal", "a_long", "delta"])[["d_p5", "d_median", "share_rmax", "rmax_episodes_per_1000"]].mean().round(3).to_string())
    plot(runs)
    sweep(runs)


SWEEP_SIGNALS = ("interest_long", "surprise_log")
SWEEP_RATES = ((0.02, 0.002), (0.02, 0.005), (0.02, 0.01), (0.05, 0.005), (0.05, 0.01))  # (short, long)
SWEEP_DELTAS = (0.1, 0.175, 0.25, 0.35, 0.5, 0.7, 1.0)


def sweep(runs) -> None:
    """stage1_sweep.csv: the drive's two time scales against Δ, for interest_long and log surprise, on both sets of logs."""
    rows = []
    for g, sd, run, nav in runs:
        S = signals(run)
        for sig in SWEEP_SIGNALS:
            x = S[sig].to_numpy(float)
            for a_s, a_l in SWEEP_RATES:
                D = Drive(a_s, a_l)
                d = np.array([D.update(float(v)) for v in x])
                for de in SWEEP_DELTAS:
                    rows.append({"group": g, "seed": sd, "run": run, "nav": nav, "signal": sig, "a_short": a_s, "a_long": a_l, "delta": de,
                                 **stats(d, S.bored.to_numpy(), de)})
    A = pd.DataFrame(rows)
    A.to_csv(OUT / "stage1_sweep.csv", index=False)
    keep = ["share_rmin", "share_le_2rmin", "share_rmax", "rmax_episodes_per_1000", "rmax_episode_median_len"]
    print(A.groupby(["signal", "nav", "a_short", "a_long", "delta"])[keep].mean().round(3).to_string())


def plot(runs) -> None:
    """stage1_drive.png: the drive on interest_long (as the walker computed it for compass runs; mapped for classic runs), and raw novelty
    at the chosen cell (rolling median over 50 steps). Compass Stage 1 walks (12) against the classic Reference (8)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colour = {"compass": "#2a78d6", "classic": "#eb6834"}
    label = {"compass": "compass, Stage 1 (12 walks, closed loop)", "classic": "classic Reference (8 walks, mapped offline)"}
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6), sharex=True)
    for g, sd, run, nav in runs:
        S = signals(run)
        d = drive(S.interest_long.to_numpy(float), 0.002)
        kw = dict(color=colour[nav], lw=0.8, alpha=0.55)
        axes[0].plot(S.step, d, **kw)
        axes[1].plot(S.step, pd.Series(S.novelty).rolling(50, min_periods=10).median(), **kw)
        axes[2].plot(S.step, pd.Series(S.surprise_log).rolling(50, min_periods=10).median(), **kw)
    axes[0].axhline(-0.35, color="#52514e", lw=0.8, ls="--")
    axes[0].text(1000, -0.38, "Δ 0.35: r_max below", ha="right", va="top", fontsize=7, color="#52514e")
    axes[0].axhline(0, color="#c3c2b7", lw=0.6)
    axes[0].set_title("drive d (interest on the long yardstick)", fontsize=9)
    axes[1].set_title("novelty at the chosen cell (raw, 50-step median)", fontsize=9)
    axes[2].set_title("log surprise at the chosen cell (50-step median)", fontsize=9)
    for ax in axes:
        ax.set_xlabel("step", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(color="#e5e4df", lw=0.5)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    for nav in colour:
        axes[0].plot([], [], color=colour[nav], lw=1.6, label=label[nav])
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=2, fontsize=8, frameon=False, bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(OUT / "stage1_drive.png", dpi=150)


if __name__ == "__main__":
    main()
