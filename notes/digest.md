# Digest while Moe is away (2026-11-17 to 2026-11-25)

One dated line per notable event, newest last. The full history is in `runs/g1/events.log`, and the live view is `runs/g1/STATUS.md`.

- **2026-11-17 13:10:**
  - G2 training is at about 1,600 of 3,840 kimg per run.
  - G3, G4, the recursion readout and the upscaler are queued (Moe's decisions).
  - Predictions 169–173 are dated.
- **2026-11-18 20:54:** G2 training is done (3,840 kimg each, 55.3 h, no restarts).
- **2026-11-18 21:44–21:51:** G2 FID (curious 8.4, null 7.7, each against its own training set) and the G2 readouts ran cleanly at full size.
- **2026-11-18 21:57:** the G2 latent walks started (α_min 16.7° curious, 14.1° null).
- **2026-11-18 23:00:** `notes/gen2_gan_report.md` is written.
  - Predictions: 164, 165, 167 and 168 right; 166 wrong.
  - Coverage of the real G1 package rose for curious (recall 0.098 → 0.171) and held for null; no collapse.
  - Banding rose in both loops; the null's walk was rougher than its GAN's samples.
