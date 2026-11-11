# Changelog

Newest entry first. Each entry: date, what changed, why this approach, what you expect.

## 2026-11-11: research, a world made of the whole Landsat 1 mission

- **What changed.**
  - Research note `notes/11_landsat1_mission/research.md`: sources, a census of the mission, a probe of its quirks, and what changes for the setup.
  - New scripts: `analysis/landsat1/census.py` (every Landsat 1 STAC item on Planetary Computer, metadata and footprints only, and land coverage on a 0.25° grid) and `analysis/landsat1/quirk_probe.py` (56 image windows: cloud, fill, dropped-pixel and saturation flags, stripes, DN levels).
  - The census table `data/landsat/landsat1_c2l1_items.parquet` (24 MB) is force-added on branch `landsat-1`, since `data/` is ignored. The coverage grid is not committed: `census.py coverage` rebuilds it from the table. The coverage map and probe table are in the note's folder. Nothing built, nothing walked.
  - Rendered tiles with their quirks and a resolution comparison over Paris (`analysis/landsat1/render_quirks.py`, `figures/quirks_sheet.png`, `resolution_paris.png`, `offset_paris.png`). In an L1GS scene Paris is drawn 21.7 km from where it is.
  - A discarded attempt the same day (a multispectral eye on a Major TOM block) left no files.
- **Why this approach.** No ready-made aggregate exists, so the world would be built from the catalogue. Counting the catalogue first shows what any selection rule would produce. Moe's interest is the quirks, so the probe measures how far the QA bands record them. They do so badly: line defects go unflagged, saturation flags disagree with the pixels, and the cloud mask is binary.
- **What I expect.** If Moe chooses Landsat 1, the world reopens the decision of 2026-11-11 and changes milestone 1. The first build steps are the Major TOM grid, a selection rule, a lazy store over COG windows (about 0.37 MB a cell), and quirk columns per cell. The walker stays as it is.
