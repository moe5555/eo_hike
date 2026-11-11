# Changelog

Newest entry first. Each entry: date, what changed, why this approach, what you expect.

## 2026-11-11: the world decided; the season-seam readout

- **What changed.**
  - The world is Major TOM (Moe's decision).
  - New readouts: `analysis/e09/seams.py` (season, time, processing baseline and year of the chosen cell against its offers and against the cell stood on) and `analysis/e09/novelty_unseen.py` (novelty against ground distance from the cells stood on).
  - Predictions 91–95 written, then scored. Report in `notes/09_compass/observations.md` (findings 65–70).
  - STATE.md filled in for the first time.
- **Why this approach.** Choosing Major TOM because it is a stitched multi-temporal image means the stitching has to be measurable in the walks. The readout uses only the index's acquisition time and product name, so it runs offline on every existing log.
- **What I expect.** The seam readouts join the core for the replication in the final world. The processing seam (N04/05 tiles washed out) will show in the GAN's generations as two tones of the Earth.
