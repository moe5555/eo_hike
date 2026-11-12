"""Experiment 12 readouts (notes/brief_landsat_pipeline.md, E15; predictions 96-110 in notes/06_characters/expectations.md).

    python analysis/e12/readouts.py            # every finished e12 walk -> notes/12_two_eye/results/*.csv
    python analysis/e12/readouts.py shuffle    # the patch-shuffle test on the final networks (slower)

Written before the factorial walks finished (2026-11-12) and not changed after, except for bugs (logged).
Steps before SETTLE (50) are left out. Quirk shares are the pass world's tables (analysis/e12/pass_quirks.py); "stripe" and "at255"
are the maximum over the three bands the eye sees (green, red, nir08); brightness is the mean pixel of the rendered tile (the one view).

Per walk:
- decomposition: mean share of |contribution| at the choice for glance, grid, progress; mean lift (contribution at the choice minus its
  mean over the offers; the lifts sum to I_chosen - mean I).
- within tile: on chosen tiles and on all offers, the top crop's quirk minus the median of its tile's other 15 crops; and the share
  of tiles where the top crop is above that median, among tiles where the quirk varies.
- selection (offer -> choice): selz = (value at the choice - mean over the offers) / SD over the offers, averaged over steps with SD > 0,
  for the tile's stripe, DN 255, QA cloud, brightness, and its most striped crop ("crop_stripe_max"); also by halves (50-500, 500-1000).
- edge pull: share of chosen tiles (and of all offers) whose top crop is on the tile's edge (12 of 16 crops: chance 0.75).
- correlations over offers: Spearman of glance, grid and v1-shadow novelty with cloud and brightness; shadow against pooled grid.
- returns: revisit share (cell visited before), straight-backs (back to the cell two steps ago), unique cells.
- rhythm: share of steps at r_max, number of r_max episodes; far - near gap in offered interest (long yardstick).
- forgetting: grid and glance error on the forgetting set at 0, 500, 1,000, by kind.
- death dry run (brief D12): C1 (surprise > running mean + 3 running SD, rate 0.002 cumulative until step 500, values before the step,
  after step 150), C2 (C1 after 50 steps of drive d >= 0), C3 (r_max for 20 steps in a row); sources glance, pooled grid, max grid
  (v1: its one surprise). Each firing with the tile's terrain and quirks.
A hint (two seeds): both seeds of a condition outside the Null's two-seed range, on the same side.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
RUNS = ROOT / "runs"
OUT = ROOT / "notes" / "12_two_eye" / "results"
CACHE = ROOT / "data" / "sheet"
WORLD = ROOT / "data" / "landsat" / "LM01_183_19721122" / "c10680m_256px_cir_sqrt"
SETTLE = 50
SEEN = ("green", "red", "nir08")
CONDS = ["e12_v1", "e12_null", "e12_grid_mean", "e12_grid_top4", "e12_grid_top1", "e12_two_top4", "e12_two_top4_g2",
         "e12_two_top4_shifted", "e12_two_top4_shuffled"]
EDGE = np.array([r in (0, 3) or c in (0, 3) for r, c in (divmod(k, 4) for k in range(16))])


def world_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per cell: stripe, at255 (max over seen bands), cloud, fill, brightness, crop_stripe_max, cover. Per crop: stripe, at255, cloud, fill."""
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / "e12_pass_cells.parquet"
    q = pd.read_parquet(WORLD / "quirks.parquet").set_index("tile_idx")
    qc = pd.read_parquet(WORLD / "crop_quirks.parquet")
    for d in (q, qc):
        d["stripe"] = d[[f"stripe_{b}" for b in SEEN]].max(axis=1)
        d["at255"] = d[[f"at255_{b}" for b in SEEN]].max(axis=1)
    if p.exists():
        cells = pd.read_parquet(p)
    else:
        tiles = np.load(WORLD / "tiles.npy", mmap_mode="r")
        br = np.array([float(np.asarray(tiles[i]).mean()) for i in range(len(tiles))])
        idx = pd.read_parquet(WORLD / "index.parquet").set_index("idx")
        cells = pd.DataFrame({"brightness": br, "cover": idx.cover.to_numpy()}, index=idx.index)
        cells.to_parquet(p)
    cells = cells.join(q[["stripe", "at255", "cloud", "fill"]])
    cells["crop_stripe_max"] = qc.groupby("tile_idx").stripe.max()
    cells["bright_q"] = pd.qcut(cells.brightness, 4, labels=False)
    return cells, qc[["tile_idx", "crop", "stripe", "at255", "cloud", "fill"]]


