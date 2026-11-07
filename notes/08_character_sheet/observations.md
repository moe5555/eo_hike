# Character sheet (round h0311): observations, Stages 0 and 1

The brief is `notes/08_character_sheet/brief.md`, decisions and deviations are in `notes/08_character_sheet/log.md`. Scripts are in `analysis/e08/`, tables and figures in `notes/08_character_sheet/results/`. Stage 0 is offline: no new walks. It uses the 28 h0111 Paris walks (Reference, Null, Bored, and Reference and Bored with best-of-k landings at k=3 and k=8; seeds 0–3, 1,000 steps, split streams).

Values are the mean of four seeds with the lowest and highest seed in brackets. **Young** is steps 0–149, **settled** is steps 150–999. **A seed SD** is how much one setting varies from seed to seed (pooled over all seven settings). **A lead** is the brief's rule: all four paired differences with the same sign, and the mean difference larger than half the Reference's range over seeds.

**The short version.** The readouts work, and they see the scorer clearly. They see temperament (Bored) in rhythm only, and taste weakly. Four seeds are enough for effects of about two seed SDs and no smaller. Pairing walks by seed helps much less than the brief expected, because two settings diverge from step 0 and after that behave like independent walks. The lead rule then fires by chance on about 1 readout in 11. Before Stage 1, the readouts should be cut to a fixed core of 17, so that a setting's leads can be told from chance (about 1.5 false leads per setting on 17 readouts, against 6–7 on all 74).

## The tables

### What the walk readouts see (`readouts.csv`, `calibration.csv`; whole walk unless marked)

| Readout | Reference | Null (chooses blindly) | Bored | Seed SD |
|---|---|---|---|---|
| places | 8.75 (4–14) | **2.75** (1–6) | **16.8** (14–23) | 4.7 |
| median steps per place | 103 (40–183) | **632** (155–1,000) | **21** (12–37) | 170 |
| teleports | 3.5 (1–7) | 0.5 (0–2) | **11.8** (7–20) | 4.2 |
| rejected landings | 0.75 (0–2) | 0 | **7.5** (2–15) | 3.0 |
| far tiles taken ÷ blind chance | 1.60 (0.43–2.42) | **0.51** (0–1.22) | 1.48 (0.86–1.99) | 0.59 |
| revisits beyond a blind walker | 0.18 (0.15–0.25) | **0.00** (−0.01–0.01) | 0.18 (0.16–0.21) | 0.03 |
| straight-backs beyond blind chance | 0.12 (0.10–0.14) | **0.00** (0.00–0.01) | 0.12 (0.09–0.14) | 0.02 |
| top-scoring tile chosen, beyond blind chance | 0.42 (0.40–0.45) | **−0.01** (−0.02–0.01) | 0.44 (0.41–0.46) | 0.02 |
| taste: snow, ice, cloud (settled) | **−0.35** (−0.49 to −0.26) | 0.02 (−0.10–0.16) | **−0.48** (−0.59 to −0.38) | 0.19 |
| taste: brightness (settled) | 0.34 (−0.05–0.64) | −0.02 (−0.06–0.02) | 0.21 (−0.03–0.44) | 0.33 |
| taste: saturation (settled) | −0.28 (−0.68–0.05) | 0.02 (−0.03–0.06) | −0.25 (−0.47 to −0.04) | 0.31 |
| taste: texture (settled) | 0.06 (−0.12–0.18) | 0.04 (0.01–0.09) | 0.11 (−0.10–0.36) | 0.18 |
| taste: contrast (settled) | 0.13 (−0.06–0.28) | 0.04 (−0.01–0.12) | 0.20 (0.11–0.39) | 0.15 |
| held-out error at step 1,000 | 0.0064 (0.0029–0.0128) | 0.0034 (0.0028–0.0046) | 0.0039 (0.0021–0.0071) | 0.0032 |
| step where the appetite ends | 462 (375–575) | 519 (375–800) | 388 (275–475) | 108 |
| unique tiles | 418 (356–452) | 460 (379–513) | 446 (438–451) | 41 |
| ocean share of unique tiles | 0.18 (0–0.39) | 0.03 (0–0.12) | 0.17 (0.03–0.39) | 0.14 |

Taste rows are standardised selection differentials. On each step where a neighbour is chosen, the chosen tile's property is set against the neighbours on offer, in SDs of what was on offer, then averaged over steps. A blind walker gives 0. **Bold:** a lead against the Reference.

### When the readouts start to see something (leads against the Reference)

| | Young (0–149) | Settled (150–999) |
|---|---|---|
| Null | places, steps per place, teleports, revisits beyond chance, top tile chosen | revisits and straight-backs beyond chance, top tile chosen, far tiles taken, **taste** (snow/ice/cloud) |
| Bored | places, steps per place, teleports, rejected landings | taste: snow/ice/cloud (stronger avoidance) |

### The taste panel (`panel_*.csv`, `panel_similarity.png`)

300 tiles, 100 each of land, coast and ocean, spread over texture and brightness quartiles, never visited by any h0111 walk. Each walker's own network scores them at steps 250, 500, 750 and 1,000.

How alike two walkers rank the panel (Spearman ρ, median over all pairs, 10th–90th percentile):

