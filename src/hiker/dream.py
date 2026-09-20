"""The dream: at the end of a walk the agent steers a generator with its own score.

What "prompting" means here
---------------------------
The hiker has no language. What it has is a history of embeddings and one number it
acts on: the novelty of a candidate, the mean cosine distance to the ``j`` nearest
things it has seen (plus, if the run used one, a pull towards its taste vector). So
the prompt *is* that score. Sampling from the fine-tuned Stable Diffusion runs as
usual under the empty prompt, and at every denoising step the current estimate of
the finished image is decoded, pushed through the same DOFA encoder that produced
the archive's embeddings, scored exactly as a candidate chip would be, and the
gradient of that score with respect to the latent nudges the sample towards "unlike
anything I have seen". No text, no target vector chosen by hand: the agent's history
is the only thing that shapes the image.

Mechanics (DDIM, eta = 0, no classifier-free guidance because there is no text):

    x0_hat  = (x_t - sqrt(1 - a_t) * eps) / sqrt(a_t)          predicted clean latent
    image   = VAE.decode(x0_hat)                              differentiable
    e       = centre(DOFA(image))                             unit vector, archive-centred
    score   = novelty(e, history, j) + w_taste * cos(e, taste)
    x0_hat <- x0_hat + s * ||x0_hat|| * grad_x0 score / ||grad||   within the guidance window
    x_{t-1} = sqrt(a_prev) * x0_hat + sqrt(1 - a_prev) * eps_hat,   eps_hat from the nudged x0_hat

The step is a fixed fraction ``s`` of the latent's norm, so the strength does not
depend on the score's scale. The UNet's noise prediction is treated as a constant in
the gradient (no backprop through the UNet), which keeps memory within 8 GB.

What is measured, and why it is honest
--------------------------------------
Each dream is re-encoded from its saved PNG through the ordinary ``encode`` path and
scored against the history like any chip. Alongside it: a *control* (same seed, no
guidance) scored the same way; the archive *ceiling* (the most novel unvisited real
chip); and the nearest real chip to the dream. So the log says whether the steering
did anything, and whether the dream went beyond what the archive could offer.

The dream is an epilogue: it is never appended to the history or the archive, and
``log.jsonl`` is untouched. Records go to ``dreams.json`` and the images to
``sequence/agent_<id>/dream_<k>.png`` (``dream_<k>_control.png`` for the control).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
import yaml
from PIL import Image
from tqdm import tqdm

from . import config as C
from .dream_train import SD15, dream_dir, empty_prompt_embedding, load_unet_with_adapter, load_vae
from .embed import load_embeddings
from .encoders import get_encoder
from .encoders.base import pick_device
from .encoders.dofa import IMAGENET_MEAN, IMAGENET_STD, RGB_WAVELENGTHS_UM
from .index import load_index
from .ingest import load_manifest
from .io import read_jsonl, write_json
from .scoring import novelty_scores


# --- the differentiable score ------------------------------------------------------


def novelty_torch(e: torch.Tensor, history: torch.Tensor, j: int) -> torch.Tensor:
    """Mean cosine distance from ``e`` (1, d) to its ``j`` nearest rows of ``history``.
    Same formula as :func:`hiker.scoring.novelty_scores`, differentiable in ``e``."""
    d = 1.0 - history @ e.reshape(-1)
    jj = min(j, history.shape[0])
    return torch.topk(d, jj, largest=False).values.mean()


def dofa_embed_differentiable(images: torch.Tensor, dofa: torch.nn.Module, mean_vec: torch.Tensor | None) -> torch.Tensor:
    """``images`` (B, 3, H, W) in [-1, 1] -> centred unit DOFA embeddings (B, 768).

    Mirrors ``DOFABase16.encode`` (resize 224, ImageNet stats, forward_features) and
    ``embed.py``'s centring, with tensors instead of PIL so gradients flow."""
    x = (images.float().clamp(-1, 1) + 1.0) / 2.0
    x = F.interpolate(x, size=(224, 224), mode="bicubic", align_corners=False)
    m = torch.tensor(IMAGENET_MEAN, device=x.device).view(1, 3, 1, 1)
    s = torch.tensor(IMAGENET_STD, device=x.device).view(1, 3, 1, 1)
    x = (x - m) / s
    with torch.autocast("cuda", dtype=torch.float16, enabled=x.is_cuda):
        feats = dofa.forward_features(x, RGB_WAVELENGTHS_UM)
    e = feats.float()
    e = e / e.norm(dim=1, keepdim=True).clamp_min(1e-12)
    if mean_vec is not None:
        e = e - mean_vec
        e = e / e.norm(dim=1, keepdim=True).clamp_min(1e-12)
    return e


