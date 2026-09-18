"""OpenAI CLIP ViT-B/32 via ``open_clip``.

This is the *contrast* encoder. Its similarity comes from captioned internet
photographs, not from satellite data, so "unlike what I have seen" means something
different under it. Running the same hike under CLIP and under an Earth-observation
encoder is a research result in itself; that is why it is here.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch
from PIL import Image

from . import register
from .base import l2_normalise, pick_device


@register("clip_vit_b32")
class CLIPViTB32:
    name = "clip_vit_b32"
    dim = 512

    def __init__(self, ecfg: dict[str, Any]) -> None:
        import open_clip

        self.device = pick_device(ecfg.get("device", "auto"))
        self.model_name = "ViT-B-32"
        self.pretrained = "openai"
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            self.model_name, pretrained=self.pretrained, device=self.device
        )
        self.model.eval()
        self.open_clip_version = open_clip.__version__

    @torch.no_grad()
    def encode(self, images: list[Image.Image]) -> np.ndarray:
        x = torch.stack([self.preprocess(im.convert("RGB")) for im in images]).to(self.device)
        feats = self.model.encode_image(x).float().cpu().numpy()
        return l2_normalise(feats)

    def describe(self) -> dict[str, Any]:
        return {
            "encoder": self.name,
            "model": self.model_name,
            "weights": self.pretrained,
            "library": f"open_clip {self.open_clip_version}",
            "torch": torch.__version__,
            "dim": self.dim,
            "preprocessing": "open_clip default: resize 224 (bicubic), centre crop, CLIP mean/std",
            "pooling": "CLIP image projection (cls token)",
            "normalised": True,
        }
