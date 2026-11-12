# Experiments

One folder per experiment, numbered in the order they were run. Each one has a brief (what was asked), an expectation written before running, a log of decisions and deviations, and observations. Code stays in the shared packages (`data/`, `agent/`, `gen/`, `analysis/`); run outputs are in `runs/` and `data/`, which git ignores.

## Naming

- **Experiment folder:** `NN_topic`, e.g. `06_characters`. The number gives the order, the topic says what the experiment is about. `notes/` and `configs/` use the same folder names, so `configs/06_characters/` holds the configs for `notes/06_characters/`.
- **Run IDs are permanent.** A run is named after its config file (`runs/<config>_s<seed>/`), and those names are quoted in the analysis code, the notes and the paper, and used on three machines. Config files therefore keep their original names when they move: `h2910_` (06), `h0111_` (07), `global_` (03, 04), no prefix (01).
- **From experiment 08 on**, config files and run IDs start with `eNN_`, e.g. `configs/08_topic/e08_bored.yaml` → `runs/e08_bored_s0/`. Analysis scripts for one experiment go in `analysis/eNN/`; the CSVs and figures they write go in `notes/NN_topic/results/`.

| # | Folder | Dates | Question | Status | Old name / run prefix |
|---|---|---|---|---|---|
| 01 | `01_first_walk/` | 2026-10-24 | Do curious agents with different temperaments walk differently, and does a DDPM trained on an agent's path dream differently from one trained on random tiles? | done | first walk + dreams v1 / none |
| 02 | `02_dreams_hires/` | 2026-10-27 | Do 10 m crops and agent-driven selection or guidance change the dreams? | done (Step B, 128 px, not run) | dreams v2 / – |
| 03 | `03_planet_walks/` | 2026-10-28 | 3a: the v1 baseline agent walking the whole planet vs. confined to the Great Sand Sea. 3b: can the agent's learning progress steer a GAN's latent space to dreams beyond what it saw? | 3a walks done; 3b paused before training | dreams v3 / `global_`, `confined_` |
| 04 | `04_perception_fix/` | 2026-10-29 | Do the walkers still dwell and step straight back once perception is fixed (fixed crops, fresh archive latents, normalised latents)? | in progress | hikes v3 revised / `global_` |
| 05 | `05_attention_films/` | 2026-10-29 | Where does a walker look inside a tile it found novel, and in what order? Rendered as a Ken Burns film | first films | attention films / – |
| 06 | `06_characters/` | 2026-10-29 | Do Bored, Globalist, Localist and Fast learner settings give walks that differ by more than the seed-to-seed spread? | done (part 1: 1,000 steps from Milan; part 2: 5,000 steps from Paris) | hikes 29.10 / `h2910_` |
| 07 | `07_film_arc/` | 2026-11-01 | Emergent or designed arc for the film? Is "interesting" the same as "hard to draw", and what does the scorer really do? | done (the recommended 5,000-step walk not run) | round h0111 / `h0111_` |
| 08 | `08_character_sheet/` | 2026-11-03 | Which settings are responsible for what, in what the walker sees and how it moves? A character sheet backed by paired walks | Stage 0 done; Done: Stages 0 and 1, seeds 4–7 for seven settings (17 results); Stages 2–3 replaced by the new navigation | round h0311 / `e08_` |
| 09 | `09_compass/` | 2026-11-08 | Can one drive set how far the walker looks (eight offers at one radius, close when curious, far when bored), and is the rhythm that comes out the walker's or the mapping's? | Stage 2 walked (48 walks): the radius follows the drive and a rhythm comes out, but the loop is open (going far does not restore the drive) and the rhythm is the drive's filter, shared with the Null; character against the Null (preference, clusters) comes from the choice. Stage 3a (larger eye, 24 walks, world-view readout): a 5.3 or 8 km eye does not open the loop (far offers stay duller than near ones even decoupled), the embedding is ordered at continental scale at every eye, and no eye beats colour on land cover. Progress test (12 walks): a drive on learning progress does not make far pay either; it makes a homebody with rare long voyages. Walker v1 frozen (= the compass Reference, tag `walker-v1`) and walked for 15,000 steps: rhythm, preference and clusters last, a taste for texture, contrast and snow grows for 6,000 steps and takes the walker into the high north, novelty does not wear down, and the embedding's ordering by distance dissolves (Tobler ρ 0.16 → −0.02) | `e09_` |
| 10 | `10_landsat_pass/` | 2026-11-10 | Placeholder: a walk inside one orbital pass of one satellite (the satellite as the first walker). Oldest usable pass: Landsat 1 MSS, 22 Nov 1972, path 183 (Caucasus → South Africa) | infrastructure built; first try: 300 steps of walker v1 at 5.34 km cells (r 7.5–100 km) from the pass's first tile, and a clip (no brief yet) | `e10_` |
| 11 | `11_landsat1_mission/` | 2026-11-11 | A world made of the whole Landsat 1 mission (1972–78): sources, census, quirks; then the world itself on the Major TOM grid, one acquisition per cell (earliest) | research done; world built (1,466,863 cells), lazy store, quirk columns, portrait (`world.md`) | – |
| 12 | `12_two_eye/` | 2026-11-12 | Walker v2: a glance at the whole tile and a 4 × 4 grid of crops, each with its own network and memory. Which conditions chase stripes, cloud, brightness? The short factorial on the e10 pass, the death dry run, a smoke walk on the mission world | built; factorial walked | `e12_` |

