# Character sheet (round h0311): log

Brief: `brief.md` (the Mac version of 2026-11-04, from branch `claude-cloud`, commit `6a43015`). Expectation: `notes/06_characters/expectations.md`, section "Round h0311", to be written before the first Stage 1 walk.

## 2026-11-04: setup

- **Names.** The brief predates the naming convention (`notes/README.md`). This round is experiment 08: `e08_` for configs and runs, `analysis/e08/` for code, `notes/08_character_sheet/results/` for its CSVs and figures. Noted at the top of the brief; the brief's paths to older notes were updated to the renamed folders.
- **Runs used in Stage 0.** The 28 h0111 Paris walks on this Mac: Reference, Null, Bored and the four landing variants (Reference and Bored at k=3 and k=8), seeds 0–3, 1,000 steps, split streams. The two eye-size walks (seed 0 only) are left out of the calibration: they cannot be paired over four seeds.

## Stage 0.1: readouts (`analysis/e08/readouts.py`)

- Definitions in the script's docstring. Places, bursts, rejected landings and appetite are imported from `analysis/h0111/` (`common.py`, `compare.py`, `task7_appetite.py`), so they match h0111 exactly.
- **Phases.** A place belongs to the phase in which it starts; a teleport and a landing to the phase of their step. Held-out error, appetite end and steps before the first jump are whole-walk readouts only.
- **Appetite end** has no definition in h0111. Used here: the first logged step from 100 on at which the fall in log held-out error over the trailing 200 steps stops; 1,000 when it never stops.
- **Spread** is the Reference's range over seeds (the brief's "spread"; the same number for the lead rule and for the matrix units).
- **Noise for paired differences.** There is no repeat of the Reference. The four landing comparisons (Reference k=3, k=8 against Reference; Bored k=3, k=8 against Bored) are the nearest thing, since best-of-k "changes little" (h0111). Their paired SD is used as the noise. For rhythm readouts it is an upper bound: best-of-k does move teleport landings.
- **Detectable effect** with four seeds: the effect a lead catches 80 % of the time, max(1.6 × paired SD, spread / 2), where 1.6 makes all four paired differences fall on the right side of zero with probability 0.8.
- **Per-tile statistics** for the 19,862 tiles offered in the 28 walks: same definitions as h0111 task 1, cached in `data/sheet/tile_stats.parquet` (git-ignored), about 50 s from the tile cache.
- **Redefinition after the first calibration.** Raw selection differentials (chosen minus mean on offer, in pixel units) are dominated by the few steps where neighbours differ a lot, such as coasts. Added standardised differentials (`selz_`: divided by the SD on offer, over the steps where it varies). Both are kept in `readouts.csv`; the calibration decides.
- **Built-in check.** The Null walker chooses uniformly, so its selection differentials must be about 0, and its difference from the Reference about minus the Reference's value. They are. Its `far_offered` equals the Reference's in every seed (shared offer stream).

## Stage 0.2: taste panel (`analysis/e08/panel.py`)

- **Pool.** 600 random tiles per cover (land, coast, ocean) from the global index, seed 311, leaving out every tile any h0111 walk stood on. Fetched into the tile cache (about 1,800 tiles at about 1.4 tiles/s; the cache stays under 30 GB).
- **Panel.** Within each cover, 6 tiles per cell of texture quartile × brightness quartile (16 cells), filled to 100 from the rest of that cover where a cell is short: 300 tiles, `analysis/e08/panel.csv`, never changed.
- **Scoring.** As the walker scores a candidate, with the checkpoint's network and an archive rebuilt from `steps.parquet` (one entry per arrival, embedded with the checkpoint's network). **Checked exact:** at step 500, which follows a re-embed with the `ckpt_0500` network, this reproduces the logged surprise and novelty of every candidate bit for bit and progress to 1e-9 (Reference s0, Bored s2, Null s1).
- About 20 s per run and checkpoint on the Mac CPU; 28 runs × 4 checkpoints. Raw scores in `data/sheet/panel_scores.parquet` (git-ignored), summaries in `results/`.

## Paused 2026-11-04: where Stage 0 stands and how to continue

**Done**

- 0.1 readouts and 0.3 calibration for the walk readouts: `results/readouts.csv`, `paired.csv`, `calibration.csv` (rerun any time, about 5 s: `.venv/bin/python analysis/e08/readouts.py`).
- First reading of the calibration, to go into the Stage 0 report:
  - The scorer is visible in returns and choice: excess revisit, excess straight-back, top candidate chosen and far tiles taken separate Null from the Reference in all four seeds, both phases.
  - Bored is visible in rhythm (teleports, places, rejected landings, shorter places), mostly in the young phase (steps 0–149).
  - Taste from choices is weak. Standardised selection differentials: the Reference avoids snow, ice and cloud (`selz_bright` −0.31 SD of what is on offer, lead against Null; Bored the same in the settled phase). No measurable preference for texture, contrast or entropy in its choices. Raw (pixel-unit) differentials see less than standardised ones.
  - Readouts that see nothing between Null, Bored and the Reference: held-out error, appetite end, unique tiles, ocean share, colour diversity. `far_offered` is identical by design (a check, not a readout).
