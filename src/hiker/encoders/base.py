"""The encoder boundary.

An encoder turns a batch of RGB chips into one L2-normalised vector each. Because the
vectors are unit length, the dot product of two of them is their cosine similarity,
and ``1 - dot`` is the cosine distance the novelty score is built on.

Planned additional encoders (spectral histograms, Haralick texture, land-cover
statistics) implement the same protocol; they are *not* implemented yet.
"""

from __future__ import annotations

from typing import Any, Protocol

import numpy as np
from PIL import Image


class Encoder(Protocol):
    name: str
    dim: int

    def encode(self, images: list[Image.Image]) -> np.ndarray:
        """Return an array of shape ``(len(images), dim)``, float32, rows L2-normalised."""
        ...

    def describe(self) -> dict[str, Any]:
        """Model name, weights, version and preprocessing, for ``embed_meta.json``."""
        ...


def l2_normalise(x: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """Divide each row by its Euclidean norm so every row has length 1."""
    x = np.asarray(x, dtype=np.float32)
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.maximum(n, eps)


def pick_device(requested: str) -> str:
    if requested != "auto":
        return requested
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"
