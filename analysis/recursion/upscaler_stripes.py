"""Does the Landsat 1 upscaler add scan-line texture where a sample already has some? (prediction 173, second part; 2026-11-24)

For held-out real tiles (the upscaler's own split) and for GAN samples of every generation (seeds 0-599, psi 1, the saved 128 px
samples): upscale 128 -> 178 px with the learned model and with bicubic, and compute chroma_y (analysis/recursion/chroma_stripes.py;
post hoc since G3) on both. Report model / bicubic per set, and per tercile of the input's own chroma_y (low / mid / high stripes).
For the held-out reals the 178 px target exists, so target / bicubic shows what "the instrument's own" texture would add.
Colour and texture statistics of rendered images, labelled as such. Outputs are a learned model's (notes/upscaling.md).

    scripts/sg.bat analysis/recursion/upscaler_stripes.py   ->  notes/upscaler/stripes_model_vs_bicubic.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import upscaler as U  # noqa: E402

N = 600


def chroma_y(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    luma = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    return np.abs(np.diff(a - luma[..., None], axis=1)).mean((1, 2, 3))


def main() -> None:
    import torch

    model = U.make_model().cuda()
    model.load_state_dict(torch.load(U.OUT / "model.pt", map_location="cuda"))
    model.eval()

    def up(a):
        out = []
        for i in range(0, len(a), 64):
            with torch.no_grad():
                out.append((model(U.to_t(a[i:i + 64], "cuda")).clamp(0, 1) * 255).round().byte().permute(0, 2, 3, 1).cpu().numpy())
        return np.concatenate(out)

    def bic(a):
        return np.stack([np.asarray(Image.fromarray(t).resize((U.OUT_PX, U.OUT_PX), Image.Resampling.BICUBIC)) for t in a])

    sets = []
    xi, xo, _, ho, _ = U.load_pairs(False)
    hidx = np.sort(np.random.default_rng(0).choice(np.flatnonzero(ho), N, replace=False))
    sets.append(("held-out reals", np.asarray(xi[hidx]), np.asarray(xo[hidx])))
    for g in range(1, 20):
        for cond in ("curious", "null"):
            sd = ROOT / "runs" / f"g{g}" / "gan" / cond / "samples"
            if sd.exists() and (sd / f"seed{N - 1:05d}.png").exists():
                sets.append((f"G{g}-{cond} samples", np.stack([np.asarray(Image.open(sd / f"seed{s:05d}.png").convert("RGB")) for s in range(N)]), None))
    rows = []
    for name, a, tgt in sets:
        c_in, c_b, c_m = chroma_y(a), chroma_y(bic(a)), chroma_y(up(a))
        q = np.quantile(c_in, [1 / 3, 2 / 3])
        r = {"set": name, "n": len(a), "in_128": c_in.mean(), "bicubic_178": c_b.mean(), "model_178": c_m.mean(), "model_over_bicubic": c_m.mean() / c_b.mean()}
        for lab, mask in (("low", c_in <= q[0]), ("mid", (c_in > q[0]) & (c_in <= q[1])), ("high", c_in > q[1])):
            r[f"model_over_bicubic_{lab}"] = c_m[mask].mean() / c_b[mask].mean()
            r[f"added_{lab}"] = (c_m[mask] - c_b[mask]).mean()
        if tgt is not None:
            r["target_178"] = chroma_y(tgt).mean()
            r["target_over_bicubic"] = r["target_178"] / c_b.mean()
        rows.append(r)
        print(name, flush=True)
    df = pd.DataFrame(rows)
    (ROOT / "notes" / "upscaler").mkdir(parents=True, exist_ok=True)
    df.to_csv(ROOT / "notes" / "upscaler" / "stripes_model_vs_bicubic.csv", index=False, float_format="%.4f")
    print(df.to_string(index=False, float_format=lambda v: f"{v:.3f}"))


if __name__ == "__main__":
    sys.exit(main())
