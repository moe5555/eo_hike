# Brief: MVP "hiker" — agentic novelty search over a satellite image archive

This is a task brief for a coding agent. Read the whole thing before writing code.
Work in phases, stop at the checkpoints, and document as you go: the person reading
your output is a media artist and programmer who knows Python well but is new to
embeddings, FAISS and novelty search. Explain your choices in prose, not just in code.

---

## 1. What this is for

Part of an MA thesis and a short film. One or more agents ("hikers") move through a
large archive of satellite images. They have no goal. At each step a hiker picks the
next image because it is *unlike what it has already seen* — novelty search, in the
lineage of Lehman & Stanley (2008). The output is a sequence of images plus a full log
of the walk, which later drives an edit, a narration layer and a sound layer.

Design commitments already made, do not relitigate them:

- Each agent has a **private history**. Agents do not share what they have seen.
- The hiker is a **plain algorithm, not an LLM**. Language enters the project later, in a separate narrator component.
- The archive is **finite and real**. No image generation.
- Non-determinism is wanted, but must be **seeded and reproducible**.

Everything downstream (film edit, sound, explainability) reads the JSON log. The log is
the real deliverable; the images are a by-product. Treat its schema as an interface.

---

## 2. Phase 0 — dataset survey (do this first, then STOP)

No downloads over a few hundred MB before this is reviewed.

Produce `docs/datasets.md` comparing candidate Earth-observation datasets that are
already chipped (cut into small tiles) and freely downloadable. Starting candidates,
all of which you must verify against current sources — the information here may be out
of date:

- **EuroSAT** — Sentinel-2, ~27k chips, 64×64 px, tiny. Good for pipeline debugging only.
- **BigEarthNet** — Sentinel-2, large, comes with land-cover labels.
- **SSL4EO-S12 / SSL4EO-L** — Sentinel-1/2 and Landsat, globally sampled, designed for
  self-supervised pretraining; pretrained weights exist in **TorchGeo**.
- **fMoW**, **Satlas**, or anything else current that fits better.

For each, report: download size, number of chips, chip size in pixels, ground sample
distance (m/px), bands available, licence, and — critically — **what per-chip metadata
survives**: latitude/longitude, acquisition date, sensor. Metadata drives the sound layer
later, so a dataset that has lost its coordinates and dates is much less useful even if
it is otherwise ideal.

Also report **geographic spread**. A Europe-only archive produces a Europe-only walk.
Global coverage matters more than raw size.

Recommend one small dataset for debugging and one mid-sized one (target: roughly
30k–60k chips, on the order of 5 GB) for real runs. Say what you would pick and why.
Then stop and wait.

---

## 3. Phase 1 — the MVP hiker

### 3.1 Pipeline

Four steps, each resumable and cached. Never recompute embeddings that already exist.

1. **`ingest.py`** — walk the dataset, write `manifest.parquet` (or CSV):
   `chip_id, path, lat, lon, date, sensor, source_dataset`. Missing fields are null, not
   invented. Report coverage stats (what fraction has coordinates, dates).
2. **`embed.py`** — run a pretrained encoder over every chip, write `embeddings.npy`
   (float32, N×D, row order matching the manifest) plus `embed_meta.json` recording model
   name, weights, version, preprocessing and D.
3. **`index.py`** — build a FAISS index. At this scale `IndexFlatIP` over L2-normalised
   vectors (cosine similarity) is correct; do not add approximate indexing, it is not
   needed and it would add a second source of randomness.
4. **`hike.py`** — run the agents, write the outputs in §3.4.

### 3.2 Encoder

Prefer an **Earth-observation pretrained encoder** (TorchGeo's SSL4EO weights, or a
comparable current model). Include **OpenAI CLIP ViT-B/32 as a second, selectable
encoder** — not because it is appropriate, but because it is a useful contrast: CLIP's
notion of similarity comes from captioned internet images, the EO model's from satellite
data. Being able to run the same hike under both is a research result, not just an option.

Define the encoder behind a small interface so more can be added later:

```python
class Encoder(Protocol):
    name: str
    dim: int
    def encode(self, images: list[Image]) -> np.ndarray: ...  # (B, dim), L2-normalised
```

Planned future encoders, so keep this clean: raw spectral-histogram features, Haralick
texture features, land-cover class statistics. Do **not** implement them now.

### 3.3 The agent loop

One step, in full:

1. From the current chip, retrieve **k nearest neighbours** in the index (default k=50).
2. Add **m random chips** from anywhere in the archive (default m=5) as long-range jumps,
   so the agent can escape a region it has exhausted.
3. Drop anything already in this agent's history.
4. **Novelty score** for each candidate: the mean cosine distance to its **j nearest
   entries in this agent's own history** (default j=15; if the history is shorter than j,
   use all of it). This is the standard novelty-search formulation — distance to the
   *archive of what has been seen*, not to the previous image.
5. Choose via **softmax over scores with temperature `T`** (default 0.1). `T→0` is greedy,
   higher `T` is more erratic. This is the single dial for "character".
6. Append the chosen chip to the history, move there, log everything.

Stop when either `max_steps` is reached (default 300) or the **running mean novelty over
the last `w` steps** (default w=20) falls below `boredom_threshold`. Record which
condition fired.

Multiple agents: run `n_agents` independently, each with its own seed, start chip and
history. Starts are random by default, or given explicitly in the config. Agents may
visit the same chip — that is expected and interesting; log it.

Everything named above is a config value, not a constant in the code. Use a single YAML
config plus CLI overrides.

