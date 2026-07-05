#!/usr/bin/env python3
"""Validate semantic page architecture inventory for slide-image-rebuild.

The inventory captures the page architecture that pure bbox extraction misses:
zones, semantic roles, reading order, and relationships. It is optional during
rollout; if present, it is validated strictly.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ALLOWED_ROLES = {
    "title",
    "subtitle",
    "overview_band",
    "principle_strip",
    "timeline",
    "timeline_node",
    "card",
    "card_header",
    "card_body",
    "icon_slot",
    "table",
    "table_cell",
    "flow_connector",
    "complex_visual_region",
    "decorative_region",
    "footer",
    "label",
    "metric",
}
ALLOWED_RELATIONSHIPS = {
    "contains",
    "connects",
    "aligns_with",
    "labels",
    "supports",
    "sequence_next",
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
    return w > 0 and h > 0 and x >= 0 and y >= 0


def _layout_reading_order(project: Path) -> set[str]:
    layout = _load_json(project / "layout_reference.json") or {}
    grammar = layout.get("layout_grammar")
    if not isinstance(grammar, dict):
        return set()
    order = grammar.get("reading_order")
    return {str(item) for item in order if isinstance(item, str)} if isinstance(order, list) else set()


def _validate_page(page: dict[str, Any], *, layout_order: set[str]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    page_id = page.get("page_id")
    if not isinstance(page_id, str) or not page_id.strip():
        errors.append("page.page_id must be a non-empty string")

    architecture = page.get("architecture")
    if not isinstance(architecture, dict):
        errors.append(f"page {page_id}: architecture must be an object")
    else:
        primary_axis = architecture.get("primary_axis")
        if primary_axis is not None and primary_axis not in {"left_to_right", "top_to_bottom", "radial", "matrix", "freeform"}:
            errors.append(f"page {page_id}: architecture.primary_axis is not supported: {primary_axis}")
        reading_order = architecture.get("reading_order")
        if reading_order is not None and not all(isinstance(item, str) and item.strip() for item in reading_order or []):
            errors.append(f"page {page_id}: architecture.reading_order must contain non-empty string ids")

    zones = page.get("zones")
    if not isinstance(zones, list) or not zones:
        errors.append(f"page {page_id}: zones must be a non-empty list")
        zones = []
    ids: set[str] = set()
    for zone in zones:
        if not isinstance(zone, dict):
            errors.append(f"page {page_id}: zone entries must be objects")
            continue
        zone_id = zone.get("id")
        if not isinstance(zone_id, str) or not zone_id.strip():
            errors.append(f"page {page_id}: every zone requires id")
            continue
        if zone_id in ids:
            errors.append(f"page {page_id}: duplicate zone id `{zone_id}`")
        ids.add(zone_id)
        role = zone.get("semantic_role")
        if role not in ALLOWED_ROLES:
            errors.append(f"page {page_id}: zone `{zone_id}` has unsupported semantic_role `{role}`")
        if not _bbox_valid(zone.get("bbox")):
            errors.append(f"page {page_id}: zone `{zone_id}` requires bbox [x,y,w,h] with positive size")
        parent = zone.get("parent_id")
        if isinstance(parent, str) and parent and parent not in ids:
            # Parent may appear later in hand-authored files; validate after all
            # zones below with a second pass.
            pass

    for zone in zones:
        if not isinstance(zone, dict):
            continue
        parent = zone.get("parent_id")
        if isinstance(parent, str) and parent and parent not in ids:
            errors.append(f"page {page_id}: zone `{zone.get('id')}` parent_id `{parent}` is not declared")

    reading_order = architecture.get("reading_order") if isinstance(architecture, dict) else None
    if isinstance(reading_order, list):
        for item in reading_order:
            if isinstance(item, str) and item not in ids:
                errors.append(f"page {page_id}: reading_order id `{item}` is not declared in zones")
    if layout_order and ids and not layout_order.issubset(ids):
        missing = sorted(layout_order - ids)
        warnings.append(f"page {page_id}: inventory does not include layout_reference reading_order ids: {missing}")

    relationships = page.get("relationships", [])
    if relationships is None:
        relationships = []
    if not isinstance(relationships, list):
        errors.append(f"page {page_id}: relationships must be a list")
        relationships = []
    for rel in relationships:
        if not isinstance(rel, dict):
            errors.append(f"page {page_id}: relationship entries must be objects")
            continue
        rel_id = rel.get("id", "<unnamed>")
        kind = rel.get("kind")
        if kind not in ALLOWED_RELATIONSHIPS:
            errors.append(f"page {page_id}: relationship `{rel_id}` has unsupported kind `{kind}`")
        source = rel.get("from")
        target = rel.get("to")
        if kind in {"connects", "sequence_next"}:
            if source not in ids or target not in ids:
                errors.append(f"page {page_id}: relationship `{rel_id}` must connect declared from/to zone ids")
        elif source is not None and source not in ids:
            errors.append(f"page {page_id}: relationship `{rel_id}` from `{source}` is not declared")
        elif target is not None and target not in ids:
            errors.append(f"page {page_id}: relationship `{rel_id}` to `{target}` is not declared")

    return errors, warnings


def inspect(project: Path) -> dict[str, Any]:
    inventory_path = project / "architecture_inventory.json"
    if not inventory_path.is_file():
        return {
            "valid": True,
            "count": 0,
            "errors": [],
            "warnings": ["architecture_inventory.json not found; architecture inventory gate is advisory until authored"],
        }
    payload = _load_json(inventory_path)
    if payload is None:
        return {"valid": False, "count": 0, "errors": ["architecture_inventory.json is not valid JSON object"], "warnings": []}
    pages = payload.get("pages")
    if not isinstance(pages, list) or not pages:
        return {"valid": False, "count": 0, "errors": ["architecture_inventory.json must contain non-empty pages[]"], "warnings": []}

    layout_order = _layout_reading_order(project)
    errors: list[str] = []
    warnings: list[str] = []
    for page in pages:
        if not isinstance(page, dict):
            errors.append("pages[] entries must be objects")
            continue
        page_errors, page_warnings = _validate_page(page, layout_order=layout_order)
        errors.extend(page_errors)
        warnings.extend(page_warnings)
    return {"valid": not errors, "count": len(pages), "errors": errors, "warnings": warnings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate architecture_inventory.json.")
    parser.add_argument("project", type=Path)
    args = parser.parse_args(argv)
    payload = inspect(args.project)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
