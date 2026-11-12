"""Portrait of the Landsat 1 world (notes/brief_landsat_pipeline.md, A3): what the earliest rule makes of the mission.

    python analysis/landsat1/portrait.py     # -> notes/11_landsat1_mission/results/world_*.csv, figures/world_*.png

From data/landsat1/index.parquet (and grid.parquet, candidates.parquet) only, plus the baseline's quirk table
(data/landsat1/baseline.parquet, 2,000 random cells) for the pixel-measured shares. Every cell is ~10.7 km a side, so cell counts
are areas. Regions as analysis/landsat1/census.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
W = ROOT / "data" / "landsat1"
FIG = ROOT / "notes" / "11_landsat1_mission" / "figures"
RES = ROOT / "notes" / "11_landsat1_mission" / "results"
REGIONS = {"N America": (15, 75, -170, -50), "S America": (-56, 15, -82, -34), "Europe": (35, 72, -10, 40), "Africa": (-35, 37, -18, 52),
           "Asia": (5, 78, 40, 180), "Oceania": (-48, 0, 110, 180), "Antarctica": (-90, -60, -180, 180)}
INK, MUTED = "#2b2b2a", "#6b6a63"


def region(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    out = np.full(len(lat), "other", dtype=object)
    for r, (a, b, c0, c1) in REGIONS.items():  # first match wins; Europe before Africa and Asia
        m = (out == "other") & (lat >= a) & (lat < b) & (lon >= c0) & (lon < c1)
        out[m] = r
    return out


def main() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIG.mkdir(parents=True, exist_ok=True)
    RES.mkdir(parents=True, exist_ok=True)
    g = pd.read_parquet(W / "grid.parquet", columns=["cell", "lat", "lon", "cover"])
    x = pd.read_parquet(W / "index.parquet")
    g["region"] = region(g.lat.to_numpy(), g.lon.to_numpy())
    x["region"] = region(x.lat.to_numpy(), x.lon.to_numpy())
    x["year"] = x.timestamp.dt.year
    x["month"] = x.timestamp.dt.to_period("M")

    # coverage, levels, tiers, cloud, night by region
    rows = []
    for r, gg in list(g.groupby("region")) + [("all", g), ("all but Antarctica", g[g.region != "Antarctica"])]:
        xx = x[x.cell.isin(gg.cell)] if r not in ("all",) else x
        if r == "all but Antarctica":
            xx = x[x.region != "Antarctica"]
        rows.append({"region": r, "grid_cells": len(gg), "world_cells": len(xx), "covered": len(xx) / len(gg),
                     "first_date_median": str(xx.timestamp.median().date()) if len(xx) else "",
                     "share_1972": float((xx.year == 1972).mean()), "share_1973": float((xx.year == 1973).mean()),
                     "share_1974_on": float((xx.year >= 1974).mean()),
                     "L1GS": float((xx.level == "L1GS").mean()), "T1": float((xx.tier == "T1").mean()),
                     "scene_cloud_median": float(xx.scene_cloud.median()), "scene_cloud_gt50": float((xx.scene_cloud > 50).mean()),
                     "night": float(xx.night.mean()), "sun_below_15": float((xx.sun_elevation < 15).mean()),
                     "candidates_median": float(xx.n_candidates.median())})
    reg = pd.DataFrame(rows)
    reg.to_csv(RES / "world_regions.csv", index=False)
    print(reg.round(3).to_string(index=False))

    # date histogram by month, split by level
    m = x.groupby(["month", "level"]).size().unstack(fill_value=0)
    m = m.reindex(pd.period_range(m.index.min(), m.index.max(), freq="M"), fill_value=0)  # empty months stay empty in the figure
    m.to_csv(RES / "world_months.csv")
    fig, ax = plt.subplots(figsize=(10, 3.2))
    idx = m.index.to_timestamp()
    for lv, col in (("L1TP", "#3a6ea5"), ("L1GS", "#d08a2c")):  # separate lines: stacked bars would misstate shares on a log axis
        ax.step(idx, m.get(lv, 0).replace(0, np.nan), where="mid", color=col, lw=1.6, label=lv)
    ax.set_yscale("log")
    ax.set_ylabel("cells first imaged (log)")
    ax.set_title(f"The Landsat 1 world under the earliest rule: {len(x):,} cells by the month of their acquisition", loc="left", fontsize=10, color=INK)
    ax.legend(frameon=False, fontsize=8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "world_dates_hist.png", dpi=130)
    plt.close(fig)

    # map of acquisition dates: each cell as a point, colour = days since first light
    days = (x.timestamp - x.timestamp.min()).dt.days.to_numpy()
    fig, ax = plt.subplots(figsize=(13, 6.4))
    ax.set_facecolor("#f4f3ef")
    gl = g[~g.cell.isin(x.cell)]
    ax.scatter(gl.lon, gl.lat, s=0.05, c="#c9c6bc", linewidths=0, rasterized=True)
    o = np.argsort(-days)  # early cells drawn last, on top
    sc = ax.scatter(x.lon.to_numpy()[o], x.lat.to_numpy()[o], s=0.05, c=days[o], cmap="viridis_r", vmin=0, vmax=600, linewidths=0, rasterized=True)
    cb = fig.colorbar(sc, ax=ax, fraction=0.02, pad=0.01)
    cb.set_label("days after first light (25 Jul 1972); 600 = Mar 1974 and later", fontsize=8)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-85, 85)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("The Landsat 1 world: one acquisition per 10 km cell, the earliest. Grey: land cells no Landsat 1 scene covers whole.",
                 loc="left", fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(FIG / "world_dates_map.png", dpi=150)
    plt.close(fig)

    # map of the processing level and night
    fig, ax = plt.subplots(figsize=(13, 6.4))
    ax.set_facecolor("#f4f3ef")
    col = np.where(x.night, "#111111", np.where(x.level == "L1GS", "#d08a2c", "#3a6ea5"))
    ax.scatter(x.lon, x.lat, s=0.05, c=col, linewidths=0, rasterized=True)
    for c, lab in (("#3a6ea5", "L1TP (terrain-corrected)"), ("#d08a2c", "L1GS (systematic: may be offset by km)"), ("#111111", "night (sun <= 0)")):
        ax.scatter([], [], c=c, s=20, label=lab)
    ax.legend(loc="lower left", fontsize=8, frameon=False)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-85, 85)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("The Landsat 1 world: processing level of each cell's acquisition, night cells in black", loc="left", fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(FIG / "world_levels_map.png", dpi=150)
    plt.close(fig)

    # pixel-measured shares on the baseline sample
    b = pd.read_parquet(W / "baseline.parquet")
    bands = ("green", "red", "nir08")
    b["stripe_max"] = b[[f"stripe_{k}" for k in bands]].max(axis=1)
    b["at255_max"] = b[[f"at255_{k}" for k in bands]].max(axis=1)
    b["satflag_max"] = b[[f"satflag_{k}" for k in bands]].max(axis=1)
    b["disagree_max"] = b[[f"disagree_{k}" for k in bands]].max(axis=1)
    q = {}
    for k in ("cloud", "fill", "stripe_max", "at255_max", "satflag_max", "disagree_max", "dropped"):
        v = b[k]
        q[k] = {"mean": v.mean(), "median": v.median(), "p90": v.quantile(0.9), "share_gt_1pct": (v > 0.01).mean(), "share_gt_10pct": (v > 0.1).mean()}
    qt = pd.DataFrame(q).T
    by = b.groupby("level")[["cloud", "stripe_max", "at255_max", "satflag_max"]].median()
    qt.to_csv(RES / "world_quirks_baseline.csv")
    by.to_csv(RES / "world_quirks_by_level.csv")
    print(qt.round(4).to_string())
    print(by.round(4).to_string())
    # QA cloud against the scene's listed cloud
    rho = b[["cloud", "scene_cloud"]].corr("spearman").iloc[0, 1]
    print(f"Spearman(cell QA cloud, scene cloud) {rho:.2f}; night cells in the baseline {int(b.night.sum())}")


if __name__ == "__main__":
    main()
