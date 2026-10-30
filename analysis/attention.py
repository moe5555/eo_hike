"""Where a walker looks inside one tile, and in what order: attention maps and a Ken Burns shotlist.

    python -m analysis.attention runs/global_perception_1k_s0 --list              # tiles it found most novel
    python -m analysis.attention runs/global_perception_1k_s0 --pick novelty      # or --step 523
    python -m analysis.kenburns runs/global_perception_1k_s0/attention/step_0523_learn/shotlist.json

The walker has no gaze: at each step it scores a candidate tile on K = 16 crops of crop_px (64 px ~ 2.6 km)
at once, random or (score_crops: fixed) seeded by tile id, and averages them. The maps here score every
crop_px window of the tile (stride 8 px, 25 x 25 windows) with the walker's own model and memory at that
step, using the walk's own signals:

    e  reconstruction error of the window ("how badly can I draw it")
    n  novelty: mean distance from the window's latent to its k_nn nearest crop latents of the tiles visited
       before this step. A crop bank, like the patch bank of main's heat maps: the walker's archive holds
       tile means, and one crop is not comparable with a mean of 16. The bank is re-encoded by the model
       that scores (as the walk re-embeds its archive), so after a look nothing is new just because the model moved
    g  progress: error drop on the window after probe_steps fresh Adam steps on it
    I  w_n z(n) + w_g z(g) + w_e z(e), with the walk's weights and z over the tile's windows

The order of looks is constructed (--order):

    glances  the K crops the walker actually scored (fixed-crop runs only), hottest first
    peaks    local maxima of the map, hottest first, at least crop_px / 2 apart
    learn    look and learn: take the hottest window, train on it as the walker trains on a tile
             (update_steps Adam steps on K jittered crops plus replay), add those crops to the bank, rescore, repeat.
             Familiarity moves the gaze on; whatever stays hot is looked at again (marked as a return).

Model: the latest snapshot at or before the step (ckpt_<c>.pt is the model used at step c, bored_<b>.pt the one
used at step b + 1; step 0 is the seed's initial model). The gap to the step is recorded in the shotlist.

Writes runs/<run>/attention/step_<step>_<order>/: maps.npz (maps per look), shotlist.json (editable; read by
analysis/kenburns.py), preview.png (tile, map, numbered looks).
"""

from __future__ import annotations

import argparse
import json
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

STRIDE = 8
TILE_KM = 10.68  # 1068 px at 10 m
SIGNALS = {"interest": "I", "novelty": "n", "surprise": "e", "progress": "g"}


def load_run(run: Path) -> tuple[dict, pd.DataFrame]:
    cfg = yaml.safe_load((run / "config.yaml").read_text())
    s = pd.read_parquet(run / "steps.parquet").reset_index(drop=True)
    s["visit"] = s.groupby("tile_idx").cumcount() + 1
    return cfg, s


def snapshot(run: Path, cfg: dict, step: int) -> tuple[ConvAE, str, int]:
    """The walker's model as it was used at `step`, or the latest earlier snapshot."""
    snaps = [(int(p.stem[5:]), p) for p in run.glob("ckpt_*.pt")] + [(int(p.stem[6:]) + 1, p) for p in run.glob("bored_*.pt")]
    snaps = [x for x in snaps if x[0] <= step]
    torch.manual_seed(int(cfg["seed"]))  # walk.py: the model is the first thing drawn from the global RNG
    model = ConvAE()
    if not snaps:
        return model.eval(), "initial model (seed)", step
    used, p = max(snaps)
    model.load_state_dict(torch.load(p, map_location="cpu")["model"])
    return model.eval(), p.name, step - used


def grid(H: int, crop: int) -> tuple[torch.Tensor, torch.Tensor]:
    pos = torch.arange(0, H - crop + 1, STRIDE)
    oy, ox = torch.meshgrid(pos, pos, indexing="ij")
    return oy.reshape(1, -1), ox.reshape(1, -1)


def crops(img: np.ndarray, oy: torch.Tensor, ox: torch.Tensor, crop: int) -> torch.Tensor:
    """[M, 3, 32, 32] crops of one tile at the given offsets ([1, M] each)."""
    t = torch.from_numpy(np.array(img))[None]
    return S.patches(t, torch.zeros(1, dtype=torch.bool), oy.shape[1], crop, None, (oy, ox))[0]


