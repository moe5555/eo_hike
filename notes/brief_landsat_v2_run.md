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
- **The thinned time offer (Moe, 2026-11-13; `notes/gen1/time_offer_rule.md`):** when a later pass exists, the time offer comes through with probability `q` (`time_offer_p`), drawn each step from its own random stream (`time`). The Null is thinned the same way. For generation 1, **q = 0.10** (the calibration is in the rule note). Log `time_exists` next to `time_offered`. Every finding about time names q.
- **Returns:** a revisited cell is shown at the pass closest to the current `t`.
- **Interest and choice:** the time offer is scored by the same eye and interest function as the compass offers, and drawn with the same temperature (0.5). No bonus, no penalty.
- **Memory per place:** a wait shows the same place at a new date, compared against that place's memory as usual.

## 3. Ending

- **End rule:** the walk ends at the first step where `t ≥ T_end`, with `T_end` = the archive's last acquisition date minus 18 days: **1977-12-20** (Moe, Gate B, 2026-11-13). That's Landsat 1's last repeat cycle; from there the satellite won't return anywhere. `T_end` is a config value.
- **Lingering in the last period (Moe, 2026-11-13):** when the clock first reaches **1977-01-01** (`linger_from`), the walk may stay L more steps, L = steps so far / years from its start clock to 1977-01-01 (its own pace per year of clock). When those are used up, the walk ends (`linger`).
- **Step guard:** a walk that hasn't ended by **40,000 steps** (`steps`) stops there and is flagged `capped`.
- The walk ends at whichever of `linger`, `time` or `capped` comes first. Never shorten or extend a walk after the fact.

## 4. Logging

- **Per step:** step, cell, tile date, clock, offset (tile date − clock), chosen offer (compass direction or `time`), Δt if a wait, number of offers available and whether a time offer was among them, every offer's cell, date and interest components (z-glance novelty, z-top-k crop novelty, z-learning progress), learning progress, surprise (glance, pooled grid, max grid; logged only), and the pixel quirks of the current tile (cloud fraction, night flag, dropouts).
- **Per walk:** walk ID, condition, seed, start cell, start and end clock, number of steps, end reason (`time`, `linger` or `capped`), q, the step at which lingering began and its length L, and unique tiles seen.
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

*Decided by Moe at Gate B, 2026-11-13: T_end 1977-12-20, lingering from 1977-01-01, the 40,000-step guard, q = 0.10, N = 10,000, the package cut at N, the lost green band kept. Configs: `configs/gen1/curious.yaml`, `configs/gen1/null.yaml`.*

- **Walks (Moe):** generation 1 is meant to be **one walk per condition**, configured (through q) to end somewhere between about 8,000 and 15,000 unique tiles. For each condition:
  - walk 1 starts at start cell 0 and runs to its own end;
  - if it ends with fewer than N = 10,000 unique tiles, a second wanderer starts at start cell 1 and runs to its end, and so on, until the pooled unique tiles reach N;
  - each walk always runs to its end. Only the path package is cut at N (addendum below).
- **Order:** curious and Null run side by side (walk 1 of each), then any second walks, so a stopped job leaves comparable partial sets.
- **Output:** `runs/gen1/<condition>/<walk_id>/` with the step log, offers log, checkpoints, renders, and the config with git hash. The path packages (addendum) are built from these.
- **`notes/gen1_report.md`:**
  - the same readouts as the dry runs, over all walks;
  - the walkers compared over matching clock-date stretches, with clock reported next to step everywhere;
  - novelty split into what came from moving and what came from waiting;
  - end reasons per walk (`time`, `linger` or `capped`), and where each package was cut;
  - for each condition, a rendered strip of the last 50 steps of one walk;
  - **the era of each package:** clock and tile-date distributions of the N packaged tiles, side by side (see the stated limitation below).
- **Limits of what generation 1 can show:** one walk per condition, from one start region, is a single wanderer, not a sample. Anything about the curious walker against the Null from these walks is a hint, never a lead.

## Not in this brief

GAN training, the occupant twin, naming, any change to the eye or drives, the low-temperature variant, and the rule for how time ends in a GAN's world (generation 2 onward). That rule needs a decision from Moe first.

# Addendum to `notes/brief_landsat_v2_run.md`: the handoff to generation one

*13 Nov 2026; Gate B decisions written in the same day. The walks and the GANs are now separate briefs. This section is the contract between them. `notes/brief_gan_g1.md` takes exactly what is defined here and nothing else.*

