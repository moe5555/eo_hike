"""The walk: candidates -> signals -> softmax choice -> train -> boredom -> log.

nav: classic (default, every run before experiment 09) offers the neighbours within radius_km plus blind far offers, and teleports when
bored. nav: compass (experiment 09, agent/compass.py) offers eight cells at one radius, set by the walker's drive; no far offers, no
boredom, no teleports.

    python -m agent.walk configs/01_first_walk/baseline.yaml --seed 1
    python -m agent.walk configs/01_first_walk/baseline.yaml --steps 50 --name smoke     # quick test

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

from agent import compass as CP
from agent import signals as S
from agent.model import CH, LATENT, ConvAE

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RUNS = ROOT / "runs"
HELDOUT_N, HELDOUT_SEED = 200, 12345
# rng_mode: split, one independent generator per decision, in this order (SeedSequence children depend only on their position).
# "start" and "neighbours" draw nothing today: the start is the tile nearest start_lat/lon and every neighbour in radius is a
# candidate. They hold their places so that a future draw there shifts nothing else.
# Experiment 09 appends "compass" (the rotation of the eight bearings) and "radius" (jitter); a child's stream depends only on its position,
# so appending leaves every earlier stream, and every classic walk, unchanged.
RNG_STREAMS = ("start", "neighbours", "offers", "landing", "choice", "init", "crops", "replay", "daydream", "compass", "radius")


class RegionalTiles:
    """v1 backend: the 1,814 Northern Italy tiles of data/tiles.npy, all on the GPU, noisy TV included."""

    def __init__(self, cfg: dict, device: str) -> None:
        import sys

        sys.path.insert(0, str(DATA))
        from prepare import neighbours  # noqa: E402

        self.dev, self.name = device, "regional"
        self.idx = pd.read_parquet(DATA / "tiles.parquet")
        self.tiles = torch.from_numpy(np.load(DATA / "tiles.npy")).to(device)
        self.tv = torch.from_numpy(self.idx.tv.to_numpy().copy()).to(device)
        self.lat, self.lon = self.idx.lat.to_numpy(), self.idx.lon.to_numpy()
        self.N = len(self.idx)
        self.nbrs = neighbours(self.lat, self.lon, float(cfg["radius_km"]))
        self.pool_size = self.N
        self.heldout_pool = np.flatnonzero(~self.idx.tv.to_numpy())

    def start(self, lat: float, lon: float) -> int:
        return int(np.argmin(haversine_km(self.lat, self.lon, lat, lon)))

    def neighbours(self, t: int) -> list[int]:
        return list(map(int, self.nbrs[t]))

    def random_tile(self, rng: np.random.Generator) -> int:
        return int(rng.integers(self.N))

    def get(self, ids: list[int], timeout: float | None = None):
        """-> (uint8 [C, H, W, 3] on device, tv mask [C], ids actually returned, fetch stats)."""
        cid = torch.tensor(ids, device=self.dev)
        return self.tiles[cid], self.tv[cid], list(ids), {}

    def prefetch(self, t: int) -> None:
        pass

    def summary(self) -> dict:
        return {}


class LazyTiles:
    """v3 backend: data/tile_store.py over the global Major TOM index, restricted to a World pool
    (global, regional_lazy for development, or a confinement circle). No noisy TV."""

    def __init__(self, cfg: dict, device: str) -> None:
        from data.tile_store import TileStore, World

        self.dev, self.cfg = device, cfg
        self.store = TileStore(cache_gb=float(cfg.get("cache_gb", 50)))
        self.world = World.from_config(self.store, cfg)
        self.name = self.world.name
        self.idx = self.store.idx.assign(tv=False)
        self.lat, self.lon = self.world.lat, self.world.lon
        self.N = self.store.N
        self.pool_size = len(self.world.pool)
        self.radius = float(cfg["radius_min_km"] if cfg.get("nav", "classic") == "compass" else cfg["radius_km"])
        self.ring = float(cfg.get("prefetch_ring_km", 10.0))
        self.timeout = float(cfg.get("fetch_timeout", 30.0))
        # held-out tiles come from the whole global index, so global and confined walkers are scored on the same 200
        self.heldout_pool = np.arange(self.N) if cfg.get("heldout", "global") == "global" else self.world.pool

    def start(self, lat: float, lon: float) -> int:
        return self.world.nearest(lat, lon)

    def neighbours(self, t: int) -> list[int]:
        return list(map(int, self.world.neighbours(t, self.radius)))

    def random_tile(self, rng: np.random.Generator) -> int:
        return self.world.random_tile(rng)

    def get(self, ids: list[int], timeout: float | None = None):
        arrs, dropped, st = self.store.get_many(ids, timeout=self.timeout if timeout is None else timeout)
        keep = [i for i in ids if i in arrs]
        img = torch.from_numpy(np.stack([arrs[i] for i in keep])).to(self.dev) if keep else None
        st["dropped"] = dropped
        return img, torch.zeros(len(keep), dtype=torch.bool, device=self.dev), keep, st

    def prefetch(self, t: int) -> None:
        self.store.prefetch(self.world.neighbours(t, self.radius + self.ring))

    def summary(self) -> dict:
        return self.store.summary()


def load_tiles(cfg: dict, device: str):
    return RegionalTiles(cfg, device) if cfg.get("world", "regional") == "regional" else LazyTiles(cfg, device)


def haversine_km(lat1, lon1, lat2, lon2):
    from data.tile_store import haversine_km as h

    return h(lat1, lon1, lat2, lon2)


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

    T = load_tiles(cfg, dev)
    idx, lat, lon = T.idx, T.lat, T.lon
    t = T.start(cfg["start_lat"], cfg["start_lon"])
    meta = {"run_id": out.name, "name": name, "seed": seed, "git": git_hash(), "start_tile": t, "n_tiles": T.N, "device": dev, "torch": torch.__version__, "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    if T.name != "regional":
        meta.update(world=T.name, pool_size=T.pool_size, start_cell=str(idx.grid_cell[t]), start_latlon=[float(lat[t]), float(lon[t])],
                    start_cover=str(idx.cover[t]), confine_center=cfg.get("confine_center"), confine_radius_km=cfg.get("confine_radius_km"))
    (out / "meta.json").write_text(json.dumps(meta, indent=2))

    def look(ids: list[int], g: torch.Generator, timeout: float | None = None, fixed: bool = False):
        img, is_tv, kept, st = T.get(ids, timeout)
        if not kept:
            return None, kept, st
        off = S.fixed_offsets(kept, K, img.shape[1], crop, img.device) if fixed else None
        return S.patches(img, is_tv, K, crop, g, off), kept, st

    if cfg.get("rng_mode", "legacy") == "split":
        ss = dict(zip(RNG_STREAMS, np.random.SeedSequence(seed).spawn(len(RNG_STREAMS))))
        r_offer, r_land, r_choice, r_compass, r_radius = (np.random.default_rng(ss[k]) for k in ("offers", "landing", "choice", "compass", "radius"))
        torch.manual_seed(int(ss["init"].generate_state(1)[0]))
        gen, gen_replay, gen_dream = (torch.Generator(device=dev).manual_seed(int(ss[k].generate_state(1)[0])) for k in ("crops", "replay", "daydream"))
    else:
        r_offer = r_land = r_choice = r_compass = r_radius = np.random.default_rng(seed)
        torch.manual_seed(seed)
        gen = gen_replay = gen_dream = torch.Generator(device=dev).manual_seed(seed)
    random_policy = cfg.get("policy", "curious") == "random"
    K, crop = int(cfg["K"]), int(cfg["crop_px"])
    # hike revisions (notes/04_perception_fix/); the defaults are the v1/v3a walker
    fixed_crops = cfg.get("score_crops", "random") == "fixed"  # score (and archive) with crops seeded by tile id; train on random crops
    refresh = cfg.get("refresh_archive", "none") == "candidates"  # re-embed a candidate's own archive entries before novelty
    unit_z = bool(cfg.get("normalise_latents", False))  # novelty on L2-normalised latents
    return_cost = float(cfg.get("return_cost", 0.0))  # I -= return_cost * log(1 + visits)
    no_backstep = bool(cfg.get("no_backstep", False))  # the tile just left is not a candidate
    # round h0111 (notes/07_film_arc/brief.md); the defaults are the h2910 walker
    uniform_choice = cfg.get("choice", "softmax") == "uniform"  # all signals computed and logged, the choice ignores them
    land_k = int(cfg.get("landing_k", 1)) if cfg.get("teleport_landing", "blind") == "best_of_k" else 0  # teleport to the most novel of k random tiles
    log_prev = bool(cfg.get("log_prev_error", False))  # log the error on the current and previous tile after each update
    ae_width = float(cfg.get("ae_width", 1.0))  # multiplies the autoencoder's channels and latent size
    # experiment 09 (notes/09_compass/brief_e09_compass.md); nav classic is every earlier walker
    compass = cfg.get("nav", "classic") == "compass"
    if compass:
        assert T.name != "regional", "nav: compass needs the global tile store"
        assert not random_policy, "nav: compass needs the curious policy (the drive is the walker's interest)"
        r_min, r_max = float(cfg["radius_min_km"]), float(cfg["radius_max_km"])
        delta, dead = float(cfg["radius_delta"]), float(cfg.get("radius_hysteresis", 0.0))
        warm = int(cfg.get("drive_warmup", 50))
        # first step the drive counts (Stage 1 round 2, finding 25): before it, the young network's "everything is new" is left out of both averages
        drive_start = int(cfg.get("drive_start", 0))
        sig = cfg.get("drive_signal", "interest_long")
        assert sig in ("interest", "interest_long", "novelty", "progress", "surprise", "novelty_z", "progress_z"), sig
        # the drive's two averages (Stage 1 report, finding 17): default to ema_alpha (the scorer's rate) and ema_alpha_long (the yardstick)
        a_short = float(cfg.get("drive_alpha_short", cfg["ema_alpha"]))
        a_long = float(cfg.get("drive_alpha_long", cfg.get("ema_alpha_long", 0.002)))
        drive = CP.Drive(a_short, a_long, cfg.get("drive_norm", "z_diff"))
        long_norms = {k: CP.LongNorm(float(cfg.get("ema_alpha_long", 0.002))) for k in "eng"}  # interest on the long yardstick
        jitter = float(cfg.get("radius_jitter", 0.25)) if cfg.get("radius_mode", "deterministic") == "jitter" else 0.0
        frame = cfg.get("compass_frame", "random")
        assert frame in ("fixed", "random", "heading"), frame
        persistence = float(cfg.get("persistence", 0.0))
        snap_tol, snap_floor = float(cfg.get("snap_tol", 0.25)), float(cfg.get("snap_floor_km", 7.5))
        offer_stay = bool(cfg.get("offer_stay", False))
        schedule = None
        if cfg.get("radius_schedule"):
            sp = Path(str(cfg["radius_schedule"]).format(seed=seed))  # a {seed} in the path: one schedule per walk seed
            schedule = pd.read_csv(sp if sp.is_absolute() else ROOT / sp).radius_km.to_numpy(float)
            assert len(schedule) >= int(cfg["steps"]), f"radius_schedule has {len(schedule)} radii for {cfg['steps']} steps"
        meta["compass"] = {"drive_signal": sig, "drive_alpha_short": a_short, "drive_alpha_long": a_long, "drive_start": drive_start, "r_min": r_min, "r_max": r_max, "delta": delta, "schedule": cfg.get("radius_schedule")}

        def next_radius(step: int) -> float:
            if schedule is not None:
                return float(schedule[step])
            r = r_min if step <= warm else CP.radius(drive.d, r_min, r_max, delta, dead)
            if jitter and step > warm:
                r = float(np.clip(r * np.exp(jitter * r_radius.standard_normal()), r_min, r_max))  # lognormal around r, kept in [r_min, r_max]
            return r

        def next_theta(heading: float | None) -> float:
            if frame == "fixed":
                return 0.0
            if frame == "heading" and heading is not None:
                return heading
            return float(r_compass.uniform(0.0, 45.0)) if frame == "random" else float(r_compass.uniform(0.0, 360.0))

        def compass_offers(t: int, r: float, theta: float) -> tuple[list[int], dict]:
            return CP.offers(T.world, t, r, theta, max(snap_tol, snap_floor / r))

        heading = None
        r_now, theta_now = next_radius(0), next_theta(None)
    visits: dict[int, int] = {}
    came_from = None

    model = opt = None
    if not random_policy:
        model = ConvAE(tuple(int(c * ae_width) for c in CH), int(LATENT * ae_width)).to(dev)
        opt = torch.optim.Adam(model.parameters(), lr=float(cfg["lr"]))
        # fixed held-out set: same 200 tiles and crop positions for every run of this crop_px
        hrng = np.random.default_rng(HELDOUT_SEED)
        held_ids = np.sort(hrng.choice(T.heldout_pool, HELDOUT_N, replace=False)).tolist()
        hgen = torch.Generator(device=dev).manual_seed(HELDOUT_SEED)
        held_x, held_kept, _ = look(held_ids, hgen, timeout=600.0)
        meta["heldout_n"] = len(held_kept)
    norms = {k: S.RunningNorm(float(cfg["ema_alpha"])) for k in ("e", "n", "g")}
    buf = torch.zeros(int(cfg["buffer_size"]), 3, S.IN_PX, S.IN_PX, device=dev)
    buf_n, buf_ptr = 0, 0
    arch_tiles: list[int] = []
    arch_z: torch.Tensor | None = None
    B = 0.0
    force_teleport = False
    steps_log, cand_log, held_log, land_log = [], [], [], []
    t0 = time.time()

    def heldout_eval(step):
        held_log.append({"step": step, "heldout_mse": float(S.recon_err(model, held_x).mean())})

    def reembed():
        nonlocal arch_z
        zs = []
        for i in range(0, len(arch_tiles), 256):
            x, kept, _ = look(arch_tiles[i : i + 256], gen, timeout=600.0, fixed=fixed_crops)
            assert len(kept) == len(arch_tiles[i : i + 256]), "visited tile missing from the store"
            zs.append(S.mean_latent(model, x))
        arch_z = torch.cat(zs)

    def best_landing(step: int) -> int:
        """The most novel of land_k random tiles under the current network; the first draw if none of them could be fetched."""
        offers = [T.random_tile(r_land) for _ in range(land_k)]
        xl, kept, _ = look(offers, gen, fixed=fixed_crops)
        if not kept:
            return offers[0]
        nl = S.novelty(S.mean_latent(model, xl), arch_z, int(cfg["k_nn"]), unit=unit_z).cpu().numpy()
        best = int(nl.argmax())
        land_log.extend({"step": step, "tile_idx": i, "n": float(v), "landed": o == best} for o, (i, v) in enumerate(zip(kept, nl)))
        return kept[best]

    if model is not None:
        heldout_eval(0)

    for step in range(int(cfg["steps"])):
        ts = time.time()
        # -- candidates ------------------------------------------------------------
        if compass:
            cands, cinfo = compass_offers(t, r_now, theta_now)
            n_turn = 0
            while not cands and n_turn < 20:  # every target dropped (open ocean all round): turn the compass
                n_turn += 1
                theta_now = float(r_compass.uniform(0.0, 360.0))
                cands, cinfo = compass_offers(t, r_now, theta_now)
            if not cands:  # still nothing: the eight indexed cells nearest to this one
                cands = [int(c) for c in T.world.pool[T.world.tree.query(np.radians([[lat[t], lon[t]]]), k=9)[1][0]] if c != t][:8]
            kinds = ["compass"] * len(cands)
            if offer_stay:
                cands, kinds = cands + [t], kinds + ["stay"]
        elif force_teleport:
            cands, kinds = [best_landing(step) if land_k else T.random_tile(r_land)], ["bored"]
            force_teleport = False
        else:
            cands = T.neighbours(t)
            if no_backstep and came_from is not None:
                cands = [c for c in cands if c != came_from] or cands
            kinds = ["neighbour"] * len(cands)
            if r_offer.random() < float(cfg["p_long_jump"]):
                cands.append(T.random_tile(r_offer))
                kinds.append("long")
            if not cands:
                cands, kinds = [T.random_tile(r_land)], ["empty"]

        # -- look (lazy store: candidates that can't be fetched in time are dropped) ----
        x, kept, fst = look(cands, gen, fixed=fixed_crops) if not random_policy else (None, cands, {})
        n_redraw = 0
        if not random_policy and len(kept) < len(cands):
            if not kept:  # nothing arrived: wait longer rather than stall the walk on an empty choice
                x, kept, fst2 = look(cands, gen, timeout=120.0, fixed=fixed_crops)
                fst["wait_sec"] += fst2["wait_sec"]
                fst["dropped"] = fst2["dropped"]
            while not kept:  # still nothing (e.g. one blind target that can't be fetched): blindly redraw it
                n_redraw += 1
                if n_redraw > 50:
                    raise RuntimeError(f"step {step}: no candidate could be fetched after {n_redraw - 1} redraws")
                if compass:  # turn the compass and try eight new cells at the same radius
                    theta_now = float(r_compass.uniform(0.0, 360.0))
                    cands, cinfo = compass_offers(t, r_now, theta_now)
                    cands = cands or [T.random_tile(r_land)]
                    kinds = ["compass"] * len(cands)
                else:
                    cands, kinds = [T.random_tile(r_land)], [kinds[0] if kinds[0] in ("bored", "empty") else "redraw"]
                x, kept, fst2 = look(cands, gen, timeout=120.0, fixed=fixed_crops)
                fst["wait_sec"] += fst2["wait_sec"]
                fst["dropped"] = fst["dropped"] + fst2["dropped"]
            kinds = [k for c, k in zip(cands, kinds) if c in set(kept)]
            cands = kept
        C = len(cands)

        # -- signals + choice --------------------------------------------------------
        rec = {"step": step}
        if random_policy:
            j = int(r_choice.integers(C))
            e = n = g = ez = nz = gz = I = np.full(C, np.nan)
            maxI = np.nan
        else:
            g_t, _, _ = S.progress_probe(model, x, float(cfg["lr"]), int(cfg["probe_steps"]))
            e_t = S.recon_err(model, x)
            z_c = S.mean_latent(model, x)
            seen = [c for c in cands if c in visits] if refresh and arch_z is not None else []
            if seen:  # a fresh look at revisited candidates replaces their stale archive latents
                xr, _, _ = look(seen, gen, timeout=600.0, fixed=fixed_crops)
                at = torch.as_tensor(arch_tiles, device=dev)
                for c, zr in zip(seen, S.mean_latent(model, xr)):
                    arch_z[at == c] = zr
            n_t = S.novelty(z_c, arch_z, int(cfg["k_nn"]), unit=unit_z)
            ez_t, gz_t = norms["e"](e_t), norms["g"](g_t)
            nz_t = norms["n"](n_t) if arch_z is not None else torch.zeros_like(n_t)
            I_t = float(cfg["w_n"]) * nz_t + float(cfg["w_g"]) * gz_t + float(cfg["w_e"]) * ez_t
            if return_cost:
                I_t = I_t - return_cost * torch.log1p(torch.tensor([visits.get(c, 0) for c in cands], dtype=I_t.dtype, device=dev))
            e, n, g, ez, nz, gz, I = (v.cpu().numpy().astype(np.float64) for v in (e_t, n_t, g_t, ez_t, nz_t, gz_t, I_t))
            if compass:
                # interest on the long yardstick (drive_signal interest_long): each raw signal z-scored at ema_alpha_long over the candidates
                lz = {k: (long_norms[k](v) if (k != "n" or arch_z is not None) else np.zeros(C)) for k, v in (("e", e), ("n", n), ("g", g))}
                I_long = float(cfg["w_n"]) * lz["n"] + float(cfg["w_g"]) * lz["g"] + float(cfg["w_e"]) * lz["e"]
                c_bear = CP.initial_bearing(lat[t], lon[t], lat[cands], lon[cands])
                c_dist = haversine_km(lat[t], lon[t], lat[cands], lon[cands])
                if persistence and heading is not None:  # temperament: a pull towards the current heading
                    I = I + persistence * np.cos(np.radians(c_bear - heading))
            logits = I / float(cfg["temperature"])
            p = np.exp(logits - logits.max())
            p /= p.sum()
            if uniform_choice:
                p = np.full(C, 1.0 / C)
            j = int(r_choice.choice(C, p=p))
            maxI = float(I.max())
            for c in range(C):
                cand_log.append({"step": step, "tile_idx": cands[c], "kind": kinds[c], "e": e[c], "n": n[c], "g": g[c], "e_z": ez[c], "n_z": nz[c], "g_z": gz[c], "I": I[c], "p": p[c], "chosen": c == j,
                                 **({"I_long": I_long[c], "bearing": c_bear[c], "cand_km": c_dist[c]} if compass else {})})
        prev, t = t, cands[j]
        came_from = prev
        if not compass:  # the compass walker prefetches exactly its next offers instead (below)
            T.prefetch(t)
        if compass:
            # the drive after this step's choice sets the next radius; the next offers are known now, so fetching starts before training
            x_drive = {"interest": I[j], "interest_long": I_long[j], "novelty": n[j], "progress": g[j], "surprise": e[j], "novelty_z": nz[j], "progress_z": gz[j]}[sig]
            if step >= drive_start:
                drive.update(float(x_drive))
            if t != prev:
                heading = float(CP.initial_bearing(lat[prev], lon[prev], lat[t], lon[t]))
            r_was, theta_was, info_was = r_now, theta_now, cinfo
            if step + 1 < int(cfg["steps"]):
                r_now, theta_now = next_radius(step + 1), next_theta(heading)
                T.store.prefetch(compass_offers(t, r_now, theta_now)[0])

        # -- train on the chosen tile --------------------------------------------------
        err_before = err_after = np.nan
        if not random_policy:
            xs = x[j]  # the K patches the agent just looked at
            xt = look([t], gen, timeout=600.0)[0][0] if fixed_crops else xs  # training keeps random crops
            batch = xt
            if buf_n > 0:
                ri = torch.randint(0, buf_n, (int(cfg["replay_batch"]),), generator=gen_replay, device=dev)
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
                zt = model.encode(xs).mean(0, keepdim=True)
            if log_prev:  # the scoring crops of each tile, so comparable with candidates.parquet; draws no random numbers
                rec["e_self_after"] = float(S.recon_err(model, look([t], gen, timeout=600.0, fixed=True)[0]))
                rec["e_prev_after"] = float(S.recon_err(model, look([prev], gen, timeout=600.0, fixed=True)[0]))
            # memory: FIFO patch buffer and archive of visited latents (revisits push again)
            for pch in xt:
                buf[buf_ptr] = pch
                buf_ptr = (buf_ptr + 1) % len(buf)
                buf_n = min(buf_n + 1, len(buf))
            arch_tiles.append(t)
            arch_z = zt if arch_z is None else torch.cat([arch_z, zt])
            visits[t] = visits.get(t, 0) + 1

        # -- boredom -------------------------------------------------------------------
        B_before = B
        bored = False
        if not random_policy and not compass and kinds[j] != "bored":
            B = 0.9 * B + 0.1 * float(maxI < 0)
            if B > float(cfg["patience"]):
                bored = True
                torch.save({"model": model.state_dict(), "step": step}, out / f"bored_{step:04d}.pt")
                daydream(model, arch_z, gen_dream, out / "daydreams" / f"bored_{step:04d}.png", int(cfg["k_nn"]))
                B = 0.0
                force_teleport = True

        rec.update(
            tile_idx=t, grid_cell=idx.grid_cell[t], lat=lat[t], lon=lon[t], cloud_cover=float(idx.cloud_cover[t]), tv=bool(idx.tv[t]),
            e=e[j], n=n[j], g=g[j], e_z=ez[j], n_z=nz[j], g_z=gz[j], I=I[j], max_I=maxI, n_candidates=C, jump_type=kinds[j],
            B=B_before, B_after=B, bored_event=bored, err_before=err_before, err_after=err_after,
            dist_km=float(haversine_km(lat[prev], lon[prev], lat[t], lon[t])) if step > 0 else 0.0, sec=time.time() - ts,
        )
        if compass:
            dr = list(info_was["drop"])
            rec.update(r_km=r_was, theta=theta_was, drive_x=float(x_drive), **{f"drive_{k}": v for k, v in drive.state().items() if k != "t"},
                       n_drop_far=dr.count("far"), n_drop_dup=dr.count("dup"), n_drop_self=dr.count("self"), heading=heading if heading is not None else np.nan)
        if T.name != "regional":
            rec.update(cover=str(idx.cover[t]), fetch_sec=float(fst.get("wait_sec", 0.0)), n_fetch=int(fst.get("n", 0)),
                       n_cache_hit=int(fst.get("cache_hits", 0)), n_dropped=len(fst.get("dropped", [])), n_redraw=n_redraw,
                       dropped=",".join(map(str, fst.get("dropped", []))))
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
                  f"tv {df.tv.mean():.2f}  bored {df.bored_event.sum()}  B {B:.2f}  err {df.err_before.mean():.4f}"
                  + (f"  fetch {df.fetch_sec.mean():.2f}s  hit {df.n_cache_hit.sum() / max(df.n_fetch.sum(), 1):.2f}  dropped {df.n_dropped.sum()}"
                     if "fetch_sec" in df else ""), flush=True)

    pd.DataFrame(steps_log).to_parquet(out / "steps.parquet")
    if not random_policy:
        pd.DataFrame(cand_log).to_parquet(out / "candidates.parquet")
        pd.DataFrame(held_log).to_parquet(out / "heldout.parquet")
        torch.save({"model": model.state_dict(), "step": int(cfg["steps"]), "norms": {k: v.state() for k, v in norms.items()}}, out / "final.pt")
        reembed()
        np.savez(out / "archive.npz", z=arch_z.cpu().numpy(), tile_idx=np.array(arch_tiles))
        daydream(model, arch_z, gen_dream, out / "daydreams" / "final.png", int(cfg["k_nn"]))
        if land_log:
            pd.DataFrame(land_log).to_parquet(out / "landings.parquet")
    meta.update(finished=time.strftime("%Y-%m-%d %H:%M:%S"), seconds=round(time.time() - t0, 1))
    if T.name != "regional":
        meta["store"] = T.summary()
        pd.DataFrame(T.store.fetch_log, columns=["tile_idx", "sec", "attempts"]).to_parquet(out / "fetches.parquet")
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
