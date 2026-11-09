"""Stage 0.2: the compass geometry (agent/compass.py).

    python analysis/e09/geometry.py            # checks, offer statistics, figure
    python analysis/e09/geometry.py --export   # also writes the check cases for the geographiclib comparison (see below)

1. Bearings and distances: destination() against an independent 3-D vector rotation, and round trip (haversine distance and initial bearing
   back from the target). The comparison with geographiclib (on a sphere of the same radius) runs in a separate throwaway environment,
   because the project does not depend on it:
       uv run --no-project --with geographiclib --with numpy python analysis/e09/geographiclib_check.py
2. Edge cases: near the poles, across the antimeridian.
3. Offers from 2,000 random cells of the global index at radii from 15 to 10,000 km: how many of the eight survive, and why the others are
   dropped (no cell within the snap tolerance, duplicate, the current cell), at several snap tolerances.
4. Figure: the offers of 20 random cells at five radii (results/geometry_offers.png).

Writes notes/09_compass/results/geometry_offers.csv and geometry_offers.png; prints the checks.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from e09_common import CACHE, OUT, ROOT  # sets sys.path

from agent.compass import EARTH_R_KM, bearings, destination, offers
from data.tile_store import haversine_km

RADII = (15, 20, 30, 50, 100, 300, 1000, 2000, 5000, 10000)
TOLS = (0.25, 0.5)
FLOORS = (0.0, 7.5)


def destination_vec(lat, lon, b, dist):
    """Independent: rotate the start's unit vector towards the bearing's tangent direction."""
    la, lo, bb, a = np.radians(lat), np.radians(lon), np.radians(b), np.asarray(dist) / EARTH_R_KM
    p = np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], -1)
    north = np.stack([-np.sin(la) * np.cos(lo), -np.sin(la) * np.sin(lo), np.cos(la)], -1)
    east = np.stack([-np.sin(lo), np.cos(lo), np.zeros_like(lo)], -1)
    t = np.cos(bb)[..., None] * north + np.sin(bb)[..., None] * east
    q = np.cos(a)[..., None] * p + np.sin(a)[..., None] * t
    return np.degrees(np.arcsin(np.clip(q[..., 2], -1, 1))), np.degrees(np.arctan2(q[..., 1], q[..., 0]))


def initial_bearing(lat1, lon1, lat2, lon2):
    la1, la2, dl = np.radians(lat1), np.radians(lat2), np.radians(lon2 - lon1)
    return np.degrees(np.arctan2(np.sin(dl) * np.cos(la2), np.cos(la1) * np.sin(la2) - np.sin(la1) * np.cos(la2) * np.cos(dl))) % 360


def lon_diff(a, b):
    return np.abs((a - b + 180) % 360 - 180)


def check_formulas(export: bool) -> None:
    rng = np.random.default_rng(9)
    n = 200_000
    lat = np.degrees(np.arcsin(rng.uniform(-1, 1, n)))
    lat = np.clip(lat, -89.0, 89.0)  # the bearing is undefined at a pole itself; poles are checked separately
    lon, b, d = rng.uniform(-180, 180, n), rng.uniform(0, 360, n), np.exp(rng.uniform(np.log(1), np.log(19_000), n))
    la2, lo2 = destination(lat, lon, b, d)
    la3, lo3 = destination_vec(lat, lon, b, d)
    pos = haversine_km(la2, lo2, la3, lo3)
    back = haversine_km(lat, lon, la2, lo2)
    ib = initial_bearing(lat, lon, la2, lo2)
    print(f"[0.2] vs vector rotation: max position difference {pos.max() * 1e3:.3g} m over {n} random cases (1-19,000 km)")
    print(f"[0.2] round trip: max |distance error| {np.abs(back - d).max() * 1e3:.3g} m, max bearing error {lon_diff(ib, b).max():.3g} deg")
    print(f"[0.2] longitudes in [-180, 180): {bool((lo2 >= -180).all() and (lo2 < 180).all())}")
    # edge cases
    cases = [("near the north pole", 89.95, 10.0, 0.0, 15.0), ("over the north pole", 89.95, 10.0, 0.0, 100.0), ("near the south pole", -89.95, -70.0, 180.0, 50.0),
             ("east across the antimeridian", 0.0, 179.95, 90.0, 15.0), ("west across the antimeridian", 65.0, -179.9, 270.0, 30.0),
             ("Paris, 2,000 km NE", 48.8566, 2.3522, 45.0, 2000.0), ("Paris, antipode", 48.8566, 2.3522, 0.0, np.pi * EARTH_R_KM)]
    for name, a, o, bb, dd in cases:
        x, y = destination(a, o, bb, dd)
        xv, yv = destination_vec(a, o, bb, dd)
        print(f"[0.2] {name}: ({a}, {o}) bearing {bb} {dd:.0f} km -> ({float(x):.4f}, {float(y):.4f}); vector ({float(xv):.4f}, {float(yv):.4f}); "
              f"distance back {float(haversine_km(a, o, x, y)):.3f} km")
    if export:
        CACHE.mkdir(parents=True, exist_ok=True)
        np.savez(CACHE / "e09_geometry_cases.npz", lat=lat[:20000], lon=lon[:20000], b=b[:20000], d=d[:20000], la2=la2[:20000], lo2=lo2[:20000], R=EARTH_R_KM)


class _World:
    """A data.tile_store.World without a tile store: the global index's cells and a BallTree over them."""

    def __init__(self) -> None:
        from sklearn.neighbors import BallTree

        idx = pd.read_parquet(ROOT / "data" / "global" / "index.parquet", columns=["lat", "lon", "cover"])
        self.lat, self.lon, self.cover = idx.lat.to_numpy(), idx.lon.to_numpy(), idx.cover.to_numpy()
        self.pool = np.arange(len(idx))
        self.tree = BallTree(np.radians(np.stack([self.lat, self.lon], 1)), metric="haversine")


