"""Figures and tables of agents_paper.typ, all from real walks. Offline apart from any tile missing from the cache.

    .venv/bin/python notes/agents_paper/build_figures.py

Writes notes/agents_paper/fig/. Reads notes/07_film_arc/results/drawings/ (run analysis/h0111/drawings.py first).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "analysis" / "h0111")]

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from common import RUNS, places
from drawings import AGES, grid_crops, heldout_set, mosaic, net, per_tile_mse, pick_by_contrast
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle
from PIL import Image, ImageDraw, ImageFont

from agent import signals as S
from data.tile_store import TileStore

RUN = "h2910_bored_paris_s0"
FIG = Path(__file__).resolve().parent / "fig"
INK, MUTED, GRID, BLUE, ORANGE = "#0b0b0b", "#52514e", "#dddcd7", "#2a78d6", "#eb6834"  # validated with dataviz/scripts/validate_palette.js
PATIENCE = 0.3
K, CROP = 16, 64
plt.rcParams.update({"font.family": "serif", "font.serif": ["STIXGeneral"], "mathtext.fontset": "stix", "axes.formatter.use_mathtext": True, "svg.fonttype": "path", "font.size": 9,
                     "text.color": INK, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": GRID, "axes.linewidth": 0.8,
                     "xtick.major.size": 0, "ytick.major.size": 0, "xtick.minor.size": 0, "ytick.minor.size": 0, "axes.spines.top": False, "axes.spines.right": False, "axes.unicode_minus": False})
store = TileStore(cache_gb=30.0)
steps = places(pd.read_parquet(RUNS / RUN / "steps.parquet"))
first = steps.drop_duplicates("tile_idx").set_index("tile_idx").step
GLACIER = int(first[first == 3800].index[0])


def save(fig, name: str) -> None:
    fig.savefig(FIG / f"{name}.svg", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def fixed_crops(i: int) -> tuple[np.ndarray, torch.Tensor, tuple[torch.Tensor, torch.Tensor]]:
    a = store.get_lowres(i)
    img = torch.from_numpy(a.copy())[None]
    off = S.fixed_offsets([i], K, 256, CROP, "cpu")
    return a, S.patches(img, torch.zeros(1, dtype=torch.bool), K, CROP, torch.Generator(), off)[0], off


def to_img(x: torch.Tensor) -> np.ndarray:
    return x.clamp(0, 1).permute(1, 2, 0).numpy()


def crops_figure() -> None:
    a, x, (oy, ox) = fixed_crops(GLACIER)
    fig, ax = plt.subplots(1, 2, figsize=(6.2, 2.9), gridspec_kw={"wspace": 0.42})
    ax[0].imshow(a, interpolation="nearest")
    for y, x0 in zip(oy[0].tolist(), ox[0].tolist()):
        ax[0].add_patch(Rectangle((x0, y), CROP, CROP, fill=False, ec="white", lw=0.8))
    ax[0].set_title("One tile: 256 px, about 10.7 km across,\nwith its 16 fixed 64 px crops", fontsize=9, color=INK)
    grid = np.ones((4 * 32 + 3 * 3, 4 * 32 + 3 * 3, 3))
    for k in range(K):
        r, c = k // 4, k % 4
        grid[r * 35 : r * 35 + 32, c * 35 : c * 35 + 32] = to_img(x[k])
    ax[1].imshow(grid, interpolation="nearest")
    ax[1].set_title("What the network receives: 16 crops,\neach reduced to 32 × 32 px (about 2.7 km)", fontsize=9, color=INK)
    for q in ax:
        q.set_xticks([]), q.set_yticks([])
        for s in q.spines.values():
            s.set_visible(False)
    fig.add_artist(FancyArrowPatch((0.475, 0.46), (0.545, 0.46), transform=fig.transFigure, arrowstyle="-|>", mutation_scale=11, color=MUTED, lw=1))
    save(fig, "crops")


@torch.no_grad()
def autoencoder_figure() -> None:
    _, x, _ = fixed_crops(GLACIER)
    k = int(x.flatten(1).std(1).argmax())
    pred = net(RUN, 5000)(x[k][None])[0]
    layers = [("3×32×32", 32), ("16×16×16", 16), ("32×8×8", 8), ("64×4×4", 4), ("96×2×2", 2.4), ("64", 1.4), ("96×2×2", 2.4), ("64×4×4", 4), ("32×8×8", 8), ("16×16×16", 16), ("16×32×32", 32), ("3×32×32", 32)]
    fig, ax = plt.subplots(figsize=(6.6, 2.0))
    ax.set_xlim(-14, 134), ax.set_ylim(-26, 25), ax.axis("off")
    ax.imshow(to_img(x[k]), extent=(-14, 6, -10, 10), interpolation="nearest", zorder=2)
    ax.imshow(to_img(pred), extent=(114, 134, -10, 10), interpolation="nearest", zorder=2)
    xs = np.linspace(14, 106, 10)
    for i, (px, (lab, h)) in enumerate(zip(xs, layers[1:-1])):
        h = 1.0 + h * 0.42
        c = ORANGE if lab == "64" else BLUE
        ax.add_patch(Rectangle((px - 2.2, -h), 4.4, 2 * h, fc=c, ec="none"))
        ax.text(px, -17 if i % 2 else -21.5, lab, ha="center", va="center", fontsize=7.5, color=MUTED)
    ax.annotate("", xy=(13, 0), xytext=(7, 0), arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=0.9))
    ax.annotate("", xy=(113, 0), xytext=(107, 0), arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=0.9))
    for a, b in zip(xs[:-1], xs[1:]):
        ax.annotate("", xy=(b - 2.6, 0), xytext=(a + 2.6, 0), arrowprops=dict(arrowstyle="-", color=GRID, lw=0.9))
    ax.text(-4, 16, "crop $x$", ha="center", fontsize=9), ax.text(124, 16, r"drawing $\hat{x}$", ha="center", fontsize=9)
    ax.text(30, 16, "encoder $E$", ha="center", fontsize=9), ax.text(85, 16, "decoder $D$", ha="center", fontsize=9)
    ax.text(xs[4], 8, "latent $z$\n64 numbers", ha="center", va="bottom", fontsize=9)
    save(fig, "autoencoder")


@torch.no_grad()
def drawings_figure() -> None:
    """Four rows of analysis/h0111/drawings.py's sheets, with labels large enough for a page: two never-visited tiles and two from long stays."""
    held_ids, _ = heldout_set(store)
    never = pick_by_contrast(store, [i for i in held_ids if i not in set(steps.tile_idx)], 6)
    top = steps[steps.place_len >= 60].groupby("place").tile_idx.agg(lambda v: v.value_counts().index[0])
    walked = pick_by_contrast(store, [int(i) for i in top if store.cached(int(i))], 6)
    rows = [never[0], never[4], walked[1], walked[5]]
    print("drawings rows", rows, [int(first.get(i, -1)) for i in rows])
    nets = {a: net(RUN, a) for a in AGES}
    cols = [None, *AGES]
    cell, pad, head, foot = 256, 8, 44, 42
    font = ImageFont.load_default(size=30)
    im = Image.new("RGB", (len(cols) * (cell + pad) - pad, head + len(rows) * (cell + foot)), "white")
    d = ImageDraw.Draw(im)
    for c, a in enumerate(cols):
        d.text((c * (cell + pad) + 2, 2), "real" if a is None else f"step {a:,}", fill=INK, font=font)
    for r, i in enumerate(rows):
        x, y = grid_crops(store.get_lowres(i)), head + r * (cell + foot)
        for c, a in enumerate(cols):
            pred = x if a is None else nets[a](x)
            im.paste(Image.fromarray(mosaic(pred)).resize((cell, cell), Image.Resampling.NEAREST), (c * (cell + pad), y))
            if a is not None:
                d.text((c * (cell + pad) + 2, y + cell + 2), f"{per_tile_mse(pred, x):.4f}", fill=MUTED, font=font)
    im.save(FIG / "drawings.png", optimize=True)


