"""A film of one walk on a Landsat pass world (world: landsat_pass): the tile the walker stands on, where it is in the satellite's strip,
the eight offers around it, and the drive that sets how far it looks.

    python analysis/e10/film_pass.py e10_pass_5km_sqrt_s0                       # runs/e10_films/<run>.mp4 + contact sheet
    python analysis/e10/film_pass.py e10_pass_5km_sqrt_s0 --steps 300 --sec-per-step 0.3
    python analysis/e10/film_pass.py e10_pass_5km_sqrt_s0 --preview 0 150 299   # PNG frames in runs/e10_films/preview/, no film
    python analysis/e10/film_pass.py e10_pass_5km_sqrt_s0 --tile-only           # runs/e10_films/<run>_tile.mp4: only the tile, centred on black

--tile-only: each frame is the walker's tile alone (same image, same 720 px), centred on black; same timing, no text, maps or plots,
no contact sheet. Works with --preview too.

Left: the chosen tile as the walker saw it (128 or 256 px, enlarged). Right, left column: the whole pass, north at the top, every cell at
its place (the world's own tiles, shrunk), with the track so far and the walker. Right, right column: a local map around the walker,
drawn from the world's tiles; its window follows the offer radius (smoothed), so offers stay visible at r_min and at r_max. The dashed
ring is this step's radius around where the walker stood when it was offered, the circles the offers (sized by their choice
probability, the chosen one filled), the line the last 60 steps. The film opens on the birth tile (held 4 steps long). Below: the step, where, when
the satellite saw this cell, the radius and drive over the walk so far.

The global film (analysis/e09/film.py) draws a world map; a 185 km strip on it would be a hairline, so the pass gets its own layout.
Films go to runs/e10_films/ (git-ignored); the contact sheet (every 25th step) to notes/10_landsat_pass/results/films/.
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
from data.tile_store import open_store  # noqa: E402

RUNS = ROOT / "runs"
FILMS = RUNS / "e10_films"
SHEETS = ROOT / "notes" / "10_landsat_pass" / "results" / "films"
W, H, TILE, PAD = 1280, 720, 720, 16
BG, INK, MUTED, FAINT = (18, 18, 17), (236, 235, 230), (150, 149, 143), (58, 58, 55)
TRACK, NOW, OFFER = (110, 160, 214), (235, 104, 52), (240, 200, 90)
MOSAIC_DEG = 0.009  # ~1 km per pixel: the overview and wide local windows are cut from this


def font(size: int) -> ImageFont.FreeTypeFont:
    for p in ("/System/Library/Fonts/SFNSMono.ttf", "/System/Library/Fonts/Menlo.ttc"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size=size)


class Geo:
    """Equirectangular frame of the pass: latitude down from the northern edge, longitude unwrapped around the pass's median."""

    def __init__(self, lat: np.ndarray, lon: np.ndarray, cell_deg: float) -> None:
        self.lon0 = float(np.median(lon))
        self.lat_max = float(lat.max()) + cell_deg
        self.lat_min = float(lat.min()) - cell_deg
        lw = self.unwrap(lon)
        cmax = cell_deg / np.cos(np.radians(np.abs(lat).max()))
        self.lw_min, self.lw_max = float(lw.min()) - cmax, float(lw.max()) + cmax

    def unwrap(self, lon):
        return (np.asarray(lon) - self.lon0 + 180.0) % 360.0 - 180.0


def mosaic(idx: pd.DataFrame, tiles: np.ndarray, geo: Geo, cell_deg: float, deg: float) -> np.ndarray:
    Hm = int(np.ceil((geo.lat_max - geo.lat_min) / deg))
    Wm = int(np.ceil((geo.lw_max - geo.lw_min) / deg))
    out = np.zeros((Hm, Wm, 3), np.uint8)
    out[:] = BG
    lat, lw = idx.lat.to_numpy(), geo.unwrap(idx.lon.to_numpy())
    sy = max(1, int(np.ceil(cell_deg / deg)))
    for i in range(len(idx)):
        sx = max(1, int(np.ceil(cell_deg / np.cos(np.radians(lat[i])) / deg)))
        t = np.asarray(Image.fromarray(np.asarray(tiles[i])).resize((sx, sy), Image.Resampling.BOX))
        y = int((geo.lat_max - lat[i]) / deg) - sy // 2
        x = int((lw[i] - geo.lw_min) / deg) - sx // 2
        out[max(y, 0) : y + sy, max(x, 0) : x + sx] = t[max(-y, 0) : Hm - y, max(-x, 0) : Wm - x]
    return out


