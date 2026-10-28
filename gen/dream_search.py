"""Dreams v3 search: latent variable evolution in a StyleGAN's W space, driven by the agent's own learning progress.

    .venv-sg/Scripts/python.exe -m gen.dream_search --gan base.pkl --agent_run runs/global_baseline_s0 --reach 1.0 --seed 0 --condition B
    .venv-sg/Scripts/python.exe -m gen.dream_search --gan base.pkl --agent_run runs/global_baseline_s0 --reach 0.7 1.0 1.5 2.0 3.0 --seed 0 1 2 --beta 0.3 0 --condition B
    .venv-sg/Scripts/python.exe -m gen.dream_search --gan base.pkl --plain 64 --tag base --out runs/global_baseline_s0/dreams_v3/reference

Scoring (only the searching agent's final autoencoder from its walk, nothing pretrained):
  dream (256 px at 10 m) -> 4x area downsample to 64 px (40 m, the walker's ground scale) -> K = 16 crops of the
  agent's crop_px (crop_px >= 64: the whole 64 px image, i.e. 16 identical views) -> area-resize to 32 px.
  g = learning progress, exactly the walker's probe (agent/signals.progress_probe): a functional clone, s = 3 fresh
  Adam steps on half A at the agent's lr, g = err_B(before) - err_B(after). The real agent is never updated.
  d = distance in the agent's latent space (mean latent over the 16 views) to the nearest dream already kept in this
  search (the union of all earlier elites, excluding the individual itself); 0 in generation 0.
  F = z(g) + beta * z(d), z-scored over the generation's population.

Search: W space (after the mapping network; one w broadcast to every synthesis layer, noise_mode const).
  init: z ~ N(0, I) -> w = mapping(z) -> w = w_avg + R (w - w_avg)
  mutation: w' = w + N(0, (sigma R)^2), sigma = 0.1 * std(W) per dimension from 10k mapped samples. No clamping.
  (mu + lambda): population 64; the top 16 by F survive; each survivor has 3 mutated children -> 16 + 48 = 64.
  30 generations (0..29). Survivors keep their g (deterministic views); d and F are recomputed every generation.

Per search writes <out>/search/<condition>_b<beta>/R<R>_s<seed>/: best_<gen>.png (the best image of every
generation), elites.npz (the final 16 images uint8, w, z-latents), log.parquet (every generation's 16 elites with
F, g, d, dist_from_w_avg, w). The report (gen/dreams_v3_report.py) joins these into dreams.parquet.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SG = ROOT / "third_party" / "stylegan3"
sys.path[:0] = [str(ROOT), str(SG)]
from agent import signals as S  # noqa: E402
from agent.model import ConvAE  # noqa: E402

POP, MU, GENS, K, PROBE_STEPS, SIGMA_FRAC, W_SAMPLES = 64, 16, 30, 16, 3, 0.1, 10_000


def load_gan(pkl: Path, dev: str):
    import dnnlib  # noqa: F401
    import legacy

    with open(pkl, "rb") as f:
        G = legacy.load_network_pkl(f)["G_ema"].to(dev).eval().requires_grad_(False)
    return G


@torch.no_grad()
def w_stats(G, dev: str) -> dict:
    """w_avg (the generator's tracked average), per-dim std(W) and typical |w - w_avg| from 10k mapped samples."""
    g = torch.Generator(device=dev).manual_seed(2**31 - 1)
    ws = torch.cat([G.mapping(torch.randn(1000, G.z_dim, generator=g, device=dev), None)[:, 0] for _ in range(W_SAMPLES // 1000)])
    w_avg = G.mapping.w_avg.detach().clone()
    return {"w_avg": w_avg, "std": ws.std(0), "r_typ": float((ws - w_avg).norm(dim=1).mean())}


@torch.no_grad()
def synth(G, w: torch.Tensor, bs: int = 32) -> torch.Tensor:
    """w [B, w_dim] -> images [B, 3, 256, 256] in [0, 1]."""
    out = []
    for i in range(0, len(w), bs):
        ws = w[i : i + bs].unsqueeze(1).repeat(1, G.num_ws, 1)
        out.append((G.synthesis(ws, noise_mode="const").clamp(-1, 1) + 1) / 2)
    return torch.cat(out)


class Agent:
    def __init__(self, run: Path, dev: str) -> None:
        self.cfg = yaml.safe_load((run / "config.yaml").read_text())
        self.model = ConvAE().to(dev)
        self.model.load_state_dict(torch.load(run / "final.pt", map_location=dev)["model"])
        self.model.eval()
        self.crop = int(self.cfg["crop_px"])
        self.lr = float(self.cfg["lr"])
        self.name = run.name

    def views(self, img: torch.Tensor, gen: torch.Generator) -> torch.Tensor:
        """[B, 3, 256, 256] at 10 m -> [B, K, 3, 32, 32] at the agent's ground scale."""
        x = F.avg_pool2d(img, 4)  # 64 px at 40 m
        B = len(x)
        if self.crop >= x.shape[-1]:
            v = F.interpolate(x, size=(S.IN_PX, S.IN_PX), mode="area")
            return v[:, None].expand(B, K, 3, S.IN_PX, S.IN_PX).contiguous()
        P = self.crop
        oy = torch.randint(0, x.shape[-1] - P + 1, (B, K), generator=gen, device=x.device)
        ox = torch.randint(0, x.shape[-1] - P + 1, (B, K), generator=gen, device=x.device)
        crops = torch.stack([torch.stack([x[b, :, oy[b, k] : oy[b, k] + P, ox[b, k] : ox[b, k] + P] for k in range(K)]) for b in range(B)])
        return F.interpolate(crops.flatten(0, 1), size=(S.IN_PX, S.IN_PX), mode="area").view(B, K, 3, S.IN_PX, S.IN_PX)

    @torch.no_grad()
    def latent(self, img: torch.Tensor, gen: torch.Generator) -> torch.Tensor:
        return S.mean_latent(self.model, self.views(img, gen))

    def score(self, img: torch.Tensor, gen: torch.Generator, bs: int = 64) -> tuple[torch.Tensor, torch.Tensor]:
        gs, zs = [], []
        for i in range(0, len(img), bs):
            x = self.views(img[i : i + bs], gen)
            g, _, _ = S.progress_probe(self.model, x, self.lr, PROBE_STEPS)
            gs.append(g)
            zs.append(S.mean_latent(self.model, x))
        return torch.cat(gs), torch.cat(zs)


def zscore(x: torch.Tensor) -> torch.Tensor:
    s = x.std()
    return (x - x.mean()) / s if s > 1e-12 else torch.zeros_like(x)


def to_u8(img: torch.Tensor) -> np.ndarray:
    return (img.clamp(0, 1) * 255 + 0.5).byte().permute(0, 2, 3, 1).cpu().numpy()


def search(G, ws: dict, agent: Agent, R: float, seed: int, beta: float, out: Path, meta: dict) -> pd.DataFrame:
    dev = ws["w_avg"].device
    out.mkdir(parents=True, exist_ok=True)
    gen = torch.Generator(device=dev).manual_seed(seed)
    vgen = torch.Generator(device=dev).manual_seed(10_000 + seed)
    w_avg, sig = ws["w_avg"], SIGMA_FRAC * ws["std"]
    with torch.no_grad():
        z = torch.randn(POP, G.z_dim, generator=gen, device=dev)
        w = G.mapping(z, None, truncation_psi=1.0)[:, 0]
    w = w_avg + R * (w - w_avg)
    g_cache: torch.Tensor | None = None  # g of the survivors (first MU rows) carried over
    ids = torch.arange(POP, device=dev)
    next_id = POP
    kept_z, kept_id = torch.empty(0, 64, device=dev), torch.empty(0, dtype=torch.long, device=dev)
    rows = []
    for gi in range(GENS):
        img = synth(G, w)
        if g_cache is None:
            g, zl = agent.score(img, vgen)
        else:
            g_new, z_new = agent.score(img[MU:], vgen)
            z_old = agent.latent(img[:MU], vgen)
            g, zl = torch.cat([g_cache, g_new]), torch.cat([z_old, z_new])
        if len(kept_z):
            dist = torch.cdist(zl, kept_z)
            dist[ids[:, None] == kept_id[None, :]] = float("inf")
            d = dist.min(1).values
            d[torch.isinf(d)] = 0.0
        else:
            d = torch.zeros(POP, device=dev)
        Fit = zscore(g) + beta * zscore(d)
        order = torch.argsort(Fit, descending=True)[:MU]
        dw = (w - w_avg).norm(dim=1)
        Image.fromarray(to_u8(img[order[:1]])[0]).save(out / f"best_{gi:02d}.png")
        for rk, j in enumerate(order.tolist()):
            rows.append({**meta, "R": R, "seed": seed, "beta": beta, "generation": gi, "rank": rk, "id": int(ids[j]),
                         "F": float(Fit[j]), "g": float(g[j]), "d": float(d[j]), "dist_from_w_avg": float(dw[j]),
                         "dist_rel": float(dw[j]) / ws["r_typ"], "pop_mean_dist_from_w_avg": float(dw.mean()),
                         "pop_mean_dist_rel": float(dw.mean()) / ws["r_typ"], "w": w[j].float().cpu().numpy()})
        new = ~torch.isin(ids[order], kept_id)
        kept_z = torch.cat([kept_z, zl[order][new]])
        kept_id = torch.cat([kept_id, ids[order][new]])
        if gi == GENS - 1:
            np.savez_compressed(out / "elites.npz", img=to_u8(img[order]), w=w[order].cpu().numpy(), z_agent=zl[order].cpu().numpy(),
                                F=Fit[order].cpu().numpy(), g=g[order].cpu().numpy(), d=d[order].cpu().numpy())
            break
        # (mu + lambda): survivors + 3 children each
        par_w, par_g, par_id = w[order], g[order], ids[order]
        kids = par_w.repeat_interleave((POP - MU) // MU, 0)
        kids = kids + torch.randn(kids.shape, generator=gen, device=dev) * sig * R
        w = torch.cat([par_w, kids])
        g_cache = par_g
        ids = torch.cat([par_id, torch.arange(next_id, next_id + len(kids), device=dev)])
        next_id += len(kids)
    df = pd.DataFrame(rows)
    df.to_parquet(out / "log.parquet")
    return df


def plain(G, n: int, out: Path, tag: str) -> None:
    """Reference samples (no search): seeds 0..n-1 at psi = 1."""
    dev = next(G.parameters()).device
    out.mkdir(parents=True, exist_ok=True)
    z = torch.stack([torch.from_numpy(np.random.RandomState(s).randn(G.z_dim)) for s in range(n)]).float().to(dev)
    with torch.no_grad():
        w = G.mapping(z, None, truncation_psi=1.0)[:, 0]
    u8 = to_u8(synth(G, w))
    np.savez_compressed(out / f"plain_{tag}.npz", img=u8, w=w.cpu().numpy())
    side = int(np.ceil(np.sqrt(n)))
    grid = np.zeros((side * 256, side * 256, 3), np.uint8)
    for i, a in enumerate(u8):
        grid[(i // side) * 256 : (i // side + 1) * 256, (i % side) * 256 : (i % side + 1) * 256] = a
    Image.fromarray(grid).save(out / f"plain_{tag}.png")
    print(f"[dream_search] {n} plain samples ({tag}) -> {out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gan", type=Path, required=True)
    ap.add_argument("--agent_run", type=Path)
    ap.add_argument("--reach", type=float, nargs="+", default=[1.0])
    ap.add_argument("--seed", type=int, nargs="+", default=[0])
    ap.add_argument("--beta", type=float, nargs="+", default=[0.3])
    ap.add_argument("--condition", default="X", help="label: A, B, C, A0")
    ap.add_argument("--gan_name", help="label for the GAN (default: pkl stem)")
    ap.add_argument("--out", type=Path, help="default: <agent_run>/dreams_v3")
    ap.add_argument("--plain", type=int, help="only write this many plain psi=1 samples")
    ap.add_argument("--tag", default="gan")
    a = ap.parse_args()
    dev = "cuda"
    G = load_gan(a.gan, dev)
    if a.plain:
        plain(G, a.plain, a.out, a.tag)
        return
    agent = Agent(a.agent_run, dev)
    out = a.out or a.agent_run / "dreams_v3"
    ws = w_stats(G, dev)
    meta = {"condition": a.condition, "agent": agent.name, "gan": a.gan_name or a.gan.stem, "gan_pkl": str(a.gan)}
    (out / "search").mkdir(parents=True, exist_ok=True)
    for beta in a.beta:
        for R in a.reach:
            for s in a.seed:
                t0 = time.time()
                d = search(G, ws, agent, R, s, beta, out / "search" / f"{a.condition}_b{beta:g}" / f"R{R:g}_s{s}", meta)
                last = d[d.generation == d.generation.max()]
                print(f"[dream_search] {a.condition} beta {beta:g} R {R:g} seed {s}: best g {last.g.max():.5f}  "
                      f"pop |w-w_avg|/r_typ {last.pop_mean_dist_rel.iloc[0]:.2f}  {time.time() - t0:.0f}s", flush=True)
    (out / "search" / f"{a.condition}_wstats.json").write_text(json.dumps({"r_typ": ws["r_typ"], "sigma_mean": float(SIGMA_FRAC * ws["std"].mean()), "gan": str(a.gan)}))


if __name__ == "__main__":
    main()
