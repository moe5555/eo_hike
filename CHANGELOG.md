# Changelog

Newest entry first. Each entry: date, what changed, why this approach, what you expect. Entries before 2026-11-12 are in `notes/CHANGELOG.md`.

## 2026-11-21, morning: G3 GANs done and reported; chromatic stripes measured post hoc; G3 latent walks running

- **What changed.**
  - **G3 training** finished at 08:30 (3,840 kimg each, 55.3 h, no restarts). The G3 FID and readouts ran cleanly (`notes/gen3/gan/`, committed by the pipeline). The G3 latent walks started at 09:32.
  - **`notes/gen3_gan_report.md`:** interim readings for 169–172. 169 is already against the data; 170 is consistent; 171's null part is already outside its band.
  - **New, post hoc:**
    - `analysis/recursion/chroma_stripes.py`: chroma_y, the vertical change in each channel minus brightness;
    - `analysis/recursion/stripes_in_walks.py`: per step, tile stripes against interest and the next offer radius.
    - Outputs are in `notes/recursion/chroma_stripes.csv` and `stripes_in_walks.csv`.
  - **Figures:** the same 10 seeds across G1–G3 and the G3 far ends (`notes/gen3/gan/`).
- **Why this approach.**
  - The G3 samples are visibly dominated by coloured, slanted scan lines, while the existing row roughness fell in curious. That statistic averages brightness along pixel rows, so it cannot see them.
  - A second statistic was added next to it, labelled post hoc. The old one is unchanged, and predictions stated on it are still scored on it.
  - Splitting the loop into walk steps and GAN steps answers where the apparatus grows. The walks show a ×1.25–2.43 rise per generation, the GANs ×1.00–1.16.
- **What I expect.**
  - The G3 walks end about 12:30, then G4 packages and training (about Tuesday 2026-11-24 morning), the recursion readout and the upscaler.
  - If the walk effect belongs to the loop, the G4 package will again be stripier than G3's samples, in both conditions. The G3 walks should again link stripes to close offers.

## 2026-11-18, evening: G2 GANs done and reported; G2 latent walks running

- **What changed.**
  - **G2 training** finished at 20:54 (3,840 kimg each, no restarts). The first full-size G2 FID and readouts ran cleanly (`notes/gen2/gan/`, committed by the pipeline).
  - **`notes/gen2_gan_report.md`** scores the predictions: 164 right, 165 right, 166 wrong, 167 right, 168 right. It adds early readings for 169 and 171.
  - **`analysis/recursion/readouts.py`** ran on G1 and G2 ahead of its pipeline stage. The table is in `notes/gen2/gan/cross_generation_g1_g2.csv`; the pipeline reruns it over G1–G4.
  - **Visual sheets** of 8 seeds at ψ = 1, 2 and 3 are in `notes/gen2/gan/<cond>_far_ends_psi1-3.png`.
  - **The G2 latent walks** started at 21:57 (α_min 16.7° and 14.1°, against the real G1 15 km reference).
- **Why this approach.** Prediction 165 needed the spread across samples, so the recursion readout ran early on the two finished generations. Nothing in the pipeline changed.
- **What I expect.**
  - The G2 walks end about midnight. The G3 packages and training follow, with G3 done about Saturday evening.
  - The banding rise and the null's walk effect (findings 4–5 of the G2 report) should show again in G3 if they belong to the loop rather than to one seed.

## 2026-11-17, midday: G3 and G4 queued; the recursion readout and the Landsat 1 upscaler

- **What changed.**
  - **Moe's decisions (2026-11-17):** G3 and G4 at the same rules, then the upscaler, then stop. Recorded in `notes/brief_g2.md` (extension).
  - **`scripts/g1_lib.py`:** the generation stages are generic (`stage_gen`, `GENS = (2, 3, 4)`), with new stages `recursion_readouts` and `upscaler` before `final`. Each new generation's manifests are committed and tagged `g<g>-paths` by the pipeline.
  - **`analysis/recursion/readouts.py`:** coverage of the real G1 package, spread and colour/texture statistics per generation, plus a collapse flag. Tested on G1 (recall 0.098 and 0.178, as in the GAN report); the test output was deleted.
  - **`scripts/upscaler.py`:** Landsat 1 pairs (128 → 178 px), a residual CNN, held-out evaluation and figures. Tested end to end on 400 tiles; the full pairs were built on the CPU during G2.
  - **Predictions** 169–173 were added before any G3 package.
