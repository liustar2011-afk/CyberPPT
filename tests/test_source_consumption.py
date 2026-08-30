from __future__ import annotations

from copy import deepcopy

from script_engine.analysis_audit import audit_deck_plan, audit_final_script
from script_engine.contracts import validate_deck_plan


def _foundation() -> dict:
    return {
        "source_structure": [],
        "facts": [
            {"id": "ST1", "statement": "统一电力数据基础设施术语定义并衔接国家参考架构"},
            {"id": "ST2", "statement": "制定电力数据质量评价指标体系并覆盖全过程质量控制"},
            {"id": "ST3", "statement": "制定电力数据资产登记评估和入表相关标准"},
        ],
        "concepts": [], "entities": [], "relations": [], "arguments": [],
        "constraints": [], "numbers": [],
    }


def _strict_foundation() -> dict:
    foundation = deepcopy(_foundation())
    foundation["source_consumption_policy"] = "required"
    foundation["facts"][0]["coverage_anchors"] = ["术语定义", "国家参考架构"]
    foundation["facts"][1]["semantic_units"] = [
        {"text": "数据质量评价指标体系覆盖全过程质量控制", "claim_role": "requirement"}
    ]
    foundation["facts"][2]["coverage_anchors"] = ["资产登记", "评估", "入表"]
    return foundation


def _page() -> dict:
    return {
        "id": "P01",
        "question": "标准如何落地",
        "message": "标准覆盖共同语言与资源治理",
        "logic": "并列",
        "content": ["术语", "质量"],
        "primary_relation": {"type": "parallel", "scope": ["术语", "质量"], "authority": "hard"},
        "source_refs": ["ST1", "ST2", "ST3"],
        "source_consumption": {
            "mode": "strict",
            "detail_refs": ["ST3"],
            "full_prose_anchors": [
                {"source_ref": "ST2", "anchors": ["数据质量", "全过程质量控制"], "minimum_hits": 2}
            ],
            "onscreen_refs": ["ST1"],
        },
        "onscreen_contract": {
            "relation": "parallel",
            "detail_axis": "standard_scope",
            "modules": [
                {
                    "heading": "基础通用",
                    "evidence_refs": ["ST1"],
                    "required_signals": ["术语定义"],
                    "evidence_fit_review": {
                        "question": "基础通用标准统一什么内容",
                        "items": [{"evidence_ref": "ST1", "fit": "direct", "role": "standard_scope", "reason": "ST1 directly defines the terminology scope"}],
                        "counter_case": "A resource-quality rule would belong to the data-resource module",
                        "verdict": "keep",
                    },
                },
                {
                    "heading": "数据资源",
                    "evidence_refs": ["ST2"],
                    "required_signals": ["全过程质量控制"],
                    "evidence_fit_review": {
                        "question": "数据资源标准覆盖什么要求",
                        "items": [{"evidence_ref": "ST2", "fit": "direct", "role": "quality_requirement", "reason": "ST2 directly states the lifecycle quality requirement"}],
                        "counter_case": "A terminology definition would belong to the basic-common module",
                        "verdict": "keep",
                    },
                },
            ],
        },
    }


def _plan(page: dict | None = None) -> dict:
    return {
        "communication_goal": "说明标准范围",
        "evidence_fit_review_mode": "strict",
        "chapters": [],
        "pages": [page or _page()],
    }


def _final(full_copy: str | None = None) -> dict:
    return {
        "slides": [{
            "id": "P01", "page_type": "content", "title": "标准范围",
            "core_message": "标准覆盖共同语言与资源治理",
            "full_copy": full_copy or "统一电力数据基础设施术语定义并衔接国家参考架构。制定电力数据质量评价指标体系，覆盖全过程质量控制。",
            "onscreen": [
                {"heading": "基础通用", "items": ["统一术语定义"]},
                {"heading": "数据资源", "items": ["覆盖全过程质量控制"]},
            ],
        }]
    }


def test_legacy_page_without_source_consumption_remains_compatible() -> None:
    page = _page()
    page.pop("source_consumption")
    issues, _ = audit_final_script(_final("完全无关的完整稿"), _plan(page), _foundation())
    assert not any("source_consumption" in issue for issue in issues)


