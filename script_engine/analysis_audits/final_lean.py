"""Focused lean-authoring source-consumption and visibility audits."""
from __future__ import annotations

from .common import *
from .final_authoring import (
    _looks_like_structural_metadata,
    _onscreen_module_lines,
    _status_strength_preserved,
)


_RELATIONSHIP_CLAIM_RE = re.compile(
    r"(映射|协同|闭环|衔接|转化|贯通|联动|传导|反馈|对应|支撑.+(?:形成|实现|落地))"
)


def _audit_lean_authored_source_consumption(
    page: dict[str, Any],
    slide: dict[str, Any],
    items: dict[str, dict[str, Any]],
    foundation: dict[str, Any],
) -> list[str]:
    """Audit AUTHOR's actual evidence selection directly against the Final Script slide."""

    if not requires_source_consumption(page, foundation):
        return []

    page_refs = {ref for ref in page.get("source_refs") or [] if isinstance(ref, str) and ref}
    slide_refs = [ref for ref in slide.get("source_refs") or [] if isinstance(ref, str) and ref]

    if not slide_refs:
        return [
            "AUTHOR_SOURCE_CONSUMPTION_MISSING: strict sourced content page requires "
            "slide.source_refs to declare the Foundation records AUTHOR actually used"
        ]

    issues: list[str] = []
    unknown = sorted({ref for ref in slide_refs if ref not in items})
    if unknown:
        issues.append(
            f"AUTHOR_SOURCE_REF_UNKNOWN: slide.source_refs cites unknown foundation records {unknown}"
        )
    outside = sorted({ref for ref in slide_refs if ref not in page_refs} - set(unknown))
    if outside:
        issues.append(
            "AUTHOR_SOURCE_REF_OUTSIDE_PLAN_SCOPE: slide.source_refs "
            f"{outside} fall outside the page's PLAN-approved source_refs boundary"
        )

    usable_refs = sorted(ref for ref in set(slide_refs) if ref in page_refs and ref in items)

    substantive_page_refs = {
        ref for ref in page_refs
        if ref in items and not _looks_like_structural_metadata(_item_text(items[ref]))
    }
    substantive_usable_refs = [
        ref for ref in usable_refs
        if not _looks_like_structural_metadata(_item_text(items[ref]))
    ]
    distinct_statements = {
        str(items[ref].get("statement") or _item_text(items[ref])).strip()
        for ref in substantive_usable_refs
        if str(items[ref].get("statement") or _item_text(items[ref])).strip()
    }
    minimum_distinct = min(3, len(substantive_page_refs))
    if minimum_distinct and len(distinct_statements) < minimum_distinct:
        issues.append(
            "AUTHOR_SOURCE_CONSUMPTION_TOO_NARROW: usable evidence covers only "
            f"{len(distinct_statements)} distinct source fact(s), fewer than the required "
            f"{minimum_distinct}; a strict sourced page cannot rest the whole argument on one fact"
        )

    full_copy = str(slide.get("full_copy") or "")
    compact_full_copy = re.sub(r"\s+", "", full_copy)

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", full_copy)
        if paragraph.strip()
    ]
    required_paragraphs = (
        3 if len(substantive_usable_refs) >= 6
        else 2 if len(substantive_usable_refs) >= 3
        else 1
    )
    if len(paragraphs) < required_paragraphs:
        issues.append(
            "AUTHOR_FULL_COPY_TOO_THIN: full_copy uses "
            f"{len(substantive_usable_refs)} substantive source facts but exposes only "
            f"{len(paragraphs)} substantive paragraph(s); at least {required_paragraphs} "
            "argument paragraph(s) are required so the complete copy preserves an "
            "audience-facing reasoning hierarchy before onscreen compression"
        )

    selected_source_statements = [
        statement
        for ref in substantive_usable_refs
        for statement in _source_surface_values(items[ref])
        if statement
    ]
    for paragraph_index, paragraph in enumerate(paragraphs):
        overlap = max(
            (
                _source_statement_overlap(statement, paragraph)
                for statement in selected_source_statements
            ),
            default=0.0,
        )
        if overlap < 0.04:
            issues.append(
                "AUTHOR_FULL_COPY_PARAGRAPH_UNGROUNDED: full_copy paragraph "
                f"{paragraph_index + 1} has no source-specific support from the "
                f"page's declared evidence (overlap={overlap:.3f})"
            )

    for ref in usable_refs:
        item = items[ref]
        primary_statement = str(
            item.get("statement")
            or item.get("claim")
            or item.get("definition")
            or item.get("relation")
            or _item_text(item)
        ).strip()
        overlap = (
            _source_statement_overlap(primary_statement, full_copy)
            if primary_statement else 0.0
        )
        if overlap < 0.08:
            issues.append(
                f"AUTHOR_SOURCE_SEMANTICS_LOST: {ref} is declared as used but its source-specific "
                f"content is absent from full_copy (overlap={overlap:.3f}); "
                f"source statement: {primary_statement or _item_text(item)}"
            )

        source_surface = " ".join(_source_surface_values(item))
        protected_numbers = set(
            re.findall(
                r"\d+(?:\.\d+)?(?:年\d{1,2}月\d{1,2}日|年|月|日|%|％|万|亿|项|级)?",
                source_surface,
            )
        )
        for number_ref in item.get("number_refs") or []:
            number = items.get(number_ref)
            if not isinstance(number, dict):
                continue
            raw_value = number.get("value")
            unit = str(number.get("unit") or "").strip()
            raw_values = raw_value if isinstance(raw_value, list) else [raw_value]
            for raw_entry in raw_values:
                value = "" if raw_entry is None else str(raw_entry).strip()
                if not value:
                    continue
                protected_numbers.add(value)
                if not isinstance(raw_value, list) and unit and unit not in {"时间", "年份", "生效日期"}:
                    protected_numbers.add(f"{value}{unit}")
        missing_numbers = sorted(
            value for value in protected_numbers
            if value and re.sub(r"\s+", "", value) not in compact_full_copy
        )
        if missing_numbers:
            issues.append(f"AUTHOR_NUMBER_OR_DATE_LOST: {ref} lost protected values {missing_numbers}")

        missing_conditions = [
            str(value).strip()
            for value in item.get("conditions") or []
            if str(value).strip() and re.sub(r"\s+", "", str(value)) not in compact_full_copy
        ]
        if missing_conditions:
            issues.append(f"AUTHOR_CONDITION_LOST: {ref} lost source conditions {missing_conditions}")

        missing_entities = []
        for entity_ref in item.get("entity_refs") or []:
            entity = items.get(entity_ref)
            name = str((entity or {}).get("name") or "").strip()
            if name and re.sub(r"\s+", "", name) not in compact_full_copy:
                missing_entities.append(name)
        if missing_entities:
            issues.append(f"AUTHOR_RESPONSIBILITY_LOST: {ref} lost source actors {missing_entities}")

        status = str(item.get("status") or "").strip()
        if not _status_strength_preserved(status, full_copy):
            issues.append(f"AUTHOR_STATUS_STRENGTH_LOST: {ref} lost source status '{status}'")

    return issues


