#!/usr/bin/env python3
"""
PPT Master - Image Crops Manifest Builder

Scan rebuilt SVG pages for embedded image regions and write a lightweight
image_crops_manifest.json for text-bearing image review.

Usage:
    python3 scripts/build_image_crops_manifest.py <project_path> [--source output] [--mode auto]

Examples:
    python3 scripts/build_image_crops_manifest.py projects/demo
    python3 scripts/build_image_crops_manifest.py projects/demo --source final --mode full-editable

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

SVG_NS = "{http://www.w3.org/2000/svg}"
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"

FULL_SLIDE_RATIO = 0.88
LARGE_IMAGE_RATIO = 0.35

MODE_POLICIES = {
    "vector-hifi": {
        "editability_priority": "structure_fidelity",
        "crop_policy": "decorative_only_crop_vector_main_structure",
    },
    "text-editable-snapshot": {
        "editability_priority": "temporary_text_editing",
        "crop_policy": "snapshot_underlay_requires_user_acceptance",
    },
    "full-editable": {
        "editability_priority": "maximum_editability",
        "crop_policy": "vector_first_decorative_exceptions_only",
    },
    "hifi": {
        "editability_priority": "structure_fidelity",
        "crop_policy": "legacy_alias_for_vector_hifi",
    },
    "editable": {
        "editability_priority": "maximum_editability",
        "crop_policy": "legacy_alias_for_full_editable",
    },
    "wps-hifi": {
        "editability_priority": "visual_fidelity_wps",
        "crop_policy": "decorative_only_crop_vector_main_structure_wps_safe",
    },
}


def _effective_mode(project: Path, mode: str) -> str:
    if mode != "auto":
        return mode
    manifest = _load_json(project / "slide_image_rebuild_manifest.json")
    rebuild_mode = str(manifest.get("rebuild_mode", "")).strip()
    return rebuild_mode if rebuild_mode in MODE_POLICIES else "vector-hifi"


def _strip_ns(tag: str) -> str:
    return tag.replace(SVG_NS, "")


def _float(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    raw = value.strip()
    if raw.endswith("%"):
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _viewbox(root: ET.Element) -> tuple[float, float, float, float]:
    raw = root.get("viewBox") or root.get("viewbox")
    if raw:
        parts = [part for part in raw.replace(",", " ").split() if part]
        if len(parts) == 4:
            try:
                return tuple(float(part) for part in parts)  # type: ignore[return-value]
            except ValueError:
                pass
    width = _float(root.get("width"), 1280)
    height = _float(root.get("height"), 720)
    return 0.0, 0.0, width, height


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _existing_annotations(path: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    payload = _load_json(path)
    annotations: dict[tuple[str, str, str], dict[str, Any]] = {}
    for crop in payload.get("crops", []) if isinstance(payload, dict) else []:
        if not isinstance(crop, dict):
            continue
        key = (
            str(crop.get("page_id", "")),
            str(crop.get("href", "")),
            str(crop.get("svg_element_id", "")),
        )
        annotations[key] = {
            "contains_text": crop.get("contains_text"),
            "text_removed": crop.get("text_removed", False),
            "treatment": crop.get("treatment", ""),
            "reason": crop.get("reason", ""),
            "text_region_ids": crop.get("text_region_ids", []),
        }
    return annotations


def _source_kind(href: str, resolved: Path | None) -> str:
    blob = f"{href} {resolved or ''}".lower()
    if "reference_with_text" in blob:
        return "reference_with_text"
    if "reference_layout" in blob or "reference_pages" in blob or "reference." in blob:
        return "reference_image"
    if "/clean/" in blob or "\\clean\\" in blob or "_clean" in blob:
        return "clean_visual"
    if "crop_" in blob:
        return "crop"
    return "asset"


def _risk_flags(source_kind: str, area_ratio: float) -> list[str]:
    flags: list[str] = []
    if source_kind in {"reference_with_text", "reference_image"}:
        flags.append("source_reference_image")
    if area_ratio >= FULL_SLIDE_RATIO:
        flags.append("near_full_slide_image")
    elif area_ratio >= LARGE_IMAGE_RATIO:
        flags.append("large_image_region")
    return flags


def _recommended_treatment(source_kind: str, area_ratio: float, mode: str) -> str:
    if area_ratio >= FULL_SLIDE_RATIO:
        if mode == "text-editable-snapshot":
            return "snapshot_underlay_requires_user_acceptance"
        return "forbidden_full_slide_image"
    if source_kind in {"reference_with_text", "reference_image"}:
        return "remove_text_then_embed_background"
    if mode in {"vector-hifi", "hifi", "full-editable", "editable", "wps-hifi"} and area_ratio >= LARGE_IMAGE_RATIO:
        return "vector_rebuild_or_declared_crop_exception"
    if source_kind in {"clean_visual", "crop", "asset"}:
        return "local_crop_allowed"
    return "review"


def _resolve_href(svg_path: Path, href: str) -> Path | None:
    if not href or href.startswith("data:") or "://" in href:
        return None
    return (svg_path.parent / href).resolve()


def _scan_svg(
    svg_path: Path,
    project: Path,
    annotations: dict[tuple[str, str, str], dict[str, Any]],
    *,
    mode: str,
) -> list[dict[str, Any]]:
    try:
        root = ET.parse(svg_path).getroot()
    except ET.ParseError as exc:
        print(f"Warning: could not parse SVG {svg_path}: {exc}", file=sys.stderr)
        return []

    _, _, canvas_w, canvas_h = _viewbox(root)
    canvas_area = max(canvas_w * canvas_h, 1.0)
    page_id = svg_path.stem
    crops: list[dict[str, Any]] = []

    image_index = 0
    for elem in root.iter():
        if _strip_ns(elem.tag) != "image":
            continue
        image_index += 1
        href = elem.get("href") or elem.get(XLINK_HREF) or ""
        elem_id = elem.get("id") or elem.get("data-crop-id") or f"image_{image_index:02d}"
        crop_role = (
            elem.get("data-crop-role")
            or elem.get("data-crop-purpose")
            or elem.get("data-role")
            or ""
        )
        x = _float(elem.get("x"))
        y = _float(elem.get("y"))
        width = _float(elem.get("width"))
        height = _float(elem.get("height"))
        area_ratio = round((width * height) / canvas_area, 4)
        resolved = _resolve_href(svg_path, href)
        source_kind = _source_kind(href, resolved)
        key = (page_id, href, elem_id)
        carried = annotations.get(key, {})
        crop_id = elem.get("data-crop-id") or f"{page_id}_{elem_id}"
        crop = {
            "id": crop_id,
            "page_id": page_id,
            "used_in_svg": str(svg_path.relative_to(project)) if svg_path.is_relative_to(project) else str(svg_path),
            "svg_element_id": elem_id,
            "href": href,
            "resolved_path": str(resolved) if resolved else "",
            "bbox": [round(x, 2), round(y, 2), round(width, 2), round(height, 2)],
            "area_ratio": area_ratio,
            "crop_role": crop_role,
            "source_kind": source_kind,
            "risk_flags": _risk_flags(source_kind, area_ratio),
            "recommended_treatment": _recommended_treatment(source_kind, area_ratio, mode),
            "contains_text": carried.get("contains_text"),
            "text_removed": carried.get("text_removed", False),
            "treatment": carried.get("treatment", ""),
            "reason": carried.get("reason", ""),
            "text_region_ids": carried.get("text_region_ids", []),
        }
        crops.append(crop)
    return crops


def _svg_files(project: Path, source: str) -> list[Path]:
    if source == "final":
        return sorted((project / "svg_final").glob("*.svg"))
    if source == "output":
        return sorted((project / "svg_output").glob("*.svg"))
    return sorted((project / "svg_final").glob("*.svg")) or sorted((project / "svg_output").glob("*.svg"))


def build_manifest(project: Path, *, source: str = "auto", mode: str = "auto") -> dict[str, Any]:
    manifest_path = project / "image_crops_manifest.json"
    slide_manifest = _load_json(project / "slide_image_rebuild_manifest.json")
    effective_mode = _effective_mode(project, mode)
    annotations = _existing_annotations(manifest_path)
    crops: list[dict[str, Any]] = []
    for svg_path in _svg_files(project, source):
        crops.extend(_scan_svg(svg_path, project, annotations, mode=effective_mode))
    policy = MODE_POLICIES[effective_mode]
    return {
        "workflow": "slide-image-rebuild",
        "version": "1.0",
        "generated_by": "build_image_crops_manifest.py",
        "rebuild_mode": effective_mode,
        "pptx_export_mode": slide_manifest.get("pptx_export_mode", ""),
        "editability_priority": policy["editability_priority"],
        "crop_policy": policy["crop_policy"],
        "source": source,
        "project": str(project),
        "crops": crops,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build image_crops_manifest.json from SVG image elements.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", help="Project directory containing svg_output/ or svg_final/")
    parser.add_argument(
        "--source",
        choices=["auto", "output", "final"],
        default="auto",
        help="SVG directory to scan (default: auto prefers svg_final, then svg_output)",
    )
    parser.add_argument(
        "--output",
        help="Manifest path (default: <project_path>/image_crops_manifest.json)",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", *sorted(MODE_POLICIES.keys())],
        default="auto",
        help="Rebuild mode controlling crop-policy metadata (default: auto reads slide_image_rebuild_manifest.json, then vector-hifi)",
    )
    parser.add_argument("--json", action="store_true", help="Print the generated manifest to stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project = Path(args.project_path).resolve()
    if not project.is_dir():
        print(f"Project directory not found: {project}", file=sys.stderr)
        return 1

    manifest = build_manifest(project, source=args.source, mode=args.mode)
    output = Path(args.output).resolve() if args.output else project / "image_crops_manifest.json"
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote {output}", file=sys.stderr)
        print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
