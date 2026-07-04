from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from .layout_rule_miner import load_ocr_boxes, load_svg_texts, mine_layout_rules


CANVAS = {"width": 1280, "height": 720}
TEXT_REQUIRES_PRIORITY = {"T2": "P0", "T4": "P0", "T6": "P0", "T8": "P0", "T13": "P0"}


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


def _text_objects(boxes: list[dict[str, Any]], typography: list[dict[str, Any]]) -> list[dict[str, Any]]:
    role_by_text = {str(item.get("text", "")): item for item in typography}
    objects: list[dict[str, Any]] = []
    for index, box in enumerate(boxes, start=1):
        text = str(box.get("text", ""))
        type_decision = role_by_text.get(text, {})
        rendered_text = str(type_decision.get("rendered_text") or text)
        role = str(type_decision.get("role") or box.get("semantic_role") or "")
        objects.append(
            {
                "id": f"text_{index:03d}",
                "text": text,
                "rendered_text": rendered_text,
                "bbox": _box_to_bbox(box),
                "style": {
                    "font_family": box.get("font_family"),
                    "font_size_px": box.get("font_size"),
                    "applied_font_size_px": type_decision.get("applied_px"),
                    "fill": box.get("fill"),
                    "font_weight": box.get("font_weight"),
                    "align": box.get("align"),
                    "word_wrap": bool(box.get("word_wrap", False)),
                    "typography_role": role or None,
                },
                "source": {
                    "kind": box.get("source", "unknown"),
                    "confidence": box.get("confidence"),
                },
                "layout": {
                    "line_count": len(rendered_text.splitlines()) if rendered_text else 0,
                    "needs_wrapping": "\n" in rendered_text,
                },
            }
        )
    return objects


def _container_elements(containers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    for index, container in enumerate(containers, start=1):
        elements.append(
            {
                "element_id": str(container.get("id") or f"container_{index:03d}"),
                "element_type": "container",
                "role": container.get("role", "container"),
                "priority": "P1",
                "measurement_mode": "group_with_child_anchors",
                "blueprint_bbox_px": _box_to_bbox(container),
                "text_safe_bbox_px": _box_to_bbox(
                    {
                        "x": container.get("x"),
                        "y": container.get("y"),
                        "w": container.get("w"),
                        "h": container.get("h"),
                    }
                ),
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
    }


def _capture_gaps(page: dict[str, Any]) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    if not page["visual_element_inventory"]:
        gaps.append({"code": "visual_inventory_empty", "message": "No visual elements were captured for this page."})
    if not any(item["element_type"] != "text" for item in page["visual_element_inventory"]):
        gaps.append(
            {
                "code": "non_text_visuals_not_individually_detected",
                "message": "Current capture has text and coarse containers, but no icon/arrow/shape object detector yet.",
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


def build_source_capture(
    project_dir: Path,
    *,
    pair_manifest_path: Path | None = None,
    candidate_rules_path: Path | None = None,
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
    svg_texts_by_page = _load_svg_text_by_page(project_dir)
    source_images_by_page = _image_pairs_by_page(pair_manifest)
    page_numbers = sorted(
        set(text_mappings)
        | set(containers_by_page)
        | set(typography_by_page)
        | set(svg_texts_by_page)
        | set(source_images_by_page)
    )

    pages: list[dict[str, Any]] = []
    for page_number in page_numbers:
        text_objects = _text_objects(text_mappings.get(page_number, []), typography_by_page.get(page_number, []))
        page = {
            "page_number": page_number,
            "source_images": source_images_by_page.get(page_number, {}),
            "image_regions": {
                "canvas": CANVAS,
                "generation_contract": _generation_contract(pair_manifest),
            },
            "containers": containers_by_page.get(page_number, []),
            "text_objects": text_objects,
            "svg_text_objects": svg_texts_by_page.get(page_number, []),
            "typography_decisions": typography_by_page.get(page_number, []),
            "visual_element_inventory": [
                *_container_elements(containers_by_page.get(page_number, [])),
                *_text_elements(text_objects),
            ],
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
            "ocr_text_mappings": sum(len(items) for items in text_mappings.values()),
            "svg_text_objects": sum(len(items) for items in svg_texts_by_page.values()),
            "container_pages": len(containers_by_page),
            "typography_pages": len(typography_by_page),
        },
        "capture_policy": {
            "final_text_source": "script_truth_plus_ocr_locator",
            "text_wrap_before_shrink": True,
            "visual_delivery_mode": "dual_image_editable_overlay",
            "source_to_render_delta_required_before_final_approval": True,
        },
        "pages": pages,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a unified source-capture JSON for dual-image PPT rebuilds.")
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--pair-manifest", type=Path)
    parser.add_argument("--candidate-rules", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = build_source_capture(
        args.project_dir.resolve(),
        pair_manifest_path=args.pair_manifest.resolve() if args.pair_manifest else None,
        candidate_rules_path=args.candidate_rules.resolve() if args.candidate_rules else None,
    )
    if args.out:
        _write_json(args.out.resolve(), report)
    print(json.dumps({"pages": len(report["pages"]), "text_objects": report["inputs"]["ocr_text_mappings"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
