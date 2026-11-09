"""Stage 0.5: radius_schedule files for the controls (brief, "Controls"), written from finished compass Reference walks.

    python analysis/e09/schedules.py controls [--reference e09_ref] [--seeds 0-7] [--prefix crop128_]
    python analysis/e09/schedules.py test     # the schedule of the Stage 0.4 fetch test walk

A schedule is a CSV with one row per step (`step`, `radius_km`); the walker replays it instead of the radius rule (agent/walk.py,
radius_schedule; a `{seed}` in the path is replaced by the walk's seed). The drive is still computed and logged. Files go to
configs/09_compass/schedules/ (small, kept in git, so a control can be walked again).

- shifted: the Reference walk's own radius sequence (steps.parquet, r_km), circularly shifted by an offset drawn from [100, 900] with a
  seed fixed per walk seed (SHIFT_SEED, seed). Keeps the distribution and the autocorrelation, removes the timing relative to the drive.
- shuffled: the same radii in a random order (same seeding). Removes timing and autocorrelation.
- fixed: one radius at every step, the geometric mean of the Reference walk's radii (see the Stage 0 report: its median is r_min).
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from e09_common import ROOT, RUNS  # sets sys.path

DIR = ROOT / "configs" / "09_compass" / "schedules"
SHIFT_SEED = 909


def write(r: np.ndarray, name: str) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"step": np.arange(len(r)), "radius_km": np.round(np.asarray(r, float), 6)}).to_csv(DIR / f"{name}.csv", index=False)


def controls(reference: str, seeds, prefix: str = "") -> None:
    """prefix: put in front of every file name, so that another reference's controls don't overwrite e09_ref's (Stage 3)."""
    for sd in seeds:
        run = RUNS / f"{reference}_s{sd}"
        if not (run / "final.pt").exists():
            print(f"[schedules] {run.name} not finished, skipped")
            continue
        r = pd.read_parquet(run / "steps.parquet").r_km.to_numpy(float)
        rng = np.random.default_rng([SHIFT_SEED, sd])
        off = int(rng.integers(100, 901))
        write(np.roll(r, off), f"{prefix}shifted_s{sd}")
        write(rng.permutation(r), f"{prefix}shuffled_s{sd}")
        write(np.full(len(r), float(np.exp(np.log(r).mean()))), f"{prefix}fixed_s{sd}")
        print(f"[schedules] s{sd}: shift {off}, fixed {np.exp(np.log(r).mean()):.1f} km, median {np.median(r):.1f} km")


def test() -> None:
    """Fetch test (Stage 0.4): 10 steps at r_min, then 50 steps cycling through 50, 200, 1,000, 2,000 and 2,000 km."""
    r = np.r_[np.full(10, 15.0), np.tile([50.0, 200.0, 1000.0, 2000.0, 2000.0], 10)]
    write(r, "test_fetch")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=("controls", "test"))
    ap.add_argument("--reference", default="e09_ref")
    ap.add_argument("--seeds", default="0-7")
    ap.add_argument("--prefix", default="")
    a = ap.parse_args()
    if a.what == "test":
        test()
    else:
        lo, hi = map(int, a.seeds.split("-"))
        controls(a.reference, range(lo, hi + 1), a.prefix)


if __name__ == "__main__":
    main()
