# Latent walks in generation 4: the curious walker in G4-curious against the Null walker in G4-null — report (2026-11-24)

*Same walkers, configs and rules as in G1–G3 (`notes/gen3_latent_report.md`; Moe, 2026-11-16 and 2026-11-17): z-sphere, the step calibrated by colour character against the real G1 15 km reference, snapshot as time with q = 0.10. Code: `agent/latent_walk.py`, `analysis/gen1/latent_readouts.py`, `analysis/gen1/latent_taste_ci.py --gen 4`, `analysis/recursion/stripes_in_walks.py` (post hoc). Tables and figures: `notes/gen4/latent/`, `notes/recursion/stripes_in_walks.csv`. Runs: `runs/g4/latent/<cond>/` (outside git). Both walks ran 2026-11-23 21:06 to 2026-11-24 00:09 on the PC. These walks are the last of the run: no G5 is trained on them (Moe, 2026-11-17).*

## Short version

- **Both walks reached N = 10,000 tiles in 9,999 steps** (3.0 h each), with no crash.
- **Calibration:** α_min = 18.4° (curious) and 12.1° (Null), against the real G1 reference as decided.
- **Time is used up at once, as in every generation** (prediction 172: **right**, G3 and G4). Both walkers took all three waits and reached the 3,840 kimg snapshot at step 221 (curious, 2.2 %) and 276 (Null, 2.8 %).
  - The Null's time path is identical for the fourth generation: steps 27, 244 and 276.
- **Now neither walker lingers on stripes:**
  - In G4 the Null's link between a tile's stripes and its interest or next radius has gone too (ρ +0.08 and −0.03; G3: +0.19 and −0.25).
  - Neither walk's tiles are stripier than its GAN's samples: curious ×1.00, Null ×1.04 (G3: ×0.99 and ×1.47).
- **Boredom keeps fading in the Null:** 90° jumps were 20.6 %, 18.0 %, 11.7 % and now 6.7 % of its steps. Curious is at 4.1 %.
- **Taste is tiny, as before.**
  - The curious walker chooses slightly brighter offers with more of every band (brightness +0.63, 0.06 of the offered spread) and slightly less texture (−0.21).
  - The Null shows no gap. Its intervals cross zero except a black-share sliver of +0.0003.

## Tables

`walks.csv`, `snapshots.csv`, `taste.csv`, `taste_ci.csv` and `waits_vs_moves.csv` are in `notes/gen4/latent/`.

| | cur G1 | cur G2 | cur G3 | cur G4 | Null G1 | Null G2 | Null G3 | Null G4 |
|---|---|---|---|---|---|---|---|---|
| α_min (colour) | 19.0° | 16.7° | 16.3° | 18.4° | 14.0° | 14.1° | 13.3° | 12.1° |
| steps at α_min | 53.5 % | 44.5 % | 45.6 % | 43.0 % | 53.6 % | 49.5 % | 48.8 % | 43.0 % |
| steps at 90° (boredom jumps) | 25.3 % | 4.7 % | 3.2 % | 4.1 % | 20.6 % | 18.0 % | 11.7 % | 6.7 % |
| median angle 10 steps apart | 60.6° | 63.5° | 62.3° | 68.1° | 51.1° | 58.1° | 55.2° | 57.5° |
| first step at 3,840 kimg (share of steps) | 130 (1.3 %) | 244 (2.4 %) | 244 (2.4 %) | 221 (2.2 %) | 276 (2.8 %) | 276 | 276 | 276 |
| mean p of the chosen offer / best offer taken | 0.49 / 61 % | 0.48 / 60 % | 0.46 / 59 % | 0.48 / 60 % | 0.125 / 12 % | 0.125 / 12 % | 0.125 / 13 % | 0.125 / 13 % |
| interest shares glance / grid / progress | 0.38 / 0.33 / 0.29 | 0.38 / 0.33 / 0.29 | 0.38 / 0.36 / 0.26 | 0.38 / 0.37 / 0.26 | 0.37 / 0.34 / 0.29 | 0.36 / 0.33 / 0.32 | 0.35 / 0.33 / 0.32 | 0.34 / 0.33 / 0.33 |

**Stripes in the walks, all four generations** (`stripes_in_walks.csv`; Spearman over steps, which are autocorrelated, so these describe and do not test):

