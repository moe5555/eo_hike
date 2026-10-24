"""Writes analysis/walks.ipynb (Gate 1). Execute with:

    python analysis/build_walks_nb.py && jupyter nbconvert --to notebook --execute --inplace analysis/walks.ipynb
"""

from pathlib import Path

import nbformat as nbf

cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s.strip()))  # noqa: E731
code = lambda s: cells.append(nbf.v4.new_code_cell(s.strip()))  # noqa: E731

md("""
# Gate 1: looking at the walks

For every run in `runs/*_s*`: path map, contact sheet, stats table against the subset's base rates,
held-out learning curve, plus two diagnostics for the noisy-TV test and seed divergence.

**Pass if** (a) at least one agent's stats clearly differ from `random`; (b) `baseline` visits fewer
cloudy/noise tiles than `novelty_only`; (c) seeds and temperaments produce visibly different paths.
Noise here = the synthetic noisy-TV cluster (fresh noise per look) plus real clouds (max 25 % in Major TOM).
""")

code("""
import json
from pathlib import Path
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from PIL import Image
ROOT = Path.cwd().parent if Path.cwd().name == 'analysis' else Path.cwd()
idx = pd.read_parquet(ROOT/'data/tiles.parquet')
tiles = np.load(ROOT/'data/tiles.npy', mmap_mode='r')
ORDER = ['random', 'baseline', 'novelty_only', 'surprise_only', 'myopic', 'wide', 'restless', 'tvtest_baseline', 'tvtest_novelty_only', 'tvtest_surprise_only']
runs = sorted([p for p in (ROOT/'runs').glob('*_s*') if (p/'steps.parquet').exists()],
              key=lambda p: (ORDER.index(p.name.rsplit('_s', 1)[0]) if p.name.rsplit('_s', 1)[0] in ORDER else 99, p.name))
steps = {p.name: pd.read_parquet(p/'steps.parquet') for p in runs}
cands = {p.name: pd.read_parquet(p/'candidates.parquet') for p in runs if (p/'candidates.parquet').exists()}
held = {p.name: pd.read_parquet(p/'heldout.parquet') for p in runs if (p/'heldout.parquet').exists()}
meta = {p.name: json.loads((p/'meta.json').read_text()) for p in runs}
print(len(idx), 'tiles;', len(runs), 'runs:', [p.name for p in runs])
pd.set_option('display.width', 200, 'display.max_columns', 40, 'display.precision', 3)
""")

md("## Base rates of the subset\nWhat a walker that ignored content would see on average.")
code("""
nb = np.load(ROOT/'data/neighbours_15km.npz')
import sys; sys.path.insert(0, str(ROOT/'data'))
from prepare import haversine_km
src = np.repeat(np.arange(len(idx)), np.diff(nb['indptr']))
nd = haversine_km(idx.lat.values[src], idx.lon.values[src], idx.lat.values[nb['indices']], idx.lon.values[nb['indices']])
base = pd.Series({
    'tiles': len(idx), 'tv_tiles': int(idx.tv.sum()), 'tv_frac': idx.tv.mean(),
    'mean_cloud_cover': idx.cloud_cover.mean(), 'frac_cloud_gt10': (idx.cloud_cover > 10).mean(),
    'mean_neighbours_15km': np.diff(nb['indptr']).mean(), 'mean_neighbour_dist_km': nd.mean(),
})
base.to_frame('subset')
""")