def runs() -> list[tuple[str, int, Path]]:
    out = []
    for c in CONDS:
        for s in (0, 1):
            r = RUNS / f"{c}_s{s}"
            if (r / "final.pt").exists():
                out.append((c, s, r))
    return out


def selz(c: pd.DataFrame, col: str) -> float:
    g = c.groupby("step")[col]
    mu, sd = g.transform("mean"), g.transform("std", ddof=0)
    z = ((c[col] - mu) / sd)[c.chosen & (sd > 1e-12)]
    return float(z.mean()) if len(z) else np.nan


def within_tile(cr: pd.DataFrame, q: str) -> tuple[float, float]:
    """Top crop minus the median of the other 15, mean over tiles; share of tiles with top above, among tiles where q varies."""
    v = cr[q].to_numpy().reshape(-1, 16)
    rank = cr["rank"].to_numpy().reshape(-1, 16)
    top = v[np.arange(len(v)), rank.argmin(1)]
    others = np.where(rank == 0, np.nan, v)
    med = np.nanmedian(others, 1)
    vary = np.nanmax(v, 1) > np.nanmin(v, 1)
    ex = top - med
    return float(np.nanmean(ex)), float(np.nanmean((ex > 0)[vary])) if vary.any() else np.nan


def running_z(x: np.ndarray, alpha: float = 0.002) -> tuple[np.ndarray, np.ndarray]:
    """Running mean and SD of x before each step (rate max(alpha, 1/t))."""
    m = sd = np.full(len(x), np.nan)
    m, sd = m.copy(), sd.copy()
    mu = var = 0.0
    for t, v in enumerate(x):
        if t > 0:
            m[t], sd[t] = mu, np.sqrt(var)
        a = max(alpha, 1.0 / (t + 1))
        mu_new = (1 - a) * mu + a * v
        var = (1 - a) * var + a * (v - mu_new) ** 2 if t > 0 else 0.0
        mu = mu_new
    return m, sd


