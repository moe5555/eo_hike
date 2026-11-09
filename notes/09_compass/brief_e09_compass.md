# Brief: experiment 09, the compass walker

> **Proposal, 2026-11-08.** Names follow `notes/README.md`. Runs and configs start with `e09_`, configs go in `configs/09_compass/`, code in `analysis/e09/`, and notes, results and figures in `notes/09_compass/`. The batch script is `scripts/hikes_e09.sh`, a copy of `hikes_e08.sh` with its disk and `.git` watchdog. The folder name is a placeholder.

Context first, then the new navigation, then the decisions to take before any code, then the stages. Report after Stage 0, Stage 2 and Stage 3, and stop for review each time.

## The goal

The walker currently has two separate ways to leave a place: blind far offers (`p_long_jump`) and the teleport when it gets bored (`patience`). This round replaces both with one continuous rule. At every step the walker is offered eight cells, all at the same distance, and that distance is set by its own drive: close when the surroundings are as interesting as usual, far when they are duller. The drive decides how far, and the scorer decides which way.

Three questions:

1. **The loop.** Does the radius follow the drive, and what rhythm comes out of it?
2. **The instrument.** Is that rhythm the walker's, or the mapping's? This is tested against controls that keep the radii but cut their link to the drive.
3. **Transfer.** Do e08's results on choice and returns hold when the walker moves this way?

Death is not built into the walker this round. Stage 4 is an offline dry run: it uses this round's logs to choose the condition for the next round.

## Where we are (e08)

Results on eight seeds (e08 `observations.md`, "Seeds 4–7 for seven settings"), and what each suggests here:

| Setting | e08 result (8 seeds) | Expected here |
|---|---|---|
| progress only (`w_n` 0) | restless (14.5 places, 7.1 rejected landings); returns almost gone (0.06, 0.04); top tile half as often (0.20) | the drive falls faster, so far steps come more often; few returns |
| surprise added (`w_e` 1) | prefers texture (0.51) and contrast (0.57); firmer choice (0.49); more straight-backs (0.18) | the same taste among offers, now also at far radii |
| `k_nn` 3 | no returns (−0.02); far tiles taken 2.6× chance | patches are used up fast: shorter cycles, more time far |
| `k_nn` 30 | more straight-backs (0.19) | longer close phases |
| `temperature` 0.2 / 1.0 | top tile 0.61 / 0.28; returns follow | acts on direction; the radius should not change |

Kept from e08 as constraints:

