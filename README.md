# hiker

Agents ("hikers") that walk through a finite archive of satellite image chips with no
goal except to keep seeing things unlike what they have already seen. Novelty search
in the sense of Lehman & Stanley (2008), run as a plain algorithm over image
embeddings. The output of a run is a sequence of images and a JSON log of the walk;
the log is the deliverable, the images are a by-product.

Status: Phase 2 (patch-novelty heatmaps) done; the dream (a generated epilogue, see section 8) built on the debug archive. See `docs/datasets.md` for the archive survey,
`docs/decisions.md` for every non-obvious choice, `docs/log-schema.md` for the log.

## Install

Python 3.12 via [uv](https://docs.astral.sh/uv/). The project pins a CUDA 12.8 build
of PyTorch for the RTX 4070; on a CPU-only machine edit the `[tool.uv.index]` block in
`pyproject.toml` or let uv fall back.

```powershell
# from the repo root
$env:UV_PROJECT_ENVIRONMENT = ".venv"     # only needed if you have that variable set globally
uv sync --extra dev
uv run pytest
```

Data goes under `./data` by default. Set `HIKER_DATA_ROOT` or `data_root` in the
config to put it elsewhere. Nothing is hard-coded.

## Run

```powershell
uv run python run.py --config configs/debug.yaml            # ingest -> embed -> index -> hike
uv run python run.py --config configs/debug.yaml --stage hike --set agents.seed=8 --set agents.temperature=0.3
uv run python run.py --config configs/debug_clip.yaml       # same archive, CLIP encoder
uv run python baseline_fps.py --config configs/debug.yaml   # farthest-point baseline
uv run python run.py --config configs/debug.yaml --stage heatmap --run runs/<dir>   # patch heatmaps for a finished run
uv run python run.py --config configs/debug_dream.yaml --stage dream-train              # fine-tune the generator once per archive
uv run python run.py --config configs/debug_dream.yaml --stage dream --run runs/<dir>   # the agents dream at the end of that run
```

Every stage is cached: the manifest, the embeddings (per encoder) and the index are
only computed once per dataset key. `--force` recomputes the selected stage. Each hike
writes `runs/<timestamp>_<config-hash>/` with `config.yaml`, `log.jsonl`,
`summary.json`, `novelty_curve.png` and `sequence/agent_<id>/`. With `heatmap.enabled`
(default) the heatmap stage then adds `<step>_<chip>_heat.png` next to every sequence
image, `patch_novelty_agent_<id>.npz`, `heatmap.json` and `heatmap_sheet_agent_<id>.png`.

Configs:

| File | Archive | Purpose |
|---|---|---|
| `configs/debug.yaml` | SSL4EO-S12 v1.1 validation split, RGB, 8,704 chips | end-to-end debug, full metadata |
| `configs/debug_clip.yaml` | same | the CLIP contrast |
| `configs/debug_taste.yaml` | same | debug walk with a taste vector (`agents.taste`, see `docs/decisions.md`) |
| `configs/majortom_sample.yaml` | Major TOM, 30 fragments | adapter check, eyeball the archive |
| `configs/majortom.yaml` | Major TOM, 2,500 fragments → ~40k chips | real runs |
| `configs/eurosat.yaml` | EuroSAT RGB, 27k chips, no metadata | 95 MB smoke test |

## How it works

This section is for someone who has not used embeddings or a vector index before.

### 1. An embedding is a fixed-length description of an image, as numbers

The encoder is a neural network that has already been trained (we do not train
anything). You give it an image, it gives back a list of a few hundred numbers, the
*embedding*. Two images that the network considers similar get lists that point in
similar directions. That is all an embedding is here: a point on a sphere, one per
chip, placed by the encoder's sense of resemblance.

"Similar" depends entirely on what the network was trained on. The Earth-observation
encoder (DOFA, trained on satellite imagery across sensors) has learned that two
fields with different crops are near each other and a field and a harbour are far.
CLIP, trained on internet photos and captions, has a different sense of what matters.
Running the same walk under both is one of the project's comparisons, not a detail.

We L2-normalise every embedding, which means we scale it to length 1. After that the
*cosine similarity* of two chips is just the dot product of their vectors, a number
between −1 and 1, and the *cosine distance* is `1 − similarity`, between 0 and 2. All
"distance in embedding space" below means this cosine distance.

One correction is applied first. Straight out of these networks, every satellite
chip's vector points in nearly the same direction (they share a large common
component), so all distances are tiny and nearly equal and "more novel" stops
meaning anything. We subtract the archive's mean vector and renormalise. That
removes the shared part and leaves the differences. It is the one step where a
chip's embedding depends on the archive it sits in; `docs/decisions.md` finding 2
has the measurements.

