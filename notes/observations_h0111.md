# Round h0111: observations

The brief is `notes/brief_0111.md`, the predictions are in `notes/hikes_2910/expectations.md` (9–18), and decisions and deviations are in `notes/log_h0111.md`. Scripts, tables and figures are in `analysis/h0111/`.

New walks: 1,000 steps from Paris, seeds 0–3, separate random streams (`rng_mode: split`), Mac CPU. Values are the mean of the four seeds, with the lowest and highest seed in brackets. **A place** is a stretch of a walk between two jumps longer than 30 km. **A rejected landing** is a teleport whose place lasted at most 30 steps and ended in another teleport.

**The short version.** The evidence favours the emergent arc, with one change of wording. The walker settles on *textured* terrain, not on terrain it cannot finish learning: Patagonia fits that description, but most long stays do not. Rejection bursts survive novelty-chosen landings almost untouched. Appetite is not a slow fade: it stops at about step 500 of 5,000, and using it to re-time the film takes the climax away.

## The tables

### Without the scorer (task 3; `task3_null_vs_reference.csv`)

| | Null (chooses blindly) | Reference |
|---|---|---|
| places | **2.75** (1–6) | **8.75** (4–14) |
| median steps per place | **632** (155–1,000) | **103** (39.5–183) |
| longest stay, steps | 681 (294–1,000) | 354 (248–604) |
| boredom teleports | **0.5** (0–2) | **3.5** (1–7) |
| far tiles offered / taken | 19.2 / **1.25** (0–3) | 19.2 / **4.25** (1–6) |
| straight-back steps (A→B→A) | **0.14** (0.13–0.16) | **0.28** (0.26–0.30) |
| revisit share | 0.54 (0.49–0.62) | 0.58 (0.55–0.64) |
| unique tiles | 460 (379–513) | 418 (356–452) |
| ocean share of unique tiles | 0.03 (0–0.12) | 0.18 (0–0.39) |
| colour diversity of unique tiles | 67.8 (53.5–92.2) | 69.6 (49.4–94.3) |
| held-out error, last 200 steps | 0.0038 (0.0033–0.0049) | 0.0048 (0.0044–0.0056) |
| steps where nothing on offer beat the recent average | 0.03 (0.01–0.07) | 0.09 (0.05–0.12) |

### How often the top-scoring tile is chosen (task 3; `task3_rank.csv`, `task3_rank.png`)

| | top-scoring tile chosen | a blind choice would give | far tile taken | a blind choice would give |
|---|---|---|---|---|
| Null | 0.12–0.15 | 0.13–0.16 | 0–0.18 | 0.11–0.14 |
| Reference | 0.56–0.61 | 0.15–0.17 | 0.06–0.35 | 0.13–0.14 |
| Bored | 0.57–0.63 | 0.14–0.16 | 0.11–0.32 | 0.12–0.15 |
| Globalist | 0.50–0.62 | 0.15 | **0.14–0.17** | 0.13–0.14 |
| Localist | 0.61–0.65 | 0.16–0.17 | none offered | – |
| Fast learner | 0.52–0.53 | 0.16–0.17 | 0–0.21 | 0.14 |

### Teleport landings (task 6; `task6_table.csv`, `task6_rhythm.png`)

