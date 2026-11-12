# Experiment 12: the Landsat 1 world and the two-eye walker — report (2026-11-12)

Brief: `notes/brief_landsat_pipeline.md`. Log (what was built, every choice and deviation): `log.md`. World portrait: `notes/11_landsat1_mission/world.md`. Predictions 96–121: `notes/06_characters/expectations.md`. Tables: `results/l1/` (mission), `results/` (pass). Viewers: `runs/<run>/viewer/index.html`; contact sheet `results/e12_l1_two_top4_s0_contact_p1.png`.

## Short version

- **Built:**
  - the Landsat 1 world (1,466,863 cells on the Major TOM grid, earliest acquisition first, then each later one on revisits);
  - a lazy store reading the archive as stored, with quirk columns per cell and per crop;
  - walker v2 with two eyes: a glance at the whole tile and a 4 × 4 grid of crops, each with its own network and memory, behind `eye:`; v1 is bit-identical.
- **Walked:** the factorial on the whole mission, 9 conditions × 2 seeds × 1,000 steps from the archive's first scene (night, South Dakota). Also 6 walks on the e10 pass before Moe moved the factorial to the mission.
- **The two eyes can be told apart in every choice.** With the weights equal, the glance carries 38–42 % of interest at the choice, the grid 36–37 % and progress 21–25 %. Doubling the glance weight gives it 57 %.
- **The curious walkers share a taste no pooling changes.** Every condition selects against cloud and against bright tiles (hints against the Null for all seven curious conditions). An apparent preference for a cell's earlier acquisitions turned out to be mostly place memory; with memory held fixed, no shared taste for date remains (finding 2, corrected 2026-11-12).
- **The apparatus, read per eye:**
  - Stripes pull the grid when one crop decides (top-1) and v1, but not the two-eye walker.
  - Black fill pulls the grid and the glance-heavy walker at tile level, yet the top crop is *less* filled than its neighbours.
  - Night tiles are avoided by every two-eye walker.
- **Night is not black.** In the first night scene, nir08 reads a median DN of 209, so night tiles are a red field crossed by saturated scan lines. The walkers are born on it.
- **The "time well" is mostly an escape from the night.** Near the start, every cell's first image is that red field and its second is daylight. The two-eye walkers leaf through dates there (38–65 % revisits in the first 100 steps, Null 26–34 %). After step 100 their revisits are near the Null's. Median dates seen per visited cell: 1.
- **Homebodies of 1972.** 7 of the 12 free curious walks never left North America. The two-eye walker goes far less often than the Null (a hint). The mean acquisition year of every walk is 1972.0–1972.1.
- **Death dry run:** C1 is rare at 3 SD (≤ 6 firings a walk). Maximum grid surprise fires most often, 86 % of the time on striped, saturated or night tiles: death by the apparatus. Glance surprise fires only on cloud or the brightest tiles: death by weather.
- **Predictions:**
  - Mission (111–121): 6 right, 1 mostly right, 2 partly, 1 mostly wrong, 1 wrong.
  - Pass (96–110, on 6 walks, seed 0 only): 3 right, 2 mostly right, 3 partly, 5 wrong, 2 superseded.

## What was run

| Set | Walks | World | Notes |
|---|---|---|---|
| Pass factorial (`e12_*`) | 6 of 18, seed 0 (v1, Null, grid mean / top-4 / top-1, two eyes top-4) | e10 pass, 256 px, sqrt tone | Stopped 11:23; 3 aborted walks deleted |
| Mission factorial (`e12_l1_*`) | 18: v1, Null, grid mean / top-4 / top-1, two eyes top-4 / top-4 w_glance 2, two eyes with e09's shifted / shuffled radius schedules; seeds 0–1 | Landsat 1, `stack: revisit_next`, born in cell `479U_839L` | Tag `e12-l1-factorial` |
| Checks | v1 bit-identical (60 steps); two eyes bit-identical at equal thread count; smoke walks `e12_smoke_two_s0`, `e12_l1_smoke_s0` | | |

