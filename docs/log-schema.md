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
| `lat`, `lon` | float or null | degrees, WGS84 | measured | Chip centre. From the archive (SSL4EO), or the fragment centre offset to the tile centre in the fragment's UTM zone (Major TOM). Null for EuroSAT. |
| `date` | string or null | ISO `YYYY-MM-DD`, UTC | measured | Acquisition date. Full timestamp is in the manifest's `datetime` column. |
| `temperature` | float | > 0 | measured | Softmax temperature used for this agent. 0.0 in the baseline (greedy). |
| `seed` | int | | measured | Run seed. Each agent's generator is seeded with `(seed, agent_id)`. |

Floats are rounded to 6 decimals when written. Nulls are JSON `null`, never 0 or an empty string.

## Invariants a consumer may rely on

- Within one agent, `step` increases by exactly 1 per line and `chip_id` never repeats.
- `history_size == step + 1`.
- `was_random_jump` is false whenever `rank_among_candidates` is null.
- `novelty` is null exactly when `step == 0`.
- Across agents, the same `chip_id` may appear; `summary.json` lists those cases under `chips_visited_by_multiple_agents` with agent and step.

## Companion files in a run directory

- `config.yaml` — the fully resolved config, including seeds and the encoder's resolved model/weights.
- `summary.json` — per agent: `steps_taken`, `stop_reason` (`max_steps` | `boredom` | `exhausted`), the full `novelty_curve`, `geo_distance_total_km`, `embedding_distance_total`, `time_span`, `n_random_jumps`, `n_unique_groups` (distinct locations/fragments), `chip_ids` in order; plus the shared-chip listing.
- `novelty_curve.png` — novelty per step per agent, running mean dashed, random jumps as dots.
- `sequence/agent_<id>/<step:04d>_<chip_id>.png` — the walk as ordered images.

## The manifest (`data/processed/<key>/manifest.parquet`)

| Column | Kind | Notes |
|---|---|---|
| `chip_id`, `path` | measured | `path` is relative to the processed dataset directory. |
| `lat`, `lon`, `date`, `datetime`, `sensor` | measured | Null when the archive has no record. |
| `source_dataset` | measured | Adapter name (and split/modality where relevant). |
| `group_id` | measured | Location (SSL4EO) or fragment (Major TOM) the chip belongs to; class label for EuroSAT. |
| `height`, `width` | measured | Pixels. |
| `x_*` | mixed | Adapter extras. `x_cloud_fraction` (SSL4EO) is the output of the archive's cloud classifier and is therefore **interpreted**; `x_product_id`, `x_season_idx`, `x_tile_row/col` are measured. |
