# Brief: generation 2, the first turn of the recursion

*2026-11-16. Decisions: Moe, 2026-11-16 (four answers, quoted below). Runs unattended in the generation-1 pipeline (`scripts/g1_lib.py`), after the G1 latent walks and their readouts. Predictions: `notes/06_characters/expectations.md` 164–168, dated before any G2 package.*

## What

G2-curious and G2-null are trained on the paths of the G1 latent walks (`notes/brief_g1_latent_walks.md`): the curious wanderer's walk in G1-curious, and the Null wanderer's walk in G1-null. Fresh wanderers then walk G2. This is the recursion of the charter (milestone 5), one turn deep. The Null loop (Null walker, unweighted GAN) is the recursion without intrinsic motivation.

## Moe's decisions (2026-11-16)

1. **Generations:** "G2 only, then stop." The pipeline pauses after the G2 latent walks for review before G3.
2. **Training length:** "Same as G1: 3,840 kimg." The budget is inherited from G1's measurement (`gen/g1_gan.py inherit_budget`), not re-measured: same architecture, size and GPU, and alternating 400 kimg chunks. Kept snapshots are 960, 1,920, 2,880 and 3,840.
3. **Training set:** "Same rules as G1." These are the 10,000 tiles of each latent walk (start included) at 128 px, as rendered by the walk. G2-curious is weighted by interest at encounter, e = exp(I / τ) at ESS 0.5 N; G2-null is unweighted.
4. **Time rule for synthetic worlds:** "snapshot as time", in every generation. Waiting in G2 is the same z in G2's next kept snapshot. Walkers start fresh with the committed configs; the step is colour-calibrated; q = 0.10.

## Pipeline stages (after `latent_readouts`)

| stage | what | code |
|---|---|---|
| `g2_packages` | each G1 latent walk → `paths/g2/<cond>/` in the G1 package format. The render check re-renders 20 tiles from z and snapshot and accepts at most 2 of 255 difference, because the walk rendered offers in batches. | `scripts/g2_package.py` |
| `g2_datasets` | verification, weights and τ, zips | `gen/g1_gan.py datasets --gen 2` |
| `g2_budget` | budget and training mode taken from G1 | `gen/g1_gan.py inherit_budget --gen 2` |
| `g2_train` | alternating chunks, jobs `g2train_<cond>_<until>`, resumed exactly | `gen/g1_gan.py train --gen 2` |
| `g2_fid`, `g2_readouts` | as G1; tables go to `notes/gen2/gan/` | `gen/g1_gan.py fid/readouts --gen 2` |
| `g2_latent_walks`, `g2_latent_readouts` | fresh walkers in G2, readouts to `notes/gen2/latent/` | `agent/latent_walk.py --gen 2`, `analysis/gen1/latent_readouts.py --gen 2` |
| `final` | stop | |

Expected duration: about 2 h for the G1 latent walks, then about 0.1 h for packages and datasets, about 57 h of training, about 2 h of FID and readouts, and about 2 h of G2 latent walks. About 2.6 days in all.

## Set by hand, and left to emerge

| Set by hand | Left to emerge |
|---|---|
| one turn (G2); 3,840 kimg; N = 10,000; ESS 0.5 N; exp(I / τ); snapshots as time; q = 0.10; the colour-calibrated step | what each G2 makes of a GAN-made world; whether the curious loop drifts towards the apparatus or the planet, against the Null loop |
| G2 trains on 128 px renders of G1 (no 178 px archive window behind them) | how much of G1's character survives one generation |

## Tested before launch (2026-11-16, on test walks; outputs deleted)

