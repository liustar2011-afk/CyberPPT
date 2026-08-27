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
    return "；".join(labels)


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
        f"- 全稿主旨：{_text(plan.get('thesis'))}",
        "",
    ]

    def append_chapter(title: str, chapter_pages: list[dict[str, Any]]) -> None:
        lines.extend(
            [
                f"## {title}",
                "",
                "| 页面 | 标题 | 核心判断 | 页面职责 | 证据状态 | 承接 |",
                "|---|---|---|---|---|---|",
            ]
        )
        for page in chapter_pages:
            bridge_parts = []
            if page.get("receives"):
                bridge_parts.append(f"承接：{_text(page.get('receives'))}")
            if page.get("next"):
                bridge_parts.append(f"去向：{_text(page.get('next'))}")
            lines.append(
                "| {id} | {title} | {message} | {role} | {evidence} | {bridge} |".format(
                    id=_cell(page.get("id")),
                    title=_cell(page.get("title")),
                    message=_cell(page.get("message")),
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
                    f"- 来源范围：{'、'.join(_ids(page.get('source_scope'))) or '—'}",
                    f"- 结构操作：{_label(page.get('structural_operation'), _STRUCTURAL_OPERATION_LABELS)}",
                    f"- 后续保留：{'；'.join(_ids(page.get('reserved_for_later'))) or '—'}",
                    "",
                ]
            )

    for chapter in chapters:
        chapter_id = str(chapter.get("id") or "")
        append_chapter(_text(chapter.get("title") or chapter_id), by_chapter.get(chapter_id, []))
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
