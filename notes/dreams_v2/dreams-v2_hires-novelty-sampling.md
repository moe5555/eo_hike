# Dreams v2: Higher Resolution + Novelty at Sampling Time

**Context:** walks and per-agent DDPMs exist from the first speedrun, trained at 64 px on tiles downsampled to roughly 40 m/px. The dreams look like blurry averages, e.g. "snow, but a little orange". This brief changes two things and keeps everything else as it is.

1. **Resolution:** train on crops cut at **native 10 m** from the full-resolution tiles.
2. **Novelty at sampling time:** the agent's own model selects and steers what gets sampled, not only what gets trained on.

**Do not redo the walks.** Reuse the existing run folders: paths, per-tile weights, final autoencoder checkpoints and archives.

---

## 0. Before running anything

Write a one-paragraph expectation into `notes/expectations_dreams_v2_<date>.md`: what the higher-resolution samples will look like, and whether novelty selection or guidance will produce anything other than noise. Don't edit it afterwards.

---

## 1. Data at native resolution

- For the tiles in each training set (`path_weighted`, `path_uniform` and `random_uniform` from v1), fetch the full-resolution **B04/B03/B02** bands (10 m, ~1068×1068 px) from Major TOM Core-S2L2A. Fetch only these tiles, not the whole region.
- Apply the **same global 2–98% stretch** as v1, convert to uint8 RGB, and cache to `data/hires/<tile_idx>.npy`. That's about 3.4 MB per tile.
- Training crops:
  - **Step A:** 64×64 crops at 10 m, about 640 m field of view. This uses the same model and settings as v1, so the only change is metres per pixel. That gives a clean comparison.
  - **Step B** (only if A looks promising): 128×128 crops at 10 m, about 1.28 km field of view.
- Take 64 random crops per tile, with flips and 90° rotations. Drop crops with more than 5% no-data. Each crop inherits its tile's weight `w_i` from v1.

## 2. Training

- Same `diffusers` DDPM setup as v1. For Step B, use `UNet2DModel(sample_size=128, block_out_channels=(128,128,256,256,512))`.
- Train **`path_weighted` and `random_uniform`** first. Add `path_uniform` only if time allows.
- Same number of training steps, same seed and same architecture for each set. Log the wall-clock time.

## 3. Novelty at sampling time

All scoring uses the **agent's own final autoencoder and archive** from its walk. No pretrained networks.

**Scoring a sample:**
1. Take 16 random crops of the sample.
2. Resize each to the autoencoder's 32×32 input.
3. Encode them and take the mean latent.
4. Compute the scores:
   - `novelty` = mean distance to the k=10 nearest archive latents
   - `surprise` = mean reconstruction MSE

A known speedrun compromise: the samples' field of view doesn't match the agent's `crop_px` scale. Note it in the log and move on.

### 3a. Oversample and select (do first)

- Generate **N = 512** samples per model, with fixed noise seeds shared across models.
- Score all of them. Keep:
  - the top 32 by novelty, **excluding the top 2%**, which is a crude Wundt cut-off against garbage;
  - a random 32 as the reference.

### 3b. Novelty guidance (do second)

- During DDPM or DDIM sampling, at each step:
  1. compute the predicted clean image x̂₀;
  2. compute the gradient of `novelty(x̂₀)` through the agent's encoder;
  3. add `λ · grad` to the update.

  This is standard guidance with an external differentiable function, as in "universal guidance" (Bansal et al., 2023).
- Sweep **λ ∈ {0, 1, 3, 10}**. λ stands in for boredom: a bored agent dreams further from what it has seen.
- Normalise the gradient per step, and clip it if the samples blow up.
- Expect adversarial-looking artefacts at high λ. That's part of what this experiment is testing, so don't suppress it.

## 4. Outputs

Save everything to `runs/<agent_run_id>/dreams_v2/`.

1. **Contact sheet per agent:**
   - rows: `path_weighted` and `random_uniform` (and `path_uniform` if trained);
   - columns: random 32, novelty-selected 32, then guided at λ = 1, 3 and 10.
2. **v1 vs v2 sheet:** the same model type and seeds at 64 px from 40 m data against 64 px from 10 m data. This isolates the resolution effect.
3. **Memorisation check:** for every kept sample, show its nearest training crop by pixel L2.
4. **Scores table:** `sample_id, model, mode, λ, novelty, surprise, nn_train_dist`.
5. A short `observations.md`, descriptive only: what looks different, what looks better, and what looks like noise.

## Out of scope

Texture-by-numbers / image analogies, multispectral bands, StyleGAN, the narrator, and land-cover masks. These are possible next steps depending on what v2 shows.
