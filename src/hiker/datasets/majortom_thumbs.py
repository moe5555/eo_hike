"""Major TOM Core-S2L2A thumbnails adapter (ESA Phi-lab, CC-BY-SA-4.0).

Why this archive: it is a *uniform* 10 km grid over the whole planet, so a random
sample of cells is a sample of the Earth's land surface by area, not by population.
Deserts, ice sheets, boreal forest and rangeland appear in proportion.

How it is read: Core-S2L2A is 23 TB of parquet, 500 fragments per file, one row
group per row. Parquet is columnar, so the RGB ``thumbnail`` column (a 1068x1068 PNG,
typically 0.3-1.5 MB) can be fetched for one row with HTTP range requests without
touching the twelve band columns. We sample ``n_fragments`` rows from the 173 MB
``metadata.parquet``, fetch each thumbnail once (cached on disk), and cut every
fragment into ``tiles_per_side**2`` chips.

Ocean: Sentinel-2 acquires over open water too, and a uniform sample of the grid
turned out to be about half featureless sea (see docs/decisions.md). ``land_only``
(default true) keeps only cells whose centre is land according to a 1 km land mask;
coasts and ice sheets stay.

Chip coordinates: the fragment's centre lat/lon is given; each tile centre is offset
from it in the fragment's UTM CRS (10 m per pixel) and projected back. The date is
the fragment's acquisition timestamp.

The thumbnail is a fixed-scale RGB composite of B04/B03/B02 produced by the
archive; we do not re-stretch it.
"""

from __future__ import annotations

import hashlib
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pandas as pd
from PIL import Image

from . import register
from .base import ChipRecord

REPO = "Major-TOM/Core-S2L2A"
FRAGMENT_PX = 1068
GSD_M = 10.0


