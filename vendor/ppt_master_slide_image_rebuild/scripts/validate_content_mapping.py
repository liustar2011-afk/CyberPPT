#!/usr/bin/env python3
"""
PPT Master - Content Mapping Validator

Validate content_mapping.json for the layout-reference-rebuild workflow.

Usage:
    python3 scripts/validate_content_mapping.py <content_mapping.json> [--layout layout_reference.json]

Examples:
    python3 scripts/validate_content_mapping.py projects/demo/content_mapping.json --layout projects/demo/layout_reference.json

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

FORBIDDEN_VISIBLE_PATTERNS = [
    r"page_role",
    r"layout_type",
    r"render_contract",
    r"qa_checklist",
    r"prompt",
    r"placeholder",
    r"TODO",
    r"\{\{.*?\}\}",
]

ALLOWED_RENDERABLE_FIELDS = {
    "title",
    "subtitle",
    "core_judgment",
    "intro",
    "takeaway",
    "main_chain_labels",
    "modules",
    "table",
    "labels",
    "footnote",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def _collect_layout_zone_ids(layout_path: Path | None) -> set[str]:
    if layout_path is None:
        return set()
    data = load_json(layout_path)
    zones = data.get("zones", [])
    if not isinstance(zones, list):
        return set()
    return {zone.get("id") for zone in zones if isinstance(zone, dict) and isinstance(zone.get("id"), str)}


def _collect_layout_chain_node_ids(layout_path: Path | None) -> set[str]:
    if layout_path is None:
        return set()
    data = load_json(layout_path)
    nodes = data.get("main_chain", {}).get("nodes", [])
    if not isinstance(nodes, list):
        return set()
    return {node.get("id") for node in nodes if isinstance(node, dict) and isinstance(node.get("id"), str)}


def _string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(_string_values(item))
        return strings
    if isinstance(value, dict):
        strings = []
        for item in value.values():
            strings.extend(_string_values(item))
        return strings
    return []


def _has_forbidden_visible_text(value: Any) -> list[str]:
    hits: list[str] = []
    text = "\n".join(_string_values(value))
    for pattern in FORBIDDEN_VISIBLE_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(pattern)
    return hits


def validate(
    data: dict[str, Any],
    *,
    layout_zone_ids: set[str] | None = None,
    layout_chain_node_ids: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    layout_zone_ids = layout_zone_ids or set()
    layout_chain_node_ids = layout_chain_node_ids or set()

    for field in ["version", "page_role", "layout_type", "renderable_content"]:
        if field not in data:
            errors.append(f"Missing top-level field: {field}")

    renderable = data.get("renderable_content")
    if not isinstance(renderable, dict):
        errors.append("renderable_content must be an object")
        return errors

    unknown_renderable = sorted(set(renderable) - ALLOWED_RENDERABLE_FIELDS)
    if unknown_renderable:
        errors.append(f"renderable_content has unsupported fields: {', '.join(unknown_renderable)}")

    forbidden_hits = _has_forbidden_visible_text(renderable)
    if forbidden_hits:
        errors.append(f"renderable_content contains forbidden visible tokens: {', '.join(forbidden_hits)}")

    title = renderable.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append("renderable_content.title must be a non-empty string")

    modules = renderable.get("modules", [])
    if modules is None:
        modules = []
    if not isinstance(modules, list):
        errors.append("renderable_content.modules must be a list")
    else:
        for index, module in enumerate(modules):
            if not isinstance(module, dict):
                errors.append(f"renderable_content.modules[{index}] must be an object")
                continue
            zone_id = module.get("zone_id")
            if layout_zone_ids and zone_id not in layout_zone_ids:
                errors.append(f"modules[{index}].zone_id does not match layout zones: {zone_id}")
            module_index = module.get("index")
            if module_index is not None and not isinstance(module_index, (str, int)):
                errors.append(f"modules[{index}].index must be a string or integer when present")
            if not isinstance(module.get("title"), str) or not module.get("title", "").strip():
                errors.append(f"modules[{index}].title must be a non-empty string")
            body = module.get("body", [])
            if isinstance(body, str):
                if not body.strip():
                    errors.append(f"modules[{index}].body must not be empty")
            elif isinstance(body, list):
                if not all(isinstance(item, str) and item.strip() for item in body):
                    errors.append(f"modules[{index}].body list must contain non-empty strings")
            else:
                errors.append(f"modules[{index}].body must be a string or list of strings")
            result_title = module.get("result_title")
            result = module.get("result")
            if (result_title is None) != (result is None):
                errors.append(f"modules[{index}] result_title and result should be provided together")
            if result_title is not None and (not isinstance(result_title, str) or not result_title.strip()):
                errors.append(f"modules[{index}].result_title must be a non-empty string")
            if result is not None:
                if isinstance(result, str):
                    if not result.strip():
                        errors.append(f"modules[{index}].result must not be empty")
                elif isinstance(result, list):
                    if not all(isinstance(item, str) and item.strip() for item in result):
                        errors.append(f"modules[{index}].result list must contain non-empty strings")
                else:
                    errors.append(f"modules[{index}].result must be a string or list of strings")

    labels = renderable.get("main_chain_labels", [])
    if labels is not None:
        if not isinstance(labels, list) or not all(isinstance(item, str) and item.strip() for item in labels):
            errors.append("renderable_content.main_chain_labels must be a list of non-empty strings")
        elif layout_chain_node_ids and len(labels) != len(layout_chain_node_ids):
            errors.append(
                "renderable_content.main_chain_labels count should match layout main_chain.nodes "
                f"({len(labels)} labels vs {len(layout_chain_node_ids)} nodes)"
            )

    table = renderable.get("table")
    if table is not None and not isinstance(table, dict):
        errors.append("renderable_content.table must be null or an object")

    for field in ["subtitle", "core_judgment", "intro", "takeaway", "footnote"]:
        value = renderable.get(field)
        if value is not None and not isinstance(value, str):
            errors.append(f"renderable_content.{field} must be a string when present")

    contract = data.get("render_contract", {})
    if contract and not isinstance(contract, dict):
        errors.append("render_contract must be an object when present")
    elif isinstance(contract, dict):
        render_only = contract.get("render_only", [])
        never_render = contract.get("never_render", [])
        if render_only and (not isinstance(render_only, list) or "renderable_content" not in render_only):
            errors.append("render_contract.render_only should include renderable_content")
        if never_render and not isinstance(never_render, list):
            errors.append("render_contract.never_render must be a list when present")

    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate content_mapping.json.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="Path to content_mapping.json")
    parser.add_argument("--layout", type=Path, help="Optional layout_reference.json for zone validation")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    data = load_json(args.path)
    zone_ids = _collect_layout_zone_ids(args.layout)
    chain_node_ids = _collect_layout_chain_node_ids(args.layout)
    errors = validate(data, layout_zone_ids=zone_ids, layout_chain_node_ids=chain_node_ids)
    payload = {"valid": not errors, "errors": errors}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