def _onscreen_surface(slide: dict[str, Any]) -> str:
    return " ".join(
        value
        for module in slide.get("onscreen") or []
        if isinstance(module, dict)
        for value in (
            [str(module.get("heading") or "").strip()]
            + _onscreen_module_lines(module)
        )
        if value
    )


def _audit_lean_onscreen_full_copy_alignment(slide: dict[str, Any]) -> list[str]:
    """Require every visible v2-lean proposition to derive from complete copy."""

    if slide.get("page_type") != "content":
        return []

    full_copy = str(slide.get("full_copy") or "").strip()
    core_message = str(slide.get("core_message") or "").strip()
    issues: list[str] = []
    if core_message and _source_statement_overlap(core_message, full_copy, size=3) < 0.08:
        issues.append(
            "AUTHOR_ONSCREEN_FULL_COPY_DISCONNECTED: core_message is not materially "
            "supported by full_copy"
        )

    heading_support = " ".join(value for value in (core_message, full_copy) if value)
    compact_full_copy = re.sub(r"\s+", "", full_copy)
    for module_index, module in enumerate(slide.get("onscreen") or []):
        if not isinstance(module, dict):
            continue
        heading = str(module.get("heading") or "").strip()
        if heading and _source_statement_overlap(heading, heading_support, size=3) < 0.08:
            issues.append(
                "AUTHOR_ONSCREEN_FULL_COPY_DISCONNECTED: onscreen module "
                f"{module_index + 1} heading {heading!r} has no semantic anchor in "
                "core_message or full_copy"
            )
        for line in _onscreen_module_lines(module):
            overlap = _source_statement_overlap(line, full_copy, size=3)
            if overlap < 0.08:
                issues.append(
                    "AUTHOR_ONSCREEN_FULL_COPY_DISCONNECTED: onscreen module "
                    f"{module_index + 1} detail {line!r} is not a supported selection "
                    f"from full_copy (overlap={overlap:.3f})"
                )
            visible_numbers = set(
                re.findall(
                    r"\d+(?:\.\d+)?(?:年\d{1,2}月\d{1,2}日|年|月|日|%|％|万|亿|项|级)?",
                    line,
                )
            )
            missing_numbers = sorted(
                number for number in visible_numbers
                if number and re.sub(r"\s+", "", number) not in compact_full_copy
            )
            if missing_numbers:
                issues.append(
                    "AUTHOR_ONSCREEN_PROTECTED_FACT_DRIFTED: onscreen module "
                    f"{module_index + 1} introduces values absent from full_copy: "
                    f"{missing_numbers}"
                )
    return issues


