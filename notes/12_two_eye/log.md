# Experiment 12, the Landsat 1 world and the two-eye walker: log

Brief: `notes/brief_landsat_pipeline.md` (2026-11-12). World portrait: `notes/11_landsat1_mission/world.md`. Predictions 96–110: `notes/06_characters/expectations.md`, section "Experiment 12". Report: `observations.md`. Configs `configs/12_two_eye/`, analysis `analysis/e12/`, results `results/`, runs `runs/e12_*`. Device: the MacBook (CPU); no GAN training.

## 2026-11-12: where the brief and the code disagreed (stated before building)

1. **No Major TOM grid code exists in `curious_and_bored`.** That branch reads Major TOM's metadata (cell names, centres); it has no grid. The grid is implemented in `data/landsat1_world.py` from Major TOM's published definition (`src/grid.py` in ESA-PhiLab/Major-TOM). Checked against the archive: centres match for 99.96 % of Major TOM's land and coast cells (p95 distance 0.000 km). The crop is centred on the 10 km cell (grid point + 5.0 km in its UTM zone), not on point + 5.34 km.
2. **The census held no raster geometry**, so the pixel window could not come "from census metadata only". The catalogue was queried again for `proj:transform` and `proj:shape` (`census.py items_proj`).
3. **The test bed was in linear tone.** `c10680m_256px_cir` was built before e10 switched to sqrt; the brief's eye colour is e10's sqrt. The pass was rebuilt at 256 px in sqrt tone (`c10680m_256px_cir_sqrt`, `data/landsat_pass.py build --tone sqrt`), and the factorial walks on it. The linear world is kept.
   - Side effect, for the record: `analysis/landsat1/render_quirks.py` (research of 2026-11-11) applied the linear world's stretch after a sqrt tone. The rendered tiles in `figures/quirks_*.png` are therefore brighter than any world's one view. Not redone.
4. **"Your assessment of the crop eye and your note on the three hand-made choices"** are not in the repository (searched `notes/`, `analysis/`, `agent/`, `claude_research/`). Worked from the brief.

## 2026-11-12: A, the world

