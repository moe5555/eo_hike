"""Task 1: is "interesting" just "hard to draw"? Long stays (top 10 % of a walk's places by length) against short places
(median length or less), over all h2910 runs. Offline.

    python analysis/h0111/task1_hard_to_draw.py

Writes tile_stats.csv, task1_groups.csv, task1_runs.csv, task1_stay_profile.csv, task1_places.csv, task1_signal.csv,
task1_stay_profile.png, contact_long_vs_short.png. Error is taken from the walk's own log. "Relative error" divides it by the
held-out error at that step, because long stays come later in a walk, when everything is easier to draw.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from common import H2910, OUT, WARMUP, candidates, heldout, heldout_at, places, steps
from scipy.stats import spearmanr

from data.tile_store import TileStore


def tile_stats(ids: np.ndarray) -> pd.DataFrame:
    """Per tile: mean gradient magnitude and grey-level entropy (256 grey levels), on the 256 px tile the walker's crops come from."""
    store, rows = TileStore(), []
    for i in map(int, ids):
        a = store.get_lowres(i).astype(np.float32)
        g = a.mean(2)
        gy, gx = np.gradient(g)
        hist = np.bincount(g.astype(np.uint8).ravel(), minlength=256) / g.size
        hist = hist[hist > 0]
        hsv_max, hsv_min = a.max(2), a.min(2)
        rows.append({"tile_idx": i, "grad": float(np.hypot(gx, gy).mean()), "entropy": float(-(hist * np.log2(hist)).sum()), "grey_mean": float(g.mean()), "grey_std": float(g.std()),
                     "r": float(a[..., 0].mean()), "g": float(a[..., 1].mean()), "b": float(a[..., 2].mean()), "sat": float(((hsv_max - hsv_min) / np.maximum(hsv_max, 1)).mean())})
    return pd.DataFrame(rows)


def rough_label(t: pd.DataFrame, cover: pd.Series) -> pd.Series:
    """Rough labels from tile statistics and the index's cover field. No new data."""
    bright = t.grey_mean > 130
    lab = np.select([cover == "ocean", bright & (t.sat < 0.15), t.g > t.r * 1.02, (t.r > t.b * 1.25) & (t.grey_mean > 70)], ["open water", "snow/ice/cloud", "green", "dry/bare"], "other land")
    return pd.Series(lab, index=t.index)


def colour_div(rgb: np.ndarray) -> float:
    if len(rgb) < 2:
        return np.nan
    d = np.sqrt(((rgb[:, None] - rgb[None]) ** 2).sum(-1))
    return float(d[np.triu_indices(len(rgb), 1)].mean())


