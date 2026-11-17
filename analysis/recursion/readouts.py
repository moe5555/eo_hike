"""Across the recursion: each generation's GAN against the real world it descends from (predictions 165, 166, 169-173).

For every generation g with saved samples (runs/g<g>/gan/<cond>/samples/seed00000-04999.png, the same seeds in every generation, psi 1):
- coverage of the real world: precision and recall (k = 3 manifolds, 32 x 32 x 3 pixel space, L2; the GAN readouts' observer) against
  the real G1 package of the same condition (paths/g1/<cond>, 5,000 tiles drawn with seed 0), and against the generation's own
  training set (paths/g<g>/<cond>);
- spread: the median distance from a sample to its nearest other sample (32 px space), and the standard deviation across samples of
  brightness and of each channel's mean (colour and texture statistics of the 128 px samples, labelled as such);
- the apparatus (colour and texture statistics, not the quirk detectors): mean row roughness, green band dark share, black and white
  shares;
- the collapse flag, set by hand before G3 (notes/06_characters/expectations.md, 2026-11-17): recall against the real G1 package below
  half of G1's AND nearest-sample distance below 70 % of G1's, for that condition.

    scripts/sg.bat analysis/recursion/readouts.py   ->  notes/recursion/ (recursion.csv, recursion.json, trends.png, strip_<cond>.png)
One GAN per condition per generation and one walk each: every trend is a hint; the era confound of the G1 packages carries through.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "gen"))
import g1_gan as GG  # noqa: E402

OUT = ROOT / "notes" / "recursion"
CONDS = ("curious", "null")
N = 5000
COLLAPSE = {"recall_real_vs_g1": 0.5, "nn_sample_vs_g1": 0.7}


def tiles(d: Path, n: int) -> np.ndarray:
    files = sorted((d / "tiles").glob("*.png"))
    rng = np.random.default_rng(0)
    pick = np.sort(rng.choice(len(files), min(n, len(files)), replace=False))
    return GG.read_pngs([files[i] for i in pick])


def main() -> None:
    import torch

    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    strips = {c: [] for c in CONDS}
    for cond in CONDS:
        real = GG.down(tiles(ROOT / "paths" / "g1" / cond, N))
        for g in range(1, 20):
            sd = ROOT / "runs" / f"g{g}" / "gan" / cond / "samples"
            files = [sd / f"seed{s:05d}.png" for s in range(N)]
            if not sd.exists() or not all(f.exists() for f in files[:: 500]):
                continue
            files = [f for f in files if f.exists()]
            S = GG.read_pngs(files)
            fs = GG.down(S)
            own = GG.down(tiles(ROOT / "paths" / f"g{g}" / cond, N))
            pr_real = GG.prec_recall(torch, real, fs)
            pr_own = GG.prec_recall(torch, own, fs)
            nn = GG.cdist_min(torch, fs, fs, exclude_self=True)[0][:, 0]
            cs = GG.colour_stats(S)
            r = {"gen": g, "cond": cond, "n_samples": len(S),
                 "precision_real": pr_real["precision"], "recall_real": pr_real["recall"],
                 "precision_own": pr_own["precision"], "recall_own": pr_own["recall"],
                 "nn_sample_median": float(np.median(nn)),
                 "sd_brightness": float(cs.brightness.std()), "sd_mean_r_nir": float(cs.mean_r_nir.std()),
                 "sd_mean_g_red": float(cs.mean_g_red.std()), "sd_mean_b_green": float(cs.mean_b_green.std()),
                 **{f"mean_{k}": float(cs[k].astype(float).mean()) for k in ("brightness", "row_roughness", "green_band_dark", "black_share", "white_share", "grad_x")}}
            rows.append(r)
            strips[cond].append((g, S[:12]))
            print(f"[recursion] g{g} {cond}: recall_real {r['recall_real']:.3f} nn {r['nn_sample_median']:.3f} rough {r['mean_row_roughness']:.3f}", flush=True)
    df = pd.DataFrame(rows).sort_values(["cond", "gen"])
    for cond in CONDS:
        m = df.cond == cond
        g1 = df[m & (df.gen == 1)]
        if len(g1):
            df.loc[m, "recall_real_vs_g1"] = df.loc[m, "recall_real"] / float(g1.recall_real.iloc[0])
            df.loc[m, "nn_sample_vs_g1"] = df.loc[m, "nn_sample_median"] / float(g1.nn_sample_median.iloc[0])
    if "recall_real_vs_g1" in df:
        df["collapse_flag"] = (df.recall_real_vs_g1 < COLLAPSE["recall_real_vs_g1"]) & (df.nn_sample_vs_g1 < COLLAPSE["nn_sample_vs_g1"])
    df.to_csv(OUT / "recursion.csv", index=False)
    (OUT / "recursion.json").write_text(json.dumps({"rows": df.to_dict("records"), "collapse_rule": COLLAPSE,
                                                    "observer": "32 x 32 x 3 pixel space, L2, k = 3; colour and texture statistics of the 128 px samples (not quirk detectors)",
                                                    "reference": "the real G1 package of the same condition, 5,000 tiles (seed 0)"}, indent=1, default=float))
    # figures: trends per condition, and the same 12 seeds in every generation
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    keys = ["recall_real", "precision_real", "nn_sample_median", "sd_brightness", "mean_row_roughness", "mean_green_band_dark"]
    fig, ax = plt.subplots(1, len(keys), figsize=(3.2 * len(keys), 3))
    for a, k in zip(ax, keys):
        for cond, col in (("curious", "tab:red"), ("null", "tab:blue")):
            d = df[df.cond == cond]
            a.plot(d.gen, d[k], "o-", color=col, label=cond)
        a.set_title(k, fontsize=9)
        a.set_xlabel("generation")
        a.set_xticks(sorted(df.gen.unique()))
    ax[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "trends.png", dpi=100)
    for cond in CONDS:
        if not strips[cond]:
            continue
        g_ = 2
        im = Image.new("RGB", (12 * (128 + g_) - g_, len(strips[cond]) * (128 + g_) - g_), (255, 255, 255))
        for r_, (g, S) in enumerate(strips[cond]):
            for c_, t in enumerate(S):
                im.paste(Image.fromarray(t), (c_ * (128 + g_), r_ * (128 + g_)))
        im.save(OUT / f"strip_{cond}.png")
    print(df.round(3).to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
