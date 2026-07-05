#!/usr/bin/env python3
"""
Shared object-level reference vs preview similarity checks for slide-image rebuild.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

try:
    from render_preview_backend import ensure_preview_for_svg
except ImportError:  # pragma: no cover
    from scripts.render_preview_backend import ensure_preview_for_svg  # type: ignore

try:
    from svg_page_discovery import list_page_svg_candidates
except ImportError:  # pragma: no cover
    from scripts.svg_page_discovery import list_page_svg_candidates  # type: ignore

try:
    from PIL import Image, ImageChops, ImageStat
except ImportError:  # pragma: no cover
    Image = None  # type: ignore[misc, assignment]
    ImageChops = None  # type: ignore[misc, assignment]
    ImageStat = None  # type: ignore[misc, assignment]

DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
DEFAULT_BBOX_POSITION_PX = 3.0
DEFAULT_BBOX_SIZE_PX = 3.0
DEFAULT_ICON_POSITION_PX = 4.0
DEFAULT_ICON_SIZE_PX = 4.0
DEFAULT_ANCHOR_DRIFT_PX = 3.0
DEFAULT_ZONE_MEAN_FALLBACK = 62.0

ZONE_BANDS = (
    ("top", 0, 128),
    ("guidance", 128, 172),
    ("header", 172, 222),
    ("main", 222, 652),
    ("footer", 652, 720),
)
ZONE_THRESHOLDS = {
    "top": 70.0,
    "guidance": 82.0,
    "header": 88.0,
    "main": 62.0,
    "footer": 88.0,
}
WARNING_MARGIN = 10.0
FULL_SLIDE_RATIO = 0.9
REPORT_VERSION = "1.0"


@dataclass(frozen=True)
class Thresholds:
    bbox_position_px: float = DEFAULT_BBOX_POSITION_PX
    bbox_size_px: float = DEFAULT_BBOX_SIZE_PX
    icon_position_px: float = DEFAULT_ICON_POSITION_PX
    icon_size_px: float = DEFAULT_ICON_SIZE_PX
    anchor_drift_px: float = DEFAULT_ANCHOR_DRIFT_PX
    zone_mean_diff: float | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


try:  # shared helper; see scripts/json_io.py
    from json_io import load_json
except ImportError:  # pragma: no cover - package-context import
    from scripts.json_io import load_json  # type: ignore


def canvas_size(layout: dict[str, Any], *, width: int, height: int) -> tuple[int, int]:
    canvas = layout.get("canvas", {})
    if isinstance(canvas, dict):
        cw = canvas.get("width_px")
        ch = canvas.get("height_px")
        if isinstance(cw, (int, float)) and isinstance(ch, (int, float)):
            return int(cw), int(ch)
    return width, height


def resolve_bbox_px(item: dict[str, Any], canvas_w: int, canvas_h: int) -> tuple[float, float, float, float] | None:
    bbox = item.get("bbox_px")
    if isinstance(bbox, list) and len(bbox) >= 4:
        try:
            return tuple(float(bbox[index]) for index in range(4))  # type: ignore[return-value]
        except (TypeError, ValueError):
            pass
    ratios = item.get("bbox_ratio")
    if isinstance(ratios, list) and len(ratios) >= 4:
        try:
            return (
                float(ratios[0]) * canvas_w,
                float(ratios[1]) * canvas_h,
                float(ratios[2]) * canvas_w,
                float(ratios[3]) * canvas_h,
            )
        except (TypeError, ValueError):
            pass
    values = [item.get("x_ratio"), item.get("y_ratio"), item.get("w_ratio"), item.get("h_ratio")]
    if all(isinstance(value, (int, float)) for value in values):
        return (
            float(values[0]) * canvas_w,
            float(values[1]) * canvas_h,
            float(values[2]) * canvas_w,
            float(values[3]) * canvas_h,
        )
    bbox_field = item.get("bbox")
    if isinstance(bbox_field, list) and len(bbox_field) >= 4:
        try:
            return tuple(float(bbox_field[index]) for index in range(4))  # type: ignore[return-value]
        except (TypeError, ValueError):
            return None
    return None


def zone_band_name(y_center: float) -> str:
    for name, y0, y1 in ZONE_BANDS:
        if y0 <= y_center < y1:
            return name
    return "main"


def zone_mean_limit(bbox: tuple[float, float, float, float], thresholds: Thresholds) -> float:
    if thresholds.zone_mean_diff is not None:
        return thresholds.zone_mean_diff
    _x, y, _w, h = bbox
    return ZONE_THRESHOLDS.get(zone_band_name(y + h / 2.0), DEFAULT_ZONE_MEAN_FALLBACK)


def is_full_slide_bbox(bbox: tuple[float, float, float, float], canvas_w: int, canvas_h: int) -> bool:
    _x, _y, w, h = bbox
    return w >= canvas_w * FULL_SLIDE_RATIO and h >= canvas_h * FULL_SLIDE_RATIO


try:  # shared helper; see scripts/image_io.py
    from image_io import resize_rgb
except ImportError:  # pragma: no cover - package-context import
    from scripts.image_io import resize_rgb  # type: ignore


def crop_mean_diff(ref: Any, out: Any, bbox: tuple[float, float, float, float]) -> float | None:
    x, y, width, height = bbox
    left = max(0, int(round(x)))
    top = max(0, int(round(y)))
    right = min(ref.width, int(round(x + width)))
    bottom = min(ref.height, int(round(y + height)))
    if right - left < 2 or bottom - top < 2:
        return None
    ref_crop = ref.crop((left, top, right, bottom))
    out_crop = out.crop((left, top, right, bottom))
    return float(ImageStat.Stat(ImageChops.difference(ref_crop, out_crop)).mean[0])


def _edge_strength_at_row(image: Any, y: int) -> float:
    if y <= 0 or y >= image.height:
        return 0.0
    upper = image.crop((0, y - 1, image.width, y))
    lower = image.crop((0, y, image.width, y + 1))
    diff = ImageChops.difference(upper, lower)
    return float(sum(ImageStat.Stat(diff).mean) / 3)


def _nearest_edge_y(image: Any, expected_y: float, *, window: int = 14) -> tuple[int, float]:
    expected = int(round(expected_y))
    y0 = max(1, expected - window)
    y1 = min(image.height - 1, expected + window)
    best_y = expected
    best_strength = 0.0
    for y in range(y0, y1 + 1):
        strength = _edge_strength_at_row(image, y)
        if strength > best_strength:
            best_y = y
            best_strength = strength
    return best_y, best_strength


def _anchor_edges(layout: dict[str, Any], *, height: int) -> list[dict[str, Any]]:
    anchors = layout.get("visual_anchors", [])
    if not isinstance(anchors, list):
        return []
    canvas = layout.get("canvas", {})
    canvas_w = int(canvas.get("width_px") or DEFAULT_WIDTH) if isinstance(canvas, dict) else DEFAULT_WIDTH
    canvas_h = float(canvas.get("height_px") or height) if isinstance(canvas, dict) else float(height)
    y_scale = height / canvas_h if canvas_h else 1.0
    edges: list[dict[str, Any]] = []
    for anchor in anchors:
        if not isinstance(anchor, dict):
            continue
        anchor_id = str(anchor.get("id") or f"anchor_{len(edges) + 1}")
        anchor_type = anchor.get("type")
        if anchor_type == "horizontal_edge" and isinstance(anchor.get("y"), (int, float)):
            edges.append({
                "id": anchor_id,
                "type": "anchor",
                "expected_y": float(anchor["y"]) * y_scale,
            })
        elif anchor_type == "band":
            bbox = resolve_bbox_px(anchor, canvas_w, int(canvas_h))
            if bbox is not None:
                edges.append({"id": f"{anchor_id}.band", "type": "anchor_band", "bbox_px": bbox})
            bbox_raw = anchor.get("bbox_px")
            if isinstance(bbox_raw, list) and len(bbox_raw) == 4 and all(isinstance(item, (int, float)) for item in bbox_raw):
                top = float(bbox_raw[1]) * y_scale
                bottom = float(bbox_raw[1] + bbox_raw[3]) * y_scale
                edges.append({"id": f"{anchor_id}.top", "type": "anchor", "expected_y": top})
                edges.append({"id": f"{anchor_id}.bottom", "type": "anchor", "expected_y": bottom})
    return edges


def _layout_confidence(layout: dict[str, Any], key: str, default: float = 1.0) -> float:
    confidence = layout.get("confidence", {})
    if isinstance(confidence, dict):
        value = confidence.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    classifier = layout.get("page_type_classifier", {})
    if isinstance(classifier, dict):
        value = classifier.get("confidence")
        if isinstance(value, (int, float)):
            return float(value)
    return default


def _object_type(zone: dict[str, Any]) -> str:
    role = str(zone.get("role", "")).lower()
    component = str(zone.get("component", "")).lower()
    zone_id = str(zone.get("id", "")).lower()
    if "footer" in role or "footer" in zone_id or "bottom" in zone_id:
        return "footer_bar"
    if "card" in role or "card" in component or "card" in zone_id:
        return "card"
    return "zone"


def _failure_action(issue_code: str, obj_type: str) -> str:
    actions = {
        "ZONE_MEAN_DIFF_HIGH": "Adjust SVG geometry/colors inside the declared zone bbox to match the reference.",
        "ANCHOR_DRIFT": "Re-align the visual anchor edge to the reference y position.",
        "ICON_SHAPE_SIMPLIFIED": "Replace the simplified icon with a semantic vector matching the reference slot.",
        "ICON_NOT_VISIBLE": "Ensure data-icon-id is present and the icon slot contains visible non-background pixels.",
        "BBOX_TOO_SMALL": "Expand or correct the declared bbox in layout_reference.json before re-checking.",
    }
    if obj_type == "footer_bar" and issue_code == "ZONE_MEAN_DIFF_HIGH":
        return "Restore footer bar geometry (x, y, w, h, rx, ry) and fill/stroke to match the reference."
    return actions.get(issue_code, "Review the object in SVG against the reference image.")


def collect_objects(
    layout: dict[str, Any],
    *,
    icon_manifest: dict[str, Any] | None = None,
    text_region_map: dict[str, Any] | None = None,
    page_id: str | None = None,
) -> list[dict[str, Any]]:
    canvas_w, canvas_h = canvas_size(layout, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT)
    objects: list[dict[str, Any]] = []

    zones = layout.get("zones", [])
    if isinstance(zones, list):
        for zone in zones:
            if not isinstance(zone, dict):
                continue
            zone_id = str(zone.get("id", "")).strip()
            if not zone_id:
                continue
            bbox = resolve_bbox_px(zone, canvas_w, canvas_h)
            if bbox is None or bbox[2] < 8 or bbox[3] < 8:
                continue
            if is_full_slide_bbox(bbox, canvas_w, canvas_h):
                continue
            objects.append({
                "id": zone_id,
                "type": _object_type(zone),
                "source": "layout_reference.zones",
                "bbox_px": [round(value, 2) for value in bbox],
                "confidence": _layout_confidence(layout, "layout_type"),
            })

    icon_entries: list[dict[str, Any]] = []
    if icon_manifest:
        pages = icon_manifest.get("pages")
        if isinstance(pages, list):
            for page in pages:
                if not isinstance(page, dict):
                    continue
                if page_id and str(page.get("page_id", "")) not in {page_id, ""}:
                    continue
                icons = page.get("icons", [])
                if isinstance(icons, list):
                    icon_entries.extend(item for item in icons if isinstance(item, dict))
        elif isinstance(icon_manifest.get("icons"), list):
            icon_entries.extend(item for item in icon_manifest["icons"] if isinstance(item, dict))

    icons_layout = layout.get("icon_reconstruction", {})
    if isinstance(icons_layout, dict) and isinstance(icons_layout.get("icons"), list):
        seen = {str(item.get("id", "")) for item in icon_entries}
        for item in icons_layout["icons"]:
            if isinstance(item, dict) and str(item.get("id", "")) not in seen:
                icon_entries.append(item)

    for icon in icon_entries:
        icon_id = str(icon.get("id", "")).strip()
        if not icon_id:
            continue
        bbox = resolve_bbox_px(icon, canvas_w, canvas_h)
        if bbox is None:
            continue
        objects.append({
            "id": icon_id,
            "type": "icon",
            "source": "icon_manifest.icons",
            "bbox_px": [round(value, 2) for value in bbox],
            "required": icon.get("required", True) is not False,
            "confidence": 1.0,
        })

    if text_region_map:
        pages = text_region_map.get("pages")
        regions: list[dict[str, Any]] = []
        if isinstance(pages, list):
            for page in pages:
                if not isinstance(page, dict):
                    continue
                if page_id and str(page.get("page_id", "")) not in {page_id, ""}:
                    continue
                page_regions = page.get("regions", [])
                if isinstance(page_regions, list):
                    regions.extend(item for item in page_regions if isinstance(item, dict))
        elif isinstance(text_region_map.get("regions"), list):
            regions.extend(item for item in text_region_map["regions"] if isinstance(item, dict))
        for region in regions:
            region_id = str(region.get("id", "")).strip()
            if not region_id:
                continue
            bbox = resolve_bbox_px(region, canvas_w, canvas_h)
            if bbox is None:
                continue
            objects.append({
                "id": region_id,
                "type": "text_region",
                "source": "text_region_map.regions",
                "bbox_px": [round(value, 2) for value in bbox],
                "confidence": _layout_confidence(layout, "text_regions"),
            })

    for edge in _anchor_edges(layout, height=canvas_h):
        if edge.get("type") == "anchor_band" and isinstance(edge.get("bbox_px"), tuple):
            bbox = edge["bbox_px"]
            objects.append({
                "id": str(edge["id"]),
                "type": "anchor",
                "source": "layout_reference.visual_anchors",
                "bbox_px": [round(value, 2) for value in bbox],
                "confidence": _layout_confidence(layout, "layout_type"),
            })

    return objects


def compare_objects_for_page(
    *,
    reference: Path,
    preview: Path,
    layout: dict[str, Any],
    icon_manifest: dict[str, Any] | None = None,
    text_region_map: dict[str, Any] | None = None,
    page_id: str | None = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    thresholds: Thresholds | None = None,
) -> dict[str, Any]:
    if Image is None:
        raise RuntimeError("Pillow is required for object similarity checks.")

    limits = thresholds or Thresholds()
    size = (width, height)
    ref_img = resize_rgb(reference, size)
    out_img = resize_rgb(preview, size)

    specs = collect_objects(
        layout,
        icon_manifest=icon_manifest,
        text_region_map=text_region_map,
        page_id=page_id,
    )

    checked: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for spec in specs:
        bbox_values = spec.get("bbox_px", [])
        if not isinstance(bbox_values, list) or len(bbox_values) < 4:
            continue
        bbox = tuple(float(value) for value in bbox_values[:4])
        mean_diff = crop_mean_diff(ref_img, out_img, bbox)
        item = {
            "id": spec["id"],
            "type": spec["type"],
            "source": spec.get("source", ""),
            "reference_bbox_px": [round(value, 2) for value in bbox],
            "candidate_bbox_px": [round(value, 2) for value in bbox],
            "metrics": {"zone_mean_diff": round(mean_diff, 2) if mean_diff is not None else None},
            "confidence": spec.get("confidence", 1.0),
            "valid": True,
            "issues": [],
        }
        if mean_diff is None:
            failure = {
                "id": spec["id"],
                "type": spec["type"],
                "issue": "bbox_unmeasurable",
                "issue_code": "BBOX_TOO_SMALL",
                "message": f"Object `{spec['id']}` bbox is too small to measure.",
                "reference_bbox_px": item["reference_bbox_px"],
                "candidate_bbox_px": item["reference_bbox_px"],
                "tier": "warning",
                "action": _failure_action("BBOX_TOO_SMALL", spec["type"]),
            }
            warnings.append(failure)
            item["valid"] = False
            item["issues"].append("BBOX_TOO_SMALL")
            checked.append(item)
            continue

        limit = zone_mean_limit(bbox, limits)
        warn_limit = max(0.0, limit - WARNING_MARGIN)
        confidence = float(spec.get("confidence", 1.0))
        tier = "blocking" if confidence >= 0.7 else "warning"
        obj_type = str(spec.get("type", "zone"))
        if obj_type == "icon":
            issue_code = "ICON_NOT_VISIBLE" if mean_diff > 78 else "ICON_SHAPE_SIMPLIFIED"
        else:
            issue_code = "ZONE_MEAN_DIFF_HIGH"

        if mean_diff > limit:
            failure = {
                "id": spec["id"],
                "type": obj_type,
                "issue": issue_code.lower(),
                "issue_code": issue_code,
                "message": f"Object `{spec['id']}` mean diff {mean_diff:.1f} exceeds {limit:.1f}.",
                "reference_bbox_px": item["reference_bbox_px"],
                "candidate_bbox_px": item["candidate_bbox_px"],
                "metrics": {"zone_mean_diff": round(mean_diff, 2), "threshold": limit},
                "tier": tier,
                "action": _failure_action(issue_code, obj_type),
            }
            item["valid"] = False
            item["issues"].append(issue_code)
            if tier == "blocking":
                failures.append(failure)
            else:
                warnings.append(failure)
        elif mean_diff > warn_limit:
            warnings.append({
                "id": spec["id"],
                "type": obj_type,
                "issue_code": issue_code,
                "message": f"Object `{spec['id']}` mean diff {mean_diff:.1f} is within warning band ({warn_limit:.1f}-{limit:.1f}).",
                "reference_bbox_px": item["reference_bbox_px"],
                "metrics": {"zone_mean_diff": round(mean_diff, 2), "threshold": limit},
                "tier": "warning",
                "action": _failure_action(issue_code, obj_type),
            })
        checked.append(item)

    for edge in _anchor_edges(layout, height=height):
        expected_y = edge.get("expected_y")
        if not isinstance(expected_y, (int, float)):
            continue
        ref_y, ref_strength = _nearest_edge_y(ref_img, float(expected_y))
        out_y, out_strength = _nearest_edge_y(out_img, float(expected_y))
        if ref_strength < 2.0 and out_strength < 2.0:
            continue
        delta = out_y - ref_y
        anchor_item = {
            "id": edge["id"],
            "type": "anchor",
            "source": "layout_reference.visual_anchors",
            "metrics": {
                "anchor_drift_px": delta,
                "reference_y": ref_y,
                "candidate_y": out_y,
            },
            "valid": abs(delta) <= limits.anchor_drift_px,
            "issues": [],
        }
        checked.append(anchor_item)
        if abs(delta) > limits.anchor_drift_px:
            failure = {
                "id": edge["id"],
                "type": "anchor",
                "issue": "anchor_drift",
                "issue_code": "ANCHOR_DRIFT",
                "message": f"Anchor `{edge['id']}` drift {delta}px exceeds {limits.anchor_drift_px:.1f}px.",
                "metrics": anchor_item["metrics"],
                "tier": "blocking",
                "action": _failure_action("ANCHOR_DRIFT", "anchor"),
            }
            failures.append(failure)
            anchor_item["valid"] = False
            anchor_item["issues"].append("ANCHOR_DRIFT")

    return {
        "valid": not failures,
        "reference": str(reference),
        "preview": str(preview),
        "objects_checked": len(checked),
        "objects_failed": len(failures),
        "objects_warned": len(warnings),
        "objects": checked,
        "failures": failures,
        "warnings": warnings,
    }


def _find_reference_image(project: Path) -> Path | None:
    layout = load_json(project / "layout_reference.json")
    source = layout.get("source_reference", {}) if isinstance(layout, dict) else {}
    if isinstance(source, dict):
        raw = source.get("path", "")
        if raw:
            candidate = project / str(raw)
            if candidate.is_file():
                return candidate
    images = project / "images"
    if images.is_dir():
        for pattern in ("reference_layout.*", "reference.*", "*reference*layout*"):
            for path in sorted(images.glob(pattern)):
                if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                    return path
    return None


def _resolve_path(base: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def _page_dir(project: Path, page: dict[str, Any]) -> Path:
    for key in ["project_path", "page_project", "page_dir"]:
        resolved = _resolve_path(project, page.get(key))
        if resolved is not None:
            return resolved
    page_id = str(page.get("page_id", ""))
    candidate = project / "pages" / page_id
    return candidate if candidate.is_dir() else project


def _preview_path(project: Path, svg: Path) -> Path:
    return project / "exports" / "preview_qa" / f"{svg.stem}.preview.png"


def _render_preview(
    project: Path,
    svg: Path,
    out: Path,
    width: int,
    height: int,
    *,
    render_backend: str = "cairo",
    hard_gate: bool = False,
) -> Path:
    result = ensure_preview_for_svg(
        project,
        svg,
        out,
        render=True,
        render_backend=render_backend,
        hard_gate=hard_gate,
        width=width,
        height=height,
    )
    if not result.ok:
        raise RuntimeError("; ".join(result.errors) or "preview render failed")
    return out


def verify_project(
    project: Path,
    *,
    render: bool = False,
    render_backend: str = "cairo",
    hard_gate: bool = False,
    thresholds: Thresholds | None = None,
    write_report: bool = False,
    report_path: Path | None = None,
) -> dict[str, Any]:
    manifest = load_json(project / "slide_image_rebuild_manifest.json")
    pages = manifest.get("pages", []) if isinstance(manifest, dict) else []
    icon_manifest = load_json(project / "icon_manifest.json") or None
    text_region_map = load_json(project / "text_region_map.json") or None
    limits = thresholds or Thresholds()

    page_payloads: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []

    page_items = pages if isinstance(pages, list) and pages else [{"page_id": "01", "page_dir": "."}]

    for page in page_items:
        if not isinstance(page, dict):
            continue
        page_id = str(page.get("page_id", "")).strip() or "01"
        page_dir = _page_dir(project, page)
        reference = _resolve_path(project, page.get("reference_image")) or _find_reference_image(page_dir)
        layout_path = page_dir / "layout_reference.json"
        if not layout_path.is_file():
            layout_path = project / "layout_reference.json"
        layout = load_json(layout_path)
        svgs = list_page_svg_candidates(project, page_id, page_dir=page_dir)
        if reference is None or not reference.is_file():
            errors.append(f"Reference image missing for page `{page_id}`.")
            continue
        if not svgs:
            errors.append(f"No SVG found for page `{page_id}`.")
            continue
        svg = svgs[0]
        preview_root = page_dir if page_dir.is_dir() else project
        preview = _preview_path(preview_root, svg)
        stale = preview.is_file() and preview.stat().st_mtime < svg.stat().st_mtime
        if not preview.is_file() or (render and stale):
            if render:
                _render_preview(
                    preview_root,
                    svg,
                    preview,
                    DEFAULT_WIDTH,
                    DEFAULT_HEIGHT,
                    render_backend=render_backend,
                    hard_gate=hard_gate,
                )
            else:
                errors.append(f"Preview PNG missing or stale for page `{page_id}`; pass --render.")
                continue
        page_result = compare_objects_for_page(
            reference=reference,
            preview=preview,
            layout=layout,
            icon_manifest=icon_manifest,
            text_region_map=text_region_map,
            page_id=page_id,
            thresholds=limits,
        )
        page_result["page_id"] = page_id
        page_result["layout_reference"] = str(layout_path)
        page_result["svg"] = str(svg)
        page_payloads.append(page_result)
        if not page_result.get("valid"):
            for failure in page_result.get("failures", []):
                if isinstance(failure, dict):
                    errors.append(str(failure.get("message", failure)))
        for warning in page_result.get("warnings", []):
            if isinstance(warning, dict):
                warnings.append(str(warning.get("message", warning)))

    payload = {
        "version": REPORT_VERSION,
        "workflow": "slide-image-rebuild",
        "check": "reference_object_similarity",
        "generated_at": utc_now(),
        "project": str(project),
        "valid": not errors,
        "render": {
            "backend": render_backend if render else "existing_preview",
            "requested": render,
        },
        "thresholds": {
            "bbox_position_px": limits.bbox_position_px,
            "bbox_size_px": limits.bbox_size_px,
            "icon_position_px": limits.icon_position_px,
            "icon_size_px": limits.icon_size_px,
            "anchor_drift_px": limits.anchor_drift_px,
            "zone_mean_diff": limits.zone_mean_diff,
            "zone_band_thresholds": ZONE_THRESHOLDS,
        },
        "summary": {
            "page_count": len(page_payloads),
            "objects_checked": sum(item.get("objects_checked", 0) for item in page_payloads),
            "objects_failed": sum(item.get("objects_failed", 0) for item in page_payloads),
            "objects_warned": sum(item.get("objects_warned", 0) for item in page_payloads),
            "blocking_failure_count": sum(len(item.get("failures", [])) for item in page_payloads),
        },
        "pages": page_payloads,
        "errors": errors,
        "warnings": warnings,
    }
    if payload["summary"]["objects_checked"] == 0 and not errors:
        payload["valid"] = False
        payload["errors"] = ["No measurable objects found; add layout_reference.zones, icon_manifest icons, or text_region_map regions."]

    if write_report:
        out = report_path or project / "exports" / "qa" / "object_similarity_report.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["report_path"] = str(out.relative_to(project)) if out.is_relative_to(project) else str(out)
    return payload


def summarize_for_similarity(payload: dict[str, Any]) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    for page in payload.get("pages", []):
        if not isinstance(page, dict):
            continue
        for failure in page.get("failures", []):
            if isinstance(failure, dict):
                failures.append({
                    "id": failure.get("id"),
                    "issue_code": failure.get("issue_code"),
                    "message": failure.get("message"),
                    "page_id": page.get("page_id"),
                })
    return {
        "valid": payload.get("valid", False),
        "report_path": payload.get("report_path", ""),
        "checked": payload.get("summary", {}).get("objects_checked", 0),
        "failed": payload.get("summary", {}).get("objects_failed", 0),
        "failures": failures,
    }