### 2. The index answers "which chips are closest to this one?"

With 40,000 chips, asking "which 50 are nearest to chip X?" means computing 40,000 dot
products. A FAISS index is a data structure that stores all the vectors and answers
that question fast. We use the *exact* kind (`IndexFlatIP`): it really does compute
every dot product and returns the true top-k. That is deterministic and, at this
scale, sub-millisecond. Approximate indexes would be faster still but introduce their
own randomness, which is exactly what we do not want in a reproducible walk.

The index is built once per archive and encoder and saved next to the embeddings.

### 3. Novelty, operationally

An agent carries a private *history*: the embeddings of every chip it has visited.
The novelty of a candidate chip is

> the average cosine distance from the candidate to the `j` history entries closest
> to it (default `j = 15`; if the history is shorter, all of it).

Read that carefully: novelty is distance to the *nearest* things already seen, not to
the previous chip and not to the average of everything. A chip that closely resembles
even a handful of past chips scores low, however different it is from the rest of the
walk. That makes novelty a property of the whole walk so far. It is the standard
"sparseness" measure of novelty search.

### 4. How one step is chosen

1. Ask the index for the `k = 50` nearest neighbours of the current chip. These are
   the local moves: places that look like where the agent is.
2. Add `m = 5` chips drawn at random from the whole archive. These are long-range
   jumps: a way out of a region the agent has used up.
3. Remove anything already in this agent's history.
4. Score every remaining candidate with the novelty above.
5. Choose by softmax over the scores with temperature `T = 0.05`: each candidate's
   probability is proportional to `exp(score / T)`. With a tiny `T` the best
   candidate is chosen almost always (greedy); with a large `T` the choice is
   nearly uniform. `T` is the single dial for the agent's character.
6. Move, append to the history, write one log line.

Optionally the agent also carries a *taste vector* (`agents.taste`, off by default): an
exponential moving average of the embeddings that struck it hardest (novelty at or
above a threshold), weighted by how hard they struck. Candidates then score
`novelty + weight * cos_sim(candidate, taste)`, so the hiker is pulled towards what
resembles its strong encounters while novelty keeps pushing it off what it has seen.

A random jump can only win if its novelty beats the local options after softmax, so
jumps happen more when the neighbourhood is exhausted. Whether the chosen chip *was*
a jump is logged.

### 5. Why boredom is emergent, not coded

Nothing in the loop says "get bored". But every visited chip lowers the novelty of
everything that resembles it, and the agent keeps choosing the most novel thing
nearby, so the neighbourhood it is in gets used up. Novelty scores fall. The
`m` random jumps occasionally land somewhere fresh and novelty spikes again, then
the same thing happens there. Over a run the curve trends down with jumps, and once
the running mean over the last `w = 20` steps drops below `boredom_threshold` the
run stops and records that it stopped for that reason. The threshold only decides
*when to stop looking*; the decline itself comes from the mechanism.

How fast it declines depends on how big the archive is compared with the walk. On
the 8,704-chip debug set a 300-step walk settles near 0.65 and would need about
3,000 steps to reach the default threshold of 0.4, so short runs end at `max_steps`.
That is expected, and the stop reason is in `summary.json` either way.

