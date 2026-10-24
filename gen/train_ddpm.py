"""Unconditional 64x64 DDPM (diffusers UNet2DModel) on one training set, weighted sampling.

    python -m gen.train_ddpm data/sets/baseline_s0 path_weighted --steps 15000
    python -m gen.train_ddpm --bench            # time 200 steps on random data

Same architecture, init seed, data seed, steps and batch for every set. Each batch draws 64
tiles with replacement proportional to weight (torch.multinomial = WeightedRandomSampler),
then a random 64x64 crop, random flip and 90-degree rotation, all on the GPU.
Keeps an EMA of the weights (decay 0.999) for sampling. Writes runs/ddpm/<sets>/<set>/.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
CROP = 64


def make_unet():
    from diffusers import UNet2DModel

    return UNet2DModel(
        sample_size=CROP, in_channels=3, out_channels=3, layers_per_block=2,
        block_out_channels=(64, 128, 256, 256),
        down_block_types=("DownBlock2D", "DownBlock2D", "AttnDownBlock2D", "AttnDownBlock2D"),
        up_block_types=("AttnUpBlock2D", "AttnUpBlock2D", "UpBlock2D", "UpBlock2D"),
    )


def random_crops(tiles: torch.Tensor, ids: torch.Tensor, gen: torch.Generator) -> torch.Tensor:
    """tiles uint8 [N,256,256,3] -> float [B,3,64,64] in [-1,1], random crop + dihedral aug."""
    dev, Bn, H = tiles.device, len(ids), tiles.shape[1]
    oy = torch.randint(0, H - CROP + 1, (Bn,), generator=gen, device=dev)
    ox = torch.randint(0, H - CROP + 1, (Bn,), generator=gen, device=dev)
    ar = torch.arange(CROP, device=dev)
    x = tiles[ids[:, None, None], (oy[:, None] + ar)[:, :, None], (ox[:, None] + ar)[:, None, :]]  # B 64 64 3
    x = x.permute(0, 3, 1, 2).float() / 127.5 - 1.0
    rot = torch.randint(0, 4, (Bn,), generator=gen, device=dev)
    flip = torch.randint(0, 2, (Bn,), generator=gen, device=dev).bool()
    x = torch.where(flip[:, None, None, None], x.flip(-1), x)
    for k in (1, 2, 3):
        m = rot == k
        if bool(m.any()):
            x[m] = torch.rot90(x[m], k, dims=(-2, -1))
    return x


def train(sets_dir: Path | None, set_name: str, steps: int, batch: int, seed: int, lr: float, bench: bool = False) -> None:
    from diffusers import DDPMScheduler

    dev = "cuda"
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    if bench:
        tiles = torch.randint(0, 256, (500, 256, 256, 3), dtype=torch.uint8, device=dev)
        weights = torch.ones(500, device=dev)
        out = None
    else:
        sets = pd.read_parquet(sets_dir / "sets.parquet")
        s = sets[sets.set == set_name]
        all_tiles = np.load(ROOT / "data" / "tiles.npy", mmap_mode="r")
        tiles = torch.from_numpy(np.ascontiguousarray(all_tiles[s.tile_idx.to_numpy()])).to(dev)
        weights = torch.tensor(s.weight.to_numpy(), dtype=torch.float32, device=dev)
        out = ROOT / "runs" / "ddpm" / sets_dir.name / set_name
        out.mkdir(parents=True, exist_ok=True)
        (out / "train.json").write_text(json.dumps({"sets": str(sets_dir), "set": set_name, "steps": steps, "batch": batch, "seed": seed, "lr": lr, "n_tiles": len(s)}, indent=2))

    torch.manual_seed(seed)  # identical init for every set
    model = make_unet().to(dev)
    ema = make_unet().to(dev)
    ema.load_state_dict(model.state_dict())
    ema.requires_grad_(False)
    sched = DDPMScheduler(num_train_timesteps=1000)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.0)
    warm = 500
    lr_fn = lambda i: min(1.0, (i + 1) / warm)  # noqa: E731
    lrs = torch.optim.lr_scheduler.LambdaLR(opt, lr_fn)
    gen = torch.Generator(device=dev).manual_seed(seed)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"[ddpm] {set_name}: {len(weights)} tiles, {n_params / 1e6:.1f}M params, {steps} steps x {batch}", flush=True)

    log, t0 = [], time.time()
    for i in range(steps):
        ids = torch.multinomial(weights, batch, replacement=True, generator=gen)
        x0 = random_crops(tiles, ids, gen)
        noise = torch.randn(x0.shape, generator=gen, device=dev)
        t = torch.randint(0, sched.config.num_train_timesteps, (batch,), generator=gen, device=dev)
        xt = sched.add_noise(x0, noise, t)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            pred = model(xt, t).sample
        loss = F.mse_loss(pred.float(), noise)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        lrs.step()
        with torch.no_grad():
            d = min(0.999, (1 + i) / (10 + i))
            for pe, pm in zip(ema.parameters(), model.parameters()):
                pe.lerp_(pm, 1 - d)
        if (i + 1) % 100 == 0:
            log.append({"step": i + 1, "loss": float(loss), "sec": time.time() - t0})
            if (i + 1) % 1000 == 0 or bench:
                print(f"[ddpm] {set_name} step {i + 1} loss {float(loss):.4f} {time.time() - t0:.0f}s", flush=True)
        if out is not None and (i + 1) % 5000 == 0:
            ema.save_pretrained(out / "ema")
            pd.DataFrame(log).to_csv(out / "loss.csv", index=False)
    if bench:
        print(f"[ddpm] bench: {(time.time() - t0) / steps * 1000:.0f} ms/step, peak mem {torch.cuda.max_memory_allocated() / 1e9:.2f} GB")
        return
    ema.save_pretrained(out / "ema")
    pd.DataFrame(log).to_csv(out / "loss.csv", index=False)
    print(f"[ddpm] {set_name} done in {time.time() - t0:.0f}s -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("sets_dir", type=Path, nargs="?")
    ap.add_argument("set_name", nargs="?", default="path_weighted")
    ap.add_argument("--steps", type=int, default=15000)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--bench", action="store_true")
    a = ap.parse_args()
    if a.bench:
        train(None, "bench", 200, a.batch, a.seed, a.lr, bench=True)
    else:
        train(a.sets_dir, a.set_name, a.steps, a.batch, a.seed, a.lr)
