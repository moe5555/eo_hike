Rewritten by Claude Code at the end of every cycle. Last update: 2026-11-16, 10:40 (generation 1 GANs trained and reported; the G1 latent walks running; generation 2 queued behind them, per Moe's decision of 2026-11-16).

# Where we are, in thesis terms
## RQ1:
How do practices of moving without a predetermined destination, like wayfaring or the dérive, translate to an untasked, step-wise traversal of the planetary image, already cut into scenes, scan lines and tiles?

- **The world** is the archive of one instrument, Landsat 1 (1972–78), with every acquisition of every cell, one product per date. It was rebuilt on the PC and proven identical to the Mac's world (`runs/g1/world_check.md`).
- **The archive shapes the traversal:**
  - from mid-1974, only ~422,000 of 1.47 M cells are ever imaged again;
  - there is a winter gap from November 1976 to January 1977;
  - from April 1977 the green band is uncalibrated.
- **Under the thinned time offer (q = 0.10) the wanderers became movers** (`notes/gen1_report.md`): waits were 0.3 % of steps. Both walkers' clocks crossed the mission at the same pace, and each walk ended by `linger`.
- **"Far from its own time" is the archive,** not the walker: the closest-acquisition rule meets the coverage collapse after mid-1974. Curious and Null are alike.
- **Moving in a GAN's world** (the G1 latent walks, running): positions are latents on a sphere and the compass is 8 offers in a random plane. The step is calibrated so that a step at α_min changes a tile's colour character as much, relative to a random jump, as a real 15 km step did. On the final G1 snapshots α_min is 19.0° for curious and 14.0° for null. Waiting means the next kept training snapshot ("snapshot as time", Moe).

## RQ2:
Which paths do algorithms driven by novelty, learning progress and boredom cut through the computational planetary image, and how much of their attention follows the terrain, how much the idiosyncrasies of their perception, and how much the artefacts of the instrument, where data and phenomenon come apart?

- **Generation 1:** three walks per condition; hints, not leads (`notes/gen1_report.md`).
  - **Clear over cloud** is the most consistent hint: curious choices have cloud 0.155 against 0.214 offered; the Null shows no gap.
  - **Waits for learning:** at curious waits the progress z is 0.91, against 0.41 at moves.
  - **The curious walker revisits less** and covers more cells per step.
  - **Interest at the choice:** glance 0.38, grid 0.35, progress 0.26.
- **What the weighting picks** (`notes/gen1_gan_report.md`):
  - The heaviest 64 tiles are an apparatus-heavy tail: more striped and cloudier, with fill ×4, night ×4 and more saturation flags.
  - The broader top 10 % is clear, slightly darker and striped.

## RQ3:
What do GANs trained recursively on these paths construct, and do their worlds drift across generations towards the planet or towards the apparatus, depending on whether paths are curated by whole places or by fragments, compared with a recursive loop without intrinsic motivation?

- **Generation 1 GANs done** (`notes/gen1_gan_report.md`): 3,840 kimg each, healthy and not yet converged (FID curious 17.8, null 23.2, each against its own set).
  - **G1-curious covers its world less** than G1-null: recall 0.096 against 0.182 in 32 px space. The weighting does not explain the gap; the curious package is rougher and more varied within the tile.
  - **The apparatus survives selectively:**
    - banding along rows is kept or amplified;
    - fill and the black green band of 1977 are smoothed away (0.30 × and 0.11 × their training share);
    - curious keeps about 3 × more of the band than null does.
  - **Visual leads, not measured:** the extremes and some latent regions of curious run to flat band-yellow and scan-line texture; those of null run to fill-like black bars and magenta striping.
  - One path and one seed per condition; the era confound is small.
- **Generation 2 queued** (Moe, 2026-11-16; `notes/brief_g2.md`): G2-curious trained on the G1-curious latent walk (weighted at ESS 0.5 N), G2-null on the G1-null latent walk (unweighted). Same rules as G1, 3,840 kimg, then fresh walkers in G2, then a stop for review. Predictions 164–168 are dated before any G2 package.

# Decisions taken since the last update, and why
- **Moe, 2026-11-14:**
  - latent walks in G1: fresh walkers with the same config, z-sphere calibrated, snapshot as time, queued to start on their own;
  - the step observer is colour character, not pixel layout.
- **Moe, 2026-11-16:** generation 2 only, then stop; 3,840 kimg; same rules as G1; "snapshot as time" in every generation.
- **Mine, within the run instruction:**
  - **The supervisor's job liveness was fixed** after a reused Windows pid killed one chunk (2026-11-14 19:14; resumed from its snapshot, no kimg lost).
  - **G2 inherits G1's measured budget and training mode** instead of re-measuring them: same architecture, size and GPU.
  - **The G2 package render check accepts at most 2 of 255 difference:** the walk rendered offers in batches, so re-rendering one at a time differs in the last bit.
  - **Faithful enlargement** is integer nearest neighbour; Lanczos is labelled display-only; no learned super-resolution (`notes/upscaling.md`).

# Waiting for Moe
- **The quirk observer on GAN samples** (prediction 154; findings 4–5 of the GAN report would be tested by it).
- **After G2:** whether to continue to G3, and whether later generations keep the real 15 km step reference for the calibration.
- **Whether waiting matters enough to revisit q** for later generations of real walks.
- **The long phase** (predictions 140–142): finish or drop.

# Backlog, in order
1. **G1 latent walks** (running, about 2 h), then their readouts and report (predictions 158–163). Prediction 158 can already be scored: α_min 19.0° and 14.0° against a predicted 2–15° with curious smaller, so wrong.
2. **Generation 2** runs unattended, then the G2 GAN report (predictions 164–168) and the G2 latent walk readouts.
3. **The near-copy** at curious seed 411; a cross-sample spread readout for prediction 165 (the 5,000 G1 samples are saved).
4. **Open checks of the research note:** the missing ~14k items, the L1GS offset distribution, impulse noise, 6-bit combs.

# Next milestone and its risk
- **G2 finishes** around Thursday 2026-11-19 morning: 2 h of latent walks, about 57 h of training, about 2 h of FID and readouts, and 2 h of G2 latent walks.
- **Risks:**
  - The G2 stages were tested on test walks only (packages, datasets, 1 kimg of training), not end to end at full size.
  - One path, one seed per condition: every comparison across generations is a hint.
