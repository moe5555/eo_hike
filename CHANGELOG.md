# Changelog

Newest entry first. Each entry: date, what changed, why this approach, what you expect. Entries before 2026-11-12 are in `notes/CHANGELOG.md`.

## 2026-11-12, evening: the mission factorial read

- **What changed.**
  - **The 18 mission walks are read.** Report: `notes/12_two_eye/observations.md`. Tables: `notes/12_two_eye/results/l1/`. Viewers for the two-eye walks. Contact sheet: `results/e12_l1_two_top4_s0_contact_p1.png`. Predictions 96–121 scored.
  - **Bugs fixed after the walks:**
    - the readout `max_km_from_start` used a flat-degree distance (now great-circle);
    - the contact sheet and the viewer showed each cell's earliest image instead of the acquisition the step showed.
  - **STATE.md** rewritten, keeping Moe's new RQ wording.
- **Why this approach.** The brief's readouts, computed per image (cell and acquisition), against the two-eye Null. With two seeds, only hints.
- **What I expect.**
  - The findings to check with more seeds: the shared taste for clear, dark tiles (the apparent taste for earlier acquisitions was mostly place memory, corrected after review); stripes drawing the detail-eye; the flight from the red night field; the early time well as an escape from the night start; the two-eye walker as a homebody.
  - Before longer walks the cache needs a size cap: 18 walks filled 16 GB.

## 2026-11-12: the factorial moves to the whole Landsat 1 mission, with revisits through time

- **What changed.**
  - **The pass factorial stopped** after 6 of 18 walks (`e12_v1`, `_null`, `_grid_mean`, `_grid_top4`, `_grid_top1`, `_two_top4`, seed 0). The three walks running at the stop (`e12_two_top4_g2_s0`, `_shifted_s0`, `_shuffled_s0`) were aborted, and their run folders and logs deleted.
  - **The revisit rule** (`stack: revisit_next` in `agent/walk.py`; `data/landsat1_world.py stack`; image keys in `data/landsat1_store.py`):
    - Each cell keeps its acquisitions in date order, one per day: 31.8 M in all, a median of 7 per cell, up to 169. Overlapping scenes of one pass are the same scan lines, so the nearest scene centre stands for the day.
    - The first visit shows the earliest acquisition, each revisit the next one. A cell whose stack has run out is no longer offered.
    - Memories are kept per image, so a revisit never overwrites the memory of an earlier date.
    - The default, `earliest_only`, is every earlier walk. Checked bit-identical: v1 for 60 steps; two eyes for 60 steps against `e12_two_top4_s0`.
  - **The start** is where the archive begins: the cell nearest the centre of `LM01_L1GS_136214_19720725`, the first Landsat 1 scene in Collection 2 (25 Jul 1972, 04:00 UTC, a night pass, sun −15°). That is cell `479U_839L`, South Dakota. The publicised "first light" image (Dallas–Fort Worth, the same day, 16:31 UTC) is the sixth scene of the first daylight pass.
  - **New configs** `configs/12_two_eye/e12_l1_*.yaml`: the same nine conditions on `world: landsat1`. Predictions 111–121 were written before any of their walks. Batch: `scripts/hikes_e12.sh start l1`.
  - **Viewer and films.** `analysis/e12/walk_viewer.py` is the e09 viewer plus a two-eye card. `analysis/e10/film_pass.py --tile-only` renders only the tile, centred on black (`runs/e10_films/e12_two_top4_s0_tile.mp4`).
  - **Reproducibility.** `meta.json` now records `torch_threads`. Walks agree bit for bit only at the same thread count: three threads against the default diverge at 1e-8 by step 10, though the tiles chosen were the same over 60 steps.
  - **Not built**, per Moe: the full-tile rule (dropping tiles whose fill touches the border).
- **Why this approach.**
  - Moe: the wanderers walk the whole mission. "Earliest per cell" was meant as the first visit of a stack, not a single image per cell.
  - The single pass is a strip 177 km wide. Every step longer than ~90 km can only go along the track, and its offers snap onto the strip's edge.
  - On that edge, the glance chased the black wedges of partial cells: 59 % of `e12_two_top4_s0`'s chosen tiles, against 21 % in the Null.
- **What I expect.**
  - A **time well**: with novelty in the drive, a revisit brings a new image, so returns pay. In a 100-step smoke walk, 61 steps were revisits within ~30 km of the start.
  - Whether the drive still sends walkers far is open (prediction 113).
  - The mission factorial takes roughly 3–4 h, fetching included.

## 2026-11-12: the Landsat 1 world and walker v2's two eyes (brief `notes/brief_landsat_pipeline.md`)

- **What changed.**
  - **The world** (`data/landsat1_world.py`): the Major TOM grid (checked against the archive: centres identical), its land mask, a candidate table of every Landsat 1 acquisition covering each cell (34 M pairs), and the earliest rule. 1,466,863 cells.
  - **The lazy store** (`data/landsat1_store.py`):
    - COG windows from Planetary Computer, TOA from the MTL; night scenes without the sun term.
    - e10's sqrt tone and one global stretch from 2,000 random cells.
    - Quirk shares per cell and per 4 × 4 crop.
  - **Portrait**: `notes/11_landsat1_mission/world.md`.
  - **Walker v2** (`agent/eyes.py`, `eye: grid | two_eye`):
    - a glance at the whole tile and a grid of 16 crops, each with its own network and memory;
    - top-k pooling, the checkerboard progress probe;
    - a v1 shadow, and full logging (decomposition, crops, glance error maps, forgetting set).
    - v1 is bit-identical.
  - **The test bed**: e10's pass, rebuilt at 256 px in sqrt tone (the existing 256 px world was linear), with its quirk tables.
  - **Predictions 96–110** were written before the pass factorial.
  - **Found on the way:**
    - Planetary Computer's `proj:epsg` drops the zero of UTM zones 1–9 on 27,171 Landsat 1 items.
    - The research figures of 2026-11-11 used the linear stretch on a sqrt tone.
- **Why this approach.** The brief. Every option defaults to v1, and every hand-set choice is a named config key (log: `notes/12_two_eye/log.md`).
- **What I expect.** The two eyes separate "an interesting tile" (the glance) from "a tile containing something interesting" (the grid). The logs allow each choice to be split between them.
