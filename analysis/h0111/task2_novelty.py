"""Task 2: what novelty is measured against, and what the logs show of it. Reads the two Paris walks; changes nothing.

    python analysis/h0111/task2_novelty.py

Raw novelty (n) and its rescaled form (n_z) per 1,000 steps, for the options on offer and for the chosen tiles, and how
much of raw novelty comes from a tile's own earlier visits (one archive copy counts for a tenth of k_nn = 10).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from common import OUT, RUNS, candidates, steps

R = {"Bored": "h2910_bored_paris_s0", "Globalist": "h2910_globalist_paris_s0"}


def main() -> None:
    rows = []
    for ch, run in R.items():
        c = candidates(run)
        s = steps(run)
        arch = np.load(RUNS / run / "archive.npz")
        print(ch, "archive entries", len(arch["z"]), "unique tiles in it", len(np.unique(arch["tile_idx"])), "latent size", arch["z"].shape[1])
        for b in range(0, 5000, 1000):
            d = c[(c.step >= b) & (c.step < b + 1000) & (c.kind == "neighbour") & (c.step >= 50)]
            x = s[(s.step >= b) & (s.step < b + 1000) & (s.step >= 50)]
            rows.append({"walker": ch, "steps": f"{b}-{b + 999}", "archive_end": b + 1000, "offered_n": d.n.mean(), "offered_n_z": d.n_z.mean(), "offered_n_sd": d.n.std(), "chosen_n": x.n.mean(), "chosen_n_z": x.n_z.mean(), "chosen_I": x.I.mean(),
                         "offered_g": d.g.mean(), "offered_g_z": d.g_z.mean(), "offered_e": d.e.mean(), "offered_e_z": d.e_z.mean(), "max_I_below_0": (x.max_I < 0).mean()})
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "task2_novelty_blocks.csv", index=False)
    print(t.round(4).to_string(index=False))
    for ch, d in t.groupby("walker"):
        print(ch, f"offered raw novelty, last block / first block: {d.offered_n.iloc[-1] / d.offered_n.iloc[0]:.2f}; rescaled change {d.offered_n_z.iloc[-1] - d.offered_n_z.iloc[0]:+.3f}")


def fixed_network() -> None:
    """Raw novelty moves with the encoder, so hold it still: the final network's novelty of the 200 held-out tiles against the
    first m archive entries (latents re-embedded by that same network at the end of the walk)."""
    import torch
    import yaml

    from agent import signals as S
    from agent.model import ConvAE
    from agent.walk import HELDOUT_N, HELDOUT_SEED
    from data.tile_store import TileStore

    store = TileStore()
    held = np.sort(np.random.default_rng(HELDOUT_SEED).choice(np.arange(store.N), HELDOUT_N, replace=False)).tolist()
    arrs, _, _ = store.get_many(held, timeout=600.0)
    kept = [i for i in held if i in arrs]
    rows = []
    for ch, run in R.items():
        cfg = yaml.safe_load((RUNS / run / "config.yaml").read_text())
        model = ConvAE()
        model.load_state_dict(torch.load(RUNS / run / "final.pt", weights_only=False)["model"])
        model.eval()
        img = torch.from_numpy(np.stack([arrs[i] for i in kept]))
        x = S.patches(img, torch.zeros(len(kept), dtype=torch.bool), int(cfg["K"]), int(cfg["crop_px"]), torch.Generator(), S.fixed_offsets(kept, int(cfg["K"]), img.shape[1], int(cfg["crop_px"]), "cpu"))
        z = S.mean_latent(model, x)
        arch = torch.from_numpy(np.load(RUNS / run / "archive.npz")["z"])
        for m in (50, 100, 250, 500, 1000, 2000, 3000, 4000, 5000):
            rows.append({"walker": ch, "archive_entries": m, "heldout_novelty": float(S.novelty(z, arch[:m], int(cfg["k_nn"]), unit=True).mean())})
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "task2_novelty_fixed_network.csv", index=False)
    print(t.pivot(index="archive_entries", columns="walker", values="heldout_novelty").round(4).to_string())


def as_lived() -> None:
    """The same probe as the walker would have felt it: at each 250-step checkpoint, that step's network, novelty of the 200 held-out
    tiles against the archive so far, re-embedded by that network. Also the probe's spread, since novelty is a distance in a space that moves."""
    import torch
    import yaml

    from agent import signals as S
    from agent.model import ConvAE
    from agent.walk import HELDOUT_N, HELDOUT_SEED
    from data.tile_store import TileStore

    store = TileStore()
    held = np.sort(np.random.default_rng(HELDOUT_SEED).choice(np.arange(store.N), HELDOUT_N, replace=False)).tolist()

    def view(ids: list[int], cfg: dict) -> torch.Tensor:
        img = torch.from_numpy(np.stack([store.get_lowres(i) for i in ids]))
        return S.patches(img, torch.zeros(len(ids), dtype=torch.bool), int(cfg["K"]), int(cfg["crop_px"]), torch.Generator(), S.fixed_offsets(ids, int(cfg["K"]), img.shape[1], int(cfg["crop_px"]), "cpu"))

    rows = []
    for ch, run in R.items():
        cfg = yaml.safe_load((RUNS / run / "config.yaml").read_text())
        t = steps(run).tile_idx.to_numpy()
        px = view(held, cfg)
        uniq = np.unique(t).tolist()
        pos = {u: k for k, u in enumerate(uniq)}
        xs = torch.cat([view(uniq[i : i + 256], cfg) for i in range(0, len(uniq), 256)])
        for cp in sorted((RUNS / run).glob("ckpt_*.pt")):
            m = int(cp.stem.split("_")[1])
            model = ConvAE()
            model.load_state_dict(torch.load(cp, weights_only=False)["model"])
            model.eval()
            zu = torch.cat([S.mean_latent(model, xs[i : i + 256]) for i in range(0, len(xs), 256)])
            arch = zu[torch.as_tensor([pos[int(u)] for u in t[:m]])]
            z = S.mean_latent(model, px)
            pair = torch.cdist(torch.nn.functional.normalize(arch, dim=1), torch.nn.functional.normalize(arch, dim=1))
            rows.append({"walker": ch, "step": m, "heldout_novelty": float(S.novelty(z, arch, int(cfg["k_nn"]), unit=True).mean()), "archive_spread": float(pair.mean()), "ratio": float(S.novelty(z, arch, int(cfg["k_nn"]), unit=True).mean() / pair.mean())})
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "task2_novelty_as_lived.csv", index=False)
    print(t.pivot(index="step", columns="walker", values=["heldout_novelty", "archive_spread"]).iloc[::2].round(4).to_string())


if __name__ == "__main__":
    main()
    fixed_network()
    as_lived()
