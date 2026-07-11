from __future__ import annotations

import json

import pytest

from cyberppt.phase1.grounding import ground_gate_output
from cyberppt.phase1.prompts import build_gate_prompt
from cyberppt.phase1.renderers import render_gate_output
from cyberppt.phase1.schemas import GateDraft, parse_gate_output


def direction_payload(evidence_ids: list[str] | None = None) -> dict[str, object]:
    return {
        "audience": "分管领导",
        "purpose": "审定工作安排",
        "content_focus": "建设必要性和首期任务",
        "evidence": evidence_ids or ["E01"],
        "strengths": ["具备行业组织基础"],
        "boundaries": ["投资仍需专项论证"],
        "options": [
            {"id": "leadership", "label": "领导审定型", "reason": "适合当前任务"},
            {"id": "execution", "label": "执行对齐型", "reason": "适合实施会"},
        ],
        "recommendation": "leadership",
    }


def valid_payload(gate: str) -> dict[str, object]:
    if gate == "reporting_direction":
        return direction_payload()
    if gate == "report_structure":
        return {
            "modules": [
                {"title": "建设背景", "focus": "说明必要性", "evidence_ids": ["E01"]},
                {"title": "实施安排", "focus": "说明路径", "evidence_ids": ["E02"]},
                {"title": "审定事项", "focus": "形成决策请求", "evidence_ids": ["E03"]},
            ]
        }
    if gate == "page_design":
        return {
            "pages": [
                {
                    "page": 4,
                    "title": "形势变化与工作要求",
                    "role": "Complication",
                    "detail": "说明行业环境变化",
                    "evidence_ids": ["E01"],
                    "caveat": "数字沿用源材料口径",
                    "visual": "数据组与变量演进图",
                    "chart_plan": "三组行业指标",
                    "meaning": "说明建设必要性",
                    "transition": "进入工作基础",
                    "density": "5 个信息区",
                    "components": ["KPI", "变量地图", "说明栏"],
                }
            ]
        }
    if gate == "business_script":
        return {
            "pages": [
                {
                    "page": 4,
                    "title": "形势变化与工作要求",
                    "visible_content": ["2025年用电量103682亿千瓦时", "供需研判对象扩展"],
                    "evidence_ids": ["E01"],
                    "source_locations": ["P26"],
                    "completeness": {
                        "事实": ["供需研判对象扩展"],
                        "数字": ["103682"],
                        "分类": ["行业运行指标"],
                        "边界": ["沿用源材料口径"],
                        "请求事项": ["确认研判范围"],
                    },
                    "density": "5 个信息区",
                    "meaning": "说明建设必要性",
                    "transition": "进入工作基础",
                }
            ]
        }
    raise AssertionError(gate)


@pytest.mark.parametrize("gate", ["reporting_direction", "report_structure", "page_design", "business_script"])
def test_unknown_evidence_ids_block_downstream_gate(gate: str) -> None:
    payload = valid_payload(gate)
    if gate == "reporting_direction":
        payload["evidence"] = ["E99"]
    elif gate == "report_structure":
        payload["modules"][0]["evidence_ids"] = ["E99"]
    else:
        payload["pages"][0]["evidence_ids"] = ["E99"]

    draft = parse_gate_output(gate, json.dumps(payload, ensure_ascii=False))
    report = ground_gate_output(gate, draft, {"E01", "E02", "E03"})

    assert report.blocking
    assert any(issue.code == "unknown_evidence_id" for issue in report.issues)


def test_business_script_visible_numbers_must_exist_in_cited_evidence() -> None:
    payload = valid_payload("business_script")
    payload["pages"][0]["visible_content"] = ["2025年用电量120000亿千瓦时"]
    draft = parse_gate_output("business_script", json.dumps(payload, ensure_ascii=False))

    report = ground_gate_output(
        "business_script",
        draft,
        {"E01"},
        evidence_numbers={"E01": {"2025", "103682"}},
    )

    assert any(issue.code == "visible_number_not_grounded" for issue in report.issues)


def test_gate_prompt_contains_approved_artifacts_and_constraints() -> None:
    prompt = build_gate_prompt(
        "page_design",
        {"source_analysis": "E01 供需平衡", "reporting_direction": "领导审定型"},
        "E01：供需平衡；E02：建设安排",
        {"internal_reporting": "正式、客观、审慎"},
    )

    assert "不得新增事实、数字、来源或外部知识" in prompt
    assert "领导审定型" in prompt
    assert "E01：供需平衡" in prompt
    assert "page_design" in prompt


@pytest.mark.parametrize("gate", ["reporting_direction", "report_structure", "page_design", "business_script"])
def test_gate_renderer_produces_markdown_candidate(gate: str) -> None:
    draft = parse_gate_output(gate, json.dumps(valid_payload(gate), ensure_ascii=False))

    rendered = render_gate_output(gate, draft)

    assert rendered.startswith("# ")
    assert "E01" in rendered
    assert "未提供" not in rendered
