# The thinned time offer and lingering in the last period (Moe, 2026-11-13)

A change to the wanderer's horizon and to its ending, decided by Moe after the dry runs (`notes/dryrun_report.md`). Code: `time_offer_p` and `linger_from` in `agent/walk.py`, the end reason `linger` in `agent/clock.py`, tests in `tests/test_clock.py`. Both are off by default; with them off, a walk is bit for bit the brief's walk (checked on 60 steps of dry run curious w2).

## The rule

**The thinned time offer.**
- A step offers the eight compass offers as before.
- If the current cell has a later pass, the time offer comes through with probability *q* (`time_offer_p`). It is drawn each step from its own random stream (`time`), appended after every earlier stream, so no other draw moves.
- When the time offer comes through, nothing about it changes: it is scored by the same eyes and interest as the compass offers and drawn at the same temperature, with no bonus and no penalty.
- The Null is thinned in the same way, then draws uniformly over what is offered.

**Why** (Moe): a jump in time cannot be undone. Once the wanderer waits for the next pass, the earlier dates of the world are behind it. Offering the jump a little less often gives the wanderer reason to explore one period more, rather than exploit one tile through time.

**Lingering in the last period.**
- When the clock first reaches 1977-01-01 (`linger_from`), the walk may stay for as many steps as it spent, on average, per year of clock before: L = steps so far / years from its start clock to 1977-01-01. This is the walk's own pace, not a set number.
- The walk ends at whichever comes first:
  - those L steps are used up (`linger`);
  - the clock reaches T_end, 1977-12-20 (`time`);
  - the 40,000-step guard (`capped`).

## Set by hand, and what is left to emerge

| Set by hand (premises) | Left to emerge |
|---|---|
| *q*, calibrated once so that a curious walk reaches 1977 at about 10,000 distinct tiles (below) | when, where and how often the walker actually waits; which periods it lingers in; how far its tiles sit from its clock |
| the threshold 1977-01-01 and "linger as long as your average year" | how long the walk stays in 1977, and what it sees there |
| the same thinning for the Null | the difference between curious and Null |

What changes in the readouts, and what does not:
- The share of steps with a time offer drops by a factor of about *q* by construction. So does the share of waits.
- Readouts now log `time_exists` (a later pass exists) next to `time_offered` (it came through). P(wait | offered) and everything about the choice keep their meaning.
- Walk length becomes a setting. The CHARTER calls walk length "a result, not a setting"; Moe chose this knowingly. Every finding about time has to name *q*.

## Calibration

**Interim (2026-11-13 11:43, long phase paused with w011 and w012 checkpointed mid-walk).** Distinct tiles at which each finished q = 1 curious walk first had its clock in 1977:

| walk | dry run w000 | w001 | w002 | long w003 | w004 | w005 | w006 | w007 | w008 | w009 | w010 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tiles to 1977 | 549 | 485 | 990 | 2,395 | 846 | 1,038 | 1,017 | 1,533 | 906 | 818 | 528 |

Median 906 over 11 walks, a spread of about 5×. The assumption: the clock's progress per step scales with *q*, so q ≈ 906 / 10,000 ≈ **0.09**. It moved from 0.092 to 0.091 as walks were added. To be finalised when the long phase ends.

**Final, for generation 1 (2026-11-13, Gate B): q = 0.10.** Moe's target changed from "1977 at about 10,000 tiles" to "the walk *ends* at roughly 8,000–15,000 unique tiles", so lingering counts too. Lingering adds about 1 / 4.45 of the steps before it (the start clocks are in July–August 1972, 4.45 years before 1977-01-01), so a walk ends at about 1.22 × its tiles to 1977. The median end is then 1.22 × 906 / q. Aiming at the geometric middle of the range, √(8,000 × 15,000) ≈ 11,000, gives q ≈ 0.10. The long phase isn't needed for this and stays paused.

What follows from the spread, at q = 0.10 and under the scaling assumption: the 11 walks would end at about 5,900–29,000 tiles. Start cell 0 (dry run w000: 549 tiles to 1977 at q = 1) would end near 6,700, below N = 10,000, so a second wanderer from start cell 1 (w001: 485 at q = 1, about 5,900) is likely needed. Prediction 143 checks this.

## The first walk

*To be filled: its start cell, q = 0.10, and its outcome against predictions 143–157 (`notes/06_characters/expectations.md`).*
