"""Stage 0.5: the readouts of experiment 09 for every run, the paired differences, and the figures.

    python analysis/e09/readouts.py                  # every finished run of GROUPS
    python analysis/e09/readouts.py --runs e09_smoke_s0 e09_test_fetch_s0     # given runs only (checks), nothing paired

Writes to notes/09_compass/results/: readouts.csv (one row per run and phase), paired.csv (setting − compass Reference, per seed, with the
e08 verdicts: lead on four seeds, result on eight), places.csv (one row per place of the compass runs), radius.png, steplength.png,
recovery.png. Panel surprise per checkpoint is cached in data/sheet/e09_panel_eye.parquet (git-ignored).

The e08 core, kept (brief, "Readouts"):
- Returns: revisit_excess, back_excess. As in e08 (analysis/e08/readouts.py): on steps with more than one offer, the share of choices that
  went to a visited tile (straight back to the tile just left) minus a blind walker's expectation over the actual offers.
- Choice: top_chosen_excess, the share of choices that took the highest-interest offer minus 1/C.
- Taste: selz_ (texture, contrast, brightness, bright = snow/ice/cloud, saturation, and ocean), settled phase: the chosen offer's property
  minus the mean over the offers, in SDs of the offers, averaged over steps where it varies. Compass runs use all eight offers (all are
  "compass" offers; there are no shared far offers to leave out); classic runs keep e08's neighbours-only definition.
- Eye: panel_e_rho_texture, Spearman rho between the walker's surprise on the 300 panel tiles (analysis/e08/panel.csv) and their texture,
  mean over checkpoints 500, 750 and 1,000.
- Learning: heldout_1000.

The loop (compass runs only; brief, "New: the loop"):
- share_rmin, share_rmax: share of steps after the warm-up whose offers were at r_min (at r_max); share_mid: beyond 2 r_min but below r_max.
- rmax_episodes_per_1000, rmax_episode_median: unbroken runs of steps at r_max; rmax_to_rmin: share of r_max steps followed directly by an
  r_min step (chattering). outside_europe: share of steps on cells outside Europe (fetchcost.continent).
- step_median_km, step_p90_km: the distance actually walked per step (dist_km, steps > 0).
- step-length shape (whole walk): fits of a power law, an exponential and a lognormal above x_min (chosen by the KS distance, Clauset,
  Shalizi & Newman 2009), log-likelihood ratios with Vuong's normalised R and p. Read only against the controls.
- period: the first local maximum of the autocorrelation of log r after its first zero crossing, steps after the warm-up (NaN if none
  before lag 500).
- recovery: mean of d[t+10] − d[t] over steps t whose offers were at r_max, minus the same over steps at r_min (d after the step's
  choice, drive_d). Also both terms separately. In the compass Reference a step is at r_max only when d is at its lowest, so part of
  this is regression to the mean.
- recovery_at_d (schedule controls only, where the radius does not depend on d): the coefficient on f_t = log(r_t/r_min)/log(r_max/r_min)
  in the least-squares fit d[t+10] − d[t] ~ 1 + d[t] + f_t, steps after the warm-up: the change in d from a step at r_max rather than
  r_min, at the same d. Fixed before Stage 2 (log, 2026-11-09).
- places (D8): maximal runs of steps whose offers were at r <= 2 r_min; places, median dwell (steps), and per place the fall in the drive
  signal from arrival to departure (mean of its first three steps minus its last three; places of at least 6 steps). dwell_fall_rho is
  the Spearman rho between dwell and that fall over places.
- offer_n_far, offer_n_near, offer_n_gap (secondary; log, 2026-11-09): median novelty n of every cell offered at r_max, at r_min, and
  far minus near, steps from 150. In the Reference near offers are sampled only while d >= 0 (selection by the rule); in the shifted
  control the radius does not depend on d, so its gap is the eye's and the world's. The test of the larger eye (Stage 3).
- range: radius of gyration (km, about the walk's 3-D centroid), continents reached (rough boxes, fetchcost.continent), unique cells,
  ocean share of the cells stood on.
"""

from __future__ import annotations

import argparse
import importlib.util

import numpy as np
import pandas as pd
from e09_common import OUT, R_MIN, ROOT, RUNS, YOUNG  # sets sys.path
from fetchcost import continent

