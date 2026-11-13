# Brief v2, Gate B: the dry runs on the clock world — report (2026-11-13)

Brief: `notes/brief_landsat_v2_run.md`. Predictions 122–131: `notes/06_characters/expectations.md`. Tables and figures: `notes/gen1/dryrun/` (made by `analysis/gen1/readouts.py dryrun`). Walks: `runs/dryrun/<condition>/w00k/` (contact sheets every 500 steps in `contact/`). Code: tag `gen1-gateA`, then the fixes listed under "What broke". Walks that crossed a store bug are kept in `runs/dryrun_prefix/` and are not used.

## Short version

- **Built and tested (Gate A):**
  - the clock world: 1,466,863 cells, 31.8 M acquisitions, one product per date;
  - the clock, the time offer and the end rule;
  - checkpoints that resume bit for bit;
  - the cache cap.
  - 26 tests pass, 7 of them on real short walks.
- **Walked:** curious and Null, start cells 0–2 of the shared list (Rondônia, southern Algeria, Quebec), seeds 0–2, until the clock reaches T_end or a 3,000-step dry-run cap.
  - Only one walk ended by the clock: Null w2, Quebec, 919 steps.
  - The other five reached the cap: every curious walk, with its clock between 1977-10-03 and 1977-11-16, and Null w0–w1.
- **Time is a navigation problem.** By mid-1974 only ~422,000 of 1.47 M cells will ever be imaged again; the satellite kept returning to a shrinking part of the world. A walker can only move its clock by waiting where a later pass exists:
  - The time offer was available in only 3–75 % of steps, depending on region.
  - Every walk had stretches of 99–2,073 steps without one.
  - The clock climbs in stairs.
- **The curious walker lives far from its own time** (a hint, all three start cells):
  - It stands on tiles whose date is a median of 379–1,343 days from its clock, against 0–1,078 for the Null.
  - It is offered a wait less often than the Null in every pair: 2.7 / 4.8 / 21 % of steps, against 10.5 / 5.7 / 75 %.
  - When it does wait, the wait is taken for learning progress (z = 1.09, against 0.44 for its moves). Its waits are longer than the Null's: mean 64 against 36 days, and 3.3 % against 0.7 % jump more than a year.
- **Clear over cloud** (pooled over walks, as in e12): the curious walker picks less cloudy tiles than it is offered.
  - Moves: 0.17 against 0.23.
  - Waits: 0.28 against 0.41.
  - The Null shows no gap.
- **The archive loses its green band in spring 1977.** From April 1977 to the end, 1,293 of the 1,305 scenes the walks have read carry band 4 (green) without calibration (NULL in the MTL, a constant DN). It was crashing the store. The store now renders the band as missing: the CIR green channel is black, and the scene is listed as uncalibrated. This is a default for Moe to decide (below).
- **Compute:**
  - 1.5–1.75 s a step in wall time, two walkers side by side. Three walkers made the 16 GB Mac swap.
  - Generation 1 at N = 5,000 / 10,000 / 20,000 tiles per condition: about 3–6 / 7–13 / 13–24 h for both conditions. Well under 72 h, so no reductions are proposed.
- **Predictions 122–131:** 4 right (125, 127, 128, 129), 1 mostly right (130), 1 partly (126), 4 wrong (122, 123, 124, 131).
- **Since the dry runs (Moe, 2026-11-13):** a long phase of curious walks on start cells 3, 4, … is running (`runs/long/`). Each walk ends when its clock enters 1977 or at 20,000 tiles, and walks continue until 20,000 pooled tiles. Two walks started at 03:12 under the brief's T_end were stopped at 08:32 when Moe chose the 1977 rule; they are kept in `runs/long_aborted/`.

## What was run

