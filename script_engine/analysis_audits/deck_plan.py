"""Deck Plan audit rules."""
from __future__ import annotations

from .common import *

def _adjacent_plan_duplication_warnings(plan: dict[str, Any]) -> list[str]:
    """Flag only high-confidence near duplication; shared terminology is valid."""

    pages = [page for page in plan.get("pages") or [] if isinstance(page, dict)]
    warnings: list[str] = []
    for previous, current in zip(pages, pages[1:]):
        previous_message = _normalized_review_text(previous.get("message"))
        current_message = _normalized_review_text(current.get("message"))
        if min(len(previous_message), len(current_message)) < 12:
            continue
        similarity = SequenceMatcher(None, previous_message, current_message).ratio()
        if similarity >= 0.90:
            warnings.append(
                "adjacent pages {left} and {right} have near-duplicate core messages "
                "(similarity {similarity:.0%}); verify that each page has a distinct proof responsibility".format(
                    left=previous.get("id") or "?",
                    right=current.get("id") or "?",
                    similarity=similarity,
                )
            )
    for page in pages:
        title = _normalized_review_text(page.get("title"))
        message = _normalized_review_text(page.get("message"))
        if title and len(title) >= 8 and title == message:
            warnings.append(
                f"page {page.get('id') or '?'} repeats the same text as title and core message; "
                "verify the title-message hierarchy"
            )
    return warnings

def _scope_chapters(source_scope: list[Any]) -> set[int]:
    chapters: set[int] = set()
    for ref in source_scope:
        if isinstance(ref, str):
            match = SOURCE_CHAPTER_RE.match(ref)
            if match:
                chapters.add(int(match.group(1)))
    return chapters

def _audit_content_coverage_definition(page: dict[str, Any]) -> list[str]:
    """Ensure an explicit internal-report route has evidence and meaning duties.

    This replaces character and module-count proxies. The audit only checks
    obligations the page author already declared in its route and visible-module
    contract; it never asks a sparse, source-native page to add filler.
    """

    route = page.get("content_route")
    if not isinstance(route, dict) or str(route.get("primary") or "") == "source_native":
        return []
    issues: list[str] = []
    if not _page_evidence_ids(page):
        issues.append(
            "explicit content_route has no declared source evidence; add source_refs, proof evidence_refs, "
            "analysis supports, or onscreen_contract module evidence_refs"
        )
    facets = {
        str(value).strip()
        for value in route.get("facets") or []
        if isinstance(value, str) and value.strip()
    }
    if facets.intersection({"risk", "coordination", "next_step"}) and not [
        value for value in route.get("meaning_signals") or []
        if isinstance(value, str) and value.strip()
    ]:
        issues.append(
            "content_route facets require one or more meaning_signals that must remain visible in final copy"
        )
    return issues

def _audit_onscreen_contract_definition(
    page: dict[str, Any], items: dict[str, dict[str, Any]]
) -> list[str]:
    contract = page.get("onscreen_contract")
    if not isinstance(contract, dict):
        return []
    return _onscreen_contract_definition_issues(page, contract, items)

