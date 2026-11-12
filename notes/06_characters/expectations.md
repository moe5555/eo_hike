# Hikes 29.10: expectation

Written 2026-10-29, before the first walk. Not to be edited afterwards.

Reference numbers (`runs/global_perception_1k_s0`, 1,000 steps): 430 unique tiles, 3 boredom teleports, 23 steps with a long-jump offer of which 6 were taken (26 %; chance with ~8 candidates is ~16 %), highest B before a teleport 0.58.

1. **Bored** (`patience` 0.3). Teleports rise from 3 to 15–40 per 1,000 steps. More unique tiles than the reference (500+) and the largest spread of all except possibly the Globalist. Between teleports the walk looks like the reference.
2. **Globalist** (`p_long_jump` 0.2). About 200 offers; the far tile is taken more often than chance (25–35 %), because a tile from another biome is novel against an archive built around Milan, so 50–70 long jumps. Most unique tiles, most land-cover types, and the lowest held-out MSE at the end, because the held-out tiles are drawn from the whole planet. Fewer boredom teleports than the reference: a far tile on offer keeps max interest above 0.
3. **Localist** (`patience` 0.8, `p_long_jump` 0). No long jumps by construction and 0–1 teleports, so one continuous walk from Milan, never more than ~15 km per step. Fewest unique tiles (under 350), the highest revisit share, the smallest radius of gyration, and the highest held-out MSE.
4. **Fast learner** (`lr` 3e-3). The least certain prediction. Each tile becomes familiar in fewer steps, so it moves on sooner: more unique tiles than the reference. It also forgets faster, so it returns to old tiles more than the reference does once it has been away a while. Its held-out MSE falls faster early on and is noisier later.
5. **Seeds.** Globalist and Localist differ from the reference by more than the gap between seeds of the same character. Bored probably does too. Fast learner may not.

## Part 2: 5,000 steps from Paris (added 2026-10-29, before these walks)

Bored and Globalist, seed 0, the same configs started from Paris (cell 543U_17R) instead of Milan. Written after seeing the 1,000-step seed-0 results of part 1, so these predictions are informed by them.

6. **Bored, Paris.** About 5x the 1,000-step teleport count, so 60–90 teleports. Unique tiles grow roughly linearly, because every teleport opens a new neighbourhood: 2,000–2,500. The ocean share stays high (35–50 %), because a teleport that lands at sea finds a uniform neighbourhood and stays several steps.
7. **Globalist, Paris.** About 1,000 offers and 150–180 far tiles taken, with acceptance staying near chance (~15 %). Most unique tiles of the two (2,300–2,800) and the higher colour diversity.
8. **Paris itself.** The start matters for the first ~100 steps only: the Paris basin (city, then flat farmland) is more uniform than Milan's Alps and Po plain, so both walkers leave it early, through a boredom teleport or a long jump, within the first 50–100 steps. After that, the 5,000-step walks are statistically like the Milan walks scaled up.

## Round h0111 (added 2026-11-01, before any analysis or walk of this round; brief: `notes/07_film_arc/brief.md`)

Written after reading `observations.md` and `reflection_revisits.md` and the code of `agent/`, and before computing anything new. New walks start from Paris, 1,000 steps, seeds 0–3, with `rng_mode: split` unless stated.

9. **Interesting = hard to draw (offline).** Places are compared on arrival, with the error measured against the network's held-out error at that moment, because long stays come later in a walk. Tiles of long stays are harder to draw than tiles of short places by 1.3–2×, with mean gradient and grey-level entropy at least 30 % higher, in every character that has long stays. Ocean is under 15 % of long-stay tiles and over 40 % of short-place tiles. Colour diversity within a place is higher in long stays; pooled over a whole walk it is lower, because short places sample the whole planet. The hypothesis holds, but texture alone predicts a place's length only moderately (rank correlation 0.3–0.5).
10. **Error during a long stay.** It falls and the walker stays anyway: the chosen tiles' error falls by 30–50 % in the first quarter of a long stay, then flattens, and stays above the held-out error. The walker stays because interest is measured against the last ~50 steps, not because the terrain stays hard in absolute terms.
11. **Novelty's yardstick.** I have read the code, so this is not a prediction: novelty is measured against an archive of every visit, not the replay buffer. The prediction: raw novelty falls by 30–50 % from the first to the last 1,000 steps of the Paris walks, while its rescaled form stays flat. So the signal does fade and the score cannot.
12. **Null walker against the reference (Paris, 4 seeds each).** Straight-back share 13–17 % (reference 24–28 %), revisit share 44–50 % (reference 50–56 %), unique tiles 500–560 (reference 430–520). Teleports about the same as the reference (2–6). Far tiles taken about one time in eight, against one in four. Held-out MSE and colour diversity are not distinguishable from the reference. Places and steps per place are close to the reference's, within the seed spread.
13. **The scorer's influence.** In all characters the chosen tile is the top-ranked one 35–50 % of the time, against 12–15 % for a uniform choice, and every character looks alike here because they share a temperature. So rhythm comes from the rules (patience, jump offers) and scoring adds about 7 points of revisits and 10 points of straight-back steps. The Globalist's chance-level acceptance is specific to far tiles: its neighbour choices are as far above chance as everyone else's. Its far tiles are taken nearly always or nearly never, depending on the moment, and those average out near chance.
14. **Streams.** `legacy` reproduces `global_perception_1k_s0` exactly for 200 steps. `split` gives a different walk with each seed.
    - *Added 2026-11-01, late in the round, before the check was run:* the Globalist's step-1 jump comes from the untrained network, not from shifted draws. Under `split`, with seeds 0–7 and 5 steps each, a far tile is on offer at step 1 in about 1 seed in 5 (`p_long_jump` 0.2), and is taken nearly every time it is offered. So `split` does not stop the jump, it only decides independently which seeds get one.
