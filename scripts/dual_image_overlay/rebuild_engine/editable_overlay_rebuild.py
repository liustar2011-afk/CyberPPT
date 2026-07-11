#!/usr/bin/env python3
"""CyberPPT dual-image manifest -> editable text overlay -> template PPTX route."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from PIL import Image

from scripts.dual_image_overlay.rebuild_modes import resolve_rebuild_mode
from scripts.dual_image_overlay.background_text_scan import scan_background_text
from scripts.dual_image_overlay.block_fit import fit_text_block_to_container
from scripts.dual_image_overlay.page_understanding import (
    build_implicit_text_containers,
    build_page_understanding,
    write_page_understanding,
)
from scripts.dual_image_overlay.semantic_typography_qa import apply_semantic_typography_qa
from scripts.dual_image_overlay.text_content_qa import build_text_content_qa
from scripts.dual_image_overlay.scene_graph.builder import build_page_scene_graph
from scripts.dual_image_overlay.scene_graph.gate import build_scene_graph_gate
from scripts.dual_image_overlay.scene_graph.layout import build_layout_plan_from_scene_graph
from scripts.dual_image_overlay.scene_graph.schema import scene_graph_to_dict
from scripts.dual_image_overlay.text_block_group import build_text_block_group
from scripts.dual_image_overlay.text_truth import verify_text_blocks_against_script
from scripts.dual_image_overlay.rebuild_engine.ocr_quality_gate import evaluate_ocr_quality
from scripts.dual_image_overlay.rebuild_engine.text_forensics import attach_correction_evidence, build_line_evidence

if __package__:
    from .ocr_text_locator import load_layout, locate_text
    from .script_text_overlay import (
        OverlayTextBox,
        SemanticContainer,
        build_overlay_boxes_from_semantic_plan,
        boxes_to_json,
        build_overlay_boxes,
        build_semantic_layout_plan,
        containers_to_json,
        extract_script_truth_lines,
        extract_semantic_plan,
        extract_script_truth_sections,
        _fit_all_boxes,
        infer_semantic_containers,
        normalize_semantic_plan_to_canvas,
        reconcile_semantic_plan_with_script_truth,
        render_overlay_svg,
        resolve_overlay_coordinate_context,
        semantic_plan_to_json,
        validate_explicit_semantic_plan,
    )
    from .template_image_ppt_export import (
        CANVAS_SIZE,
        copy_brand,
        extract_content,
        inset_content_region,
        load_brand_rules,
        page_notes_text,
        page_stem,
        parse_page_blocks,
        scale_region,
        write_spec_lock,
    )
else:
    from ocr_text_locator import load_layout, locate_text
    from script_text_overlay import (
        OverlayTextBox,
        SemanticContainer,
        build_overlay_boxes_from_semantic_plan,
        boxes_to_json,
        build_overlay_boxes,
        build_semantic_layout_plan,
        containers_to_json,
        extract_script_truth_lines,
        extract_semantic_plan,
        extract_script_truth_sections,
        _fit_all_boxes,
        infer_semantic_containers,
        normalize_semantic_plan_to_canvas,
        reconcile_semantic_plan_with_script_truth,
        render_overlay_svg,
        resolve_overlay_coordinate_context,
        semantic_plan_to_json,
        validate_explicit_semantic_plan,
    )
    from template_image_ppt_export import (
        CANVAS_SIZE,
        copy_brand,
        extract_content,
        inset_content_region,
        load_brand_rules,
        page_notes_text,
        page_stem,
        parse_page_blocks,
        scale_region,
        write_spec_lock,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_pair_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Pair manifest must be a JSON object.")
    return data


def resolve_project_path(manifest_path: Path, manifest: dict[str, Any]) -> Path:
    raw = manifest.get("project_path")
    if isinstance(raw, str) and raw.strip():
        return Path(raw).expanduser().resolve()
    return manifest_path.resolve().parents[2]


def _require_image(item: dict[str, Any], key: str) -> Path:
    raw = item.get("path")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"Missing {key}.path in pair manifest.")
    path = Path(raw).expanduser().resolve()
    if not path.is_file() or path.stat().st_size <= 0:
        raise FileNotFoundError(f"Missing {key} image: {path}")
    return path


def _copy_image_to_project(image_path: Path, project_path: Path) -> str:
    images_dir = project_path / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    target = images_dir / image_path.name
    if image_path.resolve() != target.resolve():
        shutil.copy2(image_path, target)
    return "../images/" + target.name


def _normalized_image_name(source: Path, suffix: str) -> str:
    stem = source.stem
    if stem.endswith("_full"):
        stem = stem[: -len("_full")]
    if stem.endswith("_background"):
        stem = stem[: -len("_background")]
    return f"{stem}_{suffix}_{CANVAS_SIZE[0]}x{CANVAS_SIZE[1]}.png"


def _resize_to_canvas(source: Path, target: Path) -> list[int]:
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        source_size = list(image.size)
        image.convert("RGB").resize(CANVAS_SIZE, Image.Resampling.LANCZOS).save(target)
    return source_size


def _prepare_page_images(
    *,
    full_image: Path,
    background_image: Path,
    project_path: Path,
) -> tuple[Path, Path, dict[str, Any]]:
    normalized_dir = project_path / "images" / "normalized"
    prepared_full = normalized_dir / _normalized_image_name(full_image, "full")
    prepared_background = normalized_dir / _normalized_image_name(background_image, "background")
    full_size = _resize_to_canvas(full_image, prepared_full)
    background_size = _resize_to_canvas(background_image, prepared_background)
    return prepared_full, prepared_background, {
        "status": f"normalized_{CANVAS_SIZE[0]}x{CANVAS_SIZE[1]}",
        "source_full_size": full_size,
        "source_background_size": background_size,
        "full_size": list(CANVAS_SIZE),
        "background_size": list(CANVAS_SIZE),
        "output_size": list(CANVAS_SIZE),
        "full_output_path": str(prepared_full),
        "background_output_path": str(prepared_background),
        "output_path": str(prepared_background),
    }


def _background_href_for_svg(prepared_background: Path) -> str:
    return "../images/normalized/" + prepared_background.name


def _write_rebuild_quality(project_path: Path, pages: list[dict[str, Any]]) -> None:
    quality_path = project_path / "analysis" / "rebuild_quality.json"
    quality_path.parent.mkdir(parents=True, exist_ok=True)
    quality_path.write_text(
        json.dumps({"pages": pages}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_explicit_semantic_plan(semantic_plan_dir: Path | None, page_number: int) -> tuple[Path, dict[str, Any]] | None:
    if semantic_plan_dir is None:
        return None
    candidates = [
        semantic_plan_dir / f"page_{page_number:03d}_semantic_plan.json",
        semantic_plan_dir / f"slide-{page_number:02d}-semantic-plan.json",
        semantic_plan_dir / f"slide-{page_number:02d}-semantic_plan.json",
    ]
    for path in candidates:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(f"Semantic plan must be a JSON object: {path}")
            return path, data
    return None


def _load_visual_registry(visual_registry_dir: Path | None, page_number: int) -> tuple[Path, dict[str, Any]] | None:
    if visual_registry_dir is None:
        return None
    candidates = [
        visual_registry_dir / f"slide-{page_number:02d}-visual-element-registry.json",
        visual_registry_dir / f"page_{page_number:03d}_visual_element_registry.json",
    ]
    for path in candidates:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(f"Visual registry must be a JSON object: {path}")
            return path, data
    return None


def _semantic_container_from_plan(container: dict[str, Any]) -> SemanticContainer:
    bbox = container.get("bbox") if isinstance(container.get("bbox"), list) else [0, 0, 0, 0]
    x1, y1, x2, y2 = [float(value) for value in bbox]
    return SemanticContainer(
        id=str(container.get("id") or ""),
        role=str(container.get("role") or "container"),
        x=round(x1, 2),
        y=round(y1, 2),
        w=round(max(1.0, x2 - x1), 2),
        h=round(max(1.0, y2 - y1), 2),
        background=str(container.get("background") or "light"),
        fill=str(container.get("fill") or "#0B1F3D"),
        align=str(container.get("align") or "center"),
        max_lines=int(container.get("max_lines") or 1),
    )


def _body_region() -> dict[str, int]:
    rules = load_brand_rules()
    brand_body_region = scale_region(rules["content_regions"]["body_pages"], CANVAS_SIZE)
    return inset_content_region(brand_body_region)


def _ensure_project_shell(project_path: Path) -> None:
    for subdir in ("svg_output", "notes", "templates", "images", "exports", "analysis/ocr"):
        (project_path / subdir).mkdir(parents=True, exist_ok=True)
    rules = load_brand_rules()
    copy_brand(project_path)
    write_spec_lock(project_path, rules, CANVAS_SIZE)


def _layout_for_page(
    *,
    full_image: Path,
    ocr_dir: Path,
    page_number: int,
    ocr_backend: str,
    force_ocr: bool,
    timeout: int,
    min_expected_items: int | None = None,
    variant: str = "full",
) -> tuple[Path, dict[str, Any]]:
    suffix = "" if variant == "full" else f"_{variant}"
    layout_path = ocr_dir / f"page_{page_number:03d}{suffix}_text_layout.json"
    if layout_path.is_file() and not force_ocr:
        return layout_path, load_layout(layout_path)
    layout = locate_text(
        full_image,
        backend=ocr_backend,
        output_path=layout_path,
        timeout=timeout,
        min_expected_items=min_expected_items,
    )
    return layout_path, layout


def _prefetch_page_ocr_layouts(
    *,
    manifest: dict[str, Any],
    source_script: Path,
    ocr_dir: Path,
    ocr_backend: str,
    force_ocr: bool,
    timeout: int,
    max_workers: int = 4,
) -> None:
    """Warm the OCR cache for every page/variant concurrently before the main loop.

    The main per-page loop below is sequential (each page's local processing
    depends on nothing from other pages, but is simplest to reason about run
    one at a time). For a multi-page manifest, its two OCR network calls per
    page were previously the dominant wall-clock cost, paid N-pages times in a
    row. This fires every page's full+background OCR request concurrently
    ahead of time; `_layout_for_page`'s existing cache check (`if
    layout_path.is_file() and not force_ocr: return cached`) means the main
    loop's own calls then just read the now-populated cache instead of
    blocking on the network again.

    This is a pure, best-effort optimization: it does not change what OCR is
    called or how its result is used. If a page's prefetch fails or is still
    in flight when the main loop reaches it, that page's own `_layout_for_page`
    call falls back to doing the (slower, synchronous) OCR call itself,
    exactly as it did before this function existed -- so a prefetch failure
    degrades to today's baseline behavior, never worse.
    """
    indexed_tasks: list[tuple[int, Path, str, int | None]] = []
    for pair in manifest.get("pairs", []):
        page_number = int(pair["page_number"])
        if "background" not in pair:
            continue
        try:
            expected_lines = extract_script_truth_lines(source_script, page_number)
        except ValueError:
            expected_lines = []
        min_expected_items = max(1, round(len(expected_lines) * 0.6)) if expected_lines else None
        indexed_tasks.append((page_number, _require_image(pair["full"], "full"), "full", min_expected_items))
        indexed_tasks.append((page_number, _require_image(pair["background"], "background"), "background", None))

    if len(indexed_tasks) <= 1:
        return  # Nothing to gain from a thread pool for a single request.

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [
            pool.submit(
                _layout_for_page,
                full_image=image_path,
                ocr_dir=ocr_dir,
                page_number=page_number,
                ocr_backend=ocr_backend,
                force_ocr=force_ocr,
                timeout=timeout,
                min_expected_items=min_expected_items,
                variant=variant,
            )
            for page_number, image_path, variant, min_expected_items in indexed_tasks
        ]
        for future in futures:
            try:
                future.result()
            except Exception as exc:  # noqa: BLE001 - best-effort warm-up, main loop retries synchronously
                print(f"OCR prefetch task failed (will retry synchronously in main loop): {exc}", file=sys.stderr)


def _scene_graph_artifact_paths(project_path: Path, page_number: int) -> dict[str, Path]:
    return {
        "graph": project_path / "analysis" / "scene_graph" / f"page_{page_number:03d}_scene_graph.json",
        "gate": project_path / "analysis" / "scene_graph_gate" / f"page_{page_number:03d}_scene_graph_gate.json",
        "layout": project_path / "analysis" / "page_layout_plan" / f"page_{page_number:03d}_layout_plan.json",
    }


def _scene_graph_gate_blocks_export(gate_path: Path) -> bool:
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    return bool(gate.get("blocking_count") or not gate.get("valid", False))


def _image_size_for_scene_graph(image_size_check: dict[str, Any]) -> dict[str, float]:
    output_size = image_size_check.get("output_size")
    if isinstance(output_size, list) and len(output_size) == 2:
        return {"width": float(output_size[0]), "height": float(output_size[1])}
    full_size = image_size_check.get("full_size")
    if isinstance(full_size, list) and len(full_size) == 2:
        return {"width": float(full_size[0]), "height": float(full_size[1])}
    return {"width": float(CANVAS_SIZE[0]), "height": float(CANVAS_SIZE[1])}


def _source_full_size(image_size_check: dict[str, Any]) -> dict[str, float]:
    source_size = image_size_check.get("source_full_size")
    if isinstance(source_size, list) and len(source_size) == 2:
        return {"width": float(source_size[0]), "height": float(source_size[1])}
    return {"width": float(CANVAS_SIZE[0]), "height": float(CANVAS_SIZE[1])}


def _write_scene_graph_artifacts(
    *,
    project_path: Path,
    page_number: int,
    source_script: Path,
    semantic_plan_payload: dict[str, Any],
    semantic_layout_plan: dict[str, Any] | None,
    visual_registry: dict[str, Any] | None,
    image_size_check: dict[str, Any],
) -> dict[str, Path]:
    paths = _scene_graph_artifact_paths(project_path, page_number)
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    graph = build_page_scene_graph(
        page_number=page_number,
        script_sections=extract_script_truth_sections(source_script, page_number),
        semantic_plan=semantic_plan_payload,
        visual_registry=visual_registry or {"blueprint_canvas_px": {"w": CANVAS_SIZE[0], "h": CANVAS_SIZE[1]}, "elements": []},
        image_size=_image_size_for_scene_graph(image_size_check),
        semantic_layout_plan=semantic_layout_plan,
    )
    graph_gate = build_scene_graph_gate(graph)
    paths["graph"].write_text(json.dumps(scene_graph_to_dict(graph), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths["gate"].write_text(json.dumps(graph_gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if _scene_graph_gate_blocks_export(paths["gate"]):
        raise ValueError(f"Scene graph gate failed for page {page_number}: {graph_gate['issues']}")
    page_layout_plan = build_layout_plan_from_scene_graph(graph)
    paths["layout"].write_text(json.dumps(page_layout_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return paths


def _overlay_boxes_from_scene_graph_layout(
    page_layout_plan: dict[str, Any],
    body_region: dict[str, float],
    *,
    font_family: str = "Microsoft YaHei",
    fill: str = "#0B1F3D",
) -> list[OverlayTextBox]:
    sx = float(body_region["width"]) / float(CANVAS_SIZE[0])
    sy = float(body_region["height"]) / float(CANVAS_SIZE[1])
    boxes: list[OverlayTextBox] = []
    for index, item in enumerate(page_layout_plan.get("items", [])):
        if not isinstance(item, dict):
            continue
        bbox = item.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            raise ValueError(f"page_layout_plan.items[{index}].bbox must contain four numbers.")
        x1, y1, x2, y2 = [float(value) for value in bbox]
        boxes.append(
            OverlayTextBox(
                text=str(item.get("text") or ""),
                x=round(float(body_region["x"]) + x1 * sx, 2),
                y=round(float(body_region["y"]) + y1 * sy, 2),
                w=round(max(1.0, (x2 - x1) * sx), 2),
                h=round(max(1.0, (y2 - y1) * sy), 2),
                font_size=round(float(item.get("font_size") or 12) * sy, 2),
                font_family=font_family,
                fill=str(item.get("fill") or fill),
                font_weight=str(item.get("font_weight") or "400"),
                align=str(item.get("align") or "left"),
                word_wrap=bool(item.get("word_wrap", True)),
                source="scene_graph_layout",
                confidence=1.0,
            )
        )
    _fit_all_boxes(boxes)
    return boxes


def _editable_boxes_from_scene_graph_or_recognition(
    page_layout_plan: dict[str, Any],
    body_region: dict[str, float],
    recognized_boxes: list[OverlayTextBox],
) -> tuple[list[OverlayTextBox], str]:
    items = page_layout_plan.get("items")
    if isinstance(items, list) and items:
        return _overlay_boxes_from_scene_graph_layout(page_layout_plan, body_region), "scene_graph_layout"
    _fit_all_boxes(recognized_boxes)
    return recognized_boxes, "ocr_script_recognition"


def _overlay_box_style(box: OverlayTextBox) -> dict[str, Any]:
    return {
        "font_size": box.font_size,
        "font_family": box.font_family,
        "font_weight": box.font_weight,
        "fill": box.fill,
        "align": box.align,
    }


def _bbox_overlap_area(a: list[float], b: list[float]) -> float:
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def _nearest_overlay_box_style(bbox: list[float], boxes: list[OverlayTextBox]) -> dict[str, Any]:
    if not boxes:
        return {
            "font_size": 12.0,
            "font_family": "Microsoft YaHei",
            "font_weight": "400",
            "fill": "#0B1F3D",
            "align": "left",
        }

    cx = (bbox[0] + bbox[2]) / 2.0
    cy = (bbox[1] + bbox[3]) / 2.0
    best_box = min(
        boxes,
        key=lambda box: (
            -_bbox_overlap_area(bbox, [box.x, box.y, box.x + box.w, box.y + box.h]),
            ((box.x + box.w / 2.0) - cx) ** 2 + ((box.y + box.h / 2.0) - cy) ** 2,
        ),
    )
    return _overlay_box_style(best_box)


def _scale_layout_bbox_to_canvas(bbox: Any, layout: dict[str, Any]) -> list[float] | None:
    if not isinstance(bbox, list) or len(bbox) != 4:
        return None
    try:
        x1, y1, x2, y2 = [float(value) for value in bbox]
    except (TypeError, ValueError):
        return None
    if x2 <= x1 or y2 <= y1:
        return None

    image_size = layout.get("image_size") if isinstance(layout.get("image_size"), dict) else {}
    try:
        width = float(image_size.get("width") or CANVAS_SIZE[0])
        height = float(image_size.get("height") or CANVAS_SIZE[1])
    except (TypeError, ValueError):
        width = float(CANVAS_SIZE[0])
        height = float(CANVAS_SIZE[1])
    if width <= 0 or height <= 0:
        width = float(CANVAS_SIZE[0])
        height = float(CANVAS_SIZE[1])

    sx = float(CANVAS_SIZE[0]) / width
    sy = float(CANVAS_SIZE[1]) / height
    return [round(x1 * sx, 2), round(y1 * sy, 2), round(x2 * sx, 2), round(y2 * sy, 2)]


def _page_understanding_text_blocks_from_layout(
    layout: dict[str, Any],
    boxes: list[OverlayTextBox],
    body_region: dict[str, Any],
) -> list[dict[str, Any]]:
    del body_region
    if boxes:
        return _page_understanding_text_blocks_from_boxes_with_layout_evidence(boxes, layout)

    blocks: list[dict[str, Any]] = []
    items = layout.get("items") if isinstance(layout.get("items"), list) else []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        raw_text = str(item.get("text") or "").strip()
        bbox = _scale_layout_bbox_to_canvas(item.get("bbox"), layout)
        if not raw_text or bbox is None:
            continue
        block: dict[str, Any] = {
            "id": f"ocr_item_{index:03d}",
            "ocr_text": raw_text,
            "text": raw_text,
            "bbox": bbox,
            "style": _nearest_overlay_box_style(bbox, boxes),
            "source": str(item.get("source") or "ocr_layout"),
        }
        if item.get("confidence") is not None:
            block["confidence"] = item.get("confidence")
        blocks.append(block)
    return blocks


def _layout_text_evidence_for_box(box: OverlayTextBox, layout: dict[str, Any]) -> tuple[str, list[list[float]], Any | None]:
    items = layout.get("items") if isinstance(layout.get("items"), list) else []
    box_bbox = [box.x, box.y, box.x + box.w, box.y + box.h]
    evidence: list[tuple[list[float], str, Any | None]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_text = str(item.get("text") or "").strip()
        bbox = _scale_layout_bbox_to_canvas(item.get("bbox"), layout)
        if not raw_text or bbox is None:
            continue
        if _bbox_overlap_area(bbox, box_bbox) <= 0:
            continue
        evidence.append((bbox, raw_text, item.get("confidence")))

    if not evidence:
        return box.text, [], None

    evidence.sort(key=lambda entry: (entry[0][1], entry[0][0]))
    text = "\n".join(entry[1] for entry in evidence)
    line_boxes = [entry[0] for entry in evidence]
    confidences = [entry[2] for entry in evidence if isinstance(entry[2], (int, float))]
    confidence = round(sum(float(value) for value in confidences) / len(confidences), 3) if confidences else None
    return text, line_boxes, confidence


def _same_text_evidence_scope(left: str, right: str) -> bool:
    left_key = re.sub(r"[\s,，。:：;；、（）()【】\[\]\"'“”‘’]+", "", str(left or "")).lower()
    right_key = re.sub(r"[\s,，。:：;；、（）()【】\[\]\"'“”‘’]+", "", str(right or "")).lower()
    if not left_key or not right_key:
        return False
    if left_key in right_key or right_key in left_key:
        return min(len(left_key), len(right_key)) / max(len(left_key), len(right_key)) >= 0.75
    matches = sum(1 for a, b in zip(left_key, right_key) if a == b)
    return len(left_key) == len(right_key) and matches / max(1, len(left_key)) >= 0.75


def _page_understanding_text_blocks_from_boxes_with_layout_evidence(
    boxes: list[OverlayTextBox],
    layout: dict[str, Any],
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for index, box in enumerate(boxes, start=1):
        evidence_text, line_boxes, confidence = _layout_text_evidence_for_box(box, layout)
        ocr_text = evidence_text if _same_text_evidence_scope(evidence_text, box.text) else box.text
        block: dict[str, Any] = {
            "id": f"overlay_box_{index:03d}",
            "ocr_text": ocr_text,
            "text": box.text,
            "bbox": [box.x, box.y, box.x + box.w, box.y + box.h],
            "line_boxes": line_boxes,
            "style": _overlay_box_style(box),
            "source": "overlay_export_context",
        }
        if confidence is not None:
            block["confidence"] = confidence
        blocks.append(block)
    return blocks


def _page_understanding_text_blocks_from_boxes(boxes: list[OverlayTextBox]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for index, box in enumerate(boxes, start=1):
        blocks.append(
            {
                "id": f"overlay_box_{index:03d}",
                "ocr_text": box.text,
                "text": box.text,
                "bbox": [box.x, box.y, box.x + box.w, box.y + box.h],
                "style": _overlay_box_style(box),
                "source": "overlay_export_context",
            }
        )
    return blocks


def _write_page_understanding_artifact(
    *,
    project_path: Path,
    page_number: int,
    full_image: Path,
    background_image: Path,
    source_script: Path,
    boxes: list[OverlayTextBox],
    layout: dict[str, Any],
    body_region: dict[str, Any],
    containers: list[SemanticContainer],
    visual_registry: dict[str, Any] | None,
) -> Path:
    text_blocks = _page_understanding_text_blocks_from_layout(layout, boxes, body_region)
    if not text_blocks:
        text_blocks = _page_understanding_text_blocks_from_boxes(boxes)
    try:
        script_truth_lines = extract_script_truth_lines(source_script, page_number)
    except ValueError:
        script_truth_lines = []
    verified_blocks = verify_text_blocks_against_script(text_blocks, script_truth_lines)
    explicit_containers = containers_to_json(containers)
    visual_elements = visual_registry.get("elements", []) if isinstance(visual_registry, dict) else []
    implicit_containers = build_implicit_text_containers(
        verified_blocks,
        explicit_containers,
        visual_elements,
        canvas={"width": float(CANVAS_SIZE[0]), "height": float(CANVAS_SIZE[1])},
    )
    payload = build_page_understanding(
        page_number=page_number,
        full_image=full_image,
        background_image=background_image,
        registration={"valid": True, "transform": "identity", "source": f"normalized_{CANVAS_SIZE[0]}x{CANVAS_SIZE[1]}"},
        text_blocks=verified_blocks,
        explicit_containers=explicit_containers,
        implicit_containers=implicit_containers,
        visual_elements=visual_elements,
        canvas={"width": float(CANVAS_SIZE[0]), "height": float(CANVAS_SIZE[1])},
    )
    payload["inputs"] = {
        "full_image": str(full_image.resolve()),
        "background_image": str(background_image.resolve()),
    }

    containers_by_id = {
        str(container.get("id")): container
        for container in payload.get("containers", [])
        if isinstance(container, dict) and container.get("id")
    }
    binding_by_text_id = {
        str(binding.get("text_block_id")): binding
        for binding in payload.get("container_text_bindings", [])
        if isinstance(binding, dict) and binding.get("text_block_id")
    }
    for text_block in payload.get("text_blocks", []):
        if not isinstance(text_block, dict):
            continue
        binding = binding_by_text_id.get(str(text_block.get("id") or ""))
        container = containers_by_id.get(str(binding.get("container_id") or "")) if isinstance(binding, dict) else None
        if not isinstance(container, dict):
            continue
        fit = fit_text_block_to_container(text_block, container)
        text_block["fit"] = fit
        text_block["text_block_group"] = build_text_block_group(text_block, fit=fit)

    page_understanding_dir = project_path / "analysis" / "page_understanding"
    page_understanding_path = page_understanding_dir / f"page_{page_number:03d}_page_understanding.json"
    write_page_understanding(page_understanding_path, payload)
    return page_understanding_path


def rebuild_from_manifest(
    manifest_path: Path,
    *,
    ocr_backend: str = "vision-json",
    force_ocr: bool = False,
    timeout: int = 300,
    visible_image_variant: str = "background",
    editable_text_visibility: str = "visible",
    explicit_semantic_plan_dir: Path | None = None,
    visual_registry_dir: Path | None = None,
) -> dict[str, Any]:
    """Create overlay SVG pages from generated full/background image pairs."""
    manifest_path = manifest_path.resolve()
    manifest = load_pair_manifest(manifest_path)
    rebuild_mode = resolve_rebuild_mode(manifest)
    project_path = resolve_project_path(manifest_path, manifest)
    source_script = Path(str(manifest.get("source_script", ""))).expanduser().resolve()
    if not source_script.is_file():
        raise FileNotFoundError(f"Source script not found: {source_script}")

    _ensure_project_shell(project_path)
    body = _body_region()
    pages = parse_page_blocks(source_script)
    ocr_dir = project_path / "analysis" / "ocr"
    semantic_plan_dir = project_path / "analysis" / "semantic_plan"
    explicit_semantic_dir = explicit_semantic_plan_dir.resolve() if explicit_semantic_plan_dir else None
    explicit_visual_registry_dir = visual_registry_dir.resolve() if visual_registry_dir else None
    semantic_layout_dir = project_path / "analysis" / "semantic_layout_plan"
    semantic_gate_dir = project_path / "analysis" / "semantic_plan_gate"
    containers_dir = project_path / "analysis" / "semantic_containers"
    background_scan_dir = project_path / "analysis" / "background_text_scan"
    typography_qa_dir = project_path / "analysis" / "semantic_typography_qa"
    semantic_plan_dir.mkdir(parents=True, exist_ok=True)
    semantic_layout_dir.mkdir(parents=True, exist_ok=True)
    semantic_gate_dir.mkdir(parents=True, exist_ok=True)
    containers_dir.mkdir(parents=True, exist_ok=True)
    background_scan_dir.mkdir(parents=True, exist_ok=True)
    typography_qa_dir.mkdir(parents=True, exist_ok=True)
    svg_count = 0
    quality_pages: list[dict[str, Any]] = []
    background_scan_pages: list[dict[str, Any]] = []
    typography_qa_pages: list[dict[str, Any]] = []
    forensic_policy = {
        "min_line_recall": 0.95,
        "max_low_confidence_ratio": 0.10,
        "max_protected_replacement_failures": 0,
    }

    for pair in manifest.get("pairs", []):
        page_number = int(pair["page_number"])
        if "background" not in pair:
            raise ValueError(f"Page {page_number} has no background variant. Run with --dual-image first.")
        source_full_image = _require_image(pair["full"], "full")
        source_background_image = _require_image(pair["background"], "background")
        normalized_full, normalized_background, image_size_check = _prepare_page_images(
            full_image=source_full_image,
            background_image=source_background_image,
            project_path=project_path,
        )
        full_image = normalized_full
        background_image = normalized_background
        prepared_background = full_image if visible_image_variant == "full" else background_image
        try:
            expected_lines = extract_script_truth_lines(source_script, page_number)
        except ValueError:
            expected_lines = []
        # Not every script truth line is a separate on-image OCR item (titles/
        # subtitles usually come from the template layer, not the content
        # region), so use a conservative fraction as the "looks under-detected,
        # resample" floor rather than the full count.
        min_expected_items = max(1, round(len(expected_lines) * 0.6)) if expected_lines else None
        # The full-image and background-image OCR calls are independent
        # network requests (each can take tens of seconds to minutes), so run
        # them concurrently instead of waiting on one before starting the
        # other. This alone roughly halves the OCR-bound portion of this
        # loop's wall-clock time per page; it does not change what either
        # call does or how its result is used below.
        with ThreadPoolExecutor(max_workers=2) as ocr_pool:
            full_future = ocr_pool.submit(
                _layout_for_page,
                full_image=source_full_image,
                ocr_dir=ocr_dir,
                page_number=page_number,
                ocr_backend=ocr_backend,
                force_ocr=force_ocr,
                timeout=timeout,
                min_expected_items=min_expected_items,
            )
            # SKILL.md's dual_image_editable_overlay contract requires a
            # no-text scan of the background: it must never carry readable
            # primary text (that would double-render once the editable text
            # layer sits on top of it). OCR the background the same way as
            # the full image and let `scan_background_text` flag any
            # detected text as a defect.
            background_future = ocr_pool.submit(
                _layout_for_page,
                full_image=source_background_image,
                ocr_dir=ocr_dir,
                page_number=page_number,
                ocr_backend=ocr_backend,
                force_ocr=force_ocr,
                timeout=timeout,
                variant="background",
            )
            layout_path, layout = full_future.result()
            background_layout_path, background_layout = background_future.result()
        # Preserve raw line-level evidence before any overlay boxes are built.
        # A failed gate leaves this artifact behind for review/recovery.
        forensic_dir = ocr_dir / f"page_{page_number:03d}_text_forensics"
        forensics = build_line_evidence(layout, full_image, evidence_dir=forensic_dir)
        forensics["page_number"] = page_number
        forensics["expected_lines"] = expected_lines
        forensics = attach_correction_evidence(
            forensics,
            policy_path=REPO_ROOT / "config/ocr/correction_policy.json",
            protected_terms_path=REPO_ROOT / "config/ocr/protected_terms.json",
        )
        quality_report = evaluate_ocr_quality(forensics, policy=forensic_policy)
        forensics["quality"] = {**forensics.get("quality", {}), **quality_report["metrics"], "gate": quality_report}
        forensic_path = ocr_dir / f"page_{page_number:03d}_text_forensics.json"
        _write_json(forensic_path, forensics)
        if ocr_backend != "none" and quality_report["status"] != "passed":
            raise RuntimeError(
                f"OCR quality gate failed for page {page_number}: {quality_report['failures']}. "
                f"Raw evidence retained at {forensic_path}. Recovery: {quality_report['recovery_command']}"
            )
        background_scan_report = scan_background_text(background_layout_path)
        background_scan_report["page_number"] = page_number
        _write_json(
            background_scan_dir / f"page_{page_number:03d}_background_text_scan.json",
            background_scan_report,
        )
        background_scan_pages.append(background_scan_report)
        explicit_semantic = _load_explicit_semantic_plan(explicit_semantic_dir, page_number)
        visual_registry_entry = _load_visual_registry(explicit_visual_registry_dir, page_number)
        visual_registry = visual_registry_entry[1] if visual_registry_entry is not None else None
        semantic_plan = extract_semantic_plan(source_script, page_number)
        semantic_plan_path = semantic_plan_dir / f"page_{page_number:03d}_semantic_plan.json"
        if explicit_semantic is not None:
            explicit_path, explicit_plan = explicit_semantic
            explicit_plan = reconcile_semantic_plan_with_script_truth(explicit_plan, source_script, page_number)
            explicit_plan = normalize_semantic_plan_to_canvas(
                explicit_plan,
                input_space=_source_full_size(image_size_check),
            )
            semantic_plan_path.write_text(
                json.dumps(explicit_plan, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            semantic_gate = validate_explicit_semantic_plan(explicit_plan)
            coordinate_context = resolve_overlay_coordinate_context(
                explicit_plan,
                visual_registry=visual_registry,
                background_image=prepared_background,
            )
            semantic_layout_plan = build_semantic_layout_plan(
                explicit_plan,
                visual_registry=visual_registry,
                coordinate_context=coordinate_context,
            )
            if not semantic_gate["valid"]:
                raise ValueError(f"Semantic plan preflight failed for page {page_number}: {semantic_gate['issues']}")
            boxes, semantic_layout_plan, semantic_gate = build_overlay_boxes_from_semantic_plan(
                explicit_plan,
                body,
                visual_registry=visual_registry,
                background_image=prepared_background,
            )
            containers = [
                _semantic_container_from_plan(container)
                for container in explicit_plan.get("containers", [])
                if isinstance(container, dict)
            ]
            semantic_source = str(explicit_path)
            visual_registry_source = str(visual_registry_entry[0]) if visual_registry_entry is not None else None
            scene_graph_semantic_plan = explicit_plan
        else:
            scene_graph_semantic_plan = semantic_plan_to_json(semantic_plan)
            semantic_plan_path.write_text(
                json.dumps(scene_graph_semantic_plan, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            containers = infer_semantic_containers(prepared_background, layout, body, semantic_plan=semantic_plan)
            boxes = build_overlay_boxes(
                source_script,
                page_number,
                layout,
                body,
                background_image=prepared_background,
                semantic_containers=containers,
                semantic_plan=semantic_plan,
            )
            semantic_gate = validate_explicit_semantic_plan(None, required=False)
            semantic_layout_plan = {"schema": "cyberppt.dual_image.semantic_layout_plan.v1", "items": []}
            semantic_source = "script_derived_fallback"
            visual_registry_source = str(visual_registry_entry[0]) if visual_registry_entry is not None else None
        scene_graph_paths = _write_scene_graph_artifacts(
            project_path=project_path,
            page_number=page_number,
            source_script=source_script,
            semantic_plan_payload=scene_graph_semantic_plan,
            semantic_layout_plan=semantic_layout_plan,
            visual_registry=visual_registry,
            image_size_check=image_size_check,
        )
        page_layout_plan = json.loads(scene_graph_paths["layout"].read_text(encoding="utf-8"))
        boxes, editable_text_layout_source = _editable_boxes_from_scene_graph_or_recognition(
            page_layout_plan,
            body,
            boxes,
        )
        # SKILL.md requires a semantic typography QA pass: parallel text at the
        # same semantic role (title vs body) must share one bold/weight
        # decision, not whatever OCR happened to observe on that one line.
        # This is reported as an informational check for now (see
        # `apply_semantic_typography_qa`'s docstring: it treats OCR-derived
        # bold as an observation, not truth); it does not yet feed corrections
        # back into `boxes`, since this pipeline's own `_fit_all_boxes` already
        # owns font sizing and blindly overwriting `font_weight` here risked a
        # second, uncoordinated adjustment system fighting the first one.
        typography_input = [
            {
                "text": item.get("text"),
                "bbox": [item["x"], item["y"], item["x"] + item["w"], item["y"] + item["h"]],
                "bold": str(item.get("font_weight") or "").strip() in {"700", "bold", "Bold"},
            }
            for item in boxes_to_json(boxes)
        ]
        _, typography_qa_report = apply_semantic_typography_qa(
            typography_input,
            report_path=typography_qa_dir / f"page_{page_number:03d}_semantic_typography_qa.json",
        )
        typography_qa_report["page_number"] = page_number
        typography_qa_pages.append(typography_qa_report)
        page_understanding_path = _write_page_understanding_artifact(
            project_path=project_path,
            page_number=page_number,
            full_image=full_image,
            background_image=background_image,
            source_script=source_script,
            boxes=boxes,
            layout=layout,
            body_region=body,
            containers=containers,
            visual_registry=visual_registry,
        )
        semantic_gate_path = semantic_gate_dir / f"page_{page_number:03d}_semantic_plan_gate.json"
        semantic_gate_path.write_text(
            json.dumps(semantic_gate, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        semantic_layout_path = semantic_layout_dir / f"page_{page_number:03d}_layout_plan.json"
        semantic_layout_path.write_text(
            json.dumps(semantic_layout_plan, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        containers_path = containers_dir / f"page_{page_number:03d}_containers.json"
        containers_path.write_text(
            json.dumps(
                {
                    "page_number": page_number,
                    "background_image": str(prepared_background),
                    "semantic_plan": str(semantic_plan_path),
                    "containers": containers_to_json(containers),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        mapping_path = ocr_dir / f"page_{page_number:03d}_text_mapping.json"
        mapping_path.write_text(
            json.dumps(
                {
                    "page_number": page_number,
                    "ocr_layout": str(layout_path),
                    "semantic_plan": str(semantic_plan_path),
                    "semantic_plan_gate": str(semantic_gate_path),
                    "semantic_layout_plan": str(semantic_layout_path),
                    "scene_graph": str(scene_graph_paths["graph"]),
                    "scene_graph_gate": str(scene_graph_paths["gate"]),
                    "page_layout_plan": str(scene_graph_paths["layout"]),
                    "page_understanding": str(page_understanding_path.resolve()),
                    "text_forensics": str(forensic_path.resolve()),
                    "ocr_quality_gate": quality_report,
                    "semantic_source": semantic_source,
                    "editable_text_layout_source": editable_text_layout_source,
                    "visual_registry_source": visual_registry_source,
                    "geometry_truth": editable_text_layout_source,
                    "boxes": boxes_to_json(boxes),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        block = pages.get(page_number)
        if block is not None:
            content = extract_content(block)
            slide_title = content.title
            subtitle = content.subtitle
            notes_text = page_notes_text(block)
            title_for_name = block.title
        else:
            slide_title = str(pair.get("title") or page_number)
            subtitle = ""
            notes_text = ""
            title_for_name = slide_title

        background_href = _background_href_for_svg(prepared_background)
        text_opacity = 0.0 if editable_text_visibility == "hidden" else 1.0
        svg = render_overlay_svg(
            background_href=background_href,
            canvas={"width": CANVAS_SIZE[0], "height": CANVAS_SIZE[1]},
            body_region=body,
            slide_title=slide_title,
            subtitle=subtitle,
            text_boxes=boxes,
            text_opacity=text_opacity,
        )
        stem = page_stem(page_number, title_for_name)
        (project_path / "svg_output" / f"{stem}.svg").write_text(svg, encoding="utf-8")
        (project_path / "notes" / f"{stem}.md").write_text(f"# {slide_title}\n\n{notes_text}\n", encoding="utf-8")
        svg_count += 1
        quality_pages.append(
            {
                "page_number": page_number,
                "title": title_for_name,
                "rebuild_mode": rebuild_mode,
                "semantic_plan": str(semantic_plan_path),
                "semantic_plan_gate": str(semantic_gate_path),
                "semantic_layout_plan": str(semantic_layout_path),
                "scene_graph": str(scene_graph_paths["graph"]),
                "scene_graph_gate": str(scene_graph_paths["gate"]),
                "page_layout_plan": str(scene_graph_paths["layout"]),
                "semantic_source": semantic_source,
                "editable_text_layout_source": editable_text_layout_source,
                "visual_registry_source": visual_registry_source,
                "semantic_containers": str(containers_path),
                "text_forensics": str(forensic_path.resolve()),
                "ocr_quality_gate": quality_report,
                "image_size_check": image_size_check,
                "text_color_check": {
                    "white_text_boxes": sum(1 for box in boxes if box.fill.upper() == "#FFFFFF"),
                    "total_text_boxes": len(boxes),
                },
                "visible_image_variant": visible_image_variant,
                "editable_text_visibility": editable_text_visibility,
            }
        )

    _write_rebuild_quality(project_path, quality_pages)
    _write_json(
        background_scan_dir / "background_text_scan_index.json",
        {
            "schema": "cyberppt.dual_image.background_text_scan_set.v1",
            "valid": bool(background_scan_pages) and all(page["valid"] for page in background_scan_pages),
            "page_count": len(background_scan_pages),
            "error_count": sum(int(page.get("error_count", 0) or 0) for page in background_scan_pages),
            "pages": background_scan_pages,
        },
    )
    _write_json(
        typography_qa_dir / "semantic_typography_qa_index.json",
        {
            "schema": "cyberppt.dual_image.semantic_typography_qa_set.v1",
            "valid": bool(typography_qa_pages) and all(page["valid"] for page in typography_qa_pages),
            "page_count": len(typography_qa_pages),
            "correction_count": sum(int(page.get("correction_count", 0) or 0) for page in typography_qa_pages),
            "pages": typography_qa_pages,
        },
    )
    return {"project_path": str(project_path), "slides": svg_count, "svg_dir": str(project_path / "svg_output")}


def export_project(project_path: Path) -> Path:
    commands = [
        [sys.executable, str(SCRIPTS_DIR / "svg_quality_checker.py"), str(project_path)],
        [sys.executable, str(SCRIPTS_DIR / "finalize_svg.py"), str(project_path)],
        [sys.executable, str(SCRIPTS_DIR / "svg_to_pptx.py"), str(project_path), "-t", "none", "-a", "none"],
    ]
    for command in commands:
        subprocess.run(command, check=True)
    exports = sorted((project_path / "exports").glob("*.pptx"), key=lambda p: p.stat().st_mtime)
    if not exports:
        raise FileNotFoundError(f"No PPTX exported in {project_path / 'exports'}")
    return exports[-1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rebuild CyberPPT full/background image pairs as template PPTX with editable text.")
    sub = parser.add_subparsers(dest="command", required=True)

    rebuild = sub.add_parser("rebuild", help="Rebuild overlay SVG pages from an existing page_image_pairs.json.")
    rebuild.add_argument("manifest", type=Path)
    rebuild.add_argument("--ocr-backend", choices=("paddleocr-local", "vision-json", "none"), default="vision-json")
    rebuild.add_argument("--force-ocr", action="store_true")
    rebuild.add_argument("--timeout", type=int, default=300)
    rebuild.add_argument("--visible-image-variant", choices=("background", "full"), default="background")
    rebuild.add_argument("--editable-text-visibility", choices=("visible", "hidden"), default="visible")
    rebuild.add_argument("--semantic-plan-dir", type=Path)
    rebuild.add_argument("--visual-registry-dir", type=Path)
    rebuild.add_argument("--export", action="store_true", help="Run SVG quality/finalize/export after rebuilding SVG pages.")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = rebuild_from_manifest(
            args.manifest,
            ocr_backend=args.ocr_backend,
            force_ocr=args.force_ocr,
            timeout=args.timeout,
            visible_image_variant=args.visible_image_variant,
            editable_text_visibility=args.editable_text_visibility,
            explicit_semantic_plan_dir=args.semantic_plan_dir.resolve() if args.semantic_plan_dir else None,
            visual_registry_dir=args.visual_registry_dir.resolve() if args.visual_registry_dir else None,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.export:
            pptx = export_project(Path(result["project_path"]))
            print(f"PPTX: {pptx}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
