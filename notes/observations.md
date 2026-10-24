# Observations — Bored Machines speedrun (2026-10-24)

Figures: `notes/img/`. Notebooks: `analysis/walks.ipynb` (Gate 1) and `analysis/dreams.ipynb` (Gate 2).
Predictions written before any run: `notes/expectations.md`.

## Setup in one paragraph

- **Data:** 1,814 Major TOM Core-S2L2A tiles in Northern Italy (lat 43.5–47.0, lon 6.5–12.6), as 256 px RGB thumbnails (~42 m/px), with neighbours within 15 km (6.7 on average).
- **Agent:** a 272k-parameter conv AE, random init.
- **Walk:** 1,500 steps from Milan. On average 7.3 candidates per step, about 0.05 s per step, so ~80 s per run on the RTX 4070 laptop GPU.
- **Runs:** 20 walks, 2 seeds each. The brief's six temperaments, plus two additions explained below: `surprise_only` and three `tvtest_*` runs.

## Deviations from the brief, and why

| What | Why |
|---|---|
| No tiles above 25 % cloud | Major TOM Core was built with a 25 % cloud cap. Only 4.7 % of the region's tiles exceed 10 % cloud. |
| **Synthetic noisy TV**: 7 tiles near Novara show fresh 4×4-px RGB noise each time an agent looks | Agreed with Moritz as a substitute for heavy clouds. Flagged `tv` in `tiles.parquet` and dropped from DDPM training sets. |
| **`surprise_only`** temperament (w_e = 1, w_n = w_g = 0) | `novelty_only` turned out to be the wrong noisy-TV control (finding 2). |
| **TV test**: baseline, novelty_only and surprise_only started one step from the TV | In the main runs the TV was rarely even a candidate: 7 tiles, 50 km from the start. |
| Learning curve logged during the walk (every 25 steps) on 200 fixed tiles with fixed crops | Cheaper than reloading checkpoints. The walkers may visit those tiles; they are a fixed probe, not a test split. |
| DDPM UNet block types: attention only at 16×16 and 8×8 | The brief fixes only `block_out_channels`. |

## Gate 1 — the walk: **PASS**, with (b) passing via the TV test rather than real clouds

**(a) Different from random — yes, clearly.**
- The random walk diffuses through the Po plain.
- Every curious temperament leaves the flat farmland within about 100 steps. They go to the Alps or along the Ligurian coast and Apennines. Share of steps north of 45.8° N: random 34 %, baseline 51 %, novelty_only 59 %, surprise_only 97 %.
- Snow-bright tiles make up 13 % of the region but 24–40 % of curious paths.
- Curious agents visit *fewer* unique tiles than random (baseline 0.77×, novelty_only 0.51×) but range wider (radius of gyration 1.2×).

**(b) Interestingness keeps agents off noise — yes for the TV, no effect for real clouds.**
- TV test, share of steps on the TV:
  - `surprise_only`: 77–96 %. It sits on the TV for up to 266 consecutive steps. Trapped.
  - `novelty_only`: 0.3–0.5 %.
  - `baseline`: 0 %. It had TV tiles among its candidates 8 times and never chose one; the TV's progress z-score is −0.4 to −0.6.
- Real clouds: no effect. Cloud cover on the path relative to the subset is baseline 1.27×, novelty_only 1.04×. Clouds here are thin (max 25 %) and carry no signal.

**(c) Seeds and temperaments differ — yes.**
- Every pair of seeds diverges at step 0 or 1.
- Jaccard overlap of visited sets between seeds is 0.04–0.23.
- The maps differ visibly by temperament: myopic and wide go to different parts of the Alps, and restless is scattered by 18–20 teleports.

## Findings worth keeping

