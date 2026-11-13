"""The logic of the generation-1 supervisor (scripts/g1_pipeline.py reloads this file whenever it changes). One call of tick() looks at
the state on disk, acts (starts, restarts, stops processes; starts the next stage), and rewrites runs/g1/STATUS.md.

Stages, in order, each finished by a marker in runs/g1/markers/<stage>.done:
  walks          brief v2 section 7: curious w000 and Null w000 side by side; a condition gets w001, w002, ... only while its pooled
                 unique tiles (start tiles included, as the package counts them) are below N when its last walk ends. Every walk runs
                 to its own end (linger, time or capped). Configs as committed (configs/gen1/*.yaml), CPU, 3 threads (the Mac's setting).
  packages       scripts/g1_package.py build curious, build null (the handoff), each with its render check
  freeze         scripts/g1_verify.py paths; manifests copied to notes/gen1/packages/; commit; tag g1-paths
  walk_readouts  analysis/gen1/readouts.py gen1 (tables and figures for notes/gen1_report.md); a failure here is logged, not fatal
  datasets       gen/g1_gan.py datasets (verify as GAN input, weights, tau, ESS, zips, metadata, contact sheets)
  throughput     gen/g1_gan.py throughput (both runs concurrently, >= 20 kimg after warm-up; custom ops status)
  budget         gen/g1_gan.py budget (kimg from the measured rates, <= 60 h; written to expectations.md and STATE.md; tag g1-start)
  train          gen/g1_gan.py train curious | null, concurrently; restarted from the latest snapshot at most 3 times per run
  fid            gen/g1_gan.py fid (fid50k_full on the kept snapshots: a training-health signal only); not fatal
  gan_readouts   gen/g1_gan.py readouts (samples, memorisation, diversity, colour and texture statistics, film assets)
  final          the final STATUS.md
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]
G1 = ROOT / "runs" / "g1"
MARK, JOBS, LOGS = G1 / "markers", G1 / "jobs", G1 / "logs"
STATE_F, STATUS_F, EVENTS_F, GPU_F = G1 / "pipeline_state.json", G1 / "STATUS.md", G1 / "events.log", G1 / "gpu_log.csv"
WALK_RUNS = ROOT / "runs" / "gen1"
PY_WALK = str(ROOT / ".venv" / "Scripts" / "python.exe")
PY_SG = str(ROOT / ".venv-sg" / "Scripts" / "python.exe")
SG_BAT = str(ROOT / "scripts" / "sg.bat")

TICK_S = 60
N = 10_000
CONDS = ("curious", "null")
STAGES = ("walks", "packages", "freeze", "walk_readouts", "datasets", "throughput", "budget", "train", "fid", "gan_readouts", "final")
MAX_RESTARTS = 3
WALK_STALL_S = 45 * 60          # a walk prints every 100 steps (~1 min); 45 min of silence is a stall
JOB_STALL_S = {"train": 40 * 60}
MIN_FREE_WALK_GB = 30
MIN_FREE_GAN_GB = 20            # notes/brief_gan_g1.md: below 20 GB, stop gracefully after the next snapshot
MAX_GIT_GROWTH_MB = 1000
GPU_EVERY_S = 600
WALK_ENV = {"OMP_NUM_THREADS": "3", "MKL_NUM_THREADS": "3", "CUDA_VISIBLE_DEVICES": "-1", "PYTHONUNBUFFERED": "1", "PYTHONFAULTHANDLER": "1"}
T1977 = date(1977, 1, 1).toordinal()
EPOCH = date(1970, 1, 1).toordinal()

FLAGS = 0x00000200 | 0x08000000  # CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
BREAKAWAY = 0x01000000           # CREATE_BREAKAWAY_FROM_JOB: survive the scheduled task's job if the supervisor is ended


# -- small helpers ----------------------------------------------------------------------------------------------------------------
def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def event(msg: str) -> None:
    G1.mkdir(parents=True, exist_ok=True)
    with open(EVENTS_F, "a", encoding="utf-8") as f:
        f.write(f"{now()} {msg}\n")


def load_state() -> dict:
    if STATE_F.exists():
        return json.loads(STATE_F.read_text(encoding="utf-8"))
    return {"walks": {}, "jobs": {}, "halt": None, "disk_stop": None, "created": now()}


def save_state(st: dict) -> None:
    tmp = STATE_F.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1, default=str), encoding="utf-8")
    os.replace(tmp, STATE_F)


def marked(stage: str) -> bool:
    return (MARK / f"{stage}.done").exists()


def mark(stage: str, info: dict | None = None) -> None:
    MARK.mkdir(parents=True, exist_ok=True)
    (MARK / f"{stage}.done").write_text(json.dumps({"time": now(), **(info or {})}, default=str))
    event(f"stage {stage} done")


def free_gb() -> float:
    return shutil.disk_usage(ROOT).free / 1e9


def git_mb() -> float:
    tot = 0
    for dp, _, fs in os.walk(ROOT / ".git" / "objects"):
        for f in fs:
            try:
                tot += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return tot / 1e6


def alive(pid: int | None, needle: str | None = None) -> bool:
    if not pid or not psutil.pid_exists(int(pid)):
        return False
    try:
        p = psutil.Process(int(pid))
        if p.status() == psutil.STATUS_ZOMBIE:
            return False
        return needle is None or needle in " ".join(p.cmdline())
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def kill_tree(pid: int) -> None:
    try:
        p = psutil.Process(int(pid))
    except psutil.NoSuchProcess:
        return
    procs = p.children(recursive=True) + [p]
    for q in procs:
        try:
            q.kill()
        except psutil.NoSuchProcess:
            pass
    psutil.wait_procs(procs, timeout=30)


def spawn(name: str, cmd: list[str], log: Path, env_extra: dict | None = None, python: str = PY_WALK) -> int:
    """Start a job through scripts/g1_job.py (it records the exit code in runs/g1/jobs/<name>.exit). Detached from the supervisor."""
    env = {**os.environ, **(env_extra or {})}
    argv = [python, str(ROOT / "scripts" / "g1_job.py"), name, str(log), "--", *cmd]
    (JOBS / f"{name}.exit").unlink(missing_ok=True)
    JOBS.mkdir(parents=True, exist_ok=True)
    kw = dict(cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
    try:
        p = subprocess.Popen(argv, creationflags=FLAGS | BREAKAWAY, **kw)
    except OSError:
        p = subprocess.Popen(argv, creationflags=FLAGS, **kw)
    return p.pid


def job_exit(name: str) -> dict | None:
    f = JOBS / f"{name}.exit"
    return json.loads(f.read_text()) if f.exists() else None


def tail(p: Path, n: int = 12) -> str:
    try:
        return "\n".join(p.read_text(encoding="utf-8", errors="replace").splitlines()[-n:])
    except OSError:
        return ""


def run_job(st: dict, name: str, cmd: list[str], log: Path, *, python: str = PY_WALK, env: dict | None = None, attempts: int = 3,
            act: bool = True, stall_s: float | None = None) -> str:
    """A job's life over ticks: 'running', 'ok', 'failed' (attempts used up). Starts it if it isn't running and hasn't succeeded."""
    j = st["jobs"].setdefault(name, {"attempts": 0, "pid": None})
    if j.get("result") == "ok":
        return "ok"
    if alive(j.get("pid"), "g1_job.py"):
        if stall_s and log.exists() and time.time() - log.stat().st_mtime > stall_s and act:
            event(f"job {name}: no output for {stall_s / 60:.0f} min; killed")
            kill_tree(j["pid"])
            j["stalls"] = j.get("stalls", 0) + 1
        return "running"
    ex = job_exit(name)
    if ex is not None and j.get("started") and ex["ended"] >= j["started"]:
        if ex["rc"] == 0:
            j["result"] = "ok"
            j["seconds"] = ex["seconds"]
            return "ok"
        if not j.get("logged_rc_" + j["started"]):
            event(f"job {name} failed (exit {ex['rc']}, attempt {j['attempts']}):\n{tail(log)}")
            j["logged_rc_" + j["started"]] = True
    elif j.get("started") and not j.get("noted_dead_" + j["started"]):
        event(f"job {name} ended without an exit record (killed?), attempt {j['attempts']}")
        j["noted_dead_" + j["started"]] = True
    if j["attempts"] >= attempts:
        j["result"] = "failed"
        return "failed"
    if not act:
        return "waiting"
    j["attempts"] += 1
    j["started"] = now()
    j["pid"] = spawn(name, cmd, log, env, python)
    event(f"job {name} started (attempt {j['attempts']}, pid {j['pid']})")
    return "running"


