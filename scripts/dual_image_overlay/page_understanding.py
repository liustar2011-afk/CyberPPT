from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any


SCHEMA = "cyberppt.dual_image.page_understanding.v1"
DEFAULT_CANVAS = {"width": 1280.0, "height": 720.0}
BINDING_INTERSECTION_THRESHOLD = 0.55
IMPLICIT_CONTAINER_CONFIDENCE = 0.82


def _hash_file(path: Path | None) -> str | None:
    if path is None or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_path_value(path: Path | None) -> str | None:
    if path is None:
        return None
    return hashlib.sha256(str(path).encode("utf-8")).hexdigest()


def _xyxy(raw: Any) -> list[float] | None:
    if isinstance(raw, (list, tuple)) and len(raw) == 4:
        try:
            x1, y1, x2, y2 = (float(value) for value in raw)
        except (TypeError, ValueError):
            return None
        if not all(math.isfinite(value) for value in (x1, y1, x2, y2)):
            return None
        if x2 <= x1 or y2 <= y1:
            return None
        return [x1, y1, x2, y2]

    if isinstance(raw, dict):
        if "bbox" in raw:
            return _xyxy(raw.get("bbox"))
        if "x" not in raw or "y" not in raw:
            return None
        width_key = "w" if "w" in raw else "width" if "width" in raw else None
        height_key = "h" if "h" in raw else "height" if "height" in raw else None
        if width_key is None or height_key is None:
            return None
        try:
            x = float(raw["x"])
            y = float(raw["y"])
            width = float(raw[width_key])
            height = float(raw[height_key])
        except (TypeError, ValueError):
            return None
        if not all(math.isfinite(value) for value in (x, y, width, height)):
            return None
        if width <= 0.0 or height <= 0.0:
            return None
        return _xyxy([x, y, x + width, y + height])

    return None


def _confidence(raw: Any, default: float = 0.8) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(value):
        return default
    return value


def _area(bbox: list[float]) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


def _intersection_ratio(inner: list[float], outer: list[float]) -> float:
    left = max(inner[0], outer[0])
    top = max(inner[1], outer[1])
    right = min(inner[2], outer[2])
    bottom = min(inner[3], outer[3])
    return _area([left, top, right, bottom]) / max(1.0, _area(inner))


