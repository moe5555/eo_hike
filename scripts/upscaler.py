"""A learned upscaler trained only on Landsat 1 (Moe, 2026-11-17: "after the last generation"; notes/upscaling.md).

The GAN tiles are a degraded copy of the archive tiles through a known chain: the 178 px window at 60 m -> 256 px bilinear (the walker's
view) -> 128 px BOX (~83 m, the package tiles). The pairs are made with exactly that chain from the walk cache (every tile any G1 walk was
shown, ~104,000; nothing filtered, fill and stripes stay): input = the 128 px package rendering, target = the 178 px rendering of the
same window (the one view, render(..., out_px=178)). The model learns how Landsat 1 MSS looks at 60 m, so its extra detail is the
instrument's own (scan lines, striping, 6-bit steps), not a later sensor's. 178 px is the ceiling: there is no Landsat 1 ground truth
beyond 60 m. Its outputs are a learned model's, labelled as such; the faithful enlargement stays integer nearest neighbour.

    .venv-sg python scripts/upscaler.py pairs            # CPU: runs/upscaler/pairs_{in,out}.npy (+ keys, split)
    scripts/sg.bat scripts/upscaler.py train             # GPU: runs/upscaler/model.pt (resumes from ckpt.pt)
    scripts/sg.bat scripts/upscaler.py eval              # held-out cells: L1 / PSNR against bilinear and bicubic -> notes/upscaler/eval.json
    scripts/sg.bat scripts/upscaler.py apply             # figures: held-out reals and GAN samples of every generation -> notes/upscaler/
    scripts/sg.bat scripts/upscaler.py all [--test]      # pairs (if missing), train, eval, apply
Split: 5 % of grid cells (by a hash of the cell index) are held out, so no held-out place is seen at any date in training.
Set by hand: the architecture (bilinear 128 -> 178, then a residual CNN of 10 convolutions, 64 channels), L1 loss, 100k iterations at
batch 32, Adam 2e-4 with cosine decay, seed 0. Emerged: the error against the baselines, and what the model draws.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "runs" / "upscaler"
NOTES = ROOT / "notes" / "upscaler"
IN_PX, OUT_PX, VIEW_PX = 128, 178, 256
HOLDOUT = 0.05


def log(m: str) -> None:
    print(f"[upscaler {time.strftime('%H:%M:%S')}] {m}", flush=True)


def held_out(cell: int) -> bool:
    return int(hashlib.sha256(str(cell).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF < HOLDOUT


# -- pairs --------------------------------------------------------------------------------------------------------------------------
def cmd_pairs(test: bool) -> None:
    from data.landsat1_store import CACHE, render

    out = OUT / ("test" if test else "")
    out.mkdir(parents=True, exist_ok=True)
    if (out / "pairs_done.json").exists():
        log("pairs exist; skipped")
        return
    files = sorted(p for p in CACHE.glob("*/*_s*.npz"))
    if test:
        files = files[:400]
    n = len(files)
    xi = np.lib.format.open_memmap(out / "pairs_in.npy", "w+", np.uint8, (n, IN_PX, IN_PX, 3))
    xo = np.lib.format.open_memmap(out / "pairs_out.npy", "w+", np.uint8, (n, OUT_PX, OUT_PX, 3))
    cells, ok = np.zeros(n, np.int64), np.zeros(n, bool)
    t0 = time.time()
    for i, f in enumerate(files):
        try:
            toa = np.load(f)["toa"]
        except Exception as e:  # an unreadable cache file is skipped and counted, never repaired
            log(f"unreadable {f.name}: {e}")
            continue
        xo[i] = render(toa, out_px=OUT_PX)
        xi[i] = np.asarray(Image.fromarray(render(toa, out_px=VIEW_PX)).resize((IN_PX, IN_PX), Image.Resampling.BOX))
        cells[i] = int(f.name.split("_")[0])
        ok[i] = True
        if i % 10000 == 0:
            log(f"{i}/{n} {time.time() - t0:.0f}s")
    xi.flush(), xo.flush()
    hold = np.array([held_out(c) for c in cells]) & ok
    np.savez(out / "pairs_meta.npz", cells=cells, ok=ok, holdout=hold, files=np.array([str(f.relative_to(CACHE)) for f in files]))
    info = {"n": int(n), "ok": int(ok.sum()), "unreadable": int((~ok).sum()), "holdout": int(hold.sum()), "train": int((ok & ~hold).sum()),
            "chain": "input: render(out_px=256) -> PIL BOX 128 (the package tiles); target: render(out_px=178), the one view at 60 m",
            "source": "the walk cache data/landsat1/cache (every tile any G1 walk was shown); nothing filtered", "seconds": round(time.time() - t0)}
    (out / "pairs_done.json").write_text(json.dumps(info, indent=1))
    log(f"pairs: {info}")


# -- model --------------------------------------------------------------------------------------------------------------------------
def make_model():
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    class Up(nn.Module):
        def __init__(self, ch: int = 64, depth: int = 10) -> None:
            super().__init__()
            layers = [nn.Conv2d(3, ch, 3, padding=1), nn.ReLU(inplace=True)]
            for _ in range(depth - 2):
                layers += [nn.Conv2d(ch, ch, 3, padding=1), nn.ReLU(inplace=True)]
            layers += [nn.Conv2d(ch, 3, 3, padding=1)]
            self.body = nn.Sequential(*layers)

        def forward(self, x):  # x in [0, 1], 128 px -> 178 px
            b = F.interpolate(x, size=(OUT_PX, OUT_PX), mode="bilinear", align_corners=False)
            return b + self.body(b)

    torch.manual_seed(0)
    return Up()


def load_pairs(test: bool):
    out = OUT / ("test" if test else "")
    xi = np.load(out / "pairs_in.npy", mmap_mode="r")
    xo = np.load(out / "pairs_out.npy", mmap_mode="r")
    m = np.load(out / "pairs_meta.npz")
    return xi, xo, m["ok"] & ~m["holdout"], m["ok"] & m["holdout"], out


def to_t(a, dev):
    import torch
    return torch.from_numpy(np.ascontiguousarray(a)).to(dev).permute(0, 3, 1, 2).float() / 255.0


def cmd_train(test: bool) -> None:
    import torch

    xi, xo, tr, _, out = load_pairs(test)
    idx = np.flatnonzero(tr)
    iters, bs = (200, 8) if test else (100_000, 32)
    dev = "cuda"
    model = make_model().to(dev)
    opt = torch.optim.Adam(model.parameters(), 2e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, iters)
    start = 0
    ck = out / "ckpt.pt"
    if (out / "model.pt").exists():
        log("model exists; skipped")
        return
    if ck.exists():
        s = torch.load(ck, map_location=dev)
        model.load_state_dict(s["model"]), opt.load_state_dict(s["opt"]), sched.load_state_dict(s["sched"])
        start = s["it"]
        log(f"resumed at {start}")
    rng = np.random.default_rng(1000 + start)
    t0, run = time.time(), 0.0
    for it in range(start, iters):
        b = np.sort(rng.choice(idx, bs, replace=False))
        x, y = to_t(xi[b], dev), to_t(xo[b], dev)
        loss = (model(x) - y).abs().mean()
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step(), sched.step()
        run = 0.98 * run + 0.02 * loss.item() if it > start else loss.item()
        if (it + 1) % (50 if test else 2000) == 0:
            log(f"it {it + 1}/{iters} L1 {run:.4f} {time.time() - t0:.0f}s")
        if (it + 1) % (100 if test else 5000) == 0 or it + 1 == iters:
            torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "sched": sched.state_dict(), "it": it + 1}, ck)
    torch.save(model.state_dict(), out / "model.pt")
    log("trained")


def cmd_eval(test: bool) -> None:
    import torch
    import torch.nn.functional as F

    xi, xo, _, ho, out = load_pairs(test)
    model = make_model().cuda()
    model.load_state_dict(torch.load(out / "model.pt", map_location="cuda"))
    model.eval()
    idx = np.flatnonzero(ho)
    acc = {k: [] for k in ("model", "bilinear", "bicubic")}
    with torch.no_grad():
        for s in range(0, len(idx), 64):
            b = idx[s:s + 64]
            x, y = to_t(xi[b], "cuda"), to_t(xo[b], "cuda")
            preds = {"model": model(x).clamp(0, 1),
                     "bilinear": F.interpolate(x, size=(OUT_PX, OUT_PX), mode="bilinear", align_corners=False),
                     "bicubic": F.interpolate(x, size=(OUT_PX, OUT_PX), mode="bicubic", align_corners=False).clamp(0, 1)}
            for k, p in preds.items():
                p8 = (p * 255).round() / 255  # scored as the 8-bit image that would be saved
                mse = ((p8 - y) ** 2).mean((1, 2, 3))
                acc[k].append(torch.stack([(p8 - y).abs().mean((1, 2, 3)) * 255, 10 * torch.log10(1 / mse.clamp_min(1e-10))], 1).cpu())
    res = {"n_holdout_tiles": int(len(idx)), "note": "held-out grid cells (5 %, by hash); 8-bit outputs; L1 in 0-255 units; PSNR in dB"}
    for k, v in acc.items():
        v = torch.cat(v).numpy()
        res[k] = {"L1": round(float(v[:, 0].mean()), 3), "PSNR_mean": round(float(v[:, 1].mean()), 3), "PSNR_median": round(float(np.median(v[:, 1])), 3)}
    dst = (out / "notes") if test else NOTES
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "eval.json").write_text(json.dumps(res, indent=1))
    log(f"eval: {res}")


def cmd_apply(test: bool) -> None:
    import torch
    import torch.nn.functional as F

    xi, xo, _, ho, out = load_pairs(test)
    dst = (out / "notes") if test else NOTES
    dst.mkdir(parents=True, exist_ok=True)
    model = make_model().cuda()
    model.load_state_dict(torch.load(out / "model.pt", map_location="cuda"))
    model.eval()

    def up(a: np.ndarray) -> np.ndarray:
        with torch.no_grad():
            return (model(to_t(a, "cuda")).clamp(0, 1) * 255).round().byte().permute(0, 2, 3, 1).cpu().numpy()

    def bicubic(a: np.ndarray) -> np.ndarray:
        return np.stack([np.asarray(Image.fromarray(t).resize((OUT_PX, OUT_PX), Image.Resampling.BICUBIC)) for t in a])

    def sheet(rows: list[list[np.ndarray]], path: Path) -> None:
        g = 4
        H = len(rows) * (OUT_PX + g) - g
        W = max(len(r) for r in rows) * (OUT_PX + g) - g
        im = Image.new("RGB", (W, H), (255, 255, 255))
        for r, row in enumerate(rows):
            for c, t in enumerate(row):
                im.paste(Image.fromarray(t), (c * (OUT_PX + g), r * (OUT_PX + g)))
        im.save(path)

    # held-out reals: input (nearest, centred at 178), bicubic, model, target
    idx = np.flatnonzero(ho)[:: max(1, len(np.flatnonzero(ho)) // 8)][:8]
    a_in = np.asarray(xi[np.sort(idx)])
    pad = [np.pad(t, (((OUT_PX - IN_PX) // 2, (OUT_PX - IN_PX + 1) // 2),) * 2 + ((0, 0),), constant_values=255) for t in a_in]
    rows = [[pad[i], b, m, np.asarray(t)] for i, (b, m, t) in enumerate(zip(bicubic(a_in), up(a_in), xo[np.sort(idx)]))]
    sheet(rows, dst / "heldout_input_bicubic_model_target.png")
    # GAN samples of every generation's last snapshot (seeds 0-7, psi 1): bicubic and model, side by side
    sys.path.insert(0, str(ROOT / "third_party" / "stylegan2-ada-pytorch"))
    import dnnlib
    import legacy

    dnnlib.util.set_cache_dir(str(ROOT / "runs" / "g1" / "dnnlib_cache"))
    made = []
    for gen in range(1, 10):
        for cond in ("curious", "null"):
            run = ROOT / "runs" / f"g{gen}" / "gan" / cond
            snaps = sorted(run.glob("network-snapshot-*.pkl")) if run.exists() else []
            if not snaps:
                continue
            with dnnlib.util.open_url(str(snaps[-1])) as f:
                G = legacy.load_network_pkl(f)["G_ema"].cuda().eval()
            z = torch.from_numpy(np.random.default_rng(0).standard_normal((8, G.z_dim))).float().cuda()
            with torch.no_grad():
                img = ((G(z, None, truncation_psi=1, noise_mode="const").clamp(-1, 1) + 1) * 127.5).round().byte().permute(0, 2, 3, 1).cpu().numpy()
            k = int(snaps[-1].stem.split("-")[-1])
            sheet([list(bicubic(img)), list(up(img))], dst / f"g{gen}_{cond}_{k}kimg_bicubic_vs_model.png")
            sd = out / "samples" / f"g{gen}_{cond}_{k}"
            sd.mkdir(parents=True, exist_ok=True)
            for i, t in enumerate(up(img)):
                im = Image.fromarray(t)
                from PIL import PngImagePlugin
                meta = PngImagePlugin.PngInfo()
                meta.add_text("upscale", "learned: scripts/upscaler.py (Landsat 1 pairs 128->178); NOT a faithful enlargement")
                im.save(sd / f"seed{i:02d}_178px_learned.png", pnginfo=meta)
            made.append(f"g{gen}_{cond}_{k}")
            del G
            torch.cuda.empty_cache()
    log(f"apply: held-out sheet + GAN sheets {made}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["pairs", "train", "eval", "apply", "all"])
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args()
    for c in (["pairs", "train", "eval", "apply"] if a.cmd == "all" else [a.cmd]):
        {"pairs": cmd_pairs, "train": cmd_train, "eval": cmd_eval, "apply": cmd_apply}[c](a.test)


if __name__ == "__main__":
    main()
