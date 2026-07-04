#!/usr/bin/env python3
"""Dual-image text-overlay rebuild.

This standalone route takes a text-bearing full slide image and a no-text
background image, normalizes both to a PPT canvas, aligns the full image to the
background image, and exports a PPTX with the background as a locked picture and
visible text as editable PowerPoint text boxes. The visible wording is an
AI-designed display layer (`display_text`) derived from semantic understanding;
source wording remains provenance for notes and review.
"""

from __future__ import annotations

import argparse
import copy
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageStat
from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.util import Emu, Pt

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from project_manager import ProjectManager  # noqa: E402
from svg_to_pptx.pptx_notes import (  # noqa: E402
    create_notes_slide_rels_xml,
    create_notes_slide_xml,
    markdown_to_plain_text,
)

from image_to_editable_pptx_lib import (  # noqa: E402
    build_manifest,
    scaffold_content_mapping,
    scaffold_text_region_map,
)


class _ScaffoldConfig:
    def __init__(self, *, image: Path, name: str, canvas_format: str, text_density: str) -> None:
        self.image = image
        self.name = name
        self.canvas_format = canvas_format
        self.text_density = text_density


CANVAS = (1280, 720)
EMU_PER_PX = 9525

BODY_TEXT_ROLES = {
    "actor_summary",
    "body_summary",
    "chain_body",
    "profit_body",
    "product_body",
    "service_item",
    "stage_body",
    "trust_body",
}
LEFT_BODY_TEXT_ROLES = {"actor_summary", "body_summary", "product_body", "trust_body"}
ROLE_TYPESETTING_POLICY: dict[str, dict[str, Any]] = {
    "actor_summary": {"min_font_size": 9.0, "align": "left", "v_align": "top"},
    "body_summary": {"min_font_size": 9.0, "align": "left", "v_align": "top"},
    "chain_body": {"min_font_size": 9.0, "v_align": "middle"},
    "product_body": {"min_font_size": 9.0, "align": "left", "v_align": "top"},
    "profit_body": {"min_font_size": 9.0, "v_align": "middle"},
    "section_title": {"min_font_size": 11.0},
    "service_item": {"min_font_size": 9.0},
    "stage_body": {"min_font_size": 9.0, "v_align": "top"},
    "trust_body": {"min_font_size": 7.0, "align": "left", "v_align": "top"},
}
DEFAULT_TYPESETTING_POLICY = {"min_font_size": 8.0}
STYLE_KEYS = ("font_size", "font_weight", "fill", "align", "v_align", "word_wrap")

# QA severity thresholds. These decide which findings are hard failures (severity
# "error", counted in layout_qa["error_count"] and able to flip the CLI exit code)
# versus soft findings (severity "warning", reported but never blocking). Kept as
# named constants so tuning the bar does not require touching the check logic.
QA_SAFE_BBOX_ERROR_OVERFLOW_PX = 8.0
QA_VERTICAL_OVERFLOW_ERROR_RATIO = 0.35
QA_BOX_OVERLAP_ERROR_RATIO = 0.08

# Row/column eligibility gates for infer_semantic_containers_from_full_style()'s
# fallback container inference. These values were reverse-engineered from one
# reference slide (project page012) and are the primary generalization risk
# flagged in the dual-image-rebuild diagnostic brief (docs/zh/dual-image-rebuild-
# workflow-diagnostic-brief.md, 2026-07-03 review): a slide whose bands don't
# line up with these thresholds will have items silently miss their intended
# container and fall through to `isolated_text_region` instead. Pass a `profile`
# dict to infer_semantic_containers_from_full_style() to override any subset of
# these per project; do not edit the defaults for a one-off slide.
CONTAINER_INFERENCE_DEFAULT_PROFILE: dict[str, float] = {
    "stage_row_max_y": 240.0,
    "chain_label_row_min_y": 300.0,
    "chain_label_row_max_y": 370.0,
    "chain_label_max_x": 940.0,
    "chain_body_row_min_y": 340.0,
    "chain_body_row_max_y": 450.0,
    "chain_body_max_x": 940.0,
    "service_row_min_y": 600.0,
    "service_title_row_max_y": 665.0,
    "trust_card_min_x": 1104.0,
    "trust_card_max_x": 1268.0,
    "trust_card_container_min_x": 1084.0,
    "trust_card_container_max_x": 1273.0,
    "side_actor_row_max_y": 330.0,
    "side_actor_left_max_x": 180.0,
    "side_actor_right_min_x": 1080.0,
    "terminal_chain_min_x": 940.0,
    "terminal_chain_max_width": 90.0,
    # Row-anchor coordinates below decide *where on the canvas* each card
    # family's container/text-safe band sits. Unlike the eligibility gates
    # above (which decide whether an item joins a family), these decide the
    # constructed geometry once it has. They carry the same page012-specific
    # risk: a slide whose card rows sit at different heights needs these
    # overridden too, not just the gates above. Local padding/sizing-ratio
    # constants inside each branch remain inline; they tune a few pixels of
    # fit rather than gross card placement, so parameterizing them has much
    # lower generalization payoff for the added surface area.
    "stage_card_container_top": 56.0,
    "stage_card_container_bottom": 220.0,
    "stage_card_text_top": 72.0,
    "product_panel_container_top": 480.0,
    "product_panel_container_bottom": 558.0,
    "product_panel_text_top": 492.0,
    "product_panel_text_bottom": 550.0,
    "chain_card_container_top": 316.0,
    "chain_card_container_bottom": 456.0,
    "chain_card_text_top": 326.0,
    "chain_card_text_bottom": 448.0,
    "service_card_container_top": 620.0,
    "service_card_container_bottom": 698.0,
    "service_card_text_top": 628.0,
    "service_card_text_bottom": 692.0,
    "trust_card_group_top_min": 374.0,
    "trust_card_group_bottom_fallback": 705.0,
}

REQUIRED_FRAMEWORK_ROLES = {
    "lifecycle_outer_frame",
    "processing_chain_frame",
    "left_role_swimlane_frame",
    "right_trust_frame",
    "service_product_frame",
    "third_party_service_frame",
    "actor_endpoint_frame",
}


@dataclass(frozen=True)
class AlignmentTransform:
    scale: float = 1.0
    dx: float = 0.0
    dy: float = 0.0
    score: float = 0.0
    model: str = "uniform-scale-translation"

    def map_point(self, x: float, y: float, canvas: tuple[int, int] = CANVAS) -> tuple[float, float]:
        cx = canvas[0] / 2.0
        cy = canvas[1] / 2.0
        return (
            cx + (x - cx) * self.scale + self.dx,
            cy + (y - cy) * self.scale + self.dy,
        )

    def map_bbox(self, bbox: list[float], canvas: tuple[int, int] = CANVAS) -> list[float]:
        x1, y1 = self.map_point(bbox[0], bbox[1], canvas)
        x2, y2 = self.map_point(bbox[2], bbox[3], canvas)
        return [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]


@dataclass
class OverlayTextBox:
    text: str
    x: float
    y: float
    w: float
    h: float
    font_size: float
    font_family: str
    fill: str
    font_weight: str = "400"
    align: str = "left"
    confidence: float = 1.0
    source_bbox: list[float] | None = None
    mapped_bbox: list[float] | None = None
    role: str = "text"
    word_wrap: bool = False
    source_text: str = ""
    v_align: str = "top"
    container_id: str = ""
    container_role: str = ""
    container_safe_bbox: list[float] | None = None
    reserved_zones: list[dict[str, Any]] | None = None
    group_id: str = ""
    group_align: str = ""
    layout_strategy: str = ""
    semantic_compression_level: str = ""


def _project_name(value: str | None, full_image: Path) -> str:
    if value:
        return value
    return f"dual_image_rebuild_{full_image.stem}"


def _image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def normalize_image(source: Path, target: Path, canvas: tuple[int, int] = CANVAS) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image.convert("RGB").resize(canvas, Image.Resampling.LANCZOS).save(target)


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON must be an object: {path}")
    return data


def _run_tool(script_name: str, args: list[str], *, cwd: Path) -> None:
    command = [sys.executable, str(_SCRIPTS_DIR / script_name), *args]
    subprocess.run(command, cwd=cwd, check=True)


