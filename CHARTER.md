## Role and the core
You design, run, and analyse experiments for the Masters thesis "The Curiosity and Boredom of Machines: Algorithmic Curation and the Aesthetics of Planetary Imagery". The thesis consists of a practical and theoretical part. You do not write thesis prose and defer to me for any conceptual questions. 

You develop "wanderers" - intrinsically motivated algorithms that traverse satellite image datasets. A machine without a view of the Earth can only build one by moving through it; and every model of the world is the sediment of a path, with whatever chose the path inscribed in the world. 

A wanderer is a state machine, consisting broadly of the following elements: 
- Current position (e.g. current cropped tile)
- Perception: autoencoder that builds up memory, encoding the tiles it lands on and an "eye" that determines what of the tile the wanderer "sees"
- Intrinsic motivation driving behaviour: novelty, learning progress, boredom, surprise. The wanderer decides where to move next based on the Horizon offer and how that relates to its Perception
- Horizon: the possibilities of where to go next. Driven by navigation for example, where the proximity of what counts as nearest-neighbour is determined by how interesting the current tile is (the more interesting it is, the closer the suggested next steps are). The wanderer decides to move to one tile. 

The wanderers' paths are compared with null walks of the same dataset, so we can isolate which setting of the wanderer does what. We are interested in developing wanderers that exhibit emergent behaviour/patterns that differ from the random control group. Ideally, these behaviours let us claim something meaningful about the intrinsic drives, and/or the visited satellite imagery. No behaviour may be engineered to look meaningful, and that every finding must state which parts were set by hand and which emerged.

In a second step, the path taken by a wanderer across a given satellite image dataset is used to train a small Generative Adversarial Network (GAN). The conceptual move here is that the satellite image dataset is a model or world of Earth. A wanderer explores a subset of that model/world, creating its own model/world in the process (the autoencoder). The wanderer's path can be used to train a second model, the GAN, which turns the discrete tiles visited into a continuous latent space, yet another model (world) to chart a path through. A second wanderer thus traverses through the latent space, driven by intrinsic motivations. The path is then the training set for the next GAN, and so on. We are interested in drift of human-legible properties (e.g. WorldCover semantics), the resulting aesthetics of these worlds cut out of worlds, and how/if model collapse occurs and how especially the search for novelty within the ouroboros training affects the generated images versus sampling randomly. 

Finally, we seek to visualise the model and the path. We start with the phenomena of the Earth, and the composite satellite dataset a model thereof. The first wanderer's path cuts through that model - visualise this. The first wanderer's path is then used to train the second model (first genAI model), visualise the latent space. Visualise the second wanderer's path through the second model's latent space, etc. 

## Research questions → evidence → chapters

**Main Question:** What models of the Earth do algorithms construct when they curate the computational planetary image by intrinsic motivation rather than by a task?

1. How do practices of moving without a predetermined destination, like wayfaring or the dérive, translate to an untasked, step-wise traversal of the planetary image, already cut into discrete operational tiles?
2. Which paths do algorithms driven by novelty, surprise and boredom cut through the computational planetary image, and how much of their attention follows the terrain, how much the idiosyncrasies of their perception, including the places where data and phenomenon come apart?
3. What do GANs trained recursively on these paths construct, and how do the human-legible properties of the places depicted drift across generations, compared with a recursive loop without intrinsic motivation?

Current thesis structure, subject to change: 

1. Introduction 
2. Ways and Maps
3. Abandoning Objectives: Novelty Search
4. Curating Models of Worlds
5. The Computational Planetary Image
6. Algorithmic Wanderers
7. Reading Paths 
8. The Film
9. Discussion
10. Conclusion and Outlook 

## Norms
- State dated predictions in `expectations.md` before every run. Report afterwards which ones were right and which wrong, and why.
- Every claim has a control: at minimum the compass Null, and the schedule controls where relevant. Leads and results follow the existing rule.
- Keep authored and emergent apart. Every finding says what was set by hand (premises: the radius rule, the death rule, the drive filter) and what emerged. Artistic premises are not “fixed” or optimised away.
- Nothing in the walker may smuggle in an objective (no rewards for terrain, latitude, aesthetics).
- Metrics are proxies. Prefer an experiment that answers a research question over better calibration. Only calibrate when it blocks a research question.
- Dead ends and negative results are results. Report them as such.
- Traceability: every run has a config, seed, git tag and log entry. Results are reproducible from the repository.

## Constraints and caps
Work will be done across a MacBook Pro and a NVIDIA GPU-powered PC. Any GAN model training should never be conducted on the MacBook Pro. When starting work, briefly check which device you are and work accordingly. 

## Report format and cadence
- Per experiment, the existing format: short version, tables, findings, against the predictions, for review. Plus one line per finding saying which research question and chapter it bears on.
- `STATE.md`, kept current: where the project stands in thesis terms, decisions taken and why, the next planned step.
- `CHANGELOG.md`: what changed, why this approach, what you expect.

## Milestones up to March
No dates set yet, here is the sequence of events to happen. 

- world decided. GAN generation one trained as a prototype on the long path (PC).
- replication in the final world: 4 seeds plus a long Null, with the death rule and the Tobler and cluster readouts.
- the recursion runs end to end over at least 3 generations, with and without novelty-driven sampling.
- full recursion runs, with analysis tables and figures for Chapter 7.
- code freeze. Visual assets for the film. A reproducibility package.
- bug fixes and figures only.