"""Faithful enlargement of 128 px tiles (GAN samples or package tiles) for viewing: no new content. See notes/upscaling.md.

    python scripts/upscale_faithful.py <png or dir> [...] --out <dir> [--factor 8] [--mode nearest|lanczos]

- nearest (default, the faithful one): every source pixel becomes a factor x factor block. No value is invented, nothing is smoothed,
  stripes, fill and quantisation stay exactly as rendered. One block = 10.68 km / 128 = 83.4 m on the ground.
- lanczos (display only, labelled): interpolates between existing values. No new structure, but new in-between values and slight
  ringing at hard edges (fill, stripes). Never use it for measurement.
The method, factor and ground size of one source pixel are written into each PNG (text chunk "upscale") and the file name.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, PngImagePlugin

TILE_KM = 10.68  # the Major TOM cell: 178 native 60 m pixels of the archive
MODES = {"nearest": Image.Resampling.NEAREST, "lanczos": Image.Resampling.LANCZOS}


def upscale(src: Path, out: Path, factor: int, mode: str) -> Path:
    im = Image.open(src).convert("RGB")
    w, h = im.size
    big = im.resize((w * factor, h * factor), MODES[mode])
    meta = {"source": src.name, "source_px": [w, h], "factor": factor, "mode": mode,
            "source_pixel_m": round(TILE_KM * 1000 / w, 1), "faithful": mode == "nearest",
            "method": "notes/upscaling.md (scripts/upscale_faithful.py)"}
    info = PngImagePlugin.PngInfo()
    info.add_text("upscale", json.dumps(meta))
    dst = out / f"{src.stem}_x{factor}_{mode}.png"
    big.save(dst, pnginfo=info)
    return dst


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--factor", type=int, default=8)
    ap.add_argument("--mode", choices=list(MODES), default="nearest")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    files = [f for p in a.inputs for f in (sorted(p.glob("*.png")) if p.is_dir() else [p])]
    for f in files:
        print(upscale(f, a.out, a.factor, a.mode))


if __name__ == "__main__":
    main()
