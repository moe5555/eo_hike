# Dreams v3 run log

Brief: `dreams-v3_gan-latent-search.md`. Expectation (written first, not edited): `expectations_dreams_v3_2026-10-28.md` (both in this folder).

## Decisions taken with the artist before starting (2026-10-28)

| Question | Choice |
|---|---|
| Confinement centre | Great Sand Sea (Egypt/Libya), `[26.5, 25.0]`, radius 300 km |
| RGB source | archive `thumbnail` for the walker views **and** the GAN crops (one colour mapping for the agent and its dreams). `data/global_stretch.json` documents the scale on 5,000 global tiles; it is not applied |
| Noisy TV | dropped: v3 worlds are real Earth only |
| Custom CUDA ops | VS Build Tools installed by the artist; ops compiled with MSVC v143 |

## The planet (1.1)

`data/global_index.py` → `data/global/index.parquet`, `coverage.json`, `notes/dreams_v3/world_coverage.png`.

- Major TOM Core-S2L2A metadata: 2,245,886 rows → 2,189,161 after the v1 filters (no-data ≤ 10 %, cloud ≤ 70 %; Core itself caps cloud at 25 %) → **2,182,212 tiles**, one per 10 km grid cell (earliest product), lat −82.8 … 82.7.
- Coarse land mask (GLOBE 1 km, 5×5 samples per tile): **59.7 % land, 3.7 % coast, 36.7 % open water.**
- So "the planet" here is *every Sentinel-2 L2A acquisition footprint Major TOM Core keeps*: all land including Antarctica and Greenland, plus a lot of water: shelf seas, the swaths around coasts and islands, sea ice, big lakes. It is **not** mostly land and coast as assumed in the brief: about a third of tiles are open water, and a blind long jump lands on water roughly one time in three.
- The v1 regional subset (Northern Italy bbox) is the same 1,814 tiles inside this index (`regional` column); it was used for development.

## Colour scale (`data/global_stretch.json`, `notes/dreams_v3/global_stretch.png`)

5,000 uniform global tiles (4,096 pixels each), none failed. Thumbnail RGB median ≈ 100 per channel; **≈ 9 % of all pixels on the planet are clipped at 255** in every channel (snow, ice, cloud, bright sand), 0.2–0.7 % at 0. On 40 tiles with raw bands fetched, the thumbnail is a fixed monotone function of the band (Spearman 0.995–0.998; Pearson 0.99 with sqrt(band)). A 2–98 % band stretch from this sample would have been B04 132–9504, B03 277–9184, B02 131–9512 (×1e-4 reflectance), recorded only. Consequence: bright surfaces reach the GANs as flat white; expect white-out dreams.

## Tile store (1.2)

`data/tile_store.py`. Remote reads fetch only the `thumbnail` column chunk of one row group (≈ 150–250 kB PNG, the full 1068 px tile at 10 m); parquet footers (≈ 1 MB each) are cached on disk once per file. On-disk LRU cache at `data/global/cache`, 50 GB cap; in-memory LRU of 20k low-res tiles. Background prefetch of radius + 10 km around the current tile. Five attempts with exponential backoff per tile; a candidate not fetched within 30 s is dropped from that step and logged (`n_dropped`, `dropped` in steps.parquet; every remote fetch in `fetches.parquet`). Measured: one remote tile ≈ 1–1.7 s alone, ≈ 3.7 s under 16-way parallel load; a cold footer ≈ 4 s.

Walker refactor: `agent/walk.py` now talks to a tile backend (`RegionalTiles` = v1 tiles.npy, `LazyTiles` = the store), `agent/signals.patches` takes the gathered tiles. Checked bit-identical to the pre-refactor walker on 120 v1 steps with deterministic CUDA (steps, candidates, held-out). Without deterministic mode the walker differs from *itself* run to run at the float32 last-bit level (cuDNN), which can change a sampled choice after a few dozen steps; that was already true in v1.

## Walks (1.3, 1.4)

Configs `configs/global_baseline.yaml`, `configs/confined_baseline.yaml`: v1 `baseline` temperament, seed 0, 5,000 steps.

- Birthplace of the global walker: Milan (45.46, 9.19), the v1 start: Alps, Po plain, lakes, Apennines and coast within ~150 km.
- Confined walker: born at the circle's centre (tile 935218, cell 294U_249R, land). Pool: 2,785 tiles, all land.
- Held-out set: the same 200 tiles drawn from the **global** index for both walkers (`heldout: global`), so their held-out errors are comparable.
- Timing: 0.3–1 s/step (mostly network early on, then cache hits), so `steps: 5000` was kept unchanged. Summaries in `runs/<run>/dreams_v3/walk_summary.json`, maps `map_global_path.png` / `map_confined_path.png` (copies in `runs/global_baseline_s0/dreams_v3/maps/`).

