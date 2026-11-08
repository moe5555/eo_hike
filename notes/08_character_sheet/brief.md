# Brief: round h0311, towards a character sheet

Superseded (added 2026-11-08). Stage 1, with its seeds 4–7, is the last stage run on this walker. Stages 2 and 3 are replaced by the new navigation (compass offers at a radius set by the drive, no long jumps). Where each of their questions went is in log.md, 2026-11-08. The character sheet stands for this walker's scorer at 1,000 steps from Paris.

> **Naming (added 2026-11-04).** Written before the naming convention in `notes/README.md`. This round is experiment 08: run and config names start with `e08_` where the brief says `h0311_` (e.g. `e08_knn_3_s0`, configs in `configs/08_character_sheet/`), `analysis/sheet/` is `analysis/e08/`, its CSVs and figures go to `notes/08_character_sheet/results/`, and `notes/observations_h0311.md`, `notes/log_h0311.md` are `notes/08_character_sheet/observations.md`, `log.md`. The rest of the brief is as written.

Context first, then the design, then the walks in the order to run them. Report after Stage 0 and after Stage 1 before going further.

## The goal

A **character sheet**: a short list of settings, and for each one a plain statement of what it does to the agent, both to what it sees (perception, taste) and to how it moves through the world (rhythm, returns, range). Every statement should be backed by walks that show the effect is larger than what changing the seed alone would do.

The sheet has three sections, and every walker setting belongs to one of them:

| Section | Setting (config key) | In character terms |
|---|---|---|
| **Eye** (what it can see and learn) | `crop_px` | scale of attention: 32 ≈ 1.3 km, 64 ≈ 2.6 km, 128 ≈ 5 km |
| | `ae_width` | capacity: how much it can hold |
| | `update_steps` | learning speed: how fast a tile becomes familiar |
| | `buffer_size` | memory: how much it replays, so how fast it forgets |
| **Taste** (what counts as interesting) | `w_n`, `w_g`, `w_e` | what it values: novelty, learning progress, being hard to draw |
| | `k_nn` | habituation: how many visits until a tile feels familiar |
| | `ema_alpha` | attention span: how far back "recently" reaches when it judges interest (0.02 ≈ 50 steps) |
| **Temperament** (how it acts on taste) | `temperature` | decisiveness: how firmly it takes the best option |
| | `patience` | how long it tolerates dull surroundings |
| | `p_long_jump` | wanderlust: how often a far place is offered |
| | `radius_km` | stride: how far a neighbour is |
| | `return_cost`, `no_backstep` | aversion to going back |

## Where we are

What earlier rounds already say about each setting (`notes/06_characters/observations.md`, `notes/07_film_arc/observations.md`):

| Setting | Known | Gap |
|---|---|---|
| `patience` | 0.3 (Bored) triples teleports and halves time per place; teleports come in bursts of rejected landings | 0.8 was only tested together with `p_long_jump` 0 (Localist), so the two are confounded |
| `p_long_jump` | 0.2 (Globalist) gives many short places; far tiles are taken at chance | tested from Milan with the old random streams, 2 seeds |
| `lr` | 3e-3 killed one network (seed 1, step 142) | learning speed untested by any safe lever |
| `ae_width` | 0.5 and 2: no clear difference | one seed each |
| scorer on/off | removing it cuts places to a third (null walker) | does the scorer cause the boredom, or does the rule just never fire? (null with patience 0.3) |
| landing best-of-k | changes little | done; not repeated |
| `w_n`, `w_g`, `w_e`, `k_nn`, `ema_alpha`, `temperature`, `crop_px`, `buffer_size`, `radius_km`, `return_cost`, `no_backstep` | nothing on the planet walker | everything |

Three findings shape the design:

1. **Characters differ in rhythm, not in coverage.** Unique tiles, revisit share, held-out error and colour diversity barely separate characters. Places, steps per place and teleports do (29.10, finding 1).
2. **Where a teleport lands is the largest source of noise.** Ocean share spans 0–39 % between reference seeds. Any "taste" measured as *what the walker ended up on* is mostly landing luck.
3. **The first ~150–500 steps are a young network.** Over half of all teleports, most rejected landings and the whole of the appetite signal fall there (h0111, findings 10, 14). A trait seen in 1,000 steps may be a trait of youth.

