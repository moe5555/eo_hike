# Hikes 29.10: observations, part 1 (1,000 steps from Milan)

Ten walks: four characters and the reference, two seeds each, 1,000 steps, Mac CPU. Numbers come from `analysis/h2910_compare.py` (`summary.csv`). Figures: `maps_world.png`, `maps_milan.png`, `curves.png`. One page per run: `runs/<run>/hike.html`.

**A place** below means a stretch of the walk between two jumps longer than 30 km, i.e. between long jumps and boredom teleports.

## The table (mean of the two seeds; the per-seed values are in `summary.csv`)

| | Reference | Bored | Globalist | Localist | Fast learner (s0 only) |
|---|---|---|---|---|---|
| unique tiles | 478 (430 / 525) | 478 (526 / 430) | 513 (543 / 482) | 401 (426 / 376) | 491 |
| revisit share | 0.52 | 0.52 | 0.49 | **0.60** | 0.51 |
| straight-back steps (A→B→A) | 0.26 | 0.25 | 0.25 | **0.31** | 0.23 |
| boredom teleports | 3.5 | **12** (16 / 8) | 6.5 | 1 | 9 |
| long jumps offered / taken | 20 / 5 | 20 / 4.5 | **212 / 35** | 0 / 0 | 25 / 6 |
| long-jump acceptance | 0.26 | 0.24 | 0.17 | – | 0.24 |
| places | 9.5 | 17.5 | **42.5** | **2** | 16 |
| median steps per place | 45 | 26 | **15** | **500** | 28 |
| steps before the first jump | 41 | 23 | 8 | **72** | 25 |
| ocean share of unique tiles | 0.40 | 0.28 | 0.29 | 0.15 | 0.39 |
| colour diversity of unique tiles | 87 | 73 | 91 | 80 | 86 |
| held-out MSE, last 200 steps | 0.0043 | 0.0039 | 0.0035 | 0.0043 | 0.0037 |

## What happened

1. **The characters differ in rhythm, not in how much they see.** The number of places and the time spent in each separate every character from the reference by more than the gap between seeds: Localist 2 places of about 500 steps, reference about 10 of 45, Bored about 18 of 26, Globalist about 43 of 15. The total number of unique tiles does not separate them. Reference seeds alone span 430–525, and every character mean except Localist's lies inside that range. Inside a place, every walker revisits about half the time, whatever its character, and that habit sets the tile count. Teleports and long jumps redistribute the steps over more places without raising the count.

2. **Bored.** Teleports rose from 3.5 to 12 (16 and 8). The walks broke into twice as many, shorter places. Unique tiles, spread and colour diversity did not rise. Seed 0 spent 47 % of its tiles at sea, seed 1 only 10 %: where a teleport lands decides a lot.

3. **Globalist.** It was offered a far tile 212 times per walk and took it 35 times. The acceptance rate (0.15–0.18) is about chance with ~8 other candidates (~0.16), so the walker is not drawn to far tiles: it takes them because they are offered more often. Teleports went up, not down (9 and 4 against 3 and 4). Seed 0 jumped on its very first step. The result is a walker of short visits: 43 places, half of them under 15 steps.

4. **Localist.** It took no long jumps (by construction) and got bored exactly once in each seed, at steps 87 and 57. That single teleport took it far from Milan, and it stayed there for the rest of the walk: 913 steps around the Black Sea coast of Georgia (41.8 N, 42.3 E) for seed 0, 943 steps on the Labrador coast (54.1 N, 60.5 W) for seed 1. It is the clearest character: the highest revisit and straight-back rates, the fewest tiles, a radius of gyration of ~1,000 km against 6,000+ for all others. Its "home" is wherever its one boredom sent it, not Milan.

