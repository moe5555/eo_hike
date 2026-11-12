"""Step-by-step viewer of a two-eye walk (experiment 12): the e09 viewer (analysis/e09/walk_viewer.py) plus a card for the two eyes.

    python analysis/e12/walk_viewer.py runs/e12_two_top4_s0 [--out DIR]     # -> <run>/viewer/index.html, tiles beside it

Everything of the e09 viewer (path map, compass of offers, timeline, filmstrip, keys), and per step a "Two eyes" card:
- the tile as the walker saw it with its 4 x 4 grid: each crop's novelty rank (0 = most novel), the top-k crops outlined, the top crop
  in white; the overlay can show instead the crop novelty, or a quirk share per crop (stripe, DN 255, QA cloud; the maximum over the
  three bands the eye sees). Quirks are measured from pixels, never shown to the walker;
- the glance's reconstruction-error map (32 x 32, the whole tile at ~333 m/px), on one scale for the whole walk;
- the interest decomposition at the choice: the share of |contribution| of glance, grid and progress, and each one's lift (its
  contribution at the choice minus its mean over the offers: what made this offer win);
- the eye signals (novelty per eye, the v1 shadow, surprise per eye, choice probability, best offer or not), the tile's quirks, and
  any firing of the death dry run (notes/12_two_eye/results/deaths.csv) at this step.
For a v1 walk the page is the e09 viewer alone.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "analysis" / "e09"), str(ROOT)]
import walk_viewer as V  # noqa: E402  (analysis/e09/walk_viewer.py; its import sets the rest of sys.path)

SEEN = ("green", "red", "nir08")
DEATHS = ROOT / "notes" / "12_two_eye" / "results" / "deaths.csv"


def eye_data(rd: Path, cfg: dict, store) -> dict | None:
    if cfg.get("eye", "v1") == "v1":
        return None
    s = pd.read_parquet(rd / "steps.parquet").reset_index(drop=True)
    cr = pd.read_parquet(rd / "crops.parquet")
    ch = cr[cr.chosen].sort_values(["step", "crop"])
    assert len(ch) == 16 * len(s), "crops.parquet: chosen tile rows missing"

    def qmax(d: pd.DataFrame, q: str) -> np.ndarray:
        cols = [f"{q}_{b}" for b in SEEN if f"{q}_{b}" in d]
        return d[cols].max(axis=1).to_numpy() if cols else np.full(len(d), np.nan)

    crops = {"n": V.rnd(ch.n, 4), "rank": ch["rank"].astype(int).tolist(), "e": V.rnd(ch.e, 5),
             "stripe": V.rnd(qmax(ch, "stripe"), 3), "at255": V.rnd(qmax(ch, "at255"), 3), "cloud": V.rnd(ch.cloud if "cloud" in ch else np.nan, 3)}
    ge = np.load(rd / "glance_err.npy").astype(np.float32)
    gmax = float(np.percentile(ge, 99.5))
    gq = np.clip(np.sqrt(ge / gmax) * 255, 0, 255).astype(np.uint8)  # sqrt scale, one for the walk
    q = store.quirks(s.tile_idx.unique()) if hasattr(store, "quirks") else pd.DataFrame()
    tq = {}
    if len(q):
        q = q.set_index("tile_idx")
        for k in ("stripe", "at255", "satflag"):
            q[k] = q[[f"{k}_{b}" for b in SEEN]].max(axis=1)
        qq = q.reindex(s.tile_idx)
        tq = {k: V.rnd(qq[k], 3) for k in ("cloud", "fill", "stripe", "at255", "satflag") if k in qq}
    idx = store.idx
    meta = {}
    for k in ("timestamp", "level", "tier", "night", "scene", "sun_elevation"):
        if k in idx:
            v = idx.set_index("idx")[k].reindex(s.tile_idx) if "idx" in idx else idx[k].reindex(s.tile_idx)
            meta[k] = [str(pd.Timestamp(x).date()) for x in v] if k == "timestamp" else (V.rnd(v, 1) if k == "sun_elevation" else [str(x) for x in v])
    deaths = []
    if DEATHS.exists():
        d = pd.read_csv(DEATHS)
        name = rd.name
        cond, seed = name.rsplit("_s", 1)
        d = d[(d.cond == cond) & (d.seed == int(seed))]
        deaths = [[int(r.step), f"{r.rule} {r.source}" + (f" (z {r.z:.1f})" if pd.notna(getattr(r, "z", np.nan)) else "")] for r in d.itertuples()]
    return {
        "k": int(cfg.get("novelty_topk", 4)), "eye": cfg["eye"], "w": [float(cfg.get("w_glance", 1.0)), float(cfg.get("w_grid", cfg["w_n"])), float(cfg["w_g"])],
        "top": s.top_crop.astype(int).tolist(),
        "sh": [V.rnd(s[f"share_{k}"], 3) for k in ("glance", "grid", "prog")],
        "lift": [V.rnd(s[f"lift_{k}"], 2) for k in ("glance", "grid", "prog")],
        "z": [V.rnd(s[f"z_{k}"], 2) for k in ("glance", "grid", "prog")],
        "ngl": V.rnd(s.n_glance, 4), "ngr": V.rnd(s.n_grid, 4), "nv1": V.rnd(s.n_v1, 4), "prog": V.rnd(s.prog, 6),
        "egl": V.rnd(s.e_glance, 5), "egr": V.rnd(s.e_grid, 5), "egm": V.rnd(s.e_grid_max, 5),
        "p": V.rnd(s.p_chosen, 3), "best": s.best_offer.astype(int).tolist(),
        "crops": crops, "gerr": base64.b64encode(gq.tobytes()).decode(), "gmax": gmax, "tq": tq, "meta": meta, "deaths": deaths,
    }


CARD = r"""
<div class="row" style="grid-template-columns: 400px minmax(420px,1fr)" id="eyerow">
  <div class="card">
    <h2><span>Two eyes: the grid</span><span><select id="eyemode">
      <option value="rank">novelty rank</option><option value="n">crop novelty</option><option value="stripe">stripe share</option>
      <option value="at255">DN 255 share</option><option value="cloud">QA cloud share</option><option value="none">tile only</option></select></span></h2>
    <canvas id="eyecv" width="378" height="378" style="width:378px;height:378px"></canvas>
    <div class="help" id="eyehelp" style="margin-top:4px"></div>
  </div>
  <div class="card">
    <h2><span>Two eyes: glance, interest, quirks</span><span id="eyecap" class="muted" style="text-transform:none;letter-spacing:0"></span></h2>
    <div style="display:flex;gap:14px;align-items:flex-start;flex-wrap:wrap">
      <div><canvas id="gerr" width="192" height="192" style="width:192px;height:192px;image-rendering:pixelated;border-radius:4px"></canvas>
        <div class="help">glance reconstruction error (32 × 32), one scale for the walk</div></div>
      <div style="flex:1;min-width:260px">
        <canvas id="shares" height="70"></canvas>
        <table id="eyeinfo" style="margin-top:6px"></table>
      </div>
    </div>
  </div>
