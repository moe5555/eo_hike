"""DOFA ViT-B/16 (Xiong et al. 2024) via torchgeo, used as the Earth-observation encoder.

DOFA ("Dynamic One-For-All") is a vision transformer pretrained on satellite imagery
from several sensors (SatlasPretrain, Five-Billion-Pixels, HySpecNet-11k). Its patch
embedding is generated from the *wavelengths* of the input bands, so the same weights
accept RGB, all thirteen Sentinel-2 bands, or SAR. We feed it RGB with the Sentinel-2
band centres 0.665 / 0.560 / 0.490 um.

Embedding: the mean of the 196 patch tokens followed by a LayerNorm (DOFA's own
``global_pool=True`` convention; the released checkpoint has no final norm for the
cls-token path, so that path would use untrained weights), then L2-normalised.
768 dimensions.

Preprocessing: resize to 224x224 (bicubic), scale to [0, 1], ImageNet mean/std.
torchgeo ships no normalisation with these weights ("sensor-dependent"); ImageNet
statistics are the conventional choice for 8-bit RGB and are recorded in
``embed_meta.json`` so the choice is visible.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from . import register
from .base import l2_normalise, pick_device

RGB_WAVELENGTHS_UM = [0.665, 0.560, 0.490]  # Sentinel-2 B04, B03, B02 centres
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


@register("dofa_base")
class DOFABase16:
    name = "dofa_base"
    dim = 768

    def __init__(self, ecfg: dict[str, Any]) -> None:
        import torchgeo
        from torchgeo.models import DOFABase16_Weights, dofa_base_patch16_224

        self.device = pick_device(ecfg.get("device", "auto"))
        self.weights = DOFABase16_Weights.DOFA_MAE
        self.model = dofa_base_patch16_224(weights=self.weights, global_pool=True)
        self.model.eval().to(self.device)
        self.torchgeo_version = torchgeo.__version__
        self.preprocess = transforms.Compose(
            [
                transforms.Resize((224, 224), interpolation=transforms.InterpolationMode.BICUBIC),
                transforms.ToTensor(),
                transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
            ]
        )

    @torch.no_grad()
    def encode(self, images: list[Image.Image]) -> np.ndarray:
        x = torch.stack([self.preprocess(im.convert("RGB")) for im in images]).to(self.device)
        feats = self.model.forward_features(x, RGB_WAVELENGTHS_UM)
        return l2_normalise(feats.float().cpu().numpy())

    def describe(self) -> dict[str, Any]:
        return {
            "encoder": self.name,
            "model": "dofa_base_patch16_224",
            "weights": f"{self.weights.__class__.__name__}.{self.weights.name}",
            "weights_url": self.weights.url,
            "library": f"torchgeo {self.torchgeo_version}",
            "torch": torch.__version__,
            "dim": self.dim,
            "input_wavelengths_um": RGB_WAVELENGTHS_UM,
            "preprocessing": "resize 224x224 bicubic, scale to [0,1], ImageNet mean/std",
            "pooling": "mean of patch tokens, then LayerNorm (DOFA default global_pool=True; the checkpoint carries no final norm for the cls path)",
            "normalised": True,
        }
