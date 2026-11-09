"""The walker's world-view (brief amendment 2026-11-09, A0-A3): what its encoder comes to know about the Earth, read offline from checkpoints.

    python analysis/e09/worldview.py labels               # A0: WorldCover class fractions for candidate cells -> data/worldcover_cells.parquet
    python analysis/e09/worldview.py probe                # A0: the stratified probe set -> data/probe_cells.parquet (+ results/probe_cells.csv)
    python analysis/e09/worldview.py fetch                # the probe tiles, once, at the walker's 256 px -> data/worldview/probe_tiles.npy
    python analysis/e09/worldview.py run --groups "compass Reference" "compass Null"   # A1, A2 -> results/worldview.csv, worldview.png
    python analysis/e09/worldview.py run --runs e09_ref_s0                             # given runs only

Read-only by construction: it loads saved checkpoints (ckpt_*.pt; step 0 from ckpt_0000.pt, or rebuilt from the walk's init stream if the
walk predates ckpt_init) into a fresh network in eval mode, under no_grad, and never runs alongside walks. Nothing here touches a walk.

Representation: the one the scorer uses for novelty. model.encode (the 64-d latent after the encoder's linear layer) on the tile's K = 16
fixed scoring crops (score_crops: fixed; signals.fixed_offsets, seeded by tile id), crop_px of the walk, area-resized to 32x32, mean over
the K crops (signals.mean_latent), then L2-normalised (normalise_latents: true). Distances between tiles are cosine distances.

Labels: ESA WorldCover 2021 v200, read at overview level 2 (8x: 1/1500 degree, ~74 m north-south) over the cell's footprint, a square of
2 x 5.34 km (1,068 px at 10 m) around the cell centre. Pixels with no WorldCover tile, or nodata (0), count as water (80). Cells south of 60 S
are left out: WorldCover has no Antarctica, and the rule "outside coverage = water" would call the ice sheet sea.

A1, the land-cover probe: multinomial logistic regression (standardised features, class_weight balanced) on the dominant class, ridge
(alpha 1) on the 11 class fractions; out-of-fold over 5 spatial folds (GroupKFold on ~500 km blocks). balanced accuracy, macro-F1, R^2
(variance-weighted). Baselines: the walker's encoder at step 0; colour and texture (per-channel mean and SD over the 16 crops, and the mean
absolute grey-level gradient: 7 numbers); chance (a stratified dummy classifier and the training mean).
A2, geography: Tobler curve, mean cosine distance in 16 log-spaced bins of great-circle distance (10-20,000 km) over a fixed pair set: 50,000
random pairs plus every cell's 10 nearest cells on the ground (random pairs alone leave the bins under ~200 km empty); bins with fewer
than 30 pairs dropped. tobler_rho: Spearman rho between embedding and ground distance, on the random pairs only. plateau_km: the lower edge
of the first bin from which every populated bin lies within 5 % of the far mean (pairs beyond 10,000 km). knn_geo_excess: per cell, the
share of its 10 nearest embedding neighbours within 500 km, minus the share of all other probe cells within 500 km; mean over cells.
B2: probe_spread, the mean pairwise cosine distance of the probe set; probe_spread_rel, the same over its value at step 0. The collapse
flag uses the absolute spread: the untrained network is itself nearly collapsed (0.001-0.020), so the ratio to step 0 ranges from 23 to
1,400 in healthy walks and does not separate them from collapsed checkpoints (log 2026-11-09).
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import torch
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from agent import signals as S  # noqa: E402
from agent.model import CH, LATENT, ConvAE  # noqa: E402

RUNS = ROOT / "runs"
DATA = ROOT / "data"
OUT = ROOT / "notes" / "09_compass" / "results"
WC_CELLS = DATA / "worldcover_cells.parquet"
PROBE = DATA / "probe_cells.parquet"
PROBE_TILES = DATA / "worldview" / "probe_tiles.npy"
WC_TILES = DATA / "worldcover_tiles.txt"
WC_BUCKET = "https://esa-worldcover.s3.eu-central-1.amazonaws.com"
WC_URL = WC_BUCKET + "/v200/2021/map/ESA_WorldCover_10m_2021_v200_{}_Map.tif"
CLASSES = [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100]
NAMES = ["tree", "shrub", "grass", "crop", "built", "bare", "snow_ice", "water", "wetland", "mangrove", "moss_lichen"]
OVR, PPD = 2, 1500  # overview level 2 = 8x; pixels per degree at that level (36,000 px per 3 degrees / 8 / 3)
HALF_KM = 5.34  # half the side of a Major TOM tile (1,068 px at 10 m)
SEED = 20261109
N_CAND, N_PROBE = 60000, 5000
BLOCK_DEG = 4.5  # ~500 km spatial blocks
EDGES = np.logspace(1, np.log10(20000), 17)
RNG_STREAMS = ("start", "neighbours", "offers", "landing", "choice", "init", "crops", "replay", "daydream", "compass", "radius")  # as walk.py


# -- A0: labels --------------------------------------------------------------------------------------------------------------------------
def wc_tiles() -> set[str]:
    if not WC_TILES.exists():
        keys, tok = [], None
        while True:
            p = {"list-type": 2, "prefix": "v200/2021/map/"} | ({"continuation-token": tok} if tok else {})
            r = requests.get(WC_BUCKET, params=p, timeout=60).text
            keys += re.findall(r"v200_([NS]\d\d[EW]\d\d\d)_Map\.tif", r)
            m = re.search(r"<NextContinuationToken>(.*?)</NextContinuationToken>", r)
            if not m:
                break
            tok = m.group(1)
        WC_TILES.write_text("\n".join(sorted(set(keys))) + "\n")
    return set(WC_TILES.read_text().split())


def tile_name(la: int, lo: int) -> str:
    return f"{'N' if la >= 0 else 'S'}{abs(la):02d}{'E' if lo >= 0 else 'W'}{abs(lo):03d}"


def footprint(lat: np.ndarray, lon: np.ndarray):
    """Global pixel ranges [r0, r1) x [c0, c1) of each cell's footprint on the overview grid."""
    dlat = HALF_KM / 111.32
    dlon = np.minimum(HALF_KM / (111.32 * np.cos(np.radians(lat))), 10.0)
    r0 = np.round((90 - (lat + dlat)) * PPD).astype(np.int64)
    r1 = np.round((90 - (lat - dlat)) * PPD).astype(np.int64)
    c0 = np.clip(np.round((lon - dlon + 180) * PPD), 0, 360 * PPD).astype(np.int64)
    c1 = np.clip(np.round((lon + dlon + 180) * PPD), 0, 360 * PPD).astype(np.int64)
    return r0, r1, c0, c1


