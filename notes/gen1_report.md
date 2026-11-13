# Brief v2, section 7: the generation-1 walks — report (2026-11-13)

Brief: `notes/brief_landsat_v2_run.md` (section 7 and the handoff). Predictions 143–151: `notes/06_characters/expectations.md`. Tables and figures: `notes/gen1/gen1/` (made by `analysis/gen1/readouts.py gen1`, run by the pipeline). Walks: `runs/gen1/<condition>/w00k/`. Packages: `paths/g1/<condition>/`; manifests and checksums are in `notes/gen1/packages/` (tag `g1-paths`, commit `081fc77`). Pipeline: `scripts/g1_pipeline.py` and `scripts/g1_lib.py`; history in `runs/g1/events.log`. Device: the PC (Windows); walks on CPU with 3 threads; walker at commit `1c8dc31`.

**The world was rebuilt on the PC and checked against the Mac** (`runs/g1/world_check.md`):
- After Moe's `grid.parquet`, all 14 `clock.json` values match and `startlist` reproduces the committed list exactly.
- A first build from the PC's own grid failed the start-list check. PROJ rounds cell centres differently in the last bit on macOS and Windows, which reorders cells with tied latitudes. Nothing walked on that world.

## Short version

- **Six walks, all ended by `linger`, none capped, no restarts, no offer dropped.** Each condition needed three wanderers (start cells 0–2) to reach N = 10,000 pooled tiles. The walks lasted 2,617–8,989 steps; 16:20–23:16 in wall time (about 7 h), two walkers side by side.
  - Curious: 6,943 + 2,999 + 5,196 tiles; the package was cut at w002 step 308.
  - Null: 6,455 + 1,969 + 5,204 tiles; the package was cut at w002 step 2,144.
- **q worked as built.** The time offer came through on 9.7 % of the steps where a later pass existed, in both conditions. Lingering added 1.21–1.25 × the tiles a walk had when its clock reached 1977, against the 1.22 assumed. For start cell 0 the calibration landed within 3 %: curious w000 had 5,672 tiles to 1977 against 5,490 predicted.
  - But start cells 1 and 2 reached 1977 with only 43–50 % of the predicted tiles. Scaling the q = 1 dry run by 1/q held for one start cell out of three.
- **Waiting almost vanished.** With q = 0.10, a wait was possible on only 1.5–4.3 % of steps.
  - Curious waited 57 times in 18,310 steps, the Null 47 times in 18,405.
  - When a wait was offered, curious took it about as often as the Null: P(wait | offered) 0.114 against 0.134; uniform choice would give about 0.12.
  - The thinned time offer turns both walkers into movers through space. Their clocks advance at nearly the same pace.
- **"Far from its own time" is the archive, not the walker.** The median |tile date − clock| is 612 days for curious and 625 for the Null (pooled).
  - Both clocks spend most of their steps in 1976 while their tiles date mostly from 1973–74.
  - The cause is the world: after mid-1974 most cells are never imaged again, so the acquisition closest to a 1976 clock is usually an old one.
  - The dry-run hint (curious far from its time, the Null not) does not survive a matched comparison.
- **Clear over cloud holds** (pooled over three walks per condition):
  - curious compass choices have cloud 0.155 against 0.214 offered;
  - the Null's choices have 0.222 against 0.214;
  - in every pair, the curious walk stood on less cloudy tiles than the Null (0.078–0.179 against 0.205–0.234).
- **Waits for learning holds again:** at the curious walker's waits the progress z is 0.91, against 0.41 at its moves. That's on 57 waits. The Null's waits have lower interest than its moves on every component.
- **The era confound is small, against prediction 145.** The two packages cover nearly the same clock and tile-date range:
  - median tile date 1973-12-24 (curious) against 1974-01-01 (Null);
  - 18.4 % against 16.9 % of tiles encountered with the clock in 1977;
  - 2.1 % against 2.2 % of tiles from April 1977 on (the lost green band).
  - The q thinning, shared by both, set the pace of both clocks.
