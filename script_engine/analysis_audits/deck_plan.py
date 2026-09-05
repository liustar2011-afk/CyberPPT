"""Deterministic audits for the only supported Deck Plan contract: v2 lean."""
from __future__ import annotations

from difflib import SequenceMatcher
import re

from cyberppt.semantic_fidelity import audit_semantic_strength
from script_engine.plan_quality import plan_critic_priorities

from .common import *


_STRUCTURAL_PAGE_ROLES = frozenset(
    {"cover", "agenda", "contents", "chapter", "chapter_divider", "transition", "ending", "closing"}
)
_CHAPTER_TRANSITION_ROLES = frozenset({"chapter", "chapter_divider", "transition"})
_ROOT_FIELDS = frozenset(
    {
        "communication_goal", "plan_contract_version", "planning_profile", "authoring_mode", "audience",
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

_PLAN_PROMOTION_TERMS = (
    "完备",
    "落地",
    "一次填清",
    "全面具备",
    "立即",
)
_CONDITIONAL_STATUSES = frozenset(
    {
        "proposal", "recommendation", "to_confirm", "conditional",
        "拟建议", "建议", "待确认", "有条件",
    }
)
_BOUNDARY_MARKERS = (
    "可", "建议", "拟", "待", "协商", "条件", "原则", "按实际", "以正式", "逐步",
)
_SOURCE_HEADING_PREFIX_RE = re.compile(
    r"^\s*(?:第?[一二三四五六七八九十百]+[章节部分、.．]\s*|[（(]?[一二三四五六七八九十0-9]+[）)、.．]\s*)"
)


def _text(value: object) -> str:
    return str(value or "").strip()


def _unambiguous_source_heading_core(
    page: dict[str, Any], foundation: dict[str, Any]
) -> str:
    page_refs = {_text(ref) for ref in page.get("source_refs") or [] if _text(ref)}
    # Deck Plan source_refs normally name Foundation facts/constraints, while
    # lightweight argument nodes bind directly to stable SU-* units. Expand
    # page item IDs to their source-unit refs before matching headings.
    item_unit_refs = {
        _text(item.get("id")): {
            _text(ref) for ref in item.get("source_refs") or [] if _text(ref)
        }
        for key in ("facts", "constraints")
        for item in foundation.get(key) or []
        if isinstance(item, dict) and _text(item.get("id"))
    }
    expanded_refs = set(page_refs)
    for ref in page_refs:
        expanded_refs.update(item_unit_refs.get(ref, set()))
    headings = {
        _text(node.get("source_heading"))
        for node in foundation.get("argument_nodes") or []
        if isinstance(node, dict)
        and _text(node.get("source_heading"))
        and expanded_refs.intersection(
            {_text(ref) for ref in node.get("source_refs") or [] if _text(ref)}
        )
    }
    if len(headings) != 1:
        return ""
    return _SOURCE_HEADING_PREFIX_RE.sub("", next(iter(headings))).strip()


def _source_heading_title_issues(
    plan: dict[str, Any], foundation: dict[str, Any]
) -> list[str]:
    """Keep faithful page titles anchored to one unambiguous source heading."""

    if _text(plan.get("authoring_mode") or "faithful") != "faithful":
        return []
    issues: list[str] = []
    for index, page in enumerate(plan.get("pages") or []):
        if not isinstance(page, dict) or _text(page.get("page_role")) in _STRUCTURAL_PAGE_ROLES:
            continue
        heading_core = _unambiguous_source_heading_core(page, foundation)
        title = _text(page.get("title"))
        if heading_core and heading_core not in title:
            page_id = _text(page.get("id")) or f"#{index}"
            issues.append(
                f"pages.{index} ({page_id}).title: PLAN_SOURCE_TITLE_NOT_PRIORITIZED: "
                f"faithful mode title must retain source heading '{heading_core}'; "
                "append a page-specific qualifier only when the source section is split"
            )
    return issues


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


def _plan_semantic_fidelity_issues(
    plan: dict[str, Any], foundation: dict[str, Any]
) -> tuple[list[str], list[str]]:
    """Catch high-confidence PLAN wording promotions without pretending to prove entailment."""

    issues: list[str] = []
    warnings: list[str] = []
    items = foundation_items_by_id(foundation)
    assets = {
        _text(asset.get("id")): asset
        for asset in foundation.get("source_assets") or []
        if isinstance(asset, dict) and asset.get("id")
    }
    for index, page in enumerate(plan.get("pages") or []):
        if not isinstance(page, dict) or _text(page.get("page_role")) in _STRUCTURAL_PAGE_ROLES:
            continue
        page_id = _text(page.get("id")) or f"#{index}"
        refs = [_text(ref) for ref in page.get("source_refs") or [] if _text(ref)]
        support = [items[ref] for ref in refs if ref in items]
        evidence = "\n".join(_item_text(item) for item in support if _item_text(item))
        if not evidence:
            if refs and any(ref in assets for ref in refs):
                warnings.append(
                    f"pages.{index} ({page_id}): PLAN_SEMANTIC_TEXT_UNAVAILABLE: "
                    "source boundary contains only non-text assets; require qualitative PLAN review"
                )
            continue

        for field in ("title", "logic"):
            output = _text(page.get(field))
            for finding in audit_semantic_strength(output, evidence):
                issues.append(
                    f"pages.{index} ({page_id}).{field}: PLAN_{finding.code}: "
                    f"{finding.message}; source_refs={refs}"
                )
            for term in _PLAN_PROMOTION_TERMS:
                if term in output and term not in evidence:
                    issues.append(
                        f"pages.{index} ({page_id}).{field}: PLAN_COMPLETION_OR_SCOPE_PROMOTED: "
                        f"wording introduces unsupported high-risk term '{term}'; source_refs={refs}"
                    )

        question = _text(page.get("question"))
        for finding in audit_semantic_strength(question, evidence):
            warnings.append(
                f"pages.{index} ({page_id}).question: PLAN_QUESTION_{finding.code}: "
                f"{finding.message}; qualitative review required"
            )
        for term in _PLAN_PROMOTION_TERMS:
            if term in question and term not in evidence:
                warnings.append(
                    f"pages.{index} ({page_id}).question: PLAN_QUESTION_SCOPE_PROMOTED: "
                    f"question introduces unsupported high-risk term '{term}'; qualitative review required"
                )

        conditional_refs = [
            _text(item.get("id"))
            for item in support
            if _text(item.get("status")) in _CONDITIONAL_STATUSES
        ]
        title = _text(page.get("title"))
        source_heading_core = _unambiguous_source_heading_core(page, foundation)
        title_keeps_source_heading = bool(source_heading_core and source_heading_core in title)
        if (
            conditional_refs
            and title
            and not title_keeps_source_heading
            and not any(marker in title for marker in _BOUNDARY_MARKERS)
        ):
            warnings.append(
                f"pages.{index} ({page_id}).title: PLAN_STATUS_BOUNDARY_NOT_VISIBLE: "
                f"title cites conditional/recommended/pending evidence {conditional_refs} without an explicit boundary marker"
            )
    return issues, warnings


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
    semantic_issues, semantic_warnings = _plan_semantic_fidelity_issues(plan, foundation)
    issues.extend(semantic_issues)
    warnings.extend(semantic_warnings)
    issues.extend(_source_heading_title_issues(plan, foundation))
    warnings.extend(
        f"{finding['code']}: page {finding['page_id']}: {finding['reason']}"
        for finding in plan_critic_priorities(plan)
    )
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
