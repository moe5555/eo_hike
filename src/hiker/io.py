"""Run directories, JSONL logging, and the measured geo/time helpers."""

from __future__ import annotations

import json
import math
import random
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import yaml

from .config import config_hash

EARTH_RADIUS_KM = 6371.0088

# Field order of one log line. Kept explicit so the file is stable and greppable.
LOG_FIELDS = [
    "agent_id",
    "step",
    "chip_id",
    "novelty",
    "novelty_running_mean",
    "rank_among_candidates",
    "n_candidates",
    "was_random_jump",
    "embedding_distance_from_prev",
    "geo_distance_km_from_prev",
    "time_delta_days_from_prev",
    "history_size",
    "taste_similarity",
    "taste_updated",
    "taste_shift",
    "lat",
    "lon",
    "date",
    "temperature",
    "seed",
]


def seed_everything(seed: int) -> None:
    """Seed ``random``, ``numpy`` and ``torch`` (if importable). Logged in config.yaml."""
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two WGS84 points."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def geo_distance_or_none(a: dict[str, Any], b: dict[str, Any]) -> float | None:
    """Haversine between two manifest rows, or None if either lacks coordinates."""
    if any(_isnull(a.get(k)) for k in ("lat", "lon")) or any(_isnull(b.get(k)) for k in ("lat", "lon")):
        return None
    return haversine_km(float(a["lat"]), float(a["lon"]), float(b["lat"]), float(b["lon"]))


def time_delta_days_or_none(a: dict[str, Any], b: dict[str, Any]) -> int | None:
    """Signed whole days from chip ``a`` to chip ``b`` (b minus a), or None."""
    da, db = a.get("date"), b.get("date")
    if _isnull(da) or _isnull(db):
        return None
    return (_to_date(db) - _to_date(da)).days


def _to_date(x: Any) -> date:
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x
    return date.fromisoformat(str(x)[:10])


def _isnull(x: Any) -> bool:
    if x is None:
        return True
    try:
        return bool(pd.isna(x))
    except (TypeError, ValueError):
        return False


def make_run_dir(cfg: dict[str, Any], runs_dir: str | Path, tag: str | None = None) -> Path:
    """Create ``runs/<timestamp>_<config-hash>/`` and write the resolved config."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = f"{stamp}_{config_hash(cfg)}" + (f"_{tag}" if tag else "")
    run_dir = Path(runs_dir) / name
    run_dir.mkdir(parents=True, exist_ok=False)
    with open(run_dir / "config.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    return run_dir


class JsonlWriter:
    """Append-only JSONL writer with a fixed key order and float rounding.

    Rounding to 6 decimals is what makes byte-identical logs realistic: it hides
    last-bit differences from BLAS kernels while keeping far more precision than the
    downstream uses need.
    """

    def __init__(self, path: Path, fields: list[str] = LOG_FIELDS, ndigits: int = 6) -> None:
        self.path = path
        self.fields = fields
        self.ndigits = ndigits
        self._f = open(path, "w", encoding="utf-8", newline="\n")

    def write(self, record: dict[str, Any]) -> None:
        row = {k: self._clean(record.get(k)) for k in self.fields}
        self._f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _clean(self, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, (np.floating, float)):
            if math.isnan(v):
                return None
            return round(float(v), self.ndigits)
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.bool_,)):
            return bool(v)
        return v

    def close(self) -> None:
        self._f.close()

    def __enter__(self) -> "JsonlWriter":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_json(path: Path, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, default=_json_default)


def _json_default(o: Any) -> Any:
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    raise TypeError(f"not JSON serialisable: {type(o)}")


def manifest_records(manifest: pd.DataFrame) -> list[dict[str, Any]]:
    """Manifest rows as plain dicts with NaN -> None, indexed by row position."""
    out: list[dict[str, Any]] = []
    for rec in manifest.to_dict("records"):
        out.append({k: (None if _isnull(v) else v) for k, v in rec.items()})
    return out