- **Why this approach.**
  - Every generation runs under the same rules, so trends across G1–G4 aren't confounded by budget or rule changes.
  - The collapse rule is fixed before the data, so it can't be fitted to them.
- **What I expect.**
  - G2 ends about Thursday, G3 about Saturday, G4 about Tuesday morning, and the upscaler about Tuesday afternoon; then the run stops for review.
  - Neither loop meets the collapse flag by G4 (prediction 170).

## 2026-11-16, afternoon: the G1 latent walks done and reported; G2 packages and datasets built

- **What changed.**
  - **The G1 latent walks** ran 10:22–13:24: 9,999 steps and 10,000 tiles each, with no restart. The pipeline wrote the readouts (`notes/gen1/latent/`).
  - **`notes/gen1_latent_report.md`** scores the predictions: 158 wrong, 159 half right, 160 right and undecided, 161 wrong, 162 right, 163 right.
  - **`analysis/gen1/latent_taste_ci.py`**: chosen minus offered per step, with bootstrap intervals over steps (`taste_ci.csv`).
  - **G2 packages** (render check passed, at most 2 of 255) and **datasets** (curious τ = 2.62 at ESS 0.5 N) were built by the pipeline. The manifests are in `notes/gen2/packages/`, tag `g2-paths`.
- **Why this approach.**
  - The taste gaps are small, so each needed an interval before it is called a gap at all.
  - The interval is over steps of one walk; across walks and GANs these remain hints.
- **What I expect.**
  - G2 training runs about 57 h and finishes about Thursday morning; then FID, readouts, the G2 latent walks, and a stop.
  - The curious walker's texture preference is in G2-curious's training set. If prediction 166 holds, G2-curious will be more banded than G1-curious.

## 2026-11-16, morning: the G1 GANs trained and reported; the G1 latent walks running; generation 2 queued

- **What changed.**
  - **G1 training finished at 09:21:** 3,840 kimg each, in alternating 400 kimg chunks. There was one spurious restart (2026-11-14 19:14, a reused Windows pid) and no kimg were lost.
    - FID on the kept snapshots: curious 43.0 / 25.7 / 20.6 / 17.8, null 53.0 / 40.5 / 29.9 / 23.2.
    - Final ADA p: curious 0.161, null 0.141.
  - **The GAN readouts and the GAN report** (`notes/gen1_gan_report.md`): predictions 152 partly right, 153 mostly wrong, 154 deferred, 155 wrong, 156 partly right, 157 mostly wrong.
  - **The supervisor:** a job is alive only with no exit record since its start and a process created at its start. This is the pid-reuse fix.
  - **The latent walks** (`agent/latent_walk.py`, `analysis/gen1/latent_readouts.py`, stages `latent_walks` and `latent_readouts`): the step is calibrated by colour character (Moe), and the pixel observer is logged too.
  - **Generation 2** (Moe, 2026-11-16; `notes/brief_g2.md`):
    - `scripts/g2_package.py` turns a latent walk into a G1-format package, with a render check and sha256 manifest;
    - `gen/g1_gan.py` takes `--gen` and gains `inherit_budget`; the latent walker and readouts take `--gen`;
    - new stages `g2_packages` … `g2_latent_readouts` before `final`;
    - tested on test walks, and the test outputs were deleted.
  - **Predictions** 158–163 (the latent walks, with a dated note on the observer) and 164–168 (G2), each written before its run.
  - **`notes/upscaling.md` and `scripts/upscale_faithful.py`** document the resolution chain (178 px at 60 m → 256 → 128 px at 83 m) and faithful enlargement.
- **Why this approach.**
  - G2 reuses every G1 rule and G1's measured budget, so that the generations differ only by what they were trained on.
  - The latent step keeps the real 15 km reference in every generation, so "a nearby place" means the same thing across the recursion.
- **What I expect.**
  - The G1 latent walks finish around 12:30, and G2 training starts right after them.
  - G2 finishes about Thursday 2026-11-19 morning, then the pipeline stops for review.
  - Prediction 166 is the one to watch: the curious loop drifts towards the apparatus, with more banding and more band-yellow, while the null loop holds.

## 2026-11-13, evening: generation 1 moves to the PC. The world rebuilt and checked, the walks running, the pipeline and Phase A tested

