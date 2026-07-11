"""Render grounded Stage 1 candidates into existing Markdown gate contracts."""

from __future__ import annotations

from cyberppt.phase1.grounding import GroundingReport
from cyberppt.phase1.schemas import GateDraft, SourceAnalysisDraft


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


def _list(value: object) -> str:
    if isinstance(value, list):
        return "、".join(str(item) for item in value)
    return str(value)


def render_gate_output(gate: str, draft: GateDraft) -> str:
    payload = draft.payload
    if gate == "reporting_direction":
        lines = [
            "# 汇报方向策略",
            "## 汇报对象", str(payload["audience"]),
            "## 汇报目的", str(payload["purpose"]),
            "## 内容重点", str(payload["content_focus"]),
            "## 证据", _list(payload["evidence"]),
            "## 优势", _list(payload["strengths"]),
            "## 边界", _list(payload["boundaries"]),
            "## 推荐方向", str(payload["recommendation"]),
            "## 备选方向",
        ]
        lines.extend(f"- {item.get('id', 'option')}: {item.get('label', '未提供')}；{item.get('reason', '未提供理由')}" for item in payload["options"])
        return "\n".join(lines) + "\n"
    if gate == "report_structure":
        lines = ["# 汇报结构"]
        for index, item in enumerate(payload["modules"], start=1):
            lines.extend(
                [
                    f"## 模块{index}",
                    f"- 模块事项：{item['title']}",
                    f"- 组织重点：{item['focus']}",
                    f"- 证据：{_list(item['evidence_ids'])}",
                ]
            )
        return "\n".join(lines) + "\n"
    if gate == "page_design":
        lines = ["# 页面设计"]
        for item in payload["pages"]:
            lines.extend(
                [
                    f"## 第 {item['page']} 页：{item['title']}",
                    f"### 页面角色\n{item['role']}",
                    f"### 详细说明\n{item['detail']}",
                    f"### 证据\n{_list(item['evidence_ids'])}",
                    f"### Caveat\n{item['caveat']}",
                    f"### 图表计划\n{item['chart_plan']}",
                    f"### 视觉\n{item['visual']}",
                    f"### 含义\n{item['meaning']}",
                    f"### 承接\n{item['transition']}",
                    f"### 信息密度\n{item['density']}",
                    f"### 组件清单\n{_list(item['components'])}",
                ]
            )
        return "\n".join(lines) + "\n"
    if gate == "business_script":
        lines = ["# 页面业务稿"]
        for item in payload["pages"]:
            completeness = item["completeness"]
            lines.extend(
                [
                    f"## 第 {item['page']} 页：{item['title']}",
                    "### 上屏文字",
                    *[f"- {value}" for value in item["visible_content"]],
                    "### 非上屏：证据链",
                    *[f"- {value}" for value in item["evidence_ids"]],
                    "### 来源位置",
                    *[f"- {value}" for value in item["source_locations"]],
                    "### 非上屏：完整性校核",
                    *[f"- {category}：{_list(completeness[category])}" for category in ("事实", "数字", "分类", "边界", "请求事项")],
                    f"### 非上屏：信息密度\n- {item['density']}",
                    f"### 页面含义\n{item['meaning']}",
                    f"### 页面承接\n{item['transition']}",
                ]
            )
        return "\n".join(lines) + "\n"
    raise ValueError(f"unsupported downstream gate: {gate}")