# -- walks ---------------------------------------------------------------------------------------------------------------------------
def walk_dir(cond: str, k: int) -> Path:
    return WALK_RUNS / cond / f"w{k:03d}"


def walk_log(cond: str, k: int) -> Path:
    return WALK_RUNS / "logs" / f"{cond}_w{k:03d}.log"


def pooled(cond: str) -> int:
    """Unique tiles (cell, acquisition) of a condition's finished walks, start tiles included (as scripts/g1_package.py counts)."""
    import pandas as pd

    keys: set[int] = set()
    for d in sorted((WALK_RUNS / cond).glob("w[0-9][0-9][0-9]")):
        if (d / "walk.json").exists():
            w = json.loads((d / "walk.json").read_text())
            keys.add(int(w["start_idx"]))  # image_key(start, rank 0) = the cell's idx
            keys.update(pd.read_parquet(d / "steps.parquet", columns=["image_key"]).image_key.astype("int64").tolist())
    return len(keys)


LINE = re.compile(r"\[w(\d+)\] step (\d+)\s+(\d+)s\s+uniq (\d+)\s+clock (\d{4}-\d\d-\d\d)")
LINGER = re.compile(r"\[w\d+\] step (\d+): the clock reached .*? it may linger (\d+) steps")


def walk_progress(cond: str, k: int) -> dict:
    log = walk_log(cond, k)
    out = {"step": 0, "uniq": 0, "clock": None, "linger_end": None}
    if not log.exists():
        return out
    txt = log.read_text(encoding="utf-8", errors="replace")
    m = LINE.findall(txt)
    if m:
        _, s, _, u, c = m[-1]
        out.update(step=int(s), uniq=int(u), clock=c)
    lg = LINGER.findall(txt)
    if lg:
        out["linger_end"] = int(lg[-1][0]) + int(lg[-1][1])
    return out