1. **The noisy-TV trap belongs to prediction error, not to novelty in a learned embedding.** I had predicted the opposite in `expectations.md`. Novelty compares the *mean latent over 16 patches*. I.i.d. noise always averages to the same point in latent space, so after one visit the TV is familiar. Its novelty z is only +0.2 to +0.5, while its surprise z is +1 to +2.4. Only the raw-error agent is trapped. The brief's `novelty_only` control would be correct for a single-patch, per-observation novelty. With averaging, it is not.
2. **The high Alps are a *natural* noisy TV.** Snowfields with hard shadows stay both novel and surprising across dozens of visits. novelty_only's favourite tile (Aosta, 57 visits) keeps a novelty z of +1.5 to +1.8 throughout. The 272k-parameter AE can't compress high-contrast snow/rock texture, and that texture varies a lot between random crops. Every curious agent over-samples snow 2–3×. This may be the main "taste" of these agents, and it is partly a capacity artefact of the perception model.
3. **Learning progress loves things it keeps forgetting.** baseline_s0's favourite tiles include near-black January open sea, 30+ visits each. Black is trivial to relearn and is forgotten between visits as the replay buffer fills with snow, so each return reliably yields "progress". This is an accidental version of the nostalgia mechanism listed as out of scope: return to what you have forgotten. It also works as a no-data trap for the progress signal; deep sea and no-data look alike.
4. **Agents dwell.** 35–50 % of curious steps fall on about 35 favourite tiles (random walk: 4 %), and 25–32 % of moves return to the tile from two steps earlier (random: 18 %). Contact sheets read as *episodes*: farmland → long sea episode → long alpine episode → sea. That is closer to dramaturgy than the earlier hiker was.
5. **The trapped agent forgets the world.** tvtest_surprise_only_s0's held-out error falls to 0.010 and then *rises* to 0.023 while it watches the TV. Every other agent ends at 0.004–0.005, and the held-out curves barely separate the temperaments.
6. **Boredom is rare and front-loaded.** max I < 0 on only 10 % of baseline steps, and most bored events happen in the first ~100 steps while the running z-scores warm up: baseline 4–5 events, restless 18–20. With z-scores centred on a running mean, "even the best of ~7 candidates is below average" is uncommon by construction. Boredom as defined is mostly a restlessness knob, not a mood that builds up.
7. **Monotemporal patchwork.** Each cell is a different date, so neighbouring alpine tiles alternate between snow-covered and snow-free. Some of the agents' "novelty" in the Alps is season, not terrain.

## Decision: which agents go to Gate 2

- **`baseline_s0`**: the reference agent. 427 unique non-TV tiles; 28 % snow and 5 % dark sea vs 13 % and 3 % in the region.
- **`myopic_s0`**: the most snow-biased path (40 %), with a different perception scale. 362 tiles.

The flipped boredom sign (α_b = −0.5) was **not** trained. B on first arrival is ≤ 0.6, so α_b·B shifts a weight by at most e^0.3 ≈ 1.35×, and the two readings give nearly identical weights. In practice the weights are surprise weights. If boredom should matter in the dataset, it needs a bigger range: for example, use the time since the last bored event, or raise α_b to ~3.

## Gate 2 — the dreams

Three DDPMs per agent: 26.6M parameters, 64 px, 15k steps × batch 64, about 92 min each on the 4070. Same init, data seed and sampling noise for all three. 64 samples each.
Figures: `notes/img/gate2_sheets_*.png`, `notes/img/dreams_hires/`, `notes/img/dreams_far/`.

### baseline_s0: formally a **PASS**, with a strong caveat

**No memorisation.**
- The search is exhaustive: every 64 px window of every training tile, in all 8 rotations and flips.
- Detailed samples (pixel std > 12) sit *further* from their training data than unseen real crops do: median RMSE 32–40 vs about 18.
- Only 1 of 52 detailed `random_uniform` samples is closer to its training data than the closest unseen real crop.
- Flat images (open sea, saturated snow) match any other flat image at RMSE ≈ 0, so the copy test is read only on detailed samples.

**`path_weighted` differs from `random_uniform` on several statistics.** The noise floor is the spread between 20 independent batches of 64 real crops.

| | samples | real training crops |
|---|---|---|
| colour-histogram JS distance | 0.090 (1.5× floor p95) | 0.154 (2.6×) |
| Δ brightness | +0.036 (1.7 sd) | +0.124 (5.8 sd) |
| Δ saturation | −0.064 (−3.8 sd) | +0.018 (+1.1 sd) |
| Δ diversity (pairwise RMSE) | +16 (2.1 sd) | +47 (6.1 sd) |

**Caveat 1: the models follow their data only weakly.**
- Real crops of the path set are 40 % bright (snow); the samples are 47 %.
- Real crops of the random set are **10 %** bright; its samples are **37.5 %**.
- All three models come out brighter than their data.
- Checked and ruled out: a bug (the three models trained on different tiles and differ by 46 % in their weights) and a bf16 sampling artefact (fp32 sampling gives the same brightness).
- So the large data differences (5–6 sd) shrink to 1.7–2 sd in the samples. The saturation difference, the largest one, is mostly the random-tile model's own bias toward saturated colour, not a property of its data.

**Caveat 2: same noise, same dream.**
- Sample *i* of one model resembles sample *i* of the others: RMSE 16–29, against 89–98 between different samples.
- The noise largely decides the composition; the training set changes surface and colour. The triptychs show this: a blue crevasse becomes a cyan sea with a cloud, and rock becomes farmland.
- This is a known property of diffusion models that generalise rather than memorise. It makes same-seed comparisons very readable, but the effect of the data is a modulation, not a different subject.

**Caveat 3: no training-seed noise floor.** I trained one model per set. Some of the differences could come from training randomness alone; a second seed of `random_uniform` would measure that (about 92 min).

**Where the dreams leave the archive.**
- Ranked by colour signature against 50,000 real crops, the most foreign dreams are 20–36× further from any real crop than real crops are from each other. Almost all of them come from the **random-tile model**: terracotta, salmon, rust, glacier-cyan.
- The path-trained models leave the archive through *structure* instead: sharper, more fractured ice and shadow shapes than any real 64 px crop.

