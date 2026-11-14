# Brief: the first wanderers in a GAN's world (G1 latent walks)

*2026-11-14. Decisions: Moe, 2026-11-14 (four answers, quoted below). Interpretations where an answer left something open are marked **[default]** and listed under "For review". Runs automatically after the G1 GAN readouts (pipeline stages `latent_walks`, `latent_readouts`).*

## What and why

Each wanderer walks the world its own path produced: a curious wanderer walks G1-curious, a Null wanderer walks G1-null. This is the first step of the recursion (CHARTER, milestone 5): the discrete tiles a wanderer curated, turned into a continuous latent space by a GAN, walked again by intrinsic motivation. The latent walks are walks, not training: no generation-2 GAN is trained here.

## Moe's decisions (2026-11-14)

1. **Which walker:** "Fresh, same config." A new wanderer from random weights with the configs as committed (`configs/gen1/curious.yaml`, `configs/gen1/null.yaml`: two eyes, top-4, w_glance 1, temperature 0.5; the Null chooses uniformly; the same drive and radius rule).
2. **Place and step:** "z-sphere, calibrated." Positions are latents z on the sphere of radius √512. The eight compass offers lie in a random 2-D plane through z, at 45° to each other (rotated by θ ∈ [0°, 45°), as the compass frame), at an angle α set by the drive, the way the radius was. The angle range is calibrated once per GAN.
3. **Time:** "Snapshot as time." The time offer is the same z in the next kept training snapshot (960 → 1,920 → 2,880 → 3,840 kimg). Waiting means the world itself matures.
4. **Run mode:** "Queue, auto-start." Built and tested on the CPU while G1 trains; a pipeline stage after the GAN readouts; predictions dated before it runs.

## The world

- **Rendering:** G_ema of the snapshot at the clock, ψ = 1, constant noise (a latent always shows the same image in the same snapshot). 128 px, upsampled to the walker's 256 px by bilinear interpolation **[default]**: the walker's eyes are built for 256 px tiles, and the real tiles were 178 → 256 bilinear.
- **A tile** is a (z, snapshot) pair, with an integer key. Every compass step lands on a new z, so a new tile; a wait lands on the same z in a later snapshot, also a new tile.
- **The compass:** α comes from the drive exactly as the radius did (`agent/compass.radius`, r_min at a calm drive, r_max when bored, log-linear in between). It is mapped to an angle as α = α_min · (α_max / α_min)^u, with u = log(r / r_min) / log(r_max / r_min).
  - **α_max = 90°** **[default]**: an orthogonal latent is an independent draw, the latent analogue of a far jump.
  - **α_min is calibrated** so that a step at α_min changes a GAN tile as much, relative to that GAN's own random jump (90°), as a 15 km step changed a real tile relative to a jump between random tiles of the same package. With ρ = median change of 15 km moves (moves at r_min, in that condition's own package) / median change between random pairs of its tiles, α_min is the smallest angle at which the median change over random z and directions reaches ρ times the change at 90°. Measured on the GAN's last kept snapshot (3,840 kimg), 256 latents, 24 angles from 0.25° to 90°, log-spaced.
  - **The observer is colour character** (Moe, 2026-11-14): the mean and spread of each CIR channel of the 128 px render. Pixel layout (32 × 32 × 3, L2) is computed and logged in `calibration.json`, but not used. On test snapshots it gave about 74° (curious) and 36° (Null): adjacent 10.7 km tiles barely overlap, so their pixel layouts differ almost as much as random tiles (ρ 0.87 and 0.57). The colour observer gave ρ 0.33 and 0.22, and α_min 17° and 14° on those test snapshots.
  - Matching ratios rather than absolute distances lets one rule serve both GANs, whatever range each GAN's images span.
  - Both angles are logged; α_min is set by hand through this rule.
- **The time offer:** exists while a later kept snapshot exists. It comes through with probability **q = 0.10** (from the config, the same for the Null). It is scored and drawn like any offer.
- **Start:** a seeded z (the walk's seed, 0, for both conditions) at the first kept snapshot (960 kimg).
- **The end:** at **N = 10,000 unique tiles** (start tile included, as the packages count), or the 40,000-step guard. When the clock reaches the last snapshot (3,840), the time offer disappears and the walk goes on in that world until N **[default]**. There is no lingering rule: it was tied to 1977.
- **Not carried over:** the held-out set and the forgetting set (real tiles from the archive store); fetch timeouts (rendering is local); quirk detectors (deferred on GAN images, Moe).

## The walker

`agent/latent_walk.py`: the step loop of `agent/walk.py` for the two-eye compass walker, re-implemented for this world with the same components and order:
- `TwoEye` scoring and training;
- the drive (interest_long, warm-up 50 steps, drive_start 50);
- the radius rule;
- softmax at temperature 0.5 (curious) or uniform choice (Null);
- the thinned time offer;
- re-embedding every 100 steps;
- the same named random streams.

The walker code itself is unchanged. Each walk runs in `.venv-sg`, because the GAN code needs it: torch 2.14 rather than the walks' 2.11, eyes on CPU with 3 threads, G on the GPU (about 0.5 s per step in a GPU test, about 1.7 s with G on CPU). Pipeline: stage `latent_walks` calibrates both GANs, then runs both walks concurrently; stage `latent_readouts` follows; neither is fatal.

Logged:
- per step, the walker's usual fields (components, shares, p_chosen, drive, α, kind, clock snapshot);
- per offer, its interest components and colour statistics of its 128 px render (labelled as such);
- every visited tile as a 128 px PNG, with its z and snapshot (re-renderable);
- checkpoints every 1,000 steps (resume). Resume is exact: a test walk crashed at step 20 and resumed matched an uninterrupted one in keys, kinds, interest, angles and z.

## Readouts (`latent_readouts`)

- **Time:** waits per snapshot, steps spent in each snapshot, clock against step (curious against Null).
- **Movement:** α over the walk and the drive; the angle from the start, and the median angle between positions 1, 10, 100 and 1,000 steps apart. In 512 dimensions the angle from the start saturates near 90° within about 100 steps, so the lags carry the information.
- **Taste:** offered against chosen colour and texture statistics (brightness, black share, white share, green-band-dark, gradient, row roughness), curious against Null, the same as the G1 readouts.
- **Contact sheets** of the visited tiles every 500 steps; the last 50 steps of each walk.
- **Interest decomposition** at the curious choice (glance, grid, progress), against the real walks.

## Set by hand, and left to emerge

| Set by hand | Left to emerge |
|---|---|
| fresh walkers with the committed configs; q = 0.10; N = 10,000 | where each walker goes in its GAN's space; whether and when it waits for a later snapshot |
| the z-sphere, the 8-in-a-plane compass, α_max = 90°, α_min calibrated to a 15 km step | how far it travels; how the drive moves α |
| snapshots as time (4 kept snapshots); no lingering | what it chooses to look at, against the Null |

## Predictions

Written in `notes/06_characters/expectations.md` (158–163) before any latent walk.

## For review (Moe)

- **Defaults taken:** bilinear 128 → 256; α_max = 90°; after the last snapshot the walk continues to N without a time offer; no lingering; start at z of seed 0 for both conditions.
- **Not done:** training a generation-2 GAN on these walks (the recursion's next turn); a random-sampling baseline in latent space other than the Null wanderer.
