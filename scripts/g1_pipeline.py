"""The generation-1 supervisor on the PC: walks -> packages -> freeze -> verify -> GAN datasets -> throughput -> budget -> training -> readouts.

    .venv-sg\\Scripts\\python.exe scripts\\g1_pipeline.py run       # what the scheduled task runs (one instance at a time)
    .venv-sg\\Scripts\\python.exe scripts\\g1_pipeline.py status    # one tick's status, without acting
    .venv-sg\\Scripts\\python.exe scripts\\g1_pipeline.py stop      # stop the supervisor (walks and training keep running; a restart adopts them)

A thin loop: every tick it reloads scripts/g1_lib.py if that file changed, then calls g1_lib.tick(). All state is on disk
(runs/g1/pipeline_state.json, runs/g1/markers/, runs/g1/jobs/), so the supervisor can die and be restarted at any time: it skips
finished stages, adopts walks and jobs that are still running, and resumes the rest from their checkpoints.
It runs under a scheduled task (scripts/g1_task.ps1), at logon/startup and every 15 minutes; a second instance exits at once.
"""

from __future__ import annotations

import importlib
import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
G1 = ROOT / "runs" / "g1"
LOCK = G1 / "supervisor.pid"
STOP = G1 / "supervisor.stop"


def other_instance() -> int | None:
    import psutil

    if not LOCK.exists():
        return None
    try:
        pid = int(LOCK.read_text().split()[0])
    except (ValueError, IndexError):
        return None
    if pid == os.getpid() or not psutil.pid_exists(pid):
        return None
    try:
        cmd = " ".join(psutil.Process(pid).cmdline())
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None
    return pid if "g1_pipeline.py" in cmd and " run" in cmd else None


def log(msg: str) -> None:
    G1.mkdir(parents=True, exist_ok=True)
    with open(G1 / "supervisor.log", "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")


def run() -> None:
    G1.mkdir(parents=True, exist_ok=True)
    pid = other_instance()
    if pid:
        print(f"supervisor already running (pid {pid})")
        return
    LOCK.write_text(f"{os.getpid()} {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    STOP.unlink(missing_ok=True)
    log(f"supervisor start, pid {os.getpid()}, python {sys.executable}")
    lib_path = ROOT / "scripts" / "g1_lib.py"
    import g1_lib  # noqa: E402

    mtime = lib_path.stat().st_mtime
    errors = 0
    while True:
        if STOP.exists():
            log("stop file: supervisor exits (walks and jobs keep running)")
            break
        try:
            m = lib_path.stat().st_mtime
            if m != mtime:
                g1_lib = importlib.reload(g1_lib)
                mtime = m
                log("g1_lib reloaded")
            r = g1_lib.tick()
            errors = 0
            if r == "exit":
                log("pipeline finished or halted: supervisor exits")
                break
        except Exception:  # noqa: BLE001  a bug in a tick must not kill the walks' supervisor; it is logged and retried
            errors += 1
            log(f"tick error {errors}:\n{traceback.format_exc()}")
            if errors >= 20:
                log("20 tick errors in a row: supervisor exits")
                break
        time.sleep(getattr(g1_lib, "TICK_S", 60))
    LOCK.unlink(missing_ok=True)


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "run":
        run()
    elif cmd == "status":
        import g1_lib

        g1_lib.tick(act=False)
        print((G1 / "STATUS.md").read_text(encoding="utf-8"))
    elif cmd == "stop":
        STOP.write_text(time.strftime("%Y-%m-%d %H:%M:%S"))
        print("stop requested")


if __name__ == "__main__":
    main()
