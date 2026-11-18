# GAN generation 2: G2-curious (weighted) against G2-null (unweighted) â€” report (2026-11-18)

*Brief: `notes/brief_g2.md` (Moe, 2026-11-16: the same rules as G1, 3,840 kimg). Predictions 164â€“168: `notes/06_characters/expectations.md`, dated before any G2 package. Inputs: the G1 latent walks (`notes/gen1_latent_report.md`), packaged at tag `g2-paths`. Code: `gen/g1_gan.py --gen 2` and `analysis/recursion/readouts.py`. Outputs: `runs/g2/gan/` (pickles and samples; outside git) and `notes/gen2/gan/` (tables and small figures). Device: the PC (Quadro RTX 5000), in the scheduled pipeline.*

## Short version

- **Both GANs trained to 3,840 kimg** from 2026-11-16 13:38 to 2026-11-18 20:54 (55.3 h), in alternating 400 kimg chunks. There were no restarts and no lost kimg.
  - FID against each run's own training set fell at every kept snapshot (curious 23.6 â†’ 8.4, null 35.2 â†’ 7.7). This is a training-health signal only. It is not comparable with G1's FID (17.8 and 23.2), because the G2 training sets are themselves GAN images.
- **Each G2 covers its own training set far better than G1 covered its own:** recall 0.53 (curious) and 0.65 (null), against G1's 0.10 and 0.18.
- **Against the real G1 package, coverage rose for curious and held for null.** Recall was 0.171 against G1's 0.098 for curious, and 0.180 against 0.178 for null. Nothing has collapsed by the rule set by hand (prediction 170).
- **The spread across samples narrowed in both loops** (prediction 165): the standard deviation of brightness and of each channel mean is 15â€“38 % lower in G2 than in G1. The distance from a sample to its nearest other sample did not fall: curious Ã—1.00, null Ã—1.13.
- **The apparatus (colour and texture statistics, labelled as such):**
  - **Row roughness rose in both loops:** curious 1.66 â†’ 1.74 (+5 %) and null 0.98 â†’ 1.19 (+22 %). Curious is still the rougher of the two.
  - **The black green band of 1977 thinned again in both:** curious 0.94 % â†’ 0.18 % of samples, null 0.32 % â†’ 0.16 %.
  - **Black fill came back in curious** (0.04 % â†’ 0.44 % of pixels), at about its training share (0.46 %).
- **Memorisation:**
  - G2-null's closest samples are flat fields (white, yellow, black, grey, dark sea) that match flat training tiles almost exactly (distance 0.0 to 0.45). 0.8 % of its samples lie below the training set's own 1st percentile; in G1 it was 0.08 %.
  - G2-curious has no such near-copies (0.1 % below p1). Its closest pairs are flat yellow and striped beige desert.
- **Predictions:** 164 right; 165 right; 166 wrong; 167 right; 168 right.
- **Every comparison here is one walk, one GAN and one seed per condition per generation, so these are hints.** The era confound of the G1 packages carries through: G1-curious and G1-null were trained on paths from different parts of the mission, and every later generation inherits that difference.

## What was run

- **Packages (`paths/g2/<cond>/`):** the 10,000 tiles of each G1 latent walk, rendered by the walker. The render check passed with at most 2 of 255 difference (batch against single rendering). Nothing was repaired. About 1â€“3 % of each package comes from G1's earlier snapshots (960 and 1,920 kimg); the rest comes from the 3,840 kimg world.
- **Weights (curious):** the G1 formula unchanged, e = exp(I / Ï„) per encounter.
  - A latent walk never revisits, so every tile has one encounter and the ESS limit of the counts alone is N.
  - Ï„ solved for ESS = 0.5 N: **Ï„ = 2.617** (G1: 3.665).
  - The top 1 % of tiles hold 0.058 of the weight and the top 10 % hold 0.233. Max/median is 69.0.
  - Null: weight 1 for every tile.
- **Training:** G1's settings and measured budget, inherited rather than re-measured (same architecture, size and GPU).
  - StyleGAN2-ADA cfg auto at 128 px, seed 0, ADA target 0.6, bgc;
  - 3,840 kimg each, with snapshots every 40 kimg, kept at 960, 1,920, 2,880 and 3,840;
  - 25.5 s/kimg per run.