def worked_step(step: int = 424) -> None:
    c = pd.read_parquet(RUNS / RUN / "candidates.parquet")
    c = c[c.step == step].reset_index(drop=True)
    t = 0.5
    p = np.exp(c.I / t)
    p /= p.sum()
    assert np.allclose(p, c.p, atol=1e-3)
    assert np.allclose(c.I, c.n_z + c.g_z, atol=1e-4)
    for i in c.tile_idx:
        Image.fromarray(store.get_lowres(int(i))).resize((128, 128), Image.Resampling.BOX).save(FIG / f"cand_{int(i)}.png", optimize=True)
    f = lambda v: f"{v:.2f}".replace("-", "\u2212")
    rows = [{"tile": int(r.tile_idx), "kind": "far" if r.kind == "long" else "near", "e": f(r.e * 1e3), "n": f(r.n), "g": f(r.g * 1e3), "n_z": f(r.n_z), "g_z": f(r.g_z), "I": f(r.I), "p": "<0.001" if r.p < 0.001 else f"{r.p:.3f}", "chosen": bool(r.chosen)} for r in c.itertuples()]
    (FIG / "worked_step.json").write_text(json.dumps(rows, indent=1))
    print("worked step", c[["kind", "e", "n", "g", "I", "p", "chosen"]].round(4).to_string())


