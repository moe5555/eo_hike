"""Does the agent's latent space follow geography? Twins far apart, neighbours that are strangers.

    python analysis/latent_vs_geo.py runs/baseline_s0

Every non-TV tile is embedded with the run's final encoder, the same way the agent sees a tile
during the walk (mean latent over crops at the run's crop_px; 64 fixed crops here, not 16 random).
Pairs are scored by rank: score = geo-distance percentile - latent-distance percentile.

- Twins: the 10 pairs with the highest score (latent-close, geographically far).
- Strangers: among geographic neighbours (<= 15 km), the 10 pairs furthest apart in latent space.
Each tile appears in at most one pair per panel.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import yaml
from scipy.stats import rankdata, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data"))
from agent import signals as S  # noqa: E402
from agent.model import ConvAE  # noqa: E402
from prepare import haversine_km  # noqa: E402

N_PAIRS, N_CROPS, NEIGH_KM = 10, 64, 15.0


@torch.no_grad()
def embed(run: Path, dev: str) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    cfg = yaml.safe_load((run / "config.yaml").read_text())
    idx = pd.read_parquet(ROOT / "data" / "tiles.parquet")
    tiles_np = np.load(ROOT / "data" / "tiles.npy")
    tiles = torch.from_numpy(tiles_np).to(dev)
    tv = torch.from_numpy(idx.tv.to_numpy().copy()).to(dev)
    model = ConvAE().to(dev)
    model.load_state_dict(torch.load(run / "final.pt", map_location=dev)["model"])
    model.eval()
    gen = torch.Generator(device=dev).manual_seed(0)
    keep = np.flatnonzero(~idx.tv.to_numpy())
    ids = torch.from_numpy(keep).to(dev)
    z = torch.cat([S.mean_latent(model, S.patches(tiles, ids[i : i + 128], tv, N_CROPS, int(cfg["crop_px"]), gen)) for i in range(0, len(ids), 128)])
    return idx.iloc[keep].reset_index(drop=True), z.cpu().numpy(), tiles_np[keep]


def greedy(order: np.ndarray, I: np.ndarray, J: np.ndarray, n: int) -> list[tuple[int, int]]:
    used, out = set(), []
    for p in order:
        a, b = int(I[p]), int(J[p])
        if a in used or b in used:
            continue
        used |= {a, b}
        out.append((a, b))
        if len(out) == n:
            break
    return out


def main() -> None:
    run = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "runs" / "baseline_s0"
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    idx, z, img = embed(run, dev)
    visited = set(pd.read_parquet(run / "steps.parquet").tile_idx.tolist())
    orig = idx["idx"].to_numpy() if "idx" in idx else idx.index.to_numpy()
    seen = np.array([o in visited for o in orig])
    lat, lon = idx.lat.to_numpy(), idx.lon.to_numpy()

    I, J = np.triu_indices(len(z), 1)
    dz = np.linalg.norm(z[I] - z[J], axis=1)
    dg = haversine_km(lat[I], lon[I], lat[J], lon[J])
    pz, pg = rankdata(dz) / len(dz), rankdata(dg) / len(dg)
    rho = spearmanr(dz, dg).statistic

    twins = greedy(np.argsort(-(pg - pz)), I, J, N_PAIRS)
    near = np.flatnonzero(dg <= NEIGH_KM)
    strangers = greedy(near[np.argsort(-dz[near])], I, J, N_PAIRS)
    pair_of = {(int(a), int(b)): p for p, (a, b) in enumerate(zip(I, J))}

    def info(a, b):
        p = pair_of[(min(a, b), max(a, b))]
        return dg[p], pz[p] * 100

    # -- figure ---------------------------------------------------------------------------
    fig = plt.figure(figsize=(26, 22), facecolor="white", layout="constrained")
    sf = fig.subfigures(3, 1, height_ratios=[0.85, 0.85, 1.1], hspace=0.04)
    run_name = run.name
    fig.suptitle(f"How {run_name}'s self-grown latent space lines up with geography", fontsize=26)

    def panel(sub, pairs, title, colour):
        sub.suptitle(title, fontsize=19, x=0.01, ha="left", color=colour)
        axs = sub.subplots(2, 5)
        for k, (a, b) in enumerate(pairs):
            ax = axs.flat[k]
            pair_img = np.concatenate([img[a], np.full((256, 8, 3), 255, np.uint8), img[b]], axis=1)
            ax.imshow(pair_img)
            ax.set_xticks([]), ax.set_yticks([])
            for s in ax.spines.values():
                s.set_edgecolor(colour), s.set_linewidth(3)
            km, zp = info(a, b)
            mark = lambda t: "" if seen[t] else "*"
            ax.set_title(f"#{k + 1}  {km:.0f} km apart · latent pct {zp:.1f}", fontsize=12.5)
            ax.set_xlabel(f"{lat[a]:.2f}N {lon[a]:.2f}E{mark(a)}   |   {lat[b]:.2f}N {lon[b]:.2f}E{mark(b)}", fontsize=10.5)

    panel(sf[0], twins, "Latent twins, far apart: closest in the agent's latent space relative to their geographic distance", "#1f6fb4")
    panel(sf[1], strangers, f"Neighbours, latent strangers: adjacent tiles (≤ {NEIGH_KM:.0f} km) furthest apart in latent space", "#c0392b")

    bot = sf[2].subplots(1, 2, width_ratios=[1.25, 1])
    ax = bot[0]
    ax.scatter(lon, lat, s=7, c=np.where(seen, "#999999", "#dddddd"), zorder=1)
    for k, (a, b) in enumerate(twins):
        ax.plot([lon[a], lon[b]], [lat[a], lat[b]], c="#1f6fb4", lw=1.6, alpha=0.8, zorder=2)
        ax.scatter([lon[a], lon[b]], [lat[a], lat[b]], s=40, c="#1f6fb4", zorder=3)
        ax.annotate(str(k + 1), ((lon[a] + lon[b]) / 2, (lat[a] + lat[b]) / 2), fontsize=11, color="#1f6fb4", weight="bold",
                    ha="center", va="center", bbox=dict(boxstyle="circle,pad=0.15", fc="white", ec="none"), zorder=4)
    for k, (a, b) in enumerate(strangers):
        ax.scatter([lon[a], lon[b]], [lat[a], lat[b]], s=55, marker="s", c="#c0392b", zorder=3)
        ax.annotate(str(k + 1), (lon[a], lat[a]), xytext=(6, 4), textcoords="offset points", fontsize=11, color="#c0392b", weight="bold", zorder=4)
    ax.set_aspect(1 / np.cos(np.deg2rad(lat.mean())))
    ax.set_xlabel("lon"), ax.set_ylabel("lat")
    ax.set_title("Where they are. Blue: twins (lines join pairs). Red: strangers. Dark grey: tiles the agent visited", fontsize=14, loc="left")

    ax = bot[1]
    rng = np.random.default_rng(0)
    sub = rng.choice(len(dz), min(40000, len(dz)), replace=False)
    ax.scatter(dg[sub], dz[sub], s=2, c="#bbbbbb", alpha=0.4, rasterized=True)
    bins = np.linspace(0, dg.max(), 25)
    mid, med = (bins[1:] + bins[:-1]) / 2, [np.median(dz[(dg >= lo) & (dg < hi)]) if ((dg >= lo) & (dg < hi)).any() else np.nan for lo, hi in zip(bins[:-1], bins[1:])]
    ax.plot(mid, med, c="black", lw=2, label="median latent distance")
    for pairs, col, m in ((twins, "#1f6fb4", "o"), (strangers, "#c0392b", "s")):
        ps = [pair_of[(min(a, b), max(a, b))] for a, b in pairs]
        ax.scatter(dg[ps], dz[ps], c=col, s=60, marker=m, edgecolor="white", zorder=3)
    ax.set_xlabel("geographic distance (km)"), ax.set_ylabel("latent distance")
    ax.set_title(f"All {len(dz):,} tile pairs (40k shown). Spearman ρ = {rho:.2f}", fontsize=14, loc="left")
    ax.legend(loc="upper right")

    fig.text(0.01, -0.01, f"Encoder: {run_name}/final.pt; tile latent = mean over {N_CROPS} crops at the run's crop size. "
             f"{len(z)} tiles (noisy-TV cells excluded); * = never visited on the walk. "
             "latent pct = percentile of the pair's latent distance among all pairs (0 = closest).", fontsize=11, color="#555555")
    out = ROOT / "notes" / "img" / f"latent_vs_geo_{run_name}.png"
    fig.savefig(out, dpi=80, bbox_inches="tight")
    print(f"rho={rho:.3f}  -> {out}")
    for name, pairs in (("twins", twins), ("strangers", strangers)):
        for k, (a, b) in enumerate(pairs):
            km, zp = info(a, b)
            print(f"{name} #{k + 1}: {km:.0f} km, latent pct {zp:.2f}, seen {seen[a]}/{seen[b]}")


if __name__ == "__main__":
    main()