| Signal | Step 250 | Step 1,000 |
|---|---|---|
| surprise (hard to draw) | 0.84 (0.63–0.95) | 0.76 (0.35–0.90) |
| novelty | 0.65 (0.14–0.89) | 0.64 (0.23–0.89) |
| progress | 0.49 (0.21–0.68) | 0.33 (0.12–0.55) |
| interest (the walker's own mix), mean | | 0.44 |

Interest, by kind of pair (step 1,000): same setting, other seed 0.42; same seed, other setting 0.44; other setting and other seed 0.44.

What every walker shares (step 1,000, mean of the 28 walkers' rank correlations with the tile property):

| | texture | brightness | saturation |
|---|---|---|---|
| surprise | **0.58** | 0.21 | 0.10 |
| novelty | **0.44** | 0.06 | 0.10 |
| progress | −0.20 | 0.30 | −0.23 |
| interest | 0.10 | 0.27 | −0.15 |

Interest by brightness quartile, land and coast: the darkest quarter −0.6, the middle two +0.6 to +0.7, the brightest quarter −0.15 to −0.4. The brightest quarter is the hardest to draw (surprise +0.7) but not novel (−0.4 to −0.6).

### How much four seeds can show (simulated, two independent walks per seed)

| Effect, in seed SDs | 0.5 | 1 | 1.5 | 2 | 3 |
|---|---|---|---|---|---|
| chance a four-seed lead catches it | 0.14 | 0.29 | 0.50 | 0.70 | 0.93 |

With no effect, the lead rule fires on 9 % of readouts. The eight-seed result rule (at least 7 of 8 with the same sign) fires on 1.3 %. If the paired walks were correlated at 0.5, the rates would be 5 % and 0.3 %.

Leads counted per comparison (walk readouts, 74 per comparison; panel readouts, 68):

| | Walk readouts | Panel readouts |
|---|---|---|
| Null against Reference | 28 | 10 |
| Bored against Reference | 8 | 2 |
| expected by chance, independent walks | ~6.5 | ~6 |
| landing variants against their base (4 comparisons) | 2 of 295 | 3 of 272 |

## Findings

1. **The scorer is plain to see.** Without it, the walker goes back no more often than a blind walker would, and returns to tiles only as often as chance. With it, the Reference picks the top-scoring tile 42 percentage points more often than chance, revisits 18 points more and steps straight back 12 points more. These are differences of 5–17 seed SDs, in every seed. While the network is young, only revisits and top-tile choice are leads yet; once settled, all three are, and so are far tiles taken. Any setting that touches the scorer will show up here.

2. **Bored shows in rhythm and nowhere else.** More places, shorter stays, more teleports and more rejected landings, mostly in the first 150 steps. Its choices are the Reference's: the same share of top tiles, revisits and straight-backs. Bored's 8 leads on the walk readouts are about what chance alone would give (6.5). But they are exactly the rhythm readouts h0111 predicts, so they are kept as leads, not results.

3. **Taste shows up in what the walker turns down.** In its choices among neighbours, the Reference has no measurable preference for texture, contrast or entropy (0.06, 0.13, 0.08 SDs of what was on offer). What it does do is avoid snow, ice and cloud: −0.35 SD once settled, in all four seeds. Bored avoids them more (−0.48). The panel explains why. The brightest tiles are the hardest to draw but the least novel, and the walker does not value surprise (`w_e` 0), so they come out the least interesting. Any setting that changes `w_e` should move this readout first.

4. **Taste needs a settled network.** No taste readout separates the Reference from the Null walker in steps 0–149. They separate from step 150 on. Taste readouts should be read on the settled phase only.

5. **Every walker sees the planet much the same way.** Their networks rank the panel's tiles by how hard they are to draw almost alike (median ρ 0.84 at step 250, 0.76 at step 1,000). All of them find textured tiles hard to draw (ρ 0.58) and novel (0.44), and textured tiles teach them little (−0.20). This is the shared "eye" of the walker at `crop_px` 64 and `ae_width` 1. Settings that change the eye (`crop_px`, `ae_width`) have something stable to move.

6. **The panel is not free of where the walker has been.** Novelty is measured against the walker's own archive. Two Bored walks share almost none of the others' panel interest: `bored_k3_s0`, whose last stretch was in the Patagonian ice fields (novelty ρ with the others 0.03), and `bored_s1`, which ended in Yunnan. Their networks are healthy: normal held-out error, and surprise ranked like everyone else's (ρ 0.73–0.77). So surprise on the panel is free of path luck. Novelty and progress are not, and interest inherits it.

7. **On the panel, settings differ from each other no more than seeds do.** Taste similarity is 0.42 for the same setting with another seed, and 0.44 for the same seed with another setting. The panel's 10 leads for Null and 2 for Bored are about chance, and none holds across all four checkpoints. Between the existing settings, the panel sees no character difference. It describes the shared eye (finding 5), not individual taste.

8. **Pairing by seed helps less than the brief assumed.** It works while walks share a path: the landing variants against their base give only 2–3 leads in about 280 tests each. But Null, Bored and every Stage 1 setting diverge from step 0, and then the shared seed fixes only the starting weights and the far offers. Same-seed pairs agree on the panel no better than unrelated pairs (finding 7). Counting each pair as two independent walks, four seeds catch two seed SDs 70 % of the time, and the lead rule fires by chance on 9 % of readouts. `calibration.csv` gives effects and "detectable" in seed SDs on this basis.

9. **Some readouts see nothing at all.** Held-out error, the appetite end, unique tiles, ocean share and colour diversity do not separate Null, Bored or the Reference. Ocean share swings from 0 to 0.39 between Reference seeds on landing luck alone, as h0111 found. `far_offered` is identical for every walker of a seed, which is the check that the offer stream is shared, not a readout. The taste readout for ocean cannot be measured from Paris: neighbours almost never mix land and sea.

10. **Two readouts had to be redefined.** Raw selection differentials, in pixel units, were dominated by a few steps with very mixed neighbours, so the standardised ones replace them. Far offers were taken out of the taste readouts. They are the same tile for every walker of a seed, so uniform choice did not average to zero over a single walk (`log.md`). Both changes were checked against the Null walker. After them, every Null taste readout is about zero.

## Readouts for the sheet

Recommended core, 17 readouts, fixed before Stage 1. Only leads on these count:

| Section | Readouts |
|---|---|
| Rhythm | places, median steps per place, teleports, rejected landings, far tiles taken ÷ chance |
| Returns | revisits beyond blind, straight-backs beyond blind |
| Choice | top tile chosen beyond chance |
| Taste (settled only) | snow/ice/cloud, brightness, saturation, texture, contrast |
| Eye (panel, mean of steps 500–1,000) | surprise against texture, novelty against texture, progress against texture |
| Learning | held-out error at step 1,000 (compare only within one `crop_px`) |

All the other readouts stay in `readouts.csv` for continuity but do not go on the sheet: entropy, raw selection differentials, longest place, burst share, revisit and straight-back shares, held-out error at 250 and 500, appetite end, unique tiles, ocean share, colour diversity and the per-checkpoint panel readouts.

## For Stage 1

1. **Fix the core above**, so a setting's leads can be read against about 1.5 false ones (17 readouts at 9 %) instead of 6–7.
2. **Keep seeds 4–7 for every lead, as the brief plans.** The eight-seed rule is safe (1.3 % false per readout). Settings expected to act on taste (`w_e`, `k_nn`, `temperature`, `crop_px`) are the ones most likely to need all eight.
3. **The Reference's seeds 4–7 are worth walking first** (tier 1, 4 walks). Every seed SD here rests on four seeds per setting.
4. **Read taste on steps 150–999 only**, and the eye on the panel's surprise rather than on interest (findings 4 and 6).
5. **Write the dated predictions** in `notes/06_characters/expectations.md`, section "Round h0311", before the first walk. Findings 3 and 5 suggest concrete ones: `w_e: 1` should remove the avoidance of snow, ice and cloud, and `crop_px` should move how surprise relates to texture on the panel.

Not done: Stage 0.4 ("where would a reason have taken it?"). The brief made it optional, last in order.

# Stage 1: one setting at a time (2026-11-08)

**The walks.** 98 walks, made 2026-11-05 to 11-06. Each Stage 1 walk is the h0111 Reference with one key changed: Paris, 1,000 steps, split streams, seeds 0–3. The Reference gets seeds 4–7. For the two `ae_width` settings, s0 is the h0111 eye-size walk, so the batch adds s1–s3. Configs are in `configs/08_character_sheet/`, the batch script is `scripts/hikes_e08.sh`, and pauses and incidents are in `log.md`. All the walks finished, and the panel scored every one of them at steps 250, 500, 750 and 1,000.

**The readouts.** All readouts are the core 17 fixed in Stage 0 ("Readouts for the sheet"), and only leads on these count. The matrix is `results/matrix.csv` and `matrix.png`, made by `analysis/e08/matrix.py`.
- Each setting is paired with the Reference of the same seed.
- Effects are in Stage 0 seed SDs.
- A **lead** means all four paired differences have the same sign, and the mean difference is larger than half the Reference's range over those seeds.
- Chance alone gives about 1.5 leads per setting (Stage 0, finding 8).

**Dropped candidates.** These are tiles not fetched within the walker's 30 s timeout. There were 158 in 98 walks, a median of 0 per walk, and most walks dropped 0–11. Radius 25 is the exception: s0 dropped 40 and s3 dropped 23, because it fetches many tiles per step. Each drop is one candidate of about 8 at that step, and the walks are kept.

**The short version.**
- **Clear effects.** These settings change how the walker chooses and returns, by 2.7–17 seed SDs, with every seed pointing the same way:
  - removing novelty (progress only);
  - habituation over 3 neighbours;
  - temperature;
  - adding surprise;
  - the cost of returning and the ban on stepping back;
  - Null at Bored's patience.
- **Rhythm.** It moves clearly only for far jumps at 0.2 (40 places instead of 9). Shorter stays come with several other settings.
- **Taste and the eye barely move.** Their leads are small, and most of them point the way the Reference's seeds 0–3 are off.
- **The Reference's seeds 0–3 are an unlucky baseline.** On six readouts, 17–22 of the 23 Stage 1 settings differ from them in the same direction. Seeds 4–7 of the Reference don't share that offset. Four-seed pairing then turns the Reference's luck into leads.
- **Predictions.** Of the 17 written before the walks (19–35), one was right, three mostly right, eight partly right and five wrong. The surprises:
  - Novelty, not progress, carries the returns.
  - `k_nn` 3 removes them entirely.
  - Changing the eye's crop or width does not change the eye.

## The tables

### Leads per setting (core 17; chance about 1.5)

| Section | Setting (key: value) | Leads | Which (setting − Reference, in seed SDs) |
|---|---|---|---|
| Stage 0 | Null (choice: uniform) | 7 | top tile −17, revisits −5.6, straight-backs −5.2, median stay +3.1, snow/ice/cloud +1.9, far taken −1.8, places −1.3 |
| Stage 0 | Bored (patience 0.3) | 4 | rejected landings +2.2, teleports +2.0, snow/ice/cloud −0.7, median stay −0.5 |
| Scorer | novelty only (`w_g` 0) | 0 | |
| Scorer | progress only (`w_n` 0) | 7 | top tile −8.5, revisits −4.2, straight-backs −3.9, rejected landings +2.4, snow/ice/cloud +1.5, novelty ~ texture +1.1, median stay −0.5 |
| Scorer | surprise added (`w_e` 1) | 4 | straight-backs +2.9, top tile +2.7, contrast +2.6, texture +1.9 |
| Habituation | `k_nn` 3 | 2 | revisits −6.3, straight-backs −6.1 |
| Habituation | `k_nn` 30 | 2 | straight-backs +3.2, rejected landings +0.9 |
| Attention span | `ema_alpha` 0.005 | 2 | top tile −2.0, teleports +1.4 |
| Attention span | `ema_alpha` 0.08 | 0 | |
| Decisiveness | `temperature` 0.2 | 2 | top tile +7.7, straight-backs +2.8 |
| Decisiveness | `temperature` 1.0 | 1 | top tile −5.7 |
| Scale | `crop_px` 32 | 1 | snow/ice/cloud +1.6 |
| Scale | `crop_px` 128 | 1 | snow/ice/cloud +0.9 |
| Temperament | `patience` 0.8 | 0 | |
| Wanderlust | `p_long_jump` 0 | 1 | straight-backs +1.8 |
| Wanderlust | `p_long_jump` 0.2 | 4 | places +6.8, novelty ~ texture +1.7, surprise ~ texture +1.6, median stay −0.5 |
| Learning | `update_steps` 1 | 1 | straight-backs +1.5 |
| Learning | `update_steps` 12 | 4 | novelty ~ texture +1.6, revisits −1.6, straight-backs −1.0, median stay −0.4 |
| Control | Null, `patience` 0.3 | 4 | top tile −17, revisits −5.5, straight-backs −5.4, snow/ice/cloud +2.1 |
| Memory | `buffer_size` 512 | 0 | |
| Memory | `buffer_size` 8,192 | 0 | |
| Capacity | `ae_width` 0.5 | 1 | snow/ice/cloud −1.0 |
| Capacity | `ae_width` 2 | 0 | |
| Stride | `radius_km` 25 | 1 | revisits +1.9 |
| Returns | `return_cost` 0.5 | 5 | revisits −2.9, straight-backs −2.9, rejected landings +0.8, teleports +0.8, median stay −0.5 |
| Returns | `no_backstep` | 1 | straight-backs −5.4 (0 by construction) |

The median stay's seed SD (170 steps) is inflated by Null's 1,000-step stays. A median-stay lead of −0.5 SD means stays of 16–31 steps against the Reference's 103. Held-out error is compared only at `crop_px` 64.

### What the walk readouts see (mean of seeds 0–3)

| Setting | places | median stay | teleports | revisits beyond blind | straight-backs beyond blind | top tile beyond chance | snow/ice/cloud | texture | contrast | held-out ×1,000 |
|---|---|---|---|---|---|---|---|---|---|---|
| Reference s0–3 | 8.75 | 103 | 3.5 | 0.18 | 0.12 | 0.42 | −0.35 | 0.06 | 0.13 | 6.4 |
| Reference s4–7 | 9.25 | 75 | 4.25 | 0.18 | 0.13 | 0.42 | −0.14 | 0.21 | 0.23 | 4.0 |
| novelty only | 8.25 | 280 | 4.25 | 0.16 | 0.09 | 0.38 | −0.08 | −0.12 | 0.00 | 3.9 |
| progress only | 14 | **16** | 9.5 | **0.05** | **0.03** | **0.21** | **−0.07** | −0.05 | −0.05 | 4.7 |
| surprise added | 10.2 | 38 | 4.75 | 0.21 | **0.19** | **0.49** | −0.24 | **0.41** | **0.51** | 3.5 |
| `k_nn` 3 | 9.5 | 97 | 2.75 | **−0.02** | **−0.02** | 0.45 | −0.21 | −0.01 | 0.10 | 3.6 |
| `k_nn` 30 | 12 | 35 | 6 | 0.23 | **0.19** | 0.42 | −0.32 | 0.02 | 0.11 | 3.8 |
| `ema_alpha` 0.005 | 13.5 | 42 | **9.5** | 0.18 | 0.12 | **0.37** | −0.17 | −0.07 | 0.09 | 4.1 |
| `ema_alpha` 0.08 | 5.75 | 131 | 0.75 | 0.18 | 0.12 | 0.46 | −0.21 | 0.00 | 0.14 | 3.8 |
| `temperature` 0.2 | 10.8 | 37 | 4.75 | 0.22 | **0.19** | **0.62** | −0.43 | 0.10 | 0.20 | 3.4 |
| `temperature` 1.0 | 9 | 45 | 4.25 | 0.12 | 0.08 | **0.28** | −0.10 | 0.09 | 0.15 | 4.1 |
| `crop_px` 32 | 9 | 61 | 3.75 | 0.17 | 0.14 | 0.43 | **−0.05** | 0.18 | 0.23 | · |
| `crop_px` 128 | 9.5 | 92 | 4 | 0.18 | 0.13 | 0.42 | **−0.18** | 0.12 | 0.22 | · |
| `patience` 0.8 | 7 | 103 | 0.5 | 0.15 | 0.11 | 0.43 | −0.24 | 0.12 | 0.17 | 7.4 |
| `p_long_jump` 0 | 4.25 | 177 | 3.25 | 0.22 | **0.16** | 0.47 | −0.23 | 0.16 | 0.18 | 4.1 |
| `p_long_jump` 0.2 | **40.5** | **16** | 5.25 | 0.16 | 0.12 | 0.44 | −0.19 | 0.13 | 0.22 | 2.7 |
| `update_steps` 1 | 9.25 | 50 | 3.5 | 0.19 | **0.15** | 0.43 | −0.20 | −0.03 | 0.05 | 6.5 |
| `update_steps` 12 | 11.8 | **31** | 5.25 | **0.13** | **0.10** | 0.44 | −0.15 | 0.18 | 0.25 | 2.4 |
| Null, `patience` 0.3 | 10.5 | 268 | 7 | **0.01** | **0.00** | **0.00** | **0.05** | 0.01 | 0.00 | 3.1 |
| `buffer_size` 512 | 10 | 38 | 4.75 | 0.20 | 0.13 | 0.44 | −0.35 | −0.06 | 0.09 | 4.9 |
| `buffer_size` 8,192 | 8.75 | 63 | 3.5 | 0.18 | 0.11 | 0.42 | −0.18 | −0.03 | 0.08 | 3.9 |
| `ae_width` 0.5 | 10 | 51 | 4.25 | 0.15 | 0.11 | 0.43 | **−0.54** | 0.19 | 0.26 | 4.3 |
| `ae_width` 2 | 8.25 | 62 | 3.25 | 0.16 | 0.11 | 0.41 | −0.19 | 0.04 | 0.10 | 4.0 |
| `radius_km` 25 | 4.5 | 146 | 1 | **0.25** | 0.11 | 0.41 | −0.13 | 0.30 | 0.41 | 3.8 |
| `return_cost` 0.5 | 11.8 | **26** | **6.75** | **0.09** | **0.06** | 0.44 | −0.42 | 0.06 | 0.16 | 5.3 |
| `no_backstep` | 9.5 | 59 | 5 | 0.16 | **0.00** | 0.45 | −0.11 | −0.10 | 0.03 | 3.9 |

**Bold:** a lead against the Reference (seeds 0–3). Taste is read on the settled phase, in SDs of what was on offer. · = not comparable (another `crop_px`). Unique tiles, not a core readout: Reference 418, `radius_km` 25 549, `no_backstep` 558, `return_cost` 0.5 539.

### Is it the setting or the Reference? (sign of setting − Reference over the 23 Stage 1 settings)

| Readout | Settings above the Reference | below | Reference s0–3 → s4–7 |
|---|---|---|---|
| snow, ice, cloud | 20 | 3 | −0.35 → −0.14 |
| brightness | 5 | 18 | 0.34 → −0.10 |
| median stay | 4 | 19 | 103 → 75 |
| novelty ~ texture | 22 | 1 | 0.40 → 0.51 |
| surprise ~ texture | 20 | 3 | 0.58 → 0.67 |
| progress ~ texture | 6 | 17 | −0.15 → −0.26 |
| held-out error at 1,000 | 2 | 19 | 0.0064 → 0.0040 |
| (for comparison) texture | 11 | 12 | 0.06 → 0.21 |
| (for comparison) far tiles taken | 12 | 10 | 1.60 → 1.37 |

Seeds 0–3 of the Reference sit at the edge of all walkers of the same seed on several of these readouts:
- Seed 2 has the lowest surprise ~ texture of the 30 walkers of seed 2 (0.35).
- Seed 2 has the second-highest held-out error of all walkers (0.0128, after `patience` 0.8 s2).
- Seed 3 has the highest progress ~ texture of the walkers of seed 3.

### The Reference over eight seeds (prediction 19)

| Readout | Seeds 0–3 (mean, range) | Seeds 4–7 | SD over 4 seeds → 8 seeds |
|---|---|---|---|
| places | 8.75 (4–14) | 10, 13, 6, 8 | 4.1 → 3.3 |
| revisits beyond blind | 0.18 (0.15–0.25) | 0.15, 0.18, 0.26, 0.15 | 0.043 → 0.044 |
| straight-backs beyond blind | 0.12 (0.10–0.14) | 0.10, 0.14, 0.16, 0.10 | 0.018 → 0.023 |
| top tile beyond chance | 0.42 (0.40–0.45) | 0.44, 0.40, 0.45, 0.41 | 0.022 → 0.022 |
| snow, ice, cloud | −0.35 (−0.49 to −0.26) | −0.34, −0.69, **+0.83**, −0.37 | 0.11 → **0.46** |
| brightness | 0.34 (−0.05–0.64) | 0.02, 0.22, −0.56, −0.08 | 0.29 → 0.37 |
| texture | 0.06 (−0.12–0.18) | 0.25, −0.08, 0.57, 0.10 | 0.13 → 0.22 |
| novelty ~ texture | 0.40 (0.25–0.50) | 0.54, 0.47, 0.47, 0.54 | 0.12 → 0.10 |
| held-out ×1,000 | 6.4 (2.9–12.8) | 3.0, 4.7, 3.5, 4.5 | 4.4 → 3.2 |

Seed 6 spent its settled phase at one place in Heilongjiang. Bright tiles were on offer only there, and it chose them (+0.83). Weighting each place equally does not change this (+0.98; `selp_*` columns in `readouts.csv`, added after seed 6 and not part of the core).

## Findings

1. **Novelty carries the returns, and how it habituates sets them.**
   - **Without novelty** (progress only): revisits and straight-backs beyond blind fall to 0.05 and 0.03. The top tile is chosen only 0.21 beyond chance, and the walker moves in Bored's rhythm: 14 places, stays of 16 steps.
   - **Without progress** (novelty only): nothing measurable changes (0 leads).
   - **`k_nn` 3** removes returns entirely: revisits −0.02, below a blind walker, in every seed. Over its three nearest archive entries, a tile just visited is never novel again.
   - **`k_nn` 30** goes the other way, with straight-backs at 0.19.

   This is the opposite of predictions 20, 21 and 23 in size, and of 21 in direction. Returns are a property of novelty's memory, not of the scorer as a whole.

2. **Temperature is the cleanest knob.** The top tile chosen beyond chance is 0.28, 0.42 and 0.62 at temperatures 1.0, 0.5 and 0.2, in order in every seed (1.0: 0.27–0.29; 0.5: 0.40–0.45; 0.2: 0.59–0.64). That is −5.7 and +7.7 seed SDs. Returns follow, and rhythm does not.

3. **Surprise brings a taste for texture and contrast, but does not lift the avoidance of snow and ice.**
   - With `w_e` 1, the walker prefers textured (0.41) and high-contrast (0.51) neighbours: leads of +1.9 and +2.6 SDs, on readouts without the offset of finding 8.
   - Its choices sharpen: top tile 0.49, straight-backs 0.19.
   - Snow, ice and cloud are still avoided (−0.24; prediction 22 said −0.1 to +0.3).
   - Stays are shorter, not longer.

4. **Returning costs and their substitutes.**
   - **`return_cost` 0.5:** revisits and straight-backs fall by about half, as predicted. But it also spreads the walk: stays of 26 steps, 6.75 teleports, 540 unique tiles.
   - **`no_backstep`:** removes straight-backs by construction and changes little else. Revisits do not fall (0.16), and stays do not lengthen.
   - **`radius_km` 25:** more revisits (0.25), not fewer straight-backs. With twice the neighbours, the walker finds its favourites again.

5. **Rhythm is set by the far offers and by learning speed, not by patience alone.**
   - **`p_long_jump` 0.2:** 40 places of 16 steps each.
   - **`p_long_jump` 0:** places = teleports + 1 in every seed.
   - **`update_steps` 12:** short stays (31), fewer returns, and the lowest held-out error of the round (0.0024).
   - **`patience` 0.8:** removes teleports (0.5) and rejected landings (0), but misses the lead rule by a hair (−3.0 against a threshold of 3.0). Its stays are no longer than the Reference's.
   - **`ema_alpha` 0.005:** more teleports in the settled phase (3–16 against 0–3).

6. **Most of Bored's restlessness is the boredom rule, not the scorer.** Null at patience 0.3 teleports 7 times per walk, against Null's 0.5. It visits 10.5 places, against 2.75, and has fewer rejected landings than Bored (4 against 7.5). Prediction 30 was right throughout. Seed 3 never got bored even at 0.3, so it repeats Null s3 step for step (one place, 1,000 steps). The other three seeds teleported 8–11 times.

7. **The eye is shared, and the eye settings do not change it.**
   - On the panel, surprise against texture is 0.53–0.77 for every Stage 1 setting.
   - It is 0.68 at crop 32 and 0.53 at crop 128, against the predicted 0.65–0.80 and 0.30–0.50, with no lead.
   - It is 0.60 at width 2, against the predicted 0.40–0.55.
   - The three eye leads in the round go to far jumps 0.2, update steps 12 and progress only. All three point the way the Reference's seeds 0–3 are off (finding 8).

   Stage 0's finding 5 holds: the walker's eye at `crop_px` 64 is not a matter of settings in the tested range. At crop 32 and 128 the panel crops change too, so the eye there is measured on other inputs. That is a limit of the readout, and the next round should check it.

8. **Four Reference seeds are not a safe baseline for taste, the eye and held-out error.**
   - On seven readouts, 17–22 of the 23 settings fall on the same side of the Reference. For the comparison readouts (texture, far tiles taken), the split is even.
   - On every one of the seven, the Reference's seeds 4–7 sit on the settings' side.
   - So most of the round's taste and eye leads are the Reference's seeds 0–3, not the settings: snow/ice/cloud at crop 32, crop 128 and progress only, and novelty ~ texture at far jumps 0.2, update steps 12 and progress only.
   - The leads that point against the offset are the more credible ones: `ae_width` 0.5's stronger avoidance of snow, ice and cloud, and surprise's texture and contrast.
   - The walk-structure readouts are not affected: choice, returns, places and teleports split about evenly, or their effects are far beyond the offset.

9. **Taste needs eight seeds or more.**
   - The Reference's SD on snow, ice and cloud is 0.46 over eight seeds, against 0.11 over four. One seed that settles where bright tiles are the only offer is enough.
   - At this SD, a four-seed lead needs an effect of about 0.9 to show up (two seed SDs).
   - No setting moves taste that far: the largest taste differences in the round are about 0.4 (brightness at temperature 0.2 and width 0.5, not leads; snow, ice and cloud for both Nulls; contrast with surprise added).

10. **Leads against chance.**
    - The 24 settings have 44 leads, against about 36 expected by chance (1.5 each).
    - The count alone does not separate settings from chance. Effect size helps: 13 Stage 1 leads are at least 3 seed SDs. All of them are on choice and returns, except the places of far jumps 0.2. A lead needs only about one seed SD, so these are the ones least likely to be chance.
    - Six settings show no lead at all: novelty only, `ema_alpha` 0.08, `patience` 0.8, both buffer sizes and `ae_width` 2.
    - Six show a single lead under 2 SDs: `crop_px` 32 and 128, `p_long_jump` 0, `update_steps` 1, `ae_width` 0.5 and `radius_km` 25.

## Against the predictions (19–35, written 2026-11-05)

| # | Setting | Predicted | Found | Verdict |
|---|---|---|---|---|
| 19 | Reference s4–s7 | s4–7 mean within the s0–3 range on all but ≤2 readouts; choice/returns SD changes < 30 %; one seed with 1–2 places | Outside on 5 (four taste readouts, novelty ~ texture); SD change 0–28 % on choice and returns; fewest places 6 | wrong |
| 20 | novelty only | top tile 0.28–0.36; texture 0.15–0.35, brightness ~0, snow −0.35 to −0.6; returns down a third | top 0.38; texture −0.12, brightness 0.44, snow −0.08 (none leads); returns down 12 % and 24 %; 0 leads | wrong |
| 21 | progress only | top tile 0.28–0.36; brightness 0.4–0.8, texture −0.3–0, snow −0.2 to 0.1; revisits up to 0.20–0.30; rhythm between Null and Reference | top 0.21; brightness 0.07, texture −0.05, snow −0.07 (lead); revisits 0.05; Bored's rhythm (14 places, stays 16) | wrong (taste partly right) |
| 22 | surprise added | top 0.44–0.52; snow −0.1 to +0.3; texture, contrast 0.2–0.5; stays 150–400, teleports 0–3 | top 0.49; snow −0.24; texture 0.41, contrast 0.51; stays 38, teleports 4.75; no seed stuck | partly |
| 23 | `k_nn` 3 / 30 | k3: revisits 0.10–0.15, straight-backs 0.06–0.10; k30: revisits 0.18–0.24; novelty ~ texture 0.30–0.40 at k30 | k3: −0.02 and −0.02; k30: revisits 0.23, straight-backs 0.19 (lead); novelty ~ texture 0.55 | partly (direction right, k3 far stronger) |
| 24 | `ema_alpha` 0.005 / 0.08 | 0.005: 0–1 young teleports, more settled; 0.08: teleports 0–2, stays > 150; taste and returns unchanged | 0.005: young 2–5, settled 3–16 (against 0–3); 0.08: teleports 0.75, stays 131; top tile at 0.005 lower (lead) | partly |
| 25 | `temperature` 0.2 / 1.0 | 0.2: top 0.60–0.75, revisits 0.25–0.35, straight-backs 0.18–0.28, snow −0.5 to −0.8; 1.0: top 0.18–0.28, returns halved, taste halved, places 3–7 | 0.2: top 0.62, revisits 0.22, straight-backs 0.19, snow −0.43; 1.0: top 0.28, returns down a third, snow −0.10, places 9 | mostly right |
| 26 | `crop_px` 32 / 128 | surprise ~ texture 0.65–0.80 / 0.30–0.50; neighbour texture 0.1–0.3 / −0.1–0.1; rhythm unchanged | 0.68 / 0.53 (no lead; most settings 0.6–0.7); texture 0.18 / 0.12; rhythm unchanged; snow less avoided (leads, Reference offset) | wrong on the eye |
| 27 | `patience` 0.8 | teleports 0–2, rejected 0, places 2–6, stays 200–600, far 1.2–2.0, returns 0.18–0.24 | teleports 0.5, rejected 0; places 7, stays 103, far 2.15, revisits 0.15 | partly |
| 28 | `p_long_jump` 0 / 0.2 | 0: places = teleports + 1, 2–7 places; 0.2: ~200 offers, far 1.0–1.6, 30–60 places, stays < 20, teleports 0–3, returns down a third | 0: as predicted; 0.2: 175–216 offers, far 1.27, 40.5 places, stays 16; teleports 5.25; returns down 16 % and 3 % | mostly right |
| 29 | `update_steps` 1 / 12 | 1: stays 1.5–3×, revisits 0.20–0.30, held-out 1.5–3×; 12: places 12–25, teleports 6–15, held-out lower in 3 of 4, no more than one dead network | 1: stays 50, revisits 0.19, held-out as the Reference; 12: places 11.8, teleports 5.25, held-out lower in 4 of 4 (not a lead), no dead network | partly (12 right, 1 wrong) |
| 30 | Null, `patience` 0.3 | teleports 4–12, places 5–13, rejected landings 0–5, fewer than Bored | 7, 10.5, 4 (Bored 7.5) | right |
| 31 | `buffer_size` 512 / 8,192 | no rhythm or taste lead; 512: revisits +0.02–0.06, held-out up; 8,192: held-out lower in 3 of 4, returns unchanged | no lead at all; 512: revisits +0.02, held-out lower in 3 of 4; 8,192: lower in 4 of 4, returns unchanged | mostly right |
| 32 | `ae_width` 0.5 / 2 | held-out 0.5 > 1 > 2 in 3 of 4; surprise ~ texture 0.40–0.55 at width 2; nothing else | order holds in 1 of 4; 0.60; width 0.5 avoids snow more (lead) | wrong |
| 33 | `radius_km` 25 | top 0.38–0.46, straight-backs 0.05–0.09, unique tiles +20–40 %, rhythm unchanged | top 0.41, straight-backs 0.11, unique +31 %, places 4.5 and teleports 1 (within about 1 SD); revisits up (lead) | partly |
| 34 | `return_cost` 0.5 / `no_backstep` | cost: revisits 0.06–0.12, straight-backs 0.04–0.08, top unchanged; no backstep: straight-backs 0, revisits 0.08–0.14, stays 120–250; taste unchanged | cost: 0.09, 0.06, 0.44; also stays 26, teleports 6.75; no backstep: 0, 0.16, stays 59; taste unchanged | partly (cost right, no backstep wrong) |
| 35 | the round | about half of the settings with leads beyond chance; the eye moves only for crop and width; choice and returns for taste, temperature and return aversion; rhythm for patience, far jumps, ema, update steps and Null at 0.3 | 6 of 24 settings with 3 or more leads; the eye moves for far jumps 0.2, update steps 12, progress only (all along the Reference offset), not for crop or width; choice and returns as predicted, plus `k_nn`, `ema_alpha` 0.005, far jumps 0, update steps and radius; rhythm for far jumps 0.2, ema 0.005, update steps 12, progress only and return cost, not for patience 0.8 | partly |

Tally: 1 right, 3 mostly right, 8 partly right, 5 wrong.

What I got wrong, in kind:
- **Taste.** I expected the scorer settings to move it. They hardly do, and four Reference seeds can't show it either.
- **The eye.** I expected crop and width to move it, and they don't.
- **Which signal carries the returns.** I credited progress, but it is novelty.
- **Stay length.** I expected longer stays from several settings. Almost every setting has shorter stays than the Reference's seeds 0–3, and the Reference's own seeds 4–7 do too.

## For seeds 4–7 (the brief's next step)

1. **Pair against eight Reference seeds.** Seeds 4–7 of the Reference exist already. Walk seeds 4–7 of each setting and judge it by the eight-seed rule (at least 7 of 8 with the same sign, and the mean difference larger than half the Reference's range). This removes the seeds 0–3 offset in finding 8.
2. **Which settings.** The brief says every setting with a lead: 18 settings, 72 walks, about 9 h with three side by side (radius 25 is the slowest). A smaller set is possible: the 10 settings with a lead of at least 2 seed SDs or several leads, 40 walks, about 5 h:
   - progress only, surprise added, both `k_nn`;
   - both temperatures, far jumps 0.2;
   - update steps 12, `return_cost`, `no_backstep`.

   This would drop the single taste leads that point along the offset (crop 32, crop 128) and the single small leads. Your call.
3. **Taste needs its own design** (finding 9). At an eight-seed SD of 0.46 on snow, ice and cloud, eight seeds help, but the taste effects in this round are 0.1–0.4. Starting places other than Paris, or a readout per place rather than per walk, would serve taste better than more seeds from Paris.
4. **The eye readout at other crops** (finding 7). The panel is cropped at each walker's own `crop_px`. Scoring every walker on the same 64 px panel would separate "the walker sees differently" from "the panel is cut differently".
