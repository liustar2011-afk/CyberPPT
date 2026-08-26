from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class ContentRules:
    page_fields: tuple[dict[str, Any], ...]
    page_composition: dict[str, Any]
    density_levels: dict[str, dict[str, Any]]
    semantic_diagram_types: tuple[str, ...]
    render_strategies: dict[str, dict[str, Any]]
    onscreen_text: dict[str, Any]
    title_quality: dict[str, Any]
    consistency: dict[str, Any]
    page_nature: dict[str, Any]
    visual_focus: dict[str, Any]
    visual_drawing: dict[str, Any]
    page_type_quality: dict[str, Any]


_REQUIRED_KEYS = {
    "page_fields",
    "page_composition",
    "density_levels",
    "semantic_diagram_types",
    "render_strategies",
    "onscreen_text",
    "title_quality",
    "consistency",
    "page_nature",
    "visual_focus",
    "visual_drawing",
    "page_type_quality",
}


def load_rules(path: Path) -> ContentRules:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != _REQUIRED_KEYS:
        raise ValueError(f"rules.yaml must contain exactly: {', '.join(sorted(_REQUIRED_KEYS))}")
    fields = data["page_fields"]
    if not isinstance(fields, list) or not fields:
        raise ValueError("page_fields must be a non-empty list")
    for field in fields:
        if not isinstance(field, dict) or not {"name", "required", "scope"} <= set(field):
            raise ValueError("each page field requires name, required, and scope")
    composition = data["page_composition"]
    if not isinstance(composition, dict) or "onscreen_zones" not in composition:
        raise ValueError("page_composition must define onscreen_zones")
    drawing = data["visual_drawing"]
    if not isinstance(drawing, dict) or "sketch_sections" not in drawing:
        raise ValueError("visual_drawing must define sketch_sections")
    return ContentRules(
        page_fields=tuple(fields),
        page_composition=dict(composition),
        density_levels=dict(data["density_levels"]),
        semantic_diagram_types=tuple(data["semantic_diagram_types"]),
        render_strategies=dict(data["render_strategies"]),
        onscreen_text=dict(data["onscreen_text"]),
        title_quality=dict(data["title_quality"]),
        consistency=dict(data["consistency"]),
        page_nature=dict(data["page_nature"]),
        visual_focus=dict(data["visual_focus"]),
        visual_drawing=dict(drawing),
        page_type_quality=dict(data["page_type_quality"]),
    )
