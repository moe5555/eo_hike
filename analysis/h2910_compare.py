"""Hikes 29.10: compare the four characters with the reference (notes/hikes_2910/).

    python analysis/h2910_compare.py

Reads runs/global_perception_1k_s{0,1} and runs/h2910_<character>_s{0,1} (missing runs are skipped). Writes to
notes/hikes_2910/: summary.csv (one row per run), maps_world.png, maps_milan.png (±6° around the start),
curves.png (unique tiles, held-out MSE, boredom B over steps), and prints a per-character table.

Colour diversity is a yardstick shared by all runs (each run's own latents come from a different encoder):
the mean pairwise distance between the visited tiles' mean RGB (0-255), computed from the cached 256 px tiles.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.global_index import world_axes  # noqa: E402
from data.tile_store import EARTH_R_KM, haversine_km  # noqa: E402

OUT = ROOT / "notes" / "hikes_2910"
CHARACTERS = {"Reference": "global_perception_1k", "Bored": "h2910_bored", "Globalist": "h2910_globalist",
              "Localist": "h2910_localist", "Fast learner": "h2910_fastlearner"}
SEEDS = (0, 1)
COLOURS = {"Reference": "0.3", "Bored": "tab:red", "Globalist": "tab:blue", "Localist": "tab:green", "Fast learner": "tab:purple"}


def runs() -> list[tuple[str, int, Path]]:
    out = []
    for ch, stem in CHARACTERS.items():
        for s in SEEDS:
            r = ROOT / "runs" / f"{stem}_s{s}"
            if (r / "steps.parquet").exists():
                out.append((ch, s, r))
    return out


def radius_of_gyration_km(lat: np.ndarray, lon: np.ndarray) -> float:
    """RMS great-circle distance of the visited positions from their centre of mass on the sphere."""
    la, lo = np.radians(lat), np.radians(lon)
    v = np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], 1)
    c = v.mean(0)
    c /= np.linalg.norm(c)
    ang = np.arccos(np.clip(v @ c, -1, 1))
    return float(np.sqrt(np.mean((ang * EARTH_R_KM) ** 2)))


_STORE = None


def colour_diversity(tile_ids: np.ndarray) -> float:
    global _STORE
    if _STORE is None:
        from data.tile_store import TileStore

        _STORE = TileStore()
    rgb = np.array([_STORE.get_lowres(int(i)).reshape(-1, 3).mean(0) for i in tile_ids])
    d = np.sqrt(((rgb[:, None] - rgb[None]) ** 2).sum(-1))
    return float(d[np.triu_indices(len(rgb), 1)].mean())


def stats(ch: str, seed: int, run: Path) -> dict:
    s = pd.read_parquet(run / "steps.parquet")
    c = pd.read_parquet(run / "candidates.parquet")
    h = pd.read_parquet(run / "heldout.parquet")
    meta = json.loads((run / "meta.json").read_text())
    t = s.tile_idx.to_numpy()
    seen, rev = set(), np.zeros(len(t), bool)
    for i, x in enumerate(t):
        rev[i] = x in seen
        seen.add(x)
    long_c = c[c.kind == "long"]
    first = s.drop_duplicates("tile_idx")
    lat0, lon0 = meta["start_latlon"]
    # places: stretches of the walk between jumps (> 30 km, i.e. long jumps and teleports)
    jump = s.dist_km.to_numpy() > 30
    place_len = np.diff(np.r_[0, np.flatnonzero(jump), len(s)])
    place_len = place_len[place_len > 0]
    return {
        "character": ch, "seed": seed, "run": run.name, "steps": len(s),
        "unique_tiles": int(s.tile_idx.nunique()),
        "revisit_share": float(rev.mean()),
        "back_step_share": float(np.mean(t[2:] == t[:-2])),
        "bored_teleports": int(s.bored_event.sum()),
        "long_offered": int(long_c.step.nunique()),
        "long_taken": int((s.jump_type == "long").sum()),
        "long_accept_rate": float(long_c.chosen.mean()) if len(long_c) else np.nan,
        "km_walked": float(s.dist_km.sum()),
        "km_walked_local": float(s.dist_km[s.dist_km <= 30].sum()),
        "radius_of_gyration_km": radius_of_gyration_km(s.lat.to_numpy(), s.lon.to_numpy()),
        "max_km_from_start": float(haversine_km(s.lat.to_numpy(), s.lon.to_numpy(), lat0, lon0).max()),
        "steps_before_first_jump": int(place_len[0]),
        "places": len(place_len),
        "median_steps_per_place": float(np.median(place_len)),
        "longest_place_steps": int(place_len.max()),
        "ocean_share_unique": float((first.cover == "ocean").mean()),
        "colour_diversity_unique": colour_diversity(first.tile_idx.to_numpy()),
        "heldout_mse_final": float(h.heldout_mse.iloc[-1]),
        "heldout_mse_last200": float(h[h.step >= h.step.max() - 200].heldout_mse.mean()),
        "max_I_below_0_share": float((s.max_I < 0).mean()),
        "sec_per_step": meta.get("seconds", np.nan) / len(s),
    }


def segments(s: pd.DataFrame):
    la, lo = s.lat.to_numpy(), s.lon.to_numpy()
    near = (s.dist_km.to_numpy()[1:] <= 30) & (np.abs(np.diff(lo)) < 180)
    return la, lo, near


def draw_path(ax, s: pd.DataFrame) -> None:
    la, lo, near = segments(s)
    for k in np.flatnonzero(~near):
        ax.plot(lo[k : k + 2], la[k : k + 2], "--", lw=0.4, color="0.5", alpha=0.6)
    ax.scatter(lo, la, c=s.step, cmap="viridis", s=4, lw=0, zorder=3, vmin=0, vmax=len(s))
    ax.scatter(lo[0], la[0], marker="*", s=120, c="red", edgecolors="k", lw=0.5, zorder=5)
    b = s[s.bored_event]
    ax.scatter(b.lon, b.lat, marker="o", s=22, facecolors="none", edgecolors="crimson", lw=0.7, zorder=4)


def maps(rs, zoom: bool) -> Path:
    chars = [c for c in CHARACTERS if any(r[0] == c for r in rs)]
    fig, axes = plt.subplots(len(chars), len(SEEDS), figsize=(14 if not zoom else 9, 3.6 * len(chars) if not zoom else 4.2 * len(chars)), squeeze=False)
    for i, ch in enumerate(chars):
        for j, seed in enumerate(SEEDS):
            ax = axes[i, j]
            hit = [r for c, sd, r in rs if c == ch and sd == seed]
            if not hit:
                ax.axis("off")
                continue
            s = pd.read_parquet(hit[0] / "steps.parquet")
            title = f"{ch} s{seed}: {s.tile_idx.nunique()} tiles, {int(s.bored_event.sum())} bored, {int((s.jump_type == 'long').sum())} long"
            if zoom:
                lat0, lon0 = s.lat.iloc[0], s.lon.iloc[0]
                ax.set_facecolor("0.97")
                draw_path(ax, s)
                ax.set_xlim(lon0 - 6, lon0 + 6)
                ax.set_ylim(lat0 - 4, lat0 + 4)
                ax.set_aspect(1 / np.cos(np.radians(lat0)))
                ax.tick_params(labelsize=7)
                ax.set_title(title, fontsize=9)
            else:
                world_axes(ax, title)
                draw_path(ax, s)
    fig.suptitle("colour = step (viridis), star = start (Milan), red circles = bored teleports, dashed = jumps > 30 km", fontsize=9)
    fig.tight_layout()
    out = OUT / ("maps_milan.png" if zoom else "maps_world.png")
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out


def curves(rs) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    for ch, seed, r in rs:
        s = pd.read_parquet(r / "steps.parquet")
        h = pd.read_parquet(r / "heldout.parquet")
        seen, n = set(), []
        for x in s.tile_idx:
            seen.add(x)
            n.append(len(seen))
        kw = dict(color=COLOURS[ch], ls="-" if seed == 0 else "--", lw=1.2, label=f"{ch} s{seed}")
        axes[0].plot(s.step, n, **kw)
        axes[1].plot(h.step, h.heldout_mse, **kw)
        axes[2].plot(s.step, s.B_after.rolling(25, min_periods=1).mean(), **kw)
    axes[0].set(title="unique tiles visited", xlabel="step")
    axes[1].set(title="held-out MSE (200 global tiles)", xlabel="step", yscale="log")
    axes[2].set(title="boredom B (25-step mean)", xlabel="step")
    axes[0].legend(fontsize=7, ncol=2)
    fig.tight_layout()
    out = OUT / "curves.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out


def main() -> None:
    rs = runs()
    df = pd.DataFrame([stats(*r) for r in rs])
    df.to_csv(OUT / "summary.csv", index=False)
    cols = ["unique_tiles", "revisit_share", "back_step_share", "bored_teleports", "long_offered", "long_taken", "long_accept_rate",
            "steps_before_first_jump", "places", "median_steps_per_place", "longest_place_steps",
            "ocean_share_unique", "colour_diversity_unique", "heldout_mse_last200"]
    with pd.option_context("display.width", 250, "display.max_columns", 30, "display.float_format", "{:.3f}".format):
        print(df[["character", "seed"] + cols].to_string(index=False))
        print()
        print(df.groupby("character", sort=False)[cols].mean().to_string())
    for p in (maps(rs, False), maps(rs, True), curves(rs)):
        print("wrote", p.relative_to(ROOT))


PARIS = {"Bored": "h2910_bored_paris_s0", "Globalist": "h2910_globalist_paris_s0"}


def paris() -> None:
    """Part 2: the two 5,000-step walks from Paris. Whole-run stats, per-1,000-step blocks, maps and curves."""
    rs = [(ch, 0, ROOT / "runs" / r) for ch, r in PARIS.items() if (ROOT / "runs" / r / "steps.parquet").exists()]
    df = pd.DataFrame([stats(*r) for r in rs])
    df.to_csv(OUT / "paris_summary.csv", index=False)
    blocks = []
    for ch, _, r in rs:
        s = pd.read_parquet(r / "steps.parquet")
        h = pd.read_parquet(r / "heldout.parquet").set_index("step").heldout_mse
        seen = set()
        for b in range(0, len(s), 1000):
            w = s.iloc[b : b + 1000]
            new = len(set(w.tile_idx) - seen)
            seen |= set(w.tile_idx)
            jump = w.dist_km.to_numpy() > 30
            blocks.append({"character": ch, "steps": f"{b}-{b + 999}", "new_tiles": new, "bored": int(w.bored_event.sum()),
                           "long_taken": int((w.jump_type == "long").sum()), "jumps": int(jump.sum()),
                           "ocean_share": round(float((w.cover == "ocean").mean()), 3), "heldout_mse_end": round(float(h[min(b + 1000, h.index.max())]), 4)})
    bl = pd.DataFrame(blocks)
    bl.to_csv(OUT / "paris_blocks.csv", index=False)
    cols = ["unique_tiles", "revisit_share", "back_step_share", "bored_teleports", "long_offered", "long_taken", "long_accept_rate",
            "steps_before_first_jump", "places", "median_steps_per_place", "longest_place_steps",
            "ocean_share_unique", "colour_diversity_unique", "heldout_mse_last200"]
    with pd.option_context("display.width", 250, "display.max_columns", 30, "display.float_format", "{:.3f}".format):
        print(df.set_index("character")[cols].T.to_string())
        print()
        print(bl.to_string(index=False))

    fig, axes = plt.subplots(len(rs), 2, figsize=(18, 4.6 * len(rs)), squeeze=False, gridspec_kw={"width_ratios": [2, 1]})
    for i, (ch, _, r) in enumerate(rs):
        s = pd.read_parquet(r / "steps.parquet")
        title = f"{ch}, Paris, 5,000 steps: {s.tile_idx.nunique():,} tiles, {int(s.bored_event.sum())} bored, {int((s.jump_type == 'long').sum())} long"
        world_axes(axes[i, 0], title)
        draw_path(axes[i, 0], s)
        ax = axes[i, 1]
        lat0, lon0 = s.lat.iloc[0], s.lon.iloc[0]
        ax.set_facecolor("0.97")
        draw_path(ax, s)
        ax.set_xlim(lon0 - 6, lon0 + 6)
        ax.set_ylim(lat0 - 4, lat0 + 4)
        ax.set_aspect(1 / np.cos(np.radians(lat0)))
        ax.tick_params(labelsize=7)
        ax.set_title(f"{ch}: ±6° around Paris", fontsize=9)
    fig.suptitle("colour = step (viridis), star = start (Paris), red circles = bored teleports, dashed = jumps > 30 km", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "paris_maps.png", dpi=110)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    for ch, _, r in rs:
        s = pd.read_parquet(r / "steps.parquet")
        h = pd.read_parquet(r / "heldout.parquet")
        n, seen = [], set()
        for x in s.tile_idx:
            seen.add(x)
            n.append(len(seen))
        kw = dict(color=COLOURS[ch], lw=1.2, label=ch)
        axes[0].plot(s.step, n, **kw)
        axes[1].plot(h.step, h.heldout_mse, **kw)
        axes[2].plot(s.step, (s.dist_km > 30).cumsum(), **kw)
    axes[0].set(title="unique tiles visited", xlabel="step")
    axes[1].set(title="held-out MSE (200 global tiles)", xlabel="step", yscale="log")
    axes[2].set(title="jumps > 30 km (teleports + long jumps), cumulative", xlabel="step")
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "paris_curves.png", dpi=120)
    plt.close(fig)
    print("wrote notes/hikes_2910/paris_{summary,blocks}.csv, paris_maps.png, paris_curves.png")


if __name__ == "__main__":
    paris() if "--paris" in sys.argv else main()
