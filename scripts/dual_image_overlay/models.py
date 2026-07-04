from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BBox = list[float]


@dataclass(frozen=True)
class Container:
    id: str
    role: str
    bbox: BBox
    text_safe_bbox: BBox


@dataclass(frozen=True)
class TextItem:
    source_text: str
    display_text: str
    role: str
    container_id: str
    bbox: BBox
    source_bbox: BBox
    font_size: float
    fill: str
    font_family: str = "Arial"
    bold: bool = False
    align: str = "left"
    v_align: str = "top"


@dataclass(frozen=True)
class SemanticPlan:
    image_size: dict[str, int]
    containers: list[Container]
    items: list[TextItem]
    geometry_source: str = "semantic_plan_containers"


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload
