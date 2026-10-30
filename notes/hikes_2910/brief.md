# Hikes 29.10: four characters

## Request (as written)

run a few hikes with different settings:

"Bored": adjust settings to that the agent gets bored quicker.

"Globalist": adjust the setting so that the random global tiles are recommended more often, perhaps from 0.2 up to 0.4

"Localist": higher boredom threshold, less suggested random tiles

"Curious": learning rate threshold is lower, i.e. the agent feels like it has learned what there is to learn quicker.

## Adjusted after review (2026-10-29)

- `p_long_jump` is 0.02 in every existing config, not 0.2. Globalist uses 0.2, i.e. 10x the offers.
- There is no learning-rate threshold. The setting closest to "learns what there is to learn quicker" is the learning rate `lr`, and it has to go *up*: tiles become familiar in fewer visits, their progress signal falls sooner, and the walker moves on. "Curious" is renamed **Fast learner**, because every agent here runs `policy: curious`.
- Boredom: B is an EMA (0.9 / 0.1) of "the best candidate's interest is below 0". From B = 0, crossing `patience` p takes ceil(log(1 − p) / log 0.9) dull steps in a row: 4 at 0.3, 9 at 0.6 (default), 16 at 0.8.

## Runs

Base: `configs/global_perception.yaml` (the global walker with the three perception fixes of `notes/hikes_v3_revised/`) at 1,000 steps. Start Milan, seeds 0 and 1, Mac CPU. Each character changes only what is listed.

| Character | Config | Change from the base |
|---|---|---|
| Reference | `global_perception.yaml --steps 1000` | none (seed 0 exists: `runs/global_perception_1k_s0`) |
| Bored | `configs/h2910_bored.yaml` | `patience` 0.6 → 0.3 |
| Globalist | `configs/h2910_globalist.yaml` | `p_long_jump` 0.02 → 0.2 |
| Localist | `configs/h2910_localist.yaml` | `patience` 0.6 → 0.8, `p_long_jump` 0.02 → 0 |
| Fast learner | `configs/h2910_fastlearner.yaml` | `lr` 1e-3 → 3e-3 |

Script: `scripts/hikes_2910.sh` (9 walks, about 4 h).

## Analysis

Per run and character: unique tiles, revisit share, A→B→A back-steps, boredom teleports, long jumps offered and taken, distance walked, radius of gyration, land-cover mix (`cover`), held-out MSE over time. Path maps. Seed-to-seed spread within a character is the yardstick for differences between characters.

## Part 2: 5,000 steps from Paris (requested 2026-10-29)

Once the 1,000-step batch has finished: Bored and Globalist, 5,000 steps each, starting from Paris, where the dérive and the Situationists come from. Configs `configs/h2910_{bored,globalist}_paris.yaml` (part 1's configs with the start moved to Paris, 48.8566 N 2.3522 E, and `steps: 5000`). Seed 0. Script `scripts/hikes_2910_paris.sh`. Start tile 472466, cell 543U_17R, about 4 km south-east of the Île de la Cité, 8 neighbours.
