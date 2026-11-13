"""Runs one pipeline job and records how it ended (scripts/g1_pipeline.py): runs/g1/jobs/<name>.exit holds the exit code.

    python scripts/g1_job.py <name> <log> -- <command ...>

The supervisor can't read the exit code of a process it adopted after a restart, so every job leaves its own.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOBS = ROOT / "runs" / "g1" / "jobs"


def main() -> None:
    name, log = sys.argv[1], Path(sys.argv[2])
    cmd = sys.argv[sys.argv.index("--") + 1 :]
    JOBS.mkdir(parents=True, exist_ok=True)
    (JOBS / f"{name}.exit").unlink(missing_ok=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with open(log, "ab") as f:
        f.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} job {name}: {' '.join(cmd)}\n".encode())
        f.flush()
        rc = subprocess.call(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
        f.write(f"=== {time.strftime('%Y-%m-%d %H:%M:%S')} job {name} exit {rc} after {time.time() - t0:.0f} s\n".encode())
    (JOBS / f"{name}.exit").write_text(json.dumps({"rc": rc, "seconds": round(time.time() - t0, 1), "ended": time.strftime("%Y-%m-%d %H:%M:%S")}))
    sys.exit(rc)


if __name__ == "__main__":
    main()
