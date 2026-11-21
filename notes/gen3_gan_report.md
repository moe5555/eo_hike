# GAN generation 3: G3-curious (weighted) against G3-null (unweighted) — report (2026-11-21)

*Brief: `notes/brief_g2.md` and its extension (Moe, 2026-11-17: G3 and G4 at the same rules, 3,840 kimg). Predictions 169–173: `notes/06_characters/expectations.md`, dated 2026-11-17, before any G3 package. Inputs: the G2 latent walks (`notes/gen2_latent_report.md`), packaged at tag `g3-paths`. Code: `gen/g1_gan.py --gen 3`, `analysis/recursion/readouts.py`, and two scripts added for this report, `analysis/recursion/chroma_stripes.py` and `analysis/recursion/stripes_in_walks.py` (post hoc, see below). Outputs: `runs/g3/gan/` (pickles and samples; outside git), `notes/gen3/gan/` (tables and small figures), `notes/recursion/chroma_stripes.csv` and `stripes_in_walks.csv`. Device: the PC (Quadro RTX 5000), in the scheduled pipeline.*

## Short version

- **Both GANs trained to 3,840 kimg** from 2026-11-19 01:13 to 2026-11-21 08:30 (55.3 h), in alternating 400 kimg chunks. There were no restarts and no lost kimg.
  - FID against each run's own training set: curious 23.2 → 7.9 (flat from 2,880 kimg on), null 27.6 → 7.5. This is a training-health signal only.
- **Coverage of the real G1 package rose again in both loops.** Recall was 0.182 for curious (G1 0.098, G2 0.171) and 0.219 for null (G1 0.178, G2 0.180). No collapse by the hand-set rule.
- **The two loops now move apart in spacing.**
  - G3-curious samples sit closer together: nearest-sample distance 3.89, which is 0.89 × G1's.
  - G3-null's sit further apart: 3.14, which is 1.32 × G1's.
  - The colour spread across samples narrowed again in both.
- **Chromatic scan lines are what grows, and the old banding statistic misses them.**
  - The samples are visibly dominated by coloured diagonal scan lines in curious, and partly in null.
  - Yet row roughness fell in curious (1.74 → 1.67). It averages brightness along pixel rows, so lines that are coloured and slanted cancel out.
  - A post-hoc statistic, chroma_y (vertical change in each channel minus brightness), rises steadily along both loops. Against the real G1 package, G3-curious is at **3.8 ×** and G3-null at **1.9 ×**.
- **Most of that rise happens in the walks, not in the GANs.**
  - Each package is stripier than the samples of the GAN it was walked in: ×2.43 and ×1.25 in curious, ×1.25 and ×1.50 in null.
  - Each GAN then reproduces its package (×1.00 to ×1.16).
  - In both walkers, offers after a striped tile are close (α_min) about twice as often as after an unstriped one, and boredom jumps are rarer. The choice in the Null is uniform; its radius is not.
- **Memorisation:**
  - G3-null reproduces one flat saturated yellow training tile almost exactly (5 samples within 0.05–0.12 of it). 0.5 % of its samples lie below the training p1.
  - G3-curious has no near-copies (0.0 %).
- **Every comparison here is one walk, one GAN and one seed per condition per generation, so these are hints.** The era confound of the G1 packages carries through: G1-curious and G1-null were trained on paths from different parts of the mission, and every later generation inherits that difference.

## What was run

- **Packages (`paths/g3/<cond>/`):** the 10,000 tiles of each G2 latent walk, rendered by the walker. The render check passed (≤ 2 of 255). Nothing was repaired. 2.5 % (curious) and 2.8 % (null) of the steps came from G2's earlier snapshots.
- **Weights (curious):** the G1 formula unchanged, e = exp(I / τ). τ solved for ESS = 0.5 N: **τ = 2.349** (G2: 2.617). The top 1 % hold 0.070 of the weight and the top 10 % hold 0.260. Max/median is 50.9. Null: weight 1.
- **Training:** G1's settings and budget, inherited (StyleGAN2-ADA cfg auto at 128 px, seed 0, ADA target 0.6, bgc). 3,840 kimg each; kept snapshots at 960, 1,920, 2,880 and 3,840; 25.5 s/kimg.
- **After training (pipeline):** fid50k_full on the kept snapshots; 5,000 samples per GAN (seeds 0–4,999, ψ = 1); memorisation and precision/recall in 32 × 32 pixel space; colour and texture statistics.
- **Added for this report:**
  - `analysis/recursion/readouts.py` on G1–G3 (`notes/gen3/gan/cross_generation_g1_g3.csv`);
  - the same 10 seeds rendered from G1, G2 and G3 (`<cond>_same_seeds_g1_g2_g3.png`; this seed draw is separate from the far-end sheets);
  - far ends at ψ = 1, 2 and 3 (`<cond>_far_ends_psi1-3.png`).
