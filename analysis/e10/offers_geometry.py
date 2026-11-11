"""How many distinct compass offers a Landsat pass world gives at each radius: the walker's own CP.offers, on the built world.

    python analysis/e10/offers_geometry.py data/landsat/LM01_183_19721122/c5340m_128px_cir --snap-floor 4.0
    python analysis/e10/offers_geometry.py <world> --radii 5 7.5 10 15 30 50 75 100 150 200 300 --cells 3000

For each radius: from random cells of the world (and separately from cells near the strip's edge), with a random rotation as
the compass walker draws it (frame random, theta in [0, 45)), the number of distinct offers and why the others were dropped
(far: no cell within max(snap_tol r, snap_floor) of the target; dup: the same cell as another bearing; self: the walker's own
cell). Also the share of offers that are the cell's own neighbours twice over (two bearings snapping onto one cell) and the
median distance actually offered. Writes notes/10_landsat_pass/results/offers_geometry_<world>.csv.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from agent import compass as CP  # noqa: E402
from data.landsat_pass import PassStore  # noqa: E402
from data.tile_store import World, haversine_km  # noqa: E402

OUT = ROOT / "notes" / "10_landsat_pass" / "results"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("world")
    ap.add_argument("--radii", type=float, nargs="+", default=[5, 7.5, 10, 15, 20, 30, 50, 75, 100, 150, 200, 300, 500])
    ap.add_argument("--cells", type=int, default=3000)
    ap.add_argument("--snap-tol", type=float, default=0.25)
    ap.add_argument("--snap-floor", type=float, default=7.5)
    a = ap.parse_args()
    store = PassStore(a.world)
    W = World(store, None, "landsat_pass")
    rng = np.random.default_rng(0)
    lat, lon = W.lat, W.lon
    # cells within one cell size of the strip's edge: fewer than 6 of the 8 nearest-neighbour directions occupied
    cell_km = store.meta["cell_m"] / 1000.0
    nb = W.tree.query_radius(np.radians(np.stack([lat, lon], 1)), r=1.5 * cell_km / CP.EARTH_R_KM)
    edge = np.array([len(x) - 1 < 7 for x in nb])
    rows = []
    for group, pool in (("all", np.arange(store.N)), ("edge", np.flatnonzero(edge))):
        cells = rng.choice(pool, size=min(a.cells, len(pool)), replace=False)
        for r in a.radii:
            tol = max(a.snap_tol, a.snap_floor / r)
            n, far, dup, slf, dist = [], 0, 0, 0, []
            for t in cells:
                out, info = CP.offers(W, int(t), r, float(rng.uniform(0, 45)), tol)
                n.append(len(out))
                far += info["drop"].count("far")
                dup += info["drop"].count("dup")
                slf += info["drop"].count("self")
                if out:
                    dist += haversine_km(lat[t], lon[t], lat[out], lon[out]).tolist()
            n = np.array(n)
            rows.append({"group": group, "r_km": r, "cells": len(cells), "offers_mean": n.mean(), "offers_p05": np.percentile(n, 5), "share_8": (n == 8).mean(),
                         "share_ge6": (n >= 6).mean(), "share_ge4": (n >= 4).mean(), "share_0": (n == 0).mean(),
                         "drop_far": far / (8 * len(cells)), "drop_dup": dup / (8 * len(cells)), "drop_self": slf / (8 * len(cells)),
                         "dist_median": float(np.median(dist)) if dist else np.nan})
    d = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"offers_geometry_{Path(a.world).name}.csv"
    d.to_csv(p, index=False)
    print(f"{store.N} cells of {cell_km:.2f} km; edge cells {edge.sum()} ({edge.mean():.0%}); snap floor {a.snap_floor} km")
    print(d.round(3).to_string(index=False))
    print(f"-> {p}")


if __name__ == "__main__":
    main()
