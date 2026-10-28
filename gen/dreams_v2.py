"""Dreams v2: oversample, score with the agent's own perception, select, and novelty guidance.

    python -m gen.dreams_v2 sample runs/baseline_s0 10m_64_path_weighted     # N=512 pool
    python -m gen.dreams_v2 guide  runs/baseline_s0 10m_64_path_weighted     # lambda sweep on the random-32 seeds
    python -m gen.dreams_v2 report runs/baseline_s0                          # scores, selection, sheets, table

Models live in runs/<run>/dreams_v2/models/<res>_<px>_<set>/ (gen/train_ddpm.py --out).

Scoring (agent's final.pt autoencoder + archive.npz, nothing pretrained): 16 random crops of a
sample, each CROP_FRAC of its side, area-resized to the AE's 32x32 input; mean latent over the
16; novelty = mean distance to the k_nn=10 nearest archive latents; surprise = mean recon MSE.
Scoring crops come from a fixed generator, so every sample and model is scored on the same
crop positions.

Sampling: full 1000-step DDPM ancestral sampling (diffusers' linear betas, fixed_small
variance, x0 clipped to [-1, 1]), written out so guidance can enter. Noise is per *seed id*:
every step draws noise for all N seed ids from one generator and keeps the rows it needs, so
seed i gets the same initial and per-step noise in every model and in every batch layout.

Guidance (universal-guidance style, gradient through the agent's encoder only, not the UNet):
at each step, x0_hat = (x_t - sqrt(1-abar) eps) / sqrt(abar), clipped; g = d novelty(x0_hat) / d x0_hat
(fresh random scoring crops each step), normalised per sample to unit RMS; then
eps <- eps - lambda * sqrt(1-abar) * g. That moves x0_hat by lambda*(1-abar)/sqrt(abar)*g and the
posterior mean by about lambda*beta_t*g, so the push is strongest at high noise. No clipping
beyond the usual x0 clip.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.model import ConvAE  # noqa: E402

N_POOL = 512
N_KEEP = 32
WUNDT = 0.02          # drop this top fraction by novelty before selecting
CROP_FRAC = 0.75      # scoring crop side relative to the sample side (48 px of 64)
N_SCORE_CROPS = 16
SEED = 1234           # noise seed shared by every model (as v1)
SEL_SEED = 7          # which 32 seed ids form the random reference
SCORE_SEED = 99       # scoring crop positions
LAMBDAS = (0.0, 1.0, 3.0, 10.0)
REAL_N = 128          # real crops scored per model as a reference


def out_dir(run: Path) -> Path:
    return run / "dreams_v2"


def random_ids() -> np.ndarray:
    return np.sort(np.random.default_rng(SEL_SEED).choice(N_POOL, N_KEEP, replace=False))


def to_unit(u8: np.ndarray, dev: str) -> torch.Tensor:
    """uint8 [B,H,W,3] -> float [B,3,H,W] in [0,1]."""
    return torch.from_numpy(u8).to(dev).permute(0, 3, 1, 2).float() / 255.0


class Agent:
    """The walker's own perception: final AE and its archive of visited-tile latents."""

    def __init__(self, run: Path, dev: str) -> None:
        cfg = yaml.safe_load((run / "config.yaml").read_text())
        self.k, self.crop_px, self.dev = int(cfg["k_nn"]), int(cfg["crop_px"]), dev
        self.ae = ConvAE().to(dev)
        self.ae.load_state_dict(torch.load(run / "final.pt", map_location=dev, weights_only=False)["model"])
        self.ae.eval().requires_grad_(False)
        self.archive = torch.from_numpy(np.load(run / "archive.npz")["z"]).to(dev)

    def crops(self, x: torch.Tensor, gen: torch.Generator) -> torch.Tensor:
        """x [B,3,H,W] in [0,1] -> [B,K,3,32,32]; differentiable in x."""
        B, _, H, _ = x.shape
        P, K = round(H * CROP_FRAC), N_SCORE_CROPS
        oy = torch.randint(0, H - P + 1, (B, K), generator=gen, device=x.device)
        ox = torch.randint(0, H - P + 1, (B, K), generator=gen, device=x.device)
        ar = torch.arange(P, device=x.device)
        bi = torch.arange(B, device=x.device)[:, None, None, None]
        c = x.permute(0, 2, 3, 1)[bi, (oy[..., None] + ar)[:, :, :, None], (ox[..., None] + ar)[:, :, None, :]]  # B K P P 3
        c = c.permute(0, 1, 4, 2, 3).reshape(B * K, 3, P, P)
        return F.interpolate(c, size=(32, 32), mode="area").view(B, K, 3, 32, 32)

    def novelty(self, x: torch.Tensor, gen: torch.Generator) -> torch.Tensor:
        c = self.crops(x, gen)
        z = self.ae.encode(c.flatten(0, 1)).view(len(x), N_SCORE_CROPS, -1).mean(1)
        return torch.cdist(z, self.archive).topk(self.k, dim=1, largest=False).values.mean(1)

    @torch.no_grad()
    def score(self, u8: np.ndarray, batch: int = 256) -> tuple[np.ndarray, np.ndarray]:
        """uint8 images -> (novelty, surprise), on fixed crop positions."""
        gen = torch.Generator(device=self.dev).manual_seed(SCORE_SEED)
        nov, sur = [], []
        for b0 in range(0, len(u8), batch):
            x = to_unit(u8[b0 : b0 + batch], self.dev)
            c = self.crops(x, gen).flatten(0, 1)
            z = self.ae.encode(c).view(len(x), N_SCORE_CROPS, -1).mean(1)
            nov.append(torch.cdist(z, self.archive).topk(self.k, dim=1, largest=False).values.mean(1))
            sur.append(((self.ae(c) - c) ** 2).flatten(1).mean(1).view(len(x), N_SCORE_CROPS).mean(1))
        return torch.cat(nov).cpu().numpy(), torch.cat(sur).cpu().numpy()