def offer_stats(W: _World) -> pd.DataFrame:
    rng = np.random.default_rng(90)
    starts = rng.choice(len(W.pool), 2000, replace=False)
    thetas = rng.uniform(0, 45, len(starts))
    rows = []
    for r in RADII:
        for tol in TOLS:
            for floor in FLOORS:
                eff = max(tol, floor / r)
                n, far, dup, self_, ocean = [], 0, 0, 0, []
                for t, th in zip(starts, thetas):
                    o, info = offers(W, int(t), float(r), float(th), eff)
                    n.append(len(o))
                    far += info["drop"].count("far")
                    dup += info["drop"].count("dup")
                    self_ += info["drop"].count("self")
                    ocean += [W.cover[c] == "ocean" for c in o]
                n = np.array(n)
                rows.append({"radius_km": r, "snap_tol": tol, "snap_floor_km": floor, "offers_mean": n.mean(), "offers_p10": np.percentile(n, 10),
                             "none": (n == 0).mean(), "at_most_2": (n <= 2).mean(), "drop_far": far / (8 * len(starts)), "drop_dup": dup / (8 * len(starts)),
                             "drop_self": self_ / (8 * len(starts)), "ocean_share": float(np.mean(ocean)) if ocean else np.nan})
        print(f"[0.2] offers at {r} km done", flush=True)
    return pd.DataFrame(rows)


def land_raster(step: float = 1.0):
    from global_land_mask import globe

    la = np.arange(-89.5, 90, step)
    lo = np.arange(-179.5, 180, step)
    LO, LA = np.meshgrid(lo, la)
    return globe.is_land(LA, LO)


def plot_offers(W: _World, tol: float, floor: float) -> None:
    import matplotlib.pyplot as plt

    rng = np.random.default_rng(20)
    starts = rng.choice(len(W.pool), 20, replace=False)
    radii = (15, 100, 500, 2000, 10000)
    colours = ("#2a78d6", "#1baf7a", "#eda100", "#eb6834", "#6250d6")
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_axes((0.04, 0.38, 0.92, 0.58))
    ax.imshow(land_raster(), origin="lower", extent=(-180, 180, -90, 90), cmap="Greys", vmin=0, vmax=4, interpolation="nearest")
    cells = W.lat[W.pool[::50]], W.lon[W.pool[::50]]
    ax.scatter(cells[1], cells[0], s=0.05, color="#b5b4ad", rasterized=True)
    for r, c in zip(radii, colours):
        for t in starts:
            o, info = offers(W, int(t), float(r), float(rng.uniform(0, 45)), max(tol, floor / r))
            keep = np.array([x == "" for x in info["drop"]])
            ax.scatter(info["target_lon"][~keep], info["target_lat"][~keep], s=10, marker="x", color=c, lw=0.8)
            ax.scatter(W.lon[o], W.lat[o], s=9, color=c, label=f"{r:,} km" if t == starts[0] else None)
    ax.scatter(W.lon[starts], W.lat[starts], s=30, color="#0b0b0b", marker="*", label="start cell")
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.legend(loc="lower left", fontsize=8, ncol=6, frameon=True)
    ax.set_title(f"Compass offers from 20 random cells at five radii (dots: offered cells; x: target dropped, no cell within max({tol} r, {floor:g} km)). "
                 "Grey: indexed cells (1 in 50).", fontsize=9, loc="left")
    # zoom: one cell at r_min and 50 km, with the 10 km grid
    for k, (r, w) in enumerate(((15, 40), (30, 70), (100, 200))):
        a = fig.add_axes((0.04 + 0.32 * k, 0.03, 0.28, 0.31))
        t = int(starts[3])
        near = W.tree.query_radius(np.radians([[W.lat[t], W.lon[t]]]), r=w * 1.5 / EARTH_R_KM)[0]
        a.scatter(W.lon[near], W.lat[near], s=6, color="#b5b4ad")
        o, info = offers(W, t, float(r), 10.0, max(tol, floor / r))
        a.scatter(info["target_lon"], info["target_lat"], s=25, marker="+", color="#0b0b0b", label="targets")
        a.scatter(W.lon[o], W.lat[o], s=22, color="#2a78d6", label="offers")
        a.scatter(W.lon[t], W.lat[t], s=60, marker="*", color="#eb6834", label="current cell")
        a.set_aspect(1 / np.cos(np.radians(W.lat[t])))
        a.set_title(f"r = {r} km: {len(o)} offers", fontsize=8)
        a.tick_params(labelsize=7)
        if k == 0:
            a.legend(fontsize=7, loc="lower left")
    fig.savefig(OUT / "geometry_offers.png", dpi=110)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    check_formulas(a.export)
    W = _World()
    S = offer_stats(W)
    S.to_csv(OUT / "geometry_offers.csv", index=False)
    pd.set_option("display.width", 250)
    print(S.round(3).to_string(index=False))
    plot_offers(W, 0.25, 7.5)


if __name__ == "__main__":
    main()
