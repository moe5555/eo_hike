"""The season-seam readout (2026-11-11; predictions 91-95 in notes/06_characters/expectations.md): does the choice follow the seams of the
Major TOM mosaic?

    python analysis/e09/seams.py                          # every finished run of readouts.GROUPS (compass walks), paired against the Null
    python analysis/e09/seams.py --runs e09_v1_long_s0    # given runs only, plus blocks of 1,000 steps

The world is one acquisition per 10 km cell (data/global/index.parquet: `timestamp`, `product_id`), from 2016 to 2023 and any season,
stitched into one image. At every step the offers are made around "here", the tile chosen at the step before (step 0 is skipped). Per
offered cell, against here:
- seam: the offer comes from another datatake than here. A datatake is one satellite's continuous acquisition, the product's platform
  and sensing start (`S2B_..._20190728T000149_...`), shared by every granule of one overpass.
- days_gap: |acquisition time of the offer − of here|, in days. doy_gap: the same on the day of the year (circular, 0-182), the season
  apart regardless of year.
- cold: the offer was imaged in the local cold half-year (Nov-Apr north, May-Oct south); NaN within 30° of the equator.
- bright: as in the e08/e09 taste readouts (sheet.tile_stats: grey mean and saturation thresholds, snow, ice and cloud).
- same_baseline: the offer's ESA processing baseline (the product name's `Nxxxx`) equals here's. same_year: the acquisition year does.
  Added after the first pass (2026-11-11, not predicted): the choice followed the date but not the season. Baseline and year are
  confounded (N9999 only up to 2022, none in 2023).

In Major TOM a datatake leaves a median of 12 cells scattered over the planet, so neighbouring cells almost never share one: seam_share is
1.0 in every e09 walk and seam_cross_excess is 0 by construction. Both are kept as the record of the world.

Readouts per run and phase (phases as readouts.py: all, young < 150, settled >= 150):
- seam_share: the mean over steps of the share of offers across a seam (the world, not the choice).
- seam_cross_excess: the share of choices across a seam minus seam_share (as revisit_excess: the choice beyond a blind walker over the
  actual offers).
- same_baseline_excess, same_year_excess: as seam_cross_excess, on same_baseline and same_year.
- cold_excess: the chosen offer's cold minus the mean over its step's offers, steps where cold is defined for at least two offers.
- selz_cold, selz_daysgap, selz_doygap, selz_bright: the chosen offer's property minus the mean over the offers, in SDs of the offers,
  averaged over steps where it varies (the readouts.py taste definition).
- selz_bright_inseason: selz_bright over only the offers of the chosen offer's own season class (cold or not), steps with at least two
  such offers that differ in bright. Whether the taste for bright ground holds once the season is held fixed.
Steps with one offer are left out.

Writes notes/09_compass/results/seams.csv (one row per run and phase), seams_paired.csv (setting − compass Null and setting − compass
Reference per seed, e08 verdicts) and, with --runs, seams_blocks_<run>.csv (the same readouts per block of 1,000 steps).
"""

from __future__ import annotations

import argparse
import importlib.util

import numpy as np
import pandas as pd
from e09_common import OUT, ROOT, RUNS  # sets sys.path

_spec = importlib.util.spec_from_file_location("e09_readouts", ROOT / "analysis" / "e09" / "readouts.py")  # e08 has a readouts.py on the path too
_ro = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ro)
sheet, E08, PHASES = _ro.sheet, _ro.E08, _ro.PHASES

NULL, REFERENCE = "compass Null", _ro.REFERENCE
COLD_LAT = 30.0
BLOCK = 1000
SELZ = {"cold": "cold", "daysgap": "days_gap", "doygap": "doy_gap", "bright": "bright"}


def index() -> pd.DataFrame:
    ix = pd.read_parquet(ROOT / "data" / "global" / "index.parquet", columns=["idx", "lat", "timestamp", "product_id"]).set_index("idx")
    p = ix.product_id.str.split("_")
    ix["take"] = p.str[0] + "_" + p.str[2]
    ix["baseline"] = p.str[3]
    ix["year"] = ix.timestamp.dt.year
    m, south = ix.timestamp.dt.month, ix.lat < 0
    cold = np.where(south, m.between(5, 10), m.isin([11, 12, 1, 2, 3, 4])).astype(float)
    ix["cold"] = np.where(ix.lat.abs() >= COLD_LAT, cold, np.nan)
    ix["t_day"] = (ix.timestamp - pd.Timestamp("2016-01-01")).dt.total_seconds() / 86400.0
    ix["doy"] = ix.timestamp.dt.day_of_year.astype(float)
    return ix[["take", "baseline", "year", "cold", "t_day", "doy"]]


