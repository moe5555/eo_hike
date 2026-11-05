"""Stage 1 deliverable: the knob-to-effect matrix (brief, "Deliverables" 1) on the core of 17 readouts (observations.md, "Readouts for the sheet").

    python analysis/e08/readouts.py && python analysis/e08/panel.py score && python analysis/e08/panel.py summarise
    python analysis/e08/matrix.py

Reads results/readouts.csv and results/panel_readouts.csv, writes results/matrix.csv (one row per setting and core readout) and matrix.png.

- Each setting is paired with the Reference of the same seed: d_s = setting_s − Reference_s.
- Units: the seed SD of Stage 0 (pooled over the seven h0111 settings, seeds 0–3), fixed before any Stage 1 walk, so cells of different settings
  are on one scale. `in_sd` = mean d ÷ seed SD.
- Verdicts as in readouts.paired: lead = all paired differences with the same sign and |mean d| > half the Reference's range over the seeds
  compared; result = a lead on at least 8 seeds with at least 7 of the same sign.
- Eye readouts: rank correlation on the panel between a signal and texture, mean over checkpoints 500, 750 and 1,000 of each walk.
- Held-out error is compared only at the Reference's crop_px (64): the held-out crops depend on it.
- By chance, about 1.5 of a setting's 17 readouts are leads (9 % each, independent walks; observations.md, finding 8).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sheet import OUT, REFERENCE, SETTINGS, STAGE0, STAGE0_SEEDS  # sets sys.path

CORE = [  # (section, label, column, phase)
    ("Rhythm", "places", "places", "all"),
    ("Rhythm", "median steps per place", "median_steps_per_place", "all"),
    ("Rhythm", "teleports", "teleports", "all"),
    ("Rhythm", "rejected landings", "rejected_landings", "all"),
    ("Rhythm", "far tiles taken ÷ chance", "far_taken_over_chance", "all"),
    ("Returns", "revisits beyond blind", "revisit_excess", "all"),
    ("Returns", "straight-backs beyond blind", "back_excess", "all"),
    ("Choice", "top tile beyond chance", "top_chosen_excess", "all"),
    ("Taste", "snow, ice, cloud", "selz_bright", "settled"),
    ("Taste", "brightness", "selz_brightness", "settled"),
    ("Taste", "saturation", "selz_saturation", "settled"),
    ("Taste", "texture", "selz_texture", "settled"),
    ("Taste", "contrast", "selz_contrast", "settled"),
    ("Eye", "surprise ~ texture", "panel_e_rho_texture", "late"),
    ("Eye", "novelty ~ texture", "panel_n_rho_texture", "late"),
    ("Eye", "progress ~ texture", "panel_g_rho_texture", "late"),
    ("Learning", "held-out error at 1,000", "heldout_1000", "all"),
]
LATE = ("ckpt_500", "ckpt_750", "ckpt_1000")
REF_CROP = 64


def table() -> pd.DataFrame:
    """One row per run and core readout: group, seed, readout, value, crop_px."""
    R = pd.read_csv(OUT / "readouts.csv")
    P = pd.read_csv(OUT / "panel_readouts.csv")
    late = P[P.phase.isin(LATE)].groupby(["group", "seed", "run"]).mean(numeric_only=True).reset_index().assign(phase="late")
    crop = R.drop_duplicates("run").set_index("run").crop_px
    rows = []
    for sec, label, col, phase in CORE:
        src = late if phase == "late" else R[R.phase == phase]
        x = src[["group", "seed", "run", col]].rename(columns={col: "value"}).assign(section=sec, readout=label, phase=phase)
        rows.append(x)
    T = pd.concat(rows, ignore_index=True)
    T["crop_px"] = T.run.map(crop)
    return T


def seed_sd(T: pd.DataFrame) -> pd.Series:
    """Stage 0's pooled seed SD per readout: RMS of the within-setting SDs of the seven h0111 settings, seeds 0–3."""
    s0 = T[T.group.isin(STAGE0) & T.seed.isin(STAGE0_SEEDS)]
    return s0.groupby(["readout", "group"]).value.var(ddof=1).groupby("readout").mean() ** 0.5


