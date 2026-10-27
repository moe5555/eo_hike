<!-- instructions: narration/inst_narration_1.md · input: narration/out/inst_narration_1_input.md (run baseline_s0) · 2026-10-26 -->

# ANALYSIS

1. **Away from cropland, toward grassland and water.** Cropland is 19.2 % of the region's tiles and 18.2 % of the random walk's steps, but only 3.7 % of this agent's steps. Over-represented: grassland 26.9 % (region 15.7 %, random 10.3 %), permanent water 16.6 % (9.4 %, 12.6 %), open sea 3.4 % (2.7 %, 1.0 %) and snow and ice 3.5 % (2.0 %, 1.6 %). 51 % of its steps lie north of 45.8° N, against 34 % for the random walk.
2. **It dwells and returns.** It visits 434 unique tiles where the random walk visits 555. 29 % of its moves go back to the tile of two steps earlier (random: 16 %), and 38 % of its steps fall on its 35 most-visited tiles (random: 19 %). Three of the five most-visited tiles are sea tiles off San Remo, Riva Ligure and San Lorenzo al Mare, with 31–33 visits each, inside one unbroken 101-step stretch on water (steps 203–303). The last visits there have low or negative novelty (−0.23, −1.15) but positive learning progress (+0.77). With w_g = 1, learning progress keeps the returns going after novelty is spent.
3. **Boredom is front-loaded.** Four of the five boredom events fall in the first 110 steps (31, 89, 99, 109). The fifth is at step 623, and none occur in the last 876 steps. Even the best candidate scored below zero on 10 % of steps, but boredom is an average with a long memory: those steps have to come in a run to push it past patience 0.6, and after step 109 they did so only once. Novelty is negative at every boredom event (−0.30 to −1.23).
4. **The noise tiles produce surprise but do not steer the walk.** The agent spends 16 steps on the synthetic noise tiles (1.1 % of steps; random walk 0.1 %). 13 of them fall in one early episode, steps 11–31, which ends with the first boredom event. At steps 1035–1038 the noise tiles produce the two highest surprise scores of the walk (+5.37, +4.84). The total score stays near zero (+0.06, −0.06) because surprise has weight 0 in this temperament, and no noise tile follows step 1039.
5. **Cloud cover plays no part.** Mean cloud cover on the path is 1.37 %, against 1.36 % for the random walk and 1.2 % for the region. The cloudiest tiles in the events (Gallio 18.4 %, Mezzoldo 21.0 %, sea off Ospedaletti 23.6 %) score positive and negative alike.

# NARRATION — field naturalist observing an unfamiliar species

**0.** The specimen leaves the Milan start tile for Caronno Pertusella, built-up land, with surprise +1.48 and learning progress +1.49. Novelty registers 0.00.

**1.** It moves 13 km to tree cover at Locate Varesino, a tile scoring +0.05 when the best candidate offered +0.72. The highest score is not always the one taken.

**3.** At Rovellasca, tree cover, learning progress reaches +3.55.

**4.** At Varedo, built-up, learning progress +4.04 and novelty +2.92 combine into a score of +6.96, the highest recorded on the walk.

**10.** First cropland, at Arborio, taken at +0.45 against a best of +1.26.

**11.** The specimen enters the noise cluster at Oldenico, where every look returns fresh random pixels. Surprise +1.75, novelty −0.42, learning progress −0.08. It stays among noise tiles for 13 of the next 21 steps.

**31.** Second visit to the noise tile at Casaleggio Novara; the best candidate scores −0.86. Boredom, at 0.57 before the step, passes patience for the first time.

**32.** A teleport of 202 km sets it down on permanent water at Vallecrosia, Liguria. Novelty, surprise and learning progress are all negative on arrival.

**41.** Fourth visit to the sea 24 km from San Remo: novelty +4.77.

**42.** Third visit to the sea 16 km from Riva Ligure: novelty +4.78. In this species, repeat visits can still register as novel.

**46.** A long jump of 390 km is taken to tree cover 6 km from Gallio, Veneto, under 18.4 % cloud. Novelty +2.77.

**48.** Back on the Gallio tile for a second visit: learning progress +3.70, surprise +3.05, score +4.35.

