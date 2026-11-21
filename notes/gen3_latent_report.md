# Latent walks in generation 3: the curious walker in G3-curious against the Null walker in G3-null — report (2026-11-21)

*Same walkers, configs and rules as in G1 and G2 (`notes/gen1_latent_report.md`, `notes/gen2_latent_report.md`; Moe, 2026-11-16 and 2026-11-17): z-sphere, the step calibrated by colour character against the real G1 15 km reference, snapshot as time with q = 0.10. Code: `agent/latent_walk.py`, `analysis/gen1/latent_readouts.py`, `analysis/gen1/latent_taste_ci.py --gen 3`, `analysis/recursion/stripes_in_walks.py` (post hoc, see `notes/gen3_gan_report.md`). Tables and figures: `notes/gen3/latent/`, `notes/recursion/stripes_in_walks.csv`. Runs: `runs/g3/latent/<cond>/` (outside git). Both walks ran 2026-11-21 09:32 to 12:34 on the PC, side by side. Their tiles are G4's training sets (`paths/g4/<cond>/`, being built).*

## Short version

- **Both walks reached N = 10,000 tiles in 9,999 steps** (3.0 h each), with no crash.
- **Calibration:** α_min = 16.3° (curious) and 13.3° (Null), against 16.7° and 14.1° in G2 and 19.0° and 14.0° in G1. ρ is the real G1 reference, as decided.
- **Time is used up at once, as in G1 and G2** (prediction 172: right for G3). Both walkers took all three waits and reached the 3,840 kimg snapshot at step 244 (curious, 2.4 % of steps) and 276 (Null, 2.8 %).
  - The Null's time path is the same as in G1 and G2 for the third time: steps 27, 244 and 276.
- **Boredom keeps falling, now in the Null too:**
  - 90° jumps are 3.2 % of curious steps (G2 4.7 %, G1 25.3 %) and 11.7 % of the Null's (G2 18.0 %, G1 20.6 %).
  - The share of steps at α_min hardly moved (45.6 % and 48.8 %).
- **The curious walker no longer lingers on stripes; the Null still does** (post hoc, chroma_y):
  - In G3-curious the link between a tile's stripes and the walker's interest or next radius has gone (ρ +0.04 and +0.00; G1: +0.19 and −0.29).
  - The Null keeps it (ρ +0.19 and −0.25).
  - So the curious walk's tiles are no stripier than its GAN's samples (×0.99), while the Null's are ×1.47 stripier.
- **Taste: tiny gaps, as in G2.** The largest is the curious walker choosing slightly more green band (B channel +0.66, 0.04 of the offered spread) and no dark green band at all. The Null shows no gap.
  - The step bootstrap is too narrow (G2 report, finding 4); read the intervals loosely.
- **Interest at the choice keeps its proportions** (curious: glance 0.38, grid 0.36, progress 0.26).

## Tables

`walks.csv`, `snapshots.csv`, `taste.csv`, `taste_ci.csv` and `waits_vs_moves.csv` are in `notes/gen3/latent/`.

| | curious G1 | curious G2 | curious G3 | Null G1 | Null G2 | Null G3 |
|---|---|---|---|---|---|---|
| α_min (colour) | 19.0° | 16.7° | 16.3° | 14.0° | 14.1° | 13.3° |
| steps at α_min / at 90° | 53.5 % / 25.3 % | 44.5 % / 4.7 % | 45.6 % / 3.2 % | 53.6 % / 20.6 % | 49.5 % / 18.0 % | 48.8 % / 11.7 % |
| median angle 10 steps apart | 60.6° | 63.5° | 62.3° | 51.1° | 58.1° | 55.2° |
| steps reaching 1,920 / 2,880 / 3,840 kimg | – / – / 130 | 52 / 197 / 244 | 27 / 193 / 244 | 27 / 244 / 276 | 27 / 244 / 276 | 27 / 244 / 276 |
| waits / time offers that came through | 3 / 11 | 3 / 24 | 3 / 24 | 3 / 28 | 3 / 28 | 3 / 28 |
| mean p of the chosen offer / best offer taken | 0.49 / 61 % | 0.48 / 60 % | 0.46 / 59 % | 0.125 / 12 % | 0.125 / 12 % | 0.125 / 13 % |
| interest shares glance / grid / progress | 0.377 / 0.332 / 0.291 | 0.380 / 0.334 / 0.286 | 0.377 / 0.359 / 0.264 | 0.366 / 0.340 / 0.294 | 0.356 / 0.327 / 0.317 | 0.346 / 0.331 / 0.324 |

**Stripes in the walks** (`stripes_in_walks.csv`; chroma_y of the tile the walker stands on, against its interest I and the radius α of the next offers; Spearman; steps are autocorrelated, so these describe and do not test):

