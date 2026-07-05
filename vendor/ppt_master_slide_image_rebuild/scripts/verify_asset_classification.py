#!/usr/bin/env python3
"""Validate asset classification for slide-image-rebuild projects.

The classification declares each non-text visual object's reconstruction source
and responsibility. It bridges Knight-style visual inventory with ppt-master's
resource reuse rule: shared SVG/icon libraries are preferred, imagegen is only
for complex visuals that cannot be stably rebuilt as editable vectors.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


SVG_NS = "{http://www.w3.org/2000/svg}"
ALLOWED_KINDS = {
    "shape",
    "card",
    "card_header",
    "icon",
    "connector",
    "table",
    "table_cell",
    "complex_visual",
    "decorative",
    "image",
}
ALLOWED_SOURCES = {
    "native_editable",
    "shared_icon_library",
    "shared_svg_library",
    "generated_svg",
    "imagegen_asset",
    "supplied_brand_asset",
    "crop_asset",
}
ALLOWED_TREATMENTS = {
    "editable_shape",
    "editable_text",
    "editable_svg",
    "transparent_png",
    "decorative_crop",
    "native_table",
}


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _bbox_valid(value: Any) -> bool:
    if not isinstance(value, list) or len(value) != 4:
        return False
    try:
        x, y, w, h = [float(item) for item in value]
    except (TypeError, ValueError):
        return False
    return x >= 0 and y >= 0 and w > 0 and h > 0


def _strip_ns(tag: str) -> str:
    return tag.replace(SVG_NS, "")


def _svg_icon_ids(project: Path) -> set[str]:
    ids: set[str] = set()
    svg_dir = project / "svg_output"
    if not svg_dir.is_dir():
        svg_dir = project / "svg_final"
    if not svg_dir.is_dir():
        return ids
    for svg in svg_dir.glob("*.svg"):
        try:
            root = ET.parse(svg).getroot()
        except ET.ParseError:
            continue
        for elem in root.iter():
            if _strip_ns(elem.tag) == "g":
                icon_id = elem.get("data-icon-id")
                if icon_id:
                    ids.add(icon_id)
    return ids


def _manifest_icon_ids(project: Path) -> set[str]:
    manifest = _load_json(project / "icon_manifest.json") or {}
    ids: set[str] = set()
    pages = manifest.get("pages")
    if isinstance(pages, list):
        for page in pages:
            icons = page.get("icons") if isinstance(page, dict) else None
            if not isinstance(icons, list):
                continue
            for icon in icons:
                if isinstance(icon, dict) and isinstance(icon.get("id"), str):
                    ids.add(icon["id"])
    return ids


def _validate_page(page: dict[str, Any], *, project: Path, svg_icons: set[str]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    page_id = page.get("page_id")
    if not isinstance(page_id, str) or not page_id.strip():
        errors.append("page.page_id must be a non-empty string")
    assets = page.get("assets")
    if not isinstance(assets, list):
        errors.append(f"page {page_id}: assets must be a list")
        return errors, warnings
    ids: set[str] = set()
    classified_icons: set[str] = set()
    for asset in assets:
        if not isinstance(asset, dict):
            errors.append(f"page {page_id}: asset entries must be objects")
            continue
        asset_id = asset.get("id")
        if not isinstance(asset_id, str) or not asset_id.strip():
            errors.append(f"page {page_id}: every asset requires id")
            continue
        if asset_id in ids:
            errors.append(f"page {page_id}: duplicate asset id `{asset_id}`")
        ids.add(asset_id)
        kind = asset.get("kind")
        source = asset.get("source")
        treatment = asset.get("treatment")
        if kind not in ALLOWED_KINDS:
            errors.append(f"page {page_id}: asset `{asset_id}` has unsupported kind `{kind}`")
        if source not in ALLOWED_SOURCES:
            errors.append(f"page {page_id}: asset `{asset_id}` has unsupported source `{source}`")
        if treatment not in ALLOWED_TREATMENTS:
            errors.append(f"page {page_id}: asset `{asset_id}` has unsupported treatment `{treatment}`")
        if not _bbox_valid(asset.get("bbox")):
            errors.append(f"page {page_id}: asset `{asset_id}` requires bbox [x,y,w,h] with positive size")
        if kind == "icon":
            classified_icons.add(asset_id)
            if not asset.get("parent_id"):
                errors.append(f"page {page_id}: icon asset `{asset_id}` requires parent_id")
            if source == "imagegen_asset":
                warnings.append(
                    f"page {page_id}: icon `{asset_id}` uses imagegen_asset; prefer shared_icon_library when possible"
                )
        if kind == "connector":
            if not asset.get("from") or not asset.get("to"):
                errors.append(f"page {page_id}: connector asset `{asset_id}` requires from and to")
        if source == "imagegen_asset" or treatment == "transparent_png":
            raw_path = asset.get("path") or asset.get("file") or asset.get("final_png") or asset.get("asset_path")
            if not isinstance(raw_path, str) or not raw_path.strip():
                errors.append(f"page {page_id}: imagegen/transparent asset `{asset_id}` requires final PNG path")
            else:
                path = Path(raw_path)
                if not path.is_absolute():
                    path = project / path
                if not path.is_file():
                    errors.append(f"page {page_id}: asset `{asset_id}` final PNG does not exist: {raw_path}")
        if source in {"crop_asset"} and treatment != "decorative_crop":
            errors.append(f"page {page_id}: crop_asset `{asset_id}` must use treatment=decorative_crop")
        if source in {"shared_icon_library", "shared_svg_library", "generated_svg"} and treatment not in {
            "editable_svg",
            "editable_shape",
        }:
            errors.append(f"page {page_id}: reusable/vector asset `{asset_id}` should use editable treatment")

    missing_icons = sorted(svg_icons - classified_icons)
    if missing_icons:
        warnings.append(f"page {page_id}: SVG icons not listed in asset_classification.json: {missing_icons}")
    return errors, warnings


def inspect(project: Path) -> dict[str, Any]:
    path = project / "asset_classification.json"
    if not path.is_file():
        icon_count = len(_manifest_icon_ids(project) or _svg_icon_ids(project))
        warning = "asset_classification.json not found; asset source classification gate is advisory until authored"
        if icon_count:
            warning += f" ({icon_count} icon assets detected)"
        return {"valid": True, "count": 0, "errors": [], "warnings": [warning]}
    payload = _load_json(path)
    if payload is None:
        return {"valid": False, "count": 0, "errors": ["asset_classification.json is not valid JSON object"], "warnings": []}
    pages = payload.get("pages")
    if not isinstance(pages, list) or not pages:
        return {"valid": False, "count": 0, "errors": ["asset_classification.json must contain non-empty pages[]"], "warnings": []}
    svg_icons = _svg_icon_ids(project)
    errors: list[str] = []
    warnings: list[str] = []
    asset_count = 0
    for page in pages:
        if not isinstance(page, dict):
            errors.append("pages[] entries must be objects")
            continue
        assets = page.get("assets")
        if isinstance(assets, list):
            asset_count += len(assets)
        page_errors, page_warnings = _validate_page(page, project=project, svg_icons=svg_icons)
        errors.extend(page_errors)
        warnings.extend(page_warnings)
    return {"valid": not errors, "count": asset_count, "errors": errors, "warnings": warnings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate asset_classification.json.")
    parser.add_argument("project", type=Path)
    args = parser.parse_args(argv)
    payload = inspect(args.project)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
