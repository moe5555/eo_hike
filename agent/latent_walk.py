"""The first wanderers in a GAN's world (notes/brief_g1_latent_walks.md; Moe's decisions of 2026-11-14).

    .venv-sg python agent/latent_walk.py calibrate curious|null    # alpha_min from a 15 km step of the real walks -> runs/g1/latent/<cond>/calibration.json
    .venv-sg python agent/latent_walk.py walk curious|null         # the walk -> runs/g1/latent/<cond>/ (resumes from its checkpoint)
    ... --test: the snapshots that exist now, GAN on the CPU, a few steps, q = 1, into runs/g1/latent_test/ (never a result)

The world: positions are latents z on the sphere of radius sqrt(512); a tile is (z, snapshot), rendered by G_ema (psi 1, constant noise),
128 px, upsampled bilinear to the walker's 256 px. The eight compass offers lie in a random 2-D plane through z, 45 degrees apart, rotated
by theta, at an angle alpha from z; alpha follows the drive exactly as the radius did (agent/compass.radius), mapped log-linearly onto
[alpha_min, alpha_max]. The time offer is the same z in the next kept snapshot (960, 1,920, 2,880, 3,840 kimg), thinned at q = time_offer_p.
The walker: the step loop of agent/walk.py for the two-eye compass walker (TwoEye, the drive, the radius rule, softmax or uniform choice,
the named random streams, re-embedding every 100 steps), with the configs as committed. Nothing in it is changed.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import shutil
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
sys.path.insert(0, str(ROOT))
SG = ROOT / "third_party" / "stylegan2-ada-pytorch"
from agent import clock as CL  # noqa: E402
from agent import compass as CP  # noqa: E402

RNG_STREAMS = ("start", "neighbours", "offers", "landing", "choice", "init", "crops", "replay", "daydream", "compass", "radius", "time")  # walk.py's
Z_DIM = 512
R = math.sqrt(Z_DIM)
N_TILES = 10_000
CALIB_N, CALIB_SEED = 256, 20261114
WALK_PX, GAN_PX, OBS_PX = 256, 128, 32


def out_dir(cond: str, test: bool) -> Path:
    return ROOT / "runs" / "g1" / ("latent_test" if test else "latent") / cond


def kept_snapshots(cond: str, test: bool) -> list[int]:
    run = ROOT / "runs" / "g1" / "gan" / cond
    have = sorted(int(p.stem.split("-")[-1]) for p in run.glob("network-snapshot-*.pkl"))
    if test:
        return have[-2:] if len(have) >= 2 else have
    b = json.loads((ROOT / "runs" / "g1" / "gan" / "budget.json").read_text())
    snaps = [k for k in b["kept_snapshots"]]
    missing = [k for k in snaps if k not in have]
    assert not missing, f"{cond}: kept snapshots missing: {missing}"
    return snaps


# -- the world -----------------------------------------------------------------------------------------------------------------------
class LatentWorld:
    def __init__(self, cond: str, snaps: list[int], dev_gan: str, dev_eye: str) -> None:
        sys.path.insert(0, str(SG))
        import dnnlib
        import legacy

        dnnlib.util.set_cache_dir(str(ROOT / "runs" / "g1" / "dnnlib_cache"))
        self.snaps, self.dev, self.dev_eye = snaps, dev_gan, dev_eye
        self.G = []
        for k in snaps:
            with open(ROOT / "runs" / "g1" / "gan" / cond / f"network-snapshot-{k:06d}.pkl", "rb") as f:
                self.G.append(legacy.load_network_pkl(f)["G_ema"].to(dev_gan).eval().requires_grad_(False))
        self.z: dict[int, np.ndarray] = {}
        self.s: dict[int, int] = {}
        self.cache: dict[int, torch.Tensor] = {}  # visited keys only: uint8 [256, 256, 3] (re-embedding)
        self.next_key = 0

    def add(self, z: np.ndarray, s: int) -> int:
        k = self.next_key
        self.next_key += 1
        self.z[k], self.s[k] = z.astype(np.float32), int(s)
        return k

    def drop(self, keys) -> None:
        for k in keys:
            self.z.pop(k, None), self.s.pop(k, None)

    @torch.no_grad()
    def render(self, keys: list[int]) -> tuple[torch.Tensor, np.ndarray]:
        """-> (uint8 [n, 256, 256, 3] on the eye device, uint8 [n, 128, 128, 3] numpy): G_ema(z) of each key's snapshot."""
        n = len(keys)
        out128 = np.empty((n, GAN_PX, GAN_PX, 3), np.uint8)
        for s in sorted({self.s[k] for k in keys}):
            idx = [i for i, k in enumerate(keys) if self.s[k] == s]
            z = torch.from_numpy(np.stack([self.z[keys[i]] for i in idx])).to(self.dev)
            kw = {"force_fp32": True} if self.dev == "cpu" else {}
            img = self.G[s](z, None, truncation_psi=1, noise_mode="const", **kw)
            out128[idx] = (img.permute(0, 2, 3, 1) * 127.5 + 128).clamp(0, 255).to(torch.uint8).cpu().numpy()
        x = torch.from_numpy(out128).permute(0, 3, 1, 2).float()
        x = F.interpolate(x, size=(WALK_PX, WALK_PX), mode="bilinear", align_corners=False)
        x256 = x.round().clamp(0, 255).to(torch.uint8).permute(0, 2, 3, 1).contiguous().to(self.dev_eye)
        return x256, out128

    def get(self, keys: list[int]) -> torch.Tensor:
        """Visited tiles for re-embedding (rendered again if not cached, e.g. after a resume)."""
        miss = [k for k in keys if k not in self.cache]
        if miss:
            x, _ = self.render(miss)
            for k, im in zip(miss, x):
                self.cache[k] = im
        return torch.stack([self.cache[k] for k in keys])


