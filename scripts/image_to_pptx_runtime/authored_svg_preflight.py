"""Read-only preflight for authored SVG inputs before Quick reconstruction."""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

SCHEMA = "cyberppt.authored_svg_preflight.v1"
_TEXT_ID = "data-cyberppt-text-id"
_NUMERIC_ATTRS = ("x", "y", "font-size", "dx", "dy")


def _local_name(node: ET.Element) -> str:
    return node.tag.rsplit("}", 1)[-1]


def _numbers(value: str) -> tuple[float, ...]:
    values = tuple(
        float(item)
        for item in re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", value)
    )
    if not values or any(not math.isfinite(item) for item in values):
        raise ValueError(f"invalid finite numeric SVG value: {value!r}")
    return values


def validate_authored_svg_preflight(
    authored_svg: Path | str,
    *,
    page_number: int,
) -> dict[str, Any]:
    path = Path(authored_svg).expanduser().resolve()
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if not path.is_file():
        return {
            "schema": SCHEMA,
            "page_number": page_number,
            "path": str(path),
            "valid": False,
            "errors": [{"code": "missing_authored_svg", "message": str(path)}],
            "warnings": [],
        }
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return {
            "schema": SCHEMA,
            "page_number": page_number,
            "path": str(path),
            "valid": False,
            "errors": [{"code": "invalid_xml", "message": str(exc)}],
            "warnings": [],
        }

    view_box = str(root.get("viewBox") or "").strip()
    try:
        view_values = _numbers(view_box)
    except ValueError:
        view_values = ()
    if len(view_values) != 4 or view_values[2] <= 0 or view_values[3] <= 0:
        errors.append({"code": "invalid_viewbox", "message": view_box})

    seen_text_ids: set[str] = set()
    text_count = 0
    referenced_assets: list[str] = []
    for node in root.iter():
        kind = _local_name(node)
        if kind == "image":
            href = node.get("href") or node.get("{http://www.w3.org/1999/xlink}href") or ""
            if not href:
                errors.append({"code": "image_without_href", "message": "SVG image has no href"})
            elif href.startswith(("http:", "https:")):
                warnings.append({"code": "external_image_resource", "message": href})
            elif not href.startswith("data:"):
                asset = (path.parent / href).resolve() if not Path(href).is_absolute() else Path(href)
                referenced_assets.append(str(asset))
                if not asset.is_file():
                    errors.append({"code": "missing_relative_asset", "message": str(asset)})
        if kind != "text":
            continue
        text_count += 1
        text_id = str(node.get(_TEXT_ID) or "").strip()
        if text_id:
            if text_id in seen_text_ids:
                errors.append({"code": "duplicate_text_id", "message": text_id})
            seen_text_ids.add(text_id)
        for current in (node, *tuple(node.iter())):
            if _local_name(current) not in {"text", "tspan"}:
                continue
            for attr in _NUMERIC_ATTRS:
                raw = current.get(attr)
                if raw is None:
                    continue
                try:
                    _numbers(raw)
                except ValueError:
                    errors.append({
                        "code": "invalid_numeric_text_geometry",
                        "message": f"{attr}={raw!r}",
                    })
        parent_x = node.get("x")
        if parent_x:
            try:
                base_x = _numbers(parent_x)[0]
            except ValueError:
                base_x = None
            if base_x is not None:
                for tspan in (item for item in node if _local_name(item) == "tspan"):
                    raw_x = tspan.get("x")
                    if not raw_x:
                        continue
                    try:
                        child_x = _numbers(raw_x)[0]
                    except ValueError:
                        continue
                    if view_values and abs(child_x - base_x) > view_values[2] * 0.55:
                        warnings.append({
                            "code": "tspan_cross_region_jump",
                            "message": f"text x={base_x:g}, tspan x={child_x:g}",
                        })

    return {
        "schema": SCHEMA,
        "page_number": page_number,
        "path": str(path),
        "view_box": list(view_values) if len(view_values) == 4 else [],
        "text_count": text_count,
        "text_id_count": len(seen_text_ids),
        "referenced_assets": referenced_assets,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "diagnostic_only_warnings": True,
    }


__all__ = ["SCHEMA", "validate_authored_svg_preflight"]
