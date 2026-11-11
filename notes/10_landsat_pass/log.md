# Log: experiment 10, a walk on one Landsat pass (placeholder name)

No brief yet. This log covers the infrastructure only: a world made of one orbital pass of one satellite, so the satellite's own strip is the first walk and the walker follows inside it.

## 2026-11-09/10: research (before any code)

- **Sentinel-2.** One satellite repeats its ground track every 10 days (143 orbits, ~100 min each). One pass is a strip 290 km wide. Earth Search STAC (`s2:datatake_id`) returns a whole datatake, and the 10 m true-colour COGs are public on AWS.
  - In S2A's cycle of 1–11 July 2023, the longest pass is 34 min (Svalbard → South Africa), ~39,000 cells of 10 km; the median orbit has ~22,000.
  - Major TOM cannot give a pass: it keeps one random date per cell, so a datatake leaves a median of 12 cells.
- **Oldest usable pass.** Landsat 1 MSS (launched 23 July 1972). Collection 2 Level-1 is on Microsoft Planetary Computer and needs no account. The first daylight scene is from 25 July 1972.
  - Of 53,168 Landsat 1 scenes up to July 1973, the largest unbroken pass is **22 November 1972, WRS path 183**: 53 scenes, 22 min, 8,650 km, from the Caucasus (41.5° N) to the south of Africa (34.5° S), with one gap (row 82).
  - Older material (CORONA, 1960–72) is panchromatic film with panoramic distortion and is mostly order-only. Not usable as a world.
- **Geometry.** The MSS strip is 185 km wide. Compass offers inside the strip: 7.6 of 8 at 15 km, 6.6 at 50 km, 2.6 at 200 km; at 500 km, 28 % of steps have none. At r_min 15 km the walker meets an edge every ~40 steps.

## 2026-11-10: infrastructure

- **`data/landsat_pass.py`**
  - `list`: ranks the passes of a date range by number of daylight scenes.
  - `fetch`: downloads one pass (four bands, QA_PIXEL, MTL, the STAC item) to `data/landsat/<pass>/scenes/` and writes `pass.json`.
  - `build`: cuts the pass into a world folder `data/landsat/<pass>/<world>/` with `tiles.npy`, `index.parquet`, `world.json`, `check_mosaic.png` and `check_tiles.png`.
  - `check`: redraws the two check images.
  - `PassStore`: the built world behind `TileStore`'s interface.
  - The choices are in the module docstring and in `world.json`.
- **`data/tile_store.py`**: `open_store(cfg)` returns the global store or, for `world: landsat_pass`, a `PassStore`. `World.from_config` takes the whole pass as the pool.
- **`agent/walk.py`**: `LazyTiles` opens its store through `open_store`, and `meta.json` records `pass_world`. Nothing else changed.
  - **Check:** `e09_ref`, seed 0, 40 steps on the global store, against `runs/e09_ref_s0`: same tile sequence, interest and error identical to the last bit. The check run was deleted afterwards.
- **`analysis/e09/walk_viewer.py`**: tiles and the lat/lon index come from `open_store(cfg)`, so a pass walk shows its own tiles.
- **Dependencies:** `rasterio>=1.4` declared again in `pyproject.toml` (removed in an early commit, still installed). `uv lock` added only `rasterio` and `affine`.
- **`.gitignore`**: `!data/landsat_pass.py`. `data/landsat/` stays ignored.

## 2026-11-10: the first world, `LM01_183_19721122/c10680m_256px_cir`

- **Fetch:** 53 scenes, 1.8 GB, rows 31–84 with the gap at 82.
- **Build:** the defaults, 3 min 55 s.
  - 14,658 candidate cells, of which **13,419 are kept** after the overlap rule: 12,450 land, 849 ocean, 120 coast. That is fewer than the ~16,000 estimated from the footprint area, because cells on the skewed swath edges are not whole.
  - Mean cloud 18.7 %. 2.64 GB of tiles.
  - The stretch in TOA reflectance (nir, red, green): lo 0.022 / 0.037 / 0.045, hi 0.69 / 0.66 / 0.76.
- **The scale is that of the Major TOM low-res tiles:**
  - cell 10.68 km = 178 native 60 m pixels → 256 px, 41.7 m/px;
  - crop_px 64 is still a ~2.7 km eye, and radius_min_km 15 / snap_floor_km 7.5 mean what they meant.
