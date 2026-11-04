"""Why the fixed-perception walkers still return to tiles (notes/06_characters/reflection_revisits.md).

    python analysis/h2910_revisits.py

Over the ten walks of Hikes 29.10 without a collapsed network: revisit rates against a blind replay of each stay, the
interest gap between seen and new options, what one more visit does to a tile's signals, how a tile's first-look score
predicts its visits, and, for the two Paris walks, the contrast of the favourite tiles against neighbours never visited.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.tile_store import EARTH_R_KM, TileStore, haversine_km  # noqa: E402

RUNS = ["global_perception_1k_s0", "global_perception_1k_s1", "h2910_bored_s0", "h2910_bored_s1", "h2910_globalist_s0", "h2910_globalist_s1",
        "h2910_localist_s0", "h2910_localist_s1", "h2910_bored_paris_s0", "h2910_globalist_paris_s0"]
PARIS = RUNS[-2:]
JUMP_KM = 30.0  # a stay ends at a step longer than this, the same rule as "places" in analysis/h2910_compare.py
WARMUP = 50  # steps left out of the score comparisons: the running z-scores use a plain average until then
VISIT_BINS = [-1, 0, 1, 3, 10, 10**6]
VISIT_LABELS = ["0", "1", "2-3", "4-10", ">10"]
TOTAL_BINS = [-1, 0, 1, 2, 4, 6, 10**6]
TOTAL_LABELS = ["never", "1", "2", "3-4", "5-6", ">6"]


def load(run: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """-> steps and candidates, with each candidate's prior visits, counted as walk.py counts them (arrivals before this step)."""
    s = pd.read_parquet(ROOT / "runs" / run / "steps.parquet")
    c = pd.read_parquet(ROOT / "runs" / run / "candidates.parquet")
    t = s.tile_idx.to_numpy()
    counts: dict[int, int] = {}
    prior = np.zeros(len(c), int)
    done = 0
    for k, (st, i) in enumerate(zip(c.step.to_numpy(), c.tile_idx.to_numpy())):
        while done < st:
            counts[t[done]] = counts.get(t[done], 0) + 1
            done += 1
        prior[k] = counts.get(i, 0)
    c["prior"], c["seen"], c["run"] = prior, prior > 0, run
    c["C"] = c.groupby("step").step.transform("size")
    return s, c


def path_stats(seq) -> dict:
    a = np.asarray(seq)
    vc = pd.Series(a).value_counts()
    return {"revisit": 1 - vc.size / len(a), "back": (a[2:] == a[:-2]).mean(), "unique": vc.size, "top1": vc.iloc[0]}


class Grid:
    """The neighbours of data/tile_store.World on the whole global index, without loading any tile."""

    def __init__(self, radius_km: float = 15.0) -> None:
        from sklearn.neighbors import BallTree

        idx = pd.read_parquet(ROOT / "data" / "global" / "index.parquet", columns=["lat", "lon"])
        self.lat, self.lon = idx.lat.to_numpy(), idx.lon.to_numpy()
        self.tree = BallTree(np.radians(np.stack([self.lat, self.lon], 1)), metric="haversine")
        self.r, self.cache = radius_km / EARTH_R_KM, {}

    def neighbours(self, i: int) -> np.ndarray:
        if i not in self.cache:
            a = self.tree.query_radius(np.radians([[self.lat[i], self.lon[i]]]), r=self.r)[0]
            self.cache[i] = a[a != i]
        return self.cache[i]


def blind_replay(t: np.ndarray, starts: np.ndarray, ends: np.ndarray, grid: Grid, rng: np.random.Generator) -> list[int]:
    """Every stay again from its real landing tile, for its real length, choosing uniformly among the neighbours."""
    seq = []
    for a, b in zip(starts, ends):
        c = int(t[a])
        seq.append(c)
        for _ in range(b - a - 1):
            n = grid.neighbours(c)
            c = int(n[rng.integers(len(n))]) if len(n) else c
            seq.append(c)
    return seq


