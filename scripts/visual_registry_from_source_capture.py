#!/usr/bin/env python3
"""Build draft visual element registries from source_capture visual inventory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PPT_CANVAS_IN = {"w": 13.333, "h": 7.5}
DEFAULT_CANVAS = {"width": 1280.0, "height": 720.0}
EXCLUDED_ELEMENT_TYPES = {"container", "text", "text_box", "text_object", "text_zone", "label_zone"}


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _rect(value: Any) -> dict[str, float] | None:
    if isinstance(value, list) and len(value) == 4:
        try:
            x1, y1, x2, y2 = [float(item) for item in value]
        except (TypeError, ValueError):
            return None
        return {"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1}
    if not isinstance(value, dict):
        return None
    if isinstance(value.get("bbox"), (dict, list)):
        return _rect(value["bbox"])
    try:
        rect = {
            "x": float(value.get("x", 0.0) or 0.0),
            "y": float(value.get("y", 0.0) or 0.0),
            "w": float(value.get("w", value.get("width", 0.0)) or 0.0),
            "h": float(value.get("h", value.get("height", 0.0)) or 0.0),
        }
    except (TypeError, ValueError):
        return None
    if rect["w"] <= 0 or rect["h"] <= 0:
        return None
    return {key: round(value, 3) for key, value in rect.items()}


def _ppt_bbox(rect: dict[str, float], canvas: dict[str, float]) -> dict[str, float]:
    width = float(canvas.get("width") or DEFAULT_CANVAS["width"])
    height = float(canvas.get("height") or DEFAULT_CANVAS["height"])
    return {
        "x": round(rect["x"] / width * PPT_CANVAS_IN["w"], 4),
        "y": round(rect["y"] / height * PPT_CANVAS_IN["h"], 4),
        "w": round(rect["w"] / width * PPT_CANVAS_IN["w"], 4),
        "h": round(rect["h"] / height * PPT_CANVAS_IN["h"], 4),
    }


def _source_kind(item: dict[str, Any]) -> str:
    source = item.get("source")
    if isinstance(source, dict):
        value = source.get("kind")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "visual_element_inventory"


def _candidate_elements(page: dict[str, Any], canvas: dict[str, float]) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(page.get("visual_element_inventory", []), start=1):
        if not isinstance(item, dict):
            continue
        element_type = str(item.get("element_type") or item.get("type") or item.get("role") or "visual")
        if element_type.lower() in EXCLUDED_ELEMENT_TYPES:
            continue
        bbox = _rect(item.get("blueprint_bbox_px") or item.get("bbox"))
        if bbox is None:
            continue
        element_id = str(item.get("element_id") or item.get("id") or f"visual_{index:03d}")
        if element_id in seen:
            continue
        seen.add(element_id)
        priority = item.get("priority") if item.get("priority") in {"P0", "P1", "P2"} else "P1"
        element = {
            "element_id": element_id,
            "priority": priority,
            "element_type": element_type,
            "source_component_id": item.get("source_component_id"),
            "blueprint_bbox_px": bbox,
            "ppt_target_bbox_in": _ppt_bbox(bbox, canvas),
            "tolerance_px": item.get("tolerance_px") or (3 if priority == "P0" else 4 if priority == "P1" else 6),
            "measurement_mode": item.get("measurement_mode") or "individual_bbox",
            "registration_status": item.get("registration_status") or "pending_render_measurement",
            "must_reproduce": item.get("must_reproduce", True),
            "source": {
                "kind": "source_capture_inventory",
                "inventory_source": _source_kind(item),
            },
        }
        if "pixel_mean_abs_tolerance" in item:
            element["pixel_mean_abs_tolerance"] = item["pixel_mean_abs_tolerance"]
        elements.append(element)
    return elements


def build_registry_for_page(source_capture: dict[str, Any], page: dict[str, Any]) -> dict[str, Any]:
    image_regions = page.get("image_regions") if isinstance(page.get("image_regions"), dict) else {}
    canvas = image_regions.get("canvas") if isinstance(image_regions.get("canvas"), dict) else DEFAULT_CANVAS
    elements = _candidate_elements(page, canvas)
    source_images = page.get("source_images") if isinstance(page.get("source_images"), dict) else {}
    full = source_images.get("full") if isinstance(source_images.get("full"), dict) else {}
    return {
        "schema": "cyberppt.visual_element_registry.v1",
        "registry_status": "draft_from_source_capture",
        "page_number": page.get("page_number"),
        "blueprint_path": full.get("path"),
        "blueprint_canvas_px": {"w": canvas.get("width", DEFAULT_CANVAS["width"]), "h": canvas.get("height", DEFAULT_CANVAS["height"])},
        "ppt_canvas_in": PPT_CANVAS_IN,
        "elements": elements,
        "element_count": len(elements),
        "coverage_check": {
            "manual_annotations_required": True,
            "passed": bool(elements),
            "source_capture_project": source_capture.get("project"),
            "status": "draft_requires_human_or_visual_qa_confirmation",
        },
    }


def build_registries(source_capture: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        build_registry_for_page(source_capture, page)
        for page in source_capture.get("pages", [])
        if isinstance(page, dict)
    ]


def write_registries(registries: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    written: list[Path] = []
    for registry in registries:
        page_number = registry.get("page_number")
        if not isinstance(page_number, int):
            continue
        paths = [
            out_dir / f"slide-{page_number:02d}-visual-element-registry.json",
            out_dir / f"page_{page_number:03d}_visual_element_registry.json",
        ]
        for path in paths:
            _write_json(path, registry)
            written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Create draft visual registries from source_capture.json.")
    parser.add_argument("--source-capture", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    source_capture = _read_json(args.source_capture)
    registries = build_registries(source_capture)
    written = write_registries(registries, args.out_dir)
    print(json.dumps({"registries": len(registries), "files": [str(path) for path in written]}, ensure_ascii=False, indent=2))
    return 0 if any(registry.get("element_count", 0) for registry in registries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
