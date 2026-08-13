"""Authoring-oriented Outline audit rules."""

from __future__ import annotations

import re

from cyberppt.outline_audit_shared import AuditIssue, _page_id, _page_mission, _text


QUESTION_TERMS = ("什么", "哪些", "如何", "为何", "为什么", "是否", "谁", "何时", "怎样", "多少", "哪")


def _editorial_control_issues(
    outline: dict[str, object], pages: list[dict[str, object]]
) -> list[AuditIssue]:
    """Audit audience-facing page separation without replacing source semantics."""

    if outline.get("editorial_control_mode") != "required":
        return []
    issues: list[AuditIssue] = []
    question_pages: dict[str, list[str]] = {}
    for page in pages:
        if page.get("page_type") != "content":
            continue
        page_id = _page_id(page)
        question = str(page.get("audience_question") or "").strip()
        exclusions = page.get("must_not_include")
        split_risk = str(page.get("split_risk") or "").strip()
        split_reason = str(page.get("split_risk_reason") or "").strip()

        if not question:
            issues.append(AuditIssue(
                "AUDIENCE_QUESTION_MISSING",
                "Each content page must state the concrete audience question it answers.",
                (page_id,),
                "define_audience_question",
            ))
        else:
            normalized = _text(question)
            question_pages.setdefault(normalized, []).append(page_id)
            if (
                normalized == _text(_page_mission(page))
                or re.search(r"本页(?:说明|介绍|讲述|回答)", question)
                or not any(term in question for term in QUESTION_TERMS)
            ):
                issues.append(AuditIssue(
                    "AUDIENCE_QUESTION_NOT_CONCRETE",
                    "audience_question must be a real audience question, not a restatement of page_mission or a page-description placeholder.",
                    (page_id,),
                    "rewrite_audience_question",
                ))

        if (
            not isinstance(exclusions, list)
            or not exclusions
            or any(not str(item).strip() for item in exclusions)
        ):
            issues.append(AuditIssue(
                "MUST_NOT_INCLUDE_MISSING",
                "Each content page must name at least one adjacent topic, claim, or detail that must remain outside the page.",
                (page_id,),
                "separate_adjacent_page_scope",
            ))

        if split_risk not in {"low", "medium", "high"}:
            issues.append(AuditIssue(
                "SPLIT_RISK_INVALID",
                "split_risk must be low, medium, or high.",
                (page_id,),
                "assess_page_split_risk",
            ))
        elif split_risk in {"medium", "high"} and not split_reason:
            issues.append(AuditIssue(
                "SPLIT_RISK_REASON_MISSING",
                "Medium or high split risk requires a concrete explanation of the competing question, relation, or visual center.",
                (page_id,),
                "explain_page_split_risk",
            ))
        if split_risk == "high":
            issues.append(AuditIssue(
                "HIGH_SPLIT_RISK_UNRESOLVED",
                "A high-risk page must be split or restructured before the outline can pass.",
                (page_id,),
                "split_overloaded_page",
            ))

    for page_ids in question_pages.values():
        if len(page_ids) >= 3:
            issues.append(AuditIssue(
                "AUDIENCE_QUESTION_REUSED",
                "The same audience question is reused across three or more pages; aggregate them or make each page answer a materially different question.",
                tuple(page_ids),
                "differentiate_audience_questions",
            ))
    return issues
def _author_driven_editorial_issues(
    outline: dict[str, object], pages: list[dict[str, object]]
) -> list[AuditIssue]:
    """Keep deterministic candidate generation separate from authorship.

    The compiler may inventory evidence and propose pages, but it cannot decide
    why a page is indispensable, which relation governs its argument, or which
    retained facts stay off screen.  Those are author decisions, not validation
    side effects.
    """

    if outline.get("editorial_authoring_mode") != "author_driven":
        return []
    if outline.get("editorial_authoring_status") != "author_edited":
        return [AuditIssue(
            "OUTLINE_AUTHOR_EDIT_REQUIRED",
            "The deterministic Outline is only a candidate inventory. Complete the professional authoring task before formal Outline audit.",
            retry_strategy="author_outline_from_page_missions",
        )]
    issues: list[AuditIssue] = []
    for page in pages:
        if page.get("page_type") != "content":
            continue
        page_id = _page_id(page)
        evidence_roles = page.get("evidence_roles")
        exclusions = page.get("excluded_from_onscreen")
        if not str(page.get("non_substitutable_value") or "").strip():
            issues.append(AuditIssue(
                "NON_SUBSTITUTABLE_VALUE_MISSING",
                "Author-edited pages must state what the deck loses if this page is removed or merged.",
                (page_id,), "author_page_indispensability",
            ))
        if not str(page.get("argument_chain") or "").strip():
            issues.append(AuditIssue(
                "PAGE_ARGUMENT_CHAIN_MISSING",
                "Author-edited pages must state one governing source-supported argument chain.",
                (page_id,), "author_page_argument_chain",
            ))
        if not isinstance(evidence_roles, dict) or not evidence_roles:
            issues.append(AuditIssue(
                "PAGE_EVIDENCE_ROLES_MISSING",
                "Author-edited pages must assign claim, reason, instance, boundary, or trace-only duties to their evidence groups.",
                (page_id,), "author_page_evidence_roles",
            ))
        if not isinstance(exclusions, list):
            issues.append(AuditIssue(
                "ONSCREEN_EXCLUSIONS_MISSING",
                "Author-edited pages must explicitly record retained evidence that is excluded from the audience-facing layer.",
                (page_id,), "author_onscreen_exclusions",
            ))
    return issues
