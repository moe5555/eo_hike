# GAN generation 4: G4-curious (weighted) against G4-null (unweighted) — report (2026-11-23)

*Brief: `notes/brief_g2.md` and its extension (Moe, 2026-11-17: G3 and G4 at the same rules, 3,840 kimg). Predictions 169–173: `notes/06_characters/expectations.md`, dated 2026-11-17. Inputs: the G3 latent walks (`notes/gen3_latent_report.md`), packaged at tag `g4-paths`. Code: `gen/g1_gan.py --gen 4`, `analysis/recursion/readouts.py`, `analysis/recursion/chroma_stripes.py` (post hoc, see `notes/gen3_gan_report.md`). Outputs: `runs/g4/gan/` (outside git), `notes/gen4/gan/`, `notes/recursion/chroma_stripes.csv`. Device: the PC (Quadro RTX 5000), in the scheduled pipeline. This is the last GAN generation of the run; 169–171 are scored here. 172 waits for the G4 walks and 173 for the upscaler; both go into the recursion report.*

## Short version

- **Both GANs trained to 3,840 kimg** from 2026-11-21 12:48 to 2026-11-23 20:05 (55.3 h). There were no restarts.
  - FID against each run's own training set: curious 29.8 → 7.3, null 27.4 → 9.7. This is a training-health signal only.
- **Coverage of the real G1 package fell for the first time in curious and rose again in null.**
  - Recall: curious 0.182 → 0.151, null 0.219 → 0.249.
  - No collapse by the hand-set rule.
- **The null loop has drifted as far from the real package by precision as the curious one.** Null precision fell at every generation (0.53 → 0.42 → 0.32 → 0.24) and now sits beside curious (0.26), which never moved.
- **Chromatic scan lines kept growing in both loops:** G4-curious samples are at 4.4 × the real package, G4-null at 3.0 × (chroma_y, post hoc).
  - The curious walk no longer added stripes (×1.01); the null walk did (×1.46).
  - The GANs now add a little in both (×1.14 and ×1.10).
- **Predictions:** 169 wrong; 170 right; 171 wrong (its null part).
- **Memorisation:** G4-null again copies a flat saturated yellow field almost exactly (distance 0.03, the third generation running). G4-curious has no near-copies.
- **Every comparison here is one walk, one GAN and one seed per condition per generation, so these are hints.** The era confound of the G1 packages carries through: G1-curious and G1-null were trained on paths from different parts of the mission, and every later generation inherits that difference.

## What was run

