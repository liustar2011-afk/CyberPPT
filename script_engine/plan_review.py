"""Human-readable review for the v2 lean Deck Plan."""
from __future__ import annotations

from collections import defaultdict
from typing import Any


_PAGE_ROLE_LABELS = {
    "cover": "封面", "agenda": "目录", "contents": "目录", "chapter": "章节过渡",
    "chapter_divider": "章节过渡", "transition": "章节过渡", "ending": "封底",
    "closing": "封底", "mechanism": "机制解释", "evidence": "证据说明",
    "analysis": "分析", "conclusion": "结论", "content": "内容",
}
_STRUCTURE_MODE_LABELS = {
    "preserve": "保持来源章节结构",
    "presentation_grouping": "按汇报问题归并相邻来源章节",
    "user_authorized_restructure": "按用户授权重组",
}
_PRESENTATION_MODE_LABELS = {
    "formal_chaptered": "正式分章汇报",
    "continuous": "连续叙事",
}
_OPERATION_LABELS = {
    "preserve": "保持",
    "merge_adjacent": "合并相邻章节",
    "group_adjacent_source_chapters": "归并相邻来源章节",
    "split_for_presentation": "为汇报拆分",
    "user_authorized_cross_chapter": "用户授权跨章重组",
}


def _text(value: object) -> str:
    return str(value or "—").strip() or "—"


def _label(value: object, labels: dict[str, str]) -> str:
    text = _text(value)
    return labels.get(text, text)


def _cell(value: object) -> str:
    return _text(value).replace("|", "\\|").replace("\n", "<br>")


def _ids(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def render_plan_review(
    plan: dict[str, Any],
    foundation: dict[str, Any],
    *,
    issues: list[str] | None = None,
    warnings: list[str] | None = None,
) -> str:
    """Render the actual PLAN review boundary without AUTHOR-owned prose."""

    del foundation  # Source details remain addressable through source_refs.
    issues = list(issues or [])
    warnings = list(warnings or [])
    chapters = [item for item in plan.get("chapters") or [] if isinstance(item, dict)]
    pages = [item for item in plan.get("pages") or [] if isinstance(item, dict)]
    by_chapter: dict[str, list[dict[str, Any]]] = defaultdict(list)
    chapter_ids = {str(chapter.get("id") or "") for chapter in chapters}
    unassigned: list[dict[str, Any]] = []
    for page in pages:
        chapter_id = str(page.get("chapter_id") or "")
        if chapter_id and chapter_id in chapter_ids:
            by_chapter[chapter_id].append(page)
        else:
            unassigned.append(page)

    lines = [
        "# 脚本规划待确认", "",
        "- 规划合同：v2 lean",
        f"- 写作模式：{'忠实分页整理' if plan.get('authoring_mode', 'faithful') == 'faithful' else '分析性深化'}",
        f"- 交流目标：{_text(plan.get('communication_goal'))}",
        f"- 汇报对象：{_text(plan.get('audience'))}",
        f"- 受众范围：{_text(plan.get('audience_scope'))}",
        f"- 来源结构：{_label(plan.get('source_structure_mode'), _STRUCTURE_MODE_LABELS)}",
        f"- 汇报结构：{_label(plan.get('presentation_structure_mode'), _PRESENTATION_MODE_LABELS)}",
        f"- 汇报章节数：{len(chapters)}",
        "- 规划边界：章节、页序、页面问题、页面使命和来源范围", "",
    ]

    def append_section(title: str, section_pages: list[dict[str, Any]], chapter: dict[str, Any] | None) -> None:
        lines.extend([f"## {title}", ""])
        if chapter:
            lines.extend([
                f"- 章节使命：{_text(chapter.get('purpose'))}",
                f"- 来源章节映射：{'、'.join(_ids(chapter.get('source_chapter_ids'))) or '—'}",
            ])
            if chapter.get("structural_operation"):
                lines.append(f"- 章节结构操作：{_label(chapter.get('structural_operation'), _OPERATION_LABELS)}")
            lines.append("")
        lines.extend([
            "| 页面 | 类型 | 暂定标题 | 页面问题 | 页面使命 | 来源范围 |",
            "|---|---|---|---|---|---|",
        ])
        for page in section_pages:
            lines.append(
                "| {id} | {role} | {title} | {question} | {logic} | {refs} |".format(
                    id=_cell(page.get("id")),
                    role=_cell(_label(page.get("page_role"), _PAGE_ROLE_LABELS)),
                    title=_cell(page.get("title")),
                    question=_cell(page.get("question")),
                    logic=_cell(page.get("logic")),
                    refs=_cell("、".join(_ids(page.get("source_refs"))) or "—"),
                )
            )
        lines.append("")

    for chapter in chapters:
        chapter_id = str(chapter.get("id") or "")
        append_section(_text(chapter.get("title") or chapter_id), by_chapter.get(chapter_id, []), chapter)
    if unassigned:
        append_section("未分配章节", unassigned, None)

    lines.extend(["## 审计结论", ""])
    lines.extend([f"- 阻塞：{item}" for item in issues])
    lines.extend([f"- 提醒：{item}" for item in warnings])
    if not issues and not warnings:
        lines.append("- 当前规划通过确定性检查")
    lines.append("")
    return "\n".join(lines)


__all__ = ["render_plan_review"]