def deaths(cond: str, seed: int, s: pd.DataFrame, cr: pd.DataFrame | None, cells: pd.DataFrame, qc: pd.DataFrame, r_max: float) -> list[dict]:
    out = []
    srcs = {"glance": "e_glance", "grid_pooled": "e_grid", "grid_max": "e_grid_max"} if "e_glance" in s else {"v1": "e"}
    d = s.drive_d.to_numpy()
    settled = pd.Series(d >= 0).rolling(50).sum().shift(1).to_numpy() >= 50
    rmax = s.r_km.to_numpy() >= r_max * 0.999
    run20 = pd.Series(rmax).rolling(20).sum().to_numpy() >= 20
    crop_med = None
    if cr is not None:
        ch = cr[cr.chosen]
        crop_med = {q: float(ch[q].median()) for q in ("stripe", "at255")}
    for src, col in srcs.items():
        x = s[col].to_numpy(float)
        m, sd = running_z(x)
        c1 = (s.step.to_numpy() >= 150) & (x > m + 3 * sd)
        c2 = c1 & settled
        for cond_name, fire in (("C1", c1), ("C2", c2)):
            for t in np.flatnonzero(fire):
                row = s.iloc[t]
                rec = {"cond": cond, "seed": seed, "source": src, "rule": cond_name, "step": int(row.step), "tile_idx": int(row.tile_idx),
                       "z": float((x[t] - m[t]) / sd[t])}
                cl = cells.loc[int(row.tile_idx)]
                rec.update(cover=cl.cover, cloud=cl.cloud, bright_q=int(cl.bright_q), stripe=cl.stripe, at255=cl.at255)
                if cr is not None:
                    tc = ch[ch.step == row.step]
                    if len(tc) == 16:
                        top = tc.loc[tc["rank"].idxmin()]
                        worst = tc.loc[tc.e.idxmax()]
                        rec.update(top_crop_quirky=bool(top.stripe > crop_med["stripe"] or top.at255 > crop_med["at255"]),
                                   maxerr_crop_quirky=bool(worst.stripe > crop_med["stripe"] or worst.at255 > crop_med["at255"]))
                out.append(rec)
    for t in np.flatnonzero(run20 & ~np.r_[False, run20[:-1]]):  # C3: the first step of each 20-step stretch at r_max
        row = s.iloc[t]
        cl = cells.loc[int(row.tile_idx)]
        out.append({"cond": cond, "seed": seed, "source": "drive", "rule": "C3", "step": int(row.step), "tile_idx": int(row.tile_idx),
                    "cover": cl.cover, "cloud": cl.cloud, "bright_q": int(cl.bright_q), "stripe": cl.stripe, "at255": cl.at255})
    return out


def readout(cond: str, seed: int, r: Path, cells: pd.DataFrame, qc: pd.DataFrame) -> tuple[dict, list[dict]]:
    cfg = __import__("yaml").safe_load((r / "config.yaml").read_text())
    s = pd.read_parquet(r / "steps.parquet")
    c = pd.read_parquet(r / "candidates.parquet")
    meta = json.loads((r / "meta.json").read_text())
    r_max = float(cfg["radius_max_km"])
    out = {"cond": cond, "seed": seed, "eye": cfg.get("eye", "v1"), "minutes": meta.get("seconds", np.nan) / 60, "sec_per_step": s.sec.mean()}
    # returns over the whole walk
    t = s.tile_idx.to_numpy()
    seen, rev = set(), []
    for v in t:
        rev.append(v in seen)
        seen.add(v)
    st = s.step >= SETTLE
    out["revisit"] = float(np.mean(np.array(rev)[st.to_numpy()]))
    sb = np.r_[False, False, (t[2:] == t[:-2]) & (t[2:] != t[1:-1])]
    out["straight_back"] = float(sb[st.to_numpy()].mean())
    out["unique_cells"] = int(len(set(t)))
    # rhythm
    at = s.r_km.to_numpy() >= r_max * 0.999
    out["share_rmax"] = float(at[st.to_numpy()].mean())
    out["rmax_episodes"] = int(((at[1:]) & (~at[:-1])).sum() + at[0])
    if "I_long" in c:
        cs = c.merge(s[["step", "r_km"]], on="step")
        far, near = cs[cs.r_km >= r_max * 0.999], cs[cs.r_km <= float(cfg["radius_min_km"]) * 1.001]
        out["far_near_gap_Ilong"] = float(far.groupby("step").I_long.mean().mean() - near.groupby("step").I_long.mean().mean()) if len(far) and len(near) else np.nan
    # selection, offer -> choice
    c = c.join(cells[["stripe", "at255", "cloud", "brightness", "crop_stripe_max"]], on="tile_idx")
    cst = c[c.step >= SETTLE]
    for q in ("stripe", "at255", "cloud", "brightness", "crop_stripe_max"):
        out[f"selz_{q}"] = selz(cst, q)
        out[f"selz_{q}_h1"] = selz(cst[cst.step < 500], q)
        out[f"selz_{q}_h2"] = selz(cst[cst.step >= 500], q)
    # two-eye readouts
    cr = None
    if out["eye"] != "v1":
        ss = s[st]
        for k in ("glance", "grid", "prog"):
            out[f"share_{k}"] = float(ss[f"share_{k}"].mean())
            out[f"lift_{k}"] = float(ss[f"lift_{k}"].mean())
        out["best_offer"] = float(ss.best_offer.mean())
        out["p_chosen"] = float(ss.p_chosen.mean())
        cr = pd.read_parquet(r / "crops.parquet", columns=["step", "tile_idx", "crop", "e", "n", "rank", "share", "chosen"])
        cr = cr.merge(qc, on=["tile_idx", "crop"], how="left").sort_values(["step", "tile_idx", "crop"], kind="stable")
        # one tile appears once per step (offers are distinct); keep the order step, tile, crop
        crs = cr[cr.step >= SETTLE]
        ch = crs[crs.chosen]
        for q in ("stripe", "at255", "cloud", "fill"):
            out[f"wt_{q}_chosen"], out[f"wt_{q}_chosen_above"] = within_tile(ch, q)
            out[f"wt_{q}_offers"], out[f"wt_{q}_offers_above"] = within_tile(crs, q)
        top = ch[ch["rank"] == 0]
        out["edge_top_chosen"] = float(EDGE[top.crop.to_numpy()].mean())
        out["edge_top_offers"] = float(EDGE[crs[crs["rank"] == 0].crop.to_numpy()].mean())
        cc = cst.dropna(subset=["n_glance"])
        for a in ("n_glance", "n", "n_v1"):
            for b in ("cloud", "brightness"):
                out[f"rho_{a}_{b}"] = float(cc[[a, b]].corr("spearman").iloc[0, 1])
        out["rho_v1_grid"] = float(cc[["n_v1", "n"]].corr("spearman").iloc[0, 1])
        f = r / "forgetting.parquet"
        if f.exists():
            fg = pd.read_parquet(f).groupby(["step", "kind"])[["e_grid", "e_glance"]].mean()
            for (stp, kind), v in fg.iterrows():
                out[f"forget_grid_{kind}_{stp}"] = v.e_grid
                out[f"forget_glance_{kind}_{stp}"] = v.e_glance
    h = pd.read_parquet(r / "heldout.parquet")
    out["heldout_final"] = float(h.heldout_mse.iloc[-1])
    return out, deaths(cond, seed, s, cr, cells, qc, r_max)


