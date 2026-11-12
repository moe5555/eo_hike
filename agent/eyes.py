"""Walker v2's eyes (notes/brief_landsat_pipeline.md, B and C): a glance at the whole tile and a grid of crops over it, each with its
own network and memory. Used by agent/walk.py when `eye: grid | two_eye` (default `v1`: the walker's eye of every earlier walk).

- Glance: the whole 256 px tile, area-averaged to 32 x 32 (~333 m/px), encoded by the glance network. Glance memory: one glance
  latent per visit; novelty = mean distance to the k_nn nearest.
- Grid: 16 non-overlapping 64 px crops (4 x 4, the whole tile), each area-averaged to 32 x 32 (~83 m/px), encoded by the grid
  network. Crop memory per place: all 16 crop latents of every visit. A crop's distance to a remembered place is its distance to
  that place's nearest crop; its novelty is the mean over the k_nn nearest places. The tile's grid novelty pools the 16 crop
  novelties by the mean of the top `novelty_topk` (16 = the mean, 1 = the maximum).
- Progress: the grid network's learning-progress probe (agent/signals.progress_probe) on a checkerboard split of the 16 crops: three
  Adam steps on the 8 "black" crops, error drop on the 8 "white" ones. Tile-level, as v1.
- Surprise: reconstruction error per eye (glance; grid crops pooled by mean, and max). Weighted by w_e (0: not a drive).
- Interest: w_glance * z(glance novelty) + w_grid * z(grid novelty) + w_g * z(progress) + w_e * z(surprise), each z a running z-score
  over the offers (agent/signals.RunningNorm, ema_alpha); the same on the long yardstick for the compass drive (interest_long).
  eye `grid` is this with w_glance = 0; the glance is still computed, trained and logged.
- Training: the grid network on 16 crops drawn from the chosen tile's top-k crops by novelty (cycling through them, each with a
  uniform jitter of up to jitter_px) plus replay_batch from its crop buffer: it learns, and can tire of, what attracted it. The
  glance network on the chosen glance plus glance_replay_batch past glances. update_steps Adam steps each. Memory takes every one of
  the 16 grid crops (seen), after training, as v1's archive.
- Shadow: a v1-style archive of tile-mean grid latents in parallel; v1's novelty (kNN over tile means) is logged for every offer. It
  draws no random numbers and changes nothing; it is what archive.npz holds (one row per visit).
Hand-set here (premises of the eye, named in the configs): the 4 x 4 grid, the 32 px input, top-k, cycling the top-k crops to 16
training crops, jitter_px, glance_replay_batch, the checkerboard split.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

from agent import signals as S
from agent.model import CH, LATENT, ConvAE

GRID = 4
N_CROPS = GRID * GRID
# checkerboard: crops with (row + col) even first, then odd; the progress probe trains on the first half and measures on the second
CHECKER = [k for k in range(N_CROPS) if sum(divmod(k, GRID)) % 2 == 0] + [k for k in range(N_CROPS) if sum(divmod(k, GRID)) % 2 == 1]
EDGE = np.array([r in (0, GRID - 1) or c in (0, GRID - 1) for r, c in (divmod(k, GRID) for k in range(N_CROPS))])


def grid_offsets(C: int, H: int, device) -> tuple[torch.Tensor, torch.Tensor]:
    step = H // GRID
    k = torch.arange(N_CROPS, device=device)
    oy, ox = (k // GRID) * step, (k % GRID) * step
    return oy.expand(C, -1), ox.expand(C, -1)


def grid_crops(img: torch.Tensor) -> torch.Tensor:
    """uint8 [C, H, W, 3] -> [C, 16, 3, 32, 32] in [0, 1]: the 4 x 4 grid, each crop area-averaged to 32 px."""
    C, H = img.shape[0], img.shape[1]
    return S.patches(img, torch.zeros(C, dtype=torch.bool, device=img.device), N_CROPS, H // GRID, None, grid_offsets(C, H, img.device))


def glances(img: torch.Tensor) -> torch.Tensor:
    """uint8 [C, H, W, 3] -> [C, 3, 32, 32] in [0, 1]: the whole tile area-averaged to 32 px."""
    x = img.permute(0, 3, 1, 2).float() / 255.0
    return F.interpolate(x, size=(S.IN_PX, S.IN_PX), mode="area")


def knn_mean(z: torch.Tensor, mem: torch.Tensor | None, k: int) -> torch.Tensor:
    if mem is None or len(mem) == 0:
        return torch.zeros(len(z), device=z.device)
    d = torch.cdist(z, mem)
    return d.topk(min(k, len(mem)), dim=1, largest=False).values.mean(1)


def place_novelty(zc: torch.Tensor, mem: torch.Tensor | None, k: int) -> torch.Tensor:
    """zc [C, 16, D], mem [M, 16, D] -> [C, 16]: per crop, the mean over the k nearest places of the distance to each place's nearest crop."""
    C = zc.shape[0]
    if mem is None or len(mem) == 0:
        return torch.zeros(C, N_CROPS, device=zc.device)
    M = mem.shape[0]
    d = torch.cdist(zc.reshape(C * N_CROPS, -1), mem.reshape(M * N_CROPS, -1)).view(C * N_CROPS, M, N_CROPS).amin(-1)
    return d.topk(min(k, M), dim=1, largest=False).values.mean(1).view(C, N_CROPS)


