"""The walk: candidates -> signals -> softmax choice -> train -> boredom -> log.

    python -m agent.walk configs/baseline.yaml --seed 1
    python -m agent.walk configs/baseline.yaml --steps 50 --name smoke     # quick test

Writes runs/<name>_s<seed>/: config.yaml, meta.json, steps.parquet, candidates.parquet,
heldout.parquet, ckpt_*.pt, final.pt, archive.npz, daydreams/*.png.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml
from PIL import Image

from agent import signals as S
from agent.model import ConvAE

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RUNS = ROOT / "runs"
HELDOUT_N, HELDOUT_SEED = 200, 12345


def load_data(device: str):
    import sys

    sys.path.insert(0, str(DATA))
    from prepare import haversine_km, neighbours  # noqa: E402

    idx = pd.read_parquet(DATA / "tiles.parquet")
    tiles = torch.from_numpy(np.load(DATA / "tiles.npy")).to(device)
    tv = torch.from_numpy(idx.tv.to_numpy().copy()).to(device)
    return idx, tiles, tv, haversine_km, neighbours


def git_hash() -> str:
    try:
        h = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = subprocess.call(["git", "diff", "--quiet", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL) != 0
        return h + ("-dirty" if dirty else "")
    except Exception:  # noqa: BLE001
        return "unknown"


def save_grid(x: torch.Tensor, path: Path, scale: int = 4) -> None:
    """x: [16, 3, 32, 32] in [0, 1] -> 4x4 grid PNG."""
    a = (x.clamp(0, 1).cpu().numpy() * 255).astype(np.uint8).transpose(0, 2, 3, 1)
    n = int(np.ceil(np.sqrt(len(a))))
    h = a.shape[1]
    grid = np.zeros((n * h, n * h, 3), np.uint8)
    for i, im in enumerate(a):
        grid[(i // n) * h : (i // n + 1) * h, (i % n) * h : (i % n + 1) * h] = im
    Image.fromarray(grid).resize((n * h * scale, n * h * scale), Image.Resampling.NEAREST).save(path)


def run(cfg: dict, name: str) -> Path:
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    seed = int(cfg["seed"])
    out = RUNS / f"{name}_s{seed}"
    (out / "daydreams").mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.pt"):
        f.unlink()
    for f in (out / "daydreams").glob("*.png"):
        f.unlink()
    (out / "config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))

    idx, tiles, tv, haversine_km, neighbours = load_data(dev)
    N = len(idx)
    lat, lon = idx.lat.to_numpy(), idx.lon.to_numpy()
    nbrs = neighbours(lat, lon, float(cfg["radius_km"]))
    t = int(np.argmin(haversine_km(lat, lon, cfg["start_lat"], cfg["start_lon"])))
    meta = {"run_id": out.name, "name": name, "seed": seed, "git": git_hash(), "start_tile": t, "n_tiles": N, "device": dev, "torch": torch.__version__, "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    (out / "meta.json").write_text(json.dumps(meta, indent=2))

    rng = np.random.default_rng(seed)
    torch.manual_seed(seed)
    gen = torch.Generator(device=dev).manual_seed(seed)
    random_policy = cfg.get("policy", "curious") == "random"
    K, crop = int(cfg["K"]), int(cfg["crop_px"])

    model = opt = None
    if not random_policy:
        model = ConvAE().to(dev)
        opt = torch.optim.Adam(model.parameters(), lr=float(cfg["lr"]))
        # fixed held-out set: same 200 tiles and crop positions for every run of this crop_px
        hrng = np.random.default_rng(HELDOUT_SEED)
        held_ids = torch.from_numpy(np.sort(hrng.choice(np.flatnonzero(~idx.tv.to_numpy()), HELDOUT_N, replace=False))).to(dev)
        hgen = torch.Generator(device=dev).manual_seed(HELDOUT_SEED)
        held_x = S.patches(tiles, held_ids, tv, K, crop, hgen)
    norms = {k: S.RunningNorm(float(cfg["ema_alpha"])) for k in ("e", "n", "g")}
    buf = torch.zeros(int(cfg["buffer_size"]), 3, S.IN_PX, S.IN_PX, device=dev)
    buf_n, buf_ptr = 0, 0
    arch_tiles: list[int] = []
    arch_z: torch.Tensor | None = None
    B = 0.0
    force_teleport = False
    steps_log, cand_log, held_log = [], [], []
    t0 = time.time()

    def heldout_eval(step):
        held_log.append({"step": step, "heldout_mse": float(S.recon_err(model, held_x).mean())})

    def reembed():
        nonlocal arch_z
        ids = torch.tensor(arch_tiles, device=dev)
        zs = [S.mean_latent(model, S.patches(tiles, ids[i : i + 256], tv, K, crop, gen)) for i in range(0, len(ids), 256)]
        arch_z = torch.cat(zs)

    if model is not None:
        heldout_eval(0)

    for step in range(int(cfg["steps"])):
        ts = time.time()
        # -- candidates ------------------------------------------------------------
        if force_teleport:
            cands, kinds = [int(rng.integers(N))], ["bored"]
            force_teleport = False
        else:
            cands = list(map(int, nbrs[t]))
            kinds = ["neighbour"] * len(cands)
            if rng.random() < float(cfg["p_long_jump"]):
                cands.append(int(rng.integers(N)))
                kinds.append("long")
            if not cands:
                cands, kinds = [int(rng.integers(N))], ["empty"]
        C = len(cands)
        cid = torch.tensor(cands, device=dev)

        # -- signals + choice --------------------------------------------------------
        rec = {"step": step}
        if random_policy:
            j = int(rng.integers(C))
            e = n = g = ez = nz = gz = I = np.full(C, np.nan)
            maxI = np.nan
        else:
            x = S.patches(tiles, cid, tv, K, crop, gen)
            g_t, _, _ = S.progress_probe(model, x, float(cfg["lr"]), int(cfg["probe_steps"]))
            e_t = S.recon_err(model, x)
            z_c = S.mean_latent(model, x)
            n_t = S.novelty(z_c, arch_z, int(cfg["k_nn"]))
            ez_t, gz_t = norms["e"](e_t), norms["g"](g_t)
            nz_t = norms["n"](n_t) if arch_z is not None else torch.zeros_like(n_t)
            I_t = float(cfg["w_n"]) * nz_t + float(cfg["w_g"]) * gz_t + float(cfg["w_e"]) * ez_t
            e, n, g, ez, nz, gz, I = (v.cpu().numpy().astype(np.float64) for v in (e_t, n_t, g_t, ez_t, nz_t, gz_t, I_t))
            logits = I / float(cfg["temperature"])
            p = np.exp(logits - logits.max())
            p /= p.sum()
            j = int(rng.choice(C, p=p))
            maxI = float(I.max())
            for c in range(C):
                cand_log.append({"step": step, "tile_idx": cands[c], "kind": kinds[c], "e": e[c], "n": n[c], "g": g[c], "e_z": ez[c], "n_z": nz[c], "g_z": gz[c], "I": I[c], "p": p[c], "chosen": c == j})
        prev, t = t, cands[j]

        # -- train on the chosen tile --------------------------------------------------
        err_before = err_after = np.nan
        if not random_policy:
            xt = x[j]  # the K patches the agent just looked at
            batch = xt
            if buf_n > 0:
                ri = torch.randint(0, buf_n, (int(cfg["replay_batch"]),), generator=gen, device=dev)
                batch = torch.cat([xt, buf[ri]])
            with torch.no_grad():
                err_before = float(((model(xt) - xt) ** 2).mean())
            for _ in range(int(cfg["update_steps"])):
                loss = ((model(batch) - batch) ** 2).mean()
                opt.zero_grad(set_to_none=True)
                loss.backward()
                opt.step()
            with torch.no_grad():
                err_after = float(((model(xt) - xt) ** 2).mean())
                zt = model.encode(xt).mean(0, keepdim=True)
            # memory: FIFO patch buffer and archive of visited latents (revisits push again)
            for pch in xt:
                buf[buf_ptr] = pch
                buf_ptr = (buf_ptr + 1) % len(buf)
                buf_n = min(buf_n + 1, len(buf))
            arch_tiles.append(t)
            arch_z = zt if arch_z is None else torch.cat([arch_z, zt])

        # -- boredom -------------------------------------------------------------------
        B_before = B
        bored = False
        if not random_policy and kinds[j] != "bored":
            B = 0.9 * B + 0.1 * float(maxI < 0)
            if B > float(cfg["patience"]):
                bored = True
                torch.save({"model": model.state_dict(), "step": step}, out / f"bored_{step:04d}.pt")
                daydream(model, arch_z, gen, out / "daydreams" / f"bored_{step:04d}.png", int(cfg["k_nn"]))
                B = 0.0
                force_teleport = True

        rec.update(
            tile_idx=t, grid_cell=idx.grid_cell[t], lat=lat[t], lon=lon[t], cloud_cover=float(idx.cloud_cover[t]), tv=bool(idx.tv[t]),
            e=e[j], n=n[j], g=g[j], e_z=ez[j], n_z=nz[j], g_z=gz[j], I=I[j], max_I=maxI, n_candidates=C, jump_type=kinds[j],
            B=B_before, B_after=B, bored_event=bored, err_before=err_before, err_after=err_after,
            dist_km=float(haversine_km(lat[prev], lon[prev], lat[t], lon[t])) if step > 0 else 0.0, sec=time.time() - ts,
        )
        steps_log.append(rec)

        s1 = step + 1
        if not random_policy:
            if s1 % int(cfg["reembed_every"]) == 0:
                reembed()
            if s1 % int(cfg["heldout_every"]) == 0:
                heldout_eval(s1)
            if s1 % int(cfg["ckpt_every"]) == 0:
                torch.save({"model": model.state_dict(), "step": s1}, out / f"ckpt_{s1:04d}.pt")
        if s1 % 100 == 0:
            df = pd.DataFrame(steps_log[-100:])
            print(f"[{out.name}] step {s1}  {time.time() - t0:.0f}s  uniq {len(set(r['tile_idx'] for r in steps_log))}  "
                  f"tv {df.tv.mean():.2f}  bored {df.bored_event.sum()}  B {B:.2f}  err {df.err_before.mean():.4f}", flush=True)

    pd.DataFrame(steps_log).to_parquet(out / "steps.parquet")
    if not random_policy:
        pd.DataFrame(cand_log).to_parquet(out / "candidates.parquet")
        pd.DataFrame(held_log).to_parquet(out / "heldout.parquet")
        torch.save({"model": model.state_dict(), "step": int(cfg["steps"]), "norms": {k: v.state() for k, v in norms.items()}}, out / "final.pt")
        reembed()
        np.savez(out / "archive.npz", z=arch_z.cpu().numpy(), tile_idx=np.array(arch_tiles))
        daydream(model, arch_z, gen, out / "daydreams" / "final.png", int(cfg["k_nn"]))
    meta.update(finished=time.strftime("%Y-%m-%d %H:%M:%S"), seconds=round(time.time() - t0, 1))
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"[{out.name}] done in {time.time() - t0:.0f}s -> {out}")
    return out


@torch.no_grad()
def daydream(model, arch_z: torch.Tensor, gen: torch.Generator, path: Path, k: int) -> None:
    """16 decodes from random latents near the archive's sparsest (least-visited) point."""
    d = torch.cdist(arch_z, arch_z)
    kk = min(k + 1, len(arch_z))
    sparse = d.topk(kk, dim=1, largest=False).values[:, 1:].mean(1) if kk > 1 else torch.zeros(len(arch_z), device=arch_z.device)
    centre = arch_z[int(sparse.argmax())]
    spread = arch_z.std(0) if len(arch_z) > 1 else torch.ones_like(centre)
    z = centre + 0.5 * spread * torch.randn(16, len(centre), generator=gen, device=arch_z.device)
    save_grid(model.decode(z), path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--steps", type=int)
    ap.add_argument("--name")
    a = ap.parse_args()
    cfg = yaml.safe_load(Path(a.config).read_text())
    if a.seed is not None:
        cfg["seed"] = a.seed
    if a.steps is not None:
        cfg["steps"] = a.steps
    run(cfg, a.name or Path(a.config).stem)


if __name__ == "__main__":
    main()
