"""Deck Plan audit rules."""
from __future__ import annotations

from .common import *


_STRUCTURAL_PAGE_ROLES = frozenset(
    {"cover", "agenda", "contents", "chapter", "chapter_divider", "transition", "ending", "closing"}
)
_CHAPTER_TRANSITION_ROLES = frozenset({"chapter", "chapter_divider", "transition"})
_PLAN_FORBIDDEN_AUTHOR_FIELDS = frozenset(
    {
        "delivery_mode", "narrative_design", "source_thesis",
        "source_argument_method", "thesis", "narrative_arc", "storyline",
        "content_load_curve", "audience_start", "audience_end",
        "evidence_fit_review_mode",
    }
)
_PLAN_FORBIDDEN_CHAPTER_AUTHOR_FIELDS = frozenset(
    {"question", "message", "relationship_to_previous", "source_argument_node_ids", "source_scope"}
)
_PLAN_FORBIDDEN_PAGE_AUTHOR_FIELDS = frozenset(
    {
        "subtitle", "message", "beat", "spoken_thread", "content", "receives", "next",
        "source_argument_node_ids", "source_scope", "content_load", "must_include",
        "reserved_for_later", "analysis_basis", "visual_evidence", "content_route",
        "stage02_readiness", "onscreen_contract", "onscreen_composition",
        "source_consumption", "evidence_fit_review", "primary_relation",
        "secondary_relations", "content_relations", "proof",
    }
)

_TITLE_CLAIM_MARKERS_RE = re.compile(
    r"(正在|已经|仍将|仍需|必须|需要|应当|同步推进|协同推进|持续推进|"
    r"形成|实现|建立|完成|提升|促进|支撑|保障|决定|成为|推动|加快)"
)
_TITLE_SENTENCE_PUNCT_RE = re.compile(r"[，,；;。！？!?：:]")


def _narrative_text(value: object) -> str:
    return str(value or "").strip()


def _narrative_terms(value: object) -> set[str]:
    text = _normalized_review_text(value)
    return {text[index : index + 2] for index in range(max(0, len(text) - 1))}


def _page_subject_terms(page: dict[str, Any]) -> set[str]:
    """Return the page-wide subject vocabulary, not only the core message."""

    values: list[object] = [
        page.get("subtitle"),
        page.get("question"),
        page.get("message"),
        page.get("logic"),
    ]
    values.extend(page.get("content") or [])
    terms: set[str] = set()
    for value in values:
        terms.update(_narrative_terms(value))
    return terms


def _title_is_claim_like(title: str) -> bool:
    """Detect long sentence-like titles without policing short topic phrases."""

    compact = re.sub(r"\s+", "", title)
    if len(compact) < 18:
        return False
    return bool(_TITLE_SENTENCE_PUNCT_RE.search(title) or _TITLE_CLAIM_MARKERS_RE.search(compact))