class Strip:
    """A small time-series panel: drawn once in full, then revealed up to the current step."""

    def __init__(self, v: np.ndarray, lo: float, hi: float, log: bool, w: int, h: int, lines: dict[float, str], colour) -> None:
        self.w, self.h, self.n = w - 64, h, len(v)
        f = np.log if log else (lambda z: z)
        self.y = lambda z: h - 4 - (f(np.clip(z, lo, hi)) - f(lo)) / (f(hi) - f(lo)) * (h - 8)
        self.axes = Image.new("RGB", (w, h), BG)
        da = ImageDraw.Draw(self.axes)
        for val, txt in lines.items():
            yy = float(self.y(val))
            da.line([(0, yy), (self.w, yy)], fill=FAINT, width=1)
            da.text((self.w + 6, yy), txt, font=font(10), fill=MUTED, anchor="lm")
        self.full = self.axes.copy()
        xs = np.arange(self.n) / max(self.n - 1, 1) * (self.w - 1)
        ImageDraw.Draw(self.full).line(list(zip(xs, self.y(v))), fill=colour, width=2)

    def at(self, k: int) -> Image.Image:
        im = self.axes.copy()
        x = int(round(k / max(self.n - 1, 1) * (self.w - 1))) + 1
        im.paste(self.full.crop((0, 0, x, self.h)), (0, 0))
        ImageDraw.Draw(im).line([(x, 0), (x, self.h)], fill=MUTED, width=1)
        return im


