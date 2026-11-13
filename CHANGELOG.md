# Changelog

Newest entry first. Each entry: date, what changed, why this approach, what you expect. Entries before 2026-11-12 are in `notes/CHANGELOG.md`.

## 2026-11-13, afternoon: Gate B decided. The briefs, CHARTER, configs and predictions for generation 1

- **What changed.**
  - **Moe's decisions at Gate B:**
    - q = 0.10;
    - lingering from 1977-01-01, T_end 1977-12-20, the 40,000-step guard;
    - N = 10,000, one walk per condition (a second only if the first ends short);
    - only the package is cut at N;
    - nothing is cut from the data, the lost green band included;
    - the era confound is a stated limitation;
    - the quirk observer on GAN samples is deferred.
  - **`notes/brief_landsat_v2_run.md`:**
    - §§2–4 carry the thinned time offer, lingering, the guard and the end reasons;
    - §7 the one-walk rule and the era readout;
    - the handoff:
      - N, cutting the package rather than the walk;
      - 128 px described as the grid eye's resolution, not "as the walker saw it";
      - `I` named, and the Null's interest kept;
      - the render check done on the Mac;
      - checksums only in git;
      - the era confound.
  - **`notes/brief_gan_g1.md`:**
    - the same decisions;
    - the start tile's weight, and a fallback if ESS = 0.5 N can't be reached;
    - diversity against weighted and unweighted references;
    - quirk readout 2 deferred (samples saved);
    - the era confound as a limitation.
  - **CHARTER:** horizon (thinning), the ending (lingering, guard, walk length partly a setting), the Null, the premises, milestone 3 (two GANs).
  - **Configs** `configs/gen1/{curious,null}.yaml`:
    - `time_offer_p: 0.10`, `linger_from: "1977-01-01"`, `steps: 40000`;
    - `linger_from` is quoted: a YAML date would have crashed the walk's first `meta.json` write (`json.dumps` without `default=str`).
  - **`notes/gen1/time_offer_rule.md`:** q finalised at 0.10.
  - **`notes/06_characters/expectations.md`:** predictions 132–139 superseded; 143–151 (walks) and 152–157 (GANs) written.
  - **Not run:** no walk under the new configs (Moe: the work moves to the PC).
- **Why this approach.**
  - q now targets the walk's end (8,000–15,000 tiles), so lingering is counted in: about 1.22 × 906 / q ≈ 11,000 at q = 0.10.
  - Cutting the package rather than the walk keeps every walk whole for the RQ2 report.
  - Weighted and unweighted references keep the diversity comparison from favouring the Null by construction.
- **What I expect.**
  - Curious needs two walks to reach 10,000 tiles; the Null needs one, which runs to the guard (143–144).
  - The Null's package ends before mid-1974 while the curious package reaches 1977 (145). The era confound will be the largest single difference between the two GANs' training sets.

## 2026-11-13: brief v2 to Gate B. The clock world, the dry runs, and the long phase

- **What changed.**
  - **Built (Gate A, tag `gen1-gateA`):**
    - **The clock world** (`data/landsat1_world.py clock`): every cell's acquisitions, one product per date (the highest level, ties by product ID); 31.8 M acquisitions; start pool 250,218 cells; a seeded start list of 500 (`startlist`).
    - **The clock** (`agent/clock.py`; `stack: clock` in `agent/walk.py`):
      - offers are shown at the acquisition closest to the clock;
      - the time offer is the next pass at the current cell;
      - the end rule is the clock reaching T_end, or the step cap.
    - **Walks** run as `--walk K --phase P`. Checkpoints with resume every 1,000 steps (bit-identical, tested), contact sheets every 500 steps, `walk.json`. There is no death path.
    - **The cache cap** (`data/cache_cap.py`): LRU by mtime; tiles visited by running walks are pinned (Moe: cap + LRU).
    - **Tests:** 26 in `tests/test_clock.py`.
  - **Dry runs (Gate B):** curious and Null on start cells 0–2. Report: `notes/dryrun_report.md`; tables and figures in `notes/gen1/dryrun/`. Predictions 122–131 scored.
  - **Fixed on the way:**
    - fresh and cached tiles rendered differently (float32 against float16; e12 walks too);
    - a lock deadlock in the store;
    - three walkers swapping on the Mac (now two side by side, smaller in-RAM caches);
    - GDAL_CACHEMAX passed as a string, which failed every read for 40 minutes (my bug);
    - the MTL's NULL calibration of band 4, which made every scene from April 1977 on fail. The band is now read as missing.
  - **Rerun:** three dry runs that had lost offers to that last bug; the old runs are in `runs/dryrun_prefix/`.
  - **CHARTER:** the spec file was renamed to `notes/brief_landsat_v2_run.md` to match the CHARTER, and GAN training in milestone 3 is marked TBD (Moe).
  - **The long phase (Moe, 2026-11-13):** curious walks on start cells 3, 4, … Each walk ends when its clock enters 1977 (`--t-end`) or at 20,000 tiles (new optional end reason `tiles`, off by default). Walks continue until 20,000 pooled tiles (`scripts/gen1.sh start long`, `scripts/pool_tiles.py`). Predictions 140–142.
- **Why this approach.**
  - The brief: the architecture is frozen, and time is the only new mechanism.
  - Every fix was made at the cause, with a test where one could be written.
  - Walks that met a bug were rerun rather than patched.
- **What I expect.**
  - Gate B needs Moe's decisions: T_end (no curious dry run reached 1977-12-20), the step cap, N, and how to show the lost green band (`notes/dryrun_report.md`, "For review").
  - The long phase takes about 6–12 h on the Mac.
  - The two hints to test with more start cells: the curious walker lives far from its clock, and it waits to learn rather than to see something new.

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
