"""Before the progress test (log 2026-11-10): the drive replayed offline on the logs of compass walks, with another signal.

    python analysis/e09/progress_offline.py [stem ...]      # default: e09_ref e09_null

The signal the walker logs at its chosen cell (steps.parquet: drive_x is interest_long, g_z is progress_z, n_z is novelty_z) goes
through agent.compass.Drive with the walk's own averages and drive_start, and agent.compass.radius with its Δ. Replaying drive_x must
reproduce the logged drive_d (checked, printed). The replay is open-loop: the walk would have gone elsewhere under another radius, so
it says what the signal does on these logs, not what the closed loop will do (Stage 1: the closed loop went far less often than the
logs suggested).
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import yaml
from e09_common import RUNS  # sets sys.path

from agent.compass import Drive, radius


def replay(x: np.ndarray, cfg: dict) -> tuple[np.ndarray, np.ndarray]:
    """d after each step's update and the radius it sets for the next step, as walk.py does."""
    dr = Drive(float(cfg["drive_alpha_short"]), float(cfg["drive_alpha_long"]), cfg.get("drive_norm", "z_diff"))
    start, warm = int(cfg.get("drive_start", 0)), int(cfg.get("drive_warmup", 50))
    r_min, r_max, delta = float(cfg["radius_min_km"]), float(cfg["radius_max_km"]), float(cfg["radius_delta"])
    d, r = np.zeros(len(x)), np.full(len(x), r_min)
    for t, v in enumerate(x):
        if t >= start:
            dr.update(float(v))
        d[t] = dr.d
        if t + 1 < len(x):
            r[t + 1] = r_min if t + 1 <= warm else radius(dr.d, r_min, r_max, delta)
    return d, r


def stats(r: np.ndarray, r_min: float, r_max: float) -> dict:
    far = np.isclose(r, r_max)
    ep = int(np.sum(far[1:] & ~far[:-1]) + far[0])
    runs, cur = [], 0
    for f in far:
        cur = cur + 1 if f else 0
        if f:
            runs.append(cur)
    first = int(np.argmax(far)) if far.any() else -1
    return {"share_rmin": float(np.isclose(r, r_min).mean()), "share_rmax": float(far.mean()), "episodes_per_1000": 1000 * ep / len(r),
            "longest": max(runs) if runs else 0, "first_rmax": first}


def main() -> None:
    stems = sys.argv[1:] or ["e09_ref", "e09_null"]
    rows = []
    for stem in stems:
        for sd in range(8):
            run = RUNS / f"{stem}_s{sd}"
            if not (run / "final.pt").exists():
                continue
            cfg = yaml.safe_load((run / "config.yaml").read_text())
            s = pd.read_parquet(run / "steps.parquet", columns=["step", "drive_x", "drive_d", "g_z", "n_z", "r_km"])
            d0, r0 = replay(s.drive_x.to_numpy(), cfg)
            err = float(np.nanmax(np.abs(d0 - s.drive_d.to_numpy())))
            rerr = float(np.nanmax(np.abs(r0 - s.r_km.to_numpy())))
            for sig, col in (("interest_long (check)", "drive_x"), ("progress_z", "g_z"), ("novelty_z", "n_z")):
                d, r = replay(s[col].to_numpy(), cfg)
                rows.append({"walks": stem, "seed": sd, "signal": sig, **stats(r, float(cfg["radius_min_km"]), float(cfg["radius_max_km"])),
                             "d_sd": float(np.std(d[150:])), "check_d_err": err, "check_r_err": rerr})
    R = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(R.groupby(["walks", "signal"])[["share_rmin", "share_rmax", "episodes_per_1000", "longest", "d_sd", "check_d_err", "check_r_err"]].agg(["mean", "min", "max"]).round(3).T.to_string())
    print(R.pivot_table(index=["walks", "seed"], columns="signal", values=["episodes_per_1000", "first_rmax"]).round(1).to_string())


if __name__ == "__main__":
    main()