def labels(n: int) -> None:
    import rasterio
    from rasterio.windows import Window

    ix = pd.read_parquet(DATA / "global" / "index.parquet", columns=["idx", "lat", "lon", "cover"])
    keep = ix.lat.to_numpy() >= -60
    rng = np.random.default_rng(SEED)
    cand = np.sort(rng.choice(np.flatnonzero(keep), n, replace=False))
    c = ix.iloc[cand].reset_index(drop=True)
    r0, r1, c0, c1 = footprint(c.lat.to_numpy(), c.lon.to_numpy())
    have = wc_tiles()
    jobs: dict[str, list] = {}
    for i in range(len(c)):
        for la in range(int(np.floor((90 - r1[i] / PPD) / 3)) * 3, int(np.floor((90 - r0[i] / PPD) / 3)) * 3 + 1, 3):
            for lo in range(int(np.floor((c0[i] / PPD - 180) / 3)) * 3, int(np.floor((c1[i] / PPD - 180) / 3)) * 3 + 1, 3):
                name = tile_name(la, lo)
                if name not in have:
                    continue
                tr0, tc0 = (90 - (la + 3)) * PPD, (lo + 180) * PPD  # the tile's origin on the global overview grid
                a, b = max(r0[i], tr0), min(r1[i], tr0 + 3 * PPD)
                e, f = max(c0[i], tc0), min(c1[i], tc0 + 3 * PPD)
                if a < b and e < f:
                    jobs.setdefault(name, []).append((i, Window(e - tc0, a - tr0, f - e, b - a)))
    counts = np.zeros((len(c), 101), np.int64)

    def work(name: str) -> None:
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif", GDAL_HTTP_MULTIRANGE="YES",
                          GDAL_HTTP_MAX_RETRY="5", GDAL_HTTP_RETRY_DELAY="2"):
            with rasterio.open("/vsicurl/" + WC_URL.format(name), overview_level=OVR) as d:
                assert abs(d.res[0] * PPD - 1) < 1e-6, (name, d.res)
                for i, w in jobs[name]:
                    counts[i] += np.bincount(d.read(1, window=w).ravel(), minlength=101)[:101]

    t = time.time()
    print(f"[labels] {len(c)} cells, {len(jobs)} WorldCover tiles to read, {sum(map(len, jobs.values()))} windows", flush=True)
    with ThreadPoolExecutor(16) as ex:
        for k, _ in enumerate(ex.map(work, list(jobs))):
            if k % 200 == 0:
                print(f"[labels] {k}/{len(jobs)} tiles  {time.time() - t:.0f}s", flush=True)
    expected = (r1 - r0) * (c1 - c0)
    counted = counts.sum(1)
    water = counts[:, 80] + counts[:, 0] + (expected - counted)
    frac = np.stack([water if k == 80 else counts[:, k] for k in CLASSES], 1) / expected[:, None]
    out = c.assign(**{f"f_{nm}": frac[:, j] for j, nm in enumerate(NAMES)}, dominant=np.array(NAMES)[frac.argmax(1)],
                   expected_px=expected, outside_px=expected - counted, nodata_px=counts[:, 0])
    out.to_parquet(WC_CELLS, index=False)
    print(f"[labels] {WC_CELLS}: {len(out)} cells in {time.time() - t:.0f}s; overview level {OVR} (1/{PPD} deg); "
          f"{len(have)} WorldCover tiles exist; footprint {expected.mean():.0f} px on average")
    print(out.dominant.value_counts().to_string())