def _primary_relation_issues(page: dict[str, Any]) -> list[str]:
    """Validate the page's mandatory primary/secondary relation declaration.

    `primary_relation` is the single hard-authority statement of a page's main
    topology (parallel/sequence/hierarchy/matrix/mixed/none). `secondary_relations`
    is the only sanctioned place for local, soft-authority arrows between scope
    entries. Both exist so AUTHOR never has to invent a relation PLAN did not
    approve, and so a parallel page cannot be silently turned into a sequence via
    local arrows.
    """
    issues: list[str] = []
    content = [c for c in (page.get("content") or []) if isinstance(c, str)]
    has_contract = isinstance(page.get("onscreen_contract"), dict)
    primary = page.get("primary_relation")
    if not isinstance(primary, dict):
        if len(content) >= 2 or has_contract:
            issues.append(
                "primary_relation is required when a page has 2+ content items or an onscreen_contract"
            )
        return issues

    scope = [s for s in primary.get("scope") or [] if isinstance(s, str) and s]
    scope_set = set(scope)
    rel_type = primary.get("type")
    if rel_type == "parallel" and len(scope) < 2:
        issues.append("primary_relation.type='parallel' requires at least two scope entries")

    secondary = [r for r in page.get("secondary_relations") or [] if isinstance(r, dict)]
    for s_index, relation in enumerate(secondary):
        from_label, to_label = relation.get("from"), relation.get("to")
        if scope_set and (from_label not in scope_set or to_label not in scope_set):
            issues.append(
                f"secondary_relations[{s_index}]: from/to must both be within primary_relation.scope"
            )
        if relation.get("type") not in _SECONDARY_RELATION_TYPES:
            issues.append(
                f"secondary_relations[{s_index}].type must be one of: {sorted(_SECONDARY_RELATION_TYPES)}"
            )

    if rel_type == "parallel" and len(scope) >= 2 and secondary:
        adjacency: dict[str, set[str]] = {}
        for relation in secondary:
            from_label, to_label = relation.get("from"), relation.get("to")
            if from_label in scope_set and to_label in scope_set:
                adjacency.setdefault(from_label, set()).add(to_label)
                adjacency.setdefault(to_label, set()).add(from_label)
        if adjacency:
            start = next(iter(adjacency))
            visited = {start}
            stack = [start]
            while stack:
                node = stack.pop()
                for neighbor in adjacency.get(node, ()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        stack.append(neighbor)
            if visited >= scope_set:
                issues.append(
                    "PRIMARY_RELATION_SMUGGLED_SEQUENCE: secondary_relations connect every "
                    "primary_relation.scope entry into one chain while type='parallel'; this "
                    "reintroduces a hidden sequence through local relations"
                )

    return issues

def audit_deck_plan(plan: dict[str, Any], foundation: dict[str, Any]) -> tuple[list[str], list[str]]:
    issues: list[str] = audit_plan_internal_expert_voice(plan)
    warnings: list[str] = _adjacent_plan_duplication_warnings(plan)
    items = foundation_items_by_id(foundation)
    structure = [x for x in (foundation.get("source_structure") or []) if isinstance(x, dict)]
    source_chapters = [
        x.get("id")
        for x in sorted(
            (x for x in structure if x.get("level") == "chapter" and x.get("id")),
            key=lambda x: x.get("order", 0),
        )
    ]
    mode = plan.get("source_structure_mode")
    if source_chapters and not mode:
        warnings.append("source_structure_mode: missing; source-driven plans should declare 'preserve' unless user authorized restructuring")
    if mode == "preserve":
        planned: list[str] = []
        missing = False
        for index, chapter in enumerate(plan.get("chapters") or []):
            if not isinstance(chapter, dict):
                continue
            ids = [x for x in (chapter.get("source_chapter_ids") or []) if isinstance(x, str)]
            if not ids:
                missing = True
            planned.extend(ids)
            if chapter.get("structural_operation") == "user_authorized_cross_chapter":
                issues.append(f"chapters.{index}: cross-chapter operation conflicts with source_structure_mode='preserve'")
        if missing:
            warnings.append("chapters: one or more chapters lack source_chapter_ids, so chapter-order fidelity cannot be audited mechanically")
        elif planned != source_chapters:
            issues.append(f"chapters: source chapter order/content differs from source_structure; expected {source_chapters}, got {planned}")

    audience_scope = plan.get("audience_scope", "unspecified")
    strict_evidence_fit = plan.get("evidence_fit_review_mode") == "strict"
    if not strict_evidence_fit:
        issues.append(
            "evidence_fit_review_mode: strict is required before PLAN can enter AUTHOR"
        )
    for index, page in enumerate(plan.get("pages") or []):
        if not isinstance(page, dict):
            continue
        page_id = page.get("id") or f"#{index}"
        for route_issue in audit_content_route(page):
            issues.append(f"pages.{index} ({page_id}): {route_issue}")
        for coverage_issue in _audit_content_coverage_definition(page):
            issues.append(f"pages.{index} ({page_id}): {coverage_issue}")
        for readiness_issue in audit_stage02_readiness(page):
            issues.append(f"pages.{index} ({page_id}): {readiness_issue}")
        for composition_issue in _audit_onscreen_composition_definition(page):
            issues.append(f"pages.{index} ({page_id}): {composition_issue}")
        for contract_issue in _audit_onscreen_contract_definition(page, items):
            issues.append(f"pages.{index} ({page_id}): {contract_issue}")
        for relation_issue in _primary_relation_issues(page):
            issues.append(f"pages.{index} ({page_id}): {relation_issue}")
        for consumption_issue in _audit_source_consumption_definition(page, items):
            issues.append(f"pages.{index} ({page_id}): {consumption_issue}")
        for review_issue in _audit_evidence_fit_reviews(page, items, strict=strict_evidence_fit):
            issues.append(f"pages.{index} ({page_id}): {review_issue}")
        scope = page.get("source_scope") or []
        chapters = _scope_chapters(scope)
        operation = page.get("structural_operation")
        if len(chapters) > 1 and operation != "user_authorized_cross_chapter":
            issues.append(f"pages.{index} ({page_id}): source_scope crosses chapters {sorted(chapters)} without user_authorized_cross_chapter")

        analysis_basis = page.get("analysis_basis") or {}
        if isinstance(analysis_basis, dict) and analysis_basis.get("relation_basis") == "inferred":
            supports = [x for x in (analysis_basis.get("supports") or []) if isinstance(x, str)]
            if not supports:
                issues.append(f"pages.{index} ({page_id}).analysis_basis: inferred relation requires support IDs")
            unknown = [x for x in supports if x not in items]
            if unknown:
                issues.append(f"pages.{index} ({page_id}).analysis_basis: unknown support IDs {unknown}")

        evidence_ids = _page_evidence_ids(page)
        evidence = _support_items(sorted(evidence_ids), items)
        internal = [item.get("id", "?") for item in evidence if effective_visibility(item) == "internal_only"]
        if audience_scope == "external" and internal:
            decision = page.get("visibility_decision")
            if decision not in ("internal_only_used_as_hidden_support", "user_approved_exposure"):
                issues.append(f"pages.{index} ({page_id}): external audience uses internal-only evidence {sorted(internal)} without an explicit visibility_decision")

        page_text = _page_text(page)
        if _has_optionality(evidence) and not _preserves_optionality(page_text):
            issues.append(f"pages.{index} ({page_id}): source evidence says modes may be independently selected and progressively deepened; plan must preserve both meanings")

        group_issue = _group_strength_issue(str(page.get("message") or ""), evidence)
        if group_issue:
            issues.append(f"pages.{index} ({page_id}): {group_issue}")

    return issues, warnings

__all__ = ['_adjacent_plan_duplication_warnings', '_scope_chapters', '_audit_content_coverage_definition', '_audit_onscreen_contract_definition', '_primary_relation_issues', 'audit_deck_plan']
