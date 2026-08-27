"""V2 page contribution, storyline, and source-relation validation."""

from __future__ import annotations

from .chapter_scope import validate_page_sequence_fields, validate_topic_partition_fields
from .evidence import dict_items, string_list
from .roles import ArgumentFlowIssue, SEMANTIC_CONTRIBUTION_FIELDS
from .storyline import GENERIC_TRANSITIONS, STORYLINE_PAGE_FIELDS


def validate_source_relation_fields(outline: dict[str, object]) -> list[ArgumentFlowIssue]:
    """Validate v2 content contracts without imposing page or claim taxonomies."""

    issues = validate_topic_partition_fields(outline)
    issues.extend(validate_page_sequence_fields(outline))
    storyline_required = outline.get("storyline_contract_mode") == "required"
    pages = dict_items(outline, "pages")
    content_pages = [page for page in pages if page.get("page_type") == "content"]
    storyline = outline.get("storyline")
    missions = storyline.get("chapter_missions") if isinstance(storyline, dict) else None
    mission_items = [item for item in missions if isinstance(item, dict)] if isinstance(missions, list) else []
    if storyline_required:
        required_root = (
            "theme",
            "decision_destination",
            "story_arc",
            "chapter_missions",
            "selection_rules",
            "exclusion_rules",
            "page_rules",
            "pacing",
        )
        if not isinstance(storyline, dict) or any(not storyline.get(field) for field in required_root):
            issues.append(
                ArgumentFlowIssue(
                    "STORYLINE_CONTRACT_MISSING",
                    "A required Storyline Director contract must define theme, decision destination, story arc, chapter missions, selection and exclusion rules, page rules, and pacing.",
                    retry_strategy="rebuild_from_storyline_director",
                )
            )
        else:
            content_chapters = {str(page.get("chapter_id") or "") for page in content_pages}
            mission_chapters = {str(item.get("chapter_id") or "") for item in mission_items}
            if content_chapters != mission_chapters:
                issues.append(
                    ArgumentFlowIssue(
                        "STORYLINE_CHAPTER_COVERAGE_MISMATCH",
                        "Storyline Director chapter missions must cover exactly the chapters that contain content pages.",
                        retry_strategy="reconcile_storyline_chapter_missions",
                    )
                )
            for mission in mission_items:
                chapter_id = str(mission.get("chapter_id") or "")
                maximum = mission.get("max_content_pages")
                actual = sum(1 for page in content_pages if str(page.get("chapter_id") or "") == chapter_id)
                if isinstance(maximum, int) and actual > maximum:
                    issues.append(
                        ArgumentFlowIssue(
                            "STORYLINE_CHAPTER_PACING_EXCEEDED",
                            "A chapter exceeds the Storyline Director's maximum content-page budget.",
                            tuple(str(page.get("page_id") or "") for page in content_pages if str(page.get("chapter_id") or "") == chapter_id),
                            retry_strategy="compress_chapter_to_director_budget",
                        )
                    )
            pacing = storyline.get("pacing")
            if isinstance(pacing, dict):
                minimum = pacing.get("min_total_pages")
                maximum = pacing.get("max_total_pages")
                if isinstance(minimum, int) and isinstance(maximum, int) and not minimum <= len(pages) <= maximum:
                    issues.append(
                        ArgumentFlowIssue(
                            "STORYLINE_TOTAL_PACING_OUT_OF_RANGE",
                            "Total pages must remain inside the Storyline Director's approved pacing range.",
                            retry_strategy="rebuild_to_director_pacing",
                        )
                    )
    previous_by_chapter: dict[str, str] = {}
    for page in pages:
        if page.get("page_type") != "content":
            continue
        page_id = str(page.get("page_id") or "")
        chapter_id = str(page.get("chapter_id") or "")
        if storyline_required:
            missing_storyline = [field for field in STORYLINE_PAGE_FIELDS if not str(page.get(field) or "").strip()]
            generic_storyline = [
                field for field in ("transition_from_previous", "transition_to_next")
                if str(page.get(field) or "").strip() in GENERIC_TRANSITIONS
            ]
            if missing_storyline or generic_storyline:
                issues.append(
                    ArgumentFlowIssue(
                        "PAGE_STORYLINE_CONTRACT_INCOMPLETE",
                        "Each content page must state a concrete storyline role and specific transitions from the preceding question and to the following question; generic transition labels are invalid.",
                        (page_id,) if page_id else (),
                        retry_strategy="complete_page_storyline_contract",
                    )
                )
            previous = previous_by_chapter.get(chapter_id)
            prerequisites = string_list(page, "prerequisite_pages")
            if previous is not None and prerequisites != [previous]:
                issues.append(
                    ArgumentFlowIssue(
                        "PAGE_STORYLINE_PREDECESSOR_MISMATCH",
                        "Within a chapter, each content page must explicitly depend on the immediately preceding content page so the story cannot silently jump or reorder.",
                        (page_id,),
                        failed_edges=((previous, page_id),),
                        retry_strategy="repair_page_storyline_sequence",
                    )
                )
            previous_by_chapter[chapter_id] = page_id
        missing = [field for field in SEMANTIC_CONTRIBUTION_FIELDS if not page.get(field)]
        if missing:
            issues.append(
                ArgumentFlowIssue(
                    "SEMANTIC_CONTRIBUTION_FIELDS_MISSING",
                    "V2 content pages must declare page_mission, core_message, content_units, content_relations, new_value_vs_previous, and reserved_for_later.",
                    (page_id,) if page_id else (),
                    retry_strategy="complete_source_relation_contract",
                )
            )
        page_sources = set(string_list(page, "source_refs"))
        units = page.get("content_units")
        unit_sources: set[str] = set()
        if isinstance(units, list):
            for unit in units:
                refs = string_list(unit, "source_refs") if isinstance(unit, dict) else []
                unit_sources.update(refs)
                if (
                    not isinstance(unit, dict)
                    or not str(unit.get("statement") or "").strip()
                    or not refs
                    or not set(refs).issubset(page_sources)
                    or str(unit.get("role") or "") not in {"primary", "supporting", "boundary"}
                ):
                    issues.append(
                        ArgumentFlowIssue(
                            "CONTENT_UNIT_INVALID",
                            "Each content unit must state source-supported content, cite only page source_refs, and use primary, supporting, or boundary role.",
                            (page_id,) if page_id else (),
                            retry_strategy="reconcile_content_units",
                        )
                    )
                    break
        detail_sources = set(string_list(page, "detail_refs"))
        if not detail_sources.issubset(page_sources) or bool(detail_sources & unit_sources):
            issues.append(
                ArgumentFlowIssue(
                    "DETAIL_REFS_INVALID",
                    "detail_refs must be a subset of page source_refs and must not also appear as standalone content-unit evidence.",
                    (page_id,) if page_id else (),
                    tuple(sorted((detail_sources - page_sources) | (detail_sources & unit_sources))),
                    retry_strategy="separate_retained_detail_from_page_structure",
                )
            )
        unclassified = page_sources - unit_sources - detail_sources
        if unclassified:
            issues.append(
                ArgumentFlowIssue(
                    "PAGE_EVIDENCE_CLASSIFICATION_INCOMPLETE",
                    "Every page source must be classified as content-unit evidence or retained detail; full traceability does not require equal visual weight.",
                    (page_id,) if page_id else (),
                    tuple(sorted(unclassified)),
                    retry_strategy="classify_page_evidence_weight",
                )
            )
        relations = page.get("content_relations")
        if isinstance(relations, list):
            for relation in relations:
                refs = string_list(relation, "source_refs") if isinstance(relation, dict) else []
                subject = str(relation.get("subject") or "").strip() if isinstance(relation, dict) else ""
                objects = relation.get("objects") if isinstance(relation, dict) else None
                if isinstance(objects, str):
                    objects = [objects] if objects.strip() else []
                valid_objects = isinstance(objects, list) and bool(objects) and all(str(item).strip() for item in objects)
                if not subject or not valid_objects:
                    issues.append(
                        ArgumentFlowIssue(
                            "CONTENT_RELATION_ENDPOINTS_MISSING",
                            "Each content relation must name a non-empty subject and one or more non-empty objects so the semantic relation is human-readable and machine-consumable.",
                            (page_id,) if page_id else (),
                            tuple(refs),
                            retry_strategy="complete_content_relation_endpoints",
                        )
                    )
                if not isinstance(relation, dict) or not refs or not set(refs).issubset(page_sources):
                    issues.append(
                        ArgumentFlowIssue(
                            "CONTENT_RELATION_REFS_INVALID",
                            "Each content relation must cite a non-empty subset of the page source_refs.",
                            (page_id,) if page_id else (),
                            tuple(sorted(set(refs) - page_sources)),
                            retry_strategy="reconcile_content_relations",
                        )
                    )
                    break
        boundary_sources = set(string_list(page, "boundary_refs"))
        if not boundary_sources.issubset(page_sources):
            issues.append(
                ArgumentFlowIssue(
                    "BOUNDARY_REFS_INVALID",
                    "boundary_refs must be a subset of page source_refs.",
                    (page_id,) if page_id else (),
                    tuple(sorted(boundary_sources - page_sources)),
                    retry_strategy="reconcile_content_units",
                )
            )
    return issues


__all__ = ["validate_source_relation_fields"]
