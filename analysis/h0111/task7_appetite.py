"""Task 7: appetite as a re-timing only. Nothing here touches a walker.

    python analysis/h0111/task7_appetite.py            # signal, timings, figures
    python analysis/h0111/task7_appetite.py --films    # also renders the two cuts of the Bored Paris walk to runs/h0111_films/

Appetite at step n: how fast the network is still improving on the planet, as the downward slope of log held-out error over the trailing
window (a straight-line fit through the logged values, every 25 steps; the window itself does the smoothing). Trailing, so it only uses
what the walker had already been through. Floored at 0: a stretch in which the error rises has no appetite, not a negative one.

Cut A: uniform hold on a log-step clock, step n is shown at time proportional to log(n + c), with c so the first 50 steps take ~1 minute.
Cut B: the same clock, each hold multiplied by appetite (relative to its walk median, limited to 1/4..4), then rescaled to the same length.
"""

from __future__ import annotations

import subprocess
import sys

import numpy as np
import pandas as pd
from common import OUT, RUNS, heldout, places, steps
from PIL import Image, ImageDraw, ImageFont
from scipy.optimize import brentq

WALKS = {"Bored": "h2910_bored_paris_s0", "Globalist": "h2910_globalist_paris_s0"}
WINDOWS = (200, 500)
TOTAL_S, FIRST50_S = 600.0, 60.0
SCALE_LIMIT = 4.0
FPS, SIZE, BAR = 30, 640, 48


def appetite(h: pd.DataFrame, n_steps: int, window: int) -> np.ndarray:
    """Per step: minus the slope of log held-out MSE over the trailing window, per 1,000 steps, floored at 0."""
    x, y = h.step.to_numpy(float), np.log(h.heldout_mse.to_numpy())
    grid = np.arange(0, n_steps + 1, 25)
    slope = np.full(len(grid), np.nan)
    for k, g in enumerate(grid):
        m = (x <= g) & (x > g - window)
        if m.sum() >= 4:
            slope[k] = np.polyfit(x[m], y[m], 1)[0]
    slope = pd.Series(slope).bfill().to_numpy()
    return -1000 * np.interp(np.arange(n_steps), grid, slope)


def log_clock_c(n: int) -> float:
    return brentq(lambda c: np.log((50 + c) / c) / np.log((n + c) / c) - FIRST50_S / TOTAL_S, 1e-3, 5000)


def holds(n: int, app: np.ndarray | None) -> np.ndarray:
    c = log_clock_c(n)
    d = np.log((np.arange(1, n + 1) + c) / (np.arange(n) + c))
    d *= TOTAL_S / d.sum()
    if app is not None:
        a = np.maximum(app, 0)
        f = np.clip(a / np.median(a[a > 0]), 1 / SCALE_LIMIT, SCALE_LIMIT)
        d = d * f
        d *= TOTAL_S / d.sum()
    return d


def stretches(s: pd.DataFrame, dA: np.ndarray, dB: np.ndarray) -> pd.DataFrame:
    rows = []
    for p, x in s.groupby("place"):
        if len(x) >= 100 or p == 0:
            i = x.step.to_numpy()
            rows.append({"steps": f"{i[0]}-{i[-1]}", "n": len(x), "lat": x.lat.median().round(1), "lon": x.lon.median().round(1), "A_sec": dA[i].sum(), "B_sec": dB[i].sum(), "A_start_min": dA[: i[0]].sum() / 60, "B_start_min": dB[: i[0]].sum() / 60})
    return pd.DataFrame(rows)


def signal() -> dict:
    out, rows = {}, []
    for ch, run in WALKS.items():
        s, h = steps(run), heldout(run)
        for w in WINDOWS:
            a = appetite(h, len(s), w)
            out[ch, w] = a
            for lo in range(0, 5000, 500):
                rows.append({"walker": ch, "window": w, "steps": f"{lo}-{lo + 499}", "appetite_mean": a[lo : lo + 500].mean(), "share_at_or_below_zero": (a[lo : lo + 500] <= 0).mean()})
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "task7_appetite_blocks.csv", index=False)
    print(t.pivot_table(index="steps", columns=["walker", "window"], values="appetite_mean", sort=False).round(3).to_string())
    print(t.pivot_table(index="steps", columns=["walker", "window"], values="share_at_or_below_zero", sort=False).round(2).to_string())
    pd.DataFrame({f"{c}_{w}": v for (c, w), v in out.items()}).assign(step=np.arange(5000)).to_csv(OUT / "task7_appetite.csv", index=False)
    return out


