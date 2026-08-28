from __future__ import annotations

import copy
import json
from pathlib import Path

from script_engine.analysis_audit import audit_deck_plan, audit_final_script
from script_engine.cli import main
from script_engine.internal_report_voice import (
    audit_plan_internal_expert_voice,
    consultant_voice_hits,
)
from script_engine.plan_review import evidence_status, render_plan_review


ROOT = Path(__file__).resolve().parents[2]


def _example() -> tuple[dict, dict]:
    plan = json.loads((ROOT / "examples/deck-plan.example.json").read_text(encoding="utf-8"))
    foundation = json.loads((ROOT / "examples/foundation.example.json").read_text(encoding="utf-8"))
    return plan, foundation


def test_plan_review_renders_title_message_evidence_and_bridge_without_mutation() -> None:
    plan, foundation = _example()
    before_plan = copy.deepcopy(plan)
    before_foundation = copy.deepcopy(foundation)

    markdown = render_plan_review(plan, foundation)

    assert "# 脚本规划待确认" in markdown
    assert "| P01 | 数据服务形成机制 |" in markdown
    assert "| 机制解释 |" in markdown
    assert "来源综合推断；边界条件需保留" in markdown
    assert "去向：下一页进一步说明支撑该机制的具体能力" in markdown
    assert plan == before_plan
    assert foundation == before_foundation


def test_plan_review_marks_unknown_evidence_as_incomplete() -> None:
    plan, foundation = _example()
    plan["pages"][0]["proof"]["evidence_refs"] = ["UNKNOWN"]
    plan["pages"][0]["analysis_basis"]["supports"] = []

    assert evidence_status(plan["pages"][0], foundation).startswith("证据责任不完整")


def test_plan_review_renders_structured_evidence_fit_challenge() -> None:
    plan, foundation = _example()
    page = plan["pages"][0]
    ref = page["proof"]["evidence_refs"][0]
    page["evidence_fit_review"] = {
        "question": page["question"],
        "items": [
            {
                "evidence_ref": ref,
                "fit": "direct",
                "role": "mechanism",
                "reason": "来源直接说明该机制",
            }
        ],
        "counter_case": "若来源只描述能力清单，则不能支撑机制判断",
        "verdict": "keep",
    }

    markdown = render_plan_review(plan, foundation)

    assert "#### 页面来源适配质询" in markdown
    assert "最强反例：若来源只描述能力清单，则不能支撑机制判断" in markdown
    assert f"| {ref} | 直接支持 | mechanism | 来源直接说明该机制 |" in markdown
    assert "证据适配结论：保留" in markdown


def test_plan_review_renders_source_consumption_summary() -> None:
    plan, foundation = _example()
    page = plan["pages"][0]
    refs = page["source_refs"][:2]
    page["source_refs"] = refs
    page["source_consumption"] = {
        "mode": "strict",
        "detail_refs": [refs[1]],
        "intentional_omissions": [],
        "full_prose_anchors": [
            {"source_ref": refs[0], "anchors": ["来源特征A", "来源特征B"], "minimum_hits": 1}
        ],
        "onscreen_refs": [refs[0]],
    }

    markdown = render_plan_review(plan, foundation)

    assert "#### 来源消费摘要" in markdown
    assert f"完整稿必消费来源：{refs[0]}" in markdown
    assert f"追溯详情：{refs[1]}" in markdown
    assert f"必须上屏的代表性来源：{refs[0]}" in markdown
    assert f"| {refs[0]} | 来源特征A；来源特征B | 1 |" in markdown


def test_missing_evidence_fit_mode_is_visible_and_blocks_author() -> None:
    plan, foundation = _example()
    plan.pop("evidence_fit_review_mode")

    issues, warnings = audit_deck_plan(plan, foundation)
    markdown = render_plan_review(plan, foundation, issues=issues, warnings=warnings)

    assert any("strict is required before PLAN can enter AUTHOR" in issue for issue in issues)
    assert warnings == []
    assert "来源适配门禁：缺失，阻断 AUTHOR" in markdown