Not an experiment: `agents_paper/`, the write-up of the agent design (Typst source, figures built by `build_figures.py`, PDF).

## 01. First walk + dreams v1

All documents and figures in `notes/01_first_walk/`:

- Brief: `brief.md`
- Expectation: `expectations.md`
- Observations (Gate 1 walks and Gate 2 dreams, deviations included): `observations.md`
- Figures: `img/` (`gate1_*`, `gate2_*`, `dreams_hires/`, `dreams_far/`, `latent_vs_geo_*`)
- Notebooks: `analysis/walks.ipynb`, `analysis/dreams.ipynb` (built by `analysis/build_*_nb.py`)
- Code: `data/prepare.py` (Northern Italy, 1,814 tiles + noisy TV), `agent/`, `gen/build_sets.py`, `gen/train_ddpm.py`, `gen/sample.py`, `analysis/latent_vs_geo.py`
- Configs: `configs/01_first_walk/` (`baseline`, `myopic`, `novelty_only`, `random`, `restless`, `surprise_only`, `wide`, `tvtest_*`)
- Scripts: `scripts/gate1.sh`, `scripts/gate1_extra.sh`, `scripts/gate2_train.sh`
- Runs: `runs/<config>_s<seed>/`. Only `runs/baseline_s0` exists on this machine (re-walked 2026-10-27, see the 02 log); the other 19 walks and the v1 DDPMs are on the laptop used for v1.
- Side experiment: narration of a walk by a language model, `narration/`.

## 02. Dreams v2: native 10 m + novelty at sampling time

All documents and figures in `notes/02_dreams_hires/`:

- Brief: `dreams-v2_hires-novelty-sampling.md`
- Expectation: `expectations_dreams_v2_2026-10-27.md`
- Log (setup, deviations, timing): `log.md`
- Observations: `observations.md`, with the contact sheets, `v1_vs_v2.png`, `guidance_sweep.png`, `memorisation_*.png`, `novelty_strips.png`, `summary.csv`
- Code: `gen/hires.py`, `gen/dreams_v2.py`, `gen/dreams_v2_report.py`; `gen/train_ddpm.py` gained `--bank`, `--out`, `--amp fp16` (v1 behaviour unchanged without them)
- Scripts: `scripts/dreams_v2_train.sh`, `scripts/dreams_v2_sample.sh`
- Outputs: `runs/baseline_s0/dreams_v2/` (models, samples, `scores.csv`), data `data/hires/`, `data/crops/`
- Agent used: `runs/baseline_s0` (v1 walk, not redone)

## 03. Planet walks and GAN dreams (dreams v3: 3a walks, 3b GAN dreams)

