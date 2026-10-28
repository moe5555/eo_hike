"""Dreams v3 maps and walk summaries.

    python analysis/v3_maps.py runs/global_baseline_s0 runs/confined_baseline_s0

Writes <global run>/dreams_v3/map_global_path.png (world, coloured by step: the first v3 output),
<confined run>/dreams_v3/map_confined_path.png (the circle, its tiles and the path), a copy of both plus the
base_global map in <global run>/dreams_v3/maps/, and walk_summary.json per run.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.global_index import world_axes  # noqa: E402
from data.tile_store import EARTH_R_KM, haversine_km  # noqa: E402


def segments(s: pd.DataFrame):
    """Consecutive moves; jumps (> 30 km) and dateline crossings are drawn separately."""
    la, lo = s.lat.to_numpy(), s.lon.to_numpy()
    near = (s.dist_km.to_numpy()[1:] <= 30) & (np.abs(np.diff(lo)) < 180)
    return la, lo, near


def summary(run: Path) -> dict:
    s = pd.read_parquet(run / "steps.parquet")
    meta = json.loads((run / "meta.json").read_text())
    first = s.drop_duplicates("tile_idx")
    out = {
        "run": run.name, "steps": len(s), "unique_tiles": int(s.tile_idx.nunique()), "revisit_share": round(1 - s.tile_idx.nunique() / len(s), 3),
        "bored_events": int(s.bored_event.sum()), "jumps": s.jump_type.value_counts().to_dict(),
        "chosen_long_jumps": int((s.jump_type == "long").sum()), "km_walked": round(float(s.dist_km.sum())),
        "cover_share_unique_tiles": first.cover.value_counts(normalize=True).round(3).to_dict(),
        "lat_range": [round(float(s.lat.min()), 2), round(float(s.lat.max()), 2)], "lon_range": [round(float(s.lon.min()), 2), round(float(s.lon.max()), 2)],
        "fetch_sec_mean": round(float(s.fetch_sec.mean()), 3), "fetch_sec_p95": round(float(s.fetch_sec.quantile(0.95)), 3),
        "fetch_sec_max": round(float(s.fetch_sec.max()), 2), "cache_hit_rate": round(float(s.n_cache_hit.sum() / max(s.n_fetch.sum(), 1)), 3),
        "dropped_candidates": int(s.n_dropped.sum()), "steps_with_drops": int((s.n_dropped > 0).sum()),
        "seconds": meta.get("seconds"), "sec_per_step": round(meta.get("seconds", np.nan) / len(s), 3), "store": meta.get("store"),
        "birthplace": {"tile": meta["start_tile"], "cell": meta.get("start_cell"), "latlon": meta.get("start_latlon"), "cover": meta.get("start_cover")},
    }
    (run / "dreams_v3").mkdir(parents=True, exist_ok=True)
    (run / "dreams_v3" / "walk_summary.json").write_text(json.dumps(out, indent=2, default=str))
    return out


def global_map(run: Path) -> Path:
    s = pd.read_parquet(run / "steps.parquet")
    la, lo, near = segments(s)
    fig, ax = plt.subplots(figsize=(16, 8.5))
    world_axes(ax, f"{run.name}: {len(s):,} steps, {s.tile_idx.nunique():,} unique tiles; colour = step; dashed = jumps (> 30 km)")
    cmap = plt.get_cmap("viridis")
    for k in np.flatnonzero(~near):
        ax.plot(lo[k : k + 2], la[k : k + 2], "--", lw=0.5, color="0.45", alpha=0.6)
    sc = ax.scatter(lo, la, c=s.step, cmap=cmap, s=5, lw=0, zorder=3)
    ax.scatter(lo[0], la[0], marker="*", s=220, c="red", edgecolors="k", zorder=5, label="birthplace")
    ax.scatter(lo[-1], la[-1], marker="X", s=90, c="white", edgecolors="k", zorder=5, label="last step")
    b = s[s.bored_event]
    ax.scatter(b.lon, b.lat, marker="o", s=30, facecolors="none", edgecolors="crimson", lw=0.8, zorder=4, label=f"bored ({len(b)})")
    ax.legend(loc="lower left", fontsize=8)
    fig.colorbar(sc, ax=ax, fraction=0.02, pad=0.01, label="step")
    out = run / "dreams_v3" / "map_global_path.png"
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


def confined_map(run: Path) -> Path:
    cfg = yaml.safe_load((run / "config.yaml").read_text())
    (c_la, c_lo), r = cfg["confine_center"], float(cfg["confine_radius_km"])
    s = pd.read_parquet(run / "steps.parquet")
    idx = pd.read_parquet(ROOT / "data" / "global" / "index.parquet", columns=["lat", "lon", "cover"])
    inside = haversine_km(idx.lat.to_numpy(), idx.lon.to_numpy(), c_la, c_lo) <= r
    pool = idx[inside]
    fig = plt.figure(figsize=(16, 9))
    ax = fig.add_axes([0.04, 0.06, 0.62, 0.88])
    ax.scatter(pool.lon, pool.lat, s=3, c="0.82", lw=0, label=f"tiles in the circle ({len(pool):,})")
    th = np.linspace(0, 2 * np.pi, 361)
    ang = r / EARTH_R_KM
    cla, clo = np.radians(c_la), np.radians(c_lo)
    pla = np.arcsin(np.sin(cla) * np.cos(ang) + np.cos(cla) * np.sin(ang) * np.cos(th))
    plo = clo + np.arctan2(np.sin(th) * np.sin(ang) * np.cos(cla), np.cos(ang) - np.sin(cla) * np.sin(pla))
    ax.plot(np.degrees(plo), np.degrees(pla), "k-", lw=1, label=f"confinement: {r:.0f} km around ({c_la}, {c_lo})")
    la, lo, near = segments(s)
    for k in np.flatnonzero(~near):
        ax.plot(lo[k : k + 2], la[k : k + 2], "--", lw=0.5, color="0.45", alpha=0.6)
    sc = ax.scatter(lo, la, c=s.step, cmap="viridis", s=7, lw=0, zorder=3)
    ax.scatter(lo[0], la[0], marker="*", s=220, c="red", edgecolors="k", zorder=5, label="birthplace")
    b = s[s.bored_event]
    ax.scatter(b.lon, b.lat, marker="o", s=30, facecolors="none", edgecolors="crimson", lw=0.8, zorder=4, label=f"bored ({len(b)})")
    ax.set_aspect(1 / np.cos(np.radians(c_la)))
    ax.legend(loc="lower left", fontsize=8)
    ax.set_title(f"{run.name}: {len(s):,} steps, {s.tile_idx.nunique():,} of {len(pool):,} tiles visited; colour = step")
    fig.colorbar(sc, ax=ax, fraction=0.03, pad=0.01, label="step")
    ax2 = fig.add_axes([0.70, 0.55, 0.28, 0.4])
    world_axes(ax2, "where the circle is")
    ax2.plot(np.degrees(plo), np.degrees(pla), "r-", lw=1.5)
    out = run / "dreams_v3" / "map_confined_path.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


if __name__ == "__main__":
    g, c = Path(sys.argv[1]), Path(sys.argv[2])
    for r in (g, c):
        print(json.dumps(summary(r), indent=2, default=str))
    maps = g / "dreams_v3" / "maps"
    maps.mkdir(parents=True, exist_ok=True)
    for p in (global_map(g), confined_map(c), ROOT / "data" / "v3" / "base_global" / "map_base_global.png"):
        if p.exists():
            shutil.copy(p, maps / p.name)
            print(f"[v3_maps] {p}")
