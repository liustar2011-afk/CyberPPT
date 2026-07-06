from __future__ import annotations

from typing import Any


CANVAS = {"width": 1672, "height": 941}


def _rect(value: Any) -> list[float] | None:
    if isinstance(value, list) and len(value) == 4:
        try:
            return [float(item) for item in value]
        except (TypeError, ValueError):
            return None
    if isinstance(value, dict):
        try:
            x = float(value.get("x", 0) or 0)
            y = float(value.get("y", 0) or 0)
            w = float(value.get("w", value.get("width", 0)) or 0)
            h = float(value.get("h", value.get("height", 0)) or 0)
        except (TypeError, ValueError):
            return None
        if w > 0 and h > 0:
            return [x, y, x + w, y + h]
    return None


def _center(bbox: list[float]) -> tuple[float, float]:
    return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)


def _contains(container: list[float], point: tuple[float, float]) -> bool:
    return container[0] <= point[0] <= container[2] and container[1] <= point[1] <= container[3]


def _container_nodes(scene_graph: dict[str, Any] | None) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    if not isinstance(scene_graph, dict):
        return nodes
    for index, node in enumerate(scene_graph.get("visual_nodes", []), start=1):
        if not isinstance(node, dict):
            continue
        bbox = _rect(node.get("bbox") or node.get("blueprint_bbox_px") or node.get("render_bbox_px"))
        if bbox is None:
            continue
        element_type = str(node.get("element_type") or node.get("node_type") or "")
        role = str(node.get("semantic_role") or node.get("role") or element_type or "container")
        if element_type != "container" and "card" not in role and "cell" not in role and "segment" not in role:
            continue
        node_id = str(node.get("node_id") or node.get("element_id") or f"container_{index:03d}")
        nodes.append(
            {
                "id": node_id,
                "role": role,
                "bbox": bbox,
                "text_safe_bbox": bbox,
                "aliases": [str(item) for item in node.get("aliases", []) if item],
                "source": {"kind": "scene_graph"},
                "confidence": 0.8,
            }
        )
    return nodes


def _source_capture_container_nodes(source_capture_page: dict[str, Any] | None) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    if not isinstance(source_capture_page, dict):
        return nodes
    for index, container in enumerate(source_capture_page.get("containers", []), start=1):
        if not isinstance(container, dict):
            continue
        bbox = _rect(container.get("bbox") or container)
        if bbox is None:
            continue
        safe_bbox = _rect(container.get("text_safe_bbox") or container.get("text_safe_bbox_px")) or bbox
        container_id = str(container.get("id") or f"container_{index:03d}")
        nodes.append(
            {
                "id": container_id,
                "role": str(container.get("role") or "container"),
                "bbox": bbox,
                "text_safe_bbox": safe_bbox,
                "aliases": [str(item) for item in container.get("aliases", []) if item],
                "source": {"kind": "source_capture"},
                "confidence": float(container.get("confidence") or 0.7),
            }
        )
    return nodes


def _source_capture_text_items(source_capture_page: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(source_capture_page, dict):
        return []
    items: list[dict[str, Any]] = []
    for item in source_capture_page.get("text_objects", []):
        if not isinstance(item, dict):
            continue
        text = str(item.get("rendered_text") or item.get("text") or "").strip()
        bbox = item.get("bbox")
        if text and bbox:
            items.append({"text": text, "bbox": bbox})
    return items


def build_semantic_binding(
    *,
    page_number: int,
    script_sections: dict[str, Any],
    ocr_items: list[dict[str, Any]],
    scene_graph: dict[str, Any] | None,
    source_capture_page: dict[str, Any] | None,
    visual_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    containers = _container_nodes(scene_graph) or _source_capture_container_nodes(source_capture_page)
    effective_ocr_items = ocr_items or _source_capture_text_items(source_capture_page)
    items: list[dict[str, Any]] = []
    unassigned: list[dict[str, Any]] = []
    for index, item in enumerate(effective_ocr_items, start=1):
        bbox = _rect(item.get("bbox") or item.get("blueprint_bbox_px"))
        text = str(item.get("text") or item.get("display_text") or "").strip()
        if not text or bbox is None:
            continue
        point = _center(bbox)
        container = next((candidate for candidate in containers if _contains(candidate["bbox"], point)), None)
        if container is None:
            unassigned.append({"text": text, "bbox": bbox})
            continue
        items.append(
            {
                "id": f"text_{index:03d}",
                "container_id": container["id"],
                "display_text": text,
                "source_text": text,
                "role": f"{container['role']}_text",
                "bbox": bbox,
                "word_wrap": True,
                "source": {"kind": "ocr_locator"},
                "confidence": 0.75,
            }
        )
    return {
        "schema": "cyberppt.semantic_binding.v1",
        "page_number": page_number,
        "image_size": CANVAS,
        "inputs": {
            "script_sections": bool(script_sections),
            "ocr_items": len(ocr_items),
            "scene_graph": bool(scene_graph),
            "source_capture_page": bool(source_capture_page),
            "visual_registry": bool(visual_registry),
        },
        "containers": containers,
        "items": items,
        "unassigned_text": unassigned,
        "checks": {
            "container_count": len(containers),
            "item_count": len(items),
            "unassigned_text_count": len(unassigned),
        },
    }


def semantic_binding_to_plan(binding: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "cyberppt.explicit_semantic_plan.v1",
        "page_number": binding.get("page_number"),
        "image_size": binding.get("image_size", CANVAS),
        "inputs": {
            "source_capture": bool(binding.get("inputs", {}).get("source_capture_page")),
            "visual_element_registry": bool(binding.get("inputs", {}).get("visual_registry")),
            "script_truth": bool(binding.get("inputs", {}).get("script_sections")),
            "geometry_truth": "semantic_binding",
        },
        "geometry_truth": "semantic_containers",
        "text_truth": "script_truth_plus_ocr_locator",
        "containers": binding.get("containers", []),
        "items": binding.get("items", []),
    }
