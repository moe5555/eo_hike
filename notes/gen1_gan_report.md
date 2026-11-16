# GAN generation 1: G1-curious (weighted) against G1-null (unweighted) — report (2026-11-16)

Brief: `notes/brief_gan_g1.md`. Predictions 152–157: `notes/06_characters/expectations.md`, with the Phase A measurements appended 2026-11-14 01:52. Inputs: the path packages at tag `g1-paths` (`notes/gen1_report.md`). Code: `gen/g1_gan.py`, with StyleGAN2-ADA (NVlabs `d72cc7d`) and `scripts/stylegan2ada_g1.patch`; tag `g1-start`. Outputs: `runs/g1/gan/` (pickles, samples, videos; outside git) and `notes/gen1/gan/` (tables and small figures). Device: the PC, a Quadro RTX 5000 (16 GB). Training ran in the S4U-scheduled pipeline (`scripts/g1_pipeline.py`).

## Short version

- **Both GANs trained to 3,840 kimg** (2026-11-14 01:54 to 2026-11-16 09:21, about 55 h), in alternating 400 kimg chunks.
  - There was one spurious restart and no kimg were lost.
  - FID fell at every kept snapshot (curious 43.0 → 17.8, null 53.0 → 23.2) and had not levelled off by the end. FID is used as a training-health signal only.
- **G1-curious covers its training set less than G1-null** (32 × 32 pixel space): recall 0.096 against 0.182, precision 0.239 against 0.518.
  - The weighting does not explain the gap. Against the weighted reference, curious's recall is 0.083.
  - The curious package is more heterogeneous within each tile (row roughness 1.58 against 0.95; NIR spread 30 against 20), which may make it harder to cover. A hint: one path and one seed each, and the era confound is small.
- **Neither GAN copies its training set wholesale**, but the null sits closer to it.
  - Median distance from a sample to its nearest training tile is 1.05 × the training set's own median for curious and 0.89 × for null.
  - Curious has one near-copy (seed 411, distance 0.09 against a training p1 of 1.69).
- **The apparatus survives selectively (colour and texture statistics, labelled as such):**
  - scan-line banding is kept or slightly amplified (row roughness of samples against training: curious 1.66 against 1.58, null 0.98 against 0.95);
  - black fill pixels almost vanish (curious 0.04 % against 0.27 %, null 0.01 % against 0.49 %);
  - the black green band of 1977 is thinned to 0.30 × its weighted share in curious (0.9 % of samples against 3.1 %) and to 0.11 × in null (0.3 % against 2.8 %).
- **Predictions:** 152 partly right, 153 mostly wrong, 154 deferred, 155 wrong, 156 partly right, 157 mostly wrong.

## What was run

- **Inputs:** both packages verified as GAN input (checksums, N = 10,000, start lists, interest components, the render check passed). Nothing was repaired. Fill, stripes, saturation, cloud, night and the black green channel of 1977 are all in.
- **Datasets:** `dataset_tool.py`, unconditional, 128 × 128. Every zip image was checked pixel for pixel against its package tile.
- **Weights (curious):** e = exp(I / τ) per encounter. A walk's start tile gets the median e. Each tile sums its encounters, and weights are normalised to mean 1.
  - τ is solved for ESS = 0.5 N: **τ = 3.665**.
  - With encounter counts alone the ESS would be 0.836 N, so revisits use 16 % of the budget before interest acts.
  - The top 1 % of tiles hold 0.056 of the weight, the top 10 % hold 0.237; max/median is 69.9.
  - Null: weight 1 for every tile.
