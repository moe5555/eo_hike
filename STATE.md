Rewritten by Claude Code at the end of every cycle. Last update: 2026-11-13.

# Where we are, in thesis terms
## RQ1:
How do practices of moving without a predetermined destination, like wayfaring or the dérive, translate to an untasked, step-wise traversal of the planetary image, already cut into scenes, scan lines and tiles?

- The world is the archive of one instrument, Landsat 1 (1972–78), with every acquisition of every cell, one product per date. Each wanderer has its own clock. Moving sideways shows each place at its acquisition closest to the clock; the time offer waits for the satellite's next pass.
- The archive shapes the traversal:
  - from mid-1974, only ~422,000 of 1.47 M cells will ever be imaged again;
  - there is a winter gap, November 1976 to January 1977;
  - from April 1977, the green band is uncalibrated.
- The clock climbs in stairs: most steps offer no wait at all. How fast a walk crosses the mission depends on where it starts: in Quebec, a time offer comes in 75 % of the Null's steps; in Rondônia, in 10 %.

## RQ2:
Which paths do algorithms driven by novelty, learning progress and boredom cut through the computational planetary image, and how much of their attention follows the terrain, how much the idiosyncrasies of their perception, and how much the artefacts of the instrument, where data and phenomenon come apart?

- Hints from the dry runs (3 start cells, curious against the Null; `notes/dryrun_report.md`):
  - **The curious walker lives far from its own time.** The median gap between its tile's date and its clock is 379–1,343 days (Null 0–1,078), and it is offered a wait less often than the Null on every start cell.
  - **Waits are for learning, moves for novelty.** At waits the progress z is 1.09, against 0.44 at moves.
  - **Clear over cloud,** for moves and waits (as in e12). The Null shows no gap.
- Interest at the choice: glance 0.37–0.39, grid 0.34–0.36, progress 0.25–0.29.
- The lost green band of 1977 is an apparatus finding. Whether novelty seeks or flees it is not yet seen.
- All of this is three start cells, one seed each: hints, not leads.

## RQ3:
What do GANs trained recursively on these paths construct, and do their worlds drift across generations towards the planet or towards the apparatus, depending on whether paths are curated by whole places or by fragments, compared with a recursive loop without intrinsic motivation?

- Not started. GAN training is TBD (Moe, CHARTER). The walks log what a dataset needs: tiles per step, top crops, novelty at the visit, and quirks per tile and crop.

# Decisions taken since the last update, and why
- **Brief v2 (`notes/brief_landsat_v2_run.md`):** the clock, the time offer (next pass only), the end at T_end or the cap. There is no death (Moe; CHARTER).
- **Curious = walker v2, two eyes top-4** (`e12_l1_two_top4`); the Null is the same walker drawing uniformly (Moe, 2026-11-12).
- **Cache: cap + LRU** (Moe). 12 GB on the Mac; tiles visited by running walks are pinned.
- **The long phase** (Moe, 2026-11-13): curious walks on start cells 3, 4, …, each until its clock enters 1977 or 20,000 tiles, pooled to 20,000 tiles. It is running.
- **The uncalibrated green band** is read as missing (a black channel) — my default, for Moe to confirm.
- Two walkers side by side on the Mac: three made it swap.

# Waiting for Moe (Gate B, `notes/dryrun_report.md` "For review")
- T_end for generation 1: 1977-12-20 (the brief; no curious dry run reached it in 3,000 steps), 1977-01-01 (as in the long phase), or other.
- The step cap (15,000) and N (5,000 / 10,000 / 20,000 per condition).
- The lost green band: keep it as missing, leave those products out, or something else.
- Longer walks: Moe asked (2026-11-13) whether waiting could be made less likely, so a walk lasts 7,000–10,000 steps. My advice:
  - this turns walk length into a setting (the CHARTER: "a result, not a setting");
  - if wanted, thin the time offer in the horizon (offered with probability q, the same for the Null) rather than penalise it in the choice.
- Moe's expectations for generation 1 (slot in `expectations.md`).
- Approval to start section 7.

# Backlog, in order
1. Gate B decisions → generation-1 walks (curious and Null interleaved, pooled to N), manifest, `notes/gen1_report.md`.
2. Read the long phase when it ends (predictions 140–142).
3. Separate what draws the curious walker to old acquisitions: look, season, level, or sparse regions (finding 2 of the dry runs).
4. A Landsat dataset builder for the GAN, on the PC (when the GAN training is specified).
5. Open checks of the research note (missing ~14k items, the L1GS offset distribution, impulse noise, 6-bit combs).

# Next milestone and its risk
- **Generation one as a prototype:** walks to N for each condition (Gate B decisions first).
- **Risks:**
  - Walk length depends on the start region, so a pool comes from few walks, and one stalled walk can dominate it.
  - The 1977 green-band loss changes how the archive's last months look, in the walker's eye and in any GAN's.
  - The Mac's memory allows two walkers at a time.
