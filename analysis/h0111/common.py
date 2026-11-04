"""Round h0111 (notes/07_film_arc/brief.md): shared loading and walk statistics, same definitions as analysis/h2910_compare.py."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "notes" / "07_film_arc" / "results"
RUNS = ROOT / "runs"
JUMP_KM = 30.0  # a place ends at a step longer than this, as in analysis/h2910_compare.py
WARMUP = 50  # the running z-scores use a plain average until then

H2910 = {"global_perception_1k_s0": ("Reference", "Milan"), "global_perception_1k_s1": ("Reference", "Milan"),
         "h2910_bored_s0": ("Bored", "Milan"), "h2910_bored_s1": ("Bored", "Milan"),
         "h2910_globalist_s0": ("Globalist", "Milan"), "h2910_globalist_s1": ("Globalist", "Milan"),
         "h2910_localist_s0": ("Localist", "Milan"), "h2910_localist_s1": ("Localist", "Milan"),
         "h2910_fastlearner_s0": ("Fast learner", "Milan"), "h2910_fastlearner_s1": ("Fast learner", "Milan"),
         "h2910_bored_paris_s0": ("Bored", "Paris 5k"), "h2910_globalist_paris_s0": ("Globalist", "Paris 5k")}
DEAD = {"h2910_fastlearner_s1": 142}  # its network died at this step (notes/06_characters/observations.md, part 1, §5); later steps are left out


def steps(run: str) -> pd.DataFrame:
    s = pd.read_parquet(RUNS / run / "steps.parquet")
    return s[s.step < DEAD[run]] if run in DEAD else s


def candidates(run: str) -> pd.DataFrame:
    c = pd.read_parquet(RUNS / run / "candidates.parquet")
    return c[c.step < DEAD[run]] if run in DEAD else c


def heldout(run: str) -> pd.DataFrame:
    h = pd.read_parquet(RUNS / run / "heldout.parquet")
    return h[h.step <= DEAD[run]] if run in DEAD else h


def places(s: pd.DataFrame) -> pd.DataFrame:
    """Adds `place` (id) and `place_len`, `place_pos` (0 at arrival, 1 at the last step)."""
    new = np.r_[True, s.dist_km.to_numpy()[1:] > JUMP_KM]
    p = np.cumsum(new) - 1
    length = np.bincount(p)
    pos = np.arange(len(s)) - np.flatnonzero(new)[p]
    return s.assign(place=p, place_len=length[p], place_pos=pos / np.maximum(length[p] - 1, 1))


def heldout_at(h: pd.DataFrame, step: np.ndarray) -> np.ndarray:
    """The held-out MSE interpolated on log scale at each step: how well the network draws the planet at that moment."""
    return np.exp(np.interp(step, h.step.to_numpy(), np.log(h.heldout_mse.to_numpy())))


def rng_range(v) -> str:
    v = np.asarray(v, float)
    return f"{np.nanmean(v):.3g} ({np.nanmin(v):.3g}–{np.nanmax(v):.3g})"
