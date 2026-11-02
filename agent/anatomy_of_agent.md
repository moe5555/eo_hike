# Anatomy of an Agent 

1. Agent stands on a tile. 
2. Candidates = potential tiles to move to next, neigbours within 15km. 2% chance a random tile from anywhere is added. C = # of candidates
3. Agent observes each candidate, computes 3 signals per candidate: 
   1. **e** (surprise): reconstruction error. "How badly can I draw it?" 
   2. **n** (novelty): how far its latent is from the latents of tiles already visited. "How different is it from what I've seen?"
   3. **g** (progress): how much a little practice on it would improve the network. "How much would I learn from it?" 
4. Signals are combined into one **interest score** I per candidate and picks one at random, with higher interest more likely. 
5. Agent moves to tile and trains the autoencoder on that tile. 
6. If nothing has looked interesting for a while, it gets **bored** and teleports to a random tile. 

## Components 
model.py: small custom autoencoder, the agents self grown perception 

signals.py: crop tiles, compute signals 

walk.py: execute the hike 

