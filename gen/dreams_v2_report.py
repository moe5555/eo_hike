"""Dreams v2 report: score, select, memorisation search, sheets and the scores table.

    python -m gen.dreams_v2 report runs/baseline_s0

Reads runs/<run>/dreams_v2/samples/<model>/{pool,guided}.npy, writes into runs/<run>/dreams_v2/:
scores.csv, summary.csv, contact_sheet_<res>_<px>.png, v1_vs_v2.png, memorisation_<model>.png,
novelty_strips.png.

nn_train_dist: pixel RMSE (0-255) to the nearest crop of the model's own training set, searched
over the fixed crop bank (gen/hires.py) in all 8 flips/rotations. For the 10 m models that bank
*is* the training data; the 40 m (v1-recipe) models trained on fresh random crops of the 256 px
tiles, so for them the bank is a 64-crops-per-tile stand-in and the distance is an upper bound.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image, ImageDraw, ImageFont

from gen.dreams_v2 import LAMBDAS, N_KEEP, REAL_N, WUNDT, Agent, out_dir, random_ids

ROOT = Path(__file__).resolve().parents[1]
SETS = ("path_weighted", "random_uniform", "path_uniform")
FOV = {"10m": "10 m/px, 640 m view", "40m": "~42 m/px, 2.7 km view"}
INK, MUTED, SURFACE = (11, 11, 11), (82, 81, 78), (252, 252, 251)


def font(size: int = 16):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def parse(model: str) -> tuple[str, int, str]:
    res, px, s = model.split("_", 2)
    return res, int(px), s


def train_bank(run: Path, model: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(crops of this model's set, their tile ids, crops of tiles NOT in the set) from the bank."""
    res, px, s = parse(model)
    sets = pd.read_parquet(ROOT / "data" / "sets" / run.name / "sets.parquet")
    tiles = sets[sets.set == s].tile_idx.to_numpy()
    bk = np.load(ROOT / "data" / "crops" / f"{res}_{px}.npz")
    keep = np.isin(bk["tile_idx"], tiles)
    return bk["crops"][keep], bk["tile_idx"][keep], bk["crops"][~keep]


def dihedral(x: torch.Tensor, k: int) -> torch.Tensor:
    """x [B,H,W,3]; k in 0..7: rotate k%4 quarter turns, then flip if k>=4."""
    x = torch.rot90(x, k % 4, dims=(1, 2))
    return x.flip(2) if k >= 4 else x


@torch.no_grad()
def nearest(samples: np.ndarray, bank: np.ndarray, dev: str = "cuda", chunk: int = 4096) -> tuple[np.ndarray, np.ndarray]:
    """Pixel-L2 nearest bank crop over 8 dihedral variants -> (rmse [n], nn image uint8 [n,H,W,3])."""
    S = torch.from_numpy(samples).to(dev).float().flatten(1)
    s2 = (S**2).sum(1)
    B = torch.from_numpy(bank).to(dev)
    best = torch.full((len(S),), float("inf"), device=dev)
    arg = torch.zeros(len(S), 2, dtype=torch.long, device=dev)
    for k in range(8):
        for c0 in range(0, len(B), chunk):
            b = dihedral(B[c0 : c0 + chunk], k).float().flatten(1)
            d = s2[:, None] + (b**2).sum(1)[None] - 2 * S @ b.T
            v, j = d.min(1)
            m = v < best
            best[m], arg[m, 0], arg[m, 1] = v[m], j[m] + c0, k
    nn = torch.stack([dihedral(B[i : i + 1], int(k))[0] for i, k in arg.tolist()]).cpu().numpy()
    # the expanded form above loses ~1 grey level to fp32 cancellation; report the exact distance
    rmse = np.sqrt(((samples.astype(np.float64) - nn) ** 2).reshape(len(nn), -1).mean(1))
    return rmse, nn


def img_stats(u8: np.ndarray) -> dict:
    x = u8.astype(np.float32) / 255
    mx, mn = x.max(-1), x.min(-1)
    return {"brightness": float(x.mean()), "saturation": float(((mx - mn) / np.maximum(mx, 1e-6)).mean()),
            "pixel_std": float((u8.reshape(len(u8), -1).std(1)).mean()), "bright_frac": float((x.mean((1, 2, 3)) > 0.6).mean())}


