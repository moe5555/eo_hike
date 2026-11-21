# Digest while Moe is away (2026-11-17 to 2026-11-25)

One dated line per notable event, newest last. The full history is in `runs/g1/events.log`, and the live view is `runs/g1/STATUS.md`.

- **2026-11-17 13:10:**
  - G2 training is at about 1,600 of 3,840 kimg per run.
  - G3, G4, the recursion readout and the upscaler are queued (Moe's decisions).
  - Predictions 169–173 are dated.
- **2026-11-18 20:54:** G2 training is done (3,840 kimg each, 55.3 h, no restarts).
- **2026-11-18 21:44–21:51:** G2 FID (curious 8.4, null 7.7, each against its own training set) and the G2 readouts ran cleanly at full size.
- **2026-11-18 21:57:** the G2 latent walks started (α_min 16.7° curious, 14.1° null).
- **2026-11-18 22:10:** `notes/gen2_gan_report.md` is written.
  - Predictions: 164, 165, 167 and 168 right; 166 wrong.
  - Coverage of the real G1 package rose for curious (recall 0.098 → 0.171) and held for null; no collapse.
  - Banding rose in both loops; the null's walk was rougher than its GAN's samples.
- **2026-11-19 00:59:** the G2 latent walks are done (10,000 tiles each).
  - The curious walker almost stopped getting bored (90° jumps on 4.7 % of steps, against 25 % in G1).
  - Its taste flipped: slightly less texture and banding than offered.
  - See `notes/gen2_latent_report.md`.
- **2026-11-19 01:05:** G3 packages built and tagged `g3-paths`; the G3 datasets are building.
- **2026-11-21 08:30:** G3 training is done (3,840 kimg each, 55.3 h, no restarts). FID and readouts ran 08:31–09:26.
- **2026-11-21 09:32:** the G3 latent walks started.
- **2026-11-21 10:40:** `notes/gen3_gan_report.md` is written.
  - Chromatic scan lines grow along both loops: G3-curious is at 3.8 × the real package, G3-null at 1.9 × (a post-hoc statistic; the old row roughness cannot see them).
  - The rise happens mostly in the walks. Both walkers, the Null included, linger on striped tiles through the radius rule.
  - Recall against the real package rose again in both, so prediction 169 is already against the data. No collapse.
