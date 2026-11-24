# Latent walks in generation 2: the curious walker in G2-curious against the Null walker in G2-null — report (2026-11-19)

*Same walkers, configs and rules as in G1 (`notes/gen1_latent_report.md`; Moe, 2026-11-16 and 2026-11-17): z-sphere, the step calibrated by colour character against the real G1 15 km reference, snapshot as time with q = 0.10. Code: `agent/latent_walk.py`, `analysis/gen1/latent_readouts.py`, `analysis/gen1/latent_taste_ci.py --gen 2`. Tables and figures: `notes/gen2/latent/`. Runs: `runs/g2/latent/<cond>/` (outside git). Both walks ran 2026-11-18 21:57 to 2026-11-19 00:59 on the PC, side by side. These tiles are now G3's training sets (`paths/g3/<cond>/`, tag `g3-paths`).*

## Short version

- **Both walks reached N = 10,000 tiles in 9,999 steps** (about 3.0 h each), with no crash.
- **Calibration:** α_min = 16.7° (curious) and 14.1° (Null), against 19.0° and 14.0° in G1. ρ is the real G1 reference (0.33 and 0.22), as decided.
- **Time is used up at once again.** Both walkers took all three waits and reached the 3,840 kimg snapshot at step 244 (curious) and 276 (Null). 97.5 % and 97.2 % of their steps are in the final world.
- **The curious walker almost stopped getting bored:**
  - 4.7 % of its steps are 90° jumps, against 25.3 % in G1. The Null's share barely moved (18.0 % against 20.6 %).
  - It spends 44.5 % of its steps at α_min (G1: 53.5 %).
- **Its taste turned around** (colour and texture statistics; chosen minus offered per step):
  - In G1 it chose more textured, more banded offers (gradient +0.89, row roughness +0.042).
  - In G2 it chooses slightly less textured and less banded ones (−0.18 and −0.022), plus more green band (+1.28) and less black (−0.0008).
  - All the gaps are tiny, at most 0.07 of the offered spread.
- **The Null shows a brightness "gap" whose interval clears zero** (+0.52, 0.05 to 0.99). The Null chooses uniformly, so this is a warning that the step bootstrap is too narrow: steps in a walk are autocorrelated. Every interval in both latent reports should be read with that in mind.
- **Interest at the choice keeps its proportions** (curious: glance 0.38, grid 0.33, progress 0.29).
- **The Null's time path is the same as in G1, step for step** (finding 3). It is set by its seed, not by its world.

## Tables

`walks.csv`, `snapshots.csv`, `taste.csv`, `taste_ci.csv` and `waits_vs_moves.csv` are in `notes/gen2/latent/`. G1 values are from `notes/gen1/latent/`.

| | curious G1 | curious G2 | Null G1 | Null G2 |
|---|---|---|---|---|
| α_min (colour) | 19.0° | 16.7° | 14.0° | 14.1° |
| steps at α_min / at 90° | 53.5 % / 25.3 % | 44.5 % / 4.7 % | 53.6 % / 20.6 % | 49.5 % / 18.0 % |
| median angle 10 steps apart | 60.6° | 63.5° | 51.1° | 58.1° |
| first step at 3,840 kimg | 130 | 244 | 276 | 276 |
| waits / time offers that came through | 3 / 11 | 3 / 24 | 3 / 28 | 3 / 28 |
| mean p of the chosen offer / best offer taken | 0.49 / 61 % | 0.48 / 60 % | 0.125 / 12 % | 0.125 / 12 % |
| interest shares glance / grid / progress | 0.377 / 0.332 / 0.291 | 0.380 / 0.334 / 0.286 | 0.366 / 0.340 / 0.294 | 0.356 / 0.327 / 0.317 |

**Taste: chosen minus offered, compass offers, per step** (`taste_ci.csv`; bootstrap 95 % interval over steps, which is too narrow, see above):