| | Bored, blind | Bored, k=3 | Bored, k=8 | Reference, blind | Reference, k=3 | Reference, k=8 |
|---|---|---|---|---|---|---|
| teleports per walk | 11.8 (7–20) | 12 (2–21) | 10.8 (7–14) | 3.5 (1–7) | 2.75 (1–6) | 4 (1–8) |
| teleports in a burst (another within 30 steps) | 0.73 (0.43–1) | 0.88 (0.79–1) | 0.69 (0.55–0.86) | 0.39 (0–1) | 0.42 (0–1) | 0.34 (0–0.75) |
| largest burst | 7.25 (3–12) | 5.75 (2–9) | 6.75 (4–9) | 1.5 (1–2) | 2 (1–4) | 2.5 (1–5) |
| longest stay, steps | 462 (286–726) | 309 (179–431) | 376 (292–548) | 354 (248–604) | 457 (294–748) | 375 (294–470) |
| places | 16.8 (14–23) | 17.5 (5–27) | 15.2 (11–18) | 8.75 (4–14) | 8.5 (6–13) | 10 (8–14) |
| median steps per place | 21 (12–36.5) | 66.5 (17–204) | 25.2 (17–43) | 103 (39.5–183) | 71 (57–108) | 66.8 (34.5–108) |
| ocean share of unique tiles | 0.17 (0.03–0.39) | 0.30 (0.20–0.44) | 0.29 (0.16–0.44) | 0.18 (0–0.39) | 0.03 (0–0.11) | 0.25 (0–0.41) |
| ocean share, highest minus lowest seed | 0.37 | 0.24 | 0.29 | 0.39 | 0.11 | 0.41 |
| colour diversity | 70.9 (53.9–87.1) | 69.6 (57.1–84.8) | 59.1 (46.1–78.2) | 69.6 (49.4–94.3) | 70 (50.9–83.5) | 71.3 (60.5–94.4) |
| held-out error, last 200 steps | 0.0041 | 0.0037 | 0.0039 | 0.0048 | 0.0038 | 0.0049 |

Reference seed 2 is the same walk in all three Reference columns: it teleported once, and the first tile drawn was also the most novel of the eight. So the Reference columns hold only three walks that can differ.

### Rejected landings, all four seeds pooled (`task6_stays.csv`; landings too near the end to judge are left out)

| | Bored, blind | Bored, k=3 | Bored, k=8 | Reference, blind | Reference, k=3 | Reference, k=8 |
|---|---|---|---|---|---|---|
| first 150 steps | **25 of 30** | **20 of 26** | **23 of 30** | 3 of 9 | 4 of 9 | 6 of 11 |
| after step 150 | 5 of 16 | 8 of 20 | **0 of 12** | 0 of 5 | 0 of 2 | 0 of 5 |

| Tile chosen for a landing (`task6_landings.csv`, mean) | Bored, k=3 | Bored, k=8 | Reference, k=3 | Reference, k=8 |
|---|---|---|---|---|
| novelty: landed on / first tile drawn | 0.34 / 0.19 | 0.48 / 0.21 | 0.33 / 0.27 | 0.42 / 0.25 |
| texture (mean gradient): landed on / first tile drawn | 4.7 / 3.8 | 6.2 / 5.3 | 3.5 / 3.1 | 3.6 / 3.3 |
| share that is ocean: landed on / first tile drawn | 0.31 / 0.29 | 0.40 / 0.35 | 0.27 / 0.18 | 0.25 / 0.19 |

### Long stays against short places (task 1; 12 walks of round 29.10; `task1_long_vs_short.csv`, `contact_long_vs_short.png`)

| Median, from step 50 on | Long stays (top 10 % of places) | Short places (median length or less) | Long higher in |
|---|---|---|---|
| error on the chosen tile | 0.00157 | 0.00135 | 6 of 12 walks |
| that error relative to the planet at that moment (held-out) | 0.335 | 0.249 | 8 of 12 |
| texture: mean gradient | 4.50 | 2.42 | 10 of 12 |
| texture: grey-level entropy | 5.26 | 4.38 | 11 of 12 |
| contrast: grey-level spread | 13.3 | 7.7 | 12 of 12 |
| ocean share | 0.16 | 0.32 | – |
| colour diversity, pooled over the walk | 53 | 77 | 3 of 12 |
| colour diversity, within a place | 47.3 | 47.1 | 6 of 12 |

What predicts how long a place lasts, by rank correlation: error on the arrival tile 0.08, relative error over the first 10 steps 0.21, entropy 0.30, gradient 0.31. By texture quartile, the median place lasts 12, 17, 30 and 30 steps.

### Straight-back steps (task 5; `task5_backsteps.csv`)

| Share of all returns to A, Paris reference (4 seeds) | |
|---|---|
| would happen anyway with a blind choice among the same tiles | **51–60 %** |
| A really was high-scoring, on both the recent and the whole-walk yardstick | 76–94 % (overlaps the line above) |
| A scored high only against the recent ~50 steps (rescaling artefact) | **2–7 %** |
| interference: more error rise on A than when the walker did not return | **none detectable** |

| Did training on B make A harder to draw? (Reference and Bored, 8 walks) | Returned to A | Did not return |
|---|---|---|
| A's error rose after its own training | 0.38–0.51 | 0.42–0.49 |
| A's error at that moment ÷ just after training, median | 0.99–1.00 | 1.00 |
| A lost at least half of what its training had gained | 0.15–0.24 | 0.16–0.23 |

### Appetite cuts (task 7; `task7_stretches.csv`, `task7_appetite.png`)

| Whole Bored Paris walk, 10:00 each | A: log clock | B: log clock × appetite |
|---|---|---|
| first 50 steps | 60 s | 114 s |
| steps 66–458 (first long stay) | 184 s | 342 s |
| step 500 arrives at | 4.5 min | 8.3 min |
| everything from step 1,108 on (78 % of the walk) | 3.7 min | under 1 min |
| Patagonia (steps 3,696–4,724) | **37.1 s** | **11.5 s** |
| hold on one tile, start → end | 1.46 s → 30 ms | 2.78 s → 10 ms |
| steps shorter than one frame | 9 % | 72 % |

| Appetite (fall in log held-out error per 1,000 steps), 500-step window | Bored | At or below zero for |
|---|---|---|
| steps 0–499 | 11.5 | 0 % of the block |
| each later block of 500 steps | −0.41 to +0.77 | 0–87 % of the block |

### Eye size (task 9; seed 0 only; `task9_eye.csv`, `task9_eye.png`)

| | Half (68k weights) | Current (272k) | Double (1.09M) |
|---|---|---|---|
| held-out error at step 100 | 0.0139 | 0.0078 | 0.0080 |
| at step 500 | 0.0061 | 0.0104 | 0.0139 |
| at step 1,000 | 0.0035 | 0.0028 | 0.0036 |
| median of the last 200 steps | 0.0037 | 0.0037 | 0.0049 |
| first within 20 % of its final level | step 775 | step 725 | step 625 |
| unique tiles / teleports | 468 / 4 | 438 / 7 | 398 / 5 |
| run time | 515 s (alone) | 1,071 s (three at once) | 1,383 s (alone) |

## What happened

1. **"Interesting" mostly means textured, not hard to draw.** The working hypothesis is only partly right. Long stays are on rougher terrain in nearly every walk: gradient 1.5×, contrast 1.6×. Their raw error is no higher: the median ratio is 1.04, and it is higher in only 6 of 12 walks. Measured against how well the network draws the planet at that moment, it is higher (1.7×, 8 of 12), but the arrival tile's error predicts almost nothing about how long a place will last (0.08). Part of this is built in: the score has no direct term for error (`w_e` is 0), so a walker cannot be drawn to a tile just because it draws it badly. On the contact sheet, short places are flat sand, ice and sea, and long stays are mountains and snow on rock.

2. **Most long stays are not on terrain the network cannot finish learning. Patagonia is the exception.** Across 42 stays of at least 60 steps, error at the end is a median 0.80 of error at the start, and the error dropped below 0.75 of its arrival value at some point in 71 %. The chosen tiles were above the planet-wide error in a median of only 10 % of a stay. Interest falls from 1.94 to 1.10 and stays above zero. Patagonia is different: its error was above the planet-wide level throughout, with a relative error falling only from 3.07 to 1.45. So "settling on terrain it cannot finish learning" describes one famous stay, and "settling on textured terrain" describes the rest.