- **Rhythm** in the old walker came mostly from the boredom rule and the offer stream, not the scorer (Null at patience 0.3; e08 Stage 1, finding 6). This round asks whether the drive can carry it.
- **The eye** is the same for every setting tested. It is read on the panel's surprise (`analysis/e08/panel.csv`, unchanged).
- **Taste readouts** see large effects (surprise added: results on 8 seeds) and miss small ones. Snow, ice and cloud depend on which bright terrain a walk meets (the Reference's SD is 0.46 over eight seeds).
- **Eight Reference seeds from the start.** Four were an unlucky baseline (e08 Stage 1, finding 8).
- **Far fetches are slow.** `radius_km` 25 walks took 38–65 min and dropped up to 40 candidates on the 30 s timeout.
- **Pairing by seed is arbitrary from here.** Offers depend on where the walker stands, so walks of the same seed share only the starting weights and the random draws. The lead and result rules stay as they are: their false rates (9 % and 1.3 % per readout) were simulated for independent walks (e08 Stage 0, finding 8).

## The compass walker

Everything sits behind one key, `nav: compass`. The default, `classic`, reproduces every earlier run. In compass mode, `p_long_jump` and `patience` do nothing, and there are no teleports.

At each step:

1. **Drive.** d_t = (EMA_short − EMA_long) / SD_long of the walker's interest at the cells it stood on. This is Charnov's rule: leave when the current rate of gain falls below the long-run rate. d ≥ 0 means as interesting as usual or more.
2. **Radius.** r_t = r_min · (r_max / r_min)^clip(−d_t / Δ, 0, 1). The radius is linear in log distance: r_min at d ≥ 0, r_max at d ≤ −Δ.
3. **Offers.** Eight great-circle bearings 45° apart, rotated by θ_t. Each offer is the indexed cell nearest to the point at distance r_t along its bearing. Duplicates and points with no cell within the snap tolerance are dropped.
4. **Choice.** As now: the scorer ranks the offers, and temperature sets how firmly the walker takes the best one.

| Key | Meaning | Proposed default |
|---|---|---|
| `nav` | `classic` or `compass` | `classic` |
| `drive_signal` | `interest`, `novelty`, `surprise`, `progress` | `interest` |
| `drive_norm` | `z_diff` (as above) or `raw` | `z_diff` |
| `ema_alpha` | short average (as now) | 0.02 (≈ 50 steps) |
| `ema_alpha_long` | long average | 0.002 (≈ 500 steps) |
| `drive_warmup` | steps at r_min before the radius rule starts | 50 |
| `radius_min_km` | r_min | the Reference's `radius_km` |
| `radius_max_km` | r_max | set in Stage 0 |
| `radius_delta` | Δ, how far below usual the drive must fall to reach r_max | set in Stage 0 |
| `radius_mode` | `deterministic`, or `jitter` (lognormal around r_t) | `deterministic` |
| `radius_hysteresis` | dead band around d = 0 | 0 |
| `compass_frame` | `fixed`, `random` (θ_t drawn each step), `heading` | `random` |
| `persistence` | weight towards the current heading (only with `heading`) | 0 |
| `snap_tol` | how far an offer may sit from its target point, as a share of r_t | 0.25 |
| `offer_stay` | whether the current cell is a ninth offer | as the classic walker does (check in the code) |
| `radius_schedule` | file of radii to replay instead of the rule (for controls) | none |

The long average and its SD start as cumulative means until step 1 / `ema_alpha_long` (as `ema_alpha` 0.005 did in e08).

## Decisions before any code

Each decision gives the options, the proposed choice, and what it costs if wrong. Decide D1–D5 before code, D6–D7 in Stage 0, and D8–D10 before Stage 2.

**D1. Normalising the drive.**
- *Options:* raw signal; rank against recent history; short average against long average (difference or ratio).
- *Proposed:* the difference in long-run SDs (`z_diff`).
- *Why:* raw signals drift as the network learns (held-out error falls, surprise flattens), so a fixed mapping would shrink or widen the radius with age alone. Ranking fixes the share of time spent far by construction, so the rhythm would be imposed. Short against long is Charnov's comparison, and a long dull stretch stays dull. A ratio needs a signal that is always positive; the difference doesn't (check whether interest can go negative).
- *Cost if wrong:* the rhythm read in Stage 2 is the normaliser's, not the walker's.

**D2. Which signal drives the radius.**
- *Options:* interest (the walker's own mix), novelty, surprise, progress.
- *Proposed:* interest, with novelty and progress as Stage 3 variants.
- *Why:* interest is what the walker chooses by, so distance and direction share one value. In e08, novelty carries the returns and progress on its own makes the walker restless, so with the Reference weights, interest will in effect be mostly novelty.
- *Cost if wrong:* low. It is a config key.

**D3. The young network.**
- *Options:* the radius rule from step 0; a warm-up at r_min.
- *Proposed:* 50 steps at r_min, then the rule, with the long average cumulative until step 500.
- *Why:* everything is novel to a network from random weights, and no long-run rate exists yet.
- *Cost if wrong:* the first 150 steps look like a different walker. Read the young phase separately anyway, as in e08.

**D4. The offer frame.**
- *Options:* fixed N/NE/E…; rotated at random each step; relative to the heading, with `persistence`.
- *Proposed:* `random` for the main walks. `heading` comes later, with persistence as a temperament knob.
- *Why:* a fixed frame presses an eight-pointed star into the path, which shows in the step angles and on the map at large radii. Random rotation removes it.
- *Cost if wrong:* a lattice you then read as behaviour.

**D5. Staying.**
- *Options:* the current cell is an offer, or it isn't.
- *Proposed:* whatever the classic walker does. Check in the code before deciding.
- *Why:* without a stay offer, dwelling exists only as small steps, so a "held shot" becomes a slow pace rather than a pause.
- *Cost if wrong:* the place definition (D8) and the dwell readouts change meaning.

**D6. r_max and fetch cost.**
- *Options:* continental (~2,000 km), hemispheric (~10,000 km), uncapped; with or without prefetch.
- *Proposed:* chosen in Stage 0 from the fetch estimate and from whether a walker starting in Paris leaves Europe.
- *Why:* far offers miss the cache at every step: eight fresh tiles, at 3–5 s each.
- *Cost if wrong:* walks of hours, or a walker that never leaves the continent.

**D7. Deterministic or jittered radius.**
- *Proposed:* deterministic.
- *Why:* "the radius is the drive" is legible, also for the film. Jitter adds tails that come from the jitter, not the walker.
- *Cost if wrong:* low. The step-length distribution is read against controls in either case.

**D8. What a place is.**
- *Options:* a maximal run of steps at r ≤ 2 · r_min; a spatial cluster (for example, steps within 50 km of the run's start).
- *Proposed:* the radius run, because it is defined by the walker's own state and needs no threshold in km.
- *Why:* places used to be cut at teleports, and there are none now.
- *Cost if wrong:* the rhythm readouts become whatever was defined after seeing the data. Fix the definition before Stage 2.

**D9. Starting places.**
- *Options:* Paris only; Paris plus one or two starts unlike Europe.
- *Proposed:* Paris for every comparison (continuity with e08), plus the compass Reference from two other starts at four seeds each. Choose them for contrast in terrain: for example, a desert or steppe interior, and a cloudy tropical coast.
- *Why:* without teleports, the start matters more. Several starts are also the only realistic route back to taste (e08 Stage 1, finding 9).
- *Cost if wrong:* every claim rests on European terrain.

**D10. How to judge.**
- *Proposed:* the e08 rules, unchanged: a lead on four seeds, a result on eight (at least 7 of 8 same-sign differences, and a mean difference larger than half the Reference's range). Pairing by seed index is now arbitrary, but the rules' false rates hold for independent walks.
- *Why:* continuity, and rates that are already known.

## Readouts

**Kept from the e08 core.** Fix this list before Stage 2.

| Section | Readouts |
|---|---|
| Returns | revisits beyond blind, straight-backs beyond blind (the blind expectation follows the actual number of offers) |
| Choice | top tile chosen beyond chance |
| Taste (settled) | texture, contrast, brightness (snow, ice, cloud), saturation, and now **ocean**: offers at large radii mix land and sea, which Paris neighbours never did |
| Eye | panel surprise ~ texture, mean of steps 500–1,000 |
| Learning | held-out error at step 1,000 |

**Dropped:** teleports, rejected landings, far tiles taken ÷ chance. They don't exist in compass mode.

**New: the loop.**

| Readout | Definition |
|---|---|
| time near / far | share of steps at r_min, and share at r_max |
| step length | median and 90th percentile, in km |
| step-length shape | power law against exponential against lognormal, fitted as in Clauset, Shalizi & Newman (2009). Read only against the controls |
| period | first peak of the autocorrelation of log r |
| recovery | the change in d over the 10 steps after a step at r_max, against the same after a step at r_min. This answers "does going far restore the drive?" |
| places, dwell | per D8: number of places, median dwell |
| dwell against progress | per place, dwell against the fall in interest over the place (the marginal value theorem) |
| range | radius of gyration (km), continents reached, unique cells, ocean share |

In deterministic mode, the correlation between drive and radius is fixed by construction, so it is not a readout. Recovery is the readout that asks whether the loop does anything.

## Controls

| Control | Keeps | Removes |
|---|---|---|
| **compass Null** (`choice: uniform`) | the radius rule (the drive is still computed) | the choice of direction |
| **shifted radius** (`radius_schedule`) | each compass Reference walk's own radius sequence, circularly shifted by a random offset | the timing of the radius relative to the drive. The distribution and the autocorrelation stay intact |
| **shuffled radius** (`radius_schedule`) | the same radii in random order | the timing and the autocorrelation |
| **fixed radius** | the compass Reference's median radius at every step | variation in distance |
| **local only** | r = r_min at every step | far steps |
| **classic Reference** | the e08 walks, eight seeds | none. A historical anchor on another navigation |

The shifted radius is the main control. If the compass Reference's recovery, dwell and range are no different from it, the drive's link to distance does nothing the radius sequence alone doesn't do.

## Stage 0: build and check (offline and short walks)

**0.1 Code.** `nav: compass` and the keys above. Check that `nav: classic` reproduces `h0111_reference_s0` step for step over its first 200 steps.

**0.2 Geometry.** Check bearings and distances against a reference implementation. Then check the pole, the antimeridian, missing cells and open ocean. Plot the offers for 20 random cells at five radii.

**0.3 Mapping on old logs.** Compute d_t from the logged interest of the e08 Reference (eight seeds), progress only and `k_nn` 3, and see which radii the mapping would have given. Choose Δ so that the Reference spends most steps at r_min and reaches r_max in a few episodes per 1,000 steps, roughly as often as it used to teleport (3.5–4.25). This is only a starting point: the old drive was produced by the old navigation.

**0.4 Fetch cost.** From 0.3's radius distribution, estimate the tiles fetched per step and the walk time. Decide r_max and prefetching (D6).

**0.5 Analysis.** `analysis/e09/readouts.py` (the e08 core plus the loop readouts) and the writer for `radius_schedule` files.

**Report here.** Report Δ, r_max, the walk-time estimate and decisions D1–D7, and stop for review.

## Stage 1: calibration (12 walks)

The compass Reference (the e08 Reference with `nav: compass`) from Paris, seeds 0–3, at three settings of Δ: the Stage 0 choice, half of it, and double it.

Check for chattering at the boundary, walkers that never go far, walkers that are always far, whether walks leave Europe, dropped candidates, and walk time. Choose one Δ, which makes this the compass Reference. Log the choice in `log.md`. Stop only if none of the three works.

## Stage 2: the loop and its controls (about 52 walks)

Paris, eight seeds, 1,000 steps. The compass Reference's seeds 0–3 come from Stage 1.

| Walk | Seeds | New walks | First guess |
|---|---|---|---|
| compass Reference | 0–7 | 4 | close most of the time, a few far episodes; recovery after far steps clearly positive |
| compass Null | 0–7 | 8 | the radius still varies (the drive is still computed); returns at 0, as for the classic Null |
| shifted radius | 0–7 | 8 | the same step lengths by construction; weaker recovery; dwell less matched to progress |
| shuffled radius | 0–7 | 8 | no period |
| fixed radius | 0–7 | 8 | no cycles; fewer returns than at r_min |
| local only | 0–7 | 8 | stays in the region; returns above the Reference's; few places |
| compass Reference, start B | 0–3 | 4 | |
| compass Reference, start C | 0–3 | 4 | |

Write dated predictions in `notes/06_characters/expectations.md`, section "Experiment 09", before the first walk.

**Report here**, answering questions 1 and 2, and stop for review.

## Stage 3: transfer (about 48 walks, plus seeds 4–7 for leads)

> **Amended 2026-11-09 (review, during Stage 2): the larger eye comes first.** Far offers carry less novelty than near ones (log, 2026-11-09 note). Part of that is selection by the rule. Part may be the eye's scale: at ~2.7 km, terrain repeats worldwide, so distance carries no novelty premium. One key: `crop_px` 128 (~5.3 km) and 192 (~8.0 km), each against its own shifted-radius control, seeds 0–3 (16 walks; `scripts/hikes_e09.sh start 3a`). Not 256: there each tile has one crop position, so its 16 patches would be identical (the progress probe would test on what it trained on, and k_nn 10 would see one tile ten times). Main readouts: `offer_n_gap` in the shifted walks (the eye's own far/near gap, free of selection), `recovery_at_d`, far bouts, places and dwell. Held-out error compares only within one `crop_px`. Predictions are written after the Stage 2 review and before the first walk. The transfer settings below follow, at the eye this test favours.

> **Amended 2026-11-09 (review of Stage 2): two additions before Stage 3a.** Before the larger-eye walks, two things are added to the instrument: (A) readouts of the walker's world-view, and (B) the warm-up fix in the schedules, with a collapse readout. Neither may change how a walk moves. Same rules as before: decisions and deviations in `log.md`, dated predictions in `notes/06_characters/expectations.md` before any walk, stop and report if a check fails.
>
> **A. World-view readouts.** The thesis frames the walk as the building of a world-view. The readouts so far measure how the walker moves and chooses, not what its encoder comes to know about the Earth. Both new readouts use a fixed probe set and the walker's encoder at checkpoints.
>
> - **A0. Probe set and labels.**
>   - Labels from ESA WorldCover 2021 (v200, 10 m, 11 classes; public COGs, `s3://esa-worldcover/v200/2021/map/`). Per probe cell, the class fractions over the cell's footprint and the dominant class, read at reduced resolution (an overview, or about 100 m). Check that the overviews exist; log the resolution used. Cells outside WorldCover's coverage count as water/ocean with fraction 1. Cached in `data/worldcover_cells.parquet`, keyed by cell id.
>   - About 5,000 cells from the global index, stratified by dominant class with a cap per class. Drawn once with a logged seed, saved as `probe_cells.parquet`. The same set for every walk and every eye size. Its tiles are prefetched once into the cache.
>   - Walkers may visit probe cells: log the overlap per walk, don't exclude them.
> - **A1. Land-cover probe ("does it know what things are?").**
>   - At checkpoints (every 100 steps and the final step), embed the probe tiles with the walker's encoder. Use the representation the scorer uses for novelty, pooled to one vector per tile; document the layer and the pooling.
>   - Strictly read-only: eval mode, no gradients, no normalisation-statistics updates, no draws from the walk's random streams. Check: a 200-step walk with the readout on is bit-identical to the same walk with it off, in every logged column.
>   - Multinomial logistic regression on the dominant class, spatially blocked cross-validation (blocks of about 500 km, 5 folds): balanced accuracy and macro-F1. Ridge regression on the class-fraction vector: R².
>   - Baselines on the same probe set: the walker's encoder at step 0; hand-made colour and texture features (per-channel mean and SD, plus one simple texture statistic); chance. The colour and texture baseline matters most: it tells whether the walker learns anything beyond colour and surface.
> - **A2. Geography in the embedding ("does it know that near things are alike?").** At each checkpoint, on the same embeddings, and for the baselines too:
>   - Tobler curve: mean embedding cosine distance in log-spaced bins of great-circle distance (10 km to 20,000 km), from about 50,000 random probe pairs. The Spearman ρ between embedding and geographic distance, and the plateau distance, beyond which embedding distance no longer rises; the criterion (for example within 5 % of the far-bin mean) defined and logged.
>   - Geographic neighbour retrieval: per probe cell, the share of its 10 nearest embedding neighbours within 500 km, minus the share expected from the probe set's own geography.
>   - This is the direct measure behind Stage 2 finding 36: the plateau distance should say at what scale an eye sees the Earth as regionally structured, if at all.
> - **A3. Outputs and use.** `results/worldview.csv`, one row per walk and checkpoint: `probe_bacc`, `probe_f1`, `probe_r2`, `tobler_rho`, `plateau_km`, `knn_geo_excess`, and the baselines; `results/worldview.png` over steps per condition. The final-step values join the core readouts, with the lead and result rules as before (e08 D10). Comparisons: Reference against the compass Null (does choice build a different or better world-view than random steps?), and across the eye sizes of Stage 3a. Existing walks: if encoder checkpoints were saved in Stage 2, run A1 and A2 offline on the Reference and the Null before Stage 3a; if not, add checkpoint saving (every 100 steps, disk cost logged). Cost per checkpoint estimated and logged; above about 10 % of a walk, checkpoint every 250 steps instead (logged).
>
> **B. Warm-up fix and collapse readout.**
>
> - **B1. Schedules** (Stage 2 finding 39, option 2): `schedules.py` holds steps 0–49 at r_min, as the rule does, and shifts or shuffles only steps 50 to the end. Used for Stage 3a's shifted and shuffled controls. Stage 2 is not re-walked; one line in `log.md` notes that its shifted and shuffled walks used the old schedules.
> - **B2. Collapse readout**, per walk, from three signals: the longest run of chosen novelty below 0.005 (steps); held-out error frozen (the same value to four decimals at three or more consecutive checkpoints); probe spread, the mean pairwise embedding distance of the probe set at each checkpoint relative to step 0, flagged below a threshold set from the three collapsed Stage 2 walks and logged. A `collapsed` column (with the step window) in `readouts.csv`, shown in every table from now on; every verdict reported with and without collapsed walks.
> - **B3. Readout definitions** (cosmetic): loop readouts NaN where r_max = r_min (local only); places NaN at a fixed radius above 2 r_min.
>
> **Order.** (1) Implement A0–A2 and B1–B2; run the bit-identity check (A1); stop and report if it fails. (2) If checkpoints exist, run the offline world-view pass on the Stage 2 Reference and Null and report it briefly. (3) Dated predictions for Stage 3a, world-view readouts included, at least: does the probe beat the colour and texture baseline at the 2.7 km eye; does the plateau distance grow with eye size; does the Reference's world-view differ from the Null's; does the larger eye open the loop (`offer_n_gap` > 0 and `recovery_at_d` > 0 in the shifted control)? (4) `start 3a`.

Compass mode, Paris, seeds 0–3, each against the compass Reference.

| Walk | Change | Question |
|---|---|---|
| progress only, surprise added | `w_n: 0`, `w_e: 1` | do e08's scorer results hold? |
| `k_nn` 3, `k_nn` 30 | | does habituation now also set the cycle? |
| `temperature` 0.2, 1.0 | | does decisiveness stay on direction and leave distance alone? |
| `temperature` × `k_nn` | the four corners, 0.2 / 1.0 × 3 / 30 | e08's Stage 2 question, asked here |
| `drive_signal` novelty, progress | | D2: which signal makes the loop work? |

That is 6 + 4 + 2 settings, 48 walks. Then walk seeds 4–7 for every setting with a lead, judged by the result rule.

**Report here**, answering question 3, with the sheet in the e08 form for every setting with a result. Stop for review.

## Stage 4: the death, offline (no walks, optional long walks)

On the Stage 2 and 3 logs, test candidate conditions without killing anything:

- **C1, sudden surprise:** surprise more than k long-run SDs above its own running mean, after step 150.
- **C2, surprise once settled:** C1, but only after a stretch of d ≥ 0 lasting at least N steps.
- **C3, exhaustion:** d ≤ −Δ (r_max) for N steps in a row.

For each condition, report: the share of walks that would die before step 1,000; the age at death; the terrain at death (cover, brightness quartile, snow and cloud); and whether any of these differ from the shifted-radius control. A condition that only ever fires on cloud and snow is set by the terrain and the shared eye, not by the walker's history (e08 panel: the brightest quarter is the hardest to draw, at +0.7).

Optional: three compass Reference walks of 5,000 steps (seeds 0–2), to see whether surprise flattens with age, which would make C1 and C2 rarer late in a walk.

**Output:** a proposed death condition for experiment 10.

## Ground rules

- The new navigation sits behind a config option whose default reproduces existing runs (e08 brief). The classic walker stays available as a control.
- Dated predictions go in `expectations.md` before Stage 1 and before Stage 2.
- The core readouts are fixed before Stage 2, and only leads on these count.
- Run names have the form `e09_<setting>_<level>_s<seed>`. Never overwrite existing runs.
- Mac CPU, three walks side by side. Keep the Mac on AC power. For a closed lid, run `sudo pmset -a disablesleep 1` first and `0` afterwards. Panel scoring does not run alongside walks (memory). Large outputs go under `runs/`.
- Report in the style of e08: tables first, numbered findings in plain language, a table against expectations, then "for the next round".

## Budget

| Stage | Walks | Time |
|---|---|---|
| 0: build, check, map on old logs | a few short test walks | analysis and code |
| 1: calibration | 12 | set in Stage 0 (0.4) |
| 2: loop and controls | 52 | set in Stage 0 |
| 3: transfer | 48 + seeds 4–7 for leads | set in Stage 0 |
| 4: death dry run | none (optional 3 at 5,000 steps) | analysis |

Walk times depend on r_max and prefetching. At e08 speeds (15–25 min a walk, three side by side) Stage 2 would take about 6 h, but expect more.

## Out of scope

Death inside the walker (only the Stage 4 dry run), the GAN and its generations, the film, dreams and image generation, pretrained embeddings, new data sources, and jumps guided by a reason (rhyme, fracture): the compass replaces blind jumps, and a jump with a rationale is a later question.

## Deliverables

1. The compass navigation in the walker, behind `nav`, with the checks from 0.1 and 0.2.
2. `analysis/e09/` with the scripts, the readouts per run, and figures: radius over time for each walk, step-length distributions against the controls, and recovery.
3. `notes/09_compass/observations.md` and `log.md`, in the usual style.
4. Updated `notes/06_characters/expectations.md`.
5. A proposed death condition for experiment 10.
