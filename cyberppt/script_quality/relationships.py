"""Cross-page relationship continuity checks."""

from __future__ import annotations

import re

from .models import (
    PageRelationshipSummary,
    ScriptDocument,
    ScriptPage,
    ScriptQualityIssue,
    _issue,
)
from .source_coverage import text_similarity


_RELATION_VISIBILITY_SIGNALS = {
    "causes": ("导致", "推动", "促成", "形成", "因此", "→", "->"),
    "flows_to": ("流向", "进入", "经过", "形成", "输出", "→", "->", "第一", "第二", "第三"),
    "supports": ("支撑", "保障", "赋能", "服务于", "→", "->"),
    "depends_on": ("依赖", "以", "为基础", "前提", "→", "->"),
    "composed_of": ("构成", "由", "分层", "层级", "包括", "→", "->"),
    "collaborates_with": ("协同", "配合", "共同", "联动", "→", "->"),
    "feedback_to": ("反馈", "回流", "闭环", "迭代", "循环", "→", "->"),
}
_RELATION_ACTION_SIGNALS = tuple(
    dict.fromkeys(
        signal
        for signals in _RELATION_VISIBILITY_SIGNALS.values()
        for signal in signals
        if signal not in {"→", "->", "由", "以"}
    )
)


def _relationship_strings(value: object) -> tuple[str, ...]:
    """Return nonempty string values without making legacy contracts strict."""

    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(
        item.strip()
        for item in value
        if isinstance(item, str) and item.strip()
    )


def _contract_relations(contract: dict[str, object]) -> tuple[dict[str, object], ...]:
    relations = contract.get("content_relations")
    if not isinstance(relations, list):
        return ()
    return tuple(item for item in relations if isinstance(item, dict))


def _relation_values(
    relations: tuple[dict[str, object], ...], field: str
) -> tuple[str, ...]:
    values: list[str] = []
    for relation in relations:
        values.extend(_relationship_strings(relation.get(field)))
    return tuple(dict.fromkeys(values))


def _relation_corpus(relations: tuple[dict[str, object], ...]) -> str:
    values: list[str] = []
    for relation in relations:
        values.extend(_relationship_strings(relation.get("relation")))
        values.extend(_relationship_strings(relation.get("subject")))
        values.extend(_relationship_strings(relation.get("objects")))
        values.extend(_relationship_strings(relation.get("inputs")))
        values.extend(_relationship_strings(relation.get("outputs")))
    return " ".join(values)


def _relation_visibility_signal(text: str, relations: tuple[dict[str, object], ...]) -> bool:
    normalized = text.replace(" ", "")
    for relation in relations:
        name = str(relation.get("relation") or "").strip()
        signals = _RELATION_VISIBILITY_SIGNALS.get(name)
        if signals and any(signal in normalized for signal in signals):
            return True
    return False


def _has_visible_declared_relation(
    page: ScriptPage, relations: tuple[dict[str, object], ...]
) -> bool:
    if not relations:
        return True
    visible = "\n".join((page.onscreen_text, " ".join(page.top_level_module_titles)))
    return _relation_visibility_signal(visible, relations) or _relation_visibility_signal(
        page.visual_structure, relations
    )


def _page_relationship_summary(
    page: ScriptPage, contract: dict[str, object]
) -> PageRelationshipSummary:
    relations = _contract_relations(contract) or page.content_relations
    exit_handoffs = _relation_values(relations, "outputs") or _relation_values(
        relations, "objects"
    )
    return PageRelationshipSummary(
        page_id=page.page_id,
        entry_conditions=_relation_values(relations, "inputs"),
        page_transformation="\n".join(
            part
            for part in (
                str(contract.get("page_mission") or "").strip(),
                str(contract.get("core_message") or page.core_message).strip(),
                _relation_corpus(relations),
            )
            if part
        ),
        exit_handoffs=exit_handoffs,
        excluded_scope=_relationship_strings(contract.get("must_not_include")),
        visible_relation=_has_visible_declared_relation(page, relations),
    )


def _same_page_responsibility(
    left: PageRelationshipSummary, right: PageRelationshipSummary
) -> bool:
    if not left.page_transformation or not right.page_transformation:
        return False
    return text_similarity(left.page_transformation, right.page_transformation) >= 0.82


def _preempted_scope_terms(page: ScriptPage, excluded_scope: tuple[str, ...]) -> tuple[str, ...]:
    authored = "\n".join((page.onscreen_text, page.full_prose)).replace(" ", "")
    return tuple(
        scope
        for scope in excluded_scope
        if len(scope.replace(" ", "")) >= 3 and scope.replace(" ", "") in authored
    )