3. **Novelty is measured against a growing archive, so it can fade in principle. It doesn't.** Novelty is the mean distance to the 10 nearest entries in an archive of *every visit*, including repeat visits: 5,000 entries, 2,066 different tiles for Bored. It is not the replay buffer, which holds about 128 visits' worth of crops and is used only for training. With the network frozen, a larger archive does make the planet look more familiar (held-out novelty 0.40 → 0.15 for Bored, 0.31 → 0.11 for Globalist). But as the walks are actually lived, held-out novelty stays flat at 0.14–0.18 for Bored, and rises from 0.065 to 0.11–0.14 for Globalist. Raw novelty on offer rose over the 5,000 steps (last block ÷ first: 1.17 and 1.22). The network keeps stretching its own ruler about as fast as the archive fills. "Novelty never falls" is therefore a real finding about the walker, but it says nothing about the planet running out. Separately, the rescaled score cannot fade by construction, since it is always measured against the last ~50 steps.

4. **The scorer sets the rhythm; the rules alone hardly move the walker.** I expected the opposite. Take the scorer away and the walker jumps far less: places fall from 8.75 to 2.75, teleports from 3.5 to 0.5, and far tiles taken from 4.25 to 1.25, with identical far-tile offers. Two of the four blind walks never jumped at all: their one place lasted all 1,000 steps, wandering overland to at most 280 and 617 km from Paris. The likely reason, though I have not tested it separately, is that a choosing walker uses up what is interesting around it, whereas a blind one leaves the interesting tiles unvisited. Those tiles stay on offer and keep it from getting bored (nothing beat the recent average in 3 % of its steps, against 9 %).

5. **The characters differ through their rules, and the rules work through the scorer.** All scoring characters pick the top tile about equally often (0.50–0.65, blind 0.12–0.15), so the scorer itself does not distinguish them. Patience and jump offers do, but those rules only have something to act on because of the scores. What the scorer does *not* change is how much a walker sees and learns. Unique tiles, revisits and colour diversity overlap between null and reference, and the blind walkers' held-out error is if anything lower (0.0038 against 0.0048, ranges just overlapping).

6. **A long stay alone is not evidence of attraction.** The longest stays of the round belong to the walker that chooses nothing (two seeds at the full 1,000 steps). A long stay means something only in a walker that could have left, and it should not be read as desire on screen without that context.

7. **The Globalist's chance-level far-tile rate is specific to far tiles.** Its neighbour choices are as far above chance as anyone's (0.50–0.62 against 0.15). Its far tiles are taken at 0.14–0.17 against 0.13–0.14. That rate averages two cases: a far tile has under a 5 % chance of being chosen about 60 % of the time, and over 50 % about 11 % of the time. Far tiles are mostly dismissed and occasionally overwhelming.

8. **The Globalist's step-1 jump does not come from shifted random draws.** That part of the brief needs correcting. Seed 0 makes the same first draws in Milan and Paris, a far tile is on offer, and an untrained network happens to score it very high (chance of being chosen about 1.0). Separate streams don't prevent this. In 5-step checks with seeds 0–7, a far tile was offered at step 1 in 3 seeds and taken in 1, seed 0 again, 16,418 km away, at a chance of 0.999. The other two offers had a chance of 0.19 and 0.49. What separate streams do give is clean comparison: far-tile offers now nearly match across settings (18–21 per walk, the same for each seed apart from one walk that differs by one), and walks of the same seed stay identical until their first teleport.

9. **Straight-back steps are geometry plus real favourites.** The blind walker goes back 13–16 % of the time, which is exactly the chance of picking A among the tiles on offer. Scoring doubles it to 26–30 %. Roughly: 55 % of returns would happen anyway, about 40 % are A still being a favourite, about 5 % are the rescaling artefact, and interference adds nothing measurable. Training on B doesn't make A harder to draw: A's error at the return is 0.99–1.00 of what it was after training, and this looks the same whether or not the walker goes back. The real reason is that one visit barely teaches anything: it takes only 1–2 % off a tile's error. So a tile that was the most interesting neighbour two steps ago usually still is (top-ranked in 64–73 % of returns, 13–17 % when the walker doesn't return).