## How to attribute an effect to a setting

**One setting at a time, from the Reference.** Every new walk is `configs/07_film_arc/h0111_reference.yaml` with one key changed: Paris, 1,000 steps, `rng_mode: split`, `log_prev_error: true`. This lets the existing h0111 runs (Reference, Null, Bored, landing variants; seeds 0–3) sit on the same sheet without rerunning them.

**Compare by seed, in pairs.** Under `split`, two walks with the same seed share the network's starting weights, the far offers and the teleport landing tiles. Checked on the h0111 runs: in all four seeds, the n-th teleport of Reference, Bored and Null lands on the same tile. So the main noise source is shared within a seed. For every readout, report the paired difference `setting_s − reference_s` for each seed, its mean and its range, not just the two means.

**Two strengths of evidence:**

- **Lead:** all four paired differences have the same sign, and the mean difference is larger than half the spread of the Reference across seeds.
- **Result:** a lead that holds when seeds 4–7 are added (at least 7 of 8 paired differences with the same sign).

Only results go on the sheet as statements. Leads go on it marked as leads. A setting that shows nothing goes on it as "no measurable effect between X and Y at 1,000 steps", which is also worth knowing.

**Readouts that don't depend on landing luck.** Alongside the rhythm measures, measure taste as a **selection differential**: at each step, the chosen tile's property minus the mean over the tiles on offer at that step. `candidates.parquet` logs every candidate, so this needs only per-tile pixel statistics. Because it compares the choice with what was available at that very moment, it does not care where the walker happens to be.

**Two phases.** Report every readout for steps 0–149 ("young") and 150–999 ("settled") separately, as well as for the whole walk.

## Ground rules

- No walker code changes are needed: every setting above is already a config key. If one becomes necessary, it goes behind a config option whose default reproduces existing runs.
- Before any walk, add dated predictions to `notes/06_characters/expectations.md` (new section "Round h0311"). The "first guess" column below is a starting point, not a substitute.
- New run names start with `h0311_`, in the form `h0311_<setting>_<level>_s<seed>`, e.g. `h0311_knn_3_s0`. Never overwrite existing runs.
- Mac CPU, three walks side by side, using `scripts/hikes_0311.sh`, a copy of `scripts/hikes_0111.sh` with its disk and `.git` watchdog. Large outputs (films, `hike.html` pages) go under `runs/`, never in a folder git can see (see `notes/07_film_arc/log.md`, the incident).
- Report in the style of `notes/07_film_arc/observations.md`: tables first, numbered findings in plain language, a table against expectations, then "for the next round".

## Long jumps and teleports stay blind this round

The walker's far offers and teleport landings are random draws, and this round keeps them so. Giving the jumps a rationale (a preference, a rhyme with places it liked, a break with them, or a language model's sense of what places mean) is the likely next step, but it does not need deciding now:

- **Blind jumps are the control any rationale must beat**, as the null walker was for the scorer. They are needed anyway.
- **Under `split` they are already the same jump for everyone with the same seed.** At the same `p_long_jump`, the far tile offered at step n is the same for every walker of that seed, and the n-th teleport lands on the same tile. What differs is whether and when a walker takes them, which is its character. Four seeds give four different itineraries, so no result rests on one set of places. One exception: the far tile is drawn only when an offer happens, so walkers with a different `p_long_jump` are offered different far tiles. For those, compare offers by count, not by tile.
- **A rationale needs preferences that can be stated.** The taste panel and selection differentials of this round are where those come from.
- **Only part of the sheet depends on how jumps work.** Eye and Taste readouts (the panel, choices within a place) do not. Rhythm readouts (places, teleports, rejected landings, far tiles taken) do, and will need measuring again once jumps get a rationale.

## Stage 0: build the readouts and calibrate them (offline, no walks)

### 0.1 The sheet readouts