- Grid, candidates, selection, portrait: `notes/11_landsat1_mission/world.md`. 1,466,863 cells.
- **Catalogue quirk:** Planetary Computer's `proj:epsg` drops the zero of UTM zones 1–9 (3265 for 32605) on 27,171 items. Read as the zone it names; the catalogue value is kept. `3031` (Antarctic polar stereographic) is a real code.
- **Coverage rule (hand-set):** a scene covers a cell when the footprint holds the cell's centre and four corners. Cells only partly inside every footprint are left out (49,153 land cells, 3.2 %).
- **Window (hand-set):** 178 × 178 px centred on the cell in the scene's own projection and pixel grid. Where the scene's UTM zone is not the cell's, the window is north-up in the scene's zone, not rotated. Not resampled.
- **Night radiometry:** M · DN + A without the sun term (no infinities), flagged `night`.
- **The stretch:** from the baseline (2,000 random cells, uniform over cells, seed 20261112), daylit cells only, percentiles 0.5–99.5 in sqrt reflectance. Constants in `data/landsat1_store.py`.
- **Quirk definitions.** QA_RADSAT saturation bits 3–6 for MSS bands 4–7 (green, red, nir08, nir09); dropped pixel bit 9. Stripe is e10's measure per band, on a window with a 2 px margin, so the vertical median at the window's edge uses real neighbours. Grid crops in native pixels: bounds 0, 44, 89, 134, 178.
- The index column `cloud_cover` (the walker's log column) is the scene's listed cloud; the cell's own QA cloud is in the quirk table.
- **The pass world's quirks** (`analysis/e12/pass_quirks.py`): QA_RADSAT downloaded for its 53 scenes; per-cell and per-crop tables in the world folder. The cell's stripe share matches e10's (Spearman 0.997), and `render` reproduces its tiles exactly.

## 2026-11-12: B and C, the two eyes (`agent/eyes.py`, `eye:` in `agent/walk.py`)

As the brief, with these choices (each a config key, recorded in `meta.json`):

- **v1 stays reproducible.** `eye: v1` is the default. Checked: 60 steps of `e10_pass_v1` with the new code are bit-identical to the old code in every column of `steps`, `candidates`, `heldout` and in `archive.npz` (`runs/e12_check_v1_before_s0`, `_after_s0`). Two columns were added to `steps.parquet` for every eye: `p_chosen` and `best_offer` (brief C8). They draw no random numbers.
- `eye: grid | two_eye` needs `nav: compass` and the curious policy.
- **Progress** is the grid network's probe on the checkerboard split: three Adam steps on the eight crops with (row + col) even, the error drop measured on the eight odd ones.
- **Surprise** in `steps.e` and `candidates.e` is the grid's error, the mean over the 16 crops; `e_grid_max` and `e_glance` are logged beside it. `w_e` stays 0.
- **Training crops (hand-set):** the top-k crops by novelty, cycled to 16 crops so that every pooling trains on the same number of crops per step (top-1: 16 jittered copies of one crop; mean: each crop once), each moved by a uniform jitter of up to 4 px (`jitter_px`), plus v1's 48 replay crops. With top-k alone, top-1 would learn 16 times less per step than mean pooling, and pooling would be confounded with learning rate.
- **Glance training (hand-set):** the chosen glance plus 15 past glances (`glance_replay_batch`), four Adam steps, its own optimiser and buffer.
- **The shadow** is the tile mean of the grid network's 16 crop latents, with v1's kNN (unit latents). A separate v1 network would need random crops and so would draw random numbers. The shadow fills `archive.npz` (one row per visit). It measures v1's pooling under the grid network, not v1's network.
- **Memories** take every one of the 16 crops after training (v1's archive order); `refresh_archive: candidates` replaces a revisited offer's memories with its current encoding (fixed grid: no extra fetch).
- **Re-embedding** every 100 steps re-encodes the three memories from the stored tiles (`TwoEye.reembed`).
- **Logged:** per step, the components (`n_glance`, `n_grid`, `prog`, `surp`), their z, weights, contributions `c_*`, shares of |contribution| `share_*` and lifts `lift_*` (contribution at the choice minus its mean over the offers; the lifts sum to I − mean I, checked to 2e-16), surprise per eye, the shadow, the top crop; `crops.parquet` (one row per offered crop: position, error, novelty, rank, share of the pooled score, quirks); `train_crops.parquet` (the 16 jittered training crops); `glance_err.npy` (32 × 32 float16 per step), `crop_latents.npy` and `glance_latents.npy` (chosen tile only), `forgetting.parquet`, `memories.npz`. Checkpoints hold both networks (`model` is the grid network, so readouts that load a ConvAE still work).
- **Forgetting set (hand-set thresholds):** `analysis/e12/forget_set.py`, 8 sea, 8 sand, 8 field tiles each for the pass and for the mission world. A first draw of the pass's fields included a black tile; fields now need a mean pixel above 40.
- Smoke walk: `runs/e12_smoke_two_s0`, 120 steps, 0.94 s a step alone.

## 2026-11-12: E, the factorial

- Predictions 96–110 written before any factorial walk; commit tagged `e12-factorial`.
- **The Null** is the two-eye walker (top-4, w_glance 1) with a uniform choice, so that every readout of the eye also exists for the Null.
- **The interest-statistics check (B7)** runs as two more conditions: `e12_two_top4` with e09's existing shifted and shuffled radius schedules (seeds 0–1), not new schedules from this walker.
- **Two seeds** cannot make a lead or a result by e08's rule. Called a **hint** here: both seeds outside the Null's two-seed range on the same side.
- Batch `scripts/hikes_e12.sh start factorial`: 18 walks, three side by side, three threads each, started 10:23 with 35 GB free.
- The readouts (`analysis/e12/readouts.py`) and the contact sheet (`analysis/e12/contact_sheet.py`) were written and tested on the smoke walk before the factorial finished.
