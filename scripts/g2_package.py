"""The recursion's path packages: a latent walk in G<g-1> becomes the training set of G<g> (Moe, 2026-11-16: "same rules as G1").

    python scripts/g2_package.py build curious|null [--gen 2] [--test]

Input: runs/g<g-1>/latent/<cond>/ (steps.parquet, visited.npz, meta.json, walk.json, tiles/k<key>_s<snapshot>.png), written by
agent/latent_walk.py. Output: paths/g<g>/<cond>/ in the G1 package format (scripts/g1_package.py), so scripts/g1_verify.py, the weights
(exp(I / tau) at ESS 0.5 N) and gen/g1_gan.py datasets apply unchanged:
- tiles/<tile>.png: the walk's own renders, 128 x 128, as rendered (G_ema, psi 1, const noise); nothing is cut or repaired;
- tiles.parquet: one row per unique tile (image_key = the walk's key; tile = k<key>_s<snapshot>; snapshot; colour statistics);
- encounters.parquet: the start row (step -1, no interest) and one row per step with the interest components at the choice;
- manifest.json: N, q, the walk, the render check (20 tiles re-rendered from their z and snapshot), sha256 of every file.
In a latent walk every step lands on a new tile (a new z, or the same z in a later snapshot), so N = steps + 1 and each tile is met
once; the curious weights are then exp(I / tau) of that one encounter.
--test: from runs/g<g-1>/latent_test/ into runs/g<g>/test/paths/, labelled TEST, N = the test walk's tiles.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
from g1_verify import sha256  # noqa: E402

N_PKG = 10_000
N_RENDER_CHECK = 20


def colour(a: np.ndarray) -> dict:
    x = a.astype(np.float32)
    lum = x.mean(2)
    return {"brightness": float(lum.mean()), "white_share": float((x.min(2) >= 230).mean()), "black_share": float((x.max(2) <= 25).mean()),
            "mean_r_nir": float(x[..., 0].mean()), "mean_g_red": float(x[..., 1].mean()), "mean_b_green": float(x[..., 2].mean())}


def build(cond: str, gen: int, test: bool) -> Path:
    t0 = time.time()
    src = ROOT / "runs" / f"g{gen - 1}" / ("latent_test" if test else "latent") / cond
    dst = (ROOT / "runs" / f"g{gen}" / "test" / "paths" / cond) if test else ROOT / "paths" / f"g{gen}" / cond
    walk = json.loads((src / "walk.json").read_text())
    meta = json.loads((src / "meta.json").read_text())
    s = pd.read_parquet(src / "steps.parquet").sort_values("step").reset_index(drop=True)
    v = np.load(src / "visited.npz")
    keys, zs, snaps = v["key"], v["z"], v["snapshot"]
    assert len(keys) == len(s) + 1 and keys[0] == meta["start_key"], "visited.npz and steps.parquet disagree"
    assert len(set(keys.tolist())) == len(keys), "a latent walk revisits no tile (every step lands on a new key)"
    n = len(keys) if test else N_PKG
    if len(keys) < n:
        sys.exit(f"{cond}: the walk has {len(keys)} tiles, fewer than N = {n}; not packaged")
    keys, zs, snaps = keys[:n], zs[:n], snaps[:n]
    steps = s.iloc[: n - 1]
    walk_id = f"{cond}_latent_g{gen - 1}"
    tile = [f"k{k:06d}_s{sn:04d}" for k, sn in zip(keys, snaps)]
    if dst.exists():
        shutil.rmtree(dst)
    (dst / "tiles").mkdir(parents=True)
    rows = []
    for i, (k, sn, name) in enumerate(zip(keys, snaps, tile)):
        f = src / "tiles" / f"{name}.png"
        shutil.copyfile(f, dst / "tiles" / f"{name}.png")
        a = np.asarray(Image.open(f).convert("RGB"))
        assert a.shape == (128, 128, 3), f"{f} is not 128 x 128 RGB"
        rows.append({"image_key": int(k), "tile": name, "snapshot": int(sn), "n_encounters": 1, "first_walk": walk_id, "first_step": i - 1,
                     **colour(a)})
    t = pd.DataFrame(rows)
    comp = ["z_glance", "z_grid", "z_prog", "I"]
    e = pd.concat([pd.DataFrame([{"walk_id": walk_id, "step": -1, "clock": int(snaps[0]), "image_key": int(keys[0]), "kind": "start",
                                  "wait": False, "move": False, "tile": tile[0], **{c: np.nan for c in comp}}]),
                   pd.DataFrame({"walk_id": walk_id, "step": steps.step.to_numpy(), "clock": steps.snapshot.to_numpy().astype(int),
                                 "image_key": steps.key.to_numpy().astype(int),
                                 "kind": np.where(steps.kind == "time", "wait", "move"), "wait": (steps.kind == "time").to_numpy(),
                                 "move": (steps.kind != "time").to_numpy(), "tile": tile[1:], **{c: steps[c].to_numpy(float) for c in comp}})],
                  ignore_index=True)
    assert (e.image_key.to_numpy() == keys).all()
    t.to_parquet(dst / "tiles.parquet")
    e.to_parquet(dst / "encounters.parquet")
    # the render check: tiles re-rendered from their z at their snapshot, against the package PNGs
    import agent.latent_walk as LW
    LW.GEN = gen - 1
    rng = np.random.default_rng(20261116)
    pick = np.sort(rng.choice(n, min(N_RENDER_CHECK, n), replace=False))
    W = LW.LatentWorld(cond, meta["snapshots"], "cuda", "cpu")
    snap_idx = {k: i for i, k in enumerate(meta["snapshots"])}
    maxd, exact = 0, 0
    for i in pick:
        kk = W.add(zs[i], snap_idx[int(snaps[i])])
        _, a = W.render([kk])
        b = np.asarray(Image.open(dst / "tiles" / f"{tile[i]}.png").convert("RGB"))
        d = int(np.abs(a[0].astype(int) - b.astype(int)).max())
        maxd, exact = max(maxd, d), exact + (d == 0)
        W.drop([kk])
    rc = {"n": int(len(pick)), "exact": int(exact), "max_abs_diff": maxd, "tolerance": 2, "passed": bool(maxd <= 2),
          "note": "re-rendered one tile at a time on the GPU; the walk rendered offers in batches, so the last bit may differ"}
    m = {"label": "TEST" if test else f"G{gen} training package from the G{gen - 1} latent walk", "condition": cond, "N": int(n),
         "q": meta.get("q"), "walks": [{"walk_id": walk_id, "source": str(src.relative_to(ROOT)).replace("\\", "/"), **walk}],
         "cut": f"the first {n} tiles of the walk (start included)" if not test else "TEST: all tiles",
         "start_list": f"z from seed {meta.get('seed', 0)} at {meta['snapshots'][0]} kimg",
         "walker": {"config": meta.get("config"), "alpha_min_deg": meta.get("alpha_min_deg"), "alpha_max_deg": meta.get("alpha_max_deg")},
         "rendering": f"G{gen - 1}-{cond} G_ema, psi 1, const noise, 128 px, the snapshot at the walk's clock ({meta['snapshots']})",
         "interest_columns": comp, "render_check": rc, "built": time.strftime("%Y-%m-%d %H:%M:%S"), "build_seconds": round(time.time() - t0, 1)}
    m["files"] = {str(f.relative_to(dst)).replace("\\", "/"): sha256(f) for f in sorted(dst.rglob("*")) if f.is_file()}
    (dst / "manifest.json").write_text(json.dumps(m, indent=1, default=str))
    print(f"[g2_package] {cond}: {n} tiles from {walk_id} -> {dst}; waits {int(e.wait.sum())}; render check {rc}", flush=True)
    if not rc["passed"]:
        sys.exit(4)
    return dst


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build"])
    ap.add_argument("cond", choices=["curious", "null"])
    ap.add_argument("--gen", type=int, default=2)
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args()
    build(a.cond, a.gen, a.test)


if __name__ == "__main__":
    main()
