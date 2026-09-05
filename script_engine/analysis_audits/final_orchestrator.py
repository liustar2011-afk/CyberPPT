"""Focused orchestration for the deterministic Final Script semantic audit."""
from __future__ import annotations

from .common import *
from .composed_trace import hard_finding_messages, trace_composed
from .final_authoring import (
    _audit_authored_content_coverage,
    _authored_bare_label_detail_issues,
    _author_execution_issues,
    _onscreen_expression_warnings,
    _slide_text,
)
from .final_deck import (
    _normalize_source_chapter_title,
    _source_text_for_refs,
    _whole_deck_authoring_warnings,
)
from .final_lean import (
    _audit_lean_authored_source_consumption,
    _audit_lean_onscreen_full_copy_alignment,
    _audit_lean_relationship_visibility,
)
from .final_fidelity import faithful_relation_promotion_issues
from .final_onscreen import (
    _audit_authored_onscreen_composition,
    _audit_authored_onscreen_contract,
    _audit_self_reading_density,
)


def audit_final_script(
    final_script: dict[str, Any],
    plan: dict[str, Any],
    foundation: dict[str, Any],
) -> tuple[list[str], list[str]]:
    issues: list[str] = audit_final_internal_expert_voice(final_script, plan)
    warnings: list[str] = []
    issues.extend(hard_finding_messages(trace_composed(final_script, foundation)))
    items = foundation_items_by_id(foundation)
    pages = {p.get("id"): p for p in (plan.get("pages") or []) if isinstance(p, dict) and isinstance(p.get("id"), str)}
    chapters = {c.get("id"): c for c in (plan.get("chapters") or []) if isinstance(c, dict) and isinstance(c.get("id"), str)}
    structure = {x.get("id"): x for x in (foundation.get("source_structure") or []) if isinstance(x, dict) and isinstance(x.get("id"), str)}
    audience_scope = plan.get("audience_scope", "unspecified")
    preserve_structure = plan.get("source_structure_mode") == "preserve"
    delivery_mode = str((final_script.get("deck") or {}).get("delivery_mode") or plan.get("delivery_mode") or "self_read")
    plan_authoring_mode = str(plan.get("authoring_mode") or "faithful")
    final_authoring_mode = str(
        (final_script.get("deck") or {}).get("authoring_mode") or plan_authoring_mode
    )
    if final_authoring_mode == "analytical" and plan_authoring_mode != "analytical":
        issues.append(
            "AUTHORING_MODE_NOT_AUTHORIZED: final script requests analytical mode "
            "without analytical mode in the approved Deck Plan"
        )

    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = slide.get("id") or f"#{index}"
        page = pages.get(slide_id)
        if page is None:
            warnings.append(f"slides.{index} ({slide_id}): no matching deck-plan page; semantic inheritance cannot be audited")
            continue
        final_text = _slide_text(slide)
        plan_text = _page_text(page)
        evidence_ids = _page_evidence_ids(page)
        evidence = _support_items(sorted(evidence_ids), items)
        if final_authoring_mode == "faithful":
            issues.extend(
                f"slides.{index} ({slide_id}): {issue}"
                for issue in faithful_relation_promotion_issues(slide, evidence)
            )

        plan_model = str((page.get("analysis_basis") or {}).get("model") or "").lower()
        plan_logic = str(page.get("logic") or "")
        plan_is_classification = any(token in plan_model for token in ("classification", "taxonomy", "typology")) or "分类" in plan_logic
        plan_allows_progression = bool(PROGRESSION_RE.search(plan_text) or any(token in plan_model for token in ("progression", "maturity")))
        if plan_is_classification and not plan_allows_progression and PROGRESSION_RE.search(final_text):
            issues.append(f"slides.{index} ({slide_id}): AUTHOR upgraded a classification/taxonomy plan into a progression chain")

        if _has_optionality(evidence) and not _preserves_optionality(final_text):
            issues.append(f"slides.{index} ({slide_id}): final script lost source optionality; it must preserve independent choice and progressive deepening")

        group_issue = _group_strength_issue(str(slide.get("core_message") or ""), evidence)
        if group_issue:
            issues.append(f"slides.{index} ({slide_id}): {group_issue}")

        internal = [item for item in evidence if effective_visibility(item) == "internal_only"]
        if audience_scope == "external" and internal:
            exposed: list[str] = []
            for item in internal:
                item_text = _item_text(item)
                values = [str(item.get("value") or "")]
                for match in re.findall(r"\d+(?:\.\d+)?%?(?:至|-|—)\d+(?:\.\d+)?%?|\d+(?:\.\d+)?%", item_text):
                    values.append(match)
                normalized_final = final_text.replace("至", "-").replace("—", "-")
                if any(value and value.replace("至", "-").replace("—", "-") in normalized_final for value in values):
                    exposed.append(str(item.get("id") or "?"))
            if exposed:
                issues.append(f"slides.{index} ({slide_id}): external final script exposes internal-only evidence {sorted(set(exposed))}")

        if GAP_RE.search(final_text):
            source_text = _source_text_for_refs(page.get("source_refs") or [], foundation)
            if not GAP_RE.search(plan_text) and not GAP_RE.search(source_text):
                issues.append(f"slides.{index} ({slide_id}): final script introduces a current-vs-target gap judgment without a source or plan baseline")

        for composition_issue in _audit_authored_onscreen_composition(page, slide):
            issues.append(f"slides.{index} ({slide_id}): {composition_issue}")
        for density_issue in _audit_self_reading_density(delivery_mode, page, slide):
            issues.append(f"slides.{index} ({slide_id}): {density_issue}")
        for contract_issue in _audit_authored_onscreen_contract(page, slide, items):
            issues.append(f"slides.{index} ({slide_id}): {contract_issue}")
        for consumption_issue in _audit_lean_authored_source_consumption(page, slide, items, foundation):
            issues.append(f"slides.{index} ({slide_id}): {consumption_issue}")
        for alignment_issue in _audit_lean_onscreen_full_copy_alignment(slide):
            issues.append(f"slides.{index} ({slide_id}): {alignment_issue}")
        for relationship_issue in _audit_lean_relationship_visibility(slide):
            issues.append(f"slides.{index} ({slide_id}): {relationship_issue}")
        for coverage_issue in _audit_authored_content_coverage(page, slide):
            issues.append(f"slides.{index} ({slide_id}): {coverage_issue}")
        for detail_issue in _authored_bare_label_detail_issues(page, slide, items):
            issues.append(
                f"slides.{index} ({slide_id}): ONSCREEN_SOURCE_DETAIL_COLLAPSED_TO_LABEL: "
                f"{detail_issue}"
            )
        for author_issue in _author_execution_issues(delivery_mode, page, slide, items):
            issues.append(f"slides.{index} ({slide_id}): {author_issue}")
        warnings.extend(
            f"slides.{index} ({slide_id}): {warning}"
            for warning in _onscreen_expression_warnings(page, slide)
        )

        if preserve_structure and slide.get("page_type") == "chapter":
            chapter_id = slide.get("chapter_id")
            chapter = chapters.get(chapter_id) if isinstance(chapter_id, str) else None
            source_ids = chapter.get("source_chapter_ids") if isinstance(chapter, dict) else None
            if source_ids and len(source_ids) == 1:
                node = structure.get(source_ids[0])
                if isinstance(node, dict) and isinstance(node.get("title"), str):
                    expected = _normalize_source_chapter_title(node["title"])
                    actual = str(slide.get("title") or "").strip()
                    if actual and expected and actual != expected:
                        issues.append(f"slides.{index} ({slide_id}): source_structure_mode='preserve' requires chapter title '{expected}', got '{actual}'")

    warnings.extend(_whole_deck_authoring_warnings(final_script))
    return issues, warnings


__all__ = ["audit_final_script"]