def load_unet(model_dir: Path, dev: str):
    from diffusers import UNet2DModel

    return UNet2DModel.from_pretrained(model_dir / "ema").to(dev).eval()


def ddpm_sample(unet, ids: np.ndarray, lam: np.ndarray | None = None, agent: Agent | None = None,
                n_total: int = N_POOL, seed: int = SEED, batch: int = 128, dev: str = "cuda") -> np.ndarray:
    """DDPM ancestral sampling for seed ids `ids` (repeats allowed), optional per-row novelty guidance."""
    from diffusers import DDPMScheduler

    S = unet.config.sample_size
    acp = DDPMScheduler(num_train_timesteps=1000).alphas_cumprod.to(dev, torch.float32)
    one = torch.tensor(1.0, device=dev)
    out = []
    for b0 in range(0, len(ids), batch):
        bid = torch.as_tensor(ids[b0 : b0 + batch], device=dev)
        lb = None if lam is None else torch.as_tensor(lam[b0 : b0 + batch], device=dev, dtype=torch.float32)[:, None, None, None]
        guided = lb is not None and bool((lb > 0).any())
        gen = torch.Generator(device=dev).manual_seed(seed)
        ggen = torch.Generator(device=dev).manual_seed(seed + 1)
        x = torch.randn((n_total, 3, S, S), generator=gen, device=dev)[bid]
        for t in range(999, -1, -1):
            a, a_prev = acp[t], (acp[t - 1] if t > 0 else one)
            with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16, enabled=dev == "cuda"):
                eps = unet(x, t).sample.float()
            if guided:
                with torch.enable_grad():
                    x0 = ((x - (1 - a).sqrt() * eps) / a.sqrt()).clamp(-1, 1).requires_grad_(True)
                    (g,) = torch.autograd.grad(agent.novelty((x0 + 1) / 2, ggen).sum(), x0)
                g = g / (g.flatten(1).pow(2).mean(1).sqrt()[:, None, None, None] + 1e-12)
                eps = eps - lb * (1 - a).sqrt() * g
            x0 = ((x - (1 - a).sqrt() * eps) / a.sqrt()).clamp(-1, 1)
            beta = 1 - a / a_prev
            mean = (a_prev.sqrt() * beta / (1 - a)) * x0 + ((1 - beta).sqrt() * (1 - a_prev) / (1 - a)) * x
            if t > 0:
                var = ((1 - a_prev) / (1 - a) * beta).clamp(min=1e-20)
                x = mean + var.sqrt() * torch.randn((n_total, 3, S, S), generator=gen, device=dev)[bid]
            else:
                x = mean
        out.append(((x.clamp(-1, 1) + 1) * 127.5).round().byte().permute(0, 2, 3, 1).cpu().numpy())
        print(f"[dreams_v2] {b0 + len(bid)}/{len(ids)}", flush=True)
    return np.concatenate(out)


def cmd_sample(run: Path, model: str, n: int) -> None:
    import time

    d = out_dir(run) / "samples" / model
    d.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    unet = load_unet(out_dir(run) / "models" / model, "cuda")
    imgs = ddpm_sample(unet, np.arange(n), n_total=n)
    np.save(d / "pool.npy", imgs)
    (d / "pool.json").write_text(json.dumps({"n": n, "seed": SEED, "sec": round(time.time() - t0, 1)}, indent=2))
    print(f"[dreams_v2] {model}: pool {imgs.shape} in {time.time() - t0:.0f}s")


def cmd_guide(run: Path, model: str, lambdas: tuple[float, ...] = LAMBDAS, tag: str = "") -> None:
    """Guided samples on the random-32 seed ids -> guided[_tag].npy [L,32,H,W,3]."""
    import time

    d = out_dir(run) / "samples" / model
    d.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    unet = load_unet(out_dir(run) / "models" / model, "cuda")
    agent = Agent(run, "cuda")
    rid = random_ids()
    ids = np.tile(rid, len(lambdas))
    lam = np.repeat(np.array(lambdas, dtype=np.float32), len(rid))
    imgs = ddpm_sample(unet, ids, lam=lam, agent=agent)
    name = "guided" + (f"_{tag}" if tag else "")
    np.save(d / f"{name}.npy", imgs.reshape(len(lambdas), len(rid), *imgs.shape[1:]))
    (d / f"{name}.json").write_text(json.dumps({"lambdas": list(lambdas), "seed_ids": rid.tolist(), "seed": SEED, "sec": round(time.time() - t0, 1)}, indent=2))
    print(f"[dreams_v2] {model}: {name} {imgs.shape} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sample", "guide", "report"])
    ap.add_argument("run", type=Path)
    ap.add_argument("model", nargs="?")
    ap.add_argument("--n", type=int, default=N_POOL)
    ap.add_argument("--lambdas", help="comma-separated, e.g. 0.03,0.1,0.3 (default: the brief's 0,1,3,10)")
    ap.add_argument("--tag", default="", help="suffix for an extra guided file, e.g. low")
    a = ap.parse_args()
    if a.cmd == "sample":
        cmd_sample(a.run, a.model, a.n)
    elif a.cmd == "guide":
        lams = tuple(float(v) for v in a.lambdas.split(",")) if a.lambdas else LAMBDAS
        cmd_guide(a.run, a.model, lams, a.tag)
    else:
        from gen.dreams_v2_report import report

        report(a.run)