PHASES = {"all": (0, 10**9), "young": (0, YOUNG), "settled": (YOUNG, 10**9)}
TASTE = {"texture": "grad", "contrast": "grey_std", "brightness": "grey_mean", "bright": "bright", "saturation": "sat", "ocean": "ocean"}
EYE_CKPTS = (500, 750, 1000)
EYE_CACHE = ROOT / "data" / "sheet" / "e09_panel_eye.parquet"
REFERENCE = "compass Reference"
# label -> stems tried in order per seed (configs/09_compass/). Classic Reference: the e08 walks (seeds 0-3 are h0111's).
GROUPS = {
    "compass Reference": "e09_ref",  # Δ 0.25, drive averages 20 / 200 steps, drive from step 50 (Stage 1, two rounds)
    "compass Null": "e09_null",  # Stage 2
    "shifted radius": "e09_shifted",
    "shuffled radius": "e09_shuffled",
    "fixed radius": "e09_fixed",
    "local only": "e09_local",
    "compass Reference, start B": "e09_ref_startb",
    "compass Reference, start C": "e09_ref_startc",
    "eye 5 km (crop 128)": "e09_crop128",  # Stage 3, the larger eye (log 2026-11-09); held-out error compares only within one crop_px
    "eye 5 km, shifted": "e09_crop128_shifted",
    "eye 8 km (crop 192)": "e09_crop192",
    "eye 8 km, shifted": "e09_crop192_shifted",
    "classic Reference": ("h0111_reference", "e08_reference"),
    "round 1, delta 0.35": "e09_reference",  # Stage 1 round 1: drive averages 50 / 500 steps
    "round 1, delta 0.175": "e09_delta_0175",
    "round 1, delta 0.7": "e09_delta_07",
    "round 2, delta 0.25": "e09_avg20_d025",  # Stage 1 round 2: drive averages 20 / 200 steps, drive from step 0
    "round 2, delta 0.35": "e09_avg20_d035",
    "round 2, delta 0.5": "e09_avg20_d05",
}