- Panel scoring checked exact against the walk's own log (Stage 0.2 above).

**Interrupted**

- `panel.py select` was stopped while fetching the tile pool, by request; about 1,550 of the ~1,800 pool tiles are in the cache. Nothing was written to `analysis/e08/panel.csv` (it is written only at the end), so the panel is not chosen yet. The cache writes each tile to a `.part` file and renames it, so no tile is half-written; the 29 `.part` files in `data/global/cache` date from 2026-11-01 and are not from this round.

**To continue**

1. `.venv/bin/python analysis/e08/panel.py select` — the same seed draws the same pool, so it only fetches the missing tiles (minutes), then writes `analysis/e08/panel.csv`. Commit that file once it exists: it is never changed afterwards.
2. `.venv/bin/python analysis/e08/panel.py score` — about 40 min (28 runs × 4 checkpoints × ~20 s). Saves after every run to `data/sheet/panel_scores.parquet` and skips what is done, so it can be stopped and restarted.
3. `.venv/bin/python analysis/e08/panel.py summarise` — panel strata, panel readouts paired against the Reference, panel calibration, taste similarity (`results/panel_*.csv`, `panel_similarity.png`).
4. Optional 0.4 (where would a reason have taken it?) only if the rest of Stage 0 is done.
5. Write the Stage 0 report (`notes/08_character_sheet/observations.md`, in the style of `notes/07_film_arc/observations.md`): which readouts separate Null and Bored from the Reference, the noise and detectable effect of each, and which readouts to drop or redefine. Then stop for review before any Stage 1 walk, as the brief asks.

## 2026-11-04 (continued): panel chosen, scoring

