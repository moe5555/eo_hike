# Dreams v2: observations (baseline_s0, 2026-10-27)

(Copy of `runs/baseline_s0/dreams_v2/observations.md`; figures alongside. `scores.csv` and all samples stay in the run folder.)

This is a descriptive account. Deviations and compromises are in `log.md`; the expectation written beforehand is in `expectations_dreams_v2_2026-10-27.md`.

| Figure | Shows |
|---|---|
| `contact_sheet_10m_64.png` | the brief's contact sheet (rows: model; columns: random, novelty-selected, λ=1, 3, 10) |
| `contact_sheet_40m_64.png` | the same for the 40 m models, without guidance |
| `v1_vs_v2.png` | the same model type and seed ids, 40 m data against 10 m data |
| `guidance_sweep.png` | every λ that was run, including the extra λ = 0.03, 0.1, 0.3 |
| `memorisation_*.png` | every kept sample above its nearest training crop |
| `novelty_strips.png` | novelty and surprise per group |
| `scores.csv` | every scored image; `summary.csv` holds the medians per group |

Models: two 10 m and two 40 m (v1 recipe) DDPMs. All four are 26.6M parameters, trained for 15k steps at batch 64 in fp16, at about 76 min each. 512 samples per model, with the same seed ids across models.

## What looks different at 10 m

- **The same seed gives the same dream at both resolutions.** Median per-pixel RMSE between samples with the same seed id:

  | Pair | RMSE |
  |---|---|
  | 10 m vs 40 m, same training set (`random_uniform`) | 10.5 |
  | 10 m vs 40 m, same training set (`path_weighted`) | 17.4 |
  | path vs random, both 10 m | 13.9 |
  | path vs random, both 40 m | 20.7 |
  | different seed ids | 92 |

  Changing metres per pixel changes a dream about as much as changing which tiles it was trained on, or less. In `v1_vs_v2.png` the layout of each column (where the snow is, where the shadow is, where a valley runs) survives the resolution change.
- **The 10 m dreams are smoother patches, not sharper scenes.** At 40 m a 64 px sample covers 2.7 km and holds a whole slope with ridges and valleys. At 10 m it covers 640 m and holds one or two surfaces: a snowfield edge, a scree fan, part of a field, flat water. Edges are soft. Fine 10 m texture is rare: crevasse lines, field boundaries and roads appear in only a few samples. Several 10 m samples are nearly uniform (pale snow, grey-green, dark blue).
- **Colour follows v1's pattern.** Both 10 m models over-produce bright crops, as v1 did:

  | Model | Bright crops in its samples | Bright crops in its real training data |
  |---|---|---|
  | `path_weighted` | 39 % | 20 % |
  | `random_uniform` | 36 % | 14 % |

  The samples are also more saturated than their data: 0.30 against 0.17–0.24.
- **The 10 m `random_uniform` model shows more farmland and dark forest than `path_weighted`,** but snow patches still dominate its novelty column.

## What looks better

- **No sign of memorisation at either resolution.**
  - Among samples with any detail (pixel std > 12, 411–450 per model), none is closer to its training set than the closest *unseen* real crop is.
  - Median distance to the nearest training crop is 21–30 for detailed 10 m samples, against 12–15 for unseen real crops.
  - The closest kept samples (RMSE 4–5) are flat dark water.
- **In `contact_sheet_10m_64.png` the 10 m samples read as plausible Sentinel-2 crops.** Snow meeting rock, shadowed slopes, the edge of a lake, rust-brown scree. Nothing in the unguided pools looks like noise.

## Novelty selection (3a)

- **Novelty, as the agent measures it, is mostly contrast.** Spearman correlation of novelty with pixel std is 0.79–0.84 in all four models, with brightness 0.28–0.50 and with surprise 0.68–0.75.
  - The novelty-selected 32 are mostly hard-edged snow against black shadow, snow against brown rock, and cobalt water with bright margins.
  - The least novel samples are flat dark sea and flat grey-green.
  - This is the same taste the agent showed on its walk (v1 finding 2: snow and shadow beat the 272k-parameter AE).
- **The 2 % Wundt cut removed no garbage.** The top 10 by novelty in every model are plausible high-contrast alpine crops. The single odd one is a flat steel-blue square from the 10 m random model. The unguided pools contain no garbage for the cut to catch.
- **Selected samples sit further from training data:** median nn distance 29–56 against 18–38 for the random reference, mostly because high-contrast images have larger pixel distances to everything.
- **The 10 m dreams are more novel to the agent than its own training crops,** both the random reference and the whole pool:

  | Group (10 m `path_weighted`) | Median novelty |
  |---|---|
  | random reference | 1.70 |
  | whole pool | 1.71 |
  | real training crops at 10 m | 0.94 |
  | real unseen crops at 10 m | 0.78 |

  The field-of-view mismatch probably accounts for much of this: the agent never saw 480 m views. Real 10 m crops score low because they are mostly smooth, and the agent's archive is full of averaged latents.

## Novelty guidance (3b)

- **λ ∈ {1, 3, 10}: every guided sample collapses onto one of three smooth attractors.** The fraction of seeds per attractor is the same at every λ ≥ 1.
  1. A saturated royal-blue field with a pale pink rim: 44–47 % of seeds.
  2. Black/white binary blobs.
  3. Rust-red/white/black blobs.

  The attractor depends on the seed, not the model: the same seed id lands in the same attractor in both models and at all three λ. These aren't high-frequency adversarial patterns; they are large, smooth, posterised shapes.
- **Guided novelty saturates.** Median novelty is 9.9–11.7 at λ=1 and 11.7–12.9 at λ=10, against a pool maximum of about 5. Median surprise rises 7–24× over the pool. Nearest-training-crop distance is 78–93, so the samples are far off the data.
- **At λ ≥ 1 guidance replaces the dream rather than steering it.** The guided sample differs from its own unguided seed by RMSE 104–113, which is more than two unrelated unguided samples differ (92).
- **λ=0 reproduces the random reference exactly** (max pixel difference 0).
- **Extra sweep, not in the brief: λ ∈ {0.03, 0.1, 0.3}.** I added it because λ=1 was already saturated.
  - **λ=0.03** is the only setting where the dreams stay recognisable. The terrain layout survives, but it is recoloured: brown → terracotta or rust, water and shadow → cobalt, and snow-to-shadow contrast hardens. Median novelty 2.7–4.2, about the level of the top novelty-selected unguided samples. The colours resemble the "most foreign" dreams of v1's random model (terracotta, salmon, rust, glacier-cyan).
  - **λ=0.1:** mostly the blue and rust fields with soft remnants of structure.
  - **λ=0.3:** the three attractors are already there.

## What looks like noise

- No unguided sample from any model.
- Guided samples at λ ≥ 0.3 aren't noise in the pixel sense; they are smooth. They are, though, empty: three recurring blob shapes in three colour schemes that match nothing in the data.
- λ = 0.1 is partly in that state.

## Not done

- **Step B (128 px)** was not run, for two reasons:
  - At 128 px, batch 64 needs 33 GB and doesn't fit on this 16 GB GPU. With 4× gradient accumulation it would take about 6.4 h per model, about 13 h for two.
  - Step A's dreams don't show a clear gain from resolution, which was the condition for B.
- **`path_uniform`** was not trained (optional in the brief; about 76 min).
- **Only one agent:** `myopic_s0` was not walked on this machine.
