"""What the walker's network draws: the real tile next to its drawing, at several ages of one walk. Offline apart from any tile missing from the cache.

    python analysis/h0111/drawings.py

Checks first that the rebuilt networks and held-out crops give the logged held-out error. Then writes to notes/07_film_arc/results/drawings/:
drawings_never_seen.png, drawings_walked.png (a tile cut into its 4x4 grid of 64 px crops, each drawn separately, so seams are the
network's), drawings_baselines.csv (the network against one flat colour per crop and against PCA with as many numbers as the latent),
drawings_seen_vs_unseen.csv (tiles visited during a stay against neighbours offered there and never visited in the whole walk).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import torch
import yaml
from common import OUT, RUNS, places, steps
from PIL import Image, ImageDraw, ImageFont

from agent import signals as S
from agent.model import LATENT, ConvAE
from agent.walk import HELDOUT_N, HELDOUT_SEED, RNG_STREAMS
from data.tile_store import TileStore

RUN = "h2910_bored_paris_s0"
K, CROP = 16, 64
AGES = (0, 19, 65, 250, 1000, 5000)  # step 0 is the untrained network; every other age is a checkpoint saved by the walk
MIN_STAY = 60
DIR = OUT / "drawings"
SCALE = 2
PAD = 6
FONT = ImageFont.load_default(size=13)


def net(run: str, step: int) -> ConvAE:
    """The walk's network after `step` steps. Step 0 repeats the walk's seeding, which the held-out check confirms."""
    cfg = yaml.safe_load((RUNS / run / "config.yaml").read_text())
    if cfg.get("rng_mode", "legacy") == "split":
        ss = dict(zip(RNG_STREAMS, np.random.SeedSequence(int(cfg["seed"])).spawn(len(RNG_STREAMS))))
        torch.manual_seed(int(ss["init"].generate_state(1)[0]))
    else:
        torch.manual_seed(int(cfg["seed"]))
    m = ConvAE().eval()
    if step:
        p = RUNS / run / f"ckpt_{step:04d}.pt"
        p = p if p.exists() else RUNS / run / f"bored_{step:04d}.pt"
        m.load_state_dict(torch.load(p, weights_only=True)["model"])
    return m


def saved_steps(run: str) -> np.ndarray:
    """Steps with saved weights. A bored_NNNN.pt is saved after the update of step NNNN, so it holds NNNN + 1 updates; ckpt_NNNN.pt holds NNNN."""
    ck = [int(p.stem[5:]) for p in (RUNS / run).glob("ckpt_*.pt")]
    return np.sort(ck)


def heldout_set(store: TileStore) -> tuple[list[int], torch.Tensor]:
    ids = np.sort(np.random.default_rng(HELDOUT_SEED).choice(np.arange(store.N), HELDOUT_N, replace=False)).tolist()
    arrs, dropped, _ = store.get_many(ids, timeout=600.0)
    assert not dropped, dropped
    img = torch.from_numpy(np.stack([arrs[i] for i in ids]))
    return ids, S.patches(img, torch.zeros(len(ids), dtype=torch.bool), K, CROP, torch.Generator().manual_seed(HELDOUT_SEED))


def scoring_crops(store: TileStore, ids: list[int]) -> tuple[list[int], torch.Tensor]:
    """The walker's fixed scoring crops, for tiles already in the cache only."""
    ids = [i for i in map(int, ids) if store.cached(i)]
    img = torch.from_numpy(np.stack([store.get_lowres(i) for i in ids]))
    return ids, S.patches(img, torch.zeros(len(ids), dtype=torch.bool), K, CROP, torch.Generator(), S.fixed_offsets(ids, K, img.shape[1], CROP, "cpu"))