def eta(w: dict, prog: dict, start_clock: str | None) -> str:
    h = w.get("hist", [])
    if len(h) < 2 or not prog["clock"]:
        return "?"
    t0, s0, c0 = h[max(0, len(h) - 30)]
    t1, s1, c1 = h[-1]
    if s1 <= s0 or t1 <= t0:
        return "?"
    sps = (s1 - s0) / (t1 - t0)
    dps = (c1 - c0) / (s1 - s0)
    if prog["linger_end"]:
        left = prog["linger_end"] - s1
        how = "to the end of lingering"
    elif dps > 0 and start_clock:
        to77 = max(T1977 - c1, 0) / dps
        sc = date.fromisoformat(start_clock).toordinal()
        linger = (s1 + to77) / max((T1977 - sc) / 365.25, 1e-6)
        left = to77 + linger
        how = f"projected: 1977 at ~step {s1 + to77:,.0f}, then ~{linger:,.0f} lingering"
    else:
        left = 40000 - s1
        how = "to the guard"
    left = min(left, 40000 - s1)
    return f"~{left / sps / 3600:.1f} h ({left:,.0f} steps, {how}; {sps * 60:.0f} steps/min, {dps:.2f} clock days/step)"


def stage_walks(st: dict, act: bool) -> None:
    W = st["walks"]
    started_one = False
    done_conds = 0
    for cond in CONDS:
        ws = W.setdefault(cond, {})
        k = max((int(x) for x in ws), default=0)
        w = ws.setdefault(str(k), {"restarts": 0, "pid": None, "status": "new", "hist": []})
        d = walk_dir(cond, k)
        if (d / "walk.json").exists():
            if w["status"] != "done":
                w["status"] = "done"
                wj = json.loads((d / "walk.json").read_text())
                w["walk"] = {x: wj.get(x) for x in ("steps", "end_reason", "end_clock", "unique_tiles", "linger_entry_step", "linger_steps", "seconds")}
                w["pooled_after"] = pooled(cond)
                event(f"walk {cond} w{k:03d} ended: {w['walk']}; pooled unique tiles {w['pooled_after']:,}")
            if w["pooled_after"] >= N:
                done_conds += 1
                continue
            if not act or started_one or st.get("disk_stop"):
                continue
            k += 1
            if k >= 500:
                st["halt"] = f"{cond}: the start list (500 cells) ran out before N"
                return
            ws[str(k)] = {"restarts": 0, "pid": None, "status": "new", "hist": []}
            w, d = ws[str(k)], walk_dir(cond, k)
            event(f"walk {cond}: pooled {pooled(cond):,} < N = {N:,}: a new wanderer, w{k:03d} (start cell {k})")
        # running?
        if alive(w.get("pid"), "g1_job.py"):
            prog = walk_progress(cond, k)
            if prog["clock"] and (not w["hist"] or w["hist"][-1][1] != prog["step"]):
                w["hist"].append([time.time(), prog["step"], date.fromisoformat(prog["clock"]).toordinal()])
                w["hist"] = w["hist"][-200:]
            log = walk_log(cond, k)
            if act and log.exists() and time.time() - log.stat().st_mtime > WALK_STALL_S:
                event(f"walk {cond} w{k:03d}: no log output for {WALK_STALL_S / 60:.0f} min (stall); killed\n{tail(log)}")
                kill_tree(w["pid"])
                w["stalls"] = w.get("stalls", 0) + 1
            if st.get("disk_stop") and act:
                r = d / "resume.pt"
                m0 = st["disk_stop"]["resume_mtime"].get(f"{cond}_{k}", 0)
                if r.exists() and r.stat().st_mtime > m0:
                    event(f"walk {cond} w{k:03d}: stopped after its checkpoint (disk)")
                    kill_tree(w["pid"])
                    w["status"] = "stopped_disk"
            continue
        if st.get("disk_stop") or not act or started_one:
            continue
        # not running and not finished: first start, or a crash
        if w["status"] in ("running",):
            w["restarts"] += 1
            ex = job_exit(f"walk_{cond}_w{k:03d}")
            event(f"walk {cond} w{k:03d} died (exit {ex['rc'] if ex else '?'}; restart {w['restarts']} of {MAX_RESTARTS}):\n{tail(walk_log(cond, k), 25)}")
            if w["restarts"] > MAX_RESTARTS:
                w["status"] = "failed"
                st["halt"] = (f"walk {cond} w{k:03d} failed {MAX_RESTARTS} resumes; the cause needs fixing, then the walk reruns from scratch "
                              f"(run instruction). Log: {walk_log(cond, k)}")
                return
        resume = (d / "resume.pt").exists()
        cmd = [PY_WALK, "-m", "agent.walk", f"configs/gen1/{cond}.yaml", "--walk", str(k), "--phase", "gen1"] + (["--resume"] if resume else [])
        walk_log(cond, k).parent.mkdir(parents=True, exist_ok=True)
        w["pid"] = spawn(f"walk_{cond}_w{k:03d}", cmd, walk_log(cond, k), WALK_ENV)
        w["status"] = "running"
        w.setdefault("starts", []).append({"time": now(), "resume": resume})
        started_one = True
        event(f"walk {cond} w{k:03d} {'resumed from its checkpoint' if resume else 'started'} (pid {w['pid']})")
    if done_conds == len(CONDS):
        mark("walks", {c: {"walks": len(W[c]), "pooled": max(v.get("pooled_after", 0) for v in W[c].values())} for c in CONDS})