def random_views(img: torch.Tensor, n: int, g: torch.Generator) -> torch.Tensor:
    """``n`` random rotations/flips/crops of ``img`` (1, 3, H, W), differentiable.

    Averaging the score over such views is "expectation over transformation": a
    pixel-level perturbation that fools the encoder on one view rarely survives a
    rotation and a crop, while a change in what the image *shows* does. Without it
    the gradient finds adversarial noise, not new terrain (finding 12)."""
    out = []
    H = img.shape[-1]
    for _ in range(n):
        v = img
        k = int(torch.randint(0, 4, (1,), generator=g, device=img.device))
        v = torch.rot90(v, k, dims=(2, 3))
        if bool(torch.rand(1, generator=g, device=img.device) < 0.5):
            v = torch.flip(v, dims=(3,))
        s = int(H * (0.75 + 0.25 * float(torch.rand(1, generator=g, device=img.device))))
        y = int(torch.randint(0, H - s + 1, (1,), generator=g, device=img.device))
        x = int(torch.randint(0, H - s + 1, (1,), generator=g, device=img.device))
        v = v[:, :, y : y + s, x : x + s]
        out.append(v)
    return torch.cat([F.interpolate(v, size=(H, H), mode="bilinear", align_corners=False) for v in out], dim=0)


# --- guided sampling -----------------------------------------------------------------


