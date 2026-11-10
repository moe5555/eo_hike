"""Step-by-step viewer of a compass walk (experiment 09): a folder with index.html and the tiles as JPEGs beside it.

    python analysis/e09/walk_viewer.py [run] [--out DIR] [--px 256] [--quality 82]     # default run e09_v1_long_s0

Writes <run>/viewer/index.html (or DIR/index.html) and viewer/tiles/<tile_idx>.jpg, one per tile stood on: the 256 px low-res
the walker saw. The tiles are files, not embedded: 10,000 tiles would make one page of 200+ MB. Open index.html in a browser
from the folder (file:// works). Tiles already written are not written again, so rebuilding after the world-view pass is quick.

The page shows, per step:
- the tile stood on, its place in the walk (cell, visit, cover, distance moved), and the signals: novelty n and its z, progress
  g and its z, interest I, the drive d and its two averages, and the radius it set;
- the world map with the path so far, coloured by the radius of the step (r_min, between, r_max);
- the compass: the eight offers of the step around the walker's last position, sized by their choice probability, the chosen
  one ringed;
- a timeline of the whole walk (radius, drive, chosen novelty, held-out error, new cell or return) with a zoomed window around
  the cursor; click or drag to seek;
- a filmstrip of the steps around the cursor;
- the per-block readouts of analysis/e09/long_walk.py and the world-view readouts per checkpoint, where those files exist.

Keys: <-/-> step, Shift = 10, PgUp/PgDn = 100, Home/End, Space play, +/- speed, F / Shift+F next / previous bout at r_max,
R next return to a cell left 100+ steps before, M map zoom (world / whole path / last 300 steps).
"""

from __future__ import annotations

import argparse
import base64
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from e09_common import OUT, RUNS  # sets sys.path
from fetchcost import continent
from PIL import Image

WORLD_W = 4096  # land raster, 0.088 deg per pixel (about 10 km at the equator)


def land_png() -> str:
    from global_land_mask import globe

    H = WORLD_W // 2
    lo = -180 + (np.arange(WORLD_W) + 0.5) * 360 / WORLD_W
    la = 90 - (np.arange(H) + 0.5) * 180 / H
    LO, LA = np.meshgrid(lo, np.clip(la, -89.99, 89.99))
    land = globe.is_land(LA, LO)
    rgb = np.where(land[..., None], np.array([222, 220, 210], np.uint8), np.array([236, 242, 247], np.uint8))
    buf = io.BytesIO()
    Image.fromarray(rgb.astype(np.uint8)).save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def write_tiles(ids: list[int], folder: Path, px: int, quality: int) -> int:
    from tqdm import tqdm

    from data.tile_store import TileStore

    folder.mkdir(parents=True, exist_ok=True)
    todo = [i for i in ids if not (folder / f"{i}.jpg").exists()]
    if not todo:
        return 0
    store = TileStore(cache_gb=30)
    failed = set(store.fetch_all(todo, desc="fetch evicted tiles"))
    if failed:
        print(f"[viewer] {len(failed)} tiles could not be fetched and are shown blank: {sorted(failed)[:10]}")
    for i in tqdm([i for i in todo if i not in failed], desc="tiles"):
        im = Image.fromarray(np.asarray(store.get_lowres(i), dtype=np.uint8))
        if im.size != (px, px):
            im = im.resize((px, px), Image.Resampling.LANCZOS)
        im.save(folder / f"{i}.jpg", "JPEG", quality=quality)
    return len(todo) - len(failed)


def rnd(v, d: int) -> list:
    v = np.asarray(v, dtype=np.float64)
    return [None if not np.isfinite(x) else round(float(x), d) for x in v]


