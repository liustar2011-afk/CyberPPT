"""Chapter topic scope and intra-chapter ordering contracts."""

from __future__ import annotations

from .evidence import dict_items, string_list
from .roles import ArgumentFlowIssue
from .storyline import PAGE_ORDER_PRINCIPLES


def _topic_partition_required(outline: dict[str, object]) -> bool:
    mode = str(outline.get("topic_partition_mode") or "").strip()
    if mode == "disabled":
        return False
    if mode == "required":
        return True
    return (
        outline.get("schema") == "cyberppt.outline.v2"
        and outline.get("storyline_contract_mode") == "required"
    )


def validate_topic_partition_fields(outline: dict[str, object]) -> list[ArgumentFlowIssue]:
    if not _topic_partition_required(outline):
        return []
    issues: list[ArgumentFlowIssue] = []
    pages = dict_items(outline, "pages")
    content_pages = [page for page in pages if page.get("page_type") == "content"]
    storyline = outline.get("storyline")
    missions = storyline.get("chapter_missions") if isinstance(storyline, dict) else None
    mission_items = [item for item in missions if isinstance(item, dict)] if isinstance(missions, list) else []
    missions_by_chapter = {
        str(item.get("chapter_id") or ""): item
        for item in mission_items
        if str(item.get("chapter_id") or "")
    }
    chapter_topic_scopes: dict[str, set[str]] = {}
    for chapter_id in sorted({str(page.get("chapter_id") or "") for page in content_pages}):
        mission = missions_by_chapter.get(chapter_id)
        raw_categories = mission.get("topic_categories") if mission else None
        categories = (
            [str(value).strip() for value in raw_categories if str(value).strip()]
            if isinstance(raw_categories, list) else []
        )
        if not categories:
            chapter_pages = tuple(
                str(page.get("page_id") or "")
                for page in content_pages
                if str(page.get("chapter_id") or "") == chapter_id
            )
            issues.append(
                ArgumentFlowIssue(
                    "CHAPTER_TOPIC_SCOPE_MISSING",
                    "Each content chapter must have a storyline chapter mission with a non-empty topic_categories list that defines its coherent business and argument scope.",
                    chapter_pages,
                    retry_strategy="define_chapter_topic_scope",
                )
            )
        else:
            chapter_topic_scopes[chapter_id] = set(categories)

    pages_by_chapter_topic: dict[tuple[str, str], list[dict[str, object]]] = {}
    for page in content_pages:
        page_id = str(page.get("page_id") or "")
        chapter_id = str(page.get("chapter_id") or "")
        page_topic = str(page.get("topic_category") or "").strip()
        if not page_topic:
            issues.append(
                ArgumentFlowIssue(
                    "PAGE_TOPIC_CATEGORY_MISSING",
                    "Each content page must declare one authoritative topic_category so unrelated themes cannot be aggregated on the same page.",
                    (page_id,) if page_id else (),
                    retry_strategy="assign_single_page_topic",
                )
            )
            continue
        pages_by_chapter_topic.setdefault((chapter_id, page_topic), []).append(page)
        chapter_scope = chapter_topic_scopes.get(chapter_id)
        if chapter_scope is not None and page_topic not in chapter_scope:
            issues.append(
                ArgumentFlowIssue(
                    "PAGE_TOPIC_OUTSIDE_CHAPTER_SCOPE",
                    "A page topic_category must belong to its storyline chapter mission's topic_categories.",
                    (page_id,) if page_id else (),
                    retry_strategy="reconcile_page_and_chapter_topics",
                )
            )
        units = page.get("content_units")
        if isinstance(units, list) and any(
            not isinstance(unit, dict)
            or str(unit.get("topic_category") or "").strip() != page_topic
            for unit in units
        ):
            issues.append(
                ArgumentFlowIssue(
                    "PAGE_TOPIC_MIXED",
                    "Every content unit must declare the same topic_category as its page; different page topics must be split instead of aggregated.",
                    (page_id,) if page_id else (),
                    retry_strategy="split_mixed_page_topics",
                )
            )

    for topic_pages in pages_by_chapter_topic.values():
        if len(topic_pages) < 2:
            continue
        if any(not str(page.get("topic_split_reason") or "").strip() for page in topic_pages):
            issues.append(
                ArgumentFlowIssue(
                    "TOPIC_CATEGORY_SPLIT_WITHOUT_REASON",
                    "When one topic_category spans multiple pages in a chapter, every page in that group must state a page-specific topic_split_reason based on a different business object, relation, status, decision task, or audience question.",
                    tuple(str(page.get("page_id") or "") for page in topic_pages),
                    retry_strategy="justify_or_merge_same_topic_pages",
                )
            )
    return issues


def _page_sequence_required(outline: dict[str, object]) -> bool:
    mode = str(outline.get("page_sequence_mode") or "").strip()
    if mode == "disabled":
        return False
    if mode == "required":
        return True
    return (
        outline.get("schema") == "cyberppt.outline.v2"
        and outline.get("storyline_contract_mode") == "required"
    )