### 3.4 Outputs

Per run, into `runs/<timestamp>_<config-hash>/`:

- `config.yaml` — the fully resolved config, including seeds and encoder version.
- `log.jsonl` — one line per step per agent. Schema:

```json
{
  "agent_id": 0,
  "step": 42,
  "chip_id": "ssl4eo_000123_4",
  "novelty": 0.3871,
  "novelty_running_mean": 0.4012,
  "rank_among_candidates": 3,
  "n_candidates": 51,
  "was_random_jump": false,
  "embedding_distance_from_prev": 0.2210,
  "geo_distance_km_from_prev": 8812.4,
  "time_delta_days_from_prev": -1460,
  "history_size": 42,
  "lat": -23.51, "lon": 133.88, "date": "2019-04-11",
  "temperature": 0.1, "seed": 7
}
```

  Null out geo/time fields when the dataset lacks them; never fabricate.
- `sequence/agent_<id>/0001_<chip_id>.png …` — the walk as ordered image files.
- `summary.json` — per agent: steps taken, stop reason, novelty curve, total distance
  travelled on the globe and in embedding space, time span covered, number of random
  jumps, and any chips visited by more than one agent (with step numbers).
- `novelty_curve.png` — novelty per step, one line per agent. Rough matplotlib is fine.

### 3.5 Baseline (small, but do it)

`baseline_fps.py`: greedy **farthest-point sampling** over the whole archive — repeatedly
take the chip furthest from everything already selected. It is the omniscient,
deterministic version of the same idea: no locality, no per-agent history, no path. Emit
the same log schema so the two can be compared. The point is to show what the hiker's
constraints actually add.

### 3.6 Acceptance criteria

- Two runs with the same config and seed produce byte-identical `log.jsonl`.
- Changing only the seed produces a visibly different walk.
- Novelty declines over a run (expect a noisy downward trend with jumps, not a smooth curve).
- Show progress bars. 
- `python run.py --config configs/debug.yaml` works end to end on the small dataset in
  under ten minutes on a laptop.

---

## 4. Phase 2 — patch-novelty heatmap (only after Phase 1 is reviewed)

If the encoder is a vision transformer, it produces one vector per image patch, not only
one per image. Compute novelty **per patch** against a bank of patch vectors from the
agent's history, and render a heatmap overlay per visited chip.

This is not a post-hoc explanation like Grad-CAM. It is the same quantity the agent acts
on, at finer resolution — which is worth stating clearly in the docs, because it is the
reason for choosing a plain algorithm over an LLM in the first place.

Outputs: `sequence/agent_<id>/0001_<chip_id>_heat.png` and per-patch scores in the log
(or a sidecar file, if the log gets unwieldy).

---

## 5. Phase 3 — mappings spec (a document, not an implementation)

Write `docs/SPEC-mappings.md` proposing, with defaults and justification:

- **Novelty → dwell time.** How long a chip stays on screen. Suggest a logarithmic
  mapping with explicit floor and ceiling (e.g. 0.4 s to 15 s). Machine time becomes human
  time here, so the function must be stated, not buried in an edit.
- **Log fields → sound parameters.** Which fields drive what: geo distance, time delta,
  embedding distance, novelty, history size, random-jump flag. SuperCollider is the target,
  via OSC.
- **Emit format.** Define a flat, OSC-friendly JSON derived from `log.jsonl`. Write the
  converter; do not write any SuperCollider code.

Distinguish clearly between **measured** fields (distances, dates, counts) and
**interpreted** ones (anything derived from a classifier). The distinction matters
conceptually and should be visible in the spec.

---

## 6. Engineering notes

- Python 3.11+, `uv` or venv, pinned `requirements.txt`. Likely: torch, torchgeo,
  faiss-cpu, numpy, pandas/pyarrow, pillow, rasterio, tqdm, typer, pyyaml, matplotlib.
- No hard-coded paths. Data root from config or env var.
- Set every seed (`random`, `numpy`, `torch`) and log them.
- Structure: `src/hiker/{ingest,embed,index,agent,scoring,io,viz}.py`, thin CLI in `run.py`,
  configs in `configs/`, notebooks nowhere.
- Type hints throughout; tests for the scoring function and the softmax selection at least.
- If a dataset download fails or a model's weights have moved, stop and report rather than
  silently substituting something else.

---

## 7. Documentation (part of the deliverable, not an afterthought)

- **`README.md`** — install, run, and a "How it works" section written in plain prose for
  someone who has not used embeddings or FAISS before. Explain in order: what an embedding
  is here, what the index does, what novelty means operationally, how a step is chosen,
  why boredom emerges from the mechanism rather than being coded in.
- **`docs/decisions.md`** — every non-obvious choice, with the alternative you rejected and
  why. Defaults for k, j, m, T and the boredom threshold belong here, including how you
  arrived at them.
- **`docs/log-schema.md`** — every field, its unit, its range, and whether it is measured
  or interpreted.
- Docstrings on all public functions, with the maths spelled out for the scoring code.

---

## 8. Checkpoints

Stop and report at each:

1. After the dataset survey (§2). Recommendation, no bulk download yet.
2. After the pipeline runs end to end on the small dataset, before scaling up.
3. After the first real run: the sequence, the novelty curve, and your own reading of
   whether the walk looks like anything.

Flag anything that seems conceptually wrong rather than working around it silently. If a
default produces degenerate behaviour — the agent oscillating between two regions,
novelty never declining, every candidate scoring identically — say so and describe the
behaviour before fixing it. Those failures are findings.