**72.** First grassland, 10 km from Canazei. Boredom has climbed to 0.31.

**89.** At Vidor, grassland, novelty is −0.75 and the best candidate −1.03. Boredom passes patience a second time.

**90.** Teleport, 203 km, to tree cover at Verderio Superiore. The scores remain negative.

**98.** A long jump of 100 km to cropland at Lungavilla is taken at a score of −1.21.

**99.** One step later, at Sommo, cropland, boredom passes patience again.

**100.** Teleport, 122 km, to tree cover at Osiglia, Liguria.

**109.** Ormea, tree cover: the fourth boredom event, the third within twenty steps.

**110.** Teleport, 52 km, to the sea 12 km from Ospedaletti, a tile it has visited once before, under 23.6 % cloud. Learning progress, +0.23, is the only positive score.

**124.** First open sea, 49 km from Cervo, at novelty +1.01.

**203.** On its 21st visit to the sea 30 km from San Lorenzo al Mare, the specimen begins 101 unbroken steps on permanent water.

**299.** Last of 33 visits to the sea off Riva Ligure. Novelty is down to −0.23; learning progress holds at +0.77.

**300.** Last of 31 visits to the sea off San Remo, with novelty −1.15 and learning progress +0.77. The water stretch ends three steps later.

**314.** Fourth visit to grassland 6 km from Limone Piemonte. All three readings are high: novelty +2.94, surprise +3.84, learning progress +3.28, score +6.22.

**323.** Grassland 10 km from Saint-Martin-Vésubie, across the French border: surprise +4.73, learning progress +0.11.

**341.** First visit to Bersezio, grassland: novelty +5.49, the highest of the walk.

**352.** First bare and sparse vegetation, 12 km from Pleyne.

**424.** A long jump of 191 km to cropland at Silvano Pietra, taken at −0.06.

**459.** A long jump of 258 km returns it to grassland at Prali for a sixth visit; score +1.65.

**623.** At Casalborgone, tree cover, novelty −1.23. Boredom passes patience for the fifth and last time.

**624.** Teleport, 202 km, to snow and ice 8 km from Silvaplana, Grisons: novelty +1.13, learning progress −2.62.

**733.** At Mezzoldo, tree cover under 21.0 % cloud, it begins 74 unbroken steps on tree cover, lasting to step 806.

**1035.** Third visit to the noise tile at Casaleggio Novara: surprise +5.37, the highest of the walk. Novelty −0.76 leaves the score at +0.06.

**1038.** Second visit to the noise tile at Oldenico: surprise +4.84, score −0.06. After step 1039 the specimen is not recorded on a noise tile again.

**1250.** Last of 32 visits to Cevio, Ticino, tree cover.

**1411.** A long jump of 360 km to the sea 38 km from Marina di Pisa, taken at +0.17 when the best candidate offered +0.97. A 46-step stretch on water follows.

**1478.** Second visit to open sea 59 km from Portofino: novelty +4.77, score +6.33.

**1499.** Final observation: open sea 52 km from Deiva Marina, third visit. Memory error on the probe tiles stands at 0.0045, down from 0.0652 at the start.

# NARRATION — ship's log

**0.** Departed Milan start tile. Caronno Pertusella, built-up. Surprise +1.48, learning progress +1.49, novelty 0.00.

**1.** 13 km to Locate Varesino, tree cover. Score +0.05; best on offer +0.72.

**3.** Rovellasca, tree cover. Learning progress +3.55.

**4.** Varedo, built-up. Learning progress +4.04, novelty +2.92, score +6.96, highest of the voyage.

**10.** Arborio. First cropland. Score +0.45.

**11.** Entered the noise cluster at Oldenico; fresh random pixels on every look. Surprise +1.75, novelty −0.42, learning progress −0.08.

**31.** Casaleggio Novara, noise tile, second call. Best candidate −0.86. Boredom 0.57, over patience; teleport ordered.

**32.** Teleported 202 km. Vallecrosia, permanent water. All readings negative.

**41.** Sea 24 km from San Remo, fourth call. Novelty +4.77.

**42.** Sea 16 km from Riva Ligure, third call. Novelty +4.78.

