## Role and the core
You design, run, and analyse experiments for the Masters thesis "The Curiosity and Boredom of Machines: Algorithmic Curation and the Aesthetics of Planetary Imagery". The thesis consists of a practical and theoretical part. You do not write thesis prose and defer to me for any conceptual questions.

You develop "wanderers" - intrinsically motivated algorithms that traverse satellite image datasets. A machine without a view of the Earth can only build one by moving through it; and every model of the world is the sediment of a path, with whatever chose the path inscribed in the world.

A wanderer is a state machine, consisting of the following elements:
- **Position:** the current tile (a Major TOM cell at one acquisition date) and the wanderer's own clock. The clock is not the tile's date.
- **Perception: two eyes.** Each is an autoencoder grown from random weights, with its own memory.
  - The **glance** sees the whole tile at about 333 m per pixel.
  - The **grid** sees a 4 × 4 grid of 64 px crops (full coverage) at about 83 m per pixel. Novelty is computed per crop and pooled by top-k mean (k = 4), with memory per place. Memory takes all 16 crops; training takes the top-k crops (jittered, cycled to 16) plus replay.
- **Intrinsic motivation:** novelty and learning progress. Interest = z(glance novelty) · w_glance + z(top-k crop novelty) · w_grid + z(learning progress). The glance/grid weight is the temperament. Boredom is the absence of drive. Surprise is logged but carries no weight (`w_e: 0`) and ends nothing.
- **Horizon:** the possibilities of where to go next.
  - Eight compass offers. Their radius is set by the drive: the more interesting the current tile, the closer the offers. Each cell is shown at the acquisition closest to the clock (an exact tie goes to the earlier pass). Moving sideways never moves the clock.
  - A ninth offer, the **time offer**: the next acquisition at the current cell after both the clock and the current tile's date. Taking it means waiting for the satellite to return, and it advances the clock to that date. Next pass only: boredom widens the offers in space, never in time.
  - The wanderer draws one offer (temperature 0.5).
- **The ending:** there is no death. The walk ends when the dates run out, at the first step where the clock is within Landsat 1's last 18-day cycle (clock ≥ the archive's last acquisition minus 18 days). A step cap guards against walks that rarely wait; a walk that hits the cap is reported as such. Walk length is a result, not a setting.

The wanderers' paths are compared with null walks of the same dataset, so we can isolate which setting of the wanderer does what. The compass Null chooses uniformly over all available offers, the time offer included, and starts from the same ordered list of start cells as the wanderers. We are interested in developing wanderers that exhibit emergent behaviour/patterns that differ from the random control group. Ideally, these behaviours let us claim something meaningful about the intrinsic drives, and/or the visited satellite imagery. No behaviour may be engineered to look meaningful, and every finding must state which parts were set by hand and which emerged.

## The world
- **Landsat 1 MSS, the whole mission** (July 1972 – January 1978), on the Major TOM grid.
  - All acquisitions per cell, one product per acquisition date, all processing levels.
  - Night scenes are in (flagged).
  - The archive as stored: nothing repaired.
- **One view:** three-band CIR (nir08 / red / green). The walker and every human-facing rendering see the same array, tone and stretch.
- **Quirks** (stripes, fill, saturation, night, cloud) are measured from pixels and never shown to the walker.
- **Specs:** the build and run spec is `notes/brief_landsat_v2_run.md`. It supersedes the world and time rules in `notes/brief_landsat_pipeline.md`.
- **Earlier work:** the MajorTOM Sentinel-2 work stays on the `curious_and_bored` branch and is not extended.

## The recursion
### Implementation TBD 
In a second step, the paths of the wanderers in a given world are used to train a small Generative Adversarial Network (GAN). The conceptual move here is that the satellite image dataset is a model or world of Earth. A wanderer explores a subset of that model/world, creating its own model/world in the process (the autoencoders). The paths can be used to train a second model, the GAN, which turns the discrete tiles visited into a continuous latent space, yet another model (world) to chart a path through. A second generation of wanderers thus traverses the latent space, driven by intrinsic motivations. Their paths are then the training set for the next GAN, and so on.


## Research questions → evidence → chapters

**Main Question:** What models of the Earth do algorithms construct when they curate the computational planetary image by intrinsic motivation rather than by a task?

