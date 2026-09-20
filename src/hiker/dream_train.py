"""Fine-tune Stable Diffusion 1.5 on the archive's chips with a LoRA (the "dream" generator).

Why this setup
--------------
- **SD 1.5, not larger.** The UNet fits the 8 GB laptop GPU in fp16 with gradient
  checkpointing at 256 px; SDXL does not.
- **LoRA on the UNet attention layers**, base weights frozen. A few million trainable
  parameters, a few hundred MB of optimizer state, and the base model's knowledge of
  what aerial imagery looks like is kept.
- **No text.** Every chip is trained under the *empty* prompt. The text encoder runs
  once, its output for "" is cached, and the text encoder is never loaded again. The
  generator therefore has exactly one condition, "a chip from this archive", and the
  only thing that will steer it at sampling time is the agent's novelty score
  (``dream.py``). Language stays out, as the brief wants.
- **Latents are precomputed.** Each chip is encoded once through the frozen VAE at
  256 px and cached (``latents_sd15_256.npy``, 8.7k x 4 x 32 x 32 fp16 = 70 MB), so the
  training loop touches only the UNet. Augmentation is horizontal/vertical flips and
  90-degree rotations applied to the latent (valid for nadir imagery: there is no up).

Outputs go to ``<data_root>/models/dream_<dataset_key>/``: ``lora/`` (peft adapter),
``train_log.jsonl`` (loss per 50 steps), ``samples_<step>.png`` (unguided grid, to eyeball
progress), ``train_meta.json``.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image
from tqdm import tqdm

from . import config as C
from .encoders.base import pick_device
from .ingest import load_manifest

SD15 = "stable-diffusion-v1-5/stable-diffusion-v1-5"


def dream_dir(cfg: dict[str, Any]) -> Path:
    return C.data_root(cfg) / "models" / f"dream_{cfg['dataset']['key']}"


def latents_path(cfg: dict[str, Any], res: int) -> Path:
    return C.processed_dir(cfg) / f"latents_sd15_{res}.npy"


def empty_prompt_path(cfg: dict[str, Any]) -> Path:
    return C.processed_dir(cfg) / "sd15_empty_prompt.pt"


def load_vae(device: str):
    from diffusers import AutoencoderKL

    vae = AutoencoderKL.from_pretrained(SD15, subfolder="vae", torch_dtype=torch.float16)
    vae.requires_grad_(False)
    return vae.to(device).eval()


def empty_prompt_embedding(cfg: dict[str, Any], device: str) -> torch.Tensor:
    """CLIP text embedding of "" (77 x 768), computed once and cached. The text encoder
    is loaded only here."""
    p = empty_prompt_path(cfg)
    if p.exists():
        return torch.load(p, map_location=device)
    from transformers import CLIPTextModel, CLIPTokenizer

    tok = CLIPTokenizer.from_pretrained(SD15, subfolder="tokenizer")
    enc = CLIPTextModel.from_pretrained(SD15, subfolder="text_encoder", torch_dtype=torch.float16).to(device)
    ids = tok([""], padding="max_length", max_length=tok.model_max_length, return_tensors="pt").input_ids.to(device)
    with torch.no_grad():
        emb = enc(ids)[0].detach().cpu()
    torch.save(emb, p)
    del enc
    torch.cuda.empty_cache()
    return emb.to(device)


@torch.no_grad()
def precompute_latents(cfg: dict[str, Any], res: int, device: str, batch_size: int = 32) -> np.ndarray:
    """VAE-encode every chip of the manifest at ``res`` px. Cached as fp16, scaled by
    the VAE's scaling factor so the array is directly what the UNet is trained on."""
    p = latents_path(cfg, res)
    if p.exists():
        return np.load(p, mmap_mode="r")
    manifest = load_manifest(cfg)
    root = C.processed_dir(cfg)
    paths = [root / q for q in manifest["path"].tolist()]
    vae = load_vae(device)
    out = np.empty((len(paths), 4, res // 8, res // 8), dtype=np.float16)
    for s in tqdm(range(0, len(paths), batch_size), desc=f"vae latents {res}px", unit="batch"):
        ims = [Image.open(q).convert("RGB").resize((res, res), Image.BICUBIC) for q in paths[s : s + batch_size]]
        x = torch.from_numpy(np.stack([np.asarray(im, dtype=np.float32) for im in ims])).permute(0, 3, 1, 2)
        x = (x / 127.5 - 1.0).to(device, torch.float16)
        z = vae.encode(x).latent_dist.sample() * vae.config.scaling_factor
        out[s : s + len(ims)] = z.cpu().numpy().astype(np.float16)
    tmp = p.with_name(p.name + ".part")
    with open(tmp, "wb") as f:
        np.save(f, out)
    tmp.replace(p)
    del vae
    torch.cuda.empty_cache()
    return np.load(p, mmap_mode="r")


def augment(z: torch.Tensor, rng: np.random.Generator) -> torch.Tensor:
    """Random flips and 90-degree rotations of a latent batch (nadir imagery has no up)."""
    out = []
    for i in range(z.shape[0]):
        zi = z[i]
        k = int(rng.integers(0, 4))
        zi = torch.rot90(zi, k, dims=(1, 2))
        if rng.random() < 0.5:
            zi = torch.flip(zi, dims=(2,))
        out.append(zi)
    return torch.stack(out)


def build_unet_with_lora(rank: int, device: str):
    from diffusers import UNet2DConditionModel
    from peft import LoraConfig

    unet = UNet2DConditionModel.from_pretrained(SD15, subfolder="unet", torch_dtype=torch.float16)
    unet.requires_grad_(False)
    lcfg = LoraConfig(r=rank, lora_alpha=rank, init_lora_weights="gaussian", target_modules=["to_k", "to_q", "to_v", "to_out.0"])
    unet.add_adapter(lcfg)
    # LoRA params train in fp32 for stability under autocast.
    for p in unet.parameters():
        if p.requires_grad:
            p.data = p.data.float()
    return unet.to(device)


@torch.no_grad()
def sample_grid(unet, vae, scheduler, prompt_emb: torch.Tensor, res: int, n: int, seed: int, device: str, steps: int = 30) -> Image.Image:
    """Unguided samples under the empty prompt, for eyeballing training progress."""
    g = torch.Generator(device=device).manual_seed(seed)
    x = torch.randn((n, 4, res // 8, res // 8), generator=g, device=device, dtype=torch.float16)
    scheduler.set_timesteps(steps, device=device)
    x = x * scheduler.init_noise_sigma
    emb = prompt_emb.expand(n, -1, -1).to(torch.float16)
    unet.eval()
    for t in scheduler.timesteps:
        with torch.autocast("cuda", dtype=torch.float16):
            eps = unet(scheduler.scale_model_input(x, t), t, encoder_hidden_states=emb).sample
        x = scheduler.step(eps, t, x).prev_sample
    ims = vae.decode(x / vae.config.scaling_factor).sample
    ims = ((ims.clamp(-1, 1) + 1) * 127.5).round().to(torch.uint8).permute(0, 2, 3, 1).cpu().numpy()
    cols = int(math.ceil(math.sqrt(n)))
    rows = int(math.ceil(n / cols))
    sheet = Image.new("RGB", (cols * res, rows * res))
    for i, im in enumerate(ims):
        sheet.paste(Image.fromarray(im), ((i % cols) * res, (i // cols) * res))
    return sheet


def run_dream_train(cfg: dict[str, Any], force: bool = False) -> Path:
    d = cfg["dream"]
    out = dream_dir(cfg)
    adapter = out / "lora"
    if (adapter / "adapter_config.json").exists() and not force:
        print(f"[dream-train] adapter exists, skipping: {adapter}")
        return adapter
    out.mkdir(parents=True, exist_ok=True)
    device = pick_device(cfg["encoder"].get("device", "auto"))
    res = int(d["resolution"])
    rng = np.random.default_rng(int(d["seed"]))
    torch.manual_seed(int(d["seed"]))

    latents = precompute_latents(cfg, res, device)
    prompt_emb = empty_prompt_embedding(cfg, device)
    from diffusers import DDIMScheduler, DDPMScheduler

    noise_sched = DDPMScheduler.from_pretrained(SD15, subfolder="scheduler")
    sample_sched = DDIMScheduler.from_pretrained(SD15, subfolder="scheduler")
    unet = build_unet_with_lora(int(d["lora_rank"]), device)
    unet.enable_gradient_checkpointing()
    params = [p for p in unet.parameters() if p.requires_grad]
    n_train = sum(p.numel() for p in params)
    opt = torch.optim.AdamW(params, lr=float(d["lr"]), weight_decay=1e-2)
    scaler = torch.amp.GradScaler("cuda")
    vae = load_vae(device)

    bs = int(d["batch_size"])
    max_steps = int(d["train_steps"])
    max_minutes = float(d["max_minutes"])
    sample_every = int(d["sample_every"])
    log_path = out / "train_log.jsonl"
    t0 = time.time()
    N = latents.shape[0]
    unet.train()
    pbar = tqdm(range(1, max_steps + 1), desc="lora", unit="step")
    losses: list[float] = []
    stop_reason = "max_steps"
    with open(log_path, "w", encoding="utf-8") as logf:
        for step in pbar:
            idx = np.sort(rng.choice(N, size=bs, replace=False))
            z0 = torch.from_numpy(np.asarray(latents[idx], dtype=np.float32)).to(device)
            z0 = augment(z0, rng)
            noise = torch.randn_like(z0)
            t = torch.randint(0, noise_sched.config.num_train_timesteps, (bs,), device=device).long()
            zt = noise_sched.add_noise(z0, noise, t)
            emb = prompt_emb.expand(bs, -1, -1)
            with torch.autocast("cuda", dtype=torch.float16):
                pred = unet(zt.half(), t, encoder_hidden_states=emb.half()).sample
                loss = torch.nn.functional.mse_loss(pred.float(), noise)
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            scaler.step(opt)
            scaler.update()
            losses.append(float(loss))
            if step % 50 == 0:
                rec = {"step": step, "loss": float(np.mean(losses[-50:])), "minutes": round((time.time() - t0) / 60, 2)}
                logf.write(json.dumps(rec) + "\n")
                logf.flush()
                pbar.set_postfix(loss=f"{rec['loss']:.4f}", min=rec["minutes"])
            if step % sample_every == 0 or step == max_steps:
                unet.eval()
                sample_grid(unet, vae, sample_sched, prompt_emb, res, 9, seed=0, device=device).save(out / f"samples_{step:05d}.png")
                unet.train()
                _save_adapter(unet, adapter)
            if (time.time() - t0) / 60 > max_minutes:
                stop_reason = "max_minutes"
                break
    unet.eval()
    _save_adapter(unet, adapter)
    sample_grid(unet, vae, sample_sched, prompt_emb, res, 9, seed=0, device=device).save(out / f"samples_{step:05d}.png")
    meta = {
        "base_model": SD15,
        "resolution": res,
        "lora_rank": int(d["lora_rank"]),
        "trainable_params": n_train,
        "batch_size": bs,
        "lr": float(d["lr"]),
        "steps_done": step,
        "stop_reason": stop_reason,
        "minutes": round((time.time() - t0) / 60, 1),
        "final_loss_50": float(np.mean(losses[-50:])) if losses else None,
        "prompt": "",
        "augmentation": "rot90 + hflip on latents",
        "n_chips": int(N),
        "dataset_key": cfg["dataset"]["key"],
        "seed": int(d["seed"]),
        "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2) if torch.cuda.is_available() else None,
    }
    with open(out / "train_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"[dream-train] {step} steps in {meta['minutes']} min, loss {meta['final_loss_50']:.4f}, adapter at {adapter}")
    return adapter


def _save_adapter(unet, adapter: Path) -> None:
    from peft.utils import get_peft_model_state_dict

    adapter.mkdir(parents=True, exist_ok=True)
    sd = get_peft_model_state_dict(unet)
    from safetensors.torch import save_file

    save_file({k: v.detach().cpu().contiguous() for k, v in sd.items()}, adapter / "adapter_model.safetensors")
    cfg = unet.peft_config["default"].to_dict() if hasattr(unet, "peft_config") else {}
    cfg = {k: (list(v) if isinstance(v, (set, tuple)) else v) for k, v in cfg.items()}
    with open(adapter / "adapter_config.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, default=str)


def load_unet_with_adapter(adapter: Path, device: str):
    """UNet with the trained LoRA merged in, fp16, no grads. Used by ``dream.py``."""
    from diffusers import UNet2DConditionModel
    from peft import LoraConfig, set_peft_model_state_dict
    from safetensors.torch import load_file

    unet = UNet2DConditionModel.from_pretrained(SD15, subfolder="unet", torch_dtype=torch.float16)
    with open(adapter / "adapter_config.json", "r", encoding="utf-8") as f:
        acfg = json.load(f)
    lcfg = LoraConfig(r=int(acfg["r"]), lora_alpha=int(acfg["lora_alpha"]), target_modules=list(acfg["target_modules"]))
    unet.add_adapter(lcfg)
    set_peft_model_state_dict(unet, load_file(adapter / "adapter_model.safetensors"))
    unet.requires_grad_(False)
    return unet.to(device).eval()
