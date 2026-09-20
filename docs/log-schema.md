# Log schema

`log.jsonl` is the real deliverable of a run. One JSON object per line, one line per
step per agent, in agent order then step order. The same schema is emitted by the
hiker (`run.py`) and by the farthest-point baseline (`baseline_fps.py`).

Two words are used throughout:

- **measured** — a quantity that follows from the archive's own records or from
  arithmetic on them (a distance, a date difference, a count). Nothing learned is
  involved.
- **interpreted** — a quantity that passes through a model. In Phase 1 that is the
  encoder: every embedding, and therefore every cosine distance and novelty score, is
  the encoder's opinion. Change the encoder and these values change; the measured
  ones do not. The archive-mean centring of embeddings (`embed_meta.json`,
  `centered: true`) is part of this: a chip's vector depends on the archive it was
  embedded with.

## Fields

| Field | Type | Unit / range | Kind | Meaning |
|---|---|---|---|---|
| `agent_id` | int | 0 … n_agents−1 | measured | Which hiker. The baseline always uses 0. |
| `step` | int | 0 … max_steps | measured | 0 is the start chip (no choice was made). |
| `chip_id` | string | archive-specific | measured | Row key into `manifest.parquet`. Stable across runs. |
| `novelty` | float or null | [0, 2] | interpreted | Mean cosine distance from this chip to its `j` nearest entries in *this agent's* history at the moment it was chosen. Null at step 0. In the baseline it is the min distance to the selected set (j = 1). |
| `novelty_running_mean` | float or null | [0, 2] | interpreted | Mean of `novelty` over the last `boredom_window` steps (fewer at the start). The stop rule compares this to `boredom_threshold`. |
| `rank_among_candidates` | int or null | 1 … n_candidates | interpreted | 1 = the chosen chip had the highest novelty among candidates. Ties broken by candidate order. Always 1 in the baseline. |
| `n_candidates` | int | ≥ 0 | measured | Candidates after removing history: up to `k_neighbours + m_random`. 0 at step 0. In the baseline: number of unselected chips. |
| `was_random_jump` | bool | | measured | True if the chosen chip entered the candidate set as one of the `m_random` random draws rather than as a nearest neighbour. Always false in the baseline. |
| `embedding_distance_from_prev` | float or null | [0, 2] | interpreted | Cosine distance between this chip and the previous chip in the walk. Note this is *not* the novelty; novelty is measured against the whole history. |
| `geo_distance_km_from_prev` | float or null | km, ≥ 0 | measured | Great-circle (haversine, WGS84 mean radius 6371.0088 km) distance between chip centres. Null if either chip lacks coordinates. |
| `time_delta_days_from_prev` | int or null | days, signed | measured | Acquisition date of this chip minus that of the previous chip. Negative = the walk moved backwards in time. Null if either date is missing. |
| `history_size` | int | ≥ 1 | measured | Chips in this agent's history *including* this one. Equals `step + 1`. |
| `taste_similarity` | float or null | [−1, 1] | interpreted | Cosine similarity between this chip and the agent's taste vector *at the moment of choice* (before any update). Null when taste is off (`agents.taste.weight = 0`), at step 0, and while taste is still empty under `init: zero`. |
| `taste_updated` | bool | | interpreted | True if this chip's novelty reached `agents.taste.threshold` and moved the taste vector. Always false when taste is off. |
| `taste_shift` | float or null | [0, 2] | interpreted | Cosine distance between the taste before and after this step's update; 1.0 when the first spike set an empty taste. Null when not updated. |
| `lat`, `lon` | float or null | degrees, WGS84 | measured | Chip centre. From the archive (SSL4EO), or the fragment centre offset to the tile centre in the fragment's UTM zone (Major TOM). Null for EuroSAT. |
| `date` | string or null | ISO `YYYY-MM-DD`, UTC | measured | Acquisition date. Full timestamp is in the manifest's `datetime` column. |
| `temperature` | float | > 0 | measured | Softmax temperature used for this agent. 0.0 in the baseline (greedy). |
| `seed` | int | | measured | Run seed. Each agent's generator is seeded with `(seed, agent_id)`. |

Floats are rounded to 6 decimals when written. Nulls are JSON `null`, never 0 or an empty string.

