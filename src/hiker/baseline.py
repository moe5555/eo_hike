"""Greedy farthest-point sampling over the whole archive.

The omniscient, deterministic cousin of the hiker: at every step take the chip whose
distance to the *nearest already-selected chip* is largest, over the entire archive.
No locality (no k-NN candidate set), no randomness, no per-agent history, no path.

It emits the same ``log.jsonl`` schema so the two can be compared field by field.
Fields that have no meaning here are filled honestly:

- ``novelty`` is the min cosine distance to the selected set (that *is* the FPS
  criterion; it equals the hiker's score with j = 1 and the whole archive as
  candidates).
- ``rank_among_candidates`` is always 1 and ``n_candidates`` is the number of
  unselected chips.
- ``was_random_jump`` is always false; ``temperature`` is 0 (greedy).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from tqdm import tqdm

from . import config as C
from .embed import load_embeddings
from .ingest import load_manifest
from .io import JsonlWriter, geo_distance_or_none, make_run_dir, manifest_records, time_delta_days_or_none, write_json
from .viz import plot_novelty_curves, write_sequence


def farthest_point_order(embs: np.ndarray, start: int, n_steps: int) -> tuple[list[int], list[float]]:
    """Return ``(indices, min_distances)`` of greedy FPS starting at ``start``.

    ``min_distances[t]`` is the cosine distance from the chip picked at step ``t+1``
    to its nearest previously selected chip, i.e. the value being maximised.
    """
    n = embs.shape[0]
    order = [start]
    d_min = 1.0 - embs @ embs[start]  # distance of every chip to the selected set
    d_min[start] = -np.inf
    scores: list[float] = []
    for _ in tqdm(range(min(n_steps, n - 1)), desc="fps", unit="step"):
        nxt = int(np.argmax(d_min))  # deterministic: first max wins
        scores.append(float(d_min[nxt]))
        order.append(nxt)
        d_new = 1.0 - embs @ embs[nxt]
        d_min = np.minimum(d_min, d_new)
        d_min[nxt] = -np.inf
    return order, scores


def run_baseline(cfg: dict[str, Any], tag: str | None = "fps") -> Path:
    a = cfg["agents"]
    manifest = load_manifest(cfg)
    records = manifest_records(manifest)
    embs, _ = load_embeddings(cfg)
    chip_to_row = {cid: i for i, cid in enumerate(manifest["chip_id"].tolist())}
    starts = a.get("start_chips")
    if starts and starts[0] is not None:
        start = chip_to_row[starts[0]]
    else:
        start = int(np.random.default_rng([int(a["seed"]), 0]).integers(0, embs.shape[0]))
    max_steps = int(a["max_steps"])
    window = int(a["boredom_window"])

    run_dir = make_run_dir(cfg, cfg["outputs"]["runs_dir"], tag)
    print(f"[fps] run dir: {run_dir}")
    order, scores = farthest_point_order(embs, start, max_steps)

    rows: list[dict[str, Any]] = []
    with JsonlWriter(run_dir / "log.jsonl") as log:
        for step, row_idx in enumerate(order):
            cur = records[row_idx]
            prev = records[order[step - 1]] if step > 0 else None
            nov = scores[step - 1] if step > 0 else None
            running = float(np.mean(scores[max(0, step - window) : step])) if step > 0 else None
            row = {
                "agent_id": 0,
                "step": step,
                "chip_id": cur["chip_id"],
                "novelty": nov,
                "novelty_running_mean": running,
                "rank_among_candidates": 1 if step > 0 else None,
                "n_candidates": embs.shape[0] - step if step > 0 else 0,
                "was_random_jump": False,
                "embedding_distance_from_prev": float(1.0 - embs[order[step - 1]] @ embs[row_idx]) if step > 0 else None,
                "geo_distance_km_from_prev": geo_distance_or_none(prev, cur) if prev else None,
                "time_delta_days_from_prev": time_delta_days_or_none(prev, cur) if prev else None,
                "history_size": step + 1,
                "lat": cur["lat"],
                "lon": cur["lon"],
                "date": cur["date"],
                "temperature": 0.0,
                "seed": int(a["seed"]),
            }
            log.write(row)
            rows.append(row)

    dates = [records[i]["date"] for i in order if records[i]["date"] is not None]
    summary = {
        "run_dir": run_dir.name,
        "method": "farthest_point_sampling",
        "dataset_key": cfg["dataset"]["key"],
        "encoder": cfg["encoder"]["name"],
        "n_chips_in_archive": int(embs.shape[0]),
        "agents": [
            {
                "agent_id": 0,
                "start_chip": records[start]["chip_id"],
                "steps_taken": len(order) - 1,
                "stop_reason": "max_steps" if len(order) - 1 >= max_steps else "exhausted",
                "novelty_curve": [round(s, 6) for s in scores],
                "novelty_mean": float(np.mean(scores)) if scores else None,
                "n_random_jumps": 0,
                "geo_distance_total_km": sum(r["geo_distance_km_from_prev"] or 0.0 for r in rows) if any(r["geo_distance_km_from_prev"] is not None for r in rows) else None,
                "embedding_distance_total": sum(r["embedding_distance_from_prev"] or 0.0 for r in rows),
                "time_span": {"min_date": min(dates), "max_date": max(dates)} if dates else None,
                "n_unique_groups": len({records[i]["group_id"] for i in order}),
                "chip_ids": [records[i]["chip_id"] for i in order],
            }
        ],
        "chips_visited_by_multiple_agents": {},
    }
    write_json(run_dir / "summary.json", summary)
    plot_novelty_curves(rows, run_dir / "novelty_curve.png", window, None)
    if cfg["outputs"].get("write_images", True):
        root = C.processed_dir(cfg)
        write_sequence(run_dir, 0, [records[i]["chip_id"] for i in order], [root / records[i]["path"] for i in order])
    print(f"[fps] {len(order) - 1} steps, mean min-distance {np.mean(scores):.4f}")
    return run_dir