def on_sphere(v: np.ndarray) -> np.ndarray:
    return R * v / np.linalg.norm(v)


def compass_offers(z: np.ndarray, alpha_deg: float, theta_deg: float, rng: np.random.Generator) -> list[np.ndarray]:
    """Eight points at angle alpha from z, in a random 2-D plane through z, 45 degrees apart, rotated by theta (the compass on a sphere)."""
    zh = z / np.linalg.norm(z)
    u = rng.standard_normal(Z_DIM)
    u -= (u @ zh) * zh
    u /= np.linalg.norm(u)
    v = rng.standard_normal(Z_DIM)
    v -= (v @ zh) * zh + (v @ u) * u
    v /= np.linalg.norm(v)
    a = math.radians(alpha_deg)
    out = []
    for k in range(8):
        b = math.radians(theta_deg + 45.0 * k)
        d = math.cos(b) * u + math.sin(b) * v
        out.append(R * (math.cos(a) * zh + math.sin(a) * d))
    return out


def angle_deg(a: np.ndarray, b: np.ndarray) -> float:
    return math.degrees(math.acos(float(np.clip(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)), -1, 1))))


def colour(a128: np.ndarray) -> dict:
    """Colour and texture statistics of a rendered tile (labelled as such; not the quirk detectors). R = nir08, G = red, B = the green band."""
    x = a128.astype(np.float32)
    luma = x.mean(2)
    return {"brightness": float(luma.mean()), "white_share": float((a128.min(2) >= 230).mean()), "black_share": float((a128.max(2) <= 3).mean()),
            "green_band_dark": bool(np.percentile(a128[..., 2], 99) <= 3), "mean_r_nir": float(x[..., 0].mean()), "mean_g_red": float(x[..., 1].mean()),
            "mean_b_green": float(x[..., 2].mean()), "grad": float(np.abs(np.diff(luma, axis=1)).mean() + np.abs(np.diff(luma, axis=0)).mean()),
            "row_roughness": float(np.abs(np.diff(luma.mean(1))).mean())}


