# Latent walks in generation 1: the curious walker in G1-curious against the Null walker in G1-null — report (2026-11-16)

*Brief: `notes/brief_g1_latent_walks.md`. Decisions: Moe, 2026-11-14 (fresh walkers with the committed configs, z-sphere, calibrated step, snapshot as time, colour-character observer). Predictions 158–163, `notes/06_characters/expectations.md`, dated before the run. Code: `agent/latent_walk.py`, `analysis/gen1/latent_readouts.py`, `analysis/gen1/latent_taste_ci.py`. Tables and figures: `notes/gen1/latent/`. Runs: `runs/g1/latent/<cond>/` (outside git). Both walks ran 2026-11-16 10:22–13:24 on the PC, side by side on one GPU.*

## Short version

- **Both walks reached N = 10,000 tiles in 9,999 steps** (about 3.0 h each), with no crash and no restart.
- **Calibration (colour character).** A real 15 km step changes a tile's colour character by ρ = 0.33 (curious) and 0.22 (Null) of a random jump. On the 3,840 kimg snapshots this gives α_min = 19.0° (curious) and 14.0° (Null).
  - The pixel observer, logged and not used, would have given 66.7° and 41.5°.
- **Time is almost used up at once.** Both walkers start in the 960 kimg snapshot and take every one of the three possible waits. They reach the last snapshot at step 130 (curious) and step 276 (Null), so 98.7 % and 97.2 % of their steps are in the 3,840 kimg world. When a later snapshot was offered, the curious walker took it 3 times in 11 and the Null 3 times in 28; chance is 1 in 9.
- **Movement.** Both walkers spend about 54 % of steps at α_min and 21–25 % at 90° (bored). The angle from the start saturates near 90° within about 100 steps, as tested.
- **Taste, in a GAN's world (colour and texture statistics, labelled as such):**
  - The curious walker chooses offers that are more textured than it is offered: gradient +0.89 and row roughness +0.042, both with bootstrap intervals over steps clear of zero. Its choices are also redder in the red band (+3.4) and almost half as often black in the green band (0.0045 against 0.0079).
  - The Null shows no gap on any statistic.
  - The curious walker does not choose against white (cloud-like) offers: −0.00006, and its interval spans zero.
- **Predictions:** 158 wrong; 159 half right; 160 right on the first part, undecided on the second; 161 wrong; 162 right; 163 right.
- **These tiles are now G2's training sets** (`paths/g2/<cond>/`; the render check passed with at most 2 of 255 difference).

## Tables

All from `notes/gen1/latent/`: `walks.csv`, `snapshots.csv`, `taste.csv`, `taste_ci.csv` and `waits_vs_moves.csv`. Figures: `time_movement.png`, `taste.png`, `contact_every500_<cond>.png` and `last50_<cond>.png`.

**The walks:**

| | curious in G1-curious | Null in G1-null |
|---|---|---|
| steps / unique tiles / end | 9,999 / 10,000 / N reached | 9,999 / 10,000 / N reached |
| ρ colour (real 15 km step ÷ random pair) | 0.33 | 0.22 |
| α_min (colour; used) | 19.0° | 14.0° |
| α_min the pixel observer would have given (ρ) | 66.7° (0.87) | 41.5° (0.57) |
| steps at α_min / at 90° | 53.5 % / 25.3 % | 53.6 % / 20.6 % |
| median angle between positions 1 / 10 / 100 / 1,000 steps apart | 19.0° / 60.6° / 89.9° / 89.8° | 14.0° / 51.1° / 89.7° / 90.0° |
| angle from the start, at the end | 88.6° | 90.7° |
| mean p of the chosen offer / best offer taken | 0.49 / 61 % | 0.125 / 12 % |
| interest shares at the choice: glance / grid / progress | 0.377 / 0.332 / 0.291 | 0.366 / 0.340 / 0.294 |
| the same in the real G1 walks | 0.384 / 0.355 / 0.262 | 0.356 / 0.354 / 0.289 |

**Time (snapshot as time, q = 0.10):**