def probe() -> None:
    wc = pd.read_parquet(WC_CELLS)
    vc = wc.dominant.value_counts()
    cap = next(k for k in range(1, int(vc.max()) + 1) if np.minimum(vc.to_numpy(), k).sum() >= N_PROBE)
    rng = np.random.default_rng(SEED + 1)
    parts = [g.iloc[np.sort(rng.choice(len(g), min(len(g), cap), replace=False))] for _, g in wc.groupby("dominant")]
    p = pd.concat(parts).sort_values("idx").reset_index(drop=True)
    p.to_parquet(PROBE, index=False)
    p.to_csv(OUT / "probe_cells.csv", index=False, float_format="%.4f")
    print(f"[probe] {len(p)} cells, cap {cap} per dominant class, seed {SEED + 1}")
    print(p.dominant.value_counts().to_string())


def fetch() -> None:
    from data.tile_store import TileStore

    p = pd.read_parquet(PROBE)
    ids = p.idx.astype(int).tolist()
    store = TileStore()
    arr = np.zeros((len(ids), 256, 256, 3), np.uint8)
    t, missing = time.time(), []
    for a in range(0, len(ids), 200):
        got, dropped, _ = store.get_many(ids[a : a + 200], timeout=900.0)
        missing += dropped
        for j, i in enumerate(ids[a : a + 200]):
            if i in got:
                arr[a + j] = got[i]
        print(f"[fetch] {a + 200}/{len(ids)}  {time.time() - t:.0f}s  missing {len(missing)}", flush=True)
    assert not missing, f"probe tiles could not be fetched: {missing[:20]}"
    PROBE_TILES.parent.mkdir(parents=True, exist_ok=True)
    np.save(PROBE_TILES, arr)
    print(f"[fetch] {PROBE_TILES}: {arr.nbytes / 1e9:.2f} GB in {time.time() - t:.0f}s")


