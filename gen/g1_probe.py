"""Throughput probes on the real G1 datasets (2026-11-13): why both runs concurrently train at ~90 s/kimg each.

    scripts\\sg.bat gen/g1_probe.py single            # curious alone, 20 kimg
    scripts\\sg.bat gen/g1_probe.py concurrent16      # both concurrently with batch_gpu 16 (two rounds of 16 per batch of 32), 20 kimg each

Throwaway runs in runs/g1/gan/probe/ (deleted afterwards); results appended to runs/g1/gan/probe.json. sec/kimg over ticks after 8 kimg.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs" / "g1" / "gan" / "probe"


def run(conds, kimg=20, env_extra=None):
    procs = {}
    for c in conds:
        d = OUT / f"{sys.argv[1]}_{c}"
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
        procs[c] = (d, subprocess.Popen([sys.executable, str(ROOT / "gen" / "g1_gan.py"), "_train_into", c, str(d), str(kimg)], cwd=ROOT,
                                        env={**os.environ, **(env_extra or {})}, stdout=open(d / "stdout.log", "w"), stderr=subprocess.STDOUT))
    t0 = time.time()
    res = {}
    for c, (d, p) in procs.items():
        rc = p.wait()
        L = [json.loads(x) for x in (d / "stats.jsonl").read_text().splitlines() if x.strip()]
        spk = [x["Timing/sec_per_kimg"]["mean"] for x in L if x["Progress/kimg"]["mean"] > 8]
        mem = max(x.get("Resources/peak_gpu_mem_gb", {}).get("mean", 0) for x in L)
        res[c] = {"rc": rc, "sec_per_kimg": sum(spk) / len(spk) if spk else None, "ticks": len(spk), "peak_gpu_mem_gb": mem}
    return {"probe": sys.argv[1], "env": env_extra or {}, "wall_s": round(time.time() - t0, 1), "runs": res, "time": time.strftime("%Y-%m-%d %H:%M:%S")}


if __name__ == "__main__":
    what = sys.argv[1]
    r = {"single": lambda: run(["curious"]), "concurrent32": lambda: run(["curious", "null"]),
         "concurrent16": lambda: run(["curious", "null"], env_extra={"G1_BATCH_GPU": "16"})}[what]()
    f = ROOT / "runs" / "g1" / "gan" / "probe.json"
    allr = json.loads(f.read_text()) if f.exists() else []
    allr.append(r)
    f.write_text(json.dumps(allr, indent=1))
    print(json.dumps(r))