15. **Straight-back steps.** About 15 of the ~26 points come from geometry, which is what the null walker does anyway. Error on A rises after training on B in over 60 % of cases, but by under 10 %, and about as often when the walker does not go back, so interference explains under 15 % of events. A's raw scores are high in absolute terms in over 60 % of the excess returns, and only relatively high in under 25 %. Straight-back steps are mostly geometry plus real favourites, not an artefact.
16. **Teleport landings.** Bored: blind 8–16 teleports per walk, `best_of_k` k=3 5–10, k=8 3–7. Bursts survive at k=3 at about half the rate, and mostly vanish at k=8, though not entirely, because a novel tile can still bore the walker. Longest stay grows from 150–400 steps (blind) to 250–600 (k=8). Reference: blind 2–6, with k changing little because it teleports so rarely. The spread of ocean share across seeds narrows, from a range of about 30 points (blind) to about 15 (k=8). Places and steps per place stay about as variable between seeds as before. The most novel of k tiles will usually be bright or high-contrast land (snow, desert, cloud).
17. **Appetite.** The slope of log held-out error is negative through the first ~1,000 steps and then wavers around a small negative value, with stretches at or above zero during the longest stays, when the network forgets the planet while specialising. On the log clock (c near 100), steps 3,696–4,724 of Bored (Patagonia, 1,029 steps) get about 36 s of the 10 min on cut A, and clearly less on cut B. The two cuts differ most in the last third.
18. **Eye size.** Held-out error at step 1,000 is ordered half > current > double. The half-size eye flattens first (around step 400–600) and the double-size eye has not flattened by step 1,000, so a bigger eye ages later. That points to capacity, but 1,000 steps may be too few to separate capacity from having seen enough. Runtime about 2–3× at double size.

## Round h0311 / experiment 08 (added 2026-11-05, before any Stage 1 walk; brief: `notes/08_character_sheet/brief.md`)

Written after the Stage 0 report (`notes/08_character_sheet/observations.md`) and before any new walk. Every walk is the h0111 Reference with one key changed: Paris, 1,000 steps, split streams, seeds 0–3. Readouts are the core 17 of that report. "Taste" means the settled phase (steps 150–999), in SDs of what was on offer. Reference values (mean of seeds 0–3): places 8.75, median steps per place 103, teleports 3.5, rejected landings 0.75, far tiles taken ÷ chance 1.60, revisits beyond blind 0.18, straight-backs beyond blind 0.12, top tile beyond chance 0.42, snow/ice/cloud −0.35, brightness 0.34, texture 0.06, contrast 0.13. On the panel, surprise against texture ρ 0.58.

19. **Reference seeds 4–7.** Every core readout's mean over seeds 4–7 lies within the range of seeds 0–3, except at most two. The pooled seed SD changes by under 30 % for the choice and returns readouts. Rhythm readouts are the exception: one seed of the four will have 1–2 places, as Null s0 did, because a walk that settles early stays settled.
20. **Novelty only** (`w_g` 0). With one signal instead of two, interest has a smaller spread in z units, so at the same temperature the top tile is chosen less: 0.28–0.36 beyond chance. On the panel, progress is the signal that likes bright tiles (ρ 0.30) and dislikes texture (−0.20), so removing it makes taste lean towards texture: texture 0.15–0.35, brightness near 0 (−0.1 to 0.15), and snow/ice/cloud avoided at least as strongly (−0.35 to −0.6). Revisits and straight-backs beyond blind fall by a third. Rhythm within one seed SD of the Reference.
21. **Progress only** (`w_n` 0). The top tile is also chosen less (0.28–0.36). Taste the other way: brightness 0.4–0.8, texture below 0 (−0.3 to 0), and snow/ice/cloud avoided less (−0.2 to 0.1). Revisits beyond blind rise, to 0.20–0.30, because progress does not fall for a tile already visited the way novelty does. Rhythm between Null and Reference, as the brief guesses: fewer places (3–7), longer stays.
22. **Surprise added** (`w_e` 1). Three signals widen interest, so the top tile is chosen slightly more (0.44–0.52). The avoidance of snow, ice and cloud goes: −0.1 to +0.3, a lead against the Reference. Texture and contrast rise to 0.2–0.5. Longer stays (median steps per place 150–400) and fewer teleports (0–3), with one seed of four stuck on bright or rough terrain for over 400 steps.
23. **Habituation** (`k_nn` 3 and 30). With k = 3, a tile's own archive entries weigh more in its novelty, so returns fall: revisits beyond blind 0.10–0.15, straight-backs 0.06–0.10. With k = 30, the reverse but weaker: revisits 0.18–0.24. Rhythm, taste and the panel's surprise unchanged within one seed SD; the panel's novelty against texture is lower at k = 30 (ρ 0.30–0.40), because averaging over 30 neighbours blurs it.
24. **Attention span** (`ema_alpha` 0.005 and 0.08). At 0.005 (about 200 steps) the young phase has 0–1 teleports and the settled phase more than the Reference's; places overall within one seed SD. At 0.08 (about 12 steps), interest is always measured against the last few tiles, so boredom fires less: teleports 0–2, median steps per place over 150. Taste and returns within one seed SD for both.
25. **Decisiveness** (`temperature` 0.2 and 1.0). At 0.2 the top tile is chosen 0.60–0.75 beyond chance, revisits beyond blind 0.25–0.35, straight-backs 0.18–0.28, and every taste readout further from zero (snow/ice/cloud −0.5 to −0.8). At 1.0 the walk drifts toward Null: top tile 0.18–0.28, returns about halved, taste halved, and fewer places (3–7), as the brief guesses. Both are among the clearest effects of the round: leads on the choice and returns readouts at four seeds.
26. **Scale of attention** (`crop_px` 32 and 128). On the panel, surprise against texture is ρ 0.65–0.80 at 32 (fine texture survives, since no averaging) and 0.30–0.50 at 128 (four-by-four averaging smooths fine texture away, so brightness and large structures carry more of the surprise). In choices, texture among neighbours is preferred more at 32 (0.1–0.3) than at 128 (−0.1 to 0.1). Rhythm: no measurable effect. Held-out error is not compared with the Reference.
27. **Patience alone** (`patience` 0.8). 0–2 teleports and 0 rejected landings, places 2–6, median steps per place 200–600. Far tiles are still taken above chance (1.2–2.0). Returns beyond blind slightly higher than the Reference (0.18–0.24), because stays are longer.
28. **Wanderlust** (`p_long_jump` 0 and 0.2). At 0, places equal teleports + 1, and places 2–7. At 0.2, about 200 offers, far tiles taken ÷ chance 1.0–1.6, 30–60 places, median steps per place under 20, and 0–3 teleports, because a far tile on offer keeps interest up. Taste unchanged for both; at 0.2 returns beyond blind fall by a third, because many places last too few steps to return to.
29. **Learning speed** (`update_steps` 1 and 12). At 1, tiles stay novel longer: median steps per place 1.5–3× the Reference, revisits beyond blind 0.20–0.30, held-out error at step 1,000 1.5–3× the Reference. At 12, restless: places 12–25, teleports 6–15, and held-out error lower than the Reference in three seeds of four; at most one seed of four has a dead network (held-out flat near 0.25).
30. **Null with Bored's patience** (`choice: uniform`, `patience` 0.3). The rule fires more by itself: teleports 4–12 and places 5–13, against Null's 0.5 and 2.75. So most of Bored's restlessness comes from the boredom rule and the patience setting, not from the scorer choosing. Rejected landings fewer than Bored's (0–5), because a uniform walker does not prefer the tiles that keep interest up.
31. **Memory** (`buffer_size` 512 and 8,192). No lead on any rhythm or taste readout. At 512, revisits beyond blind rise by 0.02–0.06 ("nostalgia", v1 finding 3) and held-out error at step 1,000 rises; at 8,192, held-out error is lower in three seeds of four and returns are unchanged.
32. **Capacity** (`ae_width` 0.5 and 2; s0 from h0111). Held-out error at step 1,000 ordered 0.5 > 1 > 2 in three seeds of four. On the panel, surprise against texture is lower at width 2 (ρ 0.40–0.55): a bigger network draws texture better. Rhythm, returns and taste: no measurable effect.
33. **Stride** (`radius_km` 25). About twice the candidates. The top tile beyond chance stays near the Reference (0.38–0.46), straight-backs beyond blind fall to 0.05–0.09, because the tile just left is one of many. Unique tiles up by 20–40 % (not a core readout). Rhythm within one seed SD.
34. **Aversion to returning** (`return_cost` 0.5; `no_backstep`). With a cost: revisits beyond blind 0.06–0.12, straight-backs 0.04–0.08; top tile unchanged, since the cost is part of interest. Without straight-backs: straight-backs beyond blind are 0 by construction, revisits beyond blind fall to 0.08–0.14, and places last longer (median steps per place 120–250), since A-B-A oscillation no longer wears a place out. Taste unchanged for both.
35. **Across the round.** About half of the 24 settings show at least one lead on the core readouts beyond what chance gives (about 1.5 per setting). The Eye readouts move only for `crop_px` and `ae_width`. The choice and returns readouts move for the taste and temperature settings, and for `return_cost` and `no_backstep`. Rhythm moves for `patience`, `p_long_jump`, `ema_alpha`, `update_steps` and Null at patience 0.3.

