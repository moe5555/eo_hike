"""Unconditional 64x64 DDPM (diffusers UNet2DModel) on one training set, weighted sampling.

    python -m gen.train_ddpm data/sets/baseline_s0 path_weighted --steps 15000
    python -m gen.train_ddpm --bench            # time 200 steps on random data
    python -m gen.train_ddpm data/sets/baseline_s0 path_weighted --bank data/crops/10m_64.npz \
        --out runs/baseline_s0/dreams_v2/models/10m_64_path_weighted --amp fp16      # dreams v2

Same architecture, init seed, data seed, steps and batch for every set. Each batch draws 64
tiles with replacement proportional to weight (torch.multinomial = WeightedRandomSampler),
then a random 64x64 crop, random flip and 90-degree rotation, all on the GPU.
Keeps an EMA of the weights (decay 0.999) for sampling. Writes runs/ddpm/<sets>/<set>/.

--bank: draw from a fixed crop bank (gen/hires.py) instead of cropping the 256 px tiles; each
crop inherits its tile's weight, then the same flip + 90-degree rotation. --amp fp16 (with a
GradScaler) for GPUs without bf16 tensor cores: on a Turing Quadro RTX 5000 bf16 autocast runs
at 2.25 s/step, fp16 at 0.29 s/step.
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


def make_unet(size: int = CROP):
    from diffusers import UNet2DModel

    if size == 128:  # dreams v2 Step B; attention at 16x16 and 8x8 as at 64 px
        return UNet2DModel(
            sample_size=128, in_channels=3, out_channels=3, layers_per_block=2,
            block_out_channels=(128, 128, 256, 256, 512),
            down_block_types=("DownBlock2D", "DownBlock2D", "DownBlock2D", "AttnDownBlock2D", "AttnDownBlock2D"),
            up_block_types=("AttnUpBlock2D", "AttnUpBlock2D", "UpBlock2D", "UpBlock2D", "UpBlock2D"),
        )
    return UNet2DModel(
        sample_size=CROP, in_channels=3, out_channels=3, layers_per_block=2,
        block_out_channels=(64, 128, 256, 256),
        down_block_types=("DownBlock2D", "DownBlock2D", "AttnDownBlock2D", "AttnDownBlock2D"),
        up_block_types=("AttnUpBlock2D", "AttnUpBlock2D", "UpBlock2D", "UpBlock2D"),
    )


def random_crops(tiles: torch.Tensor, ids: torch.Tensor, gen: torch.Generator, bank: bool = False) -> torch.Tensor:
    """tiles uint8 [N,256,256,3] -> float [B,3,64,64] in [-1,1], random crop + dihedral aug.

    bank=True: tiles is already a crop bank [M,px,px,3]; ids pick crops, no further cropping.
    """
    dev, Bn, H = tiles.device, len(ids), tiles.shape[1]
    if bank:
        x = tiles[ids]
    else:
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


def train(sets_dir: Path | None, set_name: str, steps: int, batch: int, seed: int, lr: float, bench: bool = False,
          bank_path: Path | None = None, out: Path | None = None, amp: str = "bf16") -> None:
    from diffusers import DDPMScheduler

    dev = "cuda"
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    size = CROP
    if bench:
        tiles = torch.randint(0, 256, (500, 256, 256, 3), dtype=torch.uint8, device=dev)
        weights = torch.ones(500, device=dev)
        out = None
    else:
        sets = pd.read_parquet(sets_dir / "sets.parquet")
        s = sets[sets.set == set_name]
        info = {"sets": str(sets_dir), "set": set_name, "steps": steps, "batch": batch, "seed": seed, "lr": lr, "n_tiles": len(s), "amp": amp}
        if bank_path is not None:
            bk = np.load(bank_path)
            keep = np.isin(bk["tile_idx"], s.tile_idx.to_numpy())
            w_tile = dict(zip(s.tile_idx.to_numpy(), s.weight.to_numpy()))
            tiles = torch.from_numpy(bk["crops"][keep]).to(dev)
            weights = torch.tensor([w_tile[t] for t in bk["tile_idx"][keep]], dtype=torch.float32, device=dev)
            size = tiles.shape[1]
            info.update(bank=str(bank_path), n_crops=int(keep.sum()), size=size)
        else:
            all_tiles = np.load(ROOT / "data" / "tiles.npy", mmap_mode="r")
            tiles = torch.from_numpy(np.ascontiguousarray(all_tiles[s.tile_idx.to_numpy()])).to(dev)
            weights = torch.tensor(s.weight.to_numpy(), dtype=torch.float32, device=dev)
        out = out or ROOT / "runs" / "ddpm" / sets_dir.name / set_name
        out.mkdir(parents=True, exist_ok=True)
        (out / "train.json").write_text(json.dumps(info, indent=2))

    amp_dtype = {"bf16": torch.bfloat16, "fp16": torch.float16}[amp]
    scaler = torch.amp.GradScaler(enabled=amp == "fp16")
    torch.manual_seed(seed)  # identical init for every set
    model = make_unet(size).to(dev)
    ema = make_unet(size).to(dev)
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
        x0 = random_crops(tiles, ids, gen, bank=bank_path is not None)
        noise = torch.randn(x0.shape, generator=gen, device=dev)
        t = torch.randint(0, sched.config.num_train_timesteps, (batch,), generator=gen, device=dev)
        xt = sched.add_noise(x0, noise, t)
        with torch.autocast("cuda", dtype=amp_dtype):
            pred = model(xt, t).sample
        loss = F.mse_loss(pred.float(), noise)
        opt.zero_grad(set_to_none=True)
        scaler.scale(loss).backward()
        scaler.unscale_(opt)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(opt)
        scaler.update()
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
    info = json.loads((out / "train.json").read_text())
    info.update(wall_clock_s=round(time.time() - t0, 1), gpu=torch.cuda.get_device_name(), finished=time.strftime("%Y-%m-%d %H:%M:%S"))
    (out / "train.json").write_text(json.dumps(info, indent=2))
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
    ap.add_argument("--bank", type=Path, help="crop bank .npz from gen/hires.py")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--amp", choices=["bf16", "fp16"], default="bf16")
    a = ap.parse_args()
    if a.bench:
        train(None, "bench", 200, a.batch, a.seed, a.lr, bench=True, amp=a.amp)
    else:
        train(a.sets_dir, a.set_name, a.steps, a.batch, a.seed, a.lr, bank_path=a.bank, out=a.out, amp=a.amp)
