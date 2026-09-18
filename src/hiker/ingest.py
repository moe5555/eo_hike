"""Step 1: archive -> chips on disk + ``manifest.parquet``.

The manifest is the contract between the archive and everything else:

    chip_id, path, lat, lon, date, datetime, sensor, source_dataset, group_id, extra...

Missing metadata is null. ``path`` is relative to the processed dataset directory so
the directory can be moved. Chips are written as PNG (lossless) so the encoder sees
exactly the archive's pixels.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from PIL import Image
from tqdm import tqdm

from . import config as C
from .datasets import get_adapter

MANIFEST_COLUMNS = ["chip_id", "path", "lat", "lon", "date", "datetime", "sensor", "source_dataset", "group_id"]


def coverage_stats(df: pd.DataFrame) -> dict[str, Any]:
    """What fraction of chips have coordinates / dates, plus spans. Printed and saved."""
    n = len(df)
    has_geo = df["lat"].notna() & df["lon"].notna()
    has_date = df["date"].notna()
    stats: dict[str, Any] = {
        "n_chips": int(n),
        "n_groups": int(df["group_id"].nunique()) if "group_id" in df else None,
        "frac_with_coordinates": float(has_geo.mean()) if n else 0.0,
        "frac_with_date": float(has_date.mean()) if n else 0.0,
        "sensors": {str(k): int(v) for k, v in df["sensor"].value_counts(dropna=False).items()},
    }
    if has_geo.any():
        stats["lat_range"] = [float(df.lat.min()), float(df.lat.max())]
        stats["lon_range"] = [float(df.lon.min()), float(df.lon.max())]
        stats["frac_southern_hemisphere"] = float((df.lat[has_geo] < 0).mean())
    if has_date.any():
        stats["date_range"] = [str(df.date.min()), str(df.date.max())]
    return stats


def run_ingest(cfg: dict[str, Any], force: bool = False) -> Path:
    """Materialise chips and write the manifest. Skipped if the manifest exists."""
    out = C.manifest_path(cfg)
    if out.exists() and not force:
        print(f"[ingest] manifest exists, skipping: {out}")
        return out

    adapter = get_adapter(cfg["dataset"], C.raw_dir(cfg))
    adapter.prepare()
    chips_dir = C.chips_dir(cfg)
    chips_dir.mkdir(parents=True, exist_ok=True)
    fmt = cfg["outputs"].get("image_format", "png")

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rec in tqdm(adapter.iter_chips(), total=len(adapter), desc="ingest", unit="chip"):
        if rec.chip_id in seen:
            raise ValueError(f"duplicate chip_id from adapter: {rec.chip_id}")
        seen.add(rec.chip_id)
        if rec.image.ndim != 3 or rec.image.shape[2] != 3 or rec.image.dtype.name != "uint8":
            raise ValueError(f"{rec.chip_id}: expected (H, W, 3) uint8 image, got {rec.image.shape} {rec.image.dtype}")
        rel = Path("chips") / f"{rec.chip_id}.{fmt}"
        p = C.processed_dir(cfg) / rel
        if not p.exists():
            Image.fromarray(rec.image).save(p)
        rows.append(
            {
                "chip_id": rec.chip_id,
                "path": rel.as_posix(),
                "lat": rec.lat,
                "lon": rec.lon,
                "date": rec.datetime.date().isoformat() if rec.datetime else None,
                "datetime": rec.datetime.isoformat() if rec.datetime else None,
                "sensor": rec.sensor,
                "source_dataset": rec.source_dataset,
                "group_id": rec.group_id,
                "height": int(rec.image.shape[0]),
                "width": int(rec.image.shape[1]),
                **{f"x_{k}": v for k, v in rec.extra.items()},
            }
        )
    if not rows:
        raise RuntimeError("adapter yielded no chips")
    df = pd.DataFrame(rows)
    for col in ("lat", "lon"):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
    df.to_parquet(out, index=False)
    stats = coverage_stats(df)
    extra_stats = {k: v for k, v in vars(adapter).items() if k.startswith("skipped_")}
    stats.update(extra_stats)
    with open(C.processed_dir(cfg) / "ingest_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print("[ingest] " + json.dumps(stats))
    return out


def load_manifest(cfg: dict[str, Any]) -> pd.DataFrame:
    df = pd.read_parquet(C.manifest_path(cfg))
    if df["chip_id"].duplicated().any():
        raise ValueError("manifest has duplicate chip_ids")
    return df
