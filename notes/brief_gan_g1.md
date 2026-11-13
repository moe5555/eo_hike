# Brief: GAN generation one (curious, weighted, against Null, unweighted)

*12 Nov 2026, revised 13 Nov (twice: the second time with Moe's Gate B decisions: N = 10,000, one walk per condition where possible, the era confound as a stated limitation, the quirk observer on samples deferred). Supersedes the three GAN conditions in the chapter 7 notes (Null, tile-weighted, collage). The collage and the crop-only side study are dropped. This brief starts where the walks end: it takes two frozen path packages as input, delivered by `notes/brief_landsat_v2_run.md`, and never runs or changes a walk.*

## What and why

Train two StyleGAN2-ADA models on the PC. The only question they answer is RQ3's first comparison: does a world built from a curious path differ from one built without intrinsic motivation?

- **G1-curious:** the path of the curious wanderer (two eyes, top-4, w_glance 1; one walk, or more if the first ends short of N), each tile weighted by the interest it had when the wanderer encountered it.
- **G1-null:** the path of the compass Null walker (one walk, or more), every tile weighted equally.
- Both: N = 10,000 unique tiles, the time offer thinned at q = 0.10.

Everything else is identical: tile count N, resolution, rendering, config, seed, training length, snapshot schedule. The difference between the two models is the difference between curated and uncurated, selection and weighting together. Separating the two is a later, optional ablation (curious tiles, equal weights) and isn't part of this brief.

The crops are not trained on separately. They enter through the weight: the interest score already contains z(top-k crop novelty) next to the glance, so a tile is valued partly for the novel detail it contained.

## How this brief runs

There are two phases, and the split matters.

- **Phase A, attended (Moe at the PC):** write and test everything, measure throughput, fix the budget, write predictions, start the job.
- **Phase B, unattended for about 72 hours:** the job builds the datasets, trains both GANs, and runs the post-training readouts. It needs no tile store, no archive access and no network. Nobody can answer a question or fix a crash during it. Anything that can fail in Phase B must have been made to fail once in Phase A.

Don't start Phase B until every item on the Phase A checklist passes. If one can't pass, tell Moe before he leaves, with the options.

## Inputs

1. **Device check.** Confirm you're on the PC (NVIDIA GPU). Log the GPU, driver, CUDA, PyTorch and OS versions. No GAN code runs on the MacBook.
2. **Two path packages, one per condition (curious, Null),** produced by the walk brief, their manifests and checksums frozen under the git tag `g1-paths`, the packages themselves copied to the PC (tiles stay outside git). The package format is defined in the walk brief's handoff section. Each package holds:
   - the N unique tiles, already rendered at 128 px by the walker's own rendering code;
   - an encounter table, one row per step, with the logged interest components;
   - a manifest with N, q, the walk ids, the start-cell list, where the package was cut, the walker's git tag, a checksum per file, and the render check done on the Mac.
3. **Verify, don't repair.** Before anything else:
   - checksums match;
   - both packages have exactly N unique tiles and the same start-cell list;
   - every curious encounter has its interest components, except each walk's start tile (never an offer);
   - the manifest records the render check (20 tiles re-rendered from the store on the Mac) as passed. The PC has no tile store, so this check is not redone there.

   If any check fails, stop and report. Don't re-render, re-walk or patch the packages on the PC. If the packages don't exist yet, this brief doesn't start: generation one is not trained on e12 paths.

## The datasets

- **Rendering:** take the renders from the package as they are (three-band CIR, square-root tone, the fixed stretch, area-resampled from the walker's 256 px tile to 128 × 128, the grid eye's ground resolution). Nothing is cut or repaired: fill, stripes, saturation, cloud, night and the black green channel of 1977 all stay in (Moe).
- **Packaging:** use `dataset_tool.py` from `NVlabs/stylegan2-ada-pytorch`, unconditional (no labels).
- **Metadata:** beside each zip, write a table built from the package, one row per unique tile:
  - cell, acquisition date, processing level, night flag;
  - quirk shares (stripes, fill, saturation, cloud) and brightness;
  - walk id and the step(s) of each encounter;
  - for curious tiles, the logged interest components at each encounter: z glance, z grid, z progress, total;
  - the final weight.

  Order lives here. A standard GAN shuffles its data; the sequence survives only in the weights and in this table.
- **Weights (curious only):**
  - Let I be the total interest of the chosen offer as logged at the moment of encounter (`I`, the value the softmax chose by; not `I_long`). Each encounter gets e = exp(I / τ). A tile encountered more than once sums its encounters.
  - A walk's start tile has no logged interest at its first encounter. That encounter gets the median e of the package (set by hand; one tile per walk).
  - I is a z-score against the offers of roughly the last 50 steps, so a weight means "more interesting than what was on offer then", not an absolute value.
  - Weights are normalised to mean 1.
  - **τ is not tuned by hand.** It is solved by bisection so that the effective sample size, ESS = (Σw)² / Σw², equals **0.5 · N**. The ESS target is the authored premise; τ follows from it. Log τ, ESS, max/median weight and the share of total weight held by the top 1 % and top 10 % of tiles.
  - **If 0.5 · N can't be reached:** summing encounters alone lowers the ESS (as τ → ∞ the weights become the encounter counts; 0.81–0.85 N in the curious dry runs). If that limit is below 0.5 · N, stop in Phase A and tell Moe. Log that limit too: it says how much of the ESS budget revisits use up before interest does anything.
  - Why the ESS floor: weighting shrinks the effective dataset, and a smaller dataset alone narrows a GAN's output. Without the floor, a less diverse G1-curious couldn't be told apart from a smaller G1-null.
- **Null:** weight 1 for every unique tile. Duplicate encounters do not add weight. Log ESS (= N) for symmetry.
- **Sanity checks**, written to the run folder:
  - contact sheets of 64 random tiles per condition;
  - for curious, the 64 heaviest and the 64 lightest tiles.

## Training

- **Code:** `NVlabs/stylegan2-ada-pytorch`, pinned to a commit and logged. Patch it as little as possible, and keep every patch in a separate, documented diff.
- **Weighted sampling:** replace the uniform `InfiniteSampler` with a seeded weighted sampler (draws proportional to weight, with replacement) for G1-curious. G1-null uses the same sampler code with all weights 1, so both runs go through identical code paths.
- **Config:**
  - resolution 128;
  - ADA on (target p 0.6, the default);
  - augmentation pipe `bgc`;
  - `--mirror=0`: flips are already in `bgc`, and the dataset isn't doubled;
  - batch size and γ from the repo's recommendations for this resolution and dataset size.

  Same seed for both, logged. One training seed per condition is a stated limitation.
- **Length:** a fixed kimg budget, identical for both runs, set in Phase A from measured throughput (see the budget section). Not "until it looks good".
- **Snapshots:**
  - a network pickle plus a 8 × 8 grid of fakes at fixed latents, at the same kimg intervals for both runs;
  - keep the last snapshot and every snapshot at a quarter, a half and three quarters of the budget; delete the rest as you go.
- **Metrics:**
  - `fid50k_full` against each run's own training set, at a low frequency (four times per run, at most), as a **training-health signal only**. Inception is an ImageNet eye, and FID on CIR satellite tiles is not an RQ3 readout. Say so in the report.
  - If metrics would cost more than 10 % of the budget, compute them only on the kept snapshots after training.
- **Which snapshot counts:** the final snapshot of each run, at equal kimg. Never "best FID". Picking the best snapshot per condition would let the selection itself differ between conditions.
- **Running both on one GPU:** prefer running the two jobs **concurrently**, with the same kimg target. If anything goes wrong mid-run, both stop at comparable progress, and you never end up with a finished curious model and no Null. Only if memory or throughput rule this out, run them sequentially in alternating chunks of equal kimg (curious, null, curious, …), resuming each time. That depends on resume being exact (see below).

## Unattended robustness (must be tested in Phase A)

- **Resume.** Check what the repo's snapshot and `--resume` actually restore. My recollection is that it reloads the networks but not the ADA probability p, the optimiser states or the kimg counter. Test it rather than trust either of us. Make the snapshot carry all of them and resume restore all of them. Test by killing a training process mid-run and confirming that p, kimg and the loss curves continue rather than restart.
- **Watchdog.** A supervisor script restarts a crashed job from its latest snapshot, at most 3 times per run. It logs every restart with its cause. After the third failure it stops that run cleanly and writes the reason to the status file. If one run fails for good, the other carries on.
- **Disk.** Estimate total disk use (datasets, kept snapshots, readouts) and check it against free space with at least 30 % margin. If free space falls below 20 GB during the run, stop gracefully after the next snapshot.
- **Custom CUDA ops.** If the repo's plugins (`bias_act`, `upfirdn2d`) fail to compile on this machine, it falls back to slow reference ops. Detect this in Phase A and include it in the throughput measurement. Fix the compilation if you can; otherwise budget for the slower speed.
- **Thermals and throttling.** Log GPU temperature, clock and utilisation every 10 minutes.
- **The status file.** `runs/g1/STATUS.md`, rewritten at every snapshot and on any event. It holds:
  - per run: kimg done and target, sec/kimg, ETA, augment p, the latest health metric, restarts;
  - disk free, GPU temperature, last event, wall-clock time.

  Plus the latest fakes grid per run as a PNG. This is the first thing Moe opens on return.

## The budget

Phase B has about 72 hours. Plan to finish in **60**, leaving 12 hours of margin for restarts and slow steps.

1. In Phase A, measure on this machine:
   - dataset build time;
   - sec/kimg for both runs going concurrently, from a short run of at least 20 kimg after warm-up;
   - readout time.
2. Set the kimg budget so that datasets + training + readouts ≤ 60 h.
3. Write the budget and the measured rates into `expectations.md` and `STATE.md` before Phase B.

If the arithmetic gives less than about 2,000 kimg per run, tell Moe before he leaves. A short budget is acceptable as a prototype, but it should be a decision, not a surprise.

## Post-training readouts (run automatically at the end of Phase B)

On the final snapshot of each run:

1. **Samples:** 5,000 images per GAN at fixed seeds (the same seeds for both). Truncation ψ = 1, so the GAN's whole distribution is sampled and nothing is trimmed.
2. **Quirk detectors** (the apparatus observer): **deferred (Moe, 2026-11-13).** The e12 detectors can't run on samples as they stand. They read raw values and QA bands (stripes on raw values, cloud from QA_PIXEL, saturation from QA_RADSAT, night from the sun elevation in the metadata), and a sample is an 8-bit CIR image. Detectors that work on the image itself (black fill, pixels at 255, stripes on the rendered channels, darkness for night), run the same way on training renders and samples, are one option; the choice is Moe's. Until then Phase B saves the 5,000 samples per GAN, and this readout runs on them afterwards. Nothing in Phase B depends on it.
3. **Human-legible observers:** run the ones that already exist and are frozen. Don't build new ones in this session. If ISODATA land cover is not ready, say so and report colour and texture statistics in its place, labelled as such.
4. **Memorisation:** for each sample, its nearest training tile in downsampled pixel space. Report the distribution of nearest distances against the training set's own nearest-neighbour distances, and the 32 closest pairs as a contact sheet.
5. **Diversity:** precision and recall against each GAN's training set (Kynkäänniemi et al., 2019), with a pixel-space or downsampled feature space. Any pretrained feature extractor is named as an observer outside the loop. For G1-curious, report it against two references: the unweighted training set, and a reference of N draws by the weights (what the GAN was shown). Against the unweighted set alone, G1-curious would look less diverse by construction.
6. **Film assets:**
   - contact sheets of 256 samples per GAN;
   - a 60-second latent interpolation video per GAN through fixed seeds;
   - the snapshot fakes grids over training as a time-lapse.
7. **Report** in the existing format (short version, tables, findings, against the predictions, for review), one line per finding for its RQ and chapter. Every finding says what was set by hand (N, q, the ESS target, the weight mapping, kimg, config) and what emerged. The era confound (below) is stated next to every comparison of the two GANs.

## A stated limitation: the era confound (Moe, 2026-11-13)

The curious walker and the Null move their clocks at different speeds, so their N tiles can come from different stretches of the mission (season, coverage, the 1977 green band). The two GANs then differ by era as well as by curation. This is accepted, not matched. The report shows both packages' clock and tile-date distributions side by side, and generation one has one walk per condition, so a difference between the GANs is a hint about one curious path against one Null path, not about curiosity in general.

## Predictions (dated in `notes/06_characters/expectations.md` before Phase B)

A first set is written before the walks (predictions 152–157). Phase A adds the measured ones (τ, the budget) and may restate these, dated, before Phase B.

At least:

- τ and the top-10 % weight share at ESS = 0.5 N.
- Whether the heaviest tiles are enriched in quirks (stripes, fill, night) compared with the curious training set as a whole, given e12's taste for clear and dark tiles with the eye's pull towards stripes.
- Whether G1-curious reproduces its training set's quirk shares, amplifies them or flattens them, against G1-null.
- Which GAN is less diverse (recall), and whether the gap survives the ESS floor.
- The final augment p for each run. Expected high, since N is small.
- Memorisation: whether either GAN copies tiles at this N and kimg.

## Phase A checklist (all must pass before Moe leaves)

- [ ] On the PC; versions logged; repo commit pinned; patches in a separate diff.
- [ ] Both path packages copied to the PC, their checksums at tag `g1-paths`, and verified (checksums, N, start cells, interest components, the Mac's render check recorded).
- [ ] Both datasets built at small scale (200 tiles); contact sheets look right; weights, τ and ESS check out on the small set.
- [ ] Weighted sampler verified: over 100k draws, empirical frequencies match the weights within sampling error.
- [ ] Both runs train concurrently for 20+ kimg; sec/kimg measured; custom ops status known.
- [ ] Kill test passed: a run killed mid-training resumes with p, kimg and optimiser state intact. The watchdog restarts it without help.
- [ ] Disk estimate with margin; cache cap on.
- [ ] Budget computed, ≤ 60 h; written down.
- [ ] Predictions dated in `notes/06_characters/expectations.md`; `STATE.md` and `CHANGELOG.md` updated; config and git tag (`g1-start`) committed.
- [ ] `STATUS.md` updates on a test snapshot.
- [ ] One command starts the whole Phase B pipeline. Moe has seen it start and the first status update arrive.

## For Moe before leaving (machine settings)

- Turn off sleep and hibernation, and disable automatic restarts for OS updates for the next four days.
- Make sure the PC is on power that won't be switched off. No network is needed during Phase B.
- Leave the session, terminal or service in a state that a closed laptop lid or a logged-out screen won't kill.

## Out of scope here

- The optional ablation (curious tiles, equal weights).
- Generation 2, and how a wanderer's time runs out in a synthetic world (Moe decides before generation 2).
- Running, re-running or changing any walk, and any change to the walker.
- Thesis prose.