def any_walk_running(st: dict) -> bool:
    return any(alive(w.get("pid"), "g1_job.py") for ws in st["walks"].values() for w in ws.values())


# -- housekeeping ----------------------------------------------------------------------------------------------------------------
def cache_cap(st: dict, act: bool) -> None:
    need = not marked("packages")
    pid = st.get("cache_cap_pid")
    if need and act and not alive(pid, "cache_cap.py"):
        cap = st.setdefault("cache_cap_gb", int(min(150, 0.35 * free_gb())))
        p = subprocess.Popen([PY_WALK, str(ROOT / "data" / "cache_cap.py"), "--cap-gb", str(cap), "--every", "60"], cwd=ROOT,
                             stdout=open(LOGS / "cache_cap.log", "a"), stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, creationflags=FLAGS)
        st["cache_cap_pid"] = p.pid
        event(f"cache cap started: {cap} GB, LRU (data/cache_cap.py), pid {p.pid}")
    elif not need and alive(pid, "cache_cap.py") and act:
        kill_tree(pid)


def gpu_log(st: dict) -> None:
    if time.time() - st.get("gpu_logged", 0) < GPU_EVERY_S:
        return
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=timestamp,temperature.gpu,clocks.sm,clocks.max.sm,utilization.gpu,memory.used,power.draw,clocks_throttle_reasons.active",
                            "--format=csv,noheader"], capture_output=True, text=True, timeout=60, creationflags=0x08000000)
        new = not GPU_F.exists()
        with open(GPU_F, "a") as f:
            if new:
                f.write("timestamp,temp_c,sm_mhz,sm_max_mhz,util_pct,mem_used,power_w,throttle\n")
            f.write(r.stdout.strip() + "\n")
        st["gpu_last"] = r.stdout.strip()
    except Exception as e:  # noqa: BLE001
        st["gpu_last"] = f"nvidia-smi failed: {e!r}"
    st["gpu_logged"] = time.time()


