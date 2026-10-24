# Bored Machines — Brief: First Agentic Walk (Speedrun)

**Goal:** get one end-to-end loop working as fast as possible:
real tiles → agents with self-grown perception walk → paths logged → small image model trained on each path, weighted by surprise/boredom → samples compared against baselines.

This is a **speedrun, not the system**. Hardcode where convenient, keep one config file, log everything, and avoid abstractions. The point is to find out what works before building it carefully.

Two gates decide what gets built up afterwards:

- **Gate 1 — the walk:** paths are distinguishable from a random walk, and interestingness keeps agents off noise (clouds, no-data).
- **Gate 2 — the dreams:** a model trained on a weighted path produces samples that differ visibly or measurably from baselines, and isn't just memorising.


---

## 1. Dataset

**Source:** Major TOM `Core-S2L2A` on Hugging Face (`Major-TOM/Core-S2L2A`, CC-BY-SA-4.0). It holds about 2.2M Sentinel-2 L2A patches of roughly 1068×1068 px at 10 m, on a ~10 km grid. It's monotemporal, so **time is out of scope for the speedrun**.

**Subset:** one heterogeneous region, roughly 1,000–3,000 grid cells. Pick a bounding box that mixes several terrain types:
- mountains
- farmland
- a city
- water or coast
- forest

The region is your call.

**Steps:**

1. Load `metadata.parquet` and filter by bounding box. Keep these fields, and **check the exact column names on the dataset card**:
   - grid cell ID
   - centre lat/lon
   - timestamp
   - cloud cover
   - no-data fraction
   - the pointer to the image shard and row
2. **Don't filter out cloudy tiles entirely.** Keep tiles up to ~60–70% cloud cover, because the noisy-TV test needs clouds present. Drop tiles with no-data above ~10%.
3. Fetch only the RGB you need. Parquet is columnar, so read just one column, not whole rows:
   - the `thumbnail` column, if it exists (fastest), **or**
   - `B04`/`B03`/`B02`, converted to RGB with a fixed percentile stretch. Use one global 2–98% stretch computed over the subset, not a per-tile stretch, so brightness differences stay meaningful.
4. Resize each tile to **256×256 RGB uint8**, which is roughly 40 m/px. Store everything in one `tiles.npy` (memmap, shape `N×256×256×3`) plus `tiles.parquet`, an index with columns `idx, grid_cell, lat, lon, cloud_cover, timestamp`.
5. Precompute neighbours with a haversine BallTree on the tile centres. Use radius queries rather than grid row/col arithmetic, because Major TOM's columns shift with latitude.

**Out of scope for now:** multi-temporal data, multispectral bands, and WorldCover/GHSL/DEM joins. Logging lat/lon and grid cell IDs now is enough to join those layers later.

---

## 2. Agent

### 2.1 Perception (self-grown, no learned prior)

- A small **convolutional autoencoder** with random initialisation from the agent's seed.
  - Input: 32×32×3. Latent: 64-d. Size: ~100–300k parameters.
  - Encoder: 4 stride-2 conv blocks (32→16→8→4→2), then flatten and linear to 64.
  - Decoder: mirrors the encoder.
- **Patches:** for each tile, sample `K = 16` random crops of size `crop_px` from the 256 px tile, then resize them to 32×32.
  - `crop_px` is the **scale of attention**: 32 px ≈ 1.3 km field of view, 64 px ≈ 2.6 km, 128 px ≈ 5 km.
  - The model input size stays fixed, so every temperament uses the same network.
- Optimiser: Adam with learning rate `lr`. `lr` is how quickly things become familiar.
- **Replay buffer:** a FIFO of patches with size `buffer_size`. This is the agent's **memory**. Every update mixes new patches with a replay sample.

### 2.2 Signals per candidate tile `c`

All signals use the current model. Normalise each with a running mean and standard deviation (EMA) to get z-scores.

| Signal | Definition | Role |
|---|---|---|
| **surprise** `e(c)` | mean reconstruction MSE over `c`'s patches | raw prediction error (logged; low weight by default) |
| **novelty** `n(c)` | distance from `c`'s mean latent to its `k=10` nearest neighbours in the **archive** of visited tiles' latents | novelty search (Lehman & Stanley) |
| **progress** `g(c)` | **probe:** split `c`'s patches into halves A and B. Clone the model, run `s = 3` Adam steps on A, then measure `g = err_B(before) − err_B(after)` | learning progress / interestingness (Schmidhuber, Oudeyer). Noise like clouds doesn't generalise from A to B, so it scores low |