def crop_bank(store, cfg: dict, tiles: list[int]) -> torch.Tensor | None:
    """K crops [N * K, 3, 32, 32] of every tile visited before the step (the walk's fixed crops if it used them).
    Kept as pixels and encoded by whichever model scores, so the bank is never stale."""
    if not tiles:
        return None
    K, crop = int(cfg["K"]), int(cfg["crop_px"])
    arrs, dropped, _ = store.get_many(tiles, timeout=600.0)
    assert not dropped, f"tiles missing from the store: {dropped[:5]}"
    gen = torch.Generator().manual_seed(0)
    xs = []
    for i in range(0, len(tiles), 128):
        ids = tiles[i : i + 128]
        img = torch.from_numpy(np.stack([arrs[t] for t in ids]))
        off = S.fixed_offsets(ids, K, img.shape[1], crop, "cpu") if cfg.get("score_crops") == "fixed" else None
        xs.append(S.patches(img, torch.zeros(len(ids), dtype=torch.bool), K, crop, gen, off).flatten(0, 1))
    return torch.cat(xs)


def zscore(v: np.ndarray) -> np.ndarray:
    return (v - v.mean()) / (v.std() + 1e-8)


def score(model: ConvAE, x: torch.Tensor, bank: torch.Tensor | None, cfg: dict) -> dict[str, np.ndarray]:
    """The walk's signals for each crop in x [M, 3, 32, 32]; bank: crops seen before, encoded now by `model`."""
    with torch.no_grad():
        e = ((model(x) - x) ** 2).flatten(1).mean(1)
        zb = None if bank is None else torch.cat([model.encode(b) for b in bank.split(4096)])
        n = S.novelty(model.encode(x), zb, int(cfg["k_nn"]), unit=bool(cfg.get("normalise_latents", False)))
    g = torch.cat([S.progress_probe(model, torch.stack([xc, xc], 1), float(cfg["lr"]), int(cfg["probe_steps"]))[0]
                   for xc in x.split(64)])  # train on the window, measure on the same window
    out = {"e": e.numpy(), "n": n.numpy(), "g": g.numpy()}
    out["I"] = float(cfg["w_n"]) * zscore(out["n"]) + float(cfg["w_g"]) * zscore(out["g"]) + float(cfg["w_e"]) * zscore(out["e"])
    return out