- **Packages (`paths/g4/<cond>/`):** the 10,000 tiles of each G3 latent walk, rendered by the walker. The render check passed (≤ 2 of 255). Nothing was repaired.
- **Weights (curious):** e = exp(I / τ), unchanged. τ was solved for ESS = 0.5 N: **τ = 2.243** (G3: 2.349, G2: 2.617). The top 1 % hold 0.063 of the weight and the top 10 % hold 0.254. Max/median is 67.6. Null: weight 1.
- **Training:** G1's settings and budget, inherited. 3,840 kimg each, with kept snapshots at 960, 1,920, 2,880 and 3,840; 25.5 s/kimg.
- **After training (pipeline):** FID on the kept snapshots; 5,000 samples per GAN (ψ = 1); memorisation and precision/recall at 32 px; colour and texture statistics.
- **Added for this report:**
  - the recursion readout on G1–G4 (`notes/gen4/gan/cross_generation_g1_g4.csv`; the pipeline's `recursion_readouts` stage reruns it);
  - chroma_y on all sets;
  - the same 10 seeds rendered from each generation's 3,840 kimg snapshot (`<cond>_same_seeds_g1_to_g4.png`);
  - far ends at ψ = 1–3 (`<cond>_far_ends_psi1-3.png`).

### Set by hand, and left to emerge

| Set by hand (premises) | Left to emerge |
|---|---|
| the G3 latent walks as packages (walker configs, z-sphere, the colour-calibrated step against the real 15 km reference, snapshot as time, q = 0.10) | what each package contains |
| N = 10,000; ESS = 0.5 N; e = exp(I / τ) | τ and the weight concentration |
| 3,840 kimg, G1's training settings, seed 0, four generations | ADA p, FID, the samples |
| the observers: 32 px pixel space, k = 3; colour and texture statistics; chroma_y (post hoc); the collapse rule (prediction 170) | coverage, spread, the apparatus statistics |
| the radius rule, in both walkers | where each walk lingered, and on what |

## Tables

**Coverage and spread across the four generations** (`cross_generation_g1_g4.csv`; 5,000 samples each, ψ = 1):

| | G1-cur | G2-cur | G3-cur | G4-cur | G1-null | G2-null | G3-null | G4-null |
|---|---|---|---|---|---|---|---|---|
| final ADA p | 0.161 | 0.124 | 0.145 | 0.167 | 0.141 | 0.097 | 0.109 | 0.121 |
| FID at 3,840 (own set; health only) | 17.8 | 8.4 | 7.9 | 7.3 | 23.2 | 7.7 | 7.5 | 9.7 |
| precision / recall, own set | 0.24 / 0.10 | 0.74 / 0.53 | 0.78 / 0.61 | 0.75 / 0.60 | 0.53 / 0.18 | 0.76 / 0.65 | 0.79 / 0.80 | 0.83 / 0.83 |
| precision, real G1 package | 0.240 | 0.235 | 0.254 | 0.258 | 0.526 | 0.423 | 0.324 | 0.241 |
| recall, real G1 package | 0.098 | 0.171 | 0.182 | 0.151 | 0.178 | 0.180 | 0.219 | 0.249 |
| recall ÷ G1's | 1.00 | 1.75 | 1.86 | 1.55 | 1.00 | 1.01 | 1.23 | 1.40 |
| nearest-sample distance ÷ G1's | 1.00 | 1.00 | 0.89 | 0.90 | 1.00 | 1.12 | 1.32 | 1.36 |
| SD of brightness across samples | 22.3 | 13.7 | 12.0 | 11.9 | 48.0 | 39.8 | 36.6 | 31.6 |
| SD of NIR / red / green-band means | 23.9 / 27.2 / 27.0 | 16.5 / 20.0 / 22.3 | 13.1 / 16.7 / 19.7 | 12.3 / 17.0 / 17.8 | 48.1 / 50.3 / 49.2 | 39.6 / 42.3 / 41.1 | 37.8 / 40.5 / 38.9 | 33.6 / 35.7 / 34.2 |
| collapse flag | – | no | no | no | – | no | no | no |

**Chromatic stripes along the whole loop** (chroma_y; factor against the previous set in brackets; `chroma_stripes.csv`, n = 2,000 per set):

| set | curious | null |
|---|---|---|
| real G1 package | 3.66 | 2.88 |
| G1 samples | 3.75 (×1.03) | 2.84 (×0.98) |
| G2 package (G1 walk) | 9.12 (×2.43) | 3.53 (×1.25) |
| G2 samples | 9.60 (×1.05) | 3.52 (×1.00) |
| G3 package (G2 walk) | 12.02 (×1.25) | 5.29 (×1.50) |
| G3 samples | 13.93 (×1.16) | 5.35 (×1.01) |
| G4 package (G3 walk) | 14.08 (×1.01) | 7.81 (×1.46) |
| G4 samples | 16.09 (×1.14) | 8.59 (×1.10) |
| G4 samples ÷ real package | **×4.40** | **×2.98** |

**The apparatus: G3 samples → G4 package → G4 samples** (colour and texture statistics; `colour_texture.csv`):

| statistic | G3-cur samples | G4-cur package (unw. / weighted) | G4-cur samples | G3-null samples | G4-null package | G4-null samples |
|---|---|---|---|---|---|---|
| row roughness (old banding statistic) | 1.667 | 1.656 / 1.719 | 1.737 | 1.483 | 1.582 | 1.599 |
| chroma_y (post hoc) | 13.93 | 14.08 / – | 16.09 | 5.35 | 7.81 | 8.59 |
| green band dark (image share) | 0.0018 | 0.0001 / 0.0003 | 0.0002 | 0.0040 | 0.0016 | 0.0032 |
| black share | 0.0028 | 0.0033 / 0.0034 | 0.0034 | 0.0007 | 0.0009 | 0.0006 |
| white share | 0.0099 | 0.0103 / 0.0151 | 0.0165 | 0.0104 | 0.0059 | 0.0085 |
| gradient x / y | 7.29 / 12.63 | 6.90 / 12.35 | 7.44 / 13.73 | 6.04 / 7.50 | 6.55 / 8.81 | 6.46 / 8.95 |

**Memorisation** (32 px):

| | G3-curious | G4-curious | G3-null | G4-null |
|---|---|---|---|---|
| median sample→train ÷ median train→train | 1.24 | 1.29 | 1.27 | 1.27 |
| samples below the training set's p1 | 0.0 % | 0.0 % | 0.5 % | 0.34 % |
| closest pair | 1.31 | 1.23 | 0.05 (flat saturated yellow) | 0.03 (flat saturated yellow, `k037592_s3840`, `k029652_s3840`) |
| samples nearer the heaviest 10 % than the lightest | 48.5 % | 49.0 % | – | – |

## Findings

1. **Four generations, no collapse, two kinds of drift.**
   - Neither loop meets the hand-set collapse rule. Recall against the real package stays above G1's in both (curious ×1.55, null ×1.40), and samples did not crowd together.
   - Both loops narrowed in colour at every generation. The brightness SD fell to 53 % (curious) and 66 % (null) of G1's.
   - The null loop drifted in a way the curious one did not: its precision against the real package halved (0.53 → 0.24). By G4 its samples are no closer to the planet's neighbourhoods than curious ones.
   - The curious loop's precision never moved (0.24–0.26). Its first generation was already as far from the package as it would go.
   - Set by hand: the observers and the collapse rule. Emerged: the trajectories.
   - *RQ3; ch. 8.*
2. **The instrument's line structure is what the recursion amplifies, in both loops.**
   - chroma_y rose at every generation, to 4.4 × the real package (curious) and 3.0 × (null).
   - The curious loop's walk stopped adding stripes after G3 (×1.01), as the G3 latent report expected. The null walk kept adding them (×1.46).
   - In G4 both GANs added some (×1.14, ×1.10), where earlier GANs had mostly reproduced their package.
   - Read with the G3 reports: in this setup, it is the radius rule plus eyes grown from random weights that turn the scan line into a destination. Novelty weighting is not needed for that; it only gets there sooner.
   - Set by hand: the radius rule, the eyes, chroma_y. Emerged: the rise and where it happens.
   - *RQ2/RQ3; ch. 6, 7, 8.*
3. **By eye** (`<cond>_same_seeds_g1_to_g4.png`, contact sheets, far ends; visual, not measured):
   - **G4-curious:** grey-khaki ground under fine multicoloured scan lines on most samples. A recurring new motif is a teal lake with a red rim. Lime and yellow fields and black streaks continue; red vegetation is nearly absent.
   - **G4-null:** still the more varied world, with relief, cloud, red vegetation and some sea. But stripes now cover a much larger share than in G3, often red lines over red vegetation.
   - The flat saturated yellow field appears several times in 256 samples and is a near-exact copy of a training tile, for the third generation.
   - *RQ3; ch. 8, 9 (film).*
4. **The 1977 green band is gone from the curious loop.** Its unweighted package holds 0.01 % and its samples 0.02 %. The null loop keeps it at about its G1 share (0.32 %).
   - *RQ2/RQ3; ch. 6.*
5. **Coverage numbers and the eye disagree.** Recall against the real package rose in null while its precision fell and its samples became visibly stripier.
   - Recall in 32 px pixel space counts real tiles inside the samples' neighbourhoods. It is not a measure of being more planet-like, as the G2 report cautioned. A pretrained-feature or quirk observer would be needed before reading it either way.
   - *Method; ch. 8.*

## Against the predictions (169–171; scored on G4)

| # | predicted | measured | verdict |
|---|---|---|---|
| 169 | recall against the real G1 package lower in G4 than G2 and in G2 than G1, both conditions; curious loses faster | curious 0.098 → 0.171 → 0.151; null 0.178 → 0.180 → 0.249 | **wrong**: G2 > G1 in both; null G4 > G2; only curious G4 < G2 |
| 170 | neither loop meets the collapse rule (recall < 0.5 × G1 and nearest-sample distance < 0.7 × G1) by G4 | curious ×1.55 and ×0.90; null ×1.40 and ×1.36 | **right** (low confidence was stated; the rule was never close) |
| 171 | G4-curious row roughness above G1-curious (1.66) and above G4-null; G4-null within ±20 % of G1-null (0.98) | G4-curious 1.737; G4-null 1.599 (+63 %) | **wrong**: the curious part holds, the null part fails. By chroma_y (post hoc, not the stated measure) the same pattern is much stronger: curious ×4.3 of G1 samples, null ×3.0 |

**Why the misses:**
- **169** assumed recursion would forget the planet. Measured by recall in pixel space, it does not. Each GAN learns its own world better than G1 learned the planet, and recall rewards that spread.
- **171** assumed the Null walk would be a neutral sampler. It is not: its radius follows its drive, and it lingers on stripes. This was the G2 report's warning, and the G3 reports measured it.

## For review

- **The Null loop is not "a recursive loop without intrinsic motivation" in its movement** (finding 2). It reaches the instrument too, only later. A Null with a fixed radius, or random sampling of each GAN, would be the clean control. This is Moe's decision.
- **chroma_y as a standing observer** (post hoc since G3).
- **The quirk observer on GAN samples** (prediction 154) would test findings 2–4.
- **The recursion report** follows after the G4 walks (172) and the upscaler (173).
