"""Stage 0.1 and 0.3: the sheet readouts for every run, the paired differences against the Reference of the same seed, and the calibration.

    python analysis/e08/readouts.py

Writes to notes/08_character_sheet/results/: readouts.csv (one row per run and phase), paired.csv (one row per setting, phase and readout),
calibration.csv (one row per readout and phase: Null and Bored against the Reference, the seed SD, the effect four seeds can show).

Definitions (brief, Stage 0.1), all on steps with a choice (more than one candidate) unless they are about teleports:
- places, teleports, bursts, rejected landings: as in analysis/h0111/compare.py. A place belongs to the phase in which it starts.
- far taken ÷ chance: far tiles taken over the sum of 1/C on the steps where one was offered.
- excess revisit: share of choices that went to an already visited tile, minus the share of visited tiles among the candidates (a blind walker's
  expectation on the same steps). Excess straight-back: share of choices that went back to the tile just left, minus its blind chance 1/C.
- selection differential (sel_): on steps where a neighbour was chosen, the chosen tile's property minus the mean over the neighbours on offer,
  averaged over steps. Far offers are left out: they are the same tile for every walker of a seed, and taking them is far_taken's readout.
  Standardised (selz_): the same difference divided by the SD of the property among the neighbours, over the steps where it varies.
- top chosen: share of choices that took the highest-interest candidate; `_excess` subtracts the blind chance 1/C.
- appetite end: the first logged step from 100 on at which the fall in log held-out error over the trailing 200 steps stops (h0111 task 7);
  1,000 if it never stops (censored).
- spread: the range (max − min) of the Reference over the seeds compared. Lead: all paired differences with the same sign and |mean| > spread / 2.
  Result: a lead with 8 seeds, at least 7 of them with the same sign.
- seed SD: the spread between seeds of one setting, pooled over all groups (RMS of the within-group SDs). Pairing by seed barely reduces it once
  two walks diverge, which every setting but the landing variants does from step 0: on the panel, same-seed pairs of different settings agree
  no more than different seeds of one setting (log, Stage 0.3). So effects are given in seed SDs, and `detectable` = 2 seed SDs, the effect a
  four-seed lead catches 70 % of the time when the two walks are independent (simulated; 3 SDs: 93 %). The same simulation gives the lead
  rule a false-alarm rate of 9 % per readout for independent walks, and the eight-seed result rule 1.3 %.
- sd_paired_landing: SD of the paired differences of the four landing comparisons (Reference k=3, k=8 against Reference; Bored k=3, k=8
  against Bored). Kept for reference; too small as a noise model, because those walks share their path until the first teleport.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sheet import OUT, PHASES, REFERENCE, RUNS, STAGE0, STAGE0_SEEDS, candidates, config, heldout, places, runs, steps, tile_stats  # sets sys.path

from compare import BURST_GAP  # noqa: E402  (analysis/h0111)
from task7_appetite import appetite  # noqa: E402

TASTE = {"texture": "grad", "contrast": "grey_std", "entropy": "entropy", "brightness": "grey_mean", "bright": "bright", "saturation": "sat", "ocean": "ocean"}
NOISE_PAIRS = [("Reference k=3", "Reference"), ("Reference k=8", "Reference"), ("Bored k=3", "Bored"), ("Bored k=8", "Bored")]
DETECT_SD = 2.0  # 70 % power for a four-seed lead between independent walks


def teleport_flags(s: pd.DataFrame) -> pd.DataFrame:
    """One row per bored teleport (the step boredom fired) with in_burst, and one per landing with rejected (compare.burst_stats, per event)."""
    tele = s.step[s.bored_event].to_numpy()
    close = np.diff(tele) <= BURST_GAP
    in_burst = (np.r_[False, close] | np.r_[close, False]) if len(tele) > 1 else np.zeros(len(tele), bool)
    ends_bored = s.groupby("place").bored_event.last()
    land = s[s.jump_type == "bored"]
    rejected = (land.place_len <= BURST_GAP).to_numpy() & ends_bored.reindex(land.place).to_numpy(bool)
    return pd.DataFrame({"step": tele, "in_burst": in_burst}), pd.DataFrame({"step": land.step.to_numpy(), "rejected": rejected})


def colour_div(rgb: np.ndarray) -> float:
    if len(rgb) < 2:
        return np.nan
    d = np.sqrt(((rgb[:, None] - rgb[None]) ** 2).sum(-1))
    return float(d[np.triu_indices(len(rgb), 1)].mean())


def appetite_end(h: pd.DataFrame, n: int) -> float:
    a = appetite(h, n, 200)
    grid = h.step.to_numpy()
    hit = [g for g in grid if 100 <= g < n and a[g] <= 0]
    return float(hit[0]) if hit else float(n)


def readouts(group: str, seed: int, run: str, ts: pd.DataFrame) -> list[dict]:
    s = places(steps(run))
    c = candidates(run).join(ts[list(TASTE.values())], on="tile_idx")
    h = heldout(run)
    tele, land = teleport_flags(s)
    starts = s.groupby("place").agg(start=("step", "first"), length=("place_len", "first"))
    ch = c[c.C > 1]
    per = ch.groupby("step")
    chosen = ch[ch.chosen].set_index("step")
    offer = pd.DataFrame({"C": per.size(), "seen_share": per.seen.mean(), "back_chance": per.back.sum() / per.size(), "top": per.I.max()})
    offer = offer.join(chosen[["seen", "back", "I", "kind"]])
    offer["top_chosen"] = offer.I == offer.top
    # taste: choices within a place, among the neighbours only; a far offer is the same tile for every walker of a seed and is read by far_taken
    nb = ch[ch.kind == "neighbour"]
    nb = nb[nb.groupby("step").step.transform("size") > 1]
    nper, nchosen = nb.groupby("step"), nb[nb.chosen].set_index("step")
    for name, col in TASTE.items():
        offer[f"sel_{name}"] = nchosen[col] - nper[col].mean()
        sd = nper[col].std(ddof=0)
        offer[f"selz_{name}"] = offer[f"sel_{name}"] / sd.where(sd > 0)  # standardised: in SDs of what was on offer; steps without spread left out
    far = c[c.kind == "long"].groupby("step").agg(taken=("chosen", "max"), C=("C", "first"))
    first = s.drop_duplicates("tile_idx")
    rows = []
    for phase, (lo, hi) in PHASES.items():
        inp = lambda v: (v >= lo) & (v < hi)  # noqa: E731
        st, o, f, pl = s[inp(s.step)], offer[inp(offer.index)], far[inp(far.index)], starts[inp(starts.start)]
        t, ld = tele[inp(tele.step)], land[inp(land.step)]
        u = first[inp(first.step)]
        urgb = ts.loc[u.tile_idx.to_numpy(), ["r", "g", "b"]].to_numpy()
        r = {"group": group, "seed": seed, "run": run, "phase": phase, "steps": len(st),
             "places": len(pl), "median_steps_per_place": float(pl.length.median()), "longest_place": float(pl.length.max()),
             "teleports": len(t), "teleport_burst_share": float(t.in_burst.mean()) if len(t) else np.nan, "rejected_landings": int(ld.rejected.sum()),
             "far_offered": len(f), "far_taken": int(f.taken.sum()), "far_taken_over_chance": float(f.taken.sum() / (1 / f.C).sum()) if len(f) else np.nan,
             "revisit_share": float(o.seen.mean()), "revisit_excess": float(o.seen.mean() - o.seen_share.mean()),
             "back_share": float(o.back.mean()), "back_excess": float(o.back.mean() - o.back_chance.mean()),
             "top_chosen": float(o.top_chosen.mean()), "top_chosen_excess": float(o.top_chosen.mean() - (1 / o.C).mean()),
             **{f"sel_{k}": float(o[f"sel_{k}"].mean()) for k in TASTE}, **{f"selz_{k}": float(o[f"selz_{k}"].mean()) for k in TASTE},
             "unique_tiles": len(u), "ocean_share": float((u.cover == "ocean").mean()), "colour_diversity": colour_div(urgb)}
        if phase == "all":
            hm = h.set_index("step").heldout_mse
            r.update(steps_before_first_jump=int(starts.length.iloc[0]), heldout_250=float(hm[250]), heldout_500=float(hm[500]), heldout_1000=float(hm[1000]),
                     appetite_end=appetite_end(h, len(s)), crop_px=int(config(run)["crop_px"]))
        rows.append(r)
    return rows


def all_readouts() -> pd.DataFrame:
    rs = runs()
    ids = np.unique(np.concatenate([pd.read_parquet(RUNS / r / "candidates.parquet", columns=["tile_idx"]).tile_idx.to_numpy() for _, _, r in rs]))
    print(f"[readouts] {len(rs)} runs, {len(ids)} distinct candidate tiles", flush=True)
    ts = tile_stats(ids)
    R = pd.DataFrame([row for g, sd, r in rs for row in readouts(g, sd, r, ts)])
    return R


def metric_cols(R: pd.DataFrame) -> list[str]:
    return [c for c in R.columns if c not in ("group", "seed", "run", "phase", "steps", "crop_px")]


def paired(R: pd.DataFrame, against: str = REFERENCE, groups=None) -> pd.DataFrame:
    """setting_s − reference_s per seed, for every group, phase and readout."""
    rows = []
    for phase, P in R.groupby("phase"):
        ref = P[P.group == against].set_index("seed")
        for g in groups or [x for x in P.group.unique() if x != against]:
            G = P[P.group == g].set_index("seed")
            sd = sorted(set(G.index) & set(ref.index))
            for m in metric_cols(R):
                d = (G.loc[sd, m] - ref.loc[sd, m]).dropna()
                if d.empty:
                    continue
                rng = float(ref.loc[sd, m].max() - ref.loc[sd, m].min())  # the Reference's spread over the seeds compared
                same = int(max((d > 0).sum(), (d < 0).sum()))
                big = abs(d.mean()) > rng / 2
                result = len(d) >= 8 and same >= len(d) - 1 and big
                lead = len(d) >= 4 and same == len(d) and big
                verdict = "result" if result else "lead" if lead else "none"
                rows.append({"group": g, "against": against, "phase": phase, "readout": m, "n": len(d), "mean": d.mean(), "min": d.min(), "max": d.max(),
                             "same_sign": same, "ref_mean": ref[m].mean(), "ref_spread": rng, "effect_in_spread": d.mean() / rng if rng else np.nan, "verdict": verdict,
                             **{f"d_s{k}": v for k, v in d.items()}})
    return pd.DataFrame(rows)


def calibration(R: pd.DataFrame) -> pd.DataFrame:
    P = paired(R)
    noise = pd.concat([paired(R, against=b, groups=[a]) for a, b in NOISE_PAIRS])
    sd_land = noise.groupby(["phase", "readout"])[[c for c in noise.columns if c.startswith("d_s")]].apply(lambda x: np.sqrt(np.nanmean(np.nanvar(x.to_numpy(float), axis=1, ddof=1))))
    seed_sd = R.groupby(["phase", "group"])[metric_cols(R)].var(ddof=1).groupby("phase").mean() ** 0.5
    rows = []
    for (phase, m), x in P.groupby(["phase", "readout"]):
        x = x.set_index("group")
        sd = float(seed_sd.loc[phase, m]) if m in seed_sd else np.nan
        r = {"phase": phase, "readout": m, "ref_mean": x.ref_mean.iloc[0], "ref_spread": x.ref_spread.iloc[0], "seed_sd": sd,
             "detectable": DETECT_SD * sd, "sd_paired_landing": float(sd_land.get((phase, m), np.nan))}
        for g in ("Null", "Bored"):
            if g in x.index:
                y = x.loc[g]
                r.update({f"{g.lower()}_diff": y["mean"], f"{g.lower()}_range": f"{y['min']:.3g}…{y['max']:.3g}", f"{g.lower()}_same_sign": f"{y.same_sign}/{y.n}",
                          f"{g.lower()}_in_sd": y["mean"] / sd if sd else np.nan, f"{g.lower()}_verdict": y.verdict})
        rows.append(r)
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    R = all_readouts()
    R.to_csv(OUT / "readouts.csv", index=False)
    P = paired(R)
    P.to_csv(OUT / "paired.csv", index=False)
    C = calibration(R[R.group.isin(STAGE0) & R.seed.isin(STAGE0_SEEDS)])  # Stage 0: the h0111 walks only
    C.to_csv(OUT / "calibration.csv", index=False)
    pd.set_option("display.width", 250)
    for phase in PHASES:
        x = C[C.phase == phase]
        print(f"\n-- calibration, {phase} --")
        print(x[["readout", "ref_mean", "seed_sd", "detectable", "null_diff", "null_in_sd", "null_same_sign", "null_verdict", "bored_diff", "bored_in_sd", "bored_same_sign", "bored_verdict"]]
              .round(4).to_string(index=False))
    print(f"\nwrote {OUT}/readouts.csv, paired.csv, calibration.csv")


if __name__ == "__main__":
    main()
