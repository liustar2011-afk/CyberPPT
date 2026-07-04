from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import Container, SemanticPlan, TextItem, read_json
from .normalize import CANVAS, relative_bbox, scale_bbox


def _image_size(payload: dict[str, Any]) -> tuple[int, int]:
    size = payload.get("image_size")
    if isinstance(size, dict) and "width" in size and "height" in size:
        return int(size["width"]), int(size["height"])
    return CANVAS


def load_semantic_plan(path: Path) -> SemanticPlan:
    payload = read_json(path)
    source_size = _image_size(payload)
    raw_containers = payload.get("containers")
    raw_items = payload.get("items")
    if not isinstance(raw_containers, list) or not raw_containers:
        raise ValueError("semantic_plan.containers must be a non-empty array")
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("semantic_plan.items must be a non-empty array")

    containers: list[Container] = []
    by_id: dict[str, Container] = {}
    for index, raw in enumerate(raw_containers):
        if not isinstance(raw, dict):
            raise ValueError(f"containers[{index}] must be an object")
        container_id = str(raw.get("id") or "").strip()
        if not container_id:
            raise ValueError(f"containers[{index}].id is required")
        if container_id in by_id:
            raise ValueError(f"containers[{index}].id is duplicated: {container_id}")

        try:
            raw_bbox = raw["bbox"]
        except KeyError as exc:
            raise ValueError(f"containers[{index}].bbox is required") from exc
        bbox = scale_bbox(raw_bbox, source_size=source_size)
        safe = scale_bbox(raw.get("text_safe_bbox", raw_bbox), source_size=source_size)
        container = Container(
            id=container_id,
            role=str(raw.get("role") or ""),
            bbox=bbox,
            text_safe_bbox=safe,
        )
        containers.append(container)
        by_id[container_id] = container

    items: list[TextItem] = []
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            raise ValueError(f"items[{index}] must be an object")
        container_id = str(raw.get("container_id") or "").strip()
        container = by_id.get(container_id)
        if container is None:
            raise ValueError(f"items[{index}] references unknown container_id: {container_id}")

        if "relative_bbox" in raw:
            bbox = relative_bbox(container.text_safe_bbox, raw["relative_bbox"])
        else:
            try:
                raw_bbox = raw["bbox"]
            except KeyError as exc:
                raise ValueError(f"items[{index}].bbox or relative_bbox is required") from exc
            bbox = scale_bbox(raw_bbox, source_size=source_size)

        source_text = str(raw.get("source_text") or raw.get("display_text") or "").strip()
        display_text = str(raw.get("display_text") or source_text).strip()
        if not display_text:
            raise ValueError(f"items[{index}].display_text is required")

        items.append(
            TextItem(
                source_text=source_text,
                display_text=display_text,
                role=str(raw.get("role") or "body"),
                container_id=container_id,
                bbox=bbox,
                source_bbox=scale_bbox(raw.get("bbox", bbox), source_size=source_size)
                if "bbox" in raw
                else bbox,
                font_size=float(raw.get("font_size") or 12),
                fill=str(raw.get("fill") or "#111111"),
                font_family=str(raw.get("font_family") or "Arial"),
                bold=bool(raw.get("bold", False)),
                align=str(raw.get("align") or "left"),
                v_align=str(raw.get("v_align") or "top"),
            )
        )

    return SemanticPlan(
        image_size={"width": CANVAS[0], "height": CANVAS[1]},
        containers=containers,
        items=items,
        geometry_source="semantic_plan_containers",
    )