def test_author_gate_rejects_structural_metadata_concatenated_into_full_copy() -> None:
    page = _page()
    page["source_refs"] = ["ST1", "ST2", "ST3", "META1", "META2"]
    foundation = _strict_foundation()
    foundation["facts"].extend([
        {"id": "META1", "statement": "目 录"},
        {"id": "META2", "statement": "2026年7月"},
    ])
    final = _final(
        "标准覆盖共同语言与资源治理；目 录；2026年7月；基础通用；数据资源；治理要求"
    )

    issues, _ = audit_final_script(final, _plan(page), foundation)

    assert any("AUTHOR_STRUCTURAL_METADATA_LEAK" in issue for issue in issues)
    assert any("AUTHOR_MECHANICAL_SOURCE_CONCATENATION" in issue for issue in issues)


def test_author_gate_rejects_phrase_led_self_read_fragments() -> None:
    page = _page()
    page["onscreen_contract"]["expression_mode"] = "phrase_led"
    final = _final()
    final["deck"] = {"delivery_mode": "self_read"}
    final["slides"][0]["onscreen"][1]["items"] = ["月度修正、重点时段和区域专题"]

    issues, _ = audit_final_script(final, _plan(page), _strict_foundation())

    assert any("AUTHOR_ONSCREEN_INCOMPLETE_DETAIL" in issue for issue in issues)


def test_author_gate_accepts_complete_phrase_led_business_proposition() -> None:
    page = _page()
    page["onscreen_contract"]["expression_mode"] = "phrase_led"
    final = _final()
    final["deck"] = {"delivery_mode": "self_read"}
    final["slides"][0]["onscreen"][0]["items"] = [
        "基础通用标准统一电力数据基础设施术语定义"
    ]
    final["slides"][0]["onscreen"][1]["items"] = [
        "需求侧结构变化增加了负荷预测难度"
    ]

    issues, _ = audit_final_script(final, _plan(page), _strict_foundation())

    assert not any("AUTHOR_ONSCREEN_INCOMPLETE_DETAIL" in issue for issue in issues)


def test_strict_foundation_missing_contract_fails_plan_and_author() -> None:
    page = _page()
    page.pop("source_consumption")

    plan_issues, _ = audit_deck_plan(_plan(page), _strict_foundation())
    final_issues, _ = audit_final_script(
        _final("完全无关的完整稿"), _plan(page), _strict_foundation()
    )

    assert any("SOURCE_CONSUMPTION_CONTRACT_MISSING" in issue for issue in plan_issues)
    assert any("SOURCE_CONSUMPTION_CONTRACT_MISSING" in issue for issue in final_issues)


def test_strict_structural_page_with_sources_is_exempt() -> None:
    page = _page()
    page["page_role"] = "agenda"
    page.pop("source_consumption")
    issues, _ = audit_deck_plan(_plan(page), _strict_foundation())
    assert not any("SOURCE_CONSUMPTION_CONTRACT_MISSING" in issue for issue in issues)


def test_schema_and_plan_audit_reject_invalid_mode_and_outside_ref() -> None:
    page = _page()
    page["source_consumption"]["mode"] = "required"
    page["source_consumption"]["detail_refs"] = ["ST9"]
    assert validate_deck_plan(_plan(page))
    issues, _ = audit_deck_plan(_plan(page), _foundation())
    joined = "\n".join(issues)
    assert "must be 'strict'" in joined
    assert "outside refs ['ST9']" in joined


def test_detail_ref_is_exempt_from_full_copy() -> None:
    issues, _ = audit_final_script(_final(), _plan(), _foundation())
    assert not any("ST3" in issue and "full_copy gap" in issue for issue in issues)


def test_specific_intentional_omission_passes_but_short_reason_fails() -> None:
    page = _page()
    page["source_consumption"]["detail_refs"] = []
    page["source_consumption"]["intentional_omissions"] = [
        {"source_refs": ["ST3"], "reason": "该项保留到后续资产管理专题页面展开"}
    ]
    assert validate_deck_plan(_plan(page)) == []
    issues, _ = audit_final_script(_final(), _plan(page), _foundation())
    assert not any("ST3" in issue and "full_copy gap" in issue for issue in issues)

    bad = deepcopy(page)
    bad["source_consumption"]["intentional_omissions"][0]["reason"] = "后续再说"
    assert validate_deck_plan(_plan(bad))
    issues, _ = audit_deck_plan(_plan(bad), _foundation())
    assert any("at least 8 characters" in issue for issue in issues)


