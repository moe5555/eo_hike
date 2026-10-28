"""Dreams v3 report: contact sheets, home vs dream, dream origins, reference sheet, search strips (+ MP4),
memorisation check and dreams.parquet.

    python -m gen.dreams_v3_report runs/global_baseline_s0 runs/confined_baseline_s0

Reads the searches written by gen/dream_search.py (A, B, A0 under the global run, C under the confined run),
the plain samples in <global run>/dreams_v3/reference/, and the GAN training sets in data/v3/.
Everything is written to <global run>/dreams_v3/.

Choices made here (not fixed by the brief):
- "Top 8 dreams" of a (condition, R) cell = the final-generation elites of the 3 search seeds taken round-robin
  by rank (rank 0 of seeds 0, 1, 2, then rank 1, ...), because F is z-scored within a search and not comparable
  across seeds.
- Nearest real crop: pixel L2 at 64 px (4x area-downsampled, uint8 scale) against the dreamer's own training set
  (agent_path for A and A0, base_global for B and C). nn_train_dist is the RMS per pixel-channel (0..255).
  Computed for every final elite; NaN for the earlier generations in dreams.parquet.
- Dream origins: distance from the nn crop's tile to the nearest tile on the searching agent's own path (km),
  the same measure for B (global walker) and C (confined walker).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.global_index import world_axes  # noqa: E402

V3 = ROOT / "data" / "v3"
RS = [0.7, 1.0, 1.5, 2.0, 3.0]
CONDS = ["A", "B", "C"]
TRAIN_SET = {"A": "agent", "A0": "agent", "B": "base", "C": "base"}
TOP = 8
TH = 128  # thumbnail px on the sheets


def search_root(cond: str, g: Path, c: Path) -> Path:
    return (c if cond == "C" else g) / "dreams_v3" / "search"


def load_elites(root: Path, cond: str, beta: float) -> dict:
    """{(R, seed): elites.npz contents} for one condition and beta."""
    out = {}
    d = root / f"{cond}_b{beta:g}"
    for p in sorted(d.glob("R*_s*/elites.npz")):
        R, s = p.parent.name[1:].split("_s")
        out[(float(R), int(s))] = dict(np.load(p))
    return out


def top8(el: dict, R: float) -> np.ndarray:
    seeds = sorted(s for (r, s) in el if r == R)
    if not seeds:
        return np.zeros((0, 256, 256, 3), np.uint8)
    rows = [el[(R, s)]["img"] for s in seeds]
    pick = [rows[k % len(rows)][k // len(rows)] for k in range(TOP)]
    return np.stack(pick)


def thumb(a: np.ndarray, px: int = TH) -> np.ndarray:
    return np.asarray(Image.fromarray(a).resize((px, px), Image.Resampling.BOX))


def canvas_grid(cells: list[list[np.ndarray]], px: int = TH, gap: int = 4, group_gap: int = 24) -> np.ndarray:
    """cells[row][group] = [n, H, W, 3] images -> one canvas, groups separated by a wider gap."""
    n_g = len(cells[0])
    per = max(len(x) for row in cells for x in row)
    gw = per * (px + gap)
    W = n_g * gw + (n_g - 1) * group_gap
    H = len(cells) * (px + gap)
    can = np.full((H, W, 3), 255, np.uint8)
    for r, row in enumerate(cells):
        for g, imgs in enumerate(row):
            for k, a in enumerate(imgs):
                x0 = g * (gw + group_gap) + k * (px + gap)
                can[r * (px + gap) : r * (px + gap) + px, x0 : x0 + px] = thumb(a, px)
    return can


def labelled(can: np.ndarray, out: Path, title: str, row_labels: list[str], col_labels: list[str], px: int = TH, gap: int = 4, group_gap: int = 24, per: int = TOP) -> None:
    H, W = can.shape[:2]
    fig = plt.figure(figsize=((W + 140) / 100, (H + 90) / 100), dpi=100)
    ax = fig.add_axes([140 / (W + 140), 0, W / (W + 140), H / (H + 90)])
    ax.imshow(can, interpolation="nearest")
    ax.set_axis_off()
    for r, lab in enumerate(row_labels):
        fig.text(0.005, 1 - (90 + r * (px + gap) + px / 2) / (H + 90), lab, fontsize=11, va="center")
    gw = per * (px + gap)
    for g, lab in enumerate(col_labels):
        fig.text((140 + g * (gw + group_gap) + gw / 2) / (W + 140), 1 - 70 / (H + 90), lab, fontsize=12, ha="center", weight="bold")
    fig.text(0.005, 1 - 25 / (H + 90), title, fontsize=13)
    fig.savefig(out, dpi=100)
    plt.close(fig)


# -- nearest neighbours ---------------------------------------------------------------------------------
class NN:
    def __init__(self, which: str, g: Path, dev: str) -> None:
        d = V3 / g.name / "agent_path" if which == "agent" else V3 / "base_global"
        self.crops = pd.read_parquet(d / "crops.parquet")
        self.small = np.load(d / "small64.npy", mmap_mode="r")
        self.dev = dev
        self.T = torch.from_numpy(np.ascontiguousarray(self.small)).to(dev).flatten(1).half()
        self.T2 = (self.T.float() ** 2).sum(1)

    def query(self, imgs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        q = np.stack([thumb(a, 64) for a in imgs])
        Q = torch.from_numpy(q).to(self.dev).flatten(1).float()
        best_d = torch.full((len(Q),), float("inf"), device=self.dev)
        best_i = torch.zeros(len(Q), dtype=torch.long, device=self.dev)
        for s in range(0, len(self.T), 8192):
            Tc = self.T[s : s + 8192].float()
            d2 = (Q**2).sum(1, keepdim=True) + self.T2[s : s + 8192][None] - 2 * Q @ Tc.T
            v, i = d2.min(1)
            upd = v < best_d
            best_d[upd], best_i[upd] = v[upd], i[upd] + s
        rms = (best_d.clamp(min=0) / Q.shape[1]).sqrt()
        return rms.cpu().numpy(), best_i.cpu().numpy()


def path_tiles(run: Path) -> pd.DataFrame:
    s = pd.read_parquet(run / "steps.parquet", columns=["tile_idx", "lat", "lon"])
    return s.drop_duplicates("tile_idx")


def km_to_path(lat: np.ndarray, lon: np.ndarray, path: pd.DataFrame) -> np.ndarray:
    from sklearn.neighbors import BallTree

    from data.tile_store import EARTH_R_KM

    t = BallTree(np.radians(path[["lat", "lon"]].to_numpy()), metric="haversine")
    return t.query(np.radians(np.stack([lat, lon], 1)), k=1)[0][:, 0] * EARTH_R_KM


# -- outputs -------------------------------------------------------------------------------------------
def main_sheets(g: Path, c: Path, out: Path, beta: float) -> None:
    el = {k: load_elites(search_root(k, g, c), k, beta) for k in CONDS + ["A0"]}
    rows = [[top8(el[k], R) for k in CONDS] for R in RS]
    can = canvas_grid(rows)
    labelled(can, out / f"contact_sheet_main_b{beta:g}.png", f"Top {TOP} dreams per reach R (rows) and condition (columns); beta = {beta:g}; same search seeds",
             [f"R = {R:g}" for R in RS], ["A  global walker x own fine-tuned dreamer", "B  global walker x shared base", "C  confined walker x shared base"])
    rows = [[top8(el[k], R) for k in ["A", "A0"]] for R in RS]
    labelled(canvas_grid(rows), out / f"contact_sheet_A_vs_A0_b{beta:g}.png", f"A (fine-tuned dreamer) beside A0 (from-scratch dreamer); beta = {beta:g}",
             [f"R = {R:g}" for R in RS], ["A  agent_finetune", "A0  agent_scratch"])


def home_vs_dream(g: Path, c: Path, out: Path, beta: float) -> None:
    from data.tile_store import TileStore

    store = TileStore()
    p = path_tiles(c)
    rng = np.random.default_rng(0)
    ids = rng.choice(p.tile_idx.to_numpy(), 16, replace=False)
    home = []
    for t in ids:
        h = store.get_hires(int(t))
        y, x = rng.integers(0, h.shape[0] - 256 + 1), rng.integers(0, h.shape[1] - 256 + 1)
        home.append(h[y : y + 256, x : x + 256])
    el = load_elites(search_root("C", g, c), "C", beta)
    rows = [[np.stack(home[:8]), top8(el, RS[0])], [np.stack(home[8:]), top8(el, RS[1])]] + [[np.zeros((0, 256, 256, 3), np.uint8), top8(el, R)] for R in RS[2:]]
    labelled(canvas_grid(rows), out / f"home_vs_dream_C_b{beta:g}.png",
             f"C: 16 random 10 m crops from the confined walker's path (left) and its top dreams through the shared base (right); beta = {beta:g}",
             ["home | R = 0.7", "home | R = 1.0"] + [f"R = {R:g}" for R in RS[2:]], ["home (confined path, 10 m)", "C dreams"])


def origins(g: Path, c: Path, out: Path, beta: float, nn_base: NN) -> dict:
    res, fig = {}, plt.figure(figsize=(20, 6.2))
    for k, (cond, run) in enumerate([("B", g), ("C", c)]):
        el = load_elites(search_root(cond, g, c), cond, beta)
        rows = []
        for (R, s), e in el.items():
            dist, ii = nn_base.query(e["img"])
            cr = nn_base.crops.iloc[ii]
            rows.append(pd.DataFrame({"R": R, "seed": s, "rank": np.arange(len(ii)), "nn_dist": dist, "lat": cr.lat.to_numpy(), "lon": cr.lon.to_numpy(), "tile": cr.tile_idx.to_numpy()}))
        df = pd.concat(rows, ignore_index=True)
        df["km_from_path"] = km_to_path(df.lat.to_numpy(), df.lon.to_numpy(), path_tiles(run))
        idx = pd.read_parquet(ROOT / "data" / "global" / "index.parquet", columns=["cover"])
        df["cover"] = idx.cover.to_numpy()[df.tile.to_numpy()]
        res[cond] = {
            "n": len(df), "km_from_own_path_median": round(float(df.km_from_path.median())), "km_from_own_path_mean": round(float(df.km_from_path.mean())),
            "by_R_median_km": df.groupby("R").km_from_path.median().round().to_dict(), "nn_cover_share": df.cover.value_counts(normalize=True).round(3).to_dict(),
            "unique_nn_tiles": int(df.tile.nunique()),
        }
        ax = fig.add_subplot(1, 2, k + 1)
        world_axes(ax, f"{cond}: where its dreams come from (nearest base_global crop), n = {len(df)}; median {res[cond]['km_from_own_path_median']:,} km from its own path")
        p = path_tiles(run)
        ax.scatter(p.lon, p.lat, s=2, c="k", lw=0, label="its path")
        sc = ax.scatter(df.lon + np.random.default_rng(0).normal(0, 0.6, len(df)), df.lat + np.random.default_rng(1).normal(0, 0.6, len(df)),
                        c=np.log(df.R), cmap="plasma", s=14, alpha=0.8, lw=0)
        ax.legend(loc="lower left", fontsize=8)
        df.to_parquet(out / f"origins_{cond}_b{beta:g}.parquet")
    cb = fig.colorbar(sc, ax=fig.axes, fraction=0.015, ticks=np.log(RS))
    cb.ax.set_yticklabels([f"R {R:g}" for R in RS])
    fig.savefig(out / f"dream_origins_B_vs_C_b{beta:g}.png", dpi=110)
    plt.close(fig)
    (out / f"dream_origins_b{beta:g}.json").write_text(json.dumps(res, indent=2))
    return res


def reference_sheet(g: Path, out: Path) -> None:
    ref = g / "dreams_v3" / "reference"
    tags = ["base", "agent_scratch", "agent_finetune"]
    cells = []
    for t in tags:
        p = ref / f"plain_{t}.npz"
        cells.append(np.load(p)["img"] if p.exists() else np.zeros((0, 256, 256, 3), np.uint8))
    rows = [[x[r * 8 : (r + 1) * 8] for x in cells] for r in range(8)]
    labelled(canvas_grid(rows, px=96), out / "reference_sheet.png", "Plain samples, psi = 1.0, seeds 0-63 (no search)", [""] * 8, tags, px=96)


def strips(g: Path, c: Path, out: Path, beta: float) -> None:
    import imageio.v2 as imageio

    sd = out / "strips"
    sd.mkdir(exist_ok=True)
    for cond in CONDS + ["A0"]:
        root = search_root(cond, g, c) / f"{cond}_b{beta:g}"
        for R in RS:
            rows = []
            for s in range(3):
                d = root / f"R{R:g}_s{s}"
                frames = [np.asarray(Image.open(p).convert("RGB")) for p in sorted(d.glob("best_*.png"))]
                if not frames:
                    continue
                rows.append([np.stack(frames)])
                with imageio.get_writer(sd / f"{cond}_b{beta:g}_R{R:g}_s{s}.mp4", fps=6, codec="libx264", quality=9, macro_block_size=16) as w:
                    for f in frames:
                        w.append_data(f)
            if rows:
                labelled(canvas_grid(rows, px=96, gap=2), sd / f"{cond}_b{beta:g}_R{R:g}.png", f"{cond}, R = {R:g}, beta = {beta:g}: the best image of each of 30 generations",
                         [f"seed {s}" for s in range(len(rows))], [""], px=96, gap=2, per=30)


def memorisation(g: Path, c: Path, out: Path, beta: float, nns: dict) -> pd.DataFrame:
    """Every kept dream beside its nearest training crop; returns nn columns for dreams.parquet."""
    recs = []
    for cond in CONDS + ["A0"]:
        el = load_elites(search_root(cond, g, c), cond, beta)
        nn = nns[TRAIN_SET[cond]]
        pairs = []
        for (R, s), e in sorted(el.items()):
            dist, ii = nn.query(e["img"])
            cr = nn.crops.iloc[ii]
            for r in range(len(ii)):
                recs.append({"condition": cond, "beta": beta, "R": R, "seed": s, "rank": r, "nn_train_dist": float(dist[r]),
                             "nn_lat": float(cr.lat.iloc[r]), "nn_lon": float(cr.lon.iloc[r]), "nn_tile": int(cr.tile_idx.iloc[r]), "nn_crop": int(ii[r])})
                pairs.append(np.stack([e["img"][r], np.asarray(Image.fromarray(np.asarray(nn.small[ii[r]])).resize((256, 256), Image.Resampling.NEAREST))]))
        if not pairs:
            continue
        per_row = 8
        rows = [[np.concatenate(pairs[i : i + per_row])] for i in range(0, len(pairs), per_row)]
        labelled(canvas_grid(rows, px=64, gap=2), out / f"memorisation_{cond}_b{beta:g}.png",
                 f"{cond}: every kept dream (left of each pair) beside its nearest {TRAIN_SET[cond]} training crop (pixel L2 at 64 px); rows ordered R 0.7 -> 3.0, seed, rank",
                 [""] * len(rows), [""], px=64, gap=2, per=2 * per_row)
    return pd.DataFrame(recs)


def table(g: Path, c: Path, out: Path, betas: list[float], nn_df: pd.DataFrame) -> None:
    logs = []
    for cond in CONDS + ["A0"]:
        for beta in betas:
            for p in sorted((search_root(cond, g, c) / f"{cond}_b{beta:g}").glob("R*_s*/log.parquet")):
                logs.append(pd.read_parquet(p))
    df = pd.concat(logs, ignore_index=True)
    last = df.generation == df.generation.max()
    df = df.merge(nn_df, on=["condition", "beta", "R", "seed", "rank"], how="left")
    for col in ("nn_train_dist", "nn_lat", "nn_lon", "nn_tile", "nn_crop"):
        df.loc[~last, col] = np.nan
    cols = ["condition", "agent", "gan", "beta", "R", "seed", "generation", "rank", "F", "g", "d", "dist_from_w_avg", "dist_rel",
            "pop_mean_dist_from_w_avg", "pop_mean_dist_rel", "nn_train_dist", "nn_lat", "nn_lon", "nn_tile", "nn_crop", "id", "gan_pkl", "w"]
    df[cols].to_parquet(out / "dreams.parquet")
    summ = df[last].groupby(["condition", "beta", "R"]).agg(g_mean=("g", "mean"), g_max=("g", "max"), d_mean=("d", "mean"), dist_rel=("dist_rel", "mean"), nn_rms=("nn_train_dist", "mean"), nn_rms_min=("nn_train_dist", "min"))
    summ.round(5).to_csv(out / "dreams_summary.csv")
    print(summ.round(4).to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("global_run", type=Path)
    ap.add_argument("confined_run", type=Path)
    ap.add_argument("--betas", type=float, nargs="+", default=[0.3, 0.0])
    a = ap.parse_args()
    g, c = a.global_run, a.confined_run
    out = g / "dreams_v3"
    out.mkdir(parents=True, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    nns = {"agent": NN("agent", g, dev), "base": NN("base", g, dev)}
    reference_sheet(g, out)
    nn_all = []
    for beta in a.betas:
        main_sheets(g, c, out, beta)
        home_vs_dream(g, c, out, beta)
        print(json.dumps(origins(g, c, out, beta, nns["base"]), indent=2))
        strips(g, c, out, beta)
        nn_all.append(memorisation(g, c, out, beta, nns))
    table(g, c, out, a.betas, pd.concat(nn_all, ignore_index=True))
    print(f"[dreams_v3_report] -> {out}")
