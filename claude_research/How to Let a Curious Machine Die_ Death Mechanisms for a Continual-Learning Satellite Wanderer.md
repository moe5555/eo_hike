# How to Let a Curious Machine Die: Death Mechanisms for a Continual-Learning Satellite Wanderer

The best principled death for your wanderer is **senescence by loss of plasticity**. The world never runs out of novelty, but the agent's ability to learn from it does run out. You can measure that decline, tune it per temperament, and it is a very active research area (Dohare et al., *Nature* 2024). Pair it with **death by surprise**, an optimiser- and saturation-driven collapse like the one your Fast learner already suffered, as a second, sudden way to die. Define both deaths operationally, as a learning-progress or plasticity test the agent fails, not as a step count. That way boredom becomes something the agent runs out of internally, which is the honest version of Schmidhuber's theory, rather than something the world has to run out of.

## TL;DR

- **Main recommendation: senescence through loss of plasticity.** Standard deep learning "gradually lose[s] plasticity in continual-learning settings until [networks] learn no better than a shallow network" (Dohare et al., *Nature* 2024). Death is declared when the wanderer can no longer learn from fresh tiles better than a newborn network can. In Schmidhuber's terms, compression progress stops because the learner is exhausted, not because the world is. You set lifespan through "longevity genes": how much weight decay, shrink-and-perturb or continual-backprop replacement a temperament gets. Teleports (abrupt distribution shifts) work as the ageing clock.
- **Second death: death by surprise.** This is a sudden, absorbing collapse: an Adam-driven update spike pushes a sigmoid decoder into saturation, giving black output and zero gradient. That is your step-142 death, and it is a real, currently studied failure mode. Molybog et al. (2023) analysed Adam instability, and Bai et al. (arXiv 2506.04805, ICML 2026) found that loss spikes occur when "the adaptive preconditioner v_t fails to track the instantaneous squared gradients" and that "directly reducing β2 effectively mitigates loss spikes." Give it to the Fast learner and tune its hazard with learning rate, Adam β2/ε and gradient clipping. Be aware that its timing is heavy-tailed, so you need survival curves across seeds, not single runs.
- **Satellite and mortality framings.** Sensor degradation modelled on Landsat 7's 2003 scan-line-corrector failure, or Sentinel-1B's 2021 payload power failure, fits better as a dramaturgical layer or a third temperament than as the main mechanism, because you choose the schedule. Mortal computation (Hinton 2022; Ororbia & Friston 2023) and programmed death (Werfel et al., *PRL* 2015) give the thesis its philosophical footing. Model collapse (Shumailov et al., *Nature* 2024) belongs to the recursive GAN chain, not to the death of an individual wanderer.

## Key Findings

1. **Ask what the agent runs out of, not what the world runs out of.** Plasticity loss is well documented: dead or dormant units rise, weight magnitude grows and effective rank falls (Dohare et al. 2024; Sokar et al. 2023; Lyle et al. 2023/2024).\[1\] It turns "boredom can never be exhausted on 2 million tiles" into "the wanderer can no longer be surprised productively." That is exactly the condition Schmidhuber (2010) and Oudeyer et al. (2007) call boredom: learning progress at zero.\[2\]
2. **Your teleports are an ageing mechanism.** The literature attributes plasticity loss mainly to non-stationarity. Liu & Mou (arXiv 2602.09234, 2026 preprint) report that "the severity of plasticity loss is closely tied to the abruptness of task transitions, and can be substantially reduced when the environment changes gradually." Walking tile to tile is gradual change; a boredom teleport is an abrupt task switch. So boredom ages the agent. This is a conceptually elegant loop and it can be tested.
3. **Natural senescence is slow at your scale, so speed it up on purpose and say so.** In Dohare et al., collapse takes hundreds to thousands of tasks (e.g. up to 25% dead units after 800 Permuted-MNIST tasks; PPO collapse after ~3M steps).\[1\]\[3\] To die within 5,000–10,000 steps you must remove the remedies and raise the replay ratio. This is a legitimate "set the conditions" move.
4. **Death by surprise is real, but its timing is the hardest part to control.** Loss spikes come from interacting factors (optimiser state, curvature, data), so the moment of death is heavy-tailed. You control the hazard rate, not the moment. That matches your "set the conditions, not the moment" brief exactly, provided you show the distribution.
5. **The black decoder output is a literal "dark room."** In Friston's dark-room problem, an agent minimises surprise by sitting in the dark (Friston, Thornton & Clark 2012).\[4\] A saturated autoencoder that outputs black for every input has reached that fixed point. For a curiosity agent, which seeks prediction error the way Schmidhuber's agents do, it is death.\[5\] That is a strong conceptual image for the film.

