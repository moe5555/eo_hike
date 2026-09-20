"""Phase 2: per-patch novelty heatmaps for a finished run.

The encoder is a vision transformer: before it pools them into one chip embedding it
holds one vector per 16x16 patch (a 14x14 grid at 224 px). Here the *same* quantity
the agent acts on, mean cosine distance to the ``j`` nearest things already seen, is
computed for every patch of every visited chip, against a bank made of all patches of
the chips the agent had seen before that step. It is the agent's own score at a finer
grain, not a post-hoc attribution like Grad-CAM: no second model explains the first,
the number is the same kind of number, only per patch instead of per chip.

Patch vectors get the same treatment as chip vectors: the model's own final LayerNorm,
L2-normalisation, then subtraction of a mean and renormalisation. The mean is the mean
patch vector over a fixed random sample of the archive, cached next to the embeddings
(``patch_mean_<encoder>.npy``). Only agents' visited chips are encoded, so the stage
costs seconds, not the full-archive pass of ``embed``.

Outputs, all inside the run directory:

- ``sequence/agent_<id>/<step:04d>_<chip_id>_heat.png``: the chip with hot patches
  tinted. The colour scale is fixed across the whole run: tint starts at the 75th
  percentile of all patch scores in the run and saturates at the 98th, so "hot"
  means hot for this walk, not for this chip, and three quarters of all patches
  show the plain image.
- ``patch_novelty_agent_<id>.npz``: ``scores`` of shape ``(steps + 1, gh, gw)`` with
  NaN at step 0 (no history to compare with), plus ``chip_ids`` and ``steps``.
- ``heatmap.json``: parameters, colour scale, per-step summary (mean, max, hottest
  patch) and the correlation between per-chip novelty and patch novelty.
- ``heatmap_sheet_agent_<id>.png``: the first 25 steps as original/overlay pairs.

The step log ``log.jsonl`` is not rewritten; the sidecar carries the per-patch numbers
(brief §4 allows this when the log would get unwieldy: 196 floats per line would).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml
from PIL import Image
from tqdm import tqdm

from . import config as C
from .encoders import get_encoder
from .encoders.base import pick_device
from .ingest import load_manifest
from .io import read_jsonl, write_json


# --- the score --------------------------------------------------------------------


def patch_novelty(query: torch.Tensor, bank: torch.Tensor, j: int) -> torch.Tensor:
    """Mean cosine distance from each query patch to its ``j`` nearest bank patches.

    ``query`` is ``(P, d)`` and ``bank`` ``(N, d)``, both rows unit length. Returns
    ``(P,)``. If the bank holds fewer than ``j`` patches all of it is used. This is
    :func:`hiker.scoring.novelty_scores` for patches, in torch so the bank can sit on
    the GPU.
    """
    if j < 1:
        raise ValueError("j must be >= 1")
    if bank.shape[0] == 0:
        raise ValueError("bank must contain at least one patch")
    d = 1.0 - query @ bank.T
    jj = min(j, bank.shape[0])
    nearest = torch.topk(d, jj, dim=1, largest=False).values
    return nearest.mean(dim=1)


def centre_patches(tokens: np.ndarray, mean: np.ndarray | None) -> np.ndarray:
    """L2-normalise ``(..., d)`` patch vectors, optionally after subtracting ``mean``."""
    x = np.asarray(tokens, dtype=np.float32)
    x = x / np.maximum(np.linalg.norm(x, axis=-1, keepdims=True), 1e-12)
    if mean is not None:
        x = x - mean.astype(np.float32)
        x = x / np.maximum(np.linalg.norm(x, axis=-1, keepdims=True), 1e-12)
    return x


# --- patch mean (cached per archive and encoder) ----------------------------------


def patch_mean_path(cfg: dict[str, Any]) -> Path:
    return C.processed_dir(cfg) / f"patch_mean_{C.encoder_key(cfg)}.npy"


def patch_mean(cfg: dict[str, Any], encoder: Any, manifest: Any, n_sample: int, batch_size: int) -> np.ndarray:
    """Mean of L2-normalised patch vectors over a seeded random sample of the archive."""
    p = patch_mean_path(cfg)
    if p.exists():
        return np.load(p)
    rng = np.random.default_rng(0)
    rows = np.sort(rng.choice(len(manifest), size=min(n_sample, len(manifest)), replace=False))
    root = C.processed_dir(cfg)
    paths = [root / manifest["path"].iloc[int(r)] for r in rows]
    acc: np.ndarray | None = None
    count = 0
    for s in tqdm(range(0, len(paths), batch_size), desc="patch mean", unit="batch"):
        ims = [Image.open(q).convert("RGB") for q in paths[s : s + batch_size]]
        t = encoder.encode_patches(ims)  # (B, P, d), rows L2-normalised
        t = t.reshape(-1, t.shape[-1]).astype(np.float64)
        acc = t.sum(axis=0) if acc is None else acc + t.sum(axis=0)
        count += t.shape[0]
    assert acc is not None
    mean = (acc / count).astype(np.float32)
    with open(p, "wb") as f:
        np.save(f, mean)
    return mean


# --- rendering ----------------------------------------------------------------------


def render_overlay(
    image: Path, scores: np.ndarray, vmin: float, vmax: float, alpha: float, cmap: str, out: Path
) -> None:
    """Tint the chip where patches are hot. Cold patches show the plain image.

    The alpha of the tint scales with the normalised score, so a chip that is new all
    over is covered all over, and one with a single surprising corner shows a single
    tinted corner. The 14x14 grid is upsampled bilinearly to the chip size.
    """
    import matplotlib

    im = Image.open(image).convert("RGB")
    w, h = im.size
    norm = np.clip((scores - vmin) / max(vmax - vmin, 1e-9), 0.0, 1.0).astype(np.float32)
    up = Image.fromarray((norm * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
    n = np.asarray(up, dtype=np.float32) / 255.0
    colour = matplotlib.colormaps[cmap](n)[..., :3]  # (h, w, 3) in [0, 1]
    base = np.asarray(im, dtype=np.float32) / 255.0
    a = (alpha * n)[..., None]
    blend = (1.0 - a) * base + a * colour
    Image.fromarray((blend * 255).round().astype(np.uint8)).save(out)


def overlay_sheet(pairs: list[tuple[Path, Path]], out: Path, cols: int = 10, thumb: int = 96) -> None:
    """Original and overlay side by side, ``cols // 2`` pairs per row."""
    from .viz import contact_sheet

    flat = [p for pair in pairs for p in pair]
    contact_sheet(flat, out, cols=cols, thumb=thumb)