def build(run: str, out: Path, px: int, quality: int) -> Path:
    rd = RUNS / run
    cfg = yaml.safe_load((rd / "config.yaml").read_text())
    s = pd.read_parquet(rd / "steps.parquet").reset_index(drop=True)
    c = pd.read_parquet(rd / "candidates.parquet", columns=["step", "tile_idx", "n", "n_z", "g_z", "I", "p", "chosen"])
    h = pd.read_parquet(rd / "heldout.parquet")
    ix = pd.read_parquet(Path(__file__).resolve().parents[2] / "data" / "global" / "index.parquet", columns=["idx", "lat", "lon"]).set_index("idx")
    c = c.join(ix, on="tile_idx").sort_values(["step", "p"], ascending=[True, False])
    ids = list(dict.fromkeys(map(int, s.tile_idx)))
    n_new = write_tiles(ids, out / "tiles", px, quality)

    cells = s.grid_cell.to_numpy()
    first_seen: dict = {}
    last_seen: dict = {}
    visit, gap = np.zeros(len(s), int), np.full(len(s), -1)
    for i, cl in enumerate(cells):
        first_seen.setdefault(cl, i)
        visit[i] = (visit[last_seen[cl]] + 1) if cl in last_seen else 1
        gap[i] = i - last_seen[cl] if cl in last_seen else -1
        last_seen[cl] = i
    cont = continent(s.lat, s.lon)
    seen_c: set = set()
    new_cont = []
    for i, k in enumerate(cont):
        if k not in seen_c:
            seen_c.add(k)
            new_cont.append([i, str(k)])

    off = c.groupby("step")
    o_start = np.zeros(len(s) + 1, int)
    sizes = off.size().reindex(s.step, fill_value=0).to_numpy()
    o_start[1:] = np.cumsum(sizes)
    blocks = OUT / "long_walk_blocks.csv"
    wv = OUT / "worldview.csv"
    W = pd.read_csv(wv) if wv.exists() else pd.DataFrame(columns=["run"])
    W = W[W.run == run].sort_values("step") if len(W) else W
    data = {
        "run": run, "steps_n": len(s), "px": px,
        "cfg": {k: cfg.get(k) for k in ("drive_signal", "radius_min_km", "radius_max_km", "radius_delta", "crop_px", "drive_warmup", "start_lat", "start_lon", "seed", "w_n", "w_g")},
        "land": land_png(),
        "s": {"tile": s.tile_idx.astype(int).tolist(), "cell": s.grid_cell.tolist(), "lat": rnd(s.lat, 4), "lon": rnd(s.lon, 4),
              "r": rnd(s.r_km, 1), "d": rnd(s.drive_d, 3), "ds": rnd(s.drive_short, 3), "dl": rnd(s.drive_long, 3),
              "n": rnd(s.n, 4), "nz": rnd(s.n_z, 2), "g": rnd(s.g, 6), "gz": rnd(s.g_z, 2), "I": rnd(s.I, 2), "maxI": rnd(s.max_I, 2),
              "dist": rnd(s.dist_km, 1), "cover": s.cover.astype(str).tolist(), "cloud": rnd(s.cloud_cover, 1),
              "err": rnd(s.err_after, 5), "visit": visit.tolist(), "gap": gap.tolist(), "cont": [str(k) for k in cont],
              "noff": sizes.tolist(), "drop": s.n_dropped.astype(int).tolist()},
        "o": {"start": o_start.tolist(), "lat": rnd(c.lat, 3), "lon": rnd(c.lon, 3), "p": rnd(c.p, 3), "n": rnd(c.n, 4),
              "nz": rnd(c.n_z, 2), "gz": rnd(c.g_z, 2), "chosen": c.chosen.astype(int).tolist()},
        "held": {"step": h.step.astype(int).tolist(), "mse": rnd(h.heldout_mse, 5)},
        "new_cont": new_cont,
        "blocks": json.loads(pd.read_csv(blocks).to_json(orient="records")) if blocks.exists() and run == "e09_v1_long_s0" else [],
        "wv": json.loads(W[[k for k in ("step", "probe_bacc", "probe_r2", "tobler_rho", "plateau_km", "knn_geo_excess", "colour_probe_bacc", "init_probe_bacc") if k in W]].to_json(orient="records")) if len(W) else [],
    }
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    out.mkdir(parents=True, exist_ok=True)
    page = out / "index.html"
    page.write_text(PAGE.replace("__TITLE__", f"{run}: the walk").replace("__DATA__", blob), encoding="utf-8")
    size = sum(f.stat().st_size for f in (out / "tiles").glob("*.jpg")) / 1e6
    print(f"[viewer] {page}  (page {page.stat().st_size / 1e6:.1f} MB, {len(ids):,} tiles {size:.0f} MB, {n_new} written now, {len(s):,} steps)")
    return page


PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>__TITLE__</title>
<style>
  :root { --bg:#f4f4f1; --panel:#fcfcfb; --ink:#0b0b0b; --muted:#52514e; --faint:#8a8984; --line:#e3e2dc; --grid:#ecebe6;
          --near:#2a78d6; --mid:#1baf7a; --far:#eb6834; --cursor:#0b0b0b; --path:#9a9890; }
  * { box-sizing:border-box; }
  body { margin:0; font:13px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif; color:var(--ink); background:var(--bg); }
  header { padding:10px 18px; display:flex; gap:22px; align-items:baseline; flex-wrap:wrap; border-bottom:1px solid var(--line); background:var(--panel); }
  header h1 { font-size:16px; margin:0; }
  .muted { color:var(--muted); }
  .wrap { padding:12px 18px; display:flex; flex-direction:column; gap:12px; }
  .row { display:grid; gap:12px; align-items:start; }
  .r1 { grid-template-columns: 400px minmax(420px,1fr); }
  .r2 { grid-template-columns: 400px minmax(420px,1fr); }
  .card { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:10px; min-width:0; }
  .card h2 { font-size:12px; font-weight:600; margin:0 0 6px; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; display:flex; justify-content:space-between; align-items:baseline; }
  #tile { width:378px; height:378px; display:block; background:#ddd; border-radius:4px; image-rendering:auto; }
  canvas { display:block; width:100%; }
  table { border-collapse:collapse; width:100%; }
  td { padding:2px 6px; border-bottom:1px solid var(--grid); vertical-align:top; font-variant-numeric:tabular-nums; }
  td:first-child { color:var(--muted); width:46%; }
  .controls { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
  button, select { font:inherit; padding:3px 9px; border:1px solid var(--line); border-radius:5px; background:#fff; cursor:pointer; color:var(--ink); }
  button:hover { border-color:#b9bcc2; }
  input[type=range] { flex:1; min-width:200px; }
  .key { display:inline-flex; align-items:center; gap:5px; margin-right:12px; color:var(--muted); }
  .sw { width:10px; height:10px; border-radius:2px; display:inline-block; }
  #film { display:flex; gap:4px; overflow:hidden; }
  #film figure { margin:0; flex:0 0 auto; text-align:center; cursor:pointer; }
  #film img { width:84px; height:84px; display:block; border-radius:3px; border:2px solid transparent; background:#ddd; }
  #film figure.cur img { border-color:var(--cursor); }
  #film figcaption { font-size:11px; color:var(--muted); }
  #tip { position:fixed; pointer-events:none; background:#fff; border:1px solid var(--line); border-radius:6px; padding:5px 8px; font-size:12px;
         box-shadow:0 2px 8px rgba(0,0,0,.08); display:none; z-index:9; font-variant-numeric:tabular-nums; }
  .tbl { max-height:360px; overflow:auto; }
  .tbl table td, .tbl table th { font-size:12px; padding:2px 5px; text-align:right; white-space:nowrap; }
  .tbl table th { position:sticky; top:0; background:var(--panel); color:var(--muted); font-weight:500; border-bottom:1px solid var(--line); }
  .tbl table td:first-child { width:auto; color:var(--ink); }
  .help { color:var(--muted); font-size:12px; }
</style>
</head>
<body>
<header>
  <h1 id="title"></h1>
  <span class="muted" id="summary"></span>
</header>
<div class="wrap">
  <div class="card">
    <div class="controls">
      <button id="play">▶ play</button>
      <select id="speed"></select>
      <button id="prevfar" title="Shift+F">◀ far bout</button><button id="nextfar" title="F">far bout ▶</button>
      <button id="nextret" title="R">return ▶</button>
      <input type="range" id="slider" min="0" value="0">
      <b id="stepno"></b>
    </div>
    <div class="help" style="margin-top:4px">←/→ step · Shift ×10 · PgUp/PgDn ×100 · Home/End · Space play · +/− speed · F / Shift+F far bout · R next return to a cell left 100+ steps before · M map zoom. Click the map or the timeline to jump.</div>
  </div>
  <div class="row r1">
    <div class="card">
      <h2><span>Tile stood on</span><span id="tilecap" class="muted" style="text-transform:none;letter-spacing:0"></span></h2>
      <img id="tile" alt="">
      <table id="info" style="margin-top:8px"></table>
    </div>
    <div class="card">
      <h2><span>The path</span><span><button id="zoom">world</button></span></h2>
      <canvas id="map"></canvas>
      <div style="margin-top:6px"><span class="key"><span class="sw" style="background:var(--near)"></span>step at r_min</span><span class="key"><span class="sw" style="background:var(--mid)"></span>between</span><span class="key"><span class="sw" style="background:var(--far)"></span>at r_max</span><span class="key"><span class="sw" style="background:var(--cursor);border-radius:50%"></span>now</span></div>
    </div>
  </div>
  <div class="row r2">
    <div class="card">
      <h2><span>The compass: this step's offers</span></h2>
      <canvas id="rose"></canvas>
      <div class="help">The eight offers around the last position, at the radius the drive set. Area ∝ choice probability; colour = novelty of the offer (light = familiar, dark = new); ringed = chosen. Distances to scale.</div>
    </div>
    <div class="card">
      <h2><span>The whole walk</span><span class="muted" style="text-transform:none;letter-spacing:0">upper: all steps · lower: ±250 steps around the cursor</span></h2>
      <canvas id="tl"></canvas>
      <canvas id="tlz" style="margin-top:6px"></canvas>
      <div style="margin-top:6px"><span class="key"><span class="sw" style="background:var(--near)"></span>r_min</span><span class="key"><span class="sw" style="background:var(--mid)"></span>between</span><span class="key"><span class="sw" style="background:var(--far)"></span>r_max</span><span class="key">- - - d = −Δ (r_max below it)</span><span class="key"><span class="sw" style="background:#52514e"></span>new cell</span><span class="key"><span class="sw" style="background:#6250d6"></span>return after 100+ steps</span><span class="key"><span class="sw" style="background:rgba(110,108,100,.22)"></span>return within 100</span></div>
    </div>
  </div>
  <div class="card"><h2><span>Filmstrip</span></h2><div id="film"></div></div>
  <div class="row" style="grid-template-columns:1fr 1fr" id="extra"></div>
</div>
<div id="tip"></div>
<script>
const D = __DATA__;
const S = D.s, O = D.o, N = D.steps_n, C = D.cfg;
const RMIN = C.radius_min_km, RMAX = C.radius_max_km;
const css = getComputedStyle(document.documentElement);
const col = k => css.getPropertyValue('--' + k).trim();
const COL = { near: col('near'), mid: col('mid'), far: col('far'), ink: col('ink'), muted: col('muted'), faint: col('faint'), grid: col('grid'), line: col('line'), path: col('path') };
const rk = r => Math.abs(r - RMIN) < 0.01 ? 'near' : (Math.abs(r - RMAX) < 0.01 ? 'far' : 'mid');
const fmt = (v, d = 3) => v === null || v === undefined ? '—' : (typeof v === 'number' ? v.toFixed(d) : v);
const km = v => v === null ? '—' : (v >= 100 ? Math.round(v).toLocaleString('en') : v.toFixed(1)) + ' km';

// --- derived
const farStart = [];
for (let i = 0; i < N; i++) if (rk(S.r[i]) === 'far' && (i === 0 || rk(S.r[i - 1]) !== 'far')) farStart.push(i);
const unique = new Set(S.cell).size;
const shareFar = S.r.filter(r => rk(r) === 'far').length / N;
document.getElementById('title').textContent = D.run;
document.getElementById('summary').textContent =
  `${N.toLocaleString('en')} steps · ${unique.toLocaleString('en')} cells · ${new Set(S.tile).size.toLocaleString('en')} tiles · ${farStart.length} bouts at r_max (${(100 * shareFar).toFixed(1)} % of steps) · ` +
  `drive ${C.drive_signal}, r ${RMIN}–${RMAX} km, Δ ${C.radius_delta}, eye ${C.crop_px} px · continents in order: ${D.new_cont.map(c => c[1] + ' (' + c[0] + ')').join(', ')}`;

// --- state
let cur = 0, playing = false, speedI = 3, zoomMode = 'world';
const SPEEDS = [1, 2, 5, 10, 25, 50, 100, 250];
const speedSel = document.getElementById('speed');
SPEEDS.forEach((v, i) => { const o = document.createElement('option'); o.value = i; o.textContent = v + ' steps/s'; speedSel.appendChild(o); });
speedSel.value = speedI;
speedSel.onchange = () => { speedI = +speedSel.value; };
const slider = document.getElementById('slider'); slider.max = N - 1;
slider.oninput = () => go(+slider.value);

// --- canvas helper (hi-dpi)
function prep(cv, h) {
  const dpr = window.devicePixelRatio || 1, w = cv.clientWidth;
  if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); cv.style.height = h + 'px'; }
  const g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); return [g, w, h];
}

