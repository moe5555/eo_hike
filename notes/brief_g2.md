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