def guards(st: dict, act: bool) -> None:
    fg = free_gb()
    st["free_gb"] = round(fg, 1)
    base = st.setdefault("git_mb_base", round(git_mb(), 1))
    if time.time() - st.get("git_checked", 0) > 600:
        st["git_mb"] = round(git_mb(), 1)
        st["git_checked"] = time.time()
        if st["git_mb"] - base > MAX_GIT_GROWTH_MB and not st.get("halt"):
            st["halt"] = f".git/objects grew from {base} to {st['git_mb']} MB: stopped (an earlier session filled the disk this way)"
            event(st["halt"])
    if not marked("walks") and fg < MIN_FREE_WALK_GB and not st.get("disk_stop") and act:
        st["disk_stop"] = {"time": now(), "free_gb": round(fg, 1),
                           "resume_mtime": {f"{c}_{k}": (walk_dir(c, int(k)) / "resume.pt").stat().st_mtime if (walk_dir(c, int(k)) / "resume.pt").exists() else 0
                                            for c, ws in st["walks"].items() for k in ws}}
        event(f"disk: {fg:.1f} GB free (< {MIN_FREE_WALK_GB}): every walk stops after its next checkpoint")
    if st.get("disk_stop") and not any_walk_running(st) and not st.get("halt"):
        st["halt"] = f"disk: under {MIN_FREE_WALK_GB} GB free at {st['disk_stop']['time']}; walks stopped after their checkpoints (resume.pt kept)"


