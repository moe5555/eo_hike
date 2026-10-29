# Experiments

One entry per experiment, in the order they were run. Each one has a brief (what was asked), an expectation written before running, a log of decisions and deviations, and observations. Code stays in the shared packages (`data/`, `agent/`, `gen/`, `analysis/`); run outputs are in `runs/` and `data/`, which git ignores.

| # | Experiment | Dates | Question | Status | Folder |
|---|---|---|---|---|---|
| 1 | First walk + dreams v1 | 2026-10-24 | Do curious agents with different temperaments walk differently, and does a DDPM trained on an agent's path dream differently from one trained on random tiles? | done | `notes/` (top level, see below) |
| 2 | Dreams v2: native 10 m + novelty at sampling time | 2026-10-27 | Do 10 m crops and agent-driven selection or guidance change the dreams? | done (Step B, 128 px, not run) | `notes/dreams_v2/` |
| 3a | Dreams v3, part 1: global and confined walks | 2026-10-28 | The v1 baseline agent walking the whole planet vs. confined to the Great Sand Sea | walks done; being revised | `notes/dreams_v3/` |
| 3b | Dreams v3, part 2: per-agent StyleGAN2 + latent search | 2026-10-28 | Can the agent's learning progress steer a GAN's latent space to dreams beyond what it saw? | paused before training | `notes/dreams_v3/` |
| 3c | Hikes v3 revised | 2026-10-29 | Do the walkers still dwell and step straight back once perception is fixed (fixed crops, fresh archive latents, normalised latents)? | in progress | `notes/hikes_v3_revised/` |

## 1. First walk + dreams v1

- Brief: `bored-machines_first-walk-brief.md` (repo root)
- Expectation: `notes/expectations.md`
- Observations (Gate 1 walks and Gate 2 dreams, deviations included): `notes/observations.md`
- Figures: `notes/img/` (`gate1_*`, `gate2_*`, `dreams_hires/`, `dreams_far/`, `latent_vs_geo_*`)
- Notebooks: `analysis/walks.ipynb`, `analysis/dreams.ipynb` (built by `analysis/build_*_nb.py`)
- Code: `data/prepare.py` (Northern Italy, 1,814 tiles + noisy TV), `agent/`, `configs/{baseline,myopic,novelty_only,random,restless,surprise_only,wide,tvtest_*}.yaml`, `gen/build_sets.py`, `gen/train_ddpm.py`, `gen/sample.py`, `analysis/latent_vs_geo.py`
- Scripts: `scripts/gate1.sh`, `scripts/gate1_extra.sh`, `scripts/gate2_train.sh`
- Runs: `runs/<config>_s<seed>/`. Only `runs/baseline_s0` exists on this machine (re-walked 2026-10-27, see the v2 log); the other 19 walks and the v1 DDPMs are on the laptop used for v1.
- Side experiment: narration of a walk by a language model, `narration/`.

## 2. Dreams v2: native 10 m + novelty at sampling time

All documents and figures in `notes/dreams_v2/`:

- Brief: `dreams-v2_hires-novelty-sampling.md`
- Expectation: `expectations_dreams_v2_2026-10-27.md`
- Log (setup, deviations, timing): `log.md`
- Observations: `observations.md`, with the contact sheets, `v1_vs_v2.png`, `guidance_sweep.png`, `memorisation_*.png`, `novelty_strips.png`, `summary.csv`
- Code: `gen/hires.py`, `gen/dreams_v2.py`, `gen/dreams_v2_report.py`; `gen/train_ddpm.py` gained `--bank`, `--out`, `--amp fp16` (v1 behaviour unchanged without them)
- Scripts: `scripts/dreams_v2_train.sh`, `scripts/dreams_v2_sample.sh`
- Outputs: `runs/baseline_s0/dreams_v2/` (models, samples, `scores.csv`), data `data/hires/`, `data/crops/`
- Agent used: `runs/baseline_s0` (v1 walk, not redone)

## 3. Dreams v3 (3a walks, 3b GAN dreams)

All documents and figures in `notes/dreams_v3/`:

- Brief: `dreams-v3_gan-latent-search.md`
- Expectation: `expectations_dreams_v3_2026-10-28.md`
- Run log (decisions with the artist, the planet's coverage, colour scale, tile store, walks, GAN data, training, deviations): `run_log.md`
- **Status when paused, and how to continue: `status_paused_2026-10-28.md`**
- Reflection on the walkers' revisits: `reflection_revisits.md` (+ `revisit_attractors.png`)
- Figures: `world_coverage.png`, `global_stretch.png`
- The artist's own notes on the v3 hikes: `moe_hike_v3_observations.md` (repo root)

3a, walks:

- Code: `data/global_index.py` (planet index), `data/tile_store.py` (lazy tile store, `World` pools), `data/global_stretch.py` (colour scale check); `agent/walk.py` gained tile backends (`RegionalTiles` for v1, `LazyTiles` for v3; checked bit-identical to v1), `agent/signals.patches` takes gathered tiles
- Configs: `configs/global_baseline.yaml`, `configs/confined_baseline.yaml`, `configs/dev_regional_lazy.yaml` (development only)
- Analysis: `analysis/v3_maps.py` (path maps, walk summaries), `analysis/hike_viewer.py` (step-by-step `hike.html` per run, also works on v1 runs), `analysis/v3_revisits.py`
- Runs: `runs/global_baseline_s0/`, `runs/confined_baseline_s0/`; data `data/global/` (index, 11 GB tile cache)

3b, GAN dreams:

- Code: `gen/v3_datasets.py` (`agent_path`, `base_global`), `gen/dream_search.py` (latent evolution in W), `gen/dreams_v3_report.py`; `gen/build_sets.tile_weights` shared with v1
- Scripts: `scripts/dreams_v3_train.bat`, `scripts/dreams_v3_chain.bat`, `scripts/dreams_v3_search.bat`, `scripts/sg.bat` (StyleGAN environment), `scripts/stylegan3_torch2.patch`
- External: NVlabs `stylegan3` at `c233a91` in `third_party/stylegan3`, venv `.venv-sg` (both git-ignored; setup in `run_log.md`)
- Outputs: `data/v3/` (GAN datasets, 18 GB), `runs/global_baseline_s0/dreams_v3/` (maps, the stopped `gan/base` run)

## 3c. Hikes v3 revised

All documents in `notes/hikes_v3_revised/`:

- Starting point: `notes/dreams_v3/reflection_revisits.md` (options 1–4), `moe_hike_v3_observations.md`; v3a code tagged `v3a-walks`
- Log (Mac setup, the revision switches, runs): `log.md`
- Code: revision switches in `agent/walk.py` and `agent/signals.py` (`score_crops`, `refresh_archive`, `normalise_latents`, `return_cost`, `no_backstep`; defaults = v3a walker)
- Configs: `configs/global_{fixedcrops,freshlatents,unitlatents,perception}.yaml`
- Runs: `runs/global_baseline_1k_s0/` and the revisions, 1,000 steps on the Mac (CPU)