5. **Fast learner: seed 1's network died at step 142.** Steps 137–141 were tiles the network drew badly (error 0.10–0.28). At step 142, four training steps at `lr` 3e-3 took the error on the chosen tile from 0.015 to 0.895. From then on the decoder outputs 0 (black) for every input: the sigmoid output is saturated, its gradient is zero, and training cannot bring it back. Held-out MSE is frozen at 0.2517, progress is exactly 0, and the walker teleports every ~10 steps (40 teleports). Steps 142–999 are a blind walk and are left out of the character comparison. Seed 0 survived, with a spike in held-out MSE at step 125 (0.052, five times its neighbours). Within one seed, the fast learner looks like a slightly more restless reference: 491 tiles and 16 places. **`lr` 3e-3 is at the edge of what this autoencoder survives**, so a faster learner needs another lever (`update_steps`, or `lr` around 2e-3 with gradient clipping).

6. **Held-out MSE does not separate the characters.** All surviving runs end between 0.0031 and 0.0047. At 1,000 steps the way a walker travels does not change how well its network draws 200 random tiles from the planet. The Globalist's seed 1 has the lowest value (0.0031), seed 0 is mid-field.

7. **Every walker leaves Milan early.** The reference's first jump comes at steps 46 and 35, the Localist's at 87 and 57, the Globalist's at 1 and 15. Milan shapes the first 1–9 % of a walk.

## Against the expectation (`expectations.md`)

