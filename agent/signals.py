"""Patches and the three per-candidate signals: surprise, novelty, progress. Plus EMA z-scores.

Everything is batched over candidates: patches are [C, K, 3, 32, 32] floats in [0, 1].
The progress probe clones the model once per candidate *functionally* (torch.func + vmap),
runs `s` fresh-Adam steps on half A and measures the error drop on half B.
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F
from torch.func import functional_call, grad, vmap

IN_PX = 32
TV_BLOCK = 4  # noisy-TV noise grain in tile pixels (4 px ~ 160 m), same as data/prepare.py
FIXED_CROP_SEED = 777


def fixed_offsets(ids: list[int], K: int, H: int, crop_px: int, device) -> tuple[torch.Tensor, torch.Tensor]:
    """Crop positions that depend only on the tile id: the same K crops every time a tile is looked at."""
    o = np.stack([np.random.default_rng([FIXED_CROP_SEED, int(i)]).integers(0, H - crop_px + 1, (2, K)) for i in ids])
    o = torch.from_numpy(o).to(device)
    return o[:, 0], o[:, 1]


def patches(img: torch.Tensor, is_tv: torch.Tensor, K: int, crop_px: int, gen: torch.Generator,
            offsets: tuple[torch.Tensor, torch.Tensor] | None = None) -> torch.Tensor:
    """K random crop_px crops per tile, area-resized to 32x32. img: uint8 [C, H, W, 3] on device
    (the candidates' tiles, already gathered; modified in place for noisy-TV tiles).
    offsets: (oy, ox), each [C, K], to use given crop positions (fixed_offsets) instead of random ones.

    Noisy-TV tiles (is_tv) are replaced by a fresh noise field every time they are looked at.
    """
    dev = img.device
    C, H = img.shape[0], img.shape[1]
    if bool(is_tv.any()):
        n = int(is_tv.sum())
        small = torch.randint(0, 256, (n, H // TV_BLOCK, H // TV_BLOCK, 3), generator=gen, device=dev, dtype=torch.uint8)
        img[is_tv] = small.repeat_interleave(TV_BLOCK, 1).repeat_interleave(TV_BLOCK, 2)
    if offsets is None:
        oy = torch.randint(0, H - crop_px + 1, (C, K), generator=gen, device=dev)
        ox = torch.randint(0, H - crop_px + 1, (C, K), generator=gen, device=dev)
    else:
        oy, ox = offsets
    ar = torch.arange(crop_px, device=dev)
    yy = (oy[..., None] + ar)[:, :, :, None]  # C K P 1
    xx = (ox[..., None] + ar)[:, :, None, :]  # C K 1 P
    ci = torch.arange(C, device=dev)[:, None, None, None]
    crops = img[ci, yy, xx]  # C K P P 3
    x = crops.permute(0, 1, 4, 2, 3).reshape(C * K, 3, crop_px, crop_px).float() / 255.0
    if crop_px != IN_PX:
        x = F.interpolate(x, size=(IN_PX, IN_PX), mode="area")
    return x.view(C, K, 3, IN_PX, IN_PX)


@torch.no_grad()
def recon_err(model, x: torch.Tensor) -> torch.Tensor:
    """Mean reconstruction MSE per candidate. x: [C, K, 3, 32, 32] -> [C]."""
    C, K = x.shape[:2]
    flat = x.flatten(0, 1)
    return ((model(flat) - flat) ** 2).flatten(1).mean(1).view(C, K).mean(1)


@torch.no_grad()
def mean_latent(model, x: torch.Tensor) -> torch.Tensor:
    C, K = x.shape[:2]
    return model.encode(x.flatten(0, 1)).view(C, K, -1).mean(1)


@torch.no_grad()
def novelty(z: torch.Tensor, archive: torch.Tensor | None, k: int, unit: bool = False) -> torch.Tensor:
    """Mean distance from each candidate latent to its k nearest archive latents (0 if archive empty).
    unit: compare L2-normalised latents (direction only), so 'loud' tiles with large latent norms don't win on norm."""
    if archive is None or len(archive) == 0:
        return torch.zeros(len(z), device=z.device)
    if unit:
        z, archive = F.normalize(z, dim=1), F.normalize(archive, dim=1)
    d = torch.cdist(z, archive)
    kk = min(k, archive.shape[0])
    return d.topk(kk, dim=1, largest=False).values.mean(1)


def progress_probe(model, x: torch.Tensor, lr: float, s: int, betas=(0.9, 0.999), eps: float = 1e-8):
    """Learning-progress probe per candidate.

    Split each candidate's K patches into halves A, B. On a functional clone of the model,
    run `s` Adam steps (fresh optimiser state) on A; return g = err_B(before) - err_B(after),
    plus err over all K patches before (= surprise), all as [C] tensors.
    """
    K = x.shape[1]
    xa, xb = x[:, : K // 2], x[:, K // 2 :]
    params = {k: v.detach() for k, v in model.named_parameters()}

    def loss(p, xx):
        return ((functional_call(model, p, (xx,)) - xx) ** 2).mean()

    gfn = grad(loss)

    def one(xa_, xb_):
        p = params
        before = loss(p, xb_)
        m = {k: torch.zeros_like(v) for k, v in p.items()}
        v2 = {k: torch.zeros_like(v) for k, v in p.items()}
        for t in range(1, s + 1):
            g = gfn(p, xa_)
            m = {k: betas[0] * m[k] + (1 - betas[0]) * g[k] for k in p}
            v2 = {k: betas[1] * v2[k] + (1 - betas[1]) * g[k] ** 2 for k in p}
            c1, c2 = 1 - betas[0] ** t, 1 - betas[1] ** t
            p = {k: p[k] - lr * (m[k] / c1) / ((v2[k] / c2).sqrt() + eps) for k in p}
        after = loss(p, xb_)
        return before - after, before, after

    g, before_b, after_b = vmap(one)(xa, xb)
    return g.detach(), before_b.detach(), after_b.detach()


class RunningNorm:
    """EMA mean/variance -> z-scores. Updated with every candidate batch, then applied to it.

    Warm-up: the rate is max(alpha, 1/t), i.e. a plain cumulative average for the first
    1/alpha batches, so early z-scores are not blown up by a near-zero initial variance.
    """

    def __init__(self, alpha: float = 0.02) -> None:
        self.alpha, self.mean, self.var, self.t = alpha, 0.0, 0.0, 0

    def __call__(self, x: torch.Tensor) -> torch.Tensor:
        self.t += 1
        a = max(self.alpha, 1.0 / self.t)
        self.mean = (1 - a) * self.mean + a * float(x.mean())
        self.var = (1 - a) * self.var + a * float(((x - self.mean) ** 2).mean())
        return (x - self.mean) / (self.var**0.5 + 1e-8)

    def state(self) -> dict:
        return {"mean": self.mean, "var": self.var}
