# Narrator input — baseline_s0

Generated 2026-10-26 from `runs/baseline_s0/steps.parquet`. Land cover: dominant ESA WorldCover 2021 class over each tile's ~10.7 km footprint (tiles outside WorldCover's land coverage are open Ligurian Sea). Place: nearest GeoNames place with ≥1,000 inhabitants; "N km from X" when it is more than 6 km away.

## Temperament (config)

| key | value | meaning |
|---|---|---|
| policy | curious | scores candidates; picks one by softmax |
| w_n, w_g, w_e | 1.0, 1.0, 0.0 | weights of novelty, learning progress, surprise in the score I |
| temperature | 0.5 | softmax temperature over I |
| radius_km | 15 | neighbour candidates within this radius |
| p_long_jump | 0.02 | chance per step that one random tile joins the candidates |
| patience | 0.6 | boredom B = EMA(0.9) of [best candidate's I < 0]; above patience → teleport to a random tile |
| crop_px, K | 64, 16 | the agent looks at K random crops per tile |
| buffer_size | 2048 | memory: FIFO buffer of patches it replays while learning |
| steps | 1500 | walk length; start Milan (45.46, 9.19) |

Scores are z-scores against the agent's own running mean (0 = ordinary for this agent so far). I = w_n·novelty_z + w_g·progress_z + w_e·surprise_z. Surprise has weight 0: it is logged but does not steer.

## Base rates for the region

1,814 tiles, Northern Italy (lat 43.5–47.0, lon 6.5–12.6). Mean tile cloud cover 1.2 % (dataset capped at 25 %). 7 tiles near Novara are a synthetic noise source ("noisy TV").

Share of steps by dominant land cover (%):

| land cover | region (tiles) | random walk (2 seeds) | this agent |
|---|---|---|---|
| tree cover | 49.0 | 54.9 | 44.9 |
| cropland | 19.2 | 18.2 | 3.7 |
| grassland | 15.7 | 10.3 | 26.9 |
| permanent water | 9.4 | 12.6 | 16.6 |
| open sea | 2.7 | 1.0 | 3.4 |
| snow and ice | 2.0 | 1.6 | 3.5 |
| built-up | 1.0 | 0.8 | 0.4 |
| bare / sparse vegetation | 0.9 | 0.6 | 0.6 |

| path statistic | random walk | this agent |
|---|---|---|
| unique tiles in 1,500 steps | 555 | 434 |
| moves back to the tile of two steps earlier (%) | 16 | 29 |
| steps on its 35 most-visited tiles (%) | 19 | 38 |
| steps north of 45.8° N (%) | 34 | 51 |
| mean cloud cover on path (%) | 1.36 | 1.37 |
| steps on noise tiles (%) | 0.1 | 1.1 (16 steps) |
| boredom events | — | 5 (steps 31, 89, 99, 109, 623) |
| steps where even the best candidate had I < 0 (%) | — | 10 |

Memory: reconstruction error on 200 fixed probe tiles fell from 0.0652 (step 0) to 0.0045 (step 1500); lowest 0.0044 at step 1450.

Most-visited tiles:

| place | land cover | visits |
|---|---|---|
| sea, 16 km from Riva Ligure (Liguria) | permanent water | 33 |
| Cevio (Ticino) | tree cover | 32 |
| sea, 24 km from San Remo (Liguria) | permanent water | 31 |
| sea, 30 km from San Lorenzo al Mare (Liguria) | permanent water | 31 |
| 7 km from Lavertezzo (Ticino) | tree cover | 31 |

## Significant events

Columns: novelty z, surprise z, learning-progress z, score I of the chosen tile, best score among candidates, boredom B before the step, visit number of this tile, distance moved (km).

| step | place | land cover | cloud % | nov z | sur z | LP z | I | best I | B | visit | km | event |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | Caronno Pertusella (Lombardy) | built-up | 0.0 | +0.00 | +1.48 | +1.49 | +1.49 | +1.49 | 0.00 | 1 | 0 | first move, out of the Milan start tile |
| 1 | Locate Varesino (Lombardy) | tree cover | 1.5 | +0.78 | -0.81 | -0.74 | +0.05 | +0.72 | 0.00 | 1 | 13 | first step on tree cover |
| 3 | Rovellasca (Lombardy) | tree cover | 0.0 | +0.85 | +0.65 | +3.55 | +4.40 | +4.40 | 0.00 | 1 | 10 | learning-progress peak |
| 4 | Varedo (Lombardy) | built-up | 0.0 | +2.92 | +1.35 | +4.04 | +6.96 | +6.96 | 0.00 | 1 | 13 | learning-progress peak |
| 10 | Arborio (Piedmont) | cropland | 0.0 | -0.33 | -0.19 | +0.78 | +0.45 | +1.26 | 0.00 | 1 | 15 | first step on cropland |
| 11 | Oldenico (Piedmont) | cropland — synthetic noise tile (fresh random pixels on every look) | 0.0 | -0.42 | +1.75 | -0.08 | -0.50 | -0.50 | 0.00 | 1 | 10 | enters noise cluster (13 noise-tile steps between step 11 and 31) |
| 31 | Casaleggio Novara (Piedmont) | cropland — synthetic noise tile (fresh random pixels on every look) | 0.0 | -0.61 | +1.33 | -0.54 | -1.14 | -0.86 | 0.57 | 2 | 15 | boredom exceeds patience |
| 32 | Vallecrosia (Liguria) | permanent water | 0.0 | -0.68 | -0.84 | -0.51 | -1.18 | -1.18 | 0.00 | 1 | 202 | first step on permanent water; boredom teleport (random tile) |
| 41 | sea, 24 km from San Remo (Liguria) | permanent water | 0.0 | +4.77 | -0.89 | -0.44 | +4.33 | +4.33 | 0.00 | 4 | 10 | novelty peak |
| 42 | sea, 16 km from Riva Ligure (Liguria) | permanent water | 0.0 | +4.78 | -0.89 | -0.46 | +4.32 | +4.32 | 0.00 | 3 | 10 | novelty peak |
| 46 | 6 km from Gallio (Veneto) | tree cover | 18.4 | +2.77 | +1.75 | +0.43 | +3.19 | +3.19 | 0.00 | 1 | 390 | long jump taken (random candidate) |
| 48 | 6 km from Gallio (Veneto) | tree cover | 18.4 | +0.64 | +3.05 | +3.70 | +4.35 | +4.35 | 0.10 | 2 | 13 | learning-progress peak |
| 72 | 10 km from Canazei (Trentino-Alto Adige) | grassland | 0.0 | +1.37 | +1.03 | -0.53 | +0.84 | +0.84 | 0.31 | 1 | 10 | first step on grassland |
| 89 | Vidor (Veneto) | grassland | 0.0 | -0.75 | -0.77 | -0.40 | -1.16 | -1.03 | 0.56 | 1 | 13 | boredom exceeds patience |
| 90 | Verderio Superiore (Lombardy) | tree cover | 0.0 | -0.85 | -0.80 | -0.37 | -1.22 | -1.22 | 0.00 | 1 | 203 | boredom teleport (random tile) |
| 98 | Lungavilla (Lombardy) | cropland | 0.0 | -0.98 | -0.72 | -0.24 | -1.21 | -0.61 | 0.52 | 1 | 100 | long jump taken (random candidate) |
| 99 | Sommo (Lombardy) | cropland | 0.0 | -0.86 | -0.57 | -0.22 | -1.07 | -1.07 | 0.57 | 1 | 10 | boredom exceeds patience |
| 100 | Osiglia (Liguria) | tree cover | 0.0 | -0.19 | -0.51 | -0.12 | -0.31 | -0.31 | 0.00 | 1 | 122 | boredom teleport (random tile) |
| 109 | Ormea (Piedmont) | tree cover | 0.0 | -0.30 | +0.12 | -0.17 | -0.47 | -0.47 | 0.57 | 1 | 15 | boredom exceeds patience |
| 110 | sea, 12 km from Ospedaletti (Liguria) | permanent water | 23.6 | -0.39 | -0.46 | +0.23 | -0.16 | -0.16 | 0.00 | 2 | 52 | boredom teleport (random tile) |
| 124 | sea, 49 km from Cervo (Liguria) | open sea | 0.0 | +1.01 | -0.57 | -0.26 | +0.75 | +0.75 | 0.35 | 1 | 13 | first step on open sea |
| 203 | sea, 30 km from San Lorenzo al Mare (Liguria) | permanent water | 0.0 | +0.24 | -0.29 | +0.41 | +0.65 | +0.65 | 0.23 | 21 | 13 | start of longest unbroken permanent water stretch (101 steps, to step 303) |
| 299 | sea, 16 km from Riva Ligure (Liguria) | permanent water | 0.0 | -0.23 | -0.26 | +0.77 | +0.54 | +0.71 | 0.05 | 33 | 14 | last of 33 visits to this tile (most-visited rank 1) |
| 300 | sea, 24 km from San Remo (Liguria) | permanent water | 0.0 | -1.15 | -0.26 | +0.77 | -0.38 | -0.38 | 0.05 | 31 | 10 | last of 31 visits to this tile (most-visited rank 3) |
| 314 | 6 km from Limone Piemonte (Piedmont) | grassland | 0.8 | +2.94 | +3.84 | +3.28 | +6.22 | +6.22 | 0.04 | 4 | 10 | learning-progress peak |
| 323 | 10 km from Saint-Martin-Vesubie (Provence-Alpes-Cote d'Azur) | grassland | 0.0 | +1.78 | +4.73 | +0.11 | +1.90 | +1.90 | 0.01 | 2 | 15 | surprise peak |
| 341 | Bersezio (Piedmont) | grassland | 0.0 | +5.49 | +0.06 | -0.29 | +5.20 | +5.20 | 0.00 | 1 | 15 | novelty peak |
| 352 | 12 km from Pleyne (Piedmont) | bare / sparse vegetation | 1.5 | +1.63 | +0.49 | +0.70 | +2.33 | +2.33 | 0.00 | 1 | 10 | first step on bare / sparse vegetation |
| 424 | Silvano Pietra (Lombardy) | cropland | 0.0 | -0.50 | -0.42 | +0.44 | -0.06 | -0.06 | 0.14 | 1 | 191 | long jump taken (random candidate) |
| 459 | Prali (Piedmont) | grassland | 0.1 | +1.33 | +0.67 | +0.32 | +1.65 | +1.65 | 0.48 | 6 | 258 | long jump taken (random candidate) |
| 623 | Casalborgone (Piedmont) | tree cover | 0.0 | -1.23 | -0.75 | +0.39 | -0.84 | -0.29 | 0.56 | 1 | 10 | boredom exceeds patience |
| 624 | 8 km from Silvaplana (Grisons) | snow and ice | 0.0 | +1.13 | +0.69 | -2.62 | -1.50 | -1.50 | 0.00 | 1 | 202 | first step on snow and ice; boredom teleport (random tile) |
| 733 | Mezzoldo (Lombardy) | tree cover | 21.0 | +0.35 | +1.00 | +1.09 | +1.44 | +1.57 | 0.14 | 1 | 10 | start of longest unbroken tree cover stretch (74 steps, to step 806) |
| 1035 | Casaleggio Novara (Piedmont) | cropland — synthetic noise tile (fresh random pixels on every look) | 0.0 | -0.76 | +5.37 | +0.82 | +0.06 | +0.06 | 0.47 | 3 | 10 | enters noise cluster (3 noise-tile steps between step 1035 and 1039); surprise peak |
| 1038 | Oldenico (Piedmont) | cropland — synthetic noise tile (fresh random pixels on every look) | 0.0 | -0.39 | +4.84 | +0.33 | -0.06 | -0.06 | 0.34 | 2 | 10 | surprise peak |
| 1250 | Cevio (Ticino) | tree cover | 0.0 | +0.90 | +0.19 | +0.40 | +1.29 | +1.29 | 0.00 | 32 | 15 | last of 32 visits to this tile (most-visited rank 2) |
| 1411 | sea, 38 km from Marina di Pisa (Tuscany) | permanent water | 0.0 | -0.61 | -1.28 | +0.78 | +0.17 | +0.97 | 0.00 | 1 | 360 | long jump taken (random candidate); start of longest unbroken permanent water stretch (46 steps, to step 1456) |
| 1478 | sea, 59 km from Portofino (Liguria) | open sea | 0.0 | +4.77 | -0.49 | +1.55 | +6.33 | +6.33 | 0.15 | 2 | 13 | novelty peak |
| 1499 | sea, 52 km from Deiva Marina (Liguria) | open sea | 0.0 | +1.25 | -0.39 | +0.79 | +2.04 | +2.04 | 0.02 | 3 | 13 | last step |