def main() -> None:
    all_s = []
    for run, (ch, start) in H2910.items():
        s = places(steps(run))
        h = heldout(run)
        s = s.assign(run=run, character=ch, start=start, held=heldout_at(h, s.step.to_numpy()))
        s["e_rel"] = s.e / s.held
        q90, q50 = s.groupby("place").place_len.first().quantile([0.9, 0.5])
        s["group"] = np.select([s.place_len >= q90, s.place_len <= q50], ["long", "short"], "middle")
        all_s.append(s)
    S = pd.concat(all_s, ignore_index=True)
    ids = np.sort(S.tile_idx.unique())
    cache = OUT / "tile_stats.csv"
    t = pd.read_csv(cache) if cache.exists() else tile_stats(ids)
    t.to_csv(cache, index=False)
    t = t.set_index("tile_idx")
    cover = S.drop_duplicates("tile_idx").set_index("tile_idx").cover.reindex(t.index)
    t["label"] = rough_label(t, cover)
    S = S.join(t, on="tile_idx", rsuffix="_t")
    W = S[S.step >= WARMUP]  # the first 50 steps are the network's infancy

    # -- long against short, walk by walk ---------------------------------------------------------------------------------
    metrics = ["e", "e_rel", "n", "g", "grad", "entropy", "grey_std"]
    rows = []
    for (run, grp), d in W[W.group != "middle"].groupby(["run", "group"]):
        u = d.drop_duplicates("tile_idx")
        by_place = [colour_div(x[["r", "g", "b"]].to_numpy()) for _, x in u.groupby("place") if len(x) >= 5]
        rows.append({"run": run, "character": d.character.iloc[0], "start": d.start.iloc[0], "group": grp, "places": d.place.nunique(), "steps": len(d), "tiles": len(u),
                     **{m: d[m].median() for m in metrics}, "ocean": (u.cover == "ocean").mean(), "colour_div_pooled": colour_div(u[["r", "g", "b"]].to_numpy()),
                     "colour_div_within_place": np.nanmean(by_place) if by_place else np.nan, **{f"lab_{k}": (u.label == k).mean() for k in t.label.unique()}})
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "task1_runs.csv", index=False)
    cols = metrics + ["ocean", "colour_div_pooled", "colour_div_within_place"] + [f"lab_{k}" for k in t.label.unique()]
    G = []
    for grp, d in R.groupby("group"):
        G.append({"group": grp, "walks": len(d), "places": d.places.sum(), "steps": d.steps.sum(), **{c: f"{d[c].median():.4g} ({d[c].min():.3g}–{d[c].max():.3g})" for c in cols}})
    G = pd.DataFrame(G).set_index("group").T
    G.to_csv(OUT / "task1_groups.csv")
    print(G.to_string())
    P = R.pivot(index="run", columns="group", values=metrics + ["ocean", "colour_div_within_place", "colour_div_pooled"])
    wins = {m: f"{int((P[m].long > P[m].short).sum())}/{P[m].dropna().shape[0]}, ratio {(P[m].long / P[m].short).median():.2f} ({(P[m].long / P[m].short).min():.2f}–{(P[m].long / P[m].short).max():.2f})" for m in metrics + ["colour_div_within_place", "colour_div_pooled"]}
    print("\nlong > short, walks; ratio long/short, median (range)"); [print(f"  {k}: {v}") for k, v in wins.items()]
    pd.Series(wins).to_csv(OUT / "task1_long_vs_short.csv", header=["long>short walks, ratio"])

    # -- arrival: what predicts how long a place lasts? ---------------------------------------------------------------------
    arr = W[W.place_pos == 0].copy()
    first10 = W[W.step >= WARMUP].groupby(["run", "place"]).head(10).groupby(["run", "place"]).agg(e_rel10=("e_rel", "median"), grad10=("grad", "median"), ent10=("entropy", "median"), std10=("grey_std", "median"))
    arr = arr.join(first10, on=["run", "place"])
    pl = arr[["run", "character", "start", "place", "step", "place_len", "lat", "lon", "cover", "label", "jump_type", "e_rel", "e_rel10", "grad", "entropy", "grey_std", "grad10", "ent10", "std10"]]
    pl.to_csv(OUT / "task1_places.csv", index=False)
    print(f"\nplaces arriving after step {WARMUP}: {len(pl)}; Spearman with place length:")
    corr = {}
    for m in ["e_rel", "e_rel10", "grad", "entropy", "grey_std", "grad10", "ent10", "std10"]:
        r, p = spearmanr(pl[m], pl.place_len, nan_policy="omit")
        per = pl.groupby("run").apply(lambda d: spearmanr(d[m], d.place_len, nan_policy="omit")[0] if len(d) >= 6 else np.nan, include_groups=False).dropna()
        corr[m] = {"rho_pooled": r, "p": p, "rho_walk_median": per.median(), "walk_min": per.min(), "walk_max": per.max()}
    corr = pd.DataFrame(corr).T
    corr.to_csv(OUT / "task1_place_length_corr.csv")
    print(corr.round(3).to_string())
    print("\nplace length by arrival label:\n", pl.groupby("label").place_len.describe()[["count", "50%", "75%", "max"]].round(1).to_string())
    print("\nplace length by grad quartile on arrival (first 10 steps):")
    print(pl.assign(q=pd.qcut(pl.grad10, 4, labels=False)).groupby("q").agg(places=("place_len", "size"), median_len=("place_len", "median"), mean_len=("place_len", "mean"), top10pct=("place_len", lambda v: (v >= pl.place_len.quantile(0.9)).mean()), grad=("grad10", "median")).round(2).to_string())

    # -- candidate level: is the interest score just the error? ------------------------------------------------------------
    rows = []
    for run, (ch, start) in H2910.items():
        c = candidates(run)
        c = c[c.step >= WARMUP]
        c = c[c.groupby("step").step.transform("size") > 1]
        rk = lambda col: c.groupby("step")[col].rank(pct=True)  # noqa: E731
        c = c.assign(re=rk("e"), rI=rk("I"), rn=rk("n"), rg=rk("g"))
        top_e = c.groupby("step").e.transform("max") == c.e
        rows.append({"run": run, "character": ch, "start": start, "rho_I_e": spearmanr(c.rI, c.re)[0], "rho_n_e": spearmanr(c.rn, c.re)[0], "rho_g_e": spearmanr(c.rg, c.re)[0],
                     "chosen_is_hardest": float(c[c.chosen].pipe(lambda d: top_e[d.index]).mean()), "chance": float((1 / c.groupby("step").size()).mean()),
                     "chosen_e_rank": float(c[c.chosen].re.mean())})
    SIG = pd.DataFrame(rows)
    SIG.to_csv(OUT / "task1_signal.csv", index=False)
    print("\nwithin a step, across candidates (steps >= 50):\n", SIG.drop(columns="start").round(3).to_string())

    # -- during long stays ---------------------------------------------------------------------------------------------------
    L = W[(W.group == "long") & (W.place_len >= 60)].copy()
    L["decile"] = np.minimum((L.place_pos * 10).astype(int), 9)
    prof = L.groupby(["run", "place", "decile"]).agg(e=("e", "median"), e_rel=("e_rel", "median"), held=("held", "median"), max_I=("max_I", "median"), I=("I", "median"), n=("n", "median"), g=("g", "median")).reset_index()
    prof = prof.join(L.groupby(["run", "place"]).agg(len_=("place_len", "first"), character=("character", "first"), lat=("lat", "median"), lon=("lon", "median"), start_step=("step", "min")), on=["run", "place"])
    prof.to_csv(OUT / "task1_stay_profile.csv", index=False)
    wide = prof.pivot_table(index=["run", "place", "len_", "lat", "lon"], columns="decile", values="e")
    wrel = prof.pivot_table(index=["run", "place", "len_", "lat", "lon"], columns="decile", values="e_rel")
    summ = pd.DataFrame({"first_tenth_e": wide[0], "last_tenth_e": wide[9], "ratio": wide[9] / wide[0], "min_ratio": wide.min(axis=1) / wide[0], "rel_first": wrel[0], "rel_last": wrel[9],
                         "share_tenths_above_held": (wrel > 1).mean(axis=1), "half_time_tenth": ((wide.div(wide[0], axis=0) <= 0.75).values.argmax(axis=1))}).reset_index()
    summ.to_csv(OUT / "task1_stays.csv", index=False)
    print(f"\nlong stays of >= 60 steps: {len(summ)}\n", summ.sort_values("len_", ascending=False).head(16).round(3).to_string(index=False))
    print("\nmedian profile by tenth of the stay:\n", prof.groupby("decile")[["e", "e_rel", "held", "max_I", "I", "n", "g"]].median().round(4).to_string())
    print(f"\nlast/first e: median {summ.ratio.median():.2f} ({summ.ratio.min():.2f}–{summ.ratio.max():.2f}); falls below 0.75 of arrival in {(summ.min_ratio <= 0.75).mean():.2f} of stays; share of tenths above held-out, median {summ.share_tenths_above_held.median():.2f}")
    print(f"correlation of stay length with last/first e ratio: {spearmanr(summ.len_, summ.ratio)[0]:.2f}")

    figures(S, prof, summ)