| Walk | Start cell (list row) | Steps | End | Clock at the end | Distinct tiles |
|---|---|---|---|---|---|
| curious w0 | `156D_664L`, Rondônia (0) | 3,000 | capped | 1977-10-23 | 2,387 |
| curious w1 | `280U_59R`, southern Algeria (1) | 3,000 | capped | 1977-11-16 | 2,259 |
| curious w2 | `577U_514L`, Quebec (2) | 3,000 | capped | 1977-10-03 | 2,443 |
| Null w0 | (0) | 3,000 | capped | 1975-08-22 | 2,246 |
| Null w1 | (1) | 3,000 | capped | 1977-08-05 | 2,150 |
| Null w2 | (2) | 919 | **time** | 1977-12-21 | 755 |

Configs `configs/gen1/curious.yaml` and `null.yaml`. The walker is `e12_l1_two_top4` (Moe), and the Null is the same walker with a uniform draw. `--steps 3000`; T_end = 1977-12-20.

Notes on these runs:
- Null w0 ran its first 2,000 steps on the store as of Gate A. It never met an affected tile, so it was resumed from its checkpoint, bit for bit.
- The other five ran fully on the fixed store: curious w0 and w2 and Null w1 were rerun.
- One offer was dropped on a fetch timeout in 117,000.

Three seeds, one per start cell, paired by cell. **Hint** here means the same direction in all three pairs. Nothing below is a lead.

## Tables

### Time (`walks.csv`, `dt.csv`, figure `clock_vs_step.png`)

| | curious w0 / w1 / w2 | Null w0 / w1 / w2 |
|---|---|---|
| waits | 17 / 28 / 45 | 29 / 22 / 85 |
| steps with a time offer available | 0.027 / 0.048 / 0.214 | 0.105 / 0.057 / 0.750 |
| P(wait \| available) | 0.21 / 0.19 / 0.07 | 0.09 / 0.13 / 0.12 |
| the same, by chance (mean 1 / offers) | 0.14 / 0.13 / 0.12 | 0.12 / 0.12 / 0.12 |
| longest stretch without a time offer | 1,198 / 1,267 / 747 | 852 / 2,073 / 99 |
| first step with the clock in 1977 | 806 / 801 / 1,137 | – / 2,445 / 646 |
| median \|tile date − clock\|, days | 1,343 / 1,336 / 379 | 390 / 1,078 / 0 |
| share of steps with \|tile date − clock\| > 1 year | 0.68 / 0.81 / 0.64 | 0.51 / 0.88 / 0.07 |
| projected steps to T_end (rate of the last 1,000 steps; 15,000 = would be capped) | 5,759 / 3,586 / 15,000 | 8,863 / 3,472 / 919 |

Δt of a wait, pooled:

| | waits | p10 | median | p90 | mean | most common | 1 day | > 180 days | > 1 year |
|---|---|---|---|---|---|---|---|---|---|
| curious | 90 | 1 | 18 | 157 | 64 | 18 | 0.12 | 0.08 | 0.033 |
| Null | 136 | 1 | 18 | 73 | 36 | 18 | 0.15 | 0.03 | 0.007 |

Waits and moves, pooled: the chosen tiles, and the interest at the choice (`waits_vs_moves.csv`, `offer_selection.csv`):

| | n | cloud chosen (offered) | night | \|Δcloud\| from the tile before | z glance / grid / progress |
|---|---|---|---|---|---|
| curious, moves | 8,910 | 0.17 (0.23) | 0.008 | 0.12 | 0.71 / 0.69 / 0.44 |
| curious, waits | 90 | 0.28 (0.41) | 0.022 | 0.23 | 0.58 / 0.49 / **1.09** |
| Null, moves | 6,783 | 0.22 (0.22) | 0.006 | 0.19 | 0.03 / 0.03 / 0.00 |
| Null, waits | 136 | 0.38 (0.38) | 0.015 | 0.27 | 0.00 / 0.08 / −0.11 |

### Length, yield, movement (`walks.csv`, `offer_histogram.csv`)

