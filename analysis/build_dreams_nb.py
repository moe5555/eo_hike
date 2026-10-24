"""Writes analysis/dreams.ipynb (Gate 2). Execute with:

    python analysis/build_dreams_nb.py && jupyter nbconvert --to notebook --execute --inplace analysis/dreams.ipynb
"""

from pathlib import Path

import nbformat as nbf

cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s.strip()))  # noqa: E731
code = lambda s: cells.append(nbf.v4.new_code_cell(s.strip()))  # noqa: E731

md("""
# Gate 2: looking at the dreams

Three DDPMs per agent, identical except for their training set: `path_weighted` | `path_uniform` | `random_uniform`.
64 samples each with the same noise seed. **Pass if** `path_weighted` differs visibly or on at least one statistic
from `random_uniform` without memorising. "No difference" is a valid result.

Two references keep the statistics honest:
- **real crops** drawn from each training set exactly as the trainer draws them, which shows whether a sample difference reflects a *data* difference;
- a **noise floor** for each statistic: the same distance between two independent batches of 64 real crops from one set. A model-vs-model distance below the floor is not a difference.
""")

code("""
import json
from pathlib import Path
import numpy as np, pandas as pd, matplotlib.pyplot as plt, torch, torch.nn.functional as F
from matplotlib.colors import rgb_to_hsv
ROOT = Path.cwd().parent if Path.cwd().name == 'analysis' else Path.cwd()
import sys; sys.path.insert(0, str(ROOT))
from gen.train_ddpm import random_crops
tiles_all = np.load(ROOT/'data/tiles.npy', mmap_mode='r')
idx = pd.read_parquet(ROOT/'data/tiles.parquet')
SETS = ['path_weighted', 'path_uniform', 'random_uniform']
agents = sorted(p.name for p in (ROOT/'runs/ddpm').iterdir() if all((p/s/'samples.npy').exists() for s in SETS))
print('agents with all three models:', agents)
pd.set_option('display.precision', 4, 'display.width', 200)
dev = 'cuda'
""")

code("""
def set_tiles(agent, s):
    sets = pd.read_parquet(ROOT/f'data/sets/{agent}/sets.parquet')
    return sets[sets.set == s].reset_index(drop=True)

def real_crops(agent, s, n, seed):
    st = set_tiles(agent, s)
    t = torch.from_numpy(np.ascontiguousarray(tiles_all[st.tile_idx.values])).to(dev)
    w = torch.tensor(st.weight.values, dtype=torch.float32, device=dev)
    g = torch.Generator(device=dev).manual_seed(seed)
    x = random_crops(t, torch.multinomial(w, n, replacement=True, generator=g), g)
    return ((x + 1) * 127.5).round().clamp(0, 255).byte().permute(0, 2, 3, 1).cpu().numpy()

samples = {a: {s: np.load(ROOT/f'runs/ddpm/{a}/{s}/samples.npy') for s in SETS} for a in agents}
reals = {a: {s: real_crops(a, s, 64, 1) for s in SETS} for a in agents}
for a in agents:
    print(a, json.loads((ROOT/f'data/sets/{a}/info.json').read_text()))
""")

md("## 1. Side-by-side contact sheets\nTop row: samples. Bottom row: real training crops from the same set (weighted like training).")
code("""
def grid(imgs, n=8):
    g = np.full((n * 66, n * 66, 3), 255, np.uint8)
    for i, im in enumerate(imgs[: n * n]):
        r, c = divmod(i, n); g[r * 66 + 1:r * 66 + 65, c * 66 + 1:c * 66 + 65] = im
    return g
for a in agents:
    fig, axes = plt.subplots(2, 3, figsize=(18, 12.4))
    for j, s in enumerate(SETS):
        axes[0, j].imshow(grid(samples[a][s])); axes[0, j].set_title(f'{a} | {s} | samples'); axes[0, j].axis('off')
        axes[1, j].imshow(grid(reals[a][s])); axes[1, j].set_title(f'{s} | real crops'); axes[1, j].axis('off')
    fig.tight_layout(); fig.savefig(ROOT/f'notes/img/gate2_sheets_{a}.png', dpi=70); plt.show()
""")

