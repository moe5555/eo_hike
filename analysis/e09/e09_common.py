"""Experiment 09 (notes/09_compass/brief_e09_compass.md): paths and the e08 walks used offline in Stage 0."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "analysis" / "e08"), str(ROOT / "analysis" / "h0111"), str(ROOT / "analysis")]

OUT = ROOT / "notes" / "09_compass" / "results"
CACHE = ROOT / "data" / "sheet"  # git-ignored: intermediate files that rebuild in seconds
RUNS = ROOT / "runs"
R_MIN = 15.0  # the Reference's radius_km
YOUNG = 150
# e08 walks for Stage 0.3, eight seeds each; the Reference's seeds 0-3 are the h0111 walks
OLD = {"Reference": ("h0111_reference", "e08_reference"), "progress only": "e08_progress_only", "k_nn 3": "e08_knn_3"}


def old_runs() -> list[tuple[str, int, str]]:
    out = []
    for g, stems in OLD.items():
        for sd in range(8):
            for stem in (stems,) if isinstance(stems, str) else stems:
                if (RUNS / f"{stem}_s{sd}" / "final.pt").exists():
                    out.append((g, sd, f"{stem}_s{sd}"))
                    break
    return out