**One line per model (descriptive):**
- `path_weighted`: bright snowfields, blue shadows and glacier tongues, brown scree; a few flat dark-sea squares. The most varied.
- `path_uniform`: the same alpine vocabulary, a little darker and greyer; more water-blue.
- `random_uniform`: the same compositions as the path models, but warmer and more saturated (ochre, rust, pink-tinted snow, cyan water). Some farmland texture. Far more snow than its data.

### myopic_s0: replicates baseline

- **No memorisation.** Detailed samples have median RMSE 26–39 to their training data, vs 17–20 for unseen real crops. 1–2 samples per model come closer than the closest unseen crop: 1.7–3.9 %, the same rate as baseline.
- **`path_weighted` vs `random_uniform`, in noise-floor sd:**
  - samples: colour JS 1.4× floor p95, brightness +1.4 sd, saturation −2.9 sd, diversity +2.1 sd;
  - real crops: brightness +2.9 sd, diversity +5.0 sd.
  - Same direction and similar size as baseline.
- **Composition is again flattened.** Random set: 11 % bright in the data, 36 % in the samples. The weighted path set is slightly *under*-produced: 45 % in the data, 39 % in the samples.
- **`path_weighted` vs `path_uniform` is the smallest difference:** JS 0.4× floor, every statistic within ±1 sd. **For myopic, the weighting changed nothing measurable.**

One line per model:
- `path_weighted`: alpine snow, blue shadow and rock, nearly indistinguishable from baseline's `path_weighted`.
- `path_uniform`: the same, slightly greyer.
- `random_uniform`: warmer and more saturated, with cyan water, rust and pink-tinted snow; more farmland green.

### Across agents: the decisive comparison

| same-noise RMSE (lower = more alike) | |
|---|---|
| baseline vs myopic, `random_uniform` (two different random tile sets, 85 tiles shared) | **12.4** |
| baseline vs myopic, `path_weighted` / `path_uniform` | 13.3 / 11.3 |
| within an agent, `path_uniform` vs `path_weighted` | 15.6–24.6 |
| within an agent, **path vs `random_uniform`** | **23.7–31.9** |
| unrelated samples (different noise) | 85–102 |

The two random-set models act as a **data-resampling noise floor**. Path-trained models differ from random-trained ones by about 2.5× that floor, in both agents. So **what the hike *selected* visibly changes the dreams, and the effect replicates. What the hike *emphasised* (the weighting) is close to or below the floor.** Baseline's and myopic's paths share 171 tiles and are dreamed almost identically. At this resolution and training length, the two agents' "tastes" are the same taste: snow and shadow.

## Gate 2 verdict: **PASS, narrowly**

- `path_weighted` differs from `random_uniform` on colour distribution, saturation and diversity in both agents. The difference exceeds both the batch-sampling floor and the data-resampling floor, and the models do not memorise.
- **Selection** carries the effect: the agent walked to the Alps. **Weighting** carries little: surprise weights clipped to [0.2, 5] change little on top of selection, and boredom weights change almost nothing.
- **The dreams compress the data's differences.** All models over-produce bright snow, and the random-tile model invents saturated colours that do not occur in the region (`notes/img/dreams_far/`).
- **Not measured:** variance from the *training seed* (init and noise). All models share one seed, which also couples them, as the cross-agent table shows.

## What to build properly (recommendations)

1. **The walk is worth building.** Gate 1 passed clearly, and the dwell-and-episode structure of the paths is the most promising "dramaturgy" result so far.
2. **Fix what curiosity is measured against** before tuning temperaments:
   - snow texture beats the 272k-parameter AE, and that drives every agent's taste;
   - deep sea gives easy "progress" through forgetting.
   - Options: a larger or slower perception model; novelty in a normalised latent; a learning-progress window that discounts re-learning of forgotten content, or keeps it on purpose and names it nostalgia.
3. **Make boredom matter:** it is rare after warm-up and its weight in the dataset is negligible. Try boredom relative to the agent's own recent interest instead of the running mean, or "time since something was interesting".
4. **Dreams:**
   - Train longer, or use a stronger generator, so samples follow their data's composition.
   - Add a second training seed per set.
   - Compare agents whose paths actually differ in terrain. Baseline and myopic both chose snow; an agent pushed away from snow, or a different region, would test whether a hike can *dream differently*, not just select differently.
5. **Infrastructure:** never run analysis on the GPU during training (−1.7 h today). Keep notebook output small. Commit the run configs and logs together.

### Lessons for building this properly
- Train longer, or with a larger model, before drawing conclusions from the dreams. At 15k steps the samples don't yet match their data's composition, which is the property this comparison relies on.
- Add a second-seed control per set.
- Never share the GPU during training. Analysis jobs running beside the trainer pushed it into shared memory and slowed it 17× (≈1.7 h lost).
