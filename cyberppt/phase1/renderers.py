"""Render grounded Stage 1 candidates into existing Markdown gate contracts."""

from __future__ import annotations

from cyberppt.phase1.grounding import GroundingReport
from cyberppt.phase1.schemas import SourceAnalysisDraft


def _value(item: dict[str, object], key: str, default: str = "未提供") -> str:
    value = item.get(key)
    if isinstance(value, list):
        return "、".join(str(part) for part in value)
    return str(value).strip() if value not in (None, "") else default


def render_source_analysis(draft: SourceAnalysisDraft, report: GroundingReport) -> str:
    lines = [
        "# 阶段一确认包",
        "",
        "## 输入盘点",
        f"- 材料类型：{draft.material_type}",
        f"- 汇报任务：{draft.reporting_task}",
        f"- 受众：{draft.audience}",
        "",
        "## 证据表",
        "| ID | 论点或数据 | 数值 | 来源位置 | 置信度 | 冲突或 caveat | 含义 | 推荐视觉 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    locations = dict(report.source_locations)
    for evidence_id, candidate in zip(report.evidence_ids, report.accepted_evidence):
        lines.append(
            "| {id} | {claim} | {numbers} | {locations} | {confidence} | {caveat} | {meaning} | {visual} |".format(
                id=evidence_id,
                claim=candidate.claim,
                numbers=" / ".join(candidate.numbers) or "未提供",
                locations="、".join(locations[evidence_id]),
                confidence=candidate.confidence,
                caveat=candidate.caveat,
                meaning=candidate.meaning,
                visual=candidate.visual,
            )
        )
    lines.extend(["", "## 开放数据冲突"])
    if report.issues:
        lines.extend(f"- 待复核：{issue.message}" for issue in report.issues)
    else:
        lines.append("- 未发现模型输出与源材料之间的落地冲突。")

    lines.extend(["", "## 内容脑暴"])
    for index, storyline in enumerate(draft.storylines, start=1):
        lines.extend(
            [
                f"### 备选 {index}：{_value(storyline, 'title', f'备选主线{index}')}",
                f"- 核心事项：{_value(storyline, 'core_conclusion')}",
                f"- 组织方式：{_value(storyline, 'organization')}",
                f"- 证据：{_value(storyline, 'evidence_unit_ids')}",
                f"- Caveat：{_value(storyline, 'caveat')}",
            ]
        )
    if not draft.storylines:
        lines.append("- 待形成至少两条备选汇报主线。")

    lines.extend(["", "## 页面物料池"])
    for item in draft.material_pool:
        lines.append(f"- {_value(item, 'item', _value(item, 'description'))}")
    if not draft.material_pool:
        lines.append("- 待根据证据表补充可视化物料。")

    lines.extend(["", "## 需要用户决策的问题"])
    lines.extend(f"{index}. {question}" for index, question in enumerate(draft.confirmation_questions, start=1))
    if not draft.confirmation_questions:
        lines.append("1. 请确认材料类型、汇报任务和推荐主线。")
    return "\n".join(lines) + "\n"