### 6. The baseline

`baseline_fps.py` runs farthest-point sampling: at each step, over the *entire*
archive, take the chip whose distance to the nearest already-selected chip is
largest. It is the same idea with every constraint removed: no locality, no
randomness, no per-agent history, no path through the archive. Its log uses the same
schema so the two can be set side by side. What the hiker adds is exactly the
difference between those two logs.

### 7. The heatmap is the same score, per patch

A vision transformer such as DOFA does not look at the chip as one thing. It cuts it
into a 14 x 14 grid of 16-pixel patches, turns each into a vector, and the chip's
embedding is the mean of those 196 vectors. So the patch vectors are already there,
and we can ask the agent's own question of each one: how far is this patch from the
`j` nearest patches among all the patches of the chips I have already visited?

That number, per patch, is what the heatmap shows. It is not an explanation produced
by a second model looking at the first (Grad-CAM and its relatives do that). It is
the agent's novelty score at a finer grain, so a hot patch is hot for exactly the
reason the chip was chosen. Tint starts at the 75th percentile of all patch scores
in the run, so three quarters of all patches show the plain image, and "hot" means
hot for this walk, not for this chip. `docs/decisions.md` (finding 11) reports what
the first heatmaps showed, including a real discrepancy between the chip score and
the patch score.

### 8. The dream: the agent's score as the prompt

The brief said no image generation. The user overrode that on 2026-09-18 with one
restriction: the generated image is an **epilogue**. It is never added to the archive
or to the agent's history, and `log.jsonl` does not mention it. The walk stays real.

When a run ends (at boredom, or at `max_steps` if `dream.at_end` is on), each agent
produces an image that it, with its whole history, would score as particularly novel.
The hiker has no language, so there is no text prompt. Instead, the generator is a
Stable Diffusion 1.5 fine-tuned with a LoRA on the archive's chips *under the empty
prompt* (the text encoder runs once, for "", and is never used again), and at each
denoising step the current estimate of the finished image is decoded, embedded with
the same DOFA encoder that embedded the archive, scored with the agent's own
selection score (novelty against the history, plus the taste term if the run used
one), and the gradient of that score nudges the sample. The prompt is the score; the
history is the only thing that shapes the image.

Because the sample could in principle drift into something DOFA finds "novel" for
uninteresting reasons, every dream is measured honestly: the saved PNG is re-encoded
through the ordinary path and scored like a chip; a *control* with the same seed and
no guidance is scored the same way; and the *archive ceiling* (the most novel real
chip the agent never visited) is recorded next to it. `dreams.json` holds all of it.
The first runs showed why this matters: a plain pixel gradient produced adversarial
noise that raised the score without changing the picture. The score is therefore
averaged over random rotated, flipped and cropped views of the image, which only a
real change survives. `docs/decisions.md` finding 12 has the numbers and the sheets.

## Adding an archive or an encoder

- Archive: add `src/hiker/datasets/<name>.py` implementing `DatasetAdapter` (see
  `datasets/base.py`), register it, point `dataset.name` at it. Ingest turns it into
  PNG chips plus a manifest; nothing downstream changes.
- Encoder: add `src/hiker/encoders/<name>.py` implementing `Encoder`
  (`encoders/base.py`): a `name`, a `dim`, `encode(images) -> (B, dim)` L2-normalised,
  and `describe()` for `embed_meta.json`.

## Layout

```
run.py, baseline_fps.py        thin CLIs
configs/                       YAML configs; CLI --set overrides
src/hiker/
  config.py                    defaults, YAML + overrides, derived paths
  datasets/                    archive adapters (ssl4eo_s12_v11, majortom_thumbs, eurosat)
  encoders/                    dofa_base, clip_vit_b32
  ingest.py embed.py index.py  the cached pipeline stages
  scoring.py agent.py hike.py  the algorithm
  baseline.py io.py viz.py
tests/                         scoring, selection, agent determinism, io
docs/                          datasets survey, decisions, log schema
```
