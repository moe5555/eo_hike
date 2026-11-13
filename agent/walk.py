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
import os
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml
from PIL import Image

from agent import clock as CL
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
RNG_STREAMS = ("start", "neighbours", "offers", "landing", "choice", "init", "crops", "replay", "daydream", "compass", "radius", "time")
# "time" (Moe 2026-11-13): the draw that thins the time offer (time_offer_p < 1); appended, so every earlier stream is unchanged


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
    (global, regional_lazy for development, or a confinement circle). No noisy TV.
    world: landsat_pass swaps in a local Landsat pass (data/landsat_pass.PassStore, `pass_world: <dir>`) behind the same interface;
    its held-out tiles come from the pass (heldout: global means the whole world the store holds)."""

    def __init__(self, cfg: dict, device: str) -> None:
        from data.tile_store import World, open_store

        self.dev, self.cfg = device, cfg
        self.store = open_store(cfg)
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


def run(cfg: dict, name: str, out: Path | None = None, resume: bool = False, stop_after: int | None = None) -> Path:
    """resume and stop_after: the clock walker only (brief v2). resume continues from <out>/resume.pt (the last checkpoint);
    stop_after ends the process after the checkpoint at that step without finishing the walk (tests the resume)."""
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    seed = int(cfg["seed"])
    out = Path(out) if out is not None else RUNS / f"{name}_s{seed}"
    (out / "daydreams").mkdir(parents=True, exist_ok=True)
    if not resume:
        for f in list(out.glob("*.pt")) + list((out / "daydreams").glob("*.png")) + list((out / "parts").glob("*")) + list((out / "contact").glob("*")):
            f.unlink()
    (out / "config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))

    T = load_tiles(cfg, dev)
    idx, lat, lon = T.idx, T.lat, T.lon
    # brief v2 (notes/brief_landsat_v2_run.md): stack clock, the wanderer's clock (agent/clock.py); the start cell comes from the shared start list
    clockm = cfg.get("stack") == "clock"
    t = int(cfg["start_idx"]) if clockm else T.start(cfg["start_lat"], cfg["start_lon"])
    meta = {"run_id": cfg.get("walk_id", out.name), "name": name, "seed": seed, "git": git_hash(), "start_tile": t, "n_tiles": T.N, "device": dev, "torch": torch.__version__, "torch_threads": torch.get_num_threads(), "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    if T.name != "regional":
        meta.update(world=T.name, pool_size=T.pool_size, start_cell=str(idx.grid_cell[t]), start_latlon=[float(lat[t]), float(lon[t])],
                    start_cover=str(idx.cover[t]), confine_center=cfg.get("confine_center"), confine_radius_km=cfg.get("confine_radius_km"),
                    **({"pass_world": cfg["pass_world"]} if T.name == "landsat_pass" else {}))
    (out / "meta.json").write_text(json.dumps(meta, indent=2))

    # walker v2 (notes/brief_landsat_pipeline.md, B): eye grid | two_eye (agent/eyes.py); v1 (the default) is every earlier walker
    eye = cfg.get("eye", "v1")
    assert eye in ("v1", "grid", "two_eye"), eye
    two = eye != "v1"
    if two:
        assert cfg.get("nav", "classic") == "compass" and cfg.get("policy", "curious") == "curious", "eye grid | two_eye needs nav: compass, policy: curious"

    # the revisit rule (Moe 2026-11-12; data/landsat1_world.py `stack`): stack revisit_next shows a cell's acquisitions in date order, one
    # more per visit, and stops offering a cell whose stack has run out. earliest_only (the default) is every earlier walk.
    stack = cfg.get("stack", "earliest_only") == "revisit_next"
    if stack:
        assert cfg.get("world") == "landsat1" and cfg.get("nav", "classic") == "compass", "stack: revisit_next needs world: landsat1 and nav: compass"
        from data.landsat1_store import image_key, split_key

    if clockm:
        assert cfg.get("world") == "landsat1" and cfg.get("nav", "classic") == "compass" and two, "stack: clock needs world: landsat1, nav: compass and eye grid | two_eye"
        from data.landsat1_store import QUIRK_COLS, image_key, split_key

        t_end, cap = CL.to_day(str(cfg["t_end"])), int(cfg["steps"])
        tile_cap = int(cfg["tile_cap"]) if cfg.get("tile_cap") else None  # optional: end at this many distinct tiles (end reason `tiles`)
        # the thinned time offer (Moe 2026-11-13, notes/gen1/time_offer_rule.md): when a later pass exists, it is offered with probability
        # time_offer_p (1 = always, the brief's rule; draws nothing then). The same for the Null: a property of the horizon, not of the choice
        q_time = float(cfg.get("time_offer_p", 1.0))
        time_ok = True
        # lingering (Moe 2026-11-13): once the clock reaches linger_from, the walk may stay as many steps as it spent, on average, per year
        # of clock before (its own pace); then it ends (end reason `linger`). Off unless linger_from is set
        linger_from = CL.to_day(str(cfg["linger_from"])) if cfg.get("linger_from") else None
        linger_entry = linger_len = linger_end = None
        clk = d_cur = int(T.store.days(t)[0])  # the clock starts at the start cell's first acquisition
        cur_key = prev_key = int(image_key(t, 0))
        render_every, ckpt_every = int(cfg.get("render_every", 500)), int(cfg["ckpt_every"])
        assert ckpt_every % render_every == 0, "renders are drawn from the steps in memory: render_every must divide ckpt_every"
        parts = out / "parts"
        (out / "contact").mkdir(exist_ok=True)
        pin = T.store.cache / "pins" / ("_".join(out.resolve().relative_to(RUNS.resolve()).parts) + ".txt")  # data/cache_cap.py never evicts these
        pin.parent.mkdir(parents=True, exist_ok=True)
        meta["clock"] = {"t_end": CL.to_date(t_end), "cap": cap, "start_idx": t, "start_cell": str(idx.grid_cell[t]), "start_clock": CL.to_date(clk), "tile_cap": tile_cap,
                         "time_offer_p": q_time, "linger_from": cfg.get("linger_from"),
                         "archive_last": CL.to_date(int(T.store.ck_day.max())), "condition": cfg.get("condition"), "walk_id": cfg.get("walk_id")}
        (out / "meta.json").write_text(json.dumps(meta, indent=2))

    def key_of(c: int) -> int:
        """The image a cell shows now: under the clock, its acquisition closest to the clock (ties to the earlier pass); under the
        revisit rule, its acquisition of rank = visits so far; otherwise the cell itself."""
        if clockm:
            return int(image_key(c, CL.closest_rank(T.store.days(c), clk)))
        return int(image_key(c, visits.get(c, 0))) if stack else c

    def clock_offers(cands: list[int], kinds: list[str]) -> tuple[list[int], list[str], list[int], bool, bool]:
        """brief v2, 2: each compass offer shown at its acquisition closest to the clock, plus the time offer at the current cell (its
        first acquisition after max(clock, the date now seen), next pass only), when there is one and this step's thinning draw lets it
        through (time_ok). Returns cells, kinds, image keys, whether a later pass exists, whether it is offered."""
        keys = [key_of(c) for c in cands]
        r = CL.time_offer(T.store.days(t), clk, d_cur)
        if r is not None and time_ok:
            cands, kinds, keys = cands + [t], kinds + ["time"], keys + [int(image_key(t, r))]
        return cands, kinds, keys, r is not None, r is not None and time_ok

    def last_key(c: int) -> int:
        """The image a cell showed at its last visit."""
        return int(image_key(c, visits.get(c, 1) - 1)) if stack else c

    def look(ids: list[int], g: torch.Generator, timeout: float | None = None, fixed: bool = False):
        img, is_tv, kept, st = T.get(ids, timeout)
        if not kept:
            return None, kept, st
        if two:  # the two-eye walker cuts its own crops and glances from the whole tile (agent/eyes.py); draws no random numbers here
            return img, kept, st
        off = S.fixed_offsets(kept, K, img.shape[1], crop, img.device) if fixed else None
        return S.patches(img, is_tv, K, crop, g, off), kept, st

    def look_cells(cells: list[int], g: torch.Generator, timeout: float | None = None, fixed: bool = False):
        """look() at offered cells: each shows its current image (key_of); returns the cells that arrived."""
        if not stack:
            return look(cells, g, timeout, fixed)
        x, kept, st = look([key_of(c) for c in cells], g, timeout, fixed)
        return x, [int(c) for c in split_key(kept)[0]], st

    if cfg.get("rng_mode", "legacy") == "split":
        ss = dict(zip(RNG_STREAMS, np.random.SeedSequence(seed).spawn(len(RNG_STREAMS))))
        r_offer, r_land, r_choice, r_compass, r_radius, r_time = (np.random.default_rng(ss[k]) for k in ("offers", "landing", "choice", "compass", "radius", "time"))
        torch.manual_seed(int(ss["init"].generate_state(1)[0]))
        gen, gen_replay, gen_dream = (torch.Generator(device=dev).manual_seed(int(ss[k].generate_state(1)[0])) for k in ("crops", "replay", "daydream"))
    else:
        r_offer = r_land = r_choice = r_compass = r_radius = r_time = np.random.default_rng(seed)
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
            out, info = CP.offers(T.world, t, r, theta, max(snap_tol, snap_floor / r))
            if stack:  # a cell whose acquisitions have all been seen is no longer offered
                keep = [c for c in out if visits.get(c, 0) < T.store.stack_len(c)]
                info["exhausted"] = len(out) - len(keep)
                out = keep
            return out, info

        heading = None
        r_now, theta_now = next_radius(0), next_theta(None)
    visits: dict[int, int] = {}
    came_from = None

    model = opt = te = None
    forget_log, forget_x, forget_kinds = [], None, None
    if not random_policy:
        if two:
            from agent.eyes import TwoEye

            te = TwoEye(cfg, dev)
            model = te.grid
            if clockm:  # crop quirks attached when scored: the cache may evict an offer's file before the walk ends
                te.crop_quirk_fn = lambda keys: np.stack([T.store.crop_quirk_rows(k) for k in keys])
                te.crop_quirk_cols = QUIRK_COLS
            meta["eye"] = {"eye": eye, "novelty_topk": te.k_top, "w": te.w, "jitter_px": te.jitter, "glance_replay_batch": te.glance_replay}
        else:
            model = ConvAE(tuple(int(c * ae_width) for c in CH), int(LATENT * ae_width)).to(dev)
            opt = torch.optim.Adam(model.parameters(), lr=float(cfg["lr"]))
        if cfg.get("ckpt_init", False):  # e09 world-view readout: the network at step 0; saving draws no random numbers
            torch.save({**(te.state() if two else {"model": model.state_dict()}), "step": 0}, out / "ckpt_0000.pt")
        # fixed held-out set: same 200 tiles and crop positions for every run of this crop_px
        hrng = np.random.default_rng(HELDOUT_SEED)
        held_ids = np.sort(hrng.choice(T.heldout_pool, HELDOUT_N, replace=False)).tolist()
        hgen = torch.Generator(device=dev).manual_seed(HELDOUT_SEED)
        held_x, held_kept, _ = look(held_ids, hgen, timeout=600.0)
        meta["heldout_n"] = len(held_kept)
        if two and cfg.get("forget_set"):  # brief C10: fixed ordinary tiles (sea, sand, field), errors of both eyes every forget_every steps
            fs = pd.read_csv(ROOT / cfg["forget_set"])
            forget_x, fkept, _ = look(fs.tile_idx.tolist(), hgen, timeout=600.0)
            forget_kinds = fs.set_index("tile_idx").kind.reindex(fkept).tolist()
            forget_ids = fkept
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
        if two:
            eg, el = te.errors(held_x)
            held_log.append({"step": step, "heldout_mse": float(eg.mean()), "heldout_mse_glance": float(el.mean())})
            return
        held_log.append({"step": step, "heldout_mse": float(S.recon_err(model, held_x).mean())})

    def forget_eval(step):
        eg, el = te.errors(forget_x)
        forget_log.extend({"step": step, "tile_idx": i, "kind": k, "e_grid": float(a), "e_glance": float(b)}
                          for i, k, a, b in zip(forget_ids, forget_kinds, eg, el))

    def render_contact(s1: int) -> None:
        """brief v2, 4: a contact sheet of the steps since the last one (every render_every steps, and at the end), as the walker saw them."""
        from analysis.e12.contact_sheet import sheet

        s_first = (s1 - 1) // render_every * render_every
        page = pd.DataFrame([r for r in steps_log if r["step"] >= s_first])
        title = (f"{cfg.get('walk_id', out.name)}: steps {s_first}-{s1 - 1}, clock {page.clock.iloc[0]} to {page.clock.iloc[-1]}. Outline: top crop. "
                 f"Bars: glance / grid / progress share at the choice. WAIT = time offer; +Nd = tile date minus clock; N = night.")
        sheet(T.store, page, title, th=96, cols=25).save(out / "contact" / f"steps_{s_first:05d}-{s1 - 1:05d}.jpg", quality=85)

    def reembed():
        nonlocal arch_z
        if two:
            def get(ids):
                img, kept, _ = look(ids, gen, timeout=600.0)
                assert len(kept) == len(ids), "visited tile missing from the store"
                return img
            te.reembed(get)
            return
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
    if forget_x is not None:
        forget_eval(0)

    step0 = 0

    def resume_state(s1: int) -> dict:
        return {"step": s1, "t": t, "clk": clk, "d_cur": d_cur, "cur_key": cur_key, "prev_key": prev_key, "came_from": came_from, "heading": heading,
                "r_now": r_now, "theta_now": theta_now, "visits": visits, "te": te, "drive": drive, "norms": norms, "long_norms": long_norms,
                "held_log": held_log, "forget_log": forget_log, "land_log": land_log,
                "rng": {"offer": r_offer, "land": r_land, "choice": r_choice, "compass": r_compass, "radius": r_radius, "time": r_time},
                "linger": (linger_entry, linger_len, linger_end),
                "torch_gen": {"crops": gen.get_state(), "replay": gen_replay.get_state(), "daydream": gen_dream.get_state()},
                "torch_rng": torch.get_rng_state(), "elapsed": time.time() - t0, "meta": meta}

    if clockm and resume:  # brief v2, 4: continue from the last checkpoint, every state of the walker as it was
        R = torch.load(out / "resume.pt", weights_only=False, map_location=dev)
        step0, t, clk, d_cur, cur_key, prev_key = R["step"], R["t"], R["clk"], R["d_cur"], R["cur_key"], R["prev_key"]
        came_from, heading, r_now, theta_now, visits = R["came_from"], R["heading"], R["r_now"], R["theta_now"], R["visits"]
        te, drive, norms, long_norms = R["te"], R["drive"], R["norms"], R["long_norms"]
        model = te.grid
        te.crop_quirk_fn = lambda keys: np.stack([T.store.crop_quirk_rows(k) for k in keys])
        held_log[:], forget_log[:], land_log[:] = R["held_log"], R["forget_log"], R["land_log"]
        r_offer, r_land, r_choice, r_compass, r_radius = (R["rng"][k] for k in ("offer", "land", "choice", "compass", "radius"))
        r_time = R["rng"].get("time", r_time)
        linger_entry, linger_len, linger_end = R.get("linger", (None, None, None))
        gen.set_state(R["torch_gen"]["crops"])
        gen_replay.set_state(R["torch_gen"]["replay"])
        gen_dream.set_state(R["torch_gen"]["daydream"])
        torch.set_rng_state(R["torch_rng"])
        t0 = time.time() - R["elapsed"]
        meta = {**R["meta"], "resumed": meta.get("resumed", []) + R["meta"].get("resumed", []) + [{"at_step": step0, "time": time.strftime("%Y-%m-%d %H:%M:%S")}]}
        for f in parts.glob("*"):  # chunks written after the checkpoint (a crash between flush and resume.pt) are written again
            k = int(f.stem.rsplit("_", 1)[1])
            if k >= te.n_parts:
                f.unlink()
        pin.write_text("".join(T.store.cache_path(k) + "\n" for k in dict.fromkeys(te.tiles)))
        print(f"[{out.name}] resumed at step {step0}, clock {CL.to_date(clk)}", flush=True)
    end_reason = None

    import faulthandler

    for step in range(step0, int(cfg["steps"])):
        ts = time.time()
        faulthandler.dump_traceback_later(900, exit=False)  # a step stalled for 15 min writes every thread's stack to the log (re-armed each step)
        # -- candidates ------------------------------------------------------------
        if clockm and q_time < 1.0:  # this step's thinning draw: the time offer (if a later pass exists) comes through with probability q
            time_ok = bool(r_time.random() < q_time)
        if compass:
            cands, cinfo = compass_offers(t, r_now, theta_now)
            n_turn = 0
            while not cands and n_turn < 20:  # every target dropped (open ocean all round): turn the compass
                n_turn += 1
                theta_now = float(r_compass.uniform(0.0, 360.0))
                cands, cinfo = compass_offers(t, r_now, theta_now)
            if not cands:  # still nothing: the eight indexed cells nearest to this one
                if stack:
                    near = T.world.pool[T.world.tree.query(np.radians([[lat[t], lon[t]]]), k=200)[1][0]]
                    cands = [int(c) for c in near if c != t and visits.get(int(c), 0) < T.store.stack_len(int(c))][:8]
                else:
                    cands = [int(c) for c in T.world.pool[T.world.tree.query(np.radians([[lat[t], lon[t]]]), k=9)[1][0]] if c != t][:8]
            kinds = ["compass"] * len(cands)
            if offer_stay:
                cands, kinds = cands + [t], kinds + ["stay"]
            if clockm:
                cands, kinds, ckeys, time_exists, time_offered = clock_offers(cands, kinds)
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
        if clockm:  # offers are image keys: the time offer is the current cell at a later date
            x, kept, fst = look(ckeys, gen)
            n_redraw = 0
            if not kept:  # nothing arrived: wait longer rather than stall the walk on an empty choice
                x, kept, fst2 = look(ckeys, gen, timeout=120.0)
                fst["wait_sec"] += fst2["wait_sec"]
                fst["dropped"] = fst2["dropped"]
            while not kept:  # still nothing: turn the compass and try eight new cells at the same radius
                n_redraw += 1
                if n_redraw > 50:
                    raise RuntimeError(f"step {step}: no offer could be fetched after {n_redraw - 1} redraws")
                theta_now = float(r_compass.uniform(0.0, 360.0))
                cands, cinfo = compass_offers(t, r_now, theta_now)
                cands = cands or [T.random_tile(r_land)]
                cands, kinds, ckeys, time_exists, time_offered = clock_offers(cands, ["compass"] * len(cands))
                x, kept, fst2 = look(ckeys, gen, timeout=120.0)
                fst["wait_sec"] += fst2["wait_sec"]
                fst["dropped"] = fst["dropped"] + fst2["dropped"]
            ks = set(kept)
            m = [k in ks for k in ckeys]
            cands, kinds, ckeys = ([v for v, ok in zip(l, m) if ok] for l in (cands, kinds, ckeys))
        else:
            x, kept, fst = look_cells(cands, gen, fixed=fixed_crops) if not random_policy else (None, cands, {})
            n_redraw = 0
            if not random_policy and len(kept) < len(cands):
                if not kept:  # nothing arrived: wait longer rather than stall the walk on an empty choice
                    x, kept, fst2 = look_cells(cands, gen, timeout=120.0, fixed=fixed_crops)
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
                    x, kept, fst2 = look_cells(cands, gen, timeout=120.0, fixed=fixed_crops)
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
        elif two:  # walker v2: glance and grid (agent/eyes.py); n is the pooled grid novelty, e the grid surprise (mean over crops)
            if clockm:
                sc = te.score(step, x, ckeys, set(te.tiles), refresh)
            else:
                sc = te.score(step, x, [key_of(c) for c in cands], set(te.tiles), refresh) if stack else te.score(step, x, cands, set(visits), refresh)
            e, n, g = sc["raw"]["e"], sc["raw"]["grid"], sc["raw"]["g"]
            ez, nz, gz = sc["z"]["e"], sc["z"]["grid"], sc["z"]["g"]
            I, I_long = sc["I"], sc["I_long"]
            if return_cost:
                rc = return_cost * np.log1p(np.array([visits.get(c, 0) for c in cands], dtype=np.float64))
                I, I_long = I - rc, I_long - rc
            c_bear = CP.initial_bearing(lat[t], lon[t], lat[cands], lon[cands])
            c_dist = haversine_km(lat[t], lon[t], lat[cands], lon[cands])
            if clockm:  # the time offer has no bearing
                c_bear = np.where(np.array(kinds) == "time", np.nan, c_bear)
        else:
            g_t, _, _ = S.progress_probe(model, x, float(cfg["lr"]), int(cfg["probe_steps"]))
            e_t = S.recon_err(model, x)
            z_c = S.mean_latent(model, x)
            if stack:  # a revisited cell shows a new acquisition: only an image already in the archive is refreshed (never, by construction)
                seen = [key_of(c) for c in cands if key_of(c) in set(arch_tiles)] if refresh and arch_z is not None else []
            else:
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
        if not random_policy:
            if compass and persistence and heading is not None:  # temperament: a pull towards the current heading
                I = I + persistence * np.cos(np.radians(c_bear - heading))
            p = CL.choice_probs(I, float(cfg["temperature"]), uniform_choice)  # the Null: uniform over the offers available this step
            j = int(r_choice.choice(C, p=p))
            maxI = float(I.max())
            rec.update(p_chosen=float(p[j]), best_offer=bool(j == int(np.argmax(I))))  # brief C8; draws nothing
            extra = ({"n_glance": sc["raw"]["glance"], "n_glance_z": sc["z"]["glance"], "n_v1": sc["n_v1"], "e_max": sc["e_max"], "e_glance": sc["e_glance"]}
                     if two else {})
            if clockm:  # each offer's image, date, offset from the clock and pixel quirks (fill, cloud, dropped) and night
                ka = np.array(ckeys, np.int64)
                cq = np.stack([T.store.quirk_row(k) for k in ckeys])
                cday = T.store.day_of(ka).astype(np.int64)
                extra.update(image_key=ka, acq_rank=split_key(ka)[1], day=cday, clock_day=np.full(C, clk), offset_days=cday - clk, night=T.store.night_of(ka),
                             q_fill=cq[:, 0], q_cloud=cq[:, 1], q_dropped=cq[:, 2])
            for c in range(C):
                cand_log.append({"step": step, "tile_idx": cands[c], "kind": kinds[c], "e": e[c], "n": n[c], "g": g[c], "e_z": ez[c], "n_z": nz[c], "g_z": gz[c], "I": I[c], "p": p[c], "chosen": c == j,
                                 **({"I_long": I_long[c], "bearing": c_bear[c], "cand_km": c_dist[c]} if compass else {}),
                                 **{k: v[c] for k, v in extra.items()}, **({"image_key": key_of(cands[c]), "acq_rank": visits.get(cands[c], 0)} if stack else {})})
        prev, t = t, cands[j]
        came_from = prev
        if clockm:  # a time offer sets the clock to its date; sideways moves never change it
            clk_before, prev_key, cur_key = clk, cur_key, ckeys[j]
            if kinds[j] == "time":
                clk = int(T.store.day_of(cur_key))
            d_cur = int(T.store.day_of(cur_key))
            assert cur_key == key_of(t), "the tile seen is not its cell's acquisition closest to the clock"
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
                nxt = compass_offers(t, r_now, theta_now)[0]
                T.store.prefetch(clock_offers(nxt, ["compass"] * len(nxt))[2] if clockm else [key_of(c) for c in nxt])

        # -- train on the chosen tile --------------------------------------------------
        err_before = err_after = np.nan
        if two:
            xj = x[j : j + 1]
            tr = te.train(step, xj, sc["n_crop"][j], gen, gen_replay)
            err_before, err_after = tr["err_before"], tr["err_after"]
            rec.update(err_glance_before=tr["err_glance_before"], err_glance_after=tr["err_glance_after"], **te.log_choice(j, sc))
            if log_prev:  # grid error (mean over the 16 crops) on this tile and the one before, after the update; draws no random numbers
                rec["e_self_after"] = float(te.errors(xj)[0][0])
                pk = prev_key if clockm else (last_key(prev) if prev != t else key_of(prev))
                rec["e_prev_after"] = float(te.errors(look([pk], gen, timeout=600.0)[0])[0][0])
            if stack:
                rec.update(image_key=key_of(t), acq_rank=visits.get(t, 0))
            if clockm:
                rec.update(image_key=cur_key, acq_rank=int(split_key(cur_key)[1]))
                if cur_key not in te.tiles:
                    with open(pin, "a") as fh:
                        fh.write(T.store.cache_path(cur_key) + "\n")
            te.remember(key_of(t), xj)
            visits[t] = visits.get(t, 0) + 1
        elif not random_policy:
            xs = x[j]  # the K patches the agent just looked at
            xt = look([key_of(t)], gen, timeout=600.0)[0][0] if fixed_crops else xs  # training keeps random crops
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
                rec["e_self_after"] = float(S.recon_err(model, look([key_of(t)], gen, timeout=600.0, fixed=True)[0]))
                rec["e_prev_after"] = float(S.recon_err(model, look([last_key(prev) if prev != t else key_of(prev)], gen, timeout=600.0, fixed=True)[0]))
            # memory: FIFO patch buffer and archive of visited latents (revisits push again)
            for pch in xt:
                buf[buf_ptr] = pch
                buf_ptr = (buf_ptr + 1) % len(buf)
                buf_n = min(buf_n + 1, len(buf))
            if stack:
                rec.update(image_key=key_of(t), acq_rank=visits.get(t, 0))
            arch_tiles.append(key_of(t))
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
                       n_drop_far=dr.count("far"), n_drop_dup=dr.count("dup"), n_drop_self=dr.count("self"), heading=heading if heading is not None else np.nan,
                       **({"n_drop_exhausted": int(info_was.get("exhausted", 0))} if stack else {}))
        if T.name != "regional":
            rec.update(cover=str(idx.cover[t]), fetch_sec=float(fst.get("wait_sec", 0.0)), n_fetch=int(fst.get("n", 0)),
                       n_cache_hit=int(fst.get("cache_hits", 0)), n_dropped=len(fst.get("dropped", [])), n_redraw=n_redraw,
                       dropped=",".join(map(str, fst.get("dropped", []))))
        if clockm:  # brief v2, 4: the clock, the offer taken, and the pixel quirks of the tile now seen
            q = T.store.quirk_row(cur_key)
            slot = [k for k in range(CP.N_BEARINGS) if int(cinfo["cell"][k]) == t and cinfo["drop"][k] == ""] if kinds[j] == "compass" else []
            rec.update(clock_before=CL.to_date(clk_before), clock=CL.to_date(clk), clock_day=clk, tile_date=CL.to_date(d_cur), tile_day=d_cur,
                       offset_days=d_cur - clk, offer_kind=kinds[j], compass_slot=slot[0] if slot else -1,
                       wait_days=float(clk - clk_before) if kinds[j] == "time" else np.nan, n_offers=C, time_exists=bool(time_exists), time_offered=bool(time_offered),
                       time_available="time" in kinds, night=bool(T.store.night_of(cur_key)), cloud_cover=float(q[1]),
                       **{f"q_{k}": float(v) for k, v in zip(QUIRK_COLS, q)})
        steps_log.append(rec)

        s1 = step + 1
        if not random_policy:
            if s1 % int(cfg["reembed_every"]) == 0:
                reembed()
            if s1 % int(cfg["heldout_every"]) == 0:
                heldout_eval(s1)
            if s1 % int(cfg["ckpt_every"]) == 0:
                torch.save({**(te.state() if two else {"model": model.state_dict()}), "step": s1}, out / f"ckpt_{s1:04d}.pt")
            if forget_x is not None and s1 % int(cfg.get("forget_every", 500)) == 0:
                forget_eval(s1)
        if s1 % 100 == 0:
            df = pd.DataFrame(steps_log[-100:])
            print(f"[{out.name}] step {s1}  {time.time() - t0:.0f}s  uniq {len(set(te.tiles)) if two else len(set(r['tile_idx'] for r in steps_log))}  "
                  + (f"clock {CL.to_date(clk)}  waits {(df.offer_kind == 'time').mean():.2f}  " if clockm else "")
                  + 
                  f"tv {df.tv.mean():.2f}  bored {df.bored_event.sum()}  B {B:.2f}  err {df.err_before.mean():.4f}"
                  + (f"  fetch {df.fetch_sec.mean():.2f}s  hit {df.n_cache_hit.sum() / max(df.n_fetch.sum(), 1):.2f}  dropped {df.n_dropped.sum()}"
                     if "fetch_sec" in df else ""), flush=True)
        if clockm:
            # brief v2, 3: the only ways a walk ends, the clock reaching T_end or the step cap. There is no death
            if linger_from is not None and linger_entry is None and clk >= linger_from:  # the clock has reached the last period: how long it may stay
                linger_entry = s1
                years = (linger_from - CL.to_day(meta["clock"]["start_clock"])) / 365.25
                linger_len = int(round(s1 / years))
                linger_end = s1 + linger_len
                meta["clock"].update(linger_entry_step=s1, linger_entry_clock=CL.to_date(clk), linger_steps=linger_len)
                print(f"[{out.name}] step {s1}: the clock reached {CL.to_date(linger_from)} ({CL.to_date(clk)}); it may linger {linger_len} steps "
                      f"(its pace: {s1} steps over {years:.2f} years of clock)", flush=True)
            end_reason = CL.end_reason(clk, s1, t_end, cap, len(set(te.tiles)), tile_cap, linger_end)
            if render_every and (s1 % render_every == 0 or end_reason):
                render_contact(s1)
            if end_reason:
                break
            if s1 % ckpt_every == 0:  # brief v2, 4: checkpoint (encoders above, every 1,000 steps), logs flushed, the state to resume from
                te.flush(parts)
                k = te.n_parts - 1
                pd.DataFrame(steps_log).to_parquet(parts / f"steps_{k:03d}.parquet")
                pd.DataFrame(cand_log).to_parquet(parts / f"candidates_{k:03d}.parquet")
                steps_log.clear()
                cand_log.clear()
                fn, te.crop_quirk_fn = te.crop_quirk_fn, None  # a closure over the store: not part of the state, set again on resume
                torch.save(resume_state(s1), out / "resume.tmp")
                te.crop_quirk_fn = fn
                os.replace(out / "resume.tmp", out / "resume.pt")
                if stop_after is not None and s1 >= stop_after:  # tests only: an interruption right after a checkpoint
                    print(f"[{out.name}] stopped after the checkpoint at step {s1} (stop_after)", flush=True)
                    return out

    if clockm and te.n_parts:  # chunks flushed at checkpoints, then the rest
        steps_log[:0] = [r for k in range(te.n_parts) for r in pd.read_parquet(parts / f"steps_{k:03d}.parquet").to_dict("records")]
        cand_log[:0] = [r for k in range(te.n_parts) for r in pd.read_parquet(parts / f"candidates_{k:03d}.parquet").to_dict("records")]
    sl = pd.DataFrame(steps_log)
    if (stack or clockm) and "image_key" in sl:  # the acquisition each step showed: scene, date, level, night
        a = T.store.acquisitions(sl.image_key.to_numpy())
        sl = sl.assign(acq_scene=a.scene.to_numpy(), acq_date=a.timestamp.to_numpy(), acq_level=a.level.to_numpy(), acq_night=a.night.to_numpy(),
                       acq_sun=a.sun_elevation.to_numpy())
    sl.to_parquet(out / "steps.parquet")
    if not random_policy:
        pd.DataFrame(cand_log).to_parquet(out / "candidates.parquet")
        pd.DataFrame(held_log).to_parquet(out / "heldout.parquet")
        if two:  # final.pt's "model" is the grid network, so readouts that load a ConvAE from it still work; archive.npz is the shadow
            torch.save({**te.state(), "step": int(cfg["steps"]), "norms": {k: v.state() for k, v in te.norms.items()}}, out / "final.pt")
            reembed()
            np.savez(out / "archive.npz", z=te.mem_v1.cpu().numpy(), tile_idx=np.array(te.tiles))
            daydream(te.grid, te.mem_crop.flatten(0, 1), gen_dream, out / "daydreams" / "final.png", int(cfg["k_nn"]))
            te.save_logs(out, None if clockm else T.store)  # the clock walker attached crop quirks when it scored
            if forget_log:
                pd.DataFrame(forget_log).to_parquet(out / "forgetting.parquet")
        else:
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
    if clockm:  # brief v2, 4: the walk's summary
        acq = T.store.acquisitions(sl.image_key.to_numpy())
        walk = {"walk_id": cfg.get("walk_id", out.name), "condition": cfg.get("condition"), "seed": seed, "start_idx": int(cfg["start_idx"]),
                "start_cell": meta["clock"]["start_cell"], "start_clock": meta["clock"]["start_clock"], "end_clock": CL.to_date(clk),
                "steps": len(sl), "end_reason": end_reason, "unique_tiles": int(sl.image_key.nunique()), "unique_cells": int(sl.tile_idx.nunique()),
                "waits": int((sl.offer_kind == "time").sum()), "t_end": CL.to_date(t_end), "cap": cap,
                "night_share": float(acq.night.mean()), "seconds": round(time.time() - t0, 1), "git": meta["git"],
                "time_offer_p": q_time, "linger_from": cfg.get("linger_from"), "linger_entry_step": linger_entry, "linger_steps": linger_len}
        meta["walk"] = walk
        (out / "walk.json").write_text(json.dumps(walk, indent=2))
        pin.unlink(missing_ok=True)
        (out / "resume.pt").unlink(missing_ok=True)
        for f in parts.glob("*"):
            f.unlink()
        parts.rmdir() if parts.exists() else None
    (out / "meta.json").write_text(json.dumps(meta, indent=2, default=str))
    print(f"[{out.name}] done in {time.time() - t0:.0f}s -> {out}" + (f"  end {end_reason}, clock {CL.to_date(clk)}" if clockm else ""))
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
    import faulthandler
    import signal

    faulthandler.register(signal.SIGUSR1, all_threads=True)  # kill -USR1 <pid>: every thread's stack into the walk's log
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--steps", type=int)
    ap.add_argument("--name")
    # brief v2: one wanderer per start cell of the shared start list; the walk number is its row (0-based) and its seed
    ap.add_argument("--walk", type=int, help="row of the config's start_list: the start cell; seed = walk unless --seed")
    ap.add_argument("--phase", default="gen1", help="runs/<phase>/<condition>/w<walk>/ (dryrun | gen1 | smoke | test)")
    ap.add_argument("--resume", action="store_true", help="continue from the walk's last checkpoint (resume.pt)")
    ap.add_argument("--stop-after", type=int, help="tests: end the process after the checkpoint at this step")
    ap.add_argument("--tile-cap", type=int, help="also end the walk at this many distinct tiles (end reason `tiles`)")
    ap.add_argument("--t-end", help="the clock date that ends the walk (end reason `time`), instead of the config's t_end")
    ap.add_argument("--time-offer-p", type=float, help="probability that an existing time offer is offered on a step (thinning; default 1)")
    ap.add_argument("--linger-from", help="once the clock reaches this date, the walk may stay its own steps-per-year, then ends (`linger`)")
    a = ap.parse_args()
    cfg = yaml.safe_load(Path(a.config).read_text())
    if a.seed is not None:
        cfg["seed"] = a.seed
    if a.steps is not None:
        cfg["steps"] = a.steps
    if a.tile_cap is not None:
        cfg["tile_cap"] = a.tile_cap
    if a.t_end is not None:
        cfg["t_end"] = a.t_end
    if a.time_offer_p is not None:
        cfg["time_offer_p"] = a.time_offer_p
    if a.linger_from is not None:
        cfg["linger_from"] = a.linger_from
    if a.walk is not None:
        sl = pd.read_csv(ROOT / cfg["start_list"])
        cfg["start_idx"] = int(sl.idx.iloc[a.walk])
        cfg["seed"] = a.walk if a.seed is None else a.seed
        cfg["walk_id"] = f"{cfg['condition']}_w{a.walk:03d}"
        run(cfg, cfg["walk_id"], RUNS / a.phase / cfg["condition"] / f"w{a.walk:03d}", resume=a.resume, stop_after=a.stop_after)
        return
    run(cfg, a.name or Path(a.config).stem)


if __name__ == "__main__":
    main()