## Comparative overview

| Mechanism | Type | Timing control | Conceptual fit | Contemporaneity | Overall |
|---|---|---|---|---|---|
| Loss of plasticity / senescence (dormant units, rank collapse, weight growth, primacy bias) | Gradual | Good (via remedy strength, replay ratio, LR) | Excellent: boredom from within; teleports age | Very high (2022–2026) | **1st** |
| Death by surprise (Adam spike → sigmoid saturation / dead units) | Sudden | Moderate (hazard, not moment) | Excellent: curiosity killed by what it seeks; dark room | High (LLM loss-spike work 2023–2025) | **2nd** |
| Sensor degradation (SLC-off gaps, sensor drift, noise, bit flips) | Gradual or sudden | Fully designer-set unless coupled to use | Strong for operational images / planetary theme | Mostly engineering, not ML-novel | **3rd (or framing layer)** |
| Hazard-rate / programmed death (constant or state-dependent mortality) | Stochastic | Excellent (mean = 1/q) | Good (Werfel: death leaves resources for descendants → GAN chain) | Moderate | Fallback / scaffolding |
| Noisy-TV capture / curiosity "addiction" | Behavioural | Poor | Good (dérive captured) but it is a stall, not a death | Classic (2018) | Secondary symptom |
| Catastrophic forgetting | Gradual / episodic | Poor | Weak: an autoencoder relearns; forgetting ≠ death | High, but wrong fit | Not recommended |
| Model collapse | Across generations | Good (per generation) | Essential for the chain, not individual death | Very high (Nature 2024) | Use in stage 2 |

## Details

### 1. Senescence: loss of plasticity (recommended primary death)

**(a) Plain language.** The more a network learns from a changing stream, the worse it gets at learning anything new. Units go silent, the remaining ones become redundant and over-committed, and the weights grow until small updates stop mattering. In the end it learns no better than a much simpler model.\[1\]

**(b) Key sources.**
- Dohare, Hernandez-Garcia, Lan, Rahman, Mahmood & Sutton, "Loss of plasticity in deep continual learning," *Nature* 632, 768–774 (2024). On Continual ImageNet, networks "learned up to 88% correct on the test set of the early tasks" but by the 2,000th task "had lost substantial plasticity for all values of the step-size parameter," some ending "below that of a linear network."\[1\] Plasticity loss was "correlated with an increase in weight magnitude, a decrease in the effective rank of the representation and an increase in the fraction of dead units."\[1\] In a constant-friction ant task, PPO "increased for about 3 million steps but then collapsed."\[1\]
- The same paper reports that "popular methods such as Adam, Dropout and normalization actually increased loss of plasticity," while L2 regularisation, Shrink and Perturb and continual backpropagation maintained it. Continual backprop reinitialises "a small fraction of less-used units."\[1\]
- Sokar, Agarwal, Castro & Evci, "The dormant neuron phenomenon in deep reinforcement learning," ICML 2023 (oral). It defines τ-dormant neurons by normalised activation, identifies target non-stationarity as the main cause, and proposes ReDo (recycling dormant neurons).\[6\]\[7\]\[8\]
- Lyle et al., "Understanding plasticity in neural networks," ICML 2023: plasticity loss is tied to loss-landscape curvature and "often occurs in the absence of saturated units."\[9\] Lyle, Zheng, Khetarpal, van Hasselt, Pascanu, Martens & Dabney, "Disentangling the causes of plasticity loss in neural networks," CoLLAs 2024: "a combination of layer normalization and weight decay is highly effective at maintaining plasticity."\[10\] It also hypothesises that regression on large-mean targets drives parameter-norm growth.\[11\]
- Nikishin, Schwarzer, D'Oro, Bacon & Courville, "The primacy bias in deep reinforcement learning," ICML 2022: agents overfit early experience, and the effect worsens as the replay ratio (updates per interaction) rises. The remedy is periodic resets.\[12\]\[13\]\[14\]
- Liu & Mou, "Do Neural Networks Lose Plasticity in a Gradually Changing World?" (arXiv 2602.09234, v2 June 2026), report that "the severity of plasticity loss is closely tied to the abruptness of task transitions, and can be substantially reduced when the environment changes gradually."
- Active follow-ups (2024–2026) include spectral-collapse, curvature, Hessian-based and theoretical accounts ("Spectral Collapse Drives Loss of Plasticity," 2025; "Barriers for Learning in an Evolving World," 2025; "Predicting Plasticity in Deep Continual Learning," 2026), plus a 2024 deep-RL survey (Klein et al., arXiv 2411.04832).\[15\]\[16\]\[17\]\[18\]