def down(a: np.ndarray) -> np.ndarray:
    """Pixel layout: 32 x 32 x 3 by area, in [0, 1]."""
    f = a.shape[1] // OBS_PX
    return a.reshape(len(a), OBS_PX, f, OBS_PX, f, 3).mean((2, 4)).reshape(len(a), -1).astype(np.float32) / 255.0


def colour_char(a: np.ndarray) -> np.ndarray:
    """Colour character: mean and spread of each CIR channel, in [0, 1] (the calibration's observer; Moe 2026-11-14)."""
    x = a.astype(np.float32) / 255.0
    return np.concatenate([x.mean((1, 2)), x.std((1, 2))], 1)


OBSERVERS = {"colour": colour_char, "pixels": down}


# -- calibration ---------------------------------------------------------------------------------------------------------------------
def _alpha_for(grid: np.ndarray, curve: np.ndarray, target: float) -> float:
    """The smallest angle whose median change reaches the target, log-interpolated on the monotone envelope of the curve."""
    env = np.maximum.accumulate(curve)
    if target <= env[0]:
        return float(grid[0])
    if target >= env[-1]:
        return float(grid[-1])
    i = int(np.searchsorted(env, target))
    t = (target - env[i - 1]) / max(env[i] - env[i - 1], 1e-9)
    return float(np.exp(np.log(grid[i - 1]) + t * (np.log(grid[i]) - np.log(grid[i - 1]))))


