# Dreams v3: status when paused (2026-10-28)

GAN training was stopped on 2026-10-28 at about 17:50, at the artist's request: the hikes should be revised and made solid before multi-day dream training starts. Nothing is running now (trainer, the chain script and the search watcher were all stopped).

Brief: `dreams-v3_gan-latent-search.md`. Run log with every decision and deviation so far: `run_log.md`. Reflection on the walkers' revisits (written after stepping through the walks): `reflection_revisits.md`.

## Where each step of the brief stands

| Brief step | State | Where |
|---|---|---|
| 0. Expectation | written, not to be edited | `expectations_dreams_v3_2026-10-28.md` |
| 1.1 Global world (index of the planet) | done | `data/global_index.py` → `data/global/index.parquet`, `world_coverage.png` |
| 1.2 Lazy tile store | done, tested on two full walks | `data/tile_store.py`, cache `data/global/cache` (11 GB) |
| 1.3 Global walker `global_baseline_s0` | done (5,000 steps) | `runs/global_baseline_s0/` (+ `hike.html` viewer) |
| 1.4 Confined walker `confined_baseline_s0` (Great Sand Sea, 300 km) | done (5,000 steps) | `runs/confined_baseline_s0/` (+ `hike.html` viewer) |
| Colour scale check | done, documentation only | `data/global_stretch.py`, `global_stretch.png` |
| 2. GAN datasets `agent_path`, `base_global` | built from the walks above | `data/v3/` (18 GB, zips + crop tables) |
| 3. GANs `base`, `agent_finetune`, `agent_scratch` | **stopped**: `base` reached 84 of 3,000 kimg; only the kimg-0 snapshot exists, so nothing usable was produced | `runs/global_baseline_s0/dreams_v3/gan/base/00000-…/`, `logs/gan_base.log` |
| 4. Dream search (conditions A, B, C, A0) | code written; tested only on an untrained random generator | `gen/dream_search.py` |
| 5. Report (sheets, strips, MP4, memorisation, parquet) | code written; never run on real searches | `gen/dreams_v3_report.py` |
| 6. Observations | not started | (would go to `runs/global_baseline_s0/dreams_v3/observations.md`) |

## What depends on the walks

If the walks change, everything from step 2 on has to be rebuilt; steps 1.1, 1.2 and the StyleGAN environment stay valid.

- `agent_path` is built from the global walker's `steps.parquet` (tile weights from surprise and boredom).
- `base_global` excludes the global walker's path tiles, so it changes too (and so does `base`, and `agent_finetune` which resumes from it).
- The dream search loads each walker's `config.yaml` and `final.pt` (its autoencoder) and the report reads its `steps.parquet`. Condition C uses the confined walker.
- The run names `global_baseline_s0` and `confined_baseline_s0` are hard-coded in `scripts/dreams_v3_train.bat` (`AGENT`) and `scripts/dreams_v3_search.bat` (`G`, `C`). New run names mean editing those lines.

## How to continue

All commands from the repo root. The GAN side runs in the separate venv `.venv-sg` through `scripts\sg.bat` (MSVC + CUDA ops, see `run_log.md`, "Deviations"); everything else in `.venv`. The Hugging Face read-only token must be logged in (`.venv\Scripts\hf.exe auth login`) for the tile store.

### A. After revising the walks (the expected path)

1. Re-walk both agents (new config values in `configs/global_baseline.yaml`, `configs/confined_baseline.yaml`, or new config files):
   ```
   .venv\Scripts\python.exe -m agent.walk configs\global_baseline.yaml
   .venv\Scripts\python.exe -m agent.walk configs\confined_baseline.yaml
   ```
   About 30 min each; cached tiles are reused, new ones fetched. Optional: `analysis/v3_maps.py`, `analysis/hike_viewer.py`, `analysis/v3_revisits.py` to compare with the walks above.