**(c) Implementation for a small online convolutional autoencoder (PyTorch).**
- *Ageing levers (turn them up to age faster):*
  - Use ReLU, not LeakyReLU.
  - Use Adam with default betas; Dohare et al. found Adam increased plasticity loss, and Lyle et al. found standard β1/β2 settings harmful.\[1\]\[19\]
  - Use no weight decay, no LayerNorm, and a narrow bottleneck and channel count.
  - Use a higher replay ratio: k gradient steps per visited tile, sampled from the 128-step buffer. This is the most direct accelerator via primacy bias.
  - Make teleports the abrupt shocks. If ageing is too slow, a temperament with a low boredom threshold, meaning more teleports, will age faster. That gives a meaningful link between personality and lifespan.
- *Longevity genes (the "remedies" as a dial):* weight-decay λ, shrink-and-perturb strength, or the continual-backprop replacement rate (Dohare et al. call the replacement rate the main hyperparameter).\[20\] A temperament with a small amount of regeneration lives longer. Setting these to zero is the "mortal" default.
- *Vital signs (log every N steps, and show them in the film as telemetry):*
  - Dormant-unit fraction per layer, using the Sokar τ-dormant definition: mean |activation| divided by the layer mean, below τ (e.g. 0.025 or 0.1).\[6\]
  - Effective rank of the bottleneck embedding over a fixed probe batch, as in Dohare et al.\[21\]
  - Mean |weight|.
  - Gradient norm.
- *Operational definition of death (the important part):* run a **plasticity probe** every M steps (e.g. 100):
  1. Clone the current network and optimiser state.
  2. Train the clone for K steps (e.g. 50) on a batch of fresh, never-visited tiles.
  3. Measure the relative reconstruction-error reduction.
  4. Do the same with a freshly initialised network of the same architecture, trained for the same K steps from scratch. Cache this reference over a few seeds.
  5. Declare death when the wanderer's learning gain falls below the newborn's (ratio < 1, or < 0.5 for a stricter criterion) for P consecutive probes.

  This takes Dohare's benchmark ("no better than a shallow/linear network") and turns it into a criterion that is not arbitrary. You can also compare against a linear autoencoder (PCA-like) baseline, which mirrors Nature's "linear network" line exactly.\[1\]
- *Expected timescale:* with remedies off and replay ratio 1, a small autoencoder will probably not die within 10,000 steps. The literature timescales are thousands of tasks. Expect to need a replay ratio of about 4–16 and/or a higher learning rate to bring death into the 5,000–10,000-step window. Calibrate empirically with 10–20 seeds per temperament on short runs, then extrapolate the vital-sign trends.

**(d) Conceptual fit.**
- Excellent. Schmidhuber defines fun as compression progress, and progress "is zero whenever the unexpected is just random white noise."\[22\] For a senescent learner, every tile becomes either already compressed or effectively noise, so the whole world turns boring at once. Oudeyer's IAC seeks situations "neither too predictable nor too unpredictable." A dead learner has no such region left anywhere.\[23\]
- For the dérive, the walk does not end at a destination; it ends when the walker can no longer be changed by the city.
- Primacy bias means late-life perception is shaped by the earliest tiles.\[13\] That gives the agent a "first landscape" it never stops seeing, which then feeds the GAN chain.

**(e) Contemporaneity.** This is one of the most active areas in continual learning and RL from 2022 to 2026: Nature 2024, ICML 2022/2023, CoLLAs 2024, and multiple arXiv papers in 2025–2026.

### 2. Death by surprise: optimiser instability and output saturation (recommended secondary death)

**(a) Plain language.** One unusually surprising input, or a run of them, produces a gradient that the optimiser's internal scaling over-amplifies. One or a few huge updates shove the network into a region where the output nonlinearity is saturated: sigmoid at 0 means black. There the gradient is about zero, so the network can never climb out. Death is absorbing.

