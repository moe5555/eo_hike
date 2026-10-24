# Bored Machines: first agentic walk (speedrun)

Curious agents grow their own perception, a small conv autoencoder trained from scratch, while they walk Sentinel-2 tiles of Northern Italy. Each agent picks its next tile by novelty, learning progress and surprise, and gets bored. A small DDPM is then trained on each agent's path, weighted by surprise and boredom, and its samples are compared with baselines.

- Brief: `bored-machines_first-walk-brief.md`
- Predictions written before any run: `notes/expectations.md`
- Results and deviations from the brief: `notes/observations.md`

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
| `analysis/build_*_nb.py` | generators for the two gate notebooks |
| `notes/` | expectations, observations, figures |

Each run folder holds `config.yaml`, `meta.json` (seed, git hash, start tile, timing), `steps.parquet`, `candidates.parquet`, `heldout.parquet`, checkpoints every 250 steps plus one per bored event, `final.pt`, `archive.npz`, and `daydreams/*.png`.

Data: Major TOM Core-S2L2A (ESA Φ-lab), CC-BY-SA-4.0.