| statistic | curious G1 | curious G2 (interval) | Null G2 (interval) |
|---|---|---|---|
| brightness | +1.84 | +0.25 (0.09 to 0.41) | +0.52 (0.05 to 0.99) |
| black share | −0.0005 | −0.0008 (−0.0012 to −0.0005) | +0.0001 (−0.0000 to 0.0002) |
| green band dark | −0.0033 | −0.0006 (−0.0009 to −0.0003) | +0.0002 (−0.0006 to 0.0009) |
| mean of the red band (G channel) | +3.35 | −0.26 (−0.47 to −0.03) | +0.60 (0.09 to 1.10) |
| mean of the green band (B channel) | – | +1.28 (1.06 to 1.51) | +0.45 (−0.01 to 0.91) |
| gradient (texture) | +0.89 | −0.18 (−0.29 to −0.07) | −0.06 (−0.14 to 0.01) |
| row roughness (banding) | +0.042 | −0.022 (−0.032 to −0.012) | −0.005 (−0.015 to 0.004) |

## Findings

One walk per condition in one GAN per condition, in worlds that inherit the era confound of the G1 packages: hints.

1. **The curious walker stays interested in G2-curious.**
   - Boredom jumps (90°) fell from a quarter of its steps to one in twenty. The Null, which uses the same radius rule, hardly changed.
   - The radius follows the drive: the short average of interest against the long one. Fewer jumps mean the drive rarely fell far below its own long average.
   - A candidate reading, not tested: G2-curious varies more within a short distance (finding 2 of the G2 GAN report: narrower colour spread, but samples as far apart as in G1), so interest keeps refreshing.
   - Set by hand: the radius rule, the drive settings, α_min from the calibration. Emerged: the jump share.
   - *RQ2/RQ3; ch. 7.*
2. **The curious walker's taste flipped sign in G2.**
   - In G1 it chose texture and banding. In G2-curious, where banding is already everywhere (row roughness of samples 1.74), it chooses slightly less of both, and more green band.
   - The gaps are tiny (≤ 0.07 of the spread). With the step bootstrap too narrow, they are at most a hint that novelty works relative to what the world already holds.
   - *RQ2/RQ3; ch. 6, 8.*
3. **Under snapshot as time, waiting stays a short opening phase.** It is the same as in G1, and prediction 172 expects the same in G3 and G4.
   - The Null's time path is identical in G1 and G2: it reached 1,920, 2,880 and 3,840 kimg at steps 27, 244 and 276 both times, with the same 28 time offers.
   - Its choice is uniform and seeded, so its draws do not depend on the world, and its time follows from the seed and q alone. The Null's "when" in every generation is a premise, not a result.
   - *RQ1/RQ3; ch. 5, 7.*
4. **The step bootstrap is too narrow** (the Null's brightness and red-band intervals clear zero although its choice is uniform).
   - A block bootstrap over runs of steps, or a comparison against the Null's gap, would be honest.
   - Until then the taste intervals in both latent reports describe a walk only loosely.
   - *Method; ch. 8.*

## Against the predictions

- 168 (α_min within 30 % of G1) was scored right in `notes/gen2_gan_report.md`.
- No other prediction was stated for the G2 latent walks. 172 (time in G3 and G4) is consistent with G2 so far.

## For review

- **A block bootstrap for the taste intervals** (finding 4), for all latent reports. It changes no data, only the intervals. I'll add it when the recursion report is written unless Moe says otherwise.
- **The collapse of boredom in the curious loop** (finding 1) is worth watching in G3: if it holds, the curious G3 package will be even more locally correlated.

## Correction (2026-11-24): the step bootstrap was not too narrow

nalysis/recursion/taste_block_ci.py (
otes/recursion/taste_block_ci.csv) resampled the per-step gaps in moving blocks of 50 and 200 steps for G1–G4.

- **The gaps are nearly independent:** the median lag-1 autocorrelation is about 0.
- **The block intervals are no wider than the iid ones:** median width ratio ×0.99 for the Null and ×1.2 for curious.
- **The Null's intervals clear zero in 4–5 of 36 statistic × generation cells.** These are mostly one correlated cluster (brightness and channel means in G2). At 95 % that is about what chance gives, so it does not show the bootstrap was too narrow.
- **The curious walker's gaps clear zero in 22–23 of 36 cells under every scheme.** Its taste is small but stable within each walk.

The claim above that the step bootstrap is too narrow is withdrawn. The intervals in this report stand. They still describe one walk, not walks in general.
