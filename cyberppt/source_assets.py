"""Derived source-asset candidates and Foundation asset validation.

Candidates are factual routing hints stored in the non-authoritative source
index.  Their communication meaning remains model-authored in Foundation.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from typing import Any


_ASSET_ID_RE = re.compile(r"^ASSET-[0-9A-F]{16}$")
_CANDIDATE_KINDS = {"caption", "table", "formula", "image", "chart"}


def _asset_id(kind: str, source_id: str, locator: dict[str, Any]) -> str:
    identity = json.dumps(
        {"kind": kind, "source_id": source_id, "locator": locator},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16].upper()
    return f"ASSET-{digest}"


def _group_locator(unit: dict[str, Any]) -> dict[str, Any]:
    locator = unit.get("locator") if isinstance(unit.get("locator"), dict) else {}
    kind = str(unit.get("kind") or "")
    if kind == "table_row":
        keys = ("table", "slide", "shape", "sheet")
        grouped = {key: locator[key] for key in keys if key in locator}
        return grouped or dict(locator)
    return dict(locator)


def asset_candidates(
    units: list[dict[str, Any]], headings: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return stable caption/table/formula/image/chart candidates.

    Consecutive rows from the same native table are deliberately represented
    as one asset.  A candidate records source location only; it does not claim
    that the asset deserves a slide or determine how it should be read.
    """

    heading_titles = {
        str(item.get("heading_id")): str(item.get("title") or "")
        for item in headings
        if isinstance(item, dict) and item.get("heading_id")
    }
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    sheet_regions: dict[tuple[str, str], tuple[int, int]] = {}
    for unit in sorted(
        units,
        key=lambda item: (str(item.get("source_id") or ""), int(item.get("source_order") or 0)),
    ):
        if not isinstance(unit, dict):
            continue
        unit_kind = str(unit.get("kind") or "")
        kind = "table" if unit_kind == "table_row" else unit_kind
        if kind not in _CANDIDATE_KINDS:
            continue
        source_id = str(unit.get("source_id") or "")
        locator = _group_locator(unit)
        raw_locator = unit.get("locator") if isinstance(unit.get("locator"), dict) else {}
        if kind == "table" and "sheet" in raw_locator and "row" in raw_locator:
            sheet = str(raw_locator["sheet"])
            row = int(raw_locator["row"])
            state_key = (source_id, sheet)
            previous, start = sheet_regions.get(state_key, (row - 1, row))
            if row != previous + 1:
                start = row
            sheet_regions[state_key] = (row, start)
            locator = {"sheet": sheet, "row_start": start}
        key = (
            kind,
            source_id,
            json.dumps(locator, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        )
        grouped[key].append(unit)

    result: list[dict[str, Any]] = []
    for (kind, source_id, locator_json), members in grouped.items():
        members.sort(key=lambda item: (int(item.get("source_order") or 0), str(item.get("unit_id") or "")))
        first = members[0]
        locator = json.loads(locator_json)
        if kind == "table" and "row_start" in locator:
            locator["row_end"] = max(
                int((item.get("locator") or {}).get("row") or locator["row_start"])
                for item in members
            )
        refs = [str(item.get("unit_id")) for item in members if item.get("unit_id")]
        heading_id = str(first.get("heading_id") or "")
        texts = [str(item.get("text") or "").strip() for item in members]
        label = heading_titles.get(heading_id) or next((text for text in texts if text), kind)
        result.append(
            {
                "id": _asset_id(kind, source_id, locator),
                "kind": kind,
                "source_id": source_id,
                "source_unit_refs": refs,
                "locator": locator,
                "label": label[:160],
                "heading_id": heading_id or None,
                "requires_visual_interpretation": any(
                    bool((item.get("metadata") or {}).get("requires_visual_interpretation"))
                    for item in members
                    if isinstance(item.get("metadata") or {}, dict)
                ),
            }
        )
    return sorted(result, key=lambda item: (str(item["source_id"]), str(item["id"])))


def validate_source_assets(
    assets: list[dict[str, Any]], source_unit_ids: list[str] | set[str]
) -> list[dict[str, str]]:
    """Validate authored Foundation assets against source-unit identity.

    Missing ``wrong_reading`` is a warning for supporting assets and a
    blocking issue for assets explicitly assigned the money-slide role.
    """

    known_units = {str(value) for value in source_unit_ids}
    seen: set[str] = set()
    findings: list[dict[str, str]] = []

    def add(severity: str, code: str, asset_id: str, message: str) -> None:
        findings.append(
            {"severity": severity, "code": code, "asset_id": asset_id, "message": message}
        )

    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            add("blocking", "SOURCE_ASSET_INVALID", f"#{index}", "asset must be an object")
            continue
        asset_id = str(asset.get("id") or f"#{index}")
        if not _ASSET_ID_RE.fullmatch(asset_id):
            add("blocking", "SOURCE_ASSET_ID_INVALID", asset_id, "id must use ASSET- plus 16 uppercase hex characters")
        if asset_id in seen:
            add("blocking", "SOURCE_ASSET_ID_DUPLICATE", asset_id, "asset id is duplicated")
        seen.add(asset_id)
        if str(asset.get("kind") or "") not in _CANDIDATE_KINDS:
            add("blocking", "SOURCE_ASSET_KIND_INVALID", asset_id, "kind is not a supported source asset kind")
        locator = asset.get("locator")
        if not isinstance(locator, dict) or not locator:
            add("blocking", "SOURCE_ASSET_LOCATOR_MISSING", asset_id, "a native source locator is required")
        refs = {str(value) for value in asset.get("source_unit_refs") or [] if str(value)}
        if not refs:
            add("blocking", "SOURCE_ASSET_SOURCE_REFS_MISSING", asset_id, "source_unit_refs is required")
        unknown = sorted(refs - known_units) if known_units else []
        if unknown:
            add("blocking", "SOURCE_ASSET_SOURCE_REF_UNKNOWN", asset_id, f"unknown source units {unknown}")
        if not str(asset.get("wrong_reading") or "").strip():
            severity = "blocking" if asset.get("presentation_role") == "money_slide" else "warning"
            add(severity, "SOURCE_ASSET_WRONG_READING_MISSING", asset_id, "state the plausible reading this asset must not imply")
    return findings


def source_asset_argument_binding_issues(
    assets: list[dict[str, Any]],
    argument_nodes: list[dict[str, Any]],
    *,
    selected_asset_ids: set[str] | None = None,
) -> list[str]:
    """Check that selected assets share source evidence with bound arguments."""

    nodes = {
        str(node.get("id")): {
            str(ref) for ref in node.get("source_refs") or [] if isinstance(ref, str)
        }
        for node in argument_nodes
        if isinstance(node, dict) and node.get("id")
    }
    issues: list[str] = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        asset_id = str(asset.get("id") or "?")
        if selected_asset_ids is not None and asset_id not in selected_asset_ids:
            continue
        node_ids = [str(value) for value in asset.get("argument_node_ids") or [] if str(value)]
        if not node_ids:
            issues.append(f"SOURCE_ASSET_ARGUMENT_BINDING_MISSING: {asset_id}")
            continue
        unknown = sorted(set(node_ids) - set(nodes))
        if unknown:
            issues.append(f"SOURCE_ASSET_ARGUMENT_NODE_UNKNOWN: {asset_id} uses {unknown}")
        asset_refs = {str(value) for value in asset.get("source_unit_refs") or [] if str(value)}
        if not any(asset_refs & nodes.get(node_id, set()) for node_id in node_ids):
            issues.append(
                f"SOURCE_ASSET_ARGUMENT_EVIDENCE_DISCONNECTED: {asset_id} source refs do not intersect its argument nodes"
            )
    return issues


__all__ = ["asset_candidates", "validate_source_assets", "source_asset_argument_binding_issues"]