## Experiment 09, Stage 1 (added 2026-11-08, before any Stage 1 walk; brief: `notes/09_compass/brief_e09_compass.md`)

Written after the Stage 0 report (`notes/09_compass/observations.md`, approved as proposed) and before any Stage 1 walk. Walks: the compass Reference (the e08 Reference with `nav: compass`, `drive_signal: interest_long`, r_min 15 km, r_max 2,000 km, snap floor 7.5 km), Paris, 1,000 steps, seeds 0–3, at Δ 0.35, 0.175 and 0.7. Offline, on the e08 logs, Δ 0.35 gave 59 % of steps at r_min, 9 % at r_max and 3.6 r_max episodes per 1,000 steps (median length 20 steps); a blind walker with those radii left Europe in every walk, at a median step of 500. Shares are of steps after the warm-up (step 50). Classic Reference for comparison: revisits beyond blind 0.18, straight-backs beyond blind 0.12, top tile beyond chance 0.42.

36. **Δ 0.35, the loop.** Going far restores the drive, so the walker spends less time far than the offline mapping says: 2–8 % of steps at r_max (offline 9 %), episodes at r_max of median 1–5 steps (offline 20), 1–5 episodes per 1,000 steps, and 55–75 % of steps at r_min. Every seed stays within 2 r_min until step 150. At least three seeds of four reach r_max at least once.
37. **Δ 0.35, recovery.** In every seed that reaches r_max, d rises more over the 10 steps after a step at r_max than after a step at r_min (recovery > 0).
38. **Δ 0.35, range.** Three or four seeds of four leave Europe by step 1,000, and spend 20–50 % of their steps outside it. Ocean share of the cells stood on 0.15–0.40 (classic Reference 0.18), higher than the classic walker's in at least three seeds.
39. **Δ 0.175 (half).** The walker goes far often and chatters: 8–25 % of steps at r_max, 4–15 episodes per 1,000 steps, most of them 1–3 steps long, and r_min 40–65 %. Every seed leaves Europe.
40. **Δ 0.7 (double).** r_max is reached in at most one seed of four; the 90th percentile of the step length stays under 300 km in at least three seeds; at least two seeds never leave Europe.
41. **Returns and choice (Δ 0.35).** At r_min the eight offers are almost the classic neighbourhood, so the scorer's readouts stay near the classic walker's, slightly lower because far steps break up places: revisits beyond blind 0.08–0.18, straight-backs beyond blind 0.05–0.12, top tile beyond chance 0.33–0.45.
42. **Period.** No regular rhythm: where the autocorrelation of log r has a first peak at all, it lies at 100–400 steps, and in at most two seeds of four at Δ 0.35.
43. **Cost.** 35–75 min per walk three side by side; fewer than 20 dropped candidates per walk; no walk fails. The young phase (steps 0–149) runs at classic speed, because the drive stays near 0.

Scored 2026-11-08 in `notes/09_compass/observations.md`, "Against the predictions (36–43)": 1 right (40), 1 mostly right (41), 1 partly (43), 4 wrong (36, 38, 39, 42), 1 untestable (37). No compass walk reached r_max; the Stage 0 mapping had counted on dips that followed the classic walker's own far jumps.