**(b) Key sources.**
- Molybog et al., "A Theory on Adam Instability in Large-Scale Machine Learning," arXiv 2304.09871 (2023, Meta). Adam "can enter a state in which the parameter update vector has a relatively large norm and is essentially uncorrelated with the direction of descent," linked to time-domain correlation of gradients.\[24\]\[25\]\[26\]
- Bai, Zhou, Xu et al., "Adaptive Preconditioners Trigger Loss Spikes in Adam" (arXiv 2506.04805; ICML 2026). They find spikes arise when "the adaptive preconditioner v_t fails to track the instantaneous squared gradients," observe that "sudden small gradients are often observed before spikes," and report that "directly reducing β2 effectively mitigates loss spikes," consistent with recent LLMs adopting β2 ≤ 0.95.
- "Beyond Quadratic Loss: The Stability Phase Diagram of Adam" (2026 preprint) links spikes to the mismatch between Adam's two momentum timescales.\[27\]
- Foundations: Cohen et al., "Gradient Descent on Neural Networks Typically Occurs at the Edge of Stability," ICLR 2021. Sharpness rises to about 2/η and hovers there. Lewkowycz et al. 2020, the "catapult" large-learning-rate phase.\[28\]\[29\]\[30\]
- For dead units, Dohare et al. 2024 report dead-unit fractions climbing over training.\[31\] That gives a gradual route to the same absorbing end state.

**(c) Implementation.**
- *Likely mechanism of your step-142 death:* Adam normalises each update by √v (a running mean of squared gradients). Familiar tiles let v shrink. Then a run of hard tiles (ice, mountains) produces gradients far larger than √v, and the effective step balloons. With a sigmoid output and MSE, a large negative push on the final bias or weights saturates every pixel, and the gradient through σ′≈0 vanishes. "Four updates, 0.015 → 0.895" is a textbook absorbing collapse.
- *Hazard levers:*
  - Learning rate. This is the main one.
  - Adam β2. Bai et al. (ICML 2026) note that this "decoupling is exacerbated by larger β2 as higher β2 increases the inertia of the second-moment estimator."
  - ε. Smaller ε amplifies small-v spikes.
  - Gradient clipping. Remove it to allow death, or set a per-temperament clip value as a "constitution."
  - Batch size. Batch size 1 is most fragile.
  - Sigmoid output vs. linear-plus-clamp. Sigmoid makes the collapse absorbing; linear makes it recoverable.
  - Curiosity weighting toward high-error tiles. This raises surprise exposure, so curiosity literally raises mortality.
- *Operational definition of death:* treat a loss spike as a seizure and an unrecovered seizure as death.
  - Spike: a MAD-based reconstruction-error z-score above 5 relative to a rolling median over a trailing window, following the IFM/LLM360 K2-V2 report (arXiv 2512.06201, Dec 2025), where the window is "approximately 1% of the full training duration" and "Points with z_t > 5 are flagged as loss spikes."
  - Death: within W steps (e.g. 50), (i) error stays above, say, 10× its pre-spike median, and (ii) decoder output std across a fixed probe batch is below 1e-3 (the flatline: same image for every input), and/or (iii) gradient norm is below 1e-7.
  - Requiring "no recovery within W" separates death from a survivable shock and makes the definition defensible.
- *Timescale:* highly stochastic. The Fast learner at 3e-3 died at step 142; to place death around 5,000–10,000 steps, lower the learning rate and β2 and sweep across seeds. Expect a broad, possibly heavy-tailed distribution of lifespans. Report it as a survival (Kaplan–Meier) curve per temperament.

**(d) Conceptual fit.**
- Superb. The curious agent is killed by the very surprise it seeks. Burda et al. (2018) showed prediction-error agents become "addicted" to a noisy TV.\[32\] Your Fast learner's attraction to high-frequency, high-contrast terrain (mountains, ice) is plausibly the same pull. Here the pull is lethal.
- The black decoder output is the dark room, Friston's surprise-minimising fixed point (Friston, Thornton & Clark 2012). For a curiosity agent that is death, because Schmidhuber's agents seek out prediction error rather than suppress it.\[4\]\[5\]
- The operational-image parallel is Sentinel-1B: on 23 December 2021 an anomaly in the instrument power supply left it "unable to deliver radar data." ESA declared the mission over on 3 August 2022, while the platform kept functioning: "all other systems except the power affected unit... continue to function nominally."\[33\]\[34\]\[35\] Your wanderer can likewise keep walking with a dead eye. A post-mortem walk, still choosing tiles from an embedding that no longer sees, is a striking filmic coda.

**(e) Contemporaneity.** High. LLM loss-spike research 2023–2026 and edge-of-stability theory 2021–2026.

### 3. Sensor degradation and satellite end-of-life (framing layer or third temperament)

**(a) Plain language.** The eye degrades rather than the brain: gaps, noise, drift, dead pixels or corrupted weights.