2. Rebuild the GAN data (agent set first, base set excludes its path):
   ```
   .venv\Scripts\python.exe -m gen.v3_datasets agent runs\global_baseline_s0
   .venv\Scripts\python.exe -m gen.v3_datasets base runs\global_baseline_s0
   ```
   Move or delete the old `data/v3/` first so the old zips are not mistaken for the new ones.
3. Delete the stopped run `runs\global_baseline_s0\dreams_v3\gan\base\` (only a kimg-0 snapshot), then continue with B.

### B. Training, searches and report

1. Before committing days of GPU time, a short check: train 200 kimg (`scripts\dreams_v3_train.bat timing 200`, ≈ 4 h), look at `fakes000200.png`, then dry-run one search and the report on that snapshot:
   ```
   scripts\sg.bat -m gen.dream_search --gan <…\network-snapshot-000200.pkl> --gan_name base --agent_run runs\global_baseline_s0 --condition B --reach 1.0 --seed 0 --beta 0.3
   .venv\Scripts\python.exe -m gen.dreams_v3_report runs\global_baseline_s0 runs\confined_baseline_s0
   ```
   Then delete `runs\*\dreams_v3\search\`, `runs\global_baseline_s0\dreams_v3\reference\` and the `timing` run: the watchers and the report read those fixed paths.
2. Start the three trainings and the searches, each in its own detached window so they survive closing VS Code (PowerShell):
   ```
   Start-Process cmd -ArgumentList '/c scripts\dreams_v3_train.bat base 3000' -WindowStyle Minimized
   Start-Process cmd -ArgumentList '/c scripts\dreams_v3_chain.bat' -WindowStyle Minimized
   Start-Process cmd -ArgumentList '/c scripts\dreams_v3_search.bat' -WindowStyle Minimized
   ```
   The chain waits for `base`'s kimg-3000 snapshot, then trains `agent_finetune` (800 kimg, resumed from it) and `agent_scratch` (3,000 kimg). The search script waits for each final snapshot and runs plain samples + searches (B and C after `base`, A after `agent_finetune`, A0 after `agent_scratch`), then the report. Logs: `logs\gan_*.log`, `logs\gan_chain.log`, `logs\dreams_v3_search.log`, `logs\dreams_v3_report.log`.
3. Resuming after an interruption: snapshots are written every 200 kimg. `scripts\dreams_v3_train.bat <run> <remaining kimg> <path to latest snapshot>`, and adjust the snapshot names the two watcher scripts wait for.

### Cost

Measured 68–69 s/kimg for `--batch=32 --batch-gpu=16` on the Quadro RTX 5000 with the GPU otherwise idle (anything else on the GPU, e.g. a walk, pushes it into shared memory and it slows by 20×).

| GAN | kimg | time |
|---|---|---|
| base | 3,000 | ≈ 58 h |
| agent_finetune | 800 | ≈ 15 h |
| agent_scratch | 3,000 | ≈ 58 h |
| searches (3 GANs × 2 β × 5 R × 3 seeds, ≈ 25 s each, + 4 conditions) | | ≈ 1 h |
| total | | ≈ 5.5 days |

Ways to make it cheaper if needed: fewer kimg for `base`/`agent_scratch` (quality plateaus are visible in the fakes grids every 200 kimg; the run can be stopped at any snapshot and the watchers pointed at it), or drop `agent_scratch` (condition A0) and keep A vs B vs C.

## Things learned that matter for the next attempt

- About 37 % of the planet's tiles are open water, and a blind long jump lands in water about one time in three; the global walker's unique tiles were 43 % water.
- About 9 % of all thumbnail pixels on the planet are clipped white (snow, ice, cloud, bright sand); the agent dataset is snow-heavy. Expect white-out dreams unless this changes.
- The walkers revisit heavily (≈ 78 % of steps on known tiles, 43 % straight back for the global walker); see `reflection_revisits.md`. This is the main reason for revising the hikes.
- Hugging Face rate limit: run only one heavy tile-fetching job at a time; with the token and the signed-URL caching in the store, two full walks ran without a dropped candidate.
