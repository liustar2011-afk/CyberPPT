from __future__ import annotations

from typing import Any, Mapping

from .schema import BBox, NORMALIZED_CANVAS


COORDINATE_CONTEXT_SCHEMA = "cyberppt.scene_graph.coordinate_context.v1"
EXTENT_TOLERANCE = 2.0


def _size(value: Mapping[str, Any] | None) -> dict[str, float] | None:
    if not value:
        return None
    width = float(value.get("width") or value.get("w") or 0)
    height = float(value.get("height") or value.get("h") or 0)
    if width <= 0 or height <= 0:
        return None
    return {"width": round(width, 3), "height": round(height, 3)}


def _exceeds(
    candidate: dict[str, float] | None,
    reference: dict[str, float] | None,
    *,
    tolerance: float = EXTENT_TOLERANCE,
) -> bool:
    return bool(
        candidate
        and reference
        and (
            candidate["width"] > reference["width"] + tolerance
            or candidate["height"] > reference["height"] + tolerance
        )
    )


def _fits(candidate: dict[str, float] | None, reference: dict[str, float] | None) -> bool:
    return bool(candidate and reference and not _exceeds(candidate, reference))


def resolve_coordinate_context(
    *,
    plan_size: Mapping[str, Any] | None,
    image_size: Mapping[str, Any] | None,
    registry_size: Mapping[str, Any] | None,
    semantic_extent: Mapping[str, Any] | None,
    registry_extent: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Resolve source coordinate spaces before any scene graph bbox is emitted."""

    plan = _size(plan_size)
    image = _size(image_size)
    registry = _size(registry_size)
    semantic = _size(semantic_extent)
    registry_used = _size(registry_extent)
    warnings: list[dict[str, Any]] = []

    semantic_input = image or registry or plan or dict(NORMALIZED_CANVAS)
    if plan and image and _exceeds(semantic, image):
        semantic_input = plan
        warnings.append(
            {
                "code": "semantic_coordinate_space_uses_plan_extent",
                "semantic_plan_image_size": plan,
                "background_image_actual": image,
                "semantic_bbox_extent": semantic,
                "resolved_semantic_input_space": semantic_input,
            }
        )

    registry_input = registry or semantic_input
    if registry and _exceeds(registry_used, registry):
        if _fits(registry_used, plan):
            registry_input = plan
        else:
            registry_input = registry_used
        warnings.append(
            {
                "code": "visual_registry_canvas_metadata_stale",
                "visual_registry_canvas": registry,
                "registry_bbox_extent": registry_used,
                "resolved_visual_registry_input_space": registry_input,
            }
        )
        if semantic_input == image and _fits(registry_used, plan):
            semantic_input = plan
            warnings.append(
                {
                    "code": "semantic_coordinate_space_follows_registry_extent",
                    "semantic_plan_image_size": plan,
                    "registry_bbox_extent": registry_used,
                    "resolved_semantic_input_space": semantic_input,
                }
            )

    return {
        "schema": COORDINATE_CONTEXT_SCHEMA,
        "coordinate_space": dict(NORMALIZED_CANVAS),
        "semantic_input_space": semantic_input,
        "visual_registry_input_space": registry_input,
        "image_size": image,
        "semantic_plan_image_size": plan,
        "visual_registry_canvas": registry,
        "semantic_bbox_extent": semantic,
        "visual_registry_bbox_extent": registry_used,
        "warnings": warnings,
    }


def normalize_bbox(bbox: BBox, input_space: Mapping[str, Any], context: Mapping[str, Any]) -> BBox:
    source = _size(input_space)
    target = _size(context.get("coordinate_space") if isinstance(context, Mapping) else None)
    if source is None:
        raise ValueError("input_space must contain positive width and height")
    if target is None:
        raise ValueError("context.coordinate_space must contain positive width and height")

    box = BBox.from_any(bbox)
    sx = target["width"] / source["width"]
    sy = target["height"] / source["height"]
    return BBox(box.x1 * sx, box.y1 * sy, box.x2 * sx, box.y2 * sy)