## Invariants a consumer may rely on

- Within one agent, `step` increases by exactly 1 per line and `chip_id` never repeats.
- `history_size == step + 1`.
- `was_random_jump` is false whenever `rank_among_candidates` is null.
- `taste_shift` is non-null exactly when `taste_updated` is true.
- When taste is on, `rank_among_candidates` ranks by `novelty + weight * taste_similarity`, not by `novelty` alone.
- `novelty` is null exactly when `step == 0`.
- Across agents, the same `chip_id` may appear; `summary.json` lists those cases under `chips_visited_by_multiple_agents` with agent and step.

## Companion files in a run directory

- `config.yaml` — the fully resolved config, including seeds and the encoder's resolved model/weights.
- `summary.json` — per agent: `steps_taken`, `stop_reason` (`max_steps` | `boredom` | `exhausted`), the full `novelty_curve`, `geo_distance_total_km`, `embedding_distance_total`, `time_span`, `n_random_jumps`, `n_taste_updates` and `taste_drift_from_initial` (null when taste is off), `n_unique_groups` (distinct locations/fragments), `chip_ids` in order; plus the shared-chip listing.
- `novelty_curve.png` — novelty per step per agent, running mean dashed, random jumps as dots.
- `sequence/agent_<id>/<step:04d>_<chip_id>.png` — the walk as ordered images.

Written by the heatmap stage (Phase 2), when it has run:

- `sequence/agent_<id>/<step:04d>_<chip_id>_heat.png` — the chip with its hot patches tinted; none for step 0.
- `patch_novelty_agent_<id>.npz` — `scores` of shape `(steps + 1, 14, 14)`, float32, NaN at step 0: the mean cosine distance from each patch to its `heatmap.j_patches` nearest patches among all patches of the chips this agent had visited before that step. *Interpreted.* Plus `chip_ids` and `steps` aligned to the first axis. This is the per-patch record the brief asked for; it lives in a sidecar because 196 floats per log line would make `log.jsonl` unwieldy.
- `heatmap.json` — the colour scale (`vmin`/`vmax` and the percentiles they came from), `j_patches`, whether patches were centred, and per agent a `steps_detail` list with `patch_mean`, `patch_max`, `patch_min`, `hot_fraction` (share of patches at or above `vmin`) and `hottest_patch` `[row, col]` per step, and the correlation between the chip-level `novelty` and the patch mean/max.
- `heatmap_sheet_agent_<id>.png` — the first 25 steps as original/overlay pairs.
- `taste_agent_<id>.npy` — the agent's final taste vector (only when `agents.taste.weight` is non-zero).

Written by the dream stage, when it has run. Nothing here enters `log.jsonl`, the history or the archive:

- `sequence/agent_<id>/dream_<k>.png` and `dream_<k>_control.png` — the `k`-th guided dream and its unguided control (same seed).
- `dreams.json` — per agent: `trigger` (`boredom` | `end_of_run`), the last real step's novelty, the `archive_ceiling` (most novel unvisited real chip and its novelty), `best_candidate`, and per candidate the `dream` and `control` records: `novelty` and `score` measured by re-encoding the saved PNG exactly as a chip (*interpreted*), `taste_similarity` when taste was used, `nearest_chip` and `nearest_chip_distance` in the archive, and `guided_score_first_last` (the differentiable score at the first and last guided step). Plus the generator (base model, adapter path, resolution, prompt `""`) and guidance parameters.

## The manifest (`data/processed/<key>/manifest.parquet`)

| Column | Kind | Notes |
|---|---|---|
| `chip_id`, `path` | measured | `path` is relative to the processed dataset directory. |
| `lat`, `lon`, `date`, `datetime`, `sensor` | measured | Null when the archive has no record. |
| `source_dataset` | measured | Adapter name (and split/modality where relevant). |
| `group_id` | measured | Location (SSL4EO) or fragment (Major TOM) the chip belongs to; class label for EuroSAT. |
| `height`, `width` | measured | Pixels. |
| `x_*` | mixed | Adapter extras. `x_cloud_fraction` (SSL4EO) is the output of the archive's cloud classifier and is therefore **interpreted**; `x_product_id`, `x_season_idx`, `x_tile_row/col` are measured. |