**(b) Sources and analogues.**
- **Landsat 7.** The ETM+ scan line corrector failed on 31 May 2003. The cause, per NASA, was a power-supply issue, and the SLC had no redundant unit. The satellite kept imaging, but according to Storey, Scaramuzza, Schmidt & Barsi (USGS, 2005), SLC-off images are "missing approximately 22 percent of the normal scene area" in wedge-shaped gaps.
- **Sentinel-1B.** Payload power failure in 2021 (see above). ESA's In-Flight Anomaly Summary Report identified "18 potential failure modes related to a potential leakage of a ceramic capacitor," and pointed to the soldering process used years earlier to repair that capacitor. On 3 August 2022, ESA's Simonetta Cheli concluded it was "impossible to recover the 28V regulated bus": a latent flaw from 2016 that failed five years later. That is a perfect "conditions set, moment emergent" story.

**(c) Implementation.**
- Mask the input with SLC-off-style wedge gaps whose width grows with age.
- Add sensor noise or band drift.
- Inject random bit flips into weights.
- To avoid arbitrariness, couple degradation to use rather than time. For example, each teleport (an "orbital manoeuvre") costs fuel or wear, or degradation probability rises with the cumulative gradient magnitude the eye has absorbed.
- Death can then be the point where the plasticity probe from section 1 fails, so sensor decay becomes one cause of the same honestly measured end.

**(d) Fit.** Very strong for Farocki and Paglen's operational images and for the Sentinel-2 / Major TOM corpus. But taken alone it is the least intrinsic death: the agent does not die of curiosity, it dies of you. Use it as visual language (gaps creeping into the film's frames) or as a "hardware-mortal" temperament.

**(e) Contemporaneity.** Fault-injection and bit-flip robustness is an established engineering field. I did not verify specific recent sources for it here, so treat this part as unsourced.

### 4. Hazard-rate / programmed death (scaffolding, not centrepiece)

Werfel, Ingber & Bar-Yam, "Programed Death Is Favored by Natural Selection in Spatial Systems," *Physical Review Letters* 114, 238103 (2015). In spatial models with local reproduction, "programmed deaths instead robustly result in long-term benefit to a lineage, by reducing local environmental resource depletion."\[36\] In their model each consumer dies with probability q per step (mean lifespan 1/q).\[37\] Implemented directly, this is exactly "set the conditions, not the moment." A pure timer, though, will read as arbitrary.

The better use is a **state-dependent hazard**: per-step death probability rises with the vital signs (e.g. hazard ∝ dormant fraction, or ∝ 1 − plasticity ratio). The conceptual payoff is the chain: the wanderer's death "leaves resources for descendants."\[37\] Its path becomes the GAN's training data, and a new wanderer inherits a world made of its parent's attention.

### 5. Curiosity-specific failure modes (symptoms, not deaths)

- **Noisy TV** (Burda et al., ICLR 2019; Pathak et al. 2017). Prediction-error curiosity is trapped by unlearnable stochasticity. Your reconstruction-error signal is vulnerable to this. Your probe-based learning-progress signal is the principled defence, since in Schmidhuber's terms progress on white noise is zero.\[22\]\[32\] Use the gap between "high reconstruction error" and "low learning progress" as a diagnostic, and possibly as a cause of death: an agent addicted to unlearnable terrain wastes its plasticity there.
- **Detachment and derailment** (Ecoffet et al., "First return, then explore," *Nature* 2021). Intrinsic-motivation agents lose track of frontiers they once found interesting.\[38\] In your wanderer, teleports constantly detach it. This is a good concept for the thesis text, but it is not a death mechanism.
- **Boredom in learning-progress agents** (Oudeyer, Kaplan & Hafner 2007; Schmidhuber 2010).\[39\]\[40\]\[41\]\[42\]\[43\] Once something is learned it "will not provide learning progress anymore."\[2\] Your recommended death is the global, irreversible version of this local boredom.

### 6. Mortality as philosophy (thesis framing)

Hinton's Forward-Forward paper (2022) has a section titled "Mortal Computation." It argues for giving up the separation of software and hardware: learned parameters "are only useful for that specific hardware instance, so the computation they perform is mortal: it dies with the hardware."\[44\]\[45\] Ororbia & Friston, "Mortal Computation: A Foundation for Biomimetic Intelligence" (arXiv 2311.09589, 2023), extend this through the free-energy principle, Markov blankets and self-maintenance.\[46\]\[47\]

For you this justifies a key artistic choice: **the wanderer's weights are never transplanted.** Its knowledge survives only by distillation into its path, and through the path into the GAN. That mirrors Hinton's proposal that mortal computers pass on knowledge by training successors.\[48\]

### 7. Artistic precedents

