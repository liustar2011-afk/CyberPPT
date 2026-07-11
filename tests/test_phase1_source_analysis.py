from __future__ import annotations

import json

import pytest

from cyberppt.phase1.prompts import build_source_analysis_prompt
from cyberppt.phase1.renderers import render_source_analysis
from cyberppt.phase1.schemas import (
    EvidenceCandidate,
    SourceAnalysisDraft,
    parse_source_analysis_output,
)
from cyberppt.phase1.source_bundle import SourceBundle, SourceChunk, SourceUnit
from cyberppt.phase1.grounding import ground_source_analysis


def bundle_with_unit(unit_id: str, text: str, numbers: tuple[str, ...]) -> SourceBundle:
    unit = SourceUnit(unit_id, "paragraph", text, "source.md", "P1", numbers)
    chunk = SourceChunk("C001", (unit_id,), len(text))
    return SourceBundle("source.md", "source-hash", (unit,), (chunk,))


def valid_payload() -> dict[str, object]:
    return {
        "material_type": "工作方案",
        "reporting_task": "领导审定",
        "audience": "分管领导",
        "evidence": [
            {
                "claim": "2025年用电量达到103682亿千瓦时",
                "verbatim_support": "2025年用电量103682亿千瓦时",
                "source_unit_ids": ["U0001"],
                "numbers": ["2025", "103682"],
                "confidence": "high",
                "caveat": "原文未提供计算底表",
                "meaning": "说明运行规模",
                "visual": "KPI",
            }
        ],
        "storylines": [],
        "material_pool": [],
        "confirmation_questions": ["是否确认首期范围？"],
    }


def test_parse_source_analysis_accepts_fenced_json() -> None:
    text = "```json\n" + json.dumps(valid_payload(), ensure_ascii=False) + "\n```"

    draft = parse_source_analysis_output(text)

    assert draft.material_type == "工作方案"
    assert draft.evidence[0].source_unit_ids == ("U0001",)


def test_parse_source_analysis_rejects_missing_required_array() -> None:
    payload = valid_payload()
    del payload["evidence"]

    with pytest.raises(ValueError, match="evidence"):
        parse_source_analysis_output(json.dumps(payload, ensure_ascii=False))


def test_grounding_rejects_number_missing_from_cited_units() -> None:
    bundle = bundle_with_unit("U0001", "2025年用电量103682亿千瓦时", ("2025", "103682"))
    draft = SourceAnalysisDraft(
        material_type="工作方案",
        reporting_task="领导审定",
        audience="分管领导",
        evidence=(
            EvidenceCandidate(
                claim="2025年用电量达到120000亿千瓦时",
                verbatim_support="2025年用电量103682亿千瓦时",
                source_unit_ids=("U0001",),
                numbers=("120000",),
                confidence="high",
                caveat="",
                meaning="说明运行规模",
                visual="KPI",
            ),
        ),
        storylines=(),
        material_pool=(),
        confirmation_questions=(),
    )

    report = ground_source_analysis(draft, bundle)

    assert report.blocking
    assert report.issues[0].code == "number_not_in_source"


def test_grounding_rejects_unknown_unit_and_non_verbatim_support() -> None:
    bundle = bundle_with_unit("U0001", "供需总体平衡。", ())
    payload = valid_payload()
    payload["evidence"] = [
        {
            **payload["evidence"][0],
            "claim": "源材料未提供该结论",
            "verbatim_support": "源材料没有这句话",
            "source_unit_ids": ["U9999"],
            "numbers": [],
        }
    ]
    draft = parse_source_analysis_output(json.dumps(payload, ensure_ascii=False))

    report = ground_source_analysis(draft, bundle)

    assert report.blocking
    assert {issue.code for issue in report.issues} == {"unknown_source_unit", "verbatim_support_missing"}


def test_prompt_contains_reference_contract_and_source_units() -> None:
    bundle = bundle_with_unit("U0001", "供需总体平衡。", ())

    prompt = build_source_analysis_prompt(bundle, {"source_analysis": "证据表规则"})

    assert "不得新增事实、数字、来源或外部知识" in prompt
    assert "U0001" in prompt
    assert "证据表规则" in prompt
    assert "source_unit_ids" in prompt


def test_renderer_assigns_deterministic_evidence_ids_and_required_headings() -> None:
    bundle = SourceBundle(
        "source.md",
        "source-hash",
        (
            SourceUnit("U0001", "paragraph", "后出现结论。", "source.md", "P2", ()),
            SourceUnit("U0002", "paragraph", "先出现结论。", "source.md", "P1", ()),
        ),
        (SourceChunk("C001", ("U0001", "U0002"), 10),),
    )
    payload = valid_payload()
    payload["evidence"] = [
        {**payload["evidence"][0], "claim": "后出现结论", "verbatim_support": "后出现结论", "source_unit_ids": ["U0001"], "numbers": []},
        {**payload["evidence"][0], "claim": "先出现结论", "verbatim_support": "先出现结论", "source_unit_ids": ["U0002"], "numbers": []},
    ]
    draft = parse_source_analysis_output(json.dumps(payload, ensure_ascii=False))
    report = ground_source_analysis(draft, bundle)

    rendered = render_source_analysis(draft, report)

    assert "## 输入盘点" in rendered
    assert "## 证据表" in rendered
    assert "## 开放数据冲突" in rendered
    assert "## 内容脑暴" in rendered
    assert "## 页面物料池" in rendered
    assert "E01" in rendered and "先出现结论" in rendered
    assert rendered.index("E01") < rendered.index("E02")
