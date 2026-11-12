# Brief: Landsat 1 wanderer v2, from build to the generation-1 walks

*Written 2026-11-12*

## Goal

Build the final Landsat 1 world (all acquisitions per cell, the wanderer's clock), finish walker v2 (two eyes), and check it with dry runs. Then run curious and Null wanderers until their time runs out, walk after walk, until each condition's pooled paths reach the target tile count N for generation 1. **GAN training is out of scope for this brief.**

The architecture is **frozen**. Don't add mechanisms, drives or offers. **There is no death:** don't build surprise-based termination. Surprise is still computed and logged, nothing more. If something looks wrong, log it in the report and carry on, or stop at the next gate.

Start by reading the repo, CLAUDE.md, `notes/brief_landsat_pipeline.md` and the existing walker v2 code, to see what's already built. Reuse it; don't rewrite. Remove or disable any existing death code paths, so they can't end a walk.

## 1. World index

- **Source:** Landsat 1 MSS, the whole mission, from the source the existing pipeline uses, on the Major TOM grid.
- **For each cell, list all acquisitions.** Keep **one product per acquisition date**: if several processing levels exist for the same date, pick deterministically (highest level available, ties by product ID) and log which. Across dates, every processing level is allowed.
- **Night scenes** stay in, flagged.
- **Store as** a cell → sorted list of `(date, product_id, level, night_flag)`, e.g. one parquet file. This index is the world. Report how many cells there are, the distribution of passes per cell, the global first and last dates, and the cells with an acquisition in the first 18-day cycle (the start pool).
- **Tiles are fetched lazily and cached on disk.** Offers can be prefetched one step ahead.
- **View:** three-band CIR (nir08 / red / green), with one fixed tone and stretch shared by the walker and every rendering. Measure quirks from pixels (cloud fraction, scan-line dropouts, saturation, night) and log them. Never feed them to the walker.

## 2. Clock and offers (the core of this brief)

State per step: current cell `c`, clock `t`, current tile date `d_c`.

- **Start:** the start cell comes from the shared start list (section 6), and `t` = that cell's first acquisition date. Each walk is a new wanderer: fresh encoders from random weights, empty memories.
- **Compass offers:** eight grid directions, radius from the drive as in walker v2. Each offer cell is shown at **the acquisition closest to `t`** (an exact tie goes to the earlier pass). Cells with no acquisitions follow the existing coverage-gap rule. **Sideways moves never change `t`.**
- **Time offer:** the first acquisition at `c` with date `> max(t, d_c)`. Choosing it sets `t` to that date, and the wanderer stays on `c`, now seeing the new tile. **Next pass only,** never scaled by boredom. If no such acquisition exists, no time offer is given (eight offers that step).
- **Returns:** a revisited cell is shown at the pass closest to the current `t`.
- **Interest and choice:** the time offer is scored by the same eye and interest function as the compass offers, and drawn with the same temperature (0.5). No bonus, no penalty.
- **Memory per place:** a wait shows the same place at a new date, compared against that place's memory as usual.

## 3. Ending

- **End rule (default):** the walk ends at the first step where `t ≥ T_end`, with `T_end` = the archive's last acquisition date minus 18 days. That's Landsat 1's last repeat cycle; from there the satellite won't return anywhere. Make `T_end` a config value. Moe confirms or changes it at Gate B.
- **Step cap:** a walk that hasn't ended by the cap (config, default 15,000) stops there and is flagged `capped`. Never shorten or extend a walk after the fact.

## 4. Logging

- **Per step:** step, cell, tile date, clock, offset (tile date − clock), chosen offer (compass direction or `time`), Δt if a wait, number of offers available and whether a time offer was among them, every offer's cell, date and interest components (z-glance novelty, z-top-k crop novelty, z-learning progress), learning progress, surprise (glance, pooled grid, max grid; logged only), and the pixel quirks of the current tile (cloud fraction, night flag, dropouts).
- **Per walk:** walk ID, condition, seed, start cell, start and end clock, number of steps, end reason (`time` or `capped`), and unique tiles seen.
- **Checkpoints** (encoders, memories, RNG, clock) every 1,000 steps, so a walk can resume.
- **Renders:** a contact sheet every 500 steps.

## 5. Tests (Gate A)

Unit tests for:
- closest-date lookup and the tie rule;
- the time offer: strictly after `max(t, d_c)`, and absent when there's no later pass;
- sideways moves leave `t` unchanged;
- a return after a wait shows the later pass;
- one product per date;
- the Null's choice is uniform over the offers available that step;
- the end rule fires at `T_end`, and the cap fires;
- no death code path can end a walk.

Plus a 50-step smoke run of both walkers.

**Gate A:** all tests pass and the smoke run completes. Then continue.

## 6. Dry runs (Gate B)

- **Start list:** a seeded, ordered list of start cells drawn from the start pool. Both conditions use the same list, in the same order.
- **Runs:** curious and Null, the first 3 start cells each. Every walk runs until it ends or hits a 3,000-step dry-run cap.
- **Report in `notes/dryrun_report.md`:**
  - **Time:** clock against step for each walk; share of waits (curious against 1/9); Δt distribution; cloud fraction and night share of waits compared with sideways moves; projected steps until `T_end` for each condition, with uncertainty.
  - **Walk length and yield:** steps and unique tiles per walk. From this, how many walks each condition would need to reach N = 5,000, 10,000 and 20,000 unique tiles.
  - **Movement:** offer-type histogram, step lengths, revisits, edge pull.
  - **Compute:** seconds per step, and projected wall time for generation 1 at each N. If any projection exceeds about 72 h in total, propose reductions. Don't apply them on your own.
  - **Anything that looks broken,** especially curious walks that barely wait and would run into the cap.

**Gate B: stop here.** Write a dated entry `expectations.md`: `T_end`, the step cap, the target N, and his expectations for the generation-1 walks. **Don't start section 7 until that entry is committed and you've gotten Moe's approval to continue.** 

## 7. Generation-1 walks

- **Walks:** for each condition (curious, Null), walk start cells from the shared list in order, one new wanderer per start cell, until the condition's pooled unique tiles reach N. The last walk always runs to its end; don't cut it to hit N exactly.
- **Order:** run the conditions interleaved (curious 1, Null 1, curious 2, …) so a stopped job leaves comparable partial sets.
- **Output:** `runs/gen1/<condition>/<walk_id>/` with the step log, offers log, checkpoints, renders, and the config with git hash. Also `runs/gen1/<condition>/manifest.parquet` listing every tile (walk ID, step, cell, date, novelty at encounter), with walks as separate ordered sequences, not interleaved.
- **`notes/gen1_report.md`:**
  - the same readouts as the dry runs, over all walks;
  - the walkers compared over matching clock-date stretches, with clock reported next to step everywhere;
  - novelty split into what came from moving and what came from waiting;
  - end reasons per walk (`time` or `capped`);
  - for each condition, a rendered strip of the last 50 steps of one walk.

## Not in this brief

GAN training, the occupant twin, naming, any change to the eye or drives, the low-temperature variant, and the rule for how time ends in a GAN's world (generation 2 onward). That rule needs a decision from Moe first.