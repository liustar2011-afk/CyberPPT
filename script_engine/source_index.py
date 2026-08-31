"""Build derived source indexes for legacy extracts and script-profile sources."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from cyberppt.source_assets import asset_candidates, validate_source_assets

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


def _source_unit_refs(item: dict[str, Any]) -> set[str]:
    refs = {
        str(value)
        for value in item.get("source_refs") or []
        if isinstance(value, str) and value.startswith("SU-")
    }
    for semantic_unit in item.get("semantic_units") or []:
        if not isinstance(semantic_unit, dict):
            continue
        ref = semantic_unit.get("source_unit_ref")
        if isinstance(ref, str) and ref.startswith("SU-"):
            refs.add(ref)
        refs.update(
            str(value)
            for value in semantic_unit.get("source_unit_refs") or []
            if isinstance(value, str) and value.startswith("SU-")
        )
    return refs


def validate_reading_strategy(
    foundation: dict[str, Any],
    source_headings: list[dict[str, Any]],
    source_unit_ids: list[str],
) -> list[str]:
    """Validate full structure coverage and long-mode evidence boundaries."""

    strategy = foundation.get("reading_strategy")
    if not isinstance(strategy, dict):
        return ["reading_strategy is required for script-profile Foundation"]
    mode = str(strategy.get("mode") or "")
    if mode not in {"direct", "long"}:
        return ["reading_strategy.mode must be 'direct' or 'long'"]

    issues: list[str] = []
    known_headings = {
        str(item.get("heading_id") or item.get("id"))
        for item in source_headings
        if item.get("heading_id") or item.get("id")
    }
    known_units = set(source_unit_ids)
    dispositions = [
        item for item in strategy.get("section_dispositions") or [] if isinstance(item, dict)
    ]
    disposition_ids = [str(item.get("heading_id") or "") for item in dispositions]
    if len(disposition_ids) != len(set(disposition_ids)):
        issues.append("reading_strategy.section_dispositions contains duplicate heading IDs")
    missing_headings = sorted(known_headings - set(disposition_ids))
    unknown_headings = sorted(set(disposition_ids) - known_headings)
    if missing_headings:
        issues.append(f"reading_strategy omits source headings {missing_headings}")
    if unknown_headings:
        issues.append(f"reading_strategy cites unknown source headings {unknown_headings}")
    foundation_structure_ids = {
        str(item.get("id"))
        for item in foundation.get("source_structure") or []
        if isinstance(item, dict) and item.get("id")
    }
    missing_structure = sorted(known_headings - foundation_structure_ids)
    if missing_structure:
        issues.append(f"foundation source_structure omits source headings {missing_structure}")
    for item in dispositions:
        disposition = str(item.get("disposition") or "")
        heading_id = str(item.get("heading_id") or "?")
        if disposition not in {"deep_read", "mapped", "excluded"}:
            issues.append(f"reading_strategy heading {heading_id} has invalid disposition")
        if disposition == "excluded" and not str(item.get("reason") or "").strip():
            issues.append(f"reading_strategy heading {heading_id} is excluded without reason")

    deep_read_ids = {
        str(value) for value in strategy.get("deep_read_unit_ids") or [] if str(value)
    }
    excluded_ids = {
        str(value) for value in strategy.get("excluded_unit_ids") or [] if str(value)
    }
    unknown_units = sorted((deep_read_ids | excluded_ids) - known_units)
    if unknown_units:
        issues.append(f"reading_strategy cites unknown source units {unknown_units}")
    overlap = sorted(deep_read_ids & excluded_ids)
    if overlap:
        issues.append(f"reading_strategy units cannot be both deep-read and excluded {overlap}")
    if mode == "direct" and deep_read_ids != known_units:
        issues.append("direct reading_strategy must deep-read every source unit")

    thesis = foundation.get("document_thesis")
    thesis_refs = {
        str(value)
        for value in (thesis.get("source_refs") if isinstance(thesis, dict) else []) or []
        if isinstance(value, str) and value.startswith("SU-")
    }
    if not isinstance(thesis, dict) or not str(thesis.get("statement") or "").strip():
        issues.append("script-profile Foundation requires document_thesis.statement")
    if not thesis_refs:
        issues.append("script-profile Foundation requires source-bound document_thesis")
    argument_nodes = {
        str(item.get("id")): item
        for item in foundation.get("argument_nodes") or []
        if isinstance(item, dict) and item.get("id")
    }
    semantics = foundation.get("document_semantics")
    method_ids = [
        str(value)
        for value in (semantics.get("argument_method") if isinstance(semantics, dict) else []) or []
        if isinstance(value, str) and value
    ]
    if not method_ids:
        issues.append("script-profile Foundation requires document_semantics.argument_method")
    unknown_method_ids = sorted(set(method_ids) - set(argument_nodes))
    if unknown_method_ids:
        issues.append(f"document_semantics.argument_method cites unknown nodes {unknown_method_ids}")
    argument_method_refs = set(thesis_refs)
    for node_id in method_ids:
        node = argument_nodes.get(node_id) or {}
        argument_method_refs.update(
            str(value)
            for value in node.get("source_refs") or []
            if isinstance(value, str) and value.startswith("SU-")
        )
    uncovered_structure: list[str] = []
    for item in foundation.get("source_structure") or []:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "?")
        refs = {
            str(value)
            for value in item.get("source_refs") or []
            if isinstance(value, str) and value.startswith("SU-")
        }
        if not refs or refs.isdisjoint(argument_method_refs):
            uncovered_structure.append(item_id)
    if uncovered_structure:
        issues.append(
            f"document thesis and argument method do not cover source structure {uncovered_structure}"
        )

    if mode == "long":
        for key in ("facts", "constraints", "numbers"):
            for index, item in enumerate(foundation.get(key) or []):
                if not isinstance(item, dict):
                    continue
                text = json.dumps(item, ensure_ascii=False)
                refs = _source_unit_refs(item)
                if re.search(r"\d", text) and refs and not refs.issubset(deep_read_ids):
                    issues.append(
                        f"{key}.{index}: precise numeric content requires deep-read source units"
                    )
    return issues


def validate_foundation_source_bindings(
    foundation: dict[str, Any], source_index: dict[str, Any]
) -> list[str]:
    """Bind script Foundation source identity and citations to source-index v2."""

    if source_index.get("schema") != "cyberppt.source_index.v2":
        return []
    issues: list[str] = []
    indexed_sources = {
        str(item.get("source_id")): item
        for item in source_index.get("sources") or []
        if isinstance(item, dict) and item.get("source_id")
    }
    authored_sources = {
        str(item.get("id")): item
        for item in foundation.get("sources") or []
        if isinstance(item, dict) and item.get("id")
    }
    missing_sources = sorted(set(indexed_sources) - set(authored_sources))
    unknown_sources = sorted(set(authored_sources) - set(indexed_sources))
    if missing_sources:
        issues.append(f"foundation sources omit indexed sources {missing_sources}")
    if unknown_sources:
        issues.append(f"foundation sources contain unknown sources {unknown_sources}")
    for source_id in sorted(set(indexed_sources) & set(authored_sources)):
        indexed = indexed_sources[source_id]
        authored = authored_sources[source_id]
        if str(authored.get("path") or "") != str(indexed.get("path") or ""):
            issues.append(f"foundation source {source_id} path differs from source index")
        if str(authored.get("sha256") or "") != str(indexed.get("sha256") or ""):
            issues.append(f"foundation source {source_id} sha256 differs from source index")

    known_units = {
        str(item.get("unit_id"))
        for item in source_index.get("units") or []
        if isinstance(item, dict) and item.get("unit_id")
    }
    cited_units: set[str] = set()
    for key in (
        "source_structure", "facts", "concepts", "entities", "relations",
        "arguments", "constraints", "numbers", "argument_nodes", "argument_relations",
        "source_assets",
    ):
        for item in foundation.get(key) or []:
            if isinstance(item, dict):
                cited_units.update(_source_unit_refs(item))
    thesis = foundation.get("document_thesis")
    if isinstance(thesis, dict):
        cited_units.update(_source_unit_refs(thesis))
    unknown_units = sorted(cited_units - known_units)
    if unknown_units:
        issues.append(f"foundation cites unknown source units {unknown_units}")
    findings = validate_source_assets(
        [item for item in foundation.get("source_assets") or [] if isinstance(item, dict)],
        known_units,
    )
    issues.extend(
        f"{finding['code']}: {finding['asset_id']}: {finding['message']}"
        for finding in findings
        if finding["severity"] == "blocking"
    )
    indexed_assets = {
        str(item.get("id")): item
        for item in source_index.get("asset_candidates") or []
        if isinstance(item, dict) and item.get("id")
    }
    for asset in foundation.get("source_assets") or [] if "asset_candidates" in source_index else []:
        if not isinstance(asset, dict):
            continue
        asset_id = str(asset.get("id") or "")
        candidate = indexed_assets.get(asset_id)
        if candidate is None:
            issues.append(f"foundation source asset {asset_id or '<missing>'} is not an indexed candidate")
            continue
        for key in ("kind", "locator"):
            if asset.get(key) != candidate.get(key):
                issues.append(f"foundation source asset {asset_id} {key} differs from source index")
        if set(asset.get("source_unit_refs") or []) != set(candidate.get("source_unit_refs") or []):
            issues.append(f"foundation source asset {asset_id} source_unit_refs differ from source index")
    return issues


_DETAIL_SENTENCE_SPLIT_RE = re.compile(
    r"[。！？!?；;\n]+|(?=(?:一|二|三|四|五|六|七|八|九|十)是)"
)
_DETAIL_MEANINGFUL_RE = re.compile(r"[一-鿿A-Za-z0-9]")


def _detail_obligation_count(unit: dict[str, Any]) -> int:
    """Estimate how many independently preservable payloads a source unit carries."""

    if str(unit.get("kind") or "") == "heading":
        return 0
    text = str(unit.get("text") or "").strip()
    if not text:
        return 0
    clauses = [
        clause.strip()
        for clause in _DETAIL_SENTENCE_SPLIT_RE.split(text)
        if len(_DETAIL_MEANINGFUL_RE.findall(clause)) >= 12
    ]
    if str(unit.get("kind") or "") in {"table_row", "list_item"}:
        return max(1, len(clauses))
    meaningful = len(_DETAIL_MEANINGFUL_RE.findall(text))
    return max(len(clauses), 2 if meaningful >= 160 else 1)


def _detail_overlap(source: str, authored: str) -> float:
    """Return source bigram recall so generic labels cannot masquerade as detail."""

    def bigrams(text: str) -> set[str]:
        chars = "".join(_DETAIL_MEANINGFUL_RE.findall(text.lower()))
        return {chars[index : index + 2] for index in range(max(0, len(chars) - 1))}

    source_bigrams = bigrams(source)
    if not source_bigrams:
        return 1.0
    return len(source_bigrams & bigrams(authored)) / len(source_bigrams)


def validate_foundation_detail_atomicity(
    foundation: dict[str, Any], source_index: dict[str, Any]
) -> list[str]:
    """Reject strict v2 Foundations that collapse rich source material into one label.

    The gate is intentionally limited to the current source-consumption contract. Short,
    genuinely atomic facts remain valid without ``semantic_units``; compound paragraphs,
    table rows and multi-unit citations must expose traceable units for PLAN and AUTHOR.
    """

    if (
        source_index.get("schema") != "cyberppt.source_index.v2"
        or foundation.get("source_consumption_policy") != "required"
        or foundation.get("source_consumption_contract_version") != 2
    ):
        return []

    indexed_units = {
        str(unit.get("unit_id")): unit
        for unit in source_index.get("units") or []
        if isinstance(unit, dict) and unit.get("unit_id")
    }
    issues: list[str] = []
    for collection in ("facts", "constraints"):
        for index, item in enumerate(foundation.get(collection) or []):
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id") or f"{collection}.{index}")
            cited = [
                ref
                for ref in _source_unit_refs(item)
                if ref in indexed_units and str(indexed_units[ref].get("kind") or "") != "heading"
            ]
            obligations = sum(_detail_obligation_count(indexed_units[ref]) for ref in cited)
            if obligations <= 1:
                continue
            semantic_units = [
                unit for unit in item.get("semantic_units") or [] if isinstance(unit, dict)
            ]
            if len(semantic_units) < obligations:
                issues.append(
                    "FOUNDATION_SOURCE_DETAIL_ATOMICITY_GAP: "
                    f"{item_id} cites {len(cited)} source units carrying at least {obligations} "
                    f"detail obligations but exposes {len(semantic_units)} semantic_units"
                )
            covered_refs: set[str] = set()
            authored_by_ref: dict[str, list[str]] = {}
            for unit_index, unit in enumerate(semantic_units):
                unit_refs = {
                    str(value)
                    for value in unit.get("source_unit_refs") or []
                    if isinstance(value, str) and value.startswith("SU-")
                }
                direct_ref = unit.get("source_unit_ref")
                if isinstance(direct_ref, str) and direct_ref.startswith("SU-"):
                    unit_refs.add(direct_ref)
                if not unit_refs:
                    issues.append(
                        "FOUNDATION_SEMANTIC_UNIT_SOURCE_REF_MISSING: "
                        f"{item_id}.semantic_units[{unit_index}] must declare source_unit_ref(s)"
                    )
                covered_refs.update(unit_refs)
                for ref in unit_refs:
                    authored_by_ref.setdefault(ref, []).append(str(unit.get("text") or ""))
            uncovered = sorted(set(cited) - covered_refs)
            if semantic_units and uncovered:
                issues.append(
                    "FOUNDATION_SEMANTIC_UNIT_SOURCE_COVERAGE_GAP: "
                    f"{item_id}.semantic_units do not cover cited source units {uncovered}"
                )
            for ref in cited:
                authored_text = "\n".join(authored_by_ref.get(ref) or [])
                if _detail_overlap(str(indexed_units[ref].get("text") or ""), authored_text) < 0.35:
                    issues.append(
                        "FOUNDATION_SEMANTIC_UNIT_DETAIL_LOSS: "
                        f"{item_id}.semantic_units abstract away source-specific content from {ref}"
                    )
    return issues


def validate_script_foundation_against_index(
    foundation: dict[str, Any], source_index: dict[str, Any]
) -> list[str]:
    issues = validate_foundation_source_bindings(foundation, source_index)
    issues.extend(validate_foundation_detail_atomicity(foundation, source_index))
    issues.extend(
        validate_reading_strategy(
            foundation,
            [
                item
                for item in source_index.get("source_structure") or []
                if isinstance(item, dict)
            ],
            [
                str(item.get("unit_id"))
                for item in source_index.get("units") or []
                if isinstance(item, dict) and item.get("unit_id")
            ],
        )
    )
    return list(dict.fromkeys(issues))
