# Enlarging GAN and package tiles for viewing

*2026-11-15. Asked by Moe: is 128 px the final resolution, and can the images be enlarged faithfully to the material? Tool: `scripts/upscale_faithful.py`.*

## The resolution chain (all set by hand)

| stage | size | ground per pixel | how |
|---|---|---|---|
| archive window (Landsat 1 MSS, C2 L1) | 178 × 178 | 60 m (the archive's grid; the MSS sensor itself resolves about 80 m) | as stored, not resampled (`data/landsat1_world.py`) |
| walker's tile (what both eyes see) | 256 × 256 | 41.7 m | bilinear 178 → 256 (`data/landsat1_store.py`) |
| package tile = GAN training image | 128 × 128 | 83.4 m | area average 2 × 2 (PIL BOX) of the 256 px tile (`scripts/g1_package.py`) |
| GAN sample (G1) | 128 × 128 | 83.4 m | StyleGAN2-ADA, cfg auto at 128 px (`notes/brief_gan_g1.md`) |

- **128 px is the GANs' final resolution.** It is fixed by the architecture, and further training sharpens the images but does not add pixels.
- **A higher-resolution GAN would need retraining.** Training at 256 px would mean a different, several times slower run. Its extra pixels would come from the walker's bilinear enlargement, not from the instrument. The archive holds no detail beyond its 178 px window, which is 1.39× the GAN's resolution.

## Faithful enlargement

- **Default: nearest neighbour by an integer factor** (8× gives 1,024 px).
  - Each GAN pixel becomes a solid block standing for 83.4 m of ground.
  - Nothing is invented or smoothed. Stripes, fill edges, saturation and the 1977 yellow (the black green channel) keep their exact values.
  - This is the faithful one. The enlarged image is a different display of the same 128 × 128 values.
- **Optional: Lanczos, labelled "lanczos".**
  - It interpolates between existing values. It creates no new structure, but it creates new in-between values and slight ringing at hard edges.
  - For display only, never for measurement.
- **Not used: generic learned super-resolution** (ESRGAN and similar).
  - It paints in texture learned from modern photographs. That brings another apparatus into the image and would "repair" stripes and fill, against the project rule that artefacts stay material.
- **Possible later, Moe's decision: super-resolution trained on this archive alone.**
  - Pairs would be the real 178 px windows and their 128 px renders.
  - It could at most restore the archive's own grid (1.39×) and would learn MSS-specific texture.
  - It is a new trained model, so a new experiment with its own control.

Every enlarged PNG records its method, factor and source pixel size in a text chunk named `upscale` and in its file name (`_x8_nearest`).

## Usage

```
.venv-sg/Scripts/python.exe scripts/upscale_faithful.py <png or folder> --out <folder> --factor 8
.venv-sg/Scripts/python.exe scripts/upscale_faithful.py <png or folder> --out <folder> --factor 8 --mode lanczos
```