| | curious w0 / w1 / w2 | Null w0 / w1 / w2 |
|---|---|---|
| distinct tiles per step | 0.80 / 0.75 / 0.81 | 0.75 / 0.72 / 0.82 |
| revisits (a cell seen before, any date) | 0.21 / 0.26 / 0.22 | 0.27 / 0.30 / 0.37 |
| share of steps at the largest radius | 0.21 / 0.15 / 0.23 | 0.28 / 0.32 / 0.02 |
| median step (moves), km | 16.6 / 16.0 / 17.2 | 16.6 / 19.7 / 14.4 |
| edge pull (top crop on the border ring; chance 0.75) | 0.78 / 0.77 / 0.79 | 0.82 / 0.81 / 0.80 |
| interest share at the choice, glance / grid / progress | 0.37 / 0.34 / 0.29; 0.39 / 0.36 / 0.26; 0.39 / 0.36 / 0.25 | (logged, not used) |

Offer kinds:
- Compass offers per step: 7.2 (Null) to 7.5 (curious). Some of the 8 targets snap to the same cell or into the sea.
- The 8 compass slots were taken evenly (1,061–1,165 per slot for curious).
- 7 steps used the fallback (the 8 nearest cells).

### Coverage of the world (`coverage.png`, `coverage.csv`)

| 18-day cycle from | cells imaged in it | cells with a pass on or after it |
|---|---|---|
| 1972-07-25 | 250,218 | 1,466,863 |
| 1973-07-20 | 331,196 | 1,143,089 |
| 1974-07-15 | 210,610 | 422,282 |
| 1976-07-04 | 203,946 | 356,958 |
| 1976-12-31 | 0 (Nov 1976 – Jan 1977: 2,810 acquisitions in all) | 210,954 |
| 1977-11-20 | 34,136 | 63,444 |
| 1977-12-26 (the last) | 35,645 | 35,645 |

### Compute (`projection.csv`)

Wall time per step from the logs, which includes the re-embedding every 100 steps:
- curious: median 1.38 s, rising about 0.28 s per 1,000 steps;
- Null: median 1.54 s, rising about 1.24 s per 1,000 steps. That fit is noisy: it includes the swapping phase.

| N per condition | curious walks (range) | Null walks (range) | wall time, both conditions, 2 side by side |
|---|---|---|---|
| 5,000 | 1 (1–2) | 2 (1–7) | 3.4–6.4 h |
| 10,000 | 2 (1–4) | 4 (2–14) | 6.9–12.8 h |
| 20,000 | 4 (2–8) | 7 (4–27) | 12.8–23.7 h |

Tiles per walk are projected to each walk's end by its clock rate, capped at 15,000 steps. The ranges are wide because walk length depends on the start region: 919 to 15,000+ steps.

Disk: the cache held at its 12 GB cap; 18–41 GB of the disk were free during the runs; a 3,000-step walk folder is ~60 MB (logs, latents, contact sheets).
- The cache held at its 12 GB cap. 31 GB of disk was free before the long phase, 18 GB after it started.
- A walk folder is ~150–250 MB (logs, latents, contact sheets).

## Findings

1. **The clock moves in stairs, and the world sets the stairs.**
   - Most steps offer no wait: the current cell has no later pass. The clock jumps when the walker finds a place the satellite kept returning to.
   - Coverage collapses in 1973–74, from 1.47 M cells with a future pass to ~422,000. The archive has a winter gap, November 1976 to January 1977.
   - Where the walk starts decides much of how fast its clock runs. In Quebec, a time offer came in 75 % of the Null's steps, and the Null ended by the clock in 919 steps. In Rondônia, 10 %.
   - Set by hand: the time offer (next pass only), the closest-date rule, T_end, the start list. Emerged: how long a walk takes to cross the mission, and where. *RQ1 (how an untasked traversal moves through an image already cut into scenes and passes); chapters 2, 5.*
2. **The curious walker lives far from its own time** (hint, 3 of 3 pairs).
   - It stands on tiles whose acquisition is a median of 379–1,343 days from its clock (Null: 0–1,078). It is offered a wait in fewer steps than the Null from the same start cell.
   - A reading, not yet a claim: it is drawn to places the satellite stopped visiting. Their closest acquisition is old, and they have no later pass, so its clock stalls there.
   - What draws it is not separated yet. Old acquisitions may differ in look (season, sensor state, L1GS), or sparse regions may simply be novel terrain.
   - Set by hand: the closest-date rule. Emerged: the distance between the walker's time and the time of what it sees. *RQ2 (how much of the attention follows the terrain, how much the archive's structure); chapters 7, 8.*