- **Seams:**
  - Inside one UTM zone the overlap cells coincide and the seams are clean.
  - Where the pass changes zone (36 → 37 → 38), the two grids do not line up and small gaps remain (visible in `check_mosaic.png`).
  - Rows 83–84 are an island ~360 km south of the main strip, reachable only by a far step.
- **Line defects (not foreseen).** The 1972 scenes carry short bad scan-line segments in single bands, which show as coloured stripes in the tiles.
  - QA_RADSAT does not isolate them: it flags about half of one scene as saturated in green, while only 0.1 % of its pixels are at 255.
  - A vertical-median repair (5 pixels, threshold 25 DN) was tried on five tiles. It removed some lines, drew others and shifted colours. In the worst scene (row 83) the defects are several lines thick. **Not adopted.**
  - **What the build does instead.** It measures them: `stripe` per cell is the share of pixels more than 25 DN from their vertical 5-pixel median, in any band. `--max-stripe` can drop cells above a share; the default keeps all.
  - Median cell 1.2 %; 41 % of cells above 2 %, 26 % above 5 %. Rows 76–84 (the southern end) have medians of 12–41 %.
  - Rows 64–65 (cloud around Lake Victoria) score 6–11 %. That is probably cloud edges, not lines: the measure counts any sharp change from row to row.
  - **For the walk.** Stripes may act as a real noisy TV. Read `stripe` at chosen against offered cells before trusting any taste readout from this world.
- **Colour:** `cir` (near-infrared / red / green): vegetation red, deserts yellow, water black, cloud pale pink. MSS has no blue band. `--render pseudo` is a synthetic natural colour, not a measurement.

## 2026-11-10: smoke walk

- **Config** `configs/10_landsat_pass/e10_pass_v1.yaml`: walker v1 with four keys changed (`world`, `pass_world`, `start_lat`, `start_lon`; checked on the parsed settings). The start is the centre of the pass's first scene, row 31, in Georgia (41.53° N, 44.58° E).
  - radius_max_km stays at 2,000 km. In the strip, far offers snap to the nearest cell (snap_tol 0.25 r), so far steps become steps along the track. Not yet seen: the smoke walk never left r_min.
- **`runs/e10_pass_smoke_s0`**: 300 steps, 225 s alone, 3 threads.
  - 135 distinct cells, lat 41.2–42.4. Held-out set of 200 from the pass.
  - Nothing fetched, nothing dropped (0.75 s per step).
  - Eight offers in 222 of 300 steps, 4–7 in the rest: 140 offers dropped as too far, 92 as duplicates, at the strip's edges.
  - Stripe share at chosen cells 0.012, at offered cells 0.012; the pass's mean is 0.058, but the walk stayed in the clean north.
- **Viewer** `analysis/e09/walk_viewer.py e10_pass_smoke_s0 --out <dir>`: builds (135 tiles), and the page renders in headless Chrome. Its world map does not draw the pass's footprint.

## 2026-11-10: first try, 300 steps at a lowered scale

Asked for: 300 steps on the pass, stripes and defects kept, the walker's scale lowered so that its decisions stay distinct for up to 15,000 steps, born on the first tile of the pass, with the compass navigation, and a clip.

- **World** `c5340m_128px_cir` (`build --cell-m 5340 --tile-px 128`):
  - 5.34 km cells (89 native pixels) at 128 px, still 41.7 m/px.
  - 61,520 candidates, **55,082 kept** (51,189 land). Stripes kept (`max_stripe` 1).
  - Capacity: 15,000 steps that all landed on new cells would use 27 % of the world. The long walk of v1 made 10,002 distinct cells in 15,000 steps, which would be 18 %.
