"""Persist outline audit attempts and bounded retry directions."""

from __future__ import annotations

import json
from pathlib import Path

from cyberppt.argument_flow_contract import (
    argument_graph_summary,
    audit_argument_flow,
)
from cyberppt.outline_contract import audit_outline, load_outline, retry_directive
from cyberppt.source_truth_contract import load_source_truth
from cyberppt.semantic_proposition_contract import build_proposition_graph
from cyberppt.stage01_controls import (
    assert_escalation_resolved,
    snapshot_reference_gate,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_outline_markdown(payload: dict[str, object], report: dict[str, object]) -> str:
    """Render the audited outline as the human review artifact."""

    pages = payload.get("pages") if isinstance(payload.get("pages"), list) else []
    content_pages = [
        page for page in pages
        if isinstance(page, dict) and page.get("page_type") == "content"
    ]
    lines = [
        "# Stage 01 逐页大纲（人类审阅稿）",
        "",
        "> 本文件由 `cyberppt outline-audit` 从 `outline.json` 自动生成。",
        "> Markdown 是大纲确认入口；JSON 仅作为机器审计合同。",
        "",
        "## 大纲摘要",
        "",
        f"- 架构：`{payload.get('architecture_mode', '未声明')}`",
        f"- 材料类型：{payload.get('material_type', '未声明')}",
        f"- 受众：{payload.get('audience', '未声明')}",
        f"- 总页数：{len(pages)}",
        f"- 内容页：{len(content_pages)}",
        f"- 大纲审计：**{report.get('status', 'unknown')}**",
        "",
    ]
    semantics = payload.get("document_semantics")
    if isinstance(semantics, dict):
        lines.extend(
            [
                "## 文档语义身份",
                "",
                f"- 文档身份：{semantics.get('document_role', '未声明')}",
                f"- 汇报对象：{semantics.get('subject_of_report', '未声明')}",
                f"- 全篇核心命题：{semantics.get('primary_thesis', '未声明')}",
                f"- 成果边界：{semantics.get('decision_boundary', '未声明')}",
                "",
            ]
        )
    narrative_logic = payload.get("narrative_logic")
    if isinstance(narrative_logic, list) and narrative_logic:
        lines.extend(["## 全篇逻辑", ""])
        for index, item in enumerate(narrative_logic, 1):
            if str(item).strip():
                lines.append(f"{index}. {item}")
        lines.append("")
    lines.extend(["## 逐页大纲", ""])
    for index, raw_page in enumerate(pages, start=1):
        if not isinstance(raw_page, dict):
            continue
        sequence = raw_page.get("sequence", index)
        page_id = raw_page.get("page_id", f"p{index:02d}")
        page_type = str(raw_page.get("page_type") or "content")
        title = str(raw_page.get("title") or "未命名页面")
        lines.append(f"### 第 {sequence} 页｜{title}")
        lines.append("")
        lines.append(f"- 页面编号：`{page_id}`")
        lines.append(f"- 页面类型：`{page_type}`")
        if raw_page.get("chapter_id"):
            lines.append(f"- 所属章节：`{raw_page['chapter_id']}`")
        if page_type == "content":
            fields = (
                ("页面使命", raw_page.get("page_mission") or raw_page.get("page_job") or raw_page.get("business_question")),
                ("核心结论", raw_page.get("core_message") or raw_page.get("main_message")),
                ("上屏结论", raw_page.get("onscreen_conclusion") or raw_page.get("onscreen_judgment")),
                ("主视觉", raw_page.get("visual_center")),
                ("相对前页新增价值", raw_page.get("new_value_vs_previous")),
                ("留待后文", raw_page.get("reserved_for_later")),
            )
            for label, value in fields:
                if value:
                    lines.append(f"- {label}：{value}")
            derivation = raw_page.get("core_message_derivation") or raw_page.get("judgment_derivation")
            if isinstance(derivation, dict) and derivation:
                refs = derivation.get("source_refs")
                if isinstance(refs, list) and refs:
                    lines.append("- 核心结论依据：" + "、".join(f"`{ref}`" for ref in refs))
                if derivation.get("derivation"):
                    lines.append(f"- 核心结论推导：{derivation['derivation']}")
            relations = raw_page.get("content_relations")
            if isinstance(relations, list) and relations:
                lines.extend(["", "  内容关系：", ""])
                for relation in relations:
                    if not isinstance(relation, dict):
                        continue
                    subject = str(relation.get("subject") or "")
                    predicate = str(relation.get("relation") or "")
                    objects = relation.get("objects") or relation.get("object") or ""
                    if isinstance(objects, list):
                        objects = "、".join(str(item) for item in objects)
                    lines.append(f"  - {subject} → `{predicate}` → {objects}")
            refs = raw_page.get("source_refs")
            if isinstance(refs, list) and refs:
                lines.append("- 证据 ID：" + "、".join(f"`{ref}`" for ref in refs))
            modules = raw_page.get("modules")
            if isinstance(modules, list) and modules:
                labels = []
                for module in modules:
                    if not isinstance(module, dict):
                        continue
                    name = str(module.get("title") or module.get("role") or "未命名模块")
                    role = str(module.get("role") or "")
                    labels.append(f"{name}（{role}）" if role else name)
                if labels:
                    lines.append("- 页面模块：" + "；".join(labels))
            content_units = raw_page.get("content_units") or raw_page.get("proof_points")
            if isinstance(content_units, list) and content_units:
                lines.extend(["", "  内容单元：", ""])
                for point in content_units:
                    if not isinstance(point, dict):
                        continue
                    claim = str(point.get("statement") or point.get("claim") or "").strip()
                    point_refs = point.get("source_refs")
                    suffix = ""
                    if isinstance(point_refs, list) and point_refs:
                        suffix = "（" + "、".join(str(ref) for ref in point_refs) + "）"
                    if claim:
                        lines.append(f"  - {claim}{suffix}")
            boundaries = raw_page.get("boundary_refs")
            if isinstance(boundaries, list) and boundaries:
                lines.append("- 边界证据：" + "、".join(f"`{ref}`" for ref in boundaries))
        lines.append("")

    issues = report.get("issues") if isinstance(report.get("issues"), list) else []
    lines.extend(["## 审计结论", ""])
    if issues:
        lines.append(f"当前有 {len(issues)} 个未关闭问题，大纲不得批准。")
        for issue in issues:
            if isinstance(issue, dict):
                lines.append(f"- `{issue.get('code', 'ISSUE')}`：{issue.get('message', '')}")
    else:
        lines.append("结构化大纲审计已通过；请人工确认架构、页数、章节边界和逐页核心结论。")
    lines.append("")
    return "\n".join(lines)


def _write_outline_markdown(
    path: Path, payload: dict[str, object], report: dict[str, object]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_outline_markdown(payload, report), encoding="utf-8")


def _escalation_options(codes: list[str]) -> list[dict[str, str]]:
    options = [
        {"id": "source_native", "label": "恢复源材料方案顺序", "action": "按材料角色和正式章节使命重建连续页面序列。"},
        {"id": "business_aggregation", "label": "按业务问题聚合", "action": "合并重复业务问题与视觉中心，重新分配页面密度。"},
    ]
    if "SOURCE_WEIGHT_DISTORTED" in codes or "SOLUTION_ARCHITECTURE_REQUIRED" in codes:
        options.append({"id": "user_priority", "label": "由用户明确优先级", "action": "提交主体内容权重冲突，请用户选择优先方向。"})
    return options[:3]


def run_outline_audit(
    project: Path,
    input_path: Path,
    max_attempts: int = 3,
    source_truth_path: Path | None = None,
) -> tuple[int, dict[str, object]]:
    if not 1 <= max_attempts <= 5:
        raise ValueError("max_attempts must be between 1 through 5")
    project = project.expanduser().resolve()
    if not project.exists():
        raise FileNotFoundError(f"project does not exist: {project}")
    assert_escalation_resolved(project, "source_truth")
    payload = load_outline(input_path.expanduser().resolve())
    resolved_source_truth = (
        source_truth_path.expanduser().resolve()
        if source_truth_path is not None
        else project
        / "workbench"
        / "stages"
        / "01-analysis"
        / "source-truth.json"
    )
    source_truth = (
        load_source_truth(resolved_source_truth)
        if resolved_source_truth.exists()
        else None
    )
    if source_truth_path is not None and source_truth is None:
        raise FileNotFoundError(f"source truth does not exist: {resolved_source_truth}")
    retry = payload.get("retry") if isinstance(payload.get("retry"), dict) else {}
    attempt = int(retry.get("attempt", 1))
    effective_max = int(retry.get("max_attempts", max_attempts))
    if not 1 <= effective_max <= 5:
        raise ValueError("retry.max_attempts must be between 1 through 5")
    stage = project / "workbench" / "stages" / "01-analysis"
    argument_issues = (
        audit_argument_flow(payload, source_truth)
        if source_truth is not None
        else []
    )
    issues = audit_outline(payload, source_truth)
    directive = retry_directive(issues, str(retry.get("strategy") or ""))
    report: dict[str, object] = {
        "schema": "cyberppt.outline_audit.v1",
        "status": "passed" if not issues else "rewrite_required",
        "attempt": attempt,
        "max_attempts": effective_max,
        "remaining_attempts": max(0, effective_max - attempt),
        "issues": [issue.to_dict() for issue in issues],
        "retry_directive": directive,
        "argument_contract_mode": str(
            payload.get("argument_contract_mode") or "legacy"
        ),
        "semantic_contract_mode": (
            "source_relations"
            if payload.get("schema") == "cyberppt.outline.v2"
            else "legacy_argument_roles"
        ),
        "checked_source_truth": (
            str(resolved_source_truth) if source_truth is not None else None
        ),
        "argument_graph": argument_graph_summary(payload, source_truth),
        "failed_edges": [
            list(edge)
            for issue in argument_issues
            for edge in issue.failed_edges
        ],
        "retry_scope": sorted(
            {
                page
                for issue in argument_issues
                for page in issue.pages
                if page
            }
        ),
        "reference_gate": snapshot_reference_gate("outline", project),
    }
    _write_json(stage / "outline-contract.json", payload)
    _write_json(stage / "proposition-graph.json", build_proposition_graph(payload))
    _write_json(stage / "outline-audit.json", report)
    _write_json(stage / "outline-attempts" / f"attempt-{attempt:02d}.json", {"outline": payload, "audit": report})
    _write_outline_markdown(stage / "01-outline-readable.md", payload, report)
    if not issues:
        return 0, report
    if attempt < effective_max:
        return 4, report
    codes = list(directive["issue_codes"])
    report["status"] = "user_decision_required"
    report["options"] = _escalation_options(codes)
    _write_json(stage / "outline-audit.json", report)
    _write_json(stage / "outline-escalation.json", report)
    _write_outline_markdown(stage / "01-outline-readable.md", payload, report)
    return 5, report
