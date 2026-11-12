"""The wanderer's clock (notes/brief_landsat_v2_run.md, 2-3): which acquisition a cell shows, the time offer, and the end of a walk.

Pure functions over one cell's acquisition days (int days since 1970-01-01, strictly increasing: one product per date, built by
data/landsat1_world.py `clock`). Used by agent/walk.py (`stack: clock`) and tested in tests/test_clock.py.

- Compass offers, and returns, show the acquisition closest to the clock t; an exact tie goes to the earlier pass.
- The time offer at the current cell c is its first acquisition with date > max(t, d_c), d_c the date of the tile now seen. Choosing
  it sets t to that date. There is none when no such acquisition exists. Next pass only; never scaled by boredom.
- Sideways moves never change t.
- End rule: the walk ends at the first step where t >= T_end; a walk not ended by the step cap stops there, `capped`. Optionally
  (tile_cap, off by default) it ends at the first step with tile_cap distinct tiles, `tiles`. Nothing else ends a walk: there is no
  death (surprise is computed and logged only).
"""

from __future__ import annotations

import numpy as np

EPOCH = np.datetime64("1970-01-01", "D")
END_REASONS = ("time", "capped", "tiles")


def closest_rank(days: np.ndarray, t: int) -> int:
    """Index of the acquisition closest to day t; an exact tie goes to the earlier pass."""
    n = len(days)
    assert n > 0, "a cell without acquisitions"
    i = int(np.searchsorted(days, t, side="left"))  # days[i-1] < t <= days[i]
    if i == 0:
        return 0
    if i == n:
        return n - 1
    return i if int(days[i]) - t < t - int(days[i - 1]) else i - 1


def time_offer(days: np.ndarray, t: int, d_c: int) -> int | None:
    """Index of the first acquisition strictly after max(t, d_c), or None (no later pass: no time offer this step)."""
    i = int(np.searchsorted(days, max(int(t), int(d_c)), side="right"))
    return i if i < len(days) else None


def end_reason(t: int, steps_done: int, t_end: int, cap: int, n_tiles: int = 0, tile_cap: int | None = None) -> str | None:
    """'time' at the first step where t >= t_end, 'tiles' at the first step where the walk has stood on tile_cap distinct tiles (off unless
    tile_cap is set; Moe 2026-11-13, a long curious walk), 'capped' when the step cap is reached first, else None. The only ways a walk ends."""
    if t >= t_end:
        return "time"
    if tile_cap is not None and n_tiles >= tile_cap:
        return "tiles"
    if steps_done >= cap:
        return "capped"
    return None


def choice_probs(I: np.ndarray, temperature: float, uniform: bool) -> np.ndarray:
    """The draw over the offers: softmax of interest / temperature (walk.py's), or uniform over the offers available (the Null)."""
    if uniform:
        return np.full(len(I), 1.0 / len(I))
    logits = np.asarray(I, float) / float(temperature)
    p = np.exp(logits - logits.max())
    return p / p.sum()


def to_day(d) -> int:
    return int((np.datetime64(d, "D") - EPOCH).astype(int))


def to_date(day: int) -> str:
    return str(EPOCH + np.timedelta64(int(day), "D"))