# -- A1, A2 --------------------------------------------------------------------------------------------------------------------------------
class Probe:
    """The probe set with everything that doesn't depend on the walker: labels, folds, ground distances, pairs, baselines per crop_px."""

    def __init__(self) -> None:
        from sklearn.neighbors import BallTree

        self.p = pd.read_parquet(PROBE)
        self.ids = self.p.idx.astype(int).to_numpy()
        self.tiles = np.load(PROBE_TILES, mmap_mode="r")
        self.y = pd.Categorical(self.p.dominant).codes
        self.frac = self.p[[f"f_{nm}" for nm in NAMES]].to_numpy()
        lat, lon = self.p.lat.to_numpy(), self.p.lon.to_numpy()
        band = np.floor((lat + 90) / BLOCK_DEG)
        width = BLOCK_DEG / np.maximum(np.cos(np.radians(band * BLOCK_DEG - 90 + BLOCK_DEG / 2)), 0.1)
        self.groups = band * 1000 + np.floor((lon + 180) / width)
        ll = np.radians(np.c_[lat, lon])
        self.geo = haversine_matrix(ll)
        n = len(lat)
        self.chance_500 = ((self.geo < 500).sum(1) - 1) / (n - 1)
        rng = np.random.default_rng(SEED + 2)
        a, b = rng.integers(0, n, 60000), rng.integers(0, n, 60000)
        ok = a != b
        self.rand = np.c_[a[ok], b[ok]][:50000]
        _, nn = BallTree(ll, metric="haversine").query(ll, k=11)
        near = np.c_[np.repeat(np.arange(n), 10), nn[:, 1:].ravel()]
        self.pairs = np.unique(np.r_[self.rand, np.sort(near, 1)], axis=0)
        self.pairs_geo = self.geo[self.pairs[:, 0], self.pairs[:, 1]]
        self.crops: dict[int, torch.Tensor] = {}
        self.base: dict[int, dict] = {}

    def x(self, crop_px: int, K: int = 16) -> torch.Tensor:
        if crop_px not in self.crops:
            xs = []
            for a in range(0, len(self.ids), 500):
                img = torch.from_numpy(np.array(self.tiles[a : a + 500]))
                ids = self.ids[a : a + 500].tolist()
                xs.append(S.patches(img, torch.zeros(len(ids), dtype=torch.bool), K, crop_px, torch.Generator(),
                                    S.fixed_offsets(ids, K, 256, crop_px, "cpu")).half())
            self.crops[crop_px] = torch.cat(xs)
        return self.crops[crop_px]

    def colour_texture(self, crop_px: int) -> np.ndarray:
        x = self.x(crop_px).float()  # C K 3 32 32
        m = x.mean((1, 3, 4))
        sd = x.permute(0, 2, 1, 3, 4).flatten(2).std(2)
        g = x.mean(2)
        grad = ((g[..., 1:, :] - g[..., :-1, :]).abs().mean((2, 3)) + (g[..., :, 1:] - g[..., :, :-1]).abs().mean((2, 3))).mean(1, keepdim=True)
        return torch.cat([m, sd, grad], 1).numpy()


def haversine_matrix(ll: np.ndarray) -> np.ndarray:
    la, lo = ll[:, 0], ll[:, 1]
    p = np.c_[np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)]
    return (np.arccos(np.clip(p @ p.T, -1, 1)) * 6371.0088).astype(np.float32)


def metrics(P: Probe, f: np.ndarray, unit: bool) -> dict:
    """A1 and A2 on one feature matrix. unit: features are L2-normalised latents (cosine as the walker sees it); else standardised first."""
    from scipy.stats import spearmanr
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.metrics import balanced_accuracy_score, f1_score, r2_score
    from sklearn.model_selection import GroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    pred, rpred = np.zeros_like(P.y), np.zeros_like(P.frac)
    for tr, te in GroupKFold(5).split(f, P.y, P.groups):
        clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, class_weight="balanced"))
        pred[te] = clf.fit(f[tr], P.y[tr]).predict(f[te])
        rpred[te] = make_pipeline(StandardScaler(), Ridge(alpha=1.0)).fit(f[tr], P.frac[tr]).predict(f[te])
    u = f / np.linalg.norm(f, axis=1, keepdims=True) if unit else unit_std(f)
    sim = u @ u.T
    cos = 1 - sim
    d = cos[P.pairs[:, 0], P.pairs[:, 1]]
    curve = []
    for lo, hi in zip(EDGES[:-1], EDGES[1:]):
        m = (P.pairs_geo >= lo) & (P.pairs_geo < hi)
        curve.append((lo, hi, int(m.sum()), float(d[m].mean()) if m.sum() >= 30 else np.nan))
    far = float(d[P.pairs_geo > 10000].mean())
    ok = [(lo, v) for lo, _, _, v in curve if np.isfinite(v)]
    within = [abs(v - far) / far <= 0.05 for _, v in ok]
    plateau = next((ok[k][0] for k in range(len(ok)) if all(within[k:])), np.nan)
    rr = P.rand
    rho = float(spearmanr(cos[rr[:, 0], rr[:, 1]], P.geo[rr[:, 0], rr[:, 1]])[0])
    np.fill_diagonal(sim, -np.inf)
    nn = np.argpartition(-sim, 10, axis=1)[:, :10]
    share = (np.take_along_axis(P.geo, nn, 1) < 500).mean(1)
    n = len(u)
    spread = float(1 - ((u.sum(0) ** 2).sum() - (u**2).sum()) / (n * (n - 1)))
    return {"probe_bacc": balanced_accuracy_score(P.y, pred), "probe_f1": f1_score(P.y, pred, average="macro"),
            "probe_r2": r2_score(P.frac, rpred, multioutput="variance_weighted"), "tobler_rho": rho, "plateau_km": plateau,
            "knn_geo_excess": float((share - P.chance_500).mean()), "probe_spread": spread, "far_mean": far,
            **{f"tobler_{int(lo)}": v for lo, _, _, v in curve}}


