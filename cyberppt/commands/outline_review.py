"""Render the authoritative Stage 01 Outline and audit as a reviewable Markdown brief."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT = Path("workbench/stages/01-analysis/outline-human-review.md")
DEFAULT_AUDIT_OUTPUT = Path("workbench/stages/01-analysis/outline-audit.md")


def _text(value: object) -> str:
    return str(value or "").strip()


def _items(value: object) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _refs(value: object) -> str:
    return "、".join(_text(item) for item in value if _text(item)) if isinstance(value, list) else "—"


def _chain(page: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for item in _items(page.get("argument_chain")):
        statement = " ".join(_text(item.get("statement")).split())
        if len(statement) > 96:
            statement = statement[:93] + "…"
        refs = _refs(item.get("source_refs"))
        if statement:
            relation = _text(item.get("relation"))
            result.append(f"{refs}{('｜' + relation) if relation else ''}：{statement}")
    return result


def _expression_model(page: dict[str, Any]) -> list[str]:
    """Render an author-selected expression model as reviewable Markdown."""

    selection = page.get("expression_model_selection")
    if not isinstance(selection, dict) or _text(selection.get("fit")) != "selected":
        return []
    model_id = _text(selection.get("model_id")) or "未声明"
    lines = [f"- 表达模型：{model_id}｜{_text(selection.get('fit_reason')) or '未说明匹配理由'}"]
    mappings = _items(selection.get("source_mapping"))
    if mappings:
        lines.append("- 槽位映射：")
        for mapping in mappings:
            slot = _text(mapping.get("slot")) or "未命名槽位"
            detail = _refs(mapping.get("source_refs"))
            if mapping.get("implicit") is True:
                detail += "（隐含问题）"
            statement = _text(mapping.get("statement"))
            if statement:
                detail += f"：{statement}"
            lines.append(f"  - {slot}＝{detail}")
    return lines


def render_outline_review_markdown(outline: dict[str, Any], audit: dict[str, Any]) -> str:
    """Produce the human gate document from the canonical Outline and audit report."""

    authoring_mode = _text(outline.get("editorial_authoring_mode"))
    authoring_status = _text(outline.get("editorial_authoring_status"))
    is_candidate = authoring_mode == "author_driven" and authoring_status != "author_edited"
    title = "# 候选 Outline（待作者化）" if is_candidate else "# 正式 Outline 人工审阅稿"
    lines = [
        title,
        "",
        f"- 交流目标：{_text(outline.get('communication_goal')) or '未声明'}",
        f"- 叙事主张：{_text(outline.get('narrative_thesis')) or '未声明'}",
        f"- 作者状态：{authoring_status or '未声明'}{('（待作者化）' if is_candidate else '')}",
        f"- 审计结论：**{_text(audit.get('status')) or 'unknown'}**",
        f"- 审计模式：{_text(audit.get('mode')) or 'unknown'}；论证契约：{_text(audit.get('argument_contract_mode')) or 'legacy'}",
        "",
        "## 审计报告",
        "",
        f"- 问题数：{len(_items(audit.get('issues')))}",
        f"- 语义节点消费问题：{len(_items(audit.get('argument_model_issues')))}",
        f"- 失败论证边：{len(audit.get('failed_edges') or []) if isinstance(audit.get('failed_edges'), list) else 0}",
        f"- 覆盖的 Source Truth：{_text(audit.get('checked_source_truth')) or '未加载'}",
        "",
    ]
    issues = _items(audit.get("issues"))
    if issues:
        lines.extend(["### 待修复问题", ""])
        for issue in issues:
            pages = _refs(issue.get("pages"))
            lines.append(f"- `{_text(issue.get('code'))}`｜页面：{pages}｜{_text(issue.get('message'))}")
        lines.append("")
    else:
        lines.extend(["### 结论", "", "严格 Outline 审计通过；仍需在此人工门审阅叙事取舍后，才可进入逐页内容编写。", ""])

    pages = _items(outline.get("pages"))
    chapters = [page for page in pages if page.get("page_type") == "chapter"]
    lines.extend(["## 章节与页面提纲", ""])
    for chapter in chapters:
        chapter_id = _text(chapter.get("chapter_id"))
        chapter_pages = [
            page for page in pages
            if page.get("page_type") == "content" and _text(page.get("chapter_id")) == chapter_id
        ]
        lines.extend([
            f"## {_text(chapter.get('title')) or chapter_id}",
            "",
            f"- 章节使命：{_text(chapter.get('chapter_mission')) or _text(chapter.get('page_mission')) or '见以下页面使命。'}",
            f"- 内容页：{', '.join(_text(page.get('page_id')) for page in chapter_pages)}",
            "",
        ])
        for page in chapter_pages:
            lines.extend([
                f"### {_text(page.get('page_id'))}｜{_text(page.get('title'))}",
                "",
                f"- 受众问题：{_text(page.get('audience_question')) or '未声明'}",
                f"- 页面使命：{_text(page.get('page_mission')) or '未声明'}",
                f"- 核心判断：{_text(page.get('core_message')) or _text(page.get('main_message')) or '未声明'}",
                f"- 不可替代价值：{_text(page.get('non_substitutable_value')) or '未声明'}",
                f"- 证据范围：{_refs(page.get('source_refs'))}",
            ])
            roles = []
            for role in _items(page.get("evidence_roles")):
                role_name = _text(role.get("role"))
                role_refs = _refs(role.get("source_refs"))
                if role_name and role_refs != "—":
                    roles.append(f"{role_name}={role_refs}")
            lines.append(f"- 证据职责：{'；'.join(roles) or '未分组'}")
            chain = _chain(page)
            lines.append("- 主论证链：")
            lines.extend(f"  - {item}" for item in chain) if chain else lines.append("  - 未声明")
            lines.extend(_expression_model(page))
            excluded = _refs(page.get("excluded_from_onscreen"))
            lines.append(f"- 不上屏取舍：{excluded}")
            lines.append(f"- 后页保留：{_text(page.get('reserved_for_later')) or '无'}")
            if page.get("source_heading_preserved") is True:
                lines.append(
                    "- 原文目录保留："
                    + (_text(page.get("source_heading_preservation_rationale")) or "作者明确保留。")
                )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_outline_audit_markdown(audit: dict[str, Any]) -> str:
    """Render only the audit JSON as its independently reviewable Markdown report."""

    lines = [
        "# Outline 审计报告",
        "",
        f"- 审计结论：**{_text(audit.get('status')) or 'unknown'}**",
        f"- 审计模式：{_text(audit.get('mode')) or 'unknown'}",
        f"- 论证契约：{_text(audit.get('argument_contract_mode')) or 'legacy'}",
        f"- 语义契约：{_text(audit.get('semantic_contract_mode')) or 'legacy'}",
        f"- Source Truth：{_text(audit.get('checked_source_truth')) or '未加载'}",
        f"- 语义模型：{_text(audit.get('semantic_argument_model')) or '未加载'}",
        "",
        "## 审计结果",
        "",
    ]
    issues = _items(audit.get("issues"))
    if not issues:
        lines.append("无问题项。")
    else:
        lines.extend(["| 代码 | 页面 | 修复方向 | 问题 |", "|---|---|---|---|"])
        for issue in issues:
            lines.append(
                f"| `{_text(issue.get('code'))}` | {_refs(issue.get('pages'))} | "
                f"{_text(issue.get('retry_strategy'))} | {_text(issue.get('message'))} |"
            )
    lines.extend([
        "",
        "## 论证图检查",
        "",
        f"- 页面节点：{len(_items((audit.get('argument_graph') or {}).get('nodes')) if isinstance(audit.get('argument_graph'), dict) else [])}",
        f"- 页面论证边：{len(_items((audit.get('argument_graph') or {}).get('edges')) if isinstance(audit.get('argument_graph'), dict) else [])}",
        f"- Source Truth 记录：{_text((audit.get('argument_graph') or {}).get('source_record_count')) if isinstance(audit.get('argument_graph'), dict) else '0'}",
        f"- 语义节点消费问题：{len(_items(audit.get('argument_model_issues')))}",
        f"- 失败论证边：{len(audit.get('failed_edges') or []) if isinstance(audit.get('failed_edges'), list) else 0}",
        f"- 需重写页面：{_refs(audit.get('retry_scope'))}",
        "",
    ])
    return "\n".join(lines)


def render_outline_audit_report(project: Path, audit: dict[str, Any]) -> Path:
    """Write the Markdown sibling of the authoritative outline-audit JSON."""

    target = project.expanduser().resolve() / DEFAULT_AUDIT_OUTPUT
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_outline_audit_markdown(audit), encoding="utf-8")
    return target


def render_outline_review(
    project: Path,
    input_path: Path,
    audit_path: Path,
    output: Path | None = None,
) -> Path:
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise FileNotFoundError(f"project does not exist: {project}")
    input_path = input_path.expanduser().resolve()
    audit_path = audit_path.expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"outline does not exist: {input_path}")
    if not audit_path.is_file():
        raise FileNotFoundError(f"audit report does not exist: {audit_path}")
    target = output.expanduser().resolve() if output else project / DEFAULT_OUTPUT
    outline = json.loads(input_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_outline_review_markdown(outline, audit), encoding="utf-8")
    return target
