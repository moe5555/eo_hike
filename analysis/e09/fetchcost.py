"""Stage 0.4: how far the compass walker gets and what its far offers cost, estimated offline.

    python analysis/e09/fetchcost.py [--latency runs/<test walk>]

A blind walker (uniform choice among the offers) walks the global index from Paris, 1,000 steps, with the radius sequence that the drive gave
on each of the e08 Reference's eight walks (Stage 0.3: interest_long, delta 0.35, warm-up 50), at several r_max. A blind walker is the
cheapest stand-in: a curious one chooses differently but meets the same offers at the same radii. For every step it counts the offers that
would have to be fetched (not seen before: neither offered nor within r_min + 10 km, the prefetch ring, of a cell stood on), and from that
the time a walk spends waiting for tiles: a step waits for the slowest of its fresh tiles (fetched in parallel), capped at the 30 s
timeout, less the time training overlaps it. Latencies are drawn from fetches.parquet of e08 walks (remote fetches only, three walks side
by side), or from a given test walk.

Range: continents reached (rough boxes, `continent()`), whether and when the walk leaves Europe, the largest distance from Paris, ocean
share of the cells stood on.

Writes notes/09_compass/results/fetchcost.csv (per seed and r_max) and prints the summary.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from e09_common import CACHE, OUT, R_MIN, ROOT, RUNS  # sets sys.path
from geometry import _World

from agent.compass import offers, radii
from data.tile_store import haversine_km

PARIS = (48.8566, 2.3522)
R_MAXES = (500, 1000, 2000, 5000, 10000)
DELTA, WARMUP, SIGNAL = 0.35, 50, "d_interest_long"
RING = R_MIN + 10.0
TIMEOUT = 30.0
OVERLAP = 0.5  # seconds of training (and scoring of the next step's offers) that a prefetch of the next offers overlaps
LATENCY_RUNS = ("e08_reference_s4", "e08_reference_s5", "e08_radius_25_s0", "e08_radius_25_s1", "e08_knn_3_s4", "e08_temp_02_s4")


def continent(lat, lon) -> np.ndarray:
    """Rough continent from boxes: good enough to tell whether a walk left Europe, not for borders."""
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    out = np.full(lat.shape, "Asia", dtype=object)
    sa = (lat < 12.5) & (lat > -60) & (lon > -82) & (lon < -30) & ~((lat > 7) & (lon < -77.2))
    na = ((lon < -30) & (lat > -60) & ~sa & ~((lon < -125) & (lat < 30))) | ((lon > 172) & (lat > 45))
    af_north = np.where(lon < -2, 35.95, np.where(lon < 11.6, 37.4, np.where(lon < 32, 33.5, 31.5)))
    af = (lon > -26) & (lon < 52) & (lat > -36) & (lat < af_north) & ~((lon > 34) & (lat > 12.5))
    eu = (lat >= 34.5) & (lon >= -32) & (lon <= 60) & ~af & ~((lon > 26) & (lat < 41.3)) & ~((lon > 40) & (lat < 47))
    oc = ((lon > 141) & (lat < 0) & (lat > -60)) | ((lon > 110) & (lat < -10.5) & (lat > -60)) | (((lon > 155) | (lon < -130)) & (lat < 30) & (lat > -60) & ~na)
    out[eu] = "Europe"
    out[af] = "Africa"
    out[na] = "North America"
    out[sa] = "South America"
    out[oc] = "Oceania"
    out[lat <= -60] = "Antarctica"
    return out


def latencies(test: str | None) -> np.ndarray:
    runs = (test,) if test else LATENCY_RUNS
    v = np.concatenate([pd.read_parquet(RUNS / r / "fetches.parquet").sec.to_numpy() for r in runs if (RUNS / r / "fetches.parquet").exists()])
    return v


def walk(W: _World, r: np.ndarray, rng: np.random.Generator) -> dict:
    t = int(W.tree.query(np.radians([PARIS]), k=1)[1][0, 0])
    seen: set[int] = set()
    pos, fresh = [t], []
    for k in range(len(r)):
        o, _ = offers(W, t, float(r[k]), float(rng.uniform(0, 45)), max(0.25, 7.5 / r[k]))
        if not o:
            o = [int(c) for c in W.tree.query(np.radians([[W.lat[t], W.lon[t]]]), k=9)[1][0] if c != t][:8]
        near = W.tree.query_radius(np.radians([[W.lat[t], W.lon[t]]]), r=RING / 6371.0088)[0]
        seen.update(map(int, near))
        fresh.append(sum(c not in seen for c in o))
        seen.update(o)
        t = int(o[rng.integers(len(o))])
        pos.append(t)
    pos = np.array(pos)
    la, lo = W.lat[pos], W.lon[pos]
    cont = continent(la, lo)
    out_eu = np.flatnonzero(cont != "Europe")
    return {"fresh": np.array(fresh), "continents": len(set(cont)), "left_europe": len(out_eu) > 0, "first_step_outside": int(out_eu[0]) if len(out_eu) else np.nan,
            "share_outside_europe": float((cont != "Europe").mean()), "max_km_from_paris": float(haversine_km(PARIS[0], PARIS[1], la, lo).max()),
            "ocean_share": float((W.cover[pos] == "ocean").mean()), "unique_cells": len(set(pos.tolist()))}


def wait_seconds(fresh: np.ndarray, lat_s: np.ndarray, rng: np.random.Generator) -> float:
    tot = 0.0
    for k in fresh:
        if k:
            tot += max(min(rng.choice(lat_s, k).max(), TIMEOUT) - OVERLAP, 0.0)
    return tot


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--latency", help="a test walk's run name: draw latencies from its fetches.parquet")
    a = ap.parse_args()
    A = pd.read_parquet(CACHE / "e09_mapping_series.parquet")
    A = A[A.group == "Reference"]
    lat_s = latencies(a.latency)
    print(f"[0.4] latency: {len(lat_s)} remote fetches, median {np.median(lat_s):.2f} s, p90 {np.percentile(lat_s, 90):.2f} s, p99 {np.percentile(lat_s, 99):.2f} s")
    W = _World()
    rows = []
    for sd, x in A.groupby("seed"):
        for rmax in R_MAXES:
            r = radii(x[SIGNAL].to_numpy(), R_MIN, rmax, DELTA, 0.0, WARMUP)
            rng = np.random.default_rng([90, int(sd), rmax])
            w = walk(W, r, rng)
            fresh = w.pop("fresh")
            rows.append({"seed": sd, "r_max": rmax, "steps_beyond_ring": int((r > RING).sum()), "steps_fetching": int((fresh > 0).sum()),
                         "fresh_tiles": int(fresh.sum()), "wait_min": wait_seconds(fresh, lat_s, rng) / 60, **w})
        print(f"[0.4] seed {sd}", flush=True)
    F = pd.DataFrame(rows)
    F.to_csv(OUT / ("fetchcost.csv" if not a.latency else f"fetchcost_{a.latency}.csv"), index=False)
    pd.set_option("display.width", 250)
    print(F.groupby("r_max").agg(steps_beyond_ring=("steps_beyond_ring", "mean"), steps_fetching=("steps_fetching", "mean"), fresh_tiles=("fresh_tiles", "mean"),
                                 wait_min=("wait_min", "mean"), wait_min_max=("wait_min", "max"), left_europe=("left_europe", "mean"),
                                 first_step_outside=("first_step_outside", "median"), share_outside_europe=("share_outside_europe", "mean"),
                                 continents=("continents", "mean"), max_km=("max_km_from_paris", "median"), ocean=("ocean_share", "mean"),
                                 unique=("unique_cells", "mean")).round(2).to_string())


if __name__ == "__main__":
    main()
