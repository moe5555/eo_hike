"""Sample 64 images from a trained DDPM's EMA weights, same noise seed for every model.

    python -m gen.sample runs/ddpm/baseline_s0/path_weighted

Full 1000-step DDPM ancestral sampling. The generator is reseeded identically for every
model, so initial noise and per-step noise match across models (differences are the model's).
Writes samples.npy (uint8 [64,64,64,3]) and samples.png (8x8 grid) into the model dir.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
from PIL import Image


@torch.no_grad()
def sample(model_dir: Path, n: int = 64, seed: int = 1234, batch: int = 64) -> np.ndarray:
    from diffusers import DDPMScheduler, UNet2DModel

    dev = "cuda"
    unet = UNet2DModel.from_pretrained(model_dir / "ema").to(dev).eval()
    sched = DDPMScheduler(num_train_timesteps=1000)
    sched.set_timesteps(1000)
    gen = torch.Generator(device=dev).manual_seed(seed)
    out = []
    for b0 in range(0, n, batch):
        bn = min(batch, n - b0)
        x = torch.randn((bn, 3, 64, 64), generator=gen, device=dev)
        for t in sched.timesteps:
            with torch.autocast("cuda", dtype=torch.bfloat16):
                eps = unet(x, t).sample.float()
            x = sched.step(eps, t, x, generator=gen).prev_sample
        out.append(((x.clamp(-1, 1) + 1) * 127.5).round().byte().permute(0, 2, 3, 1).cpu().numpy())
    imgs = np.concatenate(out)
    np.save(model_dir / "samples.npy", imgs)
    g = int(np.ceil(np.sqrt(n)))
    grid = np.zeros((g * 66, g * 66, 3), np.uint8)
    for i, im in enumerate(imgs):
        r, c = divmod(i, g)
        grid[r * 66 + 1 : r * 66 + 65, c * 66 + 1 : c * 66 + 65] = im
    Image.fromarray(grid).save(model_dir / "samples.png")
    print(f"[sample] {model_dir} -> samples.npy {imgs.shape}")
    return imgs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("model_dirs", type=Path, nargs="+")
    ap.add_argument("--n", type=int, default=64)
    ap.add_argument("--seed", type=int, default=1234)
    a = ap.parse_args()
    for d in a.model_dirs:
        sample(d, a.n, a.seed)
