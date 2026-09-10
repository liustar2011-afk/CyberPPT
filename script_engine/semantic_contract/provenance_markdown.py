"""Canonical Markdown projection for Final Script 1.1 provenance.

The evidence block is audit-only. It keeps a short human-readable summary for
review and a compact canonical JSON record per module so the structured binding
can be reconstructed losslessly without punctuation heuristics.
"""

from __future__ import annotations

import json
from typing import Any


PROVENANCE_MARKDOWN_HEADING = "### 证据映射（模块级｜不上屏）"


def _text(value: object) -> str:
    return str(value or "").strip()


def provenance_records(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return canonical module provenance records in authored module order."""

    records: list[dict[str, Any]] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        module_id = _text(section.get("id"))
        provenance = section.get("provenance")
        if not module_id or not isinstance(provenance, dict):
            continue
        records.append({"module_id": module_id, "provenance": provenance})
    return records


def _human_summary_lines(records: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for record in records:
        module_id = _text(record.get("module_id"))
        provenance = record.get("provenance")
        if not module_id or not isinstance(provenance, dict):
            continue
        derivation = _text(provenance.get("derivation"))
        claim_refs = [_text(item) for item in (provenance.get("claim_refs") or []) if _text(item)]
        summary = f"- {module_id}"
        if derivation:
            summary += f" | {derivation}"
        if claim_refs:
            summary += f" | claims={','.join(claim_refs)}"
        lines.append(summary)
        for binding in provenance.get("bindings") or []:
            if not isinstance(binding, dict):
                continue
            target = _text(binding.get("target"))
            if not target:
                continue
            source_refs = [_text(item) for item in (binding.get("source_refs") or []) if _text(item)]
            relation = _text(binding.get("relation"))
            sources = ",".join(source_refs) if source_refs else "∅"
            suffix = f" ({relation})" if relation else ""
            lines.append(f"  - {target} <= {sources}{suffix}")
    return lines


def render_provenance_markdown(sections: list[dict[str, Any]]) -> list[str]:
    """Render reviewable evidence mapping plus a lossless canonical JSON mirror."""

    records = provenance_records(sections)
    if not records:
        return []
    lines = [PROVENANCE_MARKDOWN_HEADING, "", *_human_summary_lines(records), "", "```json"]
    for record in records:
        lines.append(
            json.dumps(
                record,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    lines.append("```")
    return lines


def parse_provenance_markdown(markdown: str) -> list[dict[str, Any]]:
    """Recover canonical module provenance records from rendered Markdown."""

    lines = markdown.splitlines()
    try:
        heading_index = lines.index(PROVENANCE_MARKDOWN_HEADING)
    except ValueError:
        return []

    index = heading_index + 1
    while index < len(lines) and lines[index].strip() != "```json":
        if lines[index].startswith("### "):
            raise ValueError("module provenance heading has no canonical json block")
        index += 1
    if index >= len(lines):
        raise ValueError("module provenance heading has no canonical json block")
    index += 1

    records: list[dict[str, Any]] = []
    seen_modules: set[str] = set()
    while index < len(lines):
        line = lines[index].strip()
        if line == "```":
            return records
        if line:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError("module provenance record must be a JSON object")
            module_id = _text(value.get("module_id"))
            provenance = value.get("provenance")
            if not module_id or not isinstance(provenance, dict):
                raise ValueError("module provenance record requires module_id and provenance")
            if module_id in seen_modules:
                raise ValueError(f"duplicate module provenance record: {module_id}")
            seen_modules.add(module_id)
            records.append({"module_id": module_id, "provenance": provenance})
        index += 1
    raise ValueError("module provenance json code fence is not closed")
