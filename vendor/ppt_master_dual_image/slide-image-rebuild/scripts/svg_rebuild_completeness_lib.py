#!/usr/bin/env python3
"""
SVG rebuild completeness checks for slide-image rebuild projects.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from svg_page_discovery import find_page_svg

SVG_NS = "{http://www.w3.org/2000/svg}"
FULL_SLIDE_RATIO = 0.9
REPORT_VERSION = "1.0"


try:  # shared helper; see scripts/json_io.py
    from json_io import load_json
except ImportError:  # pragma: no cover - package-context import
    from scripts.json_io import load_json  # type: ignore

try:
    from rebuild_quality_mode import resolve_rebuild_modes
except ImportError:  # pragma: no cover - package-context import
    from scripts.rebuild_quality_mode import resolve_rebuild_modes  # type: ignore


def _is_snapshot_mode(project: Path) -> bool:
    """text-editable-snapshot has no vector structure (no arrows/connectors to
    mark, the full-slide background is the approved underlay) -- detect it from
    the project manifest so completeness checks built for vector-hifi don't
    fire on a mode that was never supposed to satisfy them."""
    manifest_path = project / "slide_image_rebuild_manifest.json"
    if not manifest_path.is_file():
        return False
    manifest = load_json(manifest_path)
    resolved = resolve_rebuild_modes(manifest)
    rebuild_mode = resolved.rebuild_mode or manifest.get("rebuild_mode")
    return rebuild_mode == "text-editable-snapshot"


def _strip_ns(tag: str) -> str:
    return tag.replace(SVG_NS, "")


def _float(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.match(r"\s*(-?\d+(?:\.\d+)?)", value)
    return float(match.group(1)) if match else None


def _viewbox(root: ET.Element) -> tuple[float, float, float, float]:
    raw = root.get("viewBox") or root.get("viewbox")
    if raw:
        parts = [float(part) for part in re.split(r"[\s,]+", raw.strip()) if part]
        if len(parts) == 4:
            return parts[0], parts[1], parts[2], parts[3]
    return 0, 0, _float(root.get("width")) or 1280, _float(root.get("height")) or 720


def _layout_paths(project: Path) -> list[tuple[str, Path]]:
    manifest = load_json(project / "slide_image_rebuild_manifest.json")
    pages = manifest.get("pages", []) if isinstance(manifest, dict) else []
    out: list[tuple[str, Path]] = []
    if isinstance(pages, list) and pages:
        for page in pages:
            if not isinstance(page, dict):
                continue
            page_id = str(page.get("page_id", "")).strip() or "01"
            page_dir = project / "pages" / page_id
            layout_path = page_dir / "layout_reference.json"
            if layout_path.is_file():
                out.append((page_id, layout_path))
        if out:
            return out
    root_layout = project / "layout_reference.json"
    if root_layout.is_file():
        return [("01", root_layout)]
    return []


def _collect_markers(svg_path: Path) -> dict[str, set[str]]:
    root = ET.parse(svg_path).getroot()
    zones: set[str] = set()
    icons: set[str] = set()
    text_regions: set[str] = set()
    connectors: set[str] = set()
    images: list[tuple[float, float, float, float]] = []
    element_count = 0
    _vx, _vy, vw, vh = _viewbox(root)
    for elem in root.iter():
        element_count += 1
        tag = _strip_ns(elem.tag)
        zone_id = elem.get("data-zone-id")
        if zone_id:
            zones.add(zone_id)
        icon_id = elem.get("data-icon-id")
        if icon_id:
            icons.add(icon_id)
        region_id = elem.get("data-text-region-id") or elem.get("data-region-id")
        if region_id and tag == "text":
            text_regions.add(region_id)
        connector_id = elem.get("data-chain-connector")
        if connector_id:
            connectors.add(connector_id)
        if tag == "image":
            x = _float(elem.get("x")) or 0
            y = _float(elem.get("y")) or 0
            width = _float(elem.get("width")) or 0
            height = _float(elem.get("height")) or 0
            images.append((x, y, width, height))
    return {
        "zones": zones,
        "icons": icons,
        "text_regions": text_regions,
        "connectors": connectors,
        "images": images,
        "element_count": element_count,
        "canvas": (vw, vh),
    }


def _regions_for_page(project: Path, page_id: str) -> list[dict[str, Any]]:
    text_map = load_json(project / "text_region_map.json")
    pages = text_map.get("pages")
    if isinstance(pages, list):
        for page in pages:
            if isinstance(page, dict) and str(page.get("page_id", "")) in {page_id, ""}:
                regions = page.get("regions", [])
                return [item for item in regions if isinstance(item, dict)] if isinstance(regions, list) else []
    regions = text_map.get("regions", [])
    return [item for item in regions if isinstance(item, dict)] if isinstance(regions, list) else []


def _icon_ids(project: Path, page_id: str) -> list[str]:
    manifest = load_json(project / "icon_manifest.json")
    pages = manifest.get("pages")
    ids: list[str] = []
    if isinstance(pages, list):
        for page in pages:
            if not isinstance(page, dict):
                continue
            if str(page.get("page_id", "")) not in {page_id, ""}:
                continue
            icons = page.get("icons", [])
            if isinstance(icons, list):
                for item in icons:
                    if isinstance(item, dict) and item.get("required", True) is not False:
                        icon_id = str(item.get("id", "")).strip()
                        if icon_id:
                            ids.append(icon_id)
    elif isinstance(manifest.get("icons"), list):
        for item in manifest["icons"]:
            if isinstance(item, dict) and item.get("required", True) is not False:
                icon_id = str(item.get("id", "")).strip()
                if icon_id:
                    ids.append(icon_id)
    return ids


def inspect_page(
    *,
    layout: dict[str, Any],
    svg_path: Path,
    text_regions: list[dict[str, Any]],
    required_icons: list[str],
    strict: bool,
    snapshot_mode: bool = False,
) -> dict[str, Any]:
    markers = _collect_markers(svg_path)
    vw, vh = markers["canvas"]
    missing_zones: list[str] = []
    missing_icons: list[str] = []
    missing_text_regions: list[str] = []
    missing_connectors: list[str] = []
    large_images: list[dict[str, Any]] = []

    zones = layout.get("zones", [])
    if isinstance(zones, list):
        for zone in zones:
            if not isinstance(zone, dict):
                continue
            zone_id = str(zone.get("id", "")).strip()
            if zone_id and zone_id not in markers["zones"]:
                missing_zones.append(zone_id)

    for icon_id in required_icons:
        if icon_id not in markers["icons"]:
            missing_icons.append(icon_id)

    for region in text_regions:
        region_id = str(region.get("id", "")).strip()
        if region_id and region_id not in markers["text_regions"]:
            missing_text_regions.append(region_id)

    main_chain = layout.get("main_chain", {})
    connectors = main_chain.get("connectors", []) if isinstance(main_chain, dict) else []
    if strict and not snapshot_mode and isinstance(connectors, list) and connectors:
        if not markers["connectors"]:
            missing_connectors.append("main_chain.connectors")
        else:
            for connector in connectors:
                if not isinstance(connector, dict):
                    continue
                source = str(connector.get("from", "")).strip()
                target = str(connector.get("to", "")).strip()
                if not source or not target:
                    continue
                needle = f"{source}->{target}".lower()
                matched = any(
                    needle in item.lower() or source.lower() in item.lower()
                    for item in markers["connectors"]
                )
                if not matched:
                    missing_connectors.append(needle)

    if not snapshot_mode:
        for x, y, width, height in markers["images"]:
            if width >= vw * FULL_SLIDE_RATIO and height >= vh * FULL_SLIDE_RATIO:
                large_images.append({"x": x, "y": y, "width": width, "height": height})

    zone_count = len(zones) if isinstance(zones, list) else 0
    if snapshot_mode:
        # No vector structure to count (no per-zone/per-connector primitives) --
        # only the editable text layer is required to actually exist.
        estimated_min = max(1, len(text_regions))
    else:
        estimated_min = max(12, zone_count * 2 + len(required_icons) * 2 + len(text_regions) + len(markers["connectors"]))

    errors: list[str] = []
    if missing_zones:
        errors.append(f"Missing data-zone-id for: {', '.join(missing_zones)}")
    if missing_icons:
        errors.append(f"Missing required data-icon-id for: {', '.join(missing_icons)}")
    if missing_text_regions:
        errors.append(f"Missing data-text-region-id for: {', '.join(missing_text_regions)}")
    if strict and missing_connectors:
        errors.append(f"Missing data-chain-connector for: {', '.join(missing_connectors)}")
    if large_images:
        errors.append(f"Found {len(large_images)} full-slide or near-full-slide raster image(s).")
    if strict and markers["element_count"] < estimated_min:
        errors.append(
            f"SVG element_count {markers['element_count']} below estimated minimum {estimated_min}."
        )

    return {
        "valid": not errors,
        "svg": str(svg_path),
        "missing_zones": missing_zones,
        "missing_icons": missing_icons,
        "missing_text_regions": missing_text_regions,
        "missing_connectors": missing_connectors,
        "large_images": large_images,
        "element_count": markers["element_count"],
        "estimated_min_element_count": estimated_min,
        "markers_found": {
            "zones": sorted(markers["zones"]),
            "icons": sorted(markers["icons"]),
            "text_regions": sorted(markers["text_regions"]),
            "connectors": sorted(markers["connectors"]),
        },
        "errors": errors,
    }


def verify_project(
    project: Path,
    *,
    strict: bool = False,
    write_report: bool = False,
    report_path: Path | None = None,
) -> dict[str, Any]:
    project = project.resolve()
    page_payloads: list[dict[str, Any]] = []
    errors: list[str] = []
    snapshot_mode = _is_snapshot_mode(project)

    layouts = _layout_paths(project)
    if not layouts:
        layouts = [("01", project / "layout_reference.json")] if (project / "layout_reference.json").is_file() else []

    for page_id, layout_path in layouts:
        if not layout_path.is_file():
            continue
        layout = load_json(layout_path)
        page_dir = layout_path.parent if layout_path.parent.name not in {"", project.name} else project
        svg_path = find_page_svg(project, page_id, page_dir=page_dir)
        if svg_path is None:
            errors.append(f"No SVG found for page `{page_id}`.")
            continue
        payload = inspect_page(
            layout=layout,
            svg_path=svg_path,
            text_regions=_regions_for_page(project, page_id),
            required_icons=_icon_ids(project, page_id),
            strict=strict,
            snapshot_mode=snapshot_mode,
        )
        payload["page_id"] = page_id
        payload["layout_reference"] = str(layout_path)
        page_payloads.append(payload)
        errors.extend(payload.get("errors", []))

    result = {
        "version": REPORT_VERSION,
        "workflow": "slide-image-rebuild",
        "check": "svg_rebuild_completeness",
        "project": str(project),
        "valid": not errors,
        "strict": strict,
        "summary": {
            "page_count": len(page_payloads),
            "pages_failed": sum(0 if item.get("valid") else 1 for item in page_payloads),
        },
        "pages": page_payloads,
        "errors": errors,
    }
    if write_report:
        out = report_path or project / "exports" / "qa" / "svg_completeness_report.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        result["report_path"] = str(out.relative_to(project)) if out.is_relative_to(project) else str(out)
    return result
