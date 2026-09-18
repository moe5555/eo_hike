"""Step 2: manifest -> ``embeddings_<encoder>.npy`` + ``embed_meta_<encoder>.json``.

Row ``i`` of the embeddings array is chip ``i`` of the manifest. The array is
float32 and every row is a unit vector. Existing embeddings are never recomputed.

Centring (``encoder.center``, default on): mean-pooled transformer features share a
large common component, so every chip lies in a narrow cone and all cosine distances
are tiny and nearly equal (DOFA on the debug set: archive-mean length 0.988, random
pairs 0.02 apart). Subtracting the archive mean and renormalising removes that
common component; distances then span the full range and the softmax temperature
means what it says. The mean vector is saved next to the embeddings so the step is
reproducible and so new chips could be projected the same way. It makes a chip's
embedding depend on the archive it sits in, which is why it is recorded as an
interpreted step in ``embed_meta.json``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from tqdm import tqdm

from . import config as C
from .encoders import get_encoder
from .ingest import load_manifest


def run_embed(cfg: dict[str, Any], force: bool = False) -> Path:
    out = C.embeddings_path(cfg)
    meta_path = C.embed_meta_path(cfg)
    if out.exists() and meta_path.exists() and not force:
        print(f"[embed] embeddings exist, skipping: {out}")
        return out

    manifest = load_manifest(cfg)
    encoder = get_encoder(cfg["encoder"])
    bs = int(cfg["encoder"].get("batch_size", 64))
    root = C.processed_dir(cfg)
    paths = [root / p for p in manifest["path"].tolist()]

    embs = np.empty((len(paths), encoder.dim), dtype=np.float32)
    for start in tqdm(range(0, len(paths), bs), desc=f"embed[{encoder.name}]", unit="batch"):
        batch = [Image.open(p).convert("RGB") for p in paths[start : start + bs]]
        embs[start : start + len(batch)] = encoder.encode(batch)

    norms = np.linalg.norm(embs, axis=1)
    if not np.allclose(norms, 1.0, atol=1e-3):
        raise RuntimeError("encoder returned non-normalised vectors")
    mean_vec = embs.mean(axis=0)
    mean_norm_raw = float(np.linalg.norm(mean_vec))
    centered = bool(cfg["encoder"].get("center", True))
    if centered:
        embs = embs - mean_vec
        embs /= np.maximum(np.linalg.norm(embs, axis=1, keepdims=True), 1e-12)
        with open(out.with_name(out.stem + "_mean.npy"), "wb") as f:
            np.save(f, mean_vec.astype(np.float32))
    tmp = out.with_name(out.name + ".part")
    with open(tmp, "wb") as f:  # np.save(path) would append ".npy" to a non-.npy path
        np.save(f, embs)
    tmp.replace(out)
    meta = {
        **encoder.describe(),
        "n": int(embs.shape[0]),
        "dim": int(embs.shape[1]),
        "dtype": "float32",
        "row_order": "manifest.parquet row order",
        "centered": centered,
        "archive_mean_norm_before_centering": round(mean_norm_raw, 4),
        "archive_mean_norm_after": round(float(np.linalg.norm(embs.mean(axis=0))), 4),
        "manifest": C.manifest_path(cfg).name,
        "dataset_key": cfg["dataset"]["key"],
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"[embed] wrote {out} {embs.shape}")
    return out


def load_embeddings(cfg: dict[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
    embs = np.load(C.embeddings_path(cfg), mmap_mode="r")
    with open(C.embed_meta_path(cfg), "r", encoding="utf-8") as f:
        meta = json.load(f)
    return np.ascontiguousarray(embs, dtype=np.float32), meta
