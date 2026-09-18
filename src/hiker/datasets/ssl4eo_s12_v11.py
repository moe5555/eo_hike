"""SSL4EO-S12 v1.1 (embed2scale) adapter.

Archive facts (verified 2026-09-17, see docs/datasets.md):

- Hugging Face dataset ``embed2scale/SSL4EO-S12-v1.1``, CC-BY-4.0.
- 477 globally shuffled train shards + 5 val shards per modality, 512 locations each.
- Each tar member is a zarr-v2 zip holding ``bands (4, 3, 264, 264) uint8`` for the
  S2RGB modality (time, band, y, x), plus ``time (4,)`` in ns since epoch,
  ``center_lat``, ``center_lon``, ``crs``, ``cloud_mask (4, 264, 264)`` and
  ``file_id (4,)`` with the Sentinel-2 product IDs.
- Locations are sampled within 50 km of the 10k most populous cities (city-biased).

One (location, season) pair becomes one chip. ``group_id`` is the location, so the
seasonal siblings of a chip can be found later.
"""

from __future__ import annotations

import hashlib
import io
import tarfile
import tempfile
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pandas as pd

from . import register
from .base import ChipRecord

REPO = "embed2scale/SSL4EO-S12-v1.1"
N_SEASONS = 4
# Cloud mask classes, from the array attrs: land, water, snow, thin_cloud, thick_cloud,
# cloud_shadow, no_data. Anything from index 3 on is "not a clear view of the ground".
CLOUDY_CLASSES = (3, 4, 5, 6)


@register("ssl4eo_s12_v11")
class SSL4EOS12v11:
    name = "ssl4eo_s12_v11"

    def __init__(self, dcfg: dict[str, Any], raw_dir: Path) -> None:
        self.raw_dir = raw_dir
        self.split: str = dcfg.get("split", "val")
        self.modality: str = dcfg.get("modality", "S2RGB")
        if self.modality != "S2RGB":
            raise NotImplementedError(
                "only the S2RGB modality is wired up; multispectral is a planned extension"
            )
        self.max_shards: int | None = dcfg.get("max_shards")
        self.seasons: str = dcfg.get("seasons", "all")  # all | one
        if self.seasons not in ("all", "one"):
            raise ValueError("dataset.seasons must be 'all' or 'one'")
        self.download: bool = dcfg.get("download", True)
        self._meta: pd.DataFrame | None = None

    # -- files -------------------------------------------------------------------

    def _meta_path(self) -> Path:
        return self.raw_dir / f"{self.split}_metadata.parquet"

    def _shard_paths(self) -> list[Path]:
        meta = self._metadata()
        shards = sorted(meta["tar"].unique())
        if self.max_shards is not None:
            shards = shards[: self.max_shards]
        return [self.raw_dir / self.split / self.modality / s for s in shards]

    def _metadata(self) -> pd.DataFrame:
        if self._meta is None:
            self._meta = pd.read_parquet(self._meta_path())
        return self._meta

    def prepare(self) -> None:
        """Fetch the metadata parquet and the selected shards if they are missing."""
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        if not self._meta_path().exists():
            self._fetch(f"{self.split}_metadata.parquet")
        for p in self._shard_paths():
            if not p.exists():
                self._fetch(f"{self.split}/{self.modality}/{p.name}")

    def _fetch(self, rel: str) -> None:
        if not self.download:
            raise FileNotFoundError(f"{rel} missing under {self.raw_dir} and download=false")
        from huggingface_hub import hf_hub_download

        print(f"[ssl4eo] downloading {rel}")
        hf_hub_download(REPO, rel, repo_type="dataset", local_dir=str(self.raw_dir))

    # -- iteration ---------------------------------------------------------------

    def __len__(self) -> int:
        meta = self._metadata()
        shards = {p.name for p in self._shard_paths()}
        n_loc = int(meta["tar"].isin(shards).sum())
        return n_loc * (N_SEASONS if self.seasons == "all" else 1)

    @staticmethod
    def _season_for(sample_id: str) -> int:
        """Deterministic season pick used when ``seasons: one``."""
        return int(hashlib.md5(sample_id.encode()).hexdigest(), 16) % N_SEASONS

    def iter_chips(self) -> Iterator[ChipRecord]:
        import zarr

        for shard in self._shard_paths():
            with tarfile.open(shard) as tf:
                members = sorted((m for m in tf.getmembers() if m.isfile()), key=lambda m: m.name)
                for m in members:
                    data = tf.extractfile(m).read()  # type: ignore[union-attr]
                    yield from self._chips_from_zip(data, zarr)

    def _chips_from_zip(self, data: bytes, zarr: Any) -> Iterator[ChipRecord]:
        # zarr's ZipStore wants a path; write to a temp file rather than fight it.
        with tempfile.NamedTemporaryFile(suffix=".zarr.zip", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            store = zarr.storage.ZipStore(tmp_path, mode="r")
            g = zarr.open(store, mode="r")
            bands = np.asarray(g["bands"][:])  # (4, 3, 264, 264) uint8
            band_names = [str(b) for b in g["band"][:]]
            times = np.asarray(g["time"][:])  # ns since epoch
            lat = float(g["center_lat"][()])
            lon = float(g["center_lon"][()])
            sample_id = str(g["sample"][()])
            file_ids = [str(f) for f in g["file_id"][:]]
            cloud = np.asarray(g["cloud_mask"][:])  # (4, 264, 264)
            store.close()
        finally:
            os.unlink(tmp_path)

        # Reorder to R, G, B if the archive stores B02/B03/B04 in another order.
        try:
            order = [band_names.index(b) for b in ("B04", "B03", "B02")]
        except ValueError:
            order = [0, 1, 2]
        seasons = range(N_SEASONS) if self.seasons == "all" else [self._season_for(sample_id)]
        for t in seasons:
            img = np.ascontiguousarray(bands[t][order].transpose(1, 2, 0))
            when = datetime.fromtimestamp(int(times[t]) / 1e9, tz=timezone.utc)
            cloud_frac = float(np.isin(cloud[t], CLOUDY_CLASSES).mean())
            yield ChipRecord(
                chip_id=f"ssl4eo_{sample_id}_s{t}",
                image=img,
                lat=lat,
                lon=lon,
                datetime=when,
                sensor="Sentinel-2 L2A (RGB composite)",
                source_dataset=f"{self.name}/{self.split}/{self.modality}",
                group_id=sample_id,
                extra={"product_id": file_ids[t], "cloud_fraction": round(cloud_frac, 4), "season_idx": t},
            )
