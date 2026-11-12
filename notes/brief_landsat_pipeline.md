# Brief: the Landsat 1 world and the two-eye walker

Two things are being built, and they meet in one walk:

- **A.** A Major TOM-like world over the whole Landsat 1 MSS mission (1972–78).
- **B.** Walker v2: an eye that sees the whole tile at two scales. A **glance** takes in the whole tile as a gist; a **grid** of crops covers it in detail. Novel details count high instead of being averaged away.

Where this brief and the code disagree, say so before building. You know the codebase; this brief carries intentions, premises and open questions.

## Context

- Read first:
  - the Landsat 1 research note (2026-11-11);
  - your assessment of the crop eye and your note on the three hand-made choices (weighted draw, training crops, eye size);
  - `agent/walk.py`, `agent/signals.py`, `agent/compass.py`, `analysis/attention.py`, `gen/v3_datasets.py`;
  - e10's data code (`data/landsat_pass.py`, `data/tile_store.py`, `data/global_index.py`).
- On this branch, Landsat 1 is the world and the default. Major TOM stays in `curious_and_bored`: a reference for interfaces, not ported or kept in sync.
- The existing 256 px pass world (`data/landsat/LM01_183_19721122/c10680m_256px_cir`) is the test bed for the eye until the mission world exists.
- This machine is the MacBook: no GAN training here.
- Commit after each step. Large outputs go in `runs/` (git-ignored).

## Principles

1. **The archive as stored.** Don't repair, equalise or re-register anything. L1GS offsets, stripes, saturation, clouds, fill and night scenes stay in.
2. **Quirks are measured from pixels**, never shown to the walker. QA flags are kept as separate columns, since their disagreement with the pixels is a readout.
3. **One view.** The walker and every human-facing rendering (contact sheets, film frames, GAN samples) see the same array: the same bands, tone and stretch. No separate display path. Per-tile stretches are allowed only in diagnostic figures, labelled as such.
4. **Keep the readings apart.** Every step must be able to say how much of a choice came from the whole tile (glance), from a detail (grid) and from learnability (progress). "An interesting tile" and "a tile containing something interesting" are different claims, and the logs must be able to tell them apart.
5. **v1 stays reproducible.** Every new option defaults to v1's behaviour (the repo's convention).

## Fixed premises (decided)

| Premise | Decision |
|---|---|
| World | Landsat 1 MSS, whole mission, Major TOM grid and land mask |
| Selection rule | **earliest** acquisition per cell |
| Processing levels | **all** (L1TP and L1GS, Tier 1 and Tier 2) |
| Eye colour | **three-band CIR** (nir08 / red / green), e10's tone (sqrt), one fixed global stretch per band. nir09 cached, not seen |
| Night scenes | **in**, flagged |
| Coverage | The walker **sees the whole tile**. No centre bias |
| Novelty | Highly novel parts **count high**, not averaged away |
| Eye design | **Two eyes:** a whole-tile glance plus a detail grid, each with its own memory |
| Zoom | The film will zoom onto the most novel crop. Low resolution is accepted |
| Readouts against land cover | **open**. Don't build them. Every cell carries coordinates for later joins |

## Proposed defaults (confirm or change)

| Question | Proposed default | Reason |
|---|---|---|
| Networks | **two small encoders**, one per eye | One shared latent space would mix 333 m and 83 m textures, making scale confusion a hidden variable. At 32 px the second network is cheap. Keep `shared` as an option |
| Grid | **4 × 4 only** in round 1, no offset grid | The offset grid double-counts border features under top-k. Add it later if the zoom needs finer maps |
| Crop memory | **per place**: for each remembered tile, its nearest crop; novelty = mean over the 10 nearest tiles | Keeps k_nn's meaning; avoids one homogeneous tile supplying all neighbours |
| Seen against attended | **memory = all 16 grid crops** (seen); **grid training = top-k crops with a few px jitter, plus replay** (attended) | It learns, and can tire of, what attracted it, while the whole tile still enters memory. Watch for forgetting (see logging) |
| Pooling | **top-k mean, k = 4** in the two-eye condition | Moderate: details count, but one crop alone doesn't decide |
| Interest | **z(glance novelty) · w_glance + z(top-k crop novelty) · w_grid + z(progress)** | The glance/grid weight is the temperament: judge of the whole against connoisseur of details |
| Progress | **tile-level**, probe on a **checkerboard** split of the grid crops | Grid order would make it "does the north half teach the south half" |
| Surprise | **not a drive** (`w_e: 0`); the **trigger for death** | Wanderers driven by novelty and progress, killed by surprise |
| Draw | **unchanged** (temperature 0.5) | Named as a premise. A low-temperature variant (0.1–0.2) is a later test |

## A. The Landsat 1 world