| walk | ρ(chroma_y, I) | ρ(chroma_y, next α) | next offers at α_min: most / least striped fifth | next at 90°: most / least striped fifth | walk tiles' chroma_y ÷ its GAN's samples |
|---|---|---|---|---|---|
| G1 curious | +0.19 | −0.29 | 67 % / 33 % | 12 % / 41 % | ×2.32 |
| G2 curious | +0.07 | −0.11 | 55 % / 36 % | 4 % / 6 % | ×1.23 |
| G3 curious | +0.04 | +0.00 | 47 % / 46 % | 3 % / 3 % | ×0.99 |
| G1 Null | +0.23 | −0.21 | 68 % / 39 % | 14 % / 30 % | ×1.24 |
| G2 Null | +0.30 | −0.26 | 70 % / 34 % | 8 % / 26 % | ×1.46 |
| G3 Null | +0.19 | −0.25 | 62 % / 37 % | 5 % / 18 % | ×1.47 |

(The last column uses all 10,000 walk tiles against 2,000 samples of the GAN walked in; the GAN report's package figures use 2,000 package tiles, so they differ slightly.)

**Taste: chosen minus offered, compass offers, per step** (`taste_ci.csv`; bootstrap 95 % interval over steps, too narrow):

| statistic | curious G2 | curious G3 (interval) | Null G3 (interval) |
|---|---|---|---|
| brightness | +0.25 | +0.22 (0.07 to 0.37) | +0.09 (−0.31 to 0.49) |
| green band dark | −0.0006 | −0.0002 (−0.0004 to 0.0000) | −0.0002 (−0.0009 to 0.0005) |
| mean of the green band (B channel) | +1.28 | +0.66 (0.45 to 0.86) | −0.09 (−0.48 to 0.33) |
| gradient (texture) | −0.18 | −0.11 (−0.23 to 0.02) | +0.04 (−0.03 to 0.12) |
| row roughness (old banding statistic) | −0.022 | −0.005 (−0.015 to 0.005) | +0.007 (−0.004 to 0.018) |

## Findings

One walk per condition in one GAN per condition, in worlds that inherit the era confound of the G1 packages: hints.

1. **What held the walkers has worn off for the curious one, not for the Null.**
   - In G1 both walkers lingered on striped tiles. By G3, the curious walker's interest no longer follows stripes, and its radius ignores them.
   - The Null's still do: its interest and radius follow stripes as strongly as in G1.
   - A candidate reading, not tested: G3-curious is so striped (3.8 × the real package) that stripes no longer stand out to eyes grown on it. G3-null is striped only on a minority of tiles, so stripes remain the novelty there.
   - Both walkers' eyes are grown from random weights in each world; the difference lies in the worlds the two loops built, not in the eyes.
   - Set by hand: the radius rule, the eyes, the drive settings. Emerged: what each walker found interesting, and its change across generations.
   - *RQ2/RQ3; ch. 6, 7, 8.*
2. **The prediction for G4's packages follows directly.**
   - The G4-curious package should be about as striped as G3-curious's samples (×0.99).
   - The G4-null package should be about 1.5 × stripier than G3-null's samples.
   - If so, the loops converge in stripes from G4 on: the Null loop keeps amplifying them, and the curious loop stops.
   - This is stated before the G4 package readouts and is post hoc in its statistic.
   - *RQ3; ch. 8.*
3. **Boredom fades in both loops.**
   - 90° jumps fell to 3.2 % (curious) and 11.7 % (Null). As in G2, a candidate reading is that each new world varies more within a short distance.
   - Set by hand: the radius rule. Emerged: the jump share.
   - *RQ2/RQ3; ch. 7.*
4. **Time in latent walks is a premise, not a result.**
   - The Null's time path is identical in all three generations (steps 27, 244, 276). It follows from the seeded thinning and its uniform choice.
   - The curious walker's last wait fell at step 244 in both G2 and G3: the same seeded time offer came through, and it took it both times.
   - Prediction 172 holds for G3.
   - *RQ1/RQ3; ch. 5, 7.*

## Against the predictions

- **172** (the G3 and G4 walks reach the last snapshot within the first 3 % of steps): **right for G3** (2.4 % and 2.8 %). G4 pending.
- No other prediction was stated for the G3 latent walks.

## For review

- **Finding 2 is a check worth doing before G4's readouts:** chroma_y on the G4 packages, against G3's samples. It is a description stated in advance, not a test.
- **The block bootstrap** for the taste intervals is still owed (G2 report, finding 4). I'll add it to the recursion report.
- **The taste readout cannot see stripes.** The walk stores no offer images; the offers' chroma would need re-rendering from the stored offer latents, if they are stored.
