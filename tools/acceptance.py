"""Acceptance checks from the brief, run against a config whose ingest/embed/index exist.

    uv run python tools/acceptance.py --config configs/debug.yaml

1. Two hikes with the same config and seed -> byte-identical log.jsonl.
2. Changing only the seed -> a visibly different walk (chip overlap reported).
3. Novelty declines over a run (first-third vs last-third of the running mean,
   and the slope of a least-squares line through the per-step novelty).
Also reports sibling hops (consecutive chips from the same group), random-jump
rate, stop reasons and wall time, and diagnoses degenerate behaviour.
"""

from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np
import typer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hiker.config import load_config  # noqa: E402
from hiker.hike import run_hike  # noqa: E402
from hiker.ingest import load_manifest  # noqa: E402
from hiker.io import read_jsonl  # noqa: E402

app = typer.Typer(add_completion=False)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def analyse(run_dir: Path, group_of: dict[str, str]) -> dict:
    log = read_jsonl(run_dir / "log.jsonl")
    out = {}
    for a in sorted({r["agent_id"] for r in log}):
        rows = [r for r in log if r["agent_id"] == a]
        nov = np.array([r["novelty"] for r in rows if r["novelty"] is not None])
        n = len(nov)
        third = max(1, n // 3)
        slope = float(np.polyfit(np.arange(n), nov, 1)[0]) if n > 2 else float("nan")
        sib = sum(1 for p, q in zip(rows, rows[1:]) if group_of.get(p["chip_id"]) == group_of.get(q["chip_id"]))
        out[a] = {
            "steps": n,
            "first_third_mean": float(nov[:third].mean()) if n else float("nan"),
            "last_third_mean": float(nov[-third:].mean()) if n else float("nan"),
            "slope_per_step": slope,
            "novelty_min": float(nov.min()) if n else float("nan"),
            "novelty_max": float(nov.max()) if n else float("nan"),
            "novelty_std": float(nov.std()) if n else float("nan"),
            "random_jumps": sum(1 for r in rows if r["was_random_jump"]),
            "sibling_hops": sib,
            "rank1_frac": float(np.mean([r["rank_among_candidates"] == 1 for r in rows if r["rank_among_candidates"]])),
            "mean_n_candidates": float(np.mean([r["n_candidates"] for r in rows[1:]])) if n else float("nan"),
            "chips": [r["chip_id"] for r in rows],
        }
    return out


@app.command()
def main(config: Path = typer.Option(..., "--config", "-c"), set_: Optional[list[str]] = typer.Option(None, "--set")) -> None:
    cfg = load_config(config, set_ or [])
    manifest = load_manifest(cfg)
    group_of = dict(zip(manifest["chip_id"], manifest["group_id"].astype(str)))

    t0 = time.time()
    r1 = run_hike(cfg, tag="acc1")
    t1 = time.time() - t0
    r2 = run_hike(cfg, tag="acc2")
    cfg_b = load_config(config, (set_ or []) + [f"agents.seed={int(cfg['agents']['seed']) + 1}"])
    r3 = run_hike(cfg_b, tag="acc-seedB")

    print("\n=== 1. reproducibility ===")
    same = sha(r1 / "log.jsonl") == sha(r2 / "log.jsonl")
    print(f"same seed, byte-identical log.jsonl: {same}   ({r1.name} vs {r2.name})")

    a1, a3 = analyse(r1, group_of), analyse(r3, group_of)
    print("\n=== 2. seed sensitivity ===")
    for a in a1:
        s1, s3 = set(a1[a]["chips"]), set(a3[a]["chips"])
        print(f"agent {a}: seed {cfg['agents']['seed']} vs {cfg_b['agents']['seed']}: "
              f"{len(s1 & s3)} shared chips of {len(s1)} / {len(s3)}; same start: {a1[a]['chips'][0] == a3[a]['chips'][0]}")

    print("\n=== 3. novelty trend and behaviour (seed run 1) ===")
    for a, d in a1.items():
        print(f"agent {a}: steps={d['steps']} first-third mean={d['first_third_mean']:.4f} last-third mean={d['last_third_mean']:.4f} "
              f"slope={d['slope_per_step']:+.5f}/step  min/max/std={d['novelty_min']:.3f}/{d['novelty_max']:.3f}/{d['novelty_std']:.3f}")
        print(f"         random jumps={d['random_jumps']} sibling hops={d['sibling_hops']} rank-1 choices={d['rank1_frac']:.0%} "
              f"mean candidates={d['mean_n_candidates']:.1f}")
        flags = []
        if d["novelty_std"] < 0.005:
            flags.append("DEGENERATE: all novelties nearly identical")
        if d["last_third_mean"] >= d["first_third_mean"]:
            flags.append("novelty did not decline")
        if d["sibling_hops"] > 0.5 * max(1, d["steps"]):
            flags.append("mostly hopping between seasonal siblings")
        if d["mean_n_candidates"] < 5:
            flags.append("candidate set nearly empty")
        print("         " + ("; ".join(flags) if flags else "no degeneracy flags"))
    print(f"\nwall time for one hike (all agents): {t1:.1f} s")


if __name__ == "__main__":
    app()