# -- stages after the walks -----------------------------------------------------------------------------------------------------
def stage_packages(st: dict, act: bool) -> None:
    for cond in CONDS:
        r = run_job(st, f"package_{cond}", [PY_WALK, "scripts/g1_package.py", "build", cond], LOGS / f"package_{cond}.log", act=act)
        if r == "failed":
            st["halt"] = f"package {cond} failed 3 times; see {LOGS / f'package_{cond}.log'}"
            return
        if r != "ok":
            return  # one at a time
    mark("packages")


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, creationflags=0x08000000)


def commit(paths: list[str], msg: str) -> str:
    git("add", "-f", *paths)
    r = git("commit", "-m", msg + "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>", "--", *paths)
    return (r.stdout + r.stderr).strip()[-400:]


def stage_freeze(st: dict, act: bool) -> None:
    r = run_job(st, "verify_paths", [PY_WALK, "scripts/g1_verify.py", "paths"], LOGS / "verify_paths.log", attempts=1, act=act)
    if r == "running" or r == "waiting":
        return
    res = json.loads((G1 / "verify_paths.json").read_text()) if (G1 / "verify_paths.json").exists() else {"passed": False}
    if r == "failed" or not res.get("passed"):
        n = st.setdefault("package_rebuilds", 0)
        if n >= 2:
            st["halt"] = f"the packages failed verification after {n} rebuilds: {res}"
            return
        st["package_rebuilds"] = n + 1
        event(f"packages failed verification ({res}); rebuilt from the walk logs (rebuild {n + 1})")
        (MARK / "packages.done").unlink(missing_ok=True)
        for k in ("package_curious", "package_null", "verify_paths"):
            st["jobs"].pop(k, None)
        return
    if not act:
        return
    dst = ROOT / "notes" / "gen1" / "packages"
    dst.mkdir(parents=True, exist_ok=True)
    for cond in CONDS:
        shutil.copyfile(ROOT / "paths" / "g1" / cond / "manifest.json", dst / f"{cond}_manifest.json")
    shutil.copyfile(G1 / "verify_paths.json", dst / "verify_paths.json")
    out = commit(["notes/gen1/packages"], "generation 1: the two path packages frozen (manifests, checksums, render check); tag g1-paths")
    t = git("tag", "g1-paths")
    event(f"freeze: {out}; tag g1-paths: {(t.stdout + t.stderr).strip() or 'ok'}")
    mark("freeze")


def stage_simple(st: dict, act: bool, stage: str, cmd: list[str], *, python: str = PY_SG, fatal: bool = True, attempts: int = 2,
                 sg: bool = False) -> None:
    full = ["cmd", "/c", SG_BAT, *cmd] if sg else [python, *cmd]
    r = run_job(st, stage, full, LOGS / f"{stage}.log", python=PY_WALK, attempts=attempts, act=act)
    if r == "ok":
        mark(stage)
    elif r == "failed":
        if fatal:
            ex = job_exit(stage)
            if stage == "datasets" and ex and ex["rc"] == 3:
                st["halt"] = "ESS = 0.5 N can't be reached for the curious package: neither GAN is trained (runs/g1/gan/ess.json)"
            else:
                st["halt"] = f"stage {stage} failed {attempts} times; see {LOGS / f'{stage}.log'}"
        else:
            event(f"stage {stage} failed (not fatal; the pipeline goes on)")
            mark(stage, {"failed": True})