md("""
## 2. Memorisation check
For each sample: the nearest 64×64 window, by pixel L2, among *all* windows (stride 1) of all training tiles, under all 8 rotations and flips.
This is an exhaustive search done as a convolution. Reference: the same nearest distance for 64 real crops from tiles **not** in that training set.
If samples sit much closer to the training data than unseen real imagery does, the model is copying.
""")
code("""
D8 = [(k, f) for f in (False, True) for k in range(4)]
def d8(x):  # x [n,3,64,64] -> [8n,3,64,64]
    return torch.cat([torch.rot90(x.flip(-1) if f else x, k, (-2, -1)) for k, f in D8])

@torch.no_grad()
def nearest(q_u8, tile_ids, chunk=3):
    q = torch.from_numpy(q_u8).to(dev).permute(0, 3, 1, 2).float() / 255
    n = len(q); qq = d8(q)                                   # 8n kernels
    qn = (qq ** 2).sum((1, 2, 3))
    best = torch.full((n,), float('inf'), device=dev); arg = torch.zeros((n, 3), dtype=torch.long, device=dev)
    ones = torch.ones(1, 3, 64, 64, device=dev)
    for c0 in range(0, len(tile_ids), chunk):
        ids = tile_ids[c0:c0 + chunk]
        t = torch.from_numpy(np.ascontiguousarray(tiles_all[ids])).to(dev).permute(0, 3, 1, 2).float() / 255
        with torch.autocast('cuda', dtype=torch.float16):
            xc = F.conv2d(t, qq)                             # [B, 8n, 193, 193]
        tn = F.conv2d(t ** 2, ones)                          # [B, 1, 193, 193]
        d = (tn + qn[None, :, None, None] - 2 * xc.float()).clamp_min(0)
        d = d.view(len(ids), 8, n, -1).amin(1)               # min over D8 -> [B, n, P]
        v, pos = d.permute(1, 0, 2).reshape(n, -1).min(1)
        better = v < best
        best = torch.where(better, v, best)
        b_tile = pos // d.shape[-1]; b_pos = pos % d.shape[-1]
        new = torch.stack([torch.as_tensor(ids, device=dev)[b_tile], b_pos // 193, b_pos % 193], 1)
        arg[better] = new[better]
    arg = arg.cpu().numpy()
    # exact fp32 RMSE of the winning window (the fp16 search leaves ~1 RMSE of numerical noise)
    rmse = np.empty(n)
    for i, (t, y, x) in enumerate(arg):
        w = torch.from_numpy(np.ascontiguousarray(tiles_all[t, y:y + 64, x:x + 64])).to(dev).permute(2, 0, 1).float() / 255
        rmse[i] = float(((d8(q[i:i + 1]) - w[None]) ** 2).mean((1, 2, 3)).min().sqrt()) * 255
    return rmse, arg

mem = {}
pool = np.flatnonzero(~idx.tv.values)
for a in agents:
    for s in SETS:
        tr = np.sort(set_tiles(a, s).tile_idx.unique())
        rng = np.random.default_rng(7)
        outside = rng.choice(np.setdiff1d(pool, tr), 64, replace=False)
        o = tiles_all[outside]; oy, ox = rng.integers(0, 193, 64), rng.integers(0, 193, 64)
        ref = np.stack([o[i, oy[i]:oy[i] + 64, ox[i]:ox[i] + 64] for i in range(64)])
        r_s, a_s = nearest(samples[a][s], tr)
        r_r, _ = nearest(ref, tr)
        mem[(a, s)] = dict(sample_rmse=r_s, ref_rmse=r_r, arg=a_s, textured_s=samples[a][s].reshape(64, -1).std(1) > 12, textured_r=ref.reshape(64, -1).std(1) > 12)
# Flat images (open sea, saturated snow) match any other flat image at RMSE ~0, so nearness says
# nothing about copying for them. "textured" = pixel std > 12 (0-255); the copy test is read on those.
rows = []
for (a, s), m in mem.items():
    ts, tr_ = m['textured_s'], m['textured_r']
    rows.append({'agent': a, 'set': s, 'sample_nn_rmse_median': np.median(m['sample_rmse']), 'unseen_real_nn_rmse_median': np.median(m['ref_rmse']),
                 'textured_samples': int(ts.sum()), 'textured_sample_nn_median': np.median(m['sample_rmse'][ts]) if ts.any() else np.nan,
                 'textured_sample_nn_min': m['sample_rmse'][ts].min() if ts.any() else np.nan,
                 'textured_unseen_nn_median': np.median(m['ref_rmse'][tr_]) if tr_.any() else np.nan,
                 'textured_unseen_nn_min': m['ref_rmse'][tr_].min() if tr_.any() else np.nan,
                 'frac_textured_samples_closer_than_any_unseen': (m['sample_rmse'][ts] < m['ref_rmse'][tr_].min()).mean() if ts.any() and tr_.any() else np.nan})
memtab = pd.DataFrame(rows).set_index(['agent', 'set'])
memtab
""")
code("""
def crop_at(a):
    t, y, x = a; return np.asarray(tiles_all[t, y:y + 64, x:x + 64])
for a in agents:
    fig, axes = plt.subplots(6, 16, figsize=(16, 6.6))
    for j, s in enumerate(SETS):
        m = mem[(a, s)]; order = np.argsort(m['sample_rmse'])[:16]   # the 16 closest = worst case
        for k, i in enumerate(order):
            axes[2 * j, k].imshow(samples[a][s][i]); axes[2 * j, k].set_title(f'{m["sample_rmse"][i]:.0f}', fontsize=7)
            axes[2 * j + 1, k].imshow(crop_at(m['arg'][i]))
        axes[2 * j, 0].set_ylabel(s[:12], fontsize=7)
    for ax in axes.flat: ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle(f'{a}: the 16 samples closest to training data (row) and their nearest training crop (row below; best match up to rotation/flip). Title = RMSE 0-255')
    fig.tight_layout(); plt.show()
""")