def per_step(run: str, ix: pd.DataFrame, ts: pd.DataFrame) -> pd.DataFrame:
    """One row per step with more than one offer: the chosen offer's properties against its offers'."""
    s = pd.read_parquet(RUNS / run / "steps.parquet", columns=["step", "tile_idx"])
    c = pd.read_parquet(RUNS / run / "candidates.parquet", columns=["step", "tile_idx", "chosen"])
    c = c[c.step > 0]
    here = pd.Series(s.tile_idx.to_numpy(), index=s.step.to_numpy() + 1, name="here")
    c = c.join(here, on="step").join(ix, on="tile_idx").join(ix.add_suffix("_here"), on="here").join(ts[["bright"]], on="tile_idx")
    c["seam"] = (c.take != c.take_here).astype(float)
    c["same_baseline"] = (c.baseline == c.baseline_here).astype(float)
    c["same_year"] = (c.year == c.year_here).astype(float)
    c["days_gap"] = (c.t_day - c.t_day_here).abs()
    dd = (c.doy - c.doy_here).abs()
    c["doy_gap"] = np.minimum(dd, 365.25 - dd)
    c = c[c.groupby("step").step.transform("size") > 1]
    g = c.groupby("step")
    ch = c[c.chosen].set_index("step")
    out = pd.DataFrame({"seam_share": g.seam.mean(), "seam_chosen": ch.seam})
    for k in ("same_baseline", "same_year"):
        out[f"{k}_share"], out[f"{k}_chosen"] = g[k].mean(), ch[k]
    for name, col in SELZ.items():
        sd = g[col].std(ddof=0)
        out[f"selz_{name}"] = (ch[col] - g[col].mean()) / sd.where(sd > 0)
    nc = g.cold.count()
    out["cold_excess"] = (ch.cold - g.cold.mean()).where(nc >= 2)
    # bright among the offers of the chosen offer's own season class only (NaN class: the tropics, left out)
    same = c[c.cold == c.step.map(ch.cold)]
    gs = same.groupby("step")
    sd = gs.bright.std(ddof=0)
    out["selz_bright_inseason"] = ((same[same.chosen].set_index("step").bright - gs.bright.mean()) / sd.where(sd > 0)).where(gs.size() >= 2)
    return out


def summarise(p: pd.DataFrame) -> dict:
    return {"steps_read": len(p), "seam_share": float(p.seam_share.mean()), "seam_cross_excess": float(p.seam_chosen.mean() - p.seam_share.mean()),
            **{f"{k}_excess": float(p[f"{k}_chosen"].mean() - p[f"{k}_share"].mean()) for k in ("same_baseline", "same_year")},
            "same_baseline_share": float(p.same_baseline_share.mean()),
            "cold_excess": float(p.cold_excess.mean()), "cold_steps": int(p.cold_excess.notna().sum()),
            **{f"selz_{k}": float(p[f"selz_{k}"].mean()) for k in [*SELZ, "bright_inseason"]},
            "inseason_steps": int(p.selz_bright_inseason.notna().sum())}


def readouts(group: str, seed: int, run: str, ix: pd.DataFrame, ts: pd.DataFrame) -> list[dict]:
    p = per_step(run, ix, ts)
    rows = []
    for phase, (lo, hi) in PHASES.items():
        q = p[(p.index >= lo) & (p.index < hi)]
        rows.append({"group": group, "seed": seed, "run": run, "phase": phase, **summarise(q)})
    return rows


def blocks(run: str, ix: pd.DataFrame, ts: pd.DataFrame) -> pd.DataFrame:
    p = per_step(run, ix, ts)
    return pd.DataFrame([{"run": run, "block_start": b * BLOCK, **summarise(q)} for b, q in p.groupby(p.index // BLOCK)])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="*", help="run names; their group is the run name")
    a = ap.parse_args()
    if a.runs:
        rl = [(r, 0, r) for r in a.runs]
    else:  # compass walks only: the classic walkers' far offers and teleports are another kind of offer
        rl = [x for x in _ro.runs() if sheet.config(x[2]).get("nav", "classic") == "compass"]
    print(f"[seams] {len(rl)} runs", flush=True)
    ix = index()
    ids = np.unique(np.concatenate([pd.read_parquet(RUNS / r / "candidates.parquet", columns=["tile_idx"]).tile_idx.to_numpy() for _, _, r in rl]))
    ts = sheet.tile_stats(ids)
    rows = []
    for g, sd, r in rl:
        rows += readouts(g, sd, r, ix, ts)
    R = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    if a.runs:
        R.to_csv(OUT / "seams_check.csv", index=False)
        for r in a.runs:
            B = blocks(r, ix, ts)
            B.to_csv(OUT / f"seams_blocks_{r}.csv", index=False)
            print(B.round(3).to_string(index=False))
    else:
        R.to_csv(OUT / "seams.csv", index=False)
        M = R.drop(columns=["steps_read", "cold_steps", "inseason_steps"])
        pd.concat([E08.paired(M, against=NULL), E08.paired(M, against=REFERENCE)]).to_csv(OUT / "seams_paired.csv", index=False)
    pd.set_option("display.width", 250)
    print(R[R.phase == "settled"].drop(columns=["phase"]).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