def _relation_parallel_labels(page: ScriptPage) -> tuple[str, ...]:
    raw_labels = list(page.top_level_module_titles)
    raw_labels.extend(re.split(r"[；;｜|]", page.onscreen_text))
    labels = [label.strip(" -—•") for label in raw_labels if label.strip(" -—•")]
    return tuple(dict.fromkeys(labels))


def _relationship_prerequisite_issue(
    page: ScriptPage,
    contract: dict[str, object],
    summary: PageRelationshipSummary,
    previous_handoffs: tuple[str, ...],
) -> list[ScriptQualityIssue]:
    if not summary.entry_conditions:
        return []
    directly_assigned = "\n".join(
        str(contract.get(field) or "")
        for field in ("page_mission", "audience_question", "core_message", "main_message")
    )
    available = "\n".join((*previous_handoffs, directly_assigned))
    missing = tuple(item for item in summary.entry_conditions if item not in available)
    if not missing:
        return []
    return [
        _issue(
            "PAGE_PREREQUISITE_UNFORMED",
            page,
            "Page relation consumes a prerequisite not formed by the prior page or assigned to this page.",
            "Form the missing prerequisite on the preceding page, or assign its supporting source and condition to this page.",
            evidence=missing,
            severity="warning",
        )
    ]


def _page_relationship_continuity_issues(
    script: ScriptDocument, pages_by_id: dict[str, dict[str, object]]
) -> list[ScriptQualityIssue]:
    """Audit cross-page handoffs and visible expression of declared relations."""

    issues: list[ScriptQualityIssue] = []
    content_pages = [
        page
        for page in script.pages
        if page.page_type == "content" and page.page_id in pages_by_id
    ]
    summaries = {
        page.page_id: _page_relationship_summary(page, pages_by_id[page.page_id])
        for page in content_pages
    }
    previous_handoffs: tuple[str, ...] = ()
    for page in content_pages:
        contract = pages_by_id[page.page_id]
        summary = summaries[page.page_id]
        relations = _contract_relations(contract) or page.content_relations
        if relations and not summary.visible_relation:
            issues.append(
                _issue(
                    "DECLARED_RELATION_NOT_VISIBLE",
                    page,
                    "Declared content relation is not readable in the visible modules or visual structure.",
                    "Express the approved subject-action-object relation with a directional chain, hierarchy, collaboration, or loop signal.",
                    evidence=tuple(str(item.get("relation") or "") for item in relations),
                )
            )
            labels = _relation_parallel_labels(page)
            if len(labels) >= 2 and not any(
                signal in " ".join(labels) for signal in _RELATION_ACTION_SIGNALS
            ):
                issues.append(
                    _issue(
                        "ONSCREEN_FALSE_RELATION_PARALLEL",
                        page,
                        "On-screen modules are parallel labels and do not carry the declared relation.",
                        "Rewrite top-level modules as subject-action-object steps or show their ordered, hierarchical, collaborative, or closed-loop relation.",
                        evidence=labels[:6],
                    )
                )
        issues.extend(
            _relationship_prerequisite_issue(
                page, contract, summary, previous_handoffs
            )
        )
        previous_handoffs = tuple(
            dict.fromkeys((*previous_handoffs, *summary.exit_handoffs))
        )
    for left, right in zip(content_pages, content_pages[1:]):
        left_summary = summaries[left.page_id]
        right_summary = summaries[right.page_id]
        if _same_page_responsibility(left_summary, right_summary):
            issues.append(
                ScriptQualityIssue(
                    "ADJACENT_PAGE_RESPONSIBILITY_DUPLICATE",
                    "error",
                    "Adjacent pages repeat the same editorial responsibility and declared relation.",
                    (left.page_id, right.page_id),
                    evidence=(left_summary.page_transformation, right_summary.page_transformation),
                    suggested_action="Keep the responsibility on one page and make the adjacent page advance a distinct audience question or relation.",
                )
            )
        preempted = _preempted_scope_terms(left, right_summary.excluded_scope)
        if preempted:
            issues.append(
                ScriptQualityIssue(
                    "PAGE_SCOPE_PREEMPTED",
                    "error",
                    "Current page writes a mechanism or task reserved outside the next page's allowed scope.",
                    (left.page_id, right.page_id),
                    evidence=preempted,
                    suggested_action="Remove the reserved content from the current page and let the later page introduce its assigned mechanism or task.",
                )
            )
    return issues