| | curious | Null |
|---|---|---|
| steps in snapshot 960 / 1,920 / 2,880 / 3,840 | 28 / 99 / 4 / 9,868 | 28 / 217 / 32 / 9,722 |
| first step at 1,920 / 2,880 / 3,840 | 27 / 126 / 130 | 27 / 244 / 276 |
| waits / time offers that came through | 3 / 11 | 3 / 28 |
| waits when offered (chance 1 in 9) | 0.27 | 0.11 |
| progress z at waits / at moves (3 waits) | 1.63 / 0.49 | −0.06 / 0.00 |

**Taste: chosen minus offered, compass offers, per step** (`taste_ci.csv`; bootstrap 95 % interval over the 9,996 steps of each walk; colour and texture statistics of the 128 px renders):

| statistic | curious | interval | Null | interval |
|---|---|---|---|---|
| brightness | +1.84 | 1.59 to 2.08 | −0.34 | −0.86 to 0.21 |
| white share (all channels ≥ 230) | −0.00006 | −0.00043 to 0.00031 | −0.00010 | −0.00146 to 0.00134 |
| black share (fill-like) | −0.00051 | −0.00093 to −0.00007 | 0.00000 | −0.00004 to 0.00005 |
| green band dark (tile share) | −0.0033 (0.0045 against 0.0079) | −0.0042 to −0.0023 | +0.0001 | −0.0007 to 0.0008 |
| mean of the red band (G channel) | +3.35 | 3.06 to 3.67 | −0.37 | −0.96 to 0.16 |
| gradient (texture) | +0.89 | 0.79 to 1.00 | −0.02 | −0.09 to 0.05 |
| row roughness (banding) | +0.042 | 0.030 to 0.053 | −0.006 | −0.014 to 0.002 |

The intervals describe each walk: steps are resampled, so they show that a gap is stable within the walk, not that it would repeat in another walk or another GAN. All curious gaps are small, at most 0.13 of the offered spread.

## Findings

Each finding is one walk per condition in one GAN per condition, so each is a hint. The two GANs are different worlds, trained on different packages (with the era confound of `notes/gen1_gan_report.md`), so a comparison between the walkers is also a comparison between their worlds. The colour statistics of this report are defined in `agent/latent_walk.py` and are not the same as those of the GAN report: compare within this report only.

1. **Under snapshot as time, waiting is a short opening phase.**
   - With four kept snapshots there are only three possible waits, and both walkers took all three within the first 2–3 % of the walk.
   - The rest of each walk, and almost all of each G2 training set, is in the final world (3,840 kimg).
   - The curious walker took the time offer more often than chance (3 of 11), the Null at chance (3 of 28). With three waits each this says nothing yet.
   - Set by hand: four kept snapshots, q = 0.10, start at 960 kimg. Emerged: when each walker left each snapshot.
   - *RQ1/RQ3; ch. 5, 7.*
2. **The colour-calibrated step makes neighbours alike in colour, not in layout.**
   - At α_min a step changes colour character as much, relative to a random jump, as a real 15 km step did. The pixel observer would have asked for 41–67°, because adjacent real tiles barely overlap.
   - The curious GAN needs the larger angle (19° against 14°), because its real package changed more per step (ρ 0.33 against 0.22).
   - Set by hand: the observer (Moe), the 15 km reference, α_max = 90°. Emerged: ρ and α_min.
   - *RQ1/RQ3; ch. 4, 5.*
3. **The radius rule works in latent space as on the planet.**
   - About half of all steps are at α_min, and a fifth to a quarter are 90° boredom jumps, for both walkers.
   - The angle from the start says nothing after about 100 steps; the lags do. Positions 10 steps apart are 61° (curious) and 51° (Null) apart, which follows from the different α_min.
   - Set by hand: the radius rule, its log mapping onto [α_min, 90°], and the drive settings from the configs. Emerged: the shares.
   - *RQ1/RQ2; ch. 7.*
