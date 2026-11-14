# GAN generation 1: G1-curious (weighted) against G1-null (unweighted) — report (DRAFT, 2026-11-14: training running; results not yet written)

Brief: `notes/brief_gan_g1.md`. Predictions 152–157: `notes/06_characters/expectations.md`, with the Phase A measurements appended 2026-11-14 01:52. Inputs: the path packages at tag `g1-paths` (`notes/gen1_report.md`). Code: `gen/g1_gan.py`, with StyleGAN2-ADA (NVlabs `d72cc7d`) and `scripts/stylegan2ada_g1.patch`; tag `g1-start`. Outputs: `runs/g1/gan/` (pickles, samples, videos; outside git) and `notes/gen1/gan/` (tables and small figures). Device: the PC, a Quadro RTX 5000 (16 GB). Training ran in the S4U-scheduled pipeline (`scripts/g1_pipeline.py`).

## Short version

*(to be written when training and readouts are done)*

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

*(from `notes/gen1/gan/`: readouts.json, colour_texture.csv, weights_vs_quirks.csv, fid.json, budget.json, ess.json; figures: samples_contact256, closest32, heaviest64 / lightest64)*

## Findings

*(each with what was set by hand, the era confound where it applies, and its RQ and chapter)*

## Against the predictions (152–157)

*(152 and 153 can be scored from the weights now; 154 is deferred with the quirk observer; 155–157 after the readouts)*

## For review

*(to be written)*