| walk | ρ(chroma_y, I) | ρ(chroma_y, next α) | next offers at α_min: most / least striped fifth | next at 90°: most / least striped fifth | walk tiles' chroma_y ÷ its GAN's samples |
|---|---|---|---|---|---|
| G1 curious | +0.19 | −0.29 | 67 % / 33 % | 12 % / 41 % | ×2.32 |
| G2 curious | +0.07 | −0.11 | 55 % / 36 % | 4 % / 6 % | ×1.23 |
| G3 curious | +0.04 | +0.00 | 47 % / 46 % | 3 % / 3 % | ×0.99 |
| G4 curious | +0.06 | +0.03 | 40 % / 42 % | 5 % / 4 % | ×1.00 |
| G1 Null | +0.23 | −0.21 | 68 % / 39 % | 14 % / 30 % | ×1.24 |
| G2 Null | +0.30 | −0.26 | 70 % / 34 % | 8 % / 26 % | ×1.46 |
| G3 Null | +0.19 | −0.25 | 62 % / 37 % | 5 % / 18 % | ×1.47 |
| G4 Null | +0.08 | −0.03 | 40 % / 41 % | 7 % / 8 % | ×1.04 |

**Taste: chosen minus offered, compass offers, per step** (`taste_ci.csv`; step bootstrap, too narrow):

| statistic | curious G3 | curious G4 (interval) | Null G4 (interval) |
|---|---|---|---|
| brightness | +0.22 | +0.63 (0.47 to 0.79) | −0.28 (−0.61 to 0.04) |
| green band dark | −0.0002 | −0.0001 (−0.0001 to 0.0000) | +0.0001 (−0.0004 to 0.0006) |
| mean of the green band (B channel) | +0.66 | +0.81 (0.57 to 1.02) | −0.23 (−0.58 to 0.08) |
| gradient (texture) | −0.11 | −0.21 (−0.35 to −0.06) | +0.02 (−0.05 to 0.10) |
| row roughness (old banding statistic) | −0.005 | −0.009 (−0.020 to 0.004) | +0.009 (−0.000 to 0.019) |

## Findings

One walk per condition in one GAN per condition, in worlds that inherit the era confound of the G1 packages: hints.

1. **The stripe pull wore off in both walkers, one generation apart.**
   - The curious walker stopped lingering on stripes in G3, when its world was at 3.8 × the real package. The Null stopped in G4, when its world had reached 3.0 ×.
   - After that, neither walk adds stripes; only the GANs do, a little (×1.10–1.14 in G4).
   - A candidate reading, not tested: stripes pull eyes grown from random weights while they are a minority of the world. Once common, they no longer stand out.
   - So the loops reach the instrument at different speeds and then stop accelerating.
   - Set by hand: the radius rule, the eyes. Emerged: when the pull wears off.
   - *RQ2/RQ3; ch. 6, 7, 8.*
2. **Boredom fades in both loops.** 90° jumps fell to a few per cent in both by G4. A candidate reading, as in G2 and G3: each recursive world varies more within a short distance, so interest stays high and the radius stays close.
   - *RQ2/RQ3; ch. 7.*
3. **Time in latent walks is a premise across all four generations.**
   - The Null's time path never changed (27, 244, 276): it is set by the seed and q alone.
   - The curious walker's last wait fell at steps 130, 244, 244 and 221.
   - Prediction 172 holds.
   - *RQ1/RQ3; ch. 5, 7.*

## Against the predictions

- **172** (both G3 and G4 walks reach the last snapshot within the first 3 % of steps): **right**. G3 at 2.4 % and 2.8 %; G4 at 2.2 % and 2.8 %.

## For review

- **The block bootstrap for the taste intervals** is still owed. It goes into the recursion report.
- **The end of the stripe pull** suggests that a G5 would not add stripes in the walks. It is not planned (Moe, 2026-11-17: stop after G4).

## Correction (2026-11-24): the step bootstrap was not too narrow

nalysis/recursion/taste_block_ci.py (
otes/recursion/taste_block_ci.csv) resampled the per-step gaps in moving blocks of 50 and 200 steps for G1–G4.

- **The gaps are nearly independent:** the median lag-1 autocorrelation is about 0.
- **The block intervals are no wider than the iid ones:** median width ratio ×0.99 for the Null and ×1.2 for curious.
- **The Null's intervals clear zero in 4–5 of 36 statistic × generation cells.** These are mostly one correlated cluster (brightness and channel means in G2). At 95 % that is about what chance gives, so it does not show the bootstrap was too narrow.
- **The curious walker's gaps clear zero in 22–23 of 36 cells under every scheme.** Its taste is small but stable within each walk.

The claim above that the step bootstrap is too narrow is withdrawn. The intervals in this report stand. They still describe one walk, not walks in general.
