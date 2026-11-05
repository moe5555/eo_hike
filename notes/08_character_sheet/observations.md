# Character sheet (round h0311): observations, Stage 0

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