- `panel.py select` finished the pool (1,800 fetched, none dropped; 10,178 walked tiles left out). The first `panel.csv` had the right tiles but lost the quartile labels of the 6-per-cell picks (pandas' `groupby().apply` drops the grouping columns). Fixed in the script, deleted and reselected with the same seed before any use: the same 300 tiles, now with every label, 6–8 tiles in each of the 48 cells. `analysis/e08/panel.csv` is final from here on.
- `panel.py score` started (log in `data/sheet/score.log`).
- **Second redefinition: taste among neighbours only.** The Null check failed for `selz_ocean` (−0.29 where uniform choice must give about 0). Cause: ocean varied among the candidates almost only at far offers, which are the same tile for every walker of a seed and rarely taken under uniform choice, so the per-step values were a few large positives against many small negatives. The brief reads taste from "choices within a place", and far offers have their own readout (`far_taken_over_chance`), so selection differentials now use the neighbours only, on steps where a neighbour was chosen. After the change every Null selection differential is about 0 (largest mean |0.07|).
- `selz_ocean` is unusable as a walk readout: from Paris the neighbours almost never mix land and ocean (one seed has such steps at all). Ocean preference comes from the panel.
- Scoring finished: 28 walks × 4 checkpoints × 300 tiles, about 40 s per checkpoint while other analysis shared the CPU. A column clash between the panel's green channel and the progress signal (both `g`) in `panel.py summarise` was fixed by joining only the panel columns the summary needs.

## Stage 0.3: calibration, and a change of noise model

- **Pairing by seed fails once walks diverge.** On the panel, same-seed pairs of different settings agree (ρ 0.44) no better than different seeds of one setting (0.42). The landing-variant noise model (`sd_paired_landing`) therefore understates the noise for every comparison that diverges from step 0, which is all of them except the landing variants. `calibration.csv` now gives effects in pooled **seed SDs** (RMS of the within-setting SDs over all seven settings) and `detectable` = 2 seed SDs.
- **Simulated lead rule** (four seeds, the setting's and the Reference's walks independent normal draws): false lead 9 % per readout, eight-seed result rule 1.3 %; with a pairing correlation of 0.5, 5 % and 0.3 %. Power of a four-seed lead: 0.29 at 1 seed SD, 0.70 at 2, 0.93 at 3. Lead counts: Null 28 of 74 walk readouts, Bored 8 (chance about 6.5); panel 10 and 2 of 68 (chance about 6).
- The pooled seed SD of rhythm readouts is inflated by the Null walker, whose places vary far more between seeds than any other setting's (median steps per place 155–1,000).
- **Two outlier walks on the panel**, `h0111_bored_s1` and `h0111_bored_k3_s0`, share almost no panel interest with anyone. Their networks are healthy (held-out error normal; surprise ranked like the others', ρ 0.73–0.77). The difference sits in novelty and progress, which depend on the archive: one ended in the Patagonian ice fields, the other in Yunnan. Panel surprise is free of path luck; novelty, progress and interest are not.
- Stage 0.4 not done (optional, last in order).

## Stage 0 done, 2026-11-04

Report: `observations.md`. It stops here for review before any Stage 1 walk, as the brief asks. Open decisions for that review: the core of 17 readouts, whether to walk the Reference's seeds 4–7 first, and the dated predictions for Stage 1.

## Stage 1 set up, 2026-11-05

- After review ("commit and continue"): the core of 17 readouts is fixed as in `observations.md`, and the Reference's seeds 4–7 walk first.
- Predictions 19–35 in `notes/06_characters/expectations.md`, section "Round h0311 / experiment 08", written and committed before the first walk.
- Configs in `configs/08_character_sheet/`, one per setting, each the h0111 Reference with one key changed and the old value noted on that line. `e08_reference.yaml` is the h0111 Reference unchanged (seeds 4–7 only; seeds 0–3 are `h0111_reference_s0`–`s3`).
- Batch: `scripts/hikes_e08.sh start` (a copy of `hikes_0111.sh` with its disk and `.git` watchdog), logs in `runs/hikes_e08.log` and `runs/e08_logs/`. All three tiers in one queue, tier 1 first, 102 walks; finished walks are skipped on restart. Capacity runs seeds 1–3 only (s0 are `h0111_eye_half_s0` and `h0111_eye_double_s0`).
- Batch started 2026-11-05 12:07, about 21 min per walk, three side by side: about 12 h for all 102.
- **Analysis code for Stage 1.** `sheet.py` now names the Stage 1 settings (`SETTINGS`) and lets a group take its seeds from more than one stem (the Reference: `h0111_reference` for seeds 0–3, `e08_reference` for 4–7; capacity: the h0111 eye-size walk for seed 0). Calibration stays the Stage 0 one (h0111 walks, seeds 0–3): rerunning `readouts.py` and `panel.py summarise` reproduced `calibration.csv` and the panel files unchanged. The lead rule's spread is now the Reference's range over the seeds compared, which is what it was in Stage 0. `matrix.py` writes `results/matrix.csv` and `matrix.png`: each setting's paired effect on the 17 core readouts in Stage 0 seed SDs (fixed units, chosen before any Stage 1 walk), with its verdict.

## Paused 2026-11-05 12:38: where Stage 1 stands and how to continue

- **Done:** `e08_reference_s4` (1,695 s). The batch was stopped by request at 12:38 with `scripts/hikes_e08.sh stop`; `e08_reference_s5` and `s6` had reached step 750 and `s7` had just started. A walk cannot resume, so these three walk again from step 0. Their unfinished folders stay in `runs/` until then; on restart the batch script moves each one to `runs/e08_partial/` before walking it again (added at the pause), so nothing is walked on top of old files. `runs/e08_partial/` can be deleted once the batch is through.
- **Not yet run on Stage 1 walks:** `readouts.py`, `panel.py score` / `summarise`, `matrix.py`. Nothing in `results/` uses an e08 walk yet; `readouts.csv` and `paired.csv` gained only the two h0111 eye-size walks (seed 0 of the capacity settings) and `matrix.csv` / `matrix.png` show Stage 0's Null and Bored.

**To continue**

1. `scripts/hikes_e08.sh start` — the remaining 101 walks, about 12 h (Reference seeds 5–7 first, then tiers 1, 2, 3). Finished walks are skipped.
2. As walks finish (any time, also while the batch runs): `.venv/bin/python analysis/e08/readouts.py`, then `.venv/bin/python analysis/e08/panel.py score` (resumable, about 20–40 s per walk and checkpoint) and `panel.py summarise`, then `.venv/bin/python analysis/e08/matrix.py`.
3. First check: prediction 19 (the Reference's seeds 4–7 against 0–3).
4. Report after Stage 1 in `observations.md` (Stage 1 section), with the matrix and a table against predictions 19–35, then stop for review before seeds 4–7 of the leads.

## 2026-11-05 13:41: Stage 1 resumed

- `scripts/hikes_e08.sh start`; the three unfinished Reference walks moved to `runs/e08_partial/` and walk again. 45 GB free.

## 2026-11-05 14:15: the Reference's seeds 4–7 (prediction 19)

- Walked in 1,326–2,002 s, slower than h0111 (swap; see below). At this pace the batch takes about 15 h, not 12.
- **Prediction 19 fails on taste.** Rhythm, returns, choice and held-out error: the mean of seeds 4–7 lies inside the range of seeds 0–3 on all nine, and the SD of the choice and returns readouts over eight seeds is within 30 % of Stage 0's. Taste: four of five readouts lie outside (snow/ice/cloud −0.14 against −0.49…−0.26; brightness, saturation, texture), all because of seed 6, whose snow/ice/cloud is **+0.83**, against −0.26 to −0.69 in the other seven seeds.
- **Why.** Seed 6's taste rests on one place: 119 of the 145 settled steps where its neighbours mixed bright and other tiles fall in its last place (from step 782, 47.1 °N 126.3 °E, Heilongjiang; little cloud on those tiles, so probably snow-covered fields), where it took the bright tile 68 % of the time. Before step 800 it never did. The selection differential compares a choice only with what was on offer, but averaging over steps lets one long place outweigh the rest of the walk, so landing luck comes back in through the weights.
- **Consequence for Stage 1.** The Stage 0 seed SD of the taste readouts is too small: snow/ice/cloud 0.19 in Stage 0, 0.46 over the Reference's eight seeds. Effects in Stage 0 seed SDs overstate taste, and four-seed taste leads will be more frequent by chance than the 9 % of finding 8. The core readouts stay as declared; for the report, a second version weighted per place (each place's mean differential, places averaged) is computed alongside and marked as added after seeing seed 6. The units of the matrix stay Stage 0's, and the report gives the eight-seed Reference SD next to them.
- The disk dropped from 52 to 43 GB free during the day, not from the project: about 4–6 GB of swap (three walks side by side), Time Machine local snapshots keeping tiles the cache evicts (the cache is at its 30 GB cap), and app updates. `runs/` is 1.9 GB, `.git` 156 MB.
- **The per-place version does not change it.** `selp_` (in `readouts.csv`, not a core readout) gives seed 6 +0.98 on snow/ice/cloud: its other settled places (ocean, Amazon, India) never offered bright tiles among the neighbours, so the one place is all there is. Seed 6 is not a weighting artefact. It met bright tiles in one place, snowy fields, and took them; the other seven met them as ice, cloud or mountain snow and turned them down. So the snow/ice/cloud readout depends on what bright terrain a walker happens to meet, which is landing luck of a kind the selection differential cannot remove. Over eight seeds the Reference avoids bright tiles in 7 (mean −0.25, SD 0.46). For Stage 1 this readout needs eight seeds before it says anything; its four-seed leads are read as weak.

## 2026-11-05 15:22–15:56: the Mac slept

- The Mac was unplugged and its lid closed at 15:22:58 and woke at 15:56:38 (`pmset -g log`). `caffeinate -i` prevents idle sleep only, not sleep with the lid closed on battery. The batch was not stopped: its three walks (`e08_surprise_s1`–`s3`, at steps 600, 200 and 200) were frozen and carried on after waking. A walk's random streams do not depend on time, so a pause changes nothing unless tile fetches time out on waking; their dropped candidates are checked when they finish.
- Saved at that point: 13 Stage 1 walks (Reference s4–s7, novelty only s0–s3, progress only s0–s3, surprise s0); panel scores for Reference s4–s7 and the two h0111 eye-size walks. Nothing to discard. `runs/e08_partial/` (the three walks cut off at the first pause) can be deleted once the batch is through.
- **Dropped candidates.** Every e08 walk so far dropped 0–11 candidates on the walker's 30 s fetch timeout (`steps.parquet`, `n_dropped`); the h0111 walks dropped none, except 3 in the double-size eye walk. Usually one slow tile dropped at a few steps in a row, one of about 8 candidates at those steps. This is the walker's designed behaviour and is logged; the walks are kept and the counts go in the report.
- **The tile cache overshoots its cap** (34.2 GB on disk against 30 GB): each process counts the cache from its own scan at start plus its own writes, so with three walks and the panel scoring fetching at once the total runs over by what the others add. Every new walk rescans and evicts back to the cap on its first write. This, with swap, explains most of the fall to 35 GB free.
- The three walks frozen by the sleep finished with 2, 2 and 3 dropped candidates, none near the steps where they were frozen (about 600, 200, 200). Kept.
- **First matrix rows, 16:30** (novelty only, progress only, surprise added; four seeds each; read in `results/matrix.csv`). Leads: 0, 7 and 4 of 17 (chance about 1.5). First reading, for the Stage 1 report: removing novelty takes away the returns (progress only: revisits beyond blind 0.05 against 0.18, top tile 0.21 against 0.42, and a Bored-like rhythm); removing progress changes nothing measurable; adding surprise brings a preference for texture and contrast among neighbours.
