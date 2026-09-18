"""Novelty curve plot and ordered sequence images."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def plot_novelty_curves(log: list[dict[str, Any]], out: Path, window: int, threshold: float | None) -> None:
    """One line per agent: novelty per step, running mean dashed, random jumps as dots."""
    agents = sorted({r["agent_id"] for r in log})
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for a in agents:
        rows = [r for r in log if r["agent_id"] == a and r["novelty"] is not None]
        steps = [r["step"] for r in rows]
        nov = [r["novelty"] for r in rows]
        (line,) = ax.plot(steps, nov, lw=0.9, alpha=0.75, label=f"agent {a}")
        ax.plot(steps, [r["novelty_running_mean"] for r in rows], lw=1.6, ls="--", color=line.get_color())
        jumps = [r for r in rows if r["was_random_jump"]]
        ax.scatter([r["step"] for r in jumps], [r["novelty"] for r in jumps], s=14, color=line.get_color(), zorder=3)
    if threshold is not None:
        ax.axhline(threshold, color="grey", lw=0.8, ls=":", label=f"boredom threshold {threshold}")
    ax.set_xlabel("step")
    ax.set_ylabel("novelty (mean cosine distance to j nearest in own history)")
    ax.set_title(f"novelty per step; dashed = running mean over {window}; dots = random jumps")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)


def write_sequence(run_dir: Path, agent_id: int, chip_ids: list[str], paths: list[Path]) -> None:
    """Copy chips into ``sequence/agent_<id>/<step:04d>_<chip_id>.<ext>``."""
    d = run_dir / "sequence" / f"agent_{agent_id}"
    d.mkdir(parents=True, exist_ok=True)
    for step, (cid, src) in enumerate(zip(chip_ids, paths)):
        shutil.copyfile(src, d / f"{step:04d}_{cid}{src.suffix}")


def contact_sheet(paths: list[Path], out: Path, cols: int = 10, thumb: int = 128) -> None:
    """Grid of thumbnails, handy for eyeballing a walk or a dataset sample."""
    from PIL import Image

    n = len(paths)
    rows = (n + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb, rows * thumb), (20, 20, 20))
    for i, p in enumerate(paths):
        im = Image.open(p).convert("RGB").resize((thumb, thumb))
        sheet.paste(im, ((i % cols) * thumb, (i // cols) * thumb))
    sheet.save(out)
