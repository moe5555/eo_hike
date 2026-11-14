Rewritten by Claude Code at the end of every cycle. Last update: 2026-11-14, 02:00 (generation 1 on the PC: walks done and reported, packages frozen, GAN training started; to be rewritten when the GANs finish).

# Where we are, in thesis terms
## RQ1:
How do practices of moving without a predetermined destination, like wayfaring or the dérive, translate to an untasked, step-wise traversal of the planetary image, already cut into scenes, scan lines and tiles?

- **The world** is the archive of one instrument, Landsat 1 (1972–78), with every acquisition of every cell, one product per date. It was rebuilt on the PC and proven identical to the Mac's world: `clock.json` exact, and the seeded start list identical once the Mac's cell grid was used. A Windows PROJ difference in the last bit had reordered cells (`runs/g1/world_check.md`).
- **The archive shapes the traversal:**
  - from mid-1974, only ~422,000 of 1.47 M cells are ever imaged again;
  - there is a winter gap from November 1976 to January 1977;
  - from April 1977 the green band is uncalibrated.
- **Under the thinned time offer (q = 0.10) the wanderers became movers** (generation 1, `notes/gen1_report.md`). A wait came through on 1.5–4.3 % of steps, and waits were 0.3 % of steps (57 curious, 47 Null).
  - Both walkers' clocks crossed the mission at the same pace.
  - Each walk lingered its own year's steps in 1977 and ended by `linger`.
- **"Far from its own time" is the archive.** Every walker's tiles lie further from its clock as the clock advances: about 0 days in 1972, about 800 days in 1976, 1,000–1,450 days in 1977. The cause is the closest-acquisition rule meeting the coverage collapse after mid-1974. Curious and Null are alike (pooled median 612 against 625 days).

## RQ2:
Which paths do algorithms driven by novelty, learning progress and boredom cut through the computational planetary image, and how much of their attention follows the terrain, how much the idiosyncrasies of their perception, and how much the artefacts of the instrument, where data and phenomenon come apart?

- **Generation 1:** three walks per condition, start cells 0–2; hints, not leads. Report: `notes/gen1_report.md`.
  - **Clear over cloud** (the most consistent hint). Curious compass choices have cloud 0.155 against 0.214 offered; the Null shows no gap. It holds in all three pairs and in every matched clock stretch but the first.
  - **Waits for learning.** At curious waits the progress z is 0.91, against 0.41 at moves (57 waits).
  - **The curious walker revisits less and covers more cells per step** than the Null, in every pair.
  - **Interest at the choice:** glance 0.38, grid 0.35, progress 0.26, stable since the dry runs.
  - **The dry-run hint "the curious walker lives far from its time" did not survive a matched comparison** (see RQ1).
- **The curious package's heaviest tiles are an apparatus-heavy tail.** The heaviest 64 (by weight at ESS 0.5 N) against the package as a whole:
  - stripes 0.121 against 0.067; fill ×4; night ×4; cloud 0.214 against 0.153; saturation flags 0.24 against 0.14 (`notes/gen1/gan/weights_vs_quirks.csv`).
  - The top 10 % are slightly darker, less cloudy and more striped than the package.
- **The lost green band of 1977:** about 2 % of tiles in both packages.

## RQ3:
What do GANs trained recursively on these paths construct, and do their worlds drift across generations towards the planet or towards the apparatus, depending on whether paths are curated by whole places or by fragments, compared with a recursive loop without intrinsic motivation?

- **Generation 1 is training** (started 2026-11-14 01:54, tag `g1-start`):
  - G1-curious, weighted by interest at encounter (τ = 3.665 for ESS = 0.5 N), against G1-null, unweighted;
  - N = 10,000 each, StyleGAN2-ADA cfg auto at 128 px, 3,840 kimg each.
- **The era confound is small:** both packages cover nearly the same clock and tile-date range (`notes/gen1/gen1/package_era.csv`).
- **Results:** the GAN report, after about 60 h.

# Decisions taken since the last update, and why
- **Moe, 2026-11-13:**
  - pushed `data/landsat/landsat1_c2l1_proj.parquet` and then `data/landsat1/grid.parquet` to git, so the PC could rebuild the world exactly (option 1 of the world check);
  - registered the pipeline as an S4U scheduled task and paused Windows Update to 18 Dec.
- **Mine, within the run instruction:**
  - **The walks run on CPU with 3 threads**, the Mac's setting for the dry runs and the q calibration. CPU and CUDA walks diverge within 50 steps.
  - **GAN training in alternating chunks of 400 kimg**, the GAN brief's fallback, instead of concurrent runs.
    - Probes: one run alone 25.4 s/kimg; both concurrently 88–91 s/kimg each; concurrently with half-size rounds, no first tick in 45 min (`runs/g1/gan/probe.json`).
    - Resume is exact: Adam step counters and batch index equal an uninterrupted run (`runs/g1/phase_a/`).
    - The run that is behind trains next, so both runs are never more than one chunk apart and end at the same kimg.
  - **FID only after training**, on the kept snapshots (960, 1,920, 2,880, 3,840 kimg), as a training-health signal.
  - **Diversity in pixel space (32 × 32)**, with weighted and unweighted references holding the same number of distinct tiles.
  - **Colour and texture statistics on samples, labelled as such**; the quirk observer stays deferred.
  - **StyleGAN2-ADA patches in one diff** (`scripts/stylegan2ada_g1.patch`): torch 2, scipy 1.18, the weighted sampler, full resume, the snapshot callback.

# Waiting for Moe
- **The quirk observer on GAN samples** (deferred; 5,000 samples per GAN will be saved).
- **Whether waiting matters enough to revisit q** for later generations. Under q = 0.10, waits are rare (finding 2 of the walk report).
- **The long phase** (predictions 140–142): finish or drop.

# Backlog, in order
1. **GAN Phase B runs unattended:** training, then FID, then readouts. Then the GAN report (predictions 152–157), this file, and the CHANGELOG.
2. **What draws the curious walker to old acquisitions:** now largely explained by the archive (walk report, finding 3). Close it, or recast it as an RQ1 readout.
3. **Open checks of the research note:** the missing ~14k items, the L1GS offset distribution, impulse noise, 6-bit combs.

# Next milestone and its risk
- **Generation 1 GANs** finish around 2026-11-16 at 11:00; readouts take about an hour after that.
- **Risks:**
  - Alternating mode restarts each run about 10 times. Each restart is tested, but a crash in one chunk costs up to 40 kimg; the watchdog allows 3 restarts per chunk.
  - One training seed per condition, one path per condition: every GAN comparison is a hint.
