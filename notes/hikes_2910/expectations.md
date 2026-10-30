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
