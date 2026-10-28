# Dreams v2 log: baseline_s0

Brief: `dreams-v2_hires-novelty-sampling.md`. Expectation (written first): `expectations_dreams_v2_2026-10-27.md` (both in this folder).

## Setup on this machine

- GPU: Quadro RTX 5000 (Turing, 16 GB), not the RTX 4070 laptop GPU used for v1.
- The `diffusers` package was missing from `.venv`. `uv` isn't installed here, so I bootstrapped pip and installed the locked `diffusers==0.40.0`. That pulled `huggingface-hub` back from 2.3.0 to 1.33.0.
- **v1's DDPMs and `data/sets/` don't exist on this machine.** The only run folder is `runs/baseline_s0`, re-walked here (git 70558b3, 2026-10-27 15:39). It visited 289 unique non-TV tiles; the v1 write-up's baseline_s0 visited 427, so this is a different walk with the same config. `myopic_s0` was not walked here.
- `data/sets/baseline_s0` was rebuilt with `python -m gen.build_sets runs/baseline_s0`, using v1 defaults α_s=1 and α_b=0.5. Result: 289 tiles per set, 42 tiles shared by the path and random sets, effective n of the weighted set 145, 6.9 % of weights clipped at 5.
- The walk itself was not redone. I reused its `final.pt`, `archive.npz` (1,500 latents, re-embedded with the final AE at the end of the walk) and `steps.parquet`.

## Deviations and compromises

| What | Why |
|---|---|
| **No band fetch; native-resolution RGB comes from the cached `thumbnail` PNGs** | v1 never applied a 2–98 % stretch. It used the Major TOM `thumbnail` column, a fixed-scale B04/B03/B02 composite, box-downsampled from 1068 to 256 px (`data/prepare.py`). That thumbnail is itself the full 1068×1068 10 m grid. I checked tile 300 against freshly fetched B04/B03/B02: the cached PNG is byte-identical to the archive's thumbnail, its correlation with sqrt(band) is 0.99 per channel, and its adjacent-pixel detail matches B04. So using it reproduces v1's colour mapping exactly at 10 m. A new 2–98 % stretch on the raw bands would have changed colour as well as resolution. |
| **fp16 autocast + GradScaler instead of bf16** | Turing has no bf16 tensor cores. A training step takes 2.25 s in bf16, 0.29 s in fp16 and 0.52 s in fp32 (batch 64, 26.6M-parameter UNet). Every model in this comparison, including the 40 m retrains, uses fp16. |
| **v1 (40 m) models retrained here** with the v1 recipe | They're needed for the v1-vs-v2 sheet, and the v1 models live on another machine with a different walk. Same code path as v1 (`gen/train_ddpm.py` without `--bank`), same seed and steps, fp16. |
| 10 m training draws from a **fixed bank of 64 crops per tile**, positions seeded by (tile, px) | As the brief specifies. The v1 recipe instead takes fresh random crops of the 256 px tile every step. Same flips and rotations in both. 85 of 34,304 10 m crops were dropped for > 5 % no-data. |
| **Scoring crops are 75 % of the sample side** (48 px of a 64 px sample), area-resized to 32×32 | The brief doesn't give a crop size, and using the agent's `crop_px` = 64 would make all 16 crops the whole sample. |
| **Known field-of-view mismatch** (accepted in the brief) | The agent's AE learned from 64 px crops of the 42 m/px tiles: 2.7 km, about 84 m per AE pixel. A 48 px crop of a 10 m sample covers 480 m, about 15 m per AE pixel: 5–6× finer than anything the agent saw. For the 40 m models the scoring crop covers about 2 km, close to the agent's scale. Novelty of the 10 m dreams is therefore partly "this scale is new", and is not comparable in absolute terms to the 40 m dreams' novelty. |
| Guidance gradient taken w.r.t. x̂₀ through the agent's encoder only, not through the UNet | As the brief specifies ("through the agent's encoder"). Applied as ε ← ε − λ·√(1−ᾱ_t)·ĝ, where ĝ is unit-RMS per sample at every step and is computed on fresh random scoring crops each step. The posterior mean shifts by ≈ λ·β_t·ĝ per step, so the push acts mostly at high noise. No clipping beyond DDPM's usual x̂₀ ∈ [−1, 1]. |
| Noise per seed id | Every step draws noise for all 512 seed ids and keeps the needed rows. A seed id therefore has identical noise in every model, batch and λ, so guided λ=0 reproduces the random-32 reference. |
| `nn_train_dist` for the 40 m models | Searched against a 64-crops-per-tile bank of the 256 px tiles, not against every window the model saw, so it is an upper bound. For the 10 m models the bank is the training data. |
| Sampler | A hand-written DDPM loop (linear β, fixed_small variance, x̂₀ clip), checked to match diffusers' `DDPMScheduler.step` bit for bit on the same noise. |

## Additions and decisions after Step A

- **Extra guidance sweep λ ∈ {0.03, 0.1, 0.3}** (`samples/10m_*/guided_low.npy`): the brief's λ=1 already saturates novelty (see `observations.md`). Same seed ids and code; shown in `guidance_sweep.png` and `scores.csv`. The brief's contact sheet keeps λ = 1, 3, 10.
- **Step B not run.** UNet (128,128,256,256,512) at 128 px has 76.7M parameters. At batch 64 it needs 33 GB, so on this 16 GB card it spills into shared memory and runs at 26 s/step. Batch 16 fits (9.4 GB, 0.38 s/step), so batch 64 with 4× accumulation would take about 6.4 h per model, about 13 h for path_weighted plus random_uniform, before sampling. On top of that, Step A doesn't show a clear gain from resolution (same-seed dreams barely change between 40 m and 10 m).
- **`path_uniform` not trained** (optional; about 76 min).

## Timing (Quadro RTX 5000)

| Job | Wall clock |
|---|---|
| hires cache + both crop banks | 18 s |
| train 10m_64_path_weighted | 4,572 s |
| train 10m_64_random_uniform | 4,515 s |
| train 40m_64_path_weighted | 4,563 s |
| train 40m_64_random_uniform | 4,559 s |
| 512-sample pool, each model (1000 DDPM steps) | 862 s |
| guidance λ ∈ {0,1,3,10} × 32, each 10 m model | 236–240 s |
| guidance λ ∈ {0.03,0.1,0.3} × 32, each 10 m model | 179 s |
| report (scoring, nn search, sheets) | ~2 min |
