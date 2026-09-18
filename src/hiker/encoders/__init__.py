"""Encoder registry. ``encoder.name`` in the config selects one of these."""

from __future__ import annotations

from typing import Any, Callable

from .base import Encoder, l2_normalise, pick_device

_REGISTRY: dict[str, Callable[[dict[str, Any]], Encoder]] = {}


def register(name: str) -> Callable[[type], type]:
    def deco(cls: type) -> type:
        _REGISTRY[name] = lambda ecfg: cls(ecfg)  # type: ignore[call-arg]
        return cls

    return deco


def get_encoder(encoder_cfg: dict[str, Any]) -> Encoder:
    name = encoder_cfg["name"]
    if name not in _REGISTRY:
        from importlib import import_module

        module = {"dofa_base": "dofa", "clip_vit_b32": "clip"}.get(name, name)
        try:
            import_module(f"hiker.encoders.{module}")
        except ModuleNotFoundError as e:
            raise KeyError(f"unknown encoder {name!r}; known: {sorted(_REGISTRY)}") from e
    if name not in _REGISTRY:
        raise KeyError(f"encoder module did not register {name!r}; known: {sorted(_REGISTRY)}")
    return _REGISTRY[name](encoder_cfg)


__all__ = ["Encoder", "get_encoder", "l2_normalise", "pick_device", "register"]