**46.** Long jump, 390 km. 6 km from Gallio, Veneto, tree cover, cloud 18.4 %. Novelty +2.77.

**48.** Gallio, second call. Learning progress +3.70, surprise +3.05, score +4.35.

**72.** 10 km from Canazei. First grassland. Boredom 0.31.

**89.** Vidor, grassland. Novelty −0.75, best candidate −1.03. Boredom over patience.

**90.** Teleported 203 km. Verderio Superiore, tree cover. Readings negative.

**98.** Long jump, 100 km. Lungavilla, cropland. Taken at −1.21.

**99.** Sommo, cropland. Boredom over patience.

**100.** Teleported 122 km. Osiglia, Liguria, tree cover.

**109.** Ormea, tree cover. Boredom over patience, third time in twenty steps.

**110.** Teleported 52 km. Sea 12 km from Ospedaletti, second call, cloud 23.6 %. Learning progress +0.23, all else negative.

**124.** Open sea, 49 km from Cervo. First open sea. Novelty +1.01.

**203.** Sea 30 km from San Lorenzo al Mare, 21st call. Begin 101 consecutive steps on permanent water.

**299.** Sea off Riva Ligure, 33rd and last call. Novelty −0.23, learning progress +0.77.

**300.** Sea off San Remo, 31st and last call. Novelty −1.15, learning progress +0.77. Left the water at step 304.

**314.** 6 km from Limone Piemonte, grassland, fourth call. Novelty +2.94, surprise +3.84, learning progress +3.28. Score +6.22.

**323.** 10 km from Saint-Martin-Vésubie, France, grassland. Surprise +4.73.

**341.** Bersezio, grassland, first call. Novelty +5.49, highest of the voyage.

**352.** 12 km from Pleyne. First bare and sparse vegetation.

**424.** Long jump, 191 km. Silvano Pietra, cropland. Taken at −0.06.

**459.** Long jump, 258 km. Prali, grassland, sixth call. Score +1.65.

**623.** Casalborgone, tree cover. Novelty −1.23. Boredom over patience, fifth and last time.

**624.** Teleported 202 km. 8 km from Silvaplana, Grisons. First snow and ice. Novelty +1.13, learning progress −2.62.

**733.** Mezzoldo, tree cover, cloud 21.0 %. Begin 74 consecutive steps on tree cover, to step 806.

**1035.** Casaleggio Novara, noise tile, third call. Surprise +5.37, highest of the voyage. Novelty −0.76. Score +0.06.

**1038.** Oldenico, noise tile, second call. Surprise +4.84, score −0.06. Last noise tile at step 1039.

**1250.** Cevio, Ticino, tree cover. 32nd and last call.

**1411.** Long jump, 360 km. Sea 38 km from Marina di Pisa. Taken at +0.17; best on offer +0.97. 46 steps on water follow.

**1478.** Open sea 59 km from Portofino, second call. Novelty +4.77, score +6.33.

**1499.** Open sea 52 km from Deiva Marina, third call. End of log. Memory error 0.0045, from 0.0652 at departure.

# NARRATION — incident report

**0.** Unit departed the Milan start tile for Caronno Pertusella (built-up). Readings at first contact: surprise +1.48, learning progress +1.49, novelty 0.00.

**1.** Unit moved 13 km to Locate Varesino (tree cover) at a score of +0.05, below the best available candidate (+0.72). No fault: selection is probabilistic.

**3.** Learning-progress reading of +3.55 at Rovellasca (tree cover).

**4.** Peak score of the operation, +6.96, at Varedo (built-up). Contributing readings: learning progress +4.04, novelty +2.92.

**10.** First contact with cropland, at Arborio. Score +0.45.

**11.** Unit entered the synthetic noise cluster at Oldenico, where every look returns fresh random pixels. Surprise +1.75; novelty −0.42; learning progress −0.08. The unit logged 13 noise-tile steps before step 31.

**31.** Boredom incident #1 at Casaleggio Novara (noise tile, second visit). Boredom stood at 0.57 before the step and passed the patience threshold of 0.6; best available score −0.86.

