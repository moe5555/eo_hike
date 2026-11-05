"""Stage 0.2: the taste panel. A fixed set of 300 tiles that every walker's own network scores at each checkpoint, free of path and landing luck.

    python analysis/e08/panel.py select      # once: writes analysis/e08/panel.csv, refuses to overwrite it
    python analysis/e08/panel.py score       # surprise, novelty, progress of every panel tile, per run and checkpoint -> data/sheet/panel_scores.parquet
    python analysis/e08/panel.py summarise   # -> notes/08_character_sheet/results/panel_*.csv, panel_*.png

Selection: a random pool from the global index (600 tiles per cover: land, coast, ocean; seed 311), leaving out every tile any h0111 walk stood
on. Within each cover, tiles are binned by quartile of texture (mean gradient) and of brightness (mean grey), 16 cells; 6 tiles are drawn from
each cell, and the cover is filled up to 100 from its remaining pool where a cell has fewer.

Scoring, as the walker scores a candidate (walk.py): the checkpoint's network, the tile's fixed scoring crops (score_crops: fixed), surprise =
reconstruction error, progress = the vmapped probe with the run's lr and probe_steps, novelty = mean distance to the k_nn nearest archive latents
(normalised if normalise_latents). The archive is rebuilt from steps.parquet: one entry per arrival up to the checkpoint, revisits included as in
the walk, every entry embedded with the checkpoint's network (the walk re-embeds every 100 steps, so this is its state at the next re-embed).
Interest on the panel: I = w_n z(n) + w_g z(g) + w_e z(e), z-scored over the panel, with the run's own weights. The Null walker keeps the
Reference's weights: its panel taste is what its network would value, though it never acts on it.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import torch
from sheet import CACHE, CKPTS, GROUPS, OUT, STAGE0, STAGE0_SEEDS, PANEL, ROOT, RUNS, S, _stats_of, config, net, runs, scoring_crops, steps  # sets sys.path

from readouts import calibration, paired  # noqa: E402

POOL_PER_COVER, PER_CELL, PER_COVER, SEED = 600, 6, 100, 311
SIGNALS = ("n", "e", "g", "I")
PROPS = {"texture": "grad", "brightness": "grey_mean", "saturation": "sat"}
SCORES = CACHE / "panel_scores.parquet"


def select() -> None:
    from data.tile_store import TileStore

    if PANEL.exists():
        sys.exit(f"{PANEL} exists and is never changed; delete it by hand to choose again")
    store = TileStore()
    cover = store.idx.cover.to_numpy()
    walked = set()
    for p in RUNS.glob("h0111_*_s*"):  # every h0111 walk
        if (p / "steps.parquet").exists():
            walked |= set(pd.read_parquet(p / "steps.parquet", columns=["tile_idx"]).tile_idx)
    rng = np.random.default_rng(SEED)
    pool = []
    for cv in ("land", "coast", "ocean"):
        ids = np.setdiff1d(np.flatnonzero(cover == cv), np.fromiter(walked, np.int64))
        pool += [(int(i), cv) for i in rng.choice(ids, POOL_PER_COVER, replace=False)]
    print(f"[panel] fetching a pool of {len(pool)} tiles ({len(walked)} walked tiles left out)", flush=True)
    arrs, dropped, _ = store.get_many([i for i, _ in pool], timeout=1800.0)
    print(f"[panel] {len(arrs)} fetched, {len(dropped)} dropped", flush=True)
    P = pd.DataFrame([{**_stats_of(store, i), "cover": cv} for i, cv in pool if i in arrs])
    out = []
    for cv, d in P.groupby("cover"):
        d = d.assign(texture_q=pd.qcut(d.grad, 4, labels=False), brightness_q=pd.qcut(d.grey_mean, 4, labels=False))
        take = d.groupby(["texture_q", "brightness_q"], group_keys=False).apply(lambda x: x.sample(min(PER_CELL, len(x)), random_state=SEED))
        take = d.loc[take.index]  # apply drops the grouping columns; take the rows back from d with all columns
        rest = d.drop(take.index)
        take = pd.concat([take, rest.sample(PER_COVER - len(take), random_state=SEED)])
        out.append(take)
    panel = pd.concat(out).sort_values(["cover", "texture_q", "brightness_q", "tile_idx"])
    panel[["tile_idx", "cover", "texture_q", "brightness_q", "grad", "grey_mean", "grey_std", "entropy", "sat", "r", "g", "b"]].to_csv(PANEL, index=False)
    print(f"[panel] wrote {PANEL}: {len(panel)} tiles\n" + panel.groupby(["cover", "texture_q"]).size().unstack().to_string())


def archive_latents(model, store, tiles: np.ndarray, K: int, crop: int, unit: bool) -> torch.Tensor:
    """One latent per arrival (revisits repeat their tile's latent, as the walk's archive does)."""
    u, inv = np.unique(tiles, return_inverse=True)
    zs = [S.mean_latent(model, scoring_crops(store, u[i : i + 256], K, crop)) for i in range(0, len(u), 256)]
    return torch.cat(zs)[torch.from_numpy(inv)]


def score() -> None:
    from data.tile_store import TileStore

    torch.set_grad_enabled(True)
    store = TileStore()
    panel = pd.read_csv(PANEL)
    ids = panel.tile_idx.to_list()
    have = pd.read_parquet(SCORES) if SCORES.exists() else pd.DataFrame(columns=["run", "ckpt"])
    done = set(zip(have.run, have.ckpt))
    xs: dict[int, torch.Tensor] = {}
    rows = []
    for group, seed, run in runs():
        cfg = config(run)
        K, crop = int(cfg["K"]), int(cfg["crop_px"])
        if crop not in xs:
            xs[crop] = scoring_crops(store, ids, K, crop)
        x = xs[crop]
        t = steps(run).tile_idx.to_numpy()
        for ck in CKPTS:
            if (run, ck) in done or not (RUNS / run / f"ckpt_{ck:04d}.pt").exists():
                continue
            model = net(run, ck)
            unit = bool(cfg.get("normalise_latents", False))
            with torch.no_grad():
                arch = archive_latents(model, store, t[:ck], K, crop, unit)
                e = S.recon_err(model, x)
                n = S.novelty(S.mean_latent(model, x), arch, int(cfg["k_nn"]), unit=unit)
            g = torch.cat([S.progress_probe(model, x[i : i + 50], float(cfg["lr"]), int(cfg["probe_steps"]))[0] for i in range(0, len(x), 50)])
            rows.append(pd.DataFrame({"run": run, "group": group, "seed": seed, "ckpt": ck, "tile_idx": ids, "e": e.numpy(), "n": n.numpy(), "g": g.numpy(),
                                      "w_n": float(cfg["w_n"]), "w_g": float(cfg["w_g"]), "w_e": float(cfg["w_e"])}))
            print(f"[panel] {run} ckpt {ck}", flush=True)
        if rows:  # save after every run, so an interrupted scoring resumes
            have = pd.concat([have, *rows], ignore_index=True) if len(have) else pd.concat(rows, ignore_index=True)
            have.to_parquet(SCORES, index=False)
            rows = []


def with_interest(sc: pd.DataFrame) -> pd.DataFrame:
    z = lambda v: (v - v.mean()) / v.std()  # noqa: E731
    key = ["run", "ckpt"]
    sc = sc.assign(**{f"z_{k}": sc.groupby(key)[k].transform(z) for k in ("n", "e", "g")})
    return sc.assign(z_I=sc.w_n * sc.z_n + sc.w_g * sc.z_g + sc.w_e * sc.z_e)


def summarise() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy.stats import spearmanr

    panel = pd.read_csv(PANEL).set_index("tile_idx")[["cover", "texture_q", "brightness_q", *PROPS.values()]]
    label = {r: g for g, _, r in runs()}  # labels as sheet.py names them now
    sc = pd.read_parquet(SCORES).pipe(lambda d: d[d.run.isin(label)]).pipe(lambda d: d.assign(group=d.run.map(label)))
    sc = with_interest(sc).join(panel, on="tile_idx")

    # -- per stratum: which kinds of terrain each walker finds most novel, hard to draw, learnable, interesting --------------------------
    strata = []
    for by in ("texture_q", "brightness_q"):
        t = sc.groupby(["group", "ckpt", "cover", by])[[f"z_{k}" for k in SIGNALS]].mean().reset_index().rename(columns={by: "quartile"})
        strata.append(t.assign(by=by.removesuffix("_q")))
    strata = pd.concat(strata)
    strata.to_csv(OUT / "panel_strata.csv", index=False)

    # -- panel readouts per run and checkpoint, paired against the Reference like the walk readouts --------------------------------------
    rows = []
    for (run, ck), d in sc.groupby(["run", "ckpt"]):
        r = {"group": d.group.iloc[0], "seed": int(d.seed.iloc[0]), "run": run, "phase": f"ckpt_{ck}"}
        for k in SIGNALS:
            for name, col in PROPS.items():
                r[f"panel_{k}_rho_{name}"] = spearmanr(d[f"z_{k}"], d[col])[0]
            r[f"panel_{k}_ocean_minus_land"] = d.loc[d.cover == "ocean", f"z_{k}"].mean() - d.loc[d.cover == "land", f"z_{k}"].mean()
        r["panel_e_mean"] = d.e.mean()  # how well it draws the panel at all (only comparable at equal crop_px)
        rows.append(r)
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "panel_readouts.csv", index=False)
    paired(R).to_csv(OUT / "panel_paired.csv", index=False)
    C = calibration(R[R.group.isin(STAGE0) & R.seed.isin(STAGE0_SEEDS)])  # Stage 0: the h0111 walks only
    C.to_csv(OUT / "panel_calibration.csv", index=False)

    # -- taste similarity: rank correlation of panel interest between every pair of walkers -------------------------------------------
    sims = []
    for ck, d in sc.groupby("ckpt"):
        M = d.pivot(index="tile_idx", columns="run", values="z_I")
        rho = M.corr(method="spearman")
        meta = d.drop_duplicates("run").set_index("run")[["group", "seed"]]
        for i, a in enumerate(rho.index):
            for b in rho.index[i + 1 :]:
                ga, sa, gb, sb = *meta.loc[a], *meta.loc[b]
                kind = "same setting, other seed" if ga == gb else "same seed, other setting" if sa == sb else "other setting, other seed"
                sims.append({"ckpt": ck, "a": a, "b": b, "group_a": ga, "group_b": gb, "kind": kind, "pair": " / ".join(sorted([ga, gb])), "rho": rho.loc[a, b]})
        if ck == 1000:
            order = meta.sort_values(["group", "seed"], key=lambda v: v.map({g: i for i, g in enumerate(GROUPS)}) if v.name == "group" else v).index
            fig, ax = plt.subplots(figsize=(9, 8))
            im = ax.imshow(rho.loc[order, order], cmap="viridis", vmin=0, vmax=1)
            ax.set_xticks(range(len(order)), order, rotation=90, fontsize=6)
            ax.set_yticks(range(len(order)), order, fontsize=6)
            fig.colorbar(im, ax=ax, label="Spearman ρ of panel interest")
            ax.set_title("Taste similarity at step 1,000")
            fig.tight_layout()
            fig.savefig(OUT / "panel_similarity.png", dpi=120)
            plt.close(fig)
    sims = pd.DataFrame(sims)
    sims.to_csv(OUT / "panel_similarity.csv", index=False)

    pd.set_option("display.width", 250)
    print("-- taste similarity (Spearman ρ of panel interest), by kind of pair --")
    print(sims.groupby(["ckpt", "kind"]).rho.agg(["mean", "min", "max", "size"]).round(3).to_string())
    print("\n-- same seed, by pair of settings, step 1,000 --")
    print(sims[(sims.ckpt == 1000) & (sims.kind == "same seed, other setting")].groupby("pair").rho.agg(["mean", "min", "max"]).round(3).to_string())
    print("\n-- panel calibration --")
    print(C[["phase", "readout", "ref_mean", "seed_sd", "detectable", "null_diff", "null_in_sd", "null_same_sign", "null_verdict", "bored_diff", "bored_in_sd", "bored_same_sign", "bored_verdict"]]
          .round(3).to_string(index=False))
    print("\n-- Reference, mean z by cover and texture quartile (step 1,000) --")
    print(strata[(strata.group == "Reference") & (strata.ckpt == 1000) & (strata.by == "texture")].round(2).to_string(index=False))


if __name__ == "__main__":
    {"select": select, "score": score, "summarise": summarise}[sys.argv[1]]()
