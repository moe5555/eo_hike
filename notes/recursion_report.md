# The recursion G1–G4: curious loop against Null loop — report (2026-11-24)

*Brief: `notes/brief_g2.md` and its extension (Moe, 2026-11-16 and 2026-11-17: G2–G4 at the same rules, 3,840 kimg, "snapshot as time", the real 15 km calibration reference, then the Landsat 1 upscaler, then stop for review). Predictions 169–173: `notes/06_characters/expectations.md`, dated 2026-11-17. Per-generation reports: `notes/gen1_gan_report.md`, `notes/gen1_latent_report.md`, `notes/gen2_gan_report.md`, `notes/gen2_latent_report.md`, `notes/gen3_gan_report.md`, `notes/gen3_latent_report.md`, `notes/gen4_gan_report.md`, `notes/gen4_latent_report.md`. Readouts: `notes/recursion/` (`recursion.csv`, `trends.png`, `strip_<cond>.png` from the pipeline; `chroma_stripes.csv`, `chroma_chain.png`, `stripes_in_walks.csv`, `taste_block_ci.csv` added post hoc). Upscaler: `notes/upscaler/`.*

## Short version

- **The loop ran end to end four times per condition, unattended,** from 2026-11-13 to 2026-11-24 on the PC. Each generation was a walk, then a package, then a GAN at 3,840 kimg, then a fresh walk in that GAN. There were 8 GAN trainings (4 generations × 2 conditions, about 55 h per generation) with no lost kimg, and 8 latent walks of 10,000 tiles. One supervisor restart was needed, on 2026-11-14, from a reused Windows pid.
- **Neither loop collapsed by the rule set by hand** (prediction 170 right). Coverage of the real G1 package stayed above G1's in both loops (prediction 169 wrong).
- **Both loops narrowed in colour at every generation** (brightness SD to 53 % and 66 % of G1's).
  - The null loop drifted away from the real package's neighbourhoods: precision 0.53 → 0.24, down to the curious loop's level, which never moved (0.24–0.26).
- **What the recursion amplifies is the instrument's line structure: coloured, slanted MSS scan lines.**
  - chroma_y (post hoc) rose to 4.4 × the real package in the curious loop and 3.0 × in the null loop.
  - The old banding statistic, set before the run, missed most of this (prediction 171 wrong in its null part).
- **The amplification happens mostly in the walks, through the radius rule, in both walkers.**
  - Both walkers linger where their eyes find stripes interesting. That pull wore off once stripes were common: after G2 in curious, after G3 in null.
  - The curious weighting gets there faster; the radius rule gets there anyway.
- **Time in latent walks was a premise throughout** (prediction 172 right). Every walk used up its three waits within the first 3 % of its steps. The Null's time path was identical in all four generations.
- **The Landsat 1 upscaler works and is honest about what it adds** (prediction 173 right). It beats bicubic by 5.4 dB median PSNR on held-out cells. On GAN samples it sharpens the scan lines a sample already has and does not invent them on smooth ones.
- **G5 is running** (Moe, 2026-11-24: "G5 at the same rules"). Predictions 174–178 were dated before any G5 package.
- **Every comparison is one walk, one GAN and one seed per condition per generation, so these are hints.** The era confound of the G1 packages carries through all generations.

## What was run, and what was set by hand

| Set by hand (premises) | Left to emerge |
|---|---|
| the world (Landsat 1 MSS, one view, nothing repaired); the walkers (two eyes, interest weights, the radius rule, temperature 0.5, q = 0.10, the end rule) | the G1 paths |
| G1 packages from three real walks per condition; the curious weighting e = exp(I / τ) at ESS = 0.5 N; the null unweighted | τ (3.67, 2.62, 2.35, 2.24) and what the weights favour |
| StyleGAN2-ADA at 128 px, 3,840 kimg, seed 0, the same in every generation | each GAN's world |
| latent walks: z-sphere, 8 offers in a random plane, α_min calibrated to the real 15 km colour step, snapshot as time | α_min (19.0/16.7/16.3/18.4° curious; 14.0/14.1/13.3/12.1° null), where and how the walkers moved |
| N = 10,000 tiles per latent walk; each walk's tiles are the next package | what each package contains |
| the observers: 32 px pixel space (k = 3), colour and texture statistics, the collapse rule; post hoc: chroma_y, stripe–radius link, block bootstrap | every trend reported here |

## Tables

**Across generations** (`notes/recursion/recursion.csv`, `trends.png`; 5,000 samples per GAN, ψ = 1):

| | G1-cur | G2-cur | G3-cur | G4-cur | G1-null | G2-null | G3-null | G4-null |
|---|---|---|---|---|---|---|---|---|
| precision, real G1 package | 0.240 | 0.235 | 0.254 | 0.258 | 0.526 | 0.423 | 0.324 | 0.241 |
| recall, real G1 package | 0.098 | 0.171 | 0.182 | 0.151 | 0.178 | 0.180 | 0.219 | 0.249 |
| recall, own training set | 0.10 | 0.53 | 0.61 | 0.60 | 0.18 | 0.65 | 0.80 | 0.83 |
| nearest-sample distance ÷ G1 | 1.00 | 1.00 | 0.89 | 0.90 | 1.00 | 1.12 | 1.32 | 1.36 |
| SD of brightness across samples | 22.3 | 13.7 | 12.0 | 11.9 | 48.0 | 39.8 | 36.6 | 31.6 |
| row roughness (stated measure) | 1.66 | 1.74 | 1.67 | 1.74 | 0.98 | 1.19 | 1.48 | 1.60 |
| chroma_y (post hoc) | 3.75 | 9.60 | 13.93 | 16.09 | 2.84 | 3.52 | 5.35 | 8.59 |
| green band dark (image share) | 0.0094 | 0.0018 | 0.0018 | 0.0002 | 0.0032 | 0.0016 | 0.0040 | 0.0032 |
| collapse flag | – | no | no | no | – | no | no | no |

**Where the stripes grow** (chroma_y; walk = package ÷ the samples of the GAN it was walked in; GAN = samples ÷ their package; `chroma_chain.png`):

| step | curious | null |
|---|---|---|
| G1 walk → G2 package | ×2.43 | ×1.25 |
| G2 GAN | ×1.05 | ×1.00 |
| G2 walk → G3 package | ×1.25 | ×1.50 |
| G3 GAN | ×1.16 | ×1.01 |
| G3 walk → G4 package | ×1.01 | ×1.46 |
| G4 GAN | ×1.14 | ×1.10 |
| real package → G4 samples | ×4.40 | ×2.98 |

**The walkers, generation by generation** (`notes/gen<g>/latent/walks.csv`, `stripes_in_walks.csv`):

| | G1-cur | G2-cur | G3-cur | G4-cur | G1-null | G2-null | G3-null | G4-null |
|---|---|---|---|---|---|---|---|---|
| boredom jumps (90°) | 25.3 % | 4.7 % | 3.2 % | 4.1 % | 20.6 % | 18.0 % | 11.7 % | 6.7 % |
| ρ(stripes, interest) | +0.19 | +0.07 | +0.04 | +0.06 | +0.23 | +0.30 | +0.19 | +0.08 |
| next offers at α_min after the most / least striped fifth | 67 / 33 % | 55 / 36 % | 47 / 46 % | 40 / 42 % | 68 / 39 % | 70 / 34 % | 62 / 37 % | 40 / 41 % |
| first step at the last snapshot | 1.3 % | 2.4 % | 2.4 % | 2.2 % | 2.8 % | 2.8 % | 2.8 % | 2.8 % |

## Findings

1. **No collapse, but two different drifts.**
   - By the rule set by hand, neither loop collapsed in four generations. Recall against the real package stayed above G1's, and samples did not crowd together.
   - Both loops lost colour range at every generation.
   - The null loop's samples left the real package's neighbourhoods step by step (precision halved), while the curious loop sat at the same low precision from G1 on. By G4 the two are equally far from the planet by this measure.
   - Set by hand: the observers and the rule. Emerged: the trajectories.
   - *RQ3; ch. 4, 8.*
2. **The recursion turns the instrument's scan lines into the world's main content.**
   - Coloured, slanted MSS scan lines grow in both loops, to 4.4 × (curious) and 3.0 × (null) the real package.
   - By eye, G4-curious is grey-khaki ground under multicoloured lines. G4-null is still more varied (relief, cloud, red vegetation) but much stripier than its G1.
   - Other artefacts do not follow:
     - the black 1977 green band fades out of the curious loop and holds in the null loop;
     - fill stays marginal;
     - the null loop keeps one flat saturated yellow field that it copies almost exactly in G2, G3 and G4.
   - *RQ2/RQ3; ch. 6, 8, 9.*
3. **The walks do most of the amplifying, through the radius rule, in both conditions.**
   - Package after package is stripier than the GAN it was walked in. The GANs mostly reproduce their package, and add a little only in G4.
   - Within the walks, striped tiles bring close offers about twice as often and boredom jumps half as often, in the Null as much as in the curious walker.
   - The Null's choice is uniform, but its radius follows its own drive. "A recursive loop without intrinsic motivation" is therefore not what the Null loop is in its movement. It is the same eyes and radius rule without the choice by interest.
   - The pull wears off once stripes are common: in curious from G3 and in the Null from G4. A candidate reading, not tested: what eyes grown from random weights find novel is what is rare in the world they walk.
   - Set by hand: the radius rule, the eyes, the weighting. Emerged: what pulls, and when it stops.
   - *RQ2/RQ3; ch. 6, 7, 8.*
4. **The curious weighting accelerates; it does not decide the direction.**
   - The curious loop's first latent walk raised the stripes ×2.43 at once.
   - The null walks raised them by ×1.25–1.50 per generation and kept doing so one generation longer.
   - Both move the same way on this axis, at different speeds and to different levels.
   - *RQ3; ch. 8.*
5. **Boredom fades in both loops** (90° jumps from about a fifth of steps to a few per cent). Each recursive world seems to vary more within a short step than the planet did at 15 km. The calibration keeps the real 15 km reference by decision, so the step does not adapt to that.
   - *RQ2/RQ3; ch. 7.*
6. **Time in synthetic worlds stayed a premise.** With four kept snapshots and q = 0.10, every walk used its three waits in the first 3 % of steps. The Null's time path is fixed by its seed. Nothing about time in the latent walks is a finding about the walkers.
   - *RQ1/RQ3; ch. 5.*
7. **Method notes.**
   - The banding statistic stated before the run (row roughness) could not see the dominant change. chroma_y was added after looking at G3 and is labelled post hoc throughout.
   - The step bootstrap for the taste intervals was not too narrow, contrary to an earlier claim, which is now withdrawn (block bootstrap, `taste_block_ci.csv`).
   - Recall in 32 px pixel space rose while the worlds became visibly less planet-like. It is a coverage measure, not a likeness measure.
   - *Method; ch. 8.*

## Against the predictions (169–173)

| # | predicted | measured | verdict |
|---|---|---|---|
| 169 | recall against the real G1 package falls G1 → G2 → G4 in both; curious faster | curious 0.098 → 0.171 → 0.151; null 0.178 → 0.180 → 0.249 | **wrong** |
| 170 | neither loop meets the collapse rule by G4 | curious recall ×1.55, distance ×0.90; null ×1.40, ×1.36 | **right** |
| 171 | G4-curious row roughness above G1-curious and above G4-null; G4-null within ±20 % of G1-null | 1.74 > 1.66 and > 1.60; null +63 % | **wrong** (null part) |
| 172 | the G3 and G4 walks reach the last snapshot within the first 3 % of steps | 2.4 / 2.8 % (G3), 2.2 / 2.8 % (G4) | **right** |
| 173 | the upscaler beats bicubic by ≥ 1 dB median PSNR on held-out cells; on GAN samples it adds scan-line texture where the sample already has some | 45.0 against 39.6 dB (+5.4 dB); added chroma_y +0.3–0.7 in the least striped third, +2.3–13.8 in the most striped third | **right** (second part measured with chroma_y, post hoc) |

**Why the misses:** both came from treating the Null walk as a neutral sampler and recall as a likeness measure. The Null walk lingers on stripes like the curious one, and recall rewards a spread-out cloud of samples.

## The Landsat 1 upscaler (prediction 173)

*`scripts/upscaler.py all`, trained 2026-11-24 00:19–12:32 (100k iterations, L1 0.0057 → 0.0044). Held-out evaluation: `notes/upscaler/eval.json`. Stripes: `analysis/recursion/upscaler_stripes.py` → `notes/upscaler/stripes_model_vs_bicubic.csv` (chroma_y, post hoc). Figures: `notes/upscaler/`. Full-screen renders of G4 samples: `runs/g4/fullscreen/` (outside git). Every output is a learned model's and is labelled so; the faithful enlargement stays integer nearest neighbour (`notes/upscaling.md`).*

**Held-out grid cells** (5 % of cells by hash, never seen at any date in training; 5,176 tiles; 128 → 178 px against the real 178 px rendering):

| | L1 (0–255) | PSNR mean | PSNR median |
|---|---|---|---|
| bilinear | 2.74 | 37.2 dB | 37.4 dB |
| bicubic | 2.17 | 39.1 dB | 39.6 dB |
| learned upscaler | 1.08 | 44.5 dB | 45.0 dB |

**What it adds** (chroma_y at 178 px; model ÷ bicubic; 600 tiles or samples per set; terciles by the input's own chroma_y):

| set | model ÷ bicubic | added, least striped third | added, most striped third | target ÷ bicubic |
|---|---|---|---|---|
| held-out reals | ×1.55 | +0.34 | +2.61 | ×1.68 |
| G1-curious / G1-null | ×1.52 / ×1.56 | +0.35 / +0.40 | +3.45 / +2.33 | – |
| G4-curious / G4-null | ×1.56 / ×1.58 | +0.67 / +0.27 | +13.75 / +7.78 | – |

- **It beats bicubic by 5.4 dB median PSNR on held-out cells,** against the ≥ 1 dB predicted. The L1 error halves.
- **It sharpens what is there.** The added chroma_y is roughly proportional to the input's own stripes: small on the least striped third, large on the most striped third. This holds in every generation.
- **On real held-out tiles it restores most of the 60 m colour structure, not all of it** (×1.55 of the ×1.68 that the real target holds).
- **By eye** (`heldout_input_bicubic_model_target.png`, `g<g>_<cond>_3840kimg_bicubic_vs_model.png`): on reals the model is close to the target, with sharper relief and individual scan lines resolved. On GAN samples it turns soft colour bands into crisp one-pixel lines and does not invent lines on smooth samples.
- Set by hand: the pairs chain, the architecture, L1, 100k iterations, seed 0. Emerged: the error and what it draws.
- *RQ3; ch. 9 (film), 8.*

## For review (decisions for Moe)

- **The Null loop as a control.** Its walk is not neutral (finding 3). The options:
  - random sampling of each GAN (separates the walk from the GAN);
  - a Null with a fixed radius (separates the radius rule);
  - keep it as is and name it "same eyes, no choice".
- **chroma_y as a standing observer**, or the quirk observer on GAN samples (prediction 154), before any further generation.
- **The recursion continues to G5** (Moe, 2026-11-24). It tests whether the GANs keep adding stripes on their own (×1.10–1.14 in G4), now that the walks no longer do (predictions 174–178). The G5 report and an addendum to this one follow when G5 is done (about Friday 2026-11-27).
- **Snapshot as time** gives no time behaviour worth reading. Keep it, or change the rule for synthetic worlds.
- **The calibration** stays at the real 15 km reference by decision. Boredom fading is partly a consequence of that.