## Experiment 09, Stage 1 again (added 2026-11-08, before any round-2 walk; report: `notes/09_compass/observations.md`, Stage 1)

Written after the Stage 1 report and a 300-step smoke walk at Δ 0.35 (`e09_smoke_avg20_s0_s0`: one step at r_max, at step 51, then 831, 706 and 797 km; 58 % of steps at r_min, 27 % at middle radii, 35 % outside Europe). Walks: the compass Reference with the drive's averages at ~20 and ~200 steps (`drive_alpha_short` 0.05, `drive_alpha_long` 0.005), Paris, 1,000 steps, seeds 0–3, at Δ 0.25, 0.35 and 0.5. Offline at Δ 0.35, open loop: 2.6 % at r_max and 4.5 episodes per 1,000 steps on the Stage 1 compass logs, 19 % and 10.3 on the classic logs. Shares are of steps after the warm-up.

44. **Δ 0.35, the loop.** Between the two offline numbers, nearer the compass one: 2–10 % of steps at r_max, 3–10 r_max episodes per 1,000 steps, median length 1–4 steps; 50–70 % at r_min; middle radii 20–35 %. All four seeds reach r_max.
45. **Δ 0.25 and 0.5.** At 0.25: 6–20 % at r_max, 6–15 episodes. At 0.5: 0.5–4 % at r_max, 1–5 episodes, and at least three seeds of four reach r_max. The share at r_min is about the same at all three Δ (set by the sign of d, Stage 0 finding 8): within 0.1 of each other.
46. **Recovery (Δ 0.35).** Landing in new terrain brings a novelty spike, so d rises more over the 10 steps after a step at r_max than after one at r_min: recovery > 0 in at least three seeds of four.
47. **Range (Δ 0.35).** Three or four seeds leave Europe and spend 15–50 % of their steps outside it; radius of gyration 1,000–5,000 km; 2–5 continents.
48. **Returns and choice (Δ 0.35).** Far steps break up places, so returns fall below round 1's (revisits 0.16, straight-backs 0.09): revisits 0.06–0.15, straight-backs 0.04–0.09. Top tile beyond chance 0.36–0.46.
49. **Early far steps.** The drive now moves from step 20, so far steps can come right after the warm-up, as in the smoke walk: in at least four of the twelve walks the first step at r_max comes before step 150.
50. **Cost.** 25–50 min per walk three side by side (middle radii fetch at almost every step); no walk fails; fewer than 20 fetches dropped per walk.
51. **The choice.** Δ 0.35 or 0.5 is chosen, 0.35 more likely.

Scored 2026-11-08 in `notes/09_compass/observations.md`, Stage 1 round 2: 1 right (49), 2 partly (46, 50), 5 wrong (44, 45, 47, 48, 51). Δ 0.25 was chosen; the closed loop went far less often than either set of offline logs suggested, and the early far steps were a start-up effect of the drive.

## Experiment 09, the compass Reference (added 2026-11-09, before any `e09_ref` walk)