def _presentation_structure_diagnostics(
    plan: dict[str, Any], source_chapters: list[str]
) -> tuple[list[str], list[str]]:
    """Audit source-to-presentation chapter projection and formal page rhythm."""

    issues: list[str] = []
    warnings: list[str] = []
    chapters = [item for item in plan.get("chapters") or [] if isinstance(item, dict)]
    pages = [item for item in plan.get("pages") or [] if isinstance(item, dict)]
    source_mode = str(plan.get("source_structure_mode") or "").strip()

    if source_mode == "presentation_grouping":
        planned: list[str] = []
        for index, chapter in enumerate(chapters):
            source_ids = [
                str(value).strip()
                for value in chapter.get("source_chapter_ids") or []
                if str(value).strip()
            ]
            if not source_ids:
                issues.append(
                    f"PRESENTATION_CHAPTER_SOURCE_MAPPING_MISSING: chapters.{index} must map to one or more source chapters"
                )
                continue
            planned.extend(source_ids)
            operation = str(chapter.get("structural_operation") or "").strip()
            if len(source_ids) > 1 and operation != "group_adjacent_source_chapters":
                issues.append(
                    "PRESENTATION_CHAPTER_GROUP_OPERATION_MISSING: "
                    f"chapters.{index} groups {source_ids} without group_adjacent_source_chapters"
                )
        if source_chapters and planned != source_chapters:
            issues.append(
                "PRESENTATION_SOURCE_CHAPTER_MAPPING_CONFLICT: presentation chapter groups must cover each source chapter once in source order; "
                f"expected {source_chapters}, got {planned}"
            )

    if str(plan.get("presentation_structure_mode") or "").strip() != "formal_chaptered":
        return issues, warnings

    chapter_count = len(chapters)
    exception_reason = str(plan.get("chapter_count_exception") or "").strip()
    if chapter_count > 6 and not exception_reason:
        issues.append(
            "PRESENTATION_CHAPTER_COUNT_EXCESSIVE: formal decks may use at most six presentation chapters unless chapter_count_exception is documented"
        )
    elif chapter_count > 4:
        warnings.append(
            "PRESENTATION_CHAPTER_COUNT_HIGH: formal decks should normally target no more than four presentation chapters"
        )

    roles = [str(page.get("page_role") or page.get("page_type") or "").strip() for page in pages]
    if not roles or roles[0] != "cover":
        issues.append("PRESENTATION_COVER_MISSING: formal deck sequence must start with a cover page")
    if len(roles) < 2 or roles[1] not in {"agenda", "contents"}:
        issues.append("PRESENTATION_AGENDA_MISSING: formal deck sequence must place an agenda after the cover")
    if not roles or roles[-1] not in {"ending", "closing"}:
        issues.append("PRESENTATION_ENDING_MISSING: formal deck sequence must end with an ending page")

    page_index = {id(page): index for index, page in enumerate(pages)}
    for chapter in chapters:
        chapter_id = str(chapter.get("id") or "?").strip()
        owned = [page for page in pages if str(page.get("chapter_id") or "").strip() == chapter_id]
        transition_indices = [
            page_index[id(page)]
            for page in owned
            if str(page.get("page_role") or page.get("page_type") or "").strip()
            in _CHAPTER_TRANSITION_ROLES
        ]
        content_indices = [
            page_index[id(page)]
            for page in owned
            if str(page.get("page_role") or page.get("page_type") or "").strip()
            not in _STRUCTURAL_PAGE_ROLES
        ]
        if chapter_count > 1:
            if len(transition_indices) != 1:
                issues.append(
                    f"PRESENTATION_CHAPTER_TRANSITION_COUNT: chapter {chapter_id} requires exactly one transition page"
                )
            elif content_indices and transition_indices[0] > min(content_indices):
                issues.append(
                    f"PRESENTATION_CHAPTER_TRANSITION_ORDER: chapter {chapter_id} transition must precede its content pages"
                )
        elif transition_indices:
            issues.append(
                "PRESENTATION_SINGLE_CHAPTER_TRANSITION_FORBIDDEN: a single-chapter deck must enter content directly after the agenda"
            )
        if len(content_indices) == 1:
            warnings.append(
                f"PRESENTATION_CHAPTER_THIN: chapter {chapter_id} has only one content page; merge it with an adjacent presentation chapter unless it has a distinct decision role"
            )
        elif chapter_count > 4 and len(content_indices) == 2:
            warnings.append(
                f"PRESENTATION_CHAPTER_FRAGMENTED: chapter {chapter_id} has only two content pages while the deck exceeds four chapters; review adjacent chapter grouping"
            )
    return issues, warnings


