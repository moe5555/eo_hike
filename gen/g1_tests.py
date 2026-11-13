"""Phase A tests of the generation-1 GAN side and the supervisor, on the TEST packages (runs/g1/test/; never trained on for real).
Results -> runs/g1/test/phase_a_tests.json. Run with .venv-sg through scripts/sg.bat (the training tests compile the CUDA ops).

    scripts\\sg.bat gen/g1_tests.py sampler      # the weighted sampler: 100k draws against the weights
    scripts\\sg.bat gen/g1_tests.py train        # both TEST runs concurrently; curious killed mid-run and resumed; Null stopped by the STOP file
    scripts\\sg.bat gen/g1_tests.py fid          # fid50k_full on the TEST snapshots (fills the Inception cache, times it)
    scripts\\sg.bat gen/g1_tests.py readouts     # the full readouts on the TEST snapshots (5,000 samples, the 60-second videos), timed
    scripts\\sg.bat gen/g1_tests.py supervisor   # the job watchdog (restart, give up after 3), the disk guard, the status rendering
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / "runs" / "g1" / "test"
RES = TEST / "phase_a_tests.json"
SG_BAT = str(ROOT / "scripts" / "sg.bat")


def record(name: str, d: dict) -> None:
    r = json.loads(RES.read_text()) if RES.exists() else {}
    r[name] = {**d, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    RES.write_text(json.dumps(r, indent=1, default=str))
    print(f"[test {name}] {'PASSED' if d.get('passed') else 'FAILED'}: {json.dumps(d, default=str)[:1500]}", flush=True)


def t_sampler() -> None:
    sys.path.insert(0, str(ROOT / "third_party" / "stylegan2-ada-pytorch"))
    from torch_utils import misc

    w = json.loads((TEST / "gan" / "datasets" / "curious_weights.json").read_text())
    names = sorted(w)
    wv = np.array([w[n] for n in names])
    p = wv / wv.sum()
    n = 100_000
    it = iter(misc.WeightedInfiniteSampler(wv, seed=0, start_nimg=0))
    draws = np.array([next(it) for _ in range(n)])
    obs = np.bincount(draws, minlength=len(p))
    exp = n * p
    z = (obs - exp) / np.sqrt(exp * (1 - p))
    chi2 = float(((obs - exp) ** 2 / exp).sum())
    dof = len(p) - 1
    # chi-square against its dof: (chi2 - dof) / sqrt(2 dof) is ~N(0, 1)
    zc = (chi2 - dof) / np.sqrt(2 * dof)
    it2 = iter(misc.WeightedInfiniteSampler(wv, seed=0, start_nimg=0))
    same = all(next(it2) == d for d in draws[:1000])
    it3 = iter(misc.WeightedInfiniteSampler(wv, seed=0, start_nimg=8000))
    other = sum(next(it3) == d for d in draws[:1000])
    ones = iter(misc.WeightedInfiniteSampler(np.ones(len(p)), seed=0))
    u = np.bincount([next(ones) for _ in range(n)], minlength=len(p))
    zu = (((u - n / len(p)) ** 2 / (n / len(p))).sum() - dof) / np.sqrt(2 * dof)
    record("sampler", {"passed": bool(abs(zc) < 4 and np.abs(z).max() < 5 and same and abs(zu) < 4), "draws": n, "tiles": len(p), "chi2": chi2, "dof": dof,
                       "chi2_z": float(zc), "max_abs_z_per_tile": float(np.abs(z).max()), "reproducible_same_seed": same,
                       "agreement_with_resumed_stream_in_1000": int(other), "uniform_weights_chi2_z": float(zu),
                       "heaviest_expected_vs_observed": [float(exp.max()), int(obs[np.argmax(exp)])]})


def popen_train(cond: str, run: Path, total: int, snap: int) -> subprocess.Popen:
    run.mkdir(parents=True, exist_ok=True)
    return subprocess.Popen(["cmd", "/c", SG_BAT, "gen/g1_gan.py", "_train_test", cond, str(run), str(total), str(snap), "--test"], cwd=ROOT,
                            stdout=open(run.parent / f"{run.name}_stdout.log", "a"), stderr=subprocess.STDOUT)


def kill_tree(pid: int) -> None:
    import psutil

    p = psutil.Process(pid)
    for q in p.children(recursive=True) + [p]:
        try:
            q.kill()
        except psutil.NoSuchProcess:
            pass


def t_train() -> None:
    import torch

    g = TEST / "gan"
    for c in ("curious", "null"):
        shutil.rmtree(g / c, ignore_errors=True)
    total = 24
    t0 = time.time()
    pc, pn = popen_train("curious", g / "curious", total, 1), popen_train("null", g / "null", total, 1)
    st8 = g / "curious" / "training-state-000008.pt"
    while not st8.exists() and pc.poll() is None:
        time.sleep(5)
    time.sleep(20)  # mid-tick: kill between snapshots
    killed_at = time.time()
    kill_tree(pc.pid)
    pc.wait()
    s8 = torch.load(st8, weights_only=False)
    # the Null: the STOP file (as the disk guard writes it) once it passes 12 kimg
    st12n = g / "null" / "training-state-000012.pt"
    while not st12n.exists() and pn.poll() is None:
        time.sleep(5)
    (g / "null" / "STOP").write_text("test")
    pc2 = popen_train("curious", g / "curious", total, 1)  # the resume, as the watchdog would start it
    rc_c, rc_n = pc2.wait(), pn.wait()
    (g / "train_test_run.json").write_text(json.dumps({"rc": [rc_c, rc_n], "wall_s": round(time.time() - t0, 1), "killed_after_state_8_s": round(killed_at - st8.stat().st_mtime, 1)}))
    t_train_check()


def t_train_check() -> None:
    """Resume continuity, from what retention keeps: Adam's step counters must equal those of an uninterrupted run (Gmain every
    iteration + Greg every 4th; Dmain every iteration + Dreg every 16th), the batch index and kimg must agree, and stats.jsonl must
    continue (kimg never restarts at 0, augment p never drops to 0 after the resume)."""
    import torch

    g = TEST / "gan"
    run = json.loads((g / "train_test_run.json").read_text())
    rc_c, rc_n = run["rc"]
    c = g / "curious"
    L = [json.loads(x) for x in (c / "stats.jsonl").read_text().splitlines() if x.strip()]
    kimg = [round(x["Progress/kimg"]["mean"], 1) for x in L]
    aug = [round(x["Progress/augment"]["mean"], 4) for x in L]
    lossG = [round(x["Loss/G/loss"]["mean"], 3) if "Loss/G/loss" in x else None for x in L]
    states = {int(p.stem.split("-")[-1]): torch.load(p, weights_only=False) for p in sorted(c.glob("training-state-*.pt"))}
    batch = 32
    chk = {}
    for k, st in states.items():
        it = st["cur_nimg"] // batch
        exp = {"Gmain": it + (it + 3) // 4, "Dmain": it + (it + 15) // 16}
        got = {ph: int(next(iter(st["opt"][ph]["state"].values()))["step"]) for ph in ("Gmain", "Dmain")}
        chk[k] = {"iterations": it, "batch_idx": st["batch_idx"], "adam_step": got, "expected_uninterrupted": exp, "augment_p": st["augment_p"],
                  "ok": got == exp and st["batch_idx"] == it}
    log = (c / "log.txt").read_text(errors="replace")
    ops = {n: (f'Setting up PyTorch plugin "{n}"... Done.' in log) for n in ("bias_act_plugin", "upfirdn2d_plugin")}
    resumed = "Resuming training state" in log
    mono = all(b > a for a, b in zip(kimg, kimg[1:])) or kimg.count(0.0) == 1
    aug_cont = all(a > 0 for a in aug[1:])
    fin, stopped = (c / "FINISHED").exists(), (g / "null" / "STOPPED_DISK").exists()
    passed = rc_c == 0 and rc_n == 0 and fin and stopped and resumed and all(v["ok"] for v in chk.values()) and aug_cont and all(ops.values())
    record("train", {"passed": bool(passed), **run, "curious_finished": fin, "null_stopped_by_STOP_file": stopped, "resumed_line_in_log": resumed,
                     "states": chk, "kimg_ticks": kimg, "kimg_monotonic_after_resume": mono, "augment_ticks": aug, "augment_continues": aug_cont,
                     "lossG_ticks": lossG, "custom_ops_compiled": ops,
                     "fallback_warnings": [w for w in ("conv2d_gradfix not supported", "grid_sample_gradfix not supported") if w in log],
                     "fakes_grids": len(list(c.glob("fakes8x8_*.png"))), "snapshots_kept": sorted(p.name for p in c.glob("network-snapshot-*.pkl"))})


def t_fid() -> None:
    g = TEST / "gan"
    (g / "budget.json").write_text(json.dumps({"kimg": 24, "note": "TEST"}))
    t0 = time.time()
    r = subprocess.run(["cmd", "/c", SG_BAT, "gen/g1_gan.py", "fid", "--test"], cwd=ROOT, capture_output=True, text=True)
    fid = json.loads((g / "fid.json").read_text()) if (g / "fid.json").exists() else {}
    secs = list(fid.get("_seconds", {}).values())
    cache = ROOT / "runs" / "g1" / "dnnlib_cache"
    files = [str(p.relative_to(cache)) for p in cache.rglob("*") if p.is_file()]
    record("fid", {"passed": r.returncode == 0 and bool(secs), "fid": fid, "seconds_per_fid": secs, "wall_s": round(time.time() - t0, 1),
                   "inception_cached": any("inception" in f for f in files), "cache_files": files, "stderr_tail": r.stdout[-600:] + r.stderr[-600:]})


def t_readouts() -> None:
    g = TEST / "gan"
    t0 = time.time()
    r = subprocess.run(["cmd", "/c", SG_BAT, "gen/g1_gan.py", "readouts", "--test"], cwd=ROOT, capture_output=True, text=True)
    ro = json.loads((TEST / "notes_gan" / "readouts.json").read_text()) if (TEST / "notes_gan" / "readouts.json").exists() else {}
    tests = json.loads(RES.read_text())
    fid_s = np.mean(tests.get("fid", {}).get("seconds_per_fid") or [600])
    total = ro.get("timing", {}).get("total_s", time.time() - t0)
    # Phase B: readouts for two runs (as here, one of them stopped early in the test: count the curious run twice) + 4 FIDs per run
    per_run = sum(v for k, v in ro.get("timing", {}).items() if k.startswith("curious_"))
    projected = (2 * per_run + 8 * fid_s) / 3600 * 1.25
    (TEST / "readout_timing.json").write_text(json.dumps({"readouts_test_s": total, "per_run_s": per_run, "fid_s": fid_s, "projected_h": projected}))
    ok = r.returncode == 0 and "curious" in ro.get("runs", {}) and "missing" not in ro["runs"]["curious"]
    record("readouts", {"passed": bool(ok), "timing": ro.get("timing"), "projected_phase_b_readouts_h": round(projected, 2),
                        "samples": len(list((g / "curious" / "samples").glob("*.png"))), "video": (g / "curious" / "interpolation_60s.mp4").exists(),
                        "timelapse": (g / "curious" / "fakes_timelapse.mp4").exists(), "curious": ro.get("runs", {}).get("curious"),
                        "stdout_tail": r.stdout[-800:] + r.stderr[-800:]})


def t_supervisor() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    import g1_lib as L

    out = {}
    py = sys.executable
    L.EVENTS_F = TEST / "events_test.log"  # the real events.log stays clean
    # 1. the job watchdog: a job that always fails is retried, then given up after its attempts
    st = {"jobs": {}, "walks": {}}
    log = TEST / "sup_fail.log"
    seen = []
    for _ in range(12):
        r = L.run_job(st, "test_fail", [py, "-c", "import sys; sys.exit(7)"], log, python=py, attempts=3)
        seen.append(r)
        if r == "failed":
            break
        time.sleep(4)
    out["fail_job"] = {"sequence": seen, "attempts": st["jobs"]["test_fail"]["attempts"], "gives_up": seen[-1] == "failed" and st["jobs"]["test_fail"]["attempts"] == 3}
    # 2. a job killed while running (no exit record) is restarted, and a job that succeeds is 'ok'
    st = {"jobs": {}, "walks": {}}
    flag = TEST / "sup_flag"
    flag.unlink(missing_ok=True)
    cmd = [py, "-c", f"import time, pathlib, sys; p = pathlib.Path(r'{flag}'); first = not p.exists(); p.write_text('x'); time.sleep(30 if first else 1); sys.exit(0)"]
    seq = [L.run_job(st, "test_kill", cmd, TEST / "sup_kill.log", python=py, attempts=3)]
    time.sleep(3)
    L.kill_tree(st["jobs"]["test_kill"]["pid"])
    for _ in range(15):
        time.sleep(3)
        seq.append(L.run_job(st, "test_kill", cmd, TEST / "sup_kill.log", python=py, attempts=3))
        if seq[-1] == "ok":
            break
    out["killed_job"] = {"sequence": seq, "restarted_and_ok": seq[-1] == "ok" and st["jobs"]["test_kill"]["attempts"] == 2}
    # 3. a stalled job (no log output) is killed and restarted
    st = {"jobs": {}, "walks": {}}
    slog = TEST / "sup_stall.log"
    r1 = L.run_job(st, "test_stall", [py, "-c", "import time; time.sleep(60)"], slog, python=py, attempts=3, stall_s=5)
    time.sleep(8)
    os.utime(slog, (time.time() - 100, time.time() - 100))
    r2 = L.run_job(st, "test_stall", [py, "-c", "import time; time.sleep(60)"], slog, python=py, attempts=3, stall_s=5)
    time.sleep(3)
    r3 = L.run_job(st, "test_stall", [py, "-c", "import time; time.sleep(1)"], slog, python=py, attempts=3, stall_s=5)
    out["stall"] = {"sequence": [r1, r2, r3], "stalls": st["jobs"]["test_stall"].get("stalls"), "restarted": st["jobs"]["test_stall"]["attempts"] == 2}
    L.kill_tree(st["jobs"]["test_stall"]["pid"])
    # 4. the disk guard for walks: under the threshold, every walk stops after its next checkpoint, then the pipeline halts
    old = L.MIN_FREE_WALK_GB
    L.MIN_FREE_WALK_GB = 10 ** 6
    st = {"jobs": {}, "walks": {}, "halt": None, "git_mb_base": L.git_mb(), "git_checked": time.time()}
    L.guards(st, True)
    L.MIN_FREE_WALK_GB = old
    out["disk_guard"] = {"disk_stop_set": bool(st.get("disk_stop")), "halt": st.get("halt"), "passed": bool(st.get("disk_stop")) and "disk" in (st.get("halt") or "")}
    # 5. the status rendering with a GAN table (the TEST status.json), into a scratch file
    old_s, old_g = L.STATUS_F, L.ROOT
    L.STATUS_F = TEST / "STATUS_test.md"
    gs = ROOT / "runs" / "g1" / "gan" / "status.json"
    made = False
    if not gs.exists() and (TEST / "gan" / "status.json").exists():
        gs.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(TEST / "gan" / "status.json", gs)
        made = True
    L.status({"jobs": {}, "walks": {}, "free_gb": 1, "git_mb": 1, "git_mb_base": 1, "gpu_last": "test"}, "train")
    txt = L.STATUS_F.read_text(encoding="utf-8")
    if made:
        gs.unlink()
    L.STATUS_F = old_s
    out["status"] = {"has_gan_table": "## GAN runs" in txt and "| curious |" in txt, "excerpt": txt[txt.find("## GAN runs"):][:600]}
    passed = (out["fail_job"]["gives_up"] and out["killed_job"]["restarted_and_ok"] and out["stall"]["restarted"] and out["disk_guard"]["passed"]
              and out["status"]["has_gan_table"])
    record("supervisor", {"passed": bool(passed), **out})


if __name__ == "__main__":
    {"sampler": t_sampler, "train": t_train, "train_check": t_train_check, "fid": t_fid, "readouts": t_readouts, "supervisor": t_supervisor}[sys.argv[1]]()