def cmd_calibrate(cond: str, test: bool, dev_gan: str) -> dict:
    """alpha_min: a step at alpha_min changes a GAN tile's colour character (mean and spread per channel; Moe 2026-11-14) by the same share of
    the GAN's own random jump (90 degrees) as a 15 km step changed it in the real walks, relative to a jump between random tiles of this
    condition's package (rho = median change of 15 km moves at r_min / median change of random pairs). On the GAN's last kept snapshot.
    alpha_max = 90 degrees. The pixel-layout observer (32 x 32 x 3) is computed and logged too, not used (it gave about 74 degrees in the test:
    neighbouring 10.7 km tiles barely overlap, so their layouts differ almost as much as random tiles)."""
    cfg = yaml.safe_load((ROOT / "configs" / "gen1" / f"{cond}.yaml").read_text())
    r_min = float(cfg["radius_min_km"])
    pkg = ROOT / "paths" / "g1" / cond
    e = pd.read_parquet(pkg / "encounters.parquet")
    rk = []
    for wid, g in e.groupby("walk_id"):
        s_ = pd.read_parquet(ROOT / "runs" / "gen1" / cond / wid.split("_")[-1] / "steps.parquet", columns=["step", "r_km"])
        rk.append(g.merge(s_, on="step", how="left"))
    e = pd.concat(rk).sort_values(["walk_id", "step"])
    prev = e.groupby("walk_id").tile.shift(1)
    m = (e.kind == "move") & (e.r_km <= r_min * 1.0001) & prev.notna()
    pairs = list(zip(prev[m], e.tile[m]))
    rng = np.random.default_rng(CALIB_SEED)
    pick = rng.choice(len(pairs), min(2000, len(pairs)), replace=False)
    ld = lambda n: np.asarray(Image.open(pkg / "tiles" / f"{n}.png").convert("RGB"))  # noqa: E731
    A = np.stack([ld(pairs[i][0]) for i in pick])
    B = np.stack([ld(pairs[i][1]) for i in pick])
    tiles = pd.read_parquet(pkg / "tiles.parquet").tile.to_numpy()
    ra, rb = rng.choice(len(tiles), (2, len(pick)))
    RA, RB = np.stack([ld(tiles[i]) for i in ra]), np.stack([ld(tiles[i]) for i in rb])
    real = {}
    for nm, f in OBSERVERS.items():
        d15 = float(np.median(np.linalg.norm(f(A) - f(B), axis=1)))
        dr = float(np.median(np.linalg.norm(f(RA) - f(RB), axis=1)))
        real[nm] = {"d_15km": d15, "d_random": dr, "rho": d15 / dr}
    snaps = kept_snapshots(cond, test)
    W = LatentWorld(cond, snaps[-1:], dev_gan, "cpu")
    z0 = [on_sphere(v) for v in rng.standard_normal((32 if test else CALIB_N, Z_DIM))]  # tests: a small sample (CPU)
    _, i0 = W.render([W.add(z, 0) for z in z0])
    grid = np.geomspace(0.25, 90.0, 24)
    curves = {nm: [] for nm in OBSERVERS}
    for al in grid:
        zs = [compass_offers(z, al, float(rng.uniform(0, 45)), rng)[int(rng.integers(8))] for z in z0]
        _, i1 = W.render([W.add(z, 0) for z in zs])
        W.drop(list(W.z))
        for nm, f in OBSERVERS.items():
            curves[nm].append(float(np.median(np.linalg.norm(f(i0) - f(i1), axis=1))))
    gan = {}
    for nm in OBSERVERS:
        c = np.array(curves[nm])
        target = real[nm]["rho"] * float(c[-1])
        gan[nm] = {"curve": c.tolist(), "at_90": float(c[-1]), "target": target, "alpha_min_deg": _alpha_for(grid, c, target)}
    alpha_min = gan["colour"]["alpha_min_deg"]
    res = {"cond": cond, "alpha_min_deg": alpha_min, "alpha_max_deg": 90.0, "observer_used": "colour character (mean and spread per CIR channel)",
           "real": real, "gan": gan, "grid_deg": grid.tolist(), "n_real_pairs": len(pick), "n_gan_latents": len(z0), "r_min_km": r_min,
           "snapshot": snaps[-1], "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    od = out_dir(cond, test)
    od.mkdir(parents=True, exist_ok=True)
    (od / "calibration.json").write_text(json.dumps(res, indent=1))
    print(f"[calibrate] {cond} (snapshot {snaps[-1]}): colour rho {real['colour']['rho']:.3f} -> alpha_min {alpha_min:.2f} deg; "
          f"pixels rho {real['pixels']['rho']:.3f} -> {gan['pixels']['alpha_min_deg']:.2f} deg (logged, not used)", flush=True)
    return res


# -- the walk ------------------------------------------------------------------------------------------------------------------------
def cmd_walk(cond: str, test: bool, dev_gan: str, steps_cap: int | None, q_override: float | None, tile_cap: int,
             ckpt_override: int | None = None, crash_at: int | None = None, out_sub: str | None = None) -> None:
    from agent.eyes import TwoEye

    torch.set_num_threads(3)
    dev = "cpu"
    cfg = yaml.safe_load((ROOT / "configs" / "gen1" / f"{cond}.yaml").read_text())
    seed = 0
    od = out_dir(cond, test) / out_sub if out_sub else out_dir(cond, test)
    od.mkdir(parents=True, exist_ok=True)
    (od / "tiles").mkdir(exist_ok=True)
    (od / "contact").mkdir(exist_ok=True)
    cal = json.loads((out_dir(cond, test) / "calibration.json").read_text())
    a_min, a_max = float(cal["alpha_min_deg"]), float(cal["alpha_max_deg"])
    snaps = kept_snapshots(cond, test)
    W = LatentWorld(cond, snaps, dev_gan, dev)
    q = float(cfg.get("time_offer_p", 1.0)) if q_override is None else q_override
    cap = steps_cap or int(cfg["steps"])
    uniform = cfg.get("choice", "softmax") == "uniform"
    temp = float(cfg["temperature"])
    refresh = cfg.get("refresh_archive", "none") == "candidates"
    r_min, r_max = float(cfg["radius_min_km"]), float(cfg["radius_max_km"])
    delta, dead = float(cfg["radius_delta"]), float(cfg.get("radius_hysteresis", 0.0))
    warm, drive_start = int(cfg.get("drive_warmup", 50)), int(cfg.get("drive_start", 0))
    a_short = float(cfg.get("drive_alpha_short", cfg["ema_alpha"]))
    a_long = float(cfg.get("drive_alpha_long", cfg.get("ema_alpha_long", 0.002)))
    ckpt_every, reembed_every = int(ckpt_override or cfg["ckpt_every"]), int(cfg["reembed_every"])  # override: tests only

    def alpha_of(r_km: float) -> float:
        u = math.log(r_km / r_min) / math.log(r_max / r_min)
        return a_min * (a_max / a_min) ** u

    ck = od / "resume.pt"
    if ck.exists():
        S = torch.load(ck, weights_only=False)
        step0, te, drive = S["step"], S["te"], S["drive"]
        r_offer, r_choice, r_compass, r_radius, r_time = (S["rng"][k] for k in ("offer", "choice", "compass", "radius", "time"))
        gen, gen_replay = torch.Generator(device=dev), torch.Generator(device=dev)
        gen.set_state(S["gen"]), gen_replay.set_state(S["gen_replay"])
        torch.set_rng_state(S["torch_rng"])
        W.z, W.s, W.next_key = S["world"]["z"], S["world"]["s"], S["world"]["next_key"]
        clk, cur, z_cur, z0, r_now, theta_now, start_key = S["clk"], S["cur"], S["z_cur"], S["z0"], S["r_now"], S["theta_now"], S["start_key"]
        meta = S["meta"]
        meta.setdefault("resumed", []).append({"at_step": step0, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        parts_done = S["parts"]
        print(f"[latent {cond}] resumed at step {step0}, snapshot {snaps[clk]}", flush=True)
    else:
        ss = dict(zip(RNG_STREAMS, np.random.SeedSequence(seed).spawn(len(RNG_STREAMS))))
        r_offer, r_choice, r_compass, r_radius, r_time = (np.random.default_rng(ss[k]) for k in ("offers", "choice", "compass", "radius", "time"))
        torch.manual_seed(int(ss["init"].generate_state(1)[0]))
        gen, gen_replay = (torch.Generator(device=dev).manual_seed(int(ss[k].generate_state(1)[0])) for k in ("crops", "replay"))
        te = TwoEye(cfg, dev)
        drive = CP.Drive(a_short, a_long, cfg.get("drive_norm", "z_diff"))
        z0 = on_sphere(np.random.default_rng(ss["start"]).standard_normal(Z_DIM))
        clk = 0
        start_key = cur = W.add(z0, clk)
        z_cur = z0
        x0, i0 = W.render([cur])
        Image.fromarray(i0[0]).save(od / "tiles" / f"k{cur:06d}_s{snaps[clk]:04d}.png")
        step0, parts_done = 0, 0
        r_now = r_min
        theta_now = float(r_compass.uniform(0.0, 45.0))
        meta = {"cond": cond, "config": f"configs/gen1/{cond}.yaml", "seed": seed, "q": q, "snapshots": snaps, "alpha_min_deg": a_min, "alpha_max_deg": a_max,
                "tile_cap": tile_cap, "steps_cap": cap, "torch": torch.__version__, "torch_threads": torch.get_num_threads(), "eye_device": dev,
                "gan_device": dev_gan, "upsample": "bilinear 128 -> 256", "started": time.strftime("%Y-%m-%d %H:%M:%S"), "test": test,
                "start_key": start_key}
        (od / "meta.json").write_text(json.dumps(meta, indent=1, default=str))

    def next_radius(step: int) -> float:
        return r_min if step <= warm else CP.radius(drive.d, r_min, r_max, delta, dead)

    steps_log, offers_log = [], []
    parts = od / "parts"
    t0 = time.time()
    end_reason = None
    for step in range(step0, cap):
        ts = time.time()
        time_ok = bool(r_time.random() < q) if q < 1.0 else True
        time_exists = clk < len(snaps) - 1
        zs = compass_offers(z_cur, alpha_of(r_now), theta_now, r_offer)
        kinds = ["compass"] * 8
        keys = [W.add(z, clk) for z in zs]
        if time_exists and time_ok:
            keys.append(W.add(z_cur, clk + 1))
            kinds.append("time")
        x, i128 = W.render(keys)
        sc = te.score(step, x, keys, set(te.tiles), refresh)
        I, I_long = sc["I"], sc["I_long"]
        p = CL.choice_probs(I, temp, uniform)
        j = int(r_choice.choice(len(keys), p=p))
        rec = {"step": step, "p_chosen": float(p[j]), "best_offer": bool(j == int(np.argmax(I))), **te.log_choice(j, sc)}
        cols = [colour(a) for a in i128]
        for c in range(len(keys)):
            offers_log.append({"step": step, "key": keys[c], "kind": kinds[c], "snapshot": snaps[W.s[keys[c]]], "I": I[c], "I_long": I_long[c], "p": p[c],
                               "chosen": c == j, "z_glance": sc["z"]["glance"][c], "z_grid": sc["z"]["grid"][c], "z_prog": sc["z"]["g"][c], **cols[c]})
        clk_before = clk
        if kinds[j] == "time":
            clk += 1
        prev_z, cur, z_cur = z_cur, keys[j], W.z[keys[j]]
        W.drop([k for k in keys if k != cur])
        # the drive after this step's choice sets the next angle (walk.py's order: drive, next radius and frame, then training)
        if step >= drive_start:
            drive.update(float(I_long[j]))
        r_was, theta_was = r_now, theta_now
        r_now, theta_now = next_radius(step + 1), float(r_compass.uniform(0.0, 45.0))
        xj = x[j : j + 1]
        tr = te.train(step, xj, sc["n_crop"][j], gen, gen_replay)
        te.remember(cur, xj)
        W.cache[cur] = x[j]
        Image.fromarray(i128[j]).save(od / "tiles" / f"k{cur:06d}_s{snaps[W.s[cur]]:04d}.png")
        rec.update(key=cur, kind=kinds[j], snapshot_before=snaps[clk_before], snapshot=snaps[clk], n_offers=len(keys), time_exists=time_exists,
                   time_offered="time" in kinds, r_km=r_was, alpha_deg=alpha_of(r_was), theta=theta_was, angle_step_deg=angle_deg(prev_z, z_cur),
                   angle_from_start_deg=angle_deg(z0, z_cur), I=float(I[j]), I_long=float(I_long[j]), max_I=float(np.max(I)),
                   **{f"drive_{k}": v for k, v in drive.state().items() if k != "t"}, **tr, **{f"chosen_{k}": v for k, v in cols[j].items()},
                   sec=time.time() - ts)
        steps_log.append(rec)
        s1 = step + 1
        if s1 % reembed_every == 0:
            te.reembed(W.get)
        n_unique = len(set(te.tiles)) + 1  # the start tile counts, as in the packages
        if s1 % 100 == 0:
            df = pd.DataFrame(steps_log[-100:])
            print(f"[latent {cond}] step {s1}  {time.time() - t0:.0f}s  tiles {n_unique}  snapshot {snaps[clk]}  waits {(df.kind == 'time').mean():.2f}  "
                  f"alpha {df.alpha_deg.median():.2f}  from start {rec['angle_from_start_deg']:.1f} deg", flush=True)
        if n_unique >= tile_cap:
            end_reason = "tiles"
        elif s1 >= cap:
            end_reason = "capped"
        if s1 % ckpt_every == 0 or end_reason:
            te.flush(parts)
            pd.DataFrame(steps_log).to_parquet(parts / f"steps_{parts_done:03d}.parquet")
            pd.DataFrame(offers_log).to_parquet(parts / f"offers_{parts_done:03d}.parquet")
            parts_done += 1
            steps_log.clear(), offers_log.clear()
            if not end_reason:
                st = {"step": s1, "te": te, "drive": drive, "rng": {"offer": r_offer, "choice": r_choice, "compass": r_compass, "radius": r_radius, "time": r_time},
                      "gen": gen.get_state(), "gen_replay": gen_replay.get_state(), "torch_rng": torch.get_rng_state(),
                      "world": {"z": W.z, "s": W.s, "next_key": W.next_key}, "clk": clk, "cur": cur, "z_cur": z_cur, "z0": z0, "r_now": r_now,
                      "theta_now": theta_now, "start_key": start_key, "meta": meta, "parts": parts_done}
                torch.save(st, od / "resume.tmp")
                os.replace(od / "resume.tmp", ck)
                if crash_at and s1 >= crash_at:  # tests only: a simulated crash right after a checkpoint
                    raise SystemExit(f"[latent {cond}] simulated crash at step {s1}")
        if end_reason:
            break
    s = pd.concat([pd.read_parquet(parts / f"steps_{k:03d}.parquet") for k in range(parts_done)], ignore_index=True)
    o = pd.concat([pd.read_parquet(parts / f"offers_{k:03d}.parquet") for k in range(parts_done)], ignore_index=True)
    s.to_parquet(od / "steps.parquet")
    o.to_parquet(od / "offers.parquet")
    te.save_logs(od, None)
    keys = [start_key] + s.key.tolist()
    np.savez(od / "visited.npz", key=np.array(keys), z=np.stack([W.z[k] for k in keys]), snapshot=np.array([snaps[W.s[k]] for k in keys]))
    walk = {"cond": cond, "steps": len(s), "end_reason": end_reason, "unique_tiles": int(len(set(keys))), "waits": int((s.kind == "time").sum()),
            "final_snapshot": int(s.snapshot.iloc[-1]), "first_step_at_last_snapshot": int(s.step[s.snapshot == snaps[-1]].min()) if (s.snapshot == snaps[-1]).any() else None,
            "alpha_min_deg": a_min, "median_alpha_deg": float(s.alpha_deg.median()), "angle_from_start_end_deg": float(s.angle_from_start_deg.iloc[-1]),
            "seconds": round(time.time() - t0, 1), "q": q, "test": test}
    meta["walk"] = walk
    (od / "meta.json").write_text(json.dumps(meta, indent=1, default=str))
    (od / "walk.json").write_text(json.dumps(walk, indent=1))
    ck.unlink(missing_ok=True)
    shutil.rmtree(parts, ignore_errors=True)
    print(f"[latent {cond}] done: {walk}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["calibrate", "walk"])
    ap.add_argument("cond", choices=["curious", "null"])
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--gan-dev", default="cuda")
    ap.add_argument("--steps", type=int)
    ap.add_argument("--q", type=float)
    ap.add_argument("--tile-cap", type=int, default=N_TILES)
    ap.add_argument("--ckpt-every", type=int)  # tests only
    ap.add_argument("--crash-at", type=int)  # tests only
    ap.add_argument("--out-sub")  # tests only
    a = ap.parse_args()
    if a.cmd == "calibrate":
        cmd_calibrate(a.cond, a.test, a.gan_dev)
    else:
        assert a.test or not (a.ckpt_every or a.crash_at or a.out_sub), "--ckpt-every / --crash-at / --out-sub are for --test only"
        cmd_walk(a.cond, a.test, a.gan_dev, a.steps, a.q, a.tile_cap, a.ckpt_every, a.crash_at, a.out_sub)


if __name__ == "__main__":
    main()