- **Post hoc, after looking at the sheets** (described, not tested):
  - **`chroma_stripes.py`:** chroma_y, chroma_x and their ratio on 2,000 images per set, for every package and every generation's samples.
  - **`stripes_in_walks.py`:** per step of the G1 and G2 latent walks, chroma_y of the tile against the walker's interest and the radius of the next offers.
  - The existing row roughness is kept as it was.

### Set by hand, and left to emerge

| Set by hand (premises) | Left to emerge |
|---|---|
| the G2 latent walks as packages (walker configs, z-sphere, the colour-calibrated step against the real 15 km reference, snapshot as time, q = 0.10) | what each package contains |
| N = 10,000; ESS = 0.5 N; e = exp(I / τ) | τ and the weight concentration |
| 3,840 kimg, G1's training settings, seed 0 | ADA p, FID, the samples |
| the observers: 32 px pixel space with k = 3; colour and texture statistics; chroma_y (chosen after seeing the images); the collapse rule (prediction 170) | coverage, spread, the apparatus statistics |
| the radius rule, in both walkers | where each walk lingered, and on what |

## Tables

**Training and coverage** (`readouts.json`, `cross_generation_g1_g3.csv`):

| | G1-curious | G2-curious | G3-curious | G1-null | G2-null | G3-null |
|---|---|---|---|---|---|---|
| final ADA p | 0.161 | 0.124 | 0.145 | 0.141 | 0.097 | 0.109 |
| FID at 960 / 1,920 / 2,880 / 3,840 kimg (own set; health only) | 43.0 / 25.7 / 20.6 / 17.8 | 23.6 / 12.1 / 10.0 / 8.4 | 23.2 / 11.5 / 7.9 / 7.9 | 53.0 / 40.5 / 29.9 / 23.2 | 35.2 / 12.7 / 8.1 / 7.7 | 27.6 / 17.3 / 8.6 / 7.5 |
| precision / recall, own training set | 0.239 / 0.096 | 0.737 / 0.533 | 0.776 / 0.612 | 0.518 / 0.182 | 0.755 / 0.647 | 0.789 / 0.802 |
| precision / recall, real G1 package | 0.240 / 0.098 | 0.235 / 0.171 | 0.254 / 0.182 | 0.526 / 0.178 | 0.423 / 0.180 | 0.324 / 0.219 |
| recall against real ÷ G1's | 1.00 | 1.75 | 1.86 | 1.00 | 1.01 | 1.23 |
| median nearest-sample distance (32 px) ÷ G1's | 4.39 (1.00) | 4.40 (1.00) | 3.89 (0.89) | 2.39 (1.00) | 2.68 (1.12) | 3.14 (1.32) |
| collapse flag | – | no | no | – | no | no |

**Spread across 5,000 samples** (SD of the per-sample mean; colour and texture statistics):

| | G1-cur | G2-cur | G3-cur | G1-null | G2-null | G3-null |
|---|---|---|---|---|---|---|
| brightness | 22.3 | 13.7 | 12.0 | 48.0 | 39.8 | 36.6 |
| NIR (R) | 23.9 | 16.5 | 13.1 | 48.1 | 39.6 | 37.8 |
| red band (G) | 27.2 | 20.0 | 16.7 | 50.3 | 42.3 | 40.5 |
| green band (B) | 27.0 | 22.3 | 19.7 | 49.2 | 41.1 | 38.9 |

**The apparatus: G2 samples → G3 package → G3 samples** (colour and texture statistics; `colour_texture.csv` in `notes/gen2/gan/` and `notes/gen3/gan/`; chroma from `notes/recursion/chroma_stripes.csv`, n = 2,000 per set, unweighted):

