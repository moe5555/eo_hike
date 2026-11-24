Rewritten by Claude Code at the end of every cycle. Last update: 2026-11-24, 12:55 (G1–G4 recursion and the Landsat 1 upscaler done and reported in `notes/recursion_report.md`, 169–173 scored; G5 started at 12:43 per Moe's decision of 2026-11-24; G4, the recursion readout and the Landsat 1 upscaler queued behind them, per Moe's decisions of 2026-11-17; Moe away until Wednesday 2026-11-25).

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
- **Moving in a GAN's world** (`notes/gen1_latent_report.md`): positions are latents on a sphere and the compass is 8 offers in a random plane. The step is calibrated so that a step at α_min changes a tile's colour character as much, relative to a random jump, as a real 15 km step did: α_min 19.0° (curious) and 14.0° (null).
  - **Under "snapshot as time" waiting is a short opening phase:** four kept snapshots allow three waits; both walkers took all three and reached the last snapshot by step 130 and 276 of 9,999.
  - **The radius rule behaves as on the planet:** about half the steps at α_min, a fifth to a quarter as 90° boredom jumps.

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
- **In a GAN's world** (`notes/gen1_latent_report.md`; one walk each, a hint): the curious walker chooses more textured, more banded, redder offers and avoids the black green band; the Null shows no gap. "Clear over cloud" does not carry over as a white-share preference. Interest shares at the choice stay at the real proportions (0.38 / 0.33 / 0.29).
- **What holds the walkers in a GAN's world is the instrument's line structure** (`notes/gen3_gan_report.md`, finding 2; post hoc, G1 and G2 walks):
  - tile stripes correlate with interest (ρ +0.07 to +0.30);
  - striped tiles bring close offers about twice as often, in the Null as much as in the curious walker.
  - Set by hand: the radius rule and the eyes. Emerged: that stripes are what the eyes find interesting.

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
- **Generation 2 under way** (Moe, 2026-11-16; `notes/brief_g2.md`): G2-curious trained on the G1-curious latent walk (weighted at ESS 0.5 N: τ = 2.62, max/median 69), G2-null on the G1-null latent walk (unweighted). Packages built 13:30 (render check passed), datasets 13:35, tag g2-paths. Same rules as G1, 3,840 kimg, then fresh walkers in G2. Predictions 164–168 are dated before any G2 package.
  - About 1–3 % of each G2 package comes from the earlier G1 snapshots; the rest is the 3,840 kimg world.