# --- the stage ----------------------------------------------------------------------


def latest_run_dir(runs_dir: str | Path) -> Path:
    dirs = sorted(p for p in Path(runs_dir).iterdir() if p.is_dir() and (p / "log.jsonl").exists())
    if not dirs:
        raise FileNotFoundError(f"no run directories with a log.jsonl under {runs_dir}")
    return dirs[-1]


def run_heatmap(cfg: dict[str, Any], run_dir: str | Path, force: bool = False) -> Path:
    """Compute and render per-patch novelty for every agent of a finished run.

    ``cfg`` supplies the ``heatmap`` section; dataset and encoder come from the run's
    own ``config.yaml`` so the heatmap always uses the encoder that made the walk.
    """
    run_dir = Path(run_dir)
    out_json = run_dir / "heatmap.json"
    if out_json.exists() and not force:
        print(f"[heatmap] exists, skipping: {out_json}")
        return out_json
    with open(run_dir / "config.yaml", "r", encoding="utf-8") as f:
        run_cfg = yaml.safe_load(f)
    hcfg = {**C.DEFAULTS["heatmap"], **(cfg.get("heatmap") or {})}
    j = int(hcfg["j_patches"])

    ecfg = {k: v for k, v in run_cfg["encoder"].items() if k != "resolved"}
    ecfg["device"] = cfg["encoder"].get("device", ecfg.get("device", "auto"))
    encoder = get_encoder(ecfg)
    if not hasattr(encoder, "encode_patches"):
        raise RuntimeError(
            f"encoder {encoder.name!r} exposes no patch tokens; the heatmap needs a ViT encoder with encode_patches()"
        )
    device = pick_device(ecfg.get("device", "auto"))
    bs = int(ecfg.get("batch_size", 64))
    manifest = load_manifest(run_cfg)
    root = C.processed_dir(run_cfg)
    chip_to_row = {cid: i for i, cid in enumerate(manifest["chip_id"].tolist())}
    mean = patch_mean(run_cfg, encoder, manifest, int(hcfg["mean_sample"]), bs) if run_cfg["encoder"].get("center", True) else None

    log = read_jsonl(run_dir / "log.jsonl")
    agents = sorted({r["agent_id"] for r in log})
    walks = {a: [r["chip_id"] for r in log if r["agent_id"] == a] for a in agents}

    # Encode every visited chip once (agents may share chips).
    needed = sorted({cid for w in walks.values() for cid in w}, key=lambda c: chip_to_row[c])
    tokens: dict[str, np.ndarray] = {}
    for s in tqdm(range(0, len(needed), bs), desc="patch tokens", unit="batch"):
        ids = needed[s : s + bs]
        ims = [Image.open(root / manifest["path"].iloc[chip_to_row[c]]).convert("RGB") for c in ids]
        t = centre_patches(encoder.encode_patches(ims), mean)
        for c, tt in zip(ids, t):
            tokens[c] = tt
    gh, gw = encoder.patch_grid
    P = gh * gw
    dim = next(iter(tokens.values())).shape[-1]

    per_agent: dict[int, np.ndarray] = {}
    for a in agents:
        w = walks[a]
        scores = np.full((len(w), gh, gw), np.nan, dtype=np.float32)
        bank = torch.empty((len(w) * P, dim), dtype=torch.float32, device=device)
        bank[:P] = torch.from_numpy(tokens[w[0]]).to(device)
        n = P
        with torch.no_grad():
            for t in tqdm(range(1, len(w)), desc=f"patch novelty agent {a}", unit="step"):
                q = torch.from_numpy(tokens[w[t]]).to(device)
                scores[t] = patch_novelty(q, bank[:n], j).cpu().numpy().reshape(gh, gw)
                bank[n : n + P] = q
                n += P
        per_agent[a] = scores
        np.savez_compressed(
            run_dir / f"patch_novelty_agent_{a}.npz",
            scores=scores,
            chip_ids=np.asarray(w),
            steps=np.arange(len(w)),
        )

    allv = np.concatenate([v[1:].ravel() for v in per_agent.values() if v.shape[0] > 1])
    p_lo, p_hi = (float(x) for x in hcfg["scale_percentiles"])
    vmin, vmax = (float(np.percentile(allv, p_lo)), float(np.percentile(allv, p_hi))) if allv.size else (0.0, 1.0)
    hot = vmin  # a patch is "hot" when it is tinted at all

    summary: dict[str, Any] = {
        "run_dir": run_dir.name,
        "encoder": encoder.name,
        "patch_grid": [gh, gw],
        "j_patches": j,
        "centered": mean is not None,
        "patch_mean_sample": int(hcfg["mean_sample"]) if mean is not None else None,
        "colour_scale": {"vmin": vmin, "vmax": vmax, "percentiles": [p_lo, p_hi], "cmap": hcfg["cmap"], "alpha": hcfg["alpha"]},
        "hot_threshold": hot,
        "agents": [],
    }
    for a in agents:
        w = walks[a]
        sc = per_agent[a]
        rows = [r for r in log if r["agent_id"] == a]
        seq_dir = run_dir / "sequence" / f"agent_{a}"
        overlays: list[tuple[Path, Path]] = []
        steps_out = []
        for t, cid in enumerate(tqdm(w, desc=f"render agent {a}", unit="img")):
            src = root / manifest["path"].iloc[chip_to_row[cid]]
            entry: dict[str, Any] = {"step": t, "chip_id": cid, "novelty": rows[t]["novelty"]}
            if t == 0:
                entry.update({"patch_mean": None, "patch_max": None, "patch_min": None, "hot_fraction": None, "hottest_patch": None})
            else:
                s = sc[t]
                am = int(np.argmax(s))
                entry.update(
                    {
                        "patch_mean": round(float(s.mean()), 6),
                        "patch_max": round(float(s.max()), 6),
                        "patch_min": round(float(s.min()), 6),
                        "hot_fraction": round(float((s >= hot).mean()), 4),
                        "hottest_patch": [am // gw, am % gw],
                    }
                )
                if seq_dir.exists():
                    out = seq_dir / f"{t:04d}_{cid}_heat.png"
                    render_overlay(src, s, vmin, vmax, float(hcfg["alpha"]), str(hcfg["cmap"]), out)
                    overlays.append((seq_dir / f"{t:04d}_{cid}.png", out))
            steps_out.append(entry)
        nov = np.array([e["novelty"] for e in steps_out[1:]], dtype=np.float64)
        pm = np.array([e["patch_mean"] for e in steps_out[1:]], dtype=np.float64)
        px = np.array([e["patch_max"] for e in steps_out[1:]], dtype=np.float64)
        corr = lambda x, y: round(float(np.corrcoef(x, y)[0, 1]), 4) if len(x) > 2 and x.std() > 0 and y.std() > 0 else None
        summary["agents"].append(
            {
                "agent_id": a,
                "steps": len(w) - 1,
                "patch_mean_over_walk": round(float(np.nanmean(sc[1:])), 6) if len(w) > 1 else None,
                "corr_novelty_vs_patch_mean": corr(nov, pm),
                "corr_novelty_vs_patch_max": corr(nov, px),
                "steps_detail": steps_out,
            }
        )
        if overlays:
            overlay_sheet(overlays[:25], run_dir / f"heatmap_sheet_agent_{a}.png")
    write_json(out_json, summary)
    for s in summary["agents"]:
        print(
            f"[heatmap] agent {s['agent_id']}: {s['steps']} steps, mean patch novelty {s['patch_mean_over_walk']:.4f}, "
            f"corr(novelty, patch mean) {s['corr_novelty_vs_patch_mean']}, corr(novelty, patch max) {s['corr_novelty_vs_patch_max']}"
        )
    print(f"[heatmap] wrote {out_json}; colour scale {vmin:.3f}..{vmax:.3f}")
    return out_json