def grid(imgs: np.ndarray, cols: int, scale: int = 2, gap: int = 2) -> Image.Image:
    n, h = len(imgs), imgs.shape[1] * scale
    rows = int(np.ceil(n / cols))
    g = Image.new("RGB", (cols * (h + gap) - gap, rows * (h + gap) - gap), SURFACE)
    for i, im in enumerate(imgs):
        r, c = divmod(i, cols)
        g.paste(Image.fromarray(im).resize((h, h), Image.Resampling.NEAREST), (c * (h + gap), r * (h + gap)))
    return g


def labelled(blocks: list[list[Image.Image]], col_titles: list[str], row_titles: list[str], title: str, pad: int = 24) -> Image.Image:
    """Lay out blocks[r][c] with column titles on top and row titles on the left."""
    f, fb = font(18), font(24)
    lw = 230
    cw = [max(b[c].width for b in blocks if b[c] is not None) for c in range(len(col_titles))]
    rh = [max(b.height for b in row if b is not None) for row in blocks]
    W = lw + sum(cw) + pad * (len(cw) + 1)
    H = 90 + sum(rh) + pad * (len(rh) + 1)
    canvas = Image.new("RGB", (W, H), SURFACE)
    d = ImageDraw.Draw(canvas)
    d.text((pad, 16), title, fill=INK, font=fb)
    x = lw + pad
    for c, t in enumerate(col_titles):
        d.text((x, 58), t, fill=INK, font=f)
        x += cw[c] + pad
    y = 90 + pad
    for r, row in enumerate(blocks):
        d.multiline_text((pad, y), row_titles[r], fill=INK, font=f, spacing=6)
        x = lw + pad
        for c, b in enumerate(row):
            if b is not None:
                canvas.paste(b, (x, y))
            x += cw[c] + pad
        y += rh[r] + pad
    return canvas


def memorisation_sheet(model: str, groups: list[tuple[str, np.ndarray, np.ndarray, np.ndarray]], path: Path) -> None:
    """Per group: samples on top, their nearest training crop below, RMSE under each pair."""
    scale, gap, h = 2, 4, 64 * 2
    f = font(14)
    blocks, names = [], []
    for name, imgs, nn, d in groups:
        pair_w = h + gap
        b = Image.new("RGB", (len(imgs) * pair_w, 2 * h + 22), SURFACE)
        dr = ImageDraw.Draw(b)
        for i, (a, n, dd) in enumerate(zip(imgs, nn, d)):
            b.paste(Image.fromarray(a).resize((h, h), Image.Resampling.NEAREST), (i * pair_w, 0))
            b.paste(Image.fromarray(n).resize((h, h), Image.Resampling.NEAREST), (i * pair_w, h + 2))
            dr.text((i * pair_w + 4, 2 * h + 4), f"{dd:.1f}", fill=MUTED, font=f)
        blocks.append([b])
        names.append(name)
    labelled(blocks, ["top: sample · bottom: nearest training crop (8 flips/rotations) · number: pixel RMSE, 0-255"],
             names, f"Memorisation check: {model}").save(path)