def _iter_dicts(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _canvas_dimensions(canvas: dict[str, Any] | None = None) -> tuple[float, float]:
    canvas_input = canvas or DEFAULT_CANVAS
    try:
        width = float(canvas_input.get("width", DEFAULT_CANVAS["width"]))
        height = float(canvas_input.get("height", DEFAULT_CANVAS["height"]))
    except (AttributeError, TypeError, ValueError):
        return DEFAULT_CANVAS["width"], DEFAULT_CANVAS["height"]
    if not math.isfinite(width) or not math.isfinite(height) or width <= 0.0 or height <= 0.0:
        return DEFAULT_CANVAS["width"], DEFAULT_CANVAS["height"]
    return width, height


def _has_positive_canvas_intersection(bbox: list[float], canvas: dict[str, Any] | None = None) -> bool:
    canvas_width, canvas_height = _canvas_dimensions(canvas)
    left = max(0.0, bbox[0])
    top = max(0.0, bbox[1])
    right = min(canvas_width, bbox[2])
    bottom = min(canvas_height, bbox[3])
    return right > left and bottom > top


def _container_payload(raw: dict[str, Any], *, kind: str, index: int) -> dict[str, Any] | None:
    bbox = _xyxy(raw.get("bbox") or raw)
    if bbox is None:
        return None

    text_safe_bbox = _xyxy(raw.get("text_safe_bbox") or raw.get("text_safe_bbox_px") or bbox) or bbox
    default_source = "background_image" if kind == "explicit_container" else "full_image_text_block"
    return {
        "id": str(raw.get("id") or f"{kind}_{index:03d}"),
        "kind": kind,
        "role": str(raw.get("role") or raw.get("container_role") or "container"),
        "bbox": bbox,
        "text_safe_bbox": text_safe_bbox,
        "source": str(raw.get("source") or default_source),
        "confidence": _confidence(raw.get("confidence", 0.8)),
    }


def _text_block_payload(raw: dict[str, Any], index: int) -> dict[str, Any] | None:
    bbox = _xyxy(raw.get("bbox") or raw)
    final_text = str(raw.get("final_text") or raw.get("text") or raw.get("ocr_text") or "").strip()
    if bbox is None or not final_text:
        return None

    raw_line_boxes = raw.get("line_boxes")
    line_box_items = raw_line_boxes if isinstance(raw_line_boxes, (list, tuple)) else []
    line_boxes = []
    for item in line_box_items:
        line_bbox = _xyxy(item)
        if line_bbox is not None:
            line_boxes.append(line_bbox)

    return {
        "id": str(raw.get("id") or f"text_block_{index:03d}"),
        "ocr_text": str(raw.get("ocr_text") or final_text),
        "final_text": final_text,
        "bbox": bbox,
        "line_boxes": line_boxes,
        "style": dict(raw.get("style") or {}),
        "truth": dict(raw.get("truth") or {"status": "ocr_unverified", "similarity": 0.0}),
        "fit_policy": dict(raw.get("fit_policy") or {"mode": "preserve_lines_then_uniform_scale"}),
        "source": str(raw.get("source") or "full_image_ocr"),
    }


def _visual_element_payload(raw: dict[str, Any], index: int) -> dict[str, Any]:
    payload = dict(raw)
    payload.setdefault("id", f"visual_element_{index:03d}")
    bbox = _xyxy(payload.get("bbox") or payload)
    if bbox is not None:
        payload["bbox"] = bbox
    else:
        payload.pop("bbox", None)
    return payload


def _expanded_bbox(
    bbox: list[float],
    *,
    x_pad: float = 12.0,
    y_pad: float = 6.0,
    canvas: dict[str, Any] | None = None,
) -> list[float] | None:
    canvas_width, canvas_height = _canvas_dimensions(canvas)
    expanded = [
        max(0.0, bbox[0] - x_pad),
        max(0.0, bbox[1] - y_pad),
        min(canvas_width, bbox[2] + x_pad),
        min(canvas_height, bbox[3] + y_pad),
    ]
    return _xyxy(expanded)


def build_implicit_text_containers(
    text_blocks: list[dict[str, Any]],
    explicit_containers: list[dict[str, Any]],
    visual_elements: list[dict[str, Any]],
    *,
    canvas: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    normalized_explicit = [
        item
        for item in (
            _container_payload(raw, kind="explicit_container", index=index)
            for index, raw in enumerate(_iter_dicts(explicit_containers), start=1)
        )
        if item is not None
    ]
    normalized_visuals = [
        _visual_element_payload(raw, index)
        for index, raw in enumerate(_iter_dicts(visual_elements), start=1)
    ]

    implicit: list[dict[str, Any]] = []
    for block in _iter_dicts(text_blocks):
        bbox = _xyxy(block.get("bbox") or block)
        text = str(block.get("final_text") or block.get("text") or block.get("ocr_text") or "").strip()
        if bbox is None or not text:
            continue
        if not _has_positive_canvas_intersection(bbox, canvas):
            continue
        if any(
            _intersection_ratio(bbox, container["text_safe_bbox"]) >= BINDING_INTERSECTION_THRESHOLD
            for container in normalized_explicit
        ):
            continue

        block_id = str(block.get("id") or f"text_{len(implicit) + 1:03d}")
        confidence = IMPLICIT_CONTAINER_CONFIDENCE
        if normalized_visuals:
            confidence = min(0.9, confidence + 0.03)
        expanded = _expanded_bbox(bbox, canvas=canvas)
        if expanded is None:
            continue
        implicit.append(
            {
                "id": f"implicit_{block_id}",
                "kind": "implicit_text_container",
                "role": "text_safe_zone",
                "bbox": expanded,
                "text_safe_bbox": expanded,
                "source": "full_image_text_block",
                "text_block_id": block_id,
                "confidence": confidence,
            }
        )
    return implicit


def _bind_text_to_containers(
    text_blocks: list[dict[str, Any]], containers: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    for text_block in text_blocks:
        ranked = sorted(
            (
                (_intersection_ratio(text_block["bbox"], container["text_safe_bbox"]), container)
                for container in containers
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        if ranked and ranked[0][0] >= BINDING_INTERSECTION_THRESHOLD:
            ratio, container = ranked[0]
            bindings.append(
                {
                    "text_block_id": text_block["id"],
                    "container_id": container["id"],
                    "method": "bbox_intersection",
                    "intersection_ratio": round(ratio, 3),
                    "confidence": round(ratio, 3),
                }
            )
    return bindings


def build_page_understanding(
    *,
    page_number: int,
    full_image: Path | None,
    background_image: Path | None,
    registration: dict[str, Any],
    text_blocks: list[dict[str, Any]],
    explicit_containers: list[dict[str, Any]],
    implicit_containers: list[dict[str, Any]],
    visual_elements: list[dict[str, Any]],
    canvas: dict[str, float] | None = None,
) -> dict[str, Any]:
    canvas_input = canvas or DEFAULT_CANVAS
    normalized_canvas = {
        "width": float(canvas_input.get("width", DEFAULT_CANVAS["width"])),
        "height": float(canvas_input.get("height", DEFAULT_CANVAS["height"])),
    }

    containers = [
        item
        for item in (
            [
                _container_payload(raw, kind="explicit_container", index=index)
                for index, raw in enumerate(_iter_dicts(explicit_containers), start=1)
            ]
            + [
                _container_payload(raw, kind="implicit_text_container", index=index)
                for index, raw in enumerate(_iter_dicts(implicit_containers), start=1)
            ]
        )
        if item is not None
    ]
    normalized_text_blocks = [
        item
        for item in (
            _text_block_payload(raw, index)
            for index, raw in enumerate(_iter_dicts(text_blocks), start=1)
        )
        if item is not None
    ]
    normalized_visual_elements = [
        _visual_element_payload(raw, index)
        for index, raw in enumerate(_iter_dicts(visual_elements), start=1)
    ]

    bindings = _bind_text_to_containers(normalized_text_blocks, containers)
    bound_text_ids = {binding["text_block_id"] for binding in bindings}
    review_items = [
        {
            "type": "unbound_text_block",
            "text_block_id": text_block["id"],
            "text": text_block["final_text"],
            "severity": "warning",
        }
        for text_block in normalized_text_blocks
        if text_block["id"] not in bound_text_ids
    ]

    error_count = sum(1 for item in review_items if item["severity"] == "error")
    warning_count = sum(1 for item in review_items if item["severity"] == "warning")
    valid = bool(registration.get("valid", False)) and bool(normalized_text_blocks) and error_count == 0

    return {
        "schema": SCHEMA,
        "page_number": int(page_number),
        "valid": valid,
        "coordinate_context": {"normalized_canvas": normalized_canvas},
        "cache_signature": {
            "full_sha256": _hash_file(full_image),
            "background_sha256": _hash_file(background_image),
            "full_path_sha256": _hash_path_value(full_image),
            "background_path_sha256": _hash_path_value(background_image),
            "text_block_count": len(normalized_text_blocks),
            "container_count": len(containers),
            "explicit_container_count": sum(1 for item in containers if item["kind"] == "explicit_container"),
            "implicit_container_count": sum(1 for item in containers if item["kind"] == "implicit_text_container"),
            "visual_element_count": len(normalized_visual_elements),
        },
        "registration": dict(registration),
        "containers": containers,
        "text_blocks": normalized_text_blocks,
        "container_text_bindings": bindings,
        "visual_elements": normalized_visual_elements,
        "review_items": review_items,
        "error_count": error_count,
        "warning_count": warning_count,
    }


def write_page_understanding(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return payload
