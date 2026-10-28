# Dreams v3: Per-Agent GAN + Latent Search Driven by Learning Progress

**Goal:** give the dreamer the agent's drives. Each agent gets a StyleGAN trained on its own weighted path. When it dreams, it searches that GAN's latent space for the images it would learn most from. "Bored, so I imagine what I'd like to see" becomes an actual mechanism.

**Decisions already made (do not change):**

| Decision | Choice |
|---|---|
| Dreamer training data | Whole path, weighted by surprise/progress (per-tile weights from v1 `gen/build_sets.py`) |
| Base model | **Both, for one agent only:** (a) from scratch on the path, (b) fine-tuned from a shared satellite-only base |
| How far the search may go | **Sweep** several reach levels; the artist picks from contact sheets |
| What the search maximises | **Learning progress** of the agent's own autoencoder |
| World | **Global**: the whole of Major TOM Core-S2L2A, loaded lazily. The regional subset is kept for development only |
| Comparison | Three conditions (section 4.0): **A** global walker × its own fine-tuned dreamer · **B** global walker × shared base · **C** confined walker × shared base |

Use **two agents**, both with the `baseline` temperament and seed 0:
- the **global walker** (section 1.3);
- the **confined walker** (section 1.4).

Earlier regional runs stay as they are; they're not inputs to v3.

---

## 0. Before running anything

Write `notes/expectations_dreams_v3_<date>.md`: one paragraph on what from-scratch vs fine-tuned dreams will look like, and what happens at the highest reach. Don't edit it afterwards.

---

## 1. Global world + one global walk

Going global changes the data backend, not the walker. Do not download the planet.

**1.1 Global index**
- Load the full `metadata.parquet` for Core-S2L2A (about 2.2M rows). Keep the same columns as v1: grid cell, centre lat/lon, timestamp, cloud cover, no-data, and the shard/row pointer.
- Apply the same filters as v1: no-data ≤ 10%, cloud cover ≤ 70%.
- Build one global haversine BallTree over tile centres. Neighbour queries (`radius_km`) work exactly as in v1, and the dateline and poles are handled by haversine.
- **Report coverage:** a world map of tile centres, plus the share that is land, coast and open ocean (via a coarse land mask). State in the run log what "the planet" means here. As far as we know, Core is mostly land and coastal tiles.

**1.2 Lazy tile store** (`data/tile_store.py`)
- `get_lowres(idx)` → 256×256 RGB uint8 at about 40 m/px, the walker's view. Use the `thumbnail` column if present, otherwise B04/B03/B02 with the **fixed global stretch**.
  - The stretch values must be computed once, from a global random sample of about 5k tiles, and stored in `data/global_stretch.json`. Never compute them per region or per tile.
- `get_hires(idx)` → full 10 m RGB (about 1068×1068) for GAN crops. Fetch only for tiles the agent actually visited, after the walk.
- On-disk LRU cache with a configurable size (start at 50 GB), keyed by tile index.
- While the agent is at a tile, prefetch its neighbourhood in the background (radius plus one ring).
- Read only the needed parquet columns; parquet is columnar, so remote reads fetch only those column chunks.
- Retry with backoff, and log fetch latency per step. If a candidate can't be fetched within a timeout, drop it from that step's candidates and log it.

**1.3 Global baseline walk**
- Same walker and `baseline` config as v1, with these changes:
  - `steps: 5000` (adjust after timing the first 500)
  - long-jump target = a random tile from the **whole** filtered global index (blind jump, as before)
  - start tile: a fixed, mixed-terrain location you record in the config. Note it in the log; it's the agent's birthplace.
- Log exactly as in v1, plus fetch latency and cache hit rate. Save the global path map (world projection, coloured by step) as the first output.
- Develop and debug against the regional subset first, then switch the tile store to the global index. The walker code shouldn't change.