def boredom_figure(end: int = 125) -> None:
    s = steps[steps.step < end]
    fig, ax = plt.subplots(2, 1, figsize=(6.4, 3.0), sharex=True, gridspec_kw={"hspace": 0.16, "height_ratios": [1, 1]})
    ax[0].plot(s.step, s.max_I, color=BLUE, lw=1.4, solid_joinstyle="round")
    ax[0].axhline(0, color=MUTED, lw=0.8)
    ax[0].set_ylabel(r"best interest, $\max_c\, I(c)$")
    peak = (0.9 * s.B + 0.1 * (s.max_I < 0)).where(s.bored_event, s.B_after)  # at an event, the value before the reset, so the crossing shows
    bx, by = [], []
    for st, v, ev in zip(s.step, peak, s.bored_event):
        bx.append(st), by.append(v)
        if ev:
            bx.append(st), by.append(0.0)
    ax[1].plot(bx, by, color=BLUE, lw=1.4, solid_joinstyle="round")
    ax[1].axhline(PATIENCE, color=MUTED, lw=0.8, ls=(0, (4, 3)))
    ax[1].text(end - 1, PATIENCE + 0.012, "patience $p = 0.3$", ha="right", va="bottom", fontsize=8, color=MUTED)
    ax[1].set_ylabel("boredom $B$")
    ax[1].set_xlabel("step"), ax[1].set_ylim(0, 0.42), ax[1].set_xlim(0, end - 1)
    for b in s[s.bored_event].step:
        for q in ax:
            q.axvline(b, color=ORANGE, lw=1.1, zorder=0)
    ax[0].text(0.995, 0.93, "orange: bored event, then a teleport", transform=ax[0].transAxes, ha="right", va="top", fontsize=8, color=MUTED, bbox=dict(fc="white", ec="none", pad=1.5))
    for q in ax:
        q.grid(axis="y", color=GRID, lw=0.5), q.set_axisbelow(True)
    save(fig, "boredom")


def heldout_figure() -> None:
    h = pd.read_parquet(RUNS / RUN / "heldout.parquet")
    b = pd.read_csv(ROOT / "notes" / "07_film_arc" / "results" / "drawings" / "drawings_baselines.csv")
    flat, pca = float(b.mean_mse[0]), float(b.mean_mse[1])
    h1 = h[h.step > 0]
    fig, ax = plt.subplots(figsize=(6.2, 2.5))
    ax.plot(h1.step, h1.heldout_mse, color=BLUE, lw=1.4, solid_joinstyle="round")
    ax.set_xscale("log"), ax.set_yscale("log"), ax.set_xlim(25, 5000), ax.set_ylim(0.001, 0.09)
    for v, lab in ((flat, "one flat colour per crop"), (pca, "PCA with 64 numbers")):
        ax.axhline(v, color=MUTED, lw=0.8, ls=(0, (4, 3)))
        ax.text(27, v * 0.93 if v == flat else v * 1.07, lab, fontsize=8, color=MUTED, va="top" if v == flat else "bottom")
    ax.text(27, 0.0635, "untrained network (step 0): 0.064", fontsize=8, color=MUTED, va="center")
    ax.text(62, 0.0115, "the walking network", fontsize=8, color=INK, ha="left")
    ax.set_xticks([25, 100, 500, 1000, 5000]), ax.set_xticklabels(["25", "100", "500", "1,000", "5,000"])
    ax.set_yticks([0.001, 0.01]), ax.set_yticklabels(["0.001", "0.01"])
    ax.minorticks_off()
    ax.set_xlabel("step (log scale)"), ax.set_ylabel("held-out error (log scale)")
    ax.grid(axis="y", color=GRID, lw=0.5), ax.set_axisbelow(True)
    save(fig, "heldout")