Written after the Stage 1 round-2 report and an 80-step check walk (d is 0 through step 72). Walks: `e09_ref` (Δ 0.25, the drive's averages at ~20 / ~200 steps, the drive counting from step 50), Paris, 1,000 steps, seeds 0–7. Round 2 at Δ 0.25 (drive from step 0): 4 of 4 seeds at r_max, 2.6 episodes per 1,000 (1.9 after step 60), first r_max at step 51 in three seeds.

52. **No early jump.** No step at r_max before step 70 in any seed; where a seed reaches r_max, the first time is between steps 150 and 800.
53. **The loop.** 6–8 of 8 seeds reach r_max (3–4 of seeds 0–3); 1–4 r_max episodes per 1,000 steps (seed mean); 0.75–0.90 of steps at r_min; no chattering.
54. **Range.** At least 5 of 8 seeds leave Europe; steps outside Europe 0.1–0.5 (seed mean), less than round 2's 0.54 because the walk now starts with ~150 more steps near Paris.
55. **Recovery.** Positive in every seed that reaches r_max.
56. **Returns and choice.** As round 2 at Δ 0.25, within its seed range: revisits beyond blind 0.13–0.29, straight-backs 0.07–0.17, top tile beyond chance 0.45–0.54.

Scored 2026-11-09 against the eight `e09_ref` walks (`notes/09_compass/log.md`, 2026-11-09): 3 right (54: 6 of 8 seeds leave Europe, 0.27 of steps outside it; 55: recovery 0.08–0.60 in all 7 seeds that reach r_max; 56: revisits 0.16, straight-backs 0.09, top tile 0.46, all three below round 2 but inside its range), 1 mostly right (52: no r_max before step 208; the first r_max between 150 and 800 in 6 of the 7, seed 4 at 816), 1 partly (53: 7 of 8 seeds reach r_max (4 of 4 in seeds 0–3), 0.77 at r_min, no chattering, but 5.5 r_max episodes per 1,000 steps, not 1–4). Not foreseen: in four seeds (0, 1, 4, 6), unbroken runs of 57–127 steps at r_max late in the walk. Offers at r_max carried less novelty than offers at r_min in all 7 seeds that went far, so the short average stayed below the long one until the long one came down.

## Experiment 09, Stage 2 (added 2026-11-09, before any Stage 2 walk; brief: `notes/09_compass/brief_e09_compass.md`, Stage 2)

Written after the eight `e09_ref` walks (above) and before any Stage 2 walk. Walks: Paris, 1,000 steps, seeds 0–7: the compass Null (`choice: uniform`), shifted, shuffled and fixed radius (each replays the `e09_ref` walk of the same seed), local only (r_max 15 km). Starts B (Tamanrasset) and C (Douala), seeds 0–3. Lead and result as in e08 (D10): lead = four seeds of the same sign, |mean| above half the Reference's range; result = eight seeds, at least 7 of the same sign. The compass Reference over eight seeds, for comparison: 5.5 r_max episodes per 1,000 steps (0–10.5), 0.77 at r_min, 18 places (11–27), median dwell 33 steps, radius of gyration 3,328 km (694–5,864), 586 unique cells, recovery 0.26, period 147 steps (43–321), dwell against fall ρ −0.03 (−0.49 to 0.50), revisits beyond blind 0.16 (0.12–0.19), straight-backs 0.09 (0.05–0.13), top tile beyond chance 0.46 (0.43–0.50). The aim, restated: rhythm, style, preference and clusters that differ from a Null, with as little set by hand as possible.

57. **The compass Null: the radius without choice.** The drive still moves the radius: at least 6 of 8 seeds reach r_max; 0.6–0.9 of steps at r_min. Returns and choice are gone: revisits and straight-backs beyond blind within ±0.04 (seed mean), top tile beyond chance within ±0.03, texture and contrast of the chosen cell within ±0.15. Against the Reference: leads, toward the Reference, on revisits, straight-backs and top tile.
58. **The dull far is the world's.** Median novelty of the offers at r_max is below that of the offers at r_min in at least 6 of the Null seeds that reach r_max, as it is in all 7 Reference seeds that do. At least 3 of 8 Null seeds have an unbroken run of 20 or more steps at r_max.
59. **Does going far restore the drive? (shifted radius, the main control).** Raw recovery: Reference minus shifted above 0, a lead (part of it is regression to the mean, see `recovery_at_d`). `recovery_at_d` in the shifted and shuffled walks is within ±0.1 of 0 or below it (seed mean): at the same d, a step at r_max does not raise d more than a step at r_min, because far offers are duller.
60. **Shifted radius: the rest.** Same radii in another order, so no lead between the Reference and shifted on more than one of radius of gyration, unique cells, places and median dwell; none on revisits, straight-backs, top tile or dwell against fall.
61. **Shuffled radius: the rhythm cut.** Period below 20 steps or none in at least 6 of 8 seeds. Far steps scattered, so places at least three times the Reference's (seed mean at least 54) and median dwell at most 8 steps; revisits beyond blind below the Reference's, a lead.
62. **Fixed radius** (16.5–50.7 km by seed, the geometric mean of the Reference walk's radii). Radius of gyration below 1,500 km in at least 6 of 8; below the Reference's, a lead. Revisits beyond blind 0.05–0.20.
63. **Local only.** Radius of gyration below 400 km in all eight; one or two places per walk. Returns as the Reference's, against the brief's first guess (round 1, almost all local, had 0.16 against the Reference's 0.16): no lead on revisits or straight-backs. Unique cells below the Reference's (lead). No lead on held-out error at step 1,000.
64. **Starts B and C.** Tamanrasset: uniform desert wears out faster, so the first r_max comes before step 400 in at least 3 of 4 seeds, and the share at r_max is above Paris's 0.066 in at least 3 of 4. Douala: first r_max between steps 150 and 800 in at least 3 of 4. Revisits beyond blind above 0.05 in all 8 walks.
65. **Character against the Null (the aim).** The Reference differs from the compass Null by a lead on preference (top tile, and texture or contrast) and on clusters (revisits, straight-backs), and not on rhythm: r_max episodes per 1,000 steps and period within the Null's range, no lead. The dip in the drive does not need a choice.
66. **Cost.** 48 of 48 walks finish; 15–35 min per walk three side by side; Stage 2 in under 7 h; fewer than 20 fetches dropped per walk.

Scored 2026-11-09 in `notes/09_compass/observations.md`, Stage 2: 4 right (60, 62, 63, 65), 4 mostly right (57, 59, 61, 66), 2 partly (58, 64), none wrong. The far offers' low novelty is the rule's selection, not the world's: with the radius decoupled from d (shifted, shuffled), far and near offers are about level (58). Going far does not raise the drive (`recovery_at_d` 0.025 in the shuffled walks), so the Reference's raw recovery is regression to the mean. Tamanrasset does not send the walker far sooner; once far it stays far longer (64). Not foreseen: three schedule walks lost their eye for 100–425 steps.

## Experiment 09, Stage 3a: the larger eye (added 2026-11-09, before any Stage 3a walk; brief: `notes/09_compass/brief_e09_compass.md`, Stage 3, amendments of 2026-11-09)

Walks: the compass Reference with `crop_px` 128 (~5.3 km) and 192 (~8.0 km), Paris, seeds 0–3, each with a shifted and a shuffled radius control replayed from its own walk, with the warm-up held at r_min (24 walks). Compared with `e09_ref` seeds 0–3 (the 2.7 km eye) and with Stage 2's controls. Lead as in e08 D10 (four seeds of one sign, |mean| above half the Reference's range). Held-out error compares only within one `crop_px`. The world-view readouts are read offline from checkpoints every 100 steps.

Already measured before these predictions (offline, Stage 2 walks, `results/worldview.csv`; not predictions):
- At the 2.7 km eye the land-cover probe does not beat colour and texture: balanced accuracy at step 1,000 is 0.37 (Reference) and 0.35 (Null), against 0.50 for colour and texture, and 0.40 for the untrained encoder. Below colour in 16 of 16 walks. R² of the class fractions is level with colour (0.28 and 0.26 against 0.25).
- The embedding is ordered at continental scale. Cosine distance rises from about 0.40 at 25–100 km to about 0.88 beyond 7,700 km. Tobler ρ is 0.17 (colour 0.04), and there is no plateau before 7,700–12,400 km (colour's plateau is at 3,000 km).
- Reference against the compass Null: no lead on any world-view readout.
- The baselines barely change with the eye. Colour and texture: 0.49 at 128 and 192. Untrained encoder: 0.43 and 0.41.

67. **The probe at the larger eyes.** Balanced accuracy at step 1,000 is still below colour and texture (0.49) in at least 7 of the 8 eye walks (`e09_crop128`, `e09_crop192`), between 0.33 and 0.45. It is higher at 192 than at the 2.7 km eye (same seed) in at least 3 of 4 seeds. Reason: a 192 px crop area-resized to 32×32 is closer to a colour summary of the tile, which is what the probe reads best.
68. **Geography with eye size.** Tobler ρ at step 1,000: 0.12–0.25 at both eyes, and no lead against the 2.7 km eye in either direction. The plateau distance stays at 7,700 km or more at every eye. At 2.7 km it is already at the top of what 5,000 probe cells can show, so "does the plateau grow" will read as no.
69. **The loop stays open.** In the shifted controls, `offer_n_gap` is within ±0.03 of 0 (seed mean) at both eyes. In the shuffled controls, `recovery_at_d` is under 0.1 in all four seeds at both eyes. Going far does not pay at 5 or 8 km either: the embedding already separates far from near at 2.7 km, and the gap is still 0 there, so a larger eye is not what is missing.
70. **The walk at the larger eyes.** At least 3 of 4 seeds reach r_max at each eye. Far episodes per 1,000 steps and the period lie within the 2.7 km Reference's seed range (0–10.5; 43–321), with no lead. Revisits, straight-backs and top tile: no lead against the 2.7 km eye.
71. **Controls at the larger eyes, as in Stage 2.** Shifted: no lead on range, places, returns or top tile against its own eye. Shuffled: period under 20 steps in all 4 seeds, at least 3 times as many places.
72. **No collapse.** None of the 24 walks is flagged collapsed, since the schedules no longer go far during the warm-up. If one is, it is a control.
73. **Reference against the Null, again.** Not walked at the larger eyes. At 2.7 km it is answered above (no lead), and I expect no lead at 128 or 192 either, but that is not tested here.
74. **Cost.** 24 of 24 walks finish, 15–35 min each three side by side, Stage 3a in under 3.5 h; at most 1 GB of new checkpoints in all; the offline world-view pass under 20 min.

Scored 2026-11-10 in `notes/09_compass/observations.md`, Stage 3a: 1 right (72), 4 mostly right (68, 70, 71, 74), 2 partly (67, 69), 1 not tested (73), none wrong. The larger eye does not open the loop: in the shifted controls, far offers are less novel than near ones even with the radius decoupled from d (−0.061 at 5.3 km, −0.054 at 8 km, the same on land only), not level as predicted (69). Shuffled `recovery_at_d` stays at 0.02–0.05 in seeds that go far. The plateau does not grow, and no eye beats colour. The 8 km probe is not better than the 2.7 km one (67: higher in 1 of 4 seeds). Not foreseen: the 8 km walker chooses high contrast (+0.33, lead), the larger eyes leave for r_max late (steps 678–871), and the shuffled walks read land cover slightly better.

## Experiment 09, the progress test and the long walk (added 2026-11-10, before any of their walks; log 2026-11-10)

Walks:
- `e09_progress`: the compass Reference with `drive_signal: progress_z`, the walker's own z-score of learning progress at the chosen cell, instead of interest on the long yardstick. The choice is unchanged. Paris, 2.7 km eye, seeds 0–3.
- Its shifted and shuffled controls, replayed from it with the warm-up held at r_min.
- Then walker v1, frozen by the rule in the log, alone for 15,000 steps (seed 0, checkpoints every 500 steps).

Lead as in e08 D10: four seeds of one sign, |mean| above half the compared group's range over those seeds.

Compared with, on seeds 0–3:
- The Reference: 5.8 r_max episodes per 1,000 steps (1.1–10.5), period 128 (43–218), 16.5 places, top tile 0.45, revisits 0.16, straight-backs 0.09, settled contrast 0.19.
- The compass Null: top tile 0.01, revisits −0.00, straight-backs −0.01, settled contrast −0.01. World-view at step 1,000: balanced accuracy 0.35, R² 0.24, Tobler ρ 0.11.

Offline previews (`analysis/e09/progress_offline.py`; log 2026-11-10; open-loop, not predictions):
- The progress drive replayed on the eight Reference walks goes far in 8 of 8: 4.0 episodes per 1,000 steps (1–8), first r_max at steps 377–877.
- In a schedule walk the drive steers nothing. So on Stage 2's shuffled walks, a progress d replayed is the d a progress drive would have had. Its `recovery_at_d` is 0.005 (−0.047 to +0.030), and the far − near gap in offered progress z is −0.006.

75. **The progress drive goes far.** At least 3 of 4 seeds reach r_max, and in at least 3 of those the first r_max is after step 300. Episodes per 1,000 steps are 1–10 and the share at r_max 0.02–0.15. No lead against the Reference on share at r_max, episodes, period, places or radius of gyration.
76. **Far does not pay in novelty.** In the shifted controls, `offer_n_gap` is between −0.10 and +0.03 (seed mean), and it is not above 0 in every seed that goes far.
77. **Far does not pay in progress either.** In the shuffled controls, `recovery_at_d` (now on the progress drive) is within ±0.05 in all 4 seeds. `offer_gz_gap` is within ±0.15 of 0 (seed mean) in the shifted and in the shuffled controls. The progress walk's raw recovery is above 0 in at least 3 of the seeds that go far (regression to the mean, as in Stage 2).
78. **Selection in the progress walk.** In the progress walk itself, near offers carry more progress than far ones: `offer_gz_gap` < 0 in at least 3 of the seeds that go far. Near is sampled while near progress pays. Low confidence: under the Reference this gap was +0.11 (−0.23 to +0.50).
79. **Character against the Null holds.** Against the compass Null: leads on top tile, revisits, straight-backs and settled contrast. Against the Reference: no lead on any of the four. Rhythm: no lead against the Null on episodes or period.
80. **World-view.** No lead against the Reference on balanced accuracy, R², Tobler ρ or neighbours within 500 km. Below colour and texture in 4 of 4, plateau 7,700 km or beyond. No lead against the Null on balanced accuracy or Tobler ρ.
81. **Controls.**
    - Shifted: no lead against the progress walk on gyration, unique cells, places, revisits, straight-backs or top tile.
    - Shuffled: period under 20 steps in all 4 seeds, and at least 3 times the places in at least 3 of 4.
82. **No collapse** in any of the 12 walks.
83. **Cost.** 12 of 12 finish, 15–30 min each, the batch in under 2 h. The world-view pass takes under 10 min.
84. **v1 is the compass Reference.** By the rule in the log, the progress drive does not make far pay. So v1 keeps `interest_long`, unchanged from `e09_ref`.

Scored 2026-11-10 in `notes/09_compass/observations.md`, the progress test: 5 right (76, 78, 82, 83, 84), 3 mostly right (77, 80, 81), 2 partly (75, 79), none wrong. A drive on progress does not make far pay. Shifted far − near in novelty is +0.015, as under the Reference's own controls. Shuffled `recovery_at_d` on the progress drive is 0.014. Far offers carry less progress than near (−0.16 shifted, −0.34 in the walk). So v1 is `e09_ref`. Not foreseen: the progress walker is a homebody. It makes 1.3 far bouts per 1,000 steps (lead against the Null, not against the Reference), late (steps 803–982) and long (36–73 steps), because progress stays near 0 far and the drive does not recover (75, 79). The character leads against the Null all hold. The shifted controls revisit more than the progress walk (+0.044, lead; 81).

The long walk (predictions written for v1 = `e09_ref`; if the rule picks the progress drive, 85 does not apply and the rest stand):

85. **It starts as `e09_ref_s0`.** The first 1,000 steps choose the same tiles as `e09_ref_s0`, step for step. Checkpoints draw no random numbers, and the step count changes nothing before step 1,000. The exception would be a fetch dropped in one walk and not in the other.
86. **The rhythm lasts.** There are r_max episodes in at least 12 of the 15 blocks of 1,000 steps, and 3–10 per 1,000 steps over the walk. The share at r_max in steps 10,000–15,000 is within a factor of 2 of steps 1,000–5,000. The drive is relative, so age does not make it go far more often.
87. **Novelty wears down, the drive doesn't.** The median chosen novelty in the last block is below 0.7 times that of block 2, as the archive fills with look-alikes. Held-out error at step 15,000 is at or below its value at step 1,000.
88. **Returns, choice and range.** Over the whole walk:
    - revisits beyond blind 0.10–0.25, top tile beyond chance 0.40–0.50;
    - radius of gyration 4,000–8,000 km, at least 5 continents;
    - 5,000–9,000 unique cells. That is the number of distinct tiles on the path, the material for a GAN.
89. **World-view with age.** At step 15,000, balanced accuracy is 0.33–0.48, still below colour and texture (0.50), and 0.00–0.08 above its value at step 1,000. Tobler ρ is 0.12–0.30. The plateau is 7,700 km or beyond.
90. **No collapse, and the cost.** No collapse flag over 15,000 steps. The walk takes 4–8 h alone, without a crash. Fewer than 100 fetches are dropped. The run folder is under 300 MB.

Scored 2026-11-10 in `notes/09_compass/observations.md`, the long walk: 3 right (85, 86, 90), 1 mostly right (88: top tile 0.51 and 10,002 cells, just above), 1 partly (87: held-out falls, but novelty rises, 0.41 → 0.55), 1 wrong (89: Tobler ρ falls to −0.02 and the plateau is gone from step 1,500; land cover −0.02 from step 1,000). Not foreseen: a taste for texture, contrast and snow that grows for 6,000 steps, and a drift into the high north (78 % of steps north of 50° N from step 5,000).

## Experiment 12: the two-eye walker (added 2026-11-12, before any factorial walk; brief: `notes/brief_landsat_pipeline.md`, E13–E16; log: `notes/12_two_eye/log.md`)

Walks: the short factorial on the e10 pass world in sqrt tone (`c10680m_256px_cir_sqrt`), 1,000 steps, seeds 0–1: `e12_v1`, `e12_grid_mean` (k = 16), `e12_grid_top4`, `e12_grid_top1`, `e12_two_top4` (w_glance 1), `e12_two_top4_g2` (w_glance 2), `e12_null` (two eyes, top-4, uniform choice). Plus `e12_two_top4_shifted` and `_shuffled` (e09's existing radius schedules replayed), the brief's check of the interest statistics. Then a 500-step smoke walk on the mission world.

Already seen, so not predicted: v1 is bit-identical (60 steps); a 120-step two-eye smoke walk (`e12_smoke_two_s0`) gave mean shares at the choice of glance 0.45, grid 0.34, progress 0.22, and lifts 0.49, 0.32, 0.10.

Readouts are defined in `analysis/e12/readouts.py` (written before the walks finish, not changed after). Steps before 50 are left out. With two seeds, nothing here can be a lead or result by e08's rule (four seeds). A **hint** is: both seeds of a condition lie outside the Null's two-seed range, on the same side.

The death dry run (brief D12), on logged surprise of the chosen tile before training, per source (glance; pooled grid; max grid):
- C1: surprise above its running mean + 3 running SDs (rate 0.002, cumulative until step 500), after step 150.
- C2: C1, but only after 50 steps in a row with drive d ≥ 0.
- C3: d ≤ −δ (r_max) for 20 steps in a row.

96. **Cost.** All 18 walks finish; 12–30 min each, three side by side. Two-eye walks take longer than v1.
97. **Interest decomposition** (`e12_two_top4`). Mean share at the choice: glance 0.35–0.50, grid 0.30–0.45, progress 0.15–0.30. Lift of the glance above the grid's in both seeds. In `g2`: glance share 0.50–0.70, glance lift more than twice the grid's.
98. **Stripes in the eye (within tile).** The top crop's stripe share exceeds the median of its tile's other crops in every grid and two-eye walk, the Null included: a striped crop is hard to place in memory. The ranking is the eye's, so the excess is within a factor of 2 across pooling.
99. **Stripes in the choice (against the Null).** Selection of the chosen tile's most striped crop (selz): top-1 > top-4 > mean pooling, and top-1 a hint against the Null. v1 within ±0.1. Medium confidence.
100. **The glance reads cloud and brightness.** Over offers, |ρ(glance novelty, cloud)| > |ρ(grid novelty, cloud)| in both seeds of `two_top4`. `g2` chooses cloudier tiles than the Null (a hint). Low confidence.
101. **Crop memory tires of stripes faster than v1.** Stripe selection falls from steps 50–500 to 500–1,000 in both seeds of grid top-4 and top-1, and by more than in v1. Low confidence.
102. **Fill and night.** Not testable on the pass (daylight only, fill ≤ 10 %). In the mission smoke walk, the top crop holds more fill than its tile's other crops (fill edges are novel). Low confidence.
103. **No edge pull.** The top crop is an edge crop in 0.70–0.80 of chosen tiles in every walk (chance 0.75).
104. **Patch shuffle.** Grid novelty does not change (|Δ| < 1e-5, by construction). Glance novelty of shuffled tiles is above that of the originals, median relative change above 10 %.
105. **The revisit problem does not return.** Revisit share and straight-backs in grid and two-eye walks at most 1.5 × v1's, in both seeds.
106. **The drive needs no recalibration.** Share of steps at r_max within a factor of 2 of v1's in every condition. Under the replayed schedules, far offers do not pay: far − near gap in offered interest (long yardstick) ≤ 0.1.
107. **Forgetting.** Grid error on the forgetting set at step 1,000 below step 0 for every kind and walk. Between 500 and 1,000 the sea's error rises in both top-1 walks, not in mean pooling. Low confidence.
108. **The shadow.** Over offers, Spearman(v1 shadow novelty, pooled grid novelty) ≥ 0.8 for mean pooling, 0.5–0.8 for top-1.
109. **Death dry run.** Firings of C1 summed over walks: max grid ≥ pooled grid ≥ glance. Max-grid firings land on a tile whose top crop has stripe or DN-255 share above the walk's median crop in at least 2/3. Glance firings land on cloud ≥ 0.3 or the brightest quarter in at least 2/3. C3 fires in fewer than half the walks.
110. **Mission smoke walk** (two eyes, top-4, 500 steps). 1.5–4 s a step with fetching, under 1 % of offers dropped, no crash.

**Stopped 2026-11-12, 11:23, after 6 of 18 walks** (`e12_v1`, `e12_null`, `e12_grid_mean`, `e12_grid_top4`, `e12_grid_top1`, `e12_two_top4`, seed 0 only). Moe: the wanderers walk the whole mission, not one pass. Predictions 96–110 are scored only as far as these six walks allow (no seed 1, no `g2`, no schedule controls). Seen before stopping: in `e12_two_top4_s0`, 59 % of chosen tiles have a black wedge where the cell sticks out over the pass's edge, against 21 % in the Null (log 2026-11-12).

## Experiment 12 on the whole mission (added 2026-11-12, before any `e12_l1_` factorial walk; log: `notes/12_two_eye/log.md`)

Walks: the same nine conditions on the Landsat 1 world (`world: landsat1`), born in South Dakota (cell `479U_839L`, the first scene of the archive, night), with the revisit rule (`stack: revisit_next`: a cell shows its acquisitions in date order, one more per visit; a cell whose stack has run out is not offered). Configs `configs/12_two_eye/e12_l1_*.yaml`, 1,000 steps, seeds 0–1. No full-tile rule (Moe: not for now).

Already seen, so not predicted: a 100-step two-eye smoke walk (`e12_l1_smoke_s0`): 61 of 100 steps were revisits, 39 distinct cells, all within ~30 km of the start; ranks up to 8; 39 steps on night tiles; 40 % of offers showed a later acquisition; 1.1 s a step alone, no fetch failed.

Readouts as for 96–110, computed per image (cell and acquisition), plus: revisit share (steps on an acquisition of rank > 0), dates seen per visited cell, selection of night and of rank among offers. A hint as before.

111. **Cost.** All 18 walks finish; 20–45 min each, three side by side; under 1 % of offers dropped; no failed fetch after retries.
112. **The time well.** Revisit share (rank > 0) in every curious walk above the Null's range: a hint for every condition. In the two-eye walks at least a third of all steps are revisits, and visited cells show a median of at least 2 dates. Medium confidence.
113. **The well is left.** The drive still sends walkers far: at least one bout at r_max in at least 3 of the 4 two-eye walks. Share at r_max below the Null's in the two-eye walks (a hint), since a new date keeps interest up near home. Low confidence.
114. **Night wears off.** Night tiles look alike (dark, with detector lines). From step 200 on, two-eye walks select against night offers (selz below the Null's range, a hint). Low confidence.
115. **Interest decomposition** (`e12_l1_two_top4`): glance share at the choice 0.30–0.55, grid 0.25–0.45, progress 0.15–0.30; in `g2` glance share above 0.5.
116. **Stripes.** Within the tile, the top crop's stripe share exceeds its tile's other crops in every grid and two-eye walk (as 98). Among offers, top-1 pooling selects striped tiles more than mean pooling, and top-1 is a hint against the Null (as 99).
117. **Black edges.** Where a tile has fill touching its border, the glance finds it: two-eye walks select fill (selz) above the Null's range (a hint), and the grid alone (w_glance 0) does not. Medium confidence (seen on the pass, one seed).
118. **The glance reads cloud and brightness** (as 100): |ρ(glance novelty, cloud)| > |ρ(grid novelty, cloud)| in both two-eye seeds.
119. **No edge pull** of the top crop: 0.70–0.80 (chance 0.75), as 103.
120. **Forgetting.** Grid error on the mission forgetting set at step 1,000 below step 0 for every kind and walk.
121. **Death dry run.** Max-grid surprise fires C1 at least as often as pooled grid and glance, summed over walks; its firings fall on striped, saturated or night tiles in at least 2/3.

Scored 2026-11-12 in `notes/12_two_eye/observations.md`.
- **Pass (96–110, six walks, seed 0):** 3 right (98, 101, 105), 2 mostly right (97, 103), 3 partly (100, 104, 107), 5 wrong (99, 102, 106, 108, 109), 2 superseded (96, 110).
- **Mission (111–121):** 6 right (111, 115, 116, 118, 119, 120), 1 mostly right (113), 2 partly (114, 121), 1 mostly wrong (112), 1 wrong (117).
- Not foreseen:
  - night tiles are red, not black (nir08 ~209 DN with the sun at −15°);
  - the early time well is the escape from the night start;
  - every curious walker prefers a cell's earlier acquisitions, and clear, dark tiles;
  - fill attracts at tile level while the top crop avoids it.