def hints(R: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    null = R[R.cond == "e12_null"]
    rows = []
    for cond, g in R.groupby("cond"):
        if cond == "e12_null" or len(g) < 2 or len(null) < 2:
            continue
        for k in cols:
            lo, hi = null[k].min(), null[k].max()
            v = g[k].to_numpy()
            if np.all(v > hi) or np.all(v < lo):
                rows.append({"cond": cond, "readout": k, "values": np.round(v, 3).tolist(), "null": [round(lo, 3), round(hi, 3)], "side": "above" if np.all(v > hi) else "below"})
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cells, qc = world_tables()
    rows, dd = [], []
    for cond, seed, r in runs():
        o, d = readout(cond, seed, r, cells, qc)
        rows.append(o)
        dd.extend(d)
        print(f"[e12] {r.name}", flush=True)
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "readouts.csv", index=False)
    D = pd.DataFrame(dd)
    D.to_csv(OUT / "deaths.csv", index=False)
    num = [k for k in R.columns if k not in ("cond", "seed", "eye")]
    summ = R.groupby("cond", sort=False)[num].mean()
    summ.T.to_csv(OUT / "summary_by_condition.csv")
    H = hints(R, [k for k in num if k.startswith(("selz_", "revisit", "straight", "share_rmax", "rmax_", "unique", "wt_", "edge_"))])
    H.to_csv(OUT / "hints.csv", index=False)
    if len(D):
        dsum = D.groupby(["cond", "source", "rule"]).agg(n=("step", "size"), walks=("seed", "nunique"), first=("step", "min"),
                                                         cloud_ge_03=("cloud", lambda v: float((v >= 0.3).mean())),
                                                         bright_top=("bright_q", lambda v: float((v == 3).mean())))
        if "top_crop_quirky" in D:
            dsum = dsum.join(D.groupby(["cond", "source", "rule"])[["top_crop_quirky", "maxerr_crop_quirky"]].mean())
        dsum.to_csv(OUT / "deaths_summary.csv")
    print(summ.T.round(3).to_string())


