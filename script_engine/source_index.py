"""Build derived source indexes for legacy extracts and script-profile sources."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from cyberppt.source_assets import asset_candidates, validate_source_assets

from .text_io import write_text_lf

PARAGRAPH_RE = re.compile(r"^\[/body/p\[(?P<key>[^\]]+)\]\]\s*(?P<text>.*)$")
CHAPTER_RE = re.compile(r"^第([一二三四五六七八九十百零〇两]+)章[　\s]*(.*)$")
SECTION_RE = re.compile(r"^([一二三四五六七八九十]+)、\s*(.+)$")
SUBSECTION_RE = re.compile(r"^（([一二三四五六七八九十]+)）\s*(.+)$")
APPENDIX_RE = re.compile(r"^附件([一二三四五六七八九十]+)[　\s]*(.*)$")
TOC_ENTRY_RE = re.compile(r"\t+\d+\s*$")
DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}

def chinese_number(text: str) -> int:
    if text == "十":
        return 10
    if "十" in text:
        left, _, right = text.partition("十")
        tens = DIGITS.get(left, 1) if left else 1
        ones = DIGITS.get(right, 0) if right else 0
        return tens * 10 + ones
    value = 0
    for char in text:
        if char == "百":
            value = max(value, 1) * 100
        else:
            value = value * 10 + DIGITS.get(char, 0)
    return value

def _ensure(refs: dict[str, dict[str, Any]], ref: str, title: str, source_file: str | None) -> dict[str, Any]:
    return refs.setdefault(ref, {"ref": ref, "title": title, "source_file": source_file, "paragraph_keys": [], "line_numbers": []})

def _is_toc_entry(text: str) -> bool:
    """Return True for Word TOC rows that end in a tab-separated page number.

    Extracted Word text often repeats chapter/section headings in the table of contents.
    Treating those rows as body headings produces duplicate CHxx structure nodes and maps
    semantic refs to both TOC and body paragraphs. The page-number tab is a stable signal in
    the source_extract format used by the current projects.
    """
    return bool(TOC_ENTRY_RE.search(text))

def build_source_index(text: str, source_file: str | None = None) -> dict[str, Any]:
    refs: dict[str, dict[str, Any]] = {}
    structure: list[dict[str, Any]] = []
    chapter_no = 1
    section_no = 0
    current_ref = "S1.0"
    current_title = "Front matter"
    order = 0
    _ensure(refs, current_ref, current_title, source_file)

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        match = PARAGRAPH_RE.match(raw_line.strip())
        if not match:
            continue
        key = match.group("key")
        para = match.group("text").strip()
        if not para:
            continue
        if _is_toc_entry(para):
            continue

        chapter = CHAPTER_RE.match(para)
        section = SECTION_RE.match(para)
        subsection = SUBSECTION_RE.match(para)
        appendix = APPENDIX_RE.match(para)

        if chapter:
            chapter_no = chinese_number(chapter.group(1))
            section_no = 0
            current_ref = f"S{chapter_no}.0"
            current_title = para
            order += 1
            structure.append({"id": f"CH{chapter_no:02d}", "title": para, "order": order, "level": "chapter", "source_refs": [current_ref]})
            _ensure(refs, current_ref, current_title, source_file)
        elif appendix:
            current_ref = f"附件{appendix.group(1)}"
            current_title = para
            order += 1
            structure.append({"id": current_ref, "title": para, "order": order, "level": "appendix", "source_refs": [current_ref]})
            _ensure(refs, current_ref, current_title, source_file)
        elif para == "结束语":
            current_ref = "结束语"
            current_title = para
            order += 1
            structure.append({"id": "CLOSING", "title": para, "order": order, "level": "closing", "source_refs": [current_ref]})
            _ensure(refs, current_ref, current_title, source_file)
        elif section and current_ref.startswith("S"):
            section_no = chinese_number(section.group(1))
            current_ref = f"S{chapter_no}.{section_no}"
            current_title = para
            order += 1
            structure.append({"id": f"CH{chapter_no:02d}-S{section_no:02d}", "title": para, "order": order, "level": "section", "parent_id": f"CH{chapter_no:02d}", "source_refs": [current_ref]})
            _ensure(refs, current_ref, current_title, source_file)
        elif subsection and current_ref.startswith("S") and section_no:
            sub_no = chinese_number(subsection.group(1))
            current_ref = f"S{chapter_no}.{section_no}.{sub_no}"
            current_title = para
            order += 1
            structure.append({"id": f"CH{chapter_no:02d}-S{section_no:02d}-SS{sub_no:02d}", "title": para, "order": order, "level": "subsection", "parent_id": f"CH{chapter_no:02d}-S{section_no:02d}", "source_refs": [current_ref]})
            _ensure(refs, current_ref, current_title, source_file)

        record = _ensure(refs, current_ref, current_title, source_file)
        record["paragraph_keys"].append(key)
        record["line_numbers"].append(line_no)

    return {"version": "1.0", "source_file": source_file, "refs": refs, "source_structure": structure}

def build_source_index_file(source_extract: Path, output: Path, source_file: str | None = None) -> dict[str, Any]:
    index = build_source_index(source_extract.read_text(encoding="utf-8-sig"), source_file=source_file)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_text_lf(output, json.dumps(index, ensure_ascii=False, indent=2) + "\n")
    return index


def estimate_reading_load(
    units: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    """Estimate model reading load without changing the source inventory."""

    texts = [str(item.get("text") or "") for item in units]
    text_chars = sum(len(text) for text in texts)
    cjk_chars = sum(1 for text in texts for char in text if "\u3400" <= char <= "\u9fff")
    latin_chars = max(0, text_chars - cjk_chars)
    token_estimate = int(math.ceil(cjk_chars * 1.1 + latin_chars / 4))
    explicit_pages = 0
    slides_by_source: dict[str, set[int]] = {}
    sheets_by_source: dict[str, set[str]] = {}
    for item in units:
        locator = item.get("locator") if isinstance(item.get("locator"), dict) else {}
        source_id = str(item.get("source_id") or "")
        slide = locator.get("slide")
        if isinstance(slide, int):
            slides_by_source.setdefault(source_id, set()).add(slide)
        sheet = locator.get("sheet")
        if isinstance(sheet, str) and sheet:
            sheets_by_source.setdefault(source_id, set()).add(sheet)
    explicit_pages += sum(len(values) for values in slides_by_source.values())
    explicit_pages += sum(len(values) for values in sheets_by_source.values())
    text_pages = int(math.ceil(text_chars / 1000)) if text_chars else 0
    return {
        "source_count": len(sources),
        "unit_count": len(units),
        "text_chars": text_chars,
        "token_estimate": token_estimate,
        "page_equivalent": max(explicit_pages, text_pages, 1 if units else 0),
    }


def recommend_reading_mode(
    reading_load: dict[str, Any],
    *,
    max_pages: int = 45,
    max_tokens: int = 60_000,
) -> dict[str, Any]:
    """Choose direct or long reading from transparent size thresholds."""

    pages = int(reading_load.get("page_equivalent") or 0)
    tokens = int(reading_load.get("token_estimate") or 0)
    reasons: list[str] = []
    if pages > max_pages:
        reasons.append(f"page_equivalent {pages} exceeds {max_pages}")
    if tokens > max_tokens:
        reasons.append(f"token_estimate {tokens} exceeds {max_tokens}")
    return {
        "mode": "long" if reasons else "direct",
        "max_pages": max_pages,
        "max_tokens": max_tokens,
        "reasons": reasons,
    }


def _critical_deep_read_unit_ids(units: list[dict[str, Any]]) -> list[str]:
    critical_markers = (
        "必须", "不得", "应当", "责任", "条件", "范围", "边界", "计划", "已完成",
        "风险", "目标", "截止", "%", "亿元", "万元", "年", "月", "日",
    )
    result: list[str] = []
    for item in units:
        text = str(item.get("text") or "")
        if item.get("kind") == "heading" or any(marker in text for marker in critical_markers):
            unit_id = str(item.get("unit_id") or "")
            if unit_id:
                result.append(unit_id)
    return result


def default_reading_strategy(
    recommendation: dict[str, Any],
    headings: list[dict[str, Any]],
    units: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create a reviewable selection without deleting any indexed unit."""

    mode = str(recommendation.get("mode") or "direct")
    all_unit_ids = [str(item.get("unit_id")) for item in units if item.get("unit_id")]
    deep_read = all_unit_ids if mode == "direct" else _critical_deep_read_unit_ids(units)
    return {
        "mode": mode,
        "section_dispositions": [
            {
                "heading_id": str(item.get("heading_id")),
                "disposition": "deep_read" if mode == "direct" else "mapped",
                "reason": (
                    "direct profile reads the complete indexed section"
                    if mode == "direct"
                    else "retain the complete argument skeleton; expand critical units first"
                ),
            }
            for item in headings
            if item.get("heading_id")
        ],
        "deep_read_unit_ids": deep_read,
        "excluded_unit_ids": [],
    }


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
