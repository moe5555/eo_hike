# Hikes 29.10: log

Brief: `brief.md` (the request as written, plus the adjustments). Expectation: `expectations.md`, written before the first walk.

## Setup (2026-10-29)

- Code: no change to `agent/`. The four characters are config files only: `configs/h2910_{bored,globalist,localist,fastlearner}.yaml`, each a copy of `global_perception.yaml` with `steps: 1000` and the changed keys marked `# hikes_2910 (was …)`.
- Machine: the Mac (CPU torch, `.venv`, tile cache `data/global/cache`), as in `notes/hikes_v3_revised/log.md`. Mac walks diverge from PC walks with the same seed.
- Smoke test: `h2910_globalist`, 15 steps: 2 long jumps taken, 2.3 s per step (cold cache). Deleted afterwards.
- Git: run on `157d2a0` with uncommitted notes, configs and this script, so `meta.json` shows the hash as dirty. `agent/` is unchanged from `157d2a0`.

## Runs

Started 2026-10-29 with `scripts/hikes_2910.sh > runs/hikes_2910.log`, one after another: seed 0 of the four characters, the reference's seed 1, then seed 1 of the four characters.

| Run | Character | Notes |
|---|---|---|
| `runs/global_perception_1k_s0` | Reference | from `notes/hikes_v3_revised/` |
| `runs/global_perception_1k_s1` | Reference | |
| `runs/h2910_bored_s{0,1}` | Bored | |
| `runs/h2910_globalist_s{0,1}` | Globalist | |
| `runs/h2910_localist_s{0,1}` | Localist | |
| `runs/h2910_fastlearner_s{0,1}` | Fast learner | **s1: the network collapsed at step 142** (decoder outputs 0 for every input; held-out MSE frozen at 0.2517 from step 150). Steps 142–999 are a blind walk; left out of the comparison (`observations.md` §5) |

Part 1 finished 2026-10-29 20:29, no failed walks. Times: 16–33 min per walk (Globalist slowest, Localist fastest).

## Hike pages

`hike.html` per run (`analysis/hike_viewer.py`, low-res tiles, default settings): built for the seed-0 walks as they finished, and for the rest by a watcher that runs the viewer once a run's `meta.json` is marked finished. `runs/global_perception_1k_s0/hike.html` existed already. The watcher built none of the six pages (cause not found); they were built by hand after the batch, and `scripts/hikes_2910.sh` now builds each page after its walk.

## Part 2: Paris, 5,000 steps

`scripts/hikes_2910_paris.sh > runs/hikes_2910_paris.log`, started 2026-10-29 while part 1 was still running. It waits for part 1's `all done`, then walks Bored and then Globalist (one after another, because both start at the same tiles and would fetch them into the shared cache at the same moment) and builds each run's `hike.html`. Expected time: about 1 h 40 min for Bored and 2 h 45 min for Globalist, at part 1's speeds.

| Run | Character | Notes |
|---|---|---|
| `runs/h2910_bored_paris_s0` | Bored, Paris, 5,000 steps | 2026-10-29 20:30–22:15, `hike.html` 37 MB |
| `runs/h2910_globalist_paris_s0` | Globalist, Paris, 5,000 steps | 2026-10-29 22:15 – 2026-10-30 00:30, `hike.html` 45 MB |

## Weighted player (2026-11-01)

`analysis/hike_viewer.py` gained a second player beside the fixed-speed one: each step is held for a duration set by its I. `d = i * x^s` above the typical interest `m`, `d = i / y^s` below it, where `s` is the distance from `m` as a share of the way to `H` or `L`, at most 1. Changing `i` keeps every ratio between durations. This is display only: the walks are unchanged. Defaults `i` = 2 s, `x` = 4, `y` = 2 (nothing under 1 s, about 55 % of steps between 1.5 and 2.67 s). At those defaults a 1,000-step walk runs about 39 min and the Paris Globalist about 3 h 18 min.

The anchors are fixed in the code: `m` = 1.1, `H` = 5.5, `L` = −1.3, about the median, p99 and p1 of the chosen tiles' I over the ten fixed-perception walks of `reflection_revisits.md`. They were not measured on `runs/global_baseline_1k_s0`, whose page uses them too. The 1 % at each end all get exactly `x` or `y`.

All 13 `hike.html` pages in `runs/` were rebuilt with default settings, as before.

### Remove duplicates

A box in the weighted player (key `D`, off by default) shows each tile once, at its first visit and with that visit's duration. Playback, arrows, filmstrip and clock follow the shortened film. The map, timeline and slider still cover the whole walk, and a slider position on a removed step snaps to the shown step before it.

Decision: the first visit's duration, not the sum over all visits. Most returns would happen on this grid without any interest (`reflection_revisits.md`), so a sum would turn chance into screen time and break `x` as the upper limit. First-visit duration already follows how often a tile was visited, at the defaults over the ten fixed-perception walks (steps ≥ 50):

| Visits over the walk | Tiles | Mean first-visit duration | Mean time over all visits |
|---|---|---|---|
| 1 | 3,941 | 1.94 s | 1.94 s |
| 2 | 1,757 | 2.27 s | 4.29 s |
| 3–4 | 1,552 | 2.87 s | 8.27 s |
| 5–6 | 653 | 3.69 s | 14.53 s |
| more than 6 | 172 | 4.86 s | 22.08 s |

The rank correlation between the two is 0.47, so it is a clear tendency and not a rule. For tiles visited 3 or more times, the first visit has the highest I of all visits in 70 % of cases.

The film keeps 48 % of the runtime on average: about 18 min for a 1,000-step walk and 1 h 42 min for the Paris Globalist. Within a stay, 79 % of cuts join tiles within 15 km of each other and 21 % skip further, typically about 22 km. All 13 pages were rebuilt again.