# -- the patch-shuffle test ------------------------------------------------------------------------------------------------------
def shuffle_test(n: int = 200) -> None:
    """For each finished two-eye or grid walk: n random pass cells it never visited, as they are and with their 16 grid crops shuffled
    (one fixed permutation per cell, seed 0). Novelty of both eyes against the walk's final memories, with its final networks."""
    import torch
    import yaml

    from agent import eyes as E
    from agent.model import ConvAE

    tiles = np.load(WORLD / "tiles.npy", mmap_mode="r")
    rows = []
    for cond, seed, r in runs():
        cfg = yaml.safe_load((r / "config.yaml").read_text())
        if cfg.get("eye", "v1") == "v1":
            continue
        ck = torch.load(r / "final.pt", map_location="cpu")
        mg, ml = ConvAE(), ConvAE()
        mg.load_state_dict(ck["model"])
        ml.load_state_dict(ck["glance"])
        mem = np.load(r / "memories.npz")
        # the final memories as saved (float16), re-embedded at the end of the walk
        mc, mlz = torch.from_numpy(mem["crop"].astype(np.float32)), torch.from_numpy(mem["glance"].astype(np.float32))
        visited = set(mem["tile_idx"].tolist())
        rng = np.random.default_rng(0)
        pool = np.array([i for i in range(len(tiles)) if i not in visited])
        ids = np.sort(rng.choice(pool, n, replace=False))
        img = torch.from_numpy(np.stack([np.asarray(tiles[i]) for i in ids]))
        perm = np.stack([rng.permutation(16) for _ in ids])
        sh = img.clone()
        for a, p in enumerate(perm):
            for k, src in enumerate(p):
                (r0, c0), (r1, c1) = divmod(k, 4), divmod(int(src), 4)
                sh[a, r0 * 64 : (r0 + 1) * 64, c0 * 64 : (c0 + 1) * 64] = img[a, r1 * 64 : (r1 + 1) * 64, c1 * 64 : (c1 + 1) * 64]
        unit = bool(cfg.get("normalise_latents", False))
        u = (lambda z: torch.nn.functional.normalize(z, dim=-1)) if unit else (lambda z: z)
        res = {}
        with torch.no_grad():
            for nm, x in (("orig", img), ("shuf", sh)):
                xg, xl = E.grid_crops(x), E.glances(x)
                zg = mg.encode(xg.flatten(0, 1)).view(len(ids), 16, -1)
                ng, _ = E.topk_mean(E.place_novelty(u(zg), u(mc), int(cfg["k_nn"])), int(cfg.get("novelty_topk", 4)))
                nl = E.knn_mean(u(ml.encode(xl)), u(mlz), int(cfg["k_nn"]))
                res[nm] = (ng.numpy(), nl.numpy())
        dg = np.abs(res["shuf"][0] - res["orig"][0])
        rel = (res["shuf"][1] - res["orig"][1]) / np.maximum(res["orig"][1], 1e-9)
        rows.append({"cond": cond, "seed": seed, "grid_max_abs_change": float(dg.max()), "glance_rel_change_median": float(np.median(rel)),
                     "glance_up_share": float((rel > 0).mean()), "glance_orig_median": float(np.median(res["orig"][1])),
                     "glance_shuf_median": float(np.median(res["shuf"][1]))})
        print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(OUT / "patch_shuffle.csv", index=False)


if __name__ == "__main__":
    shuffle_test() if sys.argv[1:2] == ["shuffle"] else main()