def strips(df: pd.DataFrame, path: Path) -> None:
    """Small multiples: novelty and surprise per group, one column per model. One hue; groups on y."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    models = list(df.model.unique())
    lams = sorted(df.loc[df["mode"] == "guided", "λ"].unique())
    order = ["real_train", "real_unseen", "pool", "random", "novelty"] + [f"guided λ={lam:g}" for lam in lams]
    fig, axes = plt.subplots(2, len(models), figsize=(4.2 * len(models), 4.5 + 0.35 * len(order)), squeeze=False, sharey=True)
    for c, m in enumerate(models):
        dm = df[df.model == m]
        for r, metric in enumerate(["novelty", "surprise"]):
            ax = axes[r, c]
            ys = []
            for yi, g in enumerate(order):
                v = dm.loc[dm.group == g, metric].to_numpy()
                if len(v) == 0:
                    continue
                ys.append(yi)
                jit = np.random.default_rng(yi).uniform(-0.18, 0.18, len(v))
                ax.scatter(v, yi + jit, s=9, color="#2a78d6", alpha=0.45, linewidths=0)
                ax.plot([np.median(v)] * 2, [yi - 0.32, yi + 0.32], color="#0b0b0b", lw=2)
            ax.set_yticks(range(len(order)), order)
            ax.invert_yaxis()
            if metric == "surprise":
                ax.set_xscale("log")
            ax.set_xlabel(metric + (" (recon MSE, log)" if metric == "surprise" else " (mean dist. to 10 nearest archive latents)"), color="#52514e")
            ax.grid(axis="x", color="#e4e3df", lw=0.8)
            ax.set_axisbelow(True)
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
            if r == 0:
                ax.set_title(m, fontsize=11, loc="left")
    fig.suptitle("Agent baseline_s0 scoring dreams with its own AE and archive. Dots: samples; bar: median.", x=0.01, ha="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def report(run: Path) -> None:
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    dev = "cuda"
    od = out_dir(run)
    agent = Agent(run, dev)
    models = sorted(p.name for p in (od / "samples").iterdir() if (p / "pool.npy").exists())
    rid = random_ids()
    rows, kept, summ = [], {}, []
    for m in models:
        res, px, s = parse(m)
        d = od / "samples" / m
        pool = np.load(d / "pool.npy")
        bank, _, unseen_bank = train_bank(run, m)
        nov, sur = agent.score(pool)
        dist, nn = nearest(pool, bank)
        n_cut = int(round(WUNDT * len(pool)))
        rank = np.argsort(-nov)
        cut, top = rank[:n_cut], rank[n_cut : n_cut + N_KEEP]
        for i in range(len(pool)):
            rows.append({"sample_id": i, "model": m, "mode": "unguided", "λ": 0.0, "novelty": nov[i], "surprise": sur[i], "nn_train_dist": dist[i],
                         "in_random32": i in rid, "in_novelty32": i in top, "wundt_cut": i in cut})
        groups = {"pool": np.arange(len(pool)), "random": rid, "novelty": top, "wundt_cut": cut}
        kept[m] = {"pool": pool, "nn": nn, "dist": dist, "random": rid, "novelty": top, "nov": nov}
        for g, ii in groups.items():
            summ.append({"model": m, "group": g, "n": len(ii), "novelty_med": np.median(nov[ii]), "surprise_med": np.median(sur[ii]),
                         "nn_train_dist_med": np.median(dist[ii]), **img_stats(pool[ii])})
        for gf in sorted(d.glob("guided*.npy")):  # guided.npy (the brief's sweep) + any extra sweeps
            gu = np.load(gf)  # [L,32,H,W,3]
            gj = json.loads(gf.with_suffix(".json").read_text())
            assert gj["seed_ids"] == rid.tolist()
            kept[m].setdefault("guided", {})
            for li, lam in enumerate(gj["lambdas"]):
                gn, gs = agent.score(gu[li])
                gd, gnn = nearest(gu[li], bank)
                kept[m]["guided"][lam] = (gu[li], gnn, gd)
                for j, sid in enumerate(rid):
                    rows.append({"sample_id": int(sid), "model": m, "mode": "guided", "λ": lam, "novelty": gn[j], "surprise": gs[j], "nn_train_dist": gd[j],
                                 "in_random32": True, "in_novelty32": False, "wundt_cut": False})
                summ.append({"model": m, "group": f"guided λ={lam:g}", "n": len(gu[li]), "novelty_med": np.median(gn), "surprise_med": np.median(gs),
                             "nn_train_dist_med": np.median(gd), **img_stats(gu[li]),
                             "max_abs_diff_vs_unguided": int(np.abs(gu[li].astype(int) - pool[rid].astype(int)).max()) if lam == 0 else None})
        # real crops as a reference: own training crops, and crops of tiles outside the set
        rng = np.random.default_rng(0)
        for g, src in (("real_train", bank), ("real_unseen", unseen_bank)):
            ii = rng.choice(len(src), REAL_N, replace=False)
            rn, rs = agent.score(src[ii])
            rd = np.zeros(REAL_N) if g == "real_train" else nearest(src[ii], bank)[0]
            for j in range(REAL_N):
                rows.append({"sample_id": int(ii[j]), "model": m, "mode": g, "λ": np.nan, "novelty": rn[j], "surprise": rs[j], "nn_train_dist": rd[j],
                             "in_random32": False, "in_novelty32": False, "wundt_cut": False})
            summ.append({"model": m, "group": g, "n": REAL_N, "novelty_med": np.median(rn), "surprise_med": np.median(rs),
                         "nn_train_dist_med": np.median(rd) if g == "real_unseen" else None, **img_stats(src[ii])})
        print(f"[report] {m} scored", flush=True)

    sc = pd.DataFrame(rows)
    sc.to_csv(od / "scores.csv", index=False)
    sm = pd.DataFrame(summ)
    sm.to_csv(od / "summary.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 20):
        print(sm.round(4).to_string(index=False))

    # strips: groups as plotted
    sg = sc.copy()
    sg["group"] = np.where(sg["mode"] == "guided", "guided λ=" + sg["λ"].map(lambda v: f"{v:g}"), sg["mode"])
    extra = []
    for flag, g in (("in_random32", "random"), ("in_novelty32", "novelty")):
        e = sg[(sg["mode"] == "unguided") & sg[flag]].copy()
        e["group"] = g
        extra.append(e)
    sg.loc[sg["mode"] == "unguided", "group"] = "pool"
    strips(pd.concat([sg, *extra]), od / "novelty_strips.png")

    # contact sheet per resolution: rows = sets, columns = random, novelty-selected, guided
    for res_px in sorted({"_".join(m.split("_")[:2]) for m in models}):
        ms = [f"{res_px}_{s}" for s in SETS if f"{res_px}_{s}" in kept]
        has_g = any("guided" in kept[m] for m in ms)
        cols = ["random 32 (reference)", f"novelty-selected 32 (top {WUNDT:.0%} cut)"] + ([f"guided λ={lam:g}" for lam in LAMBDAS if lam > 0] if has_g else [])
        blocks = []
        for m in ms:
            k = kept[m]
            row = [grid(k["pool"][k["random"]], 8), grid(k["pool"][k["novelty"]], 8)]
            if has_g:
                row += [grid(k["guided"][lam][0], 8) if "guided" in k else None for lam in LAMBDAS if lam > 0]
            blocks.append(row)
        res = res_px.split("_")[0]
        labelled(blocks, cols, [f"{parse(m)[2]}\n{FOV[res]}" for m in ms],
                 f"Dreams v2, agent {run.name}: {res_px.replace('_', ' / ')} px. Columns 1 and 3-5 share seed ids; λ=0 equals column 1.").save(od / f"contact_sheet_{res_px}.png")

    # every guidance strength that was run, first 16 of the shared seed ids each
    gm = [m for m in kept if "guided" in kept[m]]
    if gm:
        lams = sorted({lam for m in gm for lam in kept[m]["guided"]})
        blocks = [[grid(kept[m]["guided"][lam][0][:16], 8) if lam in kept[m]["guided"] else None for lam in lams] for m in gm]
        labelled(blocks, [f"λ={lam:g}" for lam in lams], [f"{parse(m)[2]}\n{FOV[parse(m)[0]]}" for m in gm],
                 f"Novelty guidance sweep, agent {run.name}: same 16 seed ids in every block; λ=0 is unguided").save(od / "guidance_sweep.png")

    # v1 vs v2: same model type, same seed ids, 40 m vs 10 m data
    blocks, names = [], []
    for s in SETS:
        for res in ("40m", "10m"):
            m = f"{res}_64_{s}"
            if m in kept and f"{'10m' if res == '40m' else '40m'}_64_{s}" in kept:
                blocks.append([grid(kept[m]["pool"][rid], 32)])
                names.append(f"{s}\n{FOV[res]}")
    if blocks:
        labelled(blocks, ["the same 32 seed ids in every row (random reference)"], names,
                 f"v1 vs v2 data, agent {run.name}: identical model, steps and noise; only metres per pixel differ").save(od / "v1_vs_v2.png")

    # memorisation: every kept sample next to its nearest training crop
    for m, k in kept.items():
        groups = [(g, k["pool"][k[g]], k["nn"][k[g]], k["dist"][k[g]]) for g in ("random", "novelty")]
        for lam, (im, nn, dd) in k.get("guided", {}).items():
            if lam > 0:
                groups.append((f"guided λ={lam:g}", im, nn, dd))
        memorisation_sheet(m, groups, od / f"memorisation_{m}.png")
    print(f"[report] wrote {od}")