def figures(app: dict) -> pd.DataFrame:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    s = places(steps(WALKS["Bored"]))
    n = len(s)
    dA, dB = holds(n, None), holds(n, app["Bored", WINDOW])
    tab = stretches(s, dA, dB)
    tab.to_csv(OUT / "task7_stretches.csv", index=False)
    print(f"c = {log_clock_c(n):.1f}; first 50 steps: A {dA[:50].sum():.0f} s, B {dB[:50].sum():.0f} s; total A {dA.sum():.0f} s, B {dB.sum():.0f} s")
    print(f"hold: A {dA[0]:.2f} s at the start, {dA[-1] * 1000:.0f} ms at the end; B {dB[0]:.2f} s, {dB[-1] * 1000:.0f} ms. Steps under one frame: A {(dA < 1 / FPS).mean():.2f}, B {(dB < 1 / FPS).mean():.2f}")
    print(tab.round(1).to_string(index=False))

    fig, axs = plt.subplots(3, 1, figsize=(11, 8.5), sharex=False)
    ax = axs[0]
    for ch, run in WALKS.items():
        h = heldout(run)
        ax.plot(h.step, h.heldout_mse, lw=1.2, label=ch, color={"Bored": "#c1443c", "Globalist": "#2a78b5"}[ch])
    ax.set_yscale("log")
    ax.set_title("held-out error, 200 tiles from the planet")
    ax.legend(frameon=False)
    ax = axs[1]
    for (ch, w), a in app.items():
        ax.plot(a, lw=1.1 if w == 500 else 0.6, ls="-" if w == 500 else "--", color={"Bored": "#c1443c", "Globalist": "#2a78b5"}[ch], label=f"{ch}, {w} steps")
    ax.axhline(0, color="0.5", lw=0.7)
    ax.set_title("appetite: how fast log error is falling, per 1,000 steps (window 200 and 500)")
    ax.set_ylim(-0.1, np.percentile(np.concatenate(list(app.values())), 98))
    ax.legend(frameon=False, ncol=2, fontsize=8)
    for k in (0, 1):
        axs[k].set_xlabel("step")
        axs[k].grid(alpha=0.2)
    ax = axs[2]
    ax.plot(np.r_[0, np.cumsum(dA)] / 60, np.arange(n + 1), label="cut A: log clock", color="k")
    ax.plot(np.r_[0, np.cumsum(dB)] / 60, np.arange(n + 1), label=f"cut B: log clock x appetite ({WINDOW} steps)", color="#c1443c")
    for _, r in tab[tab.n >= 300].iterrows():
        lo = int(r.steps.split("-")[0])
        ax.axhspan(lo, lo + r.n, color="0.9", zorder=0)
    ax.set_xlabel("minutes of film")
    ax.set_ylabel("step of the Bored walk")
    ax.set_title("which step is on screen when (grey: stays of 300 steps or more)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "task7_appetite.png", dpi=120)
    plt.close(fig)
    return s


def render(s: pd.DataFrame, d: np.ndarray, name: str, title: str) -> None:
    from data.tile_store import TileStore

    store = TileStore()
    font = ImageFont.load_default(size=20)
    t = s.tile_idx.to_numpy()
    frames = int(round(TOTAL_S * FPS))
    which = np.minimum(np.searchsorted(np.cumsum(d), (np.arange(frames) + 0.5) / FPS), len(t) - 1)
    path = RUNS / "h0111_films" / f"{name}.mp4"  # runs/ is git-ignored: an untracked film in the work tree once filled the disk by way of .git
    path.parent.mkdir(exist_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{SIZE}x{SIZE + BAR}", "-r", str(FPS), "-i", "-", "-c:v", "h264_videotoolbox", "-b:v", "6M", "-pix_fmt", "yuv420p", str(path)], stdin=subprocess.PIPE)
    last, buf = -1, b""
    for k in which:
        if k != last:
            im = Image.new("RGB", (SIZE, SIZE + BAR))
            im.paste(Image.fromarray(store.get_lowres(int(t[k]))).resize((SIZE, SIZE), Image.Resampling.BICUBIC), (0, 0))
            dr = ImageDraw.Draw(im)
            la, lo = s.lat.iloc[k], s.lon.iloc[k]
            dr.text((12, SIZE + 12), f"step {k:,}   {abs(la):.1f}{'N' if la >= 0 else 'S'} {abs(lo):.1f}{'E' if lo >= 0 else 'W'}", font=font, fill=(235, 235, 235))
            dr.text((SIZE - 12, SIZE + 12), title, font=font, fill=(150, 150, 150), anchor="ra")
            buf, last = im.tobytes(), k
        ff.stdin.write(buf)
    ff.stdin.close()
    ff.wait()
    shown = len(np.unique(which))
    print(f"[task7] {path.name}: {frames} frames, {shown} of {len(t)} steps get at least one frame, {path.stat().st_size / 1e6:.0f} MB", flush=True)
    sheet(s, which, name, store)


def sheet(s: pd.DataFrame, which: np.ndarray, name: str, store) -> None:
    """One frame every 20 seconds of film."""
    cols, thumb = 10, 150
    picks = which[:: 20 * FPS][:30]
    im = Image.new("RGB", (cols * thumb, (len(picks) // cols) * (thumb + 20)), (20, 20, 20))
    dr = ImageDraw.Draw(im)
    font = ImageFont.load_default(size=12)
    for j, k in enumerate(picks):
        x, y = (j % cols) * thumb, (j // cols) * (thumb + 20)
        im.paste(Image.fromarray(store.get_lowres(int(s.tile_idx.iloc[k]))).resize((thumb - 2, thumb - 2)), (x, y))
        dr.text((x + 3, y + thumb), f"{j * 20 // 60}:{j * 20 % 60:02d}  step {k:,}", font=font, fill=(220, 220, 220))
    (OUT / "films").mkdir(exist_ok=True)
    im.save(OUT / "films" / f"{name}_contact.png")


WINDOW = 500

if __name__ == "__main__":
    app = signal()
    s = figures(app)
    if "--films" in sys.argv:
        render(s, holds(len(s), None), "bored_paris_A_log_clock", "A: log clock")
        render(s, holds(len(s), app["Bored", WINDOW]), "bored_paris_B_log_clock_appetite", "B: log clock x appetite")