def test_missing_and_sufficient_full_prose_anchors() -> None:
    issues, _ = audit_final_script(
        _final("统一电力数据基础设施术语定义并衔接国家参考架构。仅说明数据质量。"),
        _plan(), _foundation(),
    )
    assert any("ST2" in issue and "全过程质量控制" in issue for issue in issues)

    issues, _ = audit_final_script(_final(), _plan(), _foundation())
    assert not any("ST2" in issue and "full_copy gap" in issue for issue in issues)


def test_unanchored_required_source_uses_statement_overlap() -> None:
    page = _page()
    page["source_consumption"]["full_prose_anchors"] = []
    issues, _ = audit_final_script(_final("全过程质量控制与术语都没讲清楚"), _plan(page), _foundation())
    assert any("ST1" in issue and "overlap=" in issue for issue in issues)


def test_strict_plan_requires_grounded_anchor_for_every_full_copy_ref() -> None:
    page = _page()
    page["source_consumption"]["full_prose_anchors"].append(
        {"source_ref": "ST1", "anchors": ["完全不存在的来源特征"], "minimum_hits": 1}
    )
    issues, _ = audit_deck_plan(_plan(page), _strict_foundation())
    joined = "\n".join(issues)
    assert "SOURCE_CONSUMPTION_ANCHOR_NOT_SOURCE_GROUNDED" in joined
    assert "SOURCE_CONSUMPTION_ANCHOR_MISSING" not in joined


def test_strict_plan_rejects_missing_anchor_and_empty_onscreen_selection() -> None:
    page = _page()
    page["source_consumption"]["onscreen_refs"] = []
    issues, _ = audit_deck_plan(_plan(page), _strict_foundation())
    joined = "\n".join(issues)
    assert "SOURCE_CONSUMPTION_ANCHOR_MISSING" in joined
    assert "SOURCE_CONSUMPTION_ONSCREEN_SELECTION_MISSING" in joined


def test_onscreen_ref_requires_contract_and_module_mapping() -> None:
    page = _page()
    page.pop("onscreen_contract")
    issues, _ = audit_deck_plan(_plan(page), _foundation())
    assert any("requires an onscreen_contract" in issue for issue in issues)

    page = _page()
    page["onscreen_contract"]["modules"][0]["evidence_refs"] = ["ST2"]
    issues, _ = audit_deck_plan(_plan(page), _foundation())
    assert any("unmapped refs ['ST1']" in issue for issue in issues)


def test_mapped_onscreen_ref_requires_visible_signal() -> None:
    issues, _ = audit_final_script(_final(), _plan(), _foundation())
    assert not any("required signal" in issue for issue in issues)

    bad = _final()
    bad["slides"][0]["onscreen"][0]["items"] = ["统一架构"]
    issues, _ = audit_final_script(bad, _plan(), _foundation())
    assert any(
        "ONSCREEN_REQUIRED_SIGNAL_MISSING" in issue and "required signal '术语定义'" in issue
        for issue in issues
    )


def test_onscreen_ref_cannot_be_detail_or_omitted() -> None:
    page = _page()
    page["source_consumption"]["detail_refs"] = ["ST1"]
    issues, _ = audit_deck_plan(_plan(page), _foundation())
    assert any("detail and onscreen" in issue for issue in issues)


