# Decisions

Every non-obvious choice, the alternative rejected, and why. Findings from actual
runs are appended at the end as they happen.

## Archive

**Debug on SSL4EO-S12 v1.1's validation split, real runs on Major TOM thumbnails.**
Rejected: EuroSAT as the debug set (no coordinates, no dates, so the geo/time code
would never run before the real archive); SSL4EO-S12 train shards as the real archive
(every location is within 50 km of a large city, and the user wants an archive that
covers more than cities). Major TOM is a uniform 10 km grid, so a random sample is a
sample of the land surface by area. Full survey in `datasets.md`.

**RGB, not multispectral.** The budget ("30k–60k chips, ~5 GB") is only reachable
with 8-bit RGB. Both archives keep the multispectral bands reachable for the same
chip IDs, so this is reversible. Consequence: the EO encoder must accept RGB.

**Chips are materialised as PNG at ingest.** Rejected: reading from the archive's
native format (zarr-in-tar, remote parquet) at embed time. PNG is lossless, every
archive ends up looking the same to the rest of the pipeline, and the sequence images
are already on disk. Cost: one copy of the archive (~3 GB for 40k chips).

**All four seasons are separate chips** (user's choice). Config `dataset.seasons: one`
picks one season per location deterministically (md5 of the sample id) if wanted.

**Major TOM: land cells only, one fragment per grid cell, cloud ≤ 10 %, nodata = 0,
tiles with more than 20 % black pixels dropped.** `land_only` uses the 1 km
`global-land-mask` raster on the cell centre; see finding 1 below for why. Cells imaged twice would be near-duplicates. Black
tiles are swath edges, not places. Tiling 4×4 gives 267 px chips (2.67 km), close to
SSL4EO's 264 px, so the two archives are comparable.

## Encoder

**DOFA ViT-B/16 (torchgeo `DOFABase16_Weights.DOFA_MAE`) as the EO encoder.**
Rejected: the SSL4EO ViT-S/16 weights (need 13-band L1C input, cannot take RGB);
ResNet-50 RGB weights (a CNN has no patch tokens, and Phase 2 needs them). DOFA is
wavelength-conditioned, takes RGB with the wavelengths 0.665/0.560/0.490 µm, and is a
ViT with 16 px patches, so a 224 px input yields a 14×14 patch grid for the heatmap.

**CLIP ViT-B/32 (OpenAI weights via open_clip)** as mandated. Rejected: HF
`transformers` for CLIP, heavier dependency for the same weights.

**Global embedding = mean of the 196 patch tokens, then LayerNorm, L2-normalised.**
This is DOFA's own `global_pool=True` convention. Rejected: the cls token. The
released checkpoint contains no weights for the final norm on the cls path (torchgeo's
loader refuses that configuration), so the cls token would pass through an untrained
LayerNorm. Recorded in `embed_meta.json`, so a change is visible.

**Embeddings are centred on the archive mean and renormalised (`encoder.center`,
default on).** Finding 2 below: without it, every DOFA embedding lies in a cone so
narrow that all cosine distances are ~0.02 and the softmax is uniform. Rejected:
scaling the temperature down to match (hides the problem and makes T unreadable);
whitening/PCA (more machinery, and makes the embedding depend on the archive even
more strongly). Centring is one vector, stored next to the embeddings.

**Preprocessing: resize to 224 (bicubic), scale to [0, 1], normalise with ImageNet
mean/std.** DOFA was pretrained with per-dataset statistics that are not shipped with
the weights; ImageNet statistics are the documented default for its RGB use. The
exact string is in `embed_meta.json`.

## Index

**Exact `IndexFlatIP` on unit vectors.** Rejected: IVF/HNSW. Approximate search adds
a second source of non-determinism and buys nothing at 10⁴–10⁵ vectors.

**Novelty is computed in numpy, not read off the index.** The index is used only to
*find* the k neighbours; the scores are recomputed from the embeddings array. This
keeps the score independent of FAISS's internal float ordering.

## The agent loop and its defaults

| Dial | Default | Why this value | What changes if you move it |
|---|---|---|---|
| `k_neighbours` | 50 | Large enough that the local neighbourhood is not exhausted after a handful of visits (with 4 seasonal siblings per location, 50 neighbours ≈ 12 distinct places). Small enough that "local" still means something at 40k chips (0.1 % of the archive). Measured (finding 5): k barely moves mean novelty (0.74–0.76) but sets how often a random jump wins: 157 of 300 steps at k = 10, 75 at k = 50, 18 at k = 200. | Smaller: jumps win most steps and the walk loses locality. Larger: jumps almost never win; the walk crawls along the neighbour graph. |
| `m_random` | 5 | One in ten candidates is a jump: enough that an exhausted region is escaped within a few steps, few enough that most steps are local. | 0 makes the agent trapped once its region is used up. |
| `j_history` | 15 | Averaging over the 15 nearest history entries makes the score robust to a single coincidental near-twin while still rewarding distance from the *cluster* of things seen. Lehman & Stanley used k = 15 in the original paper. Measured: mean novelty scales with j (0.61 at j = 1, 0.75 at 15, 0.85 at 50) because averaging over more, farther entries raises the number; the *ranking* of candidates changes less. | 1: a single similar past chip vetoes a candidate; scores become spiky. Large: novelty tends towards distance-from-the-mean and stops discriminating. |
| `temperature` | 0.05 | Measured, not guessed (finding 3): on centred DOFA embeddings the gap between the best and second-best candidate averages 0.033 and best-to-15th 0.125. At T = 0.05 the best candidate wins 17–22 % of steps and the top three 30 %; at the brief's 0.1 the best wins 8 % and the median chosen rank is 15 of 55, i.e. nearly a random pick among candidates. 0.05 is the middle of the useful range 0.02–0.1. | 0.02: best wins about half the time, walk is more global (more jumps win). 0.1–0.5: increasingly a random walk over the candidate set; mean novelty falls from 0.75 to 0.62. |
| `max_steps` | 300 | Brief. | |
| `boredom_window` | 20 | Long enough that a single jump does not reset it, short enough that a run ends within ~20 steps of going flat. | |
| `boredom_threshold` | 0.4 | On the 8.7k-chip debug archive the running mean plateaus near 0.65 after 300 steps and only reaches 0.40 after ~3,000 steps (a third of the archive visited). 0.4 therefore means "stop when the walk has genuinely used up the archive"; in a 300-step run on a 10k–40k archive it will not fire and `max_steps` ends the run. Finding 4 explains why that is the honest default. | Higher (0.6): fires within ~200 steps on this archive, before the walk has explored much. | |

**Per-agent RNG seeded with `(seed, agent_id)`** via `numpy.random.default_rng`.
Rejected: one shared generator (agent 1's walk would depend on agent 0's length).

**Step 0 is logged** with null novelty. Rejected: omitting the start chip from the
log (the sequence folder and the log would disagree about what image 0000 is).

**Floats rounded to 6 decimals in the log.** Byte-identical logs across runs need a
fixed text form; 6 decimals is far beyond what any downstream mapping uses.

## Taste

**A taste vector (`agents.taste`, off by default).** The user's idea (2026-09-18): the
hiker keeps a running average of the embeddings that struck it hardest and is drawn
towards things that resemble it. Implemented as the simplest version:

- `taste` is a unit vector. `init: first` sets it to the start chip's embedding;
  `init: zero` leaves it empty until the first strong encounter sets it.
- After each step, if the chosen chip's novelty is at or above `threshold`, the taste
  moves: `taste <- normalise((1 - alpha) * taste + alpha * novelty * e)`. The strike
  strength (novelty) scales the step, so a harder strike moves taste further. Weak
  encounters leave it untouched.
- Selection scores every candidate as `novelty + weight * cos_sim(candidate, taste)`.
  `novelty` in the log stays the pure Lehman-Stanley quantity; `rank_among_candidates`
  is by the combined score, since that is what the choice was made from.
- `weight: 0` reproduces the taste-less walk chip for chip (tested and re-run:
  `runs/20260918-094014_*_regress` matches the 2026-09-17 final run).

Rejected: using taste as the retrieval query instead of the current chip (would break
the locality of the walk entirely; can be added as a second mode later). Rejected: a
forgetting/decay on taste independent of encounters (the user asked for update-on-strike
only).

## Phase 2: the patch-novelty heatmap

**Patch tokens come from the same forward pass that makes the chip embedding.** DOFA's
pooled path is *mean of the 196 patch tokens, then LayerNorm*. `encode_patches` takes
the tokens before the mean, applies that same LayerNorm to each, and L2-normalises.
Checked: the mean of these per-patch vectors has cosine 1.000 with the chip embedding
on every chip tried, so the patches live in the space the chip vector is the average
of. Rejected: taking tokens from an earlier block (more local, but not the space the
agent decides in).

**Patches are centred like chips, with their own mean.** The mean patch vector over a
seeded sample of 256 archive chips (50k patches) is cached as
`patch_mean_<encoder>.npy` next to the embeddings. Rejected: reusing the chip mean
(a different quantity; the patch cloud is wider than the chip cloud) and the walk's own
patches (would make one run's heatmap depend on which chips it happened to visit).

**The bank is every patch of every chip visited so far, and the score is the same
formula as the agent's.** `j_patches = 15` mirrors `j_history`; a chip's 196 patches
are scored against a bank that grows by 196 per step (58,800 rows by step 300; well
under a second per step on the GPU). Step 0 has no bank and gets NaN.

**Colour scale is per run, not per chip.** Tint starts at the 75th percentile of all
patch scores in the run and saturates at the 98th; alpha scales with the score so
cold patches show the plain image. Rejected: per-chip min-max (every chip would show a
hot spot, including the ones where nothing is new) and a 2nd-percentile floor (first
attempt: nearly every patch was tinted and inferno's oranges vanished into desert).
`cool` (cyan to magenta) is the colourmap because nothing on the ground is magenta.

**Sidecar, not log.** Per-patch scores go to `patch_novelty_agent_<id>.npz`;
`log.jsonl` is untouched so the byte-identity acceptance test still holds.

**Only DOFA has patch tokens today.** CLIP's image embedding is a projection of the
cls token; its patch tokens exist but are not in the projected space. The stage
raises a clear error for it (and `--stage all` skips with a message).

## The dream (generated epilogue)

**The brief's "no image generation" is overridden, as an epilogue only** (user
decision 2026-09-18). The generated image never enters the archive or the history,
`log.jsonl` is untouched, and `dream.enabled` is off by default. Rejected: letting the
agent continue walking from its dream (the user chose the epilogue reading).

**The prompt is the agent's score, not text.** Sampling is steered by the gradient of
the agent's own selection score (novelty against its history, plus the taste term if
the run had one) computed through the same DOFA encoder and the same centring as the
archive embeddings. Rejected: a target embedding rendered by an embedding-conditioned
decoder (needs an adapter trained on top; and someone has to choose the target) and a
text prompt written by a narrator LLM (brings language in before Phase 3 intends).

**Stable Diffusion 1.5 + LoRA, empty prompt.** SD 1.5 in fp16 with gradient
checkpointing fits the 8 GB laptop GPU at 256 px; SDXL does not. LoRA rank 8 on the
attention projections; base weights frozen. Every chip is trained under the empty
prompt "" so the generator has a single condition ("a chip from this archive") and no
text ever varies. Latents are precomputed once through the frozen VAE (`latents_sd15_256.npy`,
70 MB) with rotation/flip augmentation on the latent. Rejected: a satellite-pretrained
diffusion model (less ours, weights and licence to verify) and training from scratch
(days, lower fidelity). Licence: CreativeML OpenRAIL-M.

**Guidance mechanics.** DDIM, eta 0, no classifier-free guidance (there is no text).
At each step the predicted clean latent is decoded, scored, and moved by a step of
fixed relative size (`guidance_scale` x the latent's norm, along the normalised
gradient) within a noise window (`guidance_window`, default 0.9 to 0.2 of the noise
schedule: not at the very start, where the estimate is mush, and not at the very end,
where it would only add texture). The UNet's prediction is treated as constant in
the gradient; backprop runs through the VAE decoder and DOFA only, which is what keeps
this inside 8 GB. Rejected: backprop through the UNet (does not fit), and a guidance
step proportional to the raw gradient (its scale depends on the score's, which is tiny).

**Guidance is scored over random views, strongly, early.** First runs (finding 12)
showed that a plain pixel gradient through DOFA finds adversarial noise: the score
rose while the image did not change. The objective is therefore averaged over four
random rotation/flip/crop views of the decoded estimate (`guidance_views`), applied
with two iterations per step at 1.5 x the latent norm, only while the noise fraction
is between 0.95 and 0.4. Rejected: the gentle first settings (0.1, one view, window
0.9 to 0.2), which were measurably adversarial.

**Measured, with a control and a ceiling.** Each saved dream is re-encoded through the
ordinary `encode` path and scored like a chip; the same seed without guidance is scored
too; and the most novel unvisited real chip is recorded. Without these three numbers
side by side a "novel" dream would be an assertion.

## Stop conditions

`max_steps`, `boredom` (running mean over `boredom_window` < `boredom_threshold`),
and `exhausted` (no unvisited candidate at all; only happens on tiny archives). The
reason is recorded per agent in `summary.json`.

## Findings from runs

**1. A uniform sample of Major TOM is about half open ocean (2026-09-17).** The
first 30-fragment sample (`docs/img_majortom_sample.png`) had 15–17 chips of
featureless sea and 3 of sea ice. Sentinel-2 acquires over water too, and the grid
is uniform by area, so this is simply what "the Earth by area" looks like. It would
make a walk that is mostly grey water. Fix: a land mask on the cell centre
(`land_only: true`), which reduces eligible fragments from 1.72 M to 1.14 M and keeps
coasts, lakes and ice sheets (`docs/img_majortom_sample_land.png`). Antarctica and
Greenland remain, roughly a tenth of chips; `lat_min: -60` removes Antarctica if
wanted. Nothing else was tuned.

**2. Raw DOFA (and CLIP) embeddings are degenerate for novelty search; the first run
was a random walk.** With the raw mean-pooled DOFA features the archive-mean vector
has length 0.988 (1.0 would mean every chip identical); random pairs are 0.02 apart,
nearest neighbours 0.004. Every candidate scored ~0.01, the softmax at T = 0.1 was
uniform (chosen ranks 7, 48, 5, 43, ...), and both agents "got bored" at step 20 only
because 0.01 < 0.05. CLIP raw is the same (mean length 0.889). The *structure* was
fine all along: seasonal siblings sit at 0.4x the random distance under both
encoders. Subtracting the archive mean and renormalising spreads random pairs to a
median distance of 1.02 and nearest neighbours to 0.21, and the sibling ratio is
unchanged (0.38). All defaults were measured after centring.

**3. Temperature.** See the table. The brief's 0.1 gave a median chosen rank of 15
out of ~55 candidates. 0.05 is the new default; 0.02 is "decisive", 0.1 "drifting".
A side effect measured in the sweep: lower T produces *more* random jumps (112 at
T = 0.01 vs 38 at T = 0.5), because a jump candidate is usually the most novel thing
on offer and a colder softmax picks it.

**4. Boredom does not happen in 300 steps on an 8.7k-chip archive, with or without
jumps.** The running mean declines from ~1.0 to ~0.65 in the first 100 steps and then
creeps down (0.60 at 500, 0.52 at 1,000, 0.43 at 3,000). Turning jumps off
(`m_random: 0`) dips novelty to 0.44 around step 50 and then *recovers* to 0.69: the
nearest-neighbour graph is connected enough that the agent walks out of its
exhausted region on its own. So on this archive the boredom stop is inert at 300
steps; it becomes real when the walk is a sizeable fraction of the archive. That is
the mechanism working as designed, not a bug: the archive is bigger than the walk.
If a short run *should* end by boredom, the honest levers are a smaller archive, a
longer walk, or a higher threshold, and the reason is recorded in the log.

**5. What the hiker adds over farthest-point sampling (debug set, same start chip).**
FPS reaches a slightly higher mean novelty (0.754 vs 0.714) because it is
omniscient, but its consecutive chips are 0.99 apart in embedding space and 8,700 km
apart on the ground (medians), with no two consecutive chips related. The hiker's
consecutive chips are 0.50 apart and 2,400 km apart, and the sequence reads as runs
of related terrain punctuated by jumps (`docs/img_debug_walk_agent0.png` vs
`docs/img_debug_fps.png`). Locality is the entire difference, and it is visible.

**6. DOFA vs CLIP on the same walk.** Same seed, same start chip: 27 of 301 chips
shared. CLIP's hops are geographically longer (median 5,500 km vs 2,400 km) at a
*shorter* embedding distance (0.39 vs 0.50): CLIP's notion of "similar" is less tied
to place-type than DOFA's. Visually, the CLIP walk (`docs/img_debug_walk_clip_agent0.png`)
forms long runs of one *look* (eight cloud chips in a row, then a run of city
grids); the DOFA walk moves through terrain types with shorter runs. Both are
RGB-only here, so the comparison is clean.

**7. Geography.** Only 12–16 % of hops are under 100 km. "Nearest in embedding
space" is not "nearby"; a global archive makes a global walk at every step. The
sound layer should expect large geo distances as the norm and small ones as events.

**8. Seasonal siblings are not a problem.** 10–11 of 300 hops land on another season
of the same location (3 %), and 280 of 301 chips are distinct locations. Novelty
handles the near-duplicates as predicted.

**9. Why the walk looks random, and what makes it read as a sequence (2026-09-18).**
The user's observation: apart from runs of ocean, the debug walk looks random. Replaying
the DOFA run with the candidate scores recorded shows three mechanical reasons, on top
of the conceptual one (novelty search maximises dissimilarity from the history, and
pattern in a sequence *is* similarity: return, variation, drift).

- *The neighbourhood is not local.* On 8.7k centred chips, neighbour #1 is at cosine
  distance 0.23, #10 at 0.45, #50 at 0.55; a random pair is at 0.99. Because the
  current chip is in the history, the nearest neighbours score lowest and the agent
  always picks from the outer ring, so a "local" step is already half a random jump.
- *T = 0.05 is not near-greedy.* The gap between the best and second-best score is
  0.023 on average, so the best candidate has a 13 % chance; T = 0.01 gives 68 %,
  T = 0.002 gives 93 %. The default is a lottery among the top ten.
- *Random jumps are structurally favoured.* Five random chips out of ~55 candidates
  win 25 % of steps at k = 50 and 52 % at k = 10; being greedy makes it worse (36 %),
  because the random candidate is by construction the most novel.

Variants on the debug archive, agent 0 (`runs/20260918-09*`):

| variant | jump share | step distance | local step | stop |
|---|---|---|---|---|
| baseline k=50, m=5, T=0.05 | 25 % | 0.63 | 0.50 | max_steps |
| k=10 | 52 % | 0.72 | 0.41 | max_steps |
| T=0.005 | 36 % | 0.74 | 0.59 | max_steps |
| m=0 | 0 % | 0.43 | 0.43 | max_steps |
| k=10, m=0 | 0 % | 0.23 | 0.23 | boredom at step 60 |

With no random jumps and k = 10 the walk becomes a continuous drift with an act
structure (`docs/img_protocol_k10_nojump.png`: forest, villages, highlands, red desert,
sea) and then bores out in the sea. With k = 50 and no jumps
(`docs/img_protocol_k50_nojump.png`) it drifts desert → farmland → city over 50 steps.
The ocean runs in the baseline are the same mechanism confined to the one region dense
enough to hold the agent against the jump lottery. Protocol options are under
discussion; nothing in the defaults has been changed.

**10. Taste, first runs (debug archive, `configs/debug_taste.yaml`, 2026-09-18).**
Three runs, agent 0 unless noted, all seed 7, k = 50, m = 5, T = 0.05, alpha 0.2,
threshold 0.9:

| run | taste weight | init | jumps | taste updates | mean cos(chosen, taste) first 50 / last 50 | mean novelty |
|---|---|---|---|---|---|---|
| `*_regress` | 0 | | 25 % | | | 0.751 |
| `*_taste_first` | 0.3 | first | 21 % | 20 | 0.09 / 0.07 | 0.736 |
| `*_taste_zero` | 0.3 | zero | 22 % | 22 | 0.08 / 0.05 | 0.744 |
| `*_taste_w1` | 1.0 | first | 13 % | 6 | 0.43 / 0.13 | 0.654 |

- *Weight 0.3 is too gentle to see.* The chosen chips' similarity to taste stays near
  0.07, barely above what a random chip would give. The bonus spread across candidates
  (~0.2) is the same size as the novelty spread, and the two terms pull in opposite
  directions: the chips closest to taste resemble the strong encounters, which are in
  the history, so novelty marks them down. They roughly cancel
  (`docs/img_taste_w03.png` looks like the baseline).
- *Weight 1.0 makes a character.* The first 50 chips sit at cosine 0.43 to the taste
  and the sheet (`docs/img_taste_w1.png`) is a single sustained palette: forested hills
  and red earth, no sea, no clouds, no cities. Then similarity decays to 0.13 over the
  walk as novelty exhausts the region the taste points at. Mean novelty drops from
  0.75 to 0.65 and random jumps halve (75 to 39): the jump lottery loses because a
  random chip is rarely to the agent's taste.
- *The absolute threshold makes taste a thing of youth.* Novelty starts near 1.0 and
  drifts under 0.9 within about 50 steps, so at weight 0.3 every update happens before
  step 60 (half of them on random jumps); at weight 1.0 the pull towards the familiar
  keeps novelty low and only 6-8 encounters ever qualify. The more the agent follows
  its taste, the less anything strikes it. That is a coherent character (it settles),
  but if taste should keep evolving through a long walk the threshold needs to be
  relative: a spike above the running mean, not a fixed number. Not implemented; the
  user decides.
- *`init: zero` vs `first` makes little difference at weight 0.3*, because the first
  spike arrives at step 1-5 anyway and alpha 0.2 with ~20 updates leaves almost nothing
  of the initial vector (drift from initial 0.48-0.66).

**11. What the heatmaps show, and a discrepancy they expose (2026-09-18).** Applied
to the baseline debug walk (`runs/20260918-094014_*_regress`) and the taste walk at
weight 1.0 (`runs/20260918-094059_*_taste_w1`); sheets in `docs/img_heatmap_*.png`.

- *The hot patches are the readable ones.* On the baseline walk, step 1 (farmland grid
  after a forest start) is hot everywhere; clouds are hot the first time and cold
  every time after; ridges, river meanders, a coastline and a town are hot inside
  otherwise-cold chips. On the taste walk the best example is step 63: a jump into a
  dense town after 62 steps of hills and forest, hot everywhere *except* the round
  green patches of vegetation, the one thing the agent had seen plenty of.
- *The hot fraction declines with the walk*, from 0.44 of patches in the first 50
  steps of the baseline to 0.16-0.20 after step 200; on the taste walk it starts lower
  (0.26) because the agent stays in familiar terrain. Per-chip novelty and the patch
  mean correlate at 0.53-0.71 per agent.
- *The discrepancy.* The patch score agrees with the *nearest* chip in history
  (correlation 0.83-0.86 with the minimum chip distance) much better than with the
  logged novelty (0.53-0.55). Step 106 of the taste walk is a dark sea chip that
  scored a chip-level novelty of 0.77 while every one of its patches scored under
  0.05: the agent had visited the sea at step 105. With `j_history = 15` the chip score
  averages the distances to the 15 nearest history chips, so one near-twin is
  outvoted by 14 unrelated chips. On the baseline walk, 10 of 300 chosen chips had a
  history chip within 0.25 yet were logged at a mean novelty of 0.71; on the taste
  walk, 34 of 300 (mean 0.61). At patch level the same chip contributes 196 bank
  entries, so the 15 nearest patches all come from the twin and the score collapses.
  **This is the mechanism behind the ocean runs the user noticed**: a new ocean chip
  keeps scoring as novel until about fifteen ocean chips are in the history. It is a
  property of the sparseness measure, not of the archive. Options, not applied: a
  smaller `j_history` (Lehman-Stanley's 15 was chosen for a dense behaviour space;
  the dial table shows the ranking shifts less than the level), or a score that mixes
  the nearest distance with the j-mean. The user decides; it changes the character of
  every walk.

**12. The dream: what steering a generator with the agent's score actually does
(2026-09-18).** Generator: SD 1.5 + LoRA rank 8, 3,000 steps at batch 8 on the 8,704
debug chips, 13 minutes, 3.2 GB peak; samples are painterly satellite textures
(`data/models/dream_ssl4eo-val-rgb/samples_03000.png`). Dreams on the taste walk
(`runs/20260918-102029_*_taste_w1b`) and the baseline (`runs/20260918-094014_*_regress`),
four candidates per agent, sheets in `docs/img_dream_*.png`; peak 4.0 GB.

- *The first guidance was adversarial.* At scale 0.1 to 0.6 with a single view the
  measured score rose by up to 0.17 while dream and control differed by 2-10 of 255
  per pixel and looked identical. Decomposing the score: novelty was flat or fell
  (0.61 to 0.58), the whole gain was the taste term (cosine to the taste vector
  0.10 to 0.27). A fixed vector is an easy target for a pixel perturbation that a
  vision transformer reads as a large semantic move; "far from everything I have
  seen" is not. Averaging the score over four random views removed that gain
  entirely (taste-on dream 0.780 vs control 0.779).
- *With views, strong scale and the high-noise window the gains are real and
  visible.* Baseline (novelty only): novelty 0.63-0.72 in the controls to 0.74-0.83
  in the dreams, pixel change 11-20 of 255, and the change survives re-encoding of
  the saved PNG. The best dreams reach the archive ceiling: 0.834 vs the most novel
  unvisited real chip at 0.841 (agent 0), 0.803 vs 0.806 (agent 1); on the taste walk
  0.883 vs 0.872. The last real step of each walk was 0.42-0.75.
- *What "novel" looks like when it can be invented.* Agent 1 of the taste walk ended
  in city grids and dreams a mottled green forest, the opposite of its last twenty
  steps; the striated desert of its control is gone. The baseline's agent 1 dreams
  green terrain with magenta blotches, a colour the archive never contains. That is
  the objective read literally: unlike anything seen includes colours no chip has,
  and a 13-minute LoRA prior does not hold the sample on the manifold hard. A longer
  training (or a stronger prior term) would trade novelty for plausibility; the
  trade is the user's.
- *Taste and novelty cancel here too.* On the taste walk at the strong settings the
  gain is again mostly taste (0.10 to 0.27) with novelty flat, because the pull
  towards familiar terrain and the push away from the history oppose each other,
  exactly as in the walk (finding 10). The dream stage can be run with
  `dream.include_taste: false` for a pure-novelty dream.
- *One candidate dominates both runs.* Seed 7's third sample is a red-and-white
  foliage-like texture that scores 0.85 unguided under any history, because the
  generator itself put it off-distribution; guidance adds only 0.03. Controls are
  identical across runs with the same seed by design (the history is the only
  difference between two runs' dreams); `n_candidates` and the per-candidate log
  exist so such a sample is seen for what it is.

