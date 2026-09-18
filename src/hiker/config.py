"""Configuration loading: defaults <- YAML file <- CLI overrides.

Every tunable named in the brief is a config value. The fully resolved config is
written into each run directory so a run can always be reproduced from it.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import yaml

# Defaults are deliberately complete so that ``config.yaml`` in a run directory
# never has an implicit value. Justification for the numbers lives in
# docs/decisions.md; do not tune them here without updating that file.
DEFAULTS: dict[str, Any] = {
    "data_root": None,  # None -> $HIKER_DATA_ROOT, else ./data
    "dataset": {
        "name": "ssl4eo_s12_v11",
        "key": None,  # None -> "<name>-<hash of this section>"
    },
    "encoder": {
        "name": "dofa_base",
        "batch_size": 64,
        "device": "auto",  # auto | cuda | cpu
        "num_workers": 0,
        # Subtract the archive-mean embedding and renormalise. Needed because mean-pooled
        # ViT features are strongly anisotropic (see docs/decisions.md, finding 2).
        "center": True,
    },
    "index": {
        "type": "flat_ip",
    },
    "agents": {
        "n_agents": 2,
        "seed": 7,
        "start_chips": None,  # list of chip_ids (one per agent) or None for random
        "k_neighbours": 50,
        "m_random": 5,
        "j_history": 15,
        "temperature": 0.05,
        "max_steps": 300,
        "boredom_window": 20,
        "boredom_threshold": 0.4,
    },
    "outputs": {
        "runs_dir": "runs",
        "write_images": True,
        "image_format": "png",
    },
}


def deep_update(base: dict[str, Any], upd: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge ``upd`` into a copy of ``base``. Dicts merge, everything else replaces."""
    out = copy.deepcopy(base)
    for k, v in upd.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_update(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def parse_override(text: str) -> dict[str, Any]:
    """Turn ``"agents.temperature=0.3"`` into ``{"agents": {"temperature": 0.3}}``.

    The value is parsed with YAML so ``0.3`` is a float, ``true`` a bool, ``null`` None,
    and ``[a, b]`` a list. Quote strings that would otherwise parse as something else.
    """
    if "=" not in text:
        raise ValueError(f"override must look like key.path=value, got {text!r}")
    key, _, raw = text.partition("=")
    value = yaml.safe_load(raw) if raw != "" else None
    node: dict[str, Any] = {}
    cur = node
    parts = key.strip().split(".")
    for p in parts[:-1]:
        cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value
    return node


def load_config(path: str | Path | None, overrides: list[str] | None = None) -> dict[str, Any]:
    """Load a YAML config on top of DEFAULTS and apply ``key=value`` overrides.

    ``data_root`` resolution order: override > YAML > ``$HIKER_DATA_ROOT`` > ``./data``.
    Paths are stored as strings so the config stays YAML-serialisable.
    """
    cfg = copy.deepcopy(DEFAULTS)
    if path is not None:
        with open(path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        cfg = deep_update(cfg, loaded)
    for o in overrides or []:
        cfg = deep_update(cfg, parse_override(o))
    if cfg.get("data_root") is None:
        cfg["data_root"] = os.environ.get("HIKER_DATA_ROOT", "data")
    cfg["data_root"] = str(Path(cfg["data_root"]))
    if cfg["dataset"].get("key") is None:
        cfg["dataset"]["key"] = f"{cfg['dataset']['name']}-{section_hash(cfg['dataset'])}"
    return cfg


def canonical_json(obj: Any) -> str:
    """Deterministic JSON used for hashing: sorted keys, no whitespace games."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def section_hash(section: dict[str, Any], n: int = 6) -> str:
    """Short hash of a config section, ignoring a ``key`` field if present."""
    s = {k: v for k, v in section.items() if k != "key"}
    return hashlib.sha1(canonical_json(s).encode()).hexdigest()[:n]


def config_hash(cfg: dict[str, Any], n: int = 8) -> str:
    """Hash of the whole resolved config; used in run directory names."""
    return hashlib.sha1(canonical_json(cfg).encode()).hexdigest()[:n]


# --- derived paths -------------------------------------------------------------

def data_root(cfg: dict[str, Any]) -> Path:
    return Path(cfg["data_root"])


def raw_dir(cfg: dict[str, Any]) -> Path:
    """Where adapters keep their downloads (shards, zips, thumbnails)."""
    return data_root(cfg) / "raw" / cfg["dataset"]["name"]


def processed_dir(cfg: dict[str, Any]) -> Path:
    """Per-dataset-config directory with the manifest, chips, embeddings and index."""
    return data_root(cfg) / "processed" / cfg["dataset"]["key"]


def manifest_path(cfg: dict[str, Any]) -> Path:
    return processed_dir(cfg) / "manifest.parquet"


def chips_dir(cfg: dict[str, Any]) -> Path:
    return processed_dir(cfg) / "chips"


def encoder_key(cfg: dict[str, Any]) -> str:
    """Encoder name plus post-processing variant, so raw and centred files never collide."""
    e = cfg["encoder"]
    return e["name"] + ("_centered" if e.get("center", True) else "")


def embeddings_path(cfg: dict[str, Any]) -> Path:
    return processed_dir(cfg) / f"embeddings_{encoder_key(cfg)}.npy"


def embed_meta_path(cfg: dict[str, Any]) -> Path:
    return processed_dir(cfg) / f"embed_meta_{encoder_key(cfg)}.json"


def index_path(cfg: dict[str, Any]) -> Path:
    return processed_dir(cfg) / f"index_{encoder_key(cfg)}_{cfg['index']['type']}.faiss"