@register("majortom_thumbs")
class MajorTOMThumbs:
    name = "majortom_thumbs"

    def __init__(self, dcfg: dict[str, Any], raw_dir: Path) -> None:
        self.raw_dir = raw_dir
        self.n_fragments: int = int(dcfg.get("n_fragments", 2500))
        self.tiles_per_side: int = int(dcfg.get("tiles_per_side", 4))
        self.max_cloud_cover: float = float(dcfg.get("max_cloud_cover", 10.0))  # percent
        self.max_nodata: float = float(dcfg.get("max_nodata", 0.0))  # fragment-level, fraction
        self.max_tile_black: float = float(dcfg.get("max_tile_black", 0.2))  # skip mostly-empty tiles
        self.land_only: bool = bool(dcfg.get("land_only", True))
        self.lat_min: float | None = dcfg.get("lat_min")
        self.lat_max: float | None = dcfg.get("lat_max")
        self.sample_seed: int = int(dcfg.get("sample_seed", 0))
        self.workers: int = int(dcfg.get("workers", 8))
        self.download: bool = dcfg.get("download", True)
        self._sel: pd.DataFrame | None = None
        self.skipped_black_tiles = 0

    # -- selection -----------------------------------------------------------------

    def _selection_key(self) -> str:
        parts = [self.n_fragments, self.max_cloud_cover, self.max_nodata, self.lat_min, self.lat_max, self.sample_seed, self.land_only]
        return hashlib.sha1(repr(parts).encode()).hexdigest()[:8]

    def _selection_path(self) -> Path:
        return self.raw_dir / f"selection_{self._selection_key()}.parquet"

    def _meta_path(self) -> Path:
        return self.raw_dir / "metadata.parquet"

    def _thumb_dir(self) -> Path:
        return self.raw_dir / "thumbs"

    def _selection(self) -> pd.DataFrame:
        if self._sel is None:
            self._sel = pd.read_parquet(self._selection_path())
        return self._sel

    def prepare(self) -> None:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self._thumb_dir().mkdir(exist_ok=True)
        if not self._selection_path().exists():
            self._build_selection()
        sel = self._selection()
        missing = [r for r in sel.itertuples(index=False) if not self._thumb_path(r).exists()]
        if missing:
            if not self.download:
                raise FileNotFoundError(f"{len(missing)} thumbnails missing and download=false")
            self._fetch_thumbs(missing)

    def _build_selection(self) -> None:
        if not self._meta_path().exists():
            if not self.download:
                raise FileNotFoundError(f"{self._meta_path()} missing and download=false")
            from huggingface_hub import hf_hub_download

            print("[majortom] downloading metadata.parquet (~173 MB)")
            hf_hub_download(REPO, "metadata.parquet", repo_type="dataset", local_dir=str(self.raw_dir))
        cols = ["grid_cell", "product_id", "timestamp", "cloud_cover", "nodata", "centre_lat", "centre_lon", "crs", "parquet_url", "parquet_row"]
        meta = pd.read_parquet(self._meta_path(), columns=cols)
        n_all = len(meta)
        meta = meta[(meta.cloud_cover <= self.max_cloud_cover) & (meta.nodata <= self.max_nodata)]
        if self.lat_min is not None:
            meta = meta[meta.centre_lat >= self.lat_min]
        if self.lat_max is not None:
            meta = meta[meta.centre_lat <= self.lat_max]
        if self.land_only:
            # Sentinel-2 also images open ocean; a uniform sample of the grid is about
            # half water. global_land_mask is a 1 km land/sea raster; testing the cell
            # centre keeps coasts and ice sheets and drops open water.
            from global_land_mask import globe

            n_before = len(meta)
            meta = meta[globe.is_land(meta.centre_lat.to_numpy(), meta.centre_lon.to_numpy())]
            print(f"[majortom] land mask: {n_before} -> {len(meta)} fragments")
        # One fragment per grid cell: cells that were imaged twice would otherwise be
        # near-duplicates of each other.
        meta = meta.sort_values(["grid_cell", "timestamp"]).drop_duplicates("grid_cell", keep="first")
        print(f"[majortom] {n_all} rows -> {len(meta)} eligible fragments after filters")
        rng = np.random.default_rng(self.sample_seed)
        idx = rng.choice(len(meta), size=min(self.n_fragments, len(meta)), replace=False)
        sel = meta.iloc[np.sort(idx)].reset_index(drop=True)
        sel.to_parquet(self._selection_path())
        self._sel = sel

    # -- thumbnails ------------------------------------------------------------------

    @staticmethod
    def _frag_id(r: Any) -> str:
        return f"{r.grid_cell}_{r.timestamp}"

    def _thumb_path(self, r: Any) -> Path:
        return self._thumb_dir() / f"{self._frag_id(r)}.png"

    def _fetch_one(self, r: Any) -> None:
        import fsspec
        import pyarrow.parquet as pq

        fs = fsspec.filesystem("https")
        with fs.open(r.parquet_url, "rb", block_size=1 << 20, cache_type="none") as f:
            pf = pq.ParquetFile(f)
            tbl = pf.read_row_group(int(r.parquet_row), columns=["thumbnail", "grid_cell"])
        row = tbl.to_pylist()[0]
        if row["grid_cell"] != r.grid_cell:
            raise RuntimeError(f"row mismatch for {self._frag_id(r)}: got {row['grid_cell']}")
        tmp = self._thumb_path(r).with_suffix(".part")
        tmp.write_bytes(row["thumbnail"])
        tmp.replace(self._thumb_path(r))

    def _fetch_thumbs(self, rows: list[Any]) -> None:
        from tqdm import tqdm

        failures: list[str] = []
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            futs = {ex.submit(self._fetch_one, r): r for r in rows}
            for fut in tqdm(as_completed(futs), total=len(futs), desc="majortom thumbnails"):
                r = futs[fut]
                try:
                    fut.result()
                except Exception as e:  # noqa: BLE001 - report, then fail at the end
                    failures.append(f"{self._frag_id(r)}: {e}")
        if failures:
            raise RuntimeError(f"{len(failures)} thumbnail fetches failed, e.g. {failures[:3]}")

    # -- iteration ---------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._selection()) * self.tiles_per_side**2

    def iter_chips(self) -> Iterator[ChipRecord]:
        from pyproj import Transformer

        n = self.tiles_per_side
        tile = FRAGMENT_PX // n
        for r in self._selection().itertuples(index=False):
            img = np.asarray(Image.open(self._thumb_path(r)).convert("RGB"))
            if img.shape[0] != FRAGMENT_PX or img.shape[1] != FRAGMENT_PX:
                raise RuntimeError(f"unexpected thumbnail size {img.shape} for {self._frag_id(r)}")
            when = datetime.strptime(r.timestamp, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
            to_utm = Transformer.from_crs("EPSG:4326", r.crs, always_xy=True)
            to_ll = Transformer.from_crs(r.crs, "EPSG:4326", always_xy=True)
            cx, cy = to_utm.transform(r.centre_lon, r.centre_lat)
            platform = "Sentinel-2A" if r.product_id.startswith("S2A") else "Sentinel-2B" if r.product_id.startswith("S2B") else "Sentinel-2"
            for ti in range(n):
                for tj in range(n):
                    chip = np.ascontiguousarray(img[ti * tile : (ti + 1) * tile, tj * tile : (tj + 1) * tile])
                    black = float((chip.max(axis=2) == 0).mean())
                    if black > self.max_tile_black:
                        self.skipped_black_tiles += 1
                        continue
                    # tile centre offset from fragment centre, metres, north-up
                    dx = (tj + 0.5 - n / 2) * tile * GSD_M
                    dy = -(ti + 0.5 - n / 2) * tile * GSD_M
                    lon, lat = to_ll.transform(cx + dx, cy + dy)
                    yield ChipRecord(
                        chip_id=f"mt_{r.grid_cell}_{r.timestamp}_r{ti}c{tj}",
                        image=chip,
                        lat=float(lat),
                        lon=float(lon),
                        datetime=when,
                        sensor=f"{platform} L2A (RGB thumbnail)",
                        source_dataset=self.name,
                        group_id=self._frag_id(r),
                        extra={
                            "product_id": r.product_id,
                            "fragment_cloud_cover": float(r.cloud_cover),
                            "tile_row": ti,
                            "tile_col": tj,
                        },
                    )
