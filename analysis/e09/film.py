"""A film of one compass walk: the tile the walker stands on, where it is on the planet, and the drive that sets how far it looks.

    python analysis/e09/film.py e09_ref_s1                 # runs/e09_films/e09_ref_s1.mp4 and a contact sheet in notes/09_compass/results/films/
    python analysis/e09/film.py e09_ref_s1 --sec-per-step 0.25

Left: the chosen tile at 10 m (the ~1,068 px thumbnail). Right, top: the planet (every cell of the global index, a silhouette of the land
the walker can stand on), the track so far, and the eight offers of this step (at r_min they sit on the walker; at r_max they ring it
2,000 km out). Right, below: the offer radius and the drive d over the walk so far, with the -Δ line where the radius reaches r_max.
Time runs evenly: every step is held for the same time. Nothing here touches a walker.

The film goes to runs/e09_films/ (git-ignored): an untracked film in the work tree once filled the disk by way of .git.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "analysis" / "e09"))
from fetchcost import continent  # noqa: E402

RUNS = ROOT / "runs"
OUT = ROOT / "notes" / "09_compass" / "results" / "films"
W, H, TILE = 1280, 720, 720
PAD, PW = 24, 1280 - 720 - 48  # right panel: x from TILE + PAD, width PW
MAP_H = PW // 2
BG, INK, MUTED, FAINT = (18, 18, 17), (236, 235, 230), (150, 149, 143), (58, 58, 55)
LAND, SEA, TRACK, NOW, OFFER, FAR = (66, 68, 62), (30, 36, 44), (110, 160, 214), (235, 104, 52), (240, 200, 90), (235, 104, 52)


def font(size: int) -> ImageFont.FreeTypeFont:
    for p in ("/System/Library/Fonts/SFNSMono.ttf", "/System/Library/Fonts/Menlo.ttc"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size=size)


def xy(lat, lon, x0: int, y0: int) -> tuple[np.ndarray, np.ndarray]:
    return x0 + (np.asarray(lon) + 180) / 360 * PW, y0 + (90 - np.asarray(lat)) / 180 * MAP_H


def basemap(index: pd.DataFrame) -> Image.Image:
    """Every cell of the global index as one pixel, by its cover: land and coast lighter, ocean darker; no cell, background."""
    x = np.clip(((index.lon.to_numpy() + 180) / 360 * PW).astype(int), 0, PW - 1)
    y = np.clip(((90 - index.lat.to_numpy()) / 180 * MAP_H).astype(int), 0, MAP_H - 1)
    land = np.zeros((MAP_H, PW)), np.zeros((MAP_H, PW))
    np.add.at(land[0], (y, x), (index.cover.to_numpy() != "ocean").astype(float))
    np.add.at(land[1], (y, x), 1.0)
    im = np.empty((MAP_H, PW, 3), np.uint8)
    im[:] = BG
    im[land[1] > 0] = SEA
    im[land[0] > 0.5 * land[1].clip(1)] = LAND
    return Image.fromarray(im)


class Strip:
    """A small time-series panel; drawn once in full, then revealed up to the current step. Labels sit in a margin on the right."""

    MARGIN = 112

    def __init__(self, v: np.ndarray, lo: float, hi: float, log: bool, h: int, lines: dict[float, str], colour):
        self.h, self.n, self.w = h, len(v), PW - self.MARGIN
        f = (lambda z: np.log(z)) if log else (lambda z: z)
        self.y = lambda z: h - 6 - (f(np.clip(z, lo, hi)) - f(lo)) / (f(hi) - f(lo)) * (h - 12)
        self.axes = Image.new("RGB", (PW, h), BG)
        da = ImageDraw.Draw(self.axes)
        for val, txt in lines.items():
            yy = float(self.y(val))
            da.line([(0, yy), (self.w, yy)], fill=FAINT, width=1)
            da.text((self.w + 8, yy), txt, font=font(11), fill=MUTED, anchor="lm")
        self.full = self.axes.copy()
        xs = np.arange(self.n) / (self.n - 1) * (self.w - 1)
        ImageDraw.Draw(self.full).line(list(zip(xs, self.y(v))), fill=colour, width=2)

    def at(self, k: int) -> Image.Image:
        im = self.axes.copy()
        x = int(round(k / (self.n - 1) * (self.w - 1))) + 1
        im.paste(self.full.crop((0, 0, x, self.h)), (0, 0))
        ImageDraw.Draw(im).line([(x, 0), (x, self.h)], fill=MUTED, width=1)
        return im


def render(run: str, sec_per_step: float, fps: int, preview: list[int] | None = None) -> Path:
    from data.tile_store import TileStore

    cfg = yaml.safe_load((RUNS / run / "config.yaml").read_text())
    s = pd.read_parquet(RUNS / run / "steps.parquet")
    c = pd.read_parquet(RUNS / run / "candidates.parquet", columns=["step", "tile_idx", "chosen"])
    index = pd.read_parquet(ROOT / "data" / "global" / "index.parquet", columns=["idx", "lat", "lon", "cover"]).set_index("idx")
    c = c.join(index[["lat", "lon"]], on="tile_idx")
    offers = {k: g for k, g in c.groupby("step")}
    r_min, r_max, delta = float(cfg["radius_min_km"]), float(cfg["radius_max_km"]), float(cfg["radius_delta"])
    n = len(s)

    store = TileStore()
    base = basemap(index)
    track = base.copy()  # the track is drawn onto this as the walk goes
    tdraw = ImageDraw.Draw(track)
    x0, y0 = TILE + PAD, PAD + 34
    radius = Strip(s.r_km.to_numpy(), r_min, r_max, True, 92, {r_min: f"{r_min:.0f} km", 200: "200 km", r_max: f"{r_max:,.0f} km"}, OFFER)
    drive = Strip(np.nan_to_num(s.drive_d.to_numpy()), -1.0, 1.0, False, 92, {0.0: "0  near above", -delta: f"−Δ  far below"}, TRACK)
    f_big, f_mid, f_small = font(22), font(15), font(12)
    title = f"{run}  ·  compass walker, {cfg.get('drive_signal')}, Δ {delta:g}"

    path = RUNS / "e09_films" / f"{run}.mp4"
    path.parent.mkdir(exist_ok=True)
    reps = max(1, int(round(sec_per_step * fps)))
    ff = None if preview else subprocess.Popen(["nice", "-n", "10", "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps),
                           "-i", "-", "-c:v", "h264_videotoolbox", "-b:v", "6M", "-pix_fmt", "yuv420p", str(path)], stdin=subprocess.PIPE)
    lat, lon, r, d = s.lat.to_numpy(), s.lon.to_numpy(), s.r_km.to_numpy(), s.drive_d.to_numpy()
    frames_kept = {}
    for k in range(max(preview) + 1 if preview else n):
        # the track: a dot per step, a line for each step longer than 2 r_min (split at the antimeridian)
        px, py = xy(lat[k], lon[k], 0, 0)
        if k:
            qx, qy = xy(lat[k - 1], lon[k - 1], 0, 0)
            moved = s.dist_km.iloc[k] > 2 * r_min
            if moved and abs(lon[k] - lon[k - 1]) < 180:
                tdraw.line([(qx, qy), (px, py)], fill=TRACK, width=1)
        tdraw.point((px, py), fill=TRACK)
        if preview and k not in preview:
            continue

        im = Image.new("RGB", (W, H), BG)
        tile = Image.fromarray(store.get_hires(int(s.tile_idx.iloc[k]))).resize((TILE, TILE), Image.Resampling.LANCZOS)
        im.paste(tile, (0, 0))
        dr = ImageDraw.Draw(im)
        dr.text((TILE + PAD, PAD - 4), title, font=f_small, fill=MUTED)

        im.paste(track, (x0, y0))
        o = offers.get(int(s.step.iloc[k]))
        if o is not None:
            ox, oy = xy(o.lat.to_numpy(), o.lon.to_numpy(), x0, y0)
            for a, b in zip(ox, oy):
                dr.ellipse([a - 2.5, b - 2.5, a + 2.5, b + 2.5], outline=OFFER, width=1)
        cx, cy = xy(lat[k], lon[k], x0, y0)
        dr.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], outline=NOW, width=2)

        y1 = y0 + MAP_H + 18
        dr.text((x0, y1), "offer radius (log)", font=f_small, fill=MUTED)
        im.paste(radius.at(k), (x0, y1 + 16))
        y2 = y1 + 16 + 92 + 14
        dr.text((x0, y2), "drive d: short average minus long, in SDs", font=f_small, fill=MUTED)
        im.paste(drive.at(k), (x0, y2 + 16))

        y3 = y2 + 16 + 92 + 22
        la, lo = lat[k], lon[k]
        where = "ocean" if s.cover.iloc[k] == "ocean" else str(continent(la, lo))  # the continent boxes are rough: they call the open sea Asia
        state = "far" if r[k] >= r_max - 1 else ("near" if r[k] <= r_min + 0.01 else "widening")
        dr.text((x0, y3), f"step {k:>4}   {abs(la):5.1f}°{'N' if la >= 0 else 'S'} {abs(lo):5.1f}°{'E' if lo >= 0 else 'W'}", font=f_big, fill=INK)
        dr.text((x0, y3 + 34), f"radius {r[k]:>6,.0f} km   d {0.0 if np.isnan(d[k]) else d[k]:+.2f}   {state:<8}  {where}", font=f_mid, fill=FAR if state == "far" else INK)
        dr.text((x0, y3 + 58), f"novelty {s.n.iloc[k]:.2f}   travelled {s.dist_km.iloc[: k + 1].sum():>8,.0f} km", font=f_mid, fill=MUTED)

        if preview:
            OUT.mkdir(parents=True, exist_ok=True)
            im.save(OUT / f"{run}_preview_{k:04d}.png")
            continue
        buf = im.tobytes()
        for _ in range(reps):
            ff.stdin.write(buf)
        if k % 50 == 0:
            frames_kept[k] = im.resize((W // 4, H // 4))
            print(f"[film] {run}: step {k}", flush=True)
    if preview:
        return OUT
    ff.stdin.close()
    ff.wait()
    print(f"[film] {path}: {n} steps, {n * reps / fps:.0f} s, {path.stat().st_size / 1e6:.0f} MB", flush=True)
    sheet(run, frames_kept)
    return path


def sheet(run: str, frames: dict[int, Image.Image]) -> None:
    """Every 50th step, five across."""
    ks = sorted(frames)
    w, h = frames[ks[0]].size
    cols = 5
    im = Image.new("RGB", (cols * w, -(-len(ks) // cols) * h), BG)
    for j, k in enumerate(ks):
        im.paste(frames[k], ((j % cols) * w, (j // cols) * h))
    OUT.mkdir(parents=True, exist_ok=True)
    im.save(OUT / f"{run}_contact.png")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--sec-per-step", type=float, default=0.3)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--preview", type=int, nargs="+", help="save these steps as PNG next to the contact sheet, and no film")
    a = ap.parse_args()
    render(a.run, a.sec_per_step, a.fps, a.preview)


if __name__ == "__main__":
    main()