- **Eye unchanged:** crop_px 64, ~2.7 km. A smaller eye would show the network upsampled 1972 pixels. Two random crops of one tile now overlap on average 44 % (as for crop 128 in 256 px tiles in e09 Stage 3a).
- **Radii from the offers** (`analysis/e10/offers_geometry.py`, `results/offers_geometry_*.csv`; the walker's own `CP.offers` on the built world, 1,500 random cells plus 1,500 edge cells per radius):

  | r (km) | distinct offers (mean) | all 8 | ≥ 4 | duplicates |
  |---|---|---|---|---|
  | 5 | 6.1 | 0.52 | 0.98 | 0.22 |
  | **7.5** | **7.6** | 0.87 | 1.00 | 0.03 |
  | 15 | 7.6 | 0.85 | 1.00 | 0 |
  | 50 | 7.0 | 0.58 | 1.00 | 0 |
  | **100** | **6.1** | 0.17 | 0.99 | 0 |
  | 150 | 5.2 | 0 | 0.98 | 0 |
  | 200 | 4.3 | 0 | 0.94 | 0 |

  - On the 10.68 km world at v1's own r_max (2,000 km): 1.3 offers, and none in 21 % of steps.
  - Chosen: **r_min 7.5 km** (1.4 cells, as v1's 15 km on the 10 km grid; v1 had 7.5 offers and 3 % duplicates there), **r_max 100 km** (the largest radius with ≥ 6 offers on average and ≥ 4 in 99 % of steps), and **snap_floor_km 4.0** (v1's 7.5 km scaled to the cell). Δ, the drive and every other setting are v1's.
  - Cells near the strip's edge get 4.6–5.0 offers at every radius: the strip is the limit there, not the radius.
- **Start:** tile 0, the northernmost cell, in the first scene (row 31), 42.42° N 44.08° E in the Greater Caucasus. The config gives its exact centre; meta `start_tile` 0.
- **First run** `e10_pass_5km` (`runs/e10_pass_5km_s0`, linear tone): **the decisions were not distinct.**
  - The best offer's choice probability had a median of 0.156 (chance is 0.125; e09_ref_s0 had 0.485). Interest varied among a step's offers by a median of 0.11 (e09_ref_s0: 2.10).
  - Novelty had a median of 0.0006 (e09_ref_s0: 0.17), progress was 0. The radius never left r_min.
  - **Cause:** the tiles were dark. Mean pixel 29 against 92 on e09_ref_s0's tiles, 62 % of pixels below 30: the pass-wide linear stretch is set at the top by clouds and desert.
  - **Check:** on the same 100 tiles, a fresh network's normalised latents lay at a median distance of 0.023 from one another; on the same tiles in sqrt tone, 0.041; on e09_ref_s0's tiles, 0.052. So dark tiles start almost on one point.
- **Fix:** `--tone sqrt` (now the default), the square root of reflectance before the stretch: the curve Major TOM's thumbnails follow. World `c5340m_128px_cir_sqrt`: mean pixel 98 (Major TOM ~100), 0.6 % clipped. The linear world and its run are kept as the record.
- **Run** `e10_pass_5km_sqrt` (`runs/e10_pass_5km_sqrt_s0`): 300 steps, 280 s alone, 3 threads.
  - **The decisions are distinct again.** The best offer's probability has a median of 0.485 (e09_ref_s0: 0.485). Interest varies among offers by a median of 2.35, and novelty has a median of 0.156.
  - 186 distinct cells, 114 returns onto visited cells.
  - At r_min 63 % of steps, at r_max 9 %, in 1 bout, which starts at step 217.
  - 5,800 km travelled. The walk ends 485 km south of the start, near Lake Van (38.2° N 42.8° E), in scene rows 31–34.
  - 7.4 offers per step, 8 in 79 % of steps, never fewer than 2.
  - Stripe share: 0.032 at chosen cells, 0.029 offered. Cloud: 13.3 % chosen, 12.1 % offered.
- **Clip** `analysis/e10/film_pass.py` (new):
  - Layout: left, the tile stood on; right, the whole pass with the track, and a local map from the world's tiles whose window follows the radius, with the ring and the eight offers sized by their choice probability.
  - The film opens on the birth tile, held for 4 steps. A step's offers are drawn around where the walker stood when they were made.
  - Checked on preview frames (birth, step 0, the first r_max step 217, step 299).
  - `runs/e10_films/e10_pass_5km_sqrt_s0.mp4`: 91 s, 1280×720, 76 MB, git-ignored. Contact sheet: `results/films/e10_pass_5km_sqrt_s0_contact.png`.

## Open, for the brief

- Cell size and scale: 5.34 km / r_min 7.5 / r_max 100 is the first try. The drive's Δ is v1's and was not retuned for the narrower radius range (×13 instead of ×133).
- Keep the stripes (a real 1972 noisy TV), drop the worst cells (`--max-stripe`), or find a proper MSS destriping.
- `cir` or `pseudo` colour.
- The start: the satellite's first scene (as now) or elsewhere.
- Whether the walk may see only what the satellite has already passed (scenes in time order).