// --- world map
const land = new Image(); land.src = D.land; land.onload = () => draw();
const mapCv = document.getElementById('map');
function mapView() {
  if (zoomMode === 'world') return { lon0: -180, lon1: 180, lat0: -78, lat1: 84 };
  let la0 = 90, la1 = -90, lo0 = 180, lo1 = -180;
  const a = zoomMode === 'path' ? 0 : Math.max(0, cur - 300);
  for (let i = a; i <= cur; i++) { la0 = Math.min(la0, S.lat[i]); la1 = Math.max(la1, S.lat[i]); lo0 = Math.min(lo0, S.lon[i]); lo1 = Math.max(lo1, S.lon[i]); }
  if (zoomMode === 'path') { for (let i = cur; i < N; i++) { la0 = Math.min(la0, S.lat[i]); la1 = Math.max(la1, S.lat[i]); lo0 = Math.min(lo0, S.lon[i]); lo1 = Math.max(lo1, S.lon[i]); } }
  const pad = Math.max(1.5, (la1 - la0) * 0.12, (lo1 - lo0) * 0.06);
  return { lon0: lo0 - pad * 2, lon1: lo1 + pad * 2, lat0: la0 - pad, lat1: la1 + pad };
}
let mapProj = null;
function drawMap() {
  const w = mapCv.clientWidth, v0 = mapView();
  // keep aspect 2:1 in degrees (equirectangular)
  let v = { ...v0 }, wd = v.lon1 - v.lon0, ht = v.lat1 - v.lat0;
  if (wd < 2 * ht) { const e = (2 * ht - wd) / 2; v.lon0 -= e; v.lon1 += e; } else { const e = (wd / 2 - ht) / 2; v.lat0 -= e; v.lat1 += e; }
  const h = Math.round(w / 2);
  const [g] = prep(mapCv, h);
  const X = lo => (lo - v.lon0) / (v.lon1 - v.lon0) * w, Y = la => (v.lat1 - la) / (v.lat1 - v.lat0) * h;
  mapProj = { X, Y, w, h };
  g.fillStyle = '#ecf2f7'; g.fillRect(0, 0, w, h);
  if (land.complete) {
    const sx = (v.lon0 + 180) / 360 * land.width, sw = (v.lon1 - v.lon0) / 360 * land.width;
    const sy = (90 - v.lat1) / 180 * land.height, sh = (v.lat1 - v.lat0) / 180 * land.height;
    g.imageSmoothingEnabled = zoomMode === 'world';
    g.drawImage(land, sx, sy, sw, sh, 0, 0, w, h);
  }
  // path so far: older steps faint grey, last 500 in radius colour
  const recent = Math.max(0, cur - 500);
  g.lineWidth = 1; g.strokeStyle = 'rgba(110,108,100,.35)'; g.beginPath();
  for (let i = 1; i <= recent; i++) {
    if (Math.abs(S.lon[i] - S.lon[i - 1]) > 180) { g.moveTo(X(S.lon[i]), Y(S.lat[i])); continue; }
    if (i === 1) g.moveTo(X(S.lon[0]), Y(S.lat[0]));
    g.lineTo(X(S.lon[i]), Y(S.lat[i]));
  }
  g.stroke();
  g.lineWidth = 1.6;
  for (let i = Math.max(1, recent); i <= cur; i++) {
    if (Math.abs(S.lon[i] - S.lon[i - 1]) > 180) continue;
    g.strokeStyle = COL[rk(S.r[i])]; g.globalAlpha = 0.35 + 0.65 * (i - recent) / Math.max(1, cur - recent);
    g.beginPath(); g.moveTo(X(S.lon[i - 1]), Y(S.lat[i - 1])); g.lineTo(X(S.lon[i]), Y(S.lat[i])); g.stroke();
  }
  g.globalAlpha = 1;
  // start, now
  g.fillStyle = '#fff'; g.strokeStyle = COL.ink; g.lineWidth = 1.5;
  g.beginPath(); g.rect(X(S.lon[0]) - 4, Y(S.lat[0]) - 4, 8, 8); g.fill(); g.stroke();
  g.beginPath(); g.arc(X(S.lon[cur]), Y(S.lat[cur]), 5.5, 0, 7); g.fillStyle = COL.ink; g.fill();
  g.beginPath(); g.arc(X(S.lon[cur]), Y(S.lat[cur]), 7.5, 0, 7); g.strokeStyle = '#fff'; g.lineWidth = 2; g.stroke();
}
mapCv.addEventListener('click', e => {
  if (!mapProj) return;
  const rc = mapCv.getBoundingClientRect(), x = e.clientX - rc.left, y = e.clientY - rc.top;
  let best = -1, bd = 1e9;
  for (let i = 0; i < N; i++) { const dx = mapProj.X(S.lon[i]) - x, dy = mapProj.Y(S.lat[i]) - y, dd = dx * dx + dy * dy; if (dd < bd) { bd = dd; best = i; } }
  if (best >= 0 && bd < 400) go(best);
});
document.getElementById('zoom').onclick = cycleZoom;
function cycleZoom() { zoomMode = { world: 'path', path: 'follow', follow: 'world' }[zoomMode]; document.getElementById('zoom').textContent = zoomMode === 'path' ? 'whole path' : zoomMode === 'follow' ? 'last 300 steps' : 'world'; draw(); }