**1.4 Confined walk**
- Same walker, `baseline` temperament, seed 0 and `steps` as 1.3.
- **Confinement:**
  - `confine_center: [lat, lon]` and `confine_radius_km: 300`. Neighbour candidates and long-jump targets are drawn **only** from tiles inside that circle. Nothing else changes.
  - The artist chooses the centre. Suggested default: fairly uniform terrain (a desert, tundra or rainforest), so that "least like home" is easy to read. Record the choice in the config.
- Log as in 1.3. Also save a map of the confinement circle and the path.
- This agent gets **no GAN of its own**. It only dreams through the shared base.

## 2. Data for the GANs

All crops are **256×256 at native 10 m** (≈2.56 km field of view), cut from full-resolution Major TOM tiles (B04/B03/B02, the fixed global stretch from 1.2, uint8), fetched via `get_hires`.

**Agent dataset (`agent_path`):**
- All unique tiles the agent visited.
- Crops per tile = `round(16 × w_i)`, where `w_i` is the v1 tile weight, clipped to [0.2, 5]. That gives roughly 3–80 crops per tile. Repeating crops is how the weighting enters StyleGAN, which has no sample weights.
- Random crop positions, horizontal flips and 90° rotations baked in at export.
- Optional flag `--crop_sampling heatmap`: if per-tile learning-progress maps exist, sample crop positions in proportion to progress inside each crop. Default is `uniform`.

**Base dataset (`base_global`), the "collective unconscious":**
- A uniform random sample of 4,000 tiles from the **whole filtered global index**, **excluding all tiles on this agent's path**, with 16 crops each.
- It is satellite-only and from the same dataset, so no external prior.
- Save the sample's tile list and a world map of where it comes from.

Export both datasets with the StyleGAN `dataset_tool.py` to zip at 256×256. Log tile counts and crop counts.

---

## 3. GAN training

- **Repo:** NVlabs `stylegan3` with `--cfg=stylegan2` (supports ADA). Pin the environment to the repo's README requirements and use its Dockerfile if the local PyTorch/CUDA doesn't compile the custom ops. If it still won't build, use a maintained community fork of `stylegan2-ada-pytorch`, and note which one.
- **Common flags:** `--gpus=1 --batch=32 --gamma=1 --mirror=1 --aug=ada --metrics=none --snap=50`.
  - `--metrics=none`: FID runs on an ImageNet-trained Inception network, which is the kind of prior this project avoids. It also costs time. Judge progress from the snapshot grids instead.
- **Runs:**

| Run | Data | Init | Budget |
|---|---|---|---|
| `base` | `base_global` | scratch | ~3000 kimg (adjust after timing) |
| `agent_scratch` | `agent_path` | scratch | same kimg as `base` |
| `agent_finetune` | `agent_path` | `--resume=base.pkl` | ~800 kimg |

- Time the first 200 kimg of `base` and report a projected total before committing. Expect days, not hours, on a single GPU.
- Keep every snapshot `.pkl` and every `fakes*.png` grid.

---

## 4. Dream search (latent variable evolution)

Script: `gen/dream_search.py --gan <pkl> --agent_run <run_dir> --reach <R> --seed <s>`.

### 4.0 Conditions

| Condition | Searching agent (scores with its model) | Dreamer (GAN) | Question |
|---|---|---|---|
| **A** | global walker | `agent_finetune` | dreams from its own history |
| **B** | global walker | `base` | the same agent, choosing from the world's shared imagination |
| **C** | confined walker | `base` | a narrow history choosing from the world's imagination: does it dream the negative of home? |
| *A0 (reference)* | *global walker* | *`agent_scratch`* | *the from-scratch dreamer, as decided earlier; secondary* |

Run the same search settings, `R` sweep and seeds for every condition.

### 4.1 Scoring an image with the agent's own model