md("""
## Stats table
`revisit_rate` = 1 − unique/steps. `rg_km` = radius of gyration of the path, `net_km` = start→end distance.
`tv_steps` = share of steps on noisy-TV tiles; `first_tv` = step of first TV visit; `max_tv_dwell` = longest run of consecutive TV steps.
`cloud` = mean cloud cover of visited (non-TV) tiles vs the subset base rate.
""")
code("""
def path_stats(name, s):
    lat, lon = s.lat.values, s.lon.values
    clat, clon = lat.mean(), lon.mean()
    rg = np.sqrt(np.mean(haversine_km(lat, lon, clat, clon) ** 2))
    tvs = s.tv.values.astype(int)
    runs_tv = np.diff(np.flatnonzero(np.diff(np.r_[0, tvs, 0])))[::2] if tvs.any() else [0]
    nontv = s[~s.tv]
    return {
        'run': name, 'steps': len(s), 'unique': s.tile_idx.nunique(), 'revisit_rate': 1 - s.tile_idx.nunique() / len(s),
        'mean_step_km': s.dist_km.iloc[1:].mean(), 'median_step_km': s.dist_km.iloc[1:].median(),
        'rg_km': rg, 'net_km': haversine_km(lat[0], lon[0], lat[-1], lon[-1]),
        'long_jumps': int((s.jump_type == 'long').sum()), 'bored_events': int(s.bored_event.sum()),
        'tv_steps': s.tv.mean(), 'tv_unique': s[s.tv].tile_idx.nunique(),
        'first_tv': int(s.step[s.tv].min()) if s.tv.any() else -1, 'max_tv_dwell': int(max(runs_tv)),
        'cloud': nontv.cloud_cover.mean(), 'cloud_vs_base': nontv.cloud_cover.mean() / idx[~idx.tv].cloud_cover.mean(),
        'frac_cloud_gt10': (nontv.cloud_cover > 10).mean(),
        'lat_mean': lat.mean(), 'frac_alps_lat_gt_45_8': (lat > 45.8).mean(),
        'minutes': meta[name].get('seconds', np.nan) / 60,
    }
stats = pd.DataFrame([path_stats(k, v) for k, v in steps.items()]).set_index('run')
stats
""")

md("Grouped by temperament (mean of seeds), with the random walk as reference.")
code("""
g = stats.copy(); g['temperament'] = [r.rsplit('_s', 1)[0] for r in g.index]
cols = ['unique', 'revisit_rate', 'mean_step_km', 'rg_km', 'net_km', 'bored_events', 'tv_steps', 'max_tv_dwell', 'cloud_vs_base', 'frac_alps_lat_gt_45_8']
gm = g.groupby('temperament', sort=False)[cols].mean()
gm
""")

md("## Path maps\nBackground: every tile pasted at its position (equirectangular km). Line coloured by step (dark→yellow), white x = bored event, magenta ring = noisy-TV cluster, green dot = start.")
code("""
LAT0 = 45.25
def to_km(lat, lon):
    return (np.asarray(lon) - 6.4) * np.cos(np.radians(LAT0)) * 111.32, (np.asarray(lat) - 43.4) * 110.57
PX = 0.5  # km per canvas pixel
W, H = int(to_km(47.1, 12.7)[0] / PX), int(to_km(47.1, 12.7)[1] / PX)
canvas = np.full((H, W, 3), 40, np.uint8)
xs, ys = to_km(idx.lat.values, idx.lon.values)
tpx = int(round(10.68 / PX))
for i in range(len(idx)):
    t = np.asarray(Image.fromarray(np.asarray(tiles[i])).resize((tpx, tpx), Image.Resampling.BOX))
    cx, cy = int(xs[i] / PX), H - int(ys[i] / PX)
    y0, x0 = max(cy - tpx // 2, 0), max(cx - tpx // 2, 0)
    canvas[y0:y0 + tpx, x0:x0 + tpx] = t[: H - y0, : W - x0][: min(tpx, H - y0), : min(tpx, W - x0)]
canvas_dim = (canvas * 0.55).astype(np.uint8)
tvx, tvy = to_km(45.40, 8.55)

def path_map(ax, name):
    s = steps[name]
    x, y = to_km(s.lat.values, s.lon.values)
    ax.imshow(canvas_dim, extent=(0, W * PX, 0, H * PX))
    jump = s.jump_type.values != 'neighbour'
    seg_x, seg_y = x.copy(), y.copy()
    seg_x[jump], seg_y[jump] = np.nan, np.nan   # break the line at jumps
    from matplotlib.collections import LineCollection
    pts = np.stack([x, y], 1)
    segs = np.stack([pts[:-1], pts[1:]], 1)[~jump[1:]]
    lc = LineCollection(segs, cmap='plasma', linewidths=1.2)
    lc.set_array(np.arange(len(s) - 1)[~jump[1:]]); ax.add_collection(lc)
    ax.scatter(x[jump], y[jump], s=10, c=np.flatnonzero(jump), cmap='plasma', vmin=0, vmax=len(s), marker='o', edgecolors='w', linewidths=0.4, zorder=4)
    b = s.bored_event.values
    ax.scatter(x[b], y[b], s=40, c='w', marker='x', zorder=5)
    ax.scatter(x[:1], y[:1], s=50, c='lime', zorder=6)
    ax.add_patch(plt.Circle((tvx, tvy), 16, fill=False, ec='magenta', lw=1.2))
    st = stats.loc[name]
    ax.set_title(f"{name}: {st['unique']} uniq, tv {st['tv_steps']:.0%}, bored {st['bored_events']}", fontsize=9)
    ax.set_xticks([]); ax.set_yticks([])

n = len(runs); ncol = 2; nrow = int(np.ceil(n / ncol))
fig, axes = plt.subplots(nrow, ncol, figsize=(13, 5.3 * nrow))
for ax, p in zip(axes.flat, runs): path_map(ax, p.name)
for ax in axes.flat[n:]: ax.axis('off')
fig.tight_layout(); fig.savefig(ROOT/'notes/img/gate1_paths.png', dpi=60); plt.show()
""")

