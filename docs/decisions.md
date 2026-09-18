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