- Load the searching agent's **final autoencoder** and archive from its walk run: the global walker for A, A0 and B, the confined walker for C. No other networks.
- **Match the agent's ground scale.** The agent saw tiles at about 40 m/px, and its patches cover `crop_px × 40 m`. A dream is 256 px at 10 m, so downsample it by 4 to 64×64 (40 m/px). Then take `K = 16` random crops of `crop_px` (if `crop_px ≥ 64`, use the whole 64×64 image) and resize each to the autoencoder's 32×32 input. For `baseline` (`crop_px = 64`) the dream covers exactly one agent patch.
- **Learning progress** `g(img)`: split the 16 crops into halves A and B. Clone the autoencoder, run `s = 3` Adam steps on A at the agent's `lr`, then compute `g = err_B(before) − err_B(after)`. Never update the real agent.
- **Diversity term:** `d(img)` is the distance in the agent's latent space to the nearest dream already kept in this search. It only stops the population collapsing to one image. Weight it `β = 0.3`, and log runs with `β = 0` as well.
- **Fitness:** `F = ĝ + β·d̂` (z-scored within the generation).

### 4.2 Search

- **Space:** StyleGAN `W` (after the mapping network).
- **Reach `R`** controls how far from the average latent `w_avg` the search may operate. It stands in for boredom level.
  - Initial population: sample `z`, map to `w`, then truncate: `w = w_avg + R·(w − w_avg)`.
  - Mutation: `w' = w + N(0, σ·R)`, with `σ = 0.1 × std(W)` measured from 10k mapped samples.
  - **No clamping.** At `R > 1` the search is allowed past the trained range. That's intended.
- **Sweep:** `R ∈ {0.7, 1.0, 1.5, 2.0, 3.0}`.
- **Algorithm:** a simple (μ+λ) evolution with population 64, keeping the top 16 each generation, for 30 generations. Use fixed seeds; run the same seeds for every condition.
- **Log per generation:** the best `F`, `g` and `d`; the mean distance of the population from `w_avg`; the best image.

### 4.3 Reference samples (no search)

For each GAN, generate 64 plain samples at ψ = 1.0 with fixed seeds. This shows what the dreamer produces without the agent's drive.

---

## 5. Outputs

Save everything to `runs/<agent_run_id>/dreams_v3/`.

0. **Maps:**
   - the global walker's path (from 1.3);
   - the confined walker's path and its confinement circle (from 1.4);
   - the `base_global` sample.
1. **Main contact sheet:** rows are reach levels `R` (0.7 → 3.0); columns are conditions **A | B | C**, the top 8 dreams each, same search seeds. Put A0 (`agent_scratch`) on a separate sheet beside A.
1b. **Home vs dream (C):**
   - 16 random tiles from the confined walker's path next to its top dreams at each `R`.
   - For every C dream, find the nearest real crop in `base_global` (pixel L2 at 64 px) and plot that crop's location on a world map. This is where its dreams "come from".
   - Do the same for B, so the two maps can be compared.
2. **Reference sheet:** plain samples from `base`, `agent_scratch` and `agent_finetune` side by side.
3. **Search strips:** for 3 seeds per `R`, the best image of each generation in a row (30 frames). This is the dream forming, and potential film material. Also export them as an MP4 at 6 fps.
4. **Memorisation check:** for every kept dream, the nearest training crop (pixel L2 at 64 px) shown beside it.
5. **Scores table** (`dreams.parquet`): `condition, agent, gan, R, seed, generation, rank, F, g, d, dist_from_w_avg, nn_train_dist, nn_lat, nn_lon, w` (store the latent too).
6. `observations.md`, descriptive only. Answer these: Where does it break? What looks strange but coherent? Does the fine-tuned dreamer differ from `base`'s plain samples? Do transitions between terrain types appear (e.g. sea becoming ridge)? Do A and B differ, i.e. does the agent's own dreamer matter compared with the shared one? Do C's dreams lean towards terrain unlike its home, and do they land further away on the map than B's?

---

## Out of scope for v3

Memory-as-training-set dreamers, GANs for other agents, multiple agents starting on different continents, steered jumps (the drifter/planner setting: horizon glimpses, momentum, an interest map; jumps stay blind for now), multispectral bands, land-cover masks and texture transfer, network bending, mapping actual boredom values to `R` (the sweep comes first), and the narrator.
