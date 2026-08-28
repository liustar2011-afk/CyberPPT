"""Human-readable, non-authoritative review projection for deck-plan.json."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .analysis_audit import foundation_items_by_id


_PAGE_ROLE_LABELS = {
    "background": "背景说明",
    "context": "背景说明",
    "state": "现状说明",
    "diagnosis": "问题诊断",
    "mechanism": "机制解释",
    "system": "体系说明",
    "evidence": "证据支撑",
    "transition": "逻辑过渡",
    "action": "工作安排",
    "source_native": "来源原生",
}

_STRUCTURE_MODE_LABELS = {
    "preserve": "保持来源章节结构",
    "user_authorized_restructure": "用户授权重组",
}

_STRUCTURAL_OPERATION_LABELS = {
    "preserve": "保持",
    "split": "拆页",
    "merge_within_chapter": "章内合并",
    "user_authorized_cross_chapter": "用户授权跨章调整",
}

_EVIDENCE_FIT_LABELS = {
    "direct": "直接支持",
    "indirect": "间接支持",
    "topic_only": "仅主题相关",
    "no": "不适配",
    "uncertain": "待确认",
}

_EVIDENCE_FIT_VERDICT_LABELS = {
    "keep": "保留当前规划",
    "rename": "需要改名",
    "move": "需要移动",
    "split": "需要拆分",
    "reject": "需要剔除",
}


def _text(value: object, fallback: str = "—") -> str:
    text = str(value or "").strip()
    return text or fallback


def _cell(value: object) -> str:
    return _text(value).replace("|", "｜").replace("\r", " ").replace("\n", " ")


def _ids(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, str) and value]


def _label(value: object, labels: dict[str, str], fallback: object = None) -> str:
    key = str(value or "").strip()
    return labels.get(key, _text(fallback if fallback is not None else value))


def evidence_status(page: dict[str, Any], foundation: dict[str, Any]) -> str:
    items = foundation_items_by_id(foundation)
    proof = page.get("proof") if isinstance(page.get("proof"), dict) else {}
    analysis = page.get("analysis_basis") if isinstance(page.get("analysis_basis"), dict) else {}
    evidence = list(dict.fromkeys(_ids(proof.get("evidence_refs")) + _ids(analysis.get("supports"))))
    boundaries = _ids(proof.get("boundary_refs"))
    unknown = [item_id for item_id in evidence + boundaries if item_id not in items]
    labels: list[str] = []
    if unknown:
        labels.append("证据责任不完整")
    elif analysis.get("relation_basis") == "inferred" or proof.get("relation_basis") == "inferred":
        labels.append("来源综合推断")
    elif evidence:
        labels.append("来源直接支持")
    else:
        labels.append("需人工确认")
    if boundaries:
        labels.append("边界条件需保留")
    review = page.get("evidence_fit_review")
    if isinstance(review, dict):
        labels.append(
            "证据适配结论：保留"
            if review.get("verdict") == "keep"
            else "证据适配结论：待修复"
        )
    return "；".join(labels)


def _append_evidence_fit_review(
    lines: list[str],
    review: object,
    *,
    title: str,
) -> None:
    if not isinstance(review, dict):
        return
    lines.extend(
        [
            f"#### {title}",
            "",
            f"- 质询问题：{_text(review.get('question'))}",
        ]
    )
    counter_case = str(review.get("counter_case") or "").strip()
    if counter_case:
        lines.append(f"- 最强反例：{counter_case}")
    lines.extend(
        [
            f"- 当前结论：{_label(review.get('verdict'), _EVIDENCE_FIT_VERDICT_LABELS)}",
            "",
            "| 来源 | 适配关系 | 来源角色 | 判断依据 |",
            "|---|---|---|---|",
        ]
    )
    for item in review.get("items") or []:
        if not isinstance(item, dict):
            continue
        lines.append(
            "| {ref} | {fit} | {role} | {reason} |".format(
                ref=_cell(item.get("evidence_ref")),
                fit=_cell(_label(item.get("fit"), _EVIDENCE_FIT_LABELS)),
                role=_cell(item.get("role")),
                reason=_cell(item.get("reason")),
            )
        )
    lines.append("")


def _append_source_consumption_review(
    lines: list[str], page: dict[str, Any]
) -> None:
    source_refs = _ids(page.get("source_refs"))
    if not source_refs:
        return
    lines.extend(["#### 来源消费摘要", ""])
    contract = page.get("source_consumption")
    if not isinstance(contract, dict):
        lines.extend(["- 来源消费合同：未声明", ""])
        return

    detail_refs = _ids(contract.get("detail_refs"))
    omissions = [
        item
        for item in contract.get("intentional_omissions") or []
        if isinstance(item, dict)
    ]
    omitted_refs = {
        ref for item in omissions for ref in _ids(item.get("source_refs"))
    }
    full_copy_refs = [
        ref for ref in source_refs if ref not in detail_refs and ref not in omitted_refs
    ]
    lines.extend(
        [
            f"- 合同模式：{_text(contract.get('mode'))}",
            f"- 完整稿必消费来源：{'、'.join(full_copy_refs) or '—'}",
            f"- 追溯详情：{'、'.join(detail_refs) or '—'}",
            f"- 必须上屏的代表性来源：{'、'.join(_ids(contract.get('onscreen_refs'))) or '—'}",
        ]
    )
    if omissions:
        lines.append("- 明确删减：")
        for item in omissions:
            lines.append(
                f"  - {'、'.join(_ids(item.get('source_refs'))) or '—'}：{_text(item.get('reason'))}"
            )
    anchors = [
        item
        for item in contract.get("full_prose_anchors") or []
        if isinstance(item, dict)
    ]
    if anchors:
        lines.extend(["", "| 来源 | 完整稿保护锚点 | 最少命中 |", "|---|---|---|"])
        for item in anchors:
            values = [value for value in item.get("anchors") or [] if isinstance(value, str)]
            lines.append(
                "| {ref} | {anchors} | {hits} |".format(
                    ref=_cell(item.get("source_ref")),
                    anchors=_cell("；".join(values)),
                    hits=_cell(item.get("minimum_hits") or len(values)),
                )
            )
    unit_dispositions = [
        item
        for item in contract.get("unit_dispositions") or []
        if isinstance(item, dict)
    ]
    if unit_dispositions:
        lines.extend(["", "| 来源 | 语义单元 | 归宿 | 理由 |", "|---|---|---|---|"])
        for item in unit_dispositions:
            lines.append(
                "| {ref} | {unit} | {disposition} | {reason} |".format(
                    ref=_cell(item.get("source_ref")),
                    unit=_cell(item.get("unit_id")),
                    disposition=_cell(item.get("disposition")),
                    reason=_cell(item.get("reason") or "—"),
                )
            )
    lines.append("")


def render_plan_review(
    plan: dict[str, Any],
    foundation: dict[str, Any],
    *,
    issues: list[str] | None = None,
    warnings: list[str] | None = None,
) -> str:
    """Render a Markdown review view without mutating either authority input."""

    issues = list(issues or [])
    warnings = list(warnings or [])
    chapters = [item for item in plan.get("chapters") or [] if isinstance(item, dict)]
    pages = [item for item in plan.get("pages") or [] if isinstance(item, dict)]
    by_chapter: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unassigned: list[dict[str, Any]] = []
    chapter_ids = {str(chapter.get("id") or "") for chapter in chapters}
    for page in pages:
        chapter_id = str(page.get("chapter_id") or "")
        if chapter_id and chapter_id in chapter_ids:
            by_chapter[chapter_id].append(page)
        else:
            unassigned.append(page)

    lines = [
        "# 脚本规划待确认",
        "",
        f"- 交流目标：{_text(plan.get('communication_goal'))}",
        f"- 汇报对象：{_text(plan.get('audience'))}",
        f"- 受众范围：{_text(plan.get('audience_scope'))}",
        f"- 来源结构：{_label(plan.get('source_structure_mode'), _STRUCTURE_MODE_LABELS)}",
        "- 来源适配门禁："
        + (
            "严格质询"
            if plan.get("evidence_fit_review_mode") == "strict"
            else "缺失，阻断 AUTHOR"
        ),
        f"- 来源总论点：{_text(plan.get('source_thesis'))}",
        "- 来源论证顺序：" + " → ".join(_ids(plan.get("source_argument_method"))),
        f"- 全稿主旨：{_text(plan.get('thesis'))}",
        f"- 叙事弧：{_text(plan.get('narrative_arc'))}",
        f"- 受众起点：{_text(plan.get('audience_start'))}",
        f"- 受众终点：{_text(plan.get('audience_end'))}",
        "",
    ]

    def append_chapter(
        title: str,
        chapter_pages: list[dict[str, Any]],
        chapter: dict[str, Any] | None = None,
    ) -> None:
        lines.extend(
            [
                f"## {title}",
                "",
                *([
                    f"- 章节使命：{_text(chapter.get('purpose'))}",
                    f"- 章节问题：{_text(chapter.get('question'))}",
                    f"- 章节结论：{_text(chapter.get('message'))}",
                    f"- 章节承接：{_text(chapter.get('relationship_to_previous'))}",
                    "- 承担源论点：" + "、".join(_ids(chapter.get("source_argument_node_ids"))),
                    "",
                ] if chapter is not None else []),
                "| 页面 | 标题 | 核心判断 | 承担源论点 | 页面职责 | 证据状态 | 承接 |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for page in chapter_pages:
            bridge_parts = []
            if page.get("receives"):
                bridge_parts.append(f"承接：{_text(page.get('receives'))}")
            if page.get("next"):
                bridge_parts.append(f"去向：{_text(page.get('next'))}")
            lines.append(
                "| {id} | {title} | {message} | {argument_nodes} | {role} | {evidence} | {bridge} |".format(
                    id=_cell(page.get("id")),
                    title=_cell(page.get("title")),
                    message=_cell(page.get("message")),
                    argument_nodes=_cell("、".join(_ids(page.get("source_argument_node_ids"))) or "—"),
                    role=_cell(_label(page.get("page_role"), _PAGE_ROLE_LABELS, page.get("logic"))),
                    evidence=_cell(evidence_status(page, foundation)),
                    bridge=_cell("；".join(bridge_parts)),
                )
            )
        lines.append("")
        for page in chapter_pages:
            page_id = _text(page.get("id"))
            lines.extend(
                [
                    f"### {page_id} {_text(page.get('title'), '')}".rstrip(),
                    "",
                    f"- 页面问题：{_text(page.get('question'))}",
                    f"- 主逻辑：{_text(page.get('logic'))}",
                    f"- 承担源论点：{'、'.join(_ids(page.get('source_argument_node_ids'))) or '—'}",
                    f"- 来源范围：{'、'.join(_ids(page.get('source_scope'))) or '—'}",
                    f"- 结构操作：{_label(page.get('structural_operation'), _STRUCTURAL_OPERATION_LABELS)}",
                    f"- 后续保留：{'；'.join(_ids(page.get('reserved_for_later'))) or '—'}",
                    "",
                ]
            )
            _append_evidence_fit_review(
                lines,
                page.get("evidence_fit_review"),
                title="页面来源适配质询",
            )
            _append_source_consumption_review(lines, page)
            contract = page.get("onscreen_contract")
            if isinstance(contract, dict):
                for module in contract.get("modules") or []:
                    if not isinstance(module, dict):
                        continue
                    _append_evidence_fit_review(
                        lines,
                        module.get("evidence_fit_review"),
                        title=f"模块来源适配质询：{_text(module.get('heading'))}",
                    )

    for chapter in chapters:
        chapter_id = str(chapter.get("id") or "")
        chapter_pages = by_chapter.get(chapter_id, [])
        append_chapter(_text(chapter.get("title") or chapter_id), chapter_pages, chapter)
    if unassigned:
        append_chapter("未分配章节", unassigned)

    lines.extend(["## 审计结论", ""])
    if not issues and not warnings:
        lines.append("- 当前规划通过确定性检查")
    else:
        lines.extend(f"- 阻断：{item}" for item in issues)
        lines.extend(f"- 提醒：{item}" for item in warnings)
    lines.append("")
    return "\n".join(lines)
