# Brief: next round after the 29.10 hikes

Context for this round, then the tasks in priority order. Work through them in order and stop at the marked checkpoints to report back before going further.

## Where we are

The 29.10 observations (Paris 1,000 steps, Paris 5,000 steps) changed the question. Characters differ in rhythm (number of places, steps per place), not in how much they see. The Bored walker in Paris shows an arc of its own: bursts of teleports, then ever longer stays, ending with 1,029 steps in the Patagonian ice fields. This is search followed by settling, not ageing. With interest rescaled against the last ~50 steps there is no long-term decline in the signal, so the falling teleport rate comes from terrain and landing luck.

There are now two candidate arcs for the film:

- **Emergent:** search by rejection, then settling on terrain the network cannot finish learning. Needs almost no engineering.
- **Designed:** appetite fades with age (log-scale error trend), cuts speed up, the walker grows indifferent.

They pull against each other. Appetite-scaled holds would compress the long stays, and novelty-chosen landings would remove the rejection bursts. **Do not change the walker's behaviour towards either arc in this round.** The goal is to get the evidence needed to choose between them, plus some baselines that are missing.

Working hypothesis to test: at this resolution and capacity, "interesting" mostly means "hard to draw". High-relief, textured terrain keeps the reconstruction error up, the learning signal persists, and the walker stays.

## Ground rules

- Do not modify or overwrite existing run outputs. New runs get new run names (prefix `h0111_`).
- Any change to walker code goes behind a config option. The defaults must reproduce existing runs. Verify this once by re-running the first 200 steps of `h2910` reference seed 0 and comparing paths.
- Before any new walk, add predictions to `notes/06_characters/expectations.md` (new section, dated) in the same style as before. Report against them afterwards.
- Walks run on Mac CPU. Keep new walks to 1,000 steps from Paris unless stated otherwise. For anything that depends on where teleports land, use seeds 0–3, not 0–1. Two seeds were too few last time.
- Report in the style of `notes/06_characters/observations.md`: tables first, then numbered findings, then a table against expectations, then "for the next round". Plain language and no jargon in the findings. Give numbers with ranges across seeds.
- Out of scope this round: inherited or pretrained embeddings, image generation and dreams, the narrator, and fixing the Fast learner (just note `lr` 3e-3 as unsafe in config comments).

## Tasks

### 1. "Interesting = hard to draw?" (offline)

Using the logs of all `h2910` runs:

- Split steps into those inside long stays (top 10% of places by length) and those inside short places (median length or less). Compare the reconstruction error of the chosen tiles, a texture measure (mean gradient magnitude, and grey-level entropy) and colour diversity.
- Check whether error on the tiles of a long stay stays high for most of the stay, or falls and the walker stays anyway.
- Rough labels are enough, from tile statistics or an existing land-cover lookup if one is already in the repo. Do not add new data dependencies for this.

### 2. What is novelty measured against? (read the code, report, change nothing)

Find exactly what novelty is computed against: the replay buffer (~128 steps), a separate archive, or something else, and how big it is. If it is the short buffer, say so plainly. Then novelty cannot fade by construction, and that needs to be known before treating "novelty never falls" as a finding about the planet.

### 3. Null walker and the scorer's real influence

Add a character `null`. It computes and logs all the same signals and trains its network the same way, but it chooses uniformly at random among the offered candidates. Teleports and long-jump offers work as in the reference, so the only difference is the choice.

- Run `null`, Paris, 1,000 steps, seeds 0–3.
- From the existing `h2910` logs (if the candidates and their scores are logged), compute for every character the distribution of the chosen candidate's rank under its own scorer, against the uniform distribution. If candidates are not logged, add logging and get this from the new runs instead.
- Compare `null` with the reference on places, steps per place, revisit share, straight-back share, ocean share, colour diversity and held-out MSE.

The question to answer: how much of each character's behaviour comes from its scoring and how much from the teleport and jump rules? Also, is the Globalist's chance-level acceptance of far tiles specific to far tiles, or are all of its choices near chance?

### 4. Separate random streams per decision

At the moment, changing one setting shifts every later random draw. That is why the Globalist jumped on step 1 in both Milan and Paris. Add an option `rng_mode: legacy | split`. In `split` mode, derive independent generators from the seed (for example `numpy.random.SeedSequence(seed).spawn(...)`) for:

- the first draw and the start position
- candidate sampling among neighbours
- long-jump offers
- teleport landing spots
- the choice itself (temperature sampling)
- network initialisation

`legacy` stays the default and must reproduce the old runs. Use `split` for every new run in tasks 4 and 6–8. Re-run task 4 under `split` if it was started before this was in place.

### 5. Straight-back steps (A→B→A)

About a quarter of steps go straight back, in every character. Find out why. For each A→B→A event, check:

- whether the error on A rose between the first visit and the moment of returning (interference: training on B made A hard to draw again), and
- whether A's score was high in absolute terms or only relative to the recent ~50-step baseline (a rescaling artefact).

If the logs do not have enough, instrument one 1,000-step Paris reference run (`split`, seed 0) to log the error on the previous tile after each update. Report the share of each cause.

### 6. Teleport landing variants (after Checkpoint A)

Add `teleport_landing: blind | best_of_k` with `k` configurable. `best_of_k` draws k random land-or-sea tiles from the planet, scores them with the walker's current network, and lands on the most novel one.

- Run the reference and Bored with `blind`, `best_of_k k=3` and `best_of_k k=8`, Paris, 1,000 steps, seeds 0–3, `split` mode.
- Report: teleports per walk, whether teleports still come in bursts, longest stay, spread of the ocean share across seeds, and number of places and steps per place.

The question to answer: how much search-by-rejection survives partial agency (k=3)? Does the variance between seeds narrow?

### 7. Appetite as a re-timing only (offline, no walker change)

On the two Paris walks:

- Compute a candidate appetite signal: the slope of a smoothed log reconstruction error (on held-out tiles if logged at enough steps, otherwise on recent chosen tiles), over a long window (try 200 and 500 steps).
- Produce two re-timed slideshows of the whole Bored Paris walk at matched total length (~10 min):
  - **A:** uniform hold per step, on a log-step clock (step *n* is shown at time proportional to log(n + c); pick c so the first 50 steps take roughly 1 minute).
  - **B:** the same clock, but with each tile's hold scaled by appetite.
- Do not use appetite in any walker decision.

These two cuts are what the person will compare against the emergent arc.

### 9. Eye size (optional, only if time remains)

Reference, Paris, 1,000 steps, seed 0, `split`, at the current autoencoder size and at roughly twice and half the latent and channel width. Compare the held-out error curves on a log scale, and where the curve flattens. The question: does a bigger eye age later? That would tell us whether the fade is about capacity or about having seen enough.

## Deliverables

- `analysis/h0111/` with scripts; CSVs and figures in `notes/07_film_arc/results/`
- `observations.md` (report)
- updated `notes/06_characters/expectations.md`
- the slideshows and contact sheets from tasks 1 and 8
- a short list of config options added, with defaults and a one-line description each
