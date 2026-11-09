# Compass walker (experiment 09): observations, Stage 0 and Stage 1 (two rounds)

The brief is `brief_e09_compass.md`; decisions, checks and deviations are in `log.md`. Scripts are in `analysis/e09/`, tables and figures in `results/`. Stage 0 is code, checks, and offline analysis on the logs of 24 e08 walks: the Reference, progress only and `k_nn` 3, eight seeds each. Three short walks were run: the classic check (200 steps), a fetch test (60 steps) and a smoke walk of the radius rule (300 steps).

**d** is the drive: (short average − long average) ÷ long SD of the signal at the cells the walker chose; short ≈ 50 steps, long ≈ 500. **r_min** is 15 km, the Reference's radius. **An r_max episode** is an unbroken run of steps at r_max. Offline numbers are the radii the rule *would* have set on walks that moved the classic way. They are a starting point, not a prediction: in compass mode the radius changes what the walker sees, and so its drive.

**The short version.** The compass walker is built and checked: `nav: classic` reproduces the old walk bit for bit, and the geometry matches geographiclib to 10⁻⁷ m. Three things in the brief needed changing:

- **The drive's signal.** The walker's logged interest is already measured against the last ~50 steps, so it cannot stay dull for longer than that. The drive uses the same mix of signals on a 500-step yardstick (`interest_long`).
- **A snap floor.** Without it, the brief's snap tolerance drops most offers at r_min.
- **The fixed-radius control.** At its brief's definition (the median radius) it would be the same walk as "local only".

Proposed: **Δ 0.35** and **r_max 2,000 km**. A walk should take **35–75 min** three side by side, against 15–25 min in e08. Far offers miss the cache, and that cost is set by the intermediate radii, not by r_max.

## The tables

### 1. Which signal can drive the radius (e08 Reference, 8 seeds, Δ 0.35; `mapping_summary.csv`)