def against_blind(walks: dict[str, tuple[pd.DataFrame, pd.DataFrame]]) -> None:
    grid = Grid()
    rows = []
    for run, (s, _) in walks.items():
        t = s.tile_idx.to_numpy()
        new = np.r_[True, s.dist_km.to_numpy()[1:] > JUMP_KM]
        starts = np.flatnonzero(new)
        ends = np.r_[starts[1:], len(t)]
        place = np.cumsum(new)
        last: dict[int, int] = {}
        returns = crossing = 0
        for x, p in zip(t, place):
            if x in last:
                returns += 1
                crossing += last[x] != p
            last[x] = p
        # did a later stay land within reach of the tiles of an earlier one, even on a different tile?
        lat, lon = s.lat.to_numpy(), s.lon.to_numpy()
        near = sum(bool((haversine_km(lat[a], lon[a], lat[:a], lon[:a]) <= JUMP_KM).any()) for a in starts[1:])
        vc = s.tile_idx.value_counts()
        sim = pd.DataFrame([path_stats(blind_replay(t, starts, ends, grid, np.random.default_rng(5000 + k))) for k in range(20 if len(t) == 1000 else 6)])
        w = path_stats(t)
        rows.append({"run": run, "revisit": w["revisit"], "blind": sim.revisit.mean(), "blind_sd": sim.revisit.std(), "back": w["back"], "blind_back": sim.back.mean(),
                     "unique": w["unique"], "blind_unique": sim.unique.mean(), "top1": w["top1"], "blind_top1": sim.top1.mean(), "stays": len(starts),
                     "returns": returns, "crossing_jump": crossing, "landed_near_earlier_stay": near, "tiles_over_10": int((vc > 10).sum())})
    o = pd.DataFrame(rows)
    print("-- each walk against a blind replay of its stays --\n" + o.round(3).to_string())
    print("mean over walks:\n" + o.drop(columns="run").mean().round(3).to_string())
    print(f"totals: {o.returns.sum()} returns, {o.crossing_jump.sum()} crossing a jump, {o.landed_near_earlier_stay.sum()} of {(o.stays - 1).sum()} jumps landing within {JUMP_KM:.0f} km of an earlier stay")
    print(f"walks revisiting less than their blind replay: {(o.revisit < o.blind).sum()}; ratio unique/blind unique, mean {(o.unique / o.blind_unique).mean():.2f}")


def options(c: pd.DataFrame) -> None:
    g = c[c.C > 1]
    per = g.groupby(["run", "step"])
    a = pd.DataFrame({"seen_share": per.seen.mean(), "any_new": per.seen.min() == 0, "p_seen": g[g.seen].groupby(["run", "step"]).p.sum(),
                      "chose_seen": g[g.chosen].set_index(["run", "step"]).seen}).fillna({"p_seen": 0.0})
    r = a.groupby("run").mean().astype(float)
    print("\n-- the options on offer, all steps with a choice (per walk) --\n" + r.round(3).to_string())
    print("mean over walks:\n" + r.mean().round(3).to_string())

    rows = []
    for (run, st), d in g[g.step >= WARMUP].groupby(["run", "step"], sort=False):
        new, seen = d[~d.seen], d[d.seen]
        if len(new) and len(seen):
            ch = d[d.chosen].iloc[0]
            rows.append({"run": run, "chose_seen": bool(ch.seen), "best_vs_best": seen.I.max() - new.I.max(), "mean_vs_mean": seen.I.mean() - new.I.mean(), "spread": d.I.std(),
                         "chosen_vs_best_new": ch.I - new.I.max(), "chose_top": ch.I == d.I.max()})
    v = pd.DataFrame(rows)
    ret = v[v.chose_seen]
    print(f"\n-- interest, steps >= {WARMUP} with both seen and new tiles on offer (N={len(v)}) --")
    print(f"chose a seen tile {v.chose_seen.mean():.3f}; within-step spread of I {v.spread.mean():.2f}")
    print(f"best seen - best new: median {v.best_vs_best.median():+.2f} (quartiles {v.best_vs_best.quantile(.25):+.2f}, {v.best_vs_best.quantile(.75):+.2f}), odds at T=0.5 {np.exp(2 * v.best_vs_best.median()):.2f}; best seen wins {(v.best_vs_best > 0).mean():.3f}")
    print(f"mean seen - mean new: median {v.mean_vs_mean.median():+.2f}, mean {v.mean_vs_mean.mean():+.2f}")
    print(f"returns (N={len(ret)}): not the top candidate {(~ret.chose_top).mean():.3f}; scored below a new tile {(ret.chosen_vs_best_new < 0).mean():.3f}")