- **Archive re-embedding:** the encoder keeps changing, so re-embed every archived tile every `reembed_every = 100` steps. Memories get re-read by a changed mind.
- **Interest:** `I(c) = w_n·n̂(c) + w_g·ĝ(c) + w_e·ê(c)`.

### 2.3 Temperament parameters (one YAML per agent)

```yaml
seed: 0               # random init of the network (identical settings, different seeds → divergence)
crop_px: 64           # scale of attention
lr: 1e-3              # how quickly things become familiar
buffer_size: 2048     # memory (patches)
radius_km: 15         # neighbourhood radius ≈ step size (~8 neighbours at 15 km)
p_long_jump: 0.02     # chance a random far tile is added to the candidates
patience: 0.6         # boredom threshold (see 3.2)
temperature: 0.5      # exploration vs exploitation (softmax over interest)
w_n: 1.0              # novelty weight
w_g: 1.0              # progress weight
w_e: 0.0              # raw surprise weight
steps: 1500
```

---

## 3. Walk mechanics

### 3.1 Loop

```
init: model(seed), start tile t0, archive = [], buffer = [], boredom B = 0
for step in range(steps):
    C = neighbours(t, radius_km) ∪ (random tile with prob p_long_jump)
    if C empty: C = {random tile}
    for c in C: compute e(c), n(c), g(c) → z-scores → I(c)
    t ← sample c ~ softmax(I / temperature)
    train model: u = 4 Adam steps on [patches(t) + replay sample]
    record: progress actually achieved on t (err before vs after these u steps)
    push patches(t) to buffer (FIFO); push mean latent(t) to archive
    boredom update (3.2)
    if step % reembed_every == 0: re-embed archive
    log everything (3.3)
```

Revisits are allowed. Novelty and progress decide whether a return is worth it, and returns are the hook for nostalgia later.

### 3.2 Boredom

- `B ← 0.9·B + 0.1·[max_c I(c) < 0]`. This counts how often even the best option is below average interest.
- If `B > patience`, it's a **bored event**:
  - log it and save a checkpoint;
  - decode 16 samples from random latents near the archive's least-visited region. These are quick "daydreams", optional and cheap;
  - teleport to a random tile and reset `B = 0`.
- A low `patience` value means a restless agent.

### 3.3 Logging (non-negotiable)

- **Per step** (`runs/<run_id>/steps.parquet`):
  - `step`, `tile_idx`, `grid_cell`, `lat`, `lon`, `cloud_cover`
  - `e`, `n`, `g`, `I` of the chosen tile
  - `max_I`, `n_candidates`, `jump_type` (neighbour / long / bored)
  - `B`, `bored_event`
  - `err_before`, `err_after`
- **Per step, optional** (`candidates.parquet`): every candidate's scores.
- **Run folder:** the config YAML, the seed, the git hash, model checkpoints every 250 steps plus the final one, the final archive latents, and the daydream PNGs.

---

## 4. Runs

Expected time per agent is roughly 1,500 steps × (≈10 probes + 1 update). On a tiny model and one GPU that should be minutes to tens of minutes per run. Measure it on the first run before planning the rest.

| Run | Change from baseline | Purpose |
|---|---|---|
| `random` | uniform choice among neighbours, no model | control |
| `baseline` | defaults above | reference agent |
| `novelty_only` | `w_g = 0` | noisy-TV control: should get stuck on clouds or noise |
| `myopic` | `crop_px = 32` | scale of attention |
| `wide` | `crop_px = 128` | scale of attention |
| `restless` | `patience = 0.3` | boredom |

Run **2 seeds each** from the **same start tile**, about 12 runs in total. If time is short, run `random`, `baseline`, `novelty_only` and one other temperament.

---

## 5. Gate 1 — looking at the walks

Write one notebook, `analysis/walks.ipynb`, that produces for each run:

1. **Path map:** lat/lon polyline over the region's tile grid (thumbnails or just dots), coloured by step, with bored events marked.
2. **Contact sheet:** every 10th visited tile, in order.
3. **Stats table** comparing runs. Each statistic is compared against the subset's base rate:
   - unique tiles visited
   - revisit rate
   - mean step distance
   - long jumps and bored events
   - mean cloud cover on the path
4. **Learning curve:** reconstruction error on a fixed held-out set of 200 tiles over steps.

**Pass if:**
- (a) at least one agent's stats clearly differ from `random`;
- (b) `baseline` visits fewer cloudy tiles than `novelty_only`, which shows interestingness is doing its job;
- (c) seeds and temperaments produce visibly different paths.