def peaks(v: np.ndarray, side: int, n: int, min_cells: int) -> list[int]:
    order, keep = np.argsort(-v), []
    for i in order:
        if all(max(abs(i // side - j // side), abs(i % side - j % side)) >= min_cells for j in keep):
            keep.append(int(i))
        if len(keep) == n:
            break
    return keep


def build(run: Path, step: int, order: str, signal: str, n_looks: int, frame: float) -> Path:
    from data.tile_store import TileStore

    cfg, s = load_run(run)
    row = s.iloc[step]
    tile = int(row.tile_idx)
    K, crop, key = int(cfg["K"]), int(cfg["crop_px"]), SIGNALS[signal]
    store = TileStore(cache_gb=float(cfg.get("cache_gb", 50)))
    img = store.get_lowres(tile)
    H = img.shape[0]
    model, snap, gap = snapshot(run, cfg, step)
    bank = crop_bank(store, cfg, list(dict.fromkeys(map(int, s.tile_idx[:step]))))
    print(f"[attention] {run.name} step {step}: tile {tile} ({row.lat:.3f}, {row.lon:.3f}), {snap} ({gap} steps before), "
          f"bank {0 if bank is None else len(bank)} crops")

    oy, ox = grid(H, crop)
    side = int(np.sqrt(oy.shape[1]))
    xw = crops(img, oy, ox, crop)
    maps = [score(model, xw, bank, cfg)]
    looks = []  # (y0, x0) in low-res px, with the scores at the time of the look

    if order == "glances":
        if cfg.get("score_crops") != "fixed":
            raise SystemExit("--order glances needs a fixed-crop run (score_crops: fixed): random crops were not logged")
        gy, gx = S.fixed_offsets([tile], K, H, crop, "cpu")
        sc = score(model, crops(img, gy, gx, crop), bank, cfg)
        sc["I"] = (float(cfg["w_n"]) * (sc["n"] - maps[0]["n"].mean()) / (maps[0]["n"].std() + 1e-8)
                   + float(cfg["w_g"]) * (sc["g"] - maps[0]["g"].mean()) / (maps[0]["g"].std() + 1e-8)
                   + float(cfg["w_e"]) * (sc["e"] - maps[0]["e"].mean()) / (maps[0]["e"].std() + 1e-8))  # on the map's scale
        for i in np.argsort(-sc[key])[:n_looks]:
            looks.append((int(gy[0, i]), int(gx[0, i]), {k: float(v[i]) for k, v in sc.items()}))
    elif order == "peaks":
        for i in peaks(maps[0][key], side, n_looks, max(1, crop // 2 // STRIDE)):
            looks.append((int(oy[0, i]), int(ox[0, i]), {k: float(v[i]) for k, v in maps[0].items()}))
    else:  # learn
        m = ConvAE()
        m.load_state_dict(model.state_dict())
        opt = torch.optim.Adam(m.parameters(), lr=float(cfg["lr"]))
        gen = torch.Generator().manual_seed(int(cfg["seed"]))
        j = crop // 8
        for k in range(n_looks):
            i = int(np.argmax(maps[-1][key]))
            y0, x0 = int(oy[0, i]), int(ox[0, i])
            looks.append((y0, x0, {kk: float(v[i]) for kk, v in maps[-1].items()}))
            jy = (y0 + torch.randint(-j, j + 1, (1, K), generator=gen)).clamp(0, H - crop)
            jx = (x0 + torch.randint(-j, j + 1, (1, K), generator=gen)).clamp(0, H - crop)
            xt = crops(img, jy, jx, crop)
            batch = xt
            if bank is not None:  # replay as in the walk, from the most recent buffer_size crops
                recent = bank[-int(cfg["buffer_size"]) :]
                batch = torch.cat([xt, recent[torch.randint(0, len(recent), (int(cfg["replay_batch"]),), generator=gen)]])
            m.train()
            for _ in range(int(cfg["update_steps"])):
                loss = ((m(batch) - batch) ** 2).mean()
                opt.zero_grad(set_to_none=True)
                loss.backward()
                opt.step()
            m.eval()
            bank = xt if bank is None else torch.cat([bank, xt])
            if k < n_looks - 1:
                maps.append(score(m, xw, bank, cfg))
            print(f"[attention] look {k + 1}: ({y0}, {x0}) {signal} {looks[-1][2][key]:.3f}")

    # -- shotlist ---------------------------------------------------------------------
    size = min(1.0, crop / H * frame)
    shots = [{"kind": "establish", "cx": 0.5, "cy": 0.5, "size": 1.0, "move": 0.0, "hold": 3.0,
              "note": f"the whole tile, {TILE_KM:.1f} km"}]
    vals = np.array([lk[2][key] for lk in looks])
    w = (vals - vals.min()) / (np.ptp(vals) + 1e-8) if len(vals) > 1 else np.ones(1)
    for k, (y0, x0, sc) in enumerate(looks):
        cx, cy = (x0 + crop / 2) / H, (y0 + crop / 2) / H
        prev = shots[-1]
        dist = float(np.hypot(cx - prev["cx"], cy - prev["cy"]))
        ret = next((q for q, (py, px, _) in enumerate(looks[:k]) if max(abs(py - y0), abs(px - x0)) < crop / 2), None)
        shots.append({"kind": "look", "look": k + 1, "cx": round(cx, 4), "cy": round(cy, 4), "size": round(size, 4),
                      "move": round(2.0 + 2.5 * dist, 2), "hold": round(1.5 + 1.5 * float(w[k]), 2),
                      "box_px": [x0, y0, x0 + crop, y0 + crop], "scores": {kk: round(v, 5) for kk, v in sc.items()},
                      "return_to": None if ret is None else ret + 1})
    shots.append({"kind": "pullout", "cx": 0.5, "cy": 0.5, "size": 1.0, "move": 3.0, "hold": 2.0})

    out = run / "attention" / f"step_{step:04d}_{order}"
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "maps.npz", **{f"{k}_{i}": v.reshape(side, side) for i, mp in enumerate(maps) for k, v in mp.items()},
                        oy=oy.reshape(side, side).numpy(), ox=ox.reshape(side, side).numpy())
    sl = {
        "run": run.name, "step": step, "tile": tile, "grid_cell": str(row.grid_cell), "lat": float(row.lat), "lon": float(row.lon),
        "cover": str(row.get("cover", "")), "visit": int(row.visit),
        "walk": {k: (None if pd.isna(row[k]) else float(row[k])) for k in ("e", "n", "g", "e_z", "n_z", "g_z", "I")},
        "model": snap, "model_gap_steps": gap, "order": order, "signal": signal, "crop_px": crop, "lowres_px": H,
        "stride_px": STRIDE, "maps": "maps.npz: <e|n|g|I>_<look index> on the oy/ox window grid (one map per look for --order learn)",
        "render": {"fps": 30, "px": 1080, "heat": 0.0, "hud": False},
        "shots": shots,
    }
    (out / "shotlist.json").write_text(json.dumps(sl, indent=2))
    preview(img, store.get_hires(tile), maps[0][key].reshape(side, side), looks, crop, sl, out / "preview.png")
    print(f"[attention] {out / 'shotlist.json'}  ({len(looks)} looks, "
          f"{sum(1 for sh in shots if sh.get('return_to'))} returns)")
    return out / "shotlist.json"


def preview(low: np.ndarray, hi: np.ndarray, mp: np.ndarray, looks, crop: int, sl: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    H = low.shape[0]
    fig, ax = plt.subplots(1, 3, figsize=(15, 5.4))
    for a in ax:
        a.imshow(hi, extent=(0, H, H, 0))
        a.set_xticks([])
        a.set_yticks([])
    ax[0].set_title(f"step {sl['step']}, tile {sl['tile']}  ({sl['lat']:.2f}, {sl['lon']:.2f}, {sl['cover']})", fontsize=10)
    half = crop / 2
    im = ax[1].imshow(mp, extent=(half - STRIDE / 2, H - half + STRIDE / 2, H - half + STRIDE / 2, half - STRIDE / 2), cmap="inferno", alpha=0.65)
    ax[1].set_xlim(0, H)
    ax[1].set_ylim(H, 0)
    ax[1].set_title(f"{sl['signal']} of each {crop} px window (centre), before the first look", fontsize=10)
    fig.colorbar(im, ax=ax[1], fraction=0.046)
    cs = [(x0 + half, y0 + half) for y0, x0, _ in looks]
    ax[2].plot(*zip(*cs), color="w", lw=1.2, alpha=0.8)
    labels: dict[tuple[int, int], list[str]] = {}
    for k, (y0, x0, _) in enumerate(looks):
        ax[2].add_patch(Rectangle((x0, y0), crop, crop, fill=False, ec="#ffcc00", lw=1.4))
        labels.setdefault((y0, x0), []).append(str(k + 1))
    for (y0, x0), ks in labels.items():
        ax[2].text(x0 + 3, y0 + 12, ", ".join(ks), color="#ffcc00", fontsize=11, weight="bold")
    ax[2].set_title(f"looks in order ({sl['order']}); model {sl['model']}, {sl['model_gap_steps']} steps before", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def listing(run: Path, n: int) -> None:
    _, s = load_run(run)
    f = s[(s.visit == 1) & (s.step > 0)]
    cols = ["step", "tile_idx", "lat", "lon", "cover", "jump_type", "n_z", "g_z", "e_z", "I"]
    for name, col in (("novelty", "n_z"), ("surprise", "e_z"), ("progress", "g_z"), ("interest", "I")):
        print(f"\n-- first visits by {name} ({col}) --")
        print(f.sort_values(col, ascending=False).head(n)[[c for c in cols if c in f]].to_string(index=False, float_format=lambda v: f"{v:.3f}"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path)
    ap.add_argument("--list", action="store_true", help="print the first visits that scored highest, then stop")
    ap.add_argument("--step", type=int, help="the step whose tile to film")
    ap.add_argument("--pick", choices=list(SIGNALS), help="film the first visit with the highest walk score of this kind")
    ap.add_argument("--order", choices=["learn", "peaks", "glances"], default="learn")
    ap.add_argument("--signal", choices=list(SIGNALS), default="interest", help="what the camera follows (default: the walk's interest)")
    ap.add_argument("--looks", type=int, default=6)
    ap.add_argument("--frame", type=float, default=1.6, help="tight shot = crop_px x frame (1 = exactly the walker's field of view)")
    a = ap.parse_args()
    if a.list:
        return listing(a.run, 10)
    if (a.step is None) == (a.pick is None):
        raise SystemExit("give --step or --pick (or --list)")
    step = a.step
    if step is None:
        _, s = load_run(a.run)
        col = {"interest": "I", "novelty": "n_z", "surprise": "e_z", "progress": "g_z"}[a.pick]
        step = int(s[(s.visit == 1) & (s.step > 0)].sort_values(col, ascending=False).step.iloc[0])
    build(a.run, step, a.order, a.signal, a.looks, a.frame)


if __name__ == "__main__":
    main()