10. **Search by rejection survives partial agency, and even k=8 in the early part of a walk.** Bored still teleports 11–12 times a walk at every k, still in bursts, and in the first 150 steps 77–83 % of landings are rejected whatever the k. Choosing the landing does work as intended: the tile is much more novel (0.48 against 0.21 at k=8). But a rejection depends on what lies around the landing, not on the tile itself: after a rejected landing nothing beat the recent average in 49–79 % of the next 5 steps, against 0–17 % after a kept one. Novelty helps somewhat (kept landings 0.29–0.54, rejected 0.19–0.36), but not enough. Over half of all teleports fall in the first 150 steps (54–82 %), when the network is young. Only there do bursts look fixed; I have not tested why they gather there.

11. **Later in a walk, k=8 may end rejection and k=3 does not.** After step 150, rejected landings run 5 of 16 blind, 8 of 20 at k=3, 0 of 12 at k=8. The counts are small, so this is a lead and not a result.

12. **The variance between seeds does not reliably narrow.** Bored's ocean spread goes 0.37, 0.24, 0.29; the Reference's 0.39, 0.11, 0.41. At k=3, Bored's places widen to 5–27 and its median stay to 17–204, because one seed (s0) made 2 teleports and another (s1) 21. Four seeds are too few to separate a small narrowing from noise, and any effect is smaller than the seed spread.

13. **Novelty-chosen landings don't avoid the sea and don't bring settling.** The chosen tile is about as often ocean as the first draw (0.25–0.40 against 0.18–0.35), and is 10–25 % more textured. Ocean share rose for Bored (0.17 → 0.29–0.30) and colour diversity fell at k=8 (70.9 → 59.1), within the seed ranges. Longest stays did not grow (Bored 462 → 309 → 376).

14. **Appetite is one event, not a fade.** It runs at 11.5 for the first 500 steps and then wavers around zero for the other 4,500. The shape of cut B follows directly: 83 % of its running time is spent on the first 10 % of the walk, 72 % of steps pass in under one frame, and Patagonia falls from 37 s to 11.5 s. Cut B does feel like an accelerating indifference, but what it is showing is the first 500 steps of a network learning to draw at all. Cut A keeps the stays and the far terrain visible.

15. **A bigger eye does not clearly age later.** No curve is flat at step 1,000 (all still falling in the last half), and the three end within their bumps: at 1,000 steps the error is lowest for the current eye, then half, then double. The half-size eye sits near 0.013 until step 400 and then drops sharply, and the double-size eye's error goes *up* several times on the way. These bumps are as large as the differences, and depend on where the walker happens to be. With one seed each this does not answer whether the fade is about capacity or about having seen enough. I also don't see a capacity limit up to 1,000 steps: the quarter-size weights end about level with the current eye.

## Against the expectation (`notes/hikes_2910/expectations.md`)