md("## Visit density\nWhere each temperament spends its time (both seeds pooled), as tile visit counts.")
code("""
temps = list(dict.fromkeys(r.rsplit('_s', 1)[0] for r in steps))
fig, axes = plt.subplots(1, len(temps), figsize=(3.6 * len(temps), 3.4))
for ax, tname in zip(np.atleast_1d(axes), temps):
    s = pd.concat([v for k, v in steps.items() if k.rsplit('_s', 1)[0] == tname])
    c = s.tile_idx.value_counts()
    ax.imshow(canvas_dim, extent=(0, W * PX, 0, H * PX))
    ax.scatter(xs[c.index], ys[c.index], s=np.clip(c.values, 1, 60) * 2, c=np.log1p(c.values), cmap='viridis', alpha=0.9)
    ax.add_patch(plt.Circle((tvx, tvy), 16, fill=False, ec='magenta', lw=1))
    ax.set_title(tname, fontsize=9); ax.set_xticks([]); ax.set_yticks([])
fig.tight_layout(); plt.show()
""")

md("## Contact sheets\nEvery 10th visited tile, in order (read left→right, top→bottom). Red frame = noisy TV, white frame = bored teleport.")
code("""
def contact_sheet(name, every=10, ncol=15, px=56):
    s = steps[name].iloc[::every]
    rows = int(np.ceil(len(s) / ncol))
    sheet = np.full((rows * (px + 2), ncol * (px + 2), 3), 255, np.uint8)
    for k, r in enumerate(s.itertuples()):
        im = np.asarray(Image.fromarray(np.asarray(tiles[r.tile_idx])).resize((px, px), Image.Resampling.BOX))
        y0, x0 = (k // ncol) * (px + 2), (k % ncol) * (px + 2)
        col = (255, 0, 0) if r.tv else (255, 255, 255) if r.jump_type == 'bored' else None
        if col: sheet[y0:y0 + px + 2, x0:x0 + px + 2] = col
        sheet[y0 + 1:y0 + 1 + px, x0 + 1:x0 + 1 + px] = im
    return sheet

for p in runs:
    sh = contact_sheet(p.name)
    Image.fromarray(sh).save(ROOT/f'notes/img/gate1_contact_{p.name}.png')
    if not p.name.endswith('_s0'): continue   # all sheets are saved to notes/img; seed 0 shown inline
    plt.figure(figsize=(12, 12 * sh.shape[0] / sh.shape[1])); plt.imshow(sh); plt.axis('off'); plt.title(p.name); plt.show()
""")