def matrix(T: pd.DataFrame) -> pd.DataFrame:
    sd = seed_sd(T)
    info = {"Null": ("Stage 0", "choice", "uniform"), "Bored": ("Stage 0", "patience", 0.3), **{k: v[:3] for k, v in SETTINGS.items()}}
    rows = []
    for g, (sec, key, val) in info.items():
        for _, label, _, _ in CORE:
            ref = T[(T.group == REFERENCE) & (T.readout == label)].set_index("seed").value
            G = T[(T.group == g) & (T.readout == label)].set_index("seed")
            if G.empty:
                continue
            r = {"setting": g, "section": sec, "key": key, "value": val, "readout": label, "readout_section": T.loc[T.readout == label, "section"].iloc[0],
                 "seed_sd": float(sd[label]), "ref_mean": ref.mean(), "n": 0, "verdict": "not comparable"}
            if label.startswith("held-out") and (G.crop_px != REF_CROP).any():
                rows.append(r)
                continue
            seeds = sorted(set(G.index) & set(ref.index))
            d = (G.loc[seeds, "value"] - ref.loc[seeds]).dropna()
            if d.empty:
                r["verdict"] = "no data"
                rows.append(r)
                continue
            rng = float(ref.loc[d.index].max() - ref.loc[d.index].min())
            same = int(max((d > 0).sum(), (d < 0).sum()))
            big = abs(d.mean()) > rng / 2
            result = len(d) >= 8 and same >= len(d) - 1 and big
            lead = len(d) >= 4 and same == len(d) and big
            r.update(n=len(d), setting_mean=G.loc[d.index, "value"].mean(), ref_mean=ref.loc[d.index].mean(), diff=d.mean(), in_sd=d.mean() / sd[label],
                     same_sign=same, ref_spread=rng, verdict="result" if result else "lead" if lead else "none", **{f"d_s{k}": v for k, v in d.items()})
            rows.append(r)
    return pd.DataFrame(rows)


def figure(M: pd.DataFrame) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    cmap = LinearSegmentedColormap.from_list("div", ["#184f95", "#2a78d6", "#f0efec", "#e34948", "#9c2b2b"])
    settings = list(dict.fromkeys(M.setting))
    readouts = [c[1] for c in CORE]
    Z = M.pivot(index="setting", columns="readout", values="in_sd").reindex(index=settings, columns=readouts)
    V = M.pivot(index="setting", columns="readout", values="verdict").reindex(index=settings, columns=readouts)
    fig, ax = plt.subplots(figsize=(11, 0.34 * len(settings) + 2.6))
    ax.imshow(np.clip(Z.to_numpy(float), -4, 4), cmap=cmap, vmin=-4, vmax=4, aspect="auto")
    for i, s in enumerate(settings):
        for j, r in enumerate(readouts):
            v, z = V.loc[s, r], Z.loc[s, r]
            if v in ("lead", "result"):
                ax.text(j, i, f"{z:+.1f}" + ("*" if v == "result" else ""), ha="center", va="center", fontsize=7, color="white" if abs(z) > 2.5 else "#222",
                        fontweight="bold")
            elif not np.isfinite(z):
                ax.text(j, i, "·", ha="center", va="center", fontsize=8, color="#999")
    ax.set_xticks(range(len(readouts)), readouts, rotation=55, ha="right", fontsize=8)
    ax.set_yticks(range(len(settings)), settings, fontsize=8)
    ax.set_xticks(np.arange(len(readouts) + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(len(settings) + 1) - 0.5, minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="minor", length=0)
    for k in ("top", "right", "left", "bottom"):
        ax.spines[k].set_visible(False)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(-4, 4))
    fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02, label="setting − Reference, in Stage 0 seed SDs (clipped at ±4)")
    ax.set_title("What each setting does: paired effect against the Reference (number = lead, * = result on 8 seeds, · = not comparable)", fontsize=9, loc="left")
    fig.tight_layout()
    fig.savefig(OUT / "matrix.png", dpi=130)
    plt.close(fig)


def main() -> None:
    T = table()
    M = matrix(T)
    M.to_csv(OUT / "matrix.csv", index=False)
    figure(M)
    pd.set_option("display.width", 250)
    n = M[M.n > 0].groupby("setting", sort=False).agg(seeds=("n", "max"), leads=("verdict", lambda v: int(v.isin(["lead", "result"]).sum())),
                                                        results=("verdict", lambda v: int((v == "result").sum())))
    print("-- leads per setting (chance about 1.5 of 17) --\n" + n.to_string())
    hits = M[M.verdict.isin(["lead", "result"])]
    print("\n-- leads and results --\n" + hits[["setting", "readout", "n", "ref_mean", "setting_mean", "in_sd", "same_sign", "verdict"]].round(3).to_string(index=False))
    print(f"\nwrote {OUT}/matrix.csv, matrix.png")


if __name__ == "__main__":
    main()