def unit_std(f: np.ndarray) -> np.ndarray:
    z = (f - f.mean(0)) / f.std(0).clip(1e-9)
    return z / np.linalg.norm(z, axis=1, keepdims=True).clip(1e-9)


def chance(P: Probe) -> dict:
    from sklearn.dummy import DummyClassifier
    from sklearn.metrics import balanced_accuracy_score, f1_score, r2_score
    from sklearn.model_selection import GroupKFold

    pred, rpred = np.zeros_like(P.y), np.zeros_like(P.frac)
    for tr, te in GroupKFold(5).split(P.frac, P.y, P.groups):
        pred[te] = DummyClassifier(strategy="stratified", random_state=SEED).fit(P.frac[tr], P.y[tr]).predict(P.frac[te])
        rpred[te] = P.frac[tr].mean(0)
    return {"probe_bacc": balanced_accuracy_score(P.y, pred), "probe_f1": f1_score(P.y, pred, average="macro"),
            "probe_r2": r2_score(P.frac, rpred, multioutput="variance_weighted"), "tobler_rho": 0.0, "plateau_km": np.nan, "knn_geo_excess": 0.0}


def init_model(run: str) -> ConvAE:
    """The walk's network at step 0: ckpt_0000.pt if the walk saved it, else rebuilt from its init stream as walk.py seeds it."""
    cfg = yaml.safe_load((RUNS / run / "config.yaml").read_text())
    seed = int(__import__("json").loads((RUNS / run / "meta.json").read_text())["seed"])
    w = float(cfg.get("ae_width", 1.0))
    m = ConvAE(tuple(int(c * w) for c in CH), int(LATENT * w))
    if (RUNS / run / "ckpt_0000.pt").exists():
        m.load_state_dict(torch.load(RUNS / run / "ckpt_0000.pt", map_location="cpu")["model"])
        return m
    if cfg.get("rng_mode", "legacy") == "split":
        ss = dict(zip(RNG_STREAMS, np.random.SeedSequence(seed).spawn(len(RNG_STREAMS))))
        torch.manual_seed(int(ss["init"].generate_state(1)[0]))
    else:
        torch.manual_seed(seed)
    return ConvAE(tuple(int(c * w) for c in CH), int(LATENT * w))


DEV = "mps" if torch.backends.mps.is_available() else "cpu"  # 2 s per checkpoint on MPS against 55 s on the CPU; latents agree to 5e-6


def embed(m: ConvAE, x: torch.Tensor) -> np.ndarray:
    m = m.to(DEV).eval()
    zs = [S.mean_latent(m, x[a : a + 1000].float().to(DEV)).cpu() for a in range(0, len(x), 1000)]
    return torch.cat(zs).numpy()