def topk_mean(n: torch.Tensor, k: int) -> tuple[torch.Tensor, torch.Tensor]:
    """n [C, 16] -> (pooled [C], rank [C, 16]: 0 = the most novel crop of its tile). Ties keep crop order."""
    order = torch.sort(n, dim=1, descending=True, stable=True).indices
    rank = torch.empty_like(order)
    rank.scatter_(1, order, torch.arange(N_CROPS, device=n.device).expand_as(order))
    return torch.gather(n, 1, order[:, :k]).mean(1), rank


class TwoEye:
    def __init__(self, cfg: dict, dev: str) -> None:
        self.cfg, self.dev = cfg, dev
        self.eye = cfg["eye"]
        assert self.eye in ("grid", "two_eye"), self.eye
        self.k_top = int(cfg.get("novelty_topk", 4))
        self.k_nn = int(cfg["k_nn"])
        self.unit = bool(cfg.get("normalise_latents", False))
        self.w = {"glance": float(cfg.get("w_glance", 1.0)), "grid": float(cfg.get("w_grid", cfg["w_n"])), "g": float(cfg["w_g"]), "e": float(cfg["w_e"])}
        if self.eye == "grid":
            assert self.w["glance"] == 0.0, "eye: grid is the grid with w_glance = 0"
        self.jitter = int(cfg.get("jitter_px", 4))
        self.glance_replay = int(cfg.get("glance_replay_batch", 15))
        self.lr, self.probe_steps, self.update_steps = float(cfg["lr"]), int(cfg["probe_steps"]), int(cfg["update_steps"])
        aw = float(cfg.get("ae_width", 1.0))
        # the global torch RNG is seeded by walk.py (stream "init"): the grid network first, then the glance network
        self.grid = ConvAE(tuple(int(c * aw) for c in CH), int(LATENT * aw)).to(dev)
        self.glance = ConvAE(tuple(int(c * aw) for c in CH), int(LATENT * aw)).to(dev)
        self.opt_grid = torch.optim.Adam(self.grid.parameters(), lr=self.lr)
        self.opt_glance = torch.optim.Adam(self.glance.parameters(), lr=self.lr)
        self.buf = torch.zeros(int(cfg["buffer_size"]), 3, S.IN_PX, S.IN_PX, device=dev)
        self.gbuf = torch.zeros(int(cfg.get("glance_buffer_size", cfg["buffer_size"])), 3, S.IN_PX, S.IN_PX, device=dev)
        self.buf_n = self.buf_ptr = self.gbuf_n = self.gbuf_ptr = 0
        self.tiles: list[int] = []  # one entry per visit: the crop-to-tile map of every memory
        self.mem_crop: torch.Tensor | None = None  # [M, 16, D]
        self.mem_glance: torch.Tensor | None = None  # [M, D]
        self.mem_v1: torch.Tensor | None = None  # [M, D], tile means of the grid latents (the shadow)
        alpha, alpha_long = float(cfg["ema_alpha"]), float(cfg.get("ema_alpha_long", 0.002))
        from agent import compass as CP

        self.norms = {k: S.RunningNorm(alpha) for k in ("glance", "grid", "g", "e", "v1")}
        self.long = {k: CP.LongNorm(alpha_long) for k in ("glance", "grid", "g", "e")}
        self.crop_log: list[pd.DataFrame] = []
        self.train_log: list[dict] = []
        self.glance_err: list[np.ndarray] = []
        self.crop_lat: list[np.ndarray] = []
        self.glance_lat: list[np.ndarray] = []

    # -- encoding ------------------------------------------------------------------------------------------------------------
    @torch.no_grad()
    def encode(self, img: torch.Tensor) -> dict:
        xg, xl = grid_crops(img), glances(img)
        C = xg.shape[0]
        flat = xg.flatten(0, 1)
        e_crop = ((self.grid(flat) - flat) ** 2).flatten(1).mean(1).view(C, N_CROPS)
        zg = self.grid.encode(flat).view(C, N_CROPS, -1)
        rl = self.glance(xl)
        e_map = ((rl - xl) ** 2).mean(1)  # [C, 32, 32]
        zl = self.glance.encode(xl)
        return {"xg": xg, "xl": xl, "e_crop": e_crop, "zg": zg, "zl": zl, "e_map": e_map}

    def _u(self, z: torch.Tensor) -> torch.Tensor:
        return F.normalize(z, dim=-1) if self.unit else z

    # -- scoring -------------------------------------------------------------------------------------------------------------
    def score(self, step: int, img: torch.Tensor, cands: list[int], seen: set[int], refresh: bool) -> dict:
        """Signals for the offers. img uint8 [C, H, W, 3]. Returns numpy arrays per offer and the encodings."""
        enc = self.encode(img)
        zg, zl = enc["zg"], enc["zl"]
        if refresh and self.mem_crop is not None:  # a fresh look at revisited offers replaces their stale memories (v1's refresh_archive)
            at = torch.as_tensor(self.tiles, device=self.dev)
            for c, cid in enumerate(cands):
                if cid in seen:
                    m = at == cid
                    self.mem_crop[m], self.mem_glance[m], self.mem_v1[m] = zg[c], zl[c], zg[c].mean(0)
        empty = self.mem_crop is None
        n_crop = place_novelty(self._u(zg), None if empty else self._u(self.mem_crop), self.k_nn)
        n_grid, rank = topk_mean(n_crop, self.k_top)
        n_glance = knn_mean(self._u(zl), None if empty else self._u(self.mem_glance), self.k_nn)
        n_v1 = knn_mean(self._u(zg.mean(1)), None if empty else self._u(self.mem_v1), self.k_nn)
        g, _, _ = S.progress_probe(self.grid, enc["xg"][:, CHECKER], self.lr, self.probe_steps)
        e = enc["e_crop"].mean(1)
        raw = {"glance": n_glance, "grid": n_grid, "g": g, "e": e}
        z = {k: (self.norms[k](v) if (k in ("g", "e") or not empty) else torch.zeros_like(v)) for k, v in raw.items()}
        z_v1 = self.norms["v1"](n_v1) if not empty else torch.zeros_like(n_v1)
        npy = lambda t: t.detach().cpu().numpy().astype(np.float64)  # noqa: E731
        raw, z = {k: npy(v) for k, v in raw.items()}, {k: npy(v) for k, v in z.items()}
        lz = {k: (self.long[k](raw[k]) if (k in ("g", "e") or not empty) else np.zeros(len(cands))) for k in raw}
        contrib = {k: self.w[k] * z[k] for k in raw}
        I = sum(contrib.values())
        I_long = sum(self.w[k] * lz[k] for k in raw)
        e_max = npy(enc["e_crop"].max(1))
        e_glance = npy(enc["e_map"].flatten(1).mean(1))
        # one row per offered crop
        C = len(cands)
        nc, ec, rk = npy(n_crop), npy(enc["e_crop"]), rank.cpu().numpy()
        top = rk < self.k_top
        sh = np.where(top, nc, 0.0)
        sh = sh / np.where(sh.sum(1, keepdims=True) > 0, sh.sum(1, keepdims=True), 1.0)
        step_px = img.shape[1] // GRID
        k = np.arange(N_CROPS)
        self._last_crops = pd.DataFrame({"step": step, "tile_idx": np.repeat(cands, N_CROPS), "crop": np.tile(k, C),
                                         "x": np.tile((k % GRID) * step_px, C), "y": np.tile((k // GRID) * step_px, C),
                                         "e": ec.ravel(), "n": nc.ravel(), "rank": rk.ravel(), "share": sh.ravel()})
        return {"raw": raw, "z": z, "contrib": contrib, "I": I, "I_long": I_long, "n_v1": npy(n_v1), "n_v1_z": npy(z_v1),
                "e_max": e_max, "e_glance": e_glance, "n_crop": n_crop, "rank": rank, "enc": enc}

    def log_choice(self, j: int, sc: dict) -> dict:
        """Per-step fields for the chosen offer: components, z, weights, contributions, shares and lifts (contribution at the choice
        minus its mean over the offers; the lifts sum to I_chosen - mean I), surprise per eye, the v1 shadow, the top crop."""
        rec = {}
        for k, name in (("glance", "glance"), ("grid", "grid"), ("g", "prog"), ("e", "surp")):
            rec[f"n_{name}" if k in ("glance", "grid") else name] = sc["raw"][k][j]
            rec[f"z_{name}"] = sc["z"][k][j]
            rec[f"w_{name}"] = self.w[k]
            rec[f"c_{name}"] = sc["contrib"][k][j]
            rec[f"lift_{name}"] = sc["contrib"][k][j] - sc["contrib"][k].mean()
        tot = sum(abs(rec[f"c_{n}"]) for n in ("glance", "grid", "prog", "surp"))
        for n in ("glance", "grid", "prog", "surp"):
            rec[f"share_{n}"] = abs(rec[f"c_{n}"]) / tot if tot > 0 else np.nan
        enc = sc["enc"]
        rec.update(e_grid=sc["raw"]["e"][j], e_grid_max=sc["e_max"][j], e_glance=sc["e_glance"][j], n_v1=sc["n_v1"][j], n_v1_z=sc["n_v1_z"][j],
                   top_crop=int(torch.argmin(sc["rank"][j]).item()), I_mean=float(np.mean(sc["I"])))
        self.glance_err.append(enc["e_map"][j].cpu().numpy().astype(np.float16))
        self.crop_lat.append(enc["zg"][j].cpu().numpy().astype(np.float16))
        self.glance_lat.append(enc["zl"][j].cpu().numpy().astype(np.float16))
        cl = self._last_crops
        self.crop_log.append(cl.assign(chosen=cl.tile_idx.to_numpy() == cl.tile_idx.to_numpy()[j * N_CROPS]))
        return rec

    # -- training and memory -------------------------------------------------------------------------------------------------
    def _push(self, buf: torch.Tensor, n: int, ptr: int, x: torch.Tensor) -> tuple[int, int]:
        for p in x:
            buf[ptr] = p
            ptr = (ptr + 1) % len(buf)
            n = min(n + 1, len(buf))
        return n, ptr

    def train(self, step: int, img: torch.Tensor, n_crop: torch.Tensor, gen: torch.Generator, gen_replay: torch.Generator) -> dict:
        """img uint8 [1, H, W, 3] (the chosen tile); n_crop [16] its crop novelties at the choice."""
        H = img.shape[1]
        cp = H // GRID
        order = torch.sort(n_crop, descending=True, stable=True).indices[: self.k_top]
        pick = order[torch.arange(N_CROPS, device=self.dev) % len(order)]  # cycle the top-k crops to 16 training crops
        jy = torch.randint(-self.jitter, self.jitter + 1, (N_CROPS,), generator=gen, device=self.dev)
        jx = torch.randint(-self.jitter, self.jitter + 1, (N_CROPS,), generator=gen, device=self.dev)
        oy = ((pick // GRID) * cp + jy).clamp(0, H - cp)
        ox = ((pick % GRID) * cp + jx).clamp(0, H - cp)
        xt = S.patches(img, torch.zeros(1, dtype=torch.bool, device=self.dev), N_CROPS, cp, None, (oy[None], ox[None]))[0]
        xl = glances(img)
        batch, gbatch = xt, xl
        if self.buf_n > 0:
            ri = torch.randint(0, self.buf_n, (int(self.cfg["replay_batch"]),), generator=gen_replay, device=self.dev)
            batch = torch.cat([xt, self.buf[ri]])
        if self.gbuf_n > 0 and self.glance_replay > 0:
            gi = torch.randint(0, self.gbuf_n, (self.glance_replay,), generator=gen_replay, device=self.dev)
            gbatch = torch.cat([xl, self.gbuf[gi]])
        with torch.no_grad():
            eb, gb = float(((self.grid(xt) - xt) ** 2).mean()), float(((self.glance(xl) - xl) ** 2).mean())
        for model, opt, b in ((self.grid, self.opt_grid, batch), (self.glance, self.opt_glance, gbatch)):
            for _ in range(self.update_steps):
                loss = ((model(b) - b) ** 2).mean()
                opt.zero_grad(set_to_none=True)
                loss.backward()
                opt.step()
        with torch.no_grad():
            ea, ga = float(((self.grid(xt) - xt) ** 2).mean()), float(((self.glance(xl) - xl) ** 2).mean())
        self.buf_n, self.buf_ptr = self._push(self.buf, self.buf_n, self.buf_ptr, xt)
        self.gbuf_n, self.gbuf_ptr = self._push(self.gbuf, self.gbuf_n, self.gbuf_ptr, xl)
        pk, y, x = pick.cpu().numpy(), oy.cpu().numpy(), ox.cpu().numpy()
        self.train_log.extend({"step": step, "i": i, "crop": int(pk[i]), "y": int(y[i]), "x": int(x[i]), "dy": int(jy[i]), "dx": int(jx[i])} for i in range(N_CROPS))
        return {"err_before": eb, "err_after": ea, "err_glance_before": gb, "err_glance_after": ga}

    @torch.no_grad()
    def remember(self, t: int, img: torch.Tensor) -> None:
        """Every one of the 16 grid crops (seen), the glance and the shadow tile mean, encoded after training (v1's archive order)."""
        enc = self.encode(img)
        zg, zl = enc["zg"], enc["zl"]
        cat = lambda m, z: z if m is None else torch.cat([m, z])  # noqa: E731
        self.mem_crop, self.mem_glance, self.mem_v1 = cat(self.mem_crop, zg), cat(self.mem_glance, zl), cat(self.mem_v1, zg.mean(1))
        self.tiles.append(int(t))

    @torch.no_grad()
    def reembed(self, get) -> None:
        """Re-encode every memory with the current networks. get(ids) -> uint8 [n, H, W, 3] on the device."""
        zc, zl = [], []
        for i in range(0, len(self.tiles), 128):
            enc = self.encode(get(self.tiles[i : i + 128]))
            zc.append(enc["zg"])
            zl.append(enc["zl"])
        self.mem_crop, self.mem_glance = torch.cat(zc), torch.cat(zl)
        self.mem_v1 = self.mem_crop.mean(1)

    @torch.no_grad()
    def errors(self, img: torch.Tensor) -> tuple[np.ndarray, np.ndarray]:
        """Per tile: grid error (mean over the 16 crops) and glance error. For the held-out and forgetting sets."""
        enc = self.encode(img)
        return enc["e_crop"].mean(1).cpu().numpy(), enc["e_map"].flatten(1).mean(1).cpu().numpy()

    def state(self) -> dict:
        return {"model": self.grid.state_dict(), "glance": self.glance.state_dict()}

    def save_logs(self, out, store=None) -> None:
        crops = pd.concat(self.crop_log, ignore_index=True) if self.crop_log else pd.DataFrame()
        if store is not None and hasattr(store, "crop_quirks") and len(crops):
            q = store.crop_quirks(np.unique(crops.tile_idx))
            if len(q):
                crops = crops.merge(q, on=["tile_idx", "crop"], how="left")
        crops.to_parquet(out / "crops.parquet")
        pd.DataFrame(self.train_log).to_parquet(out / "train_crops.parquet")
        np.save(out / "glance_err.npy", np.stack(self.glance_err))
        np.save(out / "crop_latents.npy", np.stack(self.crop_lat))
        np.save(out / "glance_latents.npy", np.stack(self.glance_lat))
        np.savez(out / "memories.npz", crop=self.mem_crop.cpu().numpy().astype(np.float16), glance=self.mem_glance.cpu().numpy().astype(np.float16),
                 tile_idx=np.array(self.tiles))
