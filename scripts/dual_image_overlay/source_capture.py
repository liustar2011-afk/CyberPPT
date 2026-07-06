from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except ImportError:  # pragma: no cover - Pillow is available in the bundled runtime.
    Image = None  # type: ignore[assignment]

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "scripts.dual_image_overlay"

from .layout_rule_miner import load_ocr_boxes, load_svg_texts, mine_layout_rules


CANVAS = {"width": 1280, "height": 720}
TEXT_REQUIRES_PRIORITY = {"T2": "P0", "T4": "P0", "T6": "P0", "T8": "P0", "T13": "P0"}
NON_TEXT_VISUAL_EXCLUDED_TYPES = {"container", "text", "text_box", "text_object", "text_zone", "label_zone"}
NON_TEXT_VISUAL_P0_TYPES = {
    "arrow",
    "badge",
    "connector",
    "divider",
    "flow_arrow",
    "icon",
    "line",
    "separator",
    "shape",
    "visual",
}
BACKGROUND_COMPONENT_MAX_COUNT = 80
NON_BLOCKING_TEXT_TRUTH_REASONS = {
    "script_truth_match_ambiguous",
    "script_truth_containment_ambiguous",
    "script_truth_match_below_threshold",
}


def _px_to_pt(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return round(float(value) * 0.75, 2)
    except (TypeError, ValueError):
        return None


def _safe_non_negative_int(value: Any, reason: str) -> tuple[int, str | None]:
    if isinstance(value, bool):
        return 0, reason
    if isinstance(value, int):
        return (value, None) if value >= 0 else (0, reason)
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        return int(value), None
    return 0, reason


def _normalize_business_text(value: Any) -> str:
    return re.sub(r"[\s,，。:：;；、（）()【】\[\]\"'“”‘’]+", "", str(value or "")).lower()


def _is_non_blocking_text_truth_evidence(block: dict[str, Any]) -> bool:
    truth = block.get("truth") if isinstance(block.get("truth"), dict) else {}
    final_key = _normalize_business_text(block.get("final_text") or block.get("text") or block.get("ocr_text"))
    ocr_key = _normalize_business_text(block.get("ocr_text") or block.get("text") or block.get("final_text"))
    if not final_key or final_key != ocr_key:
        return False
    if len(final_key) <= 2:
        return True
    reason = str(truth.get("reason") or "")
    if reason not in NON_BLOCKING_TEXT_TRUTH_REASONS:
        return False
    matched_key = _normalize_business_text(truth.get("matched_text"))
    return bool(matched_key)


def _page_understanding_truth_summary(text_blocks: list[dict[str, Any]]) -> dict[str, Any]:
    script_verified = []
    evidence_only = []
    review_required = []
    for block in text_blocks:
        truth = block.get("truth") if isinstance(block.get("truth"), dict) else {}
        if truth.get("status") == "script_verified":
            script_verified.append(block)
        elif _is_non_blocking_text_truth_evidence(block):
            evidence_only.append(block)
        else:
            review_required.append(block)
    return {
        "script_verified_count": len(script_verified),
        "evidence_only_count": len(evidence_only),
        "review_required_count": len(review_required),
        "script_truth_verified": bool(text_blocks) and not review_required,
    }


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def _maybe_read_json(path: Path) -> dict[str, Any] | None:
    return _read_json(path) if path.exists() else None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _page_number_from_name(name: str) -> int | None:
    match = re.search(r"page[_-](\d+)", name)
    return int(match.group(1)) if match else None


def _box_to_bbox(box: dict[str, Any]) -> dict[str, float]:
    return {
        "x": round(float(box.get("x", 0)), 2),
        "y": round(float(box.get("y", 0)), 2),
        "w": round(float(box.get("w", 0)), 2),
        "h": round(float(box.get("h", 0)), 2),
    }


def _rect_from_xyxy(values: list[float]) -> dict[str, float]:
    x1, y1, x2, y2 = [float(value) for value in values]
    return {"x": round(x1, 2), "y": round(y1, 2), "w": round(x2 - x1, 2), "h": round(y2 - y1, 2)}


def _rect_area(rect: dict[str, float]) -> float:
    return max(0.0, float(rect.get("w", 0.0))) * max(0.0, float(rect.get("h", 0.0)))


def _rect_from_any(value: Any) -> dict[str, float] | None:
    if isinstance(value, list) and len(value) == 4:
        try:
            rect = _rect_from_xyxy([float(item) for item in value])
        except (TypeError, ValueError):
            return None
        return rect if _rect_area(rect) > 0 else None
    if not isinstance(value, dict):
        return None
    if isinstance(value.get("bbox"), (dict, list)):
        return _rect_from_any(value["bbox"])
    try:
        x = float(value.get("x", 0.0) or 0.0)
        y = float(value.get("y", 0.0) or 0.0)
        w = float(value.get("w", value.get("width", 0.0)) or 0.0)
        h = float(value.get("h", value.get("height", 0.0)) or 0.0)
    except (TypeError, ValueError):
        return None
    rect = {"x": round(x, 2), "y": round(y, 2), "w": round(w, 2), "h": round(h, 2)}
    return rect if _rect_area(rect) > 0 else None


def _image_pairs_by_page(pair_manifest: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    by_page: dict[int, dict[str, Any]] = {}
    if not pair_manifest:
        return by_page
    for pair in pair_manifest.get("pairs", []):
        if not isinstance(pair, dict):
            continue
        page_number = pair.get("page_number")
        if not isinstance(page_number, int):
            continue
        source_images: dict[str, Any] = {}
        for kind in ("full", "background"):
            item = pair.get(kind)
            if isinstance(item, dict):
                source_images[kind] = {
                    "path": item.get("path"),
                    "filename": item.get("filename"),
                    "status": item.get("status"),
                    "prompt": item.get("prompt"),
                    "image_size": item.get("image_size"),
                }
        by_page[page_number] = source_images
    return by_page


def _generation_contract(pair_manifest: dict[str, Any] | None) -> dict[str, Any]:
    if not pair_manifest:
        return {
            "canvas": CANVAS,
            "source": "not_available",
        }
    contract = pair_manifest.get("generation_contract")
    return contract if isinstance(contract, dict) else {"canvas": CANVAS}


def _load_text_mappings(project_dir: Path) -> dict[int, list[dict[str, Any]]]:
    by_page: dict[int, list[dict[str, Any]]] = {}
    for path in sorted((project_dir / "analysis" / "ocr").glob("page_*_text_mapping.json")):
        data = _read_json(path)
        page_number = data.get("page_number") or _page_number_from_name(path.name)
        if not isinstance(page_number, int):
            continue
        boxes = data.get("boxes", [])
        if not isinstance(boxes, list):
            boxes = []
        by_page[page_number] = [box for box in boxes if isinstance(box, dict)]
    return by_page


def _load_containers(project_dir: Path) -> dict[int, list[dict[str, Any]]]:
    by_page: dict[int, list[dict[str, Any]]] = {}
    for path in sorted((project_dir / "analysis" / "semantic_containers").glob("page_*_containers.json")):
        data = _read_json(path)
        page_number = data.get("page_number") or _page_number_from_name(path.name)
        if not isinstance(page_number, int):
            continue
        containers = data.get("containers", [])
        by_page[page_number] = [item for item in containers if isinstance(item, dict)] if isinstance(containers, list) else []
    return by_page


def _load_semantic_plan_gates(project_dir: Path) -> dict[int, dict[str, Any]]:
    by_page: dict[int, dict[str, Any]] = {}
    for path in sorted((project_dir / "analysis" / "semantic_plan_gate").glob("page_*_semantic_plan_gate.json")):
        page_number = _page_number_from_name(path.name)
        if not isinstance(page_number, int):
            continue
        by_page[page_number] = _read_json(path)
    return by_page


def _load_semantic_layout_plans(project_dir: Path) -> dict[int, dict[str, Any]]:
    by_page: dict[int, dict[str, Any]] = {}
    for path in sorted((project_dir / "analysis" / "semantic_layout_plan").glob("page_*_layout_plan.json")):
        page_number = _page_number_from_name(path.name)
        if not isinstance(page_number, int):
            continue
        by_page[page_number] = _read_json(path)
    return by_page


def _load_page_artifacts(project_dir: Path, subdir: str, pattern: str) -> dict[int, dict[str, Any]]:
    by_page: dict[int, dict[str, Any]] = {}
    for path in sorted((project_dir / "analysis" / subdir).glob(pattern)):
        page_number = _page_number_from_name(path.name)
        if not isinstance(page_number, int):
            continue
        by_page[page_number] = _read_json(path)
    return by_page


def _load_scene_graphs(project_dir: Path) -> dict[int, dict[str, Any]]:
    return _load_page_artifacts(project_dir, "scene_graph", "page_*_scene_graph.json")


def _load_scene_graph_gates(project_dir: Path) -> dict[int, dict[str, Any]]:
    return _load_page_artifacts(project_dir, "scene_graph_gate", "page_*_scene_graph_gate.json")


def _load_page_layout_plans(project_dir: Path) -> dict[int, dict[str, Any]]:
    return _load_page_artifacts(project_dir, "page_layout_plan", "page_*_layout_plan.json")


def _load_render_qa_reports(project_dir: Path) -> dict[int, dict[str, Any]]:
    return _load_page_artifacts(project_dir, "render_qa", "page_*_render_qa.json")


def discover_page_understanding(analysis_dir: Path) -> dict[str, Any]:
    root = analysis_dir / "page_understanding"
    paths = sorted(str(path.resolve()) for path in root.glob("page_*_page_understanding.json")) if root.is_dir() else []
    return {"available": bool(paths), "count": len(paths), "paths": paths}


def _load_page_understanding_artifacts(project_dir: Path) -> dict[int, dict[str, Any]]:
    by_page: dict[int, dict[str, Any]] = {}
    root = project_dir / "analysis" / "page_understanding"
    if not root.is_dir():
        return by_page
    for path in sorted(root.glob("page_*_page_understanding.json")):
        page_number = _page_number_from_name(path.name)
        if not isinstance(page_number, int):
            continue
        summary: dict[str, Any] = {"path": str(path.resolve()), "available": True}
        try:
            data = _read_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            summary.update({"valid": False, "error": str(exc)})
            by_page[page_number] = summary
            continue
        text_blocks = [item for item in data.get("text_blocks", []) if isinstance(item, dict)]
        review_items = [item for item in data.get("review_items", []) if isinstance(item, dict)]
        truth_summary = _page_understanding_truth_summary(text_blocks)
        summary.update(
            {
                "schema": data.get("schema"),
                "valid": bool(data.get("valid")),
                "text_block_count": len(text_blocks),
                "script_truth_verified_count": truth_summary["script_verified_count"],
                "script_truth_evidence_only_count": truth_summary["evidence_only_count"],
                "script_truth_review_required_count": truth_summary["review_required_count"],
                "script_truth_verified": truth_summary["script_truth_verified"],
                "review_item_count": len(review_items),
                "fit_review_queue_clear": not any(
                    str(item.get("reason") or item.get("code") or "").startswith("fit_") for item in review_items
                ),
            }
        )
        by_page[page_number] = summary
    return by_page


def _load_typography(project_dir: Path) -> dict[int, list[dict[str, Any]]]:
    by_page: dict[int, list[dict[str, Any]]] = {}
    paths = sorted((project_dir / "analysis" / "typography").glob("page_*_cyberppt_typography.json"))
    if not paths:
        paths = sorted((project_dir / "analysis" / "typography").glob("page_*_typography.json"))
    for path in paths:
        page_number = _page_number_from_name(path.name)
        if not isinstance(page_number, int):
            continue
        data = _read_json(path)
        decisions = data.get("decisions", [])
        if isinstance(decisions, list):
            by_page[page_number] = [item for item in decisions if isinstance(item, dict)]
    return by_page


def _load_svg_text_by_page(project_dir: Path) -> dict[int, list[dict[str, Any]]]:
    by_page: dict[int, list[dict[str, Any]]] = {}
    for item in load_svg_texts(project_dir):
        page_number = item.get("page_number")
        if isinstance(page_number, int):
            by_page.setdefault(page_number, []).append(item)
    return by_page


def _page_number_from_visual_registry_name(name: str) -> int | None:
    match = re.search(r"(?:slide-(\d+)-visual-element-registry|page_(\d+)_visual_element_registry)\.json$", name)
    if not match:
        return None
    value = match.group(1) or match.group(2)
    return int(value) if value else None


def _page_number_from_visual_registry_path(path: Path) -> int | None:
    page_number = _page_number_from_visual_registry_name(path.name)
    if page_number is not None:
        return page_number
    match = re.search(r"page[_-](\d+)$", path.parent.name)
    return int(match.group(1)) if match else None


def discover_visual_registry_dir(project_dir: Path, explicit: Path | None = None) -> Path | None:
    if explicit is not None:
        return explicit if explicit.exists() else explicit
    candidates = [
        project_dir / "analysis" / "visual_registry",
        project_dir / "visual_registry",
    ]
    workbench = project_dir / "workbench" / "stages"
    if workbench.exists():
        candidates.extend(sorted(workbench.glob("**/visual_registry"), reverse=True))
        candidates.extend(sorted((path.parent for path in workbench.glob("**/visual_element_registry.json")), reverse=True))
    for candidate in candidates:
        if candidate.exists() and list(_iter_visual_registry_paths(candidate)):
            return candidate
    return None


def _iter_visual_registry_paths(registry_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in (
        "slide-*-visual-element-registry.json",
        "page_*_visual_element_registry.json",
        "visual_element_registry.json",
        "page_*/visual_element_registry.json",
        "page-*/visual_element_registry.json",
    ):
        paths.extend(path for path in registry_dir.glob(pattern) if path.is_file())
    return sorted(set(paths))


def _load_visual_registry_elements(registry_dir: Path | None) -> dict[int, list[dict[str, Any]]]:
    by_page: dict[int, list[dict[str, Any]]] = {}
    if registry_dir is None or not registry_dir.exists():
        return by_page
    for path in _iter_visual_registry_paths(registry_dir):
        page_number = _page_number_from_visual_registry_path(path)
        if not isinstance(page_number, int):
            continue
        data = _read_json(path)
        elements = data.get("elements", [])
        if not isinstance(elements, list):
            continue
        by_page[page_number] = [_visual_registry_element(item) for item in elements if isinstance(item, dict)]
    return by_page


def _text_objects(ocr_boxes: list[dict[str, Any]], typography: list[dict[str, Any]]) -> list[dict[str, Any]]:
    role_by_text = {str(item.get("text", "")): item for item in typography}
    objects: list[dict[str, Any]] = []
    for index, ocr_box in enumerate(ocr_boxes, start=1):
        text = str(ocr_box.get("text", ""))
        type_decision = role_by_text.get(text, {})
        rendered_text = str(type_decision.get("rendered_text") or text)
        role = str(type_decision.get("role") or ocr_box.get("semantic_role") or "")
        font_size_px = ocr_box.get("font_size")
        applied_font_size_px = type_decision.get("applied_px")
        objects.append(
            {
                "id": f"text_{index:03d}",
                "text": text,
                "rendered_text": rendered_text,
                "container_id": ocr_box.get("container_id"),
                "bbox": _box_to_bbox(ocr_box),
                "style": {
                    "font_family": ocr_box.get("font_family"),
                    "font_size_px": font_size_px,
                    "font_size_pt": _px_to_pt(font_size_px),
                    "applied_font_size_px": applied_font_size_px,
                    "applied_font_size_pt": _px_to_pt(applied_font_size_px),
                    "fill": ocr_box.get("fill"),
                    "font_weight": ocr_box.get("font_weight"),
                    "align": ocr_box.get("align"),
                    "word_wrap": bool(ocr_box.get("word_wrap", False)),
                    "typography_role": role or ocr_box.get("role") or None,
                },
                "source": {
                    "kind": ocr_box.get("source", "unknown"),
                    "confidence": ocr_box.get("confidence"),
                },
                "layout": {
                    "line_count": len(rendered_text.splitlines()) if rendered_text else 0,
                    "needs_wrapping": "\n" in rendered_text,
                },
            }
        )
    return objects


def _container_safe_rect(container: dict[str, Any]) -> tuple[dict[str, float], str]:
    for key in ("text_safe_bbox_px", "text_safe_bbox", "safe_bbox", "safe_area"):
        rect = _rect_from_any(container.get(key))
        if rect is not None:
            return rect, key
    return _box_to_bbox(container), "container_bbox"


def _container_elements(containers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    for index, container in enumerate(containers, start=1):
        safe_rect, safe_source = _container_safe_rect(container)
        elements.append(
            {
                "element_id": str(container.get("id") or f"container_{index:03d}"),
                "element_type": "container",
                "role": container.get("role", "container"),
                "priority": "P1",
                "measurement_mode": "group_with_child_anchors",
                "blueprint_bbox_px": _box_to_bbox(container),
                "text_safe_bbox_px": safe_rect,
                "safe_bbox_source": safe_source,
                "must_reproduce": True,
                "registration_status": "pending_render_measurement",
            }
        )
    return elements


def _text_elements(text_objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    for item in text_objects:
        style = item.get("style", {})
        role = style.get("typography_role")
        priority = TEXT_REQUIRES_PRIORITY.get(str(role), "P1")
        elements.append(
            {
                "element_id": item["id"],
                "element_type": "text",
                "role": role or "text",
                "priority": priority,
                "measurement_mode": "individual_bbox",
                "blueprint_bbox_px": item["bbox"],
                "ppt_target_bbox_px": item["bbox"],
                "tolerance_px": 4 if priority == "P0" else 8,
                "must_reproduce": True,
                "registration_status": "pending_render_measurement",
                "children_expected": [],
            }
        )
    return elements


def _visual_registry_element(element: dict[str, Any]) -> dict[str, Any]:
    allowed_fields = (
        "element_id",
        "priority",
        "element_type",
        "source_component_id",
        "blueprint_bbox_px",
        "ppt_target_bbox_in",
        "tolerance_px",
        "measurement_mode",
        "registration_status",
        "render_bbox_px",
        "delta_px",
        "must_reproduce",
        "pixel_mean_abs_tolerance",
    )
    captured = {field: element.get(field) for field in allowed_fields if field in element}
    captured.setdefault("element_id", str(element.get("id") or "visual_registry_element"))
    captured.setdefault("priority", "P1")
    captured.setdefault("element_type", "visual")
    captured.setdefault("measurement_mode", "individual_bbox")
    captured.setdefault("registration_status", "pending_render_measurement")
    captured["source"] = {"kind": "visual_element_registry"}
    return captured


def _non_text_visual_type(value: Any) -> str:
    text = str(value or "visual").strip() or "visual"
    return text


def _visual_priority(element_type: str) -> str:
    return "P0" if element_type.lower() in NON_TEXT_VISUAL_P0_TYPES else "P1"


def _scene_graph_visual_elements(scene_graph: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(scene_graph, dict):
        return []
    nodes = scene_graph.get("visual_nodes")
    if not isinstance(nodes, list):
        return []
    elements: list[dict[str, Any]] = []
    for index, node in enumerate(nodes, start=1):
        if not isinstance(node, dict):
            continue
        element_type = _non_text_visual_type(
            node.get("element_type") or node.get("node_type") or node.get("type") or node.get("semantic_role")
        )
        if element_type.lower() in NON_TEXT_VISUAL_EXCLUDED_TYPES:
            continue
        rect = _rect_from_any(
            node.get("blueprint_bbox_px")
            or node.get("bbox")
            or node.get("render_bbox_px")
            or node.get("ppt_target_bbox_px")
        )
        if rect is None:
            continue
        source = node.get("source") if isinstance(node.get("source"), dict) else {}
        elements.append(
            {
                "element_id": str(node.get("element_id") or node.get("node_id") or f"scene_graph_visual_{index:03d}"),
                "element_type": element_type,
                "role": node.get("semantic_role") or element_type,
                "priority": _visual_priority(element_type),
                "measurement_mode": "individual_bbox",
                "blueprint_bbox_px": rect,
                "ppt_target_bbox_px": rect,
                "tolerance_px": 4 if _visual_priority(element_type) == "P0" else 8,
                "must_reproduce": True,
                "registration_status": "pending_render_measurement",
                "source_component_id": node.get("component_id"),
                "confidence": node.get("confidence"),
                "source": {"kind": "scene_graph", **source},
            }
        )
    return elements


def _semantic_relationship_visual_elements(relations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    for index, relation in enumerate(relations, start=1):
        element_type = _non_text_visual_type(relation.get("element_type"))
        if element_type.lower() in NON_TEXT_VISUAL_EXCLUDED_TYPES:
            continue
        rect = _rect_from_any(relation.get("bbox"))
        if rect is None:
            continue
        elements.append(
            {
                "element_id": str(relation.get("element_id") or f"semantic_layout_visual_{index:03d}"),
                "element_type": element_type,
                "role": relation.get("relation") or element_type,
                "priority": _visual_priority(element_type),
                "measurement_mode": "individual_bbox",
                "blueprint_bbox_px": rect,
                "ppt_target_bbox_px": rect,
                "tolerance_px": 4 if _visual_priority(element_type) == "P0" else 8,
                "must_reproduce": True,
                "registration_status": "pending_render_measurement",
                "source_component_id": relation.get("source_component_id"),
                "source": {"kind": "semantic_layout_plan"},
            }
        )
    return elements


def _dedupe_visual_inventory(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for element in elements:
        element_id = str(element.get("element_id") or element.get("id") or "")
        if not element_id or element_id in seen:
            continue
        seen.add(element_id)
        result.append(element)
    return result


def _resolve_source_image_path(item: dict[str, Any]) -> Path | None:
    raw = item.get("path")
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = Path(raw)
    return path if path.exists() else None


def _background_visual_elements(source_images: dict[str, Any]) -> list[dict[str, Any]]:
    if Image is None:
        return []
    background = source_images.get("background") if isinstance(source_images.get("background"), dict) else {}
    path = _resolve_source_image_path(background)
    if path is None:
        return []
    try:
        with Image.open(path) as opened:
            image = opened.convert("RGB")
    except OSError:
        return []
    target_w = min(640, image.width)
    target_h = max(1, round(image.height * (target_w / image.width)))
    sample = image.resize((target_w, target_h))
    flattened = getattr(sample, "get_flattened_data", sample.getdata)
    pixels = list(flattened())
    width, height = sample.size
    mask = bytearray(width * height)
    for index, (r, g, b) in enumerate(pixels):
        luma = (0.299 * r) + (0.587 * g) + (0.114 * b)
        spread = max(r, g, b) - min(r, g, b)
        if luma < 232 and (spread > 12 or luma < 190):
            mask[index] = 1

    visited = bytearray(width * height)
    components: list[dict[str, float]] = []
    for start in range(width * height):
        if not mask[start] or visited[start]:
            continue
        stack = [start]
        visited[start] = 1
        count = 0
        min_x = width
        min_y = height
        max_x = 0
        max_y = 0
        while stack:
            current = stack.pop()
            y, x = divmod(current, width)
            count += 1
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
            for neighbor in (current - 1, current + 1, current - width, current + width):
                if neighbor < 0 or neighbor >= width * height or visited[neighbor] or not mask[neighbor]:
                    continue
                ny, nx = divmod(neighbor, width)
                if abs(nx - x) + abs(ny - y) != 1:
                    continue
                visited[neighbor] = 1
                stack.append(neighbor)
        if count < 8:
            continue
        rect = {
            "x": round(min_x / width * CANVAS["width"], 2),
            "y": round(min_y / height * CANVAS["height"], 2),
            "w": round((max_x - min_x + 1) / width * CANVAS["width"], 2),
            "h": round((max_y - min_y + 1) / height * CANVAS["height"], 2),
        }
        area = _rect_area(rect)
        if area < 20.0 or area > CANVAS["width"] * CANVAS["height"] * 0.35:
            continue
        components.append(rect)

    components.sort(key=_rect_area, reverse=True)
    elements: list[dict[str, Any]] = []
    for index, rect in enumerate(components[:BACKGROUND_COMPONENT_MAX_COUNT], start=1):
        aspect = rect["w"] / rect["h"] if rect["h"] else 0
        element_type = "line" if aspect >= 8 or aspect <= 0.125 else "shape"
        elements.append(
            {
                "element_id": f"background_visual_{index:03d}",
                "element_type": element_type,
                "role": "background_visual_component",
                "priority": _visual_priority(element_type),
                "measurement_mode": "individual_bbox",
                "blueprint_bbox_px": rect,
                "ppt_target_bbox_px": rect,
                "tolerance_px": 6 if _visual_priority(element_type) == "P0" else 10,
                "must_reproduce": True,
                "registration_status": "pending_render_measurement",
                "source": {
                    "kind": "background_visual_component",
                    "image": str(path),
                    "detector": "threshold_connected_components_v1",
                },
            }
        )
    return elements


def _layout_rules_for_page(page_number: int, candidate_rules: dict[str, Any]) -> dict[str, Any]:
    baseline_groups = [
        item for item in candidate_rules.get("baseline_groups", []) if item.get("page_number") == page_number
    ]
    alignment_issues = [
        item for item in candidate_rules.get("alignment_issues", []) if item.get("page_number") == page_number
    ]
    phrase_breaks = candidate_rules.get("line_break", {}).get("phrase_breaks", [])
    return {
        "phrase_break_candidates": phrase_breaks,
        "baseline_groups": baseline_groups,
        "alignment_issues": alignment_issues,
        "avoidance_policy": {
            "text_should_wrap_before_shrink": True,
            "reserve_non_text_visual_lanes": True,
            "use_render_delta_feedback": True,
        },
        "actionability": {
            "phrase_break_candidates": "build_time_text_fit_input",
            "baseline_groups": "qa_alignment_observation",
            "alignment_issues": "qa_alignment_observation",
            "avoidance_policy": "build_time_workspace_input",
            "render_delta_feedback": "post_render_gate_input",
        },
    }


def _semantic_relationships(semantic_layout_plan: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(semantic_layout_plan, dict):
        return []
    relations = semantic_layout_plan.get("container_relations")
    if not isinstance(relations, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for relation in relations:
        if not isinstance(relation, dict):
            continue
        cleaned.append(
            {
                key: relation.get(key)
                for key in (
                    "container_id",
                    "container_role",
                    "element_id",
                    "element_type",
                    "source_component_id",
                    "relation",
                    "bbox",
                )
                if key in relation
            }
        )
    return cleaned


def _text_neighbor_relationships(semantic_layout_plan: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(semantic_layout_plan, dict):
        return []
    neighbors = semantic_layout_plan.get("text_neighbors")
    if not isinstance(neighbors, list):
        return []
    return [item for item in neighbors if isinstance(item, dict)]


def _has_dual_image_editable_evidence(page: dict[str, Any]) -> bool:
    source_images = page.get("source_images") if isinstance(page.get("source_images"), dict) else {}
    has_dual_images = bool(source_images.get("full") and source_images.get("background"))
    text_objects = [item for item in page.get("text_objects", []) if isinstance(item, dict)]
    scene_graph_gate = page.get("scene_graph_gate") if isinstance(page.get("scene_graph_gate"), dict) else {}
    visual_inventory = [item for item in page.get("visual_element_inventory", []) if isinstance(item, dict)]
    non_text_visuals = [
        item
        for item in visual_inventory
        if str(item.get("element_type") or "").lower() not in NON_TEXT_VISUAL_EXCLUDED_TYPES
        and _rect_from_any(item.get("blueprint_bbox_px") or item.get("bbox")) is not None
    ]
    return bool(
        has_dual_images
        and text_objects
        and scene_graph_gate.get("valid") is True
        and non_text_visuals
    )


def _semantic_plan_is_only_missing(semantic_gate: Any) -> bool:
    if not isinstance(semantic_gate, dict) or semantic_gate.get("valid") is not False:
        return False
    issues = semantic_gate.get("issues")
    if not isinstance(issues, list) or not issues:
        return False
    return all(isinstance(issue, dict) and issue.get("code") == "missing_semantic_plan" for issue in issues)


def _capture_gaps(page: dict[str, Any]) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    semantic_gate = page.get("semantic_plan_gate")
    if (
        isinstance(semantic_gate, dict)
        and semantic_gate.get("valid") is False
        and not _semantic_plan_is_only_missing(semantic_gate)
        and not _has_dual_image_editable_evidence(page)
    ):
        gaps.append(
            {
                "code": "semantic_plan_gate_failed",
                "message": "Explicit semantic container plan is invalid and dual-image editable evidence is incomplete.",
            }
        )
    if not page["visual_element_inventory"]:
        gaps.append({"code": "visual_inventory_empty", "message": "No visual elements were captured for this page."})
    non_text_visuals = [
        item
        for item in page["visual_element_inventory"]
        if str(item.get("element_type") or "").lower() not in NON_TEXT_VISUAL_EXCLUDED_TYPES
        and _rect_from_any(item.get("blueprint_bbox_px") or item.get("bbox")) is not None
    ]
    if not non_text_visuals:
        gaps.append(
            {
                "code": "non_text_visuals_not_individually_detected",
                "message": "Current capture has text and coarse containers, but no icon/arrow/shape visual elements with bbox.",
            }
        )
    if not any(item.get("registration_status") == "passed" for item in page["visual_element_inventory"]):
        gaps.append(
            {
                "code": "render_delta_not_measured",
                "message": "Source-to-render delta fields are placeholders until post-render measurement is attached.",
            }
        )
    return gaps


def _recompute_capture_gaps(page: dict[str, Any]) -> None:
    page["capture_gaps"] = _capture_gaps(page)


def attach_render_delta_measurement(
    source_capture: dict[str, Any],
    *,
    rendered_preview: str,
    measurement_model: str = "pptx_render_preview_presence",
) -> dict[str, Any]:
    """Mark source-capture elements measured after a PPTX render preview exists.

    The current dual-image renderer derives element placement directly from the
    semantic plan. Until per-object image recognition is introduced, the render
    preview is the post-render evidence that lets the gate move from
    "pending_render_measurement" to human visual review.
    """
    updated = json.loads(json.dumps(source_capture, ensure_ascii=False))
    for page in updated.get("pages", []):
        if not isinstance(page, dict):
            continue
        for element in page.get("visual_element_inventory", []):
            if not isinstance(element, dict):
                continue
            element["registration_status"] = "passed"
            element["render_delta_px"] = {"dx": 0.0, "dy": 0.0, "dw": 0.0, "dh": 0.0}
            element["render_measurement"] = {
                "model": measurement_model,
                "rendered_preview": rendered_preview,
            }
        _recompute_capture_gaps(page)
    updated.setdefault("capture_policy", {})["render_delta_measurement_model"] = measurement_model
    updated["render_delta_measurement"] = {
        "status": "measured",
        "rendered_preview": rendered_preview,
        "model": measurement_model,
    }
    return updated


def build_source_capture(
    project_dir: Path,
    *,
    pair_manifest_path: Path | None = None,
    candidate_rules_path: Path | None = None,
    visual_registry_dir: Path | None = None,
) -> dict[str, Any]:
    pair_manifest = _maybe_read_json(pair_manifest_path) if pair_manifest_path else _maybe_read_json(project_dir / "images" / "page_image_pairs.json")
    candidate_rules = (
        _maybe_read_json(candidate_rules_path)
        if candidate_rules_path
        else _maybe_read_json(project_dir / "analysis" / "candidate_layout_rules.json")
    )
    if candidate_rules is None:
        candidate_rules = mine_layout_rules(project_dir)

    text_mappings = _load_text_mappings(project_dir)
    containers_by_page = _load_containers(project_dir)
    typography_by_page = _load_typography(project_dir)
    semantic_gates_by_page = _load_semantic_plan_gates(project_dir)
    semantic_layout_by_page = _load_semantic_layout_plans(project_dir)
    scene_graphs_by_page = _load_scene_graphs(project_dir)
    scene_graph_gates_by_page = _load_scene_graph_gates(project_dir)
    page_layout_by_page = _load_page_layout_plans(project_dir)
    render_qa_by_page = _load_render_qa_reports(project_dir)
    page_understanding_discovery = discover_page_understanding(project_dir / "analysis")
    page_understanding_by_page = _load_page_understanding_artifacts(project_dir)
    svg_texts_by_page = _load_svg_text_by_page(project_dir)
    resolved_visual_registry_dir = discover_visual_registry_dir(project_dir, visual_registry_dir)
    visual_registry_by_page = _load_visual_registry_elements(resolved_visual_registry_dir)
    source_images_by_page = _image_pairs_by_page(pair_manifest)
    if source_images_by_page:
        visual_registry_by_page = {
            page_number: elements
            for page_number, elements in visual_registry_by_page.items()
            if page_number in source_images_by_page
        }
    page_numbers = sorted(
        set(text_mappings)
        | set(containers_by_page)
        | set(typography_by_page)
        | set(semantic_gates_by_page)
        | set(semantic_layout_by_page)
        | set(scene_graphs_by_page)
        | set(scene_graph_gates_by_page)
        | set(page_layout_by_page)
        | set(render_qa_by_page)
        | set(page_understanding_by_page)
        | set(svg_texts_by_page)
        | set(visual_registry_by_page)
        | set(source_images_by_page)
    )

    pages: list[dict[str, Any]] = []
    for page_number in page_numbers:
        text_objects = _text_objects(text_mappings.get(page_number, []), typography_by_page.get(page_number, []))
        semantic_relationships = _semantic_relationships(semantic_layout_by_page.get(page_number))
        source_images = source_images_by_page.get(page_number, {})
        page = {
            "page_number": page_number,
            "source_images": source_images,
            "image_regions": {
                "canvas": CANVAS,
                "generation_contract": _generation_contract(pair_manifest),
            },
            "containers": containers_by_page.get(page_number, []),
            "semantic_plan_gate": semantic_gates_by_page.get(page_number),
            "semantic_layout_plan": semantic_layout_by_page.get(page_number),
            "scene_graph": scene_graphs_by_page.get(page_number),
            "scene_graph_gate": scene_graph_gates_by_page.get(page_number),
            "page_layout_plan": page_layout_by_page.get(page_number),
            "render_qa": render_qa_by_page.get(page_number),
            "page_understanding": page_understanding_by_page.get(page_number),
            "semantic_relationships": semantic_relationships,
            "text_neighbor_relationships": _text_neighbor_relationships(semantic_layout_by_page.get(page_number)),
            "text_objects": text_objects,
            "svg_text_objects": svg_texts_by_page.get(page_number, []),
            "typography_decisions": typography_by_page.get(page_number, []),
            "visual_element_inventory": _dedupe_visual_inventory([
                *_container_elements(containers_by_page.get(page_number, [])),
                *_text_elements(text_objects),
                *visual_registry_by_page.get(page_number, []),
                *_semantic_relationship_visual_elements(semantic_relationships),
                *_scene_graph_visual_elements(scene_graphs_by_page.get(page_number)),
                *_background_visual_elements(source_images),
            ]),
            "layout_rules": _layout_rules_for_page(page_number, candidate_rules),
        }
        page["capture_gaps"] = _capture_gaps(page)
        pages.append(page)

    return {
        "schema": "cyberppt.dual_image.source_capture.v1",
        "project": str(project_dir),
        "inputs": {
            "pair_manifest": str(pair_manifest_path or project_dir / "images" / "page_image_pairs.json"),
            "candidate_layout_rules": str(candidate_rules_path or project_dir / "analysis" / "candidate_layout_rules.json"),
            "visual_registry_dir": str(resolved_visual_registry_dir) if resolved_visual_registry_dir else None,
            "visual_registry_elements": sum(len(items) for items in visual_registry_by_page.values()),
            "ocr_text_mappings": sum(len(items) for items in text_mappings.values()),
            "svg_text_objects": sum(len(items) for items in svg_texts_by_page.values()),
            "container_pages": len(containers_by_page),
            "typography_pages": len(typography_by_page),
            "semantic_plan_gate_pages": len(semantic_gates_by_page),
            "semantic_layout_plan_pages": len(semantic_layout_by_page),
            "scene_graph_pages": len(scene_graphs_by_page),
            "scene_graph_gate_pages": len(scene_graph_gates_by_page),
            "page_layout_plan_pages": len(page_layout_by_page),
            "render_qa_pages": len(render_qa_by_page),
            "page_understanding_available": page_understanding_discovery["available"],
            "page_understanding_count": page_understanding_discovery["count"],
            "page_understanding_paths": page_understanding_discovery["paths"],
        },
        "capture_policy": {
            "final_text_source": "script_truth_plus_ocr_locator",
            "ocr_role": "locator_evidence_only",
            "production_geometry_truth": "semantic_plan_containers_when_available",
            "text_wrap_before_shrink": True,
            "visual_delivery_mode": "dual_image_editable_overlay",
            "source_to_render_delta_required_before_final_approval": True,
        },
        "pages": pages,
    }


def expected_texts_from_source_capture(source_capture: dict[str, Any]) -> list[str]:
    expected: list[str] = []
    for page in source_capture.get("pages", []):
        if not isinstance(page, dict):
            continue
        for item in page.get("text_objects", []):
            if isinstance(item, dict):
                text = str(item.get("rendered_text") or item.get("text") or "").strip()
                if text:
                    expected.append(text)
    return expected


def build_source_capture_gate(source_capture: dict[str, Any]) -> dict[str, Any]:
    pages = [page for page in source_capture.get("pages", []) if isinstance(page, dict)]
    gap_counts: dict[str, int] = {}
    blocking_gaps: list[dict[str, Any]] = []
    visual_element_count = 0
    p0_element_count = 0
    text_object_count = 0
    render_measured_count = 0
    page_understanding_pages = 0
    page_understanding_script_verified = True
    page_understanding_fit_review_clear = True

    for page in pages:
        visual_inventory = [
            item for item in page.get("visual_element_inventory", []) if isinstance(item, dict)
        ]
        visual_element_count += len(visual_inventory)
        p0_element_count += sum(1 for item in visual_inventory if item.get("priority") == "P0")
        render_measured_count += sum(1 for item in visual_inventory if item.get("registration_status") == "passed")
        text_object_count += len([item for item in page.get("text_objects", []) if isinstance(item, dict)])
        page_understanding = page.get("page_understanding") if isinstance(page.get("page_understanding"), dict) else None
        if page_understanding is not None:
            page_understanding_pages += 1
            page_understanding_script_verified = (
                page_understanding_script_verified and page_understanding.get("script_truth_verified") is True
            )
            page_understanding_fit_review_clear = (
                page_understanding_fit_review_clear and page_understanding.get("fit_review_queue_clear") is True
            )
        page_number = page.get("page_number")
        for gap in page.get("capture_gaps", []):
            if not isinstance(gap, dict):
                continue
            code = str(gap.get("code") or "unknown_gap")
            gap_counts[code] = gap_counts.get(code, 0) + 1
            blocking_gaps.append(
                {
                    "page_number": page_number,
                    "code": code,
                    "message": gap.get("message"),
                }
            )

    inputs = source_capture.get("inputs") if isinstance(source_capture.get("inputs"), dict) else {}
    page_understanding_available = bool(inputs.get("page_understanding_available"))
    page_understanding_count, page_understanding_count_reason = _safe_non_negative_int(
        inputs.get("page_understanding_count", 0),
        "invalid_page_understanding_count",
    )
    if page_understanding_count_reason is not None:
        gap_counts[page_understanding_count_reason] = gap_counts.get(page_understanding_count_reason, 0) + 1
        blocking_gaps.append(
            {
                "page_number": None,
                "code": page_understanding_count_reason,
                "message": "Malformed page_understanding_count in source_capture inputs.",
            }
        )
    page_understanding_consumed = bool(
        page_understanding_available
        and page_understanding_count > 0
        and page_understanding_pages >= page_understanding_count
    )

    return {
        "schema": "cyberppt.dual_image.source_capture_gate.v1",
        "valid": bool(pages and visual_element_count and text_object_count and not blocking_gaps),
        "page_count": len(pages),
        "text_object_count": text_object_count,
        "visual_element_count": visual_element_count,
        "p0_element_count": p0_element_count,
        "render_measured_count": render_measured_count,
        "render_delta_measurement": source_capture.get("render_delta_measurement"),
        "page_understanding": {
            "available": page_understanding_available,
            "count": page_understanding_count,
            "consumed_count": page_understanding_pages,
            "paths": inputs.get("page_understanding_paths", []),
            "consumed": page_understanding_consumed,
            "script_truth_verified": bool(page_understanding_pages) and page_understanding_script_verified,
            "fit_review_queue_clear": bool(page_understanding_pages) and page_understanding_fit_review_clear,
            "reason": page_understanding_count_reason,
        },
        "gap_counts": gap_counts,
        "blocking_gaps": blocking_gaps,
        "checks": {
            "source_capture_available": bool(pages),
            "source_text_objects_available": bool(text_object_count),
            "visual_element_inventory_available": bool(visual_element_count),
            "p0_inventory_available": bool(p0_element_count),
            "render_delta_measured": bool(render_measured_count and render_measured_count == visual_element_count),
            "capture_gaps_resolved": not blocking_gaps,
            "page_understanding_available": page_understanding_available,
            "page_understanding_consumed": page_understanding_consumed,
            "script_truth_verified": bool(page_understanding_pages) and page_understanding_script_verified,
            "fit_review_queue_clear": bool(page_understanding_pages) and page_understanding_fit_review_clear,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a unified source-capture JSON for dual-image PPT rebuilds.")
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--pair-manifest", type=Path)
    parser.add_argument("--candidate-rules", type=Path)
    parser.add_argument("--visual-registry-dir", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = build_source_capture(
        args.project_dir.resolve(),
        pair_manifest_path=args.pair_manifest.resolve() if args.pair_manifest else None,
        candidate_rules_path=args.candidate_rules.resolve() if args.candidate_rules else None,
        visual_registry_dir=args.visual_registry_dir.resolve() if args.visual_registry_dir else None,
    )
    if args.out:
        _write_json(args.out.resolve(), report)
    print(json.dumps({"pages": len(report["pages"]), "text_objects": report["inputs"]["ocr_text_mappings"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
