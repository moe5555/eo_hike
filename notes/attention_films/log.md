# Attention films: log

Where does a walker look inside a tile it found novel, and in what order? Turned into a Ken Burns film: an establishing shot of the whole tile, then the camera moves from look to look at the walker's scale of attention, then pulls out. Follows main's per-patch novelty heat maps (`src/hiker/heatmap.py` on `main`): the agent's own score at a finer grain, not a post-hoc attribution.

## The walker has no gaze

At each step it scores a candidate tile on K = 16 crops of 64 px (2.6 km) at once, random or fixed by tile id (`score_crops: fixed`), and averages them. So *where* can be measured, and *in what order* has to be constructed. `analysis/attention.py` scores every 64 px window of the tile (stride 8 px, 25 × 25 windows) with the walker's model and memory at that step and the walk's own signals (e, n, g, and I with the walk's weights), then orders the looks one of three ways:

| `--order` | Looks | How literal |
|---|---|---|
| `glances` | the 16 crops the walker actually scored, hottest first (fixed-crop runs only) | where it looked; the order is by score |
| `peaks` | local maxima of the map, hottest first, at least 32 px apart | where it would look; order by score |
| `learn` | take the hottest window, train on it as the walker trains on a tile (4 Adam steps on 16 jittered crops + 48 replay), rescore, repeat | an order that comes from the walker's own learning; a return to an earlier look is marked |

Shotlist → film: `analysis/kenburns.py` renders the shotlist from the tile's 1068 px 10 m thumbnail (eased moves, log-space zoom with a pull-back on long pans, slight push-in during holds). `--heat` overlays the map the camera follows (in `learn`: the map before each look), `--hud` adds captions and the walker's field of view. The shotlist is JSON and can be edited by hand (order, holds, framing) before rendering.

## Decisions

- **Novelty against a crop bank**, not the walker's archive: the archive holds tile means (mean of 16 crop latents), and one crop isn't comparable with a mean. The bank is K crops of every tile visited before the step (the walk's fixed crops if it used them), as main used a patch bank.
- **The bank is kept as pixels and re-encoded by whichever model scores.** The first version stored latents; after one `learn` look the model had moved, every window drifted away from every stored latent and a large block of the tile lit up as "new". That is mechanism 2 of `notes/dreams_v3/reflection_revisits.md` (stale archive latents) in miniature, and it produced false returns. With re-encoding and replay, the gaze moves across the tile.
- **Model snapshot:** the latest checkpoint at or before the step (`ckpt_<c>.pt` is the model used at step c, `bored_<b>.pt` the model used at step b + 1). Walks save every 250 steps, so the model can be up to 249 steps older than the step; the gap is in the shotlist. For exact maps, walk with a smaller `ckpt_every`.
- **Progress per window** trains and measures on the same window (the walk splits a tile's 16 crops into halves A and B).
- **Heat colour scale** per map, 75th to 99th percentile, fading out past the outermost window centres.

## Runs

| Tile | Run, step | Orders | Notes |
|---|---|---|---|
| 356415, steppe and village, 54.66° N 51.57° E | `global_perception_1k_s0`, step 508 (highest novelty z of any first visit, 6.8) | learn, peaks, glances | model `ckpt_0500.pt` (8 steps older); learn: 6 looks, 1 near-return; ~40 s per shotlist, ~20 s per 40 s film at 1080 px on the Mac |

Outputs in `runs/<run>/attention/step_<step>_<order>/`: `shotlist.json`, `maps.npz`, `preview.png`, `film.mp4`.
