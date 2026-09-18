"""Step 3: embeddings -> FAISS index.

``IndexFlatIP`` is an *exact* search: for a query it computes the inner product with
every stored vector and returns the top k. With unit vectors that inner product is
the cosine similarity. Exact search is deterministic and, at tens of thousands of
vectors, takes well under a millisecond per query, so approximate indexes (IVF,
HNSW) would add randomness for no gain. That is a deliberate constraint from the
brief, not an oversight.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import faiss
import numpy as np

from . import config as C
from .embed import load_embeddings


def build_index(embeddings: np.ndarray, index_type: str = "flat_ip") -> faiss.Index:
    if index_type != "flat_ip":
        raise ValueError(f"unsupported index type {index_type!r}; only flat_ip is allowed (see docs/decisions.md)")
    x = np.ascontiguousarray(embeddings, dtype=np.float32)
    index = faiss.IndexFlatIP(x.shape[1])
    index.add(x)
    return index


def run_index(cfg: dict[str, Any], force: bool = False) -> Path:
    out = C.index_path(cfg)
    if out.exists() and not force:
        print(f"[index] index exists, skipping: {out}")
        return out
    embs, _ = load_embeddings(cfg)
    index = build_index(embs, cfg["index"]["type"])
    faiss.write_index(index, str(out))
    print(f"[index] wrote {out} with {index.ntotal} vectors")
    return out


def load_index(cfg: dict[str, Any]) -> faiss.Index:
    return faiss.read_index(str(C.index_path(cfg)))