- Sommerer & Mignonneau, *A-Volve* (1993–94; Golden Nica 1994). Creatures die of hunger, of being killed, or by "natural death – a certain maximum life time was reached."\[49\] It is the clearest precedent for explicit lifespans.
- Sommerer & Mignonneau, *Life Spacies* (1997/99). Creatures starve if they cannot catch enough text characters.\[50\]
- Ian Cheng, *BOB (Bag of Beliefs)* (2018–19). BOB "dies many deaths – whether through failures of personality, bad parenting, random accident, or a life well lived." Its conservator described shutting it down and archiving its evolved state: "At this stage, BOB could be said to no longer exist."\[51\]\[52\]
- Ian Cheng, *Thousand Lives* (2023–24). An AI turtle that, according to Park Han-sol in The Korea Times (3 March 2024), reincarnates "retaining about 20 percent of the beliefs it obtained in its previous life." That figure comes from press coverage, not artist documentation.
- Alvin Lucier, *I am sitting in a room* (1969). Re-recording reinforces "the resonant frequencies of the room... so that any semblance of my speech... is destroyed."\[53\] This is your chain's model. Note the difference: Lucier's degradation is cross-generational, which corresponds to Shumailov et al.'s model collapse ("AI models collapse when trained on recursively generated data," *Nature* 631, 2024).\[54\] Senescence happens within one life.

## Recommendations

**Ranked choice.**
1. **Senescence (loss of plasticity) as the canonical death,** defined by the plasticity probe: the wanderer learns no better than a newborn. It is the most honest answer to "why stop?", it is measurable, it fits the thesis spine (Schmidhuber, Oudeyer, dérive) best, and it is the most contemporary.
2. **Death by surprise for fast or reckless temperaments,** defined as an unrecovered loss spike plus output flatline. It is already observed in your system, conceptually vivid (curiosity killed by surprise; the dark room), and grounded in current Adam-instability research.
3. **Sensor or operational decay** either as a third temperament (a "Landsat" character whose eye fails with use) or as visual dramaturgy layered onto the other deaths.

**Temperament assignments (example).**
- *Fast learner:* high learning rate, β2 = 0.999, small ε, no clipping, sigmoid output, curiosity weighted to reconstruction error. Dies suddenly, by surprise, typically early.
- *Cautious / contemplative:* low learning rate, clipping, no regeneration, high replay ratio. Fades by senescence. Its learning-progress curve flattens, the dormant fraction climbs, effective rank falls, and it eventually fails the plasticity probe.
- *Restless / bored:* low boredom threshold, many teleports. Ages through repeated abrupt shifts, so its life is shorter in steps but wider in geography.
- *Long-lived:* a small continual-backprop replacement rate or weight decay. Lives longest. Possibly it never dies within budget, which is a useful control showing that death is a property of the conditions.

**Process.**
- Calibrate with short multi-seed sweeps and fit survival curves. Pick settings where the median lifespan falls between 5,000 and 10,000 steps.
- Present the distribution in the thesis: this is your proof that the moment emerges.
- Log the vital signs in real time. They are both your scientific evidence and the film's on-screen telemetry: dormant fraction, effective rank, weight norm, learning-progress probe and gradient norm. Operational images of the agent's own body.
- Record the post-mortem. For surprise deaths, consider letting the dead eye keep walking for a coda (the Sentinel-1B image: platform alive, payload dead). For senescent deaths, the final stretch of path, concentrated and repetitive, is itself the material the GAN inherits.

## Caveats

- **Timescale mismatch.** Published plasticity loss unfolds over thousands of tasks or millions of steps. Reaching 5,000–10,000 steps will require deliberate acceleration (replay ratio, learning rate, no remedies). That is defensible as "conditions," but state it openly. Lyle et al. (2023) also found plasticity loss can occur without saturated units, so do not rely on one vital sign.\[9\]
- **Stochastic timing.** Surprise deaths can be heavy-tailed: some seeds die in 100 steps, others never. If that is unacceptable for the film, use a state-dependent hazard (section 4) to make timing more regular while keeping it emergent.
- **Death vs. bug.** A saturated sigmoid looks like a coding error. Mitigate this with:
  - the explicit no-recovery criterion;
  - logged causal precursors (the surprise run, the Adam update norm);
  - reproducibility across seeds;
  - a control temperament that does not die under the same code.
- **Arbitrariness.** Fixed fuel budgets, timers and designer-scheduled sensor decay will read as engineered. Couple any external decay to the agent's own behaviour (teleports, absorbed surprise).
- **Preprint status.** The "gradual vs. abrupt change" claim (2026) and several 2025–2026 mechanism papers are arXiv preprints, not peer-reviewed. The teleport-as-ageing hypothesis is plausible but should be checked empirically in your system.
- **Unverified items.** I did not source specific recent bit-flip / radiation-fault literature, and the *Thousand Lives* 20% figure comes only from press coverage (Park Han-sol, The Korea Times, 3 March 2024).