| # | Prediction | What happened |
|---|---|---|
| 9 | Long stays 1.3–2× harder relative to held-out; texture ≥30 % higher | Relative error 1.7× and gradient 1.5×, as predicted, but raw error about equal |
| 9 | Ocean under 15 % in long stays, over 40 % in short places | Close but neither reached: 16 % and 32 % |
| 9 | Colour diversity higher within a place, lower pooled; texture–length correlation 0.3–0.5 | Pooled lower (53 / 77), within a place equal (47.3 / 47.1); correlation 0.30–0.31, at the low edge |
| 10 | Error falls 30–50 % in the first quarter, flattens, stays above held-out | **Wrong.** Median fall about 20 % over the whole stay, above held-out only 10 % of the time |
| 11 | Raw novelty falls 30–50 %, rescaled stays flat | **Wrong on raw:** it rose (1.17 and 1.22). Rescaled flat, by construction |
| 12 | Null: straight-back 13–17 %, far tiles about 1 in 8 | Straight-back right (13–16 %). Far tiles lower (5 of 73, about 1 in 15, a small count) |
| 12 | Null: revisits 44–50 %, unique tiles 500–560 | Too optimistic: 49–62 %, 379–513 |
| 12 | Null: teleports 2–6, places close to the reference | **Wrong.** 0–2 teleports, 2.75 places against 8.75 |
| 12 | Null: held-out and colour indistinguishable | Colour yes; held-out if anything lower for null |
| 13 | Top-ranked 35–50 %; all characters alike | Alike, right. Level too low: 50–65 % |
| 13 | Rhythm comes from the rules, scoring adds a little | **Wrong.** Removing the scorer cuts places to a third and steps per place grow sixfold |
| 13 | Globalist's chance level specific to far tiles, and split in two | Right |
| 14 | `legacy` exact for 200 steps; `split` different per seed | Right. Path, signals and held-out all identical (difference 0.0) |
| 14 | *(added late)* Far tile at step 1 in about 1 seed in 5, nearly always taken | 3 of 8 offered, a small count. **Wrong on taken:** 1 of 3 |
| 15 | About 15 of 26 points are geometry; interference under 15 % | Right: 15–17 of 26–30 points; no interference detectable |
| 15 | A's error rises after B in over 60 % | **Wrong.** 38–51 %, and by about nothing |
| 15 | Absolute-high over 60 %, relative-only under 25 % | Right: 76–94 %, 2–7 % |
| 16 | Bored teleports: 8–16, 5–10, 3–7 | Blind about right (7–20). **Wrong at k:** 2–21 and 7–14, no real drop |
| 16 | Bursts halve at k=3, mostly vanish at k=8 | **Wrong.** Largest burst 7.25, 5.75, 6.75. Only rejection after step 150 falls at k=8 |
| 16 | Longest stay 150–400 → 250–600 | **Wrong.** Blind 286–726, k=8 292–548 |
| 16 | Reference changes little with k | Right |
| 16 | Ocean spread narrows 30 → 15 points | **Wrong.** 37 → 29 for Bored, 39 → 41 for the Reference |
| 16 | Novel landings mostly bright, high-contrast land | **Wrong.** As much ocean as a first draw; a little more textured |
| 17 | Slope negative to ~1,000 steps then small | Earlier and more abrupt: over by step 500, wavers around zero after |
| 17 | Patagonia about 36 s on A, clearly less on B | Right: 37.1 s, 11.5 s |
| 17 | Cuts differ most in the last third | **Wrong.** They differ most at the start, by 158 s over steps 66–458 |
| 18 | Held-out half > current > double at 1,000 | **Wrong:** double > half > current (close, and one seed) |
| 18 | Half flattens at step 400–600, double not by 1,000 | **Wrong.** None has flattened; the half-size eye is the one still high at 400 |
| 18 | Runtime 2–3× at double | Double took 2.7× half, both alone. Not comparable with the current size, which ran three at once |

## For the next round

The action plan below comes first. After it:

1. **Is settling typical?** The one question left that decides the arc. Only one 5,000-step Bored walk exists. Seeds 1–3 at 5,000 steps would tell whether walks end in long stays or merely did once. Allow a little over 2 hours for all three, side by side (the earlier 5,000-step walk took 1.75 hours).
2. **Null with Bored's patience.** Patience 0.3 without the scorer would separate "the rule never fires" from "the scorer causes the boredom". Finding 4 is untested until then.
3. **Why bursts gather in the first 150 steps.** It looks like a young network, whose fast-changing scores leave its surroundings behind. Testing that means checking whether the bursts follow the fall in error or the start-up of the rescaling.
4. **The k=8 lead after step 150** (finding 11). Worth following only if the film ever needs landings with agency.
5. **Eye size with four seeds,** to 2,000 or more steps, if capacity against experience still matters. Keep each size alone on the machine so the run times compare.