def figures(S: pd.DataFrame, prof: pd.DataFrame, summ: pd.DataFrame) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from data.tile_store import TileStore

    fig, axs = plt.subplots(1, 3, figsize=(15, 4.4))
    for (run, place), d in prof.groupby(["run", "place"]):
        d = d.sort_values("decile")
        lw = 0.6 + d.len_.iloc[0] / 400
        axs[0].plot(d.decile, d.e / d.e.iloc[0], color="#2a78b5", alpha=0.45, lw=lw)
        axs[1].plot(d.decile, d.e_rel, color="#2a78b5", alpha=0.45, lw=lw)
        axs[2].plot(d.decile, d.I, color="#2a78b5", alpha=0.45, lw=lw)
    m = prof.assign(e0=prof.groupby(["run", "place"]).e.transform("first")).assign(r=lambda x: x.e / x.e0).groupby("decile")[["r", "e_rel", "I"]].median()
    for ax, col in zip(axs, m.columns):
        ax.plot(m.index, m[col], color="k", lw=2.2, label="median")
        ax.set_xlabel("tenth of the stay")
        ax.grid(alpha=0.25)
        ax.legend(frameon=False)
    axs[0].set_title("error of the chosen tile, against its value at arrival")
    axs[1].set_title("error of the chosen tile, against the held-out error then")
    axs[1].axhline(1, color="0.5", lw=0.8)
    axs[2].set_title("interest of the chosen tile")
    fig.suptitle(f"{len(summ)} long stays of 60 steps or more; thicker line = longer stay", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "task1_stay_profile.png", dpi=120)
    plt.close(fig)

    store = TileStore()
    rng = np.random.default_rng(0)
    W = S[S.step >= WARMUP].drop_duplicates(["run", "tile_idx"])
    n_col, n_row = 16, 6
    fig, axs = plt.subplots(2 * n_row + 1, n_col, figsize=(n_col, 2 * n_row + 1), gridspec_kw={"height_ratios": [1] * n_row + [0.15] + [1] * n_row})
    for ax in axs.ravel():
        ax.axis("off")
    for k, grp in enumerate(["long", "short"]):
        d = W[W.group == grp]
        pick = d.iloc[rng.choice(len(d), n_col * n_row, replace=False)].sort_values("grad")
        off = 0 if k == 0 else n_row + 1
        for j, (_, x) in enumerate(pick.iterrows()):
            axs[off + j // n_col, j % n_col].imshow(store.get_lowres(int(x.tile_idx)))
        axs[off, 0].set_title(f"{'Long stays' if k == 0 else 'Short places'}: {n_col * n_row} random tiles, sorted by mean gradient", fontsize=9, loc="left", x=0)
    fig.subplots_adjust(0, 0, 1, 0.97, 0.02, 0.05)
    fig.savefig(OUT / "contact_long_vs_short.png", dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    main()