- **After training:** fid50k_full on the kept snapshots; 5,000 samples per GAN (seeds 0â€“4,999, Ïˆ = 1); memorisation and precision/recall in 32 Ã— 32 pixel space; colour and texture statistics.
- **Added for this report:** `analysis/recursion/readouts.py` on G1 and G2, giving coverage against the real G1 package, the spread across samples and the collapse flag (`notes/gen2/gan/cross_generation_g1_g2.csv`). The pipeline reruns it over all four generations after G4.
- **Visual, by eye:** the same 8 seeds at Ïˆ = 1, 2 and 3 (`notes/gen2/gan/<cond>_far_ends_psi1-3.png`).

### Set by hand, and left to emerge

| Set by hand (premises) | Left to emerge |
|---|---|
| the G1 latent walks as packages (walker configs, z-sphere, the colour-calibrated step, snapshot as time, q = 0.10) | what each package contains |
| N = 10,000; ESS = 0.5 N; the weight mapping e = exp(I / Ï„) | Ï„ and the weight concentration |
| 3,840 kimg, G1's training settings, seed 0 | ADA p, FID, the samples |
| the observers: 32 px pixel space with k = 3; colour and texture statistics; the collapse rule (prediction 170) | coverage, spread, the apparatus statistics |
| the radius rule, which also acts in the Null's walk | where each walk lingered |

## Tables

**Training and coverage** (`readouts.json`, `cross_generation_g1_g2.csv`):

| | G1-curious | G2-curious | G1-null | G2-null |
|---|---|---|---|---|
| final ADA p | 0.161 | 0.124 | 0.141 | 0.097 |
| FID at 960 / 1,920 / 2,880 / 3,840 kimg (own training set; health only) | 43.0 / 25.7 / 20.6 / 17.8 | 23.6 / 12.1 / 10.0 / 8.4 | 53.0 / 40.5 / 29.9 / 23.2 | 35.2 / 12.7 / 8.1 / 7.7 |
| precision / recall against own training set | 0.239 / 0.096 | 0.737 / 0.533 | 0.518 / 0.182 | 0.755 / 0.647 |
| precision / recall against the real G1 package | 0.240 / 0.098 | 0.235 / 0.171 | 0.526 / 0.178 | 0.423 / 0.180 |
| recall against real, Ã· G1's | 1.00 | 1.75 | 1.00 | 1.01 |
| median nearest-sample distance (32 px) | 4.39 | 4.40 | 2.39 | 2.68 |
| Ã· G1's | 1.00 | 1.00 | 1.00 | 1.13 |
| collapse flag (recall < 0.5 Ã— G1 and nearest-sample distance < 0.7 Ã— G1) | â€“ | no | â€“ | no |

**Spread across 5,000 samples** (standard deviation of the per-sample mean; colour and texture statistics):

| | G1-curious | G2-curious | G1-null | G2-null |
|---|---|---|---|---|
| brightness | 22.3 | 13.7 | 48.0 | 39.8 |
| NIR (R channel) | 23.9 | 16.5 | 48.1 | 39.6 |
| red band (G channel) | 27.2 | 20.0 | 50.3 | 42.3 |
| green band (B channel) | 27.0 | 22.3 | 49.2 | 41.1 |
| mean brightness | 105.6 | 112.1 | 119.5 | 111.4 |