| | global walker | confined walker |
|---|---|---|
| unique tiles | 1,067 | 1,154 (of 2,785 in the circle) |
| bored teleports / chosen long jumps | 18 / 20 | 12 / 24 |
| cover of unique tiles | land 51.9 %, open water 42.7 %, coast 5.3 % | land 100 % |
| lat range | −76.6 … 81.5 (every continent incl. Antarctica) | 23.9 … 29.0 |
| wall time | 30 min | 26 min |
| fetch wait per step (mean / p95) | 0.10 s / 0.65 s | 0.11 s / 0.74 s |
| candidate cache hit rate | 0.99 | 0.99 |
| dropped candidates | 0 | 6 (in 4 steps) |

- **First global attempt crashed at step 4755** (`logs/walk_global_baseline_s0_failed_429.log`): Hugging Face rate-limited the IP (anonymous: 3,000 "resolver" requests per 5 min; every remote range read went through `/resolve/`), triggered by the stretch sample running in parallel, and a single bored-teleport target could then not be fetched. Fixes before the rerun: the store resolves each parquet file once to its signed CDN URL (range reads there don't count), a 429 pauses all store threads (15 s, doubling), and an unfetchable blind target is redrawn (`n_redraw` in steps.parquet) instead of stopping the walk. The artist then added a read-only HF token (5,000 per 5 min). The global walk was rerun from scratch; the confined walk (finished before the fix) was kept: its 20 failed fetches cost 6 dropped candidates, all logged.

## GAN data (2)

`gen/v3_datasets.py` → `data/v3/`. Crops 256 px at 10 m from the same thumbnails the walker saw.

| | tiles | crops | crops/tile | skipped (no-data) | zip |
|---|---|---|---|---|---|
| `agent_path` (global walker) | 1,067 | 24,150 | 5–80 (round(16 w_i)), mean w 1.41, effective n 517 | 13 | 4.8 GB |
| `base_global` | 4,000 (uniform, minus the 1,067 path tiles) | 63,927 | 16 | 73 | 12.6 GB |

base_global cover: land 58.5 %, open water 37.9 %, coast 3.6 % (map `data/v3/base_global/map_base_global.png`). The agent set is heavy in snow and ice (the walk spent long stretches in Antarctica and the Arctic); a fifth of a random sample of crops is near-saturated white under the archive's fixed scale.

## GAN training (3)

- A 1-kimg smoke test at `--batch=32` in one pass ran at 1,390 s/kimg: the 16 GB card (WDDM) was full (two walks also on it) and spilled into system RAM. All runs therefore use **`--batch=32 --batch-gpu=16`** (same effective batch, two accumulated passes; `scripts/dreams_v3_train.bat`), alone on the GPU: 7.5 GB, **69 s/kimg**.
- Projection: base 3000 kimg ≈ 58 h, agent_finetune 800 kimg ≈ 15 h, agent_scratch 3000 kimg ≈ 58 h, ≈ 131 h (5.5 days) in sequence. The artist chose the full budget (2026-10-28). Order: base → agent_finetune (resumed from base's kimg-3000 snapshot) → agent_scratch; `scripts/dreams_v3_chain.bat` starts the latter two when base's final snapshot appears.
- `scripts/dreams_v3_search.bat` (also waiting) runs the plain reference samples and the searches for each GAN as its final snapshot appears (B and C after base, A after agent_finetune, A0 after agent_scratch; R ∈ {0.7, 1, 1.5, 2, 3}, seeds 0–2, β ∈ {0.3, 0}), then `gen/dreams_v3_report.py`. Logs: `logs/gan_*.log`, `logs/gan_chain.log`, `logs/dreams_v3_search.log`, `logs/dreams_v3_report.log`.
- If a training process dies, its snapshots (every 200 kimg) are kept; restart with `scripts\dreams_v3_train.bat <run> <remaining kimg> <latest snapshot>` and adjust the two watcher scripts' snapshot names.

## Deviations from the brief

- **Environment.** The repo's pinned stack (Python 3.8, PyTorch 1.9.1, CUDA 11.1, conda/Docker) is not available on this Windows machine (no Docker; CUDA toolkit 13.2). StyleGAN runs from the NVlabs `stylegan3` repo at `c233a91` in a separate venv `.venv-sg`: Python 3.12, **torch 2.14.1+cu130** (matches nvcc 13.2; sm_75 supported), MSVC v143 14.44 from VS Build Tools 18, via `scripts/sg.bat`. Two small torch-2 patches, kept in `scripts/stylegan3_torch2.patch`: `custom_ops.get_plugin` uses the module returned by `cpp_extension.load`, and `InfiniteSampler` calls `Sampler.__init__()` without arguments. The custom ops (bias_act, upfirdn2d) compile and are used; no community fork needed.
- `uv` is not installed on this machine; packages were added with the venv's pip and listed in `pyproject.toml` (`uv.lock` not regenerated).

## Paused (2026-10-28, ≈ 17:50)

`base` was stopped at 84 of 3,000 kimg, before its first 200-kimg snapshot, together with the chain and search watcher scripts: the artist wants to revise the walks first (see `reflection_revisits.md`). Nothing of 3b ran beyond that. State, what depends on the walks, and how to continue: `status_paused_2026-10-28.md`.
