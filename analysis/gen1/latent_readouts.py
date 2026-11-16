"""Readouts of the G1 latent walks (notes/brief_g1_latent_walks.md): each wanderer in its own GAN's world.

Inputs: runs/g1/latent/<cond>/ (steps.parquet, offers.parquet, walk.json, meta.json, calibration.json, tiles/).
Outputs: notes/gen1/latent/ (small tables and figures; --test writes to runs/g1/latent_test/readouts/ instead).

- time: steps per snapshot, the step each snapshot is first reached, waits, how often a time offer came through;
- movement: alpha over the walk against the drive, the angle of each step and from the start;
- taste: offered against chosen colour and texture statistics of the 128 px renders (labelled as such), compass offers only, overall and per snapshot;
- waits against moves: interest components at the choice;
- interest shares at the choice, against the real generation-1 walks (notes/gen1/gen1/walks.csv);
- contact sheets: a visited tile every 500 steps, and the last 50 steps.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CONDS = ("curious", "null")
STATS = ["brightness", "white_share", "black_share", "green_band_dark", "mean_r_nir", "mean_g_red", "mean_b_green", "grad", "row_roughness"]
COLOURS = {"curious": "#c0504d", "null": "#4f81bd"}


def load(base: Path, cond: str) -> dict:
    d = base / cond
    return {"s": pd.read_parquet(d / "steps.parquet"), "o": pd.read_parquet(d / "offers.parquet"), "walk": json.loads((d / "walk.json").read_text()),
            "meta": json.loads((d / "meta.json").read_text()), "cal": json.loads((d / "calibration.json").read_text()), "dir": d}


def tile_png(d: Path, key: int, snap: int) -> Path:
    return d / "tiles" / f"k{key:06d}_s{snap:04d}.png"


def sheet(paths: list[Path], labels: list[str], cols: int, px: int, out: Path) -> None:
    rows = max(1, int(np.ceil(len(paths) / cols)))
    fig, axs = plt.subplots(rows, cols, figsize=(cols * px / 80, rows * (px / 80 + 0.25)), squeeze=False)
    for ax in axs.flat:
        ax.axis("off")
    for ax, p, lab in zip(axs.flat, paths, labels):
        if p.exists():
            ax.imshow(Image.open(p).convert("RGB").resize((px, px), Image.NEAREST))
        ax.set_title(lab, fontsize=6)
    fig.tight_layout(pad=0.2)
    fig.savefig(out, dpi=80)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--gen", type=int, default=1)  # which generation's latent walks
    a = ap.parse_args()
    base = ROOT / "runs" / f"g{a.gen}" / ("latent_test" if a.test else "latent")
    out = base / "readouts" if a.test else ROOT / "notes" / f"gen{a.gen}" / "latent"
    out.mkdir(parents=True, exist_ok=True)
    W = {c: load(base, c) for c in CONDS if (base / c / "walk.json").exists()}
    if not W:
        sys.exit("no finished latent walks")
    real = pd.read_csv(ROOT / "notes" / "gen1" / "gen1" / "walks.csv", keep_default_na=False, na_values=[""]) if (ROOT / "notes" / "gen1" / "gen1" / "walks.csv").exists() else None

    rows, snap_rows, taste_rows, wm_rows = [], [], [], []
    for cond, D in W.items():
        s, o, snaps = D["s"], D["o"], D["meta"]["snapshots"]
        wait = s.kind == "time"
        r = {"cond": cond, **{k: D["walk"][k] for k in ("steps", "end_reason", "unique_tiles", "waits", "final_snapshot", "seconds")},
             "q": D["meta"]["q"], "alpha_min_deg": D["cal"]["alpha_min_deg"], "alpha_max_deg": D["cal"]["alpha_max_deg"],
             "calib_rho_colour": D["cal"]["real"]["colour"]["rho"], "calib_rho_pixels": D["cal"]["real"]["pixels"]["rho"],
             "calib_alpha_pixels_deg": D["cal"]["gan"]["pixels"]["alpha_min_deg"], "calib_snapshot": D["cal"]["snapshot"],
             "wait_share": wait.mean(), "time_exists_share": s.time_exists.mean(), "time_offered_share": s.time_offered.mean(),
             "wait_share_when_offered": wait[s.time_offered].mean() if s.time_offered.any() else np.nan,
             "chance_wait_when_offered": (1.0 / s.n_offers[s.time_offered]).mean() if s.time_offered.any() else np.nan,
             "median_alpha_deg": s.alpha_deg.median(), "alpha_at_min_share": (s.alpha_deg <= D["cal"]["alpha_min_deg"] * 1.0001).mean(),
             "alpha_at_max_share": (s.alpha_deg >= D["cal"]["alpha_max_deg"] * 0.9999).mean(),
             "median_angle_step_deg": s.angle_step_deg[~wait].median(), "angle_from_start_end_deg": s.angle_from_start_deg.iloc[-1],
             "angle_from_start_median_deg": s.angle_from_start_deg.median(), "p_chosen_mean": s.p_chosen.mean(), "best_offer_share": s.best_offer.mean(),
             **{f"share_{k}": s[f"share_{k}"].mean() for k in ("glance", "grid", "prog")}}
        v = np.load(D["dir"] / "visited.npz")
        z = v["z"] / np.linalg.norm(v["z"], axis=1, keepdims=True)
        for L in (1, 10, 100, 1000):  # the angle between positions L steps apart: in 512-d the angle from the start saturates near 90 deg within ~100 steps
            if len(z) > L:
                ang = np.degrees(np.arccos(np.clip((z[L:] * z[:-L]).sum(1), -1.0, 1.0)))
                r[f"angle_lag{L}_median_deg"] = float(np.median(ang))
        for i, k in enumerate(snaps):
            r[f"first_step_at_{k}"] = int(s.step[s.snapshot == k].min()) if (s.snapshot == k).any() else None
        if real is not None and "condition" in real:
            rr = real[real.condition == cond]  # mean over the generation-1 walks of this condition
            for k in ("glance", "grid", "prog"):
                r[f"real_share_{k}"] = rr[f"share_{k}"].mean() if f"share_{k}" in rr else np.nan
        rows.append(r)
        for k in snaps:
            g = s[s.snapshot_before == k]
            snap_rows.append({"cond": cond, "snapshot": k, "steps": len(g), "waits_out": int((g.kind == "time").sum()),
                              "time_offered_share": g.time_offered.mean() if len(g) else np.nan,
                              "median_alpha_deg": g.alpha_deg.median() if len(g) else np.nan,
                              **{f"chosen_{c}": g[f"chosen_{c}"].mean() if len(g) else np.nan for c in STATS}})
        oc = o[o.kind == "compass"]
        for scope, g in [("all", oc)] + [(f"snapshot {k}", oc[oc.snapshot == k]) for k in snaps]:
            if not len(g):
                continue
            ch = g[g.chosen]
            for c in STATS:
                taste_rows.append({"cond": cond, "scope": scope, "stat": c, "offered": g[c].mean(), "chosen": ch[c].mean() if len(ch) else np.nan,
                                   "chosen_minus_offered": (ch[c].mean() - g[c].mean()) if len(ch) else np.nan, "n_steps": int(ch.step.nunique())})
        for lab, g in (("wait", s[wait]), ("move", s[~wait])):
            wm_rows.append({"cond": cond, "at": lab, "n": len(g), **{f"z_{k}": g[f"z_{k}"].mean() for k in ("glance", "grid", "prog")},
                            "I": g.I.mean(), "drive_d": g.drive_d.mean(), "alpha_deg": g.alpha_deg.mean()})

    walks = pd.DataFrame(rows)
    walks.to_csv(out / "walks.csv", index=False)
    pd.DataFrame(snap_rows).to_csv(out / "snapshots.csv", index=False)
    taste = pd.DataFrame(taste_rows)
    taste.to_csv(out / "taste.csv", index=False)
    pd.DataFrame(wm_rows).to_csv(out / "waits_vs_moves.csv", index=False)

    # figures: snapshot against step; alpha and the drive; angle from the start
    fig, axs = plt.subplots(1, 3, figsize=(13, 3.4))
    for cond, D in W.items():
        s = D["s"]
        axs[0].step(s.step, s.snapshot, where="post", color=COLOURS[cond], label=cond)
        axs[1].plot(s.step, s.alpha_deg.rolling(100, min_periods=1).median(), color=COLOURS[cond], label=f"{cond} alpha (rolling median 100)")
        axs[2].plot(s.step, s.angle_from_start_deg, color=COLOURS[cond], lw=0.6, label=cond)
    axs[0].set(xlabel="step", ylabel="snapshot (kimg) = the clock", title="time: the snapshot at each step")
    axs[1].set(xlabel="step", ylabel="alpha (deg)", yscale="log", title="movement: the drive's angle")
    axs[2].set(xlabel="step", ylabel="angle from start (deg)", title="movement: from the start z")
    for ax in axs:
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out / "time_movement.png", dpi=100)
    plt.close(fig)

    # taste: chosen minus offered, compass offers, per statistic (labelled colour and texture statistics)
    t = taste[taste.scope == "all"].pivot(index="stat", columns="cond", values="chosen_minus_offered").reindex(STATS)
    fig, ax = plt.subplots(figsize=(7, 3.4))
    t.plot.barh(ax=ax, color=[COLOURS[c] for c in t.columns])
    ax.axvline(0, color="k", lw=0.5)
    ax.set(xlabel="chosen minus offered (compass offers; colour and texture statistics of the 128 px render)", ylabel="")
    fig.tight_layout()
    fig.savefig(out / "taste.png", dpi=100)
    plt.close(fig)

    for cond, D in W.items():
        s, d, snaps = D["s"], D["dir"], D["meta"]["snapshots"]
        pick = [0] + list(range(499, len(s), 500))
        paths = [tile_png(d, D["meta"]["start_key"], snaps[0])] + [tile_png(d, int(s.key.iloc[i]), int(s.snapshot.iloc[i])) for i in pick[1:]]
        labels = [f"start, {snaps[0]}"] + [f"step {i + 1}, {int(s.snapshot.iloc[i])}" for i in pick[1:]]
        sheet(paths, labels, 8, 96, out / f"contact_every500_{cond}.png")
        last = s.tail(50)
        sheet([tile_png(d, int(k), int(sn)) for k, sn in zip(last.key, last.snapshot)],
              [f"{int(st) + 1} {kd[0]}" for st, kd in zip(last.step, last.kind)], 10, 64, out / f"last50_{cond}.png")

    summ = {"walks": walks.to_dict(orient="records"), "note": "colour and texture statistics are of the 128 px renders, labelled as such; "
            "one walk per condition, one GAN per condition: hints, never leads; the era confound of the packages carries into the GANs"}
    (out / "latent_readouts.json").write_text(json.dumps(summ, indent=1, default=lambda x: None if isinstance(x, float) and np.isnan(x) else str(x)))
    print(walks.T.to_string())
    print(f"[latent_readouts] wrote {out}")


if __name__ == "__main__":
    main()