**32.** Response to incident #1: teleport of 202 km to Vallecrosia (permanent water). All post-arrival readings negative.

**41.** Novelty reading of +4.77 on the fourth visit to the sea 24 km from San Remo.

**42.** Novelty reading of +4.78 on the third visit to the sea 16 km from Riva Ligure.

**46.** Long-jump candidate accepted: 390 km to tree cover 6 km from Gallio (Veneto), cloud 18.4 %. Novelty +2.77.

**48.** Second visit to the Gallio tile. Learning progress +3.70, surprise +3.05, score +4.35.

**72.** First contact with grassland, 10 km from Canazei. Boredom at 0.31.

**89.** Boredom incident #2 at Vidor (grassland). Novelty −0.75; best available −1.03.

**90.** Response: teleport of 203 km to Verderio Superiore (tree cover). Readings remained negative.

**98.** Long-jump candidate accepted at a negative score (−1.21): 100 km to Lungavilla (cropland).

**99.** Boredom incident #3 at Sommo (cropland), one step after the long jump.

**100.** Response: teleport of 122 km to Osiglia (tree cover).

**109.** Boredom incident #4 at Ormea (tree cover), the third in twenty steps.

**110.** Response: teleport of 52 km to the sea 12 km from Ospedaletti (second visit, cloud 23.6 %). Learning progress +0.23 was the only positive reading.

**124.** First contact with open sea, 49 km from Cervo. Novelty +1.01.

**203.** Extended stay began at the sea 30 km from San Lorenzo al Mare (21st visit): 101 consecutive steps on permanent water, ending at step 303.

**299.** Final visit, the 33rd, to the sea off Riva Ligure. Novelty −0.23; learning progress +0.77 still positive.

**300.** Final visit, the 31st, to the sea off San Remo. Novelty −1.15; learning progress +0.77.

**314.** Combined high readings on the fourth visit to grassland 6 km from Limone Piemonte: novelty +2.94, surprise +3.84, learning progress +3.28; score +6.22.

**323.** Surprise reading of +4.73 on grassland 10 km from Saint-Martin-Vésubie, France.

**341.** Peak novelty of the operation, +5.49, on the first visit to Bersezio (grassland).

**352.** First contact with bare and sparse vegetation, 12 km from Pleyne.

**424.** Long-jump candidate accepted at −0.06: 191 km to Silvano Pietra (cropland).

**459.** Long-jump candidate accepted: 258 km to Prali (grassland), sixth visit; score +1.65.

**623.** Boredom incident #5 at Casalborgone (tree cover), novelty −1.23. No further boredom incidents were recorded.

**624.** Response: teleport of 202 km to snow and ice 8 km from Silvaplana (Grisons), first contact with this land cover. Novelty +1.13; learning progress −2.62.

**733.** Extended stay began at Mezzoldo (tree cover, cloud 21.0 %): 74 consecutive steps on tree cover, ending at step 806.

**1035.** Peak surprise of the operation, +5.37, on the third visit to the noise tile at Casaleggio Novara. Score stayed at +0.06 (novelty −0.76; surprise carries weight 0).

**1038.** Surprise of +4.84 at the noise tile at Oldenico; score −0.06. The last noise-tile contact was recorded at step 1039.

**1250.** Final visit, the 32nd, to Cevio (Ticino, tree cover).

**1411.** Long-jump candidate accepted at +0.17, below the best available (+0.97): 360 km to the sea 38 km from Marina di Pisa. A 46-step stay on water followed.

**1478.** Novelty of +4.77 on the second visit to open sea 59 km from Portofino; score +6.33.

**1499.** Operation ended on open sea 52 km from Deiva Marina (third visit). Memory error on the probe tiles was 0.0045, down from 0.0652 at step 0.

# NARRATION — poetic log

**0.** The walk begins by leaving Milan, and its opening ground is Caronno Pertusella, built-up. Surprise from the outset, and learning progress with it; of novelty, as yet, nothing.

**1.** Thirteen kilometres, into tree cover at Locate Varesino: not the strongest pull on offer, but the one followed.

**3.** Rovellasca, tree cover, and learning progress rising, the way a path rises once it has begun to climb.

