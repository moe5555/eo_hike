# Hikes v3 revised: log

Revising the v3a walks before the GAN dreams (3b) are trained on them. Starting point: the revisit analysis in `notes/dreams_v3/reflection_revisits.md` (the walkers spend ~78 % of steps on tiles they have seen, 43 % of global steps go straight back) and the artist's notes in `notes/moe_hike_v3_observations.md`. The v3a code state is tagged `v3a-walks`.

Expectation: not written yet; to be written before the first revised walk, and not edited afterwards.

## Setup on the Mac (2026-10-29)

The v3a runs and the 11 GB tile cache are on the Windows machine. To work on the hikes without it:

- `.venv` with CPU torch: `uv venv --python 3.12 .venv`, then `uv pip install` of the `pyproject.toml` dependencies without the CUDA index (the lock file pins CUDA torch for the PC). No tracked file changed.
- Major TOM metadata (`data/raw/majortom_thumbs/metadata.parquet`, 173 MB) and `python data/global_index.py` → `data/global/index.parquet`, same filters as on the PC (the Milan probe tile matches).
- New tile cache in `data/global/cache`, filled as the walker moves. Hugging Face did not rate-limit anonymous reads (no token on this machine).
- Speed: ~1.2 s CPU compute + ~0.5 s fetching per step at first, so ~25 min per 1,000 steps.
- A Mac walk is not the PC walk: same seed and start, but CPU instead of CUDA, so the path diverges. Compare revisions with Mac baselines of the same length, not with the 5,000-step PC runs.

## Revision switches (`agent/walk.py`, `agent/signals.py`)

Config keys; the defaults are the v3a walker. With all defaults, a 20-step global walk is identical to one from the `v3a-walks` code (steps and candidate logs compared).

| Key | Option in the reflection | What it does |
|---|---|---|
| `score_crops: fixed` | 1, fixed crops for scoring | candidates and archive entries are embedded from K crops seeded by tile id (`signals.fixed_offsets`), so a tile looks the same every time; training draws a fresh random look at the chosen tile |
| `refresh_archive: candidates` | 2, fresher archive latents | before novelty, a revisited candidate's own archive entries are replaced by a fresh look under the current model (`reembed_every` still re-embeds the whole archive) |
| `normalise_latents: true` | 3, normalised latents | novelty compares L2-normalised latents |
| `return_cost: β` | 4, visit cost (temperament) | I −= β · log(1 + visits) |
| `no_backstep: true` | 4, inhibition of return (temperament) | the tile just left is dropped from the candidates (unless it is the only one) |

Configs: `configs/global_fixedcrops.yaml` (1), `global_freshlatents.yaml` (2), `global_unitlatents.yaml` (3), `global_perception.yaml` (1–3). The option 4 keys are listed in each, off.

## Runs

| Run | Config | Steps | Machine | Notes |
|---|---|---|---|---|
| `runs/global_baseline_1k_s0` | `global_baseline.yaml` | 1,000 | Mac (CPU) | Mac baseline for the revisions; git hash marked dirty (uncommitted edit to the artist's notes), code otherwise `v3a-walks` |
| `runs/global_perception_1k_s0` | `global_perception.yaml` | 1,000 | Mac (CPU) | options 1–3 together; code `157d2a0`, marked dirty only by the same uncommitted notes edit |