- **Revisits use up 16 % of the curious ESS** (counts-only ESS 0.836 N); prediction 151 held. The curious walker revisits less than the Null in every pair (revisit share 0.157–0.215 against 0.245–0.291).
- **One walk per condition and start cell: every curious-against-Null comparison here is three pairs on three start cells.** These are hints, not leads (CHARTER: four seeds for a lead).

## What was run

- **Walks:** configs `configs/gen1/curious.yaml` and `null.yaml` as committed:
  - q = 0.10, lingering from 1977-01-01, T_end 1977-12-20, the 40,000-step guard;
  - start cells 0, 1, 2 of the shared list: 156D_664L (Rondônia), 280U_59R (southern Algeria), 577U_514L (Quebec).
- **Order:** the supervisor started a condition's next wanderer whenever its last walk ended with pooled unique tiles below 10,000, counting start tiles as the package does.
  - Curious: w000 started 16:20 and ended 19:36 at 6,944 pooled; w001 ended at 9,762 pooled; w002 ended at 14,182 pooled.
  - Null: w000 started 16:21 and ended 19:55 at 6,456 pooled; w001 ended at 8,385; w002 ended at 13,411.
  - Every walk ran to its own end.
- **Packages** (the handoff), 10,000 tiles each, at 128 px:
  - built by `scripts/g1_package.py`;
  - verified by `scripts/g1_verify.py` (checksums, N, start lists, interest components);
  - render check passed on both: 20 tiles re-fetched from Planetary Computer into an empty cache, byte-identical;
  - frozen at `g1-paths`.
