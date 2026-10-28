# Bored Machines: first agentic walk (speedrun)

Curious agents grow their own perception, a small conv autoencoder trained from scratch, while they walk Sentinel-2 tiles of Northern Italy. Each agent picks its next tile by novelty, learning progress and surprise, and gets bored. A small DDPM is then trained on each agent's path, weighted by surprise and boredom, and its samples are compared with baselines.

**Index of all experiments (briefs, expectations, logs, observations, code and outputs of each): `notes/README.md`.**

- First walk: brief `bored-machines_first-walk-brief.md`, predictions `notes/expectations.md`, results and deviations `notes/observations.md`
- Dreams v2 (native 10 m, novelty at sampling time): `notes/dreams_v2/`, outputs in `runs/<run>/dreams_v2/`
- Dreams v3 (global and confined walks, per-agent StyleGAN2 + latent search; paused before GAN training): `notes/dreams_v3/`, status and how to continue in `notes/dreams_v3/status_paused_2026-10-28.md`

## Setup

Python 3.12 via uv. The shell has `UV_PROJECT_ENVIRONMENT=orest` set for another project, so always point uv at `.venv`:

```
UV_PROJECT_ENVIRONMENT=.venv uv sync
```

## Pipeline

```
python data/prepare.py --check                 # 1,814 Major TOM tiles -> data/tiles.npy, tiles.parquet, neighbours; ~15 min fetch
python -m agent.walk configs/baseline.yaml --seed 0     # ~80 s on an RTX 4070 laptop GPU
bash scripts/gate1.sh && bash scripts/gate1_extra.sh    # all 20 walks
python analysis/build_walks_nb.py && jupyter nbconvert --to notebook --execute --inplace analysis/walks.ipynb

python -m gen.build_sets runs/baseline_s0      # three equal-size training sets
bash scripts/gate2_train.sh baseline_s0        # 3 DDPMs x ~92 min, + 64 samples each
python analysis/build_dreams_nb.py && jupyter nbconvert --to notebook --execute --inplace analysis/dreams.ipynb

# dreams v2
python -m gen.hires data/sets/baseline_s0      # 10 m tiles -> data/hires/, crop banks -> data/crops/
bash scripts/dreams_v2_train.sh baseline_s0    # 10 m and 40 m DDPMs, ~76 min each on a Quadro RTX 5000 (fp16)
bash scripts/dreams_v2_sample.sh baseline_s0   # 512-sample pools, novelty guidance, report

# dreams v3 (Windows; GAN side in .venv-sg via scripts\sg.bat, see notes/dreams_v3/)
python data/global_index.py                    # planet index of Major TOM Core -> data/global/
python -m agent.walk configs/global_baseline.yaml       # lazy tile store, ~30 min
python -m agent.walk configs/confined_baseline.yaml     # Great Sand Sea, 300 km
python -m gen.v3_datasets agent runs/global_baseline_s0 # then: base runs/global_baseline_s0
scripts\dreams_v3_train.bat base 3000          # + dreams_v3_chain.bat, dreams_v3_search.bat
```

## Layout

| Path | What it holds |
|---|---|
| `data/prepare.py` | subset, thumbnail fetch, 256 px cache, BallTree neighbours, synthetic noisy-TV tiles |
| `agent/model.py` | 272k-parameter conv autoencoder (32×32 → 64-d) |
| `agent/signals.py` | patches, surprise, archive-kNN novelty, vmapped learning-progress probe, EMA z-scores |
| `agent/walk.py` | the loop, boredom, daydreams, logging → `runs/<config>_s<seed>/` |
| `configs/*.yaml` | one complete file per temperament; `tvtest_*` start next to the noisy TV |
| `gen/build_sets.py` | per-tile weights; `path_weighted`, `path_uniform`, `random_uniform` |
| `gen/train_ddpm.py` | diffusers `UNet2DModel` at 64 px, weighted sampling, EMA |
| `gen/sample.py` | 64 samples per model, same noise seed for every model |
| `gen/hires.py` | native 10 m tiles from the cached thumbnails; fixed 64-crops-per-tile banks |
| `gen/dreams_v2.py` | agent-side scoring (own AE + archive), per-seed-id DDPM sampler, novelty guidance |
| `gen/dreams_v2_report.py` | selection, memorisation search, contact sheets, scores table |
| `data/global_index.py`, `data/tile_store.py` | v3: planet index; lazy tile store with disk cache and `World` pools (global, confined) |
| `gen/v3_datasets.py` | v3: StyleGAN datasets `agent_path` (weighted crops of the path) and `base_global` |
| `gen/dream_search.py`, `gen/dreams_v3_report.py` | v3: latent evolution in W driven by the agent's learning progress; report |
| `analysis/build_*_nb.py` | generators for the two gate notebooks |
| `analysis/hike_viewer.py` | step-by-step HTML viewer of a walk (`runs/<run>/hike.html`) |
| `notes/` | one folder per experiment, index in `notes/README.md` |

Each run folder holds `config.yaml`, `meta.json` (seed, git hash, start tile, timing), `steps.parquet`, `candidates.parquet`, `heldout.parquet`, checkpoints every 250 steps plus one per bored event, `final.pt`, `archive.npz`, and `daydreams/*.png`.

Data: Major TOM Core-S2L2A (ESA Φ-lab), CC-BY-SA-4.0.
