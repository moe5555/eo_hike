"""GAN generation one (notes/brief_gan_g1.md): two StyleGAN2-ADA models on the PC, G1-curious (weighted) against G1-null (unweighted).

Run with .venv-sg (torch 2.14 + cu130, the StyleGAN env); the stages that compile or use CUDA ops go through scripts/sg.bat (MSVC):

    python gen/g1_gan.py datasets            # verify the packages (don't repair), weights + tau + ESS, dataset_tool zips, metadata, contact sheets
    scripts\\sg.bat gen/g1_gan.py throughput  # both runs concurrently for 28 kimg (8 warm-up + 20 measured): sec/kimg, custom ops status
    python gen/g1_gan.py budget              # kimg from the measured rates (datasets + training + readouts <= 60 h); expectations.md, STATE.md, tag g1-start
    scripts\\sg.bat gen/g1_gan.py train curious | null    # resumable: continues from the latest snapshot pair (pickle + training state)
    scripts\\sg.bat gen/g1_gan.py fid         # fid50k_full on the kept snapshots of each run (a training-health signal only)
    scripts\\sg.bat gen/g1_gan.py readouts    # samples, memorisation, diversity, colour and texture statistics, film assets
    ... --test                               # the same on the TEST packages (runs/g1/test/), never trained on for real

Set by hand here (every finding names them): N (the packages), q (the walks), the ESS target 0.5 N, the weight mapping exp(I / tau) with
the start tile at the package's median, the kimg budget (from the measured rate), StyleGAN2-ADA cfg auto at 128 px (the repo's
recommendation for the resolution), ADA target 0.6, augpipe bgc, mirror off, seed 0 for both runs, snapshots every 40 kimg.
"""

from __future__ import annotations

import argparse
import copy
import io
import json
import math
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SG = ROOT / "third_party" / "stylegan2-ada-pytorch"
SG_COMMIT = "d72cc7d"
CONDS = ("curious", "null")
SEED = 0
SNAP_TICKS = 10           # kimg_per_tick 4 -> a snapshot every 40 kimg
KIMG_STEP = 160           # the budget is a multiple of 160, so 1/4, 1/2, 3/4 and the end fall on snapshots
GRID_SEED = 20261113      # the fixed latents of the 8 x 8 fakes grids (both runs)
ESS_TARGET = 0.5
BUDGET_H = 60.0
N_SAMPLES = 5000
SAMPLE_SEEDS = range(N_SAMPLES)
PX_OBS = 32               # the observer of memorisation and diversity: downsampled pixel space, 32 x 32 x 3, L2 (no pretrained network)
PR_K = 3


class Paths:
    def __init__(self, test: bool) -> None:
        self.test = test
        base = ROOT / "runs" / "g1" / ("test" if test else "")
        self.pkg = (base / "paths") if test else ROOT / "paths" / "g1"
        self.gan = base / "gan"
        self.ds = self.gan / "datasets"
        self.notes = (base / "notes_gan") if test else ROOT / "notes" / "gen1" / "gan"
        self.cache = ROOT / "runs" / "g1" / "dnnlib_cache"  # Inception and the reals' statistics; filled in Phase A (no network in Phase B)

    def run(self, cond: str) -> Path:
        return self.gan / cond


def sg_imports():
    sys.path.insert(0, str(SG))
    import dnnlib  # noqa: F401
    dnnlib.util.set_cache_dir(str(Paths(False).cache))
    return dnnlib