**4.** Varedo, built-up. Novelty and learning progress arrive together, and the highest score of the whole walk is reached almost before the walk has begun.

**10.** Arborio, and cropland enters the record.

**11.** Oldenico, and then a run of ground that is not ground at all: tiles where every look returns fresh random pixels. Surprise swells; novelty and learning progress sink below the ordinary and stay there.

**31.** Casaleggio Novara, the noise once more. Nothing within reach scores well, and boredom, which has been gathering like water behind a weir, passes patience.

**32.** Then the leap: two hundred and two kilometres, at random, to permanent water at Vallecrosia. Every score falls short.

**41.** The sea twenty-four kilometres from San Remo, returned to, and novelty running high. Return does not wear this place smooth.

**42.** The sea sixteen kilometres from Riva Ligure, returned to, and novelty high again.

**46.** Then a door opens three hundred and ninety kilometres off, a far tile slipped in among the near ones, and the walk goes through it into tree cover near Gallio, under cloud. Novelty high on the far side.

**48.** Gallio again, and the tile gives back learning progress and surprise, both high.

**72.** Grassland at last, ten kilometres from Canazei. Boredom has begun to rise, slow as a tide.

**89.** Vidor, grassland. Nothing nearby scores well; boredom crosses patience once more.

**90.** Two hundred and three kilometres, at random, to tree cover at Verderio Superiore, and still the scores fall short.

**98.** A hundred kilometres to Lungavilla, cropland: a far tile taken though it scores poorly.

**99.** Sommo, cropland, and boredom again.

**100.** A hundred and twenty-two kilometres, at random, to Osiglia, tree cover.

**109.** Ormea, tree cover. Boredom again, close on the heels of the last; the early walk is a stutter of leavings.

**110.** Fifty-two kilometres, at random, to the sea off Ospedaletti, under cloud, a tile returned to. Only learning progress lifts.

**124.** Open sea, forty-nine kilometres from Cervo, out past the edge of the land-cover map. Novelty, a little.

**203.** The sea off San Lorenzo al Mare, returned to so often now that return has become the walk. Then water, long and unbroken, crossed and recrossed.

**299.** The sea off Riva Ligure, for the last time. Novelty has worn away, but learning progress still holds above, like a light left on.

**300.** The sea off San Remo, for the last time: novelty lower still, learning progress holding. A few steps on, the water gives out.

**314.** Near Limone Piemonte, grassland, returned to, and everything at once: novelty, surprise, learning progress, all high, and the score among the highest of the walk.

**323.** Ten kilometres from Saint-Martin-Vésubie, the nearest name now a French one: surprise, high.

**341.** Bersezio, grassland, never walked before, and here the most novelty of the whole walk.

**352.** Twelve kilometres from Pleyne, a new term enters the record, spare as what it names: bare and sparse vegetation.

**424.** A hundred and ninety-one kilometres to Silvano Pietra, cropland, on a score of almost nothing.

**459.** Two hundred and fifty-eight kilometres, and the far door opens onto a place already in memory: Prali, grassland, once more.

**623.** Casalborgone, tree cover, novelty low. Boredom, for the last time; after this the walk never again runs dry.

**624.** Two hundred and two kilometres, at random, to eight kilometres from Silvaplana, and snow and ice enters the record. Novelty up; learning progress far below.

**733.** Mezzoldo, tree cover, under cloud, and a long stretch begins: tree cover after tree cover, unbroken.

**1035.** Casaleggio Novara again, where every look is fresh random pixels. The most surprise of the whole walk wells up here, and counts for next to nothing.

**1038.** Oldenico: surprise high again, the score empty. Soon after, the noise is left behind for good.

**1250.** Cevio, tree cover, for the last time, after many returns.

**1411.** Three hundred and sixty kilometres to the sea thirty-eight kilometres from Marina di Pisa, a far tile taken over a better score on offer. Then water again, a long stretch of it.

**1478.** Open sea fifty-nine kilometres off Portofino, returned to: novelty high, and the score rising with it to among the highest of the walk.

**1499.** Open sea fifty-two kilometres from Deiva Marina, returned to, and here the walk ends, out past the edge of the land-cover map. Memory carries far less error than it did at the start.
