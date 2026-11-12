"""Pooled distinct tiles of a condition's walks (brief v2, 7: walk start cells in order until the pooled tiles reach N).

    python scripts/pool_tiles.py runs/long/curious      # prints one integer

Finished walks (walk.json) count by the union of the image keys they stood on; a running walk adds the last `uniq` its log printed
(runs/<phase>/logs/<condition>_w<k>.log), so a new walk is started only while finished + running stay below N.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd


def pooled(cond_dir: Path) -> int:
    keys: set[int] = set()
    running = 0
    logs = cond_dir.parent / "logs"
    for d in sorted(cond_dir.glob("w*")):
        if (d / "walk.json").exists():
            keys.update(pd.read_parquet(d / "steps.parquet", columns=["image_key"]).image_key.astype(int).tolist())
            continue
        log = logs / f"{cond_dir.name}_w{int(d.name[1:])}.log"
        if log.exists():
            u = re.findall(r" uniq (\d+) ", log.read_text())
            running += int(u[-1]) if u else 0
    return len(keys) + running


if __name__ == "__main__":
    print(pooled(Path(sys.argv[1])))