// --- compass rose (local azimuthal-equidistant, km)
const roseCv = document.getElementById('rose');
function novCol(nz) { // novelty z of the offer: light (familiar) to dark (new), one hue
  const t = Math.max(0, Math.min(1, (nz + 2) / 4));
  const a = [214, 230, 248], b = [16, 62, 130];
  return `rgb(${a.map((v, k) => Math.round(v + (b[k] - v) * t)).join(',')})`;
}
function drawRose() {
  const [g, w, h] = prep(roseCv, 378);
  g.clearRect(0, 0, w, h);
  const ref = cur > 0 ? cur - 1 : 0;
  const la0 = cur > 0 ? S.lat[ref] : C.start_lat, lo0 = cur > 0 ? S.lon[ref] : C.start_lon;
  const a = O.start[cur], b = O.start[cur + 1];
  const R = 6371.0088, rad = Math.PI / 180;
  const proj = (la, lo) => { // azimuthal equidistant around (la0, lo0): km east, km north
    const p1 = la0 * rad, p2 = la * rad, dl = (lo - lo0) * rad;
    const c = Math.acos(Math.min(1, Math.max(-1, Math.sin(p1) * Math.sin(p2) + Math.cos(p1) * Math.cos(p2) * Math.cos(dl))));
    const az = Math.atan2(Math.sin(dl) * Math.cos(p2), Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl));
    return [R * c * Math.sin(az), R * c * Math.cos(az)];
  };
  const r = S.r[cur], scale = (Math.min(w, h) / 2 - 26) / (r * 1.3);
  const cx = w / 2, cy = h / 2, P = ([x, y]) => [cx + x * scale, cy - y * scale];
  // earlier steps within view
  g.fillStyle = 'rgba(110,108,100,.28)';
  for (let i = Math.max(0, cur - 3000); i < cur; i++) {
    if (Math.abs(S.lat[i] - la0) > r / 80 + 1) continue;
    const q = P(proj(S.lat[i], S.lon[i]));
    if (q[0] < 0 || q[0] > w || q[1] < 0 || q[1] > h) continue;
    g.fillRect(q[0] - 1.5, q[1] - 1.5, 3, 3);
  }
  // ring at r, cross
  g.strokeStyle = COL.line; g.lineWidth = 1; g.setLineDash([3, 3]);
  g.beginPath(); g.arc(cx, cy, r * scale, 0, 7); g.stroke(); g.setLineDash([]);
  g.fillStyle = COL.muted; g.font = '11px system-ui'; g.textAlign = 'left';
  g.fillText('dashed ring: r = ' + km(r) + (cur === 0 ? '' : ' · moved ' + km(S.dist[cur])), 4, 12);
  g.textAlign = 'center'; g.fillText('N', cx, cy - r * scale - 6);
  // offers
  for (let k = a; k < b; k++) {
    const q = P(proj(O.lat[k], O.lon[k])), rr = 4 + 22 * Math.sqrt(O.p[k] || 0);
    g.beginPath(); g.moveTo(cx, cy); g.lineTo(q[0], q[1]); g.strokeStyle = 'rgba(80,80,80,.18)'; g.lineWidth = 1; g.stroke();
    g.beginPath(); g.arc(q[0], q[1], rr, 0, 7); g.fillStyle = novCol(O.nz[k]); g.fill();
    g.strokeStyle = '#fcfcfb'; g.lineWidth = 2; g.stroke();
    if (O.chosen[k]) { g.beginPath(); g.arc(q[0], q[1], rr + 4, 0, 7); g.strokeStyle = COL.ink; g.lineWidth = 2; g.stroke(); }
    g.fillStyle = COL.muted; g.textAlign = 'center';
    g.fillText(Math.round(100 * O.p[k]) + '%', q[0], q[1] + rr + (O.chosen[k] ? 16 : 12));
  }
  g.beginPath(); g.arc(cx, cy, 5, 0, 7); g.fillStyle = COL.ink; g.fill();
  roseCv._hit = { a, b, P, proj };
}
roseCv.addEventListener('mousemove', e => {
  const H = roseCv._hit; if (!H) return;
  const rc = roseCv.getBoundingClientRect(), x = e.clientX - rc.left, y = e.clientY - rc.top;
  let best = -1, bd = 900;
  for (let k = H.a; k < H.b; k++) { const q = H.P(H.proj(O.lat[k], O.lon[k])), dd = (q[0] - x) ** 2 + (q[1] - y) ** 2; if (dd < bd) { bd = dd; best = k; } }
  if (best < 0) return hideTip();
  showTip(e, `<b>offer${O.chosen[best] ? ' (chosen)' : ''}</b><br>p ${fmt(O.p[best], 3)}<br>novelty n ${fmt(O.n[best], 4)} (z ${fmt(O.nz[best], 2)})<br>progress z ${fmt(O.gz[best], 2)}`);
});
roseCv.addEventListener('mouseleave', hideTip);

