"""Build derived source indexes for legacy extracts and script-profile sources."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cyberppt.source_assets import asset_candidates

from .source_index_legacy import (
    APPENDIX_RE,
    CHAPTER_RE,
    DIGITS,
    PARAGRAPH_RE,
    SECTION_RE,
    SUBSECTION_RE,
    TOC_ENTRY_RE,
    _ensure,
    _is_toc_entry,
    build_source_index,
    build_source_index_file,
    chinese_number,
)
from .source_index_validation import (
    _DETAIL_MEANINGFUL_RE,
    _DETAIL_SENTENCE_SPLIT_RE,
    _detail_obligation_count,
    _detail_overlap,
    _source_unit_refs,
    validate_foundation_detail_atomicity,
    validate_foundation_source_bindings,
    validate_reading_strategy,
    validate_script_foundation_against_index,
)
from .source_reading import (
    default_reading_strategy,
    estimate_reading_load,
    recommend_reading_mode,
)
from .text_io import write_text_lf


def build_source_index_v2(
    *,
    sources: list[dict[str, Any]],
    headings: list[dict[str, Any]],
    units: list[dict[str, Any]],
    warnings: list[dict[str, str]] | None = None,
    issues: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Build the single derived source cache used by the script profile."""

    warnings = list(warnings or [])
    issues = list(issues or [])
    reading_load = estimate_reading_load(units, sources)
    recommendation = recommend_reading_mode(reading_load)
    return {
        "schema": "cyberppt.source_index.v2",
        "profile": "script",
        "status": "passed" if not issues else "rewrite_required",
        "sources": sources,
        "source_hashes": {
            str(item.get("source_id")): str(item.get("sha256"))
            for item in sources
            if item.get("source_id") and item.get("sha256")
        },
        "source_structure": headings,
        "units": units,
        "asset_candidates": asset_candidates(units, headings),
        "reading_load": reading_load,
        "reading_recommendation": recommendation,
        "reading_strategy": default_reading_strategy(recommendation, headings, units),
        "warnings": warnings,
        "issues": issues,
    }


def render_source_context(
    source_index: dict[str, Any],
    *,
    reading_strategy: dict[str, Any] | None = None,
) -> str:
    """Render complete direct context or bounded long-mode previews plus deep reads."""

    strategy = reading_strategy or source_index.get("reading_strategy") or {}
    mode = str(strategy.get("mode") or "direct")
    deep_read_ids = {
        str(value) for value in strategy.get("deep_read_unit_ids") or [] if str(value)
    }
    lines = [
        f"[source-index schema={source_index.get('schema')} mode={mode}]",
        "",
        "## Source inventory",
    ]
    for source in source_index.get("sources") or []:
        lines.append(
            f"- [{source.get('source_id')}] {source.get('path')} sha256={source.get('sha256')}"
        )
    lines.extend(["", "## Source structure"])
    for heading in source_index.get("source_structure") or []:
        level = int(heading.get("level") or 1)
        lines.append(
            f"{'  ' * max(0, level - 1)}- [{heading.get('heading_id')}] {heading.get('title')}"
        )
    lines.extend(["", "## Indexed source units"])
    for item in source_index.get("units") or []:
        unit_id = str(item.get("unit_id") or "")
        text = str(item.get("text") or "").strip()
        if mode == "long" and unit_id not in deep_read_ids and item.get("kind") != "heading":
            text = text[:180] + ("…" if len(text) > 180 else "")
            scope = "mapped-preview"
        else:
            scope = "deep-read"
        qualifiers = [str(item.get("kind") or "unit"), scope]
        if item.get("heading_id"):
            qualifiers.append(f"heading={item['heading_id']}")
        lines.append(f"[{unit_id}][{';'.join(qualifiers)}] {text}".rstrip())
    candidates = source_index.get("asset_candidates") or []
    if candidates:
        lines.extend(["", "## Source asset candidates"])
        for candidate in candidates:
            refs = ", ".join(str(value) for value in candidate.get("source_unit_refs") or [])
            lines.append(
                f"[{candidate.get('id')}][{candidate.get('kind')}; refs={refs}] "
                f"{candidate.get('label')} locator={json.dumps(candidate.get('locator') or {}, ensure_ascii=False, sort_keys=True)}"
            )
    return "\n".join(lines).rstrip() + "\n"


def write_source_index_v2(payload: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    write_text_lf(output, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