def _e08_readouts():
    spec = importlib.util.spec_from_file_location("e08_readouts", ROOT / "analysis" / "e08" / "readouts.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


E08 = _e08_readouts()
import sheet  # noqa: E402  (analysis/e08: loaders, tile statistics, networks)


def runs(groups=GROUPS, seeds=range(8)) -> list[tuple[str, int, str]]:
    out = []
    for g, stems in groups.items():
        for sd in seeds:
            for stem in (stems,) if isinstance(stems, str) else stems:
                if (RUNS / f"{stem}_s{sd}" / "final.pt").exists():
                    out.append((g, sd, f"{stem}_s{sd}"))
                    break
    return out


# -- step lengths -----------------------------------------------------------------------------------------------------------------------
def _ll_power(x, xm):
    a = 1 + len(x) / np.log(x / xm).sum()
    return np.log((a - 1) / xm) - a * np.log(x / xm), a


def _ll_exp(x, xm):
    lam = 1 / (x - xm).mean()
    return np.log(lam) - lam * (x - xm), lam


def _ll_lognormal(x, xm):
    from scipy.optimize import minimize
    from scipy.stats import norm

    lx = np.log(x)

    def nll(p):
        mu, s = p[0], np.exp(p[1])
        return -(norm.logpdf(lx, mu, s) - lx - norm.logsf(np.log(xm), mu, s)).sum()

    r = minimize(nll, [lx.mean(), np.log(lx.std() + 1e-6)], method="Nelder-Mead")
    mu, s = r.x[0], np.exp(r.x[1])
    return norm.logpdf(lx, mu, s) - lx - norm.logsf(np.log(xm), mu, s), (mu, s)


def _vuong(l1, l2):
    from scipy.stats import norm

    d = l1 - l2
    R = d.sum()
    sd = d.std(ddof=1) * np.sqrt(len(d))
    return R, (R / sd if sd > 0 else np.nan), (2 * norm.sf(abs(R / sd)) if sd > 0 else np.nan)


def steplength_fit(x: np.ndarray) -> dict:
    """Clauset, Shalizi & Newman (2009): x_min by the KS distance of the power-law fit, then power law against exponential and lognormal
    above x_min (positive R favours the power law)."""
    x = np.sort(np.asarray(x, float)[np.asarray(x) > 0])
    if len(x) < 50 or len(np.unique(x)) < 10:
        return {}
    best = (np.inf, None)
    for xm in np.unique(np.quantile(x, np.linspace(0, 0.9, 46))):
        y = x[x >= xm]
        if len(y) < 30:
            continue
        a = 1 + len(y) / np.log(y / xm).sum()
        cdf = 1 - (y / xm) ** (1 - a)
        ks = np.abs(cdf - np.arange(1, len(y) + 1) / len(y)).max()
        best = min(best, (ks, xm), key=lambda b: b[0])
    if best[1] is None:
        return {}
    xm = best[1]
    y = x[x >= xm]
    lp, a = _ll_power(y, xm)
    le, lam = _ll_exp(y, xm)
    ln, (mu, s) = _ll_lognormal(y, xm)
    R_pe, z_pe, p_pe = _vuong(lp, le)
    R_pl, z_pl, p_pl = _vuong(lp, ln)
    return {"sl_xmin_km": xm, "sl_n_tail": len(y), "sl_alpha": a, "sl_ks": best[0], "sl_R_power_vs_exp": R_pe, "sl_p_power_vs_exp": p_pe,
            "sl_R_power_vs_lognormal": R_pl, "sl_p_power_vs_lognormal": p_pl, "sl_lognormal_mu": mu, "sl_lognormal_sigma": s, "sl_exp_mean_km": 1 / lam}


# -- loop readouts ------------------------------------------------------------------------------------------------------------------------
def period(logr: np.ndarray, max_lag: int = 500) -> float:
    x = logr - logr.mean()
    if x.std() == 0 or len(x) < 20:
        return np.nan
    n = len(x)
    ac = np.correlate(x, x, "full")[n - 1 :] / (x.var() * np.arange(n, 0, -1))
    ac = ac[: min(max_lag, n // 2)]
    neg = np.flatnonzero(ac < 0)
    if not len(neg):
        return np.nan
    for k in range(neg[0] + 1, len(ac) - 1):
        if ac[k] > ac[k - 1] and ac[k] >= ac[k + 1] and ac[k] > 0:
            return float(k)
    return np.nan


def recovery(d: np.ndarray, r: np.ndarray, r_min: float, r_max: float, lag: int = 10) -> dict:
    t = np.arange(len(d) - lag)
    dd = d[t + lag] - d[t]
    far, near = np.isclose(r[t], r_max), np.isclose(r[t], r_min)
    a = float(dd[far].mean()) if far.any() else np.nan
    b = float(dd[near].mean()) if near.any() else np.nan
    return {"recovery": a - b, "recovery_after_rmax": a, "recovery_after_rmin": b, "n_rmax_steps": int(far.sum())}


def recovery_at_d(d: np.ndarray, r: np.ndarray, r_min: float, r_max: float, start: int, lag: int = 10) -> float:
    t = np.arange(start, len(d) - lag)
    f = np.log(r[t] / r_min) / np.log(r_max / r_min)
    ok = np.isfinite(d[t]) & np.isfinite(d[t + lag])
    if ok.sum() < 50 or np.std(f[ok]) == 0:
        return np.nan
    X = np.column_stack([np.ones(ok.sum()), d[t][ok], f[ok]])
    return float(np.linalg.lstsq(X, (d[t + lag] - d[t])[ok], rcond=None)[0][2])


def place_table(s: pd.DataFrame, r_min: float) -> pd.DataFrame:
    near = (s.r_km.to_numpy() <= 2 * r_min + 1e-9)
    m = np.r_[False, near, False].astype(int)
    st, en = np.flatnonzero(np.diff(m) == 1), np.flatnonzero(np.diff(m) == -1)
    x = s.drive_x.to_numpy()
    rows = []
    for a, b in zip(st, en):
        dwell = b - a
        fall = float(x[a : a + 3].mean() - x[b - 3 : b].mean()) if dwell >= 6 else np.nan
        rows.append({"start": int(s.step.iloc[a]), "dwell": int(dwell), "fall": fall, "lat": float(s.lat.iloc[a]), "lon": float(s.lon.iloc[a])})
    # a fixed radius above 2 r_min never stands near: no places, but the columns are kept
    return pd.DataFrame(rows, columns=["start", "dwell", "fall", "lat", "lon"])


def gyration_km(lat, lon) -> float:
    if len(lat) == 0:
        return np.nan
    la, lo = np.radians(np.asarray(lat, float)), np.radians(np.asarray(lon, float))
    p = np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], 1)
    c = p.mean(0)
    c /= np.linalg.norm(c) if np.linalg.norm(c) > 0 else 1
    ang = np.arccos(np.clip(p @ c, -1, 1)) * 6371.0088
    return float(np.sqrt((ang**2).mean()))


# -- the panel's eye ------------------------------------------------------------------------------------------------------------------------
def panel_eye(run_list: list[str]) -> pd.DataFrame:
    """Surprise on the 300 panel tiles at checkpoints 500, 750, 1,000 (as analysis/e08/panel.py scores it), cached per run and checkpoint."""
    import torch
    from scipy.stats import spearmanr

    from agent import signals as S

    have = pd.read_parquet(EYE_CACHE) if EYE_CACHE.exists() else pd.DataFrame(columns=["run", "ckpt", "rho_texture", "e_mean"])
    done = set(zip(have.run, have.ckpt))
    panel = pd.read_csv(sheet.PANEL)
    todo = [(r, ck) for r in run_list for ck in EYE_CKPTS if (r, ck) not in done and (RUNS / r / f"ckpt_{ck:04d}.pt").exists()]
    if todo:
        from data.tile_store import TileStore

        store, xs, new = TileStore(), {}, []
        for r, ck in todo:
            cfg = sheet.config(r)
            key = (int(cfg["K"]), int(cfg["crop_px"]))
            if key not in xs:
                xs[key] = sheet.scoring_crops(store, panel.tile_idx.to_list(), *key)
            with torch.no_grad():
                e = S.recon_err(sheet.net(r, ck), xs[key]).numpy()
            new.append({"run": r, "ckpt": ck, "rho_texture": spearmanr(e, panel.grad)[0], "e_mean": float(e.mean())})
        have = pd.concat([have, pd.DataFrame(new)], ignore_index=True) if len(have) else pd.DataFrame(new)
        EYE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        have.to_parquet(EYE_CACHE, index=False)
    return have


# -- per run --------------------------------------------------------------------------------------------------------------------------------
def readouts(group: str, seed: int, run: str, ts: pd.DataFrame, eye: pd.DataFrame) -> tuple[list[dict], pd.DataFrame]:
    cfg = sheet.config(run)
    s = pd.read_parquet(RUNS / run / "steps.parquet")
    c = sheet.candidates(run).join(ts[list(TASTE.values())], on="tile_idx")
    compass = cfg.get("nav", "classic") == "compass"
    ch = c[c.C > 1]
    per = ch.groupby("step")
    chosen = ch[ch.chosen].set_index("step")
    offer = pd.DataFrame({"C": per.size(), "seen_share": per.seen.mean(), "back_chance": per.back.sum() / per.size(), "top": per.I.max()})
    offer = offer.join(chosen[["seen", "back", "I"]])
    offer["top_chosen"] = offer.I == offer.top
    nb = ch[ch.kind.isin(["compass"] if compass else ["neighbour"])]
    nb = nb[nb.groupby("step").step.transform("size") > 1]
    nper, nchosen = nb.groupby("step"), nb[nb.chosen].set_index("step")
    for name, col in TASTE.items():
        sd = nper[col].std(ddof=0)
        offer[f"selz_{name}"] = (nchosen[col] - nper[col].mean()) / sd.where(sd > 0)
    h = sheet.heldout(run).set_index("step").heldout_mse
    ey = eye[(eye.run == run) & eye.ckpt.isin(EYE_CKPTS)]
    pl = pd.DataFrame()
    loop: dict = {}
    if compass:
        r_min, r_max = float(cfg["radius_min_km"]), float(cfg["radius_max_km"])
        warm = int(cfg.get("drive_warmup", 50))
        pl = place_table(s, r_min).assign(group=group, seed=seed, run=run)
        live = s.step.to_numpy() > warm
        r = s.r_km.to_numpy()
        cr = c[["step", "n"]].merge(s[["step", "r_km"]], on="step")
        cr = cr[cr.step >= YOUNG]
        nfar, nnear = cr.n[np.isclose(cr.r_km, r_max)], cr.n[np.isclose(cr.r_km, r_min)]
        loop = {"offer_n_far": float(nfar.median()) if len(nfar) else np.nan, "offer_n_near": float(nnear.median()) if len(nnear) else np.nan,
                "offer_n_gap": float(nfar.median() - nnear.median()) if len(nfar) and len(nnear) else np.nan,
                "period": period(np.log(r[live])), **recovery(s.drive_d.to_numpy(), r, r_min, r_max),
                "recovery_at_d": recovery_at_d(s.drive_d.to_numpy(), r, r_min, r_max, warm + 1) if cfg.get("radius_schedule") else np.nan,
                **steplength_fit(s.dist_km.to_numpy()[1:]),
                "dwell_fall_rho": float(pl[["dwell", "fall"]].dropna().corr(method="spearman").iloc[0, 1]) if pl.fall.notna().sum() >= 5 else np.nan}
    rows = []
    for phase, (lo, hi) in PHASES.items():
        inp = lambda v: (v >= lo) & (v < hi)  # noqa: E731
        st, o = s[inp(s.step)], offer[inp(offer.index)]
        u = st.drop_duplicates("tile_idx")
        steps_moved = st.dist_km.to_numpy()[st.step.to_numpy() > 0]
        row = {"group": group, "seed": seed, "run": run, "phase": phase, "nav": cfg.get("nav", "classic"), "steps": len(st),
               "revisit_excess": float(o.seen.mean() - o.seen_share.mean()), "back_excess": float(o.back.mean() - o.back_chance.mean()),
               "top_chosen_excess": float(o.top_chosen.mean() - (1 / o.C).mean()), "offers_mean": float(o.C.mean()),
               **{f"selz_{k}": float(o[f"selz_{k}"].mean()) for k in TASTE},
               "step_median_km": float(np.median(steps_moved)) if len(steps_moved) else np.nan,
               "step_p90_km": float(np.percentile(steps_moved, 90)) if len(steps_moved) else np.nan,
               "gyration_km": gyration_km(st.lat, st.lon), "continents": int(len(set(continent(st.lat, st.lon)))),
               "unique_cells": int(len(u)), "ocean_share": float((u.cover == "ocean").mean())}
        if compass:
            rr = st.r_km.to_numpy()
            lv = st.step.to_numpy() > warm
            pp = pl[inp(pl.start)] if len(pl) else pl
            row.update(share_rmin=float(np.isclose(rr[lv], r_min).mean()) if lv.any() else np.nan,
                       share_rmax=float(np.isclose(rr[lv], r_max).mean()) if lv.any() else np.nan,
                       **rmax_episodes(rr[lv], r_min, r_max),
                       outside_europe=float((continent(st.lat, st.lon) != "Europe").mean()),
                       places=len(pp), median_dwell=float(pp.dwell.median()) if len(pp) else np.nan,
                       n_drop_far=int(st.n_drop_far.sum()), n_fetch_dropped=int(st.n_dropped.sum()))
        if phase == "all":
            row.update(heldout_1000=float(h.get(1000, np.nan)), panel_e_rho_texture=float(ey.rho_texture.mean()) if len(ey) == len(EYE_CKPTS) else np.nan,
                       seconds=float(s.sec.sum()), fetch_sec=float(s.fetch_sec.sum()), **loop)
        rows.append(row)
    return rows, pl


def rmax_episodes(r: np.ndarray, r_min: float, r_max: float) -> dict:
    """Unbroken runs of steps at r_max (per 1,000 steps, median length), and chattering: the share of steps at r_max whose next step is
    at r_min, i.e. a jump straight from far to near with nothing between."""
    at = np.isclose(r, r_max)
    m = np.r_[False, at, False].astype(int)
    st, en = np.flatnonzero(np.diff(m) == 1), np.flatnonzero(np.diff(m) == -1)
    nxt = np.isclose(r[1:], r_min)[at[:-1]]
    return {"rmax_episodes_per_1000": len(st) * 1000 / max(len(r), 1),
            "rmax_episode_median": float(np.median(en - st)) if len(st) else np.nan,
            "rmax_to_rmin": float(nxt.mean()) if len(nxt) else np.nan,
            "share_mid": float(((r > 2 * r_min + 1e-9) & ~at).mean()) if len(r) else np.nan}


# -- figures --------------------------------------------------------------------------------------------------------------------------------
def figures(R: pd.DataFrame, rl: list[tuple[str, int, str]]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    comp = [(g, sd, r) for g, sd, r in rl if R[(R.run == r)].nav.iloc[0] == "compass"]
    if not comp:
        return
    COL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
    groups = list(dict.fromkeys(g for g, _, _ in comp))
    colour = {g: COL[i % len(COL)] for i, g in enumerate(groups)}
    # radius over time, one row per walk
    fig, axs = plt.subplots(len(comp), 1, figsize=(11, 1.1 * len(comp) + 0.8), sharex=True, squeeze=False)
    for ax, (g, sd, r) in zip(axs[:, 0], comp):
        s = pd.read_parquet(RUNS / r / "steps.parquet")
        ax.semilogy(s.step, s.r_km, color=colour[g], lw=1.0)
        ax.text(0.005, 0.75, r, transform=ax.transAxes, fontsize=7, color="#52514e")
        ax.set_ylim(10, 3000)
        ax.tick_params(labelsize=7)
        ax.spines[["top", "right"]].set_visible(False)
    axs[0, 0].set_title("Radius of the offers (km, log scale) at each step", fontsize=9, loc="left")
    axs[-1, 0].set_xlabel("step")
    fig.tight_layout()
    fig.savefig(OUT / "radius.png", dpi=110)
    plt.close(fig)
    # step lengths: complementary CDF per group, walks pooled
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for g in groups:
        x = np.concatenate([pd.read_parquet(RUNS / r / "steps.parquet").dist_km.to_numpy()[1:] for gg, _, r in comp if gg == g])
        x = np.sort(x[x > 0])
        ax.loglog(x, 1 - np.arange(len(x)) / len(x), color=colour[g], lw=1.6, label=g)
    ax.set_xlabel("step length (km)")
    ax.set_ylabel("share of steps at least this long")
    ax.legend(fontsize=8, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "steplength.png", dpi=110)
    plt.close(fig)
    # recovery per walk
    A = R[(R.phase == "all") & (R.nav == "compass")]
    fig, ax = plt.subplots(figsize=(6.5, 0.35 * len(A) + 1.2))
    y = np.arange(len(A))
    ax.scatter(A.recovery_after_rmax, y, color=[colour[g] for g in A.group], s=30, label="after a step at r_max")
    ax.scatter(A.recovery_after_rmin, y, facecolor="none", edgecolor=[colour[g] for g in A.group], s=30, label="after a step at r_min")
    ax.set_yticks(y, A.run, fontsize=7)
    ax.axvline(0, color="#b5b4ad", lw=0.8)
    ax.set_xlabel("change in d over the next 10 steps")
    ax.legend(fontsize=8, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "recovery.png", dpi=110)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="*", help="run names; their group is the run name")
    a = ap.parse_args()
    rl = [(r, 0, r) for r in a.runs] if a.runs else runs()
    print(f"[readouts] {len(rl)} runs", flush=True)
    ids = np.unique(np.concatenate([pd.read_parquet(RUNS / r / "candidates.parquet", columns=["tile_idx"]).tile_idx.to_numpy() for _, _, r in rl]))
    ts = sheet.tile_stats(ids)
    eye = panel_eye([r for _, _, r in rl])
    rows, places = [], []
    for g, sd, r in rl:
        x, p = readouts(g, sd, r, ts, eye)
        rows += x
        places.append(p)
    R = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    tag = "" if not a.runs else "_check"
    R.to_csv(OUT / f"readouts{tag}.csv", index=False)
    pd.concat(places, ignore_index=True).to_csv(OUT / f"places{tag}.csv", index=False)
    if not a.runs and (R.group == REFERENCE).any():
        E08.paired(R.drop(columns=["nav"]), against=REFERENCE).to_csv(OUT / "paired.csv", index=False)
    if not a.runs:
        figures(R, rl)
    pd.set_option("display.width", 250)
    print(R[R.phase == "all"].T.to_string())


if __name__ == "__main__":
    main()