def _audit_lean_onscreen_protected_retention(
    slide: dict[str, Any],
    evidence: list[dict[str, Any]],
    items: dict[str, dict[str, Any]],
) -> list[str]:
    """Reject onscreen compression that drops protected full-copy meaning."""

    if slide.get("page_type") != "content":
        return []

    full_copy = str(slide.get("full_copy") or "").strip()
    onscreen = _onscreen_surface(slide)
    compact_full = re.sub(r"\s+", "", full_copy)
    compact_onscreen = re.sub(r"\s+", "", onscreen)
    issues: list[str] = []

    protected_numbers = set(
        re.findall(
            r"\d+(?:\.\d+)?(?:年\d{1,2}月\d{1,2}日|年|月|日|%|％|万|亿|项|级)?",
            full_copy,
        )
    )
    missing_numbers = sorted(
        value for value in protected_numbers
        if value and value not in compact_onscreen
    )
    if missing_numbers:
        issues.append(
            "AUTHOR_ONSCREEN_NUMBER_OR_DATE_LOST: onscreen compression lost "
            f"protected full-copy values {missing_numbers}; copy the affected "
            "full-copy passage when they cannot be shortened safely"
        )

    for item in evidence:
        item_id = str(item.get("id") or "?")
        statement = str(
            item.get("statement")
            or item.get("claim")
            or item.get("definition")
            or item.get("relation")
            or _item_text(item)
        ).strip()
        if not statement or _source_statement_overlap(statement, full_copy) < 0.08:
            continue

        missing_conditions = [
            str(value).strip()
            for value in item.get("conditions") or []
            if str(value).strip()
            and re.sub(r"\s+", "", str(value)) in compact_full
            and re.sub(r"\s+", "", str(value)) not in compact_onscreen
        ]
        if missing_conditions:
            issues.append(
                f"AUTHOR_ONSCREEN_CONDITION_LOST: {item_id} lost full-copy "
                f"conditions {missing_conditions}"
            )

        missing_entities: list[str] = []
        for entity_ref in item.get("entity_refs") or []:
            entity = items.get(entity_ref)
            name = str((entity or {}).get("name") or "").strip()
            compact_name = re.sub(r"\s+", "", name)
            if compact_name and compact_name in compact_full and compact_name not in compact_onscreen:
                missing_entities.append(name)
        if missing_entities:
            issues.append(
                f"AUTHOR_ONSCREEN_RESPONSIBILITY_LOST: {item_id} lost full-copy "
                f"actors {missing_entities}"
            )

        role = str(
            item.get("claim_role")
            or item.get("semantic_argument_role")
            or item.get("argument_duty")
            or ""
        ).strip().lower()
        strength = str(item.get("strength") or item.get("priority") or "").strip().upper()
        protected_item = strength == "P0" or role in {
            "boundary", "constraint", "requirement", "responsibility", "task"
        }
        overlap = _source_statement_overlap(statement, onscreen)
        if protected_item and overlap < 0.08:
            issues.append(
                f"AUTHOR_ONSCREEN_CORE_SEMANTICS_LOST: {item_id} is protected "
                "full-copy meaning but is absent from onscreen "
                f"(overlap={overlap:.3f}); retain it or copy its full-copy passage"
            )

        status = str(item.get("status") or "").strip()
        if status and not _status_strength_preserved(status, onscreen):
            issues.append(
                f"AUTHOR_ONSCREEN_STATUS_STRENGTH_LOST: {item_id} lost full-copy "
                f"status '{status}'"
            )

    return issues


def _audit_lean_relationship_visibility(slide: dict[str, Any]) -> list[str]:
    """Require relationship claims and edges to be visible in both copy layers."""

    if slide.get("page_type") != "content":
        return []

    full_copy = str(slide.get("full_copy") or "").strip()
    visible = _onscreen_surface(slide)
    relationships = [
        relation
        for relation in slide.get("relationships") or []
        if isinstance(relation, dict)
    ]
    claim_surface = " ".join(
        str(slide.get(key) or "") for key in ("core_message", "visual_thesis")
    )
    issues: list[str] = []
    if _RELATIONSHIP_CLAIM_RE.search(claim_surface) and not relationships:
        issues.append(
            "AUTHOR_RELATIONSHIP_NOT_MATERIALIZED: the page claims a relationship "
            "but declares no edge with two endpoints and a connecting action"
        )

    for relation_index, relation in enumerate(relationships):
        missing = [
            key for key in ("from", "to", "relation")
            if not str(relation.get(key) or "").strip()
        ]
        if missing:
            issues.append(
                "AUTHOR_RELATIONSHIP_NOT_MATERIALIZED: relationships[{}] is missing "
                "{}".format(relation_index, missing)
            )
            continue
        statement = " ".join(
            str(relation.get(key) or "").strip()
            for key in ("from", "relation", "to")
        )
        prose_overlap = _source_statement_overlap(statement, full_copy, size=3)
        visible_overlap = _source_statement_overlap(statement, visible, size=3)
        if prose_overlap < 0.08 or visible_overlap < 0.08:
            issues.append(
                "AUTHOR_RELATIONSHIP_METADATA_ONLY: relationships[{}] is not "
                "materially expressed in both full_copy and onscreen "
                "(full_copy={:.3f}, onscreen={:.3f})".format(
                    relation_index, prose_overlap, visible_overlap
                )
            )
    return issues


__all__ = [
    "_audit_lean_authored_source_consumption",
    "_onscreen_surface",
    "_audit_lean_onscreen_full_copy_alignment",
    "_audit_lean_onscreen_protected_retention",
    "_audit_lean_relationship_visibility",
]
