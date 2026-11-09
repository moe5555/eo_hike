"""Stage 0.3: the drive and the radius it would have given, on the logs of e08 walks (classic navigation).

    python analysis/e09/mapping.py

Signals, each the value at the cell chosen at that step (agent/compass.py for the drive and the radius rule):
- interest: the logged I, the walker's own mix of z-scores. Its norms run at ema_alpha 0.02 (about 50 steps) over the candidates.
- interest_long: the same mix, with each raw signal z-scored at the long rate (0.002) instead, over the same candidate batches.
- novelty, progress, surprise: the raw signals n, g, e. novelty_z, progress_z: the walker's own z-scores of n and g (ema_alpha 0.02).
  surprise_log: log e.

Writes data/sheet/e09_mapping_series.parquet (git-ignored; per run and step: the signals and d) and notes/09_compass/results/: mapping.csv (per run, signal and delta:
share of steps at r_min, at r_max, at most 2 r_min; episodes at r_max per 1,000 steps; old teleports near an r_max episode),
mapping_summary.csv (means over seeds) and mapping.png.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from e09_common import CACHE, OUT, RUNS, R_MIN, old_runs  # sets sys.path

from agent.compass import Drive, LongNorm, radii

WARMUP = 50
SIGNALS = ("interest", "interest_long", "novelty", "progress", "surprise", "novelty_z", "progress_z", "surprise_log")
DELTAS = (0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.7, 1.0)
R_MAX = 2000.0
NEAR = 10  # an old teleport counts as matched when it lies within this many steps of an r_max episode


def signals(run: str) -> pd.DataFrame:
    import yaml

    cfg = yaml.safe_load((RUNS / run / "config.yaml").read_text())
    s = pd.read_parquet(RUNS / run / "steps.parquet")
    c = pd.read_parquet(RUNS / run / "candidates.parquet", columns=["step", "e", "n", "g", "chosen"])
    norms = {k: LongNorm(0.002) for k in "eng"}
    il = np.full(len(s), np.nan)
    for st, b in c.groupby("step", sort=True):
        z = {k: (norms[k](b[k].to_numpy()) if (k != "n" or st > 0) else np.zeros(len(b))) for k in "eng"}  # novelty has no norm update at step 0, as in walk.py
        mix = float(cfg["w_n"]) * z["n"] + float(cfg["w_g"]) * z["g"] + float(cfg["w_e"]) * z["e"]
        il[st] = mix[b.chosen.to_numpy()][0]
    return pd.DataFrame({"step": s.step, "interest": s.I, "interest_long": il, "novelty": s.n, "progress": s.g, "surprise": s.e,
                         "novelty_z": s.n_z, "progress_z": s.g_z, "surprise_log": np.log(s.e.clip(lower=1e-6)),
                         "bored": s.bored_event, "dist_km": s.dist_km})


def drive(x: np.ndarray) -> np.ndarray:
    D = Drive(0.02, 0.002)
    return np.array([D.update(float(v)) for v in x])


def episodes(mask: np.ndarray) -> list[tuple[int, int]]:
    """Maximal runs of True: (start, end exclusive)."""
    m = np.r_[False, mask, False].astype(int)
    st, en = np.flatnonzero(np.diff(m) == 1), np.flatnonzero(np.diff(m) == -1)
    return list(zip(st, en))


def stats(d: np.ndarray, bored: np.ndarray, delta: float) -> dict:
    r = radii(d, R_MIN, R_MAX, delta, 0.0, WARMUP)
    live = np.arange(len(r)) > WARMUP
    at_max = np.isclose(r, R_MAX) & live
    ep = episodes(at_max)
    tele = np.flatnonzero(bored)
    hit = [any(a - NEAR <= x < b + NEAR for a, b in ep) for x in tele]
    n = live.sum()
    return {"share_rmin": float(np.isclose(r[live], R_MIN).mean()), "share_le_2rmin": float((r[live] <= 2 * R_MIN + 1e-9).mean()),
            "share_rmax": float(at_max[live].mean()), "rmax_episodes_per_1000": len(ep) * 1000 / n,
            "rmax_episode_median_len": float(np.median([b - a for a, b in ep])) if ep else np.nan,
            "old_teleports": len(tele), "teleports_near_rmax": float(np.mean(hit)) if len(tele) else np.nan,
            "median_r": float(np.median(r[live])), "p90_r": float(np.percentile(r[live], 90))}


def plot(A: pd.DataFrame, delta: float = 0.35) -> None:
    """The drive over the Reference's eight walks: interest on the long yardstick and the logged interest, the r_max line, old teleports."""
    import matplotlib.pyplot as plt

    R = A[A.group == "Reference"]
    fig, axs = plt.subplots(8, 1, figsize=(11, 13), sharex=True, sharey=True)
    for ax, (sd, x) in zip(axs, R.groupby("seed")):
        ax.axhline(0, color="#b5b4ad", lw=0.8)
        ax.axhline(-delta, color="#52514e", lw=0.8, ls="--")
        ax.plot(x.step, x.d_interest, color="#eb6834", lw=1.0, label="logged interest (yardstick ~50 steps)")
        ax.plot(x.step, x.d_interest_long, color="#2a78d6", lw=1.4, label="interest on the long yardstick (~500 steps)")
        for t in x.step[x.bored]:
            ax.axvline(t, ymin=0.9, ymax=1.0, color="#0b0b0b", lw=1.2)
        ax.text(0.005, 0.08, f"seed {sd}", transform=ax.transAxes, fontsize=8, color="#52514e")
        ax.spines[["top", "right"]].set_visible(False)
    axs[0].legend(loc="upper right", fontsize=8, frameon=False, ncol=2)
    axs[0].set_title(f"Drive d on the e08 Reference walks (classic navigation). Dashed: -delta = -{delta} (r_max). Black ticks: old bored teleports.", fontsize=9, loc="left")
    axs[-1].set_xlabel("step")
    fig.text(0.005, 0.5, "d", rotation=90, va="center")
    fig.tight_layout()
    fig.savefig(OUT / "mapping.png", dpi=110)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    series, rows = [], []
    for g, sd, run in old_runs():
        S = signals(run)
        for sig in SIGNALS:
            d = drive(S[sig].to_numpy())
            S[f"d_{sig}"] = d
            for delta in DELTAS:
                rows.append({"group": g, "seed": sd, "run": run, "signal": sig, "delta": delta, **stats(d, S.bored.to_numpy(), delta)})
        series.append(S.assign(group=g, seed=sd, run=run))
        print(f"[mapping] {run}", flush=True)
    A = pd.concat(series, ignore_index=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    A.to_parquet(CACHE / "e09_mapping_series.parquet", index=False)
    M = pd.DataFrame(rows)
    M.to_csv(OUT / "mapping.csv", index=False)
    cols = ["share_rmin", "share_le_2rmin", "share_rmax", "rmax_episodes_per_1000", "rmax_episode_median_len", "teleports_near_rmax", "old_teleports"]
    Sm = M.groupby(["group", "signal", "delta"])[cols].mean().reset_index()
    Sm.to_csv(OUT / "mapping_summary.csv", index=False)
    plot(A)
    pd.set_option("display.width", 250)
    print(Sm.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
