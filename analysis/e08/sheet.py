"""Experiment 08, character sheet (notes/08_character_sheet/brief.md): the runs, loaders, per-tile statistics and networks shared by
readouts.py and panel.py. Definitions of places, teleport bursts and appetite are those of round h0111 (analysis/h0111/), imported, not copied.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "analysis" / "h0111"), str(ROOT / "analysis")]
import common as h0111  # noqa: E402

from agent import signals as S  # noqa: E402
from agent.model import CH, LATENT, ConvAE  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = ROOT / "notes" / "08_character_sheet" / "results"
RUNS = ROOT / "runs"
CACHE = ROOT / "data" / "sheet"  # git-ignored: per-tile statistics, panel scores
PANEL = HERE / "panel.csv"
YOUNG = 150  # steps 0-149 are the young network (h0111, findings 10 and 14)
PHASES = {"all": (0, 10**9), "young": (0, YOUNG), "settled": (YOUNG, 10**9)}
CKPTS = (250, 500, 750, 1000)
SEEDS = tuple(range(8))
STAGE0_SEEDS = (0, 1, 2, 3)
REFERENCE = "Reference"
# a group's runs come from the first of its stems that has the seed: seeds 0-3 of the Reference are the h0111 walks, seeds 4-7 are e08's
STAGE0 = {"Reference": ("h0111_reference", "e08_reference"), "Null": "h0111_null", "Bored": "h0111_bored",
          "Reference k=3": "h0111_reference_k3", "Reference k=8": "h0111_reference_k8", "Bored k=3": "h0111_bored_k3", "Bored k=8": "h0111_bored_k8"}
# Stage 1: one key changed from the Reference (configs/08_character_sheet/). label -> (section, key, value, stems)
SETTINGS = {
    "novelty only": ("Taste", "w_g", 0, "e08_novelty_only"),
    "progress only": ("Taste", "w_n", 0, "e08_progress_only"),
    "surprise added": ("Taste", "w_e", 1, "e08_surprise"),
    "k_nn 3": ("Taste", "k_nn", 3, "e08_knn_3"),
    "k_nn 30": ("Taste", "k_nn", 30, "e08_knn_30"),
    "ema 0.005": ("Taste", "ema_alpha", 0.005, "e08_ema_005"),
    "ema 0.08": ("Taste", "ema_alpha", 0.08, "e08_ema_08"),
    "temperature 0.2": ("Temperament", "temperature", 0.2, "e08_temp_02"),
    "temperature 1.0": ("Temperament", "temperature", 1.0, "e08_temp_10"),
    "crop 32": ("Eye", "crop_px", 32, "e08_crop_32"),
    "crop 128": ("Eye", "crop_px", 128, "e08_crop_128"),
    "patience 0.8": ("Temperament", "patience", 0.8, "e08_patience_08"),
    "far jumps 0": ("Temperament", "p_long_jump", 0, "e08_farjump_0"),
    "far jumps 0.2": ("Temperament", "p_long_jump", 0.2, "e08_farjump_02"),
    "update steps 1": ("Eye", "update_steps", 1, "e08_update_1"),
    "update steps 12": ("Eye", "update_steps", 12, "e08_update_12"),
    "Null, patience 0.3": ("Temperament", "choice, patience", "uniform, 0.3", "e08_null_patience_03"),
    "buffer 512": ("Eye", "buffer_size", 512, "e08_buffer_512"),
    "buffer 8192": ("Eye", "buffer_size", 8192, "e08_buffer_8192"),
    "width 0.5": ("Eye", "ae_width", 0.5, ("h0111_eye_half", "e08_width_05")),
    "width 2": ("Eye", "ae_width", 2, ("h0111_eye_double", "e08_width_2")),
    "radius 25": ("Temperament", "radius_km", 25, "e08_radius_25"),
    "return cost 0.5": ("Temperament", "return_cost", 0.5, "e08_returncost_05"),
    "no backstep": ("Temperament", "no_backstep", True, "e08_nobackstep"),
}
GROUPS = {**STAGE0, **{k: v[3] for k, v in SETTINGS.items()}}
BRIGHT_GREY, BRIGHT_SAT = 130, 0.15  # snow, ice or cloud: bright and nearly grey (h0111 task 1, rough labels)

places, heldout, steps = h0111.places, h0111.heldout, h0111.steps


def runs(groups: dict = GROUPS, seeds=SEEDS) -> list[tuple[str, int, str]]:
    """(group, seed, run) for every finished run on this machine; a group's stem is a name or a tuple of names tried in order."""
    out = []
    for g, stems in groups.items():
        for sd in seeds:
            for stem in (stems,) if isinstance(stems, str) else stems:
                if (RUNS / f"{stem}_s{sd}" / "final.pt").exists():
                    out.append((g, sd, f"{stem}_s{sd}"))
                    break
    return out