def run_architecture_intake(project: Path, reference_image_rel: str) -> dict[str, str]:
    """Run the original image-rebuild Phase A intake artifacts for dual-image mode."""
    reference_image = project / reference_image_rel
    manifest_path = project / "slide_image_rebuild_manifest.json"
    manifest = build_manifest(
        _ScaffoldConfig(
            image=reference_image,
            name=project.name,
            canvas_format="ppt169",
            text_density="dense_formal_cn",
        ),
        reference_image_rel,
    )
    manifest["workflow"] = "dual-image-rebuild-ppt"
    manifest["dual_image_rebuild"] = {
        "mode": "background_snapshot_editable_text",
        "phase_a": "original_slide_image_rebuild_architecture_intake",
        "phase_b": "semantic_text_overlay_only",
        "text_display_policy": "ai_designed_display_text_from_semantics",
        "container_fit_policy": "container_first_safe_bbox_then_nudge_shrink_simplify",
        "do_not_draw": ["shapes", "icons", "arrows", "connectors", "charts", "decorations"],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    normalized = project / "images" / "reference_layout.normalized.png"
    try:
        _run_tool(
            "preprocess_reference_image.py",
            [str(reference_image), "--project", str(project)],
            cwd=_SCRIPTS_DIR.parent,
        )
    except subprocess.CalledProcessError:
        pass

    extract_args = [
        str(reference_image),
        "--project",
        str(project),
        "--copy-image",
        "--rebuild2",
        "--output",
        str(project / "layout_reference.json"),
    ]
    if normalized.is_file():
        extract_args.extend(["--normalized-image", str(normalized)])
    _run_tool("extract_layout_reference_from_image.py", extract_args, cwd=_SCRIPTS_DIR.parent)

    layout = _read_json(project / "layout_reference.json")
    content_mapping_path = project / "content_mapping.json"
    text_region_path = project / "text_region_map.json"
    content_mapping_path.write_text(
        json.dumps(scaffold_content_mapping(layout), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    text_region_path.write_text(
        json.dumps(scaffold_text_region_map(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for script_name, args in (
        ("layout_reference_to_design_spec.py", [str(project), "--write-design-spec"]),
        ("layout_reference_to_svg_plan.py", [str(project)]),
    ):
        _run_tool(script_name, args, cwd=_SCRIPTS_DIR.parent)

    return {
        "manifest": str(manifest_path),
        "layout_reference": str(project / "layout_reference.json"),
        "content_mapping": str(content_mapping_path),
        "text_region_map": str(text_region_path),
        "design_spec": str(project / "design_spec.md"),
        "svg_build_plan": str(project / "svg_build_plan.md"),
    }


def _num(value: Any, *, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric.") from exc


def normalize_text_layout(layout: dict[str, Any], *, canvas: tuple[int, int] = CANVAS) -> dict[str, Any]:
    image_size = layout.get("image_size")
    if not isinstance(image_size, dict):
        raise ValueError("text layout missing image_size.")
    src_w = _num(image_size.get("width"), field="image_size.width")
    src_h = _num(image_size.get("height"), field="image_size.height")
    if src_w <= 0 or src_h <= 0:
        raise ValueError("image_size must be positive.")
    sx = canvas[0] / src_w
    sy = canvas[1] / src_h

    normalized: list[dict[str, Any]] = []
    items = layout.get("items")
    if not isinstance(items, list):
        raise ValueError("text layout items must be an array.")
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"items[{index}] must be an object.")
        text = str(item.get("display_text") or item.get("text") or item.get("source_text") or "").strip()
        if not text:
            continue
        bbox = item.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            raise ValueError(f"items[{index}].bbox must be [x1, y1, x2, y2].")
        x1, y1, x2, y2 = [_num(v, field=f"items[{index}].bbox") for v in bbox]
        if x2 <= x1 or y2 <= y1:
            raise ValueError(f"items[{index}].bbox must satisfy x2>x1 and y2>y1.")
        record = {
            "text": text,
            "display_text": text,
            "bbox": [x1 * sx, y1 * sy, x2 * sx, y2 * sy],
            "confidence": float(item.get("confidence", 1.0) or 1.0),
            "role": str(item.get("role") or "text"),
        }
        for key in (
            "source_text",
            "source_meaning",
            "semantic_intent",
            "font_size",
            "font_weight",
            "fill",
            "align",
            "word_wrap",
            "lock_bbox",
            "container_id",
            "container_bbox",
            "container_text_safe_bbox",
            "container_role",
            "container_has_text_safe_bbox",
            "text_safe_bbox",
            "container_fit",
            "v_align",
            "container_safe_bbox",
            "reserved_zones",
            "container_reserved_zones",
            "group_id",
            "group_align",
            "layout_rationale",
            "semantic_compression_level",
            "layout_strategy",
            "fit_order",
        ):
            if key in item:
                record[key] = item[key]
        normalized.append(record)
    return {"image_size": {"width": canvas[0], "height": canvas[1]}, "items": normalized}


def _scale_bbox(
    bbox: list[Any],
    *,
    src_w: float,
    src_h: float,
    canvas: tuple[int, int],
) -> list[float]:
    x1, y1, x2, y2 = [_num(value, field="bbox") for value in bbox]
    return [
        x1 * canvas[0] / src_w,
        y1 * canvas[1] / src_h,
        x2 * canvas[0] / src_w,
        y2 * canvas[1] / src_h,
    ]


def _relative_bbox(container_bbox: list[float], relative: list[Any]) -> list[float]:
    if not isinstance(relative, list) or len(relative) != 4:
        raise ValueError("relative_bbox must be [x1, y1, x2, y2].")
    rx1, ry1, rx2, ry2 = [_num(value, field="relative_bbox") for value in relative]
    cx1, cy1, cx2, cy2 = container_bbox
    width = cx2 - cx1
    height = cy2 - cy1
    if max(abs(rx1), abs(ry1), abs(rx2), abs(ry2)) <= 1.5:
        return [cx1 + rx1 * width, cy1 + ry1 * height, cx1 + rx2 * width, cy1 + ry2 * height]
    return [cx1 + rx1, cy1 + ry1, cx1 + rx2, cy1 + ry2]


def normalize_semantic_plan(plan: dict[str, Any], *, canvas: tuple[int, int] = CANVAS) -> dict[str, Any]:
    """Normalize an optional semantic plan.

    Schema is intentionally lightweight:
    {
      "title": "...",
      "notes": "Markdown notes" | ["line", ...],
      "items": [
        {
          "source_text": "semantic source truth",
          "display_text": "AI-designed visible wording",
          "bbox": [x1,y1,x2,y2],
          "role": "..."
        }
      ]
    }
    """
    normalized = dict(plan)
    image_size = normalized.get("image_size")
    if isinstance(image_size, dict):
        src_w = _num(image_size.get("width"), field="image_size.width")
        src_h = _num(image_size.get("height"), field="image_size.height")
    else:
        src_w, src_h = canvas

    containers: list[dict[str, Any]] = []
    container_map: dict[str, dict[str, Any]] = {}
    for index, container in enumerate(normalized.get("containers") or []):
        if not isinstance(container, dict):
            raise ValueError(f"containers[{index}] must be an object.")
        container_id = str(container.get("id") or "").strip()
        bbox = container.get("bbox")
        if not container_id or not isinstance(bbox, list) or len(bbox) != 4:
            raise ValueError(f"containers[{index}] requires id and bbox.")
        normalized_bbox = _scale_bbox(bbox, src_w=src_w, src_h=src_h, canvas=canvas)
        record = dict(container)
        record["bbox"] = normalized_bbox
        text_safe_bbox = container.get("text_safe_bbox")
        has_text_safe_bbox = isinstance(text_safe_bbox, list) and len(text_safe_bbox) == 4
        if has_text_safe_bbox:
            record["text_safe_bbox"] = _scale_bbox(text_safe_bbox, src_w=src_w, src_h=src_h, canvas=canvas)
        reserved_zones = container.get("reserved_zones")
        if isinstance(reserved_zones, list):
            scaled_zones: list[dict[str, Any]] = []
            for zone_index, zone in enumerate(reserved_zones):
                if isinstance(zone, dict):
                    zone_bbox = zone.get("bbox")
                    zone_name = str(zone.get("name") or f"reserved_zone_{zone_index}")
                    zone_reason = str(zone.get("reason") or "")
                else:
                    zone_bbox = zone
                    zone_name = f"reserved_zone_{zone_index}"
                    zone_reason = ""
                if isinstance(zone_bbox, list) and len(zone_bbox) == 4:
                    scaled_zones.append(
                        {
                            "name": zone_name,
                            "bbox": _scale_bbox(zone_bbox, src_w=src_w, src_h=src_h, canvas=canvas),
                            "reason": zone_reason,
                        }
                    )
            if scaled_zones:
                record["reserved_zones"] = scaled_zones
        containers.append(record)
        container_map[container_id] = {
            "bbox": normalized_bbox,
            "text_safe_bbox": record.get("text_safe_bbox", normalized_bbox),
            "role": str(record.get("role") or ""),
            "has_text_safe_bbox": has_text_safe_bbox,
            "reserved_zones": record.get("reserved_zones", []),
        }
    normalized["containers"] = containers

    if "items" not in normalized:
        return normalized

    items: list[dict[str, Any]] = []
    for index, item in enumerate(normalized.get("items") or []):
        if not isinstance(item, dict):
            raise ValueError(f"items[{index}] must be an object.")
        record = dict(item)
        container_id = str(record.get("container_id") or "").strip()
        container_record = container_map.get(container_id)
        if "relative_bbox" in record:
            if container_record is None:
                raise ValueError(f"items[{index}] relative_bbox references unknown container_id: {container_id}")
            record["bbox"] = _relative_bbox(container_record["bbox"], record["relative_bbox"])
            record.pop("relative_bbox", None)
        elif isinstance(record.get("bbox"), list):
            record["bbox"] = _scale_bbox(record["bbox"], src_w=src_w, src_h=src_h, canvas=canvas)
        else:
            raise ValueError(f"items[{index}] requires bbox or relative_bbox.")
        if container_record is not None:
            record["container_bbox"] = container_record["bbox"]
            record["container_text_safe_bbox"] = container_record["text_safe_bbox"]
            record["container_role"] = container_record["role"]
            record["container_has_text_safe_bbox"] = container_record["has_text_safe_bbox"]
            record["container_reserved_zones"] = container_record.get("reserved_zones", [])
        items.append(record)
    normalized["items"] = normalize_text_layout(
        {"image_size": {"width": canvas[0], "height": canvas[1]}, "items": items},
        canvas=canvas,
    )["items"]
    normalized["image_size"] = {"width": canvas[0], "height": canvas[1]}
    return normalized


def semantic_items_or_layout(plan: dict[str, Any] | None, layout: dict[str, Any]) -> dict[str, Any]:
    if plan and isinstance(plan.get("items"), list) and plan["items"]:
        return {"image_size": {"width": CANVAS[0], "height": CANVAS[1]}, "items": plan["items"]}
    return layout


def semantic_plan_owns_geometry(plan: dict[str, Any] | None) -> bool:
    """Return true when semantic-plan coordinates should be final geometry truth."""
    if not plan:
        return False
    return bool(plan.get("containers")) and bool(plan.get("items"))


def _issue(
    severity: str,
    code: str,
    *,
    item_index: int | None = None,
    container_id: str | None = None,
    recommended_action: str,
    **extra: Any,
) -> dict[str, Any]:
    issue = {
        "severity": severity,
        "code": code,
        "item_index": item_index,
        "container_id": container_id,
        "recommended_action": recommended_action,
    }
    issue.update(extra)
    return issue


def validate_semantic_plan(plan: dict[str, Any] | None) -> dict[str, Any]:
    if not plan:
        return {
            "valid": False,
            "error_count": 1,
            "warning_count": 0,
            "issues": [
                _issue(
                    "error",
                    "missing_semantic_plan",
                    recommended_action="provide semantic_plan with explicit containers and linked items",
                )
            ],
        }

    containers = {
        str(container.get("id") or ""): container
        for container in plan.get("containers", [])
        if isinstance(container, dict)
    }
    issues: list[dict[str, Any]] = []

    for index, item in enumerate(plan.get("items", [])):
        if not isinstance(item, dict):
            issues.append(
                _issue(
                    "error",
                    "invalid_item",
                    item_index=index,
                    recommended_action="make every semantic_plan.items entry an object",
                )
            )
            continue

        role = str(item.get("role") or "")
        container_id = str(item.get("container_id") or "")
        container = containers.get(container_id)
        if not container:
            issues.append(
                _issue(
                    "error",
                    "missing_container",
                    item_index=index,
                    container_id=container_id,
                    recommended_action="add semantic_plan.containers entry or correct item.container_id",
                )
            )
            continue

        container_role = str(container.get("role") or "")
        if container_role == "isolated_text_region" and role in BODY_TEXT_ROLES:
            issues.append(
                _issue(
                    "error",
                    "body_in_isolated_region",
                    item_index=index,
                    container_id=container_id,
                    recommended_action="use a semantic container role such as trust_card, content_card, or stage_card for body text",
                    role=role,
                )
            )

        font_size = item.get("font_size")
        if font_size is not None:
            min_font_size = float(_role_policy(role).get("min_font_size", DEFAULT_TYPESETTING_POLICY["min_font_size"]))
            if float(font_size) < min_font_size:
                issues.append(
                    _issue(
                        "error",
                        "font_below_role_minimum",
                        item_index=index,
                        container_id=container_id,
                        recommended_action=f"increase font_size to at least {min_font_size:g} or shorten display_text",
                        role=role,
                        font_size=float(font_size),
                        min_font_size=min_font_size,
                    )
                )

        safe_bbox = container.get("text_safe_bbox")
        container_bbox = container.get("bbox")
        if isinstance(safe_bbox, list) and isinstance(container_bbox, list):
            if not _bbox_inside([float(v) for v in safe_bbox], [float(v) for v in container_bbox], tolerance=1.0):
                issues.append(
                    _issue(
                        "error",
                        "safe_bbox_outside_container",
                        item_index=index,
                        container_id=container_id,
                        recommended_action="move container.text_safe_bbox inside container.bbox",
                    )
                )

    error_count = sum(1 for issue in issues if issue["severity"] == "error")
    warning_count = sum(1 for issue in issues if issue["severity"] == "warning")
    return {
        "valid": error_count == 0,
        "error_count": error_count,
        "warning_count": warning_count,
        "issues": issues,
    }


def _bbox_width(bbox: list[float]) -> float:
    return max(1.0, float(bbox[2]) - float(bbox[0]))


def _bbox_height(bbox: list[float]) -> float:
    return max(1.0, float(bbox[3]) - float(bbox[1]))


def _role_policy(role: str) -> dict[str, Any]:
    return ROLE_TYPESETTING_POLICY.get(role, DEFAULT_TYPESETTING_POLICY)


def _bbox_cx(bbox: list[float]) -> float:
    return (float(bbox[0]) + float(bbox[2])) / 2.0


def _bbox_cy(bbox: list[float]) -> float:
    return (float(bbox[1]) + float(bbox[3])) / 2.0


def _union_bbox(boxes: list[list[float]]) -> list[float]:
    return [
        min(float(box[0]) for box in boxes),
        min(float(box[1]) for box in boxes),
        max(float(box[2]) for box in boxes),
        max(float(box[3]) for box in boxes),
    ]


def _has_semantic_container(item: dict[str, Any]) -> bool:
    return bool(
        item.get("container_id")
        or item.get("container_bbox")
        or item.get("container_text_safe_bbox")
        or item.get("container_safe_bbox")
        or item.get("text_safe_bbox")
    )


def _text_units(text: str) -> int:
    return sum(1 for char in text if not char.isspace())


def _text_lines(text: str) -> list[str]:
    return [line.strip() for line in str(text).splitlines() if line.strip()] or [str(text).strip()]


def _normalize_text_lines(text: str) -> str:
    return "\n".join(" ".join(line.split()) for line in str(text).strip().splitlines() if line.strip())


def _linebreaks_are_semantically_locked(item: dict[str, Any]) -> bool:
    return bool(
        item.get("preserve_linebreaks")
        or item.get("lock_linebreaks")
        or item.get("preserve_hard_linebreaks")
        or item.get("linebreak_policy") == "preserve"
    )


def _join_wrapped_fragments(left: str, right: str) -> str:
    left = left.rstrip()
    right = right.lstrip()
    if not left:
        return right
    if not right:
        return left
    if left[-1].isascii() and right[0].isascii() and left[-1].isalnum() and right[0].isalnum():
        return f"{left} {right}"
    return f"{left}{right}"


def _starts_new_list_item(line: str) -> bool:
    stripped = line.lstrip()
    return any(stripped.startswith(marker) for marker in ("·", "•", "- ", "– ", "— ", "* "))


def _normalize_full_image_linebreaks(text: str) -> str:
    """Treat full-image hard line breaks as layout artifacts unless list semantics are visible."""
    lines = [" ".join(line.split()) for line in str(text).strip().splitlines() if line.strip()]
    if len(lines) <= 1:
        return lines[0] if lines else ""

    if any(_starts_new_list_item(line) for line in lines):
        items: list[str] = []
        current = ""
        for line in lines:
            if _starts_new_list_item(line):
                if current:
                    items.append(current)
                current = line
            else:
                current = _join_wrapped_fragments(current, line)
        if current:
            items.append(current)
        return "\n".join(items)

    merged = ""
    for line in lines:
        merged = _join_wrapped_fragments(merged, line)
    return merged


def build_text_style_profile(layout: dict[str, Any]) -> dict[str, Any]:
    """Record text-layer style from the full reference image without owning final geometry."""
    role_records: dict[str, list[dict[str, Any]]] = {}
    item_profiles: list[dict[str, Any]] = []
    for index, item in enumerate(layout.get("items", [])):
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "text")
        bbox = item.get("bbox")
        record = {
            "index": index,
            "text": item.get("text") or item.get("display_text") or "",
            "role": role,
            "bbox": _round_bbox([float(v) for v in bbox]) if isinstance(bbox, list) and len(bbox) == 4 else None,
            "style": {key: item[key] for key in STYLE_KEYS if key in item},
        }
        item_profiles.append(record)
        role_records.setdefault(role, []).append(record)

    role_profiles: dict[str, Any] = {}
    for role, records in role_records.items():
        font_sizes = [
            float(record["style"]["font_size"])
            for record in records
            if isinstance(record.get("style"), dict) and record["style"].get("font_size") is not None
        ]
        fills = [
            str(record["style"].get("fill"))
            for record in records
            if isinstance(record.get("style"), dict) and record["style"].get("fill")
        ]
        weights = [
            str(record["style"].get("font_weight"))
            for record in records
            if isinstance(record.get("style"), dict) and record["style"].get("font_weight")
        ]
        aligns = [
            str(record["style"].get("align"))
            for record in records
            if isinstance(record.get("style"), dict) and record["style"].get("align")
        ]
        boxes = [record["bbox"] for record in records if isinstance(record.get("bbox"), list)]
        role_profiles[role] = {
            "count": len(records),
            "font_size_min": round(min(font_sizes), 2) if font_sizes else None,
            "font_size_max": round(max(font_sizes), 2) if font_sizes else None,
            "font_size_avg": round(sum(font_sizes) / len(font_sizes), 2) if font_sizes else None,
            "fills": sorted(set(fills)),
            "font_weights": sorted(set(weights)),
            "alignments": sorted(set(aligns)),
            "bbox_union": _round_bbox(_union_bbox(boxes)) if boxes else None,
        }

    return {
        "workflow": "dual-image-rebuild-ppt",
        "stage": "full_image_text_style_profile",
        "geometry_policy": "learn_typography_grouping_and_rhythm_but_do_not_use_ocr_ink_bbox_as_final_container",
        "role_profiles": role_profiles,
        "items": item_profiles,
    }


def _assign_container(
    item: dict[str, Any],
    *,
    container_id: str,
    container_role: str,
    container_bbox: list[float],
    text_safe_bbox: list[float],
) -> None:
    if _has_semantic_container(item):
        return
    item["container_id"] = container_id
    item["container_role"] = container_role
    item["container_bbox"] = [float(v) for v in container_bbox]
    item["container_text_safe_bbox"] = [float(v) for v in text_safe_bbox]
    item["container_safe_bbox"] = [float(v) for v in text_safe_bbox]
    item["container_has_text_safe_bbox"] = True
    item["container_fit"] = True


def _nearest_index(
    indexes: list[int],
    items: list[dict[str, Any]],
    *,
    target_x: float,
    target_y: float | None = None,
    max_dx: float,
    used: set[int] | None = None,
) -> int | None:
    candidates: list[tuple[float, int]] = []
    for index in indexes:
        if used and index in used:
            continue
        bbox = items[index].get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue
        dx = abs(_bbox_cx([float(v) for v in bbox]) - target_x)
        if dx > max_dx:
            continue
        dy = abs(_bbox_cy([float(v) for v in bbox]) - target_y) if target_y is not None else 0.0
        candidates.append((dx + dy * 0.15, index))
    if not candidates:
        return None
    return min(candidates)[1]


def _isolated_near_miss(role: str, bbox: list[float], cfg: dict[str, Any]) -> dict[str, Any] | None:
    """Best-effort diagnosis for why a body-eligible item fell through to
    `isolated_text_region`: report the single eligibility gate it came closest
    to passing, and by how much. This only covers gate-threshold misses (an
    item whose role belongs to a known family but sits just outside the
    profile's row/column band) -- the P0 generalization risk in the diagnostic
    brief. It does not cover an item that passed its gate but simply found no
    nearby sibling to pair with; that failure mode already shows up as a
    smaller `actions` count than the eligible-item count and does not need a
    per-item gate delta. Returns None when the role has no known family gate
    or when every gate the role is subject to already passes (so the isolation
    has some other cause).
    """
    x1, y1, x2, y2 = bbox
    failing: list[dict[str, Any]] = []

    def _check(gate: str, passed: bool, actual: float, threshold: float) -> None:
        if not passed:
            failing.append(
                {
                    "gate": gate,
                    "actual": round(actual, 1),
                    "threshold": threshold,
                    "miss_by": round(abs(actual - threshold), 1),
                }
            )

    if role in {"stage_label", "stage_body"}:
        _check("stage_row_max_y", y1 < cfg["stage_row_max_y"], y1, cfg["stage_row_max_y"])
    elif role == "chain_label":
        _check("chain_label_row_min_y", y1 >= cfg["chain_label_row_min_y"], y1, cfg["chain_label_row_min_y"])
        _check("chain_label_row_max_y", y1 <= cfg["chain_label_row_max_y"], y1, cfg["chain_label_row_max_y"])
        _check("chain_label_max_x", x1 < cfg["chain_label_max_x"], x1, cfg["chain_label_max_x"])
    elif role == "chain_body":
        _check("chain_body_row_min_y", y1 >= cfg["chain_body_row_min_y"], y1, cfg["chain_body_row_min_y"])
        _check("chain_body_row_max_y", y1 <= cfg["chain_body_row_max_y"], y1, cfg["chain_body_row_max_y"])
        _check("chain_body_max_x", x1 < cfg["chain_body_max_x"], x1, cfg["chain_body_max_x"])
    elif role == "service_item":
        _check("service_row_min_y", y1 > cfg["service_row_min_y"], y1, cfg["service_row_min_y"])
    elif role == "actor_summary":
        _check("side_actor_row_max_y", y2 < cfg["side_actor_row_max_y"], y2, cfg["side_actor_row_max_y"])
        if not (x2 < cfg["side_actor_left_max_x"] or x1 > cfg["side_actor_right_min_x"]):
            miss_left = abs(x2 - cfg["side_actor_left_max_x"])
            miss_right = abs(x1 - cfg["side_actor_right_min_x"])
            if miss_left <= miss_right:
                failing.append(
                    {
                        "gate": "side_actor_left_max_x",
                        "actual": round(x2, 1),
                        "threshold": cfg["side_actor_left_max_x"],
                        "miss_by": round(miss_left, 1),
                    }
                )
            else:
                failing.append(
                    {
                        "gate": "side_actor_right_min_x",
                        "actual": round(x1, 1),
                        "threshold": cfg["side_actor_right_min_x"],
                        "miss_by": round(miss_right, 1),
                    }
                )
    else:
        return None

    if not failing:
        return None
    return min(failing, key=lambda candidate: candidate["miss_by"])


def infer_semantic_containers_from_full_style(
    layout: dict[str, Any],
    *,
    profile: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Infer broad semantic text safe areas from full-image text grouping when containers are absent.

    `profile` overrides the row/column gates and card row-anchor coordinates in
    CONTAINER_INFERENCE_DEFAULT_PROFILE (merged over the defaults). Both were
    reverse-engineered from a single reference slide (project page012) and are
    the primary generalization risk called out in the dual-image-rebuild
    diagnostic brief: an item that falls outside the eligibility gates on a
    different slide silently drops through to the `isolated_text_region`
    catch-all instead of joining its real container, and even an item that
    passes the gates gets placed at a page012-shaped row height unless the
    row-anchor coordinates are also overridden. Local padding and sizing-ratio
    constants inside each branch remain inline and not parameterized; they tune
    a few pixels of local fit rather than gross card placement or routing.
    """
    cfg = {**CONTAINER_INFERENCE_DEFAULT_PROFILE, **(profile or {})}
    inferred = copy.deepcopy(layout)
    items = [item for item in inferred.get("items", []) if isinstance(item, dict)]
    actions: list[dict[str, Any]] = []

    stage_labels = [
        index
        for index, item in enumerate(items)
        if item.get("role") == "stage_label"
        and isinstance(item.get("bbox"), list)
        and float(item["bbox"][1]) < cfg["stage_row_max_y"]
    ]
    stage_bodies = [
        index
        for index, item in enumerate(items)
        if item.get("role") == "stage_body"
        and isinstance(item.get("bbox"), list)
        and float(item["bbox"][1]) < cfg["stage_row_max_y"]
    ]
    stage_indexes = [
        index
        for index, item in enumerate(items)
        if item.get("role") == "index"
        and isinstance(item.get("bbox"), list)
        and float(item["bbox"][1]) < cfg["stage_row_max_y"]
    ]
    used_stage_bodies: set[int] = set()
    used_stage_indexes: set[int] = set()
    stage_centers: list[tuple[float, int, int | None, int | None]] = []
    for label_index in sorted(stage_labels, key=lambda index: float(items[index]["bbox"][0])):
        label_bbox = [float(v) for v in items[label_index]["bbox"]]
        body_index = _nearest_index(
            stage_bodies,
            items,
            target_x=_bbox_cx(label_bbox),
            target_y=_bbox_cy(label_bbox) + 60.0,
            max_dx=92.0,
            used=used_stage_bodies,
        )
        if body_index is not None:
            used_stage_bodies.add(body_index)
        index_index = _nearest_index(
            stage_indexes,
            items,
            target_x=label_bbox[0] - 24.0,
            target_y=_bbox_cy(label_bbox),
            max_dx=76.0,
            used=used_stage_indexes,
        )
        if index_index is not None:
            used_stage_indexes.add(index_index)
        group_boxes = [[float(v) for v in items[i]["bbox"]] for i in (label_index, body_index, index_index) if i is not None]
        stage_centers.append((_bbox_cx(_union_bbox(group_boxes)), label_index, body_index, index_index))
    if len(stage_centers) >= 2:
        sorted_centers = [center for center, *_ in sorted(stage_centers)]
        gaps = [sorted_centers[pos + 1] - sorted_centers[pos] for pos in range(len(sorted_centers) - 1)]
        card_w = max(136.0, min(166.0, min(gaps) * 0.84))
        for position, (center, label_index, body_index, index_index) in enumerate(sorted(stage_centers)):
            x1 = max(0.0, center - card_w / 2.0)
            x2 = min(float(CANVAS[0]), center + card_w / 2.0)
            container_bbox = [x1, cfg["stage_card_container_top"], x2, cfg["stage_card_container_bottom"]]
            body_bbox = [float(v) for v in items[body_index]["bbox"]] if body_index is not None else [x1 + 48.0, 118.0, x2 - 10.0, 195.0]
            # The left part of a lifecycle card is occupied by its visual icon.
            # Expand text to the card's legal text area, but do not treat the
            # icon column as available typography space.
            safe_x1 = max(x1 + 14.0, body_bbox[0] - 4.0)
            safe_x2 = min(float(CANVAS[0]), min(x2 - 12.0, body_bbox[2] + 30.0))
            container_bbox[2] = max(container_bbox[2], safe_x2 + 18.0)
            text_safe_bbox = [safe_x1, cfg["stage_card_text_top"], safe_x2, container_bbox[3] - 4.0]
            for item_index in (label_index, body_index, index_index):
                if item_index is not None:
                    _assign_container(
                        items[item_index],
                        container_id=f"inferred_stage_card_{position + 1}",
                        container_role="stage_card",
                        container_bbox=container_bbox,
                        text_safe_bbox=text_safe_bbox,
                    )
            actions.append(
                {
                    "code": "inferred_stage_card_safe_bbox",
                    "container_id": f"inferred_stage_card_{position + 1}",
                    "text_safe_bbox": _round_bbox(text_safe_bbox),
                }
            )

    product_titles = [
        index
        for index, item in enumerate(items)
        if item.get("role") == "product_title" and isinstance(item.get("bbox"), list)
    ]
    product_bodies = [
        index
        for index, item in enumerate(items)
        if item.get("role") == "product_body" and isinstance(item.get("bbox"), list)
    ]
    product_groups: list[tuple[float, list[int], list[float]]] = []
    used_product_bodies: set[int] = set()
    for title_index in sorted(product_titles, key=lambda index: float(items[index]["bbox"][0])):
        title_bbox = [float(v) for v in items[title_index]["bbox"]]
        body_index = _nearest_index(
            product_bodies,
            items,
            target_x=_bbox_cx(title_bbox),
            target_y=_bbox_cy(title_bbox) + 30.0,
            max_dx=170.0,
            used=used_product_bodies,
        )
        indexes = [title_index]
        if body_index is not None:
            used_product_bodies.add(body_index)
            indexes.append(body_index)
        union = _union_bbox([[float(v) for v in items[index]["bbox"]] for index in indexes])
        product_groups.append((_bbox_cx(union), indexes, union))
    product_groups.sort(key=lambda record: record[0])
    product_midpoints = [
        (product_groups[pos][0] + product_groups[pos + 1][0]) / 2.0
        for pos in range(len(product_groups) - 1)
    ]
    for position, (_, indexes, union) in enumerate(product_groups):
        left = max(0.0, union[0] - 4.0)
        if position < len(product_midpoints):
            right = min(product_midpoints[position] - 16.0, CANVAS[0])
        else:
            right = min(float(CANVAS[0]), union[2] + max(96.0, _bbox_width(union) * 0.45))
        right = max(right, union[2] + 28.0)
        container_bbox = [
            max(0.0, left - 96.0),
            cfg["product_panel_container_top"],
            min(float(CANVAS[0]), right + 12.0),
            cfg["product_panel_container_bottom"],
        ]
        text_safe_bbox = [left, cfg["product_panel_text_top"], min(float(CANVAS[0]), right), cfg["product_panel_text_bottom"]]
        for item_index in indexes:
            _assign_container(
                items[item_index],
                container_id=f"inferred_product_panel_{position + 1}",
                container_role="product_panel",
                container_bbox=container_bbox,
                text_safe_bbox=text_safe_bbox,
            )
        actions.append(
            {
                "code": "inferred_product_panel_safe_bbox",
                "container_id": f"inferred_product_panel_{position + 1}",
                "text_safe_bbox": _round_bbox(text_safe_bbox),
            }
        )

    chain_labels = [
        index
        for index, item in enumerate(items)
        if item.get("role") == "chain_label"
        and isinstance(item.get("bbox"), list)
        and cfg["chain_label_row_min_y"] <= float(item["bbox"][1]) <= cfg["chain_label_row_max_y"]
        and float(item["bbox"][0]) < cfg["chain_label_max_x"]
    ]
    chain_bodies = [
        index
        for index, item in enumerate(items)
        if item.get("role") == "chain_body"
        and isinstance(item.get("bbox"), list)
        and cfg["chain_body_row_min_y"] <= float(item["bbox"][1]) <= cfg["chain_body_row_max_y"]
        and float(item["bbox"][0]) < cfg["chain_body_max_x"]
    ]
    chain_groups: list[tuple[float, int, int | None, list[float]]] = []
    used_chain_bodies: set[int] = set()
    for label_index in sorted(chain_labels, key=lambda index: float(items[index]["bbox"][0])):
        label_bbox = [float(v) for v in items[label_index]["bbox"]]
        body_index = _nearest_index(
            chain_bodies,
            items,
            target_x=_bbox_cx(label_bbox),
            target_y=_bbox_cy(label_bbox) + 48.0,
            max_dx=88.0,
            used=used_chain_bodies,
        )
        indexes = [label_index]
        if body_index is not None:
            used_chain_bodies.add(body_index)
            indexes.append(body_index)
        union = _union_bbox([[float(v) for v in items[index]["bbox"]] for index in indexes])
        chain_groups.append((_bbox_cx(union), label_index, body_index, union))
    if len(chain_groups) >= 2:
        centers = [center for center, *_ in sorted(chain_groups)]
        min_gap = min(centers[pos + 1] - centers[pos] for pos in range(len(centers) - 1))
        card_w = max(106.0, min(122.0, min_gap * 0.94))
        for position, (center, label_index, body_index, _union) in enumerate(sorted(chain_groups)):
            card_x1 = max(160.0, center - card_w / 2.0)
            card_x2 = min(980.0, center + card_w / 2.0)
            text_safe_bbox = [card_x1 + 8.0, cfg["chain_card_text_top"], card_x2 - 8.0, cfg["chain_card_text_bottom"]]
            container_bbox = [card_x1, cfg["chain_card_container_top"], card_x2, cfg["chain_card_container_bottom"]]
            for item_index in (label_index, body_index):
                if item_index is not None:
                    _assign_container(
                        items[item_index],
                        container_id=f"inferred_process_chain_card_{position + 1}",
                        container_role="process_chain_card",
                        container_bbox=container_bbox,
                        text_safe_bbox=text_safe_bbox,
                    )
            actions.append(
                {
                    "code": "inferred_process_chain_card_safe_bbox",
                    "container_id": f"inferred_process_chain_card_{position + 1}",
                    "text_safe_bbox": _round_bbox(text_safe_bbox),
                }
            )

    bottom_services = [
        index
        for index, item in enumerate(items)
        if item.get("role") == "service_item"
        and isinstance(item.get("bbox"), list)
        and float(item["bbox"][1]) > cfg["service_row_min_y"]
    ]
    service_titles = [
        index
        for index in bottom_services
        if _bbox_cy([float(v) for v in items[index]["bbox"]]) < cfg["service_title_row_max_y"]
    ]
    service_bodies = [index for index in bottom_services if index not in service_titles]
    used_service_bodies: set[int] = set()
    for position, title_index in enumerate(sorted(service_titles, key=lambda index: float(items[index]["bbox"][0]))):
        title_bbox = [float(v) for v in items[title_index]["bbox"]]
        body_index = _nearest_index(
            service_bodies,
            items,
            target_x=_bbox_cx(title_bbox),
            target_y=_bbox_cy(title_bbox) + 35.0,
            max_dx=170.0,
            used=used_service_bodies,
        )
        indexes = [title_index]
        if body_index is not None:
            used_service_bodies.add(body_index)
            indexes.append(body_index)
        union = _union_bbox([[float(v) for v in items[index]["bbox"]] for index in indexes])
        safe_left = max(0.0, union[0] - 10.0)
        safe_right = min(float(CANVAS[0]), union[2] + 10.0)
        container_bbox = [
            max(0.0, safe_left - 14.0),
            cfg["service_card_container_top"],
            min(float(CANVAS[0]), safe_right + 14.0),
            cfg["service_card_container_bottom"],
        ]
        text_safe_bbox = [safe_left, cfg["service_card_text_top"], safe_right, cfg["service_card_text_bottom"]]
        for item_index in indexes:
            _assign_container(
                items[item_index],
                container_id=f"inferred_service_card_{position + 1}",
                container_role="service_card",
                container_bbox=container_bbox,
                text_safe_bbox=text_safe_bbox,
            )
        actions.append(
            {
                "code": "inferred_service_card_safe_bbox",
                "container_id": f"inferred_service_card_{position + 1}",
                "text_safe_bbox": _round_bbox(text_safe_bbox),
            }
        )

    trust_titles = [
        index
        for index, item in enumerate(items)
        if item.get("role") == "trust_title" and isinstance(item.get("bbox"), list)
    ]
    trust_bodies = [
        index
        for index, item in enumerate(items)
        if item.get("role") == "trust_body" and isinstance(item.get("bbox"), list)
    ]
    used_trust_bodies: set[int] = set()
    trust_groups: list[tuple[int, int | None]] = []
    for title_index in sorted(trust_titles, key=lambda index: float(items[index]["bbox"][1])):
        title_bbox = [float(v) for v in items[title_index]["bbox"]]
        body_index = None
        candidates: list[tuple[float, int]] = []
        for index in trust_bodies:
            if index in used_trust_bodies:
                continue
            body_bbox = [float(v) for v in items[index]["bbox"]]
            if body_bbox[1] < title_bbox[1] - 2.0:
                continue
            candidates.append((abs(body_bbox[1] - title_bbox[3]), index))
        if candidates:
            body_index = min(candidates)[1]
            used_trust_bodies.add(body_index)
        trust_groups.append((title_index, body_index))
    if trust_groups:
        group_tops = [float(items[title_index]["bbox"][1]) - 22.0 for title_index, _ in trust_groups]
        for position, (title_index, body_index) in enumerate(trust_groups):
            title_bbox = [float(v) for v in items[title_index]["bbox"]]
            group_top = max(cfg["trust_card_group_top_min"], group_tops[position])
            if position + 1 < len(group_tops):
                group_bottom = max(group_top + 58.0, group_tops[position + 1] - 4.0)
            else:
                group_bottom = min(float(CANVAS[1]), max(title_bbox[3] + 58.0, cfg["trust_card_group_bottom_fallback"]))
            safe_left = max(cfg["trust_card_min_x"], title_bbox[0] - 2.0)
            safe_right = min(cfg["trust_card_max_x"], max(title_bbox[2] + 76.0, 1260.0))
            container_bbox = [cfg["trust_card_container_min_x"], group_top, cfg["trust_card_container_max_x"], group_bottom]
            text_safe_bbox = [safe_left, group_top + 18.0, safe_right, group_bottom - 6.0]
            for item_index in (title_index, body_index):
                if item_index is not None:
                    _assign_container(
                        items[item_index],
                        container_id=f"inferred_trust_card_{position + 1}",
                        container_role="trust_card",
                        container_bbox=container_bbox,
                        text_safe_bbox=text_safe_bbox,
                    )
            actions.append(
                {
                    "code": "inferred_trust_card_safe_bbox",
                    "container_id": f"inferred_trust_card_{position + 1}",
                    "text_safe_bbox": _round_bbox(text_safe_bbox),
                }
            )

    side_actor_summaries = [
        index
        for index, item in enumerate(items)
        if item.get("role") == "actor_summary"
        and isinstance(item.get("bbox"), list)
        and float(item["bbox"][3]) < cfg["side_actor_row_max_y"]
        and (
            float(item["bbox"][2]) < cfg["side_actor_left_max_x"]
            or float(item["bbox"][0]) > cfg["side_actor_right_min_x"]
        )
    ]
    for position, item_index in enumerate(side_actor_summaries):
        bbox = [float(v) for v in items[item_index]["bbox"]]
        is_left = _bbox_cx(bbox) < CANVAS[0] / 2
        if is_left:
            container_bbox = [
                max(0.0, bbox[0] - 12.0),
                max(0.0, bbox[1] - 32.0),
                min(170.0, max(158.0, bbox[2] + 18.0)),
                min(330.0, max(315.0, bbox[3] + 18.0)),
            ]
            text_safe_bbox = [
                max(10.0, container_bbox[0] + 10.0),
                bbox[1],
                min(container_bbox[2] - 10.0, max(bbox[2] + 12.0, 150.0)),
                min(container_bbox[3] - 9.0, max(bbox[3] + 14.0, 306.0)),
            ]
        else:
            container_bbox = [
                max(1088.0, bbox[0] - 24.0),
                max(0.0, bbox[1] - 32.0),
                min(float(CANVAS[0]), bbox[2] + 12.0),
                min(330.0, max(315.0, bbox[3] + 28.0)),
            ]
            text_safe_bbox = [
                max(container_bbox[0] + 10.0, min(bbox[0] - 14.0, 1110.0)),
                bbox[1],
                min(container_bbox[2] - 10.0, max(bbox[2], 1260.0)),
                min(container_bbox[3] - 9.0, max(bbox[3] + 28.0, 306.0)),
            ]
        _assign_container(
            items[item_index],
            container_id=f"inferred_side_actor_panel_{position + 1}",
            container_role="side_actor_panel",
            container_bbox=container_bbox,
            text_safe_bbox=text_safe_bbox,
        )
        actions.append(
            {
                "code": "inferred_side_actor_panel_safe_bbox",
                "container_id": f"inferred_side_actor_panel_{position + 1}",
                "text_safe_bbox": _round_bbox(text_safe_bbox),
            }
        )

    terminal_chain_bodies = [
        index
        for index, item in enumerate(items)
        if item.get("role") == "chain_body"
        and isinstance(item.get("bbox"), list)
        and float(item["bbox"][0]) > cfg["terminal_chain_min_x"]
        and _bbox_width([float(v) for v in item["bbox"]]) <= cfg["terminal_chain_max_width"]
    ]
    for position, item_index in enumerate(terminal_chain_bodies):
        bbox = [float(v) for v in items[item_index]["bbox"]]
        container_bbox = [
            max(0.0, bbox[0] - 24.0),
            max(0.0, bbox[1] - 18.0),
            min(float(CANVAS[0]), bbox[2] + 12.0),
            min(float(CANVAS[1]), bbox[3] + 18.0),
        ]
        text_safe_bbox = [
            max(container_bbox[0] + 8.0, min(bbox[0] - 14.0, 965.0)),
            max(container_bbox[1] + 8.0, min(bbox[1] - 10.0, 314.0)),
            min(container_bbox[2] - 8.0, bbox[2]),
            min(container_bbox[3] - 8.0, max(bbox[3] + 10.0, 454.0)),
        ]
        _assign_container(
            items[item_index],
            container_id=f"inferred_chain_terminal_note_{position + 1}",
            container_role="chain_terminal_note",
            container_bbox=container_bbox,
            text_safe_bbox=text_safe_bbox,
        )
        actions.append(
            {
                "code": "inferred_chain_terminal_note_safe_bbox",
                "container_id": f"inferred_chain_terminal_note_{position + 1}",
                "text_safe_bbox": _round_bbox(text_safe_bbox),
            }
        )

    isolated_count = 0
    for item_index, item in enumerate(items):
        if _has_semantic_container(item) or not isinstance(item.get("bbox"), list) or len(item["bbox"]) != 4:
            continue
        role = str(item.get("role") or "text")
        if role in {"index"}:
            continue
        bbox = [float(v) for v in item["bbox"]]
        pad_x = 28.0 if role in BODY_TEXT_ROLES else 18.0
        pad_y = 10.0 if role in BODY_TEXT_ROLES else 6.0
        text_safe_bbox = [
            max(0.0, bbox[0] - pad_x),
            max(0.0, bbox[1] - pad_y),
            min(float(CANVAS[0]), bbox[2] + pad_x),
            min(float(CANVAS[1]), bbox[3] + pad_y),
        ]
        container_bbox = [
            max(0.0, text_safe_bbox[0] - 4.0),
            max(0.0, text_safe_bbox[1] - 4.0),
            min(float(CANVAS[0]), text_safe_bbox[2] + 4.0),
            min(float(CANVAS[1]), text_safe_bbox[3] + 4.0),
        ]
        isolated_count += 1
        _assign_container(
            item,
            container_id=f"inferred_isolated_text_{isolated_count}",
            container_role="isolated_text_region",
            container_bbox=container_bbox,
            text_safe_bbox=text_safe_bbox,
        )
        actions.append(
            {
                "code": "inferred_isolated_text_safe_bbox",
                "container_id": f"inferred_isolated_text_{isolated_count}",
                "role": role,
                "text_safe_bbox": _round_bbox(text_safe_bbox),
                "near_miss": _isolated_near_miss(role, bbox, cfg),
            }
        )

    inferred["items"] = items
    profile_source = "explicit_override" if profile else "page012_default_unverified"
    isolated_near_miss_count = sum(
        1
        for entry in actions
        if entry.get("code") == "inferred_isolated_text_safe_bbox" and entry.get("near_miss")
    )
    return inferred, {
        "workflow": "dual-image-rebuild-ppt",
        "stage": "full_image_style_to_semantic_safe_area",
        "policy": "infer_container_safe_area_from_full_image_grouping_when_semantic_plan_has_no_containers",
        "summary": {
            "inferred_containers": len(actions),
            "isolated_count": isolated_count,
            "isolated_near_miss_count": isolated_near_miss_count,
        },
        "actions": actions,
        "profile_source": profile_source,
        "default_profile_is_unverified": profile_source == "page012_default_unverified",
        "profile_overrides": profile or {},
    }


def _bbox_from_any(value: Any) -> list[float] | None:
    if isinstance(value, list) and len(value) == 4:
        try:
            return [float(v) for v in value]
        except (TypeError, ValueError):
            return None
    return None


def _clamp_bbox_to_canvas(bbox: list[float], *, canvas: tuple[int, int] = CANVAS) -> list[float]:
    x1, y1, x2, y2 = [float(v) for v in bbox]
    return [
        max(0.0, min(float(canvas[0]), x1)),
        max(0.0, min(float(canvas[1]), y1)),
        max(0.0, min(float(canvas[0]), x2)),
        max(0.0, min(float(canvas[1]), y2)),
    ]


def _padded_union_bbox(
    boxes: list[list[float]],
    *,
    pad_x: float = 0.0,
    pad_y: float = 0.0,
    canvas: tuple[int, int] = CANVAS,
) -> list[float]:
    union = _union_bbox(boxes)
    return _clamp_bbox_to_canvas(
        [union[0] - pad_x, union[1] - pad_y, union[2] + pad_x, union[3] + pad_y],
        canvas=canvas,
    )


def _container_records_from_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collect item-level inferred containers into one record per container_id."""
    by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        container_id = str(item.get("container_id") or "").strip()
        if not container_id:
            continue
        item_bbox = _bbox_from_any(item.get("bbox"))
        container_bbox = (
            _bbox_from_any(item.get("container_bbox"))
            or _bbox_from_any(item.get("container_text_safe_bbox"))
            or _bbox_from_any(item.get("container_safe_bbox"))
            or _bbox_from_any(item.get("text_safe_bbox"))
            or item_bbox
        )
        if container_bbox is None:
            continue
        text_safe_bbox = (
            _bbox_from_any(item.get("container_text_safe_bbox"))
            or _bbox_from_any(item.get("container_safe_bbox"))
            or _bbox_from_any(item.get("text_safe_bbox"))
            or container_bbox
        )
        record = by_id.setdefault(
            container_id,
            {
                "id": container_id,
                "role": str(item.get("container_role") or ""),
                "bbox": container_bbox,
                "text_safe_bbox": text_safe_bbox,
                "item_indexes": [],
                "item_roles": [],
                "texts": [],
            },
        )
        if not record.get("role") and item.get("container_role"):
            record["role"] = str(item.get("container_role") or "")
        record["bbox"] = _union_bbox([record["bbox"], container_bbox])
        record["text_safe_bbox"] = _union_bbox([record["text_safe_bbox"], text_safe_bbox])
        record["item_indexes"].append(index)
        role = str(item.get("role") or "text")
        if role not in record["item_roles"]:
            record["item_roles"].append(role)
        text = str(item.get("text") or item.get("display_text") or item.get("source_text") or "").strip()
        if text and text not in record["texts"]:
            record["texts"].append(text)
    return sorted(by_id.values(), key=lambda record: (_bbox_cy(record["bbox"]), _bbox_cx(record["bbox"])))


def _item_records_for_framework(
    items: list[dict[str, Any]],
    *,
    role: str | None = None,
    text_contains: str | None = None,
    x_min: float | None = None,
    x_max: float | None = None,
    y_min: float | None = None,
    y_max: float | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        if role is not None and item.get("role") != role:
            continue
        text = str(item.get("text") or item.get("display_text") or item.get("source_text") or "")
        if text_contains is not None and text_contains not in text:
            continue
        bbox = _bbox_from_any(item.get("bbox"))
        if bbox is None:
            continue
        cx = _bbox_cx(bbox)
        cy = _bbox_cy(bbox)
        if x_min is not None and cx < x_min:
            continue
        if x_max is not None and cx > x_max:
            continue
        if y_min is not None and cy < y_min:
            continue
        if y_max is not None and cy > y_max:
            continue
        records.append({"index": index, "bbox": bbox, "role": item.get("role"), "text": text})
    return records


def _container_records_for_framework(
    container_records: list[dict[str, Any]],
    *,
    container_roles: set[str] | None = None,
    item_roles: set[str] | None = None,
    text_contains: str | None = None,
    x_min: float | None = None,
    x_max: float | None = None,
    y_min: float | None = None,
    y_max: float | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for record in container_records:
        bbox = _bbox_from_any(record.get("bbox"))
        if bbox is None:
            continue
        if container_roles is not None and str(record.get("role") or "") not in container_roles:
            continue
        if item_roles is not None and not (set(record.get("item_roles", [])) & item_roles):
            continue
        if text_contains is not None and not any(text_contains in str(text) for text in record.get("texts", [])):
            continue
        cx = _bbox_cx(bbox)
        cy = _bbox_cy(bbox)
        if x_min is not None and cx < x_min:
            continue
        if x_max is not None and cx > x_max:
            continue
        if y_min is not None and cy < y_min:
            continue
        if y_max is not None and cy > y_max:
            continue
        records.append(record)
    return records


def _framework_record(
    *,
    framework_id: str,
    role: str,
    label: str,
    container_records: list[dict[str, Any]],
    item_records: list[dict[str, Any]] | None = None,
    order: int,
    rationale: str,
    pad_x: float = 16.0,
    pad_y: float = 12.0,
) -> dict[str, Any] | None:
    item_records = item_records or []
    unique_container_records: list[dict[str, Any]] = []
    seen_container_ids: set[str] = set()
    for record in container_records:
        container_id = str(record.get("id") or "")
        if not container_id or container_id in seen_container_ids:
            continue
        seen_container_ids.add(container_id)
        unique_container_records.append(record)
    container_records = unique_container_records
    boxes = [record["bbox"] for record in container_records if _bbox_from_any(record.get("bbox"))]
    boxes.extend(record["bbox"] for record in item_records)
    if not boxes:
        return None
    child_ids = [str(record["id"]) for record in container_records]
    item_indexes = sorted({int(index) for record in container_records for index in record.get("item_indexes", [])})
    item_indexes.extend(int(record["index"]) for record in item_records if int(record["index"]) not in item_indexes)
    child_roles = sorted({str(record.get("role") or "") for record in container_records if record.get("role")})
    text_roles = sorted(
        {
            str(role)
            for record in container_records
            for role in record.get("item_roles", [])
            if str(role).strip()
        }
        | {str(record.get("role")) for record in item_records if str(record.get("role") or "").strip()}
    )
    texts: list[str] = []
    for record in container_records:
        for text in record.get("texts", []):
            if text not in texts:
                texts.append(text)
    for record in item_records:
        text = str(record.get("text") or "").strip()
        if text and text not in texts:
            texts.append(text)
    return {
        "id": framework_id,
        "role": role,
        "label": label,
        "order": order,
        "bbox": _round_bbox(_padded_union_bbox(boxes, pad_x=pad_x, pad_y=pad_y)),
        "child_container_ids": child_ids,
        "child_container_roles": child_roles,
        "item_indexes": item_indexes,
        "text_roles": text_roles,
        "key_text": texts[:12],
        "rationale": rationale,
    }


def _expected_framework_roles(container_records: list[dict[str, Any]], items: list[dict[str, Any]]) -> set[str]:
    roles = {str(record.get("role") or "") for record in container_records}
    expected: set[str] = set()
    if "stage_card" in roles:
        expected.add("lifecycle_outer_frame")
    if roles & {"process_chain_card", "chain_terminal_note"}:
        expected.add("processing_chain_frame")
    if "side_actor_panel" in roles:
        expected.add("actor_endpoint_frame")
    if "trust_card" in roles:
        expected.add("right_trust_frame")
    if "product_panel" in roles:
        expected.add("service_product_frame")
    if "service_card" in roles:
        expected.add("third_party_service_frame")
    left_candidates = _item_records_for_framework(items, x_max=360.0, y_min=300.0)
    if left_candidates:
        expected.add("left_role_swimlane_frame")
    return expected


def _right_mid(bbox: list[float]) -> list[float]:
    return [round(float(bbox[2]), 3), round(_bbox_cy(bbox), 3)]


def _left_mid(bbox: list[float]) -> list[float]:
    return [round(float(bbox[0]), 3), round(_bbox_cy(bbox), 3)]


def _top_mid(bbox: list[float]) -> list[float]:
    return [round(_bbox_cx(bbox), 3), round(float(bbox[1]), 3)]


def _bottom_mid(bbox: list[float]) -> list[float]:
    return [round(_bbox_cx(bbox), 3), round(float(bbox[3]), 3)]


def _container_text_contains(record: dict[str, Any], needle: str) -> bool:
    return any(needle in str(text) for text in record.get("texts", []))


def _edge_record(
    *,
    edge_id: str,
    role: str,
    label: str,
    from_id: str,
    to_id: str,
    start: list[float],
    end: list[float],
    direction: str,
    rationale: str,
    from_type: str = "container",
    to_type: str = "container",
    visual: str = "arrow",
) -> dict[str, Any]:
    return {
        "id": edge_id,
        "role": role,
        "label": label,
        "from_id": from_id,
        "from_type": from_type,
        "to_id": to_id,
        "to_type": to_type,
        "start": start,
        "end": end,
        "direction": direction,
        "visual": visual,
        "rationale": rationale,
    }


def _infer_relation_edges(
    frameworks: list[dict[str, Any]],
    container_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Infer visual relation arrows from semantic container topology."""
    by_role: dict[str, list[dict[str, Any]]] = {}
    for record in container_records:
        by_role.setdefault(str(record.get("role") or ""), []).append(record)
    frameworks_by_id = {str(framework["id"]): framework for framework in frameworks}
    edges: list[dict[str, Any]] = []

    stage_cards = sorted(by_role.get("stage_card", []), key=lambda record: _bbox_cx(record["bbox"]))
    process_cards = sorted(by_role.get("process_chain_card", []), key=lambda record: _bbox_cx(record["bbox"]))
    terminal_notes = sorted(by_role.get("chain_terminal_note", []), key=lambda record: _bbox_cx(record["bbox"]))
    product_panels = sorted(by_role.get("product_panel", []), key=lambda record: _bbox_cx(record["bbox"]))
    service_cards = sorted(by_role.get("service_card", []), key=lambda record: _bbox_cx(record["bbox"]))
    side_actor_panels = sorted(by_role.get("side_actor_panel", []), key=lambda record: _bbox_cx(record["bbox"]))
    left_actor = next((record for record in side_actor_panels if _bbox_cx(record["bbox"]) < CANVAS[0] / 2), None)
    right_actor = next((record for record in side_actor_panels if _bbox_cx(record["bbox"]) >= CANVAS[0] / 2), None)

    if left_actor and stage_cards:
        edges.append(
            _edge_record(
                edge_id="edge_source_to_lifecycle",
                role="source_to_lifecycle",
                label="数据来源方进入五阶段生命周期",
                from_id=left_actor["id"],
                to_id=stage_cards[0]["id"],
                start=_right_mid(left_actor["bbox"]),
                end=_left_mid(stage_cards[0]["bbox"]),
                direction="right",
                rationale="left endpoint arrow into first lifecycle stage",
            )
        )
    for position, (source, target) in enumerate(zip(stage_cards, stage_cards[1:]), start=1):
        edges.append(
            _edge_record(
                edge_id=f"edge_lifecycle_stage_{position}_to_{position + 1}",
                role="lifecycle_stage_flow",
                label="五阶段生命周期横向流转",
                from_id=source["id"],
                to_id=target["id"],
                start=_right_mid(source["bbox"]),
                end=_left_mid(target["bbox"]),
                direction="right",
                rationale="adjacent stage cards are connected by right-facing arrows in the full image",
            )
        )
    if right_actor and stage_cards:
        edges.append(
            _edge_record(
                edge_id="edge_lifecycle_to_user",
                role="lifecycle_to_user",
                label="五阶段服务输出给用户方",
                from_id=stage_cards[-1]["id"],
                to_id=right_actor["id"],
                start=_right_mid(stage_cards[-1]["bbox"]),
                end=_left_mid(right_actor["bbox"]),
                direction="right",
                rationale="last lifecycle stage points to the user endpoint",
            )
        )

    lifecycle_frame = frameworks_by_id.get("lifecycle_outer_frame")
    processing_frame = frameworks_by_id.get("processing_chain_frame")
    if lifecycle_frame and processing_frame:
        edges.append(
            _edge_record(
                edge_id="edge_lifecycle_to_processing",
                role="lifecycle_to_processing",
                label="五阶段数据下沉到技术支撑与加工链条",
                from_id=lifecycle_frame["id"],
                from_type="framework",
                to_id=processing_frame["id"],
                to_type="framework",
                start=_bottom_mid(lifecycle_frame["bbox"]),
                end=_top_mid(processing_frame["bbox"]),
                direction="down",
                rationale="the upper lifecycle row semantically feeds the middle processing chain",
            )
        )

    chain_sequence = [*process_cards, *terminal_notes]
    for position, (source, target) in enumerate(zip(chain_sequence, chain_sequence[1:]), start=1):
        edges.append(
            _edge_record(
                edge_id=f"edge_processing_chain_{position}_to_{position + 1}",
                role="processing_chain_flow",
                label="加工链条横向流转",
                from_id=source["id"],
                to_id=target["id"],
                start=_right_mid(source["bbox"]),
                end=_left_mid(target["bbox"]),
                direction="right",
                rationale="adjacent processing cards are connected by right-facing arrows in the full image",
            )
        )

    output_card = next((record for record in process_cards if _container_text_contains(record, "成果输出")), None)
    product_frame = frameworks_by_id.get("service_product_frame")
    if output_card and product_frame:
        edges.append(
            _edge_record(
                edge_id="edge_processing_to_product_outputs",
                role="processing_to_product_outputs",
                label="加工成果沉淀为服务产品",
                from_id=output_card["id"],
                to_id=product_frame["id"],
                to_type="framework",
                start=_bottom_mid(output_card["bbox"]),
                end=_top_mid(product_frame["bbox"]),
                direction="down",
                rationale="processing output becomes the two product deliverables",
            )
        )
    elif process_cards and product_frame:
        edges.append(
            _edge_record(
                edge_id="edge_processing_to_product_outputs",
                role="processing_to_product_outputs",
                label="加工链条沉淀为服务产品",
                from_id=process_cards[-1]["id"],
                to_id=product_frame["id"],
                to_type="framework",
                start=_bottom_mid(process_cards[-1]["bbox"]),
                end=_top_mid(product_frame["bbox"]),
                direction="down",
                rationale="processing chain feeds product deliverables",
            )
        )

    if service_cards and product_panels:
        product_targets = product_panels if len(product_panels) > 1 else [product_panels[0]]
        for position, source in enumerate(service_cards):
            target = product_targets[min(position, len(product_targets) - 1)]
            edges.append(
                _edge_record(
                    edge_id=f"edge_third_party_service_{position + 1}_supports_output",
                    role="third_party_supports_outputs",
                    label="第三方服务支撑证据/鉴定输出",
                    from_id=source["id"],
                    to_id=target["id"],
                    start=_top_mid(source["bbox"]),
                    end=_bottom_mid(target["bbox"]),
                    direction="up",
                    rationale="bottom service row sends support arrows upward to product outputs in the full image",
                )
            )

    expected_roles: set[str] = set()
    if left_actor and stage_cards:
        expected_roles.add("source_to_lifecycle")
    if len(stage_cards) >= 2:
        expected_roles.add("lifecycle_stage_flow")
    if right_actor and stage_cards:
        expected_roles.add("lifecycle_to_user")
    if lifecycle_frame and processing_frame:
        expected_roles.add("lifecycle_to_processing")
    if len(chain_sequence) >= 2:
        expected_roles.add("processing_chain_flow")
    if process_cards and product_frame:
        expected_roles.add("processing_to_product_outputs")
    if service_cards and product_panels:
        expected_roles.add("third_party_supports_outputs")

    present_roles = {edge["role"] for edge in edges}
    missing_roles = sorted(expected_roles - present_roles)
    coverage = {
        "valid": not missing_roles,
        "expected_roles": sorted(expected_roles),
        "present_roles": sorted(present_roles),
        "missing_roles": missing_roles,
        "edge_count": len(edges),
    }
    return edges, coverage


def infer_visual_frameworks_from_containers(
    layout: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Aggregate semantic containers into parent visual frameworks.

    Container inference answers "where can this text safely sit"; this layer
    answers "which larger composition frame does that container belong to" so a
    downstream full-object rebuild can inherit the ChatGPT page topology instead
    of seeing only isolated cards.
    """
    framed = copy.deepcopy(layout)
    items = [item for item in framed.get("items", []) if isinstance(item, dict)]
    container_records = _container_records_from_items(items)
    by_role: dict[str, list[dict[str, Any]]] = {}
    for record in container_records:
        by_role.setdefault(str(record.get("role") or ""), []).append(record)

    frameworks: list[dict[str, Any]] = []

    def add(record: dict[str, Any] | None) -> None:
        if record is not None:
            frameworks.append(record)

    add(
        _framework_record(
            framework_id="lifecycle_outer_frame",
            role="lifecycle_outer_frame",
            label="知识产权全生命周期五阶段",
            container_records=[
                *by_role.get("stage_card", []),
                *_container_records_for_framework(container_records, item_roles={"title"}, y_max=90.0),
            ],
            item_records=_item_records_for_framework(items, role="title", y_max=90.0),
            order=10,
            rationale="stage_card row plus top lifecycle title",
            pad_x=18.0,
            pad_y=20.0,
        )
    )
    add(
        _framework_record(
            framework_id="processing_chain_frame",
            role="processing_chain_frame",
            label="技术支撑方与加工链条",
            container_records=[
                *by_role.get("process_chain_card", []),
                *by_role.get("chain_terminal_note", []),
                *_container_records_for_framework(container_records, item_roles={"section_title"}, y_min=230.0, y_max=325.0, x_max=980.0),
                *_container_records_for_framework(container_records, item_roles={"left_stage_label"}, y_min=300.0, y_max=430.0, x_max=190.0),
            ],
            item_records=[
                *_item_records_for_framework(items, role="section_title", y_min=230.0, y_max=325.0, x_max=980.0),
                *_item_records_for_framework(items, role="left_stage_label", y_min=300.0, y_max=430.0, x_max=190.0),
            ],
            order=20,
            rationale="process-chain cards plus technical-support section titles",
            pad_x=18.0,
            pad_y=16.0,
        )
    )
    add(
        _framework_record(
            framework_id="left_role_swimlane_frame",
            role="left_role_swimlane_frame",
            label="左侧角色与阶段泳道",
            container_records=[
                record
                for record in container_records
                if _bbox_cx(record["bbox"]) < 390.0
                and record.get("role") in {"side_actor_panel", "isolated_text_region", "space_operator_panel"}
            ],
            item_records=[
                *_item_records_for_framework(items, role="left_stage_label", x_max=360.0),
                *_item_records_for_framework(items, role="actor_summary", x_max=360.0, y_min=520.0),
            ],
            order=30,
            rationale="left-side labels and operator/source role annotations",
            pad_x=14.0,
            pad_y=12.0,
        )
    )
    add(
        _framework_record(
            framework_id="right_trust_frame",
            role="right_trust_frame",
            label="可信机制贯穿全程",
            container_records=[
                *by_role.get("trust_card", []),
                *_container_records_for_framework(container_records, item_roles={"section_title"}, x_min=1060.0, y_min=320.0),
            ],
            item_records=_item_records_for_framework(items, role="section_title", x_min=1060.0, y_min=320.0),
            order=40,
            rationale="right trust cards plus trust-column heading",
            pad_x=12.0,
            pad_y=18.0,
        )
    )
    add(
        _framework_record(
            framework_id="service_product_frame",
            role="service_product_frame",
            label="服务产品输出",
            container_records=[
                *by_role.get("product_panel", []),
                *_container_records_for_framework(container_records, item_roles={"left_stage_label"}, y_min=460.0, y_max=560.0, x_max=220.0),
            ],
            item_records=_item_records_for_framework(items, role="left_stage_label", y_min=460.0, y_max=560.0, x_max=220.0),
            order=50,
            rationale="product output panels plus service-product lane label",
            pad_x=18.0,
            pad_y=14.0,
        )
    )
    add(
        _framework_record(
            framework_id="third_party_service_frame",
            role="third_party_service_frame",
            label="第三方服务方",
            container_records=[
                *by_role.get("service_card", []),
                *_container_records_for_framework(container_records, item_roles={"section_title"}, y_min=560.0, x_min=360.0, x_max=700.0),
            ],
            item_records=_item_records_for_framework(items, role="section_title", y_min=560.0, x_min=360.0, x_max=700.0),
            order=60,
            rationale="bottom third-party service cards plus row heading",
            pad_x=18.0,
            pad_y=14.0,
        )
    )
    add(
        _framework_record(
            framework_id="actor_endpoint_frame",
            role="actor_endpoint_frame",
            label="数据来源方与用户方端点",
            container_records=[
                *by_role.get("side_actor_panel", []),
                *_container_records_for_framework(container_records, item_roles={"actor_title"}, y_max=210.0, x_max=190.0),
                *_container_records_for_framework(container_records, item_roles={"actor_title"}, y_max=210.0, x_min=1080.0),
            ],
            item_records=[
                *_item_records_for_framework(items, role="actor_title", y_max=210.0, x_max=190.0),
                *_item_records_for_framework(items, role="actor_title", y_max=210.0, x_min=1080.0),
            ],
            order=70,
            rationale="left/right endpoint actor panels",
            pad_x=12.0,
            pad_y=14.0,
        )
    )

    frameworks.sort(key=lambda record: int(record["order"]))
    framework_by_role = {framework["role"]: framework for framework in frameworks}
    expected_roles = _expected_framework_roles(container_records, items)
    missing_roles = sorted(role for role in expected_roles if role not in framework_by_role)
    container_parent: dict[str, str] = {}
    container_memberships: dict[str, list[str]] = {}
    for framework in frameworks:
        for container_id in framework.get("child_container_ids", []):
            container_memberships.setdefault(container_id, []).append(framework["id"])
            container_parent.setdefault(container_id, framework["id"])
    item_parent: dict[int, str] = {}
    item_memberships: dict[int, list[str]] = {}
    for framework in frameworks:
        for item_index in framework.get("item_indexes", []):
            item_memberships.setdefault(int(item_index), []).append(framework["id"])
            item_parent.setdefault(int(item_index), framework["id"])

    for index, item in enumerate(items):
        container_id = str(item.get("container_id") or "")
        memberships: list[str] = []
        for framework_id in [*container_memberships.get(container_id, []), *item_memberships.get(index, [])]:
            if framework_id and framework_id not in memberships:
                memberships.append(framework_id)
        parent_id = container_parent.get(container_id) or item_parent.get(index)
        if parent_id:
            item["parent_framework_id"] = parent_id
        if memberships:
            item["framework_ids"] = memberships

    total_containers = len(container_records)
    covered_containers = len(container_memberships)
    coverage = {
        "valid": not missing_roles,
        "expected_roles": sorted(expected_roles),
        "present_roles": sorted(framework_by_role),
        "missing_roles": missing_roles,
        "total_containers": total_containers,
        "covered_containers": covered_containers,
        "covered_container_ratio": round(covered_containers / total_containers, 3) if total_containers else 1.0,
    }
    relation_edges, relation_edge_coverage = _infer_relation_edges(frameworks, container_records)
    report = {
        "workflow": "dual-image-rebuild-ppt",
        "stage": "semantic_container_to_visual_frameworks",
        "policy": "aggregate_semantic_containers_into_parent_composition_frames",
        "canvas": {"width": CANVAS[0], "height": CANVAS[1]},
        "summary": {
            "framework_count": len(frameworks),
            "container_count": total_containers,
            "coverage_valid": coverage["valid"],
        },
        "framework_coverage": coverage,
        "relation_edge_coverage": relation_edge_coverage,
        "frameworks": frameworks,
        "relation_edges": relation_edges,
        "container_records": [
            {
                "id": record["id"],
                "role": record.get("role"),
                "bbox": _round_bbox(record["bbox"]),
                "text_safe_bbox": _round_bbox(record["text_safe_bbox"]),
                "item_indexes": record["item_indexes"],
                "item_roles": record["item_roles"],
                "texts": record["texts"],
                "parent_framework_id": container_parent.get(record["id"]),
                "framework_ids": container_memberships.get(record["id"], []),
            }
            for record in container_records
        ],
    }
    composition_contract = {
        "version": "1.0",
        "source": {
            "frameworks": "analysis/dual_image_rebuild/P01_frameworks.json",
            "safe_area_reference": "analysis/dual_image_rebuild/P01_safe_area_inference.json",
            "text_layout_reference": "analysis/dual_image_rebuild/P01_text_layout_1280x720.json",
            "text_style_reference": "analysis/dual_image_rebuild/P01_text_style_profile.json",
        },
        "principle": (
            "Use the full image as semantic and composition input. Parent visual "
            "frameworks are inferred from semantic containers; OCR boxes remain "
            "locator evidence, not final layout geometry."
        ),
        "canvas": {
            "width": CANVAS[0],
            "height": CANVAS[1],
            "body_safe_area": {"x": 0, "y": 0, "w": CANVAS[0], "h": CANVAS[1]},
        },
        "framework_coverage": coverage,
        "relation_edge_coverage": relation_edge_coverage,
        "layout_zones": [
            {
                "id": framework["id"],
                "role": framework["role"],
                "safe_bbox": framework["bbox"],
                "inherits": framework["key_text"],
                "child_container_ids": framework["child_container_ids"],
            }
            for framework in frameworks
        ],
        "relation_edges": relation_edges,
        "container_topology": {
            "preserve": [
                framework["label"]
                for framework in frameworks
                if framework["role"] in REQUIRED_FRAMEWORK_ROLES
            ]
            + [
                "full-image relationship arrows and directional flow between frames",
            ],
            "may_adjust": [
                "card width and height inside each parent frame",
                "text wrapping inside semantic safe areas",
                "local nudges within the owning framework",
            ],
            "must_not": [
                "flatten parent frameworks into unrelated local cards",
                "use OCR ink boxes as final geometry when larger safe areas exist",
                "shrink text before using legal safe-area width and height",
            ],
        },
        "reading_order": [framework["label"] for framework in frameworks],
        "text_safe_policy": {
            "priority": [
                "identify text role and owning semantic container",
                "use the owning container safe area",
                "use parent framework space before reducing font size",
                "wrap or nudge inside the framework",
                "request semantic revision only when readable fit still fails",
            ]
        },
    }
    framed["items"] = items
    framed["visual_frameworks"] = frameworks
    framed["relation_edges"] = relation_edges
    return framed, report, composition_contract


def _item_has_own_safe_bbox(item: dict[str, Any]) -> bool:
    """True when the item carries a safe area of its own, distinct from a container
    it merely shares with other text items (e.g. two summary lines both pointing
    at the same card's container_text_safe_bbox)."""
    return bool(item.get("container_safe_bbox") or item.get("text_safe_bbox"))


def _count_source_text_restoration_candidates(items: list[Any]) -> dict[str, int]:
    """Count, per container_id, how many sibling items resolve their fit-check box
    to that container's *shared* safe area (rather than a per-item safe bbox) and
    also have a display_text shortened from source_text -- i.e. how many items
    will independently try to restore their full sentence into the same box.

    This exists because apply_typesetting_policy's "restore source_text when it
    fits" check runs before build_layout_plan has decided each item's actual
    per-item slot inside a shared container. Checking a candidate sentence
    against the *whole* container's safe height overstates how much room that
    one item will really get once siblings are stacked into the same box, so
    two sentences can each "fit" alone and still collide once both are
    restored. Dividing the shared height by the number of competing siblings is
    a conservative stand-in for the real per-item allocation.
    """
    counts: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        container_id = str(item.get("container_id") or "").strip()
        if not container_id or _item_has_own_safe_bbox(item):
            continue
        explicit_source_text = str(item.get("source_text") or item.get("source_meaning") or "").strip()
        display_text = str(item.get("display_text") or item.get("text") or explicit_source_text).strip()
        if explicit_source_text and explicit_source_text != display_text:
            counts[container_id] = counts.get(container_id, 0) + 1
    return counts


def _find_duplicate_source_text_indices(items: list[Any]) -> set[int]:
    """Return indices of items that share the same container_id and the same
    exact source_text as at least one sibling item.

    Restoring source_text over display_text is meant to recover meaning that
    was trimmed for space. When two sibling items were authored with
    display_text split from one shared source sentence (e.g. one card's title
    line and its body line both trace back to the same original clause), each
    one independently "fitting" its own restoration is not evidence they
    should both be restored -- doing so duplicates the identical sentence into
    two boxes instead of fixing a truncation. This is a content-duplication
    defect distinct from the geometry-collision one that
    _count_source_text_restoration_candidates guards against, so it is
    checked and skipped unconditionally, without a per-item fit check.
    """
    groups: dict[tuple[str, str], list[int]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        container_id = str(item.get("container_id") or "").strip()
        if not container_id:
            continue
        explicit_source_text = str(item.get("source_text") or item.get("source_meaning") or "").strip()
        if not explicit_source_text:
            continue
        key = (container_id, explicit_source_text)
        groups.setdefault(key, []).append(index)
    duplicate_indices: set[int] = set()
    for indices in groups.values():
        if len(indices) > 1:
            duplicate_indices.update(indices)
    return duplicate_indices


def apply_typesetting_policy(layout: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Prefer readable safe-area fit over full-image hard line-break imitation."""
    optimized = copy.deepcopy(layout)
    actions: list[dict[str, Any]] = []
    restoration_candidates_by_container = _count_source_text_restoration_candidates(
        optimized.get("items", [])
    )
    duplicate_source_text_indices = _find_duplicate_source_text_indices(optimized.get("items", []))
    summary = {
        "auto_wrapped": 0,
        "hard_linebreaks_preserved": 0,
        "hard_linebreaks_normalized": 0,
        "explicit_linebreaks_preserved": 0,
        "semantic_clause_breaks_inserted": 0,
        "source_text_restored_when_fit": 0,
        "source_text_restoration_skipped_for_shared_container": 0,
        "source_text_restoration_skipped_for_duplicate_sibling_text": 0,
        "font_floor_applied": 0,
        "semantic_text_preserved": 0,
        "align_adjusted": 0,
        "v_align_adjusted": 0,
    }
    for index, item in enumerate(optimized.get("items", [])):
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "text")
        policy = _role_policy(role)
        explicit_source_text = str(item.get("source_text") or item.get("source_meaning") or "").strip()
        source_text = explicit_source_text or str(item.get("text") or "").strip()
        display_text = str(item.get("display_text") or item.get("text") or source_text).strip()
        linebreaks_locked = _linebreaks_are_semantically_locked(item)
        if source_text and not item.get("source_text"):
            item["source_text"] = source_text
        container_id = str(item.get("container_id") or "").strip()
        sibling_restoration_count = (
            restoration_candidates_by_container.get(container_id, 1)
            if container_id and not _item_has_own_safe_bbox(item)
            else 1
        )
        shared_container_box = (
            item.get("container_safe_bbox") or item.get("container_text_safe_bbox") or item.get("text_safe_bbox")
        )
        own_bbox = item.get("bbox")
        if sibling_restoration_count > 1 and isinstance(own_bbox, list) and len(own_bbox) == 4:
            # Multiple items are competing to restore their full sentence into the
            # *same* shared container box (see _count_source_text_restoration_
            # candidates). Checking each one against the whole container
            # overstates the room any single line will actually get once
            # build_layout_plan stacks them, so fall back to this item's own
            # authored bbox -- the best per-item estimate available at this
            # stage -- for both width and height, instead of the shared box.
            text_box = own_bbox
        else:
            text_box = shared_container_box or own_bbox
        candidate_source_text = (
            explicit_source_text if linebreaks_locked else _normalize_full_image_linebreaks(explicit_source_text)
        )
        if index in duplicate_source_text_indices:
            # This item's source_text is identical to a sibling's in the same
            # container. Restoring both would duplicate one sentence into two
            # boxes, which no per-item fit check can catch (each copy can
            # individually "fit" fine) -- so restoration is skipped outright
            # for every item in the duplicate group, keeping their originally
            # authored, distinct display_text.
            if candidate_source_text and candidate_source_text != display_text:
                summary["source_text_restoration_skipped_for_duplicate_sibling_text"] += 1
                actions.append(
                    {
                        "index": index,
                        "code": "source_text_restoration_skipped_for_duplicate_sibling_text",
                        "role": role,
                        "container_id": container_id,
                    }
                )
        elif (
            candidate_source_text
            and candidate_source_text != display_text
            and isinstance(text_box, list)
            and len(text_box) == 4
        ):
            preferred_size = float(item.get("font_size") or policy.get("min_font_size", DEFAULT_TYPESETTING_POLICY["min_font_size"]))
            candidate_wrap = role in BODY_TEXT_ROLES and not linebreaks_locked
            candidate_min_size = float(policy.get("min_font_size", DEFAULT_TYPESETTING_POLICY["min_font_size"]))
            fitted_candidate_size = _fit_font_size_to_box(
                candidate_source_text,
                _bbox_width([float(v) for v in text_box]),
                _bbox_height([float(v) for v in text_box]),
                preferred_size,
                candidate_min_size,
                word_wrap=candidate_wrap,
            )
            candidate_height = _estimated_text_height(
                candidate_source_text,
                _bbox_width([float(v) for v in text_box]),
                fitted_candidate_size,
                word_wrap=candidate_wrap,
            )
            if candidate_height <= _bbox_height([float(v) for v in text_box]) + 1.0:
                # The fit check above is only meaningful if rendering actually
                # uses the font size it was validated at. Without persisting
                # fitted_candidate_size, build_overlay_boxes would re-fit the
                # restored (longer) text against the item's original preferred
                # font_size instead, silently producing a different, larger
                # rendered height than what this check just approved -- which is
                # exactly how two adjacent items could each "pass" this check
                # and still expand into each other at render time.
                display_text = candidate_source_text
                item["font_size"] = round(fitted_candidate_size, 2)
                summary["source_text_restored_when_fit"] += 1
                actions.append({"index": index, "code": "source_text_restored_when_fit", "role": role})
            elif sibling_restoration_count > 1:
                summary["source_text_restoration_skipped_for_shared_container"] += 1
                actions.append(
                    {
                        "index": index,
                        "code": "source_text_restoration_skipped_for_shared_container",
                        "role": role,
                        "container_id": container_id,
                        "sibling_restoration_count": sibling_restoration_count,
                    }
                )

        if "\n" in display_text:
            if linebreaks_locked:
                item["word_wrap"] = False
                summary["hard_linebreaks_preserved"] += 1
                summary["explicit_linebreaks_preserved"] += 1
                actions.append({"index": index, "code": "explicit_linebreaks_preserved", "role": role})
            elif role in BODY_TEXT_ROLES:
                normalized_display_text = _normalize_full_image_linebreaks(display_text)
                if normalized_display_text != display_text:
                    display_text = normalized_display_text
                    summary["hard_linebreaks_normalized"] += 1
                    actions.append({"index": index, "code": "hard_linebreaks_normalized", "role": role})
                if item.get("word_wrap") is not True:
                    item["word_wrap"] = True
                    summary["auto_wrapped"] += 1
                    actions.append({"index": index, "code": "auto_wrap", "role": role})
        elif role in BODY_TEXT_ROLES:
            if item.get("word_wrap") is not True:
                item["word_wrap"] = True
                summary["auto_wrapped"] += 1
                actions.append({"index": index, "code": "auto_wrap", "role": role})

        forced_align = policy.get("align")
        if forced_align and item.get("align") != forced_align:
            item["align"] = forced_align
            summary["align_adjusted"] += 1
            actions.append({"index": index, "code": "align_adjusted", "role": role, "align": forced_align})
        forced_v_align = policy.get("v_align")
        if forced_v_align and item.get("v_align") != forced_v_align:
            item["v_align"] = forced_v_align
            summary["v_align_adjusted"] += 1
            actions.append({"index": index, "code": "v_align_adjusted", "role": role, "v_align": forced_v_align})

        min_font_size = float(policy.get("min_font_size", DEFAULT_TYPESETTING_POLICY["min_font_size"]))
        has_explicit_size = item.get("font_size") is not None
        current_size = float(item.get("font_size") or min_font_size)
        if not has_explicit_size and current_size < min_font_size:
            item["font_size"] = min_font_size
            summary["font_floor_applied"] += 1
            actions.append(
                {
                    "index": index,
                    "code": "font_floor_applied",
                    "role": role,
                    "from": current_size,
                    "to": min_font_size,
                }
            )

        item["text"] = display_text
        item["display_text"] = display_text
        summary["semantic_text_preserved"] += 1

    return optimized, {
        "workflow": "dual-image-rebuild-ppt",
        "stage": "pre_render_typesetting_policy",
        "policy": "safe_area_readability_over_full_image_hard_linebreaks",
        "summary": summary,
        "actions": actions,
    }


def _round_bbox(bbox: list[float]) -> list[float]:
    return [round(float(value), 3) for value in bbox]


def _inset_bbox(
    bbox: list[float],
    *,
    left: float = 0.0,
    top: float = 0.0,
    right: float = 0.0,
    bottom: float = 0.0,
) -> list[float]:
    x1, y1, x2, y2 = [float(v) for v in bbox]
    return [min(x2 - 1.0, x1 + left), min(y2 - 1.0, y1 + top), max(x1 + 1.0, x2 - right), max(y1 + 1.0, y2 - bottom)]


def _bbox_center(bbox: list[float]) -> tuple[float, float]:
    return ((float(bbox[0]) + float(bbox[2])) / 2.0, (float(bbox[1]) + float(bbox[3])) / 2.0)


def _zone(name: str, bbox: list[float], reason: str) -> dict[str, Any]:
    return {"name": name, "bbox": _round_bbox(bbox), "reason": reason}


def _bbox_intersection_area(a: list[float], b: list[float]) -> float:
    x1 = max(float(a[0]), float(b[0]))
    y1 = max(float(a[1]), float(b[1]))
    x2 = min(float(a[2]), float(b[2]))
    y2 = min(float(a[3]), float(b[3]))
    if x2 <= x1 or y2 <= y1:
        return 0.0
    return (x2 - x1) * (y2 - y1)


def _bbox_inside(inner: list[float], outer: list[float], *, tolerance: float = 1.0) -> bool:
    return (
        float(inner[0]) >= float(outer[0]) - tolerance
        and float(inner[1]) >= float(outer[1]) - tolerance
        and float(inner[2]) <= float(outer[2]) + tolerance
        and float(inner[3]) <= float(outer[3]) + tolerance
    )


def _bbox_overflow_amount(inner: list[float], outer: list[float]) -> float:
    """Return the largest single-side distance `inner` protrudes past `outer` (0 when fully inside)."""
    return max(
        0.0,
        float(outer[0]) - float(inner[0]),
        float(outer[1]) - float(inner[1]),
        float(inner[2]) - float(outer[2]),
        float(inner[3]) - float(outer[3]),
    )


def _semantic_compression_level(role: str) -> str:
    if role in {"actor_title", "panel_title", "profit_title", "center_label", "stage_label", "relationship", "index"}:
        return "preserve"
    if role in {"actor_summary", "service_item"}:
        return "phrase_label"
    if role == "profit_body":
        return "compact_body"
    return "note_backed_summary"


def _profit_card_regions(card_bbox: list[float]) -> dict[str, list[float]]:
    x1, y1, x2, y2 = [float(v) for v in card_bbox]
    card_w = _bbox_width(card_bbox)
    card_h = _bbox_height(card_bbox)
    marker_side = min(31.0, max(27.0, min(card_w, card_h) * 0.17))
    marker_cx = x1 + min(max(card_w * 0.12, 22.0), 28.0)
    marker_cy = y1 + min(max(card_h * 0.12, 23.0), 29.0)
    title_y1 = y1 + max(66.0, card_h * 0.33)
    title_h = max(24.0, min(32.0, card_h * 0.15))
    body_y1 = title_y1 + title_h + max(18.0, card_h * 0.08)
    return {
        "index_marker": [
            marker_cx - marker_side / 2.0,
            marker_cy - marker_side / 2.0,
            marker_cx + marker_side / 2.0,
            marker_cy + marker_side / 2.0,
        ],
        "icon_zone": [x1 + card_w * 0.24, y1 + 10.0, x2 - card_w * 0.18, y1 + max(58.0, card_h * 0.3)],
        "title": [x1 + 10.0, title_y1, x2 - 10.0, min(y2 - 48.0, title_y1 + title_h)],
        "body": [x1 + 10.0, body_y1, x2 - 10.0, y2 - max(16.0, card_h * 0.08)],
    }


def _container_layout_context(
    group: list[dict[str, Any]],
    *,
    container_role: str,
    fallback_safe_bbox: Any,
) -> dict[str, Any]:
    has_container_geometry = bool(
        container_role
        or group[0].get("container_id")
        or group[0].get("container_bbox")
        or group[0].get("container_text_safe_bbox")
        or group[0].get("container_safe_bbox")
        or group[0].get("text_safe_bbox")
    )
    container_bbox_raw = group[0].get("container_bbox") or fallback_safe_bbox
    if isinstance(container_bbox_raw, list) and len(container_bbox_raw) == 4:
        container_bbox = [float(v) for v in container_bbox_raw]
    elif isinstance(fallback_safe_bbox, list) and len(fallback_safe_bbox) == 4:
        container_bbox = [float(v) for v in fallback_safe_bbox]
    else:
        item_boxes = [[float(v) for v in item["bbox"]] for item in group]
        container_bbox = [
            min(box[0] for box in item_boxes),
            min(box[1] for box in item_boxes),
            max(box[2] for box in item_boxes),
            max(box[3] for box in item_boxes),
        ]

    has_explicit_safe = bool(group[0].get("container_has_text_safe_bbox"))
    explicit_safe = group[0].get("container_text_safe_bbox")
    if has_explicit_safe and isinstance(explicit_safe, list) and len(explicit_safe) == 4:
        safe_bbox = [float(v) for v in explicit_safe]
        rationale = "semantic_plan_text_safe_bbox"
    elif not has_container_geometry:
        safe_bbox = None
        rationale = "uncontained_item_no_safe_bbox"
    else:
        safe_bbox = _inset_bbox(container_bbox, left=12.0, top=10.0, right=12.0, bottom=10.0)
        rationale = "container_inset_default"

    reserved_zones = list(group[0].get("container_reserved_zones") or [])
    item_boxes = [[float(v) for v in item["bbox"]] for item in group if isinstance(item.get("bbox"), list)]
    container_w = _bbox_width(container_bbox)
    container_h = _bbox_height(container_bbox)

    if container_role == "center_coordination_node" and not has_explicit_safe:
        cx, cy = _bbox_center(container_bbox)
        safe_bbox = [
            cx - container_w * 0.28,
            cy - container_h * 0.29,
            cx + container_w * 0.28,
            cy + container_h * 0.29,
        ]
        rationale = "inferred_inner_ring_safe_bbox"

    elif container_role == "left_stage_label" and not has_explicit_safe:
        safe_bbox = [float(v) for v in container_bbox]
        rationale = "left_stage_label_full_badge_safe_bbox"

    elif container_role == "top_actor_card":
        if item_boxes:
            union_x1 = min(box[0] for box in item_boxes)
            union_x2 = max(box[2] for box in item_boxes)
        else:
            union_x1, union_x2 = container_bbox[0] + container_w * 0.25, container_bbox[2] - 18.0
        icon_zone_end = max(container_bbox[0] + min(max(container_w * 0.2, 88.0), 132.0), union_x1 - 14.0)
        if union_x1 > container_bbox[0] + 56.0:
            reserved_zones.append(
                _zone("left_icon_zone", [container_bbox[0], container_bbox[1], icon_zone_end, container_bbox[3]], "top_actor_card_left_icon")
            )
        safe_bbox = [
            max(container_bbox[0] + 18.0, union_x1),
            container_bbox[1] + max(14.0, container_h * 0.1),
            min(container_bbox[2] - 18.0, union_x2 + 16.0),
            container_bbox[3] - max(14.0, container_h * 0.1),
        ]
        rationale = "top_actor_card_icon_aware_text_group"

    elif container_role == "middle_service_panel":
        service_boxes = [
            [float(v) for v in item["bbox"]]
            for item in group
            if item.get("role") in {"service_item", "panel_title"} and isinstance(item.get("bbox"), list)
        ]
        if service_boxes:
            text_min_x = min(box[0] for box in service_boxes)
            text_max_x = max(box[2] for box in service_boxes)
            left_threshold = container_bbox[0] + max(48.0, container_w * 0.1)
            right_threshold = container_bbox[2] - max(48.0, container_w * 0.08)
            text_x1 = max(container_bbox[0] + 24.0, text_min_x)
            text_x2 = min(container_bbox[2] - 24.0, text_max_x + 20.0)
            if text_min_x > left_threshold:
                reserved_zones.append(
                    _zone("left_icon_zone", [container_bbox[0], container_bbox[1], text_min_x - 14.0, container_bbox[3]], "middle_service_panel_left_icon_or_ring")
                )
            if text_max_x > right_threshold:
                right_zone_w = max(135.0, container_w * 0.26)
                right_zone_x1 = container_bbox[2] - right_zone_w
                reserved_zones.append(
                    _zone("right_icon_zone", [right_zone_x1, container_bbox[1], container_bbox[2], container_bbox[3]], "middle_service_panel_right_icon")
                )
                text_x2 = min(text_x2, right_zone_x1)
                if text_x2 - text_x1 < 210.0:
                    text_x2 = min(container_bbox[2] - 96.0, text_x1 + 240.0)
                text_x2 = min(text_x2, container_bbox[2] - 72.0)
            safe_bbox = [text_x1, container_bbox[1] + 20.0, max(text_x1 + 1.0, text_x2), container_bbox[3] - 8.0]
            rationale = "middle_service_panel_reserved_icon_zones"

    elif container_role == "profit_card":
        regions = _profit_card_regions(container_bbox)
        reserved_zones.extend(
            [
                _zone("profit_icon_zone", regions["icon_zone"], "profit_card_background_icon"),
            ]
        )
        safe_bbox = _inset_bbox(container_bbox, left=10.0, top=10.0, right=10.0, bottom=16.0)
        rationale = "profit_card_partitioned_regions"

    return {
        "container_bbox": _round_bbox(container_bbox),
        "container_safe_bbox": _round_bbox(safe_bbox) if isinstance(safe_bbox, list) else None,
        "reserved_zones": reserved_zones,
        "layout_rationale": rationale,
    }


def _item_layout_policy(item: dict[str, Any]) -> dict[str, Any]:
    role = str(item.get("role") or "text")
    container_role = str(item.get("container_role") or "")
    if container_role == "center_coordination_node":
        return {
            "strategy": "stack_center_in_container",
            "align": "center",
            "v_align": "middle",
            "font_weight": "700",
            "max_font_size": 14.5,
            "min_font_size": 10.0,
            "fit_order": ["nudge_into_text_safe_bbox", "shrink_font", "semantic_revision_if_still_overflow"],
        }
    if container_role == "profit_card" and role == "index":
        return {
            "strategy": "center_in_index_marker",
            "align": "center",
            "v_align": "middle",
            "font_weight": "700",
            "fit_order": ["infer_index_marker_from_profit_card", "center_text_in_marker", "shrink_font"],
        }
    if role in {"stage_label", "index"}:
        return {"strategy": "center_badge", "align": "center", "v_align": "middle", "font_weight": "700"}
    if role in {"actor_title", "panel_title", "profit_title"}:
        return {"strategy": "title", "align": item.get("align") or "center", "v_align": "middle", "font_weight": "700"}
    if role in {"service_item", "profit_body", "actor_summary", "relationship"}:
        return {"strategy": "body_or_label", "align": item.get("align") or "center", "v_align": "middle"}
    return {"strategy": "plain_text", "align": item.get("align") or "left", "v_align": item.get("v_align") or "top"}


def _validate_layout_items(layout: dict[str, Any], *, stage: str) -> list[dict[str, Any]]:
    items = layout.get("items", [])
    if not isinstance(items, list):
        raise ValueError(f"{stage}: items must be a list")
    validated: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"{stage}: item[{index}] must be an object")
        if "text" not in item or item.get("text") is None:
            raise ValueError(f"{stage}: item[{index}] missing required field 'text'")
        if "bbox" not in item:
            raise ValueError(f"{stage}: item[{index}] missing required field 'bbox'")
        bbox = item.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            raise ValueError(f"{stage}: item[{index}] field 'bbox' must be a 4-number list")
        try:
            [float(v) for v in bbox]
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{stage}: item[{index}] field 'bbox' must contain only numbers") from exc
        validated.append(item)
    return validated


def _layout_override(
    bbox: list[float],
    font_size: Any,
    *,
    align: str | None = None,
    v_align: str | None = None,
    font_weight: str | None = None,
    layout_strategy: str,
    fit_order: list[str],
    container_safe_bbox: list[float] | None = None,
    reserved_zones: list[dict[str, Any]] | None = None,
    group_align: str | None = None,
) -> dict[str, Any]:
    """Shared shape for a `build_layout_plan` container-role branch's per-item
    override, replacing ~20 near-identical hand-written dict literals (one per
    branch). `lock_bbox`/`container_fit` are unconditionally True: every branch
    that plans an explicit bbox wants it locked and container-fitted, and none
    of them ever asked for the opposite. Optional keys (`container_safe_bbox`,
    `reserved_zones`, `group_align`) are omitted when not given rather than set
    to `None`, but this is behaviorally identical at the consumption site in
    build_layout_plan(), which reads every key through `.get(key, default)` /
    `or` fallbacks that treat an absent key the same as a falsy one -- the one
    exception is `reserved_zones`, checked with `is None`, which is why it is
    only included here when the caller actually has a value.
    """
    override: dict[str, Any] = {
        "bbox": bbox,
        "font_size": font_size,
        "align": align,
        "v_align": v_align,
        "font_weight": font_weight,
        "lock_bbox": True,
        "container_fit": True,
        "layout_strategy": layout_strategy,
        "fit_order": fit_order,
    }
    if container_safe_bbox is not None:
        override["container_safe_bbox"] = container_safe_bbox
    if reserved_zones is not None:
        override["reserved_zones"] = reserved_zones
    if group_align is not None:
        override["group_align"] = group_align
    return override


def build_layout_plan(layout: dict[str, Any]) -> dict[str, Any]:
    """Plan text placement by container role before rendering PPT boxes."""
    plan_items: list[dict[str, Any]] = []
    items = _validate_layout_items(layout, stage="build_layout_plan")
    by_container: dict[str, list[int]] = {}
    for index, item in enumerate(items):
        container_id = str(item.get("container_id") or f"__item_{index}")
        by_container.setdefault(container_id, []).append(index)

    planned_overrides: dict[int, dict[str, Any]] = {}
    planned_contexts: dict[int, dict[str, Any]] = {}
    for indexes in by_container.values():
        group = [items[index] for index in indexes]
        if not group:
            continue
        container_role = str(group[0].get("container_role") or "")
        container_id = str(group[0].get("container_id") or f"__item_{indexes[0]}")
        raw_safe_bbox = group[0].get("container_text_safe_bbox") or group[0].get("container_bbox")
        context = _container_layout_context(group, container_role=container_role, fallback_safe_bbox=raw_safe_bbox)
        safe_bbox = context["container_safe_bbox"]
        container_bbox = context["container_bbox"]
        for index in indexes:
            role = str(items[index].get("role") or "text")
            planned_contexts[index] = {
                **context,
                "group_id": f"{container_id}:{role}",
                "group_align": "center" if role in {"stage_label", "center_label", "service_item", "profit_title", "profit_body", "index"} else "left",
                "semantic_compression_level": _semantic_compression_level(role),
            }
        center_label_indexes = [index for index in indexes if items[index].get("role") == "center_label"]
        if container_role == "center_coordination_node" and isinstance(safe_bbox, list) and center_label_indexes:
            ordered = sorted(center_label_indexes, key=lambda index: float(items[index]["bbox"][1]))
            safe_x1, safe_y1, safe_x2, safe_y2 = [float(v) for v in safe_bbox]
            safe_w = max(1.0, safe_x2 - safe_x1)
            safe_h = max(1.0, safe_y2 - safe_y1)
            max_preferred = min(float(items[ordered[0]].get("font_size") or 14.5), 14.5)
            min_size = 10.0
            font_size = max(
                min_size,
                min(_fit_font_size(str(item.get("text") or ""), safe_w * 0.78, max_preferred, min_size) for item in (items[i] for i in ordered)),
            )
            line_h = max(font_size * 1.5, 20.0)
            gap = max(5.0, font_size * 0.45)
            total_h = len(ordered) * line_h + max(0, len(ordered) - 1) * gap
            top = safe_y1 + max(0.0, (safe_h - total_h) / 2.0)
            for position, index in enumerate(ordered):
                y1 = top + position * (line_h + gap)
                planned_overrides[index] = _layout_override(
                    [safe_x1, y1, safe_x2, min(safe_y2, y1 + line_h)],
                    round(font_size, 2),
                    align="center",
                    v_align="middle",
                    layout_strategy="stack_center_in_container",
                    fit_order=["nudge_into_text_safe_bbox", "shrink_font", "semantic_revision_if_still_overflow"],
                )
        stage_label_indexes = [index for index in indexes if items[index].get("role") == "stage_label"]
        if container_role == "left_stage_label" and isinstance(safe_bbox, list) and stage_label_indexes:
            ordered = sorted(stage_label_indexes, key=lambda index: float(items[index]["bbox"][1]))
            safe_x1, safe_y1, safe_x2, safe_y2 = [float(v) for v in safe_bbox]
            if len(ordered) > 1 and not group[0].get("container_has_text_safe_bbox"):
                item_boxes = [[float(v) for v in items[index]["bbox"]] for index in ordered]
                union_x1 = min(box[0] for box in item_boxes)
                union_y1 = min(box[1] for box in item_boxes)
                union_x2 = max(box[2] for box in item_boxes)
                union_y2 = max(box[3] for box in item_boxes)
                safe_x1 = max(safe_x1, union_x1 - 8.0)
                safe_y1 = max(safe_y1, union_y1 - 8.0)
                safe_x2 = min(safe_x2, union_x2 + 8.0)
                safe_y2 = min(safe_y2, union_y2 + 8.0)
            safe_w = max(1.0, safe_x2 - safe_x1)
            safe_h = max(1.0, safe_y2 - safe_y1)
            max_preferred = max(float(items[index].get("font_size") or 16.0) for index in ordered)
            max_preferred = min(max_preferred, 18.0)
            min_size = 10.0
            font_size = max(
                min_size,
                min(_fit_font_size(str(items[index].get("text") or ""), safe_w * 0.9, max_preferred, min_size) for index in ordered),
            )
            if len(ordered) == 1:
                planned_overrides[ordered[0]] = _layout_override(
                    [safe_x1, safe_y1, safe_x2, safe_y2],
                    round(min(font_size, safe_h * 0.55), 2),
                    align="center",
                    v_align="middle",
                    font_weight="700",
                    layout_strategy="center_in_badge",
                    fit_order=["use_container_text_safe_bbox", "shrink_font", "semantic_revision_if_still_overflow"],
                )
            else:
                line_h = max(font_size * 1.35, 20.0)
                gap = max(3.0, font_size * 0.25)
                total_h = len(ordered) * line_h + max(0, len(ordered) - 1) * gap
                top = safe_y1 + max(0.0, (safe_h - total_h) / 2.0)
                for position, index in enumerate(ordered):
                    y1 = top + position * (line_h + gap)
                    planned_overrides[index] = _layout_override(
                        [safe_x1, y1, safe_x2, min(safe_y2, y1 + line_h)],
                        round(font_size, 2),
                        align="center",
                        v_align="middle",
                        font_weight="700",
                        layout_strategy="stack_center_in_badge",
                        fit_order=["use_container_text_safe_bbox", "shrink_font", "semantic_revision_if_still_overflow"],
                    )
        if container_role == "stage_card" and isinstance(safe_bbox, list):
            safe_x1, safe_y1, safe_x2, safe_y2 = [float(v) for v in safe_bbox]
            stage_index_indexes = [index for index in indexes if items[index].get("role") == "index"]
            stage_title_indexes = [index for index in indexes if items[index].get("role") == "stage_label"]
            stage_body_indexes = [index for index in indexes if items[index].get("role") == "stage_body"]
            for index in stage_index_indexes:
                item_bbox = [float(v) for v in items[index]["bbox"]]
                marker_cx, marker_cy = _bbox_center(item_bbox)
                marker_side = max(28.0, min(32.0, max(_bbox_width(item_bbox), _bbox_height(item_bbox)) + 6.0))
                marker_bbox = [
                    marker_cx - marker_side / 2.0,
                    marker_cy - marker_side / 2.0,
                    marker_cx + marker_side / 2.0,
                    marker_cy + marker_side / 2.0,
                ]
                planned_overrides[index] = _layout_override(
                    marker_bbox,
                    items[index].get("font_size"),
                    align="center",
                    v_align="middle",
                    font_weight=items[index].get("font_weight") or "700",
                    container_safe_bbox=marker_bbox,
                    layout_strategy="stage_index_follow_full_image_style",
                    fit_order=["learn_full_image_style", "keep_marker_center"],
                )
            for index in stage_title_indexes:
                item = items[index]
                item_bbox = [float(v) for v in item["bbox"]]
                title_h = max(20.0, item_bbox[3] - item_bbox[1])
                title_x1 = max(safe_x1, item_bbox[0] - 8.0)
                planned_overrides[index] = _layout_override(
                    [title_x1, item_bbox[1], safe_x2, item_bbox[1] + title_h],
                    item.get("font_size"),
                    align=item.get("align") or "left",
                    v_align="middle",
                    font_weight=item.get("font_weight") or "700",
                    layout_strategy="stage_title_use_card_text_safe_width",
                    fit_order=["learn_full_image_style", "use_card_text_safe_bbox", "shrink_font"],
                )
            for index in stage_body_indexes:
                item = items[index]
                item_bbox = [float(v) for v in item["bbox"]]
                body_y1 = max(item_bbox[1], safe_y1 + 42.0)
                planned_overrides[index] = _layout_override(
                    [safe_x1, body_y1, safe_x2, safe_y2],
                    item.get("font_size"),
                    align=item.get("align") or "left",
                    v_align=item.get("v_align") or "top",
                    font_weight=item.get("font_weight"),
                    layout_strategy="stage_body_use_card_text_safe_width",
                    fit_order=["learn_full_image_style", "use_card_text_safe_bbox", "wrap_if_needed", "shrink_font"],
                )
        isolated_text_indexes = [index for index in indexes if items[index].get("container_role") == "isolated_text_region"]
        if container_role == "isolated_text_region" and isinstance(safe_bbox, list) and isolated_text_indexes:
            safe_x1, safe_y1, safe_x2, safe_y2 = [float(v) for v in safe_bbox]
            for index in isolated_text_indexes:
                item = items[index]
                planned_overrides[index] = _layout_override(
                    [safe_x1, safe_y1, safe_x2, safe_y2],
                    item.get("font_size"),
                    align=item.get("align") or ("left" if item.get("role") in BODY_TEXT_ROLES else "center"),
                    v_align=item.get("v_align") or ("top" if item.get("role") in BODY_TEXT_ROLES else "middle"),
                    font_weight=item.get("font_weight"),
                    container_safe_bbox=[safe_x1, safe_y1, safe_x2, safe_y2],
                    layout_strategy="isolated_text_use_expanded_local_safe_area",
                    fit_order=["expand_local_region", "wrap_if_needed", "shrink_font", "semantic_revision_if_still_overflow"],
                )
        process_chain_indexes = [
            index for index in indexes if items[index].get("role") in {"chain_label", "chain_body"}
        ]
        if container_role == "process_chain_card" and isinstance(safe_bbox, list) and process_chain_indexes:
            safe_x1, safe_y1, safe_x2, safe_y2 = [float(v) for v in safe_bbox]
            for index in process_chain_indexes:
                item = items[index]
                role = str(item.get("role") or "")
                if role == "chain_label":
                    bbox = [safe_x1, safe_y1, safe_x2, min(safe_y2, safe_y1 + 35.0)]
                    strategy = "process_chain_label_use_card_safe_area"
                    v_align = "middle"
                    font_weight = item.get("font_weight") or "700"
                else:
                    bbox = [safe_x1, min(safe_y2, safe_y1 + 41.0), safe_x2, safe_y2]
                    strategy = "process_chain_body_use_card_safe_area"
                    v_align = item.get("v_align") or "middle"
                    font_weight = item.get("font_weight")
                planned_overrides[index] = _layout_override(
                    bbox,
                    item.get("font_size"),
                    align=item.get("align") or "center",
                    v_align=v_align,
                    font_weight=font_weight,
                    container_safe_bbox=[safe_x1, safe_y1, safe_x2, safe_y2],
                    layout_strategy=strategy,
                    fit_order=["infer_process_chain_card", "use_card_safe_area", "wrap_if_needed", "semantic_revision_if_still_overflow"],
                )
        product_panel_indexes = [
            index for index in indexes if items[index].get("role") in {"product_title", "product_body"}
        ]
        if container_role == "product_panel" and isinstance(safe_bbox, list) and product_panel_indexes:
            safe_x1, safe_y1, safe_x2, safe_y2 = [float(v) for v in safe_bbox]
            for index in product_panel_indexes:
                item = items[index]
                item_bbox = [float(v) for v in item["bbox"]]
                planned_overrides[index] = _layout_override(
                    [safe_x1, item_bbox[1], safe_x2, min(safe_y2, item_bbox[3] + 3.0)],
                    item.get("font_size"),
                    align=item.get("align") or "left",
                    v_align=item.get("v_align") or ("top" if item.get("role") == "product_body" else "middle"),
                    font_weight=item.get("font_weight") or ("700" if item.get("role") == "product_title" else None),
                    layout_strategy="product_text_use_panel_safe_width",
                    fit_order=["learn_full_image_style", "use_product_panel_safe_bbox", "wrap_if_needed", "shrink_font"],
                )
        service_card_indexes = [index for index in indexes if items[index].get("role") == "service_item"]
        if container_role == "service_card" and isinstance(safe_bbox, list) and service_card_indexes:
            safe_x1, safe_y1, safe_x2, safe_y2 = [float(v) for v in safe_bbox]
            ordered_services = sorted(service_card_indexes, key=lambda index: float(items[index]["bbox"][1]))
            for position, index in enumerate(ordered_services):
                item = items[index]
                item_bbox = [float(v) for v in item["bbox"]]
                planned_overrides[index] = _layout_override(
                    [safe_x1, item_bbox[1], safe_x2, min(safe_y2, item_bbox[3] + 3.0)],
                    item.get("font_size"),
                    align=item.get("align") or "center",
                    v_align="middle",
                    font_weight=item.get("font_weight") or ("700" if position == 0 else None),
                    layout_strategy="service_text_use_card_safe_width",
                    fit_order=["learn_full_image_style", "use_service_card_safe_bbox", "wrap_if_needed", "shrink_font"],
                )
        trust_indexes = [index for index in indexes if items[index].get("role") in {"trust_title", "trust_body"}]
        if container_role == "trust_card" and isinstance(safe_bbox, list) and trust_indexes:
            safe_x1, safe_y1, safe_x2, safe_y2 = [float(v) for v in safe_bbox]
            trust_title_indexes = [index for index in trust_indexes if items[index].get("role") == "trust_title"]
            trust_body_indexes = [index for index in trust_indexes if items[index].get("role") == "trust_body"]
            title_bottom = safe_y1
            for index in sorted(trust_title_indexes, key=lambda item_index: float(items[item_index]["bbox"][1])):
                item = items[index]
                item_bbox = [float(v) for v in item["bbox"]]
                title_y1 = max(safe_y1 + 4.0, item_bbox[1])
                title_y2 = min(safe_y2, title_y1 + max(18.0, item_bbox[3] - item_bbox[1]))
                title_bottom = max(title_bottom, title_y2)
                planned_overrides[index] = _layout_override(
                    [safe_x1, title_y1, safe_x2, title_y2],
                    item.get("font_size"),
                    align=item.get("align") or "left",
                    v_align=item.get("v_align") or "top",
                    font_weight=item.get("font_weight") or "700",
                    layout_strategy="trust_text_use_card_safe_width",
                    fit_order=["learn_full_image_style", "use_trust_card_safe_bbox", "wrap_if_needed", "semantic_revision_if_still_overflow"],
                )
            for index in sorted(trust_body_indexes, key=lambda item_index: float(items[item_index]["bbox"][1])):
                item = items[index]
                item_bbox = [float(v) for v in item["bbox"]]
                body_y1 = max(item_bbox[1], title_bottom + 6.0 if trust_title_indexes else safe_y1)
                planned_overrides[index] = _layout_override(
                    [safe_x1, body_y1, safe_x2, safe_y2],
                    item.get("font_size"),
                    align=item.get("align") or "left",
                    v_align=item.get("v_align") or "top",
                    font_weight=item.get("font_weight"),
                    layout_strategy="trust_text_use_card_safe_width",
                    fit_order=["learn_full_image_style", "separate_title_body", "use_trust_card_safe_bbox", "wrap_if_needed", "semantic_revision_if_still_overflow"],
                )
        side_actor_indexes = [index for index in indexes if items[index].get("role") == "actor_summary"]
        if container_role == "side_actor_panel" and isinstance(safe_bbox, list) and side_actor_indexes:
            safe_x1, safe_y1, safe_x2, safe_y2 = [float(v) for v in safe_bbox]
            for index in side_actor_indexes:
                item = items[index]
                planned_overrides[index] = _layout_override(
                    [safe_x1, safe_y1, safe_x2, safe_y2],
                    item.get("font_size"),
                    align=item.get("align") or "left",
                    v_align=item.get("v_align") or "top",
                    font_weight=item.get("font_weight"),
                    container_safe_bbox=[safe_x1, safe_y1, safe_x2, safe_y2],
                    layout_strategy="side_actor_summary_use_full_card_safe_area",
                    fit_order=["use_side_card_safe_bbox", "wrap_if_needed", "shrink_font", "semantic_revision_if_still_overflow"],
                )
        terminal_note_indexes = [index for index in indexes if items[index].get("role") == "chain_body"]
        if container_role == "chain_terminal_note" and isinstance(safe_bbox, list) and terminal_note_indexes:
            safe_x1, safe_y1, safe_x2, safe_y2 = [float(v) for v in safe_bbox]
            for index in terminal_note_indexes:
                item = items[index]
                planned_overrides[index] = _layout_override(
                    [safe_x1, safe_y1, safe_x2, safe_y2],
                    item.get("font_size"),
                    align=item.get("align") or "center",
                    v_align=item.get("v_align") or "middle",
                    font_weight=item.get("font_weight"),
                    container_safe_bbox=[safe_x1, safe_y1, safe_x2, safe_y2],
                    layout_strategy="terminal_chain_note_use_dashed_box_safe_area",
                    fit_order=["use_terminal_note_safe_bbox", "wrap_if_needed", "shrink_font", "semantic_revision_if_still_overflow"],
                )
        service_indexes = [index for index in indexes if items[index].get("role") == "service_item"]
        panel_title_indexes = [index for index in indexes if items[index].get("role") == "panel_title"]
        if container_role == "middle_service_panel" and isinstance(safe_bbox, list) and service_indexes:
            container_x1, container_y1, container_x2, container_y2 = [float(v) for v in container_bbox]
            service_boxes = [[float(v) for v in items[index]["bbox"]] for index in service_indexes]
            service_min_x = min(box[0] for box in service_boxes)
            text_x1, text_y1, text_x2, text_y2 = [float(v) for v in safe_bbox]
            if text_x2 > text_x1 + 1.0:
                text_area_w = max(1.0, text_x2 - text_x1)
                ordered_services = sorted(
                    service_indexes,
                    key=lambda index: (float(items[index]["bbox"][1]), float(items[index]["bbox"][0])),
                )
                max_service_font = max(float(items[index].get("font_size") or 13.0) for index in ordered_services)
                col_count = 2
                col_gap = max(24.0, min(56.0, text_area_w * 0.18))
                max_text_w = max(
                    _estimated_text_width(str(items[index].get("text") or ""), max_service_font) + 14.0
                    for index in ordered_services
                )
                col_w = min(max(96.0, max_text_w), max(1.0, (text_area_w - col_gap) / col_count))
                left_x = text_x1
                right_x = text_x2 - col_w
                line_h = max(20.0, max_service_font + 7.0)
                ordered_y = sorted(box[1] for box in service_boxes)
                row_gap = 32.0
                if len(ordered_y) > 1:
                    gaps = [
                        ordered_y[position + 1] - ordered_y[position]
                        for position in range(len(ordered_y) - 1)
                        if ordered_y[position + 1] - ordered_y[position] > 4.0
                    ]
                    if gaps:
                        row_gap = max(24.0, min(38.0, gaps[0]))
                first_y = max(text_y1 + 44.0, min(box[1] for box in service_boxes))
                for position, index in enumerate(ordered_services):
                    item = items[index]
                    row = position // col_count
                    col = position % col_count
                    x1 = left_x if col == 0 else right_x
                    y1 = first_y + row * row_gap
                    font_size = min(
                        float(item.get("font_size") or max_service_font),
                        _fit_font_size(str(item.get("text") or ""), col_w * 0.94, max_service_font, 10.0),
                    )
                    planned_overrides[index] = _layout_override(
                        [x1, y1, x1 + col_w, min(text_y2, y1 + line_h)],
                        round(font_size, 2),
                        align="center",
                        v_align="middle",
                        group_align="grid_columns",
                        layout_strategy="service_grid_avoid_icon_zone",
                        fit_order=["reserve_icon_zone", "reflow_service_grid", "shrink_font", "semantic_revision_if_still_overflow"],
                    )
                for index in panel_title_indexes:
                    item = items[index]
                    title_y1, title_y2 = float(item["bbox"][1]), float(item["bbox"][3])
                    planned_overrides[index] = _layout_override(
                        [text_x1, title_y1, text_x2, title_y2],
                        item.get("font_size"),
                        align="center",
                        v_align="middle",
                        font_weight=item.get("font_weight") or "700",
                        layout_strategy="panel_title_centered_in_text_zone",
                        fit_order=["reserve_icon_zone", "center_title_in_text_zone", "shrink_font"],
                    )
        index_marker_indexes = [index for index in indexes if items[index].get("role") == "index"]
        if container_role == "profit_card" and isinstance(safe_bbox, list) and index_marker_indexes:
            regions = _profit_card_regions([float(v) for v in container_bbox])
            marker_bbox = _round_bbox(regions["index_marker"])
            marker_side = _bbox_width(marker_bbox)
            for index in index_marker_indexes:
                item = items[index]
                font_size = min(float(item.get("font_size") or 13.0), marker_side * 0.48)
                planned_overrides[index] = _layout_override(
                    marker_bbox,
                    round(font_size, 2),
                    align="center",
                    v_align="middle",
                    font_weight=item.get("font_weight") or "700",
                    container_safe_bbox=marker_bbox,
                    reserved_zones=[],
                    group_align="center",
                    layout_strategy="center_in_index_marker",
                    fit_order=["infer_index_marker_from_profit_card", "center_text_in_marker", "shrink_font"],
                )
        profit_title_indexes = [index for index in indexes if items[index].get("role") == "profit_title"]
        profit_body_indexes = [index for index in indexes if items[index].get("role") == "profit_body"]
        if container_role == "profit_card" and isinstance(container_bbox, list) and (profit_title_indexes or profit_body_indexes):
            regions = _profit_card_regions([float(v) for v in container_bbox])
            title_bbox = regions["title"]
            body_bbox = regions["body"]
            for index in profit_title_indexes:
                item = items[index]
                font_size = min(float(item.get("font_size") or 14.0), _fit_font_size(str(item.get("text") or ""), _bbox_width(title_bbox) * 0.96, 14.0, 10.5))
                planned_overrides[index] = _layout_override(
                    title_bbox,
                    round(font_size, 2),
                    align="center",
                    v_align="middle",
                    font_weight=item.get("font_weight") or "700",
                    layout_strategy="profit_title_centered_in_title_region",
                    fit_order=["use_profit_title_region", "shrink_font", "semantic_revision_if_still_overflow"],
                )
            if profit_body_indexes:
                ordered_bodies = sorted(profit_body_indexes, key=lambda index: float(items[index]["bbox"][1]))
                max_body_font = min(12.0, max(float(items[index].get("font_size") or 12.0) for index in ordered_bodies))
                body_min_font = float(_role_policy("profit_body").get("min_font_size", 9.5))
                entries = [
                    {
                        "text": items[index].get("text") or "",
                        "preferred_font_size": max_body_font,
                        "word_wrap": True,
                    }
                    for index in ordered_bodies
                ]
                slots = _stack_text_group_in_region(
                    entries,
                    body_bbox,
                    gap=max(5.0, max_body_font * 0.45),
                    min_font_size=body_min_font,
                )
                for index, slot in zip(ordered_bodies, slots):
                    planned_overrides[index] = _layout_override(
                        slot["bbox"],
                        slot["font_size"],
                        align="center",
                        v_align="middle",
                        container_safe_bbox=slot["bbox"],
                        layout_strategy="profit_body_stack_centered_in_body_region",
                        fit_order=["use_profit_body_region", "center_text_group", "shrink_font", "semantic_revision_if_still_overflow"],
                    )
        actor_indexes = [
            index
            for index in indexes
            if items[index].get("role") in {"actor_title", "actor_summary"}
        ]
        if container_role == "top_actor_card" and isinstance(safe_bbox, list) and actor_indexes:
            ordered = sorted(actor_indexes, key=lambda index: float(items[index]["bbox"][1]))
            item_boxes = [[float(v) for v in items[index]["bbox"]] for index in ordered]
            container_x1, container_y1, container_x2, container_y2 = [float(v) for v in safe_bbox]
            union_x1 = min(box[0] for box in item_boxes)
            union_x2 = max(box[2] for box in item_boxes)
            safe_x1 = max(container_x1, union_x1)
            safe_x2 = min(container_x2, union_x2 + 16.0)
            safe_y1 = container_y1
            safe_y2 = container_y2

            gaps = [
                8.0
                if items[ordered[position]].get("role") == "actor_title"
                and items[ordered[position + 1]].get("role") == "actor_summary"
                else 5.0
                for position in range(len(ordered) - 1)
            ]
            entries = [
                {
                    "text": items[index].get("text") or "",
                    "preferred_font_size": float(
                        items[index].get("font_size") or (18.0 if items[index].get("role") == "actor_title" else 14.0)
                    ),
                    "word_wrap": items[index].get("role") in BODY_TEXT_ROLES,
                }
                for index in ordered
            ]
            slots = _stack_text_group_in_region(
                entries,
                [safe_x1, safe_y1, safe_x2, safe_y2],
                gap=gaps,
                min_font_size=0.82
                * min(
                    float(items[index].get("font_size") or (18.0 if items[index].get("role") == "actor_title" else 14.0))
                    for index in ordered
                ),
            )
            for index, slot in zip(ordered, slots):
                item = items[index]
                planned_overrides[index] = _layout_override(
                    slot["bbox"],
                    slot["font_size"],
                    align=item.get("align") or "left",
                    v_align="middle",
                    font_weight=item.get("font_weight") or ("700" if item.get("role") == "actor_title" else None),
                    container_safe_bbox=slot["bbox"],
                    layout_strategy="stack_text_group_with_vertical_padding",
                    fit_order=["apply_container_vertical_padding", "center_text_group", "shrink_font", "semantic_revision_if_still_overflow"],
                )

    for index, item in enumerate(items):
        policy = _item_layout_policy(item)
        override = planned_overrides.get(index, {})
        context = planned_contexts.get(index, {})
        role = str(item.get("role", "text"))
        container_safe_bbox = override.get("container_safe_bbox") or context.get("container_safe_bbox")
        reserved_zones = override.get("reserved_zones")
        if reserved_zones is None:
            reserved_zones = context.get("reserved_zones", [])
        plan_items.append(
            {
                "index": index,
                "text": item.get("text", ""),
                "source_text": item.get("source_text", ""),
                "role": role,
                "container_id": item.get("container_id"),
                "container_role": item.get("container_role"),
                "strategy": override.get("layout_strategy") or policy["strategy"],
                "align": override.get("align") or item.get("align") or policy.get("align", "left"),
                "v_align": override.get("v_align") or item.get("v_align") or policy.get("v_align", "top"),
                "bbox": override.get("bbox") or item.get("bbox"),
                "font_size": override.get("font_size") or item.get("font_size"),
                "font_weight": override.get("font_weight") or item.get("font_weight") or policy.get("font_weight"),
                "lock_bbox": override.get("lock_bbox", item.get("lock_bbox", False)),
                "container_fit": override.get("container_fit", item.get("container_fit", True)),
                "fit_order": override.get("fit_order") or policy.get("fit_order", ["nudge_into_container", "shrink_font"]),
                "container_safe_bbox": _round_bbox(container_safe_bbox) if isinstance(container_safe_bbox, list) else None,
                "reserved_zones": reserved_zones,
                "group_id": override.get("group_id") or context.get("group_id") or f"{item.get('container_id') or index}:{role}",
                "group_align": override.get("group_align") or context.get("group_align") or ("center" if item.get("align") == "center" else "left"),
                "layout_rationale": override.get("layout_rationale") or context.get("layout_rationale"),
                "semantic_compression_level": override.get("semantic_compression_level")
                or context.get("semantic_compression_level")
                or _semantic_compression_level(role),
            }
        )
    return {
        "workflow": "dual-image-rebuild-ppt",
        "canvas": {"width": CANVAS[0], "height": CANVAS[1]},
        "layout_policy": "container_role_and_text_role_first",
        "items": plan_items,
    }


def apply_layout_plan(layout: dict[str, Any], layout_plan: dict[str, Any]) -> dict[str, Any]:
    planned = copy.deepcopy(layout)
    items = planned.get("items", [])
    for record in layout_plan.get("items", []):
        index = int(record.get("index", -1))
        if index < 0 or index >= len(items):
            continue
        item = items[index]
        for key in (
            "bbox",
            "font_size",
            "font_weight",
            "align",
            "v_align",
            "lock_bbox",
            "container_fit",
            "container_safe_bbox",
            "reserved_zones",
            "group_id",
            "group_align",
            "layout_rationale",
            "semantic_compression_level",
        ):
            value = record.get(key)
            if value is not None:
                item[key] = value
        item["layout_strategy"] = record.get("strategy")
        item["fit_order"] = record.get("fit_order")
    return planned


def _make_text_mask(
    items: list[dict[str, Any]],
    *,
    canvas: tuple[int, int],
    scale_to: tuple[int, int],
    inflate: int = 8,
) -> Image.Image:
    mask = Image.new("L", scale_to, 255)
    draw = ImageDraw.Draw(mask)
    sx = scale_to[0] / canvas[0]
    sy = scale_to[1] / canvas[1]
    for item in items:
        x1, y1, x2, y2 = [float(v) for v in item["bbox"]]
        box = [
            (x1 - inflate) * sx,
            (y1 - inflate) * sy,
            (x2 + inflate) * sx,
            (y2 + inflate) * sy,
        ]
        draw.rectangle(box, fill=0)
    return mask


def _transform_image_low(
    image: Image.Image,
    *,
    scale: float,
    dx: float,
    dy: float,
    size: tuple[int, int],
) -> Image.Image:
    cx = size[0] / 2.0
    cy = size[1] / 2.0
    matrix = (
        1.0 / scale,
        0.0,
        (cx * (scale - 1.0) - dx) / scale,
        0.0,
        1.0 / scale,
        (cy * (scale - 1.0) - dy) / scale,
    )
    return image.transform(size, Image.Transform.AFFINE, matrix, resample=Image.Resampling.BILINEAR)


def estimate_alignment(
    full_image: Path,
    background_image: Path,
    layout: dict[str, Any],
    *,
    canvas: tuple[int, int] = CANVAS,
    low_size: tuple[int, int] = (320, 180),
    max_shift_px: int = 48,
) -> AlignmentTransform:
    """Estimate a small uniform scale + translation from full image to background."""
    with Image.open(full_image) as full_raw, Image.open(background_image) as bg_raw:
        full = full_raw.convert("L").resize(low_size, Image.Resampling.LANCZOS).filter(ImageFilter.FIND_EDGES)
        bg = bg_raw.convert("L").resize(low_size, Image.Resampling.LANCZOS).filter(ImageFilter.FIND_EDGES)

    text_mask = _make_text_mask(layout.get("items", []), canvas=canvas, scale_to=low_size)
    low_max_dx = max(1, round(max_shift_px * low_size[0] / canvas[0]))
    low_max_dy = max(1, round(max_shift_px * low_size[1] / canvas[1]))
    scale_values = (0.98, 0.99, 1.0, 1.01, 1.02)
    best: tuple[float, float, float, float] | None = None

    for scale in scale_values:
        for dx in range(-low_max_dx, low_max_dx + 1):
            for dy in range(-low_max_dy, low_max_dy + 1):
                transformed_full = _transform_image_low(full, scale=scale, dx=dx, dy=dy, size=low_size)
                transformed_mask = _transform_image_low(text_mask, scale=scale, dx=dx, dy=dy, size=low_size)
                diff = ImageChops.difference(transformed_full, bg)
                masked = ImageChops.multiply(diff, transformed_mask)
                valid = max(1.0, ImageStat.Stat(transformed_mask).sum[0] / 255.0)
                score = ImageStat.Stat(masked).sum[0] / valid
                if best is None or score < best[0]:
                    best = (score, scale, dx, dy)

    if best is None:
        return AlignmentTransform()
    score, scale, low_dx, low_dy = best
    return AlignmentTransform(
        scale=scale,
        dx=low_dx * canvas[0] / low_size[0],
        dy=low_dy * canvas[1] / low_size[1],
        score=score,
    )


_BUNDLED_FONT_DIR = Path(__file__).resolve().parent.parent / "templates" / "fonts"
_BUNDLED_FONT_FILENAMES = (
    "msyh.ttc",
    "Microsoft YaHei.ttf",
    "MicrosoftYaHei.ttf",
    "msyhl.ttc",
)
# Glyph advances scale linearly with point size for TrueType/OpenType fonts
# (no per-size hinting differences worth chasing here), so one reference-size
# font object gives an exact width-per-point-size ratio for any font_size,
# without needing a font object per distinct size actually used in a deck.
_TEXT_WIDTH_REFERENCE_SIZE = 100.0


@lru_cache(maxsize=1)
def _bundled_font_path() -> str | None:
    """Path to the repo-bundled Microsoft YaHei font file, if present.

    slide-image-rebuild/templates/fonts/ is a drop-in location: the render
    sandbox this script often runs in does not have Microsoft YaHei
    installed (fc-match falls back to a Latin-only font), so text-width
    estimation used a fixed per-character ratio heuristic instead of real
    glyph metrics. When the user supplies the actual font file (as on
    2026-07-03, copied from their local Office install), prefer measuring
    against it directly over guessing.
    """
    if not _BUNDLED_FONT_DIR.is_dir():
        return None
    for name in _BUNDLED_FONT_FILENAMES:
        candidate = _BUNDLED_FONT_DIR / name
        if candidate.is_file():
            return str(candidate)
    return None


@lru_cache(maxsize=1)
def _bundled_fontconfig_env() -> dict[str, str] | None:
    """Environment overlay so fontconfig-based tools (fc-list, soffice) can see
    the repo-bundled font directory, without installing anything system-wide
    and without writing generated fontconfig cache files into the repo.

    Returns None when no bundled font is available, so callers fall back to
    the host's own environment unchanged.
    """
    if not _bundled_font_path():
        return None
    try:
        cache_dir = Path(tempfile.gettempdir()) / "dual_image_rebuild_fontconfig_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        config_path = Path(tempfile.gettempdir()) / "dual_image_rebuild_fonts.conf"
        config_path.write_text(
            "<?xml version=\"1.0\"?>\n"
            "<!DOCTYPE fontconfig SYSTEM \"fonts.dtd\">\n"
            "<fontconfig>\n"
            f"  <dir>{html.escape(str(_BUNDLED_FONT_DIR))}</dir>\n"
            f"  <cachedir>{html.escape(str(cache_dir))}</cachedir>\n"
            "  <include ignore_missing=\"yes\">/etc/fonts/fonts.conf</include>\n"
            "</fontconfig>\n",
            encoding="utf-8",
        )
    except OSError:
        return None
    env = dict(os.environ)
    env["FONTCONFIG_FILE"] = str(config_path)
    return env


@lru_cache(maxsize=1)
def _bundled_font_at_reference_size() -> Any:
    path = _bundled_font_path()
    if not path:
        return None
    try:
        return ImageFont.truetype(path, int(_TEXT_WIDTH_REFERENCE_SIZE))
    except Exception:
        return None


@lru_cache(maxsize=4096)
def _measured_width_ratio(text: str) -> float | None:
    """Real glyph-advance width of `text`, expressed as a multiple of font
    size (width / _TEXT_WIDTH_REFERENCE_SIZE), measured against the bundled
    font. Returns None when no bundled font is available (missing file,
    unreadable font, or a Pillow build without truetype support), so callers
    fall back to the fixed-ratio heuristic below."""
    font = _bundled_font_at_reference_size()
    if font is None:
        return None
    try:
        return font.getlength(text) / _TEXT_WIDTH_REFERENCE_SIZE
    except Exception:
        return None


def _estimated_text_width(text: str, font_size: float) -> float:
    if not text:
        return 0.0
    ratio = _measured_width_ratio(text)
    if ratio is not None:
        return ratio * font_size
    width = 0.0
    for char in text:
        width += font_size * (0.95 if ord(char) > 127 else 0.52)
    return width


def _fit_font_size(text: str, width: float, preferred: float, minimum: float = 7.5) -> float:
    estimated = _estimated_text_width(text, preferred)
    if estimated <= width or estimated <= 0:
        return preferred
    return max(minimum, preferred * width / estimated)


def _longest_unwrapped_segment(text: str) -> str:
    longest = ""
    current = ""
    for char in str(text):
        if char.isspace():
            if _estimated_text_width(current, 1.0) > _estimated_text_width(longest, 1.0):
                longest = current
            current = ""
        elif ord(char) <= 127:
            current += char
        else:
            if _estimated_text_width(current, 1.0) > _estimated_text_width(longest, 1.0):
                longest = current
            current = char if _estimated_text_width(char, 1.0) > _estimated_text_width(longest, 1.0) else ""
    if _estimated_text_width(current, 1.0) > _estimated_text_width(longest, 1.0):
        longest = current
    return longest or str(text)


def _fit_font_size_to_box(
    text: str,
    width: float,
    height: float,
    preferred: float,
    minimum: float = 7.5,
    *,
    word_wrap: bool,
) -> float:
    width_probe = (
        _longest_unwrapped_segment(text)
        if word_wrap
        else max(_text_lines(text), key=lambda line: _estimated_text_width(line, preferred))
    )
    width_fitted = _fit_font_size(width_probe, width * 0.96, preferred, minimum)
    if _estimated_text_height(text, width, width_fitted, word_wrap=word_wrap) <= height + 1.0:
        return width_fitted
    if _estimated_text_height(text, width, minimum, word_wrap=word_wrap) > height + 1.0:
        return minimum

    low = minimum
    high = width_fitted
    for _ in range(16):
        mid = (low + high) / 2.0
        if _estimated_text_height(text, width, mid, word_wrap=word_wrap) <= height + 1.0:
            low = mid
        else:
            high = mid
    return low


def _estimate_rendered_line_count(text: str, width: float, font_size: float, *, word_wrap: bool) -> int:
    if not word_wrap:
        return len(_text_lines(text))
    line_count = 0
    usable_width = max(1.0, width * 0.92)
    for line in _text_lines(text):
        line_width = _estimated_text_width(line, font_size)
        line_count += max(1, int((line_width + usable_width - 1) // usable_width))
    return line_count


def _estimated_text_height(text: str, width: float, font_size: float, *, word_wrap: bool) -> float:
    return _estimate_rendered_line_count(text, width, font_size, word_wrap=word_wrap) * font_size * 1.28


def _stack_text_group_in_region(
    entries: list[dict[str, Any]],
    region_bbox: list[float],
    *,
    gap: float | list[float],
    min_font_size: float,
) -> list[dict[str, Any]]:
    """Stack `entries` vertically inside `region_bbox` without overlapping.

    Each entry needs `text`, `preferred_font_size`, and optionally `word_wrap`
    (default True). All entries scale by the same factor when shrinking, so a
    group that started with different preferred sizes (e.g. a title line at
    18pt above summary lines at 14pt) keeps its relative hierarchy.

    This exists because several container-role branches in build_layout_plan
    (profit_card's body stack, top_actor_card's title+summary stack) used to
    assume a fixed height per line -- one line, `font_size + N` tall -- instead
    of measuring how many lines the *restored* text (after apply_typesetting_
    policy) actually needs at a given width. When the assumption was wrong, a
    later item's box would get expanded past its assumed slot by
    _expand_wrapped_box_height_inside_safe_area and collide with a sibling
    (found on the page014 real-page regression, 2026-07-03). This function
    always measures with the same wrap-aware _estimated_text_height used
    everywhere else in the pipeline (and in Layout QA), so the height it hands
    back is the height that will actually be needed, and it places entries
    sequentially so they cannot overlap by construction for the returned sizes.

    Returns one dict per entry, in input order:
      bbox: [x1, y1, x2, y2] -- already a tight, non-overlapping vertical slot
      font_size: float
      overflow: bool -- True when the group still does not fit at min_font_size
        (sizes are held at the floor; the caller should let the normal
        text_vertical_overflow / text_boxes_overlap QA checks surface it as a
        defect for semantic revision, rather than silently expanding further)
    """
    region_x1, region_y1, region_x2, region_y2 = [float(v) for v in region_bbox]
    width = max(1.0, region_x2 - region_x1)
    gaps = [float(gap)] * max(0, len(entries) - 1) if isinstance(gap, (int, float)) else [float(v) for v in gap]
    available_height = max(1.0, region_y2 - region_y1) - sum(gaps)

    def _heights_at_scale(scale: float) -> list[float]:
        heights = []
        for entry in entries:
            size = max(min_font_size, float(entry["preferred_font_size"]) * scale)
            heights.append(
                _estimated_text_height(
                    str(entry.get("text") or ""),
                    width * 0.96,
                    size,
                    word_wrap=bool(entry.get("word_wrap", True)),
                )
            )
        return heights

    scale = 1.0
    heights = _heights_at_scale(scale)
    if sum(heights) > available_height:
        low, high = 0.0, 1.0
        for _ in range(20):
            mid = (low + high) / 2.0
            if sum(_heights_at_scale(mid)) <= available_height:
                low = mid
            else:
                high = mid
        scale = low
        heights = _heights_at_scale(scale)

    overflow = sum(heights) > available_height + 1.0
    total_height = sum(heights) + sum(gaps)
    y_cursor = region_y1 if overflow else region_y1 + max(0.0, (region_y2 - region_y1 - total_height) / 2.0)
    results: list[dict[str, Any]] = []
    for position, (entry, height) in enumerate(zip(entries, heights)):
        size = max(min_font_size, float(entry["preferred_font_size"]) * scale)
        y_next = y_cursor + height
        results.append(
            {
                "bbox": [region_x1, y_cursor, region_x2, y_next],
                "font_size": round(size, 2),
                "overflow": overflow,
            }
        )
        y_cursor = y_next + (gaps[position] if position < len(gaps) else 0.0)
    return results


def _safe_text_box(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    text: str,
    font_size: float,
    align: str,
    canvas: tuple[int, int],
) -> tuple[float, float, float, float]:
    """Expand tight OCR boxes so Office apps do not wrap single-line text."""
    width = max(1.0, x2 - x1)
    needed = _estimated_text_width(text, font_size) * 1.22 + 8.0
    if needed <= width:
        return x1, y1, x2, y2

    extra = needed - width
    if align == "center":
        x1 -= extra / 2.0
        x2 += extra / 2.0
    elif align == "right":
        x1 -= extra
    else:
        x2 += extra

    if x1 < 0:
        x2 -= x1
        x1 = 0.0
    if x2 > canvas[0]:
        overflow = x2 - canvas[0]
        x1 = max(0.0, x1 - overflow)
        x2 = float(canvas[0])
    return x1, y1, max(x1 + 1.0, x2), y2


def _clamp_box_to_bbox(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    safe_bbox: list[float],
) -> tuple[float, float, float, float]:
    sx1, sy1, sx2, sy2 = safe_bbox
    safe_w = max(1.0, sx2 - sx1)
    safe_h = max(1.0, sy2 - sy1)
    width = max(1.0, x2 - x1)
    height = max(1.0, y2 - y1)

    if width > safe_w:
        x1, x2 = sx1, sx2
    elif x1 < sx1:
        x2 += sx1 - x1
        x1 = sx1
    elif x2 > sx2:
        x1 -= x2 - sx2
        x2 = sx2

    if height > safe_h:
        y1, y2 = sy1, sy2
    elif y1 < sy1:
        y2 += sy1 - y1
        y1 = sy1
    elif y2 > sy2:
        y1 -= y2 - sy2
        y2 = sy2

    return x1, y1, max(x1 + 1.0, x2), max(y1 + 1.0, y2)


def _expand_wrapped_box_height_inside_safe_area(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    safe_bbox: list[float],
    *,
    text: str,
    font_size: float,
    word_wrap: bool,
    v_align: str,
) -> tuple[float, float, float, float]:
    if not word_wrap:
        return x1, y1, x2, y2
    _sx1, sy1, _sx2, sy2 = safe_bbox
    height = max(1.0, y2 - y1)
    safe_h = max(1.0, sy2 - sy1)
    needed_h = _estimated_text_height(text, max(1.0, x2 - x1), font_size, word_wrap=True) * 1.12
    if needed_h <= height + 1.0:
        return x1, y1, x2, y2

    target_h = min(safe_h, max(height, needed_h))
    if v_align == "bottom":
        y1 = max(sy1, y2 - target_h)
        y2 = y1 + target_h
    elif v_align == "middle":
        cy = (y1 + y2) / 2.0
        y1 = max(sy1, min(sy2 - target_h, cy - target_h / 2.0))
        y2 = y1 + target_h
    else:
        y2 = min(sy2, max(y2, y1 + target_h))
        if y2 - y1 < target_h:
            y1 = max(sy1, y2 - target_h)
    return x1, y1, x2, max(y1 + 1.0, y2)


def _sample_luminance(image: Image.Image, bbox: list[float]) -> float:
    x1, y1, x2, y2 = [round(v) for v in bbox]
    x1 = max(0, min(image.width - 1, x1))
    x2 = max(x1 + 1, min(image.width, x2))
    y1 = max(0, min(image.height - 1, y1))
    y2 = max(y1 + 1, min(image.height, y2))
    crop = image.crop((x1, y1, x2, y2)).convert("L")
    return ImageStat.Stat(crop).mean[0]


def _text_fill_for_background(image: Image.Image, bbox: list[float], preferred: str) -> str:
    luminance = _sample_luminance(image, bbox)
    if luminance < 92:
        return "#FFFFFF"
    if luminance > 205:
        return "#111827"
    return preferred


def build_overlay_boxes(
    layout: dict[str, Any],
    background_image: Path,
    transform: AlignmentTransform,
    *,
    font_family: str = "Microsoft YaHei",
    fill: str = "#111827",
    canvas: tuple[int, int] = CANVAS,
) -> list[OverlayTextBox]:
    boxes: list[OverlayTextBox] = []
    items = _validate_layout_items(layout, stage="build_overlay_boxes")
    with Image.open(background_image) as bg_raw:
        background = bg_raw.convert("RGB")
        for item in items:
            source_bbox = [float(v) for v in item["bbox"]]
            mapped = transform.map_bbox(source_bbox, canvas)
            x1, y1, x2, y2 = mapped
            x1 = max(0.0, min(canvas[0] - 1.0, x1))
            y1 = max(0.0, min(canvas[1] - 1.0, y1))
            x2 = max(x1 + 1.0, min(float(canvas[0]), x2))
            y2 = max(y1 + 1.0, min(float(canvas[1]), y2))
            text = str(item["text"]).strip()
            width = x2 - x1
            height = y2 - y1
            preferred_size = float(item.get("font_size") or max(8.0, min(54.0, height * 0.78)))
            align = str(item.get("align") or ("center" if len(text) <= 16 and width < 320 else "left"))
            role = str(item.get("role") or "text")
            word_wrap = bool(item.get("word_wrap", False))
            v_align = str(item.get("v_align") or "top")
            if not item.get("lock_bbox"):
                x1, y1, x2, y2 = _safe_text_box(
                    x1,
                    y1,
                    x2,
                    y2,
                    text=text,
                    font_size=preferred_size,
                    align=align,
                    canvas=canvas,
                )
            safe_bbox = (
                item.get("container_safe_bbox")
                or item.get("text_safe_bbox")
                or item.get("container_text_safe_bbox")
                or item.get("container_bbox")
            )
            mapped_safe = None
            if item.get("container_fit", True) and isinstance(safe_bbox, list) and len(safe_bbox) == 4:
                mapped_safe = transform.map_bbox([float(v) for v in safe_bbox], canvas)
                x1, y1, x2, y2 = _clamp_box_to_bbox(x1, y1, x2, y2, mapped_safe)
            if mapped_safe is not None and role in BODY_TEXT_ROLES:
                x1, y1, x2, y2 = _expand_wrapped_box_height_inside_safe_area(
                    x1,
                    y1,
                    x2,
                    y2,
                    mapped_safe,
                    text=text,
                    font_size=preferred_size,
                    word_wrap=word_wrap,
                    v_align=v_align,
                )
            width = x2 - x1
            height = y2 - y1
            min_font_size = float(_role_policy(role).get("min_font_size", 7.5))
            font_size = round(
                _fit_font_size_to_box(
                    text,
                    width,
                    height,
                    preferred_size,
                    min_font_size,
                    word_wrap=word_wrap,
                ),
                2,
            )
            boxes.append(
                OverlayTextBox(
                    text=text,
                    x=round(x1, 2),
                    y=round(y1, 2),
                    w=round(width, 2),
                    h=round(height, 2),
                    font_size=font_size,
                    font_family=font_family,
                    fill=str(item.get("fill") or _text_fill_for_background(background, [x1, y1, x2, y2], fill)),
                    font_weight=str(item.get("font_weight") or ("700" if height >= 30 or len(text) <= 10 else "400")),
                    align=align,
                    confidence=float(item.get("confidence", 1.0)),
                    source_bbox=source_bbox,
                    mapped_bbox=[round(v, 2) for v in mapped],
                    role=role,
                    word_wrap=word_wrap,
                    source_text=str(item.get("source_text") or ""),
                    v_align=v_align,
                    container_id=str(item.get("container_id") or ""),
                    container_role=str(item.get("container_role") or ""),
                    container_safe_bbox=[round(float(v), 2) for v in item.get("container_safe_bbox", [])]
                    if isinstance(item.get("container_safe_bbox"), list)
                    else None,
                    reserved_zones=list(item.get("reserved_zones") or []),
                    group_id=str(item.get("group_id") or ""),
                    group_align=str(item.get("group_align") or ""),
                    layout_strategy=str(item.get("layout_strategy") or ""),
                    semantic_compression_level=str(item.get("semantic_compression_level") or ""),
                )
            )
    return boxes


def _overlay_bbox(box: OverlayTextBox) -> list[float]:
    return [box.x, box.y, box.x + box.w, box.y + box.h]


def build_layout_qa_report(layout_plan: dict[str, Any], boxes: list[OverlayTextBox]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    plan_items = layout_plan.get("items", [])
    for index, box in enumerate(boxes):
        plan_item = plan_items[index] if index < len(plan_items) and isinstance(plan_items[index], dict) else {}
        role = str(plan_item.get("role") or box.role or "text")
        policy = _role_policy(role)
        bbox = _overlay_bbox(box)
        safe_bbox = plan_item.get("container_safe_bbox") or box.container_safe_bbox
        if isinstance(safe_bbox, list) and len(safe_bbox) == 4 and not _bbox_inside(bbox, [float(v) for v in safe_bbox], tolerance=1.5):
            overflow_px = _bbox_overflow_amount(bbox, [float(v) for v in safe_bbox])
            issues.append(
                {
                    "severity": "error" if overflow_px > QA_SAFE_BBOX_ERROR_OVERFLOW_PX else "warning",
                    "code": "text_outside_container_safe_bbox",
                    "text": box.text,
                    "role": box.role,
                    "container_id": box.container_id,
                    "bbox": _round_bbox(bbox),
                    "container_safe_bbox": _round_bbox([float(v) for v in safe_bbox]),
                    "overflow_px": round(overflow_px, 2),
                }
            )
        if box.container_role == "isolated_text_region":
            if role in BODY_TEXT_ROLES:
                issues.append(
                    {
                        "severity": "error",
                        "code": "isolated_text_region_used_for_body_role",
                        "text": box.text,
                        "role": role,
                        "container_id": box.container_id,
                        "recommended_action": "add_explicit_semantic_container_or_extend_container_role_inference",
                    }
                )
            else:
                issues.append(
                    {
                        "severity": "warning",
                        "code": "isolated_text_region_used_for_non_body_role",
                        "text": box.text,
                        "role": role,
                        "container_id": box.container_id,
                        "recommended_action": "review_container_inference_before_accepting_layout",
                    }
                )
        for zone in plan_item.get("reserved_zones") or box.reserved_zones or []:
            if not isinstance(zone, dict):
                continue
            zone_bbox = zone.get("bbox")
            if not isinstance(zone_bbox, list) or len(zone_bbox) != 4:
                continue
            overlap = _bbox_intersection_area(bbox, [float(v) for v in zone_bbox])
            if overlap > 4.0:
                issues.append(
                    {
                        "severity": "warning",
                        "code": "text_intersects_reserved_zone",
                        "text": box.text,
                        "role": box.role,
                        "container_id": box.container_id,
                        "zone": zone.get("name"),
                        "overlap_area": round(overlap, 2),
                    }
                )
        if box.role == "index" and box.layout_strategy == "center_in_index_marker":
            planned_bbox = plan_item.get("bbox")
            if isinstance(planned_bbox, list) and len(planned_bbox) == 4:
                planned_cx, planned_cy = _bbox_center([float(v) for v in planned_bbox])
                actual_cx, actual_cy = _bbox_center(bbox)
                if abs(planned_cx - actual_cx) > 1.5 or abs(planned_cy - actual_cy) > 1.5:
                    issues.append(
                        {
                            "severity": "warning",
                            "code": "index_not_centered_in_marker",
                            "text": box.text,
                            "container_id": box.container_id,
                            "dx": round(actual_cx - planned_cx, 2),
                            "dy": round(actual_cy - planned_cy, 2),
                        }
                    )

        min_font_size = float(policy.get("min_font_size", DEFAULT_TYPESETTING_POLICY["min_font_size"]))
        if box.font_size < min_font_size - 0.01:
            issues.append(
                {
                    # Below the role's readability floor is not a matter of degree: any
                    # amount under the floor is a hard defect, so this is always "error".
                    "severity": "error",
                    "code": "font_below_role_minimum",
                    "text": box.text,
                    "role": role,
                    "font_size": box.font_size,
                    "min_font_size": min_font_size,
                }
            )
        estimated_height = _estimated_text_height(box.text, box.w, box.font_size, word_wrap=box.word_wrap)
        if estimated_height > box.h + max(2.0, box.font_size * 0.2):
            overflow_ratio = (estimated_height - box.h) / max(box.h, 1e-6)
            issues.append(
                {
                    "severity": "error" if overflow_ratio >= QA_VERTICAL_OVERFLOW_ERROR_RATIO else "warning",
                    "code": "text_vertical_overflow",
                    "text": box.text,
                    "role": role,
                    "estimated_height": round(estimated_height, 2),
                    "box_height": box.h,
                    "overflow_ratio": round(overflow_ratio, 3),
                    "estimated_lines": _estimate_rendered_line_count(
                        box.text,
                        box.w,
                        box.font_size,
                        word_wrap=box.word_wrap,
                    ),
                    "recommended_action": "revise_display_text_or_move_detail_to_notes",
                }
            )
            issues.append(
                {
                    "severity": "warning",
                    "code": "needs_semantic_revision",
                    "text": box.text,
                    "role": role,
                    "source_text": box.source_text,
                }
            )
        lines = _text_lines(box.text)
        if len(lines) > 1 and _text_units(lines[-1]) <= 1:
            issues.append(
                {
                    "severity": "warning",
                    "code": "orphan_cjk_line",
                    "text": box.text,
                    "role": role,
                    "last_line": lines[-1],
                }
            )

    # Sibling text boxes colliding with each other. This is distinct from the
    # container_safe_bbox / reserved_zone checks above, which only look at a box
    # against its own safe area or a declared icon zone -- neither catches two
    # different text items whose boxes were independently expanded (e.g. by
    # source_text restoration in apply_typesetting_policy) until they overlap
    # each other. That gap let two real defects render silently as "0 issues" in
    # the page014 real-page regression (2026-07-03 review): two stacked
    # actor_summary lines whose restored source_text overlapped by ~40% of their
    # own height, and a two-line stage_label where both lines got the same
    # restored sentence stacked on top of each other. Any two distinct,
    # non-empty text boxes overlapping by a non-trivial fraction of the smaller
    # box's area is a hard visual defect regardless of whether they share a
    # container_id, so this check is unconditional -- not limited to siblings in
    # the same group.
    for i in range(len(boxes)):
        box_a = boxes[i]
        text_a = box_a.text.strip()
        if not text_a:
            continue
        bbox_a = _overlay_bbox(box_a)
        area_a = max(1.0, box_a.w * box_a.h)
        for j in range(i + 1, len(boxes)):
            box_b = boxes[j]
            text_b = box_b.text.strip()
            if not text_b:
                continue
            bbox_b = _overlay_bbox(box_b)
            overlap_area = _bbox_intersection_area(bbox_a, bbox_b)
            if overlap_area <= 0:
                continue
            area_b = max(1.0, box_b.w * box_b.h)
            overlap_ratio = overlap_area / min(area_a, area_b)
            if overlap_ratio > QA_BOX_OVERLAP_ERROR_RATIO:
                issues.append(
                    {
                        "severity": "error",
                        "code": "text_boxes_overlap",
                        "text": box_a.text,
                        "other_text": box_b.text,
                        "role": box_a.role,
                        "other_role": box_b.role,
                        "container_id": box_a.container_id,
                        "other_container_id": box_b.container_id,
                        "overlap_ratio": round(overlap_ratio, 3),
                        "recommended_action": "recheck_group_level_fit_or_shorten_display_text",
                    }
                )

    groups: dict[str, list[tuple[dict[str, Any], OverlayTextBox]]] = {}
    for index, box in enumerate(boxes):
        group_id = box.group_id
        if not group_id:
            continue
        plan_item = plan_items[index] if index < len(plan_items) and isinstance(plan_items[index], dict) else {}
        groups.setdefault(group_id, []).append((plan_item, box))
    for group_id, members in groups.items():
        if len(members) < 2:
            continue
        group_align = str(members[0][0].get("group_align") or members[0][1].group_align or "")
        if group_align == "left":
            lefts = [member[1].x for member in members]
            if max(lefts) - min(lefts) > 2.0:
                issues.append(
                    {
                        "severity": "warning",
                        "code": "group_left_edges_not_aligned",
                        "group_id": group_id,
                        "spread": round(max(lefts) - min(lefts), 2),
                    }
                )
        elif group_align == "center":
            centers = [member[1].x + member[1].w / 2.0 for member in members]
            if max(centers) - min(centers) > 2.0:
                issues.append(
                    {
                        "severity": "warning",
                        "code": "group_centers_not_aligned",
                        "group_id": group_id,
                        "spread": round(max(centers) - min(centers), 2),
                    }
                )

    warnings = [issue for issue in issues if issue.get("severity") == "warning"]
    errors = [issue for issue in issues if issue.get("severity") == "error"]
    return {
        "workflow": "dual-image-rebuild-ppt",
        "stage": "post_render_geometry",
        "valid": not errors,
        "checks": {
            "container_safe_bbox": True,
            "reserved_zones": True,
            "group_alignment": True,
            "index_marker_centering": True,
            "font_floor": True,
            "text_vertical_fit": True,
            "orphan_line": True,
            "isolated_text_region_role": True,
            "text_box_overlap": True,
        },
        "issue_count": len(issues),
        "warning_count": len(warnings),
        "error_count": len(errors),
        "issues": issues,
    }


def render_overlay_svg(background_href: str, boxes: list[OverlayTextBox], *, canvas: tuple[int, int] = CANVAS) -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{canvas[0]}" height="{canvas[1]}" viewBox="0 0 {canvas[0]} {canvas[1]}">',
        f'<image x="0" y="0" width="{canvas[0]}" height="{canvas[1]}" href="{html.escape(background_href)}" xlink:href="{html.escape(background_href)}" preserveAspectRatio="none"/>',
    ]
    for box in boxes:
        anchor = {"center": "middle", "right": "end"}.get(box.align, "start")
        text_x = box.x + (box.w / 2.0 if box.align == "center" else box.w if box.align == "right" else 0.0)
        if box.v_align == "middle":
            text_y = box.y + box.h / 2.0 + box.font_size * 0.35
        elif box.v_align == "bottom":
            text_y = box.y + box.h - 2.0
        else:
            text_y = box.y + box.font_size
        parts.append(
            f'<text x="{text_x:.2f}" y="{text_y:.2f}" text-anchor="{anchor}" '
            f'font-family="{html.escape(box.font_family)}, Arial, sans-serif" '
            f'font-size="{box.font_size:.2f}" font-weight="{html.escape(box.font_weight)}" '
            f'fill="{html.escape(box.fill)}">{html.escape(box.text)}</text>'
        )
    parts.append("</svg>\n")
    return "\n".join(parts)


def _set_slide_size(prs: Presentation, canvas: tuple[int, int]) -> None:
    prs.slide_width = Emu(canvas[0] * EMU_PER_PX)
    prs.slide_height = Emu(canvas[1] * EMU_PER_PX)


def _hex_to_rgb(value: str):
    from pptx.dml.color import RGBColor

    cleaned = value.strip().lstrip("#")
    if len(cleaned) == 3:
        cleaned = "".join(ch * 2 for ch in cleaned)
    if len(cleaned) < 6:
        cleaned = "111827"
    return RGBColor(int(cleaned[0:2], 16), int(cleaned[2:4], 16), int(cleaned[4:6], 16))


def _append_relationship_xml(rels_xml: str, rel_type: str, target: str) -> str:
    import re

    rid_numbers = [int(match) for match in re.findall(r'Id="rId(\d+)"', rels_xml)]
    next_rid = f"rId{max(rid_numbers, default=0) + 1}"
    rel_xml = (
        f'<Relationship Id="{next_rid}" Type="{rel_type}" Target="{target}"/>'
    )
    return rels_xml.replace("</Relationships>", rel_xml + "</Relationships>")


def _inject_notes_into_pptx(pptx_path: Path, notes_markdown: str) -> None:
    notes_text = markdown_to_plain_text(notes_markdown)
    if not notes_text:
        return
    tmp_path = pptx_path.with_suffix(".notes_tmp.pptx")
    notes_xml = create_notes_slide_xml(1, notes_text)
    notes_rels_xml = create_notes_slide_rels_xml(1)
    notes_rel_type = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide"
    notes_content_type = "application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"
    notes_override = (
        '<Override PartName="/ppt/notesSlides/notesSlide1.xml" '
        f'ContentType="{notes_content_type}"/>'
    )
    with zipfile.ZipFile(pptx_path, "r") as src, zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            content = src.read(item.filename)
            if item.filename == "ppt/slides/_rels/slide1.xml.rels":
                rels = content.decode("utf-8")
                if notes_rel_type not in rels:
                    rels = _append_relationship_xml(rels, notes_rel_type, "../notesSlides/notesSlide1.xml")
                content = rels.encode("utf-8")
            elif item.filename == "[Content_Types].xml":
                types = content.decode("utf-8")
                if "/ppt/notesSlides/notesSlide1.xml" not in types:
                    types = types.replace("</Types>", notes_override + "</Types>")
                content = types.encode("utf-8")
            dst.writestr(item, content)
        dst.writestr("ppt/notesSlides/notesSlide1.xml", notes_xml)
        dst.writestr("ppt/notesSlides/_rels/notesSlide1.xml.rels", notes_rels_xml)
    tmp_path.replace(pptx_path)


def export_pptx(
    background_image: Path,
    boxes: list[OverlayTextBox],
    output_path: Path,
    *,
    canvas: tuple[int, int] = CANVAS,
    notes_markdown: str = "",
) -> None:
    prs = Presentation()
    _set_slide_size(prs, canvas)
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.shapes.add_picture(str(background_image), 0, 0, width=prs.slide_width, height=prs.slide_height)
    for box in boxes:
        textbox = slide.shapes.add_textbox(
            Emu(max(0.0, box.x) * EMU_PER_PX),
            Emu(max(0.0, box.y) * EMU_PER_PX),
            Emu(max(1.0, box.w) * EMU_PER_PX),
            Emu(max(1.0, box.h) * EMU_PER_PX),
        )
        text_frame = textbox.text_frame
        text_frame.clear()
        text_frame.word_wrap = box.word_wrap
        text_frame.auto_size = MSO_AUTO_SIZE.NONE
        text_frame.margin_left = 0
        text_frame.margin_right = 0
        text_frame.margin_top = 0
        text_frame.margin_bottom = 0
        text_frame.vertical_anchor = {
            "middle": MSO_ANCHOR.MIDDLE,
            "bottom": MSO_ANCHOR.BOTTOM,
        }.get(box.v_align, MSO_ANCHOR.TOP)
        lines = box.text.splitlines() or [box.text]
        for line_index, line in enumerate(lines):
            paragraph = text_frame.paragraphs[0] if line_index == 0 else text_frame.add_paragraph()
            paragraph.alignment = {"center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}.get(box.align, PP_ALIGN.LEFT)
            paragraph.space_before = Pt(0)
            paragraph.space_after = Pt(0)
            run = paragraph.add_run()
            run.text = line
            run.font.name = box.font_family
            run.font.size = Pt(box.font_size)
            run.font.bold = box.font_weight in {"700", "800", "900", "bold"}
            run.font.color.rgb = _hex_to_rgb(box.fill)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
    if notes_markdown:
        _inject_notes_into_pptx(output_path, notes_markdown)


def _normalize_pptx_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def _box_text(box: Any) -> str:
    if isinstance(box, OverlayTextBox):
        return box.text
    if isinstance(box, dict):
        return str(box.get("text") or "")
    return str(box or "")


def _pptx_text_shapes(pptx_path: Path) -> list[str]:
    prs = Presentation(pptx_path)
    texts: list[str] = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if not getattr(shape, "has_text_frame", False):
                continue
            text = _normalize_pptx_text(shape.text_frame.text)
            if text:
                texts.append(text)
    return texts


def build_text_content_qa_report(expected_boxes: list[Any], pptx_path: Path) -> dict[str, Any]:
    expected_texts: list[str] = []
    for box in expected_boxes:
        text = _normalize_pptx_text(_box_text(box))
        if text:
            expected_texts.append(text)
    actual_texts = _pptx_text_shapes(pptx_path)
    mismatches: list[dict[str, Any]] = []
    for index in range(max(len(expected_texts), len(actual_texts))):
        expected = expected_texts[index] if index < len(expected_texts) else None
        actual = actual_texts[index] if index < len(actual_texts) else None
        if expected != actual:
            mismatches.append(
                {
                    "index": index,
                    "expected": expected,
                    "actual": actual,
                    "code": "pptx_text_differs_from_mapping",
                }
            )
    valid = not mismatches
    return {
        "workflow": "dual-image-rebuild-ppt",
        "stage": "pptx_text_content_qa",
        "policy": "compare_exported_pptx_text_against_mapping_without_ocr",
        "valid": valid,
        "checks": {
            "text_count_matches": len(expected_texts) == len(actual_texts),
            "pptx_text_matches_mapping": valid,
        },
        "expected_count": len(expected_texts),
        "actual_count": len(actual_texts),
        "expected_texts": expected_texts,
        "actual_texts": actual_texts,
        "mismatches": mismatches,
        "issue_count": len(mismatches),
    }


def build_production_readiness_report(
    *,
    semantic_plan: dict[str, Any] | None,
    safe_area_report: dict[str, Any],
    layout_qa: dict[str, Any],
    text_content_qa: dict[str, Any],
) -> dict[str, Any]:
    explicit_containers = semantic_plan_owns_geometry(semantic_plan)
    profile_source = str(safe_area_report.get("profile_source") or "")
    issues: list[dict[str, Any]] = []
    if not explicit_containers:
        issues.append(
            {
                "severity": "error",
                "code": "missing_explicit_semantic_containers_for_production",
                "recommended_action": "author semantic_plan.containers and link every visible text item by container_id",
            }
        )
    if not explicit_containers and profile_source == "page012_default_unverified":
        issues.append(
            {
                "severity": "error",
                "code": "page012_default_profile_used_for_production",
                "profile_source": profile_source,
                "recommended_action": "treat auto-inferred safe areas as diagnostic only; provide explicit semantic containers",
            }
        )
    if not bool(layout_qa.get("valid", True)):
        issues.append(
            {
                "severity": "error",
                "code": "layout_qa_has_errors",
                "error_count": int(layout_qa.get("error_count", 0)),
                "recommended_action": "fix P01_layout_qa.json errors before acceptance",
            }
        )
    if not bool(text_content_qa.get("valid", True)):
        issues.append(
            {
                "severity": "error",
                "code": "pptx_text_content_mismatch",
                "issue_count": int(text_content_qa.get("issue_count", 0)),
                "recommended_action": "compare P01_text_content_qa.json against the mapping truth",
            }
        )
    error_count = sum(1 for issue in issues if issue.get("severity") == "error")
    return {
        "workflow": "dual-image-rebuild-ppt",
        "stage": "production_readiness_qa",
        "policy": "production_requires_explicit_semantic_containers; inferred_page012_profile_is_diagnostic_only",
        "valid": error_count == 0,
        "checks": {
            "explicit_semantic_containers": explicit_containers,
            "default_profile_not_used_as_acceptance_basis": explicit_containers or profile_source != "page012_default_unverified",
            "layout_qa_valid": bool(layout_qa.get("valid", True)),
            "pptx_text_matches_mapping": bool(text_content_qa.get("valid", True)),
        },
        "profile_source": profile_source or None,
        "issues": issues,
        "error_count": error_count,
    }


def _check_font_available(font_family: str) -> bool | None:
    """Best-effort check for whether `font_family` is installed for the renderer to use.

    Returns True/False when `fc-list` (fontconfig) is present and answers definitively,
    or None when availability cannot be determined on this host (e.g. no fontconfig,
    as on stock macOS). None must not be treated as "available" by callers.
    """
    fc_list = shutil.which("fc-list")
    if not fc_list:
        return None
    try:
        result = subprocess.run(
            [fc_list, ":family"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=_bundled_fontconfig_env() or None,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    family_lower = font_family.strip().lower()
    return any(family_lower in line.lower() for line in result.stdout.splitlines())


def build_pdf_preview(pptx_path: Path, output_dir: Path, *, font_family: str = "Microsoft YaHei") -> dict[str, Any]:
    # This preview is rendered by LibreOffice (soffice), not PowerPoint or WPS.
    # LibreOffice's text layout, font substitution, and autofit behavior can
    # differ from real Office, especially for CJK wrapping. Treat this PNG as a
    # repeatable regression aid, not as proof of how the deck will look when a
    # user opens it in PowerPoint/WPS -- that still needs a manual cross-check.
    render_engine = "libreoffice_soffice"
    font_available = _check_font_available(font_family)
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    pdftoppm = shutil.which("pdftoppm")
    if not soffice or not pdftoppm:
        missing = []
        if not soffice:
            missing.append("soffice")
        if not pdftoppm:
            missing.append("pdftoppm")
        return {
            "valid": False,
            "warnings": [f"pdf_preview_missing_tool:{','.join(missing)}"],
            "render_engine": render_engine,
            "font_family_requested": font_family,
            "font_available": font_available,
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            soffice,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(pptx_path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=_bundled_fontconfig_env() or None,
    )
    converted_pdf = output_dir / f"{pptx_path.stem}.pdf"
    stable_pdf = output_dir / "slide.pdf"
    if converted_pdf != stable_pdf:
        converted_pdf.replace(stable_pdf)
    page_prefix = output_dir / "page-1"
    subprocess.run(
        [
            pdftoppm,
            "-png",
            "-r",
            "144",
            "-f",
            "1",
            "-l",
            "1",
            "-singlefile",
            str(stable_pdf),
            str(page_prefix),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    page_png = page_prefix.with_suffix(".png")
    warnings = [] if page_png.is_file() else ["pdf_preview_page_png_missing"]
    if font_available is False:
        warnings.append(f"pdf_preview_font_family_unavailable:{font_family}")
    return {
        "valid": page_png.is_file(),
        "pdf": str(stable_pdf),
        "page_png": str(page_png),
        "warnings": warnings,
        "render_engine": render_engine,
        "font_family_requested": font_family,
        "font_available": font_available,
    }


def notes_from_semantic_plan(plan: dict[str, Any] | None, boxes: list[OverlayTextBox]) -> str:
    if plan:
        notes = plan.get("notes")
        if isinstance(notes, list):
            return "\n".join(str(line) for line in notes if str(line).strip())
        if isinstance(notes, str) and notes.strip():
            return notes.strip()

    title = boxes[0].text if boxes else "双图复刻页"
    visible = "；".join(box.text for box in boxes[:12])
    return (
        f"# {title}\n\n"
        "本页基于完整图进行语义理解，并以无字底图作为视觉底稿重构。\n\n"
        f"讲解时可围绕页面可见信息展开：{visible}。"
    )


def _write_project_readme(project: Path, full_image: Path, background_image: Path, layout_path: Path | None) -> None:
    (project / "README.md").write_text(
        (
            "# 双图复刻ppt\n\n"
            "- Workflow: dual-image-rebuild-ppt\n"
            f"- Full image: `{full_image}`\n"
            f"- Background image: `{background_image}`\n"
            f"- Text layout: `{layout_path}`\n\n"
            "The exported PPTX uses the no-text background as a locked full-slide image "
            "and editable PowerPoint text boxes on top. Visible text follows the "
            "AI-designed `display_text` layer and full-image text style profile from "
            "semantic understanding. Complete, readable expression is preserved when it "
            "fits the semantic safe area; revisions are for fit/readability failures.\n"
        ),
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    full_image = args.full.resolve()
    background_image = args.background.resolve()
    if not full_image.is_file():
        raise FileNotFoundError(f"Full image not found: {full_image}")
    if not background_image.is_file():
        raise FileNotFoundError(f"Background image not found: {background_image}")

    project_name = _project_name(args.name, full_image)
    projects_dir = args.projects_dir.resolve() if args.projects_dir else (Path.cwd() / "projects").resolve()
    project = Path(ProjectManager(projects_dir).init_project(project_name, "ppt169")).resolve()

    sources = project / "sources"
    images = project / "images"
    analysis = project / "analysis" / "dual_image_rebuild"
    svg_output = project / "svg_output"
    exports = project / "exports"
    for directory in (sources, images, analysis, svg_output, exports):
        directory.mkdir(parents=True, exist_ok=True)
    notes_dir = project / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(full_image, sources / full_image.name)
    shutil.copy2(background_image, sources / background_image.name)
    normalized_full = images / "P01_full_1280x720.png"
    normalized_background = images / "P01_background_1280x720.png"
    normalize_image(full_image, normalized_full)
    normalize_image(background_image, normalized_background)
    architecture_artifacts = run_architecture_intake(project, "images/P01_full_1280x720.png")

    if args.text_layout:
        raw_layout_path = args.text_layout.resolve()
        raw_layout = _read_json(raw_layout_path)
        shutil.copy2(raw_layout_path, sources / raw_layout_path.name)
    else:
        raw_layout_path = None
        raw_layout = {"image_size": {"width": _image_size(full_image)[0], "height": _image_size(full_image)[1]}, "items": []}
    layout = normalize_text_layout(raw_layout)
    if args.semantic_plan:
        semantic_plan_path = args.semantic_plan.resolve()
        semantic_plan = normalize_semantic_plan(_read_json(semantic_plan_path))
        shutil.copy2(semantic_plan_path, sources / semantic_plan_path.name)
    else:
        semantic_plan_path = None
        semantic_plan = None
    if semantic_plan is not None:
        semantic_preflight = validate_semantic_plan(semantic_plan)
    else:
        semantic_preflight = {
            "valid": True,
            "error_count": 0,
            "warning_count": 0,
            "issues": [],
            "skipped": True,
            "reason": "no_semantic_plan_diagnostic_mode",
        }
    semantic_preflight_path = analysis / "P01_semantic_plan_preflight.json"
    semantic_preflight_path.write_text(
        json.dumps(semantic_preflight, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if semantic_plan is not None and int(semantic_preflight.get("error_count", 0)) > 0:
        return {
            "valid": False,
            "project": str(project),
            "artifacts": {
                "normalized_full": str(normalized_full),
                "normalized_background": str(normalized_background),
                **architecture_artifacts,
                "semantic_plan_preflight": str(semantic_preflight_path),
            },
            "warnings": [issue["code"] for issue in semantic_preflight["issues"] if issue.get("severity") == "warning"],
            "semantic_plan_preflight_valid": False,
            "semantic_plan_preflight_error_count": int(semantic_preflight.get("error_count", 0)),
            "layout_qa_valid": False,
            "layout_qa_error_count": 0,
            "text_content_qa_valid": False,
            "production_ready": False,
            "production_readiness_error_count": int(semantic_preflight.get("error_count", 0)),
        }
    effective_layout = semantic_items_or_layout(semantic_plan, layout)
    text_style_profile = build_text_style_profile(effective_layout)
    text_style_profile_path = analysis / "P01_text_style_profile.json"
    text_style_profile_path.write_text(
        json.dumps(text_style_profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    effective_layout, safe_area_report = infer_semantic_containers_from_full_style(effective_layout)
    safe_area_report_path = analysis / "P01_safe_area_inference.json"
    safe_area_report_path.write_text(
        json.dumps(safe_area_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    effective_layout, framework_report, composition_contract = infer_visual_frameworks_from_containers(effective_layout)
    frameworks_path = analysis / "P01_frameworks.json"
    frameworks_path.write_text(
        json.dumps(framework_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    composition_contract_path = analysis / "P01_composition_contract.json"
    composition_contract_path.write_text(
        json.dumps(composition_contract, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    effective_layout, typesetting_report = apply_typesetting_policy(effective_layout)
    typesetting_report_path = analysis / "P01_typesetting_report.json"
    typesetting_report_path.write_text(
        json.dumps(typesetting_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    layout_plan = build_layout_plan(effective_layout)
    effective_layout = apply_layout_plan(effective_layout, layout_plan)
    layout_plan_path = analysis / "P01_layout_plan.json"
    layout_plan_path.write_text(json.dumps(layout_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    layout_path = analysis / "P01_text_layout_1280x720.json"
    layout_path.write_text(json.dumps(effective_layout, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if semantic_plan is not None:
        (analysis / "P01_semantic_plan.json").write_text(
            json.dumps(semantic_plan, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    geometry_from_semantics = semantic_plan_owns_geometry(semantic_plan)
    transform = (
        AlignmentTransform(model="semantic-container-geometry")
        if args.no_align or geometry_from_semantics
        else estimate_alignment(normalized_full, normalized_background, effective_layout)
    )
    boxes = build_overlay_boxes(
        effective_layout,
        normalized_background,
        transform,
        font_family=args.font_family,
        fill=args.fill,
    )
    layout_qa = build_layout_qa_report(layout_plan, boxes)
    layout_qa_path = analysis / "P01_layout_qa.json"
    layout_qa_path.write_text(json.dumps(layout_qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    notes_markdown = notes_from_semantic_plan(semantic_plan, boxes)
    notes_path = notes_dir / "01_dual_image_rebuild.md"
    notes_path.write_text(notes_markdown + "\n", encoding="utf-8")
    mapping_path = analysis / "P01_text_mapping.json"
    text_content_qa_path = analysis / "P01_text_content_qa.json"
    production_readiness_path = analysis / "P01_production_readiness.json"
    mapping_path.write_text(
        json.dumps(
            {
                "workflow": "dual-image-rebuild-ppt",
                "canvas": {"width": CANVAS[0], "height": CANVAS[1]},
                "text_display_policy": "ai_designed_display_text_from_semantics",
                "container_fit_policy": "container_first_safe_bbox_then_nudge_shrink_simplify",
                "alignment": asdict(transform),
                "geometry_source": "semantic_plan_containers" if geometry_from_semantics else "full_to_background_alignment",
                "semantic_plan": str(semantic_plan_path) if semantic_plan_path else None,
                "text_style_profile": str(text_style_profile_path),
                "semantic_plan_preflight": str(semantic_preflight_path),
                "safe_area_inference": str(safe_area_report_path),
                "visual_frameworks": str(frameworks_path),
                "composition_contract": str(composition_contract_path),
                "typesetting_policy": str(typesetting_report_path),
                "layout_plan": str(layout_plan_path),
                "layout_qa": str(layout_qa_path),
                "text_content_qa": str(text_content_qa_path),
                "production_readiness": str(production_readiness_path),
                "notes": str(notes_path),
                "boxes": [asdict(box) for box in boxes],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    svg_path = svg_output / "01_dual_image_rebuild.svg"
    svg_path.write_text(render_overlay_svg("../images/P01_background_1280x720.png", boxes), encoding="utf-8")
    pptx_path = exports / f"dual_image_rebuild_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
    export_pptx(normalized_background, boxes, pptx_path, notes_markdown=notes_markdown)
    text_content_qa = build_text_content_qa_report(boxes, pptx_path)
    text_content_qa_path.write_text(
        json.dumps(text_content_qa, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    production_readiness = build_production_readiness_report(
        semantic_plan=semantic_plan,
        safe_area_report=safe_area_report,
        layout_qa=layout_qa,
        text_content_qa=text_content_qa,
    )
    production_readiness_path.write_text(
        json.dumps(production_readiness, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        pdf_preview = build_pdf_preview(pptx_path, project / "qa_pdf", font_family=args.font_family)
    except Exception as exc:
        pdf_preview = {"valid": False, "warnings": [f"pdf_preview_failed:{exc}"]}
    _write_project_readme(project, full_image, background_image, raw_layout_path)

    warnings = [issue["code"] for issue in layout_qa["issues"] if issue.get("severity") == "warning"]
    warnings.extend(pdf_preview.get("warnings", []))
    if not text_content_qa.get("valid", False):
        warnings.append("pptx_text_content_mismatch")
    warnings.extend(issue["code"] for issue in production_readiness["issues"] if issue.get("severity") == "warning")
    if not boxes:
        warnings.append("No text boxes were provided. Pass --text-layout from OCR/vision analysis.")

    return {
        # "valid" reflects whether the pipeline ran to completion and produced a
        # PPTX. It intentionally does not fold in layout_qa's error/warning
        # findings — those are reported separately below so a caller can choose
        # whether unresolved QA errors should block acceptance (see
        # "layout_qa_valid" / "layout_qa_error_count", and main()'s exit code).
        "valid": True,
        "project": str(project),
        "artifacts": {
            "normalized_full": str(normalized_full),
            "normalized_background": str(normalized_background),
            **architecture_artifacts,
            "text_style_profile": str(text_style_profile_path),
            "semantic_plan_preflight": str(semantic_preflight_path),
            "safe_area_inference": str(safe_area_report_path),
            "visual_frameworks": str(frameworks_path),
            "composition_contract": str(composition_contract_path),
            "typesetting_report": str(typesetting_report_path),
            "layout_plan": str(layout_plan_path),
            "layout_qa": str(layout_qa_path),
            "text_content_qa": str(text_content_qa_path),
            "production_readiness": str(production_readiness_path),
            "text_layout": str(layout_path),
            "text_mapping": str(mapping_path),
            "notes": str(notes_path),
            "svg": str(svg_path),
            "pptx": str(pptx_path),
            "pdf_preview": pdf_preview,
        },
        "alignment": asdict(transform),
        "text_boxes": len(boxes),
        "warnings": warnings,
        "semantic_plan_preflight_valid": bool(semantic_preflight.get("valid", True)),
        "semantic_plan_preflight_error_count": int(semantic_preflight.get("error_count", 0)),
        "layout_qa_valid": bool(layout_qa.get("valid", True)),
        "layout_qa_error_count": int(layout_qa.get("error_count", 0)),
        "text_content_qa_valid": bool(text_content_qa.get("valid", False)),
        "production_ready": bool(production_readiness.get("valid", False)),
        "production_readiness_error_count": int(production_readiness.get("error_count", 0)),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="双图复刻ppt: full text image + no-text background image -> background + editable text PPTX.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--full", required=True, type=Path, help="Full reference image with text.")
    parser.add_argument("--background", required=True, type=Path, help="No-text background image.")
    parser.add_argument("--text-layout", type=Path, help="OCR/vision JSON for the full image.")
    parser.add_argument("--semantic-plan", type=Path, help="Semantic JSON with corrected text roles and speaker notes.")
    parser.add_argument("--name", help="Project name.")
    parser.add_argument("--projects-dir", type=Path, help="Projects directory (default: ./projects).")
    parser.add_argument("--font-family", default="Microsoft YaHei")
    parser.add_argument("--fill", default="#111827", help="Preferred text fill; may be adjusted for background contrast.")
    parser.add_argument("--no-align", action="store_true", help="Skip visual alignment; use normalized full-image coordinates directly.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # Exit code 1 is reserved for pipeline crashes (see except above). Exit code 3
    # signals a structurally successful run that still failed layout QA (hard
    # errors in P01_layout_qa.json), so CI/batch callers can gate on it without
    # parsing JSON. Exit code 0 means the pipeline ran and layout QA reported no
    # hard errors (warnings may still be present; they never block). Production
    # readiness additionally requires explicit semantic containers, so the
    # page012 auto-inference profile cannot accidentally become acceptance truth.
    if (
        not result.get("semantic_plan_preflight_valid", True)
        or not result.get("layout_qa_valid", True)
        or not result.get("text_content_qa_valid", True)
        or not result.get("production_ready", True)
    ):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