| Drive signal | steps at r_min | steps ≤ 2 r_min | steps at r_max | r_max episodes per 1,000 steps |
|---|---|---|---|---|
| logged interest (yardstick ~50 steps) | 0.68 | 0.77 | 0.03 | 2.5 (at most 2.8, at any Δ) |
| **interest on the long yardstick** (~500 steps) | 0.59 | 0.67 | 0.09 | **3.6** |
| novelty (raw) | 0.54 | 0.63 | 0.09 | 3.8 |
| novelty (the walker's z-score) | 0.60 | 0.69 | 0.06 | 2.5 |
| progress (raw) | **0.07** | 0.18 | 0 | 0 |
| progress (the walker's z-score) | 0.76 | 0.87 | 0.01 | 0.1 |
| surprise (raw) | **0.16** | 0.21 | 0.03 | 0.5 |
| surprise (log) | **0.24** | 0.31 | 0.26 | 8.0 |

The old walker teleported 3.9 times per 1,000 steps (eight seeds), so the target is 3.5–4.25 episodes. Steps ≤ 2 r_min depend on r_max (here 2,000 km); the other columns don't.

### 2. Choosing Δ (interest on the long yardstick)

| Δ | 0.25 | 0.30 | **0.35** | 0.40 | 0.45 | 0.50 | 0.70 |
|---|---|---|---|---|---|---|---|
| Reference: steps at r_max | 0.14 | 0.12 | **0.09** | 0.06 | 0.04 | 0.03 | 0.01 |
| Reference: r_max episodes per 1,000 steps | 4.1 | 2.8 | **3.6** | 1.8 | 1.6 | 0.8 | 0.3 |
| `k_nn` 3: episodes | 5.7 | 3.8 | 2.6 | 1.7 | 1.8 | 1.6 | 0 |
| progress only: episodes | 0.3 | 0.1 | 0.3 | 0.3 | 0.1 | 0.4 | 0 |

The episode count is not monotone in Δ: below 0.35, neighbouring episodes merge into longer ones. At Δ 0.35, per seed: 6.3, 2.1, 1.1, 2.1, 3.2, 6.3, 3.2, 4.2. Steps at r_min are 0.59 at every Δ: that share is set by the sign of d, not by Δ.

### 3. Offers by radius (2,000 random cells of the global index; `geometry_offers.csv`)

| r (km) | 15 | 20 | 30 | 50 | 100 | 300 | 1,000 | 2,000 | 5,000 | 10,000 |
|---|---|---|---|---|---|---|---|---|---|---|
| offers (of 8), snap max(0.25 r, 7.5 km) | 7.5 | 7.7 | 7.6 | 7.8 | 7.8 | 7.6 | 7.3 | 7.2 | 7.9 | 8.0 |
| offers, the brief's 0.25 r alone | **2.0** | 6.4 | 7.6 | 7.8 | 7.8 | 7.6 | 7.3 | 7.2 | 7.9 | 8.0 |
| steps with no offer, 0.25 r alone | **0.33** | 0.004 | 0.002 | 0 | 0 | 0 | 0.002 | 0 | 0 | 0 |
| ocean share of the offers | 0.37 | 0.36 | 0.36 | 0.36 | 0.37 | 0.36 | 0.39 | 0.47 | 0.67 | 0.69 |

The index is 37 % ocean (Major TOM covers coastal waters, inland seas and islands). Duplicates occur only at 15 km (3 %).

### 4. Range and fetch cost (blind walker from Paris, the radii of table 2 at Δ 0.35, eight seeds; `fetchcost*.csv`)

| r_max (km) | 500 | 1,000 | **2,000** | 5,000 | 10,000 |
|---|---|---|---|---|---|
| walks that leave Europe | 4 of 8 | 7 of 8 | **8 of 8** | 8 of 8 | 8 of 8 |
| first step outside Europe (median) | 773 | 715 | 498 | 329 | 404 |
| share of steps outside Europe | 0.09 | 0.27 | 0.46 | 0.50 | 0.51 |
| continents reached | 1.9 | 3.0 | 4.9 | 6.4 | 6.9 |
| farthest from Paris (km, median) | 3,600 | 5,400 | 10,300 | 17,800 | 18,700 |
| steps beyond the prefetch ring (25 km) | 314 | 327 | 335 | 343 | 348 |
| fresh tiles fetched per walk | 1,720 | 1,840 | 1,930 | 1,930 | 2,100 |
| minutes waiting for tiles, latencies measured today, alone | 7.3 | 7.8 | 8.0 | 8.2 | 8.5 |
| minutes waiting for tiles, e08's latencies, three walks side by side | 47 | 51 | 53 | 53 | 58 |

Continents come from rough boxes (`fetchcost.continent`), good enough to tell Europe from the rest.

### 5. Short walks

| Walk | Steps | What it shows |
|---|---|---|
| `e09_check_classic_s0` (`h0111_reference.yaml`, new code) | 200 | identical to `h0111_reference_s0` in every logged column, all 1,271 candidates and the held-out error |
| `e09_test_fetch_s0` (fixed radius schedule) | 60 | remote fetch median 1.63 s, p95 2.1 s, none dropped; step time 0.63 s at 15 km, 1.8–2.5 s at 50–2,000 km |
| `e09_smoke_s0` (the radius rule) | 300 | d exactly 0 in the warm-up, then 0 to +0.4; r between 15 and 19 km; 87 % of steps at r_min; returns 0.11 and straight-backs 0.10 beyond blind, top tile 0.36 beyond chance; 0.73 s per step |

Figures: `mapping.png` (the drive on the eight Reference walks, with the old teleports), `geometry_offers.png`.

## Findings

1. **The classic walker is untouched.** With `nav` unset, a 200-step walk is bit-identical to `h0111_reference_s0` in every column, candidate and held-out error. Everything compass sits behind the key. The two new random streams are appended, so no earlier stream moves.
2. **The geometry is right, but the snap tolerance needs a floor.** The destination point agrees with geographiclib and with a vector rotation to 4·10⁻⁸ m. That holds over the poles and across the antimeridian. The grid is 10 km, so the nearest cell to a target can be 7 km away. With 0.25 r alone, at r_min a third of steps get no offer at all. A floor of 7.5 km restores 7.5 offers at 15 km and changes nothing beyond 30 km. At 15 km the eight offers are essentially the classic neighbourhood (`geometry_offers.png`, zoom).
3. **Far offers lean to the sea.** A target in open ocean snaps to the nearest cell within 0.25 r, which at 2,000 km can be 500 km away, usually on a coast or an island. Offers are 37 % ocean up to 300 km, 47 % at 2,000 km and 67–69 % beyond 5,000 km. The `ocean` taste readout will see this, and should be read against the share on offer, which it does by construction.
4. **The logged interest can't carry a long dull stretch.** The walker scores each offer as a sum of z-scores, and their mean and SD follow the last ~50 steps of offers. The drive's short average also spans ~50 steps. So when a place stays dull, the yardstick sinks with it, and within ~50 steps the place no longer looks dull. On the e08 logs, this drive never reaches the old teleport rate at any Δ (at most 2.8 episodes per 1,000 steps). The same mix of signals measured on a 500-step yardstick (`interest_long`) reaches 3.6 at Δ 0.35. The choice of direction is unchanged: the walker still chooses by its usual interest, and only the drive reads the slow version. This is Charnov's comparison: recent gain against the long-run rate, both on one scale.
5. **The drive is slow.** d is exactly 0 for the first 50 steps (both averages are plain means then) and stays near 0 until about step 150. After that it moves in waves of 100–300 steps, and rarely beyond ±0.6 (`mapping.png`). So Δ is small (0.35). The young phase will be almost entirely at r_min, whatever the warm-up: D3's warm-up hardly matters.
6. **Raw progress and surprise cannot drive the radius.** Both are skewed: mostly small, with rare spikes. Surprise also falls as the network learns. So their short average sits below their long one most of the time, and the walker would be far almost always (7–24 % of steps at r_min). The walker's own z-score of progress has the opposite problem: it reaches r_max about once in 10,000 steps. Raw novelty behaves like interest on the long yardstick (3.8 episodes).
7. **The drive and the old boredom fire at different times.** Only 7 % of the old teleports fall within 10 steps of an r_max episode. Boredom fired on runs of about ten dull steps, mostly before step 150, where the drive is still flat. The drive dips over tens of steps, later in the walk. So the compass walker will not copy the old rhythm. On these logs, its far episodes last about 20 steps at r_max. In compass mode, going far should end them sooner; recovery (Stage 2) is the readout for that.
8. **"Most steps at r_min" is set by the sign of d, not by Δ.** At any Δ the Reference spends 59 % of its steps at r_min, and 67 % within 2 r_min. A dead band (`radius_hysteresis`, implemented with Δ still marking r_max) would raise this. At 0.1 it gives 74 % at r_min, cuts the steps that fetch new tiles by a third, and leaves the r_max episodes as they are. Not proposed for Stage 1: it is one more parameter, and the brief keeps it at 0.
9. **Fetch cost is set by the in-between radii, not by r_max.** One step in three falls beyond the prefetch ring whatever r_max is (314–348 steps), about 1,900 fresh tiles per walk. A far step costs the slowest of its eight parallel fetches. Measured alone today, that is 1.6–2.5 s. At e08's latencies with three walks side by side (median 3 s, p90 10 s), it is much more. Prefetching the next eight offers during training is built in, but it only covers about 0.5 s.
10. **r_max 2,000 km is the smallest that leaves Europe every time.** At 1,000 km, 7 walks of 8 leave and spend a quarter of their steps outside; at 2,000 km all 8 leave (median first exit at step 500) and spend about half outside, on about five continents. At 5,000 km and more the far steps cross oceans to every continent: offers are then mostly coast and sea (finding 3), and one far step makes "where" meaningless at the scale of a place.
11. **The radius rule runs.** In the 300-step smoke walk from Paris, d stays at 0 for 50 steps and then rises to +0.4, so the walker stays near Paris (r 15–19 km). This matches what the e08 logs give for seed 0. Its returns and choice match the classic walker's young phase (returns 0.11, straight-backs 0.10 beyond blind, top tile 0.36 beyond chance).
12. **The fixed-radius control, as defined, would be local only.** The median radius is r_min in 6 of 8 mapped Reference walks. A fixed radius at the geometric mean (19–90 km per seed) keeps the control distinct, and is what `schedules.py` writes. To decide before Stage 2.

## Decisions D1–D7

| | Decision | Taken | What the data said |
|---|---|---|---|
| D1 | normalising the drive | `z_diff`, **on interest measured over the long yardstick** | Interest is a z-score and goes negative (min −2.0), so a ratio is out. The logged interest is already normalised over ~50 steps (finding 4). Raw skewed signals don't centre (finding 6) |
| D2 | the drive's signal | `interest_long` (the walker's mix, each signal z-scored over ~500 steps); variants for Stage 3: raw `novelty` and `progress_z` | Raw progress puts the walker far almost always; its z-score almost never (finding 6). `progress_z` is the variant that can ask the question, and it will probably answer "rarely far" |
| D3 | the young network | warm-up 50 steps at r_min, long average cumulative to step 500, as proposed | d is 0 for 50 steps by construction and near 0 until ~150 (finding 5) |
| D4 | the offer frame | `random`: θ drawn from [0°, 45°) each step | `fixed` and `heading` (with `persistence`) are implemented, for later |
| D5 | staying | no stay offer (`offer_stay: false`) | The classic walker never offers its own cell (`World.neighbours` drops it). Dwelling is small steps, as before |
| D6 | r_max and fetch cost | **2,000 km**; the next eight offers are prefetched during training; fetch timeout 30 s as before | Smallest r_max that leaves Europe in every walk; cost does not depend on r_max (findings 9, 10) |
| D7 | deterministic or jittered | deterministic (`jitter` implemented, lognormal, clipped to [r_min, r_max]) | — |
| new | snap floor | `snap_floor_km: 7.5` | Without it, a third of the steps at r_min have no offer (finding 2) |
| new | Δ | **0.35**; Stage 1 also walks 0.175 and 0.7 | 3.6 r_max episodes per 1,000 steps on the Reference logs (table 2) |

## Walk time

- **Alone:** about 11 min of computing (0.65–0.75 s a step) plus about 8 min of waiting for tiles: about 20 min a walk.
- **Three side by side**, as e08 ran: computing goes up to 18–28 min (e08's Reference walks took 1,070–1,700 s). Waiting depends on the day's latency: 8 min at today's, about 50 min at e08's worst. **About 35–75 min a walk.**
- **Stage 1** (12 walks, 4 rounds of three): 2.5–5 h.
- **Stage 2** (52 walks): 10–23 h. The fixed-radius control fetches at nearly every step: from about 30 min alone to 2–3 h at e08's latencies per walk.
- **Stage 3** (48 walks): 10–20 h.
- **Disk:** about 0.75 GB of new tiles per walk pass through the 30 GB tile cache, which then evicts. In e08, Time Machine's local snapshots kept evicted tiles and ate the free space for a day. The batch's watchdog stops at 10 GB free; 65 GB free now.

## For Stage 1

To decide in this review:

1. **`drive_signal: interest_long` instead of the brief's `interest`** (finding 4). The config key accepts `interest` if the brief's version is wanted. With it, the walker would rarely go far.
2. **`snap_floor_km: 7.5`** (finding 2).
3. **Δ 0.35 and r_max 2,000 km**; Stage 1 walks Δ 0.175, 0.35 and 0.7.
4. **No dead band** for now (finding 8). If Stage 1 shows chattering around r_min, or walks are too slow, 0.1 is the lever.
5. For Stage 2, decided later but flagged now: the fixed-radius control at the geometric mean, not the median (finding 12). The shifted and shuffled controls replay the compass Reference walk of the same seed, so they wait for those walks in the queue.
6. For Stage 3: the progress variant as `progress_z` (finding 6).

Then:

1. Write the dated Stage 1 predictions in `notes/06_characters/expectations.md`, section "Experiment 09", before the first walk.
2. `scripts/hikes_e09.sh start 1`: seeds 0–3 at the three Δ, seed first. On AC power; for a closed lid run `sudo pmset -a disablesleep 1` first and `0` afterwards.
3. `.venv/bin/python analysis/e09/readouts.py`, then choose Δ against the brief's checks: chattering at the boundary, walkers that never go far or are always far, whether they leave Europe, dropped candidates and walk time.

# Stage 1: calibration (2026-11-08)

Twelve walks: the compass Reference from Paris, 1,000 steps, seeds 0–3, at Δ 0.35, 0.175 and 0.7 (`e09_reference`, `e09_delta_0175`, `e09_delta_07`). Readouts: `analysis/e09/readouts.py` (`results/readouts.csv`). Diagnosis: `analysis/e09/stage1_diag.py` (`results/stage1_diag.csv`, `stage1_trend.csv`, `stage1_sweep.csv`, `stage1_drive.png`). Classic Reference: seeds 0–7 (h0111 s0–3, e08 s4–7). Shares of steps are after the warm-up (step 50).

**The short version.** None of the three Δ works. **No walk ever reached r_max, and none left Europe.** The drive rarely goes negative, and never far: its lowest value in any walk is −0.16. The walker's interest keeps rising, because at r_min it can always step away from ground it has used up, so its patch never wears out. A rising signal keeps the short average above the 500-step long one. The Stage 0 mapping had predicted far episodes because, in the classic logs, the drive's dips followed the old walker's own far jumps. The compass walker never jumps, so it never dips. That is the brief's "stop" case. The fix the data point to: shorter averages for the drive (about 20 and 200 steps). Then the dips come from local dull stretches, not from the slow drift of learning. On the compass logs, offline, that gives about the old teleport rate. To decide in this review.

## The tables

### 6. The three Δ (four seeds each; mean, with the range over seeds)

| | Δ 0.175 | **Δ 0.35** | Δ 0.7 | classic Reference (8 seeds) |
|---|---|---|---|---|
| steps at r_min | 0.87 (0.78–0.90) | 0.88 (0.80–0.92) | 0.86 (0.83–0.89) | — |
| steps at r_max | **0** | **0** | **0** | — |
| steps beyond 30 km | 0.017–0.113 | 0.016–0.059 | 0–0.006 | — |
| largest radius (km) | 85–991 | 72–136 | 29–31 | — |
| d: median / lowest | 0.07–0.17 / −0.15 | 0.10–0.29 / −0.16 | 0.13–0.41 / −0.11 | — |
| steps with d < 0 | 0.10–0.22 | 0.08–0.20 | 0.11–0.17 | — |
| radius of gyration (km) | 160–649 | 165–283 | 189–234 | 3,155–7,811 |
| walks leaving Europe | 0 of 4 | 0 of 4 | 0 of 4 | 8 of 8 (3–6 continents) |
| unique cells | 461 | 498 | 476 | 419 |
| revisits beyond blind | 0.19 (0.18–0.22) | 0.16 (0.13–0.18) | 0.18 (0.12–0.28) | 0.18 (0.15–0.26) |
| straight-backs beyond blind | 0.11 | 0.09 (0.08–0.10) | 0.11 | 0.12 |
| top tile beyond chance | 0.45 | 0.43 (0.41–0.44) | 0.45 | 0.42 |
| offers per step | 7.5 | 7.5 | 7.5 | 6.4 |
| panel surprise ~ texture | 0.54 | 0.52 (0.44–0.61) | 0.51 | 0.62 (0.35–0.76) |
| held-out error at 1,000 | 0.003–0.004 | 0.003–0.005 | 0.003–0.012 | 0.003–0.013 |
| targets dropped as too far (per walk) | 55–88 | 57–98 | 51–113 | — |
| fetches dropped | 0 | 0 | 0 | — |
| minutes per walk, three side by side | 18–20 | 18–21 | 18–20 | 15–31 (e08) |

### 7. Why: the drive's signal on both sets of logs (Δ 0.35, averages of 50 and 500 steps; `stage1_diag.csv`, `stage1_trend.csv`)

Offline, as in Stage 0 table 1, now also on the 12 compass walks. Both are open loop: the radii the rule *would* set on walks that moved another way. Rise is the signal's median at the chosen cell over steps 900–999 minus over steps 50–149, in SDs of the walk.

| Drive signal | rise, compass | rise, classic | at r_max, compass logs | episodes per 1,000, compass logs | at r_max, classic logs | episodes, classic logs |
|---|---|---|---|---|---|---|
| interest, long yardstick (the Reference's) | **+1.00** | +0.48 | **0** | **0** | 0.09 | 3.6 |
| interest (logged) | +0.81 | +0.74 | 0 | 0 | 0.03 | 2.5 |
| novelty (raw) | **+1.10** | +0.39 | 0 | 0 | 0.09 | 3.8 |
| novelty (the walker's z-score) | +0.37 | +0.35 | 0.002 | 0.4 | 0.06 | 2.5 |
| progress (the walker's z-score) | +1.32 | +1.15 | 0 | 0 | 0.01 | 0.1 |
| surprise (log) | **−0.64** | −0.06 | 0.32 (r_min 0.12) | 11.5 | 0.26 (r_min 0.24) | 8.0 |

### 8. The drive's two averages (interest on the long yardstick; `stage1_sweep.csv`)

Open loop again. The yardstick of `interest_long` stays at ~500 steps; only the drive's averages change. The target is the old teleport rate, 3.9 per 1,000 steps.

| short / long average (steps) | Δ | compass logs: at r_min | at r_max | episodes per 1,000 (median length) | classic logs: at r_max | episodes |
|---|---|---|---|---|---|---|
| 50 / 500 (Stage 1) | 0.35 | 0.87 | 0 | 0 | 0.09 | 3.6 (20) |
| 50 / 200 | 0.35 | 0.74 | 0 | 0 | 0.05 | 2.0 |
| 50 / 100 | 0.175 | 0.63 | 0.013 | 0.9 (16) | 0.12 | 4.2 |
| **20 / 200** | 0.25 | 0.65 | 0.075 | 9.5 (7) | 0.28 | 10.1 |
| **20 / 200** | **0.35** | **0.65** | **0.026** | **4.5 (4)** | 0.19 | 10.3 (11) |
| **20 / 200** | 0.5 | 0.65 | 0.005 | 1.1 (5) | 0.08 | 4.3 |
| 20 / 100 | 0.35 | 0.56 | 0.050 | 6.6 (4) | 0.17 | 10.0 |
| 20 / 100 | 0.5 | 0.56 | 0.012 | 1.6 (9) | 0.07 | 4.0 |

Figure `results/stage1_drive.png`: the drive, novelty and log surprise at the chosen cell over the walk, compass against classic.

## Findings

13. **The compass walker never goes far, at any of the three Δ.** Not one of 12 walks reached r_max. The largest radius was 991 km, in one walk at Δ 0.175; otherwise at most 205 km. All 12 stayed in Europe, within 160–650 km of their centre, where the classic walkers ranged over 3,000–8,000 km and 3–6 continents. Δ is not the lever: r_max needs d ≤ −Δ, and d is above −0.07 on 95 % of steps. Even a quarter of Δ 0.35 would rarely be reached.
14. **The walker's interest keeps rising.** At r_min the eight offers lie on a 15 km ring, and the walker takes the most interesting, mostly the most novel. It can always step off ground it has already used, so the place it is in never wears out. Raw novelty at the chosen cell rises over the walk in every compass walk: by 1.1 SD from steps 50–149 to 900–999, against 0.4 for the classic walker. A long average over ~500 steps lags any rise, so the short average sits above it: d > 0 on 78–92 % of steps.
15. **The Stage 0 mapping counted on the old walker's jumps.** In the classic logs, d fell below −0.35 when novelty fell back after a spike. Novelty spikes when the walker lands in new terrain: on average +0.10 to +0.17 after a teleport, by seed. All 673 such steps lie within 300 steps after a classic far step (> 100 km). That alone proves little, since 66–100 % of all steps do. But it fits the compass walks, which never jump, never spike and never dip (`stage1_drive.png`). So the mapping was partly circular: the old far jumps made the dips that were meant to cause far jumps. Stage 0 finding 7 had flagged that the drive and the old boredom fire at different times; this is the stronger version.
16. **Every signal drifts, and at 500 steps the drift sets d.** Interest and novelty drift up, so the walker would stay near. Surprise drifts down as the network learns, so the walker would be at middle radii most of the time: only 12 % of steps at r_min on the compass logs. Progress on the walker's own scale drifts up as well. Over 1,000 steps there is no stationary long-run rate for Charnov's rule to compare against (table 7).
17. **Shorter averages take the drift out.** With a short average of ~20 steps and a long one of ~200 (table 8), d compares the last few places with the last few hundred steps rather than with the whole walk. At Δ 0.35 the compass logs then give 65 % of steps at r_min, 2.6 % at r_max and 4.5 r_max episodes per 1,000 steps of median 4 steps: about the old teleport rate (3.9). The same setting on the classic logs gives 10 episodes. Open loop on both: in a compass walk, the first far step should bring the spike-and-fall of finding 15, so the closed loop is expected somewhere between. Shortening only the long average (50 / 100) does not do it.
18. **At r_min the compass walker is a fair stand-in for the classic one.** Returns, choice, learning and the eye are within the classic seeds' range: revisits 0.16, straight-backs 0.09, top tile 0.43, held-out error 0.003–0.005, eye 0.52. It sees 7.5 offers a step against 6.4, and stands on 10–20 % more distinct cells. This repeats Stage 0 finding 2 in closed loop, and holds at all three Δ.
19. **Walks are cheap while they stay near.** 18–21 min each, three side by side, against the predicted 35–75: almost every step is local, and fetching took 0.3–3.5 min per walk. No fetch failed, and no candidate was dropped on the timeout. The snap tolerance dropped 51–113 of 8,000 targets per walk. The radius never touched r_max, so there was no chattering there. Near r_min it wobbles to 20–40 km on small negative d, more at small Δ: steps beyond 30 km were 2–6 % at Δ 0.35 and up to 11 % at 0.175.
20. **One walk followed the sea.** At Δ 0.7, seed 2 left the Dutch coast and walked north up the North Sea in 15 km steps, to 56.7 °N. 81 % of the cells it stood on were ocean, and its held-out error at step 1,000 is 0.012, three to four times the others'. Nothing in the rule stops a walker at r_min from following open water, as the classic neighbourhood didn't either (ocean share up to 0.41 in classic walks).
21. **The period readout means nothing here.** It finds first autocorrelation peaks of log r at 29–194 steps in all twelve walks, but the radius barely leaves r_min, so these are peaks in noise. Recovery is undefined: there are no steps at r_max.

## Against the predictions (36–43, written 2026-11-08)

| # | Setting | Predicted | Found | Verdict |
|---|---|---|---|---|
| 36 | Δ 0.35, the loop | 2–8 % at r_max, episodes of 1–5 steps, 1–5 per 1,000, 55–75 % at r_min; within 2 r_min to step 150; ≥ 3 seeds reach r_max | 0 at r_max, 0 episodes, 80–92 % at r_min; one seed reached 40 km before step 150; no seed reached r_max | wrong |
| 37 | Δ 0.35, recovery | recovery > 0 in every seed that reaches r_max | no seed reached r_max | untestable |
| 38 | Δ 0.35, range | 3–4 seeds leave Europe, 20–50 % of steps outside; ocean share 0.15–0.40, above classic in ≥ 3 seeds | none left Europe; ocean share 0–0.23, above classic in 2 of 4 | wrong |
| 39 | Δ 0.175 | 8–25 % at r_max, 4–15 episodes, chattering; r_min 40–65 %; every seed leaves Europe | 0 at r_max; r_min 78–90 %; none left Europe (one walk reached the Gulf of Bothnia, with a 991 km radius once) | wrong |
| 40 | Δ 0.7 | r_max in ≤ 1 seed; step p90 < 300 km in ≥ 3; ≥ 2 never leave Europe | r_max in none; p90 20 km in all; none left | right |
| 41 | returns and choice, Δ 0.35 | revisits 0.08–0.18, straight-backs 0.05–0.12, top tile 0.33–0.45 | 0.13–0.18 (one seed 0.182), 0.08–0.10, 0.41–0.44 | mostly right |
| 42 | period | no regular rhythm; a first peak at 100–400 steps in ≤ 2 seeds of four | peaks in 4 of 4, at 50–194 steps, but in noise around r_min (finding 21) | wrong as stated, moot |
| 43 | cost | 35–75 min a walk; < 20 dropped candidates; no failure; young phase at classic speed | 18–21 min; 0 dropped; no failure; young phase at classic speed | partly (time wrong, for the reason 36 is wrong) |

Tally: 1 right, 1 mostly right, 1 partly right, 4 wrong, 1 untestable.

What I got wrong, in kind: I took the open-loop mapping on walks that jumped as a property of the drive. The far episodes were largely a property of the old walker's jumps. Stage 0 called the mapping "a starting point, not a prediction", and then my predictions treated it as one.

## For review (the brief: "Stop only if none of the three works")

None works, so I stopped here. Options, recommended first:

1. **Shorter averages for the drive (recommended).** Short ~20 steps, long ~200 steps, `interest_long` kept on its ~500-step yardstick (finding 17). This needs two new keys, because today the drive's short rate is the scorer's `ema_alpha` and its long rate also sets the yardstick: `drive_alpha_short` (default `ema_alpha`) and `drive_alpha_long` (default `ema_alpha_long`). The defaults leave every config so far unchanged. Then Stage 1 again, 12 walks (about 1.5 h at today's speed), at Δ 0.25, 0.35 and 0.5, with new predictions first. Cost: it is no longer Charnov's long-run rate over the whole walk, but over the last ~200 steps.
2. **Log surprise as the signal.** Surprise is the one signal that wears out where the walker stands, since the network learns the place. But it falls with learning over the whole walk: 12–19 % of steps at r_min, the rest mostly at middle radii, and every middle step fetches (table 7; `stage1_sweep.csv`). It would need the shorter averages as well. Not recommended as the Reference; it stays a Stage 3 variant.
3. **Keep the drive as the brief has it, and report.** Question 1's answer would then be "no: from a standing start, a drive measured on its own history never sends this walker far". Stage 2's controls and recovery need far steps, so Stage 2 could not ask its questions.

Not proposed: a smaller Δ with the present averages. d's 5th percentile is −0.03, so a Δ that reaches r_max would turn on noise. Nor a forced first far jump to seed the spike of finding 15: that puts back a teleport by another name.

Starts for Stage 2, D9, proposed (dense coverage checked: 0.89–0.99 of the full grid within 50 km): **B, Sahara interior at Tamanrasset** (22.8 °N, 5.5 °E: Hoggar mountains and sand, no sea within 1,000 km); **C, cloudy tropical coast at Douala** (4.05 °N, 9.7 °E: mangrove delta, rainforest, Mount Cameroon). D8 as proposed: a place is a run of steps with offers at r ≤ 2 r_min.

# Stage 1, round 2: the drive at 20 / 200 steps (2026-11-08)

Twelve walks: the compass Reference with the drive's averages at ~20 and ~200 steps (`drive_alpha_short` 0.05, `drive_alpha_long` 0.005; scorer and yardstick unchanged), Paris, 1,000 steps, seeds 0–3, at Δ 0.25, 0.35 and 0.5 (`e09_avg20_d025`, `_d035`, `_d05`). The rule for choosing Δ was fixed in `log.md` before the walks. "Round 1" is the Stage 1 above (Δ 0.35, averages 50 / 500).

**The short version.** The fix works in part. Walkers now go far: 6 of 12 reach r_max, and 7 of 12 leave Europe. By the rule fixed beforehand, **Δ 0.25 is chosen**: it is the only Δ at which at least three seeds reach r_max (all four do), at 2.6 r_max episodes per 1,000 steps, with no chattering. But the walks show a start-up effect I had not foreseen. The first 50 steps are identical at every Δ, and at step 50 the drive stands at −0.19 to −0.35 in all four seeds. Interest is high while everything is new (steps 0–19) and falls over steps 20–50. The 20-step short average sees the fall; the long average still holds the high start. So three of the four Δ 0.25 seeds jump to r_max at step 51, the first step the rule runs, and one of them lands in the open Atlantic. Excluding that jump, all four seeds still reach r_max later (from step 503–740), at 1.9 episodes per 1,000 steps. Proposed: start the drive's averages at the end of the warm-up, and check with four walks at Δ 0.25 before Stage 2.

## The tables

### 9. The three Δ at 20 / 200 (four seeds; mean, with the range over seeds; whole walk after the warm-up)

| | Δ 0.25 | Δ 0.35 | Δ 0.5 | round 1 (Δ 0.35, 50 / 500) | classic Reference (8 seeds) |
|---|---|---|---|---|---|
| seeds reaching r_max | **4 of 4** | 1 of 4 | 1 of 4 | 0 of 4 | — |
| of them, first at step 51 | 3 | 1 | 0 | — | — |
| steps at r_min | 0.80 (0.66–0.88) | 0.82 (0.73–0.87) | 0.74 (0.65–0.81) | 0.88 | — |
| steps at middle radii (2 r_min to r_max) | 0.12 (0.07–0.24) | 0.12 (0.08–0.18) | 0.16 (0.10–0.19) | 0.03 | — |
| steps at r_max | 0.015 (0.003–0.043) | 0.000 | 0.014 (0–0.058) | 0 | — |
| r_max episodes per 1,000 steps | **2.6** (2.1–3.2) | 0.3 (0–1.1) | 1.8 (0–7.4) | 0 | teleports 3.9 |
| the same, after step 60 | 1.9 (1.1–2.1) | 0 | 1.9 (0–7.4) | 0 | — |
| median episode length (steps) | 1–3 | 1 | 4 | — | — |
| r_max step followed directly by r_min (chattering) | 0 | 0 | 0 | — | — |
| recovery (d after r_max − after r_min, 10 steps) | +0.10 to +0.32 | +0.22 | +0.08 | — | — |
| steps outside Europe | 0.54 (0.04–0.95) | 0.15 (0–0.57) | 0.12 (0–0.32) | 0 | — |
| seeds leaving Europe | 4 of 4 | 2 of 4 | 2 of 4 | 0 of 4 | 8 of 8 |
| radius of gyration (km) | 1,743–3,169 | 393–1,284 | 321–4,247 | 165–283 | 3,155–7,811 |
| continents | 3–6 | 1–3 | 1–6 | 1 | 3–6 |
| revisits beyond blind | 0.23 (0.13–0.29) | 0.20 (0.19–0.22) | 0.18 (0.15–0.23) | 0.16 | 0.18 |
| straight-backs beyond blind | 0.13 (0.07–0.17) | 0.11 (0.10–0.15) | 0.10 (0.09–0.12) | 0.09 | 0.12 |
| top tile beyond chance | 0.50 (0.45–0.54) | 0.47 | 0.45 | 0.43 | 0.42 |
| panel surprise ~ texture | 0.68 (0.56–0.74) | 0.55 | 0.56 | 0.52 | 0.62 (0.35–0.76) |
| held-out error at 1,000 | 0.003–0.004 | 0.003–0.006 | 0.002–0.005 | 0.003–0.005 | 0.003–0.013 |
| ocean share of cells stood on | 0.22 (0.06–0.51) | 0.22 (0–0.54) | 0.52 (0.16–0.93) | 0.09 | 0.22 |
| offers per step | 7.3 (6.6–7.7) | 7.7 | 7.5 | 7.5 | 6.4 |
| targets dropped as too far (per walk) | 98–1,710 | 47–92 | 55–238 | 57–98 | — |
| minutes per walk, three side by side | 20–22 | 19–21 | 19–23 | 18–21 | — |

### 10. The step-51 jump (`steps.parquet`; identical at every Δ up to step 50)

| seed | interest, steps 0–19 | steps 20–49 | d at step 50 | Δ 0.25: first r_max | r_max episodes after step 60 | offline, drive started at step 50: d at steps 50–70 |
|---|---|---|---|---|---|---|
| 0 | 1.84 | −0.73 | −0.35 | 51 | 1 (from 503) | 0 |
| 1 | 1.80 | −0.56 | −0.33 | 51 | 2 (from 562) | 0 |
| 2 | 1.58 | −0.34 | −0.29 | 51 | 2 (from 740) | 0 |
| 3 | 1.04 | −0.17 | −0.19 | 633 | 2 (from 633) | 0 |

Offline (open loop on the Δ 0.25 logs), the drive started at step 50 still falls below −0.25 later in every seed: on 6–41 steps after step 150, against 2–40 as walked.

## Findings

22. **Shorter averages let the walker go far.** At Δ 0.25 every seed reaches r_max and leaves Europe. Radii of gyration are 1,700–3,200 km, against 165–283 km in round 1. Far steps come in short episodes (1–3 steps), with no jump straight from r_max to r_min: the radius steps down through middle radii, which take 12 % of steps.
23. **Δ 0.25 is chosen, by the rule fixed before the walks.** Only at 0.25 do at least three seeds reach r_max. Its 2.6 episodes per 1,000 steps are inside the 2–8 band. Every other criterion holds (no chattering, 80 % at r_min, four seeds leave Europe, about 20 min a walk). At 0.35 and 0.5 one seed each reaches r_max. Δ 0.5 seed 0 does so seven times after step 836, so four seeds cannot order 0.35 and 0.5: one walk that gets far once tends to go far again.
24. **Going far restores the drive.** In all six walks that reached r_max, d rose more over the next 10 steps after a step at r_max than after one at r_min (recovery +0.08 to +0.32). This is the loop the brief asks about, seen for the first time; Stage 2's shifted and shuffled controls are what will tell whether it is the drive's doing.
25. **The drive has a start-up effect at step 50 (table 10).** While the network is new, everything is interesting: mean interest 1.0–1.8 over steps 0–19, then below 0 over steps 20–49. Round 1 hid this, because both of its averages were plain means up to step 50 (d exactly 0). At 20 / 200, the short average forgets the start by step 50 and the long one does not. d is −0.19 to −0.35 at step 50 in every seed, so at Δ 0.25 three seeds of four jump to r_max at step 51. That is a property of the young network, not of a place wearing out. Started at the end of the warm-up (offline), the drive is 0 over steps 50–70 and still dips later in every seed.
26. **The step-51 jump can strand a walker in open ocean.** Seed 1 at Δ 0.25 landed between the Azores and Madeira (33 °N, 25 °W). The index has only scattered cells there, so it saw 2–3 offers per step and lost 1,710 targets as too far, almost all in steps 50–450. Seed 1 at Δ 0.5 never went far but spent 93 % of its steps on ocean cells, walking out from the coast at r_min. The ocean taste readout and the offer count need reading per walk.
27. **Returns and choice rise with going far.** At Δ 0.25: revisits 0.23, straight-backs 0.13, top tile 0.50, against 0.16, 0.09 and 0.43 in round 1 and 0.18, 0.12 and 0.42 for the classic walker. The eye rises too (0.68 against 0.52). I expected the opposite for returns, since far steps break up places. With four seeds per Δ and the step-51 jump in three of them, this is not yet a result.
28. **Cost stays low.** 19–23 min per walk three side by side. Middle radii fetch, but fetching came to only 2.5–7 min per walk. No fetch was dropped, and no walk failed.

## Against the predictions (44–51, written 2026-11-08)

| # | Setting | Predicted | Found | Verdict |
|---|---|---|---|---|
| 44 | Δ 0.35, the loop | 2–10 % at r_max, 3–10 episodes per 1,000 of 1–4 steps; 50–70 % at r_min; middle 20–35 %; all four seeds reach r_max | 0.03 %, 0.3 episodes; r_min 73–87 %; middle 8–18 %; one seed (at step 51) | wrong |
| 45 | Δ 0.25 and 0.5 | 0.25: 6–20 % at r_max, 6–15 episodes; 0.5: 0.5–4 %, 1–5 episodes, ≥ 3 seeds; r_min within 0.1 across Δ | 0.25: 1.5 %, 2.6; 0.5: 1.4 %, 1.8, one seed; r_min 0.74–0.82 | wrong (r_min part right) |
| 46 | recovery, Δ 0.35 | > 0 in ≥ 3 seeds | one seed reached r_max: +0.22; > 0 in all six walks with r_max steps | partly (right in sign, too few walks at 0.35) |
| 47 | range, Δ 0.35 | 3–4 seeds leave Europe, 15–50 % outside; gyration 1,000–5,000 km; 2–5 continents | 2 seeds (57 % and 2.5 % outside); 393–1,284 km; 1–3 | wrong |
| 48 | returns and choice, Δ 0.35 | revisits 0.06–0.15, straight-backs 0.04–0.09, top tile 0.36–0.46 | 0.19–0.22, 0.10–0.15, 0.46–0.47 | wrong (direction too) |
| 49 | early far steps | first r_max before step 150 in ≥ 4 of 12 walks | 4 of 12, all at step 51 | right (for a reason found only afterwards, finding 25) |
| 50 | cost | 25–50 min; no failure; < 20 dropped fetches | 19–23 min; none; 0 | partly (time wrong) |
| 51 | the choice | 0.35 or 0.5, 0.35 more likely | 0.25 | wrong |

Tally: 1 right, 2 partly right, 5 wrong.

What I got wrong, in kind: again the open-loop numbers. On the round-1 logs the 20 / 200 drive gave 4.5 episodes at Δ 0.35. In closed loop it gave 0.3, and only Δ 0.25 reaches the open-loop rate. I placed the closed loop between the compass and the classic logs; it fell below both. And I read the smoke walk's step-51 jump as the drive working, not as the start-up effect it is.

## For review

Δ 0.25 is chosen by the rule. I stopped before Stage 2 anyway: the compass Reference would carry the step-51 jump into all of Stage 2's 52 walks, in which start, young phase and controls all depend on when the walker first goes far. Recommended:

1. **Start the drive at the end of the warm-up**: a key `drive_start` (default 0, as now), set to 50 in the compass Reference. Both averages begin at step 50, so d is 0 until about step 70 and then compares the last 20 steps with the time since step 50. Offline it removes the step-51 jump and keeps the later dips (table 10).
2. **Check with four walks**: Δ 0.25, seeds 0–3 (about 25 min). Apply the same rule. If at least three seeds still reach r_max after step 60 at 2–8 episodes per 1,000, that becomes the compass Reference. If not, walk Δ 0.2 and 0.3 as well (eight more walks).
3. **Then Stage 2** as planned, with starts B (Tamanrasset) and C (Douala). Dated predictions and the fixed core readouts come first.

---

# Stage 2: the loop and its controls (2026-11-09)

48 walks from Paris, 1,000 steps: the compass Null (`choice: uniform`), shifted radius, shuffled radius, fixed radius (each control replays the `e09_ref` walk of the same seed) and local only (r_max 15 km), on seeds 0–7. Also the compass Reference from start B (Tamanrasset) and start C (Douala), seeds 0–3. Compared with the eight `e09_ref` walks (log, 2026-11-09). The predictions (57–66) and the core readouts were fixed before the walks. A lead is four seeds of one sign with |mean| above half the Reference's range; a result is eight seeds, at least 7 of one sign (e08 D10). Files: `results/readouts.csv`, `paired.csv`, `places.csv`, `radius.png`, `steplength.png`, `recovery.png`.

**The short version.**
- **Question 1, the loop.** Yes, the radius follows the drive, and a rhythm comes out: 5.5 far episodes per 1,000 steps, a period of about 150 steps, mostly short far episodes, and bouts of 57–127 steps in half the seeds. But the loop is open. Going far does not raise the drive: at the same d, a step at r_max moves d over the next ten steps by about a tenth of the Reference's raw recovery (shuffled control, all 8 seeds). The raw recovery is regression to the mean. The walker comes back from far because the drive's long average sinks to the dull level, not because the far paid.
- **Question 2, the instrument.**
  - The rhythm belongs to the drive's filter. The compass Null, with no choice, has the same rhythm and the same long bouts.
  - When the radius is large doesn't matter. Shifted radius (same radii, other times) differs from the Reference on no core readout except raw recovery.
  - Bouts matter. Shuffled radius breaks the walk into 133 places of 6 steps, and the walker takes the top tile less often.
  - Range comes from the far bouts (fixed radius: 342 km; local only: 170 km). Returns and choice don't depend on range.
  - The character against the Null comes from the choice: preference (top tile, contrast, avoiding ocean) and clusters (revisits, straight-backs, fewer cells), all results on eight seeds.
- **Two things not foreseen.**
  - The far offers' lower novelty is selection, not the world. With the radius decoupled from d, far and near offers are equally novel.
  - Three of the 24 shifted and shuffled walks lost their eye for 100–425 steps (novelty about 0, held-out error frozen). None of the walks whose radius follows the rule or is constant did. Verdicts are the same without those three walks.

## The tables

### 11. The loop and its controls (8 seeds each; mean, with the range over seeds; whole walk)

| | compass Reference | compass Null | shifted radius | shuffled radius | fixed radius | local only |
|---|---|---|---|---|---|---|
| what it keeps | — | the drive, no choice | the radii, other times | the radii, any order | one radius (16.5–50.7 km) | r_min only |
| seeds reaching r_max | 7 of 8 | 7 of 8 | 7 of 8 | 7 of 8 | — | — |
| first r_max (step) | 208–816 | 244–783 | 0–529 | 0–487 | — | — |
| steps at r_min | 0.77 (0.62–0.91) | 0.72 (0.52–0.88) | 0.79 (0.67–0.92) | 0.78 (0.63–0.92) | 0 | 1 |
| steps at middle radii | 0.11 | 0.16 | 0.10 | 0.11 | — | 0 |
| steps at r_max | 0.066 (0–0.175) | 0.073 (0–0.231) | 0.061 (0–0.137) | 0.062 (0–0.166) | 0 | — |
| r_max episodes per 1,000 steps | 5.5 (0–10.5) | 5.4 (0–12.6) | 5.4 (0–10.5) | **55** (0–142) | 0 | — |
| median episode (steps) | 1–6 | 2–69 | 1–6 | 1 | — | — |
| longest run at r_max (steps) | 0–127 | 0–147 | 0–94 | 1–4 | — | — |
| walks with a run of ≥ 20 at r_max | 4 | 3 | 4 | 0 | — | — |
| r_max followed directly by r_min | 0 | 0.005 | 0 | 0.84 | — | — |
| period (steps) | 147 (43–321) | 166 (77–258), 7 seeds | 142 (43–326), 7 seeds | **4** (2–8) | — | — |
| places | 18 (11–27) | 22 (13–31) | 18 (12–27) | **133** (46–216) | 0 or 1 | 1 |
| median dwell (steps) | 33 (15–76) | 15 (2–37) | 29 (13–53) | **6** (2–12) | — | 1,000 |
| dwell against fall, ρ | −0.03 | −0.02 | −0.13 | 0.04 | — | — |
| recovery, raw | 0.26 (0.08–0.60) | 0.14 (0.06–0.31) | **0.00** (−0.20 to 0.30) | 0.05 (−0.06 to 0.30) | — | — |
| `recovery_at_d` | — | — | 0.20 (−0.07 to 0.75); −0.07 to 0.14 in the 4 seeds ≥ 9 % far | **0.025** (−0.005 to 0.047) | — | — |
| radius of gyration (km) | 3,328 (694–5,864) | 3,737 (1,016–5,026) | 3,487 (1,254–7,977) | 4,248 (1,138–7,901) | **342** (178–607) | **170** (120–228) |
| continents | 3.8 (1–6) | 4.5 (3–6) | 4.0 (1–7) | 4.1 (1–7) | 1 | 1 |
| unique cells | 586 (513–672) | 689 (437–785) | 584 (510–655) | 728 (547–868) | 644 (529–843) | 462 (383–552) |
| steps outside Europe | 0.27 | 0.39 | 0.57 | 0.65 | 0 | 0 |
| ocean share of cells stood on | 0.26 | 0.32 | 0.27 | 0.35 | 0.27 | 0.16 |

How to read the controls:
- Shifted radius: the same radii as the Reference walk of the same seed, circularly shifted, so places and episodes match it by construction. A shift splits a far bout at the end of the walk: seed 0's 127 steps become 94.
- Local only: r_max = r_min, so readouts.py counts every step as "at r_max". Its share at r_max, episode length, chattering, recovery and offer gap are artefacts, and they are left out above.
- Fixed radius: places are 0 or 1, depending only on whether the seed's radius is above 2 r_min.
- `recovery_at_d`: the coefficient on the radius (0 at r_min, 1 at r_max) in d[t+10] − d[t] ~ d[t] + radius, on schedule walks only. Fixed radius has one radius, so its coefficient (0.000–0.005) carries nothing. In shifted, seeds 3 and 7 have nearly no far steps (0.1 % and 0 %), and their 0.52 and 0.75 rest on a handful of middle radii.

### 12. Returns, choice, taste, the eye (8 seeds; returns and choice over the whole walk, taste settled; mean, with the range)

| | compass Reference | compass Null | shifted | shuffled | fixed | local only |
|---|---|---|---|---|---|---|
| revisits beyond blind | 0.16 (0.12–0.19) | **−0.00** (−0.02–0.01) | 0.15 (0.08–0.20) | 0.10 (0.00–0.19) | 0.16 (0.08–0.20) | 0.16 (0.07–0.24) |
| straight-backs beyond blind | 0.09 (0.05–0.13) | **−0.00** (−0.02–0.02) | 0.08 (0.05–0.11) | 0.06 (0.01–0.10) | 0.08 (0.04–0.13) | 0.10 (0.06–0.13) |
| top tile beyond chance | 0.46 (0.43–0.50) | **0.01** (−0.01–0.03) | 0.44 (0.37–0.52) | **0.40** (0.19–0.49) | 0.47 (0.41–0.53) | 0.45 (0.42–0.50) |
| texture of the choice (SD of offers) | 0.14 (−0.03–0.53) | −0.00 (−0.04–0.02) | 0.13 (−0.34–0.53) | 0.14 (0.03–0.35) | 0.36 (−0.16–0.83) | 0.14 (−0.48–0.66) |
| contrast | 0.24 (0.08–0.49) | **−0.00** (−0.04–0.03) | 0.21 (−0.27–0.55) | 0.22 (0.14–0.41) | 0.45 (−0.06–0.83) | 0.23 (−0.35–0.66) |
| brightness | 0.17 (−0.71–0.68) | −0.01 | 0.21 | 0.24 | 0.04 | 0.11 |
| bright (snow, ice, cloud) | 0.01 (−0.65–2.65) | 0.02 | −0.06 | −0.10 | −0.32 (−0.40 to −0.19) | −0.29 |
| saturation | −0.18 | −0.00 | −0.14 | −0.20 | −0.06 | −0.15 |
| ocean | −0.14 (−0.26 to −0.03) | **+0.11** (−0.03–0.77) | −0.22 | −0.13 | −0.19 | −0.11 |
| panel surprise ~ texture | 0.61 (0.41–0.76) | 0.62 (0.46–0.81) | 0.61 (0.36–0.77) | 0.62 (0.40–0.77) | 0.53 (0.42–0.66) | 0.46 (0.37–0.53) |
| held-out error at 1,000 | 0.002–0.027 | 0.002–0.005 | 0.003–0.005; s6 0.336 | 0.002–0.005 | 0.003–0.005 | 0.003–0.005 |
| results and leads against the Reference (core) | — | revisits, straight-backs, top tile; contrast, ocean (settled); unique cells +104 | raw recovery (lead) | places, period, top tile −0.07, unique cells +143 | gyration −2,986 km | gyration −3,158 km, unique cells −124 |

Near misses (7 of 8 seeds or more of one sign, but under half the Reference's range):
- Null texture: −0.15, 7 of 8.
- Null median dwell: −16 steps, 7 of 8, settled.
- Local only, the eye: −0.16, 7 of 8.
- Shuffled revisits: −0.06, only 5 of 8, so not a near miss.

### 13. Where it starts (the compass Reference; Paris 8 seeds, Tamanrasset and Douala seeds 0–3; mean, with the range)

| | Paris | B: Tamanrasset (22.8 °N 5.5 °E) | C: Douala (4.05 °N 9.7 °E) |
|---|---|---|---|
| first r_max (step) | 208–816 (7 of 8) | 107, 405, 595, 905 | 120, 640, 774, 879 |
| steps at r_min | 0.77 | 0.63 (0.50–0.87) | 0.77 (0.70–0.86) |
| steps at r_max | 0.066 | **0.19** (0.01–0.31) | 0.10 (0.00–0.24) |
| r_max episodes per 1,000 | 5.5 | 3.4 (1.1–9.5) | 5.5 (2.1–15.8) |
| median far episode (steps) | 1–6 | **8–295** (lead) | **2–113** (lead) |
| longest run at r_max | 0–127 | 8, 69, 261, 295 | 3, 5, 37, 222 |
| radius of gyration (km) | 3,328 | 4,951 (2,650–6,784) | 3,005 (1,359–4,936) |
| places; median dwell | 18; 33 | 15; 31 | 15; 48 |
| revisits; straight-backs; top tile | 0.16; 0.09; 0.46 | 0.15; 0.09; 0.46 | 0.17; 0.08; 0.44 |
| texture; contrast; ocean (settled) | 0.14; 0.24; −0.14 | **0.21; 0.17; −0.14 against seeds 0–3** (leads, 4 of 4) | 0.03; 0.11; −0.24 |
| offered novelty near; far; gap | 0.30; 0.22; −0.09 | 0.27; 0.21; −0.05 | 0.39; 0.20; **−0.19** (lead) |

In row "texture; contrast; ocean", start B's entries are its differences from Paris seeds 0–3 (B's own values: 0.30; 0.37; −0.28).

### 14. Offered novelty at r_max and at r_min (median over offered cells, steps from 150; seeds that reach r_max)

| | far (r_max) | near (r_min) | far − near | seeds with far < near |
|---|---|---|---|---|
| compass Reference | 0.22 | 0.30 | −0.09 (−0.17 to −0.03) | 7 of 7 |
| compass Null | 0.17 | 0.23 | −0.07 (−0.16 to −0.01) | 7 of 7 |
| shifted radius | 0.21 (0.21 without s6) | 0.19 (0.21 without s6) | **+0.02** (−0.09 to +0.13); +0.00 without s6 | 2 of 6 |
| shuffled radius | 0.20 | 0.22 | **−0.02** (−0.08 to +0.03) | 5 of 7 (one level) |
| start B / start C | 0.21 / 0.20 | 0.27 / 0.39 | −0.05 / −0.19 | 3 of 4 / 4 of 4 |

### 15. Three walks whose eye collapsed

| walk | steps | chosen novelty in the window | held-out error | steps 0–49 beyond 30 km (at r_max) | before it |
|---|---|---|---|---|---|
| `e09_shuffled_s1` | ~25 to ~450 | 0.000 | 0.2517 at every checkpoint from 25 to 450, then 0.08, then normal (0.005) | 9 (4) | its first 50 steps all on ocean |
| `e09_shuffled_s4` | ~25 to ~125 | 0.000 | 0.2517 at 25–125, then normal | 10 (7) | mostly land |
| `e09_shifted_s6` | ~725 to ~950 | 0.001 | 0.1003 at every checkpoint from 725 to 950, 0.12 at 975, 0.34 at 1,000 | 0 | held at r_min for 150 steps at novelty 0.03–0.04 (steps 600–749), after a far bout over ocean |

Scanned: every finished `e09_` walk (86). No other walk has a run of more than 23 steps with chosen novelty under 0.005, or held-out error above 0.04 after step 250. The schedules put steps beyond 30 km into the warm-up of 13 of the 16 shifted and shuffled walks; neither the Reference nor the Null has any there.

## Findings

29. **The radius follows the drive, and a rhythm comes out (table 11).** In 7 of 8 seeds the walker goes far, first at steps 208–816. There are 5.5 far episodes per 1,000 steps, most of 1–6 steps, and in four seeds there is a bout of 57–127 steps late in the walk. The autocorrelation of log r peaks at 43–321 steps. The radius steps down through middle radii (0.11 of steps) and never jumps from r_max straight to r_min.
30. **Going far does not restore the drive.** With the radius set by a schedule instead of d, a step at r_max changes d over the next ten steps no more than a step at r_min does at the same d. In the shuffled control the coefficient is 0.025 in the mean, between −0.005 and 0.047 in all 8 seeds, against a raw recovery of 0.26 in the Reference. The shifted control is noisier (its far steps come in a few bouts), but it is close to 0 (−0.07 to 0.14) in the four seeds that are far on at least 9 % of steps. Its raw recovery is 0.00, so Reference minus shifted is a lead (7 of 7). The Reference's raw recovery (finding 24, prediction 55) is regression to the mean: the walker is far only when d is lowest, and from there d rises again on its own. What brings the walker back near is the long average sinking to the dull level, not a far offer that paid.
31. **The rhythm is the drive's, not the choice's.** The compass Null picks offers at random and has the same rhythm: share at r_max, episodes, period and raw recovery are all within the Reference's range, with no lead. Its long far bouts are as long (147, 110 and 69 steps). Neither choice nor any response from the world is needed. The tempo comes from the drive's filter (averages of 20 and 200 steps, Δ 0.25) acting on the novelty series. The world sets when the walker leaves and how long a bout lasts (finding 37), but not that there is a rhythm. Of the walker's behaviour, this is the most hand-set part.
32. **When the radius is large doesn't matter for anything else measured.** The shifted walks have the same radii at other times. They differ from the Reference on no core readout except raw recovery: range, unique cells, places, dwell, returns, top tile, taste and the eye all match (table 12). As the schedules require, they go far earlier, so their young-phase gyration is larger (+1,177 km, a result). At eight seeds, coupling the radius to d adds nothing visible beyond the mix of radii it produces.
33. **Bouts do matter (shuffled).** Scattering the same radii one step at a time gives 133 places of median dwell 6 and a period of 4 steps. 84 % of far steps are followed straight by r_min. The walker takes the top tile less often (−0.07, 7 of 8, a result). Revisits are lower in 5 of 8 seeds (−0.06, no lead). The lowest are seeds 0, 1, 4 and 6 (0.005–0.065), and only two of those collapsed. It stands on 143 more cells (a result), and its range is not smaller.
34. **Range comes from far bouts; returns from the choice.** At a fixed radius of 16.5–50.7 km the walker covers 342 km (178–607) and one continent; local only covers 170 km. Its returns and choice are those of the Reference: revisits 0.16 and 0.16, straight-backs 0.08 and 0.10, top tile 0.47 and 0.45. Local only stands on 124 fewer cells (a result).
35. **Travel sharpens the eye a little.** The panel's surprise follows texture at ρ 0.46 for local only, 0.53 at a fixed radius and 0.61 for the Reference. Local only is below the Reference in 7 of 8 seeds (−0.16), short of the size rule (0.175). Held-out error does not differ.
36. **The far offers' deficit is selection, not the world (table 14).** With the radius independent of d, far and near offers carry the same novelty: shifted 0.21 against 0.21 (without the collapsed s6), shuffled −0.02. Near offers in the Reference are rich (0.30 against 0.21 in shifted) because the walker stands near only while near pays. Far offers are about the same in both (0.22 and 0.21). So at the 2.7 km eye, the world's part of the Reference's −0.09 gap is at most about 0.02. The Null has the gap too (−0.07, 7 of 7), since its radius follows the same rule. The 2026-11-09 note in the log put selection first; its other two parts, the ocean in far offers and the scale of the eye, turn out small.
37. **Where it starts sets the bouts (table 13).** From Tamanrasset the far episodes are longer in all four seeds (lead): the longest runs at r_max are 261 and 295 steps, and 0.19 of steps are at r_max. From Douala the near offers are rich (0.39), so the gap is the largest (−0.19, lead), and episodes are longer too (lead). Neither start sends the walker far sooner than Paris: first r_max at 107–905 and 120–879. From Tamanrasset it is choosier: texture, contrast and ocean avoidance are leads (4 of 4), settled phase. Returns and top tile are the same everywhere.
38. **Character against the Null (the aim).** The Reference has more preference and more clusters than the Null, each a result on eight seeds:
    - Preference: top tile 0.46 against 0.01, contrast of the choice 0.24 against 0.00 (8 of 8, settled), and it avoids ocean (−0.14 against +0.11, settled). Texture is 7 of 8 but short of the size rule.
    - Clusters: revisits 0.16 against 0.00, straight-backs 0.09 against 0.00, and 88–104 fewer cells.
    - Stays: its places last longer (median dwell 33 against 15, shorter in the Null in 7 of 8 settled, short of the size rule). Picking the best offer keeps a place paying.
    - Rhythm: no difference (finding 31).
    So against the compass Null, the character comes from the choice, and the rhythm is shared.
39. **Three schedule walks lost their eye (table 15).** For 100–425 steps novelty was about 0 and held-out error froze at one value: the network mapped every patch to one point. Two walks recovered; one had not by step 1,000. None of the 40 walks of the Reference and Stage 2 whose radius follows the rule or is constant did this, nor did any Stage 1 walk. The two early collapses (from step ~25) are in walks whose schedule went far during the warm-up. The schedules did that in 13 of the 16 shifted and shuffled walks; the Reference never does, since its drive counts from step 50. The late collapse came after 150 steps held near at a place gone dull (novelty 0.03), where the rule would have sent the walker far. Three walks cannot settle the cause, but the controls differ from the Reference in a way they were not meant to. Without the three walks, no verdict changes. For example, shifted revisits are 0.157 against 0.148, and shuffled revisits are 0.127 against 0.104, still below the Reference.
40. **Cost.** 48 of 48 walks finished, 14–31 min each three side by side, 6 h 04 min in all. One fetch was dropped in all of Stage 2, in a fixed-radius walk.

## Against the predictions (57–66, written 2026-11-09)

| # | Setting | Predicted | Found | Verdict |
|---|---|---|---|---|
| 57 | compass Null | ≥ 6 of 8 reach r_max; 0.6–0.9 at r_min; revisits, straight-backs within ±0.04, top tile ±0.03, texture and contrast ±0.15; leads toward the Reference on the three | 7 of 8; 0.52–0.88 (seed 0 at 0.52); −0.00, −0.00, 0.01, −0.00, −0.00; results on all three | mostly right |
| 58 | the dull far | far < near in ≥ 6 of the Null seeds that reach r_max; ≥ 3 of 8 Null seeds with a run of ≥ 20 at r_max; read as the world's | 7 of 7; 3 (147, 110, 69); but with the radius decoupled from d far ≈ near (finding 36): it is the rule's selection | partly (numbers right, reading wrong) |
| 59 | recovery | Reference − shifted raw recovery > 0, a lead; `recovery_at_d` within ±0.1 of 0 or below in shifted and shuffled | lead (7 of 7); shuffled 0.025; shifted 0.20, from two seeds with almost no far steps (−0.07 to 0.14 in the four with many) | mostly right |
| 60 | shifted, the rest | no lead on more than one of gyration, unique cells, places, dwell; none on revisits, straight-backs, top tile, dwell ~ fall | none on any | right |
| 61 | shuffled | period < 20 or none in ≥ 6 of 8; places ≥ 54; median dwell ≤ 8; revisits below, a lead | 8 of 8 (2–8 steps); 133; 5.6; −0.06 in 5 of 8, no lead | mostly right |
| 62 | fixed radius | gyration < 1,500 km in ≥ 6 of 8, a lead; revisits 0.05–0.20 | 8 of 8 (178–607), result; 0.08–0.20 | right |
| 63 | local only | gyration < 400 km in all 8; 1–2 places; no lead on returns; unique cells below, a lead; no lead on held-out error | 120–228 km; 1; none; result (−124); none | right |
| 64 | starts | B: first r_max before step 400 in ≥ 3 of 4, share at r_max > 0.066 in ≥ 3 of 4; C: first r_max at 150–800 in ≥ 3 of 4; revisits > 0.05 in all 8 | B: 1 of 4 (107; others 405–905), 3 of 4 (0.17–0.31); C: 2 of 4 (120, 879 outside); 0.058–0.25 | partly |
| 65 | character against the Null | leads on preference (top tile, texture or contrast) and clusters (revisits, straight-backs); none on rhythm | results on top tile, contrast, revisits, straight-backs (and ocean, unique cells); none on episodes or period | right |
| 66 | cost | 48 of 48; 15–35 min per walk; under 7 h; < 20 fetches dropped per walk | 48; 14–31 min; 6 h 04; at most 1 | mostly right |

Tally: 4 right (60, 62, 63, 65), 4 mostly right (57, 59, 61, 66), 2 partly (58, 64), none wrong.

What I got wrong, in kind:
- I read the far offers' low novelty as the world's. It is the rule's selection: near offers are counted while near still pays.
- I expected the desert to wear out sooner. It doesn't send the walker far earlier; once far, the walker stays far longer.
- Finding 24 ("going far restores the drive"), written for review in round 2, was wrong. Its own caveat, that the controls would tell, was the right part.

## For review

The answers:
- **Question 1.** The radius follows the drive and a rhythm comes out, but the loop is open: going far does not feed back into the drive.
- **Question 2.**
  - The rhythm is the drive filter's.
  - The coupling's timing is invisible on every other readout.
  - Bouts shape places and choice.
  - Range comes from the far bouts.
  - The character against the Null comes from the choice.

For the aim, "as little set by hand as possible", the rhythm is the weak part. Its tempo comes from two averages and Δ that I chose, and the world only modulates it. Recommended:

1. **Stage 3 as planned, with the larger eye first, and a sharper question.** At 2.7 km, far and near offers are equally novel (finding 36), so going far cannot pay. If a 5 or 8 km eye sees regions as more different than neighbours, its shifted control should show far above near (`offer_n_gap` > 0), and `recovery_at_d` should rise above 0. That would close the loop, with the world, not the filter, deciding when the walker returns. Dated predictions first, then `start 3a` (16 walks, about 2 h).
2. **Keep the warm-up out of the schedules** (finding 39). `schedules.py` would hold steps 0–49 at r_min, as the rule does, and shift or shuffle only steps 50–999. Used for the larger eye's shifted controls. I would not re-walk Stage 2's shifted and shuffled walks (16 walks, about 2 h), since no verdict changes without the collapsed walks. If you want the cleaner instrument for Stage 2 as well, that is the cost.
3. **A collapse readout**: per walk, the longest run of chosen novelty under 0.005, and whether held-out error froze. Flagged in every table from now on.
4. **Readout definitions** (cosmetic): loop readouts as NaN where r_max = r_min (local only), and places as NaN at a fixed radius above 2 r_min.

# Stage 3a: the larger eye (2026-11-09)

24 walks from Paris, 1,000 steps, seeds 0–3: the compass Reference with `crop_px` 128 (eye about 5.3 km) and 192 (about 8.0 km). Each eye walk has a shifted and a shuffled radius control, replayed from that walk with the warm-up held at r_min (brief amendment B1). They are compared with `e09_ref` seeds 0–3 (the 2.7 km eye) and with Stage 2's controls. Predictions 67–74 and the readouts were fixed before the walks (log, 2026-11-09).

The world-view readouts (amendment A) are read offline from checkpoints taken every 100 steps.

A lead is four seeds of one sign with |mean| above half the compared group's range over those seeds (e08 D10). With four seeds, nothing here can be a result.

Files: `results/readouts.csv`, `paired.csv`, `paired_clean.csv`, `worldview.csv`, `worldview.png`.

**The short version.**
- **Does the larger eye open the loop? No.**
  - With the radius decoupled from d (shifted control), far offers are still less novel than near ones: −0.06 at 5.3 km (3 of 3 seeds that go far) and −0.05 at 8 km (2 of 3). The same holds on land only. At 2.7 km the same control gave +0.02.
  - Going far still does not raise the drive. In the shuffled walks, `recovery_at_d` is 0.05 at both eyes (0.02–0.05 in the seeds that go far), against 0.025 at 2.7 km and a raw recovery of 0.26.
- **Does the plateau grow with eye size? No.**
  - The Tobler curves of the three eyes lie inside each other's seed ranges. The plateau is at 7,700–12,400 km at every eye, and Tobler ρ is 0.15–0.17 at every eye.
  - No eye beats colour and texture on land cover (0 of 24 walks, 0 of 44 in all). The 8 km eye is not better than the 2.7 km eye.
- **The walk is the same.** No lead on any loop, range or return readout against the 2.7 km eye. Two differences:
  - At 8 km the walker chooses more contrast (lead, settled).
  - Both larger eyes leave for r_max late (steps 678–871, against 208–608).
- **The controls behave as in Stage 2**, now without collapse. None of the 24 walks lost its eye, and none of the 16 controls left r_min during the warm-up.

## The tables

### 16. The larger eye and its controls (seeds 0–3; mean, with the range over seeds; whole walk)

| | 2.7 km (`e09_ref` s0–3) | 5.3 km | 5.3 km shifted | 5.3 km shuffled | 8 km | 8 km shifted | 8 km shuffled |
|---|---|---|---|---|---|---|---|
| collapsed | 0 of 4 | 0 of 4 | 0 of 4 | 0 of 4 | 0 of 4 | 0 of 4 | 0 of 4 |
| seeds reaching r_max | 4 of 4 | 3 of 4 | 3 of 4 | 3 of 4 | 3 of 4 | 3 of 4 | 3 of 4 |
| first r_max (step) | 208, 418, 602, 608 | 778, 805, 871 | 94, 273, 562 | 51, 54, 187 | 678, 783, 795 | 329, 567, 813 | 55, 56, 113 |
| steps at r_min | 0.77 (0.62–0.90) | 0.75 (0.62–0.90) | same | same | 0.77 (0.62–0.93) | same | same |
| steps at r_max | 0.076 (0.001–0.175) | 0.046 (0–0.095) | same | same | 0.094 (0–0.189) | same | same |
| r_max episodes per 1,000 | 5.8 (1.1–10.5) | 5.3 (0–8.4) | 5.3 | **43** (0–86) | 5.3 (0–13.7) | 5.3 | **78** (0–159) |
| longest run at r_max | 1, 3, 81, 127 | 15, 26, 38 | 15, 26, 38 | 2 | 2, 72, 168 | 2, 72, 168 | 1–3 |
| r_max followed by r_min | 0 | 0 | 0.006 | **0.66** | 0 | 0.002 | **0.75** |
| period (steps) | 128 (43–218) | 170 (23–294), 3 seeds | 88 (23–152), 2 seeds | **5** (3–9) | 170 (19–351), 3 seeds | 170 (19–352), 3 seeds | **4** (2–7) |
| places | 16.5 (11–24) | 20.8 (17–28) | 21.3 (17–28) | **132** (56–196) | 17.5 (12–21) | 17.8 (12–21) | **126** (32–211) |
| median dwell (steps) | 42 (22–76) | 20 (15–27) | 20 (13–27) | **5** (2–11) | 15 (3–36) | 17 (3–44) | 10 (2–26) |
| recovery, raw | 0.27 (0.08–0.60) | 0.10 (0.04–0.20) | 0.02 (−0.04 to 0.06) | 0.05 (0.01–0.10) | 0.14 (0.04–0.32) | 0.17 (0.00–0.49) | 0.00 (−0.03 to 0.03) |
| `recovery_at_d` | — | — | 0.16 (−0.02 to 0.46) | 0.053 (0.037–0.073) | — | 0.16 (−0.03 to 0.43) | 0.056 (0.004–0.161) |
| offered novelty far; near | 0.20; 0.32 | 0.22; 0.32 | 0.21; 0.26 | 0.23; 0.26 | 0.33; 0.42 | 0.33; 0.37 | 0.28; 0.32 |
| far − near | −0.11 (−0.17 to −0.06) | −0.11 (−0.25 to −0.03) | **−0.061** (−0.075 to −0.049) | −0.040 (−0.049 to −0.036) | −0.11 (−0.15 to −0.06) | **−0.054** (−0.106 to +0.033) | −0.010 (−0.061 to +0.082) |
| far − near, land offers only | −0.11 | −0.11 | −0.049 (3 of 3 < 0) | −0.027 | −0.16 | −0.055 (2 of 3 < 0) | +0.009 |
| radius of gyration (km) | 4,326 (1,541–5,864) | 2,310 (813–3,903) | 2,866 | 3,214 | 2,458 (561–4,948) | 3,166 | 3,715 |
| continents | 4.0 (1–6) | 4.0 (2–5) | 3.5 | 4.0 | 4.5 (1–7) | 4.3 | 4.0 |
| unique cells | 603 (557–672) | 585 (537–630) | 572 | **736** | 584 (470–693) | 604 | **718** |
| steps outside Europe | 0.38 | 0.12 | **0.52** | **0.55** | 0.12 | 0.33 | 0.59 |

How to read it:
- The controls replay their own eye's radii, so their shares, episodes (shifted) and seeds reaching r_max match it by construction.
- Novelty is on each eye's own scale: it compares within an eye, not across eyes.
- In the shifted and shuffled rows, far − near is over the seeds that go far (3 per group).
- `recovery_at_d` is noisy where a seed has almost no far steps, as in Stage 2:
  - The high shifted values (0.46 and 0.43) come from seeds at r_max on 0 % and 0.5 % of steps.
  - In the four shifted seeds at r_max on 6–19 % of steps it is −0.03 to 0.21.
  - In shuffled, the 0.161 (8 km) and 0.073 (5.3 km) come from the seed that never reaches r_max. Without that seed: 0.020 (0.004–0.034) at 8 km and 0.046 (0.037–0.059) at 5.3 km.
- Stage 2's shuffled walks, seeds 0–3: −0.005, 0.022 (collapsed s1), 0.025, 0.029.

### 17. Returns, choice, taste (seeds 0–3; returns and choice over the whole walk, taste settled; mean, with the range)

| | 2.7 km | 5.3 km | 5.3 km shifted | 5.3 km shuffled | 8 km | 8 km shifted | 8 km shuffled |
|---|---|---|---|---|---|---|---|
| revisits beyond blind | 0.16 (0.13–0.18) | 0.16 (0.13–0.17) | 0.14 | 0.10 (0.07–0.17) | 0.15 (0.09–0.25) | 0.13 | 0.11 (0.06–0.18) |
| straight-backs beyond blind | 0.09 | 0.09 | 0.07 | 0.07 | 0.09 | 0.08 | 0.07 |
| top tile beyond chance | 0.45 | 0.45 | 0.44 | 0.46 | 0.47 | 0.46 | 0.45 |
| texture of the choice | 0.09 (0.02–0.27) | 0.09 (−0.14–0.43) | **0.38** | 0.12 | 0.37 (0.15–0.86) | 0.35 | 0.26 |
| contrast | 0.19 (0.08–0.31) | 0.20 (−0.05–0.45) | 0.43 | 0.25 | **0.52** (0.28–1.00) | 0.50 | 0.38 |
| ocean | −0.14 (−0.26 to −0.03) | −0.06 (−0.36–0.32) | −0.19 | −0.29 | +0.02 (−0.27–0.38) | −0.30 | **−0.34** |
| held-out error at 1,000 (own eye only) | 0.002–0.027 | 0.002–0.007 | 0.003–0.015 | 0.003 | 0.003–0.015 | 0.004–0.006 | 0.003–0.004 |
| longest run of chosen novelty < 0.005 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| lowest probe spread after step 0 | 0.65 (0.52–0.76) | 0.54 (0.27–0.65) | 0.60 | 0.71 | 0.54 (0.29–0.78) | 0.61 | 0.75 |
| leads | — | none (against 2.7 km) | texture +0.30 (settled), outside Europe +0.40 (against its eye) | places +112, dwell −15, unique cells +151, outside Europe +0.43 (against its eye) | contrast +0.33, dwell −21 (settled, against 2.7 km); contrast +0.31 against 5.3 km | dwell against fall ρ −0.48 (against its eye) | places +109, unique cells +134, ocean −0.36 (settled; against its eye) |

Near misses (4 of 4 of one sign, under half the range):
- 5.3 km against 2.7 km: places +4, median dwell −22, macro-F1 −0.018, R² −0.038.
- 8 km against 2.7 km: median dwell −27 (whole walk), dwell against fall +0.42.
- 8 km against 5.3 km: texture +0.25.
- 8 km shifted against its eye: near offers −0.049.

Without collapsed walks: none of the 24 is collapsed, and the 2.7 km Reference has none, so every verdict in tables 16–18 is the same with and without. The exception is comparing with Stage 2's controls, whose seeds 0–3 include the collapsed `e09_shuffled_s1`. There, two leads hold only with it in:
- 5.3 km shuffled `recovery_at_d` +0.035 (4 of 4);
- shuffled ocean avoidance, −0.26 and −0.35.

Without it they rest on 3 seeds.

### 18. The world-view at step 1,000 (5,006 probe cells; seeds 0–3; mean, with the range)

| | 2.7 km | 5.3 km | 5.3 km shifted | 5.3 km shuffled | 8 km | 8 km shifted | 8 km shuffled |
|---|---|---|---|---|---|---|---|
| land cover, balanced accuracy | 0.37 (0.34–0.39) | 0.37 (0.34–0.40) | 0.37 | 0.39 (0.38–0.40) | 0.35 (0.30–0.40) | 0.34 | 0.38 |
| colour and texture; untrained | 0.50; 0.40 | 0.49; 0.41 | | | 0.49; 0.40 | | |
| macro-F1 | 0.31 | 0.29 | 0.29 | 0.32 | 0.27 | 0.27 | 0.30 |
| class fractions, R² (colour 0.25; untrained 0.29–0.31) | 0.29 | 0.25 | 0.26 | **0.30** | 0.23 | 0.23 | 0.28 |
| Tobler ρ (colour 0.04; untrained 0.06) | 0.17 (0.12–0.21) | 0.15 (0.10–0.20) | 0.14 | 0.15 | 0.16 (0.14–0.18) | 0.16 | **0.12** |
| cosine distance at 25 km; 450 km; 3,000 km; 7,700 km | 0.39; 0.66; 0.69; 0.85 | 0.41; 0.64; 0.71; 0.86 | 0.35; 0.57; 0.67; 0.79 | 0.41; 0.56; 0.78; 0.92 | 0.36; 0.63; 0.62; 0.74 | 0.40; 0.64; 0.69; 0.82 | 0.45; 0.56; 0.82; 0.94 |
| plateau (km) | 7,700–12,400 | 7,700–12,400 (one seed none) | 7,700–12,400 | 7,700 | 7,700–12,400 | 7,700–12,400 | 7,700 |
| neighbours within 500 km beyond chance (colour 0.034–0.038) | 0.023 | 0.021 | 0.022 | 0.023 | 0.019 | 0.018 | 0.022 |
| probe spread | 0.77 | 0.79 | 0.72 | 0.84 | 0.68 | 0.76 | 0.87 |

Over the walk (seed means, Reference seeds 0–7, eyes seeds 0–3):
- Balanced accuracy falls from about 0.41 at step 0 to 0.25 at step 100 at the larger eyes. The 2.7 km Reference reaches 0.30 at step 250, its first checkpoint. It climbs back to 0.35–0.37 by step 1,000.
- It ends below the untrained encoder in 38 of 44 walks.
- Tobler ρ ends above the untrained encoder in 43 of 44.

The plateau can only fall on a bin edge: 7,700 or 12,400 km (the criterion is in the log). As a check I also read the curve's half-rise distance. It varies from 300 to 5,000 km within one group, so it cannot tell the eyes apart either, and it is not reported.

## Findings

41. **The larger eye walks like the small one (tables 16, 17).** At neither eye is there a lead on any loop, range or return readout against the 2.7 km walks of the same seeds:
    - share at r_max, episodes, period, places, gyration, unique cells, revisits, straight-backs and top tile are all unchanged.
    - One seed at each eye never goes far, which no 2.7 km seed in 0–3 did.
    - Those that go far leave late: steps 778–871 at 5.3 km and 678–795 at 8 km, against 208–608 for the same seeds at 2.7 km. The Reference's eight seeds range 208–816. A larger eye keeps the near ground paying for longer.
    - Places last shorter in 4 of 4 seeds at both eyes (near misses at 5.3 km, a lead at 8 km settled).
42. **The larger eye does not open the loop (table 16).**
    - With the radius decoupled from d, the larger eye's far offers are less novel than its near offers: −0.061 at 5.3 km (3 of 3) and −0.054 at 8 km (2 of 3).
    - At 2.7 km the same control gave +0.02 (Stage 2, 6 seeds, −0.09 to +0.13), so the larger eye, if anything, moves the gap the wrong way. Three seeds per eye cannot settle that.
    - It is not the ocean: on land offers alone the gap is −0.049 and −0.055.
    - Going far still does not raise the drive. In the shuffled walks, `recovery_at_d` among seeds that go far is 0.046 (5.3 km) and 0.020 (8 km), against 0.025 at 2.7 km. All are a fifth or less of the Reference's raw recovery (0.27).
    - So at no eye tested does a far offer pay. The world-view (finding 46) shows why the eye's scale is not the cause: the embedding separates far tiles from near ones at every eye. Novelty is measured against the archive of visited tiles, though, not against the current one (log, offline pass). A world-view ordered by distance does not make far tiles new to the archive.
43. **Shifted, at the larger eye: timing still doesn't matter.** No lead on gyration, continents, unique cells, places, revisits, straight-backs or top tile against its own eye walk, as in Stage 2 (finding 32).
    - The shifts move the far bouts earlier, so the 5.3 km shifted walks spend more of the walk outside Europe (+0.40, lead).
    - The 5.3 km shifted walks choose more texture (+0.30, lead, settled), and the 8 km shifted walks lose the eye walk's link between dwell and fall (ρ −0.48, lead). Neither has a counterpart in Stage 2's shifted walks.
44. **Shuffled, at the larger eye: bouts matter, as in Stage 2 (finding 33).**
    - The shuffled walks have 132 and 126 places, a period of 2–9 steps, and 0.66–0.75 of far steps followed straight by r_min. They stand on 151 and 134 more cells (leads).
    - Unlike Stage 2, the top tile is not taken less often (0.46 and 0.45 against 0.45 and 0.47).
    - Revisits are lower in the mean (0.10 and 0.11 against 0.16 and 0.15), but not in all four seeds.
    - At 8 km the shuffled walks avoid ocean more (−0.36, lead, settled).
45. **The 8 km eye chooses contrast (table 17).** Settled, the contrast of the chosen cell is 0.52 at 8 km, against 0.19 at 2.7 km (+0.33, lead) and 0.20 at 5.3 km (+0.31, lead). Texture rises the same way (near miss against 5.3 km).
    - A 192 px crop holds more structure per patch, and the choice follows it.
    - Preference (top tile 0.47) and clusters (revisits 0.15) are kept.
    - It is the one place where the eye changes the walker's style.
46. **The larger eye does not see the Earth as more regional (table 18).**
    - The Tobler curves of the three eyes overlap within the seed ranges at every distance.
    - Tobler ρ is 0.15–0.17 at every eye, with no lead.
    - The plateau stays at 7,700–12,400 km.
    - No walk at any eye beats colour and texture on land cover (0 of 24 here, 0 of 44 in all). The 8 km eye is not better than the 2.7 km eye (higher in 1 of 4 seeds). Its R² is lower (−0.058, 4 of 4 seeds, under the size rule's 0.059).
    - Training first wipes out the untrained network's land-cover reading (0.41 → 0.25 by step 100 at the larger eyes), then rebuilds most of it. Meanwhile the embedding becomes ordered by distance on the ground (ρ 0.06 → 0.15, above the untrained net in 43 of 44 walks; colour 0.04).
    - So what the walker comes to know is where things are alike, at continental scale, more than what kind of ground they are. The eye's size does not change that.
47. **The most varied walks know land cover slightly better.**
    - At 5.3 km, the shuffled walks reach R² 0.30 against 0.25 (+0.05, lead) and balanced accuracy 0.39 against 0.37 (4 of 4 seeds, under the size rule). At 8 km the shuffled walks are +0.035 on balanced accuracy (3 of 4).
    - At 8 km they are less ordered by distance (ρ −0.04, lead).
    - Stage 2's shuffled walks showed the same high probe (0.40, two walks read).
    - Stepping between many more places gives the encoder more varied ground. That buys a little land cover and costs a little geography. Two eyes and four seeds make this a hint, not a result.
48. **No collapse.**
    - In all 24 walks, chosen novelty never stays under 0.005 for more than one step, held-out error never freezes, and probe spread stays at 0.27 or more (flag: below 0.2).
    - None of the 16 controls stepped beyond 30 km before step 50, against 13 of 16 in Stage 2.
    - This fits finding 39: the two early Stage 2 collapses followed far steps in the warm-up. Sixteen walks without collapse do not prove it.
49. **Cost.**
    - 24 of 24 walks finished, 16–28 min each, three side by side. 3 h 31 min in all, 20:00:41 to 23:31:42.
    - Checkpoints: 12 MB per walk, 290 MB in all.
    - The offline world-view pass took 9 min for 24 walks × 11 checkpoints.
    - 5 fetches were dropped in one walk (`e09_crop192_shifted_s3`), none in the others.

## Against the predictions (67–74, written 2026-11-09)

| # | Setting | Predicted | Found | Verdict |
|---|---|---|---|---|
| 67 | the probe at the larger eyes | below colour (0.49) in ≥ 7 of 8; 0.33–0.45; 192 above 2.7 km (same seed) in ≥ 3 of 4 | 8 of 8; 6 of 8 in range (8 km s0 0.316, s2 0.298); 1 of 4 | partly |
| 68 | geography with eye size | ρ 0.12–0.25 at both eyes, no lead against 2.7 km; plateau ≥ 7,700 km at every eye, so "does it grow" reads no | 0.10–0.20 and 0.14–0.18 (one 5.3 km seed at 0.103); no lead; 7,700–12,400 km (one seed none); no | mostly right |
| 69 | the loop stays open | shifted `offer_n_gap` within ±0.03 of 0 at both eyes; shuffled `recovery_at_d` < 0.1 in all 4 seeds at both eyes; a larger eye is not what is missing | −0.061 and −0.054 (far below near); 4 of 4 and 3 of 4 (0.161 in the seed that never goes far); the loop stays open | partly (conclusion right, the gap's size wrong) |
| 70 | the walk at the larger eyes | ≥ 3 of 4 reach r_max at each eye; episodes 0–10.5 and period 43–321; no lead on revisits, straight-backs, top tile | 3 of 4 each; episodes 0–8.4 and 0–13.7, periods 19–351; no lead on any | mostly right |
| 71 | controls at the larger eyes | shifted: no lead on range, places, returns or top tile against its eye; shuffled: period < 20 in all 4, ≥ 3× the places | none on gyration, continents, unique cells, places, returns, top tile (but outside Europe +0.40 at 5.3 km); period 2–9 in 8 of 8; ≥ 3× in 7 of 8 (8 km s1: 2.7×) | mostly right |
| 72 | no collapse | none of the 24 flagged; if one, a control | none | right |
| 73 | Reference against the Null, again | not walked at the larger eyes | not tested | — |
| 74 | cost | 24 of 24; 15–35 min each; under 3.5 h; ≤ 1 GB of checkpoints; offline pass under 20 min | 24; 16–28 min; 3 h 31; 0.29 GB; 9 min | mostly right |

Tally: 1 right (72), 4 mostly right (68, 70, 71, 74), 2 partly (67, 69), 1 not tested (73), none wrong.

What I got wrong, in kind:
- I expected the 8 km eye's probe to read better, because a larger crop resized to 32 px is closer to a colour summary. It isn't: the encoder's reading does not follow the crop's information.
- I expected the decoupled gap to stay at 0. At the larger eyes far offers are duller than near ones even without selection. The direction of the conclusion held: going far does not pay.

## For review

The brief's questions:
- **Does the larger eye open the loop?** No. At 5.3 and 8 km the eye's own far-near gap is negative (−0.06 and −0.05), and going far does not raise the drive (`recovery_at_d` 0.02–0.05 in seeds that go far).
- **Does the plateau grow with eye size?** No. The embedding is ordered at continental scale at every eye, with the same curve.
- **Does the probe beat colour?** No, at no eye.
- **Reference against the Null:** no world-view difference at 2.7 km (Stage 2 offline pass). Not walked at the larger eyes.

What this means for the aim:
- The eye's scale is not what keeps the loop open. The open loop is in how novelty is measured: against an archive that soon holds look-alikes for every far tile, whatever the eye.
- The rhythm stays the drive filter's.
- The larger eye changes one part of the style: the 8 km walker picks high-contrast ground.

Recommended:
1. **Stage 3's transfer settings at the 2.7 km eye.** The brief says "at the eye this test favours". Neither larger eye opens the loop or reads the world better, and every Stage 1–2 calibration was done at 2.7 km. The walks cost the same at all three eyes.
2. **Of the settings, `drive_signal` first** (D2: novelty or progress). If anything can make far pay, it is a signal that is not measured against the archive. Learning progress at a new region can be high where novelty against the archive is not. The `k_nn` settings come second: they change how quickly the archive makes things look familiar.
3. **No new instrument needed.** The collapse readout and world-view readout ran on every walk at a cost of 9 min per 24 walks offline. I would keep checkpoints every 100 steps in Stage 3.

Stopped for review before the rest of Stage 3.
