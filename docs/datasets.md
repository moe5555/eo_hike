# Phase 0 — dataset survey

*Written 2026-09-17. Every number below was checked against the current hosting page,
the Hugging Face file API, or a direct read of the files, on that date. Where I could
not verify something I say so. Nothing larger than ~130 MB was downloaded.*

## TL;DR

| Role | Pick | Size | Chips | Why |
|---|---|---|---|---|
| **Debug** | SSL4EO-S12 v1.1, `val/S2RGB` split (+ EuroSAT-RGB as a 95 MB smoke test) | 1.5 GB | 8,704 (2,176 locations × 4 seasons) | Same file format and full metadata as the real run, so every code path (geo distance, time delta) is exercised before scaling up |
| **Real runs** | SSL4EO-S12 v1.1, `train/S2RGB`, first 15 of 477 shards | 5.2 GB | 30,720 (7,680 locations × 4 seasons) | Global, shuffled shards (so a prefix *is* a random global sample), lat/lon + acquisition timestamp + cloud cover per chip, CC-BY-4.0, and the 12-band version of the *same* chips can be fetched later |

Scale-up path without re-sampling: 30 shards → 10.4 GB → 61,440 chips.

**The one thing to decide before Phase 1:** RGB (8-bit, 3 bands, ~0.35 GB per shard) or
full multispectral (12-band Sentinel-2 L2A, int16, ~1.9 GB per shard). The brief's
budget of "30k–60k chips in about 5 GB" is only reachable with RGB: 5 GB of 12-band data
is roughly 5,500 chips. My recommendation is **start with RGB** and treat multispectral
as an upgrade for the same chip IDs, because (a) it meets the budget, (b) the sequence
images for the film are RGB anyway, (c) CLIP, the mandated contrast encoder, only takes
RGB, so the comparison is cleanest when both encoders see the same pixels, and (d) the
shards are paired across modalities, so switching later costs a download, not a redesign.
The cost is that the Earth-observation encoder must be one that accepts RGB (see §4).

---

## 1. What the constraints actually imply

Before the candidates, the arithmetic, because it rules most of them out.

- 5 GB / 30k chips ≈ 170 KB per chip; 5 GB / 60k ≈ 85 KB per chip.
- A 264×264 chip with 12 Sentinel-2 bands at 16-bit is 1.7 MB uncompressed, roughly
  0.9 MB compressed. A 120×120 12-band BigEarthNet patch is ~350 KB.
- A 264×264 8-bit RGB chip is ~200 KB raw and 60–170 KB compressed.

So the budget forces either **RGB** or **very small chips** (64 px EuroSAT, 32 px
So2Sat). For the hiker, the chip has to be large enough to *look like a place* on
screen and give a vision transformer enough 16-px patches to work with; 264 px does
that, 32 px does not. That is why the recommendation is RGB at 264 px rather than
multispectral at 64 px.

The second hard constraint is **metadata**. The sound layer wants lat/lon and a date per
chip. Table 1 shows that most classic benchmark sets lost one or both.

## 2. Comparison table

