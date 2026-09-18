"""EuroSAT RGB adapter (Zenodo 7711810, MIT licence).

27,000 JPEG chips of 64x64 px in ten land-cover classes, 34 European countries.
The RGB release carries **no** coordinates and **no** acquisition dates, so those
fields are null for every chip. That is exactly what makes it a smoke test rather
than a debug set: it exercises the pipeline but not the geo/time code.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any, Iterator

import numpy as np
from PIL import Image

from . import register
from .base import ChipRecord

URL = "https://zenodo.org/records/7711810/files/EuroSAT_RGB.zip"


@register("eurosat")
class EuroSATRGB:
    name = "eurosat"

    def __init__(self, dcfg: dict[str, Any], raw_dir: Path) -> None:
        self.raw_dir = raw_dir
        self.download: bool = dcfg.get("download", True)
        self.limit: int | None = dcfg.get("limit")  # cap chips, for quick smoke tests

    def _zip(self) -> Path:
        return self.raw_dir / "EuroSAT_RGB.zip"

    def _root(self) -> Path:
        return self.raw_dir / "EuroSAT_RGB"

    def prepare(self) -> None:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        if not self._root().exists():
            if not self._zip().exists():
                if not self.download:
                    raise FileNotFoundError(f"{self._zip()} missing and download=false")
                import requests
                from tqdm import tqdm

                with requests.get(URL, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    total = int(r.headers.get("content-length", 0))
                    with open(self._zip(), "wb") as f, tqdm(total=total, unit="B", unit_scale=True, desc="EuroSAT_RGB.zip") as bar:
                        for chunk in r.iter_content(1 << 20):
                            f.write(chunk)
                            bar.update(len(chunk))
            with zipfile.ZipFile(self._zip()) as z:
                z.extractall(self.raw_dir)

    def _files(self) -> list[Path]:
        files = sorted(self._root().rglob("*.jpg"))
        return files[: self.limit] if self.limit else files

    def __len__(self) -> int:
        return len(self._files())

    def iter_chips(self) -> Iterator[ChipRecord]:
        for p in self._files():
            img = np.asarray(Image.open(p).convert("RGB"))
            cls = p.parent.name
            yield ChipRecord(
                chip_id=f"eurosat_{p.stem}",
                image=img,
                lat=None,
                lon=None,
                datetime=None,
                sensor="Sentinel-2",
                source_dataset=self.name,
                group_id=cls,
                extra={"label": cls},
            )