// --- timeline
const tl = document.getElementById('tl'), tlz = document.getElementById('tlz');
const lr = Math.log(RMAX / RMIN);
const held = D.held;
const TRACKS = [
  { name: 'radius (log)', h: 46, get: i => Math.log(S.r[i] / RMIN) / lr, lo: 0, hi: 1, kind: 'radius' },
  { name: 'drive d', h: 46, get: i => S.d[i], lo: -1.2, hi: 1.2, kind: 'line', ref: [-C.radius_delta, 0] },
  { name: 'chosen novelty n', h: 46, get: i => S.n[i], lo: 0, hi: null, kind: 'dots' },
  { name: 'held-out error', h: 40, kind: 'held' },
  { name: 'new cell / return', h: 14, kind: 'visit' },
];
let nHi = 0; { const v = S.n.filter(x => x !== null).slice().sort((a, b) => a - b); nHi = v[Math.floor(v.length * 0.99)] || 1; }
TRACKS[2].hi = nHi;
const LABW = 112;
const TLH = TRACKS.reduce((s, t) => s + t.h + 6, 0) + 14;
function drawTL(cv, a, b, big) {
  const H = TLH;
  let [g, w] = prep(cv, H);
  if (!big) { // the overview never changes: draw it once into an offscreen canvas, then only the cursor
    const dpr = window.devicePixelRatio || 1;
    if (!cv._cache || cv._cache.width !== cv.width) {
      const off = document.createElement('canvas'); off.width = cv.width; off.height = cv.height;
      const og = off.getContext('2d'); og.setTransform(dpr, 0, 0, dpr, 0, 0);
      drawStatic(og, w, H, a, b, false); cv._cache = off;
    }
    g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, cv.width, cv.height); g.drawImage(cv._cache, 0, 0); g.setTransform(dpr, 0, 0, dpr, 0, 0);
  } else { g.clearRect(0, 0, w, H); drawStatic(g, w, H, a, b, true); }
  overlay(g, w, H, a, b, big);
  cv._x = { a, b, w };
}
function drawStatic(g, w, H, a, b, big) {
  const X = i => LABW + (i - a) / Math.max(1, b - a) * (w - LABW - 8);
  let y = 2;
  g.font = '11px system-ui';
  for (const t of TRACKS) {
    g.fillStyle = COL.muted; g.textAlign = 'right'; g.fillText(t.name, LABW - 8, y + t.h / 2 + 4);
    g.strokeStyle = COL.grid; g.lineWidth = 1; g.beginPath(); g.moveTo(LABW, y + t.h + 0.5); g.lineTo(w - 8, y + t.h + 0.5); g.stroke();
    const Y = v => y + t.h - (Math.max(t.lo ?? 0, Math.min(t.hi ?? 1, v)) - (t.lo ?? 0)) / ((t.hi ?? 1) - (t.lo ?? 0)) * t.h;
    const step = Math.max(1, Math.floor((b - a) / (w * 2)));
    if (t.kind === 'held') { g.fillStyle = COL.muted; g.textAlign = 'right'; }
    if (t.kind === 'radius') {
      for (let i = a; i < b; i++) { const v = t.get(i); g.fillStyle = COL[rk(S.r[i])]; const x0 = X(i), x1 = Math.max(X(i + 1), x0 + 0.6), top = Math.min(Y(v), y + t.h - 3); g.fillRect(x0, top, x1 - x0, y + t.h - top); }
    } else if (t.kind === 'line') {
      for (const rv of t.ref) { g.strokeStyle = rv === 0 ? COL.line : COL.far; g.setLineDash(rv === 0 ? [] : [4, 3]); g.beginPath(); g.moveTo(LABW, Y(rv)); g.lineTo(w - 8, Y(rv)); g.stroke(); }
      g.setLineDash([]); g.strokeStyle = COL.ink; g.lineWidth = big ? 1.4 : 1; g.beginPath();
      for (let i = a; i < b; i += step) { const v = t.get(i); if (v === null) continue; i === a ? g.moveTo(X(i), Y(v)) : g.lineTo(X(i), Y(v)); }
      g.stroke();
    } else if (t.kind === 'dots') {
      g.fillStyle = 'rgba(42,120,214,.45)';
      for (let i = a; i < b; i++) { const v = t.get(i); if (v === null) continue; g.fillRect(X(i) - (big ? 1.5 : 0.5), Y(v) - (big ? 1.5 : 0.5), big ? 3 : 1, big ? 3 : 1); }
    } else if (t.kind === 'held') {
      const v = held.mse.filter(x => x !== null), hi = Math.max(...v), lo = Math.min(...v);
      const Yh = m => y + t.h - (m - lo) / Math.max(1e-12, hi - lo) * (t.h - 4) - 2;
      g.strokeStyle = COL.ink; g.lineWidth = 1.2; g.beginPath(); let st = false;
      held.step.forEach((s0, k) => { if (s0 < a || s0 > b || held.mse[k] === null) return; st ? g.lineTo(X(s0), Yh(held.mse[k])) : g.moveTo(X(s0), Yh(held.mse[k])); st = true; });
      g.stroke();
      g.fillStyle = COL.faint; g.textAlign = 'right'; g.fillText(hi.toFixed(4), LABW - 8, y + 9); g.fillText(lo.toFixed(4), LABW - 8, y + t.h);
    } else if (t.kind === 'visit') {
      for (let i = a; i < b; i++) { g.fillStyle = S.visit[i] === 1 ? '#52514e' : (S.gap[i] >= 100 ? '#6250d6' : 'rgba(110,108,100,.22)'); const x0 = X(i), x1 = Math.max(X(i + 1), x0 + 0.6); g.fillRect(x0, y + 2, x1 - x0, t.h - 4); }
    }
    y += t.h + 6;
  }
  // x ticks
  g.fillStyle = COL.faint; g.textAlign = 'center';
  const span = b - a, tk = span > 8000 ? 1000 : span > 2000 ? 500 : span > 400 ? 100 : 50;
  for (let s0 = Math.ceil(a / tk) * tk; s0 < b; s0 += tk) { g.fillText(s0.toLocaleString('en'), X(s0), H - 2); g.fillStyle = COL.faint; }
}
function overlay(g, w, H, a, b, big) {
  const X = i => LABW + (i - a) / Math.max(1, b - a) * (w - LABW - 8);
  // cursor
  if (cur >= a && cur < b) { g.strokeStyle = COL.ink; g.lineWidth = 1.5; g.beginPath(); g.moveTo(X(cur), 0); g.lineTo(X(cur), H - 14); g.stroke(); }
  // zoom window marker on the overview
  if (!big) { const za = Math.max(0, cur - 250), zb = Math.min(N, cur + 250); g.fillStyle = 'rgba(11,11,11,.06)'; g.fillRect(X(za), 0, X(zb) - X(za), H - 14); }
}
function tlStep(cv, e) { const m = cv._x, rc = cv.getBoundingClientRect(), x = e.clientX - rc.left; return Math.max(0, Math.min(N - 1, Math.round(m.a + (x - LABW) / (m.w - LABW - 8) * (m.b - m.a)))); }
for (const cv of [tl, tlz]) {
  let down = false;
  cv.addEventListener('mousedown', e => { down = true; go(tlStep(cv, e)); });
  window.addEventListener('mouseup', () => { down = false; });
  cv.addEventListener('mousemove', e => {
    const i = tlStep(cv, e);
    if (down) go(i);
    showTip(e, `step ${i.toLocaleString('en')}<br>r ${km(S.r[i])} · d ${fmt(S.d[i], 2)}<br>novelty ${fmt(S.n[i], 4)} · visit ${S.visit[i]}<br>${S.cont[i]} · ${S.cover[i]}`);
  });
  cv.addEventListener('mouseleave', hideTip);
}

