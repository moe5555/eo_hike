# Expectations (written before the first walk, 2026-10-24)

What I expect to see, so the results can surprise us honestly.

## Data choices and deviations from the brief

- **Region:** Northern Italy, lat 43.5–47.0, lon 6.5–12.6, 1,814 tiles after filtering. It contains the western and central Alps, the Po valley (farmland), Milan and Turin, the big lakes, the Ligurian and Adriatic coasts with the Venice lagoon, and Apennine forest. The walk starts at the tile nearest Milan centre.
- **Clouds — deviation.** Major TOM Core keeps one product per cell and was built with a 25 % cloud cap. No tile anywhere is above 25 %, and only about 90 tiles in this region are above 10 %. The brief's "keep up to 60–70 %" filter therefore keeps everything. The real clouds are mostly thin or partial, so they may not be a real noisy TV.
- **Synthetic noisy TV — addition (agreed with Moritz).** The 10 or so tiles within 16 km of (45.40 N, 8.55 E), in the Po plain near Novara about 50 km west of the start, are replaced by a "TV". Each time an agent looks at one of these tiles it sees a *fresh* field of uniform RGB noise in 4×4 px blocks (~160 m grain). Nothing about it can be learned beyond its average colour. The tiles are flagged `tv` in `tiles.parquet`, counted separately in every statistic, and dropped from the DDPM training sets.
- **RGB:** the archive's `thumbnail` column is a fixed-scale composite of B04/B03/B02. Every tile shares the same scale, so it meets the "one global stretch" requirement without our own percentile stretch.
- **Held-out curve:** 200 fixed tiles with fixed crop positions (seed 12345). The walker may visit them; they are a fixed probe, not a test split.

## Gate 1 predictions

1. **novelty_only vs noisy TV:** novelty_only reaches the TV and stays. The fresh noise never gets close to the archive in latent space, so its novelty z-score stays high. Prediction: > 20 % of its steps on TV tiles once it finds them.
2. **baseline vs noisy TV:** the progress probe gives the TV about zero, or even negative, learning progress, because training on half A doesn't help half B. Novelty still pulls, so baseline visits the TV but leaves. Prediction: much lower TV share than novelty_only, but not zero.
3. **Real clouds:** a weak effect at most, because the clouds are thin and rare.
4. **vs random:** curious agents should cover more ground than a random walk, which diffuses slowly and has a high revisit rate. They should also have lower revisit rates and a different terrain mix: more coasts, mountains and the city, less uniform farmland.
5. **Scale:** myopic (32 px) sees texture, field patterns and roofs. Wide (128 px) sees landscape structure, and at 128 px the 4×4 TV noise is averaged 4×4 → nearly flat grey. **The wide agent may find the TV boring even without progress.**
6. **Boredom:** z-scores are centred on a running mean, so "max interest below zero" is rare among 8 candidates. I expect few bored events for baseline and more for restless.
7. **Seeds:** with 9 candidates and a 0.5 softmax temperature the walk is fairly stochastic, so I expect seeds to diverge within tens of steps.

## Gate 2 predictions

- A path set differs from a random set in *which* terrain it contains, so `path_uniform` vs `random_uniform` should show colour or brightness differences if the agent has a terrain preference.
- With `w` clipped to [0.2, 5], the weighting changes effective sample frequency by at most 25×. I expect `path_weighted` vs `path_uniform` to differ less than the path vs random comparison does.
- 15k steps on ~1,000 tiles × many crops: probably no pixel-level memorisation at 64 px, but samples will be blurry or texture-like rather than coherent.