## What the walk brief must deliver

The walks are an experiment in their own right (RQ2): predictions, readouts and a report in the usual format. Generation one only begins once they're finished. Their last job is to freeze two path packages.

### Walks to N

- **N = 10,000** unique tiles per condition, each a (cell, acquisition date) pair (Moe, 2026-11-13; dated in `notes/06_characters/expectations.md`). Both packages hold exactly N.
- **Conditions:**
  - curious: two eyes, top-4, w_glance 1;
  - the compass Null: uniform over all offers that come through, the thinned time offer included.
  - Both with q = 0.10, lingering from 1977-01-01, T_end 1977-12-20, the 40,000-step guard (section 3).
- **New wanderers:** one walk per condition is the intent; a second (third, …) wanderer from random weights follows only if the pooled paths are still short of N when a walk ends (section 7).
- **Start cells:** both conditions walk the same ordered list of start cells, drawn (seeded) from cells with an acquisition in the mission's first 18-day cycle. The i-th walk of each condition starts at the i-th start cell.
- **Cutting the package, not the walk (Moe):** every walk runs to its own end and is reported in full, with its own end reason. The package takes encounters in walk order and stops at the step where the N-th unique tile is reached. Where it was cut (walk, step, clock) is logged in the manifest.
- **The archive as stored:** nothing is cut from the data. Tiles with fill, stripes, saturation, cloud, night, and the lost green band of 1977 (read as missing: a black green channel) go into the package exactly as the walker saw them (Moe, 2026-11-13).
- **Devices:** walks may run on either machine. Note which one in the log.

### The path package (one per condition)

```
paths/g1/<condition>/
  tiles/            N PNGs, 128 × 128, 8-bit RGB, named <cell>_<YYYYMMDD>.png
  tiles.parquet     one row per unique tile
  encounters.parquet  one row per step of every walk, up to the cut
  manifest.json
```

- **`tiles/`:** rendered by the walker's own rendering code (`data/landsat1_store.render`): three-band CIR nir08 / red / green, square-root tone, the fixed stretch, the walker's 256 px tile. Then area-resampled to 128 px, the ground resolution the grid eye sees (~83 m per pixel; the glance sees 32 px). No eye sees the 128 px image itself.
- **`tiles.parquet`:**
  - cell, acquisition date, processing level;
  - night flag;
  - quirk shares (stripes, fill, saturation, cloud) and brightness, from the e12 detectors (on the raw bands and QA, as the walks log them);
  - the number of encounters.
- **`encounters.parquet`:**
  - walk id, step, clock date, tile (cell, date);
  - whether the step was a wait (the time offer) or a move;
  - the chosen offer's logged interest components at that step: z glance, z grid, z progress and the total interest `I`, the value the softmax chose by (not `I_long`, the drive's yardstick). These are the values the GAN weights are computed from.
  - The start tile of each walk was never an offer and has no interest: its first encounter carries empty components.

  Null rows carry the same columns, filled: the eye scores every offer in both conditions, so the Null's interest is logged too. The GAN brief weights only the curious package; the Null's interest is kept as a control.
- **`manifest.json`:**
  - condition, N, q;
  - the walk ids in order, with their start cells, step counts and how each ended (`time`, `linger`, `capped`), and where the package was cut;
  - the start-cell list and its seed;
  - the walker's git tag and config hash;
  - a SHA-256 checksum for every file;
  - the render check: 20 random package tiles re-rendered from the store on the Mac and compared byte for byte (passed or not).

### Freezing

- Commit the manifests and checksums, never the tiles, under the tag `g1-paths` (large outputs stay outside git). Keep the packages on disk and copy them to the PC.
- From that point they are read-only. If something is wrong with a package, fix it here, re-run what's needed, and re-tag. Never repair it on the PC.

### A stated limitation: the era confound (Moe, 2026-11-13)

The curious walker and the Null move their clocks at different speeds, so their N tiles can come from different stretches of the mission. The two GANs then differ by era (season, coverage, the 1977 green band) as well as by curation. This is accepted, not matched. The walk report and the GAN report show the clock and tile-date distributions of both packages side by side, and no finding about the GANs may be read past it.

## Not here

- The weights, τ and the effective-sample-size floor belong to the GAN brief. The walks only log the interest components.
- No rendering for the film, no GAN code.