def log(msg: str) -> None:
    print(f"[g1_gan {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def wjson(p: Path, d) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(d, indent=1, default=str))
    os.replace(tmp, p)


# -- weights ---------------------------------------------------------------------------------------------------------------------
def log_median_exp(a: np.ndarray) -> float:
    """log(median(exp(a))) without overflow (the even case averages the two middle values, as np.median)."""
    s = np.sort(a)
    n = len(s)
    if n % 2:
        return float(s[n // 2])
    return float(np.logaddexp(s[n // 2 - 1], s[n // 2]) - math.log(2))


def tile_weights(enc: pd.DataFrame, tau: float) -> pd.Series:
    """notes/brief_gan_g1.md: each encounter e = exp(I / tau); a walk's start tile (no interest) gets the package's median e; a tile sums
    its encounters; normalised to mean 1. Computed in logs."""
    a = (enc.I / tau).to_numpy(np.float64, copy=True)
    start = enc.step.to_numpy() == -1
    a[start] = log_median_exp(a[~start])
    lw = pd.Series(a, index=enc.image_key.to_numpy()).groupby(level=0).apply(lambda v: float(np.logaddexp.reduce(v.to_numpy())))
    w = np.exp(lw - lw.max())
    return w / w.mean()


def ess(w: np.ndarray) -> float:
    w = np.asarray(w, np.float64)
    return float(w.sum() ** 2 / (w ** 2).sum())


def solve_tau(enc: pd.DataFrame, n: int) -> dict:
    counts = enc.image_key.value_counts().to_numpy(np.float64)
    limit = ess(counts)
    target = ESS_TARGET * n
    out = {"N": n, "ess_target": target, "ess_target_share": ESS_TARGET, "ess_limit_counts": limit, "ess_limit_share": limit / n,
           "encounters": len(enc), "start_encounters": int((enc.step == -1).sum()),
           "note": "as tau -> infinity the weights become the encounter counts: ESS limit = (sum c)^2 / sum c^2"}
    if limit < target:
        out.update(reachable=False)
        return out
    lo, hi = math.log(1e-3), math.log(1e4)
    if ess(tile_weights(enc, math.exp(hi)).to_numpy()) < target:
        out.update(reachable=False, note=out["note"] + "; not reached at tau = 1e4")
        return out
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if ess(tile_weights(enc, math.exp(mid)).to_numpy()) < target:
            lo = mid
        else:
            hi = mid
    tau = math.exp(hi)
    w = tile_weights(enc, tau)
    ws = np.sort(w.to_numpy())[::-1]
    out.update(reachable=True, tau=tau, ess=ess(ws), ess_share=ess(ws) / n, max_over_median=float(ws[0] / np.median(ws)),
               max_weight=float(ws[0]), median_weight=float(np.median(ws)), min_weight=float(ws[-1]),
               top1_share=float(ws[: max(1, n // 100)].sum() / ws.sum()), top10_share=float(ws[: max(1, n // 10)].sum() / ws.sum()))
    return out


# -- datasets --------------------------------------------------------------------------------------------------------------------
def sheet(paths: list[Path], dst: Path, cols: int = 8) -> None:
    ims = [Image.open(p).convert("RGB") for p in paths]
    if not ims:
        return
    s = ims[0].size[0]
    rows = math.ceil(len(ims) / cols)
    out = Image.new("RGB", (cols * s, rows * s))
    for i, im in enumerate(ims):
        out.paste(im, ((i % cols) * s, (i // cols) * s))
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst)


def zip_order(src: Path) -> list[Path]:
    """dataset_tool.py's open_image_folder order (stylegan2-ada-pytorch d72cc7d): sorted(Path(src).rglob('*')), image files only."""
    return [f for f in sorted(Path(src).rglob("*")) if f.suffix.lower() in (".png", ".jpg", ".jpeg") and f.is_file()]


def cmd_datasets(P: Paths) -> None:
    t0 = time.time()
    sys.path.insert(0, str(ROOT / "scripts"))
    import g1_verify

    n_expect = 10_000 if not P.test else json.loads((P.pkg / "curious" / "manifest.json").read_text())["N"]
    ver = {c: g1_verify.check(P.pkg / c, n_expect) for c in CONDS}
    wjson(P.ds / "verify_input.json", ver)
    if not all(v["passed"] for v in ver.values()):
        log(f"the packages fail verification as GAN input: {[(c, v['problems']) for c, v in ver.items()]}; stop (never repaired here)")
        sys.exit(2)
    info = {"sg_commit": SG_COMMIT, "verify": {c: ver[c]["passed"] for c in CONDS}}
    for cond in CONDS:
        pkg = P.pkg / cond
        t = pd.read_parquet(pkg / "tiles.parquet")
        e = pd.read_parquet(pkg / "encounters.parquet")
        n = len(t)
        if cond == "curious":
            sol = solve_tau(e, n)
            wjson(P.gan / "ess.json", sol)
            info["ess"] = sol
            if not sol["reachable"]:
                log(f"ESS = {ESS_TARGET} N can't be reached: the limit with encounter counts alone is {sol['ess_limit_counts']:.0f} "
                    f"({sol['ess_limit_share']:.3f} N). Neither GAN is trained (brief; run instruction).")
                sys.exit(3)
            w = tile_weights(e, sol["tau"])
        else:
            w = pd.Series(1.0, index=t.image_key.to_numpy())  # duplicate encounters add no weight
            info["null_ess"] = float(n)
        t["weight"] = t.image_key.map(w).astype(float)
        assert t.weight.notna().all() and abs(t.weight.mean() - 1) < 1e-9
        # the dataset: the package's renders as they are, through dataset_tool.py (unconditional)
        src = P.ds / f"{cond}_src"
        if src.exists():
            shutil.rmtree(src)
        src.mkdir(parents=True)
        for name in t.tile:
            shutil.copyfile(pkg / "tiles" / f"{name}.png", src / f"{name}.png")
        order = zip_order(src)
        arch = {f.stem: f"{i:08d}"[:5] + f"/img{i:08d}.png" for i, f in enumerate(order)}
        z = P.ds / f"{cond}.zip"
        z.unlink(missing_ok=True)
        t1 = time.time()
        r = subprocess.run([sys.executable, str(SG / "dataset_tool.py"), f"--source={src}", f"--dest={z}"], cwd=SG, capture_output=True, text=True)
        if r.returncode:
            log(f"dataset_tool failed: {r.stdout[-800:]} {r.stderr[-800:]}")
            sys.exit(1)
        t["arch_fname"] = t.tile.map(arch)
        # every image of the zip against its source, pixel for pixel: the weights are mapped by name, so the order must be right
        with zipfile.ZipFile(z) as zf:
            names = sorted(x for x in zf.namelist() if x.endswith(".png"))
            assert len(names) == n and set(names) == set(t.arch_fname), "the zip's names are not the expected order"
            for name, fn in zip(t.tile, t.arch_fname):
                a = np.asarray(Image.open(io.BytesIO(zf.read(fn))).convert("RGB"))
                b = np.asarray(Image.open(src / f"{name}.png").convert("RGB"))
                assert np.array_equal(a, b), f"zip image {fn} is not {name}"
        wjson(P.ds / f"{cond}_weights.json", dict(zip(t.arch_fname, t.weight)))
        # metadata, one row per unique tile: order lives here (a GAN shuffles its data)
        g = e.groupby("image_key")
        meta = t.copy()
        meta["walk_ids"] = meta.image_key.map(g.walk_id.apply(lambda v: ",".join(sorted(set(v)))))
        meta["steps"] = meta.image_key.map(g.step.apply(lambda v: ",".join(map(str, v))))
        for col in ("z_glance", "z_grid", "z_prog", "I"):
            meta[f"{col}_encounters"] = meta.image_key.map(g[col].apply(lambda v: ",".join("" if pd.isna(x) else f"{x:.4f}" for x in v)))
        meta.to_parquet(P.ds / f"{cond}_metadata.parquet")
        # sanity sheets
        rng = np.random.default_rng(SEED)
        pick = t.tile.to_numpy()[np.sort(rng.choice(n, min(64, n), replace=False))]
        sheet([pkg / "tiles" / f"{x}.png" for x in pick], P.ds / f"{cond}_random64.png")
        if cond == "curious":
            o = t.sort_values("weight", ascending=False)
            sheet([pkg / "tiles" / f"{x}.png" for x in o.tile.head(64)], P.ds / "curious_heaviest64.png")
            sheet([pkg / "tiles" / f"{x}.png" for x in o.tile.tail(64)], P.ds / "curious_lightest64.png")
        shutil.rmtree(src)
        info[cond] = {"n": n, "zip": str(z), "zip_mb": round(z.stat().st_size / 1e6, 1), "dataset_tool_s": round(time.time() - t1, 1),
                      "weight_max": float(t.weight.max()), "weight_min": float(t.weight.min())}
        log(f"{cond}: {n:,} tiles -> {z} ({info[cond]['zip_mb']} MB); weights mean 1, max {t.weight.max():.2f}")
    info["seconds"] = round(time.time() - t0, 1)
    wjson(P.ds / "datasets.json", info)
    if "ess" in info:
        s = info["ess"]
        log(f"tau {s['tau']:.3f}, ESS {s['ess']:.0f} ({s['ess_share']:.3f} N), limit {s['ess_limit_share']:.3f} N, top 1 % {s['top1_share']:.3f}, "
            f"top 10 % {s['top10_share']:.3f}, max/median {s['max_over_median']:.1f}")
    log(f"datasets built in {info['seconds']:.0f} s")


# -- training --------------------------------------------------------------------------------------------------------------------
def latest_pair(run: Path) -> tuple[Path, Path] | None:
    ks = sorted(int(p.stem.split("-")[-1]) for p in run.glob("network-snapshot-*.pkl"))
    for k in reversed(ks):
        pk, st = run / f"network-snapshot-{k:06d}.pkl", run / f"training-state-{k:06d}.pt"
        if st.exists():
            return pk, st
    return None


def stats_tail(run: Path, n: int = 5) -> dict:
    f = run / "stats.jsonl"
    if not f.exists():
        return {}
    L = [json.loads(x) for x in f.read_text().splitlines()[-n:] if x.strip()]
    if not L:
        return {}
    v = lambda k: [x[k]["mean"] for x in L if k in x]  # noqa: E731
    spk = v("Timing/sec_per_kimg")
    return {"kimg": round(v("Progress/kimg")[-1], 1), "sec_per_kimg": round(float(np.median(spk)), 2) if spk else None,
            "augment_p": round(v("Progress/augment")[-1], 4) if v("Progress/augment") else None,
            "loss_G": round(v("Loss/G/loss")[-1], 4) if v("Loss/G/loss") else None, "loss_D": round(v("Loss/D/loss")[-1], 4) if v("Loss/D/loss") else None}


def merge_status(P: Paths) -> None:
    runs = {}
    for c in CONDS:
        f = P.run(c) / "run_status.json"
        if f.exists():
            try:
                runs[c] = json.loads(f.read_text())
            except json.JSONDecodeError:
                pass
    fj = P.gan / "fid.json"
    if fj.exists():
        try:
            for c, d in json.loads(fj.read_text()).items():
                if c in runs and d:
                    runs[c]["fid"] = ", ".join(f"{k}: {v:.1f}" for k, v in sorted(d.items(), key=lambda x: int(x[0])))
        except (json.JSONDecodeError, ValueError, AttributeError):
            pass
    wjson(P.gan / "status.json", {"runs": runs, "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                                  "note": "FID (fid50k_full against each run's own training set) is a training-health signal only, computed after training on the kept snapshots."})


def keep_set(total: int) -> set[int]:
    return {total // 4, total // 2, 3 * total // 4, total}


def train(cond: str, P: Paths, total_kimg: int, run: Path | None = None, snap_ticks: int = SNAP_TICKS, stop_after_kimg: float | None = None,
          weights: bool = True, tag: str = "") -> str:
    """One StyleGAN2-ADA run; resumes from the latest snapshot pair in run/. Returns 'finished' | 'stopped' | 'aborted'."""
    import torch

    dnnlib = sg_imports()
    import train as sgtrain
    from torch_utils import custom_ops, training_stats
    from training import training_loop

    run = run or P.run(cond)
    run.mkdir(parents=True, exist_ok=True)
    z = P.ds / f"{cond}.zip"
    desc, args = sgtrain.setup_training_loop_kwargs(gpus=1, snap=snap_ticks, metrics=[], seed=SEED, data=str(z), cond=False, mirror=False,
                                                    cfg="auto", kimg=int(total_kimg), aug="ada", augpipe="bgc")
    args.image_snapshot_ticks = None  # the 8 x 8 grid at fixed latents is written by the snapshot callback instead
    args.run_dir = str(run)
    args.sample_weights = str(P.ds / f"{cond}_weights.json") if weights else None
    pair = latest_pair(run)
    if pair:
        args.resume_pkl, args.resume_state = str(pair[0]), str(pair[1])  # set here, not via --resume (that is transfer learning: it changes ADA and EMA)
    stop = run / "STOP"
    t_start = time.time()
    args.abort_fn = lambda: stop.exists() or (stop_after_kimg is not None and _cur["kimg"] >= stop_after_kimg)
    keep = keep_set(int(total_kimg))
    grid_z = np.random.RandomState(GRID_SEED).randn(64, 512).astype(np.float32)

    def on_snapshot(info: dict) -> None:
        k = info["cur_nimg"] // 1000
        _cur["kimg"] = k
        G = info["G_ema"].to("cuda")
        with torch.no_grad():
            imgs = torch.cat([G(torch.from_numpy(grid_z[i : i + 16]).cuda(), None, truncation_psi=1, noise_mode="const") for i in range(0, 64, 16)])
        G.cpu()
        a = (imgs.permute(0, 2, 3, 1) * 127.5 + 128).clamp(0, 255).to(torch.uint8).cpu().numpy()
        s = a.shape[1]
        grid = a.reshape(8, 8, s, s, 3).transpose(0, 2, 1, 3, 4).reshape(8 * s, 8 * s, 3)
        Image.fromarray(grid).save(run / f"fakes8x8_{k:06d}.png")
        shutil.copyfile(run / f"fakes8x8_{k:06d}.png", run / "latest_fakes.png")
        # retention: the last two snapshots (for resume) and 1/4, 1/2, 3/4 and the end of the budget; the rest deleted as we go
        ks = sorted(int(p.stem.split("-")[-1]) for p in run.glob("network-snapshot-*.pkl"))
        for old in ks[:-2]:
            if old not in keep:
                for f in (run / f"network-snapshot-{old:06d}.pkl", run / f"training-state-{old:06d}.pt"):
                    f.unlink(missing_ok=True)
        st = stats_tail(run)
        spk = st.get("sec_per_kimg")
        left = max(int(total_kimg) - k, 0)
        wjson(run / "run_status.json", {**st, "kimg": k, "target": int(total_kimg), "snapshot": f"network-snapshot-{k:06d}.pkl",
                                        "eta": f"{left * spk / 3600:.1f} h" if spk else "?", "augment_p": round(info["augment_p"], 4),
                                        "time": time.strftime("%Y-%m-%d %H:%M:%S"), "tag": tag})
        merge_status(P)

    _cur = {"kimg": (int(torch.load(pair[1], weights_only=False)["cur_nimg"]) // 1000) if pair else 0}
    args.snapshot_fn = on_snapshot
    dnnlib.util.Logger(file_name=str(run / "log.txt"), file_mode="a", should_flush=True)
    print(f"=== {time.strftime('%Y-%m-%d %H:%M:%S')} {cond}: {desc}, total {total_kimg} kimg, "
          + (f"resume from {pair[0].name}" if pair else "fresh") + f"; weights {'on' if weights else 'off'}")
    wjson(run / "training_options.json", {k: (str(v) if callable(v) else v) for k, v in args.items()})
    training_stats.init_multiprocessing(rank=0, sync_device=None)
    custom_ops.verbosity = "brief"
    training_loop.training_loop(rank=0, **args)
    last = latest_pair(run)
    k = int(last[0].stem.split("-")[-1]) if last else 0
    if k >= int(total_kimg):
        (run / "FINISHED").write_text(time.strftime("%Y-%m-%d %H:%M:%S"))
        return "finished"
    if stop.exists():
        (run / "STOPPED_DISK").write_text(time.strftime("%Y-%m-%d %H:%M:%S"))
        return "stopped"
    return "aborted"


def cmd_train(cond: str, P: Paths) -> None:
    b = json.loads((P.gan / "budget.json").read_text())
    r = train(cond, P, int(b["kimg"]))
    log(f"{cond}: {r}")
    sys.exit(0 if r in ("finished", "stopped") else 1)


def cmd_throughput(P: Paths, kimg: int = 28, warm: int = 8) -> None:
    """Both runs concurrently, as the real runs will go, from fresh networks for `kimg`; sec/kimg over the ticks after `warm` kimg."""
    out = P.gan / "throughput"
    if out.exists():
        shutil.rmtree(out)
    procs = {}
    for c in CONDS:
        (out / c).mkdir(parents=True)
        procs[c] = subprocess.Popen([sys.executable, __file__, "_train_into", c, str(out / c), str(kimg)] + (["--test"] if P.test else []),
                                    cwd=ROOT, stdout=open(out / f"{c}.log", "w"), stderr=subprocess.STDOUT)
    t0 = time.time()
    rc = {c: p.wait() for c, p in procs.items()}
    res = {"kimg": kimg, "warm_kimg": warm, "wall_s": round(time.time() - t0, 1), "rc": rc, "runs": {}}
    for c in CONDS:
        L = [json.loads(x) for x in (out / c / "stats.jsonl").read_text().splitlines() if x.strip()] if (out / c / "stats.jsonl").exists() else []
        spk = [x["Timing/sec_per_kimg"]["mean"] for x in L if x["Progress/kimg"]["mean"] > warm]
        logtxt = (out / c / "log.txt").read_text(errors="replace") if (out / c / "log.txt").exists() else ""
        ops = {name: ("ok" if f'Setting up PyTorch plugin "{name}"... Done.' in logtxt else "FAILED (slow reference ops)")
               for name in ("bias_act_plugin", "upfirdn2d_plugin")}
        res["runs"][c] = {"sec_per_kimg": float(np.mean(spk)) if spk else None, "ticks_measured": len(spk), "custom_ops": ops,
                          "peak_gpu_mem_gb": max((x.get("Resources/peak_gpu_mem_gb", {}).get("mean", 0) for x in L), default=None),
                          "fallback_warnings": [w for w in ("conv2d_gradfix not supported", "grid_sample_gradfix not supported", "Falling back") if w in logtxt]}
    res["sec_per_kimg_concurrent"] = max((r["sec_per_kimg"] or float("inf")) for r in res["runs"].values())
    wjson(P.gan / "throughput.json", res)
    log(f"throughput: {res}")
    shutil.rmtree(out, ignore_errors=True) if all(v == 0 for v in rc.values()) and not P.test else None
    sys.exit(0 if all(v == 0 for v in rc.values()) and math.isfinite(res["sec_per_kimg_concurrent"]) else 1)


def cmd_budget(P: Paths) -> None:
    thr = json.loads((P.gan / "throughput.json").read_text())
    ds = json.loads((P.ds / "datasets.json").read_text())
    rt = ROOT / "runs" / "g1" / "phase_a" / "readout_timing.json"  # measured in Phase A on the TEST snapshots (gen/g1_tests.py readouts)
    readout_est_h = json.loads(rt.read_text())["projected_h"] if rt.exists() else 3.0
    readout_h = max(2.0, 1.5 * readout_est_h)
    ds_h = ds["seconds"] / 3600
    spk = thr["sec_per_kimg_concurrent"] * 1.03  # 3 % for snapshots, the fakes grids and maintenance between ticks
    train_h = BUDGET_H - ds_h - readout_h
    kimg = int(train_h * 3600 / spk // KIMG_STEP * KIMG_STEP)
    b = {"kimg": kimg, "budget_h": BUDGET_H, "datasets_h": round(ds_h, 2), "readouts_h_allowed": round(readout_h, 2), "readouts_h_estimated": readout_est_h,
         "training_h": round(kimg * spk / 3600, 2), "sec_per_kimg_concurrent": thr["sec_per_kimg_concurrent"], "sec_per_kimg_with_margin": round(spk, 3),
         "runs": thr["runs"], "under_2000_kimg": kimg < 2000, "kept_snapshots": sorted(keep_set(kimg)), "snapshot_every_kimg": 4 * SNAP_TICKS,
         "computed": time.strftime("%Y-%m-%d %H:%M:%S")}
    if kimg < 2000:
        b["limitation"] = (f"{kimg} kimg per run, under the brief's ~2,000: a prototype limitation (pre-approved, run instruction 2026-11-13)")
    wjson(P.gan / "budget.json", b)
    log(f"budget: {b}")
    if P.test:
        return
    e = ds.get("ess", {})
    day = time.strftime("%Y-%m-%d %H:%M")
    block = (f"\n## Generation 1, GAN Phase A measured (added {day} by the pipeline on the PC, before G1 training; nothing trained yet)\n\n"
             f"Measured, not predicted (gen/g1_gan.py; runs/g1/gan/):\n"
             f"- **Weights at ESS = 0.5 N:** tau = {e.get('tau', float('nan')):.3f}; ESS = {e.get('ess', float('nan')):.0f} ({e.get('ess_share', float('nan')):.3f} N); "
             f"limit with encounter counts alone {e.get('ess_limit_share', float('nan')):.3f} N; top 1 % of tiles {e.get('top1_share', float('nan')):.3f} of the weight, "
             f"top 10 % {e.get('top10_share', float('nan')):.3f}; max/median {e.get('max_over_median', float('nan')):.1f}.\n"
             f"- **Throughput:** {thr['sec_per_kimg_concurrent']:.2f} s/kimg per run with both running concurrently (cfg auto, 128 px); custom ops: "
             f"{ {c: r['custom_ops'] for c, r in thr['runs'].items()} }.\n"
             f"- **Budget:** {kimg:,} kimg per run (the same for both): datasets {ds_h:.2f} h + training {b['training_h']:.1f} h + readouts allowed {readout_h:.1f} h <= {BUDGET_H:.0f} h."
             + (f" {b['limitation']}." if kimg < 2000 else "") + "\n"
             f"- Predictions 152-157 stand as written; they are scored against these measurements in the GAN report.\n")
    ex = ROOT / "notes" / "06_characters" / "expectations.md"
    ex.write_text(ex.read_text(encoding="utf-8") + block, encoding="utf-8")
    stf = ROOT / "STATE.md"
    s = stf.read_text(encoding="utf-8")
    line = (f"\n# GAN generation 1: the measured budget (the pipeline, {day})\n- {kimg:,} kimg per run, both concurrently at {thr['sec_per_kimg_concurrent']:.2f} s/kimg; "
            f"tau {e.get('tau', float('nan')):.3f} at ESS 0.5 N; training starts now (tag g1-start). Details: runs/g1/gan/budget.json.\n")
    stf.write_text(s + line, encoding="utf-8")
    r = subprocess.run(["git", "commit", "-m", f"generation 1: GAN Phase A measured (tau, throughput, budget {kimg} kimg); tag g1-start\n\n"
                        "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>", "--", "notes/06_characters/expectations.md", "STATE.md"],
                       cwd=ROOT, capture_output=True, text=True)
    t = subprocess.run(["git", "tag", "g1-start"], cwd=ROOT, capture_output=True, text=True)
    log(f"commit: {(r.stdout + r.stderr).strip()[-300:]}; tag g1-start: {(t.stdout + t.stderr).strip() or 'ok'}")


# -- after training --------------------------------------------------------------------------------------------------------------
def load_G(pkl: Path):
    sg_imports()
    import legacy
    import torch

    with open(pkl, "rb") as f:
        return legacy.load_network_pkl(f)["G_ema"].to("cuda").eval().requires_grad_(False), torch


def cmd_fid(P: Paths, num_gen: int | None = None) -> None:
    dnnlib = sg_imports()
    import torch
    from metrics import metric_main

    res = json.loads((P.gan / "fid.json").read_text()) if (P.gan / "fid.json").exists() else {}
    for cond in CONDS:
        run = P.run(cond)
        b = json.loads((P.gan / "budget.json").read_text())
        for k in sorted(keep_set(int(b["kimg"]))):
            pk = run / f"network-snapshot-{k:06d}.pkl"
            if not pk.exists() or str(k) in res.get(cond, {}):
                continue
            G, _ = load_G(pk)
            dk = dnnlib.EasyDict(class_name="training.dataset.ImageFolderDataset", path=str(P.ds / f"{cond}.zip"), use_labels=False, xflip=False)
            t0 = time.time()
            m = "fid50k_full"
            if num_gen:  # tests only: a shorter FID, same code path
                from metrics import frechet_inception_distance as fidm, metric_utils
                opts = metric_utils.MetricOptions(G=G, dataset_kwargs=dk, num_gpus=1, rank=0, device=torch.device("cuda"))
                v = fidm.compute_fid(opts, max_real=None, num_gen=num_gen)
            else:
                v = metric_main.calc_metric(metric=m, G=G, dataset_kwargs=dk, num_gpus=1, rank=0, device=torch.device("cuda")).results["fid50k_full"]
            res.setdefault(cond, {})[str(k)] = float(v)
            res.setdefault("_seconds", {})[f"{cond}_{k}"] = round(time.time() - t0, 1)
            wjson(P.gan / "fid.json", res)
            log(f"FID {cond} at {k} kimg: {v:.2f} ({time.time() - t0:.0f} s)")
            del G
            torch.cuda.empty_cache()
    merge_status(P)


def gen_images(G, torch, seeds, batch: int = 50) -> np.ndarray:
    out = []
    seeds = list(seeds)
    for i in range(0, len(seeds), batch):
        z = np.stack([np.random.RandomState(s).randn(G.z_dim) for s in seeds[i : i + batch]]).astype(np.float32)
        with torch.no_grad():
            img = G(torch.from_numpy(z).cuda(), None, truncation_psi=1, noise_mode="const")
        out.append((img.permute(0, 2, 3, 1) * 127.5 + 128).clamp(0, 255).to(torch.uint8).cpu().numpy())
    return np.concatenate(out)


def down(a: np.ndarray, px: int = PX_OBS) -> np.ndarray:
    """uint8 [n, 128, 128, 3] -> float32 [n, px*px*3] in [0, 1], by area (2 x 2 ... means)."""
    f = a.shape[1] // px
    return a.reshape(len(a), px, f, px, f, 3).mean((2, 4)).reshape(len(a), -1).astype(np.float32) / 255.0


def cdist_min(torch, A: np.ndarray, B: np.ndarray, exclude_self: bool = False, k: int = 1, chunk: int = 1024):
    """For each row of A: the k smallest L2 distances to B (and the index of the nearest)."""
    Bt = torch.from_numpy(B).cuda()
    d_out, i_out = [], []
    for s in range(0, len(A), chunk):
        d = torch.cdist(torch.from_numpy(A[s : s + chunk]).cuda(), Bt)
        if exclude_self:
            idx = torch.arange(s, min(s + chunk, len(A)), device=d.device)
            d[torch.arange(len(idx)), idx] = float("inf")
        v, i = d.topk(k, dim=1, largest=False)
        d_out.append(v.cpu().numpy())
        i_out.append(i[:, 0].cpu().numpy())
    return np.concatenate(d_out), np.concatenate(i_out)


def prec_recall(torch, real: np.ndarray, fake: np.ndarray, real_mult: np.ndarray | None = None, k: int = PR_K) -> dict:
    """Kynkaenniemi et al. 2019, k-NN manifolds (k = 3) in the given feature space. real_mult: multiplicities of the reference points
    (a reference drawn by weight with replacement keeps each drawn tile once, its radius among the distinct drawn tiles, and counts it
    as often as it was drawn in recall)."""
    rr = cdist_min(torch, real, real, exclude_self=True, k=k)[0][:, -1]
    fr = cdist_min(torch, fake, fake, exclude_self=True, k=k)[0][:, -1]
    Rt, Ft = torch.from_numpy(real).cuda(), torch.from_numpy(fake).cuda()
    rrt, frt = torch.from_numpy(rr).cuda(), torch.from_numpy(fr).cuda()
    prec = []
    for s in range(0, len(fake), 1024):
        d = torch.cdist(Ft[s : s + 1024], Rt)
        prec.append((d <= rrt[None]).any(1).cpu().numpy())
    rec = []
    for s in range(0, len(real), 1024):
        d = torch.cdist(Rt[s : s + 1024], Ft)
        rec.append((d <= frt[None]).any(1).cpu().numpy())
    prec, rec = np.concatenate(prec), np.concatenate(rec)
    m = np.ones(len(real)) if real_mult is None else real_mult
    return {"precision": float(prec.mean()), "recall": float((rec * m).sum() / m.sum()), "n_real": len(real), "n_real_draws": int(m.sum()), "n_fake": len(fake), "k": k}


def colour_stats(a: np.ndarray) -> pd.DataFrame:
    """Colour and texture statistics of rendered CIR images (R = nir08, G = red, B = the green band). Labelled as such: NOT the e12
    quirk detectors (those need raw values and QA; the quirk readout on samples is deferred, Moe 2026-11-13)."""
    x = a.astype(np.float32)
    luma = x.mean(3)
    return pd.DataFrame({
        "mean_r_nir": x[..., 0].mean((1, 2)), "mean_g_red": x[..., 1].mean((1, 2)), "mean_b_green": x[..., 2].mean((1, 2)),
        "std_r_nir": x[..., 0].std((1, 2)), "std_g_red": x[..., 1].std((1, 2)), "std_b_green": x[..., 2].std((1, 2)),
        "brightness": luma.mean((1, 2)),
        "black_share": (a.max(3) <= 3).mean((1, 2)),                       # pixels black in all three channels
        "white_share": (a.max(3) == 255).mean((1, 2)),                     # pixels at 255 in any channel
        "green_band_dark": np.percentile(a[..., 2].reshape(len(a), -1), 99, axis=1) <= 3,  # the blue channel (green band) black over the image
        "grad_x": np.abs(np.diff(luma, axis=2)).mean((1, 2)), "grad_y": np.abs(np.diff(luma, axis=1)).mean((1, 2)),
        "row_roughness": np.abs(np.diff(luma.mean(2), axis=1)).mean(1),    # banding along rows
    })


def summarise(df: pd.DataFrame, w: np.ndarray | None = None) -> dict:
    w = np.ones(len(df)) if w is None else np.asarray(w, float)
    return {c: float(np.average(df[c].astype(float), weights=w)) for c in df.columns}


def read_pngs(files: list[Path]) -> np.ndarray:
    return np.stack([np.asarray(Image.open(f).convert("RGB")) for f in files])


def video(frames, path: Path, fps: int) -> None:
    import imageio.v2 as imageio

    path.parent.mkdir(parents=True, exist_ok=True)
    w = imageio.get_writer(str(path), fps=fps, codec="libx264", quality=8, macro_block_size=8)
    for f in frames:
        w.append_data(f)
    w.close()


def cmd_readouts(P: Paths, n_samples: int = N_SAMPLES, video_s: int = 60) -> None:
    import torch

    t0 = time.time()
    timing = {}
    out = P.notes
    out.mkdir(parents=True, exist_ok=True)
    b = json.loads((P.gan / "budget.json").read_text())
    K = int(b["kimg"])
    R = {"kimg": K, "observer": f"downsampled pixel space, {PX_OBS} x {PX_OBS} x 3, L2 (area resampling); no pretrained network",
         "colour_note": "colour and texture statistics of the rendered images, labelled as such; not the e12 quirk detectors (deferred)", "runs": {}}
    rows = []
    for cond in CONDS:
        run = P.run(cond)
        pk = run / f"network-snapshot-{K:06d}.pkl"
        if not pk.exists():
            R["runs"][cond] = {"missing": f"no final snapshot at {K} kimg"}
            log(f"{cond}: no final snapshot; readouts skipped")
            continue
        G, _ = load_G(pk)
        t1 = time.time()
        S = gen_images(G, torch, list(SAMPLE_SEEDS)[:n_samples])
        sd = run / "samples"
        sd.mkdir(exist_ok=True)
        for s, im in zip(SAMPLE_SEEDS, S):
            Image.fromarray(im).save(sd / f"seed{s:05d}.png")
        timing[f"{cond}_samples_s"] = round(time.time() - t1, 1)
        sheet([sd / f"seed{s:05d}.png" for s in list(SAMPLE_SEEDS)[:256]], run / "samples_contact256.png", cols=16)
        if not P.test:  # the copy in the notes: 1024 px JPEG (git stays small); the full 2048 px PNG stays in runs/
            Image.open(run / "samples_contact256.png").resize((1024, 1024), Image.Resampling.BOX).save(out / f"{cond}_samples_contact256.jpg", quality=90)
        # training set
        meta = pd.read_parquet(P.ds / f"{cond}_metadata.parquet")
        T = read_pngs([P.pkg / cond / "tiles" / f"{x}.png" for x in meta.tile])
        w = meta.weight.to_numpy()
        fs, ft = down(S), down(T)
        # memorisation: each sample's nearest training tile; against the training set's own nearest-neighbour distances
        t1 = time.time()
        d_s, i_s = cdist_min(torch, fs, ft)
        d_t, _ = cdist_min(torch, ft, ft, exclude_self=True)
        d_s, d_t = d_s[:, 0], d_t[:, 0]
        q = lambda v: {f"p{p}": float(np.percentile(v, p)) for p in (1, 5, 25, 50, 75)}  # noqa: E731
        mem = {"sample_to_train": q(d_s), "train_to_train": q(d_t), "share_samples_below_train_p1": float((d_s < np.percentile(d_t, 1)).mean()),
               "median_ratio": float(np.median(d_s) / np.median(d_t))}
        order = np.argsort(d_s)[:32]
        pair_dir = run / "closest_pairs"
        pair_dir.mkdir(exist_ok=True)
        tiles_pairs = []
        for j, o in enumerate(order):
            im = np.concatenate([S[o], T[i_s[o]]], axis=1)
            Image.fromarray(im).save(pair_dir / f"{j:02d}.png")
            tiles_pairs.append({"seed": int(o), "tile": meta.tile.iloc[i_s[o]], "dist": float(d_s[o])})
        sheet(sorted(pair_dir.glob("*.png")), run / "closest32.png", cols=4)
        shutil.copyfile(run / "closest32.png", out / f"{cond}_closest32.png") if not P.test else None
        mem["closest32"] = tiles_pairs
        if cond == "curious":  # prediction 157: closer to the heaviest tiles than to the lightest
            n10 = max(1, len(meta) // 10)
            o = np.argsort(-w)
            dh = cdist_min(torch, fs, ft[o[:n10]])[0][:, 0]
            dl = cdist_min(torch, fs, ft[o[-n10:]])[0][:, 0]
            mem["to_heaviest10pct_median"], mem["to_lightest10pct_median"] = float(np.median(dh)), float(np.median(dl))
            mem["share_closer_to_heaviest"] = float((dh < dl).mean())
        timing[f"{cond}_memorisation_s"] = round(time.time() - t1, 1)
        # diversity: precision and recall against the unweighted training set, and (curious) against N draws by the weights
        t1 = time.time()
        rng = np.random.default_rng(SEED)
        nr = min(len(ft), n_samples)
        div = {"unweighted": prec_recall(torch, ft[np.sort(rng.choice(len(ft), nr, replace=False))], fs)}
        if cond == "curious":
            # draws by weight, with replacement, until the reference holds as many distinct tiles as the unweighted one (so both
            # manifolds are estimated from the same number of points); each counts in recall as often as it was drawn
            draw = rng.choice(len(ft), 50 * nr, replace=True, p=w / w.sum())
            first = np.flatnonzero(~pd.Series(draw).duplicated().to_numpy())
            cut = first[nr - 1] + 1 if len(first) >= nr else len(draw)
            u, m = np.unique(draw[:cut], return_counts=True)
            div["weighted"] = prec_recall(torch, ft[u], fs, real_mult=m.astype(float))
            div["weighted"].update(distinct_drawn=len(u), draws=int(cut))
        timing[f"{cond}_diversity_s"] = round(time.time() - t1, 1)
        # colour and texture statistics: training (unweighted and weighted) against samples
        cs_t, cs_s = colour_stats(T), colour_stats(S)
        cols = {"train_unweighted": summarise(cs_t), "samples": summarise(cs_s)}
        if cond == "curious":
            cols["train_weighted"] = summarise(cs_t, w)
        for k_, v_ in cols.items():
            rows.append({"run": cond, "set": k_, **v_})
        cs_s.assign(seed=list(SAMPLE_SEEDS)[: len(cs_s)]).to_parquet(run / "samples_colour_stats.parquet")
        cs_t.assign(tile=meta.tile.to_numpy(), weight=w).to_parquet(run / "train_colour_stats.parquet")
        # film: a 60-second latent interpolation through fixed seeds (linear in W, psi 1), 30 fps, 512 px (nearest: the pixels stay)
        t1 = time.time()
        keys = 12
        with torch.no_grad():
            zk = torch.from_numpy(np.stack([np.random.RandomState(s).randn(G.z_dim) for s in range(keys + 1)]).astype(np.float32)).cuda()
            wk = G.mapping(zk, None, truncation_psi=1)
            frames = []
            per = video_s * 30 // keys
            for a in range(keys):
                for f in range(per):
                    t = f / per
                    wv = wk[a : a + 1] * (1 - t) + wk[a + 1 : a + 2] * t
                    im = G.synthesis(wv, noise_mode="const")
                    im = (im.permute(0, 2, 3, 1) * 127.5 + 128).clamp(0, 255).to(torch.uint8)[0].cpu().numpy()
                    frames.append(np.asarray(Image.fromarray(im).resize((512, 512), Image.Resampling.NEAREST)))
        video(frames, run / "interpolation_60s.mp4", 30)
        snaps = sorted(run.glob("fakes8x8_*.png"))
        video((np.asarray(Image.open(f).convert("RGB")) for f in snaps), run / "fakes_timelapse.mp4", 6) if snaps else None
        timing[f"{cond}_film_s"] = round(time.time() - t1, 1)
        st = stats_tail(run, 1)
        R["runs"][cond] = {"final_augment_p": st.get("augment_p"), "memorisation": mem, "diversity": div, "colour_texture": cols, "n_samples": len(S),
                           "n_train": len(T)}
        del G
        torch.cuda.empty_cache()
    if rows:
        pd.DataFrame(rows).to_csv(out / "colour_texture.csv", index=False)
    if all(c in R["runs"] and "missing" not in R["runs"][c] for c in CONDS):  # side by side over training
        a, bq = sorted(P.run("curious").glob("fakes8x8_*.png")), sorted(P.run("null").glob("fakes8x8_*.png"))
        common = sorted({f.name for f in a} & {f.name for f in bq})
        if common:
            video((np.concatenate([np.asarray(Image.open(P.run(c) / n).convert("RGB")) for c in CONDS], axis=1) for n in common),
                  P.gan / "fakes_timelapse_side_by_side.mp4", 6)
    fj = P.gan / "fid.json"
    R["fid"] = json.loads(fj.read_text()) if fj.exists() else None
    R["timing"] = {**timing, "total_s": round(time.time() - t0, 1)}
    wjson(out / "readouts.json", R)
    log(f"readouts in {time.time() - t0:.0f} s -> {out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["datasets", "throughput", "budget", "train", "fid", "readouts", "_train_into", "_train_test"])
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args()
    P = Paths(a.test)
    if a.cmd == "datasets":
        cmd_datasets(P)
    elif a.cmd == "throughput":
        cmd_throughput(P)
    elif a.cmd == "budget":
        cmd_budget(P)
    elif a.cmd == "train":
        cmd_train(a.rest[0], P)
    elif a.cmd == "_train_into":  # throughput: one run into a throwaway directory
        cond, run_dir, kimg = a.rest[0], Path(a.rest[1]), int(a.rest[2])  # snapshot only at the end
        r = train(cond, P, kimg, run=run_dir, snap_ticks=1000, tag="throughput")
        sys.exit(0 if r == "finished" else 1)
    elif a.cmd == "_train_test":  # Phase A tests only: cond, run dir, total kimg, snapshot ticks
        cond, run_dir, kimg, snap = a.rest[0], Path(a.rest[1]), int(a.rest[2]), int(a.rest[3])
        r = train(cond, P, kimg, run=run_dir, snap_ticks=snap, tag="TEST")
        log(f"{cond} test run: {r}")
        sys.exit(0 if r in ("finished", "stopped") else 1)
    elif a.cmd == "fid":
        cmd_fid(P)
    elif a.cmd == "readouts":
        cmd_readouts(P)


if __name__ == "__main__":
    main()