def render(run: str, steps: int | None, sec_per_step: float, fps: int, preview: list[int] | None, tile_only: bool = False) -> Path:
    rd = RUNS / run
    cfg = yaml.safe_load((rd / "config.yaml").read_text())
    assert cfg.get("world") == "landsat_pass", f"{run}: not a Landsat pass walk (world: {cfg.get('world')})"
    store = open_store(cfg)
    idx, tiles, meta = store.idx, store.tiles, store.meta
    s = pd.read_parquet(rd / "steps.parquet")
    n = min(len(s), steps or len(s))
    s = s.iloc[:n].reset_index(drop=True)
    c = pd.read_parquet(rd / "candidates.parquet", columns=["step", "tile_idx", "chosen", "p"])
    c = c[c.step < n].join(idx[["lat", "lon"]], on="tile_idx")
    offers = {k: g for k, g in c.groupby("step")}
    r_min, r_max, delta = float(cfg["radius_min_km"]), float(cfg["radius_max_km"]), float(cfg["radius_delta"])
    cell_km = meta["cell_m"] / 1000.0
    cell_deg = cell_km / 111.0

    print(f"[film] {run}: mosaic of {len(idx)} tiles", flush=True)
    geo = Geo(idx.lat.to_numpy(), idx.lon.to_numpy(), cell_deg)
    mos = mosaic(idx, tiles, geo, cell_deg, MOSAIC_DEG)
    ov_h = H - 2 * PAD - 18
    ov_w = max(1, int(round(mos.shape[1] * ov_h / mos.shape[0])))
    overview = Image.fromarray(mos).resize((ov_w, ov_h), Image.Resampling.BOX)
    ov_scale = ov_h / (geo.lat_max - geo.lat_min)  # px per degree
    ox0, oy0 = TILE + PAD, PAD + 18
    loc_x = ox0 + ov_w + PAD
    LOC = W - PAD - loc_x  # square local panel
    track = overview.copy()
    tdraw = ImageDraw.Draw(track)

    def ov_xy(la, lo):
        return (geo.unwrap(lo) - geo.lw_min) * ov_scale, (geo.lat_max - la) * ov_scale

    lat_t, lon_t = idx.lat.to_numpy(), idx.lon.to_numpy()

    def local(la: float, lo: float, half_km: float) -> tuple[Image.Image, callable]:
        """The local map: a window of +-half_km around (la, lo), LOC px square, true local aspect."""
        dlat = half_km / 111.0
        dlon = dlat / np.cos(np.radians(la))
        lw_c = float(geo.unwrap(lo))

        def to_px(lat2, lon2):
            return (np.asarray(geo.unwrap(lon2)) - lw_c + dlon) / (2 * dlon) * LOC, (la + dlat - np.asarray(lat2)) / (2 * dlat) * LOC

        px_per_tile = cell_km / (2 * half_km) * LOC
        if px_per_tile < 10:  # wide window: a crop of the ~1 km mosaic
            y0 = (geo.lat_max - (la + dlat)) / MOSAIC_DEG
            x0 = (lw_c - dlon - geo.lw_min) / MOSAIC_DEG
            box = (int(x0), int(y0), int(x0 + 2 * dlon / MOSAIC_DEG), int(y0 + 2 * dlat / MOSAIC_DEG))
            im = Image.fromarray(mos).crop(box).resize((LOC, LOC), Image.Resampling.BILINEAR)
        else:  # close window: the world's own tiles, pasted at their places
            im = Image.new("RGB", (LOC, LOC), BG)
            near = np.flatnonzero((np.abs(lat_t - la) < dlat + cell_deg) & (np.abs(geo.unwrap(lon_t) - lw_c) < dlon + 2 * cell_deg))
            sz = int(np.ceil(px_per_tile)) + 1
            xs, ys = to_px(lat_t[near], lon_t[near])
            for i, x, y in zip(near, xs, ys):
                im.paste(Image.fromarray(np.asarray(tiles[i])).resize((sz, sz), Image.Resampling.LANCZOS), (int(round(x - sz / 2)), int(round(y - sz / 2))))
        return im, to_px

    radius = Strip(s.r_km.to_numpy(), r_min, r_max, True, LOC, 70, {r_min: f"{r_min:g} km", r_max: f"{r_max:g} km"}, OFFER)
    drive = Strip(np.nan_to_num(s.drive_d.to_numpy()), -1.0, 1.0, False, LOC, 70, {0.0: "0", -delta: "−Δ"}, TRACK)
    f_big, f_mid, f_small = font(18), font(13), font(11)
    info = meta.get("pass_info", {})
    caption = f"Landsat 1 MSS · {info.get('date', '')} · path {info.get('path', '')} · {meta['cell_m'] / 1000:.2f} km cells · {meta['render']}, {meta.get('tone', 'linear')}"

    FILMS.mkdir(parents=True, exist_ok=True)
    path = FILMS / f"{run}{'_tile' if tile_only else ''}.mp4"
    reps = max(1, int(round(sec_per_step * fps)))
    ff = None
    if not preview:
        ff = subprocess.Popen(["nice", "-n", "10", "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
                               "-c:v", "h264_videotoolbox", "-b:v", "8M", "-pix_fmt", "yuv420p", str(path)], stdin=subprocess.PIPE)
    import json

    start = int(json.loads((rd / "meta.json").read_text())["start_tile"])
    lat, lon, r, d = s.lat.to_numpy(), s.lon.to_numpy(), s.r_km.to_numpy(), s.drive_d.to_numpy()
    # a step's row holds the cell chosen; its offers were made from where the walker stood before: the previous row, or the birth cell
    lat0 = np.concatenate([[lat_t[start]], lat[:-1]])
    lon0 = np.concatenate([[lon_t[start]], lon[:-1]])
    tiles_at = s.tile_idx.to_numpy().astype(int)
    from data.tile_store import haversine_km

    moved = haversine_km(lat0, lon0, lat, lon)  # steps.parquet logs dist_km 0 at step 0 by convention; the film shows the real move
    half = max(2.4 * r[0], 4 * cell_km)
    kept = {}
    for k in range(-1, n):  # k = -1: the birth, on the start tile, before any choice
        kb = max(k, 0)
        if k >= 0:
            qx, qy = ov_xy(lat0[k], lon0[k])
            px, py = ov_xy(lat[k], lon[k])
            tdraw.line([(qx, qy), (px, py)], fill=TRACK, width=1)
            half = 0.75 * half + 0.25 * max(2.4 * r[k], 4 * cell_km)  # the local window follows the radius, smoothed
        else:
            px, py = ov_xy(lat_t[start], lon_t[start])
        if preview and k not in preview:
            continue

        if tile_only:  # only the tile, centred on black; the same timing as the full film
            t = start if k < 0 else int(tiles_at[k])
            im = Image.new("RGB", (W, H), (0, 0, 0))
            im.paste(Image.fromarray(np.asarray(tiles[t])).resize((TILE, TILE), Image.Resampling.LANCZOS), ((W - TILE) // 2, 0))
            if preview:
                (FILMS / "preview").mkdir(parents=True, exist_ok=True)
                im.save(FILMS / "preview" / f"{run}_tile_{k:04d}.png")
                continue
            buf = im.tobytes()
            for _ in range(reps * (4 if k < 0 else 1)):  # the birth is held a little longer
                ff.stdin.write(buf)
            if k >= 0 and k % 50 == 0:
                print(f"[film] {run}: step {k}", flush=True)
            continue

        im = Image.new("RGB", (W, H), BG)
        t = start if k < 0 else int(tiles_at[k])
        im.paste(Image.fromarray(np.asarray(tiles[t])).resize((TILE, TILE), Image.Resampling.LANCZOS), (0, 0))
        dr = ImageDraw.Draw(im)
        dr.text((ox0, PAD - 4), caption, font=f_small, fill=MUTED)
        im.paste(track, (ox0, oy0))
        dr.ellipse([ox0 + px - 4, oy0 + py - 4, ox0 + px + 4, oy0 + py + 4], outline=NOW, width=2)

        loc, to_px = local(lat0[kb], lon0[kb], half)  # centred where the walker stood when the offers were made
        ld = ImageDraw.Draw(loc)
        if k >= 0:
            lo_ = max(0, k - 60)
            tx, ty = to_px(np.concatenate([[lat0[lo_]], lat[lo_ : k + 1]]), np.concatenate([[lon0[lo_]], lon[lo_ : k + 1]]))
            ld.line(list(zip(tx, ty)), fill=TRACK, width=2)
        cx, cy = LOC / 2, LOC / 2
        rr = r[kb] / (2 * half) * LOC
        for a0 in range(0, 360, 12):  # dashed ring at this step's radius
            ld.arc([cx - rr, cy - rr, cx + rr, cy + rr], a0, a0 + 6, fill=MUTED, width=1)
        o = offers.get(k) if k >= 0 else None
        if o is not None:
            ox, oy = to_px(o.lat.to_numpy(), o.lon.to_numpy())
            for a, b, ch, p in zip(ox, oy, o.chosen.to_numpy(), o.p.to_numpy()):
                rad = 3 + 9 * float(p) ** 0.5
                ld.ellipse([a - rad, b - rad, a + rad, b + rad], outline=OFFER, width=2, fill=OFFER if ch else None)
        ld.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], outline=NOW, width=2)
        im.paste(loc, (loc_x, oy0))
        dr.rectangle([loc_x, oy0, loc_x + LOC - 1, oy0 + LOC - 1], outline=FAINT)
        lab = f"window {2 * half:,.0f} km"
        dr.rectangle([loc_x + 1, oy0 + LOC - 18, loc_x + 8 + 7 * len(lab), oy0 + LOC - 2], fill=BG)
        dr.text((loc_x + 4, oy0 + LOC - 16), lab, font=f_small, fill=INK)

        y = oy0 + LOC + 12
        row = idx.iloc[t]
        la_, lo_t = lat_t[t], lon_t[t]
        head = f"born on tile {t}" if k < 0 else f"step {k:>3}"
        dr.text((loc_x, y), f"{head}  {abs(la_):.2f}°{'N' if la_ >= 0 else 'S'} {abs(lo_t):.2f}°{'E' if lo_t >= 0 else 'W'}", font=f_big, fill=INK)
        if k >= 0:
            state = "far" if r[k] >= r_max - 0.5 else ("near" if r[k] <= r_min + 0.01 else "widening")
            dr.text((loc_x, y + 26), f"radius {r[k]:5.1f} km  {state}  moved {moved[k]:.0f} km", font=f_mid, fill=NOW if state == "far" else INK)
            dr.text((loc_x, y + 44), f"drive {0.0 if np.isnan(d[k]) else d[k]:+.2f}  novelty {s.n.iloc[k]:.3f}", font=f_mid, fill=INK)
        else:
            dr.text((loc_x, y + 26), "the first cell the satellite imaged", font=f_mid, fill=INK)
        dr.text((loc_x, y + 62), f"seen {pd.Timestamp(row.timestamp):%H:%M:%S} UTC · row {row.wrs_row}", font=f_small, fill=MUTED)
        dr.text((loc_x, y + 77), f"cloud {row.cloud_cover:.0f} % · stripe {100 * row.stripe:.0f} % · {row.cover}", font=f_small, fill=MUTED)
        y2 = y + 98
        dr.text((loc_x, y2), "offer radius (log)", font=f_small, fill=MUTED)
        im.paste(radius.at(kb), (loc_x, y2 + 14))
        dr.text((loc_x, y2 + 90), "drive: short minus long average", font=f_small, fill=MUTED)
        im.paste(drive.at(kb), (loc_x, y2 + 104))

        if preview:
            (FILMS / "preview").mkdir(parents=True, exist_ok=True)
            im.save(FILMS / "preview" / f"{run}_{k:04d}.png")
            continue
        buf = im.tobytes()
        for _ in range(reps * (4 if k < 0 else 1)):  # the birth is held a little longer
            ff.stdin.write(buf)
        if k >= 0 and k % 25 == 0:
            kept[k] = im.resize((W // 4, H // 4), Image.Resampling.LANCZOS)
        if k >= 0 and k % 50 == 0:
            print(f"[film] {run}: step {k}", flush=True)
    if preview:
        print(f"[film] previews in {FILMS / 'preview'}")
        return FILMS / "preview"
    ff.stdin.close()
    ff.wait()
    print(f"[film] {path}: {n} steps, {(n + 4) * reps / fps:.0f} s, {path.stat().st_size / 1e6:.0f} MB", flush=True)
    if tile_only:  # no contact sheet in this mode
        return path
    ks = sorted(kept)
    w, h = kept[ks[0]].size
    cols = 4
    sheet = Image.new("RGB", (cols * w, -(-len(ks) // cols) * h), BG)
    for j, k in enumerate(ks):
        sheet.paste(kept[k], ((j % cols) * w, (j // cols) * h))
    SHEETS.mkdir(parents=True, exist_ok=True)
    sheet.save(SHEETS / f"{run}_contact.png", optimize=True)
    print(f"[film] contact sheet {SHEETS / f'{run}_contact.png'}")
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--steps", type=int, default=None, help="film only the first N steps")
    ap.add_argument("--sec-per-step", type=float, default=0.3)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--preview", type=int, nargs="+", help="save these steps as PNG in runs/e10_films/preview/, and no film")
    ap.add_argument("--tile-only", action="store_true", help="only the walker's tile, centred on black; writes <run>_tile.mp4, no contact sheet")
    a = ap.parse_args()
    render(a.run, a.steps, a.sec_per_step, a.fps, a.preview, a.tile_only)


if __name__ == "__main__":
    main()