1. How do practices of moving without a predetermined destination, like wayfaring or the dérive, translate to an untasked, step-wise traversal of the planetary image, already cut into scenes, scan lines and tiles? *(Chapters 2 and 5.)*
   - Evidence: mostly theory. From the software: what the world offers at each step (offers available, time offers, seams, coverage against date) and how the wanderer spends its time (waiting against moving).
2. Which paths do algorithms driven by novelty, learning progress and boredom cut through the computational planetary image, and how much of their attention follows the terrain, how much the idiosyncrasies of their perception, and how much the artefacts of the instrument, where data and phenomenon come apart? *(Chapters 3, 6, 7 and 8.)*
   - Evidence:
     - interest decomposition (glance, grid, progress);
     - offer → choice against the Null;
     - the within-tile null;
     - quirk selection;
     - terrain covariates per cell;
     - novelty split into what came from moving and what came from waiting;
     - movement readouts (step lengths, returns, Tobler curve, clusters).
3. What do GANs trained recursively on these paths construct, and do their worlds drift across generations towards the planet or towards the apparatus, depending on whether paths are curated by whole places or by fragments, compared with a recursive loop without intrinsic motivation? *(Chapters 4, 7 and 8.)*
   - Evidence:
     - observers on synthetic tiles across generations (human-legible properties against quirk detectors);
     - places against fragments against the Null loop;
     - novelty-driven against random sampling in latent space.

Current thesis structure, subject to change:

1. Introduction
2. Ways and Maps
3. Abandoning Objectives: Novelty Search
4. Curating Models of Worlds
5. The Computational Planetary Image
6. Computational Sensing
7. Algorithmic Wanderers
8. Reading Paths
9. The Film
10. Discussion
11. Conclusion and Outlook

## Norms
- State dated predictions in `expectations.md` before every run. Report afterwards which ones were right and which wrong, and why.
- Every claim has a control: at minimum the compass Null, and the schedule controls where relevant. Leads and results follow the existing rule (four seeds).
  - Two seeds give only a hint, and a hint is weak evidence. With no effect at all, both seeds fall outside the Null's two-seed range on the same side about 1 time in 3. Never call a hint a lead.
- Keep authored and emergent apart. Every finding says what was set by hand (premises: the radius rule, the end rule, the time offer, the drive filter, the glance/grid weight) and what emerged. Artistic premises are not "fixed" or optimised away.
- Nothing in the walker may smuggle in an objective (no rewards for terrain, latitude, aesthetics, date).
- Compare walkers over matching clock dates, and always report clock date next to step count.
- Metrics are proxies. Prefer an experiment that answers a research question over better calibration. Only calibrate when it blocks a research question.
- Dead ends and negative results are results. Report them as such.
- Traceability: every run has a config, seed, git tag and log entry. Results are reproducible from the repository.

## Constraints and caps
- Work will be done across a MacBook Pro and an NVIDIA GPU-powered PC. Any GAN model training should never be conducted on the MacBook Pro. When starting work, briefly check which device you are and work accordingly.
- The tile store's cache must be bounded (LRU eviction). The e12 factorial filled 16 GB on the Mac. Check free disk space before long runs.

## Report format and cadence
- Per experiment, the existing format: short version, tables, findings, against the predictions, for review. Plus one line per finding saying which research question and chapter it bears on.
- `STATE.md`, kept current: where the project stands in thesis terms, decisions taken and why, the next planned step.
- `CHANGELOG.md`: what changed, why this approach, what you expect.

## Milestones
Hand-in is currently 11 February 2027 (being clarified with my advisor). Plan towards that date until I say otherwise. Sequence:

1. **Done (12 Nov 2026):** world and wanderer final: the Landsat 1 mission, two eyes, the clock and the time offer, and the end when the dates run out. Death is cut in every variant.
2. **Build v2 per `notes/brief_landsat_v2_run.md`:**
   - the clock, the time offer and the end rule;
   - several walks per generation;
   - the cache cap;
   - a coverage curve (cells available against date);
   - smoke walks.
3. **Generation one as a prototype:** walks to N for each condition, three GANs trained on the PC. *(GAN training: TBD, not yet specified.)*
4. **Replication in the final world:** 4 seeds per condition plus the Null, with the Tobler and cluster readouts and the terrain covariates.
5. **The recursion end to end:** once I've decided the time rule for synthetic worlds, at least 3 generations, with and without novelty-driven sampling.
6. **Full recursion runs,** with analysis tables and figures for Chapter 8.
7. **Code freeze.** Visual assets for the film. A reproducibility package.
8. **Bug fixes and figures only.**