</div>
"""

SCRIPT = r"""
<script>
(function(){
const E = __EYE__;
const ECOL = {glance:'#2a78d6', grid:'#eb6834', prog:'#1baf7a'};
const gbytes = Uint8Array.from(atob(E.gerr), c => c.charCodeAt(0));
const tileImg = new Image(); let tileFor = -1;
document.getElementById('extra').insertAdjacentHTML('beforebegin', `__CARD__`);
const mode = document.getElementById('eyemode');
mode.addEventListener('change', () => drawEye());
const deathAt = {}; for (const [st, lab] of E.deaths) (deathAt[st] = deathAt[st] || []).push(lab);
function viridis(t){ t=Math.max(0,Math.min(1,t)); const a=[[68,1,84],[59,82,139],[33,145,140],[94,201,98],[253,231,37]]; const x=t*4, i=Math.min(3,Math.floor(x)), f=x-i;
  return a[i].map((v,k)=>Math.round(v+(a[i+1][k]-v)*f)); }
function fmt(v, d){ return (v===null||v===undefined) ? '–' : (+v).toFixed(d); }
function drawGrid(){
  const cv = document.getElementById('eyecv'), g = cv.getContext('2d'), W = cv.width, q = W/4, i0 = cur*16, m = mode.value;
  g.clearRect(0,0,W,W);
  if (tileImg.complete && tileFor===cur) g.drawImage(tileImg, 0, 0, W, W);
  const C = E.crops; let vals = null, vmax = 1;
  if (m==='n') { vals = C.n.slice(i0,i0+16); vmax = Math.max(...vals.map(v=>v||0), 1e-9); }
  if (m==='stripe'||m==='at255'||m==='cloud') { vals = C[m].slice(i0,i0+16); vmax = Math.max(...vals.map(v=>v||0), 0.05); }
  for (let k=0;k<16;k++){
    const r=Math.floor(k/4), c=k%4, x=c*q, y=r*q, rank=C.rank[i0+k];
    if (vals){ const v=vals[k]; if (v!==null){ const [R,G,B]=viridis(v/vmax); g.fillStyle=`rgba(${R},${G},${B},0.55)`; g.fillRect(x,y,q,q); } }
    g.strokeStyle='rgba(255,255,255,0.35)'; g.lineWidth=1; g.strokeRect(x+0.5,y+0.5,q-1,q-1);
    if (m!=='none'){
      if (rank < E.k){ g.strokeStyle = rank===0 ? '#ffffff' : 'rgba(255,255,255,0.85)'; g.lineWidth = rank===0 ? 4 : 2; g.setLineDash(rank===0?[]:[6,4]);
        g.strokeStyle='#000'; g.lineWidth += 2; g.strokeRect(x+3,y+3,q-6,q-6); g.strokeStyle='#fff'; g.lineWidth -= 2; g.strokeRect(x+3,y+3,q-6,q-6); g.setLineDash([]); }
      const lab = m==='rank' ? String(rank) : (vals ? (m==='n' ? fmt(vals[k],3) : (vals[k]===null?'–':Math.round(100*vals[k])+'%')) : '');
      g.font='bold 13px system-ui'; g.fillStyle='rgba(0,0,0,0.6)'; g.fillRect(x+6,y+q-22,g.measureText(lab).width+8,17);
      g.fillStyle='#fff'; g.fillText(lab, x+10, y+q-9);
    }
  }
  document.getElementById('eyehelp').textContent = `top-${E.k} crops outlined (top crop solid). Overlay: ${mode.options[mode.selectedIndex].text}` +
    (vals && m!=='rank' ? `, scale 0–${m==='n'?fmt(vmax,3):Math.round(100*vmax)+'%'} on this tile` : '') + '. Quirks are measured from pixels, never shown to the walker.';
}
function drawGerr(){
  const cv=document.getElementById('gerr'), g=cv.getContext('2d'), im=g.createImageData(32,32), o=cur*1024;
  for (let i=0;i<1024;i++){ const [R,G,B]=viridis(gbytes[o+i]/255); im.data[4*i]=R; im.data[4*i+1]=G; im.data[4*i+2]=B; im.data[4*i+3]=255; }
  const t=document.createElement('canvas'); t.width=32; t.height=32; t.getContext('2d').putImageData(im,0,0);
  g.imageSmoothingEnabled=false; g.drawImage(t,0,0,cv.width,cv.height);
}
function drawShares(){
  const cv=document.getElementById('shares'), w=cv.clientWidth, h=70; cv.width=w*devicePixelRatio; cv.height=h*devicePixelRatio; cv.style.height=h+'px';
  const g=cv.getContext('2d'); g.scale(devicePixelRatio,devicePixelRatio); g.clearRect(0,0,w,h);
  const names=['glance','grid','prog'], lab={glance:'glance',grid:'grid',prog:'progress'};
  let x=0; g.font='11px system-ui';
  names.forEach((nm,i)=>{ const v=E.sh[i][cur]||0, bw=v*w; g.fillStyle=ECOL[nm]; g.fillRect(x,4,bw,16); if (bw>48){ g.fillStyle='#fff'; g.fillText(`${lab[nm]} ${Math.round(100*v)}%`, x+4, 16);} x+=bw; });
  g.fillStyle='#52514e'; g.fillText('share of |contribution| to interest at the choice', 0, 34);
  const L=names.map((nm,i)=>E.lift[i][cur]||0), m=Math.max(1, ...L.map(Math.abs)), mid=w/2;
  g.font='10px system-ui';
  names.forEach((nm,i)=>{ const v=L[i], y=40+i*10; g.fillStyle=ECOL[nm]; const bw=v/m*(w/2-70); g.fillRect(bw>=0?mid:mid+bw, y, Math.abs(bw), 8); g.fillText(lab[nm], 30, y+8); });
  g.strokeStyle='#8a8984'; g.beginPath(); g.moveTo(mid,38); g.lineTo(mid,70); g.stroke();
  g.fillStyle='#52514e'; g.fillText('lift', 0, 48);
}
function drawEyeInfo(){
  const r=[], i=cur;
  r.push(['novelty: glance / grid (top-'+E.k+') / v1 shadow', `${fmt(E.ngl[i],3)} / ${fmt(E.ngr[i],3)} / ${fmt(E.nv1[i],3)}`]);
  r.push(['z at the choice: glance / grid / progress', `${fmt(E.z[0][i],2)} / ${fmt(E.z[1][i],2)} / ${fmt(E.z[2][i],2)}`]);
  r.push(['lift: glance / grid / progress', `${fmt(E.lift[0][i],2)} / ${fmt(E.lift[1][i],2)} / ${fmt(E.lift[2][i],2)}`]);
  r.push(['surprise: glance / grid mean / grid max', `${fmt(E.egl[i],4)} / ${fmt(E.egr[i],4)} / ${fmt(E.egm[i],4)}`]);
  r.push(['choice probability; best offer', `${fmt(E.p[i],2)}; ${E.best[i]?'yes':'no'}`]);
  if (E.tq.cloud) r.push(['tile quirks: QA cloud / fill / stripe / DN 255 / sat. flag', ['cloud','fill','stripe','at255','satflag'].map(k=>E.tq[k]&&E.tq[k][i]!==null?Math.round(100*E.tq[k][i])+'%':'–').join(' / ')]);
  if (E.meta.timestamp) r.push(['acquisition', `${E.meta.timestamp[i]} ${E.meta.level?E.meta.level[i]:''} ${E.meta.tier?E.meta.tier[i]:''}${E.meta.night&&E.meta.night[i]==='True'?' NIGHT':''} sun ${E.meta.sun_elevation?fmt(E.meta.sun_elevation[i],1):''}°`]);
  if (deathAt[i]) r.push(['death dry run fired', '<b>'+deathAt[i].join(', ')+'</b>']);
  document.getElementById('eyeinfo').innerHTML = r.map(([a,b])=>`<tr><td>${a}</td><td>${b}</td></tr>`).join('');
  document.getElementById('eyecap').textContent = `${E.eye}, weights glance ${E.w[0]} · grid ${E.w[1]} · progress ${E.w[2]}`;
}
function drawEye(){
  if (tileFor!==cur){ tileFor=cur; tileImg.onload=()=>drawGrid(); tileImg.src='tiles/'+S.tile[cur]+'.jpg'; }
  drawGrid(); drawGerr(); drawShares(); drawEyeInfo();
}
const _draw = draw; draw = function(){ _draw(); drawEye(); };
draw();
})();
</script>
</body>"""


def main() -> None:
    from data.tile_store import open_store

    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--out")
    ap.add_argument("--px", type=int, default=256)
    ap.add_argument("--quality", type=int, default=85)
    a = ap.parse_args()
    rd = Path(a.run).resolve()
    out = Path(a.out) if a.out else rd / "viewer"
    page = V.build(rd.name, out, a.px, a.quality)
    cfg = yaml.safe_load((rd / "config.yaml").read_text())
    E = eye_data(rd, cfg, open_store(cfg))
    if E is None:
        print(f"[viewer] {page} (v1 walk: the e09 viewer)")
        return
    html = page.read_text(encoding="utf-8")
    blob = json.dumps(E, separators=(",", ":")).replace("</", "<\\/")
    add = SCRIPT.replace("__EYE__", blob).replace("__CARD__", CARD.replace("`", "\\`"))
    assert html.rstrip().endswith("</html>") and "</body>" in html
    html = html[: html.rindex("</body>")] + add + html[html.rindex("</body>") + len("</body>") :]
    html = html.replace(f"<title>{rd.name}: the walk</title>", f"<title>{rd.name}: the two-eye walk</title>")
    page.write_text(html, encoding="utf-8")
    print(f"[viewer] {page}  (+ two-eye card, {page.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
