"""Step-by-step viewer of a walk: one self-contained HTML per run.

    python analysis/hike_viewer.py runs/global_baseline_s0 runs/confined_baseline_s0
    python analysis/hike_viewer.py runs/global_baseline_s0 --hires     # 512 px from the 10 m thumbnails

Writes <run>/hike.html: the tile the walker stood on at each step (by default the 256 px low-res it actually saw),
a filmstrip, a map of the path so far, the step's signals (I, n_z, g_z, e_z, B), a timeline of I and B with
bored events and long jumps, and the latest daydream. Images and data are embedded, so the file can be moved
or sent on its own. Each unique tile is stored once; revisits reuse it.

Keys: <-/-> step, Shift = 10, PgUp/PgDn = 100, Home/End, Space play, +/- speed,
B / Shift+B next / previous bored event, J / Shift+J next / previous long jump, M map zoom (path / world / near).
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.tile_store import EARTH_R_KM  # noqa: E402

MAP_W = 960  # land raster width (drawn at half size, so it stays sharp on hi-dpi screens)
JUMP_KM = 30.0  # moves longer than this are drawn as dashed jumps, as in analysis/v3_maps.py


def jpeg_uri(a: np.ndarray, px: int, quality: int) -> str:
    im = Image.fromarray(np.asarray(a, dtype=np.uint8))
    if im.size != (px, px):
        im = im.resize((px, px), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def file_uri(p: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()


def tile_images(cfg: dict, ids: list[int], hires: bool, px: int, quality: int) -> dict[int, str]:
    if cfg.get("world", "regional") == "regional":
        if hires:
            print("[hike] regional (v1) run: only the 256 px tiles exist, ignoring --hires")
        tiles = np.load(ROOT / "data" / "tiles.npy", mmap_mode="r")
        return {i: jpeg_uri(tiles[i], px, quality) for i in ids}
    from tqdm import tqdm

    from data.tile_store import TileStore

    store = TileStore()
    failed = set(store.fetch_all(ids, desc="fetch evicted tiles"))
    if failed:
        print(f"[hike] {len(failed)} tiles could not be fetched and are shown blank: {sorted(failed)[:10]}")
    get = store.get_hires if hires else store.get_lowres
    return {i: jpeg_uri(get(i), px, quality) for i in tqdm([i for i in ids if i not in failed], desc="encode")}


def circle(c_la: float, c_lo: float, r_km: float) -> tuple[np.ndarray, np.ndarray]:
    th = np.linspace(0, 2 * np.pi, 181)
    ang = r_km / EARTH_R_KM
    cla, clo = np.radians(c_la), np.radians(c_lo)
    pla = np.arcsin(np.sin(cla) * np.cos(ang) + np.cos(cla) * np.sin(ang) * np.cos(th))
    plo = clo + np.arctan2(np.sin(th) * np.sin(ang) * np.cos(cla), np.cos(ang) - np.sin(cla) * np.sin(pla))
    return np.degrees(pla), np.degrees(plo)


def map_view(la: np.ndarray, lo: np.ndarray, world: bool, extra: tuple[np.ndarray, np.ndarray] | None) -> dict:
    """Equirectangular view (x scaled by cos of the centre latitude) with a land raster.
    Returns the background and a projection the page applies to every point."""
    from global_land_mask import globe

    if world:
        lat0, c, x0, x1, y0, y1 = 0.0, 1.0, -180.0, 180.0, -90.0, 90.0
    else:
        bla, blo = (np.r_[la, extra[0]], np.r_[lo, extra[1]]) if extra is not None else (la, lo)
        lat0 = float((bla.min() + bla.max()) / 2)
        c = float(np.cos(np.radians(lat0)))
        x0, x1 = float(blo.min()) * c, float(blo.max()) * c
        y0, y1 = float(bla.min()), float(bla.max())
        span = max(x1 - x0, y1 - y0, 0.5) * 1.1  # 10 % margin, at least ~50 km
        if (x1 - x0) < (y1 - y0) * 1.25:  # keep the map at least 5:4 wide
            span_x, span_y = span * 1.25, span
        else:
            span_x, span_y = span, span * (y1 - y0) / max(x1 - x0, 1e-9) * 1.1
        span_y = max(span_y, span_x / 2)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        x0, x1, y0, y1 = cx - span_x / 2, cx + span_x / 2, cy - span_y / 2, cy + span_y / 2
    W = MAP_W
    H = int(round(W * (y1 - y0) / (x1 - x0)))
    LO = (x0 + (np.arange(W) + 0.5) / W * (x1 - x0)) / c
    LA = y1 - (np.arange(H) + 0.5) / H * (y1 - y0)
    LO, LA = np.meshgrid((LO + 180) % 360 - 180, np.clip(LA, -89.99, 89.99))
    land = globe.is_land(LA, LO)
    rgb = np.where(land[..., None], np.array([221, 219, 208], np.uint8), np.array([234, 241, 246], np.uint8))
    buf = io.BytesIO()
    Image.fromarray(rgb.astype(np.uint8)).save(buf, "PNG", optimize=True)
    return {"bg": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(), "w": W // 2, "h": H // 2,
            "c": c, "x0": x0, "x1": x1, "y0": y0, "y1": y1}


def r(v, d: int):
    v = np.asarray(v, dtype=np.float64)
    return [None if not np.isfinite(x) else round(float(x), d) for x in v]


def build(run: Path, hires: bool, px: int | None, quality: int) -> Path:
    cfg = yaml.safe_load((run / "config.yaml").read_text())
    meta = json.loads((run / "meta.json").read_text())
    s = pd.read_parquet(run / "steps.parquet").reset_index(drop=True)
    px = px or (512 if hires else 256)
    ids = list(dict.fromkeys(map(int, s.tile_idx)))
    imgs = tile_images(cfg, ids, hires, px, quality)

    la, lo = s.lat.to_numpy(), s.lon.to_numpy()
    conf = None
    if cfg.get("confine_center") is not None:
        c_la, c_lo = map(float, cfg["confine_center"])
        conf = circle(c_la, c_lo, float(cfg["confine_radius_km"]))
    local = (lo.max() - lo.min()) < 120 and (la.max() - la.min()) < 60
    views = {"world": map_view(la, lo, True, None)}
    if local:
        views["path"] = map_view(la, lo, False, conf)

    dd = {}
    for st in s.step[s.bored_event]:
        p = run / "daydreams" / f"bored_{int(st):04d}.png"
        if p.exists():
            dd[int(st)] = file_uri(p)

    col = lambda k: s[k].tolist() if k in s else None  # noqa: E731
    data = {
        "run": run.name, "world": cfg.get("world", "regional"), "policy": cfg.get("policy"), "seed": meta.get("seed"),
        "started": meta.get("started"), "px": px, "hires": bool(hires and cfg.get("world", "regional") != "regional"),
        "patience": float(cfg.get("patience", np.nan)), "jump_km": JUMP_KM,
        "confine": None if conf is None else {"lat": r(conf[0], 4), "lon": r(conf[1], 4), "r_km": float(cfg["confine_radius_km"])},
        "views": views,
        "steps": {
            "step": col("step"), "tile": col("tile_idx"), "cell": col("grid_cell"), "lat": r(la, 4), "lon": r(lo, 4),
            "cloud": r(s.cloud_cover, 1), "tv": col("tv"), "cover": col("cover"), "jump": col("jump_type"),
            "dist": r(s.dist_km, 1), "I": r(s.I, 3), "max_I": r(s.max_I, 3), "n_z": r(s.n_z, 3), "g_z": r(s.g_z, 3),
            "e_z": r(s.e_z, 3), "B": r(s.B, 3), "B_after": r(s.B_after, 3), "bored": col("bored_event"),
            "n_cand": col("n_candidates"), "err_before": r(s.err_before, 5), "err_after": r(s.err_after, 5),
            "visit": (s.groupby("tile_idx").cumcount() + 1).tolist(),
        },
        "images": {str(k): v for k, v in imgs.items()},
        "daydreams": {str(k): v for k, v in dd.items()},
    }
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    out = run / "hike.html"
    out.write_text(PAGE.replace("__TITLE__", f"{run.name}: the hike").replace("__DATA__", blob), encoding="utf-8")
    print(f"[hike] {out}  ({out.stat().st_size / 1e6:.1f} MB, {len(s):,} steps, {len(ids):,} unique tiles, {len(dd)} daydreams)")
    return out


PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>__TITLE__</title>
<style>
  :root { --bg:#f6f6f3; --panel:#fff; --ink:#1f2328; --muted:#6a7078; --line:#e2e2dc; --accent:#2f6fde;
          --bored:#c8323c; --long:#2f6fde; --neighbour:#4a8a5a; }
  * { box-sizing:border-box; }
  body { margin:0; font:13px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif; color:var(--ink); background:var(--bg); }
  header { padding:10px 18px; display:flex; gap:18px; align-items:baseline; flex-wrap:wrap; border-bottom:1px solid var(--line); background:var(--panel); }
  header h1 { font-size:16px; margin:0; }
  header .meta { color:var(--muted); }
  main { display:grid; grid-template-columns:minmax(360px,560px) minmax(340px,1fr); gap:14px; padding:14px 18px 6px; align-items:start; }
  .card { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:10px; }
  #tile { width:100%; aspect-ratio:1; display:block; background:#ddd; border-radius:4px; object-fit:cover; }
  #tilecap { display:flex; justify-content:space-between; margin-top:6px; color:var(--muted); }
  #tilecap b { color:var(--ink); }
  .side { display:flex; flex-direction:column; gap:14px; min-width:0; }
  #mapwrap { position:relative; }
  #map { width:100%; display:block; border-radius:4px; }
  #mapbar { display:flex; justify-content:space-between; color:var(--muted); margin-top:4px; }
  button, select, input[type=number] { font:inherit; padding:3px 9px; border:1px solid var(--line); border-radius:5px; background:#fff; cursor:pointer; }
  button:hover { border-color:#b9bcc2; }
  table { border-collapse:collapse; width:100%; }
  td { padding:2px 6px; border-bottom:1px solid #f0f0ec; vertical-align:top; }
  td:first-child { color:var(--muted); width:42%; }
  .badge { display:inline-block; padding:0 7px; border-radius:9px; color:#fff; font-size:12px; }
  .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
  #dd { width:100%; display:block; border-radius:4px; image-rendering:pixelated; }
  #ddcap { color:var(--muted); margin-top:4px; }
  #strip { display:flex; gap:6px; padding:0 18px; overflow:hidden; }
  #strip figure { margin:0; flex:1 1 0; min-width:0; cursor:pointer; opacity:.75; }
  #strip figure.cur { opacity:1; }
  #strip figure.cur img { outline:3px solid var(--accent); }
  #strip img { width:100%; aspect-ratio:1; display:block; border-radius:3px; background:#ddd; object-fit:cover; }
  #strip figcaption { text-align:center; color:var(--muted); font-size:11px; white-space:nowrap; overflow:hidden; }
  #controls { display:flex; gap:8px; align-items:center; padding:10px 18px 4px; flex-wrap:wrap; }
  #controls .grow { flex:1; }
  #stepin { width:80px; }
  #timeline { display:block; width:calc(100% - 36px); margin:0 18px; height:86px; cursor:pointer; background:var(--panel); border:1px solid var(--line); border-radius:6px; }
  #slider { width:calc(100% - 36px); margin:6px 18px 0; }
  #legend { padding:2px 18px; color:var(--muted); font-size:12px; }
  #legend span { margin-right:14px; }
  #keys { padding:4px 18px 16px; color:var(--muted); font-size:12px; }
  kbd { border:1px solid var(--line); border-bottom-width:2px; border-radius:3px; padding:0 4px; background:#fff; font:11px ui-monospace,monospace; }
  @media (max-width: 900px) { main { grid-template-columns:1fr; } }
</style>
</head>
<body>
<header><h1 id="title"></h1><span class="meta" id="hmeta"></span></header>
<main>
  <div class="card">
    <img id="tile" alt="tile at the current step">
    <div id="tilecap"><span id="capl"></span><span id="capr"></span></div>
  </div>
  <div class="side">
    <div class="card" id="mapwrap">
      <canvas id="map"></canvas>
      <div id="mapbar"><span id="mapinfo"></span><button id="mapbtn" title="M">zoom: path</button></div>
    </div>
    <div class="grid2">
      <div class="card"><table id="info"></table></div>
      <div class="card"><img id="dd" alt=""><div id="ddcap"></div></div>
    </div>
  </div>
</main>
<div id="strip"></div>
<div id="controls">
  <button id="first" title="Home">&#x23EE;</button>
  <button id="prev" title="&larr;">&#x25C0;</button>
  <button id="play" title="Space" style="min-width:70px">&#x25B6; play</button>
  <button id="next" title="&rarr;">&#x25B6;</button>
  <button id="last" title="End">&#x23ED;</button>
  <label>speed <select id="speed"></select></label>
  <span class="grow"></span>
  <button id="pbored" title="Shift+B">&larr; bored</button><button id="nbored" title="B">bored &rarr;</button>
  <button id="plong" title="Shift+J">&larr; long jump</button><button id="nlong" title="J">long jump &rarr;</button>
  <label>step <input id="stepin" type="number" min="0"></label>
</div>
<canvas id="timeline"></canvas>
<input id="slider" type="range" min="0" value="0">
<div id="legend">
  <span style="color:#555">&#x2501; I (chosen tile)</span><span style="color:#d98a1c">&#x2501; boredom B</span>
  <span style="color:#d98a1c">&#x2504; patience</span><span style="color:var(--bored)">&#x25BC; bored event</span><span style="color:var(--long)">&#x25B2; long jump</span>
</div>
<div id="keys">
  <kbd>&larr;</kbd><kbd>&rarr;</kbd> step &nbsp; <kbd>Shift</kbd> &times;10 &nbsp; <kbd>PgUp</kbd><kbd>PgDn</kbd> &times;100 &nbsp;
  <kbd>Home</kbd><kbd>End</kbd> &nbsp; <kbd>Space</kbd> play &nbsp; <kbd>+</kbd><kbd>-</kbd> speed &nbsp;
  <kbd>B</kbd> next bored event &nbsp; <kbd>J</kbd> next long jump (<kbd>Shift</kbd> = previous) &nbsp; <kbd>M</kbd> map zoom (path / world / near) &nbsp;
  the URL keeps the step (<code>#step=123</code>)
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
"use strict";
const D = JSON.parse(document.getElementById("data").textContent);
const S = D.steps, N = S.step.length;
const $ = id => document.getElementById(id);
const JUMPCOL = { neighbour: "#4a8a5a", long: "#2f6fde", bored: "#c8323c" };
const boredIdx = [], longIdx = [];
for (let i = 0; i < N; i++) { if (S.bored[i]) boredIdx.push(i); if (S.jump[i] === "long") longIdx.push(i); }
const ddSteps = Object.keys(D.daydreams).map(Number).sort((a, b) => a - b);
let cur = 0, playing = false;
const VIEWS = [...(D.views.path ? ["path"] : []), "world", "near"];
let view = VIEWS[0];
const NEAR_DEG = 1.0;  // half-height of the 'near' view in degrees of latitude (~110 km)

// ---- header -----------------------------------------------------------------
const km = S.dist.reduce((a, b) => a + (b || 0), 0);
const uniq = Object.keys(D.images).length;
$("title").textContent = D.run;
$("hmeta").textContent = [
  `${D.world} world` + (D.confine ? `, confined to ${D.confine.r_km} km` : ""), `policy ${D.policy}`, `seed ${D.seed}`,
  `${N.toLocaleString()} steps`, `${uniq.toLocaleString()} unique tiles`, `${Math.round(km).toLocaleString()} km`,
  `${boredIdx.length} bored events`, `${longIdx.length} long jumps`,
  `${D.px} px ${D.hires ? "(10 m thumbnail)" : "(what the walker saw)"}`, D.started ? `started ${D.started}` : ""
].filter(Boolean).join(" · ");

// ---- map --------------------------------------------------------------------
const mapC = $("map"), mctx = mapC.getContext("2d");
const bgImg = {};
for (const [k, v] of Object.entries(D.views)) { const im = new Image(); im.src = v.bg; im.onload = () => draw(); bgImg[k] = im; }
function proj(v, la, lo) {
  // pixel coords in the view's raster (half resolution)
  const x = lo * v.c;
  return [(x - v.x0) / (v.x1 - v.x0) * v.w, (v.y1 - la) / (v.y1 - v.y0) * v.h];
}
function stepColor(i) { // viridis-like: purple -> teal -> yellow over the hike
  const t = N > 1 ? i / (N - 1) : 0;
  return `hsl(${270 - 215 * t}, ${55 + 25 * t}%, ${32 + 28 * t}%)`;
}
function getView() {
  if (view !== "near") return D.views[view];
  // a window around the walker, no land raster
  const c = Math.cos(S.lat[cur] * Math.PI / 180), w = 480, h = 320, hy = NEAR_DEG, hx = hy * w / h;
  return { c, w, h, x0: S.lon[cur] * c - hx, x1: S.lon[cur] * c + hx, y0: S.lat[cur] - hy, y1: S.lat[cur] + hy };
}
function drawMap() {
  const v = getView();
  const dpr = window.devicePixelRatio || 1;
  const cssW = mapC.clientWidth, sc = cssW / v.w, cssH = v.h * sc;
  mapC.width = Math.round(cssW * dpr); mapC.height = Math.round(cssH * dpr); mapC.style.height = cssH + "px";
  mctx.setTransform(dpr * sc, 0, 0, dpr * sc, 0, 0);
  if (bgImg[view] && bgImg[view].complete) mctx.drawImage(bgImg[view], 0, 0, v.w, v.h);
  else { mctx.fillStyle = "#ecebe4"; mctx.fillRect(0, 0, v.w, v.h); }
  const lw = 1 / sc;
  if (D.confine) {
    mctx.beginPath();
    D.confine.lat.forEach((la, k) => { const [x, y] = proj(v, la, D.confine.lon[k]); k ? mctx.lineTo(x, y) : mctx.moveTo(x, y); });
    mctx.strokeStyle = "#333"; mctx.lineWidth = 1.2 * lw; mctx.setLineDash([]); mctx.stroke();
  }
  const P = S.lat.map((la, i) => proj(v, la, S.lon[i]));
  const isJump = i => S.dist[i] > D.jump_km || Math.abs(S.lon[i] - S.lon[i - 1]) > 180;
  // the whole hike, faint
  mctx.fillStyle = view === "near" ? "rgba(0,0,0,0.25)" : "rgba(0,0,0,0.13)";
  for (let i = 0; i < N; i++) mctx.fillRect(P[i][0] - 1.2 * lw, P[i][1] - 1.2 * lw, 2.4 * lw, 2.4 * lw);
  // the path so far, coloured by step, in chunks of one colour
  const CH = Math.max(1, Math.ceil(N / 200));
  mctx.lineCap = "round";
  for (let a = 1; a <= cur; a += CH) {
    const b = Math.min(cur, a + CH - 1);
    mctx.beginPath();
    for (let i = a; i <= b; i++) if (!isJump(i)) { mctx.moveTo(P[i - 1][0], P[i - 1][1]); mctx.lineTo(P[i][0], P[i][1]); }
    mctx.strokeStyle = stepColor(a); mctx.lineWidth = 1.6 * lw; mctx.setLineDash([]); mctx.stroke();
  }
  mctx.beginPath();
  for (let i = 1; i <= cur; i++) if (isJump(i) && Math.abs(S.lon[i] - S.lon[i - 1]) <= 180) { mctx.moveTo(P[i - 1][0], P[i - 1][1]); mctx.lineTo(P[i][0], P[i][1]); }
  mctx.strokeStyle = "rgba(60,60,60,0.55)"; mctx.lineWidth = 0.9 * lw; mctx.setLineDash([4 * lw, 3 * lw]); mctx.stroke(); mctx.setLineDash([]);
  for (const i of boredIdx) if (i <= cur) {
    mctx.beginPath(); mctx.arc(P[i][0], P[i][1], 4 * lw, 0, 7); mctx.strokeStyle = "#c8323c"; mctx.lineWidth = 1.2 * lw; mctx.stroke();
  }
  star(P[0][0], P[0][1], 7 * lw, "#e23", lw);
  const [cx, cy] = P[cur];
  mctx.beginPath(); mctx.arc(cx, cy, 6 * lw, 0, 7); mctx.fillStyle = "#fff"; mctx.fill();
  mctx.lineWidth = 2.5 * lw; mctx.strokeStyle = "#1f2328"; mctx.stroke();
  mctx.beginPath(); mctx.arc(cx, cy, 2.5 * lw, 0, 7); mctx.fillStyle = "#e23"; mctx.fill();
  $("mapinfo").textContent = (view === "near" ? `±${Math.round(NEAR_DEG * 111)} km around the walker  ·  ` : "") + `★ birthplace  ○ bored  ┄ jump > ${D.jump_km} km`;
}
function star(x, y, r, col, lw) {
  mctx.beginPath();
  for (let k = 0; k < 10; k++) { const a = -Math.PI / 2 + k * Math.PI / 5, rr = k % 2 ? r * 0.45 : r; mctx.lineTo(x + rr * Math.cos(a), y + rr * Math.sin(a)); }
  mctx.closePath(); mctx.fillStyle = col; mctx.fill(); mctx.strokeStyle = "#000"; mctx.lineWidth = 0.8 * lw; mctx.stroke();
}

// ---- timeline -----------------------------------------------------------------
const tl = $("timeline"), tctx = tl.getContext("2d");
let tlStatic = null;
const finite = a => a.filter(x => x !== null && isFinite(x));
const Iv = finite(S.I), Ilo = Math.min(...Iv), Ihi = Math.max(...Iv);
function tlStaticLayer(W, H, dpr) {
  const c = document.createElement("canvas"); c.width = W * dpr; c.height = H * dpr;
  const g = c.getContext("2d"); g.scale(dpr, dpr);
  const pad = 12, h = H - 2 * pad, xOf = i => (N > 1 ? i / (N - 1) : 0) * (W - 2) + 1;
  // I, decimated to one min/max column per pixel
  g.strokeStyle = "rgba(60,60,60,0.55)"; g.lineWidth = 1; g.beginPath();
  const per = Math.max(1, Math.floor(N / W));
  for (let a = 0; a < N; a += per) {
    let lo = Infinity, hi = -Infinity;
    for (let i = a; i < Math.min(N, a + per); i++) if (S.I[i] !== null) { lo = Math.min(lo, S.I[i]); hi = Math.max(hi, S.I[i]); }
    if (lo === Infinity) continue;
    const x = xOf(a), y = v => pad + h - (v - Ilo) / (Ihi - Ilo || 1) * h;
    g.moveTo(x, y(lo)); g.lineTo(x, y(hi) - 0.5);
  }
  g.stroke();
  if (Ilo < 0 && Ihi > 0) { const y0 = pad + h - (0 - Ilo) / (Ihi - Ilo) * h; g.strokeStyle = "rgba(0,0,0,0.15)"; g.beginPath(); g.moveTo(0, y0); g.lineTo(W, y0); g.stroke(); }
  // B in [0, 1]
  g.strokeStyle = "#d98a1c"; g.lineWidth = 1.4; g.beginPath();
  for (let i = 0; i < N; i++) { if (S.B[i] === null) continue; const x = xOf(i), y = pad + h - S.B[i] * h; i ? g.lineTo(x, y) : g.moveTo(x, y); }
  g.stroke();
  if (isFinite(D.patience)) { const y = pad + h - D.patience * h; g.setLineDash([4, 3]); g.lineWidth = 1; g.beginPath(); g.moveTo(0, y); g.lineTo(W, y); g.stroke(); g.setLineDash([]); }
  g.fillStyle = "#c8323c";
  for (const i of boredIdx) { const x = xOf(i); g.beginPath(); g.moveTo(x - 4, 1); g.lineTo(x + 4, 1); g.lineTo(x, 9); g.fill(); }
  g.fillStyle = "#2f6fde";
  for (const i of longIdx) { const x = xOf(i); g.beginPath(); g.moveTo(x - 4, H - 1); g.lineTo(x + 4, H - 1); g.lineTo(x, H - 9); g.fill(); }
  return c;
}
function drawTimeline() {
  const dpr = window.devicePixelRatio || 1, W = tl.clientWidth, H = tl.clientHeight;
  if (!tlStatic || tlStatic.width !== W * dpr) tlStatic = tlStaticLayer(W, H, dpr);
  tl.width = W * dpr; tl.height = H * dpr;
  tctx.setTransform(1, 0, 0, 1, 0, 0); tctx.drawImage(tlStatic, 0, 0);
  tctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const x = (N > 1 ? cur / (N - 1) : 0) * (W - 2) + 1;
  tctx.fillStyle = "rgba(47,111,222,0.12)"; tctx.fillRect(0, 0, x, H);
  tctx.strokeStyle = "#2f6fde"; tctx.lineWidth = 1.5; tctx.beginPath(); tctx.moveTo(x, 0); tctx.lineTo(x, H); tctx.stroke();
}
let dragging = false;
const seekTl = e => { const r = tl.getBoundingClientRect(); go(Math.round((e.clientX - r.left) / r.width * (N - 1))); };
tl.addEventListener("pointerdown", e => { dragging = true; tl.setPointerCapture(e.pointerId); stop(); seekTl(e); });
tl.addEventListener("pointermove", e => { if (dragging) seekTl(e); });
tl.addEventListener("pointerup", () => { dragging = false; });

// ---- tile, strip, info, daydream ----------------------------------------------------
const BLANK = "data:image/gif;base64,R0lGODlhAQABAAAAACw=";
const img = t => D.images[t] || BLANK;
const STRIP = 9, stripEls = [];
for (let k = 0; k < STRIP; k++) {
  const f = document.createElement("figure"), im = document.createElement("img"), cap = document.createElement("figcaption");
  f.append(im, cap); $("strip").append(f); stripEls.push({ f, im, cap });
}
const fmt = (v, d = 3) => v === null || v === undefined ? "–" : (typeof v === "number" ? v.toFixed(d) : String(v));
const badge = j => `<span class="badge" style="background:${JUMPCOL[j] || "#888"}">${j}</span>`;
function drawInfo() {
  const i = cur, t = S.tile[i];
  $("tile").src = img(t);
  $("capl").innerHTML = `<b>step ${S.step[i]}</b> / ${S.step[N - 1]} &nbsp; ${badge(S.jump[i])}` + (S.bored[i] ? ` <span class="badge" style="background:#c8323c">bored!</span>` : "");
  $("capr").innerHTML = `tile ${t} · ${S.cell[i]}` + (S.visit[i] > 1 ? ` · <b>revisit #${S.visit[i] - 1}</b>` : " · first visit");
  const rows = [
    ["lat, lon", `${S.lat[i].toFixed(4)}, ${S.lon[i].toFixed(4)}`],
    S.cover ? ["cover", S.cover[i]] : null,
    ["cloud cover", fmt(S.cloud[i], 1) + " %"],
    S.tv[i] ? ["noisy TV", "<b>yes</b>"] : null,
    ["move", `${badge(S.jump[i])} ${fmt(S.dist[i], 1)} km`],
    ["candidates", S.n_cand[i]],
    ["I (chosen / max)", `<b>${fmt(S.I[i])}</b> / ${fmt(S.max_I[i])}`],
    ["novelty n_z", fmt(S.n_z[i])],
    ["learning progress g_z", fmt(S.g_z[i])],
    ["recon error e_z", fmt(S.e_z[i])],
    ["boredom B", `${fmt(S.B[i])} &rarr; ${fmt(S.B_after[i])}` + (isFinite(D.patience) ? ` <span style="color:#6a7078">(patience ${D.patience})</span>` : "")],
    ["train err", `${fmt(S.err_before[i], 5)} &rarr; ${fmt(S.err_after[i], 5)}`],
  ].filter(Boolean);
  $("info").innerHTML = rows.map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join("");
  for (let k = 0; k < STRIP; k++) {
    const j = i + k - (STRIP >> 1), e = stripEls[k];
    if (j < 0 || j >= N) { e.f.style.visibility = "hidden"; continue; }
    e.f.style.visibility = ""; e.im.src = img(S.tile[j]); e.f.className = j === i ? "cur" : "";
    e.cap.textContent = `${S.step[j]}${S.jump[j] !== "neighbour" ? " · " + S.jump[j] : ""}${S.bored[j] ? " · bored" : ""}`;
    e.f.onclick = () => { stop(); go(j); };
  }
  // latest daydream at or before this step
  const st = S.step[i];
  let k = -1; for (const d of ddSteps) { if (d <= st) k = d; else break; }
  if (k >= 0) { $("dd").src = D.daydreams[k]; $("dd").style.display = ""; $("ddcap").innerHTML = `daydream at bored step ${k}` + (k === st ? " <b>(now)</b>" : ` (${st - k} steps ago)`); }
  else { $("dd").style.display = "none"; $("ddcap").textContent = ddSteps.length ? `no daydream yet (first at step ${ddSteps[0]})` : "no daydreams in this run"; }
}

// ---- navigation ------------------------------------------------------------------
const slider = $("slider"); slider.max = N - 1;
const SPEEDS = [1, 2, 4, 8, 16, 32, 64];
SPEEDS.forEach(v => $("speed").add(new Option(`${v} steps/s`, v)));
$("speed").value = 8;
let hashTimer = null;
function draw() { drawInfo(); drawMap(); drawTimeline(); }
function go(i) {
  cur = Math.max(0, Math.min(N - 1, i));
  slider.value = cur; $("stepin").value = S.step[cur];
  draw();
  clearTimeout(hashTimer); hashTimer = setTimeout(() => history.replaceState(null, "", `#step=${S.step[cur]}`), 250);
}
let last = 0, acc = 0;
function tick(ts) {
  if (!playing) return;
  acc += (ts - last) / 1000 * Number($("speed").value); last = ts;
  if (acc >= 1) { const n = Math.floor(acc); acc -= n; go(cur + n); if (cur >= N - 1) { stop(); return; } }
  requestAnimationFrame(tick);
}
function play() { if (cur >= N - 1) go(0); playing = true; $("play").innerHTML = "&#x23F8; pause"; last = performance.now(); acc = 0; requestAnimationFrame(tick); }
function stop() { playing = false; $("play").innerHTML = "&#x25B6; play"; }
const nextOf = (arr, dir) => { const c = dir > 0 ? arr.find(i => i > cur) : [...arr].reverse().find(i => i < cur); if (c !== undefined) go(c); };
const speedBy = d => { const s = $("speed"); s.selectedIndex = Math.max(0, Math.min(SPEEDS.length - 1, s.selectedIndex + d)); };
$("play").onclick = () => playing ? stop() : play();
$("prev").onclick = () => { stop(); go(cur - 1); };
$("next").onclick = () => { stop(); go(cur + 1); };
$("first").onclick = () => { stop(); go(0); };
$("last").onclick = () => { stop(); go(N - 1); };
$("nbored").onclick = () => { stop(); nextOf(boredIdx, 1); };
$("pbored").onclick = () => { stop(); nextOf(boredIdx, -1); };
$("nlong").onclick = () => { stop(); nextOf(longIdx, 1); };
$("plong").onclick = () => { stop(); nextOf(longIdx, -1); };
$("mapbtn").onclick = () => { view = VIEWS[(VIEWS.indexOf(view) + 1) % VIEWS.length]; $("mapbtn").textContent = `zoom: ${view}`; drawMap(); };
$("mapbtn").textContent = `zoom: ${view}`;
slider.oninput = () => { stop(); go(Number(slider.value)); };
$("stepin").onchange = () => { stop(); const v = Number($("stepin").value); const j = S.step.findIndex(s => s >= v); go(j < 0 ? N - 1 : j); };
document.addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT" && e.target.type === "number") return;
  const k = e.key;
  const m = e.shiftKey ? 10 : 1;
  if (k === "ArrowRight") { stop(); go(cur + m); }
  else if (k === "ArrowLeft") { stop(); go(cur - m); }
  else if (k === "PageDown") { stop(); go(cur + 100); }
  else if (k === "PageUp") { stop(); go(cur - 100); }
  else if (k === "Home") { stop(); go(0); }
  else if (k === "End") { stop(); go(N - 1); }
  else if (k === " ") { playing ? stop() : play(); }
  else if (k === "+" || k === "=") speedBy(1);
  else if (k === "-") speedBy(-1);
  else if (k.toLowerCase() === "b") { stop(); nextOf(boredIdx, e.shiftKey ? -1 : 1); }
  else if (k.toLowerCase() === "j") { stop(); nextOf(longIdx, e.shiftKey ? -1 : 1); }
  else if (k.toLowerCase() === "m") $("mapbtn").click();
  else return;
  e.preventDefault();
});
window.addEventListener("resize", () => { tlStatic = null; draw(); });
const h = location.hash.match(/step=(\d+)/);
go(h ? Math.max(0, S.step.findIndex(s => s >= Number(h[1]))) : 0);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("--hires", action="store_true", help="use the 1068 px 10 m thumbnails (global runs) instead of the 256 px low-res")
    ap.add_argument("--px", type=int, default=None, help="image size in the page (default 256, or 512 with --hires)")
    ap.add_argument("--quality", type=int, default=85, help="JPEG quality")
    a = ap.parse_args()
    for run in a.runs:
        build(run, a.hires, a.px, a.quality)
