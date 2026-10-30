28.10.2026 & 29.10.2026 

global_baseline_s0 & global_baseline_1k_s0
- high rate of tile revisits in quick succession 
- wondering about the geography of the walk. When do the agents jump, when do they linger in one area? Currently, they get random jumps every now and then. The jumps should only occur when the agent is bored. What happens when the agents bore quicker? 
- some of the satellite images are cropped such that sections of the image appear blank or black - all tiles should be continous. 


global_perception_1k_s0: 
- tiles are revisited 57% compared to baseline_1k_s0's 71% revisit, but that still seems quite a high number. 
- perhaps we give the agents more time to settle on tiles they find particularly novel? So far we do not have any temporality in the visits, unlike what a hike usually implies: moments of lingering, other moments of quick traversal, etc. 
- on the other hand, there is something visually interesting about running the hike.html at 16 steps/s or more, and seeing the agent returning to a tile over and over again, then moving on only to find the next tile to obsess over. Although for my narrative approach I intend to take, the stroboscopic effect wears off quickly. 

General Reflection
- What does novelty really mean here? The noisy TV problem, the cropping etc. plays into the idea, how do we make the novelty experiential? Letting the agent linger longer in places it finds particularly interesting, and shorter in ones it doesn't, is one approach. Higher revisits is another. In either case, this shouldn't be engineered away - if the agent finds a tile really interesting, then so be it. 
- How might we better understand what in the image the agent found particularly interesting? The heat maps are a scientific form of visualisation, perhaps we work with zooms, fade-ins of the colors and/or texture that were particularly interesting? Could imagine generating new images that visualise the attention in an aesthetically pleasing way and incorporate those images into the training corpus
- teleports: could they be anything other than random? 