// --- tooltip
const tip = document.getElementById('tip');
function showTip(e, html) { tip.innerHTML = html; tip.style.display = 'block'; tip.style.left = (e.clientX + 14) + 'px'; tip.style.top = (e.clientY + 12) + 'px'; }
function hideTip() { tip.style.display = 'none'; }

// --- tile, info, film
const tileImg = document.getElementById('tile');
const src = t => 'tiles/' + t + '.jpg';
function drawInfo() {
  const i = cur;
  tileImg.src = src(S.tile[i]);
  document.getElementById('tilecap').textContent = `${S.lat[i].toFixed(3)}°, ${S.lon[i].toFixed(3)}° · ${S.cover[i]}`;
  const rows = [
    ['step', `${i.toLocaleString('en')} of ${N.toLocaleString('en')}`],
    ['cell · visit', `${S.cell[i]} · ${S.visit[i] === 1 ? 'first visit' : 'visit ' + S.visit[i] + ', last ' + S.gap[i] + ' steps ago'}`],
    ['continent', S.cont[i]],
    ['moved', km(S.dist[i])],
    ['radius set for this step', `${km(S.r[i])} (${rk(S.r[i]) === 'near' ? 'r_min' : rk(S.r[i]) === 'far' ? 'r_max' : 'between'})`],
    ['drive d (short − long) / SD', `${fmt(S.d[i], 3)} (short ${fmt(S.ds[i], 2)}, long ${fmt(S.dl[i], 2)})`],
    ['novelty n (z)', `${fmt(S.n[i], 4)} (${fmt(S.nz[i], 2)})`],
    ['progress g (z)', `${S.g[i] === null ? '—' : S.g[i].toExponential(2)} (${fmt(S.gz[i], 2)})`],
    ['interest I (best offer)', `${fmt(S.I[i], 2)} (${fmt(S.maxI[i], 2)})`],
    ['error after training', S.err[i] === null ? '—' : S.err[i].toFixed(5)],
    ['offers · fetches dropped', `${S.noff[i]} · ${S.drop[i]}`],
  ];
  document.getElementById('info').innerHTML = rows.map(r => `<tr><td>${r[0]}</td><td>${r[1]}</td></tr>`).join('');
  document.getElementById('stepno').textContent = 'step ' + i.toLocaleString('en');
  slider.value = i;
}
const film = document.getElementById('film');
function drawFilm() {
  const w = film.clientWidth, n = Math.max(3, Math.floor(w / 88)), a = Math.max(0, Math.min(N - n, cur - Math.floor(n / 2)));
  let html = '';
  for (let i = a; i < Math.min(N, a + n); i++) html += `<figure data-i="${i}" class="${i === cur ? 'cur' : ''}"><img loading="lazy" src="${src(S.tile[i])}"><figcaption style="color:${COL[rk(S.r[i])]}">${i}${S.visit[i] > 1 ? ' ↺' : ''}</figcaption></figure>`;
  film.innerHTML = html;
}
film.addEventListener('click', e => { const f = e.target.closest('figure'); if (f) go(+f.dataset.i); });