- Test latent walks in G1 (60 steps per condition, GPU), then TEST packages with the render check passed (max difference 1 of 255), then TEST datasets for G2. τ was 2.77 at ESS 0.5 N on 61 tiles.
- A 1-kimg training run on the G2 test dataset with weights on finished.
- The supervisor loads the new stages; G1 behaviour is unchanged (every function's default is generation 1).

## For review (Moe)

- After G2: whether to continue to G3, and whether the step calibration in later generations should keep the real 15 km reference (as now) or use the previous generation's walk.

## Extension, 2026-11-17: generations 3 and 4, then the upscaler (Moe, 2026-11-17)

Moe's answers (2026-11-17, before leaving for a week): "G3 + G4, 3,840 kimg"; the Landsat 1 upscaler "after the last generation"; the calibration reference stays "the real 15 km step, always"; the time rule "keep as is" (four kept snapshots).

- **Stages** (`scripts/g1_lib.py`, `stage_gen`): `g3_*` and `g4_*` repeat the eight G2 steps, each generation built from the previous one's latent walks (`scripts/g2_package.py build <cond> --gen <g>`); manifests to `notes/gen<g>/packages/`, tag `g<g>-paths`.
- **`recursion_readouts`** (`analysis/recursion/readouts.py`): every generation against the real G1 package of its condition (recall, precision, nearest-sample spread, colour and texture statistics) and the collapse flag set by hand in prediction 170. Not fatal.
- **`upscaler`** (`scripts/upscaler.py all`): pairs from the walk cache (built on the CPU on 2026-11-17 during G2), training on the GPU after G4, held-out evaluation, figures; outputs labelled as learned. Not fatal.
- **Then `final`:** the pipeline stops for review.
- **Expected:** G2 ends about Thursday 2026-11-19 04:00, G3 about Saturday 2026-11-21 evening, G4 about Tuesday 2026-11-24 morning, the upscaler about Tuesday afternoon.
- **Predictions** 169–173 were dated 2026-11-17 13:00, before any G3 package.
- **Not covered by this run:** the four-seed replication (milestone 4) and a places-against-fragments comparison (RQ3) are outside this extension.

## Extension, 2026-11-24: generation 5 (Moe, 2026-11-24)

Moe's answer (2026-11-24, during the upscaler): "G5 at the same rules", that is, a walk through latent space plus GAN training once more.

- **Stages:** `GENS = (2, 3, 4, 5)` in `scripts/g1_lib.py`. The `g5_*` steps repeat the G2 steps: packages from the G4 latent walks (tag `g5-paths`), datasets, budget (inherited), training at 3,840 kimg, FID, readouts, latent walks, latent readouts.
- **The switch happens after `upscaler` is marked done**, so G5 never shares the GPU with the upscaler. Then the `recursion_readouts` and `final` markers are removed (pipeline state only), so the recursion readout reruns over G1–G5 and the run stops again at `final`.
- **Expected:** G5 packages and datasets about 13:00 on 2026-11-24, training to about Thursday 2026-11-26 21:00, FID and readouts about 22:00, latent walks about Friday 01:00, recursion readout right after.
- **Predictions** 174–178 were dated 2026-11-24 12:20, before any G5 package.

## Ended early, 2026-11-25 (Moe)

Moe, 2026-11-25 ~19:55: "End the generation", then "stop now, no readouts".

- **G5 training stopped at the latest snapshots:**
  - G5-curious at 2,252 kimg (`network-snapshot-002252.pkl`, written on stop at 19:59);
  - G5-null at 2,004 kimg (`network-snapshot-002004.pkl`, 18:27).
  - Kept snapshots at 960 and 1,920 kimg exist for both. Nothing was deleted.
- **No G5 FID, readouts, latent walks or recursion readout over G1–G5.** Predictions 174–178 are therefore not scored; they stay dated and open.
- **How it was stopped:**
  - the supervisor's stop file;
  - then `halt` set in `runs/g1/pipeline_state.json`, so any relaunch by the scheduled task exits without acting;
  - then `runs/g5/gan/curious/STOP`, which ends training cleanly at the next tick.
  - The scheduled task `eo_hike_g1` could not be disabled from this session (access denied); it stays enabled but halted.
- **To resume** (Moe's decision): remove `runs/g5/gan/curious/STOP`, clear `halt` in `pipeline_state.json`, then run the task. Training resumes from the snapshots. The `recursion_readouts` and `final` markers are still removed.
- **Incident before the stop:** at 18:09 the G5-null chunk to 2,000 kimg ended without an exit record (attempt 1). It was restarted from its snapshot (attempt 2) and finished at 18:27, with no kimg lost. Since then the GPU runs at a higher clock (1,815 MHz, 153 W, 87 °C, against about 1,200 MHz and 96 W before), and training was faster (about 21.9 s/kimg against 25.5). The cause was not found in the system log.