md("## Learning curves\nReconstruction MSE on the fixed 200-tile held-out probe (each agent at its own crop scale, so compare within a scale).")
code("""
fig, ax = plt.subplots(figsize=(9, 4))
for k, h in held.items():
    ax.plot(h.step, h.heldout_mse, label=k, lw=1.2, ls='-' if k.endswith('_s0') else '--')
ax.set_yscale('log'); ax.set_xlabel('step'); ax.set_ylabel('held-out MSE'); ax.legend(fontsize=7, ncol=3); plt.show()
""")

md("""
## Noisy-TV diagnostic
For every step where a TV tile was among the candidates: its z-scores vs the other candidates'.
Novelty should be high for TV; progress should be low. Also: the chosen-tile signals over time.
""")
code("""
rows = []
for k, c in cands.items():
    c = c.merge(idx[['idx', 'tv', 'cloud_cover']], left_on='tile_idx', right_on='idx')
    tv_steps = c.step[c.tv].unique()
    cc = c[c.step.isin(tv_steps)]
    for is_tv, grp in cc.groupby('tv'):
        rows.append({'run': k, 'tv_candidate': is_tv, 'n': len(grp), 'n_z': grp.n_z.mean(), 'g_z': grp.g_z.mean(), 'e_z': grp.e_z.mean(), 'I': grp.I.mean(), 'p_chosen': grp.p.mean(), 'chosen_rate': grp.chosen.mean()})
    cl = c[~c.tv]
    for hi, grp in cl.groupby(cl.cloud_cover > 10):
        rows.append({'run': k, 'tv_candidate': f'real cloud>10%: {hi}', 'n': len(grp), 'n_z': grp.n_z.mean(), 'g_z': grp.g_z.mean(), 'e_z': grp.e_z.mean(), 'I': grp.I.mean(), 'p_chosen': grp.p.mean(), 'chosen_rate': grp.chosen.mean()})
tvdiag = pd.DataFrame(rows).set_index(['run', 'tv_candidate'])
tvdiag
""")
code("""
fig, axes = plt.subplots(1, 2, figsize=(13, 3.5))
for k, s in steps.items():
    if k.startswith('random'): continue
    axes[0].plot(s.step, s.tv.cumsum(), label=k, ls='-' if k.endswith('_s0') else '--')
    axes[1].plot(s.step, s.B, lw=0.6, label=k)
axes[0].set_title('cumulative steps on noisy TV'); axes[0].legend(fontsize=7, ncol=2)
axes[1].set_title('boredom B'); plt.show()
""")

md("""
## TV test (added)
The main runs rarely met the TV (7 of 1,814 tiles, 50 km from the start). In these runs baseline, novelty_only and surprise_only
start one step from the TV cluster, so exposure is guaranteed. If prediction error is the trap, surprise_only should stay.
""")
code("""
tvt = stats.loc[[r for r in stats.index if r.startswith('tvtest_')], ['unique', 'tv_steps', 'tv_unique', 'first_tv', 'max_tv_dwell', 'bored_events', 'cloud_vs_base']]
tvt
""")
code("""
fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
for ax, t in zip(axes, ['tvtest_baseline_s0', 'tvtest_novelty_only_s0', 'tvtest_surprise_only_s0']):
    if t not in steps: continue
    path_map(ax, t)
    ax.set_xlim(tvx - 80, tvx + 80); ax.set_ylim(tvy - 60, tvy + 60)
fig.tight_layout(); plt.show()
""")