1. **Grid and candidates.** The Major TOM grid (reuse its code from `curious_and_bored`) with its land mask. From census metadata only, build a candidate table: every Landsat 1 acquisition covering each cell, with scene id, date, path/row, level, tier, scene cloud, sun elevation, distance to scene centre, and the pixel window. Save it as parquet.
2. **World index.** The earliest rule, with e10's tie-break (nearest scene centre). Keep selection a function so other rules can be added later.
3. **Portrait of the world.** Land coverage, a date histogram, the mix of levels and tiers, cloud, the night share, a regional breakdown, and a map of acquisition dates. A short markdown note with figures.
4. **Lazy store.** `Landsat1TileStore`, with `TileStore`'s interface. Reads COG windows from Planetary Computer (`landsat-c2-l1`): four bands plus QA_PIXEL and QA_RADSAT. SAS-token renewal, retries with backoff, limited concurrency, disk cache. Returns the 256 px tile (10.68 km). No prebuilding; prefetching offers is fine.
5. **Radiometry.** TOA reflectance from the MTL, (M · DN + A) / sin(sun elevation), with MTL reads cached. Night scenes: DN-based values scaled the same way, flagged, no infinities. Then e10's tone and the fixed global stretch. Cache all four bands as float16. Tone and stretch parameters are named constants. Night cells look nearly black: that's correct.
6. **Quirk columns, per cell and per grid crop.** Stripe share per band (e10's measure, via the summed-area table per crop), share at DN 255 per band, flagged saturation per band, flag-against-pixel disagreement, QA cloud share, fill share, a night flag, and the scene metadata. Written when a tile is first fetched, plus about 2,000 random cells offline as baselines.

## B. The two-eye walker

7. **Eye option** `eye: v1 | grid | two_eye`, default `v1`.
   - **Glance:** the whole 256 px tile, area-averaged to 32 × 32 (~333 m/px), encoded by the glance encoder. Glance memory: one glance latent per visited tile, k_nn against glances.
   - **Grid:** 16 non-overlapping 64 px crops (4 × 4, 100 % coverage), each area-averaged to 32 × 32 (~83 m/px), encoded by the grid encoder. Crop memory per place (as above). Novelty per crop, pooled by top-k mean (`novelty_topk`).
   - **`grid`** alone is the grid with `w_glance = 0`. **`two_eye`** uses both.
   - **Training.**
     - The glance encoder trains on the chosen tile's glance, plus replay of past glances.
     - The grid encoder trains on the top-k crops (jittered), plus replay. Memory takes all 16 crops.
     - Fixed grid positions mean scoring and training windows coincide up to jitter. Check this doesn't reintroduce the revisit problem that `04_perception_fix` solved.
   - **Re-embedding** every 100 steps for both memories. `refresh_archive` needs a crop-to-tile map.
   - **Shadow signal:** keep a v1-style tile-mean archive in parallel and log v1's novelty for the same offers every step. It draws no random numbers and changes no behaviour, and it keeps `archive.npz` at one row per visit so the existing readouts run unchanged.
   - The drive, radius rule and δ = 0.25 stay as in v1. Check interest statistics with the existing shifted and shuffled radius schedules, and only recalibrate if that blocks.

## C. Logging (for the zoom, the film and the readouts)

8. **Per step:**
   - glance novelty, pooled grid novelty, progress, their z-scores and weights, and **each component's share of interest**;
   - the probability of the chosen offer, and whether it was the best offer;
   - the v1 shadow novelty;
   - surprise per eye (glance error; grid error, pooled and max);
   - the glance reconstruction-error map (32 × 32, float16);
   - jittered training-crop offsets.
9. **`crops.parquet`:** one row per candidate crop (step, cell, crop id, x, y, e, n, rank within tile, share of the pooled score) plus its quirk shares. Latents only for the chosen cell.
10. **Forgetting check:** reconstruction error of both encoders on a fixed set of ordinary crops and glances (sea, sand, field), every 500 steps. Training on what was attended to may erode ordinary terrain.
11. **Checkpoints** of both encoders at fixed intervals.

## D. Death: dry run

12. Death isn't built yet, and the replication milestone depends on it. Run the dry run proposed in the e09 brief, Stage 4: C1 (surprise more than k SD above its running mean after step 150), C2 (C1 after a settled stretch), C3 (exhaustion). Do this on logged surprise, without killing the walker. The **surprise source is a premise** to compare:
    - glance surprise (the whole tile shocks it);
    - pooled grid surprise;
    - max grid surprise (one crop can kill it: death by apparatus, likely striped or saturated crops).

    Report when and where each would have fired, and on what terrain or quirk.

## E. Expectations and the short factorial

13. **Predictions first,** in `expectations.md`, dated, before any run: which conditions chase stripes, fill and night; whether the glance tracks cloud and brightness; whether crop memory tires of stripes faster than v1.
14. **Factorial on the 256 px pass world,** about 1,000 steps × 2 seeds per condition:
    - v1;
    - grid, mean pooling (k = 16);
    - grid, top-4;
    - grid, top-1;
    - two_eye, top-4, w_glance = 1;
    - two_eye, top-4, w_glance = 2 (glance-heavy);
    - the compass Null.
15. **Readouts:**
    - interest decomposition (glance against grid against progress) per condition;
    - the top crop against the tile's other crops on quirk shares (a within-tile null);
    - offer → choice against the Null;
    - **edge pull** (how often the top crop sits at the cell's edge);
    - a **patch-shuffle test** (shuffle crop positions and recompute: bag eyes don't change, the glance does);
    - glance novelty against cloud share and brightness;
    - the death dry run.
16. **Then a smoke walk on the mission world** (about 500 steps, two_eye, top-4), with a contact sheet showing each visited tile in its one view, the top crop outlined, and the step's interest decomposition.

## F. Later, not in this brief (so the logging supports it)

GAN conditions for RQ3, as currently proposed:

- Null path unweighted;
- curious tile-weighted;
- curious collage: training tiles assembled from top crops in **path order**, with the 64 px seams named as authored.
- Re-centred windows if time allows.

Tile GAN at 128 px (matches sensor and eye), each generation trained from scratch. A Landsat dataset builder is needed (`v3_datasets.py` assumes Major TOM at 10 m), and a new tile weight (pooled novelty at the visit), since the compass walker has no boredom signal.

## Deliverable

A short note covering:

- what was built;
- the world portrait;
- the factorial results against the predictions;
- the death dry run;
- the mission-world smoke walk (time per step, failures, anything odd);
- which proposed defaults held and which you'd change.

Keep the effort proportionate: this is plumbing and a first look, not the main runs.