3. **Waiting is for learning, moving for novelty.**
   - The curious walker's waits have a progress z of 1.09, against 0.44 for its moves, while its novelty z is lower at waits (glance 0.58 against 0.71, grid 0.49 against 0.69).
   - A new date at a known place is not new to the eyes. It is learnable: the place's earlier image is in memory, and the new one teaches the grid network.
   - When a wait is available, the curious walker takes it about as often as chance overall: 0.21 and 0.19 above, 0.07 below.
   - Its waits are longer: 3.3 % jump more than a year, against 0.7 % for the Null.
   - Set by hand: the time offer is scored by the same eye and interest as the compass offers, with no bonus. Emerged: what a wait is chosen for. *RQ2; chapter 7.*
4. **Clear over cloud, again.** Pooled, the curious walker chooses less cloudy tiles than it is offered: 0.17 against 0.23 for moves, 0.28 against 0.41 for waits. The Null shows no gap (0.22 / 0.22, 0.38 / 0.38). This is the e12 finding, now on the clock world. Its waits still land on cloudier tiles than its moves (0.28 against 0.17), because time offers are cloudier on average (0.41). Set by hand: nothing about cloud. Emerged: the selection. *RQ2 (terrain against weather); chapter 8.*
5. **The archive loses a band** (an apparatus finding, not a walker one).
   - From April 1977, band 4 (green) of nearly every Landsat 1 scene is uncalibrated: the MTL gives NULL, and the pixels are a constant DN, e.g. 19 in `LM01_L1GS_086018_19770525`. That is 1,293 of the 1,305 scenes read from that period, both L1TP and L1GS.
   - The store reads such a band as missing reflectance, so the CIR view's green channel is black there. The last nine months of the world look different from the rest.
   - Not yet seen: whether novelty seeks or flees them. The long phase avoids most of them, since it ends when the clock enters 1977.
   - Set by hand: how a missing calibration is shown (a default; decision 4). *RQ2 (where data and phenomenon come apart), RQ3 (what a GAN would learn from these tiles); chapters 5, 6.*
6. **Movement looks like the Null's.**
   - Median step 16–17 km for both walkers.
   - Compass slots taken evenly.
   - Revisits are lower for curious (0.21–0.26 against 0.27–0.37; a hint).
   - Top crop on the edge 0.77–0.79, chance 0.75. The Null's chosen tiles show 0.80–0.82: on tiles chosen at random, the most novel crop sits on the edge more often.
   - *RQ2; chapter 8 (Tobler and cluster readouts follow at replication).*

## Against the predictions (122–131)

| # | Prediction | Outcome |
|---|---|---|
| 122 | The Null ends by the clock in ≥ 2 of 3 walks, at 300–2,500 steps | **Wrong.** 1 of 3 (w2, 919 steps). The other two were capped; projected 3,472 and 8,863 steps. I underrated how sparse later passes are. |
| 123 | The curious walker waits less than the Null when it can; so its walks are longer, one capped | **Wrong.** P(wait \| available) is below chance in 1 of 3 walks. The curious walks were all capped (as were two Nulls), and the cause is different: the walker is rarely *offered* a wait (finding 2), not that it declines them. |
| 124 | Curious waits change the cloud more than Null waits | **Wrong.** \|Δcloud\| at waits is 0.23, against 0.27 for the Null. |
| 125 | Curious chooses clearer tiles than offered, for waits and moves; the Null shows no gap | **Right** (finding 4). |
| 126 | Δt: mode 18 days, median 18–120, under 5 % 1-day waits | **Partly.** Mode 18 and median 18: right. 1-day waits are 12–15 %: wrong, because sidelap reaches lower latitudes than I assumed. |
| 127 | Every walk has a stretch of 25+ steps without a time offer | **Right.** 99–2,073. |
| 128 | ≥ 0.6 distinct tiles per step; N = 10,000 needs under 30 walks | **Right.** 0.72–0.82; 2 (curious) and 4 (Null) walks, ranges up to 14. |
| 129 | 1–2.5 s a step; generation 1 at 10,000 under 72 h | **Right.** 1.5–1.75 s wall; 7–13 h. |
| 130 | Top crop on the edge 0.70–0.80 | **Mostly right.** Curious 0.77–0.79. The Null is 0.80–0.82, slightly above. |
| 131 | No crash, < 1 % dropped, the cache under its cap, no pinned tile evicted | **Wrong.** See below. The dropped share (1 in 117,000), the cap and the pins held. |