def per_visit(c: pd.DataFrame) -> None:
    n = c[(c.C > 1) & (c.step >= WARMUP) & (c.kind == "neighbour")].sort_values(["run", "tile_idx", "step"]).copy()
    print("\n-- neighbours by exact prior visits (a cross-section: favourites are selected into the higher rows) --")
    print(n.groupby("prior").agg(N=("n", "size"), n=("n", "mean"), n_z=("n_z", "mean"), g_z=("g_z", "mean"), I=("I", "mean"), chosen=("chosen", "mean")).round(3).to_string())
    gb = n.groupby(["run", "tile_idx"])
    x = n.assign(d_n=gb.n.diff(), d_nz=gb.n_z.diff(), d_gz=gb.g_z.diff(), d_I=gb.I.diff(), d_prior=gb.prior.diff(), gap=gb.step.diff(), before=gb.prior.shift()).dropna(subset=["d_n"])
    x = x[x.gap <= 10]
    x = x.assign(visited_between=x.d_prior > 0)
    print("\n-- the same tile, two looks at most 10 steps apart, by whether it was visited in between --")
    print(x.groupby("visited_between").agg(N=("d_n", "size"), d_n=("d_n", "mean"), d_nz=("d_nz", "mean"), d_gz=("d_gz", "mean"), d_I=("d_I", "mean")).round(3).to_string())
    y = x[x.d_prior == 1]
    y = y.assign(before=pd.cut(y.before, VISIT_BINS, labels=VISIT_LABELS))
    print("\n-- one more visit, by visits before it --")
    print(y.groupby("before", observed=True).agg(N=("d_n", "size"), d_n=("d_n", "mean"), d_nz=("d_nz", "mean"), d_gz=("d_gz", "mean"), d_I=("d_I", "mean"), I_after=("I", "mean")).round(3).to_string())


def first_look(walks: dict[str, tuple[pd.DataFrame, pd.DataFrame]]) -> None:
    rows = []
    for run, (s, c) in walks.items():
        c = c[(c.C > 1) & (c.kind == "neighbour")].copy()
        c["I_rel"] = c.I - c.groupby("step").I.transform("mean")
        f = c[c.prior == 0].sort_values("step").drop_duplicates("tile_idx")
        rows.append(f[f.step >= WARMUP].assign(total=lambda d: d.tile_idx.map(s.tile_idx.value_counts()).fillna(0).astype(int)))
    f = pd.concat(rows)
    f["total"] = pd.cut(f.total, TOTAL_BINS, labels=TOTAL_LABELS)
    print(f"\n-- a tile's first look (no visit yet, step >= {WARMUP}), by its visits over the whole walk --")
    print(f.groupby("total", observed=True).agg(N=("I", "size"), I_vs_options=("I_rel", "mean"), n_z=("n_z", "mean"), g_z=("g_z", "mean"), n=("n", "mean"), p=("p", "mean")).round(3).to_string())

    tiers = pd.concat([s.tile_idx.value_counts() for s, _ in walks.values()])
    t = pd.DataFrame({"tiles": tiers.groupby(pd.cut(tiers, [0, 1, 2, 4, 6, 10**6], labels=TOTAL_LABELS[1:]), observed=True).size(),
                      "returns": (tiers - 1).groupby(pd.cut(tiers, [0, 1, 2, 4, 6, 10**6], labels=TOTAL_LABELS[1:]), observed=True).sum()})
    t["tile_share"], t["return_share"] = t.tiles / t.tiles.sum(), t.returns / t.returns.sum()
    print("\n-- tiles and returns by visits over the whole walk --\n" + t.round(3).to_string())