- **Training:**
  - StyleGAN2-ADA cfg auto at 128 px (the repo's recommendation for the resolution): batch 32, γ = 0.1024, mapping 2 layers, fmaps 0.5;
  - ADA target 0.6, augpipe bgc, mirror off;
  - seed 0 for both, the same seeded weighted sampler code for both (Null with all weights 1);
  - **3,840 kimg each**, with snapshots every 40 kimg; kept at 960, 1,920, 2,880 and 3,840.
- **Alternating chunks of 400 kimg** (the brief's fallback). Throughput probes on the real datasets (`runs/g1/gan/probe.json`):

  | setup | s/kimg per run | wall s per kimg of both runs |
  |---|---|---|
  | one run alone | 25.4 | 50.9 (alternating) |
  | both concurrently | 88–91 | about 90 |
  | both concurrently, batch split 16 per round | no first tick in 45 min | n/a |

  - The run that is behind trains next. Each chunk resumes from the last snapshot pair: networks plus optimiser states, kimg, tick, batch index, augment p and RNG.
  - Resume is exact. In Phase A, and in a chunk test on the real dataset, Adam's step counters and the batch index equalled an uninterrupted run (`runs/g1/phase_a/`).
  - **One spurious restart (2026-11-14 19:14):** Windows reused a finished chunk's pid for the next chunk's process. The supervisor took the old job for alive and stalled, and killed the new chunk (curious, to 1,600 kimg) about a minute in. It resumed from snapshot 1,204 (attempt 2), so no kimg were lost or repeated past the snapshot. Fixed in the supervisor: a job counts as alive only with no exit record since its start and a process created when it started.
- **Budget:** datasets 0.06 h + training 56.8 h + readouts allowed 2.0 h ≤ 60 h, at 25.67 s/kimg per run and 53.3 wall seconds per kimg of both.
  - The GPU ran at a 1,200 MHz core clock (2,100 max) and about 95 W of 230 W throughout, probably a driver power setting. It was not changed; the budget was measured at this speed.
- **After training:**
  - fid50k_full on the kept snapshots, as a training-health signal only;
  - 5,000 samples per GAN (seeds 0–4,999, ψ = 1);
  - memorisation and precision/recall in 32 × 32 pixel space, against the unweighted training set and, for curious, a weighted reference of equal size;
  - colour and texture statistics (labelled as such);
  - film assets.
  - The quirk observer on samples is deferred (Moe).

### Set by hand, and left to emerge

| Set by hand (premises) | Left to emerge |
|---|---|
| N = 10,000; q = 0.10 (the walks) | which tiles each package holds |
| ESS target 0.5 N; the weight mapping exp(I / τ); the start tile at the median e | τ, and how the weight concentrates (top 1 % / 10 %) |
| StyleGAN2-ADA cfg auto, 128 px, ADA target 0.6, bgc, mirror off, seed 0 | the final augment p of each run; what each GAN produces |
| 3,840 kimg (from the measured rate and the 60 h budget); alternating chunks of 400 kimg | how far each GAN gets in that time |
| the final snapshot counts (never "best FID") | everything in the readouts |

**The era confound** (stated next to every comparison below): the two packages differ by curation and by era. Generation 1 found the era difference small (`notes/gen1_report.md`, finding 7). Both are one path per condition and one training seed per run, so every difference between the GANs is a hint.

## Tables

All from `notes/gen1/gan/`: `readouts.json`, `colour_texture.csv`, `fid.json`, `budget.json`, `ess.json` and `weights_vs_quirks.csv`. Figures: `*_samples_contact256.jpg`, `*_closest32.png`, `curious_heaviest64.png` and `curious_lightest64.png`. Samples are seeds 0–4,999 at ψ = 1. The observer is 32 × 32 × 3 pixel space, L2, with no pretrained network.

**Training health (FID, fid50k_full against each run's own training set; not comparable across runs):**

| kimg | 960 | 1,920 | 2,880 | 3,840 |
|---|---|---|---|---|
| G1-curious | 43.0 | 25.7 | 20.6 | 17.8 |
| G1-null | 53.0 | 40.5 | 29.9 | 23.2 |

**Memorisation and diversity (32 × 32 pixel space):**

| | G1-curious | G1-null |
|---|---|---|
| final ADA p | 0.161 | 0.141 |
| median sample → nearest training tile, ÷ training set's own median | 1.05 | 0.89 |
| samples closer than the training set's p1 | 0.3 % | 0.08 % |
| precision / recall against the unweighted training set (k = 3) | 0.239 / 0.096 | 0.518 / 0.182 |
| precision / recall against the weighted reference (equal distinct tiles) | 0.261 / 0.083 | — |
| median distance to the heaviest / lightest 10 % of tiles | 6.74 / 6.39 | — |

**Colour and texture statistics** (of the 128 px renders, labelled as such: not the quirk detectors):

| | brightness | black share | white share | green band dark | row roughness | grad x | NIR spread |
|---|---|---|---|---|---|---|---|
| curious training (unweighted) | 106.5 | 0.27 % | 0.31 % | 2.5 % | 1.58 | 6.54 | 30.3 |
| curious training (weighted) | 106.1 | 0.34 % | 0.31 % | 3.1 % | 1.63 | 6.80 | 31.2 |
| curious samples | 105.6 | 0.04 % | 0.34 % | 0.9 % | 1.66 | 6.90 | 30.9 |
| null training | 120.5 | 0.49 % | 1.08 % | 2.8 % | 0.95 | 4.10 | 20.2 |
| null samples | 119.5 | 0.01 % | 0.85 % | 0.3 % | 0.98 | 4.08 | 18.8 |

## Findings

Each finding is one path per condition and one training seed per run, so each is a hint. **The era confound:** the packages differ by curation and by era, and generation 1 found the era difference small (`notes/gen1_report.md`, finding 7).

1. **Both runs were healthy and unconverged at the budget.**
   - FID fell at every kept snapshot. The final snapshot counts, not the best FID.
   - Set by hand: 3,840 kimg from the 60 h budget. Emerged: the curves.
   - *RQ3; ch. 4 (method).*
2. **The curious GAN covers its world less.**
   - Recall is about half the null's, and precision too.
   - The weighted reference does not close the gap (recall 0.083), so it is not the weighting alone.
   - A candidate cause is the package itself: curious tiles are rougher and more varied within the tile (row roughness 1.58 against 0.95, NIR spread 30 against 20). This is not tested.
   - Set by hand: ESS 0.5 N, exp(I / τ), the 32 px observer.
   - *RQ3; ch. 4, 8.*
3. **The null sits closer to its training tiles.**
   - Median ratio 0.89 against 1.05.
   - Curious has one near-copy (seed 411 to tile `657U_871R_19760526`) and 0.3 % of samples below the training p1.
   - Neither copies wholesale.
   - *RQ3; ch. 4.*
4. **The apparatus survives selectively.**
   - Banding along rows, a texture, is kept or slightly amplified by both GANs.
   - Missing values are smoothed away: fill (black pixels) and the black green band of 1977.
   - Curious keeps about 3 × more of the 1977 band, relative to its training share, than null does (0.30 × against 0.11 ×).
   - Set by hand: none of the GAN's choices touch quirks; the statistics are colour statistics, not the deferred detectors.
   - *RQ2/RQ3; ch. 6, 8.*
5. **Visual, not measured (from the inspections of 2026-11-15/16).**
   - At ψ = 2 the curious GAN's extremes run to flat yellow (the band colour) and scan-line texture, and the null's to fill-like black bars, magenta striping and snow.
   - k-means regions of the final w-spaces show the same: curious has a yellow region and a striped region among 8, null a dark-water and a magenta-striped one.
   - This is a lead for the quirk observer, not a result.
   - *RQ3; ch. 8, 9 (film).*

## Against the predictions (152–157)

152 and 153 were scored on 2026-11-16 from the weights (`runs/g1/gan/ess.json`, `notes/gen1/gan/weights_vs_quirks.csv`), and 155–157 from the readouts.

| # | predicted | measured | verdict |
|---|---|---|---|
| 152 | τ = 2–4.5; top 10 % hold 0.24–0.32 of the weight; top 1 % hold 0.05–0.08; max/median 20–45 | τ = 3.665; top 10 % 0.237; top 1 % 0.056; max/median 69.9 | **partly right**: τ and the top 1 % in range; the top 10 % sits just under the range (0.237); max/median wrong, the tail is heavier than predicted |
| 153 | the heaviest 64 are darker and more striped than the package, and not cloudier | heaviest 64 against the package (unweighted): brightness 112.9 against 106.0; stripes 0.121 against 0.067; cloud 0.214 against 0.153 | **mostly wrong**: more striped (right), but brighter and cloudier (wrong). The top 10 % by weight do match the prediction: brightness 105.3, stripes 0.078, cloud 0.144. So the extreme tail is apparatus-heavy (fill ×4, night ×4, saturation flags 0.24 against 0.14), while the broad top decile is the predicted "clear, darker, striped". |
| 154 | quirks in samples | — | deferred (the quirk observer on samples, Moe) |
| 155 | G1-curious makes green-less tiles at 0.5–2 × their weighted share; G1-null makes none | curious 0.9 % against 3.1 % (0.30 ×); null 0.3 % against 2.8 % (0.11 ×) | **wrong** on both counts. Both GANs thin the band; the direction (curious keeps more than null) is right. |
| 156 | curious has lower recall than null; against the weighted reference at least half the gap disappears | 0.096 against 0.182; weighted reference 0.083 | **partly right**: lower recall, yes; the gap does not close, it widens |
| 157 | final ADA p 0.2–0.6 for both, higher for curious; neither copies (median NN ≥ the training set's own median); curious closer to its heaviest than its lightest tiles | p 0.161 and 0.141; median ratio curious 1.05, null 0.89; curious 6.74 to the heaviest and 6.39 to the lightest | **mostly wrong**: higher for curious (right), but below the range; curious doesn't copy, while null's samples sit below the training median (0.89); curious sits closer to its lightest tiles |

**Why the misses:**
- 155 assumed GANs reproduce rare whole-image colour casts; they smooth them toward the bulk.
- 156 assumed the weighting narrows curious; the gap is there without it, so the package's heterogeneity is the likelier cause.
- 157's p range came from earlier runs with smaller sets.

## For review

- **The quirk observer on samples** (prediction 154) is still deferred. Findings 4 and 5 are colour statistics and visual leads that it would test.
- **Unconverged:** FID was still falling at 3,840 kimg. If the GANs matter for chapter 8 beyond this prototype, a longer run would change the samples.
- **Near-copy:** curious seed 411 is near tile `657U_871R_19760526`. Check it in `notes/gen1/gan/curious_closest32.png`.
- **Pixel-space precision and recall are crude.** Read them relative to each other, not as absolute coverage.
- **Generation 2 has started** from these GANs (Moe, 2026-11-16; `notes/brief_g2.md`). The G1 latent walks are running now.
