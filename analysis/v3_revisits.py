"""Why the v3 walkers keep returning to the same tiles (notes/dreams_v3/reflection_revisits.md).

    python analysis/v3_revisits.py runs/global_baseline_s0 runs/confined_baseline_s0

Per run: revisit and back-step rates, how the signals and the choice change with a candidate's prior visits, and,
with the run's final autoencoder, how far two independent 16-crop looks at the same tile land from each other in
latent space compared with the distance to the 10 nearest other visited tiles.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent import signals as S  # noqa: E402
from agent.model import ConvAE  # noqa: E402

VISIT_BINS = [-1, 0, 1, 3, 10, 30, 10**6]
VISIT_LABELS = ["0", "1", "2-3", "4-10", "11-30", ">30"]


def walk_stats(run: Path) -> None:
    s = pd.read_parquet(run / "steps.parquet")
    c = pd.read_parquet(run / "candidates.parquet")
    t = s.tile_idx.to_numpy()
    seen, rev = set(), np.zeros(len(t), bool)
    for i, x in enumerate(t):
        rev[i] = x in seen
        seen.add(x)
    print(f"  {len(t):,} steps, {len(seen):,} unique tiles, revisit steps {rev.mean():.1%}, A->B->A {np.mean(t[2:] == t[:-2]):.1%}")
    print(f"  grid cells with more than one tile id: {(s.groupby('grid_cell').tile_idx.nunique() > 1).sum()}")

    # at step st the walker stands on t[st-1] and came from t[st-2]
    c = c[(c.kind == "neighbour") & (c.step >= 2)].copy()
    c["C"] = c.step.map(c.groupby("step").size())
    c["came_from"] = c.tile_idx.to_numpy() == t[c.step.to_numpy() - 2]
    counts: dict[int, int] = {}
    prior = np.zeros(len(c), int)
    done = 0
    for k in np.argsort(c.step.to_numpy(), kind="stable"):
        st = int(c.step.iat[k])
        while done < st:
            counts[t[done]] = counts.get(t[done], 0) + 1
            done += 1
        prior[k] = counts.get(int(c.tile_idx.iat[k]), 0)
    c["prior"] = pd.cut(prior, VISIT_BINS, labels=VISIT_LABELS)
    p = c[c.came_from]
    print(f"  came-from tile chosen {p.chosen.mean():.1%} of the time (uniform {np.mean(1 / p.C):.1%}); "
          f"n_z {p.n_z.mean():+.2f} vs {c[~c.came_from].n_z.mean():+.2f} for the other candidates, g_z {p.g_z.mean():+.2f} vs {c[~c.came_from].g_z.mean():+.2f}")
    tab = c.groupby("prior", observed=True).agg(share=("step", "size"), n_raw=("n", "mean"), n_z=("n_z", "mean"), g_z=("g_z", "mean"),
                                                chosen=("chosen", "mean"), uniform=("C", lambda x: np.mean(1 / x)))
    tab["share"] /= len(c)
    print("  candidates by prior visits:\n" + tab.round(3).to_string())
    vc = s.tile_idx.value_counts()
    u = s.drop_duplicates("tile_idx").set_index("tile_idx")
    top = [(int(i), int(vc[i]), round(float(u.lat[i]), 2), round(float(u.lon[i]), 2)) for i in vc.index[:5]]
    print(f"  top tiles (id, visits, lat, lon): {top}; top 20 = {vc.head(20).sum() / len(s):.1%} of steps")
    if "cover" in u:
        print(f"  cover of the top 20: {u.loc[vc.index[:20], 'cover'].value_counts().to_dict()}")


def latent_noise(run: Path) -> None:
    cfg = yaml.safe_load((run / "config.yaml").read_text())
    if cfg.get("world", "regional") == "regional":
        tiles_np = np.load(ROOT / "data" / "tiles.npy", mmap_mode="r")
        get = lambda i: np.asarray(tiles_np[i])  # noqa: E731
    else:
        from data.tile_store import TileStore

        get = TileStore().get_lowres
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = ConvAE().to(dev)
    m.load_state_dict(torch.load(run / "final.pt", map_location=dev)["model"])
    m.eval()
    vc = pd.read_parquet(run / "steps.parquet").tile_idx.value_counts()
    ids = [int(i) for i in vc.index]
    x = torch.from_numpy(np.stack([get(i) for i in ids])).to(dev)
    no_tv = torch.zeros(len(ids), dtype=torch.bool, device=dev)
    g = torch.Generator(device=dev).manual_seed(0)
    K, crop = int(cfg["K"]), int(cfg["crop_px"])
    look = lambda: S.mean_latent(m, S.patches(x.clone(), no_tv, K, crop, g))  # noqa: E731
    z1, z2, z3 = look(), look(), look()
    d = torch.cdist(z3, z1)
    d.fill_diagonal_(float("inf"))
    with torch.no_grad():
        zc = m.encode(S.patches(x.clone(), no_tv, K, crop, g).flatten(0, 1)).view(len(ids), K, -1)
    df = pd.DataFrame({
        "visits": vc.to_numpy(),
        "self_dist": (z1 - z2).norm(dim=1).cpu().numpy(),
        "nn10_other": d.topk(10, largest=False).values.mean(1).cpu().numpy(),
        "crop_spread": zc.std(1).norm(dim=1).cpu().numpy(),
        "pixel_std": [x[i].float().reshape(-1, 3).std(0).mean().item() for i in range(len(ids))],
        "z_norm": z1.norm(dim=1).cpu().numpy(),
    })
    df["visits"] = pd.cut(df.visits, [0, 1, 3, 10, 30, 10**6], labels=["1", "2-3", "4-10", "11-30", ">30"])
    out = df.groupby("visits", observed=True).agg(tiles=("self_dist", "size"), **{k: (k, "mean") for k in df.columns[1:]})
    print("  visited tiles by visit count, final model, two independent looks:\n" + out.round(3).to_string())


def attractor_strip(runs: list[Path], n: int = 6) -> Path:
    """The n most-visited tiles of each v3 run, low-res as the walker saw them, one row per run."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from data.tile_store import TileStore

    store = TileStore()
    fig, axs = plt.subplots(len(runs), n, figsize=(2.2 * n, 2.5 * len(runs)), squeeze=False)
    for row, run in zip(axs, runs):
        s = pd.read_parquet(run / "steps.parquet")
        vc = s.tile_idx.value_counts()
        u = s.drop_duplicates("tile_idx").set_index("tile_idx")
        for ax, t in zip(row, vc.index[:n]):
            ax.imshow(store.get_lowres(int(t)))
            ax.set_title(f"{vc[t]} visits\n{u.lat[t]:.2f}, {u.lon[t]:.2f}", fontsize=8)
            ax.set_xticks([])
            ax.set_yticks([])
        row[0].set_ylabel(run.name, fontsize=9)
    out = ROOT / "notes" / "dreams_v3" / "revisit_attractors.png"
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)
    return out


if __name__ == "__main__":
    runs = list(map(Path, sys.argv[1:]))
    for r in runs:
        print(f"\n== {r.name}")
        walk_stats(r)
        latent_noise(r)
    v3 = [r for r in runs if yaml.safe_load((r / "config.yaml").read_text()).get("world", "regional") != "regional"]
    if v3:
        print(f"\n[v3_revisits] {attractor_strip(v3)}")
