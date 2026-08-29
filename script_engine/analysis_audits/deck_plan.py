"""Deck Plan audit rules."""
from __future__ import annotations

from .common import *
from script_engine.narrative_arc import review_narrative_design
from script_engine.plan_quality import plan_critic_priorities
from script_engine.contracts import is_lean_deck_plan
from script_engine.source_arguments import (
    argument_source_refs,
    source_argument_index,
    source_argument_method,
)


_STRUCTURAL_PAGE_ROLES = frozenset(
    {"cover", "agenda", "contents", "chapter", "transition", "ending", "closing"}
)


def _is_lean_plan(plan: dict[str, Any]) -> bool:
    return is_lean_deck_plan(plan)


def _narrative_text(value: object) -> str:
    return str(value or "").strip()


def _narrative_terms(value: object) -> set[str]:
    text = _normalized_review_text(value)
    return {text[index : index + 2] for index in range(max(0, len(text) - 1))}


def _narrative_contract_diagnostics(
    plan: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Check the explicit deck narrative without imposing a story pattern.

    Missing fields are warnings for historical plans.  The deterministic
    failures are limited to referential and ordering errors that can be
    proven from the plan itself.
    """

    issues: list[str] = []
    warnings: list[str] = []
    narrative_keys = ("thesis", "narrative_arc", "storyline", "audience_start", "audience_end")
    has_narrative_fields = any(key in plan for key in narrative_keys)
    chapters = [item for item in plan.get("chapters") or [] if isinstance(item, dict)]
    pages = [item for item in plan.get("pages") or [] if isinstance(item, dict)]
    if not has_narrative_fields and not chapters:
        return issues, warnings

    missing_deck_fields = [
        key for key in ("thesis", "narrative_arc", "storyline")
        if not plan.get(key)
    ]
    if missing_deck_fields:
        warnings.append(
            "NARRATIVE_PLAN_FIELDS_INCOMPLETE: missing deck narrative field(s) "
            f"{missing_deck_fields}; evidence=plan; suggested_action=fill the fields from the approved source-constrained planning decision"
        )

    chapter_ids = [str(chapter.get("id") or "").strip() for chapter in chapters]
    duplicate_chapter_ids = sorted(
        {chapter_id for chapter_id in chapter_ids if chapter_id and chapter_ids.count(chapter_id) > 1}
    )
    if duplicate_chapter_ids:
        issues.append(
            "NARRATIVE_CHAPTER_ID_DUPLICATE: duplicate chapter id(s) "
            f"{duplicate_chapter_ids}; evidence=chapters; suggested_action=assign one stable id to each chapter"
        )
    chapter_id_set = {chapter_id for chapter_id in chapter_ids if chapter_id}
    missing_chapter_fields: list[str] = []
    for chapter in chapters:
        chapter_id = str(chapter.get("id") or "?")
        missing = [
            key for key in ("purpose", "question", "message", "relationship_to_previous")
            if not _narrative_text(chapter.get(key))
        ]
        if missing:
            missing_chapter_fields.append(f"{chapter_id}: {','.join(missing)}")
    if missing_chapter_fields:
        warnings.append(
            "NARRATIVE_CHAPTER_FIELDS_INCOMPLETE: "
            f"{missing_chapter_fields}; evidence=chapters; suggested_action=state each chapter's purpose, question, message and handoff"
        )

    page_chapter_ids = []
    for page in pages:
        page_id = str(page.get("id") or "?")
        chapter_id = str(page.get("chapter_id") or "").strip()
        if chapter_id:
            page_chapter_ids.append(chapter_id)
            if chapter_id not in chapter_id_set:
                issues.append(
                    "NARRATIVE_PAGE_CHAPTER_MISMATCH: "
                    f"page {page_id} references unknown chapter {chapter_id}; evidence={page_id}.chapter_id; "
                    "suggested_action=assign the page to an existing chapter or add the approved chapter"
                )
    chapter_order = {chapter_id: index for index, chapter_id in enumerate(chapter_ids) if chapter_id}
    ordered_page_chapters = [chapter_order[chapter_id] for chapter_id in page_chapter_ids if chapter_id in chapter_order]
    if ordered_page_chapters != sorted(ordered_page_chapters):
        issues.append(
            "NARRATIVE_PAGE_CHAPTER_ORDER_CONFLICT: page chapter order differs from the declared chapter order; "
            "evidence=pages.chapter_id; suggested_action=restore chapter order or record the authorized restructuring"
        )

    content_pages = [
        page for page in pages
        if str(page.get("page_role") or "").strip() not in _STRUCTURAL_PAGE_ROLES
    ]
    for index, page in enumerate(content_pages):
        page_id = str(page.get("id") or "?")
        title = _narrative_text(page.get("title"))
        message = _narrative_text(page.get("message"))
        if title and message and len(_normalized_review_text(title)) >= 4 and len(_normalized_review_text(message)) >= 8:
            title_terms = _narrative_terms(title)
            message_terms = _narrative_terms(message)
            if title_terms and message_terms and not (title_terms & message_terms):
                warnings.append(
                    "NARRATIVE_TITLE_MESSAGE_OBJECT_MISMATCH: "
                    f"page {page_id} title and core message have no identifiable object overlap; evidence={page_id}.title,{page_id}.message; "
                    "suggested_action=check that the title names the object or judgment actually developed by the page"
                )
        if index > 0 and not _narrative_text(page.get("receives")):
            warnings.append(
                "NARRATIVE_PAGE_HANDOFF_MISSING: "
                f"page {page_id} has no receives field; evidence={page_id}; suggested_action=state the prior question or recognition this page takes forward"
            )
        if index < len(content_pages) - 1 and not _narrative_text(page.get("next")):
            warnings.append(
                "NARRATIVE_PAGE_HANDOFF_MISSING: "
                f"page {page_id} has no next field; evidence={page_id}; suggested_action=state the recognition or question handed to the next content page"
            )

        next_text = _narrative_text(page.get("next"))
        if not next_text or index >= len(content_pages) - 1:
            continue
        next_page = content_pages[index + 1]
        next_question = _narrative_text(next_page.get("question"))
        next_terms = _narrative_terms(next_text)
        question_terms = _narrative_terms(next_question)
        if next_question and next_terms and question_terms and not (next_terms & question_terms):
            warnings.append(
                "NARRATIVE_NEXT_RECEIVES_CONFLICT: "
                f"page {page_id}.next has no identifiable subject overlap with {next_page.get('id') or '?'} question; "
                f"evidence={page_id}.next,{next_page.get('id') or '?'}.question; suggested_action=align the handoff wording with the next page's question"
            )

    page_messages_by_chapter: dict[str, list[str]] = {}
    for page in pages:
        chapter_id = str(page.get("chapter_id") or "").strip()
        message = _narrative_text(page.get("message"))
        if chapter_id and message:
            page_messages_by_chapter.setdefault(chapter_id, []).append(message)
    for chapter in chapters:
        chapter_id = str(chapter.get("id") or "").strip()
        chapter_message = _narrative_text(chapter.get("message"))
        page_messages = page_messages_by_chapter.get(chapter_id, [])
        if not chapter_message or not page_messages:
            continue
        chapter_terms = _narrative_terms(chapter_message)
        best_overlap = max(
            (len(chapter_terms & _narrative_terms(message)) / max(1, len(chapter_terms)) for message in page_messages),
            default=0.0,
        )
        if best_overlap < 0.15:
            warnings.append(
                "NARRATIVE_CHAPTER_MESSAGE_UNSUPPORTED: "
                f"chapter {chapter_id} message has weak overlap with its page messages; evidence={chapter_id}.message,pages[{chapter_id}].message; "
                "suggested_action=narrow the chapter conclusion or ensure its pages form the stated conclusion"
            )
    return issues, warnings


def _source_argument_binding_issues(
    plan: dict[str, Any], foundation: dict[str, Any]
) -> list[str]:
    """Keep PLAN attached to the source's document-level argument map.

    Historical foundations have no semantic graph and remain compatible.  A
    projected semantic foundation, however, must not be reduced back to a bag
    of facts when pages are planned.
    """

    thesis = foundation.get("document_thesis") or {}
    nodes = [item for item in foundation.get("argument_nodes") or [] if isinstance(item, dict)]
    semantics = foundation.get("document_semantics") or {}
    if not isinstance(thesis, dict) or not nodes or not isinstance(semantics, dict):
        return []

    issues: list[str] = []
    thesis_statement = _narrative_text(thesis.get("statement"))
    if _narrative_text(plan.get("source_thesis")) != thesis_statement:
        issues.append(
            "SOURCE_ARGUMENT_THESIS_DRIFT: plan.source_thesis must exactly copy foundation.document_thesis.statement"
        )

    node_index = source_argument_index(foundation)
    expected_method = source_argument_method(foundation)
    actual_method = [
        _narrative_text(node_id)
        for node_id in plan.get("source_argument_method") or []
        if _narrative_text(node_id)
    ]
    if actual_method != expected_method:
        issues.append(
            "SOURCE_ARGUMENT_METHOD_DRIFT: plan.source_argument_method must preserve foundation.document_semantics.argument_method order"
        )

    consumed: list[str] = []
    page_nodes_by_chapter: dict[str, set[str]] = {}
    for index, page in enumerate(plan.get("pages") or []):
        if not isinstance(page, dict):
            continue
        page_id = _narrative_text(page.get("id")) or f"#{index}"
        structural_role = _narrative_text(page.get("page_role")) or _narrative_text(page.get("page_type"))
        if structural_role in _STRUCTURAL_PAGE_ROLES:
            continue
        selected = [
            _narrative_text(node_id)
            for node_id in page.get("source_argument_node_ids") or []
            if _narrative_text(node_id)
        ]
        if not selected:
            issues.append(
                f"pages.{index} ({page_id}): SOURCE_ARGUMENT_BINDING_MISSING: content page must identify its source argument responsibility"
            )
            continue
        unknown = [node_id for node_id in selected if node_id not in node_index]
        if unknown:
            issues.append(
                f"pages.{index} ({page_id}): SOURCE_ARGUMENT_NODE_UNKNOWN: {unknown}"
            )
        consumed.extend(node_id for node_id in selected if node_id in node_index)
        chapter_id = _narrative_text(page.get("chapter_id"))
        page_nodes_by_chapter.setdefault(chapter_id, set()).update(selected)
        page_refs = set(_page_evidence_ids(page))
        if _is_lean_plan(plan):
            page_refs.update(
                _narrative_text(ref)
                for ref in page.get("source_refs") or []
                if _narrative_text(ref)
            )
        for node_id in selected:
            node = node_index.get(node_id)
            if node is None:
                continue
            node_refs = argument_source_refs([node_id], node_index)
            if node_refs and page_refs.isdisjoint(node_refs):
                issues.append(
                    f"pages.{index} ({page_id}): SOURCE_ARGUMENT_EVIDENCE_DISCONNECTED: {node_id} has no evidence overlap with the page"
                )

    for index, chapter in enumerate(plan.get("chapters") or []):
        if not isinstance(chapter, dict):
            continue
        chapter_id = _narrative_text(chapter.get("id")) or f"#{index}"
        selected = {
            _narrative_text(node_id)
            for node_id in chapter.get("source_argument_node_ids") or []
            if _narrative_text(node_id)
        }
        if not selected:
            issues.append(
                f"chapters.{index} ({chapter_id}): SOURCE_ARGUMENT_BINDING_MISSING: chapter must state its source argument responsibility"
            )
            continue
        unknown = sorted(selected - set(node_index))
        if unknown:
            issues.append(
                f"chapters.{index} ({chapter_id}): SOURCE_ARGUMENT_NODE_UNKNOWN: {unknown}"
            )
        unowned = sorted(page_nodes_by_chapter.get(chapter_id, set()) - selected)
        if unowned:
            issues.append(
                f"chapters.{index} ({chapter_id}): SOURCE_ARGUMENT_CHAPTER_PAGE_MISMATCH: page bindings {unowned} are absent from the chapter binding"
            )

    missing_method_nodes = [node_id for node_id in expected_method if node_id not in consumed]
    if missing_method_nodes:
        issues.append(
            f"SOURCE_ARGUMENT_METHOD_UNCONSUMED: no content page carries {missing_method_nodes}"
        )
    return issues

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
                "ADJACENT_PLAN_MESSAGE_DUPLICATE: adjacent pages {left} and {right} have near-duplicate core messages "
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
    narrative_issues, narrative_warnings = _narrative_contract_diagnostics(plan)
    issues.extend(narrative_issues)
    warnings.extend(narrative_warnings)
    issues.extend(_source_argument_binding_issues(plan, foundation))
    lean_plan = _is_lean_plan(plan)
    if lean_plan:
        narrative_review = review_narrative_design(plan.get("narrative_design"))
        issues.extend(narrative_review["issues"])
        warnings.extend(
            f"{finding['code']}: {finding['page_id']}: {finding['reason']}"
            for finding in plan_critic_priorities(plan)
        )
    items = foundation_items_by_id(foundation)
    source_assets = {
        str(asset.get("id")): asset
        for asset in foundation.get("source_assets") or []
        if isinstance(asset, dict) and asset.get("id")
    }
    argument_nodes = {
        str(node.get("id")): node
        for node in foundation.get("argument_nodes") or []
        if isinstance(node, dict) and node.get("id")
    }
    peak_page_id = str((plan.get("narrative_design") or {}).get("peak_page_id") or "")
    if lean_plan:
        design = plan.get("narrative_design") or {}
        node_index = source_argument_index(foundation)
        method_nodes = set(source_argument_method(foundation))
        if isinstance(design, dict):
            for candidate in design.get("candidates") or []:
                if not isinstance(candidate, dict):
                    continue
                candidate_id = str(candidate.get("id") or "?")
                focus = {
                    str(value).strip()
                    for value in candidate.get("argument_focus_node_ids") or []
                    if str(value).strip()
                }
                evidence_refs = {
                    str(value).strip()
                    for value in candidate.get("evidence_refs") or []
                    if str(value).strip()
                }
                unknown_focus = sorted(focus - method_nodes)
                if unknown_focus:
                    issues.append(
                        f"NARRATIVE_ARGUMENT_FOCUS_UNKNOWN: {candidate_id} uses {unknown_focus} outside source_argument_method"
                    )
                expected_refs = argument_source_refs(focus, node_index)
                if expected_refs and evidence_refs.isdisjoint(expected_refs):
                    issues.append(
                        f"NARRATIVE_EVIDENCE_DISCONNECTED: {candidate_id} evidence does not intersect its argument focus"
                    )
                unknown_evidence = sorted(evidence_refs - set(items))
                if unknown_evidence:
                    issues.append(
                        f"NARRATIVE_EVIDENCE_UNKNOWN: {candidate_id} uses {unknown_evidence}"
                    )
            peak_page_id = str(design.get("peak_page_id") or "").strip()
            no_peak_reason = str(design.get("no_single_peak_reason") or "").strip()
            page_index = {
                str(page.get("id") or "").strip(): page
                for page in plan.get("pages") or []
                if isinstance(page, dict) and str(page.get("id") or "").strip()
            }
            if peak_page_id:
                peak = page_index.get(peak_page_id)
                if peak is None:
                    issues.append(f"NARRATIVE_PEAK_PAGE_UNKNOWN: {peak_page_id}")
                elif not (_page_evidence_ids(peak) or peak.get("source_refs")):
                    issues.append(f"NARRATIVE_PEAK_PAGE_WITHOUT_EVIDENCE: {peak_page_id}")
            elif not no_peak_reason:
                issues.append("NARRATIVE_PEAK_UNRESOLVED: provide peak_page_id or no_single_peak_reason")
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
    if not lean_plan and not strict_evidence_fit:
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
        if not lean_plan:
            for readiness_issue in audit_stage02_readiness(page):
                issues.append(f"pages.{index} ({page_id}): {readiness_issue}")
        for composition_issue in _audit_onscreen_composition_definition(page):
            issues.append(f"pages.{index} ({page_id}): {composition_issue}")
        for contract_issue in _audit_onscreen_contract_definition(page, items):
            issues.append(f"pages.{index} ({page_id}): {contract_issue}")
        for relation_issue in _primary_relation_issues(page):
            issues.append(f"pages.{index} ({page_id}): {relation_issue}")
        if not lean_plan:
            for consumption_issue in _audit_source_consumption_definition(page, items, foundation):
                issues.append(f"pages.{index} ({page_id}): {consumption_issue}")
            for unit_issue in _audit_unit_consumption_definition(page, items, foundation):
                issues.append(f"pages.{index} ({page_id}): {unit_issue}")
            for review_issue in _audit_evidence_fit_reviews(page, items, strict=strict_evidence_fit):
                issues.append(f"pages.{index} ({page_id}): {review_issue}")
        elif isinstance(page.get("source_consumption"), dict):
            omissions = page["source_consumption"].get("intentional_omissions") or []
            for omission_index, omission in enumerate(omissions):
                if not isinstance(omission, dict) or not str(omission.get("reason") or "").strip():
                    issues.append(
                        f"pages.{index} ({page_id}).source_consumption.intentional_omissions[{omission_index}]: reason is required"
                    )

        structural_role = str(page.get("page_role") or page.get("page_type") or "").strip()
        if lean_plan and structural_role not in _STRUCTURAL_PAGE_ROLES:
            if plan.get("delivery_mode") == "presented" and not str(page.get("spoken_thread") or "").strip():
                issues.append(f"pages.{index} ({page_id}): LEAN_SPOKEN_THREAD_MISSING")
            visual = page.get("visual_evidence")
            if isinstance(visual, dict) and visual.get("kind") != "none":
                ref = str(visual.get("ref") or "").strip()
                if not ref or (ref not in items and ref not in source_assets):
                    issues.append(
                        f"pages.{index} ({page_id}): LEAN_VISUAL_EVIDENCE_REF_UNKNOWN: {ref or '<missing>'}"
                    )
                if visual.get("kind") == "asset" and ref in source_assets:
                    asset = source_assets[ref]
                    if not str(visual.get("carrying_element") or "").strip():
                        issues.append(
                            f"pages.{index} ({page_id}): SOURCE_ASSET_CARRYING_ELEMENT_MISSING: {ref}"
                        )
                    node_ids = {
                        str(value) for value in asset.get("argument_node_ids") or [] if str(value)
                    }
                    if not node_ids:
                        issues.append(
                            f"pages.{index} ({page_id}): SOURCE_ASSET_ARGUMENT_BINDING_MISSING: {ref}"
                        )
                    unknown_nodes = sorted(node_ids - set(argument_nodes))
                    if unknown_nodes:
                        issues.append(
                            f"pages.{index} ({page_id}): SOURCE_ASSET_ARGUMENT_NODE_UNKNOWN: {ref} uses {unknown_nodes}"
                        )
                    asset_refs = {
                        str(value) for value in asset.get("source_unit_refs") or [] if str(value)
                    }
                    if node_ids and not any(
                        asset_refs
                        & {
                            str(value)
                            for value in (argument_nodes.get(node_id) or {}).get("source_refs") or []
                            if str(value)
                        }
                        for node_id in node_ids
                    ):
                        issues.append(
                            f"pages.{index} ({page_id}): SOURCE_ASSET_ARGUMENT_EVIDENCE_DISCONNECTED: {ref}"
                        )
                    if not str(asset.get("wrong_reading") or "").strip():
                        message = (
                            f"pages.{index} ({page_id}): SOURCE_ASSET_WRONG_READING_MISSING: {ref}"
                        )
                        if str(page_id) == peak_page_id or asset.get("presentation_role") == "money_slide":
                            issues.append(message)
                        else:
                            warnings.append(message)
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

__all__ = ['_adjacent_plan_duplication_warnings', '_is_lean_plan', '_narrative_contract_diagnostics', '_source_argument_binding_issues', '_scope_chapters', '_audit_content_coverage_definition', '_audit_onscreen_contract_definition', '_primary_relation_issues', 'audit_deck_plan']
