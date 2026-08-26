"""Cross-page relationship continuity checks."""

from __future__ import annotations

import re

from cyberppt.page_logic_contract import page_logic_mode
from cyberppt.semantic_fidelity import (
    COMPOSITION_RELATION_MARKERS,
    audit_composition_relations,
    composition_relation_units,
    source_text,
)

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
    "sequence_before": ("先", "再", "随后", "阶段", "→", "->"),
    "bounded_by": ("受", "约束", "边界", "条件", "→", "->"),
    "composed_of": ("构成", "由", "分层", "层级", "包括", "→", "->"),
    # The Outline projection emits "contains" (not "composed_of") for every
    # heading-containment relation -- onscreen_expression.py's _RELATION_FORMS
    # already treats the two as synonyms for form selection, but this table
    # never gained a "contains" entry, so DECLARED_RELATION_NOT_VISIBLE fired
    # on essentially every content page that has real sub-headings, no matter
    # how the module structure was written.
    "contains": ("构成", "由", "分层", "层级", "包括", "→", "->"),
    "applies_to": ("面向", "适用于", "服务", "覆盖", "→", "->"),
    "has_capability": ("具备", "拥有", "专业能力", "→", "->"),
    "uses": ("复用", "使用", "采用", "利用", "→", "->"),
    "collaborates_with": ("协同", "配合", "共同", "联动", "→", "->"),
    "feedback_to": ("反馈", "回流", "闭环", "迭代", "循环", "→", "->"),
    "responsible_for": ("负责", "牵头", "承担", "职责", "→", "->"),
    "operates": ("运营", "运行", "经营", "实施", "执行", "开展", "管理", "→", "->"),
    # cyberppt.relation_semantics and stage02_relationship_adapter classify
    # relations into a separate, wider vocabulary (used for Stage 02 topology
    # selection) than this table originally covered. A name produced there
    # but absent here fell through to no signals at all -- see the generic
    # fallback in _relation_visibility_signal below -- so these entries keep
    # the two vocabularies from silently drifting apart for the well-known
    # cases that also carry a specific expected wording.
    "requires": ("需要", "依赖", "以", "为基础", "前提", "→", "->"),
    "evidence_supports": ("支撑", "证明", "印证", "→", "->"),
    "directed_dependency": ("依托", "建立在", "承接", "基于", "提供基础", "→", "->"),
    "feeds_back_to": ("反馈", "回流", "闭环", "迭代", "循环", "→", "->"),
    "peer_classification": ("并列", "分类", "同类", "相互独立", "→", "->"),
    "layered_as": ("分层", "层级", "上下", "底座", "承托", "→", "->"),
    "layer_supports": ("分层支撑", "层级支撑", "承托", "托底", "→", "->"),
    "transforms_to": ("形成", "转化", "生成", "产出", "汇聚", "→", "->"),
    "problem_response": ("回应", "映射", "响应", "→", "->"),
    "semantic_mapping": ("对应", "匹配", "适配", "→", "->"),
    "comparison": ("对照", "比较", "差异", "→", "->"),
    "optional_progression": ("逐步", "深化", "递进", "→", "->"),
}
# A relation that the codebase's broader classifiers (relation_semantics.py,
# stage02_relationship_adapter.py) can only type as a generic directed
# relation or association still carries a real arrow in the text it was
# parsed from -- that arrow itself is the visible declaration, whether or
# not it matches one of the specific verbs above.
_GENERIC_RELATION_VISIBILITY_SIGNALS = ("→", "->", "⇒")
_RELATION_ACTION_SIGNALS = tuple(
    dict.fromkeys(
        signal
        for signals in _RELATION_VISIBILITY_SIGNALS.values()
        for signal in signals
        if signal not in {"→", "->", "由", "以"}
    )
)
_COMPOSITION_SCOPE_TOPICS = (
    "课程包",
    "场景包",
    "课程",
    "模块",
    "产品",
    "平台",
    "方案",
)
_COMPOSITION_SCOPE_MARKERS = (*COMPOSITION_RELATION_MARKERS, "组合", "作为")
_PROTECTED_PREDICATE_RE = re.compile(
    r"(?P<subject>[0-9A-Za-z\u4e00-\u9fff、，,/]{4,32}(?:岗位|主体|群体|对象))"
    r"(?P<predicate>持续更新)"
)
_VAGUE_SUBJECT_PREFIXES = ("这些", "相关", "各类", "有关")


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
        signals = _RELATION_VISIBILITY_SIGNALS.get(name, _GENERIC_RELATION_VISIBILITY_SIGNALS)
        if signals and any(signal in normalized for signal in signals):
            return True
    return False