| statistic | G2-cur samples | G3-cur package (unw. / weighted) | G3-cur samples | G2-null samples | G3-null package | G3-null samples |
|---|---|---|---|---|---|---|
| row roughness (old banding statistic) | 1.737 | 1.624 / 1.681 | 1.667 | 1.194 | 1.410 | 1.483 |
| chroma_y (coloured stripes; post hoc) | 9.60 | 12.02 / – | 13.93 | 3.52 | 5.29 | 5.35 |
| chroma_y ÷ chroma_x | 1.73 | 1.90 / – | 1.98 | 1.33 | 1.46 | 1.42 |
| green band dark (image share) | 0.0018 | 0.0003 / 0.0026 | 0.0018 | 0.0016 | 0.0029 | 0.0040 |
| black share (fill-like pixels) | 0.0044 | 0.0039 / 0.0042 | 0.0028 | 0.0002 | 0.0006 | 0.0007 |
| white share | 0.0073 | 0.0064 / 0.0129 | 0.0099 | 0.0054 | 0.0048 | 0.0104 |
| gradient x / y | 7.70 / 11.35 | 6.98 / 11.62 | 7.29 / 12.63 | 4.94 / 5.68 | 5.75 / 7.05 | 6.04 / 7.50 |

**Chromatic stripes along the whole loop** (chroma_y; in brackets the factor against the previous set):

| set | curious | null |
|---|---|---|
| real G1 package (the planet, as walked) | 3.66 | 2.88 |
| G1 samples | 3.75 (×1.03) | 2.84 (×0.98) |
| G2 package (the G1 latent walk) | 9.12 (×2.43) | 3.53 (×1.25) |
| G2 samples | 9.60 (×1.05) | 3.52 (×1.00) |
| G3 package (the G2 latent walk) | 12.02 (×1.25) | 5.29 (×1.50) |
| G3 samples | 13.93 (×1.16) | 5.35 (×1.01) |
| G3 samples ÷ real package | **×3.81** | **×1.86** |

**Do the walks dwell on stripes?** (`stripes_in_walks.csv`; per step, the tile's chroma_y against the walker's interest I and the radius α of the next offers; Spearman; steps are autocorrelated, so these describe the walk and are not tests):

| walk | ρ(chroma_y, I) | ρ(chroma_y, next α) | next offers at α_min: most / least striped fifth | next offers at 90°: most / least striped fifth |
|---|---|---|---|---|
| G1 curious | +0.19 | −0.29 | 67 % / 33 % | 12 % / 41 % |
| G1 null | +0.23 | −0.21 | 68 % / 39 % | 14 % / 30 % |
| G2 curious | +0.07 | −0.11 | 55 % / 36 % | 4 % / 6 % |
| G2 null | +0.30 | −0.26 | 70 % / 34 % | 8 % / 26 % |

**Memorisation** (32 px):

| | G2-curious | G3-curious | G2-null | G3-null |
|---|---|---|---|---|
| median sample→train ÷ median train→train | 1.15 | 1.24 | 1.26 | 1.27 |
| samples below the training set's p1 | 0.1 % | 0.0 % | 0.8 % | 0.5 % |
| closest pair | 0.45 (flat yellow) | 1.31 (striped desert) | 0.00 (flat white) | 0.05 (flat saturated yellow, 5 seeds on one tile, `k000539_s1920`) |
| samples nearer the heaviest 10 % than the lightest 10 % of tiles | – | 48.5 % | – | – |

## Findings

1. **The apparatus grows through the walks, not mainly through the GANs.**
   - Chromatic scan lines (chroma_y) rose at every step of both loops, to 3.8 × the real G1 package in curious and 1.9 × in null.
   - Split by step, the GANs mostly reproduce what they are given (×1.00 to ×1.16). Each walk hands its successor a package stripier than the GAN it walked in (×1.25 to ×2.43).
   - Set by hand: the radius rule, the eyes, the drive settings, the statistic. Emerged: the size of each step's effect and the fact that it sits in the walk.
   - *RQ2/RQ3; ch. 7, 8.*
2. **Stripes hold the walkers, the Null included.**
   - On the walker's own tiles, chroma_y correlates with interest (ρ +0.07 to +0.30). After a striped tile, the offers are close (α_min) about twice as often, and boredom jumps are a third to a half as frequent, as after an unstriped one.
   - This holds for the Null as strongly as for the curious walker. The Null's choice is uniform, but its radius follows its own eyes' drive, so it lingers where the stripes are.
   - In G2-curious, where boredom had almost stopped (4.7 % jumps), the link is weaker but still there.
   - A candidate reading: scan lines are what an autoencoder grown from random weights finds hard to predict, and the radius rule turns that difficulty into dwelling.
   - Set by hand: the radius rule, the eyes, the drive filter. Emerged: what the eyes find interesting, and that it is the instrument's line structure.
   - *RQ2; ch. 6, 7.*
