"""A walk as a film: only the tiles, each held on screen for a time set by the drive at that step.

Default (--long-for high): high interest I -> long hold (the image stays while it holds interest); low interest -> short
hold (boredom lets it go). --long-for low inverts this. The mapping is authored (a premise of the film, not of the walk):
the rank of I within the walk, interpolated geometrically between --fast and --slow frames. Using the rank keeps the few
extreme peaks of I from squashing all other steps into one duration.

Each tile is rendered through the walker's one view (data.landsat1_store.render: CIR, tone, fixed stretch, bilinear) to
the frame height, centred on a black 1920 x 1080 frame. Hard cuts; a wait or a return shows the same place again.

    .venv/bin/python scripts/film_drive.py runs/dryrun/curious/w002
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.landsat1_store import Landsat1ClockStore, render  # noqa: E402


def holds(I: np.ndarray, fast: int, slow: int, long_for: str = "high") -> np.ndarray:
    """Frames per step from the rank of I in [0, 1] (ties averaged), geometric between fast and slow frames.
    long_for='high': the highest I gets slow (the longest hold); 'low': the lowest I does."""
    p = (pd.Series(I).rank(method="average").to_numpy() - 1) / max(len(I) - 1, 1)
    if long_for == "high":
        p = 1.0 - p
    else:
        assert long_for == "low", long_for
    return np.rint(np.exp(np.log(slow) + p * (np.log(fast) - np.log(slow)))).astype(int)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--signal", default="I")
    ap.add_argument("--fps", type=int, default=25)
    ap.add_argument("--long-for", choices=["high", "low"], default="high", help="which end of the signal gets the long hold")
    ap.add_argument("--fast", type=int, default=2, help="frames of the shortest hold")
    ap.add_argument("--slow", type=int, default=75, help="frames of the longest hold")
    ap.add_argument("--w", type=int, default=1920)
    ap.add_argument("--h", type=int, default=1080)
    ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()

    s = pd.read_parquet(a.run / "steps.parquet", columns=["step", "image_key", a.signal, "clock"]).sort_values("step")
    n_hold = holds(s[a.signal].to_numpy(float), a.fast, a.slow, a.long_for)
    out = a.out or a.run / "film" / f"drive_{a.signal}_long-{a.long_for}_{a.fast}-{a.slow}f.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    stills = out.parent / f"_stills_{out.stem}"
    stills.mkdir(exist_ok=True)

    t0 = time.time()
    st = Landsat1ClockStore()
    for k in s.image_key.unique():
        p = stills / f"{int(k)}.png"
        if not p.exists():
            Image.fromarray(render(st.bands(int(k)), out_px=a.h)).save(p, compress_level=1)
    t_render = time.time() - t0

    # concat list: each step's still with its hold. This ffmpeg honours the last duration, so nothing is repeated
    # (repeating the last entry held the final tile once more: +74 frames in drive_I_long-high_2-75f, 2026-11-13)
    lines = ["ffconcat version 1.0"]
    for k, f in zip(s.image_key, n_hold):
        lines += [f"file '{stills.resolve() / f'{int(k)}.png'}'", f"duration {f / a.fps:.6f}"]
    lst = out.parent / f"{out.stem}.ffconcat"
    lst.write_text("\n".join(lines) + "\n")

    vf = f"pad={a.w}:{a.h}:(ow-iw)/2:(oh-ih)/2:black,fps={a.fps},format=yuv420p"
    cmd = ["nice", "-n", "10", "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats", "-f", "concat", "-safe", "0",
           "-i", str(lst), "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-tune", "stillimage", "-crf", str(a.crf),
           "-movflags", "+faststart", str(out)]
    t1 = time.time()
    subprocess.run(cmd, check=True)
    t_enc = time.time() - t1

    frames = int(n_hold.sum())
    meta = {"run": str(a.run), "signal": a.signal, "fps": a.fps, "fast_frames": a.fast, "slow_frames": a.slow, "long_for": a.long_for,
            "mapping": f"rank of signal within the walk, geometric; the {a.long_for}est signal gets the longest hold",
            "steps": len(s), "distinct_tiles": int(s.image_key.nunique()), "frames": frames,
            "seconds": round(frames / a.fps, 1), "mean_hold_s": round(float(n_hold.mean()) / a.fps, 3),
            "clock_first": str(s.clock.iloc[0]), "clock_last": str(s.clock.iloc[-1]),
            "size": [a.w, a.h], "tile_px": a.h, "crf": a.crf, "render_s": round(t_render, 1), "encode_s": round(t_enc, 1),
            "git": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()}
    (out.parent / f"{out.stem}.json").write_text(json.dumps(meta, indent=2))
    pd.DataFrame({"step": s.step, "image_key": s.image_key, a.signal: s[a.signal], "frames": n_hold,
                  "t_start_s": np.r_[0, np.cumsum(n_hold)[:-1]] / a.fps}).to_csv(out.parent / f"{out.stem}_timing.csv", index=False)
    shutil.rmtree(stills)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