// --- blocks and world-view
function extras() {
  const ex = document.getElementById('extra'); let html = '';
  if (D.blocks.length) {
    const ks = [['block_start', 'from', 0], ['share_rmax', 'at r_max', 3], ['rmax_episodes_per_1000', 'bouts', 0], ['places', 'places', 0], ['n_chosen_median', 'novelty', 4], ['onto_visited', 'returns', 2], ['new_cells', 'new cells', 0], ['cells_sofar', 'cells', 0], ['gyration_sofar_km', 'gyration km', 0], ['continents_sofar', 'continents', 0], ['heldout_end', 'held-out', 4], ['probe_bacc', 'land cover', 3], ['tobler_rho', 'Tobler ρ', 3]];
    html += `<div class="card"><h2><span>In blocks of 1,000 steps</span></h2><div class="tbl"><table><tr>${ks.map(k => `<th>${k[1]}</th>`).join('')}</tr>` +
      D.blocks.map(b => `<tr data-i="${b.block_start}" style="cursor:pointer">${ks.map(k => `<td>${b[k[0]] === undefined || b[k[0]] === null ? '—' : (+b[k[0]]).toFixed(k[2])}</td>`).join('')}</tr>`).join('') + '</table></div></div>';
  }
  if (D.wv.length) html += `<div class="card"><h2><span>What the walker knows, per checkpoint</span></h2><canvas id="wvc"></canvas><div style="margin-top:6px"><span class="key"><span class="sw" style="background:var(--near)"></span>land cover, balanced accuracy</span><span class="key"><span class="sw" style="background:var(--far)"></span>Tobler ρ (ground distance in the embedding)</span><span class="key"><span class="sw" style="background:#8a8984;height:2px"></span>colour and texture baseline (land cover)</span></div></div>`;
  ex.innerHTML = html;
  ex.querySelectorAll('tr[data-i]').forEach(tr => tr.onclick = () => go(+tr.dataset.i));
  if (D.wv.length) drawWV();
}
function drawWV() {
  const cv = document.getElementById('wvc'); const [g, w, h] = prep(cv, 220);
  const L = 40, R = 10, T = 10, B = 22, xs = D.wv.map(r => r.step), x1 = Math.max(...xs, 1);
  const X = s => L + s / x1 * (w - L - R), Y = v => T + (1 - v / 0.6) * (h - T - B);
  g.font = '11px system-ui'; g.fillStyle = COL.faint; g.strokeStyle = COL.grid; g.lineWidth = 1;
  for (let v = 0; v <= 0.6001; v += 0.1) { g.beginPath(); g.moveTo(L, Y(v)); g.lineTo(w - R, Y(v)); g.stroke(); g.textAlign = 'right'; g.fillText(v.toFixed(1), L - 6, Y(v) + 4); }
  g.textAlign = 'center'; const tk = x1 > 5000 ? 2500 : 250; for (let s = 0; s <= x1; s += tk) g.fillText(s.toLocaleString('en'), X(s), h - 6);
  const cb = D.wv[0].colour_probe_bacc; if (cb) { g.strokeStyle = '#8a8984'; g.setLineDash([4, 3]); g.beginPath(); g.moveTo(L, Y(cb)); g.lineTo(w - R, Y(cb)); g.stroke(); g.setLineDash([]); }
  for (const [k, c] of [['probe_bacc', COL.near], ['tobler_rho', COL.far]]) {
    g.strokeStyle = c; g.lineWidth = 2; g.beginPath(); D.wv.forEach((r, j) => j ? g.lineTo(X(r.step), Y(r[k])) : g.moveTo(X(r.step), Y(r[k]))); g.stroke();
    g.fillStyle = c; D.wv.forEach(r => { g.beginPath(); g.arc(X(r.step), Y(r[k]), 3, 0, 7); g.fill(); });
  }
  if (cur <= x1) { g.strokeStyle = COL.ink; g.lineWidth = 1; g.beginPath(); g.moveTo(X(cur), T); g.lineTo(X(cur), h - B); g.stroke(); }
}

// --- navigation
function draw() { drawInfo(); drawMap(); drawRose(); drawTL(tl, 0, N, false); drawTL(tlz, Math.max(0, cur - 250), Math.min(N, cur + 250), true); drawFilm(); if (D.wv.length) drawWV(); }
function go(i) { cur = Math.max(0, Math.min(N - 1, i)); draw(); }
function nextFar(dir) { const f = dir > 0 ? farStart.find(s => s > cur) : [...farStart].reverse().find(s => s < cur); if (f !== undefined) go(f); }
function nextRet() { for (let i = cur + 1; i < N; i++) if (S.gap[i] >= 100) return go(i); }
document.getElementById('nextfar').onclick = () => nextFar(1);
document.getElementById('prevfar').onclick = () => nextFar(-1);
document.getElementById('nextret').onclick = nextRet;
const playBtn = document.getElementById('play');
playBtn.onclick = () => { playing = !playing; playBtn.textContent = playing ? '❚❚ pause' : '▶ play'; last = performance.now(); acc = 0; if (playing) requestAnimationFrame(tick); };
let last = 0, acc = 0;
function tick(t) {
  if (!playing) return;
  acc += (t - last) / 1000 * SPEEDS[speedI]; last = t;
  if (acc >= 1) { const k = Math.floor(acc); acc -= k; if (cur + k >= N - 1) { go(N - 1); playBtn.click(); return; } go(cur + k); }
  requestAnimationFrame(tick);
}
window.addEventListener('keydown', e => {
  if (e.target.tagName === 'SELECT' || e.target.tagName === 'INPUT' && e.target.type !== 'range') return;
  const k = e.key, m = e.shiftKey ? 10 : 1;
  if (k === 'ArrowRight') go(cur + m); else if (k === 'ArrowLeft') go(cur - m);
  else if (k === 'PageDown') go(cur + 100); else if (k === 'PageUp') go(cur - 100);
  else if (k === 'Home') go(0); else if (k === 'End') go(N - 1);
  else if (k === ' ') playBtn.click();
  else if (k === '+' || k === '=') { speedI = Math.min(SPEEDS.length - 1, speedI + 1); speedSel.value = speedI; }
  else if (k === '-') { speedI = Math.max(0, speedI - 1); speedSel.value = speedI; }
  else if (k === 'f') nextFar(1); else if (k === 'F') nextFar(-1);
  else if (k === 'r' || k === 'R') nextRet();
  else if (k === 'm' || k === 'M') cycleZoom();
  else return;
  e.preventDefault();
});
window.addEventListener('resize', draw);
extras();
{ const m = location.hash.match(/step=(\d+)/), z = location.hash.match(/zoom=(\w+)/); if (z && ['world', 'path', 'follow'].includes(z[1])) { zoomMode = z[1]; document.getElementById('zoom').textContent = zoomMode === 'path' ? 'whole path' : zoomMode === 'follow' ? 'last 300 steps' : 'world'; } cur = m ? Math.min(N - 1, +m[1]) : 0; }
draw();
// preload the next tiles while playing
setInterval(() => { if (playing) for (let i = cur + 1; i < Math.min(N, cur + 30); i++) { const im = new Image(); im.src = src(S.tile[i]); } }, 1000);
</script>
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", nargs="?", default="e09_v1_long_s0")
    ap.add_argument("--out", type=Path, default=None, help="folder for index.html and tiles/ (default runs/<run>/viewer)")
    ap.add_argument("--px", type=int, default=256)
    ap.add_argument("--quality", type=int, default=82)
    a = ap.parse_args()
    build(a.run, a.out or RUNS / a.run / "viewer", a.px, a.quality)


if __name__ == "__main__":
    main()
