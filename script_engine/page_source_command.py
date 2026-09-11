"""Focused command helper for derived per-page source packets."""
from __future__ import annotations

import json
from pathlib import Path

from .contracts import load_json
from .page_source_packet import build_page_source_packet
from .source_freshness import (
    PAGE_SOURCE_BUILDER_VERSION,
    PAGE_SOURCE_PACKET_SCHEMA,
    build_input_fingerprints,
    utc_now_iso,
)
from .text_io import write_text_lf


def _failure(page_id: str, issue: str) -> tuple[dict, int]:
    return (
        {
            "schema": PAGE_SOURCE_PACKET_SCHEMA,
            "builder_version": PAGE_SOURCE_BUILDER_VERSION,
            "generated_at": utc_now_iso(),
            "authority": "derived_runtime_context",
            "page_id": page_id,
            "status": "blocked",
            "issues": [issue],
            "warnings": [],
        },
        1,
    )


def page_source_report(
    plan_path: Path,
    foundation_path: Path,
    page_id: str,
    *,
    source_index_path: Path | None = None,
    output_path: Path | None = None,
) -> tuple[dict, int]:
    """Resolve exact page evidence and optionally persist derived runtime context."""

    plan = load_json(plan_path)
    foundation = load_json(foundation_path)
    resolved_source_index = (
        source_index_path or foundation_path.parent / ".cache" / "source-index.json"
    )
    if not resolved_source_index.is_file():
        return _failure(
            page_id,
            f"PAGE_SOURCE_INDEX_MISSING: source index does not exist: {resolved_source_index}",
        )

    source_index = load_json(resolved_source_index)
    if source_index.get("schema") != "cyberppt.source_index.v2":
        return _failure(
            page_id,
            "PAGE_SOURCE_INDEX_SCHEMA_INVALID: page-source requires cyberppt.source_index.v2",
        )

    page = next(
        (
            item
            for item in plan.get("pages") or []
            if isinstance(item, dict) and str(item.get("id") or "") == page_id
        ),
        None,
    )
    if page is None:
        return _failure(
            page_id,
            f"PAGE_SOURCE_PAGE_UNKNOWN: page '{page_id}' is not in deck-plan.json",
        )

    page_context = dict(page)
    page_context["authoring_mode"] = str(plan.get("authoring_mode") or "faithful")
    packet = build_page_source_packet(page_context, foundation, source_index)
    packet["inputs"] = build_input_fingerprints(plan, foundation, source_index)
    packet["source_index"] = str(resolved_source_index.resolve())

    if output_path is not None:
        output_path = output_path.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        write_text_lf(output_path, json.dumps(packet, ensure_ascii=False, indent=2) + "\n")
        packet["output"] = str(output_path)

    return packet, 0 if packet.get("status") == "passed" else 1


__all__ = ["page_source_report"]