def stays(walks: dict[str, tuple[pd.DataFrame, pd.DataFrame]]) -> None:
    s = walks["h2910_globalist_paris_s0"][0]
    print("\n-- three stays of the Paris Globalist (notes: narration/out/tests/test_research.md) --")
    for name, a, b in [("Kivalliq", 1, 24), ("Bay of Bengal", 93, 129), ("Zhegu", 130, 310)]:
        w = s[(s.step >= a) & (s.step <= b)]
        print(name, {k: round(float(v), 2) for k, v in path_stats(w.tile_idx).items()}, "steps", len(w))


def favourites(walks: dict[str, tuple[pd.DataFrame, pd.DataFrame]], min_visits: int = 6, rows_per_run: int = 6) -> None:
    """Favourite tiles against up to 8 never-visited tiles offered alongside them; a strip of the top ones for the note."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    store = TileStore()
    grey = lambda i: store.get_lowres(int(i)).astype(float).mean(2)  # noqa: E731
    rows, strip = [], []
    for run in PARIS:
        s, c = walks[run]
        c = c[(c.C > 1) & (c.step >= WARMUP) & (c.kind == "neighbour")]
        vc = s.tile_idx.value_counts()
        u = s.drop_duplicates("tile_idx").set_index("tile_idx")
        for t in vc.index[vc >= min_visits]:
            others = c[c.step.isin(c[c.tile_idx == t].step.unique()) & ~c.tile_idx.isin(vc.index)].tile_idx.unique()[:8]
            if len(others):
                rows.append({"run": run, "tile": int(t), "visits": int(vc[t]), "cover": u.cover[t], "lat": u.lat[t], "lon": u.lon[t], "others": others.tolist(),
                             "contrast": grey(t).std(), "others_contrast": np.mean([grey(o).std() for o in others])})
    f = pd.DataFrame(rows)
    f["higher"] = f.contrast > f.others_contrast
    print(f"\n-- tiles with >= {min_visits} visits (N={len(f)}) against never-visited tiles offered alongside them, std of grey level on 0-255 --")
    print(f.groupby("run")[["contrast", "others_contrast", "higher"]].mean().round(3).to_string())
    print(f"median contrast {f.contrast.median():.1f} vs {f.others_contrast.median():.1f}; median ratio {(f.contrast / f.others_contrast.clip(lower=0.5)).median():.2f}")

    strip = f.sort_values("visits", ascending=False).groupby("run").head(rows_per_run)
    fig, axs = plt.subplots(len(strip), 4, figsize=(8, 2.1 * len(strip)))
    for row, (_, x) in zip(axs, strip.iterrows()):
        row[0].imshow(store.get_lowres(x.tile))
        row[0].set_title(f"{x.visits} visits, {x.lat:.1f}, {x.lon:.1f}\n{x.run}", fontsize=7)
        for ax, o in zip(row[1:], x.others):
            ax.imshow(store.get_lowres(int(o)))
            ax.set_title("offered, never visited", fontsize=7)
        for ax in row:
            ax.set_xticks([])
            ax.set_yticks([])
    out = ROOT / "notes" / "06_characters" / "revisit_favourites.png"
    fig.tight_layout()
    fig.savefig(out, dpi=90)
    plt.close(fig)
    print(f"[h2910_revisits] {out}")


if __name__ == "__main__":
    walks = {r: load(r) for r in RUNS}
    assert all(yaml.safe_load((ROOT / "runs" / r / "config.yaml").read_text())["score_crops"] == "fixed" for r in RUNS)
    cands = pd.concat(c for _, c in walks.values())
    against_blind(walks)
    options(cands)
    per_visit(cands)
    first_look(walks)
    stays(walks)
    favourites(walks)