def run(run_list: list[tuple[str, int, str]]) -> None:
    torch.set_num_threads(8)
    P = Probe()
    path = OUT / "worldview.csv"
    old = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=["run"])
    rows = [r for r in old.to_dict("records") if r["run"] not in {r for _, _, r in run_list}]
    ch = chance(P)
    for g, sd, r in run_list:
        cfg = yaml.safe_load((RUNS / r / "config.yaml").read_text())
        px, K = int(cfg["crop_px"]), int(cfg["K"])
        assert cfg.get("score_crops") == "fixed" and cfg.get("normalise_latents"), r
        x = P.x(px, K)
        if px not in P.base:
            P.base[px] = metrics(P, P.colour_texture(px), unit=False)
        visited = set(pd.read_parquet(RUNS / r / "steps.parquet", columns=["tile_idx"]).tile_idx.astype(int))
        overlap = len(visited & set(P.ids.tolist()))
        cks = sorted((int(p.stem.split("_")[1]), p) for p in (RUNS / r).glob("ckpt_*.pt"))
        steps = [(0, None)] + [c for c in cks if c[0] > 0]
        base0 = None
        for step, p in steps:
            t = time.time()
            if p is None:
                m = init_model(r)
            else:
                m = init_model(r)
                m.load_state_dict(torch.load(p, map_location="cpu")["model"])
            with torch.no_grad():
                f = embed(m, x)
            mt = metrics(P, f, unit=True)
            if step == 0:
                base0 = mt
            row = {"group": g, "seed": sd, "run": r, "crop_px": px, "step": step, **mt,
                   "probe_spread_rel": mt["probe_spread"] / base0["probe_spread"], "probe_overlap": overlap, "sec": time.time() - t}
            for name, b in (("init", base0), ("colour", P.base[px]), ("chance", ch)):
                row.update({f"{name}_{k}": b[k] for k in ("probe_bacc", "probe_f1", "probe_r2", "tobler_rho", "plateau_km", "knn_geo_excess")})
            rows.append(row)
            print(f"[worldview] {r} step {step}: bacc {mt['probe_bacc']:.3f} (colour {P.base[px]['probe_bacc']:.3f}, init {base0['probe_bacc']:.3f})"
                  f"  rho {mt['tobler_rho']:.3f}  plateau {mt['plateau_km']:.0f}  knn {mt['knn_geo_excess']:+.3f}  spread {row['probe_spread_rel']:.2f}"
                  f"  {row['sec']:.0f}s", flush=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    plot(pd.DataFrame(rows))


def plot(w: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ks = [("probe_bacc", "land-cover probe, balanced accuracy"), ("probe_r2", "class fractions, R²"), ("tobler_rho", "Tobler ρ (embedding ~ ground)"),
          ("plateau_km", "plateau distance (km)"), ("knn_geo_excess", "neighbours within 500 km, beyond chance"), ("probe_spread", "probe spread (mean cosine distance)")]
    fig, axs = plt.subplots(2, 3, figsize=(15, 8.5))
    cols = plt.get_cmap("tab10").colors
    for ax, (k, title) in zip(axs.flat, ks):
        for j, (g, d) in enumerate(w.groupby("group", sort=False)):
            mm = d.groupby("step")[k].agg(["mean", "min", "max"])
            ax.plot(mm.index, mm["mean"], color=cols[j % 10], lw=2, label=g)
            ax.fill_between(mm.index, mm["min"], mm["max"], color=cols[j % 10], alpha=0.15, lw=0)
            if f"colour_{k}" in d:
                ax.axhline(d[f"colour_{k}"].iloc[0], color=cols[j % 10], ls=":", lw=1)
        if f"chance_{k}" in w and np.isfinite(w[f"chance_{k}"].iloc[0]):
            ax.axhline(w[f"chance_{k}"].iloc[0], color="grey", ls="--", lw=1)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("step")
    axs[0, 0].legend(fontsize=8)
    fig.suptitle("The walker's world-view on the 5,000 probe cells (dotted: colour and texture baseline, per eye; dashed: chance)", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "worldview.png", dpi=110)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("labels").add_argument("--n", type=int, default=N_CAND)
    sub.add_parser("probe")
    sub.add_parser("fetch")
    r = sub.add_parser("run")
    r.add_argument("--groups", nargs="*", default=[])
    r.add_argument("--runs", nargs="*", default=[])
    sub.add_parser("plot")
    a = ap.parse_args()
    if a.cmd == "labels":
        labels(a.n)
    elif a.cmd == "probe":
        probe()
    elif a.cmd == "fetch":
        fetch()
    elif a.cmd == "plot":
        plot(pd.read_csv(OUT / "worldview.csv"))
    else:
        sys.path.insert(0, str(ROOT / "analysis" / "e09"))
        from readouts import GROUPS

        rl = [(g, int(p.name.rsplit("_s", 1)[1]), p.name) for g in a.groups for p in sorted(RUNS.glob(f"{GROUPS[g]}_s[0-9]"))
              if (p / "final.pt").exists()]
        by_stem = {v: g for g, v in GROUPS.items() if isinstance(v, str)}
        rl += [(by_stem.get(r.rsplit("_s", 1)[0], "given"), int(r.rsplit("_s", 1)[1]), r) for r in a.runs]
        run(rl)


if __name__ == "__main__":
    main()
