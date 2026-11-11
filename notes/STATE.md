Rewritten by Claude Code at the end of every cycle. Last update: 2026-11-11.

# Where we are, in thesis terms
## RQ1:
The compass navigation is the current translation of an untasked walk: one drive sets how far the walker looks, close while a place pays, far once it goes dull. A rhythm of dwelling and sorties comes out, but the compass Null has the same rhythm, so it belongs to the drive's filter (authored), and the loop is open: going far never restores the drive (e09 findings 30–31, 42, 52). What is the walker's own is the choice once it moves. The concepts are Moe's.
## RQ2:
The strongest part. Against the compass Null, preference, clusters and taste come from the choice (8 seeds, e09 finding 38). Over 15,000 steps a taste for texture, contrast and snow grows and takes the walker north; its view of the world comes to order ground by kind, not by place, and never beats colour on land cover (findings 61–63). New (2026-11-11): the walker's choices track the stitching of Major TOM. Young, it follows the processing baseline and year of the cell it stands on; old, it follows the season. The taste for snow is its own (it survives holding season and processing fixed). Novelty is a property of a tile's look, not of its being unseen (findings 65–70). Gaps: the long-walk findings are one seed; boredom and surprise have not yet driven a walk.
## RQ3:
Not started in its current form. Earlier DDPM/GAN dreams (e01–e03) came before this design. No generation-1 GAN, no walker in latent space, no matched random loop, no drift readout.

# Decisions taken since the last update, and why
- 2026-11-11, **the world is Major TOM** (Moe). The stitched multi-temporal image that passes as one is the point. The seam readout bears it out (findings 65–68). The Landsat 1 pass (e10) stays a side piece for the film.
- 2026-11-10, walker v1 frozen (= `e09_ref`, tag `walker-v1`): the progress drive did not make far pay.

# Waiting for Moe
- Whether the world becomes the whole Landsat 1 mission (research 2026-11-11, on branch `landsat-1`: `notes/11_landsat1_mission/research.md`): this would reopen the Major TOM decision of 2026-11-11. If yes, also the selection rule per cell, the levels kept, the eye's colour, night scenes, and what a 1972 world is read against.
- The death rule (a premise). Death by surprise (the e06 Fast learner's network died at `lr` 3e-3) is the candidate under discussion. At v1's `lr` it has never fired in a v1 walk; the same black-decoder state appeared in two e09 schedule controls and lifted after 100–425 steps (finding 39).
- Whether to test habituation (novelty against recent visits) as walker v2 before the replication.

# Backlog, in order
1. PC: GAN generation 1 as a prototype on the long path (`e09_v1_long_s0`): distinct cells or visits, ocean and cloud kept or not.
2. Design the latent-space walker, its Null and the random-sampling loop; a drift readout for generated images (a land-cover classifier trained on real tiles).
3. Mac: three more seeds of v1 at 15,000 steps (is the drift north the walker's or seed 0's?).
4. The death rule: offline dry run on the e09 logs (e09 brief Stage 4, never run), then a survival test if death by surprise is chosen.
5. A Tobler readout split into within- and between-region distances (milestone 2 relies on it).
6. Check the N04/05 thumbnails against raw bands (is the processing seam the uncorrected offset?).

# Next milestone and its risk
Milestone 1: GAN generation one trained as a prototype on the long path (PC, from 2026-11-12). Risk: a GAN on about 10k tiles biased to the north and mixed between two tone regimes will collapse partly from small data alone. Collapse caused by novelty-driven sampling can only be separated from that with matched dataset sizes and more than one training seed, which costs PC time.