Two seeds per condition cannot make a lead or a result (e08's rule needs four). **Hint**: both seeds outside the Null's two-seed range, on the same side. Everything below is a first look.

## Tables (mission)

### Reach and returns (steps from 50; revisit = a step on a cell's 2nd or later acquisition)

| condition | revisits s0 / s1 | revisits, steps 0–99 | night, steps 0–99 | share at r_max | far bouts | max km from start | continents |
|---|---|---|---|---|---|---|---|
| Null | 0.34 / 0.28 | 0.34 / 0.26 | 0.66 / 0.52 | 0.04 / 0.22 | 3 / 10 | 5,126 / 16,434 | 2 / 5 |
| v1 | 0.25 / 0.16 | 0.48 / 0.31 | 0.52 / 0.38 | 0.00 / 0.17 | 1 / 12 | 3,399 / 15,795 | 1 / 5 |
| grid mean | 0.21 / 0.35 | 0.27 / 0.35 | 0.73 / 0.38 | 0.00 / 0.12 | **0 / 1** (−) | 2,545 / 6,773 | 1 / 4 |
| grid top-4 | 0.23 / 0.44 | 0.37 / 0.28 | 0.45 / 0.38 | 0.10 / 0.00 | 3 / 0 | 16,289 / 645 | 5 / 1 |
| grid top-1 | 0.38 / 0.29 | 0.36 / 0.34 | 0.64 / 0.36 | 0.00 / 0.05 | 0 / 3 | 1,583 / 7,057 | 1 / 2 |
| two eyes top-4 | 0.28 / 0.39 | **0.65 / 0.38** | **0.35 / 0.23** | **0.03 / 0.00** (−) | 3 / 1 | 4,661 / 2,532 | 1 / 1 |
| two eyes, w_glance 2 | **0.38 / 0.38** (+) | **0.59 / 0.43** | **0.41 / 0.32** | 0.10 / 0.00 | 3 / 1 | 9,249 / 3,100 | 3 / 1 |
| two eyes, shifted schedule | 0.18 / 0.21 (−) | | | 0.14 / 0.12 | 8 / 10 | 16,202 / 10,318 | |
| two eyes, shuffled schedule | 0.09 / 0.08 (−) | | | 0.17 / 0.12 | 142 / 103 | 16,614 / 13,605 | |

Median dates seen per visited cell: 1 in every walk. Most dates seen of one cell: 10–11 for the two-eye walks, 6–7 for the Null.

### Interest at the choice (steps from 50)

| condition | share glance / grid / progress | lift glance / grid / progress | best offer taken | p(chosen) |
|---|---|---|---|---|
| Null | 0.35 / 0.37 / 0.28 | 0.01 / 0.03 / 0.01 | 0.14 | 0.14 |
| grid mean | – / 0.64 / 0.36 | – / 0.55 / 0.39 | 0.41 | 0.30 |
| grid top-4 | – / 0.64 / 0.36 | – / 0.69 / 0.42 | 0.49 | 0.37 |
| grid top-1 | – / 0.62 / 0.38 | – / 0.70 / 0.39 | 0.49 | 0.38 |
| two eyes top-4 | 0.40 / 0.37 / 0.23 | 0.69 / 0.56 / 0.42 | 0.55 | 0.43 |
| two eyes, w_glance 2 | 0.57 / 0.27 / 0.16 | 1.78 / 0.67 / 0.30 | 0.71 | 0.61 |

Means of the two seeds (per seed in `results/l1/readouts.csv`). The lift is a component's contribution at the choice minus its mean over the offers: what made the chosen offer win.

### Offer → choice against the Null (selz, steps from 50; + / − = hint)

| condition | cloud | brightness | rank of the acquisition (− = earlier; see finding 2) | stripes | fill | night |
|---|---|---|---|---|---|---|
| Null (range) | −0.01 / −0.01 | −0.02 / 0.00 | +0.02 / +0.05 | −0.02 / +0.01 | −0.04 / +0.09 | +0.01 / +0.02 |
| v1 | −0.33 / −0.15 (−) | −0.43 / −0.45 (−) | −0.16 / −0.30 (−) | +0.16 / +0.18 (+) | +0.05 / +0.46 | +0.29 / −0.39 |
| grid mean | −0.48 / −0.09 (−) | −0.51 / −0.25 (−) | −0.29 / −0.11 (−) | +0.00 / +0.09 | +0.28 / +0.19 (+) | +0.02 / −0.13 |
| grid top-4 | −0.32 / −0.37 (−) | −0.44 / −0.55 (−) | −0.03 / −0.04 (−) | +0.19 / +0.04 (+) | +0.51 / +0.15 (+) | +0.13 / +0.21 (+) |
| grid top-1 | −0.25 / −0.08 (−) | −0.33 / −0.20 (−) | −0.05 / −0.17 (−) | +0.27 / +0.17 (+) | +0.08 / +0.26 | +0.29 / −0.10 |
| two eyes top-4 | −0.44 / −0.44 (−) | −0.55 / −0.57 (−) | −0.14 / −0.04 (−) | +0.07 / −0.06 | +0.20 / +0.08 | −0.25 / −0.42 (−) |
| two eyes, w_glance 2 | −0.23 / −0.02 (−) | −0.38 / −0.28 (−) | +0.05 / −0.04 | −0.03 / +0.27 | +0.19 / +0.13 (+) | −0.46 / −0.50 (−) |
| two eyes, shifted | −0.09 / −0.09 (−) | −0.18 / −0.26 (−) | −0.18 / −0.22 (−) | +0.18 / +0.25 (+) | +0.16 / +0.32 (+) | −0.43 / −0.42 (−) |
| two eyes, shuffled | −0.13 / −0.09 (−) | −0.29 / −0.16 (−) | −0.06 / −0.09 (−) | +0.15 / +0.16 (+) | +0.25 / +0.14 (+) | −0.37 / −0.59 (−) |

Stripes and fill are tile-level shares (stripe: the maximum over the three bands the eye sees). Night after step 200: below the Null for grid mean, grid top-4, w_glance 2 and both schedule controls.

### Inside the tile (chosen tiles, steps from 50)

| condition | top crop above its tile's median: stripes | fill | QA cloud | top crop on the tile's edge (chance 0.75) |
|---|---|---|---|---|
| Null | 0.55 / 0.50 | 0.47 / 0.54 | 0.28 / 0.40 | 0.78 / 0.79 |
| grid mean | 0.50 / 0.57 | 0.33 / 0.25 (−) | 0.39 / 0.46 | 0.78 / 0.78 |
| grid top-4 | 0.53 / 0.56 | 0.39 / 0.21 (−) | 0.38 / 0.42 | 0.78 / 0.78 |
| grid top-1 | 0.61 / 0.56 | 0.37 / 0.36 (−) | 0.53 / 0.35 | 0.75 / 0.79 |
| two eyes top-4 | 0.54 / 0.54 | 0.24 / 0.21 (−) | 0.45 / 0.41 | 0.75 / 0.74 |
| two eyes, w_glance 2 | 0.49 / 0.59 | 0.43 / 0.18 (−) | 0.39 / 0.44 | 0.78 / 0.77 |

Among tiles where the quirk varies between crops. The mean excess of the top crop's stripe share over its tile's median is positive in every walk, the Null included (0.001–0.016).

### Correlations over offers

| condition | ρ(glance novelty, cloud) | ρ(grid novelty, cloud) | ρ(glance, brightness) | ρ(grid, brightness) | ρ(v1 shadow, grid) |
|---|---|---|---|---|---|
| Null | 0.15 / 0.12 | 0.01 / 0.21 | −0.09 / −0.36 | −0.25 / −0.35 | 0.72 / 0.75 |
| two eyes top-4 | −0.11 / −0.41 | −0.09 / −0.19 | −0.45 / −0.56 | −0.38 / −0.27 | 0.77 / 0.42 |
| two eyes, w_glance 2 | 0.10 / 0.10 | 0.02 / 0.02 | −0.09 / −0.30 | −0.12 / −0.35 | 0.72 / 0.71 |
| grid mean | (0.0) | −0.12 / −0.11 | | −0.30 / −0.40 | 0.88 / 0.77 |
| grid top-1 | | −0.09 / 0.14 | | −0.01 / −0.15 | 0.85 / 0.50 |

### Death dry run (C1: surprise of the chosen image > running mean + 3 SD after step 150; summed over 18 walks)

| surprise source | C1 firings | walks with any | on cloud ≥ 0.3 | brightest quarter | night | striped, DN 255 or night |
|---|---|---|---|---|---|---|
| maximum grid crop | 21 | 7 | 0.62 | 0.38 | 0.14 | **0.86** |
| glance | 11 | 6 | **1.00** | 0.73 | 0.00 | – |
| pooled grid | 7 | 5 | 0.43 | 0.43 | 0.43 | – |
| v1 (its one surprise) | 4 | 1 | 0.50 | 0.50 | 0.25 | – |

C2 (after 50 settled steps) fires 1–4 times in 4 walks. C3 (20 steps at r_max) fires in 11 of 18 walks, mostly late (from step 477), and 142 / 103 times in the shuffled controls, where the radius is external. Per walk in `results/l1/deaths_summary.csv`, every firing in `deaths.csv`; the viewer marks them.

## Findings

1. **The two eyes are separable in every choice.**
   - With equal weights, the glance's share of interest at the choice is 0.38–0.42, the grid's 0.36–0.37, progress's 0.21–0.25. Lifts: glance 0.65–0.74, grid 0.55–0.56, progress 0.41–0.43.
   - Doubling the glance weight raises its share to 0.57 and its lift to 1.8, and the walker takes the best offer 71 % of the time, against 55 %.
   - Authored: the weights and the z-scoring. Emergent: how much each eye separates the offers. The decomposition is what principle 4 asked for. *RQ2; chapters 6 and 7.*
2. **A shared taste: clear and dark. Not "first".**
   - Every curious condition, whatever the eye or pooling, selects against QA cloud (−0.02 to −0.48) and against brightness (−0.16 to −0.57) compared with the offers. All seven are hints against the Null.
   - *Corrected after review (2026-11-12).* The selection of an acquisition's rank is negative in six of seven conditions (−0.03 to −0.30): the chosen offer has the lower rank. The first table's header ("−rank") had the sign flipped; the numbers are as stated.
   - But rank is confounded with place memory. Rank 0 is always an unvisited cell; rank ≥ 1 is a cell already in memory, and its rank is the number of visits. A novelty drive with per-place memory prefers unvisited cells anyway.
   - With memory held fixed (`results/l1/date_vs_memory.csv`), no shared taste for date remains:
     - Among fresh cells only (nothing in memory), v1 prefers earlier dates (−0.26 / −0.15, hint), the two-eye walker *later* ones (+0.03 / +0.15, hint), and w_glance 2 and the grid walkers split by seed. Leaving out night offers changes nothing.
     - Among revisits of equal rank (equal visit count), the two-eye walkers prefer earlier dates (−0.50 / −0.27 and −0.15 / −0.13, hints, on 59–84 steps a walk).
   - So the rank effect is mostly memory: v1 and grid mean pooling take fresh cells more often than they are offered, and the two-eye walkers do not.
   - "Date" among nearby fresh cells is not clean time either. Neighbouring cells at 15 km mostly differ in date because they fall in adjacent orbital paths (consecutive days) or a later 18-day cycle, so date is partly which pass, partly season.
   - The e09 long walk on Major TOM grew a taste for bright ground and snow only after ~6,000 steps (and started with a negative one, −0.38). At 1,000 steps this matches its first block.
   - Emergent from novelty on a 1972 world where cloud and snow saturate (the stretch's top is set by them). *RQ2; chapter 7.*
3. **Stripes pull the eye that lets one crop decide.**
   - Selection of striped tiles is a hint for grid top-1 (+0.27 / +0.17), grid top-4 (+0.19 / +0.04), v1 (+0.16 / +0.18) and both schedule controls. It is absent in the free two-eye walks (+0.07 / −0.06) and in mean pooling.
   - Inside the tile, the most novel crop is more striped than its neighbours in 50–61 % of tiles, the Null included: the eye ranks stripes high, and whether that reaches the choice depends on pooling and on the glance.
   - Authored: pooling k. Emergent: the stripe preference. *RQ2 (the artefacts of the instrument); chapter 7.*
4. **Black fill pulls at tile level, not as a detail.**
   - Tiles with fill (unimaged margins and missing scan lines) are chosen above the Null by grid mean and top-4, by w_glance 2 and by both schedule controls (+0.13 to +0.51).
   - Yet in every curious walk the top crop holds *less* fill than its tile's other crops (above the median in 18–43 % of tiles, the Null 47–54 %).
   - What attracts is a tile that contains black, not the black crop itself. On the pass, the black wedges of partial cells drew the glance (one seed, 59 % of chosen tiles against the Null's 21 %). *RQ2; chapter 7.*
5. **Night is a red field, and the two-eye walkers flee it.**
   - In the archive's first scene, nir08 reads a median DN of 209 with the sun at −15°. Night tiles in CIR are therefore red, crossed by saturated scan lines, not black (the brief expected black). As stored: possibly an internal calibration signal (not checked).
   - Every two-eye walker selects against night offers (−0.25 to −0.59, hints, both schedule controls included). Grid top-4 selects for night overall (+0.13 / +0.21), and v1 splits by seed.
   - Authored: the start in the night pass (Moe) and the CIR rendering. Emergent: the flight. *RQ2 (data and phenomenon apart); RQ1 (the start as an origin); chapters 5 and 7.*
6. **The time well is the escape from the night.**
   - Around the start, every cell's first image is that red field, and its second is daylight (1 Aug 1972).
   - In the first 100 steps the two-eye walkers revisit far more than the Null (0.65 / 0.38 and 0.59 / 0.43 against 0.34 / 0.26) and stand on night far less (0.35 / 0.23 and 0.41 / 0.32 against 0.66 / 0.52). Revisiting is the only nearby way out of the night.
   - From step 100, revisits are near the Null's (two eyes 0.25 / 0.40, Null 0.27–0.34). Only w_glance 2 stays above it (0.38 / 0.38, hint). The median visited cell shows one date.
   - Under replayed radius schedules, revisits halve (0.08–0.21, hints): the drive's close phases make the returns.
   - So the stack's time depth is used where the archive's sequence forces it, and later only by the glance-heavy walker. *RQ1 (revisiting as moving through time); RQ2; chapters 6 and 7.*
7. **The two-eye walker is a homebody.**
   - It reaches r_max on 0.1–2.6 % of steps against the Null's 3.7–21.9 % (hint). Its farthest point is 2,500–4,700 km from the start, and both seeds stay in North America. Grid mean pooling almost never goes far (0 and 1 bouts, hint).
   - 7 of the 12 free curious walks never leave North America. Every walk's mean acquisition year is 1972.0–1972.1: the walkers live in the satellite's first months.
   - The drive and radius rule are v1's, set by hand; δ was not recalibrated. Under the replayed schedules, far offers carry less interest than near ones (far − near on the long yardstick −0.19 to −1.14), as on Major TOM (e09). *RQ2; chapter 6.*
8. **The glance reads the whole tile's tone.** Over offers, glance novelty in the two-eye walker falls with brightness (ρ −0.45 / −0.56) and with cloud in one seed (−0.41). Its |ρ| with cloud exceeds the grid's in both seeds. Dark, clear tiles are new to it. *RQ2; chapter 7.*
9. **Patch shuffle (pass, 5 walks):**
   - Grid novelty does not change when the 16 crops are shuffled (exactly 0, by construction).
   - Glance novelty rises in 59–64 % of tiles, but only by a median 2–4 %. The glance reads the arrangement of its tile only a little at 333 m/px: mostly tone and texture.
   - *RQ2; chapter 6.*
10. **Death would come from the apparatus or the weather, depending on the eye.**
    - At 3 SD, C1 is rare (21, 11 and 7 firings over 18 walks). Maximum grid surprise fires most often, and 86 % of its firings land on striped, saturated or night tiles: one crop kills.
    - Glance surprise fires only on cloud (11 of 11) or bright tiles.
    - The surprise source is a premise; this is what each would mean. *RQ2; chapter 6 (the death rule, milestone 2).*
11. **Forgetting is small.** Grid error on the fixed sea, sand and field tiles falls by one to two orders of magnitude by step 500 in every walk. Sand's error rises again between steps 500 and 1,000 in 10 of 16 walks, from a tiny base (≤ 0.005). *Chapter 6 (method).*
12. **On the pass (6 walks, one seed): one axis, and black edges.**
    - The 185 km strip forces every long step along the track and snaps far offers onto its edge.
    - There, the two-eye walker stood on partial cells with black wedges in 59 % of steps (Null 21 %, v1 10 %, grid top-4 14 %).
    - The world's shape is authored (the test bed); the attraction is the glance's. *RQ2; chapter 7.*

## Against the predictions

| # | Prediction | Outcome |
|---|---|---|
| 96 | Pass: all 18 walks finish, 12–30 min | Superseded in part: 6 finished (17.5–22 min), 12 not walked (stopped) |
| 97 | Pass decomposition 0.35–0.50 / 0.30–0.45 / 0.15–0.30; glance lift > grid; g2 | Mostly right: 0.40 / 0.36 / 0.24, lift 0.46 > 0.36 (one seed); g2 not walked |
| 98 | Pass: top crop more striped than its tile, all walks, within ×2 across pooling | Right (excess 0.011–0.026 in grid walks; Null 0.014) |
| 99 | Pass: stripe selection top-1 > top-4 > mean; v1 within ±0.1 | Wrong: top-4 0.23 > mean 0.22 > top-1 0.17; v1 0.20 |
| 100 | Pass: glance reads cloud more than grid; g2 cloudier | Partly: 0.46 against 0.18 (one seed); g2 not walked |
| 101 | Pass: stripe selection falls from the first half to the second in grid walks, by more than v1 | Right on one seed (grid 0.22–0.28 → 0.13–0.17; v1 rises 0.13 → 0.27) |
| 102 | Mission: top crop holds more fill than its tile | Wrong: less (18–43 % above the median, Null 47–54 %) |
| 103 | No edge pull, 0.70–0.80 | Mostly right: 0.76–0.82 (Null and top-1 just above) |
| 104 | Patch shuffle: grid unchanged; glance > 10 % | Partly: grid 0 exactly; glance rises in 59–64 % of tiles but by 2–4 % |
| 105 | Revisits and straight-backs ≤ 1.5 × v1 | Right (all below v1's 0.49 / 0.17) |
| 106 | Share at r_max within ×2 of v1; schedules | Wrong: 0.02–0.36 against v1 0.07; schedules not walked |
| 107 | Forgetting: below step 0; sea rises in top-1 | Partly: below step 0 everywhere; no sea rise in top-1 |
| 108 | Shadow ρ ≥ 0.8 (mean), 0.5–0.8 (top-1) | Wrong: 0.70 and 0.40 |
| 109 | Death on the pass: max ≥ pooled ≥ glance | Wrong: glance fired most (5 of 8 C1) |
| 110 | Smoke walk on the mission | Superseded by the mission factorial; right in substance (1.1–1.7 s a step, 1 offer dropped, no crash) |
| 111 | Mission cost: 20–45 min, < 1 % dropped, no failures | Right (23–33 min, 1 offer dropped in 18,000 steps). Not foreseen: the cache grew to 16 GB |
| 112 | Time well: revisits above the Null everywhere; ≥ 1/3 revisits and ≥ 2 dates in two-eye walks | Mostly wrong: hint only for w_glance 2; two eyes 0.28 / 0.39; median 1 date. True only in the first 100 steps (finding 6) |
| 113 | The well is left (≥ 1 far bout in 3 of 4 two-eye walks); r_max share below the Null | Mostly right: 4 of 4; below the Null for two eyes top-4, not for w_glance 2 |
| 114 | Night selected against from step 200 (two eyes) | Partly: w_glance 2 and the schedule controls yes; two eyes top-4 one seed +0.22 (over all steps a hint, −0.25 / −0.42) |
| 115 | Decomposition 0.30–0.55 / 0.25–0.45 / 0.15–0.30; g2 glance > 0.5 | Right |
| 116 | Stripes: within the tile everywhere; top-1 > mean; top-1 a hint | Right |
| 117 | Fill: two eyes above the Null; the grid alone not | Wrong: two eyes top-4 not a hint; grid mean and top-4 are |
| 118 | |ρ(glance, cloud)| > |ρ(grid, cloud)| in both two-eye seeds | Right (0.11 > 0.09; 0.41 > 0.19) |
| 119 | No edge pull, 0.70–0.80 | Right (0.74–0.79) |
| 120 | Forgetting: below step 0 for every kind and walk | Right |
| 121 | Death: max ≥ pooled ≥ glance; max-grid on quirks ≥ 2/3 | Partly: max 21 > glance 11 > pooled 7; quirks 0.86 |

Not foreseen: night tiles are red, not black (finding 5); the early time well is the escape from the night pass (finding 6); every curious walker selects against cloud and brightness (finding 2; its apparent preference for earlier acquisitions is mostly place memory); fill attracts at tile level while the top crop avoids it (finding 4).

## The brief's proposed defaults: which held, which I'd change

| Default | Verdict |
|---|---|
| Two encoders, one per eye | Held. The eyes separate cleanly in the logs (finding 1). |
| Grid 4 × 4 only | Held. The edge share of top crops is at chance (0.74–0.79), so no offset grid is needed for the readouts. |
| Crop memory per place | Held. Within-tile rankings are stable; the shadow (tile means) correlates 0.42–0.88 with the pooled grid. |
| Memory = all 16 crops; training = top-k jittered + replay | Held, with one change made: the top-k crops are cycled to 16 training crops, so pooling does not change the learning rate. Sand's slight late rise (finding 11) is the only sign of eroding the ordinary. |
| Top-k = 4 | Keep. Top-1 makes the grid chase stripes (finding 3); mean pooling makes it a stay-at-home (finding 7). |
| Interest = z(glance) w + z(grid) + z(progress) | Held. w_glance is a real temperament: at 2 the walker revisits more, flees night harder and takes the best offer 71 % of the time. |
| Progress on a checkerboard split | Held. Its share is stable (0.16–0.25). |
| Surprise: not a drive, the trigger of death | Held. The source matters: max grid → death by apparatus, glance → death by weather (finding 10). |
| Draw at temperature 0.5 | Untested here. |
| *Changes I'd suggest* | (a) A cache cap with LRU eviction in `Landsat1TileStore`: it has none, and 18 walks filled 16 GB. (b) Decide whether the night start stays: it shapes the first 100 steps of every walk (findings 5–6). (c) Seeds 2–3 before any of this is called a lead. |

## For review

1. **The night start shapes every walk's beginning.** Keep it as the authored origin, or start in daylight (Missouri, or Dallas's first-light scene)?
2. **Is the nir08 night signal worth a look?** Night tiles are red because nir08 reads ~209 DN with the sun at −15°. Calibration lamp, detector offset or noise? Not checked. It is the clearest case so far of data without phenomenon.
3. **Fill and the full-tile rule.** You asked to defer the rule. Fill draws some walkers at tile level (finding 4). It is a quirk the readouts can now track.
4. **Cache size.** 14 GB free on the Mac after the factorial. Longer walks need the cap, or the PC.
5. **Next:** the replication milestone (4 seeds plus a long Null, the death rule, Tobler and cluster readouts) on this world. The death source to build is a choice: max grid or glance.