| Dataset | Chips | Px | GSD | Bands | Download | Lat/lon | Date | Sensor | Geographic spread | Licence | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **EuroSAT** RGB | 27,000 | 64 | 10 m | 3 (JPEG) | 94.7 MB (Zenodo 7711810) | no | no | S2 (implied) | 34 European countries | MIT (+ Copernicus terms) | smoke test only |
| **EuroSAT** MS | 27,000 | 64 | 10 m | 13 (L1C, GeoTIFF) | 2.1 GB | yes, from GeoTIFF bounds (to be confirmed on the files) | no | S2 | Europe only | MIT | debug for 13-band encoders |
| **BigEarthNet v2.0 (reBEN)** | 549,488 | 120 | 10 m | 12 (L2A) + S1 | 63.3 GB S2 (+54.4 GB S1), single archive | yes (metadata.parquet) | yes, Jun 2017–May 2018 | S2 L2A + S1 | 10 European countries | CDLA-Permissive-1.0 | too big, not subsettable, Europe only |
| **SSL4EO-S12 v1.0** | 251,079 loc × 4 seasons ≈ 1M | 264 | 10 m | 13 (L1C) / 12 (L2A) / 2 (S1) | ~557 GB per modality in 48 GB `tar.gz` parts | from GeoTIFF bounds | per-season timestamps | S2/S1 | global, 50 km around 10k largest cities | CC-BY-4.0 | superseded by v1.1 |
| **SSL4EO-S12 v1.1** (embed2scale) | 246,144 loc × 4 seasons = 984,576 | 264 | 10 m | S2RGB 3×uint8; S2L2A 12×int16; S2L1C; S1; NDVI; DEM; LULC | 477 shuffled shards per modality: 0.35 GB (RGB), 1.85 GB (L1C), 1.89 GB (L2A); 2.3 TB total | **yes** (parquet + inside each sample) | **yes**, per season, 2019-12 to 2021-03 | S2 (+S1) | global, 50 km around 10k largest cities | CC-BY-4.0 | **recommended** |
| **SSL4EO-L** (Landsat) | ~250k loc × 4 | 264 | 30 m | 7–11 | 300–400 GB per sensor split | from GeoTIFF | yes | Landsat 4–9 | global | CC-BY-4.0 | too big, no subset mechanism |
| **SeCo-100K** | 100k (20k loc × 5 dates) | 264 | 10 m | 12, uint8 JPEG-in-GeoTIFF | 7.3 GB single zip (Zenodo 4728033) | from GeoTIFF | in per-patch `metadata.json` (GEE properties), to confirm | S2 | global, Gaussian around 10k largest cities | CC-BY-4.0 | runner-up |
| **fMoW-Sentinel** | 882,779 | variable | 10 m | 13 (L2A composites, 90-day) | 77.5 GB single `tar.gz` (Stanford PURL) | yes (CSV) | composite window, not a date | S2 | global, 200+ countries, but only at fMoW building sites | fMoW Challenge licence + Copernicus | too big, single archive |
| **fMoW-RGB** | ~1M | variable, large | 0.3–1 m | 3 | ~200 GB+ (not re-verified) | yes | yes | DigitalGlobe | global | fMoW Challenge licence | too big; not "chipped" |
| **MMEarth100k** | 100k | 128 | 10 m | 12 S2 + S1 + 10 aux modalities | 48 GB single HDF5 | yes (tile_info.json) | yes | S2/S1 | global, stratified by biome/ecoregion | CC-BY-4.0 | attractive sampling, but 48 GB in one file |
| **Major TOM Core-S2L2A** | 2,245,886 fragments | 1068 | 10 m | 12 + cloud mask + RGB thumbnail | 23 TB; 500 rows per 4.4 GB parquet; columns fetchable remotely | yes (173 MB metadata.parquet) | yes | S2 L2A | global uniform 10 km grid incl. polar/coastal | CC-BY-SA-4.0 | future scale-up, not MVP |
| **SatlasPretrain** | 856k tiles | 512 | 10 m / 1 m | S2, NAIP, S1, Landsat | >30 TB | yes | yes | mixed | global (NAIP is US only) | ODC-BY / varies | out of scope |
| **So2Sat LCZ42** | 400,673 | 32 | 10 m | 10 S2 + 8 S1 | ~56 GB HDF5 | UTM in `*_geo.h5` | no | S2/S1 | 42 cities | CC-BY-4.0 | chips too small, urban only |

## 3. Notes per candidate

### EuroSAT
Two Zenodo files: `EuroSAT_RGB.zip` (94.7 MB, JPEG) and `EuroSAT_MS.zip` (2.1 GB,
13-band Level-1C GeoTIFF). 27,000 chips of 64×64 px in ten land-cover classes. The paper
calls the images geo-referenced, and the MS GeoTIFFs are reported to carry a CRS and
bounding box, so a centre lat/lon is recoverable from the MS version; the RGB JPEGs
carry nothing. No acquisition dates anywhere. All chips come from 34 European countries.
Licence MIT, plus Copernicus terms for the underlying imagery.
Torchgeo can download it directly (`torchgeo.datasets.EuroSAT`, mirror on Hugging Face).

Verdict: fine as a 95 MB smoke test for the pipeline (and the brief lists it), but a
debug run on it would leave the geo and time fields null and never test that code.
That is why I recommend the SSL4EO validation split as the *primary* debug set.