| # | Prediction | Outcome |
|---|---|---|
| 1 | Bored: 15–40 teleports | partly: 16 and 8 |
| 1 | Bored: 500+ unique tiles, largest spread but for Globalist | no: 478, same as the reference; smaller radius of gyration than the reference |
| 2 | Globalist: ~200 offers | yes: 223 and 201 |
| 2 | Globalist: acceptance 25–35 %, 50–70 long jumps | no: 15–18 % (about chance), 33 and 37 |
| 2 | Globalist: most unique tiles, most variety, lowest held-out MSE | weakly: the highest mean (513, tied with the fast learner), but inside the reference's seed range; colour diversity 91 vs 87; held-out lowest in seed 1 only |
| 2 | Globalist: fewer teleports than the reference | no: 6.5 vs 3.5 |
| 3 | Localist: no long jumps, 0–1 teleports | yes: 0, and 1 in each seed |
| 3 | Localist: one continuous walk from Milan | no: the one teleport moved it to Georgia and Labrador for 90 % of the walk |
| 3 | Localist: fewest tiles (under 350), highest revisits, smallest spread | mostly: fewest (426 / 376) but not under 350; highest revisits and back-steps; smallest radius of gyration |
| 3 | Localist: highest held-out MSE | no: within the spread |
| 4 | Fast learner: more unique tiles; returns more; held-out falls faster early, noisier later | not testable as planned: seed 1 collapsed. Seed 0: 491 tiles (within the reference's range), held-out MSE early on *higher* than the reference's (0.014 vs 0.009 at step 25), one spike at step 125 |
| 5 | Globalist and Localist separate from the reference by more than the seed gap; Bored probably; Fast learner may not | yes for places and time per place (all three); no for unique tiles and diversity, except Localist |

## For the next round

- Compare characters on places and time per place. Unique tiles only follow the revisit habit.
- Teleport landing spots are blind random draws, and the ocean share swings 10–58 % between seeds. Two seeds are too few for anything that depends on where a teleport lands.
- The Fast learner needs a learning rate that this network survives, or gradient clipping, before it can be run as a character.

# Part 2: 5,000 steps from Paris

Bored and Globalist, seed 0, 5,000 steps each, starting from cell 543U_17R (about 4 km south-east of the Île de la Cité). `python analysis/h2910_compare.py --paris` → `paris_summary.csv`, `paris_blocks.csv` (per 1,000 steps), `paris_maps.png`, `paris_curves.png`. Pages: `runs/h2910_{bored,globalist}_paris_s0/hike.html` (37 and 45 MB). Walk times: 1 h 45 min and 2 h 15 min.

| | Bored | Globalist |
|---|---|---|
| unique tiles | 2,066 | 2,591 |
| revisit share | 0.59 | 0.48 |
| boredom teleports | 35 | 12 |
| long jumps offered / taken (acceptance) | 96 / 15 (0.16) | 1,056 / 170 (0.16) |
| places | 51 | 184 |
| median / longest steps per place | 25 / 1,029 | 16.5 / 212 |
| ocean share of unique tiles | 0.17 | 0.23 |
| colour diversity of unique tiles | 88 | 102 |
| held-out MSE, last 200 steps | 0.0021 | 0.0021 |

Per 1,000 steps:

| steps | Bored: new tiles / teleports | Globalist: new tiles / long jumps / teleports |
|---|---|---|
| 0–999 | 448 / 10 | 550 / 29 / 6 |
| 1,000–1,999 | 407 / 11 | 565 / 47 / 0 |
| 2,000–2,999 | 425 / 4 | 484 / 29 / 1 |
| 3,000–3,999 | 430 / 6 | 536 / 38 / 4 |
| 4,000–4,999 | 356 / 4 | 456 / 27 / 1 |

## What happened

1. **Paris lasted 20 steps for Bored and 1 for the Globalist.** Bored walked north-west down the Seine towards the Vexin (up to 49.45 N, 1.72 E) and teleported at step 19. The Globalist took a long jump on its first step. That is the seed, not Paris: the Milan Globalist with seed 0 also jumped on step 1, because both walks draw the same first random numbers and the first draw falls under 0.2.

2. **The Bored walker searches, then settles.** Its 35 teleports come in bursts: 6 between steps 19 and 65, 10 between 1,444 and 1,627, 6 between 3,606 and 3,695. Between bursts it stays a long time in one place. The four longest stays are all on land, in mountains or high plateaus:
   - steps 3,696–4,724 (1,029 steps): Patagonia, around 48 S, 73 W (the southern Andes and ice fields)
   - steps 2,931–3,576 (646 steps): northern China, around 41 N, 112 E
   - steps 2,074–2,535 (462 steps): the eastern edge of the Tibetan plateau, around 30.5 N, 102 E
   - steps 66–458 (393 steps): south-east China, around 26 N, 115 E

   Teleports per 1,000 steps fall from 10–11 to 4–6 in the second half. A teleport lands on a blind random tile, often sea or flat land, which bores the walker again within a few steps, until a landing spot is varied enough to hold it for hundreds of steps. Its ocean share (17 %) is lower than in the Milan seed-0 walk (47 %). It got bored *away* from the sea, rather than stuck at it.

3. **The Globalist is steady.** About 500 new tiles and 30–47 long jumps in every block of 1,000 steps, and places of a median 16.5 steps, never longer than 212. Acceptance of a far tile is 0.16 over 1,056 offers, the same as chance with ~8 other candidates, and the same as in the Milan walks. Boredom has nearly vanished after the start (6 teleports in the first 81 steps, 6 in the remaining 4,900): a far tile on offer one step in five keeps the walker from staying anywhere long enough to get bored.

4. **Both walkers got bored in a cluster during their first ~80 steps** (Bored 6, Globalist 6). One possible cause, not yet checked: during the first 50 steps the running z-scores use a plain cumulative average while the network is learning fast, so the signals keep falling below that average and even the best candidate scores below 0.

5. **The longer walk halves the held-out error, for both characters alike**: 0.0021 at the end against about 0.004 after 1,000 steps. As in part 1, the two characters do not differ on it.

## Against the expectation (part 2, `expectations.md` §6–8)

| # | Prediction | Outcome |
|---|---|---|
| 6 | Bored: 60–90 teleports | no: 35. The rate falls over the walk (10–11 per 1,000 early, 4–6 late) |
| 6 | Bored: 2,000–2,500 unique tiles | yes: 2,066 |
| 6 | Bored: ocean share 35–50 % | no: 17 %. The long stays are in mountains |
| 7 | Globalist: ~1,000 offers, 150–180 taken, acceptance ~15 % | yes: 1,056, 170, 16 % |
| 7 | Globalist: more unique tiles (2,300–2,800) and higher colour diversity than Bored | yes: 2,591 vs 2,066; 102 vs 88 |
| 8 | Both leave Paris within 50–100 steps | yes, sooner: steps 20 and 1 (the 1 is the seed) |
| 8 | After that, like the Milan walks scaled up | Globalist yes (184 places ≈ 4.3 × 43, same acceptance, same median stay). Bored no: it settles into ever longer stays, so it is not a scaled-up 1,000-step walk |