def _has_visible_declared_relation(
    page: ScriptPage, relations: tuple[dict[str, object], ...], contract: dict[str, object]
) -> bool:
    if not relations:
        return True
    if page_logic_mode(contract) == "required":
        # A required page_logic_contract already verifies, edge by edge, that
        # every relation reaches a visible on-screen carrier (see
        # cyberppt.page_logic_contract's ONSCREEN_RELATION_CARRIER_MISSING /
        # ONSCREEN_EXPRESSION_RELATION_MISSING checks, run separately as part
        # of _page_logic_contract_issues). Re-checking the same page here
        # against a small fixed keyword table is strictly less precise and
        # only produces disagreements, not additional coverage.
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
        visible_relation=_has_visible_declared_relation(page, relations, contract),
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


def _reserved_scope_strings(contract: dict[str, object]) -> tuple[str, ...]:
    values: list[str] = list(
        _relationship_strings(contract.get("must_not_include"))
    )
    values.extend(_relationship_strings(contract.get("reserved_for_later")))
    items = contract.get("reserved_for_later_items")
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                topic = str(item.get("topic") or "").strip()
                if topic:
                    values.append(topic)
            elif isinstance(item, str) and item.strip():
                values.append(item.strip())
    return tuple(dict.fromkeys(values))


def _reserved_composition_relation_hits(
    page: ScriptPage,
    contract: dict[str, object],
) -> tuple[str, ...]:
    """Detect only relation-level consumption of current-page reservations.

    The page boundary must itself reserve a composition relationship.  The
    authored sentence must then contain both one controlled topic anchor and
    an explicit composition action.  A course list or a bare module noun is
    therefore insufficient to trigger the gate.
    """

    reservations = _reserved_scope_strings(contract)
    reservation_text = "\n".join(reservations)
    controlled_topics = tuple(
        topic for topic in _COMPOSITION_SCOPE_TOPICS if topic in reservation_text
    )
    if not controlled_topics or not any(
        marker in reservation_text for marker in _COMPOSITION_SCOPE_MARKERS
    ):
        return ()
    authored = "\n".join((page.onscreen_text, page.full_prose))
    hits: list[str] = []
    for unit in re.split(r"[。！？；;\n]+", authored):
        unit = unit.strip()
        if not unit or not any(topic in unit for topic in controlled_topics):
            continue
        if composition_relation_units(unit) or "组合" in unit:
            hits.append(unit)
    return tuple(dict.fromkeys(hits))


def _predicate_ownership_review_issues(
    page: ScriptPage,
    evidence: str,
) -> list[ScriptQualityIssue]:
    evidence_compact = re.sub(r"\s+", "", evidence)
    unsupported: list[str] = []
    for match in _PROTECTED_PREDICATE_RE.finditer(page.onscreen_text):
        subject = match.group("subject")
        if subject.startswith(_VAGUE_SUBJECT_PREFIXES):
            continue
        phrase = f"{subject}{match.group('predicate')}"
        if phrase not in evidence_compact:
            unsupported.append(phrase)
    if not unsupported:
        return []
    return [
        _issue(
            "PREDICATE_OWNERSHIP_REVIEW",
            page,
            "A protected business entity receives a high-risk state predicate that is not stated with the same subject in cited evidence.",
            "Review the source predicate owner and retain the governing attribute or object when compressing the sentence.",
            evidence=tuple(dict.fromkeys(unsupported)),
            severity="warning",
        )
    ]


def _page_relationship_contract_issues(
    page: ScriptPage,
    contract: dict[str, object],
    records_by_id: dict[str, dict[str, object]],
) -> list[ScriptQualityIssue]:
    refs = tuple(
        str(ref)
        for ref in contract.get("source_refs", [])
        if ref is not None and str(ref).strip()
    ) or page.source_refs
    evidence = source_text(refs, records_by_id)
    authored = "\n".join(
        part
        for part in (
            page.main_message,
            page.subtitle,
            page.full_prose,
            page.onscreen_text,
            page.visual_structure,
            page.speaker_notes,
        )
        if part
    )
    issues = [
        _issue(
            item.code,
            page,
            item.message,
            "Remove the unsupported composition claim or cite evidence that states the same relationship for the related business objects.",
        )
        for item in audit_composition_relations(authored, evidence)
    ]
    reserved_hits = _reserved_composition_relation_hits(page, contract)
    if reserved_hits:
        issues.append(
            _issue(
                "PAGE_SCOPE_RESERVED_RELATION",
                page,
                "The current page consumes a composition relationship explicitly reserved for a later page.",
                "Keep the permitted topic or course list, and move the reserved composition relationship to its assigned page.",
                evidence=reserved_hits,
                severity="error",
            )
        )
    issues.extend(_predicate_ownership_review_issues(page, evidence))
    return issues


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
            if len(labels) >= 2 and "→" not in page.onscreen_text and "->" not in page.onscreen_text and not any(
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