### BigEarthNet v2.0 ("reBEN", Zenodo 10891137, July 2024)
549,488 Sentinel-2 L2A patches of 120×120 px, 12 bands, paired with Sentinel-1; pixel
reference maps from CORINE 2018. `metadata.parquet` (4.3 MB) has per-patch coordinates,
tile and acquisition date (June 2017–May 2018). The S2 archive alone is 63.3 GB and there
is no per-patch download, so no 5 GB subset without pulling everything. Ten countries,
all European. Licence CDLA-Permissive-1.0. Rejected on size and spread.

### SSL4EO-S12 v1.0 (zhu-xlab / wangyi111 mirror)
251,079 locations × 4 seasons, 264×264 px at 10 m, sampled within 50 km of the 10,000
most populous cities. On Hugging Face each modality is a `tar.gz` split into 48 GB
parts (S2 L1C: 12 parts, 557 GB), which cannot be partially extracted, so no small
subset is possible from there. The GitHub README mentions an 8-bit compressed version
(20–50 GB per modality) on mediaTUM; that page is behind an anti-bot wall and I could
not verify it. Torchgeo's loader derives coordinates from GeoTIFF bounds. Superseded by
v1.1 for our purposes.

### SSL4EO-S12 v1.1 (embed2scale, arXiv 2503.00168) — recommended
What I verified directly:

- `train_metadata.parquet` (37 MB): 243,968 training locations across **477 tar shards,
  512 locations each** (last one 256). Columns: tar, zarr, sample_id, split, center_lon,
  center_lat, crs, bounds, geometry, four S2 timestamps, four S1 timestamps, four cloud
  cover fractions. S2 timestamps run from 2019-12 to 2021-03.
- **Shards are globally shuffled.** Shard 1 alone spans lat −38.8° to 60.3° and lon
  −123.8° to 151.4°; its latitude and longitude standard deviations (23.8°, 72.7°) match
  the whole set (24.4°, 73.9°), its share of southern-hemisphere chips (16.2%) matches
  the whole set (16.1%), and its Americas / Europe-Africa / Asia-Oceania split
  (38 / 43 / 19 %) matches the whole set (37 / 44 / 19 %). So "the first N shards" is a
  fair random global sample, no cherry-picking needed.
- One validation RGB shard (91 MB, 128 samples) opened fine: each sample is a zarr-v2
  zip with `bands (4, 3, 264, 264) uint8` (time, band, y, x), `cloud_mask (4, 264, 264)`
  with seven classes, `time (4,)` in ns since epoch, `center_lat`, `center_lon`,
  `crs`, `x`, `y`, `file_id (4,)` holding the four Sentinel-2 product IDs, and a full
  WKT CRS. That is everything the log schema needs, per chip, without any joins.
- S2RGB is derived from L2A with a per-image 2–98 % quantile contrast stretch to 0–255.
  This matters: absolute brightness is normalised away per chip, so the encoder sees
  contrast-stretched scenes. It is an *interpreted* preprocessing step and belongs in
  `docs/decisions.md`. The 12-band `S2L2A` shards keep raw int16 reflectance.
- Modalities share shard numbering and sample IDs (the "preselected" derivative on HF
  confirms "477 paired shards"), so the multispectral or SAR version of exactly the
  same chips can be added later.
- Sizes on the Hugging Face file API: S2RGB 0.346–0.351 GB per shard (166 GB total),
  S2L1C 1.84–1.87 GB, S2L2A 1.89–1.91 GB. Validation S2RGB: 5 shards, 1.53 GB, 2,176
  locations.
- Licence CC-BY-4.0. Download via `hf download embed2scale/SSL4EO-S12-v1.1 --include
  "train/S2RGB/ssl4eos12_shard_00000[1-9].tar"` style patterns; no login required.

Caveats to carry into Phase 1:

- **Sampling is city-biased.** Every location is within 50 km of a large city. The walk
  will see suburbs, farmland and coastlines more than deserts, tundra or open ocean.
  This is a property of the archive and should be stated in the film's method notes.
  MMEarth (biome-stratified) or Major TOM (uniform grid) would give a different
  character; see below.
- **Four seasons of the same place are four chips.** They are near-duplicates in
  embedding space. This is not a bug for novelty search (the second season of a visited
  place scores low and is avoided), but it means the k-nearest-neighbour candidate set
  will often be padded with a chip's own siblings. Worth a config switch
  (`seasons: all | one`) and worth watching for in the first real run; the
  `time_delta_days_from_prev` field will make sibling hops obvious.
- Clouds are already filtered to under 10 % per scene; the per-pixel cloud mask is
  available if we want to drop cloudy chips outright.