Not foreseen: the coverage collapse of 1973–74, the winter gap of 1976–77, the walker living far from its clock (finding 2), the lost green band (finding 5), and that curious walks stall in late 1977 rather than at the start.

## What broke, and what was fixed (all committed; none changes what a walk sees, except the last)

1. **A walk hung** at 0 % CPU: the main thread was stuck on a lock in the store.
   - Fix: a reentrant lock, with callbacks registered outside it.
   - Also added: GDAL HTTP timeouts, and a stack dump to the walk's log on a 15-minute stall or on SIGUSR1.
2. **Three walkers swapped** on the 16 GB Mac (15 GB of swap); starved fetch threads dropped offers.
   - Two walkers now run side by side.
   - The tile cache in RAM went from 8,000 to 2,000 tiles; GDAL's block cache is 64 MB.
3. **My own bug:** GDAL_CACHEMAX was passed as a string, and every remote read failed for 40 minutes.
   - No checkpoint was written in that time, and all walks resumed from earlier ones.
   - A test now opens the store's GDAL settings.
4. **Fresh and cached tiles differed.** A tile was rendered from float32 when fetched and from float16 when read from the cache, so a cold and a warm cache gave different walks. This also applies to the e12 walks. Fixed before the dry runs; resume is now bit-identical across cold and warm caches (tested).
5. **The uncalibrated green band** (finding 5) raised an error on every read of a 1977 scene. The store retried six times with backoff, then dropped the offer.
   - Walks could not enter April 1977 or later at all.
   - curious w0 and w2 and Null w1 had lost such offers; they were rerun on the fixed store. Their old runs are in `runs/dryrun_prefix/`.
   - The rerun of curious w0 shows how much this mattered. Its old run's clock stopped at 1976-09-16; the rerun reached 1977-10-02 by step 1,000.

## For review (Gate B: decisions for Moe; nothing below has been applied)

1. **T_end.** The brief sets 1977-12-20.
   - No curious dry run reached it within 3,000 steps: all three stall in October–November 1977, where few cells get another pass.
   - Under the brief's rule and a 15,000-step cap, some curious walks will be capped. Projected: 1 of 3 here.
   - The long phase now uses 1977-01-01 (Moe, 2026-11-13).
   - Keep 1977-12-20 for generation 1, use 1977-01-01, or something else?
2. **The step cap,** 15,000. It is reached only by walks that stall. A capped walk keeps being counted until the cap, so it contributes many tiles from one late region.
3. **N:** 5,000, 10,000 or 20,000 tiles per condition.
   - Walk lengths vary by start region, so a condition's pool comes from few walks: at N = 10,000, about 2 curious and 4 Null walks.
   - One long, stalled walk can dominate a pool.
4. **The lost green band (April 1977 on).** The default for now: the band is missing (NaN), the green channel black, the scene listed. Alternatives:
   - (a) keep the default;
   - (b) leave those products out of the world;
   - (c) show the DN without calibration. That would be equalising, against "the archive as stored".
5. **Where generation 1 runs.** The Mac can do N = 20,000 for both conditions in about 13–24 h with two walkers and the 12 GB cache cap. The PC would be faster and would not compete with daily use.
6. **Expectations for generation 1:** dated in `expectations.md` (entry 2026-11-13), with T_end, cap and N marked "pending Moe" and my predictions 132–139. Section 7 does not start until you approve.