4. **In its GAN's world the curious walker chooses texture over flatness.**
   - Its choices are more textured (gradient), more banded (row roughness), redder in the red band and brighter than its offers. They are about half as often black in the green band, and slightly less often fill-black.
   - The Null shows no gap on any statistic.
   - Unlike the real walks, it shows no preference against white. The real hint "clear over cloud" does not carry over, at least not as this colour statistic sees it.
   - Set by hand: the eyes, the temperament, temperature 0.5, and the statistics (colour and texture, not quirk detectors). Emerged: the gaps.
   - *RQ2/RQ3; ch. 6, 8.*
5. **Interest at the choice keeps its real-world proportions.**
   - The curious shares (glance 0.38, grid 0.33, progress 0.29) are within 0.03 of the real G1 walks.
   - The Null's shares are almost the same, so the proportions belong to the eyes and their z-scoring more than to the choice.
   - *RQ2; ch. 7, 8.*
6. **Visual, not measured.**
   - In the every-500-steps contact sheets, 6 of 20 curious frames are dominated by multicoloured scan-line striping, and one shows fill-like black bars. The Null's sheet has 2 of 20 striped frames and more flat, cloud-white and grey frames.
   - This fits finding 4 and the GAN report's visual lead (finding 5 there), and it is a lead for the quirk observer, not a result.
   - *RQ3; ch. 8, 9 (film).*

## Against the predictions (158–163)

| # | predicted | measured | verdict |
|---|---|---|---|
| 158 | α_min 2–15° on both GANs; G1-curious the smaller angle | colour observer (used): 19.0° and 14.0°; pixel observer (the one 158 was stated for): 66.7° and 41.5° | **wrong** under both observers: outside the range for curious (and for both under pixels), and curious needs the larger angle |
| 159 | both reach 3,840 kimg before step 1,500; when offered, curious takes a later snapshot about as often as the Null (within ×1.5) | step 130 and 276; 0.27 against 0.11 (3 of 11, 3 of 28) | **half right**: reached early, yes; the take rate differs by ×2.5, on three waits each, so the miss is fragile |
| 160 | median α < 1.5 α_min for both; at the end curious is closer to its start than the Null | median α = α_min for both (54 % of steps at α_min); end 88.6° against 90.7° | **right** on the first part; the second has the predicted sign but sits inside the spread of random directions in 512 dimensions (about ±2.5°), so it is **undecided** |
| 161 | curious chooses lower white share than offered; Null \|gap\| < 0.01 | curious −0.00006 (interval spans zero); Null −0.0001 | **wrong**: no preference against white for curious; the Null part holds trivially |
| 162 | curious chooses higher row roughness than offered; Null no gap | +0.042 (0.030 to 0.053); Null −0.006 (spans zero) | **right**, low confidence as stated; a small gap (0.05 of the spread) |
| 163 | curious shares glance 0.34–0.42, grid 0.32–0.40, progress 0.20–0.32 | 0.377 / 0.332 / 0.291 | **right**; the Null's shares are about the same, so this tests the eyes more than the choice |

**Why the misses:**
- 158 was stated for the pixel observer, before Moe chose colour character. It got the scale wrong: adjacent real tiles are almost as different in pixel layout as random ones. It also got the order wrong: the curious package, not the curious GAN, sets ρ, and its 15 km steps changed more.
- 161 carried a real-world hint (clear over cloud, seen with the cloud detector) to a colour statistic in a GAN's world. G1-curious makes few white tiles (white share 0.004 offered), so there is little to avoid.

## For review

- **Snapshot as time gives about 1–3 % of each G2 package from earlier snapshots.** With four kept snapshots, waiting is a short opening phase. If time is to matter in later generations, it needs more snapshots or another rule. This is Moe's decision; nothing has changed for G2, which follows "the same rules as G1".
- **G2-curious inherits a texture preference** (finding 4): its training set is the curious walker's choices, more textured and banded than its offers. Prediction 166 (curious drifts towards the apparatus) is the test.
- **Should the step stay calibrated by colour** in G2's latent walks (the default: the G2 calibration again uses the real 15 km reference)? Raised already in `notes/brief_g2.md`.
- **The quirk observer on GAN tiles** would test findings 4 and 6 (prediction 154, deferred).