All documents and figures in `notes/03_planet_walks/`:

- Brief: `dreams-v3_gan-latent-search.md`
- Expectation: `expectations_dreams_v3_2026-10-28.md`
- Run log (decisions with the artist, the planet's coverage, colour scale, tile store, walks, GAN data, training, deviations): `run_log.md`
- **Status when paused, and how to continue: `status_paused_2026-10-28.md`**
- Reflection on the walkers' revisits: `reflection_revisits.md` (+ `revisit_attractors.png`)
- Figures: `world_coverage.png`, `global_stretch.png`
- The artist's own notes on the v3 hikes: `moe_hike_v3_observations.md`

3a, walks:

- Code: `data/global_index.py` (planet index), `data/tile_store.py` (lazy tile store, `World` pools), `data/global_stretch.py` (colour scale check); `agent/walk.py` gained tile backends (`RegionalTiles` for v1, `LazyTiles` for v3; checked bit-identical to v1), `agent/signals.patches` takes gathered tiles
- Configs: `configs/03_planet_walks/` (`global_baseline`, `confined_baseline`, `dev_regional_lazy` for development only)
- Analysis: `analysis/v3_maps.py` (path maps, walk summaries), `analysis/hike_viewer.py` (step-by-step `hike.html` per run, also works on v1 runs), `analysis/v3_revisits.py`
- Runs: `runs/global_baseline_s0/`, `runs/confined_baseline_s0/`; data `data/global/` (index, 11 GB tile cache)

3b, GAN dreams:

- Code: `gen/v3_datasets.py` (`agent_path`, `base_global`), `gen/dream_search.py` (latent evolution in W), `gen/dreams_v3_report.py`; `gen/build_sets.tile_weights` shared with v1
- Scripts: `scripts/dreams_v3_train.bat`, `scripts/dreams_v3_chain.bat`, `scripts/dreams_v3_search.bat`, `scripts/sg.bat` (StyleGAN environment), `scripts/stylegan3_torch2.patch`
- External: NVlabs `stylegan3` at `c233a91` in `third_party/stylegan3`, venv `.venv-sg` (both git-ignored; setup in `run_log.md`)
- Outputs: `data/v3/` (GAN datasets, 18 GB), `runs/global_baseline_s0/dreams_v3/` (maps, the stopped `gan/base` run)

## 04. Perception fix (hikes v3 revised)

All documents in `notes/04_perception_fix/`:

- Starting point: `notes/03_planet_walks/reflection_revisits.md` (options 1–4), `notes/03_planet_walks/moe_hike_v3_observations.md`; v3a code tagged `v3a-walks`
- Log (Mac setup, the revision switches, runs): `log.md`
- Code: revision switches in `agent/walk.py` and `agent/signals.py` (`score_crops`, `refresh_archive`, `normalise_latents`, `return_cost`, `no_backstep`; defaults = v3a walker)
- Configs: `configs/04_perception_fix/global_{fixedcrops,freshlatents,unitlatents,perception}.yaml`
- Runs: `runs/global_baseline_1k_s0/` and the revisions, 1,000 steps on the Mac (CPU)

## 05. Attention films

All documents in `notes/05_attention_films/`:

- Log (no gaze in the walker, the three orders, decisions, runs): `log.md`
- Follows main's per-patch novelty heat maps (`src/hiker/heatmap.py` on `main`)
- Code: `analysis/attention.py` (maps, shotlist, preview), `analysis/kenburns.py` (shotlist → MP4)
- Outputs: `runs/<run>/attention/step_<step>_<order>/` (`shotlist.json`, `maps.npz`, `preview.png`, `film.mp4`)

## 06. Characters (hikes 29.10)

All documents in `notes/06_characters/`:

- Brief (request as written + adjustments): `brief.md`
- Expectation: `expectations.md` (also holds the 07 predictions, section "Round h0111")
- Log: `log.md`
- Observations, parts 1 and 2: `observations.md` (+ `summary.csv`, `paris_summary.csv`, `paris_blocks.csv`, `paris_maps.png`, `paris_curves.png`, `maps_world.png`, `maps_milan.png`, `curves.png`); analysis `analysis/h2910_compare.py`
- Reflection on why the walkers still return: `reflection_revisits.md` (+ `revisit_favourites.png`); analysis `analysis/h2910_revisits.py`
- Configs: `configs/06_characters/h2910_{bored,globalist,localist,fastlearner}.yaml` (each `global_perception.yaml` at 1,000 steps with one or two keys changed)
- Script: `scripts/hikes_2910.sh`
- Runs: `runs/h2910_<character>_s{0,1}/`, reference `runs/global_perception_1k_s{0,1}/`
- Part 2: Bored and Globalist, 5,000 steps from Paris: `configs/06_characters/h2910_{bored,globalist}_paris.yaml`, `scripts/hikes_2910_paris.sh`, `runs/h2910_{bored,globalist}_paris_s0/`

## 07. Film arc (round h0111)

All documents in `notes/07_film_arc/`:

- Brief: `brief.md`
- Expectation: `notes/06_characters/expectations.md`, section "Round h0111"
- Log (decisions, deviations, the `.git` incident): `log.md`
- Observations, action plan, config options: `observations.md`
- Results: `results/` (CSVs, figures, `drawings/`, film contact sheets in `films/`)
- Code: `analysis/h0111/` (scripts; they write to `results/`); options in `agent/walk.py` (`rng_mode`, `choice`, `teleport_landing`, `landing_k`, `log_prev_error`, `ae_width`; defaults = the h2910 walker)
- Configs: `configs/07_film_arc/h0111_*.yaml`; `h0111_walk_5k.yaml` is the recommended walk, not yet run
- Script: `scripts/hikes_0111.sh` (`start`, `stop`; with a disk and `.git` watchdog)
- Runs: `runs/h0111_*`; films in `runs/h0111_films/`

## 08. Character sheet (round h0311)

All documents in `notes/08_character_sheet/`:

- Brief: `brief.md` (written as round h0311, before the naming convention; the note at its top maps its names to `e08_`)
- Expectation: `notes/06_characters/expectations.md`, section "Round h0311 / experiment 08", predictions 19–35 (2026-11-05, before the first Stage 1 walk)
- Log: `log.md`
- Observations, Stage 0 (what the readouts see, noise, the recommended core of readouts): `observations.md`
- Results: `results/` (readouts, paired differences, calibration, taste panel summaries and figures)
- Code: `analysis/e08/` (`sheet.py` shared, `readouts.py` Stage 0.1 and 0.3, `panel.py` Stage 0.2, `matrix.py` the knob-to-effect matrix on the core readouts), the panel's tile list `analysis/e08/panel.csv` (fixed, never changed); per-tile statistics and raw panel scores are cached in `data/sheet/` (git-ignored)
- Configs and runs: `configs/08_character_sheet/e08_*.yaml`, `runs/e08_*` (Stage 1 on), batch `scripts/hikes_e08.sh`

## 09. Compass walker

All documents in `notes/09_compass/`:

- Brief: `brief_e09_compass.md`
- Log (code, checks, deviations): `log.md`
- Observations, Stage 0 (the drive on the e08 logs, Δ, r_max, geometry, fetch cost, decisions D1–D7): `observations.md`
- Results: `results/` (`mapping*.csv`, `mapping.png`, `geometry_offers.*`, `fetchcost*.csv`; later the readouts and figures)
- Code: `agent/compass.py` (drive, radius rule, offers), `nav: compass` in `agent/walk.py` (default `classic` = every earlier walker, checked bit-identical); `analysis/e09/` (`mapping.py` 0.3, `geometry.py` and `geographiclib_check.py` 0.2, `fetchcost.py` 0.4, `readouts.py` and `schedules.py` 0.5, `stage1_diag.py` Stage 1, `worldview.py` (WorldCover probe, Tobler curve) before Stage 3a; `progress_offline.py` before the progress test; `long_walk.py` (blocks of 1,000 steps) and `walk_viewer.py` (step-by-step viewer, `runs/<run>/viewer/index.html`) for the long walk; shared `e09_common.py`)
- Configs: `configs/09_compass/e09_*.yaml`, radius schedules for the controls in `configs/09_compass/schedules/`
- Script: `scripts/hikes_e09.sh start <stage> | stop` (with the disk and `.git` watchdog)
- Runs: `runs/e09_*`; Stage 0 checks `e09_check_classic_s0`, `e09_test_fetch_s0`, `e09_smoke_s0`; Stage 1 `e09_reference_s0–3`, `e09_delta_0175_s0–3`, `e09_delta_07_s0–3`; Stage 1 round 2 `e09_avg20_d025_s0–3`, `e09_avg20_d035_s0–3`, `e09_avg20_d05_s0–3`; checks `e09_check_r1_s0_s0`, `e09_smoke_avg20_s0_s0`

## 10. Landsat pass (placeholder name)

All documents in `notes/10_landsat_pass/`:

- Log (research on single passes, the infrastructure, the first world, checks): `log.md`
- Code: `data/landsat_pass.py` (`list`, `fetch`, `build`, `check`; `PassStore`), `open_store` in `data/tile_store.py`, `world: landsat_pass` in `agent/walk.py` (the global store is unchanged, checked bit-identical); `analysis/e09/walk_viewer.py` reads the run's own store
- Data: `data/landsat/<pass>/scenes/` (downloads), `data/landsat/<pass>/<world>/` (tiles, index, check images); the first world is `LM01_183_19721122/c10680m_256px_cir`
- Code, analysis: `analysis/e10/offers_geometry.py` (distinct compass offers per radius on a built world), `analysis/e10/film_pass.py` (a clip of a pass walk)
- Results: `results/offers_geometry_*.csv`, `results/films/*_contact.png`; films in `runs/e10_films/` (git-ignored)
- Configs: `configs/10_landsat_pass/e10_pass_v1.yaml` (walker v1 unchanged, 10.68 km world), `e10_pass_5km.yaml` (5.34 km, linear tone: the first try, offers indistinguishable), `e10_pass_5km_sqrt.yaml` (the same in sqrt tone)
- Runs: `runs/e10_pass_smoke_s0`, `runs/e10_pass_5km_s0`, `runs/e10_pass_5km_sqrt_s0` (300 steps each)

## 11. Landsat 1 mission

All documents in `notes/11_landsat1_mission/`:

- Research (sources, census, quirk probe, rendered tiles, resolution, zoom): `research.md`
- The world (grid, candidates, selection, store, quirks, portrait): `world.md`
- Code: `analysis/landsat1/` (`census.py`, `quirk_probe.py`, `render_quirks.py`, `render_zoom.py`, `portrait.py`), `data/landsat1_world.py` (grid, candidates, index), `data/landsat1_store.py` (`Landsat1TileStore`, `world: landsat1`)
- Data: `data/landsat/landsat1_c2l1_items.parquet` (force-added), `data/landsat/landsat1_c2l1_proj.parquet`, `data/landsat1/` (git-ignored: grid, candidates, scenes, index, baseline, cache)
- Results and figures: `results/`, `figures/`

## 12. The two-eye walker

All documents in `notes/12_two_eye/`:

- Brief: `notes/brief_landsat_pipeline.md`
- Expectation: `notes/06_characters/expectations.md`, section "Experiment 12", predictions 96–110
- Log: `log.md`; report: `observations.md`
- Code: `agent/eyes.py`, `eye:` in `agent/walk.py` (default `v1`, checked bit-identical); `analysis/e12/` (`pass_quirks.py`, `forget_set.py`, `readouts.py`, `contact_sheet.py`)
- Configs: `configs/12_two_eye/e12_*.yaml`, forgetting sets `forget_pass.csv`, `forget_mission.csv`; batch `scripts/hikes_e12.sh`
- Test bed: `data/landsat/LM01_183_19721122/c10680m_256px_cir_sqrt` (with `quirks.parquet`, `crop_quirks.parquet`)
- Runs: `runs/e12_*`; checks `e12_check_v1_before_s0`, `e12_check_v1_after_s0`, `e12_smoke_two_s0`
