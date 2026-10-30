"""Render a shotlist from analysis/attention.py as a Ken Burns film of one tile, from its 10 m thumbnail.

    python -m analysis.kenburns runs/global_perception_1k_s0/attention/step_0508_learn/shotlist.json
    python -m analysis.kenburns <shotlist.json> --heat 0.5 --hud          # with the attention map and captions

The camera is (cx, cy, size) in fractions of the tile. Between two shots the centre moves on an eased curve and
the size is interpolated in log space, with a pull-back proportional to the distance, so a long pan widens
instead of whipping across at full zoom. During a hold the camera pushes in by a few percent. The source is the
1068 px thumbnail: a tight shot (64 px window x frame 1.6 of the 256 px low-res) is ~430 source px, upsampled
to --px. With --heat, the map the camera is following fades in (for --order learn: the map before each look,
so you see familiarity cool the places already looked at).

Writes film.mp4 next to the shotlist (or --out). Edit the shotlist (move, hold, size, order of shots) and render again.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

KEY = {"interest": "I", "novelty": "n", "surprise": "e", "progress": "g"}
PUSH_IN = 0.05  # zoom during a hold
PULL_BACK = 1.2  # mid-pan the frame is at least this times the distance travelled


def ease(t: float) -> float:
    return t * t * t * (t * (6 * t - 15) + 10)  # smootherstep


def camera(a: dict, b: dict, t: float) -> tuple[float, float, float]:
    e = ease(t)
    cx, cy = a["cx"] + (b["cx"] - a["cx"]) * e, a["cy"] + (b["cy"] - a["cy"]) * e
    s = math.exp(math.log(a["size"]) + (math.log(b["size"]) - math.log(a["size"])) * e)
    d = math.hypot(b["cx"] - a["cx"], b["cy"] - a["cy"])
    m = max(1.0, PULL_BACK * d / max(a["size"], b["size"]))
    return cx, cy, min(1.0, s * (1 + (m - 1) * math.sin(math.pi * e)))


def heat_layers(sl: dict, d: Path, src: Image.Image, alpha: float) -> list[Image.Image]:
    """The source tinted by each map in maps.npz, one image per map, each on its own 75th to 99th percentile."""
    import matplotlib
    from scipy.ndimage import map_coordinates

    if alpha <= 0:
        return [src]
    z = np.load(d / "maps.npz")
    k = KEY[sl["signal"]]
    maps = [z[f"{k}_{i}"] for i in range(sum(1 for f in z.files if f.startswith(f"{k}_")))]
    W, H, crop, st = src.size[0], sl["lowres_px"], sl["crop_px"], sl["stride_px"]
    # map cell i is the window centred at crop/2 + i*stride (low-res px); outside the outermost centres the tint fades out
    u = ((np.arange(W) + 0.5) * H / W - crop / 2) / st
    iy, ix = np.meshgrid(u, u, indexing="ij")
    side = maps[0].shape[0]
    out_cells = np.maximum(np.maximum(-iy, iy - (side - 1)), np.maximum(-ix, ix - (side - 1))).clip(0)
    fade = (1 - out_cells / (crop / 2 / st)).clip(0, 1)
    base = np.asarray(src, dtype=np.float32) / 255
    out = []
    for mp in maps:
        lo, hi = np.percentile(mp, 75), np.percentile(mp, 99)
        nrm = np.clip((mp - lo) / max(hi - lo, 1e-9), 0, 1)
        n = map_coordinates(nrm.astype(np.float32), [iy, ix], order=1, mode="nearest") * fade
        col = matplotlib.colormaps["inferno"](n)[..., :3]
        a = (alpha * n)[..., None]
        out.append(Image.fromarray((((1 - a) * base + a * col).clip(0, 1) * 255).astype(np.uint8)))
    return out


def render(path: Path, px: int | None, fps: int | None, heat: float | None, hud: bool | None, out: Path | None) -> Path:
    import imageio.v2 as imageio

    from data.tile_store import TileStore

    sl = json.loads(path.read_text())
    rc = sl.get("render", {})
    px, fps = px or rc.get("px", 1080), fps or rc.get("fps", 30)
    heat = rc.get("heat", 0.0) if heat is None else heat
    hud = rc.get("hud", False) if hud is None else hud
    src = Image.fromarray(TileStore().get_hires(sl["tile"]))
    W = src.size[0]
    layers = heat_layers(sl, path.parent, src, heat)
    shots = sl["shots"]
    n_looks = sum(1 for s in shots if s["kind"] == "look")
    font = ImageFont.load_default(size=max(14, px // 40))
    small = ImageFont.load_default(size=max(12, px // 54))
    lat, lon = sl["lat"], sl["lon"]
    place = f"{abs(lat):.2f}° {'N' if lat >= 0 else 'S'}  {abs(lon):.2f}° {'E' if lon >= 0 else 'W'}  ·  {sl['cover']}  ·  step {sl['step']}"

    def layer_for(i: int) -> Image.Image:
        """Map before look k for shot i (learn order has one map per look; other orders one map)."""
        sh = shots[i]
        k = sh.get("look", n_looks if sh["kind"] == "pullout" else 1)
        return layers[min(k - 1, len(layers) - 1)]

    def frame(cam, i: int, caption: str) -> np.ndarray:
        cx, cy, s = cam
        w = s * W
        x0 = min(max(cx * W - w / 2, 0), W - w)
        y0 = min(max(cy * W - w / 2, 0), W - w)
        im = layer_for(i).resize((px, px), Image.Resampling.LANCZOS, box=(x0, y0, x0 + w, y0 + w))
        if hud:
            d = ImageDraw.Draw(im)
            sh = shots[i]
            if sh["kind"] == "look":  # the walker's field of view
                b = [(v * W / sl["lowres_px"] - o) * px / w for v, o in zip(sh["box_px"], (x0, y0, x0, y0))]
                d.rectangle(b, outline=(255, 204, 0), width=max(1, px // 400))
            m = px // 40
            d.text((m, px - m - 2.6 * font.size), place, font=small, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
            d.text((m, px - m - 1.2 * font.size), caption, font=font, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
        return np.asarray(im)

    def caption(sh: dict) -> str:
        if sh["kind"] == "look":
            c = f"look {sh['look']}/{n_looks}  ·  {sl['signal']} {sh['scores'][KEY[sl['signal']]]:.2f}"
            return c + (f"  ·  back to look {sh['return_to']}" if sh.get("return_to") else "")
        return {"establish": f"{sl['run']}: the whole tile, {10.68 * shots[0]['size']:.1f} km", "pullout": f"{n_looks} looks, order: {sl['order']}"}[sh["kind"]]

    out = out or path.parent / "film.mp4"
    wr = imageio.get_writer(out, fps=fps, codec="libx264", quality=8, macro_block_size=8)
    n = 0
    prev = shots[0]
    for i, sh in enumerate(shots):
        cap = caption(sh)
        for f in range(int(round(sh.get("move", 0) * fps))):
            wr.append_data(frame(camera(prev, sh, (f + 1) / max(1, round(sh["move"] * fps))), i, cap))
            n += 1
        hold = int(round(sh.get("hold", 0) * fps))
        for f in range(hold):
            t = ease((f + 1) / max(1, hold))
            wr.append_data(frame((sh["cx"], sh["cy"], sh["size"] * (1 - PUSH_IN * t)), i, cap))
            n += 1
        prev = dict(sh, size=sh["size"] * (1 - PUSH_IN))
    wr.close()
    print(f"[kenburns] {out}  ({n / fps:.1f} s, {n} frames at {px} px, {fps} fps)")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("shotlist", type=Path)
    ap.add_argument("--px", type=int, help="frame size (square); default from the shotlist, 1080")
    ap.add_argument("--fps", type=int)
    ap.add_argument("--heat", type=float, help="opacity of the attention map, 0 = the plain tile")
    ap.add_argument("--hud", action=argparse.BooleanOptionalAction, default=None, help="captions and the walker's field of view")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    render(a.shotlist, a.px, a.fps, a.heat, a.hud, a.out)


if __name__ == "__main__":
    main()
