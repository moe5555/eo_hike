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