def _p01_regression_case() -> tuple[dict, dict, dict]:
    foundation = {
        "source_consumption_policy": "required",
        "source_structure": [],
        "facts": [
            {
                "id": "ST0034",
                "statement": "标准体系应支撑绿色低碳领域具体应用。",
                "coverage_anchors": ["绿色低碳领域", "具体应用"],
            },
            {
                "id": "ST0035",
                "statement": "相关要求自2026年7月1日起施行，数据分为一般、重要、核心三级。",
                "coverage_anchors": ["2026年7月1日", "一般、重要、核心三级"],
            },
            {
                "id": "ST0036",
                "statement": "相关主体应落实安全责任，开展风险监测和应急处置。",
                "coverage_anchors": ["安全责任", "风险监测", "应急处置"],
                "conditions": ["发生安全风险时"],
                "entity_refs": ["E-001"],
            },
            {
                "id": "ST0037",
                "statement": "推进可信数据空间建设、场景验证、标准验证和生态培育。",
                "coverage_anchors": ["可信数据空间建设", "场景验证", "标准验证", "生态培育"],
                "status": "规划",
            },
        ],
        "concepts": [],
        "entities": [
            {"id": "E-001", "name": "相关主体", "fact_refs": ["ST0036"]}
        ],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
    }
    page = {
        "id": "P01",
        "question": "标准体系建设应保留哪些来源要求",
        "message": "来源要求覆盖应用、分类、安全与可信流通",
        "logic": "并列",
        "content": ["应用", "分类", "安全", "可信流通"],
        "primary_relation": {
            "type": "parallel",
            "scope": ["应用", "分类", "安全", "可信流通"],
            "authority": "hard",
        },
        "source_refs": ["ST0034", "ST0035", "ST0036", "ST0037"],
        "source_consumption": {
            "mode": "strict",
            "detail_refs": [],
            "intentional_omissions": [],
            "full_prose_anchors": [
                {"source_ref": "ST0034", "anchors": ["绿色低碳领域", "具体应用"], "minimum_hits": 2},
                {"source_ref": "ST0035", "anchors": ["2026年7月1日", "一般、重要、核心三级"], "minimum_hits": 2},
                {"source_ref": "ST0036", "anchors": ["安全责任", "风险监测", "应急处置"], "minimum_hits": 3},
                {"source_ref": "ST0037", "anchors": ["可信数据空间建设", "场景验证", "标准验证", "生态培育"], "minimum_hits": 4},
            ],
            "onscreen_refs": ["ST0035"],
        },
        "onscreen_contract": {
            "relation": "parallel",
            "detail_axis": "source_requirements",
            "modules": [
                {
                    "heading": "分类分级",
                    "evidence_refs": ["ST0035"],
                    "required_signals": ["2026年7月1日", "一般、重要、核心三级"],
                }
            ],
        },
    }
    plan = _plan(page)
    return foundation, plan, page


def test_p01_compressed_copy_reports_specific_source_losses() -> None:
    foundation, plan, _ = _p01_regression_case()
    final = _final("绿色发展、分类分级、安全管理和可信流通共同构成标准重点。")
    final["slides"][0]["onscreen"] = [
        {"heading": "分类分级", "items": ["分类分级"]}
    ]

    issues, _ = audit_final_script(final, plan, foundation)
    joined = "\n".join(issues)

    for ref in ("ST0034", "ST0035", "ST0036", "ST0037"):
        assert ref in joined
    assert "FULL_COPY_NUMBER_OR_DATE_LOST" in joined
    assert "FULL_COPY_CONDITION_LOST" in joined
    assert "FULL_COPY_RESPONSIBILITY_LOST" in joined
    assert "FULL_COPY_STATUS_STRENGTH_LOST" in joined
    assert "required signal '2026年7月1日' is missing" in joined


def test_p01_source_specific_full_copy_with_representative_onscreen_subset_passes() -> None:
    foundation, plan, _ = _p01_regression_case()
    final = _final(
        "标准体系应支撑绿色低碳领域具体应用。相关要求自2026年7月1日起施行，"
        "数据分为一般、重要、核心三级。发生安全风险时，相关主体应落实安全责任，"
        "开展风险监测和应急处置。规划推进可信数据空间建设、场景验证、标准验证和生态培育。"
    )
    final["slides"][0]["onscreen"] = [
        {
            "heading": "分类分级",
            "items": ["2026年7月1日起施行", "一般、重要、核心三级"],
        }
    ]

    issues, _ = audit_final_script(final, plan, foundation)
    source_issues = [
        issue
        for issue in issues
        if any(
            code in issue
            for code in (
                "SOURCE_CONSUMPTION_",
                "FULL_COPY_",
                "ONSCREEN_SOURCE_REF_MISSING",
                "ONSCREEN_REQUIRED_SIGNAL_MISSING",
            )
        )
    ]
    assert source_issues == []