## Sources

1. [Loss of plasticity in deep continual learning - PMC - NIH](https://pmc.ncbi.nlm.nih.gov/articles/PMC11338828/)
2. [Intrinsic Motivation Systems for Autonomous Mental Development](https://web.eecs.umich.edu/~stellayu/teach/2023action/slides/2007oudeyerIntrinsicMotivationSlides.pdf)
3. [(PDF) Maintaining Plasticity in Deep Continual Learning](https://www.researchgate.net/publication/371871435_Maintaining_Plasticity_in_Deep_Continual_Learning)
4. [www.frontiersin.org](https://www.frontiersin.org/articles/10.3389/fpsyg.2012.00130/pdf)
5. [Predictive coding, Free Energy in the sense of Friston — The Dan MacKinlay stable of variably-well-consider’d enterprises](https://danmackinlay.name/notebook/predictive_coding.html)
6. [GitHub - timoklein/redo: ReDo: The Dormant Neuron Phenomenon in Deep Reinforcement Learning (pytorch) · GitHub](https://github.com/timoklein/redo)
7. [The Dormant Neuron Phenomenon in Deep Reinforcement Learning](https://openreview.net/forum?id=skb34O7hFp)
8. [Learning Continually Under Changing Data Distributions](https://assets.w3.tue.nl/w/fileadmin/content/universiteit/Academische_plechtigheden/academische_jaarprijzen/2024/PhD/Thesis/PhDThesis_GhadaSokar.pdf)
9. [\[PDF\] Disentangling the Causes of Plasticity Loss in Neural Networks](https://www.semanticscholar.org/paper/Disentangling-the-Causes-of-Plasticity-Loss-in-Lyle-Zheng/5c0e88f9d0827ac6360e2c85e1fa55fc950fe67c)
10. [Disentangling the Causes of Plasticity Loss in Neural Networks](https://mlanthology.org/collas/2024/lyle2024collas-disentangling/)
11. [Plasticity Loss in Deep Reinforcement Learning: A Survey](https://www.alphaxiv.org/abs/2411.04832)
12. [\[PDF\] The Primacy Bias in Deep Reinforcement Learning](https://www.semanticscholar.org/paper/The-Primacy-Bias-in-Deep-Reinforcement-Learning-Nikishin-Schwarzer/69b80ce5ab6c2263b145b1eaa23664145938f351)
13. [GitHub - evgenii-nikishin/rl\_with\_resets: JAX implementation of deep RL agents with resets from the paper "The Primacy Bias in Deep Reinforcement Learning" · GitHub](https://github.com/evgenii-nikishin/rl_with_resets)
14. [Sample-Efficient and Safe Deep Reinforcement Learning via Reset Deep Ensemble Agents](https://arxiv.org/pdf/2310.20287)
15. [Predicting Plasticity in Deep Continual Learning: A Theoretical Perspective](https://arxiv.org/pdf/2605.09044)
16. [Barriers for Learning in an Evolving World: Mathematical Understanding of Loss of Plasticity](https://arxiv.org/pdf/2510.00304)
17. [Plasticity Loss in Deep Reinforcement Learning: A Survey](https://arxiv.org/html/2411.04832v3)
18. [Spectral Collapse Drives Loss of Plasticity in Deep Continual Learning](https://arxiv.org/pdf/2509.22335)
19. [Loss of plasticity in deep continual learning](https://www.nature.com/articles/s41586-024-07711-7)
20. [Loss of Plasticity in Deep Continual Learning Shibhansh Dohare](https://www.researchsquare.com/article/rs-3256479/v1.pdf)
21. [Maintaining Plasticity in Deep Continual Learning](http://incompleteideas.net/papers/MaintainingPlasticity.pdf)
22. [Formal Theory of Creativity and Fun and Intrinsic Motivation Explains Science, Art, Music, Humor (Juergen Schmidhuber). Artificial Scientists, Artificial Artists, Developmental Robotics, Curiosity, Attention, Surprise, Novelty, Discovery, Open-Ended Learning, Formal Theory of Beauty, Creating Novel Patters](https://people.idsia.ch/~juergen/creativity.html)
23. [Intrinsic Motivation Systems for Autonomous Mental Development - Cogprints](https://web-archive.southampton.ac.uk/cogprints.org/5473/index.html)
24. [(PDF) A Theory on Adam Instability in Large-Scale Machine Learning](https://www.researchgate.net/publication/370153049_A_Theory_on_Adam_Instability_in_Large-Scale_Machine_Learning)
25. [Don’t Just “Throw Adam at It”: Misunderstanding Adam Will Cost You](https://towardsdatascience.com/dont-just-throw-adam-at-it-misunderstanding-adam-will-cost-you/)
26. [\[PDF\] A Theory on Adam Instability in Large-Scale Machine Learning](https://www.semanticscholar.org/paper/A-Theory-on-Adam-Instability-in-Large-Scale-Machine-Molybog-Albert/88c94b11bd18161d027a28dd758b58698063e029)
27. [Beyond Quadratic Loss: The Stability Phase Diagram of Adam](https://arxiv.org/html/2609.18314)
28. [How Gradient Descent Regularizes the Sharpness of the Loss Surface Honghua Dong](https://www.cs.toronto.edu/~tianxingli/assets/csc2541-report.pdf)
29. [Understanding Edge-of-Stability Training Dynamics with a Minimalist Example](https://arxiv.org/pdf/2210.03294)
30. [Good regularity creates large learning rate implicit biases: edge of stability, balancing, and catapult](https://arxiv.org/pdf/2310.17087)
31. [(PDF) Loss of Plasticity in Deep Continual Learning](https://www.researchgate.net/publication/374017459_Loss_of_Plasticity_in_Deep_Continual_Learning)
32. [Large-Scale Study of Curiosity-Driven Learning](https://www.alphaxiv.org/abs/1808.04355)
33. [Sentinel-1 mission news](https://copernicus.gov.au/updates/sentinel-1-mission-news)
34. [S1 Mission - SentiWiki - Copernicus](https://sentiwiki.copernicus.eu/web/s1-mission)
35. [Sentinel-1B radar satellite mission comes to an end - Spatial Source](https://www.spatialsource.com.au/sentinel-1b-radar-satellite-mission-comes-to-an-end/)
36. [Programed Death Is Favored by Natural Selection in Spatial Systems — New England Complex Systems Institute](https://necsi.edu/programed-death-is-favored-by-natural-selection-in-spatial-systems)
37. <https://link.aps.org/accepted/10.1103/PhysRevLett.114.238103>
38. [arXiv:2004.12919v6 \[cs.AI\] 16 Sep 2021](https://arxiv.org/pdf/2004.12919)
39. [Motif: Intrinsic Motivation from Artificial Intelligence Feedback](https://arxiv.org/pdf/2310.00166)
40. [Can In-Context Learning Support Intrinsic Curiosity?](https://arxiv.org/pdf/2606.19476)
41. [Bootstrapping Intrinsically Motivated Learning with Human Demonstrations](https://arxiv.org/pdf/1112.1937)
42. [The Construction of Reality in an AI: A Review](https://arxiv.org/pdf/2302.05448)
43. [Intrinsic motivations and open-ended learning](https://arxiv.org/pdf/1912.13263)
44. [The Forward-Forward Algorithm: Some Preliminary Investigations Geoffrey Hinton](https://www.cs.toronto.edu/~hinton/FFA13.pdf)
45. [The Forward-Forward Algorithm: Learning Without Backpropagation](https://medium.com/@kdwaMachineLearning/the-forward-forward-algorithm-learning-without-backpropagation-4c670f1d46db)
46. [Exploring Mortal Computation - by Dr. Jordan McAfoose](https://jordanmcafoose.substack.com/p/exploring-mortal-computation)
47. [Mortal Computation: Biomimetic Intelligence](https://www.emergentmind.com/papers/2311.09589)
48. [What is the “forward-forward” algorithm, Geoffrey Hinton’s new AI technique? - TechTalks](https://bdtechtalks.com/2022/12/19/forward-forward-algorithm-geoffrey-hinton/)
49. [A-VOLVE BY (COLLECTIVE) SOMMERER / MIGNONNEAU - ADA](https://www.archive-digitalart.eu/database/general/work/a-volve.html)
50. [Life Spacies I & II](https://dam.org/museum/artists_ui/artists/sommerer-mignonneau/life-spacies-i-ii/)
51. [How Do You Care for Artificially Sentient Art?](https://www.frieze.com/article/artificially-sentient-art)
52. [Ivaylo Getov Dot Com — Ian Cheng: BOB (2019)](https://ivaylogetov.com/bob2019/)
53. [I Am Sitting in a Room](https://en.wikipedia.org/wiki/I_Am_Sitting_in_a_Room)
54. [AI models collapse when trained on recursively generated data](https://www.nature.com/articles/s41586-024-07566-y)