def grid_crops(a: np.ndarray) -> torch.Tensor:
    """A 256 px tile as its 4x4 grid of crops, at the network's 32 px: [16, 3, 32, 32]."""
    x = torch.from_numpy(a.copy()).permute(2, 0, 1)[None].float() / 255.0
    return torch.nn.functional.avg_pool2d(x, CROP // S.IN_PX).unfold(2, S.IN_PX, S.IN_PX).unfold(3, S.IN_PX, S.IN_PX).permute(0, 2, 3, 1, 4, 5).flatten(0, 2)


def mosaic(x: torch.Tensor) -> np.ndarray:
    """[16, 3, 32, 32] in [0, 1] -> 128 x 128 x 3 uint8."""
    a = (x.clamp(0, 1).numpy() * 255).round().astype(np.uint8).transpose(0, 2, 3, 1)
    return np.vstack([np.hstack(list(a[r * 4 : r * 4 + 4])) for r in range(4)])


def per_tile_mse(pred: torch.Tensor, x: torch.Tensor) -> float:
    return float(((pred - x) ** 2).mean())


@torch.no_grad()
def sheet(store: TileStore, nets: dict[int, ConvAE], ids: list[int], labels: list[str], path) -> None:
    """One row per tile: the tile as the network receives it, then the network's drawing at each age, with that drawing's error."""
    cell = 128 * SCALE
    cols = [("real", None)] + [(f"step {s:,}", s) for s in nets]
    label_w, head = 120, 24
    W = label_w + len(cols) * (cell + PAD)
    H = head + len(ids) * (cell + PAD + 16)
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    for c, (name, _) in enumerate(cols):
        d.text((label_w + c * (cell + PAD) + 2, 5), name, fill="black", font=FONT)
    for r, (i, lab) in enumerate(zip(ids, labels)):
        y = head + r * (cell + PAD + 16)
        x = grid_crops(store.get_lowres(i))
        d.multiline_text((4, y + 4), lab, fill="black", font=FONT, spacing=3)
        for c, (_, s) in enumerate(cols):
            pred = x if s is None else nets[s](x)
            im.paste(Image.fromarray(mosaic(pred)).resize((cell, cell), Image.Resampling.NEAREST), (label_w + c * (cell + PAD), y))
            if s is not None:
                d.text((label_w + c * (cell + PAD) + 2, y + cell + 1), f"error {per_tile_mse(pred, x):.4f}", fill="#444444", font=FONT)
    im.save(path, optimize=True)


def pick_by_contrast(store: TileStore, ids: list[int], n: int) -> list[int]:
    """n tiles spread evenly over the contrast range of the set, so flat and rough terrain both appear."""
    std = np.array([store.get_lowres(i).mean(2).std() for i in ids])
    order = np.argsort(std)
    return [ids[order[int(q)]] for q in np.linspace(0.05 * (len(ids) - 1), 0.97 * (len(ids) - 1), n)]


@torch.no_grad()
def baselines(store: TileStore, held: torch.Tensor, visited: list[int]) -> pd.DataFrame:
    """Held-out crops: each saved age of the network against a flat colour per crop and PCA fitted on the crops of tiles the walk visited."""
    f = held.flatten(0, 1)
    flat = ((f - f.mean((2, 3), keepdim=True)) ** 2).flatten(1).mean(1)
    _, tr = scoring_crops(store, visited)
    tr = tr.flatten(0, 1).flatten(1).double()
    mu = tr.mean(0)
    _, _, vh = torch.linalg.svd(tr - mu, full_matrices=False)
    basis = vh[:LATENT]
    fd = f.flatten(1).double() - mu
    pca = ((fd - fd @ basis.T @ basis) ** 2).mean(1).float()
    rows = [{"who": "one flat colour per crop", "step": np.nan, "mean_mse": float(flat.mean()), "median_mse": float(flat.median()), "beats_flat": np.nan, "median_share_of_detail_drawn": 0.0},
            {"who": f"PCA, {LATENT} numbers, fitted on {len(tr):,} visited crops", "step": np.nan, "mean_mse": float(pca.mean()), "median_mse": float(pca.median()), "beats_flat": float((pca < flat).float().mean()),
             "median_share_of_detail_drawn": float((1 - pca / flat).median())}]
    for s in (0, 19, 65, 250, 500, 1000, 2500, 5000):
        e = ((net(RUN, s)(f) - f) ** 2).flatten(1).mean(1)
        rows.append({"who": "network", "step": s, "mean_mse": float(e.mean()), "median_mse": float(e.median()), "beats_flat": float((e < flat).float().mean()), "median_share_of_detail_drawn": float((1 - e / flat).median())})
    return pd.DataFrame(rows)


@torch.no_grad()
def seen_vs_unseen(store: TileStore, run: str) -> pd.DataFrame:
    """Each stay of at least MIN_STAY steps, with checkpoints either side of it: visited tiles against neighbours offered during the stay and never visited in the whole walk.
    The change in error across the stay, on the same crops, separates what the visits taught from what the terrain and the rest of the walk taught."""
    s = places(steps(run))
    c = pd.read_parquet(RUNS / run / "candidates.parquet", columns=["step", "tile_idx", "kind"])
    c = c[c.kind == "neighbour"]
    ever = set(s.tile_idx)
    ck = saved_steps(run)
    rows = []
    for p, g in s.groupby("place"):
        first, last = int(g.step.min()), int(g.step.max())
        before, after = ck[ck <= first], ck[ck > last]
        if len(g) < MIN_STAY or not len(after):
            continue
        b, a = (int(before.max()) if len(before) else 0), int(after.min())
        if a - b > len(g) + 250:
            continue
        seen = g.tile_idx.value_counts()
        offered = set(c[c.step.between(first, last)].tile_idx) - ever
        ids_s, xs = scoring_crops(store, seen.index.tolist())
        ids_u, xu = scoring_crops(store, sorted(offered))
        if len(ids_s) < 10 or len(ids_u) < 10:
            continue
        mb, ma = net(run, b), net(run, a)
        for ids, x, group in ((ids_s, xs, "visited"), (ids_u, xu, "never visited")):
            eb, ea = S.recon_err(mb, x).numpy(), S.recon_err(ma, x).numpy()
            rows.append({"place": p, "first": first, "last": last, "ckpt_before": b, "ckpt_after": a, "group": group, "n_tiles": len(ids), "e_before": float(np.median(eb)), "e_after": float(np.median(ea)), "after_over_before": float(np.median(ea / eb))})
    return pd.DataFrame(rows)


def main() -> None:
    DIR.mkdir(exist_ok=True)
    store = TileStore(cache_gb=30.0)
    held_ids, held = heldout_set(store)
    log = pd.read_parquet(RUNS / RUN / "heldout.parquet").set_index("step").heldout_mse
    for s in (0, 250, 1000, 5000):
        got = float(S.recon_err(net(RUN, s), held).mean())
        assert abs(got - log[s]) < 1e-6, (s, got, log[s])
    print("rebuilt networks and crops give the logged held-out error at steps 0, 250, 1000, 5000")

    nets = {s: net(RUN, s) for s in AGES}
    s = places(steps(RUN))
    never = pick_by_contrast(store, [i for i in held_ids if i not in set(s.tile_idx)], 6)
    sheet(store, nets, never, ["never visited\n(held-out)"] * len(never), DIR / "drawings_never_seen.png")
    visits = s.tile_idx.value_counts()
    long_stays = s[s.place_len >= MIN_STAY]
    top = long_stays.groupby("place").tile_idx.agg(lambda v: v.value_counts().index[0])
    walked = pick_by_contrast(store, [int(i) for i in top if store.cached(int(i))], 6)
    first = s.drop_duplicates("tile_idx").set_index("tile_idx").step
    sheet(store, nets, walked, [f"visited {visits[i]}x\nfirst at {first[i]:,}" for i in walked], DIR / "drawings_walked.png")

    b = baselines(store, held, [int(i) for i in s.tile_idx.unique()])
    b.to_csv(DIR / "drawings_baselines.csv", index=False)
    print(b.round(5).to_string())

    u = seen_vs_unseen(store, RUN)
    u.to_csv(DIR / "drawings_seen_vs_unseen.csv", index=False)
    print(u.round(5).to_string())


if __name__ == "__main__":
    main()
