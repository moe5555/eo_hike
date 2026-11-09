"""Experiment 09, the compass walker (notes/09_compass/brief_e09_compass.md): the drive, the radius rule and the eight offers.

Shared by agent/walk.py (nav: compass) and the offline analysis (analysis/e09/), so both use one implementation.

- Drive: d_t = (EMA_short - EMA_long) / SD_long of one signal per step (the value at the cell the walker chose). Charnov's comparison:
  d >= 0 when the recent gain is at least the long-run rate. Both averages, and the long variance, use the rate max(alpha, 1/t), i.e. a
  plain cumulative mean until step 1/alpha, as agent.signals.RunningNorm does.
- Radius: r = r_min * (r_max / r_min) ** u, u = clip((-d - h) / (delta - h), 0, 1), h the dead band (radius_hysteresis; 0 by default,
  which gives the brief's clip(-d / delta, 0, 1)). r_min at d >= -h, r_max at d <= -delta: linear in log distance in between.
- Offers: eight great-circle bearings 45 degrees apart, rotated by theta. Each offer is the indexed cell nearest to the point at
  distance r along its bearing (spherical earth, R = 6371.0088 km, as data/tile_store.haversine_km). Dropped: the current cell,
  duplicates (the first bearing keeps the cell), and targets with no cell within snap_tol * r.
"""

from __future__ import annotations

import numpy as np

EARTH_R_KM = 6371.0088
N_BEARINGS = 8


def destination(lat, lon, bearing_deg, dist_km):
    """The point dist_km from (lat, lon) along the initial great-circle bearing (degrees clockwise from north). Vectorised; lon in [-180, 180)."""
    la1, lo1, b = np.radians(lat), np.radians(lon), np.radians(bearing_deg)
    dl = np.asarray(dist_km, float) / EARTH_R_KM
    sla2 = np.sin(la1) * np.cos(dl) + np.cos(la1) * np.sin(dl) * np.cos(b)
    la2 = np.arcsin(np.clip(sla2, -1.0, 1.0))
    lo2 = lo1 + np.arctan2(np.sin(b) * np.sin(dl) * np.cos(la1), np.cos(dl) - np.sin(la1) * sla2)
    return np.degrees(la2), (np.degrees(lo2) + 180.0) % 360.0 - 180.0


def initial_bearing(lat1, lon1, lat2, lon2):
    """Initial great-circle bearing from point 1 to point 2, degrees clockwise from north in [0, 360)."""
    la1, la2, dl = np.radians(lat1), np.radians(lat2), np.radians(np.asarray(lon2) - np.asarray(lon1))
    return np.degrees(np.arctan2(np.sin(dl) * np.cos(la2), np.cos(la1) * np.sin(la2) - np.sin(la1) * np.cos(la2) * np.cos(dl))) % 360.0


def bearings(theta_deg: float) -> np.ndarray:
    return (theta_deg + 45.0 * np.arange(N_BEARINGS)) % 360.0


class Drive:
    """d = (EMA_short - EMA_long) / SD_long of a per-step signal (drive_norm z_diff), or EMA_short alone (raw)."""

    def __init__(self, a_short: float = 0.02, a_long: float = 0.002, norm: str = "z_diff") -> None:
        assert norm in ("z_diff", "raw"), norm
        self.a_s, self.a_l, self.norm = a_short, a_long, norm
        self.t, self.s, self.l, self.var = 0, 0.0, 0.0, 0.0

    def update(self, x: float) -> float:
        self.t += 1
        a_s, a_l = max(self.a_s, 1.0 / self.t), max(self.a_l, 1.0 / self.t)
        self.s = (1 - a_s) * self.s + a_s * x
        self.l = (1 - a_l) * self.l + a_l * x
        self.var = (1 - a_l) * self.var + a_l * (x - self.l) ** 2
        return self.d

    @property
    def d(self) -> float:
        if self.norm == "raw":
            return self.s
        return (self.s - self.l) / (self.var**0.5 + 1e-8) if self.t > 1 else 0.0

    def state(self) -> dict:
        return {"t": self.t, "short": self.s, "long": self.l, "sd_long": self.var**0.5, "d": self.d}


def radius(d: float, r_min: float, r_max: float, delta: float, h: float = 0.0) -> float:
    """The radius for drive d: r_min at d >= -h, r_max at d <= -delta, linear in log r in between."""
    if r_max <= r_min:
        return r_min
    u = min(max((-d - h) / (delta - h), 0.0), 1.0)
    return float(r_min * (r_max / r_min) ** u)


def radii(d: np.ndarray, r_min: float, r_max: float, delta: float, h: float = 0.0, warmup: int = 0) -> np.ndarray:
    """radius() over a drive series; r[t] is the radius of the offers at step t, set by d after step t-1 (r_min for t <= warmup)."""
    if r_max <= r_min:
        return np.full(len(d), float(r_min))
    u = np.clip((-np.asarray(d, float) - h) / (delta - h), 0.0, 1.0)
    r = r_min * (r_max / r_min) ** u
    r = np.r_[r_min, r[:-1]]
    r[: warmup + 1] = r_min
    return r


class LongNorm:
    """Running mean and SD of a candidate signal at the long rate, as agent.signals.RunningNorm but slower: updated with every candidate
    batch, then applied to it. Used for drive_signal interest_long (interest on the long yardstick)."""

    def __init__(self, alpha: float = 0.002) -> None:
        self.alpha, self.mean, self.var, self.t = alpha, 0.0, 0.0, 0

    def __call__(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, float)
        self.t += 1
        a = max(self.alpha, 1.0 / self.t)
        self.mean = (1 - a) * self.mean + a * float(x.mean())
        self.var = (1 - a) * self.var + a * float(((x - self.mean) ** 2).mean())
        return (x - self.mean) / (self.var**0.5 + 1e-8)


def offers(world, t: int, r_km: float, theta_deg: float, snap_tol: float) -> tuple[list[int], dict]:
    """The compass offers from cell t at radius r_km, rotated by theta_deg, on a data.tile_store.World (its BallTree over the pool).
    Returns (cells in bearing order, info) with info: the targets, each target's nearest cell and its distance, and why each was dropped."""
    la, lo = world.lat[t], world.lon[t]
    b = bearings(theta_deg)
    tla, tlo = destination(np.full(N_BEARINGS, la), np.full(N_BEARINGS, lo), b, np.full(N_BEARINGS, r_km))
    dist, ind = world.tree.query(np.radians(np.stack([tla, tlo], 1)), k=1)
    cell = world.pool[ind[:, 0]]
    snap_km = dist[:, 0] * EARTH_R_KM
    out, why = [], []
    for c, s in zip(cell, snap_km):
        if s > snap_tol * r_km:
            why.append("far")
        elif c == t:
            why.append("self")
        elif c in out:
            why.append("dup")
        else:
            why.append("")
            out.append(int(c))
    return out, {"bearing": b, "target_lat": tla, "target_lon": tlo, "cell": cell, "snap_km": snap_km, "drop": why}