**The apparatus: samples, their training set, and the G1 GAN they came from** (colour and texture statistics of the 128 px images, the GAN report's definitions; `colour_texture.csv` in `notes/gen1/gan/` and `notes/gen2/gan/`):

| statistic | G1-curious samples | G2-curious package (unweighted / weighted) | G2-curious samples | G1-null samples | G2-null package | G2-null samples |
|---|---|---|---|---|---|---|
| row roughness (banding) | 1.659 | 1.738 / 1.765 | 1.737 | 0.982 | 1.155 | 1.194 |
| green band dark (image share) | 0.0094 | 0.0047 / 0.0103 | 0.0018 | 0.0032 | 0.0033 | 0.0016 |
| black share (fill-like pixels) | 0.0004 | 0.0046 / 0.0058 | 0.0044 | 0.0001 | 0.0001 | 0.0002 |
| white share | 0.0034 | 0.0054 / 0.0113 | 0.0073 | 0.0085 | 0.0035 | 0.0054 |
| gradient x / y (texture) | 6.90 / 7.61 | 7.33 / 10.54 | 7.70 / 11.35 | 4.08 / 4.65 | 4.80 / 5.56 | 4.94 / 5.68 |

**Memorisation** (32 px; distance from each sample to its nearest training tile, against the training set's own nearest-neighbour distances):

| | G1-curious | G2-curious | G1-null | G2-null |
|---|---|---|---|---|
| median sampleâ†’train Ã· median trainâ†’train | 1.05 | 1.15 | 0.89 | 1.26 |
| samples below the training set's p1 | 0.3 % | 0.1 % | 0.08 % | 0.8 % |
| closest pair | 0.09 (seed 411) | 0.45 (flat yellow) | â€“ | 0.00 (flat white) |

## Findings

1. **Each G2 learned its world much more completely than G1 learned the planet.**
   - Recall against its own training set rose from 0.10 to 0.53 (curious) and from 0.18 to 0.65 (null), and FID fell to 8.4 and 7.7.
   - A likely reason, not tested: a latent walk's neighbouring tiles share their layout (the step changes colour, not layout), so a 10,000-tile package holds far fewer independent places than 10,000. It is also already a GAN's image.
   - Set by hand: the colour-calibrated step and 3,840 kimg. Emerged: the coverage.
   - *RQ3; ch. 4, 8.*
2. **Narrower in colour, not closer together.**
   - Across samples, brightness and the channel means vary 15â€“38 % less in G2 than in G1, in both loops.
   - The median distance between neighbouring samples in 32 px space stayed the same (curious) or grew (null, Ã—1.13). Both GANs' mean brightness moved towards about 111â€“112 (curious up from 106, null down from 119).
   - Set by hand: the statistics and the observer. Emerged: the spreads.
   - *RQ3; ch. 8.*
3. **Coverage of the real world did not fall.**
   - Against the real G1 package (5,000 tiles), G2-curious's recall is 1.75 Ã— G1-curious's, and G2-null's is unchanged (Ã—1.01). G2-null's precision fell (0.53 â†’ 0.42).
   - By the hand-set collapse rule, neither loop is near collapse in G2.
   - Caveat: recall counts real tiles that fall inside the samples' own neighbourhoods. A smoother or more evenly spread sample cloud raises it without more planet-like images. The far-end sheets (finding 6) do not look more planet-like.
   - *RQ3; ch. 8.*
4. **Banding rose in both loops; the 1977 green band thinned in both.**
   - Row roughness of samples rose by 5 % (curious) and 22 % (null). In both, the rise happened in the walk rather than in training: each G2 package was already rougher than the G1 samples it came from (curious 1.74 against 1.66, null 1.16 against 0.98), and each G2 reproduced its package (Ã—1.00 and Ã—1.03).
   - The curious walker chose rougher offers than it was offered (+0.042 per step, `notes/gen1_latent_report.md`). The Null showed no such gap at the choice, yet its package rose more.
   - A candidate cause, not tested: the radius rule also acts in the Null's walk. It keeps the offers close while the drive is high, so the Null may linger where its eyes find more. That premise is shared by both walkers.
   - The black green band of 1977 thinned again in both GANs (to 0.38 Ã— and 0.48 Ã— of their training shares), as in G1.
   - Set by hand: the radius rule for both, the eyes, the statistics. Emerged: where the walks lingered and what the GANs kept.
   - *RQ2/RQ3; ch. 7, 8.*
5. **Black fill came back in curious; the null's attractors are flat fields.**
   - G2-curious keeps fill-like black pixels at their training share (0.44 % against 0.46 %). G1-curious had nearly erased them (0.04 %).
   - G2-null's closest-to-training samples are uniform fields (white, yellow, black, grey, dark sea) matching uniform training tiles, which explains its tenfold rise in near-copies (0.8 % below p1).
   - *RQ3; ch. 8, 9 (film).*
6. **Visual, not measured (8 seeds; `<cond>_far_ends_psi1-3.png`):**
   - G2-curious at Ïˆ = 1 already shows dense, multicoloured diagonal scan lines in 6 of 8 samples. At Ïˆ = 2â€“3 the terrain dissolves first; the stripes survive longest.
   - G2-null at Ïˆ = 1 looks like landscape (relief, sea with cumulus, red vegetation, snow), with faint stripes in 3 of 8. At Ïˆ = 2â€“3 it collapses into flat yellow, black and white fields.
   - So both loops tend towards the apparatus at the extremes, towards different parts of it: line texture for curious, flat value fields for null. In G1 the flat yellow belonged to curious and the black bars to null.
   - This is a lead for the quirk observer (prediction 154, deferred), not a result.
   - *RQ3; ch. 8, 9 (film).*

## Against the predictions (164â€“168)

| # | predicted | measured | verdict |
|---|---|---|---|
| 164 | ESS = 0.5 N reachable; Ï„ 1.5â€“4; top 10 % hold 0.20â€“0.30 of the weight | reachable (limit N); Ï„ = 2.617; top 10 % 0.233 | **right** |
| 165 | the spread across samples (SD of brightness and of each channel mean) is lower in G2 than in G1, for both | curious 22.3 â†’ 13.7, 23.9 â†’ 16.5, 27.2 â†’ 20.0, 27.0 â†’ 22.3; null 48.0 â†’ 39.8, 48.1 â†’ 39.6, 50.3 â†’ 42.3, 49.2 â†’ 41.1 | **right** on all eight. The nearest-sample distance did not fall (finding 2), so the narrowing is in colour, not in pixel-space spacing |
| 166 | G2-curious has higher row roughness and a higher green-band-dark share than G1-curious; G2-null within Â±20 % of G1-null on both | curious roughness 1.659 â†’ 1.737 (higher), green band dark 0.0094 â†’ 0.0018 (lower); null roughness +21.6 %, green band dark âˆ’50 % | **wrong**: the roughness part holds for curious, the green-band part is reversed, and the null drifted too (just outside Â±20 % on roughness) |
| 167 | final ADA p of each G2 within Ã— 1.5 of its G1's | curious 0.124 against 0.161 (Ã— 0.77); null 0.097 against 0.141 (Ã— 0.69) | **right**; null near the edge (the limit is Ã— 0.67) |
| 168 | Î±_min of each G2 within 30 % of its G1 value | curious 16.7Â° against 19.0Â° (âˆ’12 %); null 14.1Â° against 14.0Â° (+1 %) | **right** |

**Why the miss:**
- 166 assumed that the walk would carry the 1977 green band forward in curious. The G1 latent report had already shown the opposite: the curious walker chose the black green band about half as often as it was offered. The GAN then thinned it once more.
- The null part assumed the Null's walk would be a neutral sample of its GAN. Its package was 18 % rougher than G1-null's samples (finding 4).

**Early readings for 169â€“171, scored after G4:**
- 169 expects recall against the real package to fall from G1 to G2. Curious rose and null held, so that part is already against it.
- 171's curious part (rougher than G1) holds so far. Its null part (within Â±20 % of G1-null's 0.98) is already outside, at 1.19.

## For review

- **The Null's latent walk is not a neutral sampler of its GAN.**
  - The radius rule acts in both walkers (the same premise as on the planet), and the Null's package came out rougher than its GAN's samples.
  - If the Null loop is meant to be "a recursive loop without intrinsic motivation" (RQ3), a control that samples each GAN at random (5,000 seeds, Ïˆ = 1) would separate the walk's effect from the GAN's. This is Moe's decision; nothing has been changed.
- **Layout-correlated packages** (finding 1) may inflate coverage of the own training set and speed up narrowing. A within-package readout (distance between tiles k steps apart, against random pairs) would measure it. The calibration stays at the real 15 km step, per Moe (2026-11-17).
- **Recall against the real package rising** (finding 3) needs the quirk observer or a pretrained-feature observer before it is read as "closer to the planet".
- **The quirk observer on GAN samples** (prediction 154) would test findings 5 and 6.