- **Before the walks:** Windows-only fixes outside the walk (the SIGUSR1 hook, the cache cap's pin paths). Smoke runs on this machine are not reported.

### Set by hand, and left to emerge

| Set by hand (premises) | Left to emerge |
|---|---|
| q = 0.10 (both conditions) | when and where each walker waits; the offset of its tiles from its clock |
| lingering from 1977-01-01 for the walk's own steps per year; T_end; the 40,000-step guard | how long each walk lasts and how it ends: all six by `linger` |
| N = 10,000; the cut at the N-th unique tile, start tiles counted; a new wanderer only if short of N | how many wanderers each condition needed (three); where each package was cut; the era each covers |
| the shared, seeded start list | the difference between curious and Null on each start cell (one pair per cell) |
| the eye, the drive, temperature 0.5, the radius rule (frozen since e12) | everything in the readouts below |

## Tables

### The walks (`walks.csv`, figure `clock_vs_step.png`)

| walk | start | steps | end clock | end | 1977 reached at step | tiles to 1977 | unique tiles | waits | P(wait \| offered) | median \|offset\| (days) | revisit share | cloud (stood on) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| curious w000 | 156D_664L, 1972-07-29 | 8,575 | 1977-06-09 | linger | 6,995 | 5,672 | 6,943 | 21 | 0.114 | 762 | 0.199 | 0.179 |
| curious w001 | 280U_59R, 1972-08-11 | 3,746 | 1977-06-25 | linger | 3,051 | 2,422 | 2,999 | 12 | 0.194 | 744 | 0.215 | 0.078 |
| curious w002 | 577U_514L, 1972-08-02 | 5,989 | 1977-07-23 | linger | 4,883 | 4,280 | 5,196 | 24 | 0.094 | 44 | 0.157 | 0.168 |
| Null w000 | 156D_664L | 8,989 | 1977-07-17 | linger | 7,333 | 5,150 | 6,455 | 18 | 0.133 | 518 | 0.291 | 0.234 |
| Null w001 | 280U_59R | 2,617 | 1977-02-01 | linger | 2,132 | 1,574 | 1,969 | 8 | 0.167 | 845 | 0.253 | 0.228 |
| Null w002 | 577U_514L | 6,799 | 1977-08-26 | linger | 5,544 | 4,184 | 5,204 | 21 | 0.125 | 816 | 0.245 | 0.205 |

- Waits pooled: 57 for curious, 47 for the Null.
- Unique tiles exclude the start tile. Tiles to 1977 include it.
- Wall time was 0.89–1.06 s a step, two walkers side by side. Of 270,145 offers fetched, none were dropped.

### Novelty from moving against waiting (`waits_vs_moves.csv`; pooled; z at the choice)

| | n | z glance | z grid | z progress | I | cloud | night |
|---|---|---|---|---|---|---|---|
| curious, moves | 18,253 | 0.70 | 0.67 | 0.41 | 1.77 | 0.155 | 0.006 |
| curious, waits | 57 | 0.87 | 0.67 | 0.91 | 2.45 | 0.203 | 0 |
| Null, moves | 18,358 | 0.00 | 0.01 | 0.00 | 0.01 | 0.222 | 0.007 |
| Null, waits | 47 | −0.27 | −0.32 | −0.35 | −0.94 | 0.301 | 0.064 |

Interest shares at the curious choice: glance 0.38, grid 0.35, progress 0.26, across all three walks. These are the dry runs' values.

### Offered against chosen (`offer_selection.csv`)

| | kind | offered | chosen | take rate | cloud offered | cloud chosen |
|---|---|---|---|---|---|---|
| curious | compass | 135,584 | 18,253 | 0.135 | 0.214 | 0.155 |
| curious | time | 502 | 57 | 0.114 | 0.297 | 0.203 |
| Null | compass | 133,708 | 18,358 | 0.137 | 0.214 | 0.222 |
| Null | time | 351 | 47 | 0.134 | 0.327 | 0.301 |

### Δt of waits (`dt.csv`, figure `wait_dt.png`)

Curious: median 21 days, mean 94; 14 % exactly one 18-day cycle; 16 % longer than 180 days. Null: median 34 days, mean 113; 2 % one cycle; 21 % longer than 180 days.

### Matched clock stretches (`matched_clock.csv`; half-years of clock, all walks pooled)

| clock | steps (curious / Null) | wait possible (share of steps) | median \|offset\| days | cloud chosen | median move km |
|---|---|---|---|---|---|
| 1972-H2 | 762 / 529 | 1.00 / 0.99 | 0 / 1 | 0.19 / 0.17 | 14 / 14 |
| 1973-H1 | 864 / 1,549 | 0.92 / 0.43 | 2 / 13 | 0.16 / 0.23 | 15 / 15 |
| 1974-H1 | 3,742 / 1,577 | 0.32 / 0.16 | 67 / 109 | 0.15 / 0.20 | 17 / 18 |
| 1975-H2 | 1,577 / 3,189 | 0.24 / 0.14 | 610 / 649 | 0.16 / 0.22 | 17 / 18 |
| 1976-H1 | 7,700 / 6,609 | 0.21 / 0.14 | 777 / 831 | 0.14 / 0.21 | 16 / 19 |
| 1977-H1 | 2,277 / 513 | 0.09 / 0.09 | 1,405 / 1,013 | 0.17 / 0.27 | 15 / 61 |
| 1977-H2 | 1,107 / 2,886 | 0.03 / 0.08 | 1,449 / 1,183 | 0.17 / 0.24 | 15 / 21 |

- The table omits 1973-H2 (Null only, 933 steps) and 1975-H1 (281 / 620 steps); the CSV has them.
- "Wait possible" is `time_exists`: a later pass exists. It comes through with probability q.
- In 1975-H1 the curious walker's median move was 1,663 km (281 steps): the radius rule at its maximum, in a sparse part of the archive. Not followed up.

### The era of each package (`package_era.csv`, figure `package_era.png`)

| | clock at first encounter: p5 / p50 / p95 | tile date: p5 / p50 / p95 | tiles dated 1972 / 73 / 74 / 75 / 76 / 77 | from 1977-04 | green channel black | clock ≥ 1977 |
|---|---|---|---|---|---|---|
| curious | 1974-01-01 / 1976-02-12 / 1977-06-25 | 1972-08-21 / 1973-12-24 / 1976-06-27 | 1,180 / 4,044 / 3,035 / 494 / 1,034 / 211 | 212 (2.1 %) | 241 (2.4 %) | 18.4 % |
| Null | 1973-02-07 / 1975-11-14 / 1977-07-17 | 1972-09-05 / 1974-01-01 / 1976-10-17 | 986 / 3,976 / 3,367 / 555 / 873 / 243 | 220 (2.2 %) | 264 (2.6 %) | 16.9 % |

"Green channel black" counts packaged tiles whose rendered green channel is 0 throughout. That includes the 1977 band loss and some earlier tiles of fill or uncalibrated scenes.

Last-50-step strips: `last50_curious_curious_w000.png`, `last50_null_null_w000.png`.

## Findings

1. **The thinned time offer behaves as specified, and the q calibration holds for the start cell it was built on.** Offered/exists = 0.097 in both conditions. Lingering adds 1.21–1.25 × the tiles to 1977 (1.22 assumed). Tiles to 1977 at q = 0.10 against 1/q × the q = 1 dry run: 5,672 against 5,490 (start cell 0), 2,422 against 4,850 (cell 1), 4,280 against 9,900 (cell 2). So the clock's pace per step does not simply scale with q from one start cell to the next.
   - *Set by hand:* q, the linger rule. *Emerged:* the walk lengths, and the departure from scaling at cells 1–2.
   - *RQ1, chapters 2 and 5.*
2. **Under q = 0.10, the wanderers became movers: about 0.3 % of steps are waits in both conditions, and the curious walker takes an offered wait no more often than the Null** (0.114 against 0.134; uniform ≈ 0.12). The dry runs' curious P(wait | offered) was 0.07–0.21 at q = 1. Waiting is now a rare event, and how much time a walk crosses is set by the horizon, not chosen.
   - *Set by hand:* q (Moe's reason: let the wanderer explore one period more). *Emerged:* the walkers' indifference between waiting and moving when both are offered.
   - *RQ1/RQ2, chapters 5 and 7.*
3. **"Far from its own time" belongs to the archive.** Pooled, the median |offset| is 612 days (curious) against 625 (Null). By matched clock stretch, curious is lower than the Null in 1973–1976 and higher in 1977. Both offsets grow with the clock (0 in 1972, ~800 days in 1976, 1,000–1,450 in 1977), following the coverage collapse after mid-1974. The dry-run hint (curious 379–1,343 against Null 0–1,078) came from walks whose clocks sat in different eras.
   - *Set by hand:* the closest-acquisition rule. *Emerged:* the offset curve, shared by both conditions.
   - *RQ1/RQ2, chapters 5 and 6.* A negative result.
4. **Clear over cloud: the curious walker chooses less cloudy tiles than it is offered; the Null does not.**
   - Compass choices: 0.155 against 0.214 offered for curious; 0.222 against 0.214 for the Null.
   - Waits: 0.203 against 0.297 for curious.
   - It held in every matched clock stretch except the first (1972-H2: 0.19 against 0.17) and on all three start cells. This is the e12 finding again, with the same detector (QA cloud, never seen by the walker).
   - *Set by hand:* nothing about cloud. *Emerged:* the selection.
   - *RQ2, chapters 6 and 7.* Three pairs: a hint, the most consistent one.
5. **Waits are taken for learning.** At the curious walker's 57 waits the progress z is 0.91, against 0.41 at its moves. Grid novelty is the same (0.67 / 0.67) and glance novelty is higher (0.87 / 0.70). At the Null's 47 waits every component is below its moves, so a wait offer is, on average, a less interesting offer. The curious walker waits when the later pass of a place promises progress.
   - *Emerged.* *RQ2, chapter 7.* 57 events: a hint.
6. **The curious walker revisits less** (cell revisit share 0.157–0.215 against 0.245–0.291 in each pair) **and covers more cells per step** (unique cells/steps 0.79–0.84 against 0.71–0.76, per walk).
   - *Emerged.* *RQ2, chapter 8.*
7. **The two packages share their era.** Their tile-date and clock distributions nearly coincide, and both include about 2 % of tiles with the lost green band. The era confound stated at Gate B is small in generation 1. Two things shared by both conditions set the era: the thinned clock pace and the three start cells. Curation did not.
   - *Set by hand:* q, N, the start list. *Emerged:* the overlap.
   - *RQ3, chapter 4.* It strengthens what the GAN comparison can claim.

## Against the predictions (143–151)

| # | prediction | outcome | right / wrong, and why |
|---|---|---|---|
| 143 | Curious needs two walks; w000 ends by linger at 5,000–9,000 tiles with 4,000–8,000 to 1977; w001 brings the pool to 10,000; neither capped | w000: linger, 6,943 tiles, 5,672 to 1977; w001 brought the pool to 9,762; w002 was needed; none capped | **Partly right.** w000 landed inside every range, and the 549/q scaling held to 3 %. Wrong on the number of walks: start cell 1 yielded half of what its dry run implied, so the pool fell 238 tiles short. |
| 144 | The Null needs one walk, runs long (capped or linger after step 30,000) with ≥ 25,000 tiles; package cut before step 15,000 | three walks; w000 ended by linger at 8,989 steps with 6,455 tiles; the package was cut in w002 | **Wrong.** I expected the Null's clock to crawl, as in the dry runs, where most of its steps had no time offer. Under thinning both walkers wait rarely, so the Null's clock kept pace with the curious one. |
| 145 | The era confound is large: the Null package's last clock is before 1974-07-01; ≥ 5 % of curious tiles at clock ≥ 1977 | Null last clock 1977-07-17; curious 18.4 % at ≥ 1977 (Null 16.9 %) | **Wrong** on the Null; right on the curious share. The era confound is small (finding 7). |
| 146 | Thinning works: offered/exists 0.08–0.12 in both; curious P(wait \| offered) within × 2 of its dry-run value | 0.097 and 0.097; 0.114 against the dry-run pool of about 0.16 | **Right.** |
| 147 | The lost green band only in the curious package: 1–10 % of tiles from April 1977 on; none in the Null package | curious 2.1 %; Null 2.2 % | **Wrong** on the Null (it reaches 1977 too); right on the curious range. |
| 148 | The curious walk's median \|tile date − clock\| > 365 days and above the Null's | 612 against 625 days | **Wrong** on the comparison. The offset is an archive effect shared by both (finding 3). |
| 149 | Progress z higher at waits than at moves (curious) | 0.91 against 0.41 | **Right**, on 57 waits. |
| 150 | Curious chosen compass tiles less cloudy than offered; Null \|chosen − offered\| < 0.02 | 0.155 against 0.214; Null +0.008 | **Right.** |
| 151 | Counts-only ESS of the curious package 0.78–0.88 N | 0.836 N | **Right.** |

Five right (146, 149, 150, 151, and 143 in part), four wrong (144, 145, 147, 148). Three of the wrong ones share one cause: I assumed the Null's clock would stay slow under thinning, as it was at q = 1.

## For review

- **The q calibration at start cells 1–2.** Scaling with q held for cell 0 and fell to about half for cells 1 and 2. If later generations need a target length per walk, q from one start cell is not enough. This is not a change I'd propose for generation 1; the walks are done.
- **Waiting under q = 0.10.** With 57 and 47 waits, everything about waiting rests on very few events: findings 2 and 5, and the Δt table. If waiting matters for the thesis (RQ1: waiting against moving), a q between 0.10 and 1 is worth considering for later generations. That's your call.
- **"Far from its time"** should leave the list of curious-walker traits (STATE, RQ2). It belongs with the archive's coverage (RQ1).
