Rewritten by Claude Code at the end of every cycle. Last update: 2026-11-13, afternoon (Gate B decided).

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

- Not started. The GAN brief is written (`notes/brief_gan_g1.md`): two StyleGAN2-ADA models on the PC, G1-curious (tiles weighted by interest at encounter, ESS held at 0.5 N) against G1-null (unweighted), N = 10,000 each, about 72 h unattended.
- Its input is the two path packages defined in the handoff section of `notes/brief_landsat_v2_run.md`.
- The comparison carries an era confound, accepted by Moe: the two packages can come from different stretches of the mission (prediction 145 expects the Null's to end before mid-1974).

# Decisions taken since the last update, and why
- **Gate B (Moe, 2026-11-13):**
  - **The thinned time offer, q = 0.10,** the same for the Null. A jump in time can't be undone, so offering it less often lets the wanderer explore a period rather than exploit one tile through time. q is calibrated so that a curious walk ends at roughly 8,000–15,000 tiles (`notes/gen1/time_offer_rule.md`).
  - **The ending:** lingering from 1977-01-01 (the walk's own steps per year of clock), T_end 1977-12-20, a 40,000-step guard. Walk length is now partly a setting; the CHARTER says so.
  - **N = 10,000, one walk per condition.** A second wanderer runs only if the first ends short. Walks run to their end; only the package is cut at N.
  - **Nothing is cut from the data,** the lost green band of 1977 included (a black channel).
  - **The era confound** between the packages is a stated limitation, not matched.
  - **The quirk observer on GAN samples is deferred.** The e12 detectors need raw values and QA bands, and samples are 8-bit CIR images. Phase B saves the samples; the readout runs once Moe decides.
- **Mine, as defaults:**
  - the GAN weights use `I` (the choice's interest), not `I_long`;
  - the Null's interest is kept in its package as a control;
  - diversity is measured against the weighted and the unweighted reference;
  - only checksums and manifests go into git;
  - the render check runs on the Mac;
  - a start tile with no logged interest gets the package's median weight.
- **Written:** the v2 brief (§§2, 3, 4, 7 and the handoff), the GAN brief, the CHARTER (horizon, ending, Null, premises, milestone 3), `configs/gen1/{curious,null}.yaml`, predictions 143–157.
- **The long phase stays paused** (~10,400 pooled tiles, w011/w012 checkpointed). q no longer needs it.

# Waiting for Moe
- **The observer for quirks on GAN samples** (deferred; see the GAN brief, readout 2).
- **Approval to start the generation-1 walks** on the PC (section 7). Nothing has run under the new configs.
- **Whether to finish or drop the long phase** (predictions 140–142).

# Backlog, in order
1. **Generation-1 walks on the PC:**
   - curious w000 and Null w000 side by side, then curious w001 if needed;
   - the path packages, frozen at `g1-paths`;
   - `notes/gen1_report.md`, scoring predictions 143–151.
2. **The GAN brief, Phase A then B** (predictions 152–157, plus the measured ones).
3. **Separate what draws the curious walker to old acquisitions:** look, season, level, or sparse regions (finding 2 of the dry runs).
4. **Open checks of the research note:** missing ~14k items, the L1GS offset distribution, impulse noise, 6-bit combs.

t ends (predictions 140–142).
3. Separate what draws the curious walker to old acquisitions: look, season, level, or sparse regions (finding 2 of the dry runs).
4. A Landsat dataset builder for the GAN, on the PC (when the GAN training is specified).
5. Open checks of the research note (missing ~14k items, the L1GS offset distribution, impulse noise, 6-bit combs).

# Next milestone and its risk
- **Generation one as a prototype:** the walks, then the two GANs, both on the PC.
- **Risks:**
  - The calibration of q assumes the clock's pace scales with q, which is untested. The curious walk may end far outside 8,000–15,000 tiles.
  - With one walk per condition, every curious-against-Null result is a single pair: a hint, never a lead.
  - A 40,000-step Null walk takes about 17–19 h at the Mac's rate (likely less on the PC).
  - The PC needs the world index, start list and store access for the walks. Disk on the Mac is at 97 % (15 GB free).