`analysis/sheet/readouts.py`: one row per run (and per phase), plus the paired differences against the Reference of the same seed.

| Group | Readout | Notes |
|---|---|---|
| Rhythm | places, median and longest steps per place, steps before first jump | definitions as in h0111 |
| | teleports, share in bursts, rejected landings | |
| | far tiles taken ÷ chance of taking them blind | chance = 1 ÷ number of candidates at that step |
| Returns | revisit share minus a blind walker's expected revisit share on the same steps | blind expectation = share of the candidates already visited (`notes/06_characters/reflection_revisits.md`) |
| | straight-back share minus its blind chance | blind chance = 1 ÷ number of candidates |
| Taste (selection differentials) | texture (mean gradient), contrast (grey-level spread), grey-level entropy, brightness (snow, ice, cloud), saturation, ocean | per-tile statistics computed once and cached |
| | top-scoring tile chosen | against blind chance |
| Learning | held-out error at steps 250, 500, 1,000; step where the appetite ends | held-out compares only between walks of the same `crop_px` (the held-out crops depend on it) |
| Coverage | unique tiles, ocean share, colour diversity | kept for continuity; known to separate little |

### 0.2 The taste panel

A fixed set of about 300 tiles, scored by every walker's own network. This is the readout closest to "how the agent sees the world", and it is identical for all walkers, so it is free of path and landing luck.

- Choose the tiles once, stratified by `cover` (land, coast, ocean) and by quartile of texture and brightness, from tiles that none of the existing h0111 walks visited. Save the list as `analysis/sheet/panel.csv` and never change it.
- For each run and each checkpoint (`ckpt_0250` … `ckpt_1000`), rebuild the archive up to that step from the visited tiles in `steps.parquet`, embed them with that checkpoint, and compute surprise, novelty and progress for every panel tile.
- Summarise per stratum: which kinds of terrain does this walker find most novel, most hard to draw, most learnable, at each age?
- Taste similarity: rank correlation of panel interest between every pair of walkers. Two walkers with the same taste rank the panel alike, wherever they walked.

### 0.3 Calibrate on the runs that exist

Run 0.1 and 0.2 on the h0111 Paris runs (Reference, Null, Bored, and the four landing variants, seeds 0–3). Report:

- which readouts separate **Null from Reference** (any readout that cannot see the scorer cannot see taste),
- which separate **Bored from Reference** (a known temperament effect),
- the paired spread of each readout, and from it how large an effect four seeds can detect.

### 0.4 Optional: where would a reason have taken it? (offline)

A first look at jump rationales, without changing the walker. At each real teleport of the h0111 Reference and Bored walks, draw 50 random tiles and score them with the walker's network at that step (nearest checkpoint, archive up to that step). Record which tile each rule would have picked:

- **rhyme:** closest in latent to the walker's favourite tiles so far (most visits);
- **fracture:** farthest from everything in its archive (the most novel);
- **blind:** the tile it actually landed on.

Compare the three on terrain (cover, texture, brightness) and on how the walker's network rates them. Do this last, and only if Stage 0 is otherwise done.

**Report here.** Drop or redefine readouts that see nothing, before any new walk.

## Stage 1: one setting at a time (48 + 28 + 26 walks)

All seeds 0–3 unless stated, each paired with the h0111 Reference of the same seed. At about ten walks an hour (three side by side, ~17 min each), tier 1 is an evening, tiers 2 and 3 another each.

### Tier 1: taste and decisiveness (never tested on the planet walker), plus the noise floor