**If it fails:** check the progress probe first (`s`, split, normalisation). Then check `temperature`. Only after that consider swapping perception for a pretrained encoder as a control.

---

## 6. From path to dataset

For one or two agents that passed Gate 1, build per-tile weights from the **unique visited tiles**:

- `surprise_i` = z-scored `e` at the first visit
- `boredom_i` = boredom `B` at the first visit
- `w_i = clip(exp(α_s·surprise_i − α_b·boredom_i), 0.2, 5.0)`, with defaults `α_s = 1.0` and `α_b = 0.5`
  - Default reading: surprising tiles weigh more, and tiles seen while bored weigh less.
  - "Weighted by boredom" could also be read the other way round. Keep `α_b`'s sign as a switch and try both if time allows.

Then build three training sets of **the same size**:

| Set | Tiles | Weighting | Isolates |
|---|---|---|---|
| `path_weighted` | the agent's visited tiles | `w_i` | the full effect of the hike |
| `path_uniform` | the same tiles | uniform | what the hike *emphasised* (weighting) |
| `random_uniform` | a random sample of the same size from the subset | uniform | what the hike *selected* |

Implement weighting with a `WeightedRandomSampler`, or as integer repeat counts if your trainer only takes folders.

**Training images:** take random **64×64 crops** from the 256 px tiles, with flips and 90° rotations. Rotations are safe for nadir imagery. One tile yields many crops, which eases the small-data problem.

---

## 7. Small image model

**Speedrun choice:** an unconditional **DDPM at 64×64** using Hugging Face `diffusers`: `UNet2DModel(sample_size=64, block_out_channels=(64,128,256,256))` with `DDPMScheduler`. It's stable, simple, and takes a weighted sampler without extra work.

- Same steps (e.g. 15k at batch 64), same seed and same architecture for all three sets.
- Expect hours per model, not minutes. Measure the first run before planning the others.
- Sample 64 images per model, using the same noise seeds across models.

**Later, if Gate 2 passes and you want more striking images:** StyleGAN2-ADA at 128–256 px. That's where mapping boredom to truncation becomes possible. Don't do it in the speedrun.

---

## 8. Gate 2 — looking at the dreams

`analysis/dreams.ipynb`:

1. **Side-by-side contact sheets:** `path_weighted` | `path_uniform` | `random_uniform`.
2. **Memorisation check:** for each sample, show its nearest training crop by pixel L2. If samples are near-copies, the model is regurgitating, not dreaming.
3. **Cheap stats per model:**
   - colour histograms (distance between models)
   - mean brightness and saturation
   - sample diversity: mean pairwise distance
4. **One-line written observation per model,** descriptive rather than interpretive (e.g. "leans towards dark water and field edges").

**Pass if** `path_weighted` differs visibly or on at least one statistic from `random_uniform`, without memorising. A "no difference" result is also a valid finding. Log it and move on.

---

## 9. Repo layout

```
data/prepare.py          # subset, fetch, resize → tiles.npy, tiles.parquet, neighbours
agent/model.py           # conv autoencoder
agent/signals.py         # surprise, novelty (archive kNN), progress probe, normalisers
agent/walk.py            # loop, boredom, logging   →  python -m agent.walk configs/baseline.yaml
configs/*.yaml           # one file per run
gen/build_sets.py        # weights + three training sets
gen/train_ddpm.py        # diffusers training, weighted sampler
gen/sample.py
analysis/walks.ipynb
analysis/dreams.ipynb
runs/<run_id>/...        # everything a run produces
notes/                   # expectations note, observations
```

---

## 10. Order of sessions

1. **Data:** subset, fetch, cache and neighbours. Done when one cached tile shows correctly and its neighbours look right on a map.
2. **Agent and walk:** the `random` and `baseline` runs end to end with full logging.
3. **The remaining runs, plus the Gate 1 notebook.** Decide which agents go forward.
4. **Datasets and three DDPM trainings.** Run these in the background while writing theory.
5. **Gate 2 notebook.** Write a short observations note on what worked, what didn't, and what to build properly.

---

## 11. Deliberately out of scope (later, if the gates pass)

- Multi-temporal walks (same tile across dates) and **nostalgia** (detected forgetting of replayed memories → pull back to revisit)
- Information-gap curiosity (ensemble disagreement)
- Wundt-curve hedonics as an alternative to learning progress
- A SOM memory for on-screen visualisation of taste forming
- Multispectral bands and false-colour dreams
- A pretrained-encoder control agent (e.g. Major TOM's precomputed embeddings)
- Datamorphic layers: WorldCover, GHSL, DEM
- Agents whose paths cross
- The film, the music system, and any narrator