- **What changed.**
  - **Device:** the PC. Quadro RTX 5000 (16 GB), driver 596.71, CUDA 13.2, Windows 11 Pro, i9-10980XE, 128 GB RAM (`runs/g1/device.txt`).
    - The walker's `.venv` was synced to `uv.lock` (it lacked rasterio).
    - The GAN side runs in `.venv-sg` (torch 2.14 + cu130, matching nvcc 13.2 for the plugins).
  - **The world, rebuilt from git** (`runs/g1/world_check.md`):
    - The first build failed the start-list check: 4 of 500 rows differed, though all 14 `clock.json` values matched. PROJ differs between macOS and Windows in the last bit, which reorders cells with tied latitudes in `index`.
    - Moe pushed the Mac's `grid.parquet`. Rebuilt from it, `clock.json` matches on all 14 values and the start list is identical (`git diff --exit-code`: 0).
    - The cache filled under the wrong labels was emptied.
  - **Windows fixes, none in the walk logic:**
    - `agent/walk.py`: the SIGUSR1 faulthandler hook is skipped where the signal doesn't exist.
    - `data/cache_cap.py`: Windows pin paths (backslashes) are normalised, so pins match again; files open in a walker are skipped instead of crashing the cap.
  - **The walks run on CPU with 3 threads,** the Mac's setting for the dry runs and the q calibration. The CPU and CUDA runs diverged within 50 smoke steps.
  - **The pipeline:**
    - `scripts/g1_pipeline.py` (a thin loop) and `scripts/g1_lib.py` (stages, state, STATUS; hot-reloaded) cover walks → packages → freeze (`g1-paths`) → walk readouts → datasets → throughput → budget (`g1-start`) → training → FID → GAN readouts.
    - `scripts/g1_job.py` records exit codes.
    - It runs under a scheduled task (S4U, registered by Moe as admin: startup, logon, every 15 min).
    - Generation-1 walks curious w000 and Null w000 started at 16:20 and 16:21.
  - **New code:**
    - `scripts/g1_package.py`: the handoff packages, with the render check against a fresh, empty-cache store.
    - `scripts/g1_verify.py`: package verification.
    - `gen/g1_gan.py`: datasets, τ for ESS = 0.5 N, throughput, budget, resumable training, FID, readouts.
    - `gen/g1_tests.py`: the Phase A tests.
    - `analysis/gen1/readouts.py gen1`: the walk readouts, plus matched clock stretches, package era, last-50 strips and the numbers for 143–151.
  - **StyleGAN2-ADA** (NVlabs d72cc7d) with one documented diff, `scripts/stylegan2ada_g1.patch`:
    - torch-2 custom ops, the sampler base class, and `grid_sample_gradfix` as in StyleGAN3;
    - scipy 1.18's `sqrtm`;
    - the seeded weighted sampler;
    - full resume (optimisers, kimg, tick, batch index, augment p, RNG; `stats.jsonl` appended);
    - a snapshot callback.
  - **Phase A tests, all passed** (on TEST packages of 200 tiles from the running walks' first checkpoint; deleted afterwards; results in `runs/g1/phase_a/`):
    - weighted sampler, 100k draws (χ² z 0.76);
    - kill/resume: Adam's step counters and the batch index equal an uninterrupted run, and kimg and augment p continue;
    - the STOP file stops a run after a snapshot;
    - both CUDA plugins compile;
    - FID with Inception cached (~6 min per fid50k_full);
    - full-size readouts (80 s per run);
    - the supervisor's watchdog (give up after 3 attempts, restart killed or stalled jobs), disk guard and status.
  - **Found and fixed by the tests:**
    - FID crashed on scipy 1.18;
    - the resume check had to survive snapshot retention;
    - the weighted precision/recall reference had fewer distinct points than the unweighted one, which inflated precision by construction. It now draws until both hold the same number of distinct tiles.
- **Why this approach.**
  - The rule was to prove the world is the Mac's before walking. The cell order is part of the world: it decides start cells and the held-out set. So a matching `clock.json` was not enough.
  - Everything that can fail in Phase B was made to fail once here, as the GAN brief asks.
- **What I expect.**
  - Both first walks reach 1977 near step 5,000 with roughly 4,500–5,000 unique tiles. Both conditions then need w001, and possibly w002, against prediction 143 (curious two walks) and 144 (the Null one long walk).
  - The pipeline then runs unattended: about 60 h of GAN work after the walks.

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
