# Compass walker (experiment 09): log

Brief: `brief_e09_compass.md` (proposal of 2026-11-08). Report: `observations.md`. Code: `agent/compass.py`, `agent/walk.py` (`nav: compass`), `analysis/e09/`. Configs: `configs/09_compass/`. Results: `results/`.

## 2026-11-08: Stage 0

### 0.1 Code

- **`agent/compass.py`** holds the drive (`Drive`), the radius rule (`radius`, `radii`), the long-yardstick norm (`LongNorm`), the great-circle destination point and the eight offers (`offers`). The walker and the offline analysis import the same functions.
- **`agent/walk.py`, `nav: compass`.** Every compass branch is behind `compass = cfg.get("nav", "classic") == "compass"`; the classic path is unchanged. In compass mode: no far offers, no boredom (B is not updated, no teleports, no `bored_*.pt`), and `p_long_jump` and `patience` do nothing. The keys and their meaning are in `configs/09_compass/e09_reference.yaml`.
- **Random streams.** Two streams appended to `RNG_STREAMS`: `compass` (the rotation θ) and `radius` (jitter). SeedSequence children depend only on their position, so appending changes no earlier stream (checked: the first nine children are identical whether 9 or 11 are spawned).
- **Order within a step.** Offers at r_t → look → score → choose → the drive is updated with the chosen offer's value → r_{t+1} and θ_{t+1} are set and the next eight offers are computed and **prefetched** before training. That overlaps fetching with training (about 0.5 s). The compass walker does not prefetch the ring of neighbours around the cell (the classic `T.prefetch`), since it knows exactly which eight cells come next.
- **Edge rules (not in the brief).** If every target is dropped, the compass is turned (θ redrawn from [0, 360)) up to 20 times; then the eight indexed cells nearest the current one are offered. If no offer can be fetched even after the 120 s wait, θ is redrawn (the classic walker redraws a blind tile). Neither happened in any test walk.
- **Logged per step** (`steps.parquet`): `r_km`, `theta`, `drive_x` (the signal value at the chosen cell), `drive_short`, `drive_long`, `drive_sd_long`, `drive_d` (after the step's choice), `n_drop_far`, `n_drop_dup`, `n_drop_self`, `heading`. Per candidate (`candidates.parquet`): `I_long`, `bearing`, `cand_km`; kind `compass` (or `stay`).
- **Check (brief 0.1): passed.** `h0111_reference.yaml`, seed 0, 200 steps, with the new code (`runs/e09_check_classic_s0`): every column of `steps.parquet` (tile, e, n, g, their z-scores, I, max I, candidates, jump type, B, bored events, errors before and after, e_self_after, e_prev_after), all 1,271 candidate rows (tile, kind, I, p, chosen) and the held-out error at every logged step are bit-identical to `h0111_reference_s0`.

### 0.2 Geometry (`analysis/e09/geometry.py`, `geographiclib_check.py`)

- Destination point on a sphere of R = 6,371.0088 km (the radius of `haversine_km`). Against an independent 3-D vector rotation: largest difference 4·10⁻⁸ m over 200,000 random cases (1–19,000 km). Against geographiclib's `Direct` on the same sphere (run in a throwaway `uv` environment; the project gains no dependency): largest difference 4·10⁻⁸ m over 20,000 cases. Round trip (distance and initial bearing back from the target): 7·10⁻⁸ m, 5·10⁻¹⁰°.
- Poles and antimeridian: over the north pole, near the south pole and across the antimeridian in both directions, both implementations agree and the distance back is exact; longitudes stay in [−180, 180). The BallTree uses the haversine metric, so nearest cells across the antimeridian need nothing special.
- **Snap tolerance.** The global index is a 10 km grid (nearest-neighbour spacing 9.98–9.99 km), so the nearest cell to a target can be up to about 7.1 km away. With the brief's 0.25 · r alone, at r_min (15 km) only 2.0 of 8 offers survive on average and 33 % of steps have none. Added `snap_floor_km: 7.5`: an offer may sit max(0.25 r, 7.5 km) from its target. That gives 7.5 offers at 15 km (3 % dropped as too far, 3 % duplicates) and changes nothing from 30 km on (0.25 r ≥ 7.5 km). **A deviation from the brief, for review.**
- Figure `results/geometry_offers.png`: offers of 20 random cells at 15, 100, 500, 2,000 and 10,000 km; zooms at 15, 30 and 100 km with the grid.

### 0.3 Mapping on the e08 logs (`analysis/e09/mapping.py`)

- 24 walks: the Reference (h0111 s0–3, e08 s4–7), progress only and `k_nn` 3, eight seeds each. Signals tried: the logged interest I; interest on the long yardstick (`interest_long`: the same weights on e, n and g, each z-scored at rate 0.002 over the candidate batches, as the walker would compute it); raw novelty, progress, surprise; the walker's own z-scores of novelty and progress; log surprise.
- **Found:** the logged interest is itself a z-score against the last ~50 steps of offers (`RunningNorm`, ema_alpha 0.02), the same time scale as the drive's short average. Used as the drive, a dull stretch is erased by the yardstick within ~50 steps. Proposed and set in the config: `drive_signal: interest_long`. **A deviation from the brief's proposal ("interest"), for review.**
- Δ set to 0.35 (report, table 2). The Reference walks then reach r_max in 3.6 episodes per 1,000 steps (old teleports 3.9).

### 0.4 Fetch cost and range (`analysis/e09/fetchcost.py`, test walk `e09_test_fetch_s0`)

- Offline: a blind walker from Paris with each Reference walk's mapped radii, at r_max 500–10,000 km.
- Test walk `configs/09_compass/e09_test_fetch.yaml` (60 steps, a fixed radius schedule: 10 steps at 15 km, then 50, 200, 1,000, 2,000, 2,000 km in turn), alone on the Mac: 357 remote fetches, median 1.63 s, p95 2.1 s, none failed or dropped. Step time 0.63 s at 15 km, 1.8–2.5 s at 50–2,000 km.
- Smoke walk of the radius rule: `e09_reference.yaml`, seed 0, 300 steps (`runs/e09_smoke_s0`), 247 s alone. Runs as designed (report, finding 11).
- r_max set to 2,000 km.

### 0.5 Analysis

- `analysis/e09/readouts.py`: the e08 core (returns, choice, taste including ocean, eye on the panel's surprise, held-out error) and the loop readouts, with figures; paired differences use e08's rule (`analysis/e08/readouts.paired`, loaded by path). Tested on the check, test and smoke walks. Panel surprise is cached in `data/sheet/e09_panel_eye.parquet`.
- `analysis/e09/schedules.py`: writes `radius_schedule` files (shifted, shuffled, fixed) from finished compass Reference walks into `configs/09_compass/schedules/`. `radius_schedule` in a config may contain `{seed}`.
- The shared module is `analysis/e09/e09_common.py`, not `common.py`, which would shadow `analysis/h0111/common.py` (imported by `analysis/e08/sheet.py`).
- Regenerable intermediate files go to `data/sheet/` (git-ignored): `e09_mapping_series.parquet` (4 MB), `e09_geometry_cases.npz`.

### Prepared for Stage 1, not started

- Configs `e09_reference.yaml` (Δ 0.35), `e09_delta_0175.yaml`, `e09_delta_07.yaml`.
- `scripts/hikes_e09.sh start 1`: a copy of `hikes_e08.sh` with its disk and `.git` watchdog; queue by stage; Stage 1 is seeds 0–3 × three Δ, seed first.

Runs from Stage 0 (in `runs/`, git-ignored): `e09_check_classic_s0`, `e09_test_fetch_s0`, `e09_smoke_s0`. 65 GB free, `.git` 163 MB.

**Stopped for review after Stage 0**, as the brief asks.

## 2026-11-08: Stage 0 approved, Stage 1 started

- Review: approved as proposed: `drive_signal: interest_long`, `snap_floor_km: 7.5`, Δ 0.35 (Stage 1 also 0.175 and 0.7), r_max 2,000 km, no dead band; the fixed-radius control at the geometric mean; `progress_z` for the Stage 3 progress variant.
- Predictions 36–43 in `notes/06_characters/expectations.md`, section "Experiment 09, Stage 1", written before the first walk.
- Starts for Stage 2 (D9), coverage checked in the global index: grid density within 50 and 200 km of 0.89–1.01 at every candidate (Kazakh steppe, Turgai, Tamanrasset, Kufra, Gobi; Libreville, Belém, Douala, Freetown, Kerala, Padang). Proposed: B Tamanrasset (22.8, 5.5), C Douala (4.05, 9.7).

## 2026-11-08: Stage 1 walked (12 walks); no Δ works, stopped for review

- `scripts/hikes_e09.sh start 1`, 16:08–17:24, three side by side: 12 of 12 finished, none failed, 0 fetches dropped. 1,052–1,237 s per walk. 55 GB free after; `.git` unchanged at 163 MB.
- `analysis/e09/readouts.py` (with panel scoring, after the batch). New: `analysis/e09/stage1_diag.py` (the drive by signal and by time scale, open loop on the Stage 1 and classic logs; `stage1_drive.png`).
- **Result: no Δ chosen.** At 0.175, 0.35 and 0.7 no walk reached r_max, and none left Europe. The drive's lowest value in any walk was −0.16, and its median was positive in all 12. The cause: interest at the chosen cell keeps rising on a 15 km ring, and the dips in the Stage 0 mapping followed the classic walker's own far jumps (report, findings 13–17).
- Predictions 36–43: 1 right, 1 mostly right, 1 partly, 4 wrong, 1 untestable (report, "Against the predictions").
- **Stopped for review**, as the brief asks when none of the three works. Proposed: separate keys for the drive's averages (`drive_alpha_short`, `drive_alpha_long`, defaulting to today's), short ~20 and long ~200 steps, and Stage 1 again at Δ 0.25, 0.35, 0.5.

## 2026-11-08: Stage 1 again (round 2), approved and started

- Review: the proposal approved ("apply your proposed fixes and retry").
- **Code.** `agent/walk.py`: two keys, `drive_alpha_short` (default `ema_alpha`) and `drive_alpha_long` (default `ema_alpha_long`). `ema_alpha` still sets the scorer's z-scores, and `ema_alpha_long` still sets the yardstick of `interest_long`; `meta.json` records both drive rates. Check: `e09_reference.yaml`, seed 0, 150 steps with the new code (`runs/e09_check_r1_s0_s0`): every column of `steps.parquet` bit-identical to `e09_reference_s0`, timings aside. Smoke walk `e09_avg20_d035.yaml`, seed 0, 300 steps (`runs/e09_smoke_avg20_s0_s0`, 349 s alone): the logged d equals `Drive(0.05, 0.005)` over the logged signal.
- **Configs.** `e09_avg20_d025.yaml`, `e09_avg20_d035.yaml`, `e09_avg20_d05.yaml`: `e09_reference.yaml` with `drive_alpha_short: 0.05`, `drive_alpha_long: 0.005` and Δ 0.25, 0.35, 0.5. The round-1 configs and walks stay as they are.
- **Readouts** (`analysis/e09/readouts.py`): new `rmax_episodes_per_1000`, `rmax_episode_median`, `rmax_to_rmin` (share of r_max steps followed directly by an r_min step), `share_mid` (beyond 2 r_min, below r_max), `outside_europe`. Round-2 groups added.
- **How Δ will be chosen** (fixed before the walks). A Δ works if: (a) at least three seeds of four reach r_max; (b) r_max episodes are 2–8 per 1,000 steps (seed mean; old teleports 3.9); (c) no chattering: `rmax_to_rmin` (seed mean) below 0.5; (d) at least 40 % of steps at r_min; (e) at least two seeds leave Europe; (f) walk time under 75 min three side by side. Of the Δ that work, the one whose episode rate is nearest 3.9. If none works, stop again.
- Predictions 44–51 in `notes/06_characters/expectations.md`, written before the first round-2 walk.
- `scripts/hikes_e09.sh start 1b`: seeds 0–3 × Δ 0.35, 0.25, 0.5, seed first.

## 2026-11-08: Stage 1 round 2 walked (12 walks); Δ 0.25 chosen, stopped before Stage 2

- `scripts/hikes_e09.sh start 1b`, 20:46–22:10: 12 of 12 finished, 1,115–1,359 s per walk, 0 fetches dropped. 45 GB free after; `.git` 163 MB.
- `analysis/e09/readouts.py` re-run (with panel scoring, after the batch).
- **Δ 0.25 chosen** by the rule fixed beforehand: four of four seeds reach r_max, 2.6 r_max episodes per 1,000 steps, no chattering, 0.80 at r_min, four seeds leave Europe, 20–22 min a walk. Δ 0.35 and 0.5 fail (a): one seed each reaches r_max.
- **Start-up effect found** (report, finding 25): with the 20-step short average, d is −0.19 to −0.35 at step 50 in every seed, so three of four Δ 0.25 seeds jump to r_max at step 51. All four still reach r_max after step 60 (1.9 episodes per 1,000).
- Predictions 44–51: 1 right, 2 partly, 5 wrong.
- **Stopped for review before Stage 2.** Proposed: `drive_start: 50` (the drive's averages begin at the end of the warm-up), four check walks at Δ 0.25, then Stage 2.

## 2026-11-09: the compass Reference (`e09_ref`), check walked; Stage 2 prepared

- Review: "do the next step", with a reminder of the aim: configurations of intrinsic motivation (novelty, learning progress, boredom) that show rhythm, style, preference and clusters against a Null, set sensibly, engineering as little as possible.
- **Code.** `agent/walk.py`: `drive_start` (default 0): the first step the drive counts; before it, neither average is updated and d is 0. One key, default unchanged for every earlier config. Check walk `e09_ref.yaml`, seed 0, 80 steps (`runs/e09_check_start_s0`): d is 0 through step 72, r stays at r_min, and the logged d equals `Drive(0.05, 0.005)` fed from step 50.
- **The compass Reference** `configs/09_compass/e09_ref.yaml`: `e09_avg20_d025.yaml` plus `drive_start: 50`.
- **Check rule** (fixed before the walks), on seeds 0–3: the round-2 rule (a)–(f), plus (g) no step at r_max before step 70. If (a) or (b) fails, walk Δ 0.2 and 0.3 and stop for review.
- **Stage 2 configs** (one key changed each from `e09_ref.yaml`): `e09_null` (`choice: uniform`), `e09_local` (`radius_max_km: 15`), `e09_shifted`, `e09_shuffled`, `e09_fixed` (`radius_schedule: configs/09_compass/schedules/<kind>_s{seed}.csv`, written by `schedules.py controls --reference e09_ref` when Stage 2 starts), `e09_ref_startb` (Tamanrasset, 22.8 °N 5.5 °E), `e09_ref_startc` (Douala, 4.05 °N 9.7 °E). D8: a place is a run of steps with offers at r ≤ 2 r_min. D9: these starts. D10: the e08 rules.
- `analysis/e09/readouts.py`: "compass Reference" is now `e09_ref`; the Stage 1 rounds keep their own labels. `schedules.py` defaults to `e09_ref`.
- `scripts/hikes_e09.sh start 1c`: `e09_ref` seeds 0–7. `start 2`: writes the schedules, then 48 walks, seeds 0–3 first.
- Predictions 52–56 in `notes/06_characters/expectations.md`.

## 2026-11-09: the compass Reference walked (8 walks); check passed, core readouts fixed, Stage 2 started

- `scripts/hikes_e09.sh start 1c`, 08:56–10:00: 8 of 8 finished, 1,051–1,594 s per walk three side by side, 0 fetches dropped. 38 GB free after (the tile cache, `data/global/cache`, is at 33 GB of its 50 GB LRU cap, so Stage 2 can take at most 17 GB more); `.git` 163 MB.
- `analysis/e09/readouts.py` re-run (with panel scoring, after the batch).
- **Check rule, seeds 0–3: passed.** (a) 4 of 4 reach r_max; (b) 5.8 r_max episodes per 1,000 steps (7.4, 10.5, 4.2, 1.1); (c) `rmax_to_rmin` 0 in all four; (d) 0.62–0.90 at r_min; (e) 3 of 4 leave Europe; (f) 18–27 min a walk; (g) the first r_max at steps 208, 418, 608, 602. `e09_ref` is the compass Reference. Over eight seeds: 7 of 8 reach r_max (seed 7 never does), first r_max at steps 208–816.
- **Not foreseen: long far bouts.** Seeds 0, 1, 4 and 6 have unbroken runs of 127, 81, 57 and 62 steps at r_max, all after step 700 (the share at r_max in steps 800–1,000 is 0.43–0.51 in these four). Seeds 2, 3, 5 take 1–7 steps at r_max in all. In all 7 seeds that go far, the median novelty of the offers at r_max is below that of the offers at r_min (e.g. seed 0: 0.14 against 0.27, steps from 150), and in the four bout seeds the chosen interest at r_max is lower than at r_min (0.66–1.16 against 1.38–1.84). Far does not pay, so the short average stays below the long one, and the bout ends only when the long average has come down to it. Left as it is: it is behaviour of the loop, and Stage 2 asks whether it is the loop's (Null, shifted).
- Predictions 52–56: 3 right, 1 mostly right, 1 partly (scored in `notes/06_characters/expectations.md`).
- **New readout, fixed before Stage 2: `recovery_at_d`.** In the Reference a step is at r_max only when d is lowest, so raw recovery is partly regression to the mean. For the schedule controls (shifted, shuffled, fixed), where the radius does not depend on d: the coefficient on f_t = log(r_t/r_min)/log(r_max/r_min) in d[t+10] − d[t] ~ 1 + d[t] + f_t, steps after the warm-up. Synthetic check: a planted rise in d after far steps gives 0.12, the same radii shuffled −0.03.
- **Core readouts, fixed before Stage 2** (leads and results are read only on these; D10):
  - the loop: recovery, `recovery_at_d` (schedule controls), share at r_max, r_max episodes per 1,000, share at r_min, dwell against fall (ρ);
  - places and range: places, median dwell, radius of gyration, unique cells;
  - returns and choice: revisits beyond blind, straight-backs beyond blind, top tile beyond chance;
  - taste (settled): texture, brightness, snow/ice/cloud (`bright`), ocean;
  - eye and learning: panel surprise ~ texture (steps 500–1,000), held-out error at step 1,000.
  - Secondary, read only against the controls: period, step-length shape, contrast, saturation, continents, ocean share, outside Europe, offered novelty by radius.
  - For the shifted, shuffled and fixed controls the radius shares are the Reference's by construction; their informative readouts are recovery, `recovery_at_d`, places, dwell, range and returns.
- Predictions 57–66 in `notes/06_characters/expectations.md`, section "Experiment 09, Stage 2", written before the first Stage 2 walk.
- `scripts/hikes_e09.sh start 2`: schedules from `e09_ref`, then 48 walks, seeds 0–3 first.

## 2026-11-09 (note, during Stage 2): why far offers look less novel than near ones

Question from the review: why is novelty higher close by than far away? Offline, on the eight `e09_ref` logs and the eight classic Reference logs (offered novelty n, medians over every offered cell, steps from 150). Not a core readout; written down before the Stage 2 results.

- **The gap.** Compass Reference, 7 seeds that go far: far offers (r_max) 0.22 against near offers (r_min) 0.29. Lower in all 7.
- **Selection by the rule (the largest part).** The walker is at r_min only while d ≥ 0, so near offers are sampled while the place still pays, and far offers when it has stopped paying. The classic walker's blind far offers came at random times, independent of its state: there far and near are almost level (far 0.19–0.27, neighbours 0.17–0.31; far lower in 5 of 8 walks, higher in 3; only ~18 far offers per walk). In the compass walks, near land offers late in the walk (steps 700–1,000, when the far bouts take the dull spells) are at 0.37, against 0.30 over the whole walk.
- **What far offers land on.** 52 % of far offers are ocean against 24 % of near ones, and ocean is the least novel cover (far 0.21, near 0.26). Far offers are also plainer images: 32 % fall in the lowest fifth of surprise e, against 19 % of near ones. Neither explains the gap: within each cover (land: far 0.23, near 0.30) and within each fifth of e (far 0.20–0.23, near 0.29–0.33) far is still lower. n and e are hardly related (Spearman 0.09).
- **The scale of the eye.** The 64 px crop is ~2.6 km. At that scale terrain repeats worldwide (field, forest, water, bare ground), so a cell 2,000 km away is not more novel than one 15 km away; the classic walker's level numbers fit this. Novelty here measures texture, not geography, and distance carries no novelty bonus.
- **What remains.** Near offers in the last five r_min steps before each departure (the place already fading): 0.18–0.32. Far offers are still below them in 6 of 7 seeds. Having left, the walker usually finds a world no richer than the one it left, often sea.
- **Reading for the far bouts.** The long average of d is built from the walker's own choices, made mostly in good spells, so its yardstick sits high; far steps fall short of it, and the walker keeps going until the yardstick decays. A disappointment effect, from the rule and the eye, not set by hand.
- **For Stage 2.** Prediction 58 ("the dull far is the world's") is in part selection, not the world. The shifted radius control samples near and far offers independently of the drive: if far and near are about level there, selection was the main cause.
- **For the next round.** A larger eye (crop or context well above 2.6 km) might give distance a novelty premium, since terrain types differ more between regions than between 2.6 km patches.

## 2026-11-09 (during Stage 2): a film of `e09_ref_s1`

- `analysis/e09/film.py e09_ref_s1` (new): 1280×720, 0.3 s per step, 300 s, `h264_videotoolbox` 6 Mbps, 224 MB, in `runs/e09_films/` (git-ignored). Contact sheet (every 50th step): `notes/09_compass/results/films/e09_ref_s1_contact.png`. Left the chosen tile at 10 m; right the planet (index cells by cover), the track, the eight offers of the step, the radius and d so far.
- Why seed 1: it has the whole arc. About 400 steps near Paris and in the eastern Alps, short widenings, then restlessness from step 418, 70 steps on the South Atlantic, landfall on the Somali coast (3 °N 45 °E, ~120 steps), an 81-step far bout from step 704 (Southern Ocean, Pacific), and the last 205 steps settled in the mountains of Yunnan/Sichuan (28.6 °N 100 °E). The other long-bout seeds (0, 4, 6) end in or just after a bout.
- Rendered at low priority alongside Stage 2 (about a minute of one core); `.git` 163 MB after.

## 2026-11-09 (during Stage 2): Stage 3 starts with the larger eye; prepared, not walked

- Review: "yes, let's go with your suggestion": the larger eye as the first setting of Stage 3, after the Stage 2 report.
- **Why** (2026-11-09 note above): far offers carry less novelty than near ones. Part of it is selection by the rule, which no eye changes. Part may be the eye's scale: at ~2.7 km, terrain repeats worldwide. With a larger view, regions might differ more than neighbours do, and going far might pay.
- **Scales: `crop_px` 128 (~5.3 km) and 192 (~8.0 km), not 256.** At 256 a tile has one crop position, so all 16 patches would be one image: the progress probe (Adam steps on half A, error on half B) would test on what it trained on, and `k_nn` 10 would see one tile ten times. The confound grows before it is total: two random crops of one tile overlap on average 9 % of their area at 64, 44 % at 128, 79 % at 192. So at 192, progress is partly memory of shared pixels, and a tile's own patches crowd its neighbourhood in the archive. Read progress and novelty at 192 with that in mind. The network still sees 32×32 in every case, so walk time should barely change.
- **Configs:** `e09_crop128.yaml`, `e09_crop192.yaml` (`e09_ref.yaml` with `crop_px` changed), `e09_crop128_shifted.yaml`, `e09_crop192_shifted.yaml` (plus `radius_schedule: configs/09_compass/schedules/crop<px>_shifted_s{seed}.csv`).
- **Code:** `analysis/e09/schedules.py --prefix` (a reference's controls get their own file names; the default writes the e09_ref names as before). `analysis/e09/readouts.py`: groups "eye 5 km (crop 128)", "eye 5 km, shifted", "eye 8 km (crop 192)", "eye 8 km, shifted", and a secondary readout `offer_n_far`, `offer_n_near`, `offer_n_gap` (median offered novelty at r_max, at r_min, and far minus near, steps from 150). Check: `e09_ref_s1` gives 0.25, 0.42, −0.17, as in the note above.
- **Batch:** `scripts/hikes_e09.sh start 3a`: the eight eye walks, then the shifted schedules from them, then the eight controls. The script was edited while Stage 2 was running from it. Bash reads a running script as it goes, so the original bytes were put back in place (same inode, which the running batch holds) and the new version was moved in under a new inode. `bash -n` passes.
- **Main readouts for the eye:** `offer_n_gap` in the shifted walks (the eye's far/near gap, free of selection), against the Stage 2 shifted control; `recovery_at_d`; far bouts (runs of 20 or more steps at r_max); places and dwell; range. Held-out error compares only within one `crop_px`.
- **Order:** Stage 2 report, review, dated predictions in `notes/06_characters/expectations.md`, then `start 3a`.

## 2026-11-09: Stage 2 walked; report for review

- **Walks:** 48 of 48, 10:07–16:11, 14–31 min each, three side by side; one fetch dropped in all. `.git` 163 MB, 28 GB free after.
- **Readouts:** `analysis/e09/readouts.py`, 88 runs, panel scoring included. Fix: a fixed radius above 2 r_min never stands near, so its places table was empty without columns and `dwell_fall_rho` failed. The empty table now keeps its columns (places 0, dwell NaN).
- **Report:** `observations.md`, "Stage 2: the loop and its controls", tables 11–15, findings 29–40. Predictions 57–66 scored there and in `expectations.md`: 4 right, 4 mostly right, 2 partly.
- **Correction to the note above** (why far offers look less novel): the shifted and shuffled controls settle it. With the radius independent of d, far and near offers are level (shifted 0.21 and 0.21 without s6; shuffled −0.02). The gap is selection; the ocean and the eye's scale are at most ~0.02 of the −0.09. The case for the larger eye changes with it. It is not about removing a deficit, which is not the world's. It is whether a larger eye can give far a premium at all.
- **Three schedule walks lost their eye** (novelty about 0, held-out error frozen): `e09_shuffled_s1` steps ~25–450, `e09_shuffled_s4` ~25–125, `e09_shifted_s6` ~725–1,000. None of the other 83 `e09_` walks did. The schedules put far steps into the warm-up of 13 of the 16 shifted and shuffled walks, which the Reference never has. Proposed for review: hold steps 0–49 at r_min in the schedules, and a collapse readout.
- **Stopped for review** before Stage 3 (`start 3a`).

## 2026-11-09 (after the Stage 2 review): two additions before Stage 3a (brief amended, Stage 3)

- **Commits:** the experiment so far in three commits: the walker (`b430356`), analysis, configs and script (`2dcc10f`), notes (`fa67bce`).
- **Brief:** the review's two additions (A: the walker's world-view; B: the warm-up fix and a collapse readout) are in `brief_e09_compass.md`, Stage 3, amendment of 2026-11-09.
- **Decided in review:**
  - The world-view readout runs **offline from checkpoints**, not inside the walk. The walk only saves its network every 100 steps and at step 0. The readout loads the checkpoints into a fresh network (eval mode, no gradients) after the batch, like the panel scoring, so it never runs alongside walks and adds nothing to walk time. Its cost per checkpoint is logged below; the 10 % rule for walk time does not apply.
  - Stage 3a also walks **shuffled** controls for both eyes (24 walks in all, not 16). In Stage 2, `recovery_at_d` was clean in the shuffled control and noisy in the shifted one.
- **Walker change:** `ckpt_init` (default false) saves `ckpt_0000.pt` right after the network is built. Saving draws no random numbers. Stage 3a configs: `ckpt_every: 100`, `ckpt_init: true`.
- **Bit-identity check (A1): passed.** `e09_check_wv_off_s0` (e09_ref, 200 steps, checkpoints as before) against `e09_check_wv_on_s0` (`ckpt_every` 100, `ckpt_init`), walked side by side:
  - `steps.parquet` (200 rows, 44 columns), `candidates.parquet` (1,499 rows) and `heldout.parquet` are identical in every column except the two wall-clock ones (`sec`, `fetch_sec`). The cache counts are identical too.
  - The final weights are identical.
  - The step-0 network rebuilt from the walk's init stream (`worldview.init_model`) equals the saved `ckpt_0000.pt` weight for weight. Stage 2 walks, which have no step-0 checkpoint, are read at step 0 that way.
- **rasterio 1.5.2** installed into `.venv` with `uv pip install` only, so torch 2.15.0, numpy 2.5.4 and pandas 3.1.0 are unchanged. It is not in `pyproject.toml` yet: a `uv add` would re-resolve the lock and could move the packages a walk depends on.
- **A0, labels** (`analysis/e09/worldview.py labels`):
  - ESA WorldCover 2021 v200, 2,651 tiles. The COGs have overviews at 2, 4, 8, 16, 32 and 64×. Read at overview level 2 (8×): 1/1,500° per pixel, about 74 m north-south.
  - Footprint: a 2 × 5.34 km square (the tile's 1,068 px at 10 m) around the cell centre, about 29,000 overview pixels per cell.
  - 60,000 candidate cells from the global index, seed 20261109, in 7 min.
  - 19 % of the pixels read are nodata (0), which inside WorldCover tiles is open sea; 12 % fall outside any tile. Both count as water, as the brief says.
  - Left out: the 96,791 index cells south of 60°S. WorldCover has no Antarctica, and "outside coverage = water" would call the ice sheet sea.
  - Checks: every cell the index calls ocean comes out water-dominant; index land cells are water-dominant in 545 of 36,371 cases (coastal lakes and lagoons); the cell nearest central Paris is 84 % built-up.
- **A0, probe set** (`worldview.py probe`, seed 20261110): 5,006 cells, at most 564 per dominant class, the cap set so the total reaches 5,000. 564 each of tree, shrub, grass, crop, bare, water and moss/lichen; wetland 490, snow/ice 467, built-up 78, mangrove 23 (all there are among the 60,000). A 10 km cell is rarely mostly built-up or mangrove, so those two classes make the balanced accuracy noisier. `data/probe_cells.parquet`, with a copy in `results/probe_cells.csv`.
- **Representation:** as the scorer's novelty. `model.encode` (the 64-d latent after the encoder's linear layer) on the tile's 16 fixed scoring crops at the walk's `crop_px`, averaged over the crops (`signals.mean_latent`) and L2-normalised. Distances are cosine distances. The colour and texture baseline is standardised before taking cosines.
- **A2, deviations:**
  - The Tobler curve uses 50,000 random pairs plus every cell's 10 nearest cells on the ground (about 50,000 more pairs). Random pairs alone leave the bins under about 200 km empty, because 5,000 cells are sparse on a globe.
  - `tobler_rho` is computed on the random pairs only.
  - Plateau criterion: the lower edge of the first bin from which every populated bin (at least 30 pairs) lies within 5 % of the mean over pairs beyond 10,000 km.
- **B1, schedules:** `schedules.py` now holds steps 0 to `drive_warmup − 1` at r_min and shifts or shuffles only the steps after. Existing files are never overwritten without `--force`. `--whole-walk` writes Stage 2's way again; checked, it reproduces all 24 Stage 2 files byte for byte. The new rule keeps every radius of the walk (checked on e09_ref s0–7). **Stage 2's shifted and shuffled walks used the old schedules, which go far during the warm-up in 13 of 16 walks.**
- **B2, collapse readout** (`readouts.py`):
  - Low-novelty run: the longest run of chosen novelty under 0.005. Collapsed at 50 steps or more: the three collapsed Stage 2 walks have 106–445 steps, every other walk at most 23.
  - **Deviation: held-out error "frozen" means equal to six significant digits** (relative tolerance 1e-6) at three or more consecutive checkpoints, not four decimals. At errors near 0.005, four decimals is a 2 % resolution, and it flags 37 of 86 healthy walks. At 1e-6 only the three collapsed walks qualify (runs of 4, 9 and 17 checkpoints).
  - Probe spread: its threshold is set below, from the offline pass.
  - On the Stage 2 walks: shuffled s1 collapsed over steps 16–460, shuffled s4 over 16–121, shifted s6 over 750–966; shifted s1 (23 low steps) is not flagged.
- **B3:** the loop readouts are NaN for local only, and places, dwell and dwell against fall are NaN at a fixed radius above 2 r_min.
- **Probe tiles:** 5,006 tiles fetched once at 256 px (the walker's low-res tiles) into `data/worldview/probe_tiles.npy` (0.98 GB, git-ignored), in 14 min, none missing. Crops are cut from that file at each walk's `crop_px` exactly as the walker cuts its fixed scoring crops.
- **Cost of the readout:** on the CPU, 57 s per checkpoint, 55 of them embedding 80,000 patches. **On MPS: about 2 s per checkpoint** (latents agree with the CPU's to 5e-6). The fits and the geometry take 1.5 s. Stage 3a, 24 walks × 11 checkpoints, needs about 10 min offline after the batch.
- **Offline pass on the Stage 2 Reference and Null** (checkpoints 0, 250, 500, 750 and 1,000; step 0 rebuilt), and on the three collapsed walks plus shifted s1. Results in `results/worldview.csv` and `worldview.png`:
  - **No knowledge of land cover beyond colour at the 2.7 km eye.** Balanced accuracy at step 1,000: Reference 0.37 (0.30–0.39), Null 0.35 (0.31–0.38). Colour and texture: 0.50. Untrained encoder: 0.40. Chance: 0.09. Below colour in 16 of 16 walks, and below the untrained encoder in 15 of 16. Training first drops it to 0.29 (step 250), then it climbs back. R² of the class fractions: 0.28 and 0.26, against 0.25 for colour and 0.31 for the untrained encoder.
  - **The embedding is ordered at continental scale.** Cosine distance is about 0.40 at 25–100 km, 0.55 at 170–450 km, 0.67–0.71 at 1,900–3,000 km and 0.87–0.90 beyond 7,700 km. Tobler ρ 0.17 (Reference) and 0.14 (Null), against 0.04 for colour and 0.06 untrained. No plateau before 7,700–12,400 km; colour's plateau is at 3,000 km. Locally, colour retrieves ground neighbours better: within 500 km, +0.038 beyond chance against +0.023 (Reference) and +0.020 (Null).
  - **Reference against Null: no lead** on any world-view readout. The closest is macro-F1, +0.014 in 7 of 8 seeds, under half the Reference's range (0.048).
  - Probe cells visited by walks: 0–6 per walk. Negligible.
  - A question this raises for the loop: the embedding separates far from near (0.88 against 0.40), yet far offers are no more novel than near ones (Stage 2 finding 36). Novelty is measured against the archive of visited tiles, not against the current tile. Once the walker has been far a few times, the archive holds look-alikes for most far offers.
- **B2, probe spread: deviation.** Relative to step 0 the spread does not work: the untrained network maps every tile to almost one direction (spread 0.001–0.020), so healthy walks sit at 23–1,400 times step 0. **The flag uses the absolute spread instead (mean pairwise cosine distance), below 0.2 after step 0.** Collapsed checkpoints: shuffled s1 at step 250, 0.000; shifted s6 at step 1,000, 0.054. Every healthy checkpoint: 0.46 or more. Shuffled s4's collapse (steps 16–121) ended before its first checkpoint (250). At Stage 3a's 100-step cadence it would have been caught.
- **readouts.csv** now has `low_n_run`, `heldout_frozen`, `spread_min`, `collapsed` and `collapse_window`, and the final-step world-view readouts with their baselines. It flags exactly `e09_shuffled_s1` (16–460), `e09_shuffled_s4` (16–121) and `e09_shifted_s6` (750–1,000). `paired_clean.csv` is `paired.csv` without them. The result rule needs eight seeds, so a group missing a collapsed walk can reach at most a lead there; reports give both.
- **Predictions 67–74** for Stage 3a are in `expectations.md`, written before any Stage 3a walk.

## 2026-11-09 20:00: Stage 3a started

- Space freed by the user: 53 GB free. `scripts/hikes_e09.sh start 3a` at commit `1bf8471`: eight eye walks (`e09_crop128`, `e09_crop192`, seeds 0–3), then their schedules (warm-up held at r_min), then 16 controls (shifted and shuffled). The world-view pass and the readouts run after the batch, not alongside it.
- 23:31: the batch finished. 24 of 24 walks, none failed, 43 GB free. Each walk has 11 checkpoints (0, 100, …, 1,000), 12 MB per walk.

## 2026-11-10: Stage 3a read

- **World-view pass:** `worldview.py run` on the six 3a groups (24 walks × 11 checkpoints), 9 min on MPS, run after the batch. The rows for the Stage 2 walks in `worldview.csv` are kept unchanged.
- **Readouts:** `readouts.py` on all 112 `e09_` walks. Collapsed: only the three Stage 2 walks. In the 24 new walks, the low-novelty run is 1 step at most, held-out error is never frozen, and the lowest probe spread is 0.268 (`e09_crop128_s1`), above the 0.2 flag. Warm-up check: no shifted or shuffled 3a walk stepped beyond 30 km before step 50.
- **Comparisons made, beyond `paired.csv`** (which is against the 2.7 km Reference): each control against its own eye walk, 8 km against 5.3 km, and each 3a control against the Stage 2 control of the same seeds. Same rule as `paired()`: the spread is the compared group's range over the seeds compared. Computed ad hoc for the report, not saved as a file.
- **Two post-hoc checks, not readouts:**
  - The far − near offer gap on land offers only (`index.parquet` cover ≠ ocean), to see whether the ocean makes far offers dull. It doesn't: −0.049 and −0.055 against −0.061 and −0.054 overall.
  - The Tobler curve's half-rise distance, as a finer scale than the plateau's two bin edges. It varies from 300 to 5,000 km within one group, so it is not reported.
- `recovery_at_d` rests on middle radii in seeds that never reach r_max (5.3 km and 8 km shuffled, one seed each). In the report it is given with and without them.
- Report: `observations.md`, Stage 3a (tables 16–18, findings 41–49). Predictions 67–74 scored there: 1 right, 4 mostly right, 2 partly, 1 not tested.

## 2026-11-10: Stage 3a accepted; the progress test and walker v1

- **Review:** Stage 3a accepted, and the 2.7 km eye stays. The `k_nn` settings are not walked. Before freezing the walker, one last test: `drive_signal: progress_z` at 2.7 km, seeds 0–3, with shifted and shuffled controls (warm-up held at r_min). Then freeze walker v1 and walk it once for 15,000 steps (one seed, checkpoints every 500 steps, no death mechanism; the compass walker has none) to see how it behaves over a path long enough to train a GAN.
- **Configs:** `e09_progress.yaml` is `e09_ref.yaml` with `drive_signal: progress_z`, checkpoints every 100 steps and `ckpt_init`. `e09_progress_shifted.yaml` and `_shuffled.yaml` replay `schedules/progress_{shifted,shuffled}_s{seed}.csv`, written by `schedules.py --prefix progress_` from `e09_progress` between the two queues (`scripts/hikes_e09.sh start 3p`, 12 walks).
  - In the controls the drive steers nothing, but it is still computed from `progress_z` and logged. So `recovery_at_d` there is on the progress drive.
  - `progress_z` is the walker's own z-score of progress over the candidates (ema_alpha 0.02, about 50 steps). It goes through the same drive (averages 20 / 200 steps, Δ 0.25, from step 50).
- **New secondary readout** (`readouts.py`, before the walks): `offer_gz_far`, `offer_gz_near`, `offer_gz_gap`, the median progress z of the offers at r_max and at r_min from step 150. These are the progress drive's counterpart of `offer_n_*`. Checked on `e09_shuffled_s0`: +0.018.
- **Offline preview** (`analysis/e09/progress_offline.py`):
  - Replaying the logged `drive_x` reproduces the logged `drive_d` and radius exactly, in all 16 Reference and Null walks.
  - With `progress_z` instead, on the eight Reference walks: 8 of 8 reach r_max, 4.0 episodes per 1,000 steps (1–8), share at r_max 0.069 (0.016–0.122), first r_max at 377–877. Stage 0 (table 1) expected "rarely far" from this signal; that was with the old averages of 50 / 500 steps.
  - On Stage 2's shuffled walks, the replayed progress d gives `recovery_at_d` 0.005 (−0.047 to +0.030), and the far − near gap in offered progress z is −0.006 (−0.14 to +0.20). In a schedule walk the drive steers nothing, so this is close to what the progress test's shuffled controls will show. Only their radii differ.
- **Rule for freezing v1, set before the walks.** v1 takes the progress drive only if both of these hold:
  - (a) far pays: in the shifted controls, `offer_n_gap` or `offer_gz_gap` is above 0 in every seed that goes far (at least 3), and in the shuffled controls, `recovery_at_d` is above 0 in 4 of 4 seeds with a mean of at least 0.1 (four times the novelty drive's 0.025);
  - (b) the character against the compass Null holds: leads on top tile, revisits, straight-backs and settled contrast (seeds 0–3).

  Otherwise v1 is `e09_ref` unchanged (`interest_long`), the walker every Stage 1–3 calibration was done on. If (a) holds and (b) fails, I stop and report.
- **Walker v1** is then written as `configs/09_compass/walker_v1.yaml` (the 1,000-step form) and tagged `walker-v1` in git. The long walk `e09_v1_long_s0` is that config with `steps: 15000`, `ckpt_every: 500` and `ckpt_init`, walked alone (`start long`) for speed.
  - Re-embedding the archive every 100 steps reads every visited tile from the cache, so visited tiles stay recent in the LRU cache and are not evicted. The cost grows with the archive.
- Predictions 75–90 are in `expectations.md`, written before any of these walks.