def stage_train(st: dict, act: bool) -> None:
    res = {}
    for cond in CONDS:
        fin = ROOT / "runs" / "g1" / "gan" / cond / "FINISHED"
        if fin.exists():
            res[cond] = "ok"
            continue
        if fin.with_name("STOPPED_DISK").exists():
            res[cond] = "stopped"
            continue
        r = run_job(st, f"train_{cond}", ["cmd", "/c", SG_BAT, "gen/g1_gan.py", "train", cond], LOGS / f"train_{cond}.log",
                    attempts=MAX_RESTARTS + 1, act=act, stall_s=JOB_STALL_S["train"])
        res[cond] = r
        if r == "failed" and not st.get(f"train_{cond}_failed_logged"):
            st[f"train_{cond}_failed_logged"] = True
            event(f"GAN run {cond} failed for good after {MAX_RESTARTS} restarts; the other run carries on")
    # the disk: below 20 GB, every run stops after its next snapshot (gen/g1_gan.py polls the STOP file)
    if free_gb() < MIN_FREE_GAN_GB and act:
        for cond in CONDS:
            s = ROOT / "runs" / "g1" / "gan" / cond / "STOP"
            if not s.exists() and (s.parent).exists():
                s.write_text(now())
                event(f"disk under {MIN_FREE_GAN_GB} GB: {cond} stops after its next snapshot")
    if all(v in ("ok", "failed", "stopped") for v in res.values()):
        mark("train", res)
        if any(v != "ok" for v in res.values()):
            event(f"training ended: {res}")


# -- status ----------------------------------------------------------------------------------------------------------------------
def status(st: dict, stage: str) -> None:
    L = [f"# Generation 1 on the PC: STATUS", "", f"Last update: {now()} (the supervisor rewrites this every minute; history in runs/g1/events.log)", ""]
    if st.get("halt"):
        L += ["## HALTED", "", st["halt"], ""]
    L += [f"**Stage:** {stage}  ", f"**Stages done:** {', '.join(s for s in STAGES if marked(s)) or 'none'}  ",
          f"**Disk free:** {st.get('free_gb')} GB on E: (walks stop under {MIN_FREE_WALK_GB} GB, training under {MIN_FREE_GAN_GB} GB)  ",
          f"**.git/objects:** {st.get('git_mb')} MB (start {st.get('git_mb_base')} MB)  ",
          f"**GPU:** {st.get('gpu_last', '?')} (timestamp, temp C, SM MHz, max, util %, mem, W, throttle)  ",
          f"**World:** rebuilt from git and checked against the Mac (runs/g1/world_check.md)", ""]
    L += ["## Walks (q = 0.10, lingering from 1977-01-01, T_end 1977-12-20, guard 40,000; CPU, 3 threads)", "",
          "| walk | status | steps | clock | unique tiles | restarts | ETA | end |", "|---|---|---|---|---|---|---|---|"]
    for cond, ws in st["walks"].items():
        for k, w in sorted(ws.items(), key=lambda x: int(x[0])):
            p = walk_progress(cond, int(k))
            sc = None
            mj = walk_dir(cond, int(k)) / "meta.json"
            if mj.exists():
                try:
                    sc = json.loads(mj.read_text()).get("clock", {}).get("start_clock")
                except (json.JSONDecodeError, OSError):
                    pass
            fin = w.get("walk") or {}
            L.append(f"| {cond} w{int(k):03d} | {w['status']} | {fin.get('steps', p['step']):,} | {fin.get('end_clock', p['clock'])} | "
                     f"{fin.get('unique_tiles', p['uniq']):,} | {w['restarts']} | {'-' if fin else eta(w, p, sc)} | "
                     f"{fin.get('end_reason', '')}{' (pooled ' + format(w['pooled_after'], ',') + ')' if 'pooled_after' in w else ''} |")
    L.append("")
    gs = ROOT / "runs" / "g1" / "gan" / "status.json"
    if gs.exists():
        try:
            g = json.loads(gs.read_text())
            L += ["## GAN runs", "", "| run | kimg | target | sec/kimg | ETA | augment p | health (FID) | restarts | last snapshot |", "|---|---|---|---|---|---|---|---|---|"]
            for cond, v in g.get("runs", {}).items():
                L.append(f"| {cond} | {v.get('kimg')} | {v.get('target')} | {v.get('sec_per_kimg')} | {v.get('eta')} | {v.get('augment_p')} | "
                         f"{v.get('fid', '-')} | {st['jobs'].get('train_' + cond, {}).get('attempts', 1) - 1 if st['jobs'].get('train_' + cond) else 0} | {v.get('snapshot')} |")
            L += ["", f"Latest fakes: runs/g1/gan/<run>/latest_fakes.png. {g.get('note', '')}", ""]
        except (json.JSONDecodeError, OSError):
            pass
    jobs = [(k, v) for k, v in st["jobs"].items() if not k.startswith("walk_")]
    if jobs:
        L += ["## Jobs", "", "| job | result | attempts | seconds |", "|---|---|---|---|"]
        L += [f"| {k} | {v.get('result', 'running' if alive(v.get('pid'), 'g1_job.py') else '-')} | {v.get('attempts')} | {v.get('seconds', '')} |" for k, v in jobs]
        L.append("")
    ev = EVENTS_F.read_text(encoding="utf-8", errors="replace").splitlines()[-12:] if EVENTS_F.exists() else []
    L += ["## Last events", "", "```", *ev, "```", ""]
    tmp = STATUS_F.with_suffix(".tmp")
    tmp.write_text("\n".join(L), encoding="utf-8")
    os.replace(tmp, STATUS_F)