- **Generation 2 GANs done** (`notes/gen2_gan_report.md`; one walk, GAN and seed per condition, so hints; the era confound of the G1 packages carries through).
  - **Each G2 learned its own world much more completely** (recall 0.53 and 0.65 against G1's 0.10 and 0.18).
  - **Coverage of the real G1 package rose for curious (0.098 → 0.171) and held for null.** No collapse by the hand-set rule.
  - **The colour spread across samples narrowed by 16–38 % in both**, while the distance between neighbouring samples did not fall.
  - **Banding rose in both loops** (curious 1.66 → 1.74, null 0.98 → 1.19); the 1977 green band thinned again in both. The Null's walk itself was 18 % rougher than its GAN's samples: the radius rule acts in the Null too.
  - **Visual lead:** at the far ends, G2-curious keeps scan lines; G2-null collapses into flat yellow, black and white fields.
  - Predictions 164, 165, 167 and 168 right; 166 wrong.
- **G2 latent walks** (`notes/gen2_latent_report.md`): the curious walker almost stopped getting bored (90° jumps 4.7 % against 25 % in G1). The Null's time path is fixed by its seed.
- **Generation 3 GANs done** (`notes/gen3_gan_report.md`; hints; the era confound carries through).
  - **Chromatic scan lines grow along both loops:** G3-curious is at 3.8 × the real G1 package, G3-null at 1.9 ×. This uses chroma_y, a post-hoc statistic; the old row roughness cannot see coloured, slanted lines.
  - **The apparatus grows in the walks, not mainly in the GANs:** packages are ×1.25–2.43 stripier than the GAN they were walked in, and GANs reproduce their package (×1.00–1.16).
  - **Both walkers linger on stripes, the Null included:** after a striped tile, offers are at α_min about twice as often. The Null's choice is uniform; its radius follows its own drive.
  - **Coverage of the real package rose again in both** (recall curious 0.18, null 0.22). The loops part in spacing: curious samples closer together (×0.89), null further apart (×1.32). No collapse.
  - **G3 latent walks** (`notes/gen3_latent_report.md`):
    - the curious walker no longer lingers on stripes (ρ with interest +0.04), while the Null still does (+0.19, walk tiles ×1.47 stripier than its GAN);
    - boredom jumps fell in both (3.2 % and 11.7 %);
    - 172 right for G3.
  - **By eye:** G3-curious is striped khaki relief with red vegetation almost gone; G3-null is a varied planet again (sea, vegetation, cloud) with flat yellow and white attractors, one copied almost exactly.
- **Generation 4 GANs done** (`notes/gen4_gan_report.md`; hints; era confound carries through).
  - **No collapse after four generations.** Recall against the real package stays above G1's in both loops.
  - **The null loop drifted:** its precision against the real package halved (0.53 → 0.24), down to the curious loop's level, which never moved (0.24–0.26). Colour spread narrowed in both, at every generation.
  - **Chromatic scan lines at G4:** 4.4 × the real package (curious) and 3.0 × (null). The curious walk stopped adding them after G3; the null walk did not.
  - **Predictions:** 169 wrong, 170 right, 171 wrong (null part); 172 right (`notes/gen4_latent_report.md`).
  - **G4 latent walks:** the Null walker too stopped lingering on stripes (one generation after curious). Neither walk now adds stripes; boredom jumps are down to a few per cent in both.
  - **The recursion as a whole** (`notes/recursion_report.md`): no collapse; the instrument's scan lines are what the recursion amplifies, mostly in the walks through the radius rule and in both walkers; the curious weighting accelerates but does not decide the direction.
  - **The Landsat 1 upscaler:** +5.4 dB median PSNR over bicubic on held-out cells. It sharpens the scan lines a sample has and does not invent them. Prediction 173 right.
  - **G5 started** (Moe, 2026-11-24, "G5 at the same rules"). Packages tagged `g5-paths` at 12:45. Predictions 174–178 were dated before.
  - **By eye:** G4-curious is grey-khaki under fine multicoloured scan lines, with a recurring teal lake with a red rim; G4-null is still more varied, but much stripier than G3-null.

# Decisions taken since the last update, and why
- **Moe, 2026-11-14:**
  - latent walks in G1: fresh walkers with the same config, z-sphere calibrated, snapshot as time, queued to start on their own;
  - the step observer is colour character, not pixel layout.
- **Moe, 2026-11-16:** generation 2 only, then stop; 3,840 kimg; same rules as G1; "snapshot as time" in every generation.
- **Moe, 2026-11-24:** G5 at the same rules (a latent walk plus GAN training once more), queued after the upscaler.
- **Moe, 2026-11-17:** G3 and G4 at the same rules; the calibration keeps the real 15 km reference; the time rule stays; the Landsat 1 upscaler after the last generation; then stop for review (`notes/brief_g2.md`, extension).
- **Mine, within the run instruction:**
  - **The supervisor's job liveness was fixed** after a reused Windows pid killed one chunk (2026-11-14 19:14; resumed from its snapshot, no kimg lost).
  - **G2 inherits G1's measured budget and training mode** instead of re-measuring them: same architecture, size and GPU.
  - **The G2 package render check accepts at most 2 of 255 difference:** the walk rendered offers in batches, so re-rendering one at a time differs in the last bit.
  - **Faithful enlargement** is integer nearest neighbour; Lanczos is labelled display-only; no learned super-resolution (`notes/upscaling.md`).
  - **chroma_y added next to row roughness, post hoc (2026-11-21):** the old statistic was blind to what the images show. Predictions stated on row roughness are still scored on it.

# Waiting for Moe
- **The quirk observer on GAN samples** (prediction 154; findings 4–5 of the GAN report would be tested by it).
- **A random-sampling control for the Null loop?** The Null's latent walk is not a neutral sample of its GAN (G2 report, finding 4). G3 shows why: its radius follows its drive, and it lingers on stripes. Sampling each GAN at random would separate the walk's effect from the GAN's; a fixed-radius Null would isolate the radius rule.
- **chroma_y as a standing observer?** It was chosen after seeing the images. It should be stated before the G4 readouts (about Tuesday) if it is to count.
- **After G4:** whether to continue the recursion, and what the collapse flag (prediction 170) should be if this one is too strict or too loose.
- **Whether waiting matters enough to revisit q** for later generations of real walks.
- **The long phase** (predictions 140–142): finish or drop.
- **Snapshot as time beyond G2:** with four kept snapshots, waiting is over within the first 3 % of a latent walk. More snapshots, or another rule, if time should matter later.

# Backlog, in order
1. **G5** (Moe, 2026-11-24) runs unattended: training until about Thursday 2026-11-26 21:00, then FID, readouts and latent walks (about Friday 01:00), then the recursion readout over G1–G5 and `final`. Reports due: the G5 GAN and latent reports (174–178) and an addendum to the recursion report.
2. **The near-copy** at G1-curious seed 411.
3. **Open checks of the research note:** the missing ~14k items, the L1GS offset distribution, impulse noise, 6-bit combs.

# Next milestone and its risk
- **The extended run ends** about Tuesday 2026-11-24 afternoon: G5 about Friday 2026-11-27 early morning (training about 55 h from 12:50 on 2026-11-24, then readouts and walks).
- **Risks:**
  - The recursion readout and the upscaler stages have run only at test size.
  - Monitoring depends on this Claude session; the pipeline itself restarts on boot, at logon and every 15 minutes.
  - One path, one seed per condition: every comparison across generations is a hint.