md("""
## Favourite tiles
Curious agents dwell: a few tiles get dozens of visits. Which tiles, and why (mean z-scores of the chosen tile over its visits)?
""")
code("""
rows, ims = [], []
for k in ['baseline_s0', 'novelty_only_s0', 'surprise_only_s0', 'myopic_s0', 'wide_s0', 'random_s0']:
    if k not in steps: continue
    s = steps[k]; vc = s.tile_idx.value_counts()
    rows.append({'run': k, 'top10_share': vc.iloc[:10].sum() / len(s), 'tiles_ge10_visits': int((vc >= 10).sum()),
                 'share_on_ge10': vc[vc >= 10].sum() / len(s), 'immediate_return': (s.tile_idx.values[2:] == s.tile_idx.values[:-2]).mean()})
    top = vc.index[:8]
    v = s[s.tile_idx.isin(top)]
    ims.append((k, top, vc, v.groupby('tile_idx')[['n_z', 'g_z', 'e_z']].mean()))
display(pd.DataFrame(rows).set_index('run'))
fig, axes = plt.subplots(len(ims), 8, figsize=(16, 2.3 * len(ims)))
for r, (k, top, vc, z) in enumerate(ims):
    for c, t in enumerate(top):
        ax = axes[r, c]; ax.imshow(tiles[t]); ax.set_xticks([]); ax.set_yticks([])
        zz = z.loc[t] if t in z.index else None
        lab = f"{vc[t]}x" + (f" n{zz.n_z:+.1f} g{zz.g_z:+.1f} e{zz.e_z:+.1f}" if zz is not None and not np.isnan(zz.n_z) else '')
        ax.set_title(lab, fontsize=7)
    axes[r, 0].set_ylabel(k, fontsize=8)
fig.tight_layout(); plt.show()
""")

md("## Seed divergence\nJaccard overlap of visited tile sets between seed 0 and seed 1, and first step where the paths differ.")
code("""
rows = []
for tname in temps:
    a, b = steps.get(f'{tname}_s0'), steps.get(f'{tname}_s1')
    if a is None or b is None: continue
    A, Bs = set(a.tile_idx), set(b.tile_idx)
    diff = np.flatnonzero(a.tile_idx.values != b.tile_idx.values)
    rows.append({'temperament': tname, 'jaccard': len(A & Bs) / len(A | Bs), 'first_diff_step': int(diff[0]) if len(diff) else -1})
pd.DataFrame(rows).set_index('temperament')
""")

md("## Daydreams at bored events (decoded from latents near the archive's sparsest point)")
code("""
for p in runs:
    dd = sorted((p/'daydreams').glob('*.png'))
    if not dd: continue
    show = dd[:3] + ([dd[-1]] if len(dd) > 3 else [])
    fig, axes = plt.subplots(1, len(show), figsize=(3 * len(show), 3))
    for ax, f in zip(np.atleast_1d(axes), show):
        ax.imshow(Image.open(f)); ax.set_title(f'{p.name} {f.stem}', fontsize=7); ax.axis('off')
    plt.show()
""")

md("## Gate 1 checks (computed)")
code("""
r = gm.loc['random'] if 'random' in gm.index else None
checks = {}
if r is not None:
    d = {t: {c: gm.loc[t, c] / r[c] if r[c] else np.nan for c in ['unique', 'rg_km', 'revisit_rate']} for t in gm.index if t != 'random'}
    checks['(a) agent vs random (ratios: unique, rg, revisit)'] = pd.DataFrame(d).T.round(2).to_dict('index')
if {'baseline', 'novelty_only'} <= set(gm.index):
    checks['(b) tv share baseline vs novelty_only'] = (round(gm.loc['baseline', 'tv_steps'], 3), round(gm.loc['novelty_only', 'tv_steps'], 3))
    checks['(b) real-cloud ratio baseline vs novelty_only'] = (round(gm.loc['baseline', 'cloud_vs_base'], 2), round(gm.loc['novelty_only', 'cloud_vs_base'], 2))
for k, v in checks.items(): print(k, v)
""")

md("## Observations\n*(filled in after running; see `notes/observations.md`)*")

nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
nbf.write(nb, Path(__file__).with_name("walks.ipynb"))
print("wrote analysis/walks.ipynb")