| Config | Change from Reference | Question | First guess |
|---|---|---|---|
| `h0311_reference_s{4..7}` | seeds 4–7 | how large is the seed spread? | – |
| `h0311_novelty_only` | `w_g: 0` | how much of the walker is novelty alone? | close to the Reference: the favourites' lead comes almost entirely from novelty (`notes/06_characters/reflection_revisits.md`) |
| `h0311_progress_only` | `w_n: 0` | what does learning progress choose on its own? | weaker texture preference, rhythm between Null and Reference |
| `h0311_surprise` | `w_e: 1` | does "hard to draw" attract when it is allowed to? | stronger texture, contrast and brightness preference; longer stays on rough terrain; a trap on high-contrast snow is possible |
| `h0311_knn_3`, `h0311_knn_30` | `k_nn: 3`, `30` | does faster habituation cut returns? | k=3: fewer revisits and straight-backs over chance, more tiles; k=30 the reverse |
| `h0311_ema_005`, `h0311_ema_08` | `ema_alpha: 0.005`, `0.08` | what does the length of "recently" do to boredom? | 0.005 (~200 steps, cumulative for the first 200): fewer early teleports, more late ones; 0.08 (~12 steps): fewer teleports, longer places |
| `h0311_temp_02`, `h0311_temp_10` | `temperature: 0.2`, `1.0` | decisiveness | 0.2: top tile chosen over 80 %, more straight-backs over chance; 1.0: drifts toward Null, so *fewer* places |
| `h0311_crop_32`, `h0311_crop_128` | `crop_px: 32`, `128` | does the scale of attention change taste? | 32 favours fine texture (fields, roofs); 128 favours relief and coastlines |

44 new walks plus the 4 reference seeds. Notes:

- `w_e: 1` with `w_n` and `w_g` still at 1 adds surprise rather than replacing the others, so it answers "what does adding it change". If the effect is large, a surprise-only walker (`w_n: 0, w_g: 0`) follows in tier 2.
- `ema_alpha` sets both what counts as an interesting candidate and when boredom fires. Read its effect on rhythm together with `patience`; Stage 2 tests the pair.
- `crop_px` changes the held-out crops, so compare its learning curve only with itself. Use the taste panel instead.

### Tier 2: temperament and learning, on the same footing

| Config | Change from Reference | Question | First guess |
|---|---|---|---|
| `h0311_patience_08` | `patience: 0.8` | patience alone, separated from the Localist's other change | 0–2 teleports, a few long places; far offers still taken |
| `h0311_farjump_0`, `h0311_farjump_02` | `p_long_jump: 0`, `0.2` | wanderlust alone, from Paris with split streams | 0: fewer places, all via boredom; 0.2: as the Milan Globalist, many short places. Far tiles offered differ from the Reference's (see "Long jumps"), so compare offers by count |
| `h0311_update_1`, `h0311_update_12` | `update_steps: 1`, `12` | learning speed, without touching `lr` (the progress probe keeps its meaning) | 1: tiles stay novel longer, longer stays, more returns; 12: restless. Watch for a dead network (held-out frozen near 0.25) |
| `h0311_null_patience_03` | `choice: uniform`, `patience: 0.3` | does the scorer cause boredom, or does the rule simply fire more at 0.3? | open; this is item 2 of the last round's list |

28 walks.

### Tier 3: memory, capacity, stride and returns

| Config | Change from Reference | Question |
|---|---|---|
| `h0311_buffer_512`, `h0311_buffer_8192` | `buffer_size` | does a short memory create "nostalgia" returns to forgotten terrain (v1, finding 3)? |
| `h0311_width_05`, `h0311_width_2`, seeds 1–3 | `ae_width: 0.5`, `2` | capacity, with the s0 runs of h0111 making four seeds |
| `h0311_radius_25` | `radius_km: 25` | stride; about twice the candidates, so about twice the run time |
| `h0311_returncost_05` | `return_cost: 0.5` | aversion to returning, gradual |
| `h0311_nobackstep` | `no_backstep: true` | aversion to returning, absolute |

26 walks (about 3.5 hours because of width 2 and radius 25).

**Report here**, with the knob-to-effect matrix (below) filled in for Stage 1. Then run seeds 4–7 for every lead, before Stage 2.

Amended 2026-11-08: seeds 4–7 for seven settings, not every lead. Stage 2 is not run (see the note at the top), so seeds 4–7 now serve only to confirm what carries over to the new navigation. Walk the settings whose effect does not depend on how jumps work:

Setting	Change from Reference	Why
progress only	w_n: 0	novelty carries the returns (Stage 1, finding 1)
surprise added	w_e: 1	texture and contrast in choice, against the Reference offset (findings 3, 8)
habituation	k_nn: 3, 30	habituation sets the returns (finding 1)
decisiveness	temperature: 0.2, 1.0	the cleanest knob on choice (finding 2)
learning speed	update_steps: 12	held-out error and returns only; its rhythm effects are not carried over (finding 5)

Seeds 4–7 each: 28 walks, about 3–3.5 h with three side by side. Each is judged by the result rule against the Reference's seeds 0–7: at least 7 of 8 paired differences with the same sign, and the mean difference larger than half the Reference's range over the eight seeds.

Not walked:

far jumps 0.2 and 0, and ema_alpha 0.005: their leads are on rhythm, which the new navigation replaces;
crop_px 32 and 128: their leads follow the Reference's seeds 0–3 offset (finding 8);
return_cost 0.5, no_backstep and radius_km 25: to be retested if the new walker keeps them;
the single small leads of the other settings.

## Stage 2: interactions (about 32 walks)

One setting at a time can't tell whether two settings add up or interfere. Take the three or four settings with the largest results from Stage 1 and run them as a 2×2×2 design (two levels each, every combination, four seeds). Pairs worth including if both pass Stage 1:

- `patience` × `ema_alpha`: both decide when boredom fires.
- `crop_px` × `w_e`: does the eye change what "hard to draw" means?
- `temperature` × `k_nn`: decisiveness against habituation, both acting on returns.

Choose the levels at the ends of the range where Stage 1 showed an effect. Report each setting's effect at both levels of the other: if it holds at both, the sheet can state it alone; if not, the sheet states the condition.

## Stage 3: long walks

Traits seen in 1,000 steps may belong to a young network. Assemble two or three contrasting characters from the Stage 1 and 2 results and walk each for 5,000 steps from Paris, seeds 0–2. Add `configs/07_film_arc/h0111_walk_5k.yaml` (Bored at 5,000 steps), seeds 0–3, in the same batch: whether walks end by settling is still the open question from the last round (h0111, "for the next round", item 1). Read the sheet readouts per 1,000-step block and say which traits last and which fade.

## Deliverables

1. **The knob-to-effect matrix** (`analysis/sheet/matrix.csv` and a figure): rows are settings and levels, columns are readouts, cells give the paired effect in units of the Reference's seed spread, marked result, lead or none. This is the answer to "which values are responsible for what".
2. **One sheet per character**, in this form:

   ```
   Character: <name>
   Settings: <changes from Reference>
   Eye:        <what it draws well and badly, from the taste panel>
   Taste:      <what it chooses over what is on offer, from the selection differentials>
   Rhythm:     <places, time per place, teleports, rejected landings>
   Returns:    <revisits and straight-backs beyond chance>
   Over time:  <what changes between young, settled and, if walked, late>
   Evidence:   <result / lead for each line, with seeds>
   ```

3. `analysis/sheet/` with the scripts, `panel.csv`, the readouts per run, and figures.
4. `notes/observations_h0311.md` and `notes/log_h0311.md`, in the usual style.
5. Updated `notes/06_characters/expectations.md`, and the character table in `notes/agents_paper/agents_paper.typ` once there are results.

## Budget

| Stage | Walks | Time |
|---|---|---|
| 0: readouts, taste panel, calibration | none | analysis only |
| 1, tier 1 | 48 | ~5 h |
| 1, tier 2 | 28 | ~3 h |
| 1, tier 3 | 26 | ~3.5 h |
| seeds 4–7 for leads | ~30–50, depending | ~3–5 h |
| 2: interactions | ~32 | ~3.5 h |
| 3: long walks | 10–13 at 5,000 steps | ~5 h |

Tile cache: keep the 30 GB cap. All walks start from Paris on the same random streams, so many tiles are already cached.

## Out of scope

Dreams and image generation, the narrator, pretrained embeddings, new data sources, and the film. Changes to the walker's rules are out of scope unless the existing keys can't express a setting the sheet needs.
