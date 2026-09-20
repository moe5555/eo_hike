"""Step 4: run the agents and write the run directory.

Outputs (see docs/log-schema.md):
    config.yaml, log.jsonl, summary.json, novelty_curve.png, sequence/agent_<id>/...
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from tqdm import tqdm

from . import config as C
from .agent import Hiker
from .embed import load_embeddings
from .index import load_index
from .ingest import load_manifest
from .io import JsonlWriter, geo_distance_or_none, make_run_dir, manifest_records, seed_everything, time_delta_days_or_none, write_json
from .viz import plot_novelty_curves, write_sequence


def _resolve_starts(cfg_agents: dict[str, Any], chip_to_row: dict[str, int]) -> list[int | None]:
    n = int(cfg_agents["n_agents"])
    starts = cfg_agents.get("start_chips")
    if starts is None:
        return [None] * n
    if len(starts) != n:
        raise ValueError(f"start_chips has {len(starts)} entries but n_agents={n}")
    out: list[int | None] = []
    for s in starts:
        if s is None:
            out.append(None)
        elif s not in chip_to_row:
            raise KeyError(f"start chip {s!r} not in manifest")
        else:
            out.append(chip_to_row[s])
    return out


def run_hike(cfg: dict[str, Any], tag: str | None = None) -> Path:
    a = cfg["agents"]
    seed_everything(int(a["seed"]))
    manifest = load_manifest(cfg)
    records = manifest_records(manifest)
    chip_to_row = {cid: i for i, cid in enumerate(manifest["chip_id"].tolist())}
    embs, embed_meta = load_embeddings(cfg)
    if embs.shape[0] != len(manifest):
        raise RuntimeError(f"embeddings rows {embs.shape[0]} != manifest rows {len(manifest)}")
    index = load_index(cfg)

    cfg = dict(cfg)
    cfg["encoder"] = {**cfg["encoder"], "resolved": {k: embed_meta.get(k) for k in ("model", "weights", "library", "dim", "preprocessing")}}
    run_dir = make_run_dir(cfg, cfg["outputs"]["runs_dir"], tag)
    print(f"[hike] run dir: {run_dir}")

    starts = _resolve_starts(a, chip_to_row)
    window = int(a["boredom_window"])
    threshold = float(a["boredom_threshold"])
    max_steps = int(a["max_steps"])
    T = float(a["temperature"])
    taste = a.get("taste") or {}

    log_rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    visits: dict[int, list[tuple[int, int]]] = defaultdict(list)  # row -> [(agent, step)]

    with JsonlWriter(run_dir / "log.jsonl") as log:
        for agent_id in range(int(a["n_agents"])):
            hiker = Hiker(
                agent_id=agent_id,
                seed=int(a["seed"]),
                embeddings=embs,
                knn=index,
                k_neighbours=int(a["k_neighbours"]),
                m_random=int(a["m_random"]),
                j_history=int(a["j_history"]),
                temperature=T,
                taste_weight=float(taste.get("weight", 0.0)),
                taste_alpha=float(taste.get("alpha", 0.2)),
                taste_threshold=float(taste.get("threshold", 0.9)),
                taste_init=str(taste.get("init", "first")),
            )
            start_row = hiker.start(starts[agent_id])
            visits[start_row].append((agent_id, 0))
            base = {"agent_id": agent_id, "temperature": T, "seed": int(a["seed"])}
            row0 = {
                **base,
                "step": 0,
                "chip_id": records[start_row]["chip_id"],
                "novelty": None,
                "novelty_running_mean": None,
                "rank_among_candidates": None,
                "n_candidates": 0,
                "was_random_jump": False,
                "embedding_distance_from_prev": None,
                "geo_distance_km_from_prev": None,
                "time_delta_days_from_prev": None,
                "history_size": 1,
                "taste_similarity": None,
                "taste_updated": False,
                "taste_shift": None,
                "lat": records[start_row]["lat"],
                "lon": records[start_row]["lon"],
                "date": records[start_row]["date"],
            }
            log.write(row0)
            log_rows.append(row0)

            stop_reason = "max_steps"
            geo_total = 0.0
            emb_total = 0.0
            pbar = tqdm(range(1, max_steps + 1), desc=f"agent {agent_id}", unit="step", leave=True)
            for step in pbar:
                res = hiker.step(step)
                if res is None:
                    stop_reason = "exhausted"
                    break
                prev = records[hiker.history[-2]]
                cur = records[res.chip_index]
                geo = geo_distance_or_none(prev, cur)
                dt = time_delta_days_or_none(prev, cur)
                if geo is not None:
                    geo_total += geo
                emb_total += res.embedding_distance_from_prev
                visits[res.chip_index].append((agent_id, step))
                row = {
                    **base,
                    "step": step,
                    "chip_id": cur["chip_id"],
                    "novelty": res.novelty,
                    "novelty_running_mean": hiker.running_mean(window),
                    "rank_among_candidates": res.rank_among_candidates,
                    "n_candidates": res.n_candidates,
                    "was_random_jump": res.was_random_jump,
                    "embedding_distance_from_prev": res.embedding_distance_from_prev,
                    "geo_distance_km_from_prev": geo,
                    "time_delta_days_from_prev": dt,
                    "history_size": res.history_size,
                    "taste_similarity": res.taste_similarity,
                    "taste_updated": res.taste_updated,
                    "taste_shift": res.taste_shift,
                    "lat": cur["lat"],
                    "lon": cur["lon"],
                    "date": cur["date"],
                }
                log.write(row)
                log_rows.append(row)
                pbar.set_postfix(novelty=f"{res.novelty:.3f}", mean=f"{row['novelty_running_mean']:.3f}")
                if len(hiker.novelties) >= window and float(np.mean(hiker.novelties[-window:])) < threshold:
                    stop_reason = "boredom"
                    break
            pbar.close()

            dates = [records[i]["date"] for i in hiker.history if records[i]["date"] is not None]
            summaries.append(
                {
                    "agent_id": agent_id,
                    "seed": int(a["seed"]),
                    "start_chip": records[start_row]["chip_id"],
                    "steps_taken": len(hiker.history) - 1,
                    "stop_reason": stop_reason,
                    "novelty_curve": [round(v, 6) for v in hiker.novelties],
                    "novelty_mean": float(np.mean(hiker.novelties)) if hiker.novelties else None,
                    "novelty_final_running_mean": hiker.running_mean(window),
                    "n_random_jumps": hiker.n_random_jumps,
                    "n_taste_updates": hiker.n_taste_updates if hiker.taste_weight != 0.0 else None,
                    "taste_drift_from_initial": hiker.taste_drift() if hiker.taste_weight != 0.0 else None,
                    "geo_distance_total_km": geo_total if any(records[i]["lat"] is not None for i in hiker.history) else None,
                    "embedding_distance_total": emb_total,
                    "time_span": {"min_date": min(dates), "max_date": max(dates)} if dates else None,
                    "n_unique_groups": len({records[i]["group_id"] for i in hiker.history}),
                    "chip_ids": [records[i]["chip_id"] for i in hiker.history],
                }
            )
            if hiker.taste_weight != 0.0:
                with open(run_dir / f"taste_agent_{agent_id}.npy", "wb") as f:
                    np.save(f, hiker.taste.astype(np.float32))
            if cfg["outputs"].get("write_images", True):
                root = C.processed_dir(cfg)
                write_sequence(
                    run_dir,
                    agent_id,
                    [records[i]["chip_id"] for i in hiker.history],
                    [root / records[i]["path"] for i in hiker.history],
                )

    shared = {
        records[row]["chip_id"]: [{"agent_id": ag, "step": st} for ag, st in v]
        for row, v in visits.items()
        if len({ag for ag, _ in v}) > 1
    }
    summary = {
        "run_dir": run_dir.name,
        "dataset_key": cfg["dataset"]["key"],
        "encoder": cfg["encoder"]["name"],
        "n_chips_in_archive": int(embs.shape[0]),
        "agents": summaries,
        "chips_visited_by_multiple_agents": shared,
    }
    write_json(run_dir / "summary.json", summary)
    plot_novelty_curves(log_rows, run_dir / "novelty_curve.png", window, threshold)
    for s in summaries:
        print(f"[hike] agent {s['agent_id']}: {s['steps_taken']} steps, stop={s['stop_reason']}, "
              f"mean novelty {s['novelty_mean']:.4f}, random jumps {s['n_random_jumps']}"
              + (f", taste updates {s['n_taste_updates']}, taste drift {s['taste_drift_from_initial']:.3f}"
                 if s.get("taste_drift_from_initial") is not None else ""))
    if shared:
        print(f"[hike] {len(shared)} chips visited by more than one agent")
    return run_dir