### SSL4EO-L (Landsat)
Same recipe as SSL4EO-S12 but 30 m Landsat, 264×264 px, each sensor split 300–400 GB with
no shard-level subset path exposed through torchgeo. Rejected on size; also 30 m chips of
7.9 km look more abstract than 2.6 km Sentinel chips, which may or may not suit the film.

### SeCo (Seasonal Contrast) — runner-up
`seco_100k.zip` is 7.3 GB on Zenodo (md5 in torchgeo), 100k patches = 20k locations ×
5 dates, 264×264 px, 12 bands stored as **uint8 with JPEG compression inside GeoTIFF**
(this is why it is so small: the downloader rescales intensity to 8-bit). Locations are
Gaussian-sampled around the 10k largest cities, same bias as SSL4EO. The downloader
writes a `metadata.json` per patch with the Earth Engine image properties, which should
include the acquisition time; I could not open a sample without downloading the whole
zip, so treat "dates present" as likely but unconfirmed. Torchgeo has a loader and
ResNet-50 weights pretrained on SeCo. Licence CC-BY-4.0.

Why second: single 7.3 GB zip (not subsettable, but acceptable), 5 near-duplicate dates
per location instead of 4, and metadata that has to be reconstructed from GeoTIFF bounds
plus a JSON, versus v1.1's one clean parquet. If the SSL4EO download misbehaves, this is
the fallback and needs no redesign.

### fMoW-Sentinel
Sentinel-2 L2A time series at the locations of the fMoW building-category dataset:
882,779 images, 13 bands, 90-day cloud composites, variable chip size. One 77.5 GB
`tar.gz` plus CSVs (train.csv is 179 MB) with location and category. Global, but every
chip is centred on a labelled facility (airport, dam, stadium, …), which gives the archive
a strong "things" bias. Not subsettable. Rejected on size.

### MMEarth (100k variant)
100k tiles of 128×128 px, 12 Sentinel-2 bands plus Sentinel-1, elevation, climate,
land-cover and biome layers; per-tile lat/lon and date in `tile_info.json`. Sampling is
stratified by RESOLVE ecoregions, so it is the most *geographically honest* of the
candidates: it covers deserts, tundra and rainforest in proportion to their area, not to
population. But it ships as one 48 GB HDF5 and the chips are half the size. Worth keeping
in mind as a second archive for a later "same hiker, different world" comparison; too big
for the MVP.

### Major TOM Core-S2L2A
ESA Φ-lab's global 10 km grid: 2.25 million 1068×1068 fragments in 23 TB of parquet, 500
rows per 4.4 GB file, CC-BY-SA-4.0. I read the 173 MB metadata parquet schema and one
data file's footer remotely: per row the 12 bands cost ~8.9 MB but the RGB `thumbnail`
column is a 1068×1068 PNG and can be fetched on its own by HTTP range request (the row I
sampled was Antarctic and only 18 KB; a typical land thumbnail will be around 1 MB).
So a global RGB archive *can* be assembled from thumbnails without downloading bands,
at roughly 1 MB per 10.7 km fragment, and fragments would then need tiling into chips.
This is the right raw material for a much larger, uniformly sampled archive later. It is
not "already chipped" and the engineering is not trivial, so not for the MVP.
*Update after the adapter was built:* thumbnails average 200 KB, not 1 MB, so 2,500
fragments cost ~0.5 GB; and a uniform sample of the grid is about half open ocean,
so the adapter applies a land mask by default (see `decisions.md`, finding 1).
Note also that Φ-lab publishes precomputed embeddings of Major TOM (SSL4EO, DINOv2,
SigLIP); those bypass our embed step and would not give the patch tokens Phase 2 needs.

### SatlasPretrain, So2Sat LCZ42, RESISC45 / PatternNet / Million-AID
SatlasPretrain is >30 TB. So2Sat LCZ42 has coordinates (UTM in separate `_geo.h5`
files) but 32×32 px chips from 42 cities only, no dates. RESISC45-style Google Earth
sets have no coordinates or dates at all. None fit.

## 4. Encoder implications (decision deferred to Phase 1, but the dataset fixes the options)

Torchgeo 0.10 ships these relevant weights:

- `ViTSmall16_Weights.SENTINEL2_ALL_DINO` / `_MOCO`, `ViTBase16_Weights.SENTINEL2_ALL_MAE`:
  SSL4EO-S12 pretrained, **13-band L1C input**. Matches EuroSAT-MS and SSL4EO `S2L1C`
  exactly; does not take RGB, and does not take the 12-band L2A shards without a band hack.
- `DOFABase16_Weights.DOFA_MAE` (ViT-B/16, 768-d): wavelength-conditioned, accepts any
  band subset including RGB, trained on satellite data across sensors. **This is the
  natural EO encoder for the RGB recommendation** and, being a ViT, gives per-patch
  tokens for the Phase 2 heatmap.
- `ResNet50_Weights.SENTINEL2_RGB_SECO` / `SENTINEL2_RGB_MOCO`: RGB Sentinel-2, but a
  CNN, so no patch tokens.
- Copernicus-FM and Panopticon (ViT-B/14) also accept flexible bands; candidates if
  DOFA disappoints.
- OpenAI CLIP ViT-B/32 (RGB only) as the mandated contrast encoder.

So: RGB archive → DOFA vs CLIP; multispectral archive → SSL4EO ViT-S/16 vs CLIP-on-RGB-
composite. The first comparison is cleaner because both models see identical pixels.

## 5. Proposed download plan (waiting for approval)

| Step | Files | Size |
|---|---|---|
| Debug | `val/S2RGB/*.tar` (5 shards) + `val_metadata.parquet` | 1.5 GB |
| Smoke | `EuroSAT_RGB.zip` | 95 MB |
| Real | `train/S2RGB/ssl4eos12_shard_000001..000015.tar` + `train_metadata.parquet` | 5.2 GB |
| Optional later | same 15 shard numbers under `train/S2L2A/` | 28 GB |

Local machine: RTX 4070 Laptop 8 GB, 32 GB RAM, 384 GB free. Python 3.14 is the only
system interpreter; `uv` 0.12 is installed and can pin 3.12 for the project (torch and
faiss-cpu wheels for 3.14 are not something I want to depend on). Embedding 30k chips
with a ViT-B on this GPU is minutes, not hours.

## 6. Open questions for you

1. RGB now, multispectral later (my recommendation), or multispectral from the start
   at ~28 GB for 30k chips?
2. Keep all four seasons as separate chips (my default, with a config switch), or one
   season per location for the first real run?
3. Are you comfortable with the city-biased sampling for the thesis's framing, or should
   MMEarth's biome-stratified archive be planned as a second world from the start?

## Sources

- EuroSAT: https://github.com/phelber/eurosat · https://zenodo.org/records/7711810
- BigEarthNet v2 / reBEN: https://zenodo.org/records/10891137 · https://arxiv.org/abs/2407.03653 · https://bigearth.net/
- SSL4EO-S12 v1.0: https://github.com/zhu-xlab/SSL4EO-S12 · https://huggingface.co/datasets/wangyi111/SSL4EO-S12 · torchgeo `datasets/ssl4eo.py`
- SSL4EO-S12 v1.1: https://huggingface.co/datasets/embed2scale/SSL4EO-S12-v1.1 · https://arxiv.org/abs/2503.00168 · https://github.com/DLR-MF-DAS/SSL4EO-S12-v1.1 · https://huggingface.co/datasets/moham741/SSL4EO-S12-v1.1-preselected
- SSL4EO-L: https://huggingface.co/datasets/torchgeo/ssl4eo_l · https://arxiv.org/abs/2306.09424
- SeCo: https://zenodo.org/records/4728033 · https://github.com/ServiceNow/seasonal-contrast · torchgeo `datasets/seco.py`
- fMoW-Sentinel: https://purl.stanford.edu/vg497cb6002 · https://github.com/sustainlab-group/SatMAE
- MMEarth: https://github.com/vishalned/MMEarth-data · https://arxiv.org/abs/2405.02771
- Major TOM: https://huggingface.co/datasets/Major-TOM/Core-S2L2A · https://github.com/ESA-PhiLab/Major-TOM · https://arxiv.org/abs/2412.05600
- SatlasPretrain: https://github.com/allenai/satlas/blob/main/SatlasPretrain.md
- So2Sat LCZ42: https://github.com/zhu-xlab/So2Sat-LCZ42 · https://arxiv.org/abs/1912.12171
- Torchgeo pretrained weights: https://docs.torchgeo.org/en/stable/api/models.html
