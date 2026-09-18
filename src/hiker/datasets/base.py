"""The dataset boundary.

An archive adapter turns *whatever an archive looks like on disk or on the network*
into a stream of :class:`ChipRecord` objects. Everything downstream of ingest only
ever sees PNG files and ``manifest.parquet``, so swapping archives never touches the
embedding, indexing or hiking code.

To add an archive:

1. Create ``datasets/<name>.py`` with a class implementing :class:`DatasetAdapter`.
2. Register it in ``datasets/__init__.py``.
3. Point ``dataset.name`` at it in a config.

Rules the adapter must respect (they are checked in ingest):

- ``chip_id`` is unique within the archive and stable across runs.
- Missing metadata is ``None``; never invented, never defaulted to 0.
- Images are ``uint8`` arrays of shape ``(H, W, 3)`` (RGB). Multispectral archives
  would extend this with a different ``image_kind``; that is a planned change, not
  something to bolt on here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterator, Protocol

import numpy as np


@dataclass
class ChipRecord:
    """One chip: pixels plus whatever metadata survived in the source archive."""

    chip_id: str
    image: np.ndarray  # (H, W, 3) uint8
    lat: float | None
    lon: float | None
    datetime: datetime | None  # acquisition time; ``date`` in the manifest is derived
    sensor: str | None
    source_dataset: str
    group_id: str | None = None  # e.g. the location a seasonal chip belongs to
    extra: dict[str, Any] = field(default_factory=dict)  # small, JSON-able


class DatasetAdapter(Protocol):
    """What ingest needs from an archive."""

    name: str

    def prepare(self) -> None:
        """Download or locate raw data. Must be safe to call twice (idempotent)."""
        ...

    def __len__(self) -> int:
        """Expected number of chips, for the progress bar. May be an upper bound."""
        ...

    def iter_chips(self) -> Iterator[ChipRecord]:
        """Yield every chip, in a deterministic order."""
        ...