md("""
## 3. Cheap statistics
Colour histogram: joint RGB, 8 bins per channel; distance = Jensen–Shannon (base 2, 0 = identical, 1 = disjoint).
Brightness = mean of RGB/255; saturation = HSV S. Diversity = mean pairwise pixel RMSE between the 64 images.
""")
code("""
def hist(imgs):
    q = (imgs.reshape(-1, 3) // 32).astype(np.int64)
    h = np.bincount(q[:, 0] * 64 + q[:, 1] * 8 + q[:, 2], minlength=512).astype(float)
    return h / h.sum()
def js(p, q):
    m = (p + q) / 2
    kl = lambda a, b: np.sum(np.where(a > 0, a * np.log2(np.where(a > 0, a, 1) / np.where(b > 0, b, 1)), 0))
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)
def summ(imgs):
    f = imgs.astype(np.float32) / 255
    hsv = rgb_to_hsv(f.reshape(-1, 3))
    x = torch.from_numpy(f.reshape(len(f), -1)).to(dev)
    pd_ = torch.cdist(x, x) / np.sqrt(x.shape[1]) * 255
    return {'brightness': f.mean(), 'saturation': hsv[:, 1].mean(), 'r': f[..., 0].mean(), 'g': f[..., 1].mean(), 'b': f[..., 2].mean(),
            'diversity_rmse': float(pd_.sum() / (len(f) * (len(f) - 1)))}

rows = []
for a in agents:
    for s in SETS:
        rows.append({'agent': a, 'set': s, 'kind': 'samples', **summ(samples[a][s])})
        rows.append({'agent': a, 'set': s, 'kind': 'real', **summ(reals[a][s])})
stat = pd.DataFrame(rows).set_index(['agent', 'kind', 'set']).sort_index()
stat
""")