# -- the tick --------------------------------------------------------------------------------------------------------------------
def tick(act: bool = True) -> str | None:
    for d in (MARK, JOBS, LOGS):
        d.mkdir(parents=True, exist_ok=True)
    st = load_state()
    stage = next((s for s in STAGES if not marked(s)), "done")
    if act and not (G1 / "gpu_probe.json").exists():  # once: can the GAN side see the GPU from the scheduled task's session?
        r = subprocess.run([PY_SG, "-c", "import torch, json, os; print(json.dumps({'cuda': torch.cuda.is_available(), 'torch': torch.__version__, "
                                         "'device': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None, 'user': os.environ.get('USERNAME'), "
                                         "'session': os.environ.get('SESSIONNAME')}))"], capture_output=True, text=True, timeout=300, creationflags=0x08000000)
        (G1 / "gpu_probe.json").write_text(r.stdout.strip() or json.dumps({"error": r.stderr[-500:]}))
        event(f"GPU probe from the supervisor's session: {r.stdout.strip() or r.stderr[-300:]}")
    if not st.get("halt"):
        guards(st, act)
        if act:
            cache_cap(st, act)
            gpu_log(st)
    if not st.get("halt") and act:
        if stage == "walks":
            stage_walks(st, act)
        elif stage == "packages":
            stage_packages(st, act)
        elif stage == "freeze":
            stage_freeze(st, act)
        elif stage == "walk_readouts":
            stage_simple(st, act, "walk_readouts", ["analysis/gen1/readouts.py", "gen1"], python=PY_WALK, fatal=False)
        elif stage == "datasets":
            stage_simple(st, act, "datasets", ["gen/g1_gan.py", "datasets"], attempts=2)
        elif stage == "throughput":
            stage_simple(st, act, "throughput", ["gen/g1_gan.py", "throughput"], sg=True, attempts=2)
        elif stage == "budget":
            stage_simple(st, act, "budget", ["gen/g1_gan.py", "budget"], attempts=1)
        elif stage == "train":
            stage_train(st, act)
        elif stage == "fid":
            stage_simple(st, act, "fid", ["gen/g1_gan.py", "fid"], sg=True, fatal=False, attempts=2)
        elif stage == "gan_readouts":
            stage_simple(st, act, "gan_readouts", ["gen/g1_gan.py", "readouts"], sg=True, fatal=False, attempts=2)
        elif stage == "final":
            mark("final")
        stage = next((s for s in STAGES if not marked(s)), "done")
    if st.get("halt") and not st.get("halt_logged"):
        event(f"HALT: {st['halt']}")
        st["halt_logged"] = True
    if act:
        save_state(st)
    status(st, stage)
    if stage == "done" or (st.get("halt") and not any_walk_running(st)):
        return "exit"
    return None
