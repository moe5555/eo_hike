"""Test of alternating-chunk training (2026-11-14): one run in chunks to 8, 16, then 24 kimg in a scratch folder, each chunk a new process
resuming from the last snapshot pair. Checks: each chunk stops at the first tick past its boundary; Adam's step counters and the batch index
equal an uninterrupted run; kimg and augment p continue. Result -> runs/g1/phase_a/chunk_test.json; the scratch folder is deleted."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "g1" / "gan" / "chunktest_curious"


def main() -> None:
    shutil.rmtree(RUN, ignore_errors=True)
    RUN.mkdir(parents=True)
    code = ("import sys; sys.path.insert(0, r'{g}'); import g1_gan as G; from pathlib import Path; "
            "r = G.train('curious', G.Paths(False), 24, run=Path(r'{run}'), snap_ticks=2, stop_after_kimg={u}, tag='CHUNKTEST'); print('RESULT', r)")
    out = []
    for u in (8, 16, None):
        p = subprocess.run([sys.executable, "-c", code.format(g=ROOT / "gen", run=RUN, u=u)], cwd=ROOT, capture_output=True, text=True)
        res = [l for l in p.stdout.splitlines() if l.startswith("RESULT")]
        ks = sorted(int(f.stem.split("-")[-1]) for f in RUN.glob("training-state-*.pt"))
        out.append({"until": u, "rc": p.returncode, "result": res[-1] if res else p.stderr[-500:], "states_after": ks})
    L = [json.loads(x) for x in (RUN / "stats.jsonl").read_text().splitlines() if x.strip()]
    kimg = [round(x["Progress/kimg"]["mean"], 1) for x in L]
    aug = [round(x["Progress/augment"]["mean"], 4) for x in L]
    chk = {}
    for f in sorted(RUN.glob("training-state-*.pt")):
        st = torch.load(f, weights_only=False)
        it = st["cur_nimg"] // 32
        got = {ph: int(next(iter(st["opt"][ph]["state"].values()))["step"]) for ph in ("Gmain", "Dmain")}
        exp = {"Gmain": it + (it + 3) // 4, "Dmain": it + (it + 15) // 16}
        chk[f.stem] = {"iterations": it, "batch_idx": st["batch_idx"], "adam": got, "expected": exp, "ok": got == exp and st["batch_idx"] == it}
    finished = (RUN / "FINISHED").exists()
    passed = (finished and all(v["ok"] for v in chk.values()) and out[0]["result"].endswith("aborted") and out[1]["result"].endswith("aborted")
              and out[2]["result"].endswith("finished") and 12 in out[0]["states_after"] and 20 in out[1]["states_after"])
    r = {"passed": bool(passed), "chunks": out, "kimg_ticks": kimg, "augment_ticks": aug, "states": chk, "finished": finished}
    (ROOT / "runs" / "g1" / "phase_a" / "chunk_test.json").write_text(json.dumps(r, indent=1))
    print(json.dumps(r)[:2500])
    if passed:
        shutil.rmtree(RUN, ignore_errors=True)


if __name__ == "__main__":
    main()