md("Noise floor: spread of each statistic and of JS distance across 20 independent batches of 64 real crops from one set (`random_uniform`).")
code("""
floor = {}
for a in agents:
    bs = [real_crops(a, 'random_uniform', 64, 100 + i) for i in range(20)]
    sm = pd.DataFrame([summ(b) for b in bs])
    hs = [hist(b) for b in bs]
    jsd = [js(hs[i], hs[j]) for i in range(20) for j in range(i + 1, 20)]
    floor[a] = {**{f'{c}_sd': sm[c].std() for c in sm}, 'js_median': np.median(jsd), 'js_p95': np.percentile(jsd, 95)}
pd.DataFrame(floor).T
""")
code("""
pairs = [('path_weighted', 'random_uniform'), ('path_uniform', 'random_uniform'), ('path_weighted', 'path_uniform')]
rows = []
for a in agents:
    for kind, src in [('samples', samples), ('real', reals)]:
        for p, q in pairs:
            sp, sq = summ(src[a][p]), summ(src[a][q])
            rows.append({'agent': a, 'kind': kind, 'pair': f'{p} vs {q}', 'js_hist': js(hist(src[a][p]), hist(src[a][q])),
                         **{f'd_{c}': sp[c] - sq[c] for c in ['brightness', 'saturation', 'diversity_rmse']}})
cmp = pd.DataFrame(rows).set_index(['agent', 'kind', 'pair'])
cmp['js_over_floor_p95'] = [r.js_hist / floor[a]['js_p95'] for (a, _, _), r in cmp.iterrows()]
for c in ['brightness', 'saturation', 'diversity_rmse']:
    cmp[f'd_{c}_in_sd'] = [r[f'd_{c}'] / floor[a][f'{c}_sd'] for (a, _, _), r in cmp.iterrows()]
cmp
""")
code("""
for a in agents:
    fig, axes = plt.subplots(1, 3, figsize=(15, 3.2))
    for s, c in zip(SETS, ['C3', 'C0', 'C7']):
        for kind, src, ls in [('samples', samples, '-'), ('real', reals, ':')]:
            f = src[a][s].astype(np.float32) / 255
            hsv = rgb_to_hsv(f.reshape(-1, 3))
            axes[0].hist(f.mean(-1).ravel(), 64, range=(0, 1), histtype='step', color=c, ls=ls, density=True, label=f'{s} {kind}')
            axes[1].hist(hsv[:, 1], 64, range=(0, 1), histtype='step', color=c, ls=ls, density=True)
            axes[2].hist(hsv[:, 0], 64, range=(0, 1), histtype='step', color=c, ls=ls, density=True)
    for ax, t in zip(axes, ['pixel brightness', 'saturation', 'hue']): ax.set_title(f'{a}: {t}')
    axes[0].legend(fontsize=7); plt.show()
""")

md("""
## 3b. Same noise, same dream? And do samples follow their data's composition?
Same-index RMSE between models (identical noise) vs RMSE between different samples. Then the share of bright (mean > 0.6, mostly snow)
and dark (mean < 0.12, deep water) images in samples vs 2,000 real crops of the same training set.
""")
code("""
rows = []
for a in agents:
    S = {s: samples[a][s].astype(np.float32) / 255 for s in SETS}
    rm = lambda x, y: np.sqrt(((x - y) ** 2).mean((1, 2, 3))) * 255
    for i, p in enumerate(SETS):
        for q in SETS[i + 1:]:
            rows.append({'agent': a, 'pair': f'{p} vs {q}', 'same_noise_rmse': rm(S[p], S[q]).mean(),
                         'different_sample_rmse': np.mean([rm(S[p], np.roll(S[q], k, 0)).mean() for k in range(1, 64)])})
display(pd.DataFrame(rows).set_index(['agent', 'pair']))
rows = []
for a in agents:
    for s in SETS:
        r = real_crops(a, s, 2000, 5).astype(np.float32) / 255; m_r = r.mean((1, 2, 3))
        x = samples[a][s].astype(np.float32) / 255; m_s = x.mean((1, 2, 3))
        rows.append({'agent': a, 'set': s, 'real_bright': (m_r > 0.6).mean(), 'samples_bright': (m_s > 0.6).mean(),
                     'real_dark': (m_r < 0.12).mean(), 'samples_dark': (m_s < 0.12).mean(), 'real_brightness': m_r.mean(), 'samples_brightness': m_s.mean()})
pd.DataFrame(rows).set_index(['agent', 'set'])
""")

md("## 4. Observations (descriptive, one line per model)\n*(written after running; see `notes/observations.md`)*")

nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
nbf.write(nb, Path(__file__).with_name("dreams.ipynb"))
print("wrote analysis/dreams.ipynb")