## Action plan: the walk I recommend

**Choose the emergent arc, and say "textured" where the brief says "cannot finish learning".** Rejection is robust: it appears in every Bored seed at every k. The designed arc rests on an appetite signal with one event at step 500. Re-timing by it spends 83 % of the film on the first 10 % of the walk and takes two-thirds of the time away from Patagonia. **Cut A, not cut B, is the right clock**, and it gives the first 150 steps (where most rejections fall) 2.3 minutes on its own.

**The setting: `configs/h0111_walk_5k.yaml`, seed 0.** It is `h0111_bored` with only the length changed, and I have not run it.

| Setting | Value | Why |
|---|---|---|
| character | Bored (patience 0.3) | The most search by rejection. Reference has about a third as much |
| start, length | Paris, 5,000 steps | As before, so it compares with `h2910_bored_paris_s0` |
| choice | softmax, temperature 0.5 | The scorer is what gives the walker a rhythm (finding 4) |
| landing | blind, not `best_of_k` | k changes nothing that matters in the early bursts, adds no longer stays, and at k=8 costs colour (findings 10, 13) |
| random streams | `split` | Clean comparisons from here on |
| eye | current (272k weights) | No reason to change (finding 15) |
| seed | 0 | Its first 1,000 steps already show the arc: four rejected landings by step 72, then 726 steps on land starting in British Columbia, then a new search from step 862. Ocean is only 3 % of its tiles |

**To carry it out:**

1. Add dated predictions to `expectations.md`, as the ground rules ask. The first must be that steps 0–999 match `h0111_bored_s0` exactly, which is also the check that nothing has shifted.
2. Run `.venv/bin/python -m agent.walk configs/h0111_walk_5k.yaml --seed 0`. About 1.75 hours, going by the earlier 5,000-step Bored walk. Disk: keep the 30 GB tile cap; there is 70 GB free.
3. Put any film under `runs/`, never in a folder git can see (`notes/log_h0111.md` explains why).
4. Cut it on clock A.

**Two limits on this choice.** Seed 0 was picked because its opening looks good, so it can be a good film, but it isn't evidence of what walkers usually do. And the recommendation assumes the walk will end by settling somewhere, which I can't promise: it happened once. If the seed-0 walk doesn't settle, item 1 of the next round becomes the thing to do first.

## Config options added

All defaults reproduce the earlier walks. `agent/walk.py` keeps the old behaviour when these are absent.

| Option | Default | What it does |
|---|---|---|
| `rng_mode` | `legacy` | `legacy` or `split`: one independent random stream per decision |
| `choice` | `softmax` | `softmax` or `uniform`: uniform ignores the scores when choosing (the null walker) |
| `teleport_landing` | `blind` | `blind` or `best_of_k`: land on the most novel of `landing_k` random tiles |
| `landing_k` | `1` | How many tiles `best_of_k` draws |
| `log_prev_error` | `false` | Log `e_self_after` and `e_prev_after`; changes nothing in the walk |
| `ae_width` | `1.0` | Multiplies the autoencoder's channels and latent size |

`configs/h2910_fastlearner.yaml` also gained a comment marking `lr` 3e-3 as unsafe.

## Where things are

- **Films:** `runs/h0111_films/bored_paris_A_log_clock.mp4` and `bored_paris_B_log_clock_appetite.mp4` (10:00 each; not in `analysis/h0111/`, see the log)
- **Contact sheets:** `analysis/h0111/films/` for the two cuts, `analysis/h0111/contact_long_vs_short.png` for task 1
- **Walks:** `runs/h0111_{reference,null,bored,reference_k3,reference_k8,bored_k3,bored_k8}_s{0..3}`, `runs/h0111_eye_{half,double}_s0`, `runs/h0111_globalist_step1_s{0..7}` (5 steps each), `runs/h0111_verify_legacy_s0`