def dream_once(
    unet,
    vae,
    scheduler,
    prompt_emb: torch.Tensor,
    dofa: torch.nn.Module,
    mean_vec: torch.Tensor | None,
    history: torch.Tensor,
    taste: torch.Tensor | None,
    taste_weight: float,
    j: int,
    res: int,
    steps: int,
    seed: int,
    guidance_scale: float,
    window: tuple[float, float],
    iters: int,
    device: str,
    progress: str | None = None,
    n_views: int = 0,
) -> tuple[Image.Image, list[dict[str, float]]]:
    """One guided DDIM sample. ``guidance_scale = 0`` gives the unguided control.
    Returns the image and a per-step trace of the differentiable score."""
    g = torch.Generator(device=device).manual_seed(seed)
    x = torch.randn((1, 4, res // 8, res // 8), generator=g, device=device, dtype=torch.float32)
    scheduler.set_timesteps(steps, device=device)
    ts = scheduler.timesteps
    ac = scheduler.alphas_cumprod.to(device)
    emb = prompt_emb.to(torch.float16)
    trace: list[dict[str, float]] = []
    it = tqdm(list(enumerate(ts)), desc=progress, unit="step", leave=False) if progress else enumerate(ts)
    for i, t in it:
        frac = float(t) / scheduler.config.num_train_timesteps  # 1 = pure noise, 0 = clean
        a_t = ac[t]
        a_prev = ac[ts[i + 1]] if i + 1 < len(ts) else torch.tensor(1.0, device=device)
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
            eps = unet(x.half(), t, encoder_hidden_states=emb).sample.float()
        x0 = (x - (1 - a_t).sqrt() * eps) / a_t.sqrt()
        guided = guidance_scale > 0 and window[1] <= frac <= window[0]
        score_val = None
        if guided:
            for _ in range(iters):
                x0g = x0.detach().requires_grad_(True)
                with torch.autocast("cuda", dtype=torch.float16):
                    img = vae.decode(x0g.half() / vae.config.scaling_factor).sample
                views = random_views(img, n_views, g) if n_views > 0 else img
                e = dofa_embed_differentiable(views, dofa, mean_vec)
                score = torch.stack([novelty_torch(e[v : v + 1], history, j) for v in range(e.shape[0])]).mean()
                if taste is not None and taste_weight != 0.0:
                    score = score + taste_weight * (e @ taste).mean()
                (grad,) = torch.autograd.grad(score, x0g)
                step = guidance_scale * x0.norm() * grad / grad.norm().clamp_min(1e-12)
                x0 = (x0.detach() + step).detach()
                score_val = float(score)
        eps_hat = (x - a_t.sqrt() * x0) / (1 - a_t).sqrt()
        x = a_prev.sqrt() * x0 + (1 - a_prev).sqrt() * eps_hat
        trace.append({"t": int(t), "score": score_val if score_val is not None else float("nan")})
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
        img = vae.decode(x.half() / vae.config.scaling_factor).sample
    arr = ((img[0].float().clamp(-1, 1) + 1) * 127.5).round().to(torch.uint8).permute(1, 2, 0).cpu().numpy()
    return Image.fromarray(arr), trace


# --- the stage -----------------------------------------------------------------------


def run_dream(cfg: dict[str, Any], run_dir: str | Path, force: bool = False) -> Path:
    run_dir = Path(run_dir)
    out_json = run_dir / "dreams.json"
    if out_json.exists() and not force:
        print(f"[dream] exists, skipping: {out_json}")
        return out_json
    d = {**C.DEFAULTS["dream"], **(cfg.get("dream") or {})}
    with open(run_dir / "config.yaml", "r", encoding="utf-8") as f:
        run_cfg = yaml.safe_load(f)
    with open(run_dir / "summary.json", "r", encoding="utf-8") as f:
        summary = json.load(f)
    if run_cfg["encoder"]["name"] != "dofa_base":
        raise RuntimeError("the dream steers through DOFA; this run used another encoder")
    adapter = dream_dir(run_cfg) / "lora"
    if not (adapter / "adapter_config.json").exists():
        raise RuntimeError(f"no trained generator at {adapter}; run --stage dream-train first")

    device = pick_device(cfg["encoder"].get("device", "auto"))
    res = int(d["resolution"])
    j = int(d["j_history"] or run_cfg["agents"]["j_history"])
    taste_cfg = run_cfg["agents"].get("taste") or {}
    taste_weight = float(taste_cfg.get("weight", 0.0)) if d["include_taste"] else 0.0

    manifest = load_manifest(run_cfg)
    chip_to_row = {cid: i for i, cid in enumerate(manifest["chip_id"].tolist())}
    embs, _ = load_embeddings(run_cfg)
    index = load_index(run_cfg)
    mean_np = None
    if run_cfg["encoder"].get("center", True):
        ep = C.embeddings_path(run_cfg)
        mean_np = np.load(ep.with_name(ep.stem + "_mean.npy"))
    mean_vec = torch.from_numpy(mean_np).to(device) if mean_np is not None else None

    ecfg = {k: v for k, v in run_cfg["encoder"].items() if k != "resolved"}
    ecfg["device"] = device
    encoder = get_encoder(ecfg)
    dofa = encoder.model
    dofa.requires_grad_(False)

    from diffusers import DDIMScheduler

    scheduler = DDIMScheduler.from_pretrained(SD15, subfolder="scheduler")
    unet = load_unet_with_adapter(adapter, device)
    vae = load_vae(device)
    prompt_emb = empty_prompt_embedding(run_cfg, device)
    log = read_jsonl(run_dir / "log.jsonl")

    def score_image(im: Image.Image, hist_np: np.ndarray, taste_np: np.ndarray | None) -> dict[str, Any]:
        """Score a saved image exactly as the hiker scores a chip (non-differentiable path)."""
        e = encoder.encode([im])
        if mean_np is not None:
            e = e - mean_np
            e = e / np.maximum(np.linalg.norm(e, axis=1, keepdims=True), 1e-12)
        nov = float(novelty_scores(e, hist_np, j)[0])
        sims, idx = index.search(e.astype(np.float32), 1)
        rec = {"novelty": round(nov, 6), "nearest_chip": manifest["chip_id"].iloc[int(idx[0][0])], "nearest_chip_distance": round(float(1 - sims[0][0]), 6)}
        if taste_np is not None:
            rec["taste_similarity"] = round(float(e[0] @ taste_np), 6)
            rec["score"] = round(nov + taste_weight * float(e[0] @ taste_np), 6)
        else:
            rec["score"] = rec["novelty"]
        return rec

    records: list[dict[str, Any]] = []
    for ag in summary["agents"]:
        a = int(ag["agent_id"])
        trigger = "boredom" if ag["stop_reason"] == "boredom" else ("end_of_run" if d["at_end"] else None)
        if trigger is None:
            print(f"[dream] agent {a}: stopped by {ag['stop_reason']} and dream.at_end is off; no dream")
            continue
        rows = [chip_to_row[r["chip_id"]] for r in log if r["agent_id"] == a]
        hist_np = embs[rows]
        history = torch.from_numpy(hist_np).to(device)
        taste_np = None
        tp = run_dir / f"taste_agent_{a}.npy"
        if taste_weight != 0.0 and tp.exists():
            taste_np = np.load(tp)
            if not np.any(taste_np):
                taste_np = None
        taste = torch.from_numpy(taste_np).to(device) if taste_np is not None else None

        # The archive ceiling: the most novel real chip the agent had not visited.
        unvisited = np.setdiff1d(np.arange(embs.shape[0]), np.asarray(rows))
        ceil_scores = novelty_scores(embs[unvisited], hist_np, j)
        ci = int(np.argmax(ceil_scores))
        ceiling = {"chip_id": manifest["chip_id"].iloc[int(unvisited[ci])], "novelty": round(float(ceil_scores[ci]), 6)}

        seq_dir = run_dir / "sequence" / f"agent_{a}"
        seq_dir.mkdir(parents=True, exist_ok=True)
        candidates = []
        for k in range(int(d["n_candidates"])):
            seed = int(run_cfg["agents"]["seed"]) * 1000 + a * 100 + k
            im, trace = dream_once(
                unet, vae, scheduler, prompt_emb, dofa, mean_vec, history, taste, taste_weight, j, res,
                int(d["steps"]), seed, float(d["guidance_scale"]), tuple(d["guidance_window"]), int(d["guidance_iters"]),
                device, progress=f"dream agent {a} candidate {k}", n_views=int(d["guidance_views"]),
            )
            p = seq_dir / f"dream_{k}.png"
            im.save(p)
            ctrl, _ = dream_once(
                unet, vae, scheduler, prompt_emb, dofa, mean_vec, history, taste, taste_weight, j, res,
                int(d["steps"]), seed, 0.0, tuple(d["guidance_window"]), 1, device, progress=f"control agent {a} candidate {k}",
            )
            pc = seq_dir / f"dream_{k}_control.png"
            ctrl.save(pc)
            sc = score_image(Image.open(p).convert("RGB"), hist_np, taste_np)
            scc = score_image(Image.open(pc).convert("RGB"), hist_np, taste_np)
            guided_trace = [x["score"] for x in trace if x["score"] == x["score"]]
            candidates.append(
                {
                    "candidate": k,
                    "seed": seed,
                    "image": str(p.relative_to(run_dir)),
                    "control_image": str(pc.relative_to(run_dir)),
                    "dream": sc,
                    "control": scc,
                    "guided_score_first_last": [round(guided_trace[0], 4), round(guided_trace[-1], 4)] if guided_trace else None,
                }
            )
            print(f"[dream] agent {a} candidate {k}: dream score {sc['score']:.3f} (novelty {sc['novelty']:.3f}) vs control {scc['score']:.3f}; nearest chip {sc['nearest_chip']} at {sc['nearest_chip_distance']:.3f}")
        best = max(candidates, key=lambda c: c["dream"]["score"])
        records.append(
            {
                "agent_id": a,
                "trigger": trigger,
                "stop_reason": ag["stop_reason"],
                "steps_taken": ag["steps_taken"],
                "history_size": len(rows),
                "final_running_mean_novelty": ag.get("novelty_final_running_mean"),
                "last_step_novelty": log[[i for i, r in enumerate(log) if r["agent_id"] == a][-1]]["novelty"],
                "archive_ceiling": ceiling,
                "j_history": j,
                "taste_weight": taste_weight if taste_np is not None else 0.0,
                "best_candidate": best["candidate"],
                "candidates": candidates,
            }
        )
    out = {
        "run_dir": run_dir.name,
        "generator": {"base_model": SD15, "adapter": str(adapter), "resolution": res, "prompt": ""},
        "guidance": {
            "objective": "novelty(e, history, j) + taste_weight * cos(e, taste), e = centred DOFA embedding of the decoded x0 estimate",
            "scale": float(d["guidance_scale"]),
            "window_noise_fraction": list(d["guidance_window"]),
            "iters_per_step": int(d["guidance_iters"]),
            "views_per_step": int(d["guidance_views"]),
            "ddim_steps": int(d["steps"]),
            "n_candidates": int(d["n_candidates"]),
        },
        "agents": records,
        "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2) if torch.cuda.is_available() else None,
    }
    write_json(out_json, out)
    for r in records:
        b = r["candidates"][r["best_candidate"]]
        print(f"[dream] agent {r['agent_id']} ({r['trigger']}): best dream score {b['dream']['score']:.3f}, control {b['control']['score']:.3f}, archive ceiling {r['archive_ceiling']['novelty']:.3f}, last real step {r['last_step_novelty']:.3f}")
    return out_json
