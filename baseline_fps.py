"""Farthest-point-sampling baseline: ``python baseline_fps.py --config configs/debug.yaml``.

Requires the manifest, embeddings and index from ``run.py`` (any stage up to
``index``). Writes a run directory with the same log schema as the hiker.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

sys.path.insert(0, str(Path(__file__).parent / "src"))

from hiker.config import load_config  # noqa: E402

app = typer.Typer(add_completion=False, help=__doc__)


@app.command()
def main(
    config: Path = typer.Option(..., "--config", "-c", exists=True),
    set_: Optional[list[str]] = typer.Option(None, "--set"),
    tag: str = typer.Option("fps", "--tag"),
) -> None:
    cfg = load_config(config, set_ or [])
    from hiker.baseline import run_baseline

    run_dir = run_baseline(cfg, tag=tag)
    typer.echo(f"done: {run_dir}")


if __name__ == "__main__":
    app()
