"""Archive adapter registry. ``dataset.name`` in the config selects one of these."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .base import ChipRecord, DatasetAdapter

# name -> factory(dataset_cfg, raw_dir) -> adapter
_REGISTRY: dict[str, Callable[[dict[str, Any], Path], DatasetAdapter]] = {}


def register(name: str) -> Callable[[type], type]:
    def deco(cls: type) -> type:
        _REGISTRY[name] = lambda dcfg, raw: cls(dcfg, raw)  # type: ignore[call-arg]
        return cls

    return deco


def get_adapter(dataset_cfg: dict[str, Any], raw_dir: Path) -> DatasetAdapter:
    name = dataset_cfg["name"]
    # Import lazily so a broken optional dependency only breaks the adapter that needs it.
    if name not in _REGISTRY:
        from importlib import import_module

        try:
            import_module(f"hiker.datasets.{name}")
        except ModuleNotFoundError as e:
            raise KeyError(f"unknown dataset adapter {name!r}; known: {sorted(_REGISTRY)}") from e
    if name not in _REGISTRY:
        raise KeyError(f"module hiker.datasets.{name} did not register an adapter named {name!r}")
    return _REGISTRY[name](dataset_cfg, raw_dir)


__all__ = ["ChipRecord", "DatasetAdapter", "get_adapter", "register"]
