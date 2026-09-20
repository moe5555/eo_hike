"""Thin CLI: ``python run.py --config configs/debug.yaml [--set key=value ...]``.

Stages run in order and each is skipped when its output already exists:
ingest -> embed -> index -> hike -> heatmap. Use ``--stage`` to run a single one,
``--force`` to recompute that stage, and ``--set`` (repeatable) to override any config
value. ``--stage heatmap`` works on a finished run: pass ``--run runs/<dir>`` or it
takes the newest run directory.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

sys.path.insert(0, str(Path(__file__).parent / "src"))

from hiker.config import load_config  # noqa: E402

app = typer.Typer(add_completion=False, help=__doc__)

STAGES = ("ingest", "embed", "index", "hike", "heatmap", "dream-train", "dream", "all")


@app.command()
def main(
    config: Path = typer.Option(..., "--config", "-c", exists=True, help="YAML config"),
    stage: str = typer.Option("all", "--stage", "-s", help="ingest | embed | index | hike | heatmap | dream-train | dream | all"),
    set_: Optional[list[str]] = typer.Option(None, "--set", help="override, e.g. agents.temperature=0.3"),
    force: bool = typer.Option(False, "--force", help="recompute the selected stage even if its output exists"),
    tag: Optional[str] = typer.Option(None, "--tag", help="suffix for the run directory name"),
    run: Optional[Path] = typer.Option(None, "--run", help="run directory for --stage heatmap / dream (default: newest)"),
) -> None:
    if stage not in STAGES:
        raise typer.BadParameter(f"stage must be one of {STAGES}")
    cfg = load_config(config, set_ or [])
    typer.echo(f"dataset={cfg['dataset']['key']} encoder={cfg['encoder']['name']} data_root={cfg['data_root']}")

    if stage in ("ingest", "all"):
        from hiker.ingest import run_ingest

        run_ingest(cfg, force=force and stage == "ingest")
    if stage in ("embed", "all"):
        from hiker.embed import run_embed

        run_embed(cfg, force=force and stage == "embed")
    if stage in ("index", "all"):
        from hiker.index import run_index

        run_index(cfg, force=force and stage == "index")
    if stage in ("hike", "all"):
        from hiker.hike import run_hike

        run_dir = run_hike(cfg, tag=tag)
        typer.echo(f"done: {run_dir}")
        run = run_dir
    if stage == "heatmap" or (stage == "all" and cfg["heatmap"].get("enabled", True)):
        from hiker.heatmap import latest_run_dir, run_heatmap

        target = run or latest_run_dir(cfg["outputs"]["runs_dir"])
        try:
            run_heatmap(cfg, target, force=force and stage == "heatmap")
        except RuntimeError as e:
            if stage == "heatmap":
                raise
            typer.echo(f"[heatmap] skipped: {e}")
    if stage == "dream-train" or (stage == "all" and cfg["dream"].get("enabled", False)):
        from hiker.dream_train import run_dream_train

        run_dream_train(cfg, force=force and stage == "dream-train")
    if stage == "dream" or (stage == "all" and cfg["dream"].get("enabled", False)):
        from hiker.dream import run_dream
        from hiker.heatmap import latest_run_dir

        target = run or latest_run_dir(cfg["outputs"]["runs_dir"])
        run_dream(cfg, target, force=force and stage == "dream")


if __name__ == "__main__":
    app()