3. **The old banding statistic was blind to the main change.**
   - Row roughness averages brightness along pixel rows. The MSS scan lines in these tiles run at an angle to the rows and are mostly in one band at a time, so the average washes them out.
   - Its fall in G3-curious (1.74 → 1.67) contradicts the images and chroma_y.
   - The G2 latent report's "taste flip" (curious chose slightly less banding, −0.022) used the same statistic and should be re-read; the G3 package it produced is stripier by chroma_y (×1.25).
   - *Method; ch. 8.*
4. **Coverage of the real world rose, the loops parted in spacing, and the colour range narrowed.**
   - Recall against the real G1 package rose in both: curious ×1.86 and null ×1.23 of G1.
   - The colour spread across samples narrowed again in both (curious brightness SD 22.3 → 12.0, null 48.0 → 36.6).
   - Nearest-sample distance fell in curious (×0.89) and rose in null (×1.32).
   - G3-null's precision against the real package keeps falling (0.53 → 0.42 → 0.32): more of its samples fall outside the planet's neighbourhoods.
   - The same caveat as in G2: recall can rise with a smoother or more evenly spread cloud of samples, without more planet-like images. The sheets show a curious loop that looks less planet-like.
   - *RQ3; ch. 8.*
5. **Two different worlds by eye** (`<cond>_same_seeds_g1_g2_g3.png`, `<cond>_far_ends_psi1-3.png`, the 256-sample contact sheets; visual, not measured):
   - **G3-curious:** grey-khaki relief and desert, crossed by dense, multicoloured diagonal scan lines on most samples. Black streaks, lime-green and fluorescent patches appear; red vegetation is almost gone (8 of 10 same-seed samples are striped).
   - At ψ = 2–3, terrain dissolves first. Stripes and flat colour fields (green, yellow, violet) are what remain.
   - **G3-null:** a more varied planet than G2-null: red vegetation and cumulus are back, open sea with coastlines appears (3 of 10 same-seed samples), and there is relief and snow. Stripes appear on a minority.
   - Its flat attractors persist: a pure yellow field that it copies almost exactly from its training set, and white and black fields at ψ ≥ 2.
   - *RQ3; ch. 8, 9 (film).*
6. **The 1977 green band now survives in null and is carried by the weighting in curious.**
   - G3-null samples hold more dark-green-band images than their package (0.40 % against 0.29 %): the first time a GAN in this loop did not thin it.
   - In curious the unweighted package has almost none (0.03 %), the weighted one 0.26 %, and the samples 0.18 %. The heaviest tiles carry it in.
   - *RQ2/RQ3; ch. 6, 8.*

## Against the predictions (interim; 169–171 and 173 are scored after G4, 172 after the G3 and G4 walks)

| # | predicted | at G3 | reading so far |
|---|---|---|---|
| 169 | recall against real falls G1 → G2 → G4 in both; curious faster | curious 0.098 → 0.171 → 0.182; null 0.178 → 0.180 → 0.219 | **against it**: the G1 → G2 part is already wrong for curious, and both still rise |
| 170 | neither loop meets the collapse rule by G4 | curious recall ×1.86, distance ×0.89; null ×1.23, ×1.32 | consistent: neither is close |
| 171 | G4-curious rougher than G1-curious (1.66) and G4-null; null within ±20 % of G1-null (0.98) | curious 1.67; null 1.48 (+51 %) | curious part barely holds; null part already outside. By chroma_y the curious part holds strongly (×3.7 of G1 samples) and the null drifts too (×1.9). The prediction was stated on row roughness, so it will be scored on row roughness, with chroma_y next to it |
| 172 | G3 and G4 walks reach the last snapshot within 3 % of steps | G3 walks running (started 09:32) | pending |

## For review

- **chroma_y was chosen after seeing the images.** It describes; it does not test. If it should become a standing observer, it should be stated before G4's readouts land (about Tuesday). I have not changed the pipeline's statistics.
- **The Null loop is not "without intrinsic motivation" in its movement.** Its radius follows its own drive, and finding 2 shows that this alone makes it dwell on the instrument's stripes. A random-sampling control per GAN (already in "Waiting for Moe") would isolate the walk. A Null with a fixed radius would isolate the radius rule. Both are Moe's decisions.
- **The G2 latent report's taste readout** should be re-read with chroma_y (finding 3). It needs the offered tiles, which are not stored as images; it could be recomputed from the saved offer latents.
- **The quirk observer on GAN samples** (prediction 154) would turn findings 5 and 6 into measurements.
