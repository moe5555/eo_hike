"""Verify the two generation-1 path packages, don't repair them (notes/brief_gan_g1.md, Inputs 3; the handoff).

    python scripts/g1_verify.py paths                                   # paths/g1/{curious,null} -> runs/g1/verify_paths.json
    python scripts/g1_verify.py paths --root runs/g1/test/paths --n 30 --out runs/g1/test/verify.json   # the TEST packages

Checks, per package and across both:
- every file's SHA-256 matches the manifest, and no file is missing or extra;
- exactly N unique tiles (tiles/ PNGs, tiles.parquet rows, unique encounter tiles), every PNG 128 x 128 8-bit RGB;
- both packages carry the same start-cell list (path, seed, checksum), and it is the committed configs/gen1/start_list.csv;
- every curious encounter has its interest components (z glance, z grid, z progress, I), except each walk's start tile (step -1);
  the Null's are checked and reported the same way (kept as a control);
- the manifest records the render check (20 tiles re-rendered from the store, byte for byte) as passed.
Exit 0 if everything passes, 1 otherwise. The result is written as JSON either way.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
COMP = ["z_glance", "z_grid", "z_prog", "I"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def check(pkg: Path, n: int) -> dict:
    r: dict = {"package": str(pkg), "problems": []}
    P = r["problems"]
    m = json.loads((pkg / "manifest.json").read_text())
    r["condition"], r["label"] = m["condition"], m.get("label")
    files = {str(p.relative_to(pkg)).replace("\\", "/") for p in pkg.rglob("*") if p.is_file()} - {"manifest.json"}
    listed = set(m["files"])
    if files != listed:
        P.append(f"files on disk and in the manifest differ: {len(files - listed)} extra, {len(listed - files)} missing")
    bad = [f for f in sorted(files & listed) if sha256(pkg / f) != m["files"][f]]
    if bad:
        P.append(f"{len(bad)} checksums differ, e.g. {bad[:3]}")
    r["files_checked"] = len(files & listed)
    t = pd.read_parquet(pkg / "tiles.parquet")
    e = pd.read_parquet(pkg / "encounters.parquet")
    pngs = sorted((pkg / "tiles").glob("*.png"))
    r["n_png"], r["n_tiles_rows"], r["n_unique_encounter_tiles"] = len(pngs), len(t), int(e.image_key.nunique())
    if not (m["N"] == n == len(pngs) == len(t) == e.image_key.nunique() == t.image_key.nunique()):
        P.append(f"not exactly N = {n} unique tiles: manifest {m['N']}, png {len(pngs)}, tiles {len(t)}, encounters {e.image_key.nunique()}")
    if set(t.tile + ".png") != {p.name for p in pngs}:
        P.append("tile names in tiles.parquet and tiles/ differ")
    odd = []
    for p in pngs:
        with Image.open(p) as im:
            if im.size != (128, 128) or im.mode != "RGB":
                odd.append(p.name)
    if odd:
        P.append(f"{len(odd)} PNGs not 128 x 128 RGB, e.g. {odd[:3]}")
    start = e.step == -1
    r["start_rows"] = int(start.sum())
    r["walks"] = [w["walk_id"] for w in m["walks"]]
    if r["start_rows"] != e.walk_id.nunique():
        P.append(f"{r['start_rows']} start rows for {e.walk_id.nunique()} walks")
    if e.loc[start, COMP].notna().any().any():
        P.append("a start tile carries interest components")
    miss = e.loc[~start, COMP].isna().any(axis=1)
    r["encounters"], r["encounters_missing_components"] = len(e), int(miss.sum())
    if m["condition"] == "curious" and miss.any():
        P.append(f"{int(miss.sum())} curious encounters without interest components")
    rc = m.get("render_check", {})
    r["render_check"] = {"passed": rc.get("passed"), "n": rc.get("n")}
    if not rc.get("passed") or rc.get("n", 0) < min(20, n):
        P.append(f"render check not passed: {r['render_check']}")
    r["start_list"] = m["start_list"]
    r["passed"] = not P
    return r


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["paths"])
    ap.add_argument("--root", default=str(ROOT / "paths" / "g1"))
    ap.add_argument("--n", type=int, default=10_000)
    ap.add_argument("--out", default=str(ROOT / "runs" / "g1" / "verify_paths.json"))
    a = ap.parse_args()
    root = Path(a.root)
    res = {c: check(root / c, a.n) for c in ("curious", "null")}
    sl = {c: {k: res[c]["start_list"][k] for k in ("path", "seed", "sha256")} for c in res}
    committed = sha256(ROOT / "configs" / "gen1" / "start_list.csv")
    same = sl["curious"] == sl["null"] and sl["curious"]["sha256"] == committed
    out = {"passed": all(r["passed"] for r in res.values()) and same, "same_start_list": same, "start_list_sha256_committed": committed,
           "N": a.n, "packages": res}
    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    for c, r in res.items():
        print(f"[verify] {c}: {'passed' if r['passed'] else 'FAILED'}; {r['n_png']:,} tiles, {r['encounters']:,} encounters "
              f"({r['encounters_missing_components']} without components besides {r['start_rows']} start rows); render check {r['render_check']}"
              + ("" if r["passed"] else f"; problems: {r['problems']}"))
    print(f"[verify] same start list in both, as committed: {same}. {'PASSED' if out['passed'] else 'FAILED'} -> {a.out}")
    sys.exit(0 if out["passed"] else 1)


if __name__ == "__main__":
    main()