def test_review_plan_cli_prints_markdown_and_creates_no_artifact(tmp_path, capsys) -> None:
    plan, foundation = _example()
    plan_path = tmp_path / "deck-plan.json"
    foundation_path = tmp_path / "foundation.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    foundation_path.write_text(json.dumps(foundation, ensure_ascii=False), encoding="utf-8")
    before = {path.name for path in tmp_path.iterdir()}

    exit_code = main(["review-plan", str(plan_path), str(foundation_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert output.startswith("# 脚本规划待确认")
    assert {path.name for path in tmp_path.iterdir()} == before


def test_business_vocabulary_is_valid_in_internal_expert_voice() -> None:
    plan = {
        "audience_scope": "internal",
        "pages": [
            {
                "id": "P01",
                "title": "客户经营成效",
                "question": "经营转化取得了哪些进展",
                "message": "客户需求牵引产品优化，市场拓展和项目成交推动数据价值释放",
                "logic": "客户需求到经营成效",
                "content": ["客户服务", "市场拓展", "项目成交", "价值释放", "商业化"],
            }
        ],
    }

    assert audit_plan_internal_expert_voice(plan) == []
    assert consultant_voice_hits("客户、市场、成交、价值释放、增长和商业化") == []


def test_internal_plan_rejects_external_consultant_address() -> None:
    plan, foundation = _example()
    plan["pages"][0]["message"] = "建议贵司全面重构客户经营体系"

    issues, _ = audit_deck_plan(plan, foundation)

    assert any("internal-expert voice required" in issue for issue in issues)
    assert any("建议贵司" in issue for issue in issues)


def test_internal_plan_checks_deck_thesis_and_keeps_business_vocabulary_available() -> None:
    plan, foundation = _example()
    plan["thesis"] = "从顾问视角看，建议贵司以客户需求牵引市场拓展和项目成交"

    issues, _ = audit_deck_plan(plan, foundation)

    assert any("plan.thesis" in issue for issue in issues)
    assert not any("客户" in issue or "市场" in issue or "成交" in issue for issue in issues)


def test_external_plan_may_address_the_client_explicitly() -> None:
    plan, _ = _example()
    plan["audience_scope"] = "external"
    plan["pages"][0]["message"] = "建议贵司完善客户经营体系"

    assert audit_plan_internal_expert_voice(plan) == []


def test_final_script_rejects_external_consultant_voice_for_internal_report() -> None:
    plan, foundation = _example()
    final_script = {
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "客户经营",
                "core_message": "客户需求牵引产品优化",
                "full_copy": "从外部咨询视角看，建议贵司全面重构客户经营体系",
                "onscreen": [],
            }
        ]
    }

    issues, _ = audit_final_script(final_script, plan, foundation)

    assert any("external consulting viewpoint" in issue for issue in issues)
    assert any("建议贵司" in issue for issue in issues)


def test_final_script_checks_relationship_copy_for_consultant_identity() -> None:
    plan, foundation = _example()
    final_script = {
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "经营机制",
                "core_message": "客户需求牵引市场拓展",
                "relationships": [{"relation": "作为外部顾问团队帮助贵司识别成交机会"}],
                "onscreen": [],
            }
        ]
    }

    issues, _ = audit_final_script(final_script, plan, foundation)

    assert any("relationships.0.relation" in issue for issue in issues)


def test_adjacent_duplicate_messages_warn_without_banning_shared_business_terms() -> None:
    plan, foundation = _example()
    first = plan["pages"][0]
    second = copy.deepcopy(first)
    second["id"] = "P02"
    second["title"] = "数据服务支撑机制"
    second["message"] = first["message"] + "。"
    plan["pages"].append(second)

    issues, warnings = audit_deck_plan(plan, foundation)

    assert issues == []
    assert any("near-duplicate core messages" in warning for warning in warnings)


def _label_detail_fixture(*, list_only_source: bool = False) -> tuple[dict, dict, dict]:
    green = (
        "重点场景包括行业治理、市场运行、绿色低碳、科技创新"
        if list_only_source
        else "绿色低碳场景用于检验标准在电碳业务中的适用性和可操作性"
    )
    foundation = {
        "source_structure": [],
        "facts": [
            {"id": "V1", "statement": green, "source_refs": ["S1"]},
            {
                "id": "V2",
                "statement": "科技创新场景用于检验标准对科研数据流通和成果应用的支撑能力",
                "source_refs": ["S2"],
            },
        ],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
    }
    module = {
        "heading": "重点验证场景",
        "evidence_refs": ["V1", "V2"],
        "required_signals": ["绿色低碳", "科技创新"],
    }
    plan = {
        "audience_scope": "internal",
        "chapters": [],
        "pages": [
            {
                "id": "P01",
                "question": "哪些场景承担标准验证",
                "message": "重点场景用于检验标准适用性",
                "logic": "场景验证",
                "content": ["绿色低碳", "科技创新"],
                "content_load": "standard",
                "proof": {"evidence_refs": ["V1", "V2"]},
                "onscreen_contract": {
                    "relation": "parallel",
                    "detail_axis": "validation_scene",
                    "modules": [module],
                },
            }
        ],
    }
    final = {
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "重点场景验证",
                "core_message": "重点场景用于检验标准适用性",
                "onscreen": [
                    {"heading": "重点验证场景", "items": ["绿色低碳", "科技创新"]}
                ],
            }
        ]
    }
    return foundation, plan, final


def test_final_audit_blocks_source_detail_collapsed_to_bare_labels() -> None:
    foundation, plan, final = _label_detail_fixture()

    issues, _ = audit_final_script(final, plan, foundation)

    assert any("ONSCREEN_SOURCE_DETAIL_COLLAPSED_TO_LABEL" in issue for issue in issues)
    assert any("绿色低碳" in issue for issue in issues)


def test_final_audit_accepts_label_with_source_grounded_explanation() -> None:
    foundation, plan, final = _label_detail_fixture()
    final["slides"][0]["onscreen"][0]["items"] = [
        "绿色低碳：检验标准在电碳业务中的适用性",
        "科技创新：检验标准对科研数据流通的支撑能力",
    ]

    issues, _ = audit_final_script(final, plan, foundation)

    assert not any("ONSCREEN_SOURCE_DETAIL_COLLAPSED_TO_LABEL" in issue for issue in issues)


def test_final_audit_allows_explicit_label_only_taxonomy_for_thin_source() -> None:
    foundation, plan, final = _label_detail_fixture(list_only_source=True)
    plan["pages"][0]["onscreen_contract"]["detail_policy"] = {
        "label_only_allowed": True
    }
    plan["pages"][0]["proof"]["evidence_refs"] = ["V1"]
    plan["pages"][0]["onscreen_contract"]["modules"][0]["evidence_refs"] = ["V1"]

    issues, _ = audit_final_script(final, plan, foundation)

    assert not any("ONSCREEN_SOURCE_DETAIL_COLLAPSED_TO_LABEL" in issue for issue in issues)