def validate_page_sequence_fields(outline: dict[str, object]) -> list[ArgumentFlowIssue]:
    if not _page_sequence_required(outline):
        return []
    issues: list[ArgumentFlowIssue] = []
    pages = dict_items(outline, "pages")
    content_pages = [page for page in pages if page.get("page_type") == "content"]
    storyline = outline.get("storyline")
    missions = storyline.get("chapter_missions") if isinstance(storyline, dict) else None
    mission_items = [item for item in missions if isinstance(item, dict)] if isinstance(missions, list) else []
    missions_by_chapter = {
        str(item.get("chapter_id") or ""): item
        for item in mission_items
        if str(item.get("chapter_id") or "")
    }
    raw_chapter_orders = outline.get("chapter_page_orders")
    chapter_order_items = [item for item in raw_chapter_orders if isinstance(item, dict)] if isinstance(raw_chapter_orders, list) else []
    orders_by_chapter = {
        str(item.get("chapter_id") or ""): item
        for item in chapter_order_items
        if str(item.get("chapter_id") or "")
    }
    content_chapters: dict[str, list[dict[str, object]]] = {}
    for page in content_pages:
        content_chapters.setdefault(str(page.get("chapter_id") or ""), []).append(page)
        if not str(page.get("page_order_reason") or "").strip():
            page_id = str(page.get("page_id") or "")
            issues.append(
                ArgumentFlowIssue(
                    "PAGE_ORDER_REASON_MISSING",
                    "Each content page must explain why it occupies this position in the chapter's understanding and dependency sequence.",
                    (page_id,) if page_id else (),
                    retry_strategy="explain_page_sequence_position",
                )
            )

    declared_chapters = [str(item.get("chapter_id") or "") for item in chapter_order_items]
    if len(declared_chapters) != len(set(declared_chapters)) or set(declared_chapters) != set(content_chapters):
        issues.append(
            ArgumentFlowIssue(
                "CHAPTER_PAGE_ORDER_COVERAGE_MISMATCH",
                "chapter_page_orders must contain exactly one entry for every content chapter and no duplicate or extra chapter entries.",
                tuple(
                    str(page.get("page_id") or "")
                    for chapter_pages in content_chapters.values()
                    for page in chapter_pages
                ),
                retry_strategy="reconcile_chapter_page_order_coverage",
            )
        )

    for chapter_id, chapter_pages in content_chapters.items():
        page_ids = [str(page.get("page_id") or "") for page in chapter_pages]
        page_topics = [str(page.get("topic_category") or "").strip() for page in chapter_pages]
        mission = missions_by_chapter.get(chapter_id)
        order_logic = orders_by_chapter.get(chapter_id)
        if not isinstance(order_logic, dict):
            issues.append(
                ArgumentFlowIssue(
                    "CHAPTER_PAGE_ORDER_LOGIC_MISSING",
                    "Each content chapter must have one chapter_page_orders entry with ordering_principles, ordered_topic_categories, ordered_page_ids, and rationale.",
                    tuple(page_ids),
                    retry_strategy="define_chapter_page_order",
                )
            )
            continue
        principles = string_list(order_logic, "ordering_principles")
        invalid_principles = sorted(set(principles) - PAGE_ORDER_PRINCIPLES)
        if not principles or invalid_principles:
            issues.append(
                ArgumentFlowIssue(
                    "CHAPTER_PAGE_ORDER_PRINCIPLE_INVALID",
                    "chapter_page_orders.ordering_principles must use one or more supported source- and audience-grounded ordering principles.",
                    tuple(page_ids),
                    retry_strategy="select_supported_page_order_principles",
                )
            )
        declared_page_ids = string_list(order_logic, "ordered_page_ids")
        if declared_page_ids != page_ids:
            issues.append(
                ArgumentFlowIssue(
                    "CHAPTER_PAGE_ORDER_MISMATCH",
                    "chapter_page_orders.ordered_page_ids must exactly match the actual content-page order in the chapter.",
                    tuple(page_ids),
                    retry_strategy="reconcile_declared_and_actual_page_order",
                )
            )
        declared_topics = string_list(order_logic, "ordered_topic_categories")
        mission_topics = string_list(mission or {}, "topic_categories")
        actual_topic_order = list(dict.fromkeys(topic for topic in page_topics if topic))
        if (
            not declared_topics
            or len(declared_topics) != len(set(declared_topics))
            or set(declared_topics) != set(mission_topics)
            or declared_topics != actual_topic_order
        ):
            issues.append(
                ArgumentFlowIssue(
                    "CHAPTER_TOPIC_ORDER_MISMATCH",
                    "ordered_topic_categories must uniquely cover the chapter topic scope and match the topics' first-appearance order in the actual pages.",
                    tuple(page_ids),
                    retry_strategy="reconcile_chapter_topic_order",
                )
            )
        if not str(order_logic.get("rationale") or "").strip():
            issues.append(
                ArgumentFlowIssue(
                    "CHAPTER_PAGE_ORDER_RATIONALE_MISSING",
                    "chapter_page_orders.rationale must explain why the selected principles fit this chapter's source argument and audience question.",
                    tuple(page_ids),
                    retry_strategy="explain_chapter_page_order",
                )
            )
        positions_by_topic: dict[str, list[int]] = {}
        for index, topic in enumerate(page_topics):
            if topic:
                positions_by_topic.setdefault(topic, []).append(index)
        fragmented_topics = [
            topic
            for topic, positions in positions_by_topic.items()
            if positions != list(range(positions[0], positions[-1] + 1))
        ]
        if fragmented_topics:
            issues.append(
                ArgumentFlowIssue(
                    "CHAPTER_TOPIC_SEQUENCE_FRAGMENTED",
                    "Pages with the same topic_category must remain contiguous inside a chapter instead of reappearing after another topic.",
                    tuple(page_ids),
                    retry_strategy="restore_contiguous_topic_sequence",
                )
            )
    return issues


__all__ = ["validate_page_sequence_fields", "validate_topic_partition_fields"]