def _narrative_contract_diagnostics(
    plan: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Check PLAN structure without requiring AUTHOR-owned narrative fields."""

    issues: list[str] = []
    warnings: list[str] = []
    chapters = [item for item in plan.get("chapters") or [] if isinstance(item, dict)]
    pages = [item for item in plan.get("pages") or [] if isinstance(item, dict)]
    if not chapters:
        return issues, warnings

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
        if title and _title_is_claim_like(title):
            warnings.append(
                "NARRATIVE_TITLE_CLAIM_LIKE: "
                f"page {page_id} uses a long sentence-like title; evidence={page_id}.title; "
                "suggested_action=use a concise formal topic title and move the bounded judgment to subtitle/message"
            )
        if title and len(_normalized_review_text(title)) >= 4:
            title_terms = _narrative_terms(title)
            subject_terms = _page_subject_terms(page)
            if title_terms and subject_terms and not (title_terms & subject_terms):
                warnings.append(
                    "NARRATIVE_TITLE_PAGE_SUBJECT_MISMATCH: "
                    f"page {page_id} title has no identifiable overlap with the page-wide subject; "
                    f"evidence={page_id}.title,{page_id}.subtitle,{page_id}.question,{page_id}.message,{page_id}.logic,{page_id}.content; "
                    "suggested_action=use a concise formal title that names the page's overall topic without restating one judgment"
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

    if True:
        items = foundation_items_by_id(foundation)
        known_refs = set(items).union(
            str(asset.get("id"))
            for asset in foundation.get("source_assets") or []
            if isinstance(asset, dict) and asset.get("id")
        )
        issues: list[str] = []
        for index, page in enumerate(plan.get("pages") or []):
            if not isinstance(page, dict):
                continue
            role = _narrative_text(page.get("page_role")) or _narrative_text(page.get("page_type"))
            if role in _STRUCTURAL_PAGE_ROLES:
                continue
            page_id = _narrative_text(page.get("id")) or f"#{index}"
            refs = [str(ref).strip() for ref in page.get("source_refs") or [] if str(ref).strip()]
            if not refs:
                issues.append(f"pages.{index} ({page_id}): LEAN_SOURCE_BOUNDARY_MISSING")
                continue
            unknown = sorted(set(refs) - known_refs)
            if unknown:
                issues.append(f"pages.{index} ({page_id}): LEAN_SOURCE_REF_UNKNOWN: {unknown}")
        return issues

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
        if True:
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
    present = sorted(_PLAN_FORBIDDEN_AUTHOR_FIELDS.intersection(plan))
    if present:
        issues.append(f"PLAN_AUTHOR_FIELDS_FORBIDDEN: move AUTHOR fields out of Deck Plan: {present}")
    for index, chapter in enumerate(plan.get("chapters") or []):
        if not isinstance(chapter, dict):
            continue
        present = sorted(_PLAN_FORBIDDEN_CHAPTER_AUTHOR_FIELDS.intersection(chapter))
        if present:
            issues.append(f"chapters.{index}: PLAN_CHAPTER_AUTHOR_FIELDS_FORBIDDEN: {present}")
    for index, page in enumerate(plan.get("pages") or []):
        if not isinstance(page, dict):
            continue
        present = sorted(_PLAN_FORBIDDEN_PAGE_AUTHOR_FIELDS.intersection(page))
        if present:
            issues.append(f"pages.{index} ({page.get('id') or '?'}): PLAN_PAGE_AUTHOR_FIELDS_FORBIDDEN: {present}")
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
        warnings.append("source_structure_mode: missing; ordinary source-driven plans should declare 'presentation_grouping'")
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

    presentation_issues, presentation_warnings = _presentation_structure_diagnostics(
        plan, source_chapters
    )
    issues.extend(presentation_issues)
    warnings.extend(presentation_warnings)

    audience_scope = plan.get("audience_scope", "unspecified")
    for index, page in enumerate(plan.get("pages") or []):
        if not isinstance(page, dict):
            continue
        page_id = page.get("id") or f"#{index}"
        if True:
            # Lean planning excludes AUTHOR prose and visual selections, but a
            # Foundation may still require strict source consumption.  Validate
            # that compiler-owned contract before approval so AUTHOR is never
            # started on a plan that cannot prove semantic preservation.
            for consumption_issue in _audit_source_consumption_definition(
                page, items, foundation
            ):
                issues.append(f"pages.{index} ({page_id}): {consumption_issue}")
            for unit_issue in _audit_unit_consumption_definition(
                page, items, foundation
            ):
                issues.append(f"pages.{index} ({page_id}): {unit_issue}")
            evidence = _support_items(sorted(_page_evidence_ids(page)), items)
            internal = [item.get("id", "?") for item in evidence if effective_visibility(item) == "internal_only"]
            if audience_scope == "external" and internal and page.get("visibility_decision") not in (
                "internal_only_used_as_hidden_support", "user_approved_exposure"
            ):
                issues.append(f"pages.{index} ({page_id}): external audience uses internal-only evidence {sorted(internal)} without an explicit visibility_decision")
            continue

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

__all__ = ['_adjacent_plan_duplication_warnings', '_narrative_contract_diagnostics', '_source_argument_binding_issues', '_scope_chapters', 'audit_deck_plan']
