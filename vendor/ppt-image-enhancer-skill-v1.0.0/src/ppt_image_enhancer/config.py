from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "default.yaml"
MODES_DIR = PROJECT_ROOT / "config" / "modes"


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(mode: str = "ppt_page", user_config: str | None = None) -> Dict[str, Any]:
    cfg = load_yaml(DEFAULT_CONFIG)
    mode_path = MODES_DIR / f"{mode}.yaml"
    if not mode_path.exists():
        supported = ", ".join(sorted(p.stem for p in MODES_DIR.glob("*.yaml")))
        raise ValueError(f"Unknown mode '{mode}'. Supported: {supported}")
    cfg = deep_merge(cfg, load_yaml(mode_path))
    if user_config:
        cfg = deep_merge(cfg, load_yaml(Path(user_config)))
    cfg["mode"] = mode
    return cfg
