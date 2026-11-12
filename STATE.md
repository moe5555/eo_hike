Rewritten by Claude Code at the end of every cycle. Last update: 2026-11-12.

# Where we are, in thesis terms
## RQ1:
How do practices of moving without a predetermined destination, like wayfaring or the dérive, translate to an untasked, step-wise traversal of the planetary image, already cut into scenes, scan lines and tiles?

- The world is now the archive of one instrument: Landsat 1's whole mission on the Major TOM grid (1,466,863 cells). Each cell is a stack of acquisitions; a revisit moves one acquisition later in time. Moving through the image is now also moving through the archive's dates.
- The walk begins where the archive begins: the first scene, a night pass over South Dakota, 25 Jul 1972 (authored). That origin shapes the first 100 steps: the two-eye walkers escape the night by revisiting cells, the one way to a daylight image nearby (e12, finding 6).
- After that the walkers mostly move on to new cells; they live in the satellite's first months (mean acquisition year 1972.0–1972.1) and, at 1,000 steps, mostly in North America.

## RQ2:
Which paths do algorithms driven by novelty, learning progress and boredom cut through the computational planetary image, and how much of their attention follows the terrain, how much the idiosyncrasies of their perception, and how much the artefacts of the instrument, where data and phenomenon come apart?

- Walker v2 splits perception into a glance at the whole tile and a grid of details, and logs how much each made every choice (e12). The two are separable: with equal weights the glance carries ~40 % of interest at the choice, the grid ~37 %, progress ~23 %.
- Terrain: every curious walker prefers clear, dark tiles (hints against the Null for all seven conditions). An apparent preference for a cell's earlier acquisitions is mostly place memory (unvisited cells are rank 0); with memory held fixed, v1 leans to earlier dates and the two-eye walker to later ones among fresh cells: no shared taste for date.
- Perception: what reaches the choice depends on the eye. One crop deciding (top-1) makes the grid chase stripes; the glance does not.
- The instrument: stripes, saturation, black fill and night are measured per tile and per crop, never shown. Stripes draw the detail-eye; fill draws at tile level (and drew the glance to the pass's black edges); night, which is a red detector field (nir08 ~209 DN with no sun), is fled by every two-eye walker. The death dry run splits the same way: max-grid surprise fires on artefacts (86 %), glance surprise on weather (100 % cloud or bright).
- All of this is two seeds per condition: hints, not leads.

## RQ3:
What do GANs trained recursively on these paths construct, and do their worlds drift across generations towards the planet or towards the apparatus?

- Not started. The logs now support the planned conditions: tile weights from pooled novelty at the visit, top crops per step for a "curious collage", and per-image quirk shares for reading drift towards the apparatus.

# Decisions taken since the last update, and why
- **World: the whole Landsat 1 mission** (Moe, 2026-11-12), not one pass and not Major TOM. The single pass forced every long step along a 185 km strip and onto its edge.
- **Selection: a stack per cell**, earliest first, each revisit the next acquisition (one per day); a cell whose stack has run out is no longer offered (Moe).
- **All processing levels, night scenes in, interior missing data kept**; no full-tile rule for now (Moe).
- **Start: the archive's first scene** (night, South Dakota, cell `479U_839L`) (Moe, after checking that Dallas's "first light" image is the sixth scene of the first daylight pass).
- **Eye: CIR, sqrt tone, one global stretch** from 2,000 random cells (the brief). The e10 256 px pass was rebuilt in sqrt tone as the test bed.
- **Walker v2's defaults** as the brief proposed, with one change: the top-k training crops are cycled to 16, so pooling does not change how much the walker learns per step.
- **Reproducibility:** walks are bit-identical only at the same thread count; `meta.json` records it.

# Waiting for Moe
- Keep the night start, or start in daylight? It shapes the first 100 steps of every walk.
- Which surprise source the death rule uses: max grid (death by the apparatus) or glance (death by weather).
- Whether the nir08 night signal should be looked into (what it is), or left as material.
- The full-tile rule: deferred; fill is tracked in the readouts.

# Backlog, in order
1. A size cap with LRU eviction for the Landsat 1 cache (18 walks filled 16 GB; 14 GB free on the Mac).
2. Seeds 2–3 for the mission factorial's key conditions (Null, v1, two eyes top-4, grid top-1), so hints can become leads.
3. Build the death rule (after Moe's choice of source) and the replication milestone: 4 seeds plus a long Null on this world, with the Tobler and cluster readouts.
4. A Landsat dataset builder for the GAN (gen/v3_datasets.py assumes Major TOM at 10 m), on the PC.
5. Open checks of the research note (missing ~14k items, L1GS offset distribution, memory effect, impulse noise, 6-bit combs).

# Next milestone and its risk
- **Replication in the final world:** 4 seeds plus a long Null, with the death rule and the Tobler and cluster readouts.
- **Risks:**
  - Disk: the Mac's cache will not hold long walks without a cap, so long walks may need the PC.
  - The death rule's source is still open.
  - Two of the defining behaviours (the night escape, the stay in North America) are set by the authored start. Every finding has to keep them apart from what the walker brings.
