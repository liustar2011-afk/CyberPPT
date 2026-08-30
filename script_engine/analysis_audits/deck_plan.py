"""Deterministic audits for the only supported Deck Plan contract: v2 lean."""
from __future__ import annotations

from difflib import SequenceMatcher

from .common import *


_STRUCTURAL_PAGE_ROLES = frozenset(
    {"cover", "agenda", "contents", "chapter", "chapter_divider", "transition", "ending", "closing"}
)
_CHAPTER_TRANSITION_ROLES = frozenset({"chapter", "chapter_divider", "transition"})
_ROOT_FIELDS = frozenset(
    {
        "communication_goal", "plan_contract_version", "planning_profile", "audience",
        "audience_scope", "source_structure_mode", "presentation_structure_mode",
        "chapter_count_exception", "chapters", "pages",
    }
)
_CHAPTER_FIELDS = frozenset(
    {"id", "title", "purpose", "source_chapter_ids", "structural_operation"}
)
_PAGE_FIELDS = frozenset(
    {"id", "chapter_id", "title", "question", "logic", "page_role", "source_refs"}
)


def _text(value: object) -> str:
    return str(value or "").strip()


def _contract_issues(plan: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if plan.get("plan_contract_version") != 2:
        issues.append("PLAN_CONTRACT_VERSION_INVALID: only plan_contract_version=2 is supported")
    if plan.get("planning_profile") != "lean":
        issues.append("PLAN_PROFILE_INVALID: only planning_profile='lean' is supported")
    unknown = sorted(set(plan) - _ROOT_FIELDS)
    if unknown:
        issues.append(f"PLAN_AUTHOR_FIELDS_FORBIDDEN: {unknown}")
    for index, chapter in enumerate(plan.get("chapters") or []):
        if isinstance(chapter, dict):
            unknown = sorted(set(chapter) - _CHAPTER_FIELDS)
            if unknown:
                issues.append(f"chapters.{index}: PLAN_CHAPTER_AUTHOR_FIELDS_FORBIDDEN: {unknown}")
    for index, page in enumerate(plan.get("pages") or []):
        if isinstance(page, dict):
            unknown = sorted(set(page) - _PAGE_FIELDS)
            if unknown:
                issues.append(
                    f"pages.{index} ({page.get('id') or '?'}): PLAN_PAGE_AUTHOR_FIELDS_FORBIDDEN: {unknown}"
                )
    return issues


def _source_boundary_issues(plan: dict[str, Any], foundation: dict[str, Any]) -> list[str]:
    items = foundation_items_by_id(foundation)
    known_refs = set(items).union(
        _text(asset.get("id"))
        for asset in foundation.get("source_assets") or []
        if isinstance(asset, dict) and asset.get("id")
    )
    issues: list[str] = []
    for index, page in enumerate(plan.get("pages") or []):
        if not isinstance(page, dict):
            continue
        role = _text(page.get("page_role"))
        if role in _STRUCTURAL_PAGE_ROLES:
            continue
        page_id = _text(page.get("id")) or f"#{index}"
        refs = [_text(ref) for ref in page.get("source_refs") or [] if _text(ref)]
        if not refs:
            issues.append(f"pages.{index} ({page_id}): LEAN_SOURCE_BOUNDARY_MISSING")
            continue
        unknown = sorted(set(refs) - known_refs)
        if unknown:
            issues.append(f"pages.{index} ({page_id}): LEAN_SOURCE_REF_UNKNOWN: {unknown}")
    return issues


def _chapter_mapping_issues(
    plan: dict[str, Any], source_chapters: list[str]
) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    warnings: list[str] = []
    chapters = [item for item in plan.get("chapters") or [] if isinstance(item, dict)]
    pages = [item for item in plan.get("pages") or [] if isinstance(item, dict)]
    chapter_ids = {_text(chapter.get("id")) for chapter in chapters}

    for index, page in enumerate(pages):
        chapter_id = _text(page.get("chapter_id"))
        if chapter_id and chapter_id not in chapter_ids:
            issues.append(
                f"NARRATIVE_PAGE_CHAPTER_MISMATCH: page {page.get('id') or index} references unknown chapter {chapter_id}"
            )

    mapped: list[str] = []
    for index, chapter in enumerate(chapters):
        refs = [_text(value) for value in chapter.get("source_chapter_ids") or [] if _text(value)]
        if source_chapters and not refs:
            issues.append(f"PRESENTATION_CHAPTER_SOURCE_MAPPING_MISSING: chapters.{index}")
        mapped.extend(refs)
        if len(refs) > 1 and chapter.get("structural_operation") != "group_adjacent_source_chapters":
            issues.append(
                f"PRESENTATION_CHAPTER_GROUP_OPERATION_MISSING: chapters.{index} groups {refs}"
            )
    if source_chapters and mapped != source_chapters:
        issues.append(
            "PRESENTATION_SOURCE_CHAPTER_MAPPING_CONFLICT: presentation chapters must cover every source chapter once and in source order; "
            f"expected {source_chapters}, got {mapped}"
        )

    if _text(plan.get("presentation_structure_mode")) != "formal_chaptered":
        return issues, warnings
    chapter_count = len(chapters)
    if chapter_count > 6 and not _text(plan.get("chapter_count_exception")):
        issues.append("PRESENTATION_CHAPTER_COUNT_EXCESSIVE: more than six chapters require chapter_count_exception")
    elif chapter_count > 4:
        warnings.append("PRESENTATION_CHAPTER_COUNT_HIGH: formal reports should normally use no more than four chapters")

    roles = [_text(page.get("page_role")) for page in pages]
    if not roles or roles[0] != "cover":
        issues.append("PRESENTATION_COVER_MISSING: formal deck must start with cover")
    if len(roles) < 2 or roles[1] not in {"agenda", "contents"}:
        issues.append("PRESENTATION_AGENDA_MISSING: formal deck must place agenda after cover")
    if not roles or roles[-1] not in {"ending", "closing"}:
        issues.append("PRESENTATION_ENDING_MISSING: formal deck must end with ending")

    for chapter in chapters:
        chapter_id = _text(chapter.get("id"))
        owned = [page for page in pages if _text(page.get("chapter_id")) == chapter_id]
        transitions = [page for page in owned if _text(page.get("page_role")) in _CHAPTER_TRANSITION_ROLES]
        content = [page for page in owned if _text(page.get("page_role")) not in _STRUCTURAL_PAGE_ROLES]
        if chapter_count > 1 and len(transitions) != 1:
            issues.append(f"PRESENTATION_CHAPTER_TRANSITION_COUNT: chapter {chapter_id} requires exactly one transition")
        if chapter_count == 1 and transitions:
            issues.append("PRESENTATION_SINGLE_CHAPTER_TRANSITION_FORBIDDEN")
        if len(content) == 1:
            warnings.append(f"PRESENTATION_CHAPTER_THIN: chapter {chapter_id} has only one content page")
    return issues, warnings


def _adjacent_mission_warnings(plan: dict[str, Any]) -> list[str]:
    pages = [page for page in plan.get("pages") or [] if isinstance(page, dict)]
    warnings: list[str] = []
    for previous, current in zip(pages, pages[1:]):
        left = _normalized_review_text(previous.get("logic"))
        right = _normalized_review_text(current.get("logic"))
        if min(len(left), len(right)) >= 12 and SequenceMatcher(None, left, right).ratio() >= 0.90:
            warnings.append(
                f"ADJACENT_PLAN_MISSION_DUPLICATE: pages {previous.get('id') or '?'} and {current.get('id') or '?'} have near-duplicate missions"
            )
    return warnings


def audit_deck_plan(plan: dict[str, Any], foundation: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Audit PLAN structure and evidence boundaries without doing AUTHOR work."""

    issues = audit_plan_internal_expert_voice(plan)
    warnings = _adjacent_mission_warnings(plan)
    issues.extend(_contract_issues(plan))
    issues.extend(_source_boundary_issues(plan, foundation))
    structure = [item for item in foundation.get("source_structure") or [] if isinstance(item, dict)]
    source_chapters = [
        _text(item.get("id"))
        for item in sorted(structure, key=lambda item: item.get("order", 0))
        if item.get("level") == "chapter" and item.get("id")
    ]
    mapping_issues, mapping_warnings = _chapter_mapping_issues(plan, source_chapters)
    issues.extend(mapping_issues)
    warnings.extend(mapping_warnings)

    if plan.get("audience_scope") == "external":
        items = foundation_items_by_id(foundation)
        for index, page in enumerate(plan.get("pages") or []):
            if not isinstance(page, dict):
                continue
            internal = sorted(
                ref for ref in page.get("source_refs") or []
                if ref in items and effective_visibility(items[ref]) == "internal_only"
            )
            if internal:
                issues.append(
                    f"pages.{index} ({page.get('id') or '?'}): external plan source boundary contains internal-only evidence {internal}"
                )
    return issues, warnings


__all__ = ["audit_deck_plan"]