def config(run: str) -> dict:
    return yaml.safe_load((RUNS / run / "config.yaml").read_text())


def candidates(run: str) -> pd.DataFrame:
    """candidates.parquet with C (candidates at that step), each candidate's prior visits (arrivals before this step, as walk.py
    counts them) and whether it is the tile the walker just came from."""
    s, c = steps(run), h0111.candidates(run)
    t = s.tile_idx.to_numpy()
    counts: dict[int, int] = {}
    prior = np.zeros(len(c), int)
    done = 0
    for k, (st, i) in enumerate(zip(c.step.to_numpy(), c.tile_idx.to_numpy())):
        while done < st:
            counts[t[done]] = counts.get(t[done], 0) + 1
            done += 1
        prior[k] = counts.get(i, 0)
    start = yaml.safe_load((RUNS / run / "meta.json").read_text())["start_tile"]
    came_from = np.r_[-1, start, t[:-2]]  # at step n the walker stands on t[n-1] and came from t[n-2] (the start tile at step 1)
    return c.assign(prior=prior, seen=prior > 0, C=c.groupby("step").step.transform("size"), back=c.tile_idx.to_numpy() == came_from[c.step.to_numpy()])


def _stats_of(store, i: int) -> dict:
    a = store.get_lowres(int(i)).astype(np.float32)
    g = a.mean(2)
    gy, gx = np.gradient(g)
    hist = np.bincount(g.astype(np.uint8).ravel(), minlength=256) / g.size
    hist = hist[hist > 0]
    mx, mn = a.max(2), a.min(2)
    return {"tile_idx": int(i), "grad": float(np.hypot(gx, gy).mean()), "entropy": float(-(hist * np.log2(hist)).sum()), "grey_mean": float(g.mean()),
            "grey_std": float(g.std()), "r": float(a[..., 0].mean()), "g": float(a[..., 1].mean()), "b": float(a[..., 2].mean()),
            "sat": float(((mx - mn) / np.maximum(mx, 1)).mean())}


def tile_stats(ids) -> pd.DataFrame:
    """Per tile, on the 256 px tile the walker's crops come from (same definitions as h0111 task 1): texture (mean gradient), contrast
    (grey-level spread), grey-level entropy, brightness, saturation, mean RGB; plus `bright` (snow, ice, cloud) and `ocean` from the
    index. Cached in data/sheet/tile_stats.parquet and extended as new tiles are asked for."""
    from data.tile_store import TileStore

    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "tile_stats.parquet"
    have = pd.read_parquet(path) if path.exists() else pd.DataFrame(columns=["tile_idx"])
    want = np.setdiff1d(np.unique(np.asarray(ids, np.int64)), have.tile_idx.to_numpy(np.int64))
    if len(want):
        store = TileStore()
        new = []
        for k, i in enumerate(want):
            new.append(_stats_of(store, i))
            if (k + 1) % 2000 == 0:
                print(f"[tile_stats] {k + 1}/{len(want)}", flush=True)
        have = pd.concat([have, pd.DataFrame(new)], ignore_index=True) if len(have) else pd.DataFrame(new)
        have.to_parquet(path, index=False)
    t = have.set_index("tile_idx").loc[np.asarray(ids, np.int64)]
    cover = pd.read_parquet(ROOT / "data" / "global" / "index.parquet", columns=["cover"]).cover.to_numpy()
    return t.assign(cover=cover[t.index.to_numpy()], ocean=lambda d: (d.cover == "ocean").astype(float),
                    bright=lambda d: ((d.grey_mean > BRIGHT_GREY) & (d.sat < BRIGHT_SAT)).astype(float))


def net(run: str, step: int) -> ConvAE:
    """The walk's network after `step` steps (a ckpt_NNNN.pt), at the run's own ae_width."""
    w = float(config(run).get("ae_width", 1.0))
    m = ConvAE(tuple(int(c * w) for c in CH), int(LATENT * w)).eval()
    m.load_state_dict(torch.load(RUNS / run / f"ckpt_{step:04d}.pt", weights_only=True)["model"])
    return m


def scoring_crops(store, ids, K: int, crop_px: int) -> torch.Tensor:
    """The walker's fixed scoring crops (score_crops: fixed), as walk.py makes them: [C, K, 3, 32, 32]."""
    ids = list(map(int, ids))
    arrs, dropped, _ = store.get_many(ids, timeout=600.0)
    assert not dropped, f"tiles could not be fetched: {dropped[:10]}"
    img = torch.from_numpy(np.stack([arrs[i] for i in ids]))
    return S.patches(img, torch.zeros(len(ids), dtype=torch.bool), K, crop_px, torch.Generator(), S.fixed_offsets(ids, K, img.shape[1], crop_px, "cpu"))