def map_figure() -> None:
    idx = store.idx
    land = idx[idx.cover == "land"].iloc[::25]
    ramp = LinearSegmentedColormap.from_list("blue", ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    ax.scatter(land.lon, land.lat, s=0.25, color="#e4e3de", lw=0, rasterized=True)
    jump = steps.dist_km.to_numpy() > 30
    lon, lat, st = steps.lon.to_numpy(), steps.lat.to_numpy(), steps.step.to_numpy()
    for i in np.flatnonzero(jump):
        if abs(lon[i] - lon[i - 1]) < 180:
            ax.plot(lon[i - 1 : i + 1], lat[i - 1 : i + 1], color="#b9b8b2", lw=0.35, zorder=1)
    sc = ax.scatter(lon, lat, c=st, cmap=ramp, s=3.5, lw=0, zorder=2)
    ax.annotate("Paris (start)", (2.35, 48.86), (-8, 66), fontsize=8, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6), ha="center")
    ax.annotate("Patagonia,\nsteps 3,696–4,724", (-73, -47.5), (-122, -44), fontsize=8, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6), ha="center", va="center")
    ax.set_xlim(-180, 180), ax.set_ylim(-84, 84), ax.set_aspect("equal"), ax.axis("off")
    cb = fig.colorbar(sc, ax=ax, orientation="horizontal", fraction=0.035, pad=0.02, aspect=40)
    cb.set_label("step", fontsize=8, color=MUTED), cb.outline.set_visible(False), cb.set_ticks([0, 1000, 2000, 3000, 4000, 5000]), cb.set_ticklabels(["0", "1,000", "2,000", "3,000", "4,000", "5,000"])
    save(fig, "map")


def loop_figure() -> None:
    fig, ax = plt.subplots(figsize=(6.6, 2.5))
    ax.set_xlim(0, 100), ax.set_ylim(0, 40), ax.axis("off")

    def box(cx, cy, t, w=20, h=10, fc="#f4f3ef", ec=GRID):
        ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h, boxstyle="round,pad=0,rounding_size=1", fc=fc, ec=ec, lw=0.8))
        ax.text(cx, cy, t, ha="center", va="center", fontsize=8)

    def arrow(a, b, **kw):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=8, color=MUTED, lw=0.8, shrinkA=0, shrinkB=0, **kw))

    top, bot = 31, 9
    xs = [10, 36, 62, 90]
    box(xs[0], top, "Candidates\nneighbours, plus\nrare far offers")
    box(xs[1], top, "Look and score\n$e,\\ n,\\ g$ for each\ncandidate")
    box(xs[2], top, "Compare\nz-scores, then\ninterest $I$")
    box(xs[3], top, "Choose\nsoftmax over $I$", w=20)
    box(xs[3], bot, "Move and learn\n4 Adam steps on\nnew + replayed crops", w=20)
    box(xs[2], bot, "Remember\nbuffer and archive")
    box(xs[1], bot, "Boredom\nupdate $B$; is\n$B$ above patience?")
    box(xs[0], bot, "Teleport\nnext step: one\nrandom landing", fc="#fde9e0", ec=ORANGE)
    for a, b in zip(xs[:3], xs[1:]):
        arrow((a + 10, top), (b - 10, top))
    arrow((xs[3], top - 5), (xs[3], bot + 5))
    arrow((xs[3] - 10, bot), (xs[2] + 10, bot))
    arrow((xs[2] - 10, bot), (xs[1] + 10, bot))
    arrow((xs[1] - 10, bot), (xs[0] + 10, bot))
    ax.text((xs[0] + xs[1]) / 2, bot + 1.4, "yes", ha="center", fontsize=7.5, color=MUTED)
    arrow((xs[1] - 3, bot + 5), (xs[0] + 3, top - 5))
    ax.text((xs[0] + xs[1]) / 2 + 4.5, 20, "no: next step", ha="left", fontsize=7.5, color=MUTED)
    arrow((xs[0], bot + 5), (xs[0], top - 5))
    save(fig, "loop")


if __name__ == "__main__":
    FIG.mkdir(exist_ok=True)
    crops_figure()
    autoencoder_figure()
    drawings_figure()
    worked_step()
    boredom_figure()
    heldout_figure()
    map_figure()
    loop_figure()
