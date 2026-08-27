from __future__ import annotations

from pathlib import Path

from script_engine.analysis_audit import audit_deck_plan, audit_final_script, audit_foundation_analysis
from script_engine.contracts import validate_deck_plan

ROOT = Path(__file__).resolve().parents[2]


def _foundation() -> dict:
    return {
        "source_structure": [
            {"id": "CH01", "title": "第一章　建设背景与合作基础", "order": 1, "level": "chapter", "source_refs": ["S1.0"]},
            {"id": "CH03", "title": "第三章　重点服务与合作机会", "order": 2, "level": "chapter", "source_refs": ["S3.0"]},
            {"id": "CH04", "title": "第四章　合作模式与保障机制", "order": 3, "level": "chapter", "source_refs": ["S4.0"]},
        ],
        "facts": [
            {"id": "F14", "statement": "总体建设任务完成时实现600家以上主体接入。", "source_refs": ["S1.4"]},
            {"id": "F30", "statement": "根据服务内容，重点形成五类基础服务能力。", "source_refs": ["S3.1"]},
            {"id": "F35", "statement": "设备可靠性方向具有长期积累。", "source_refs": ["S3.3.1"], "group_id": "G-directions"},
            {"id": "F36", "statement": "绿色低碳方向具有长期积累。", "source_refs": ["S3.3.2"], "group_id": "G-directions"},
            {"id": "F37", "statement": "供需市场方向具有资源与场景储备。", "source_refs": ["S3.3.3"], "group_id": "G-directions"},
            {"id": "F38", "statement": "燃料价格预测已纳入首期重点服务方向，可依托行业资源开展联合验证。", "source_refs": ["S3.3.4"], "group_id": "G-directions"},
            {"id": "F39", "statement": "科研教育方向具有长期积累。", "source_refs": ["S3.3.5"], "group_id": "G-directions"},
            {"id": "F40", "statement": "科技成果方向具有长期积累。", "source_refs": ["S3.3.6"], "group_id": "G-directions"},
            {"id": "F44", "statement": "四类合作模式可以独立采用，也可以随着合作成熟度逐步深化。", "source_refs": ["S4.2"]},
            {"id": "F59", "statement": "内部测算可将客户净收入的15%至25%作为平台运营收入参考区间。", "source_refs": ["附件七"], "visibility": "external_ok"},
        ],
        "concepts": [],
        "entities": [],
        "relations": [
            {"id": "R7", "from": "资源成熟度", "to": "合作模式", "relation": "从标准接入向战略生态逐步深化", "basis": "explicit", "support": ["F44"], "source_refs": ["S4.2"]},
        ],
        "arguments": [
            {"id": "A3", "claim": "六个方向均已具备中电联长期积累的现实基础。", "support": ["F35", "F36", "F37", "F38", "F39", "F40"], "basis": "inferred", "confidence": "high", "source_refs": ["S3.3"]},
        ],
        "constraints": [],
        "numbers": [
            {"id": "N7", "value": "15%至25%", "unit": "客户净收入占比", "context": "内部测算参考区间", "source_refs": ["附件七"]},
        ],
    }


def _plan() -> dict:
    plan = {
        "audience_scope": "external",
        "source_structure_mode": "preserve",
        "evidence_fit_review_mode": "strict",
        "chapters": [
            {"id": "C1", "title": "建设背景与合作基础", "purpose": "x", "source_chapter_ids": ["CH01"], "structural_operation": "preserve"},
            {"id": "C3", "title": "重点服务与合作机会", "purpose": "x", "source_chapter_ids": ["CH03"], "structural_operation": "preserve"},
            {"id": "C4", "title": "合作模式与保障机制", "purpose": "x", "source_chapter_ids": ["CH04"], "structural_operation": "preserve"},
        ],
        "pages": [
            {"id": "P03", "chapter_id": "C1", "question": "x", "message": "x", "logic": "章节导入", "content": [], "source_scope": ["S1.0"], "structural_operation": "preserve"},
            {"id": "P07", "chapter_id": "C1", "question": "x", "message": "到期实现600家以上主体接入。", "logic": "目标陈述", "content": [], "source_scope": ["S1.4"], "proof": {"evidence_refs": ["F14"]}, "source_refs": ["S1.4"]},
            {"id": "P14", "chapter_id": "C3", "question": "x", "message": "平台形成五类基础服务能力。", "logic": "能力分类：按服务内容逐一列举", "content": [], "source_scope": ["S3.1"], "analysis_basis": {"model": "classification", "relation_basis": "explicit", "supports": ["F30"]}, "proof": {"evidence_refs": ["F30"]}, "source_refs": ["S3.1"]},
            {"id": "P16", "chapter_id": "C3", "question": "x", "message": "六个方向均已具备中电联长期积累的现实基础。", "logic": "分类对比", "content": [], "source_scope": ["S3.3"], "proof": {"evidence_refs": ["F35", "F36", "F37", "F38", "F39", "F40"]}, "source_refs": ["S3.3"]},
            {"id": "P19", "chapter_id": "C4", "question": "x", "message": "四类模式按参与深度逐步深化。", "logic": "递进", "content": [], "source_scope": ["S4.2"], "proof": {"evidence_refs": ["F44"]}, "source_refs": ["S4.2"]},
            {"id": "P20", "chapter_id": "C4", "question": "x", "message": "商务机制分类协商。", "logic": "定价", "content": [], "source_scope": ["S4.4", "附件七"], "proof": {"evidence_refs": ["N7", "F59"]}, "visibility_decision": "external_ok", "source_refs": ["S4.4", "附件七"]},
        ],
    }
    for page in plan["pages"]:
        proof = page.get("proof") or {}
        analysis = page.get("analysis_basis") or {}
        refs = list(dict.fromkeys((proof.get("evidence_refs") or []) + (proof.get("boundary_refs") or []) + (analysis.get("supports") or [])))
        if not refs:
            continue
        inferred = proof.get("relation_basis") == "inferred" or analysis.get("relation_basis") == "inferred"
        page["evidence_fit_review"] = {
            "question": page["question"],
            "items": [
                {
                    "evidence_ref": ref,
                    "fit": "indirect" if inferred else "direct",
                    "role": "test_support",
                    "reason": f"{ref} is assigned to the page proof responsibility",
                }
                for ref in refs
            ],
            "counter_case": "The page claim would need narrowing if an assigned record did not support it",
            "verdict": "keep",
        }
    return plan


def _final() -> dict:
    return {
        "slides": [
            {"id": "P03", "page_type": "chapter", "chapter_id": "C1", "title": "建设背景与总体定位", "core_message": "x", "onscreen": []},
            {"id": "P07", "page_type": "content", "title": "建设目标", "core_message": "600家以上主体接入", "full_copy": "600家以上主体接入意味着当前主体数量距离目标还有很大缺口。", "onscreen": []},
            {"id": "P14", "page_type": "content", "title": "服务能力体系", "core_message": "五类能力沿数据加工链条依次递进。", "full_copy": "数据获取是起点，知识内容在数据基础上叠加，模型与智能进一步加工，分析监测形成决策支持。", "onscreen": []},
            {"id": "P16", "page_type": "content", "title": "重点合作方向", "core_message": "六个方向均已具备中电联长期积累的现实基础。", "onscreen": []},
            {"id": "P19", "page_type": "content", "title": "角色与合作模式", "core_message": "四类模式按参与深度递进。", "full_copy": "可以从标准接入开始，再逐步升级到更深的合作模式。", "onscreen": []},
            {"id": "P20", "page_type": "content", "title": "支持与商务机制", "core_message": "分类协商", "full_copy": "内部测算参考：平台运营收入约占客户净收入15%-25%。", "onscreen": []},
        ]
    }


def _contracted_gap_fixture() -> tuple[dict, dict, dict]:
    foundation = {
        "source_structure": [],
        "facts": [
            {"id": "G1", "statement": "基础通用标准供给不足。", "source_refs": ["S2.1"]},
            {"id": "G2", "statement": "新兴应用场景标准供给滞后。", "source_refs": ["S2.2"]},
        ],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
    }
    contract = {
        "relation": "parallel",
        "detail_axis": "gap_manifestation",
        "scope_mode": "exclusive",
        "modules": [
            {
                "heading": "基础通用",
                "evidence_refs": ["G1"],
                "required_signals": ["术语"],
                "forbidden_signals": ["场景问题"],
            },
            {
                "heading": "新兴场景",
                "evidence_refs": ["G2"],
                "required_signals": ["场景"],
                "forbidden_signals": ["机制问题"],
            },
        ],
        "detail_policy": {
            "allowed_roles": ["gap", "evidence"],
            "forbidden_roles": ["measure", "summary"],
            "role_markers": {
                "measure": [r"^(完善|建立|加强|构建)"],
                "summary": [r"(共同指向|后续)"],
                "gap": [r"(不足|滞后|不均衡|缺少|有待)"],
                "evidence": [r"(术语|架构|场景)"],
            },
        },
    }
    page = {
        "id": "P06",
        "question": "现状差距集中在哪些方面？",
        "message": "两类差距并列呈现。",
        "logic": "并列差距清单",
        "content": ["基础通用", "新兴场景"],
        "onscreen_contract": contract,
        "primary_relation": {
            "type": "parallel",
            "scope": ["基础通用", "新兴场景"],
            "authority": "hard",
        },
    }
    plan = {
        "communication_goal": "说明差距",
        "evidence_fit_review_mode": "strict",
        "chapters": [],
        "pages": [page],
    }
    for module in contract["modules"]:
        module["evidence_fit_review"] = {
            "question": f"{module['heading']}模块呈现什么差距",
            "items": [
                {
                    "evidence_ref": ref,
                    "fit": "direct",
                    "role": "gap_evidence",
                    "reason": f"{ref} directly states the module gap",
                }
                for ref in module["evidence_refs"]
            ],
            "counter_case": "If the source described a measure, it would need a different module",
            "verdict": "keep",
        }
    return foundation, plan, {"slides": []}


def _contracted_final(*, mixed: bool = False, different_counts: bool = False) -> dict:
    first_items = ["术语标准供给不足。", "共性规则供给不足。"]
    if mixed:
        first_items = [
            "完善术语、参考架构和目录规范",
            "场景问题影响新业态服务供给",
            "共同指向体系化供给",
        ]
    elif different_counts:
        first_items = ["术语标准供给不足。", "共性规则供给不足。", "接口规范供给不足。"]
    second_items = ["新兴场景标准供给滞后。"]
    return {
        "slides": [
            {
                "id": "P06",
                "page_type": "content",
                "title": "现状差距",
                "core_message": "两类差距并列呈现。",
                "onscreen": [
                    {"heading": "基础通用", "items": first_items},
                    {"heading": "新兴场景", "items": second_items},
                ],
            }
        ]
    }


def _strict_evidence_fit_fixture() -> tuple[dict, dict]:
    foundation = {
        "source_structure": [],
        "facts": [
            {"id": "E1", "statement": "分类分级要求构成页面判断依据。", "source_refs": ["S1"]},
            {"id": "E2", "statement": "绿色低碳行动提出数据流通应用要求。", "source_refs": ["S2"]},
        ],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
    }
    page_question = "相关政策对标准体系提出哪些要求"
    plan = {
        "communication_goal": "说明政策要求",
        "evidence_fit_review_mode": "strict",
        "chapters": [],
        "pages": [
            {
                "id": "P01",
                "question": page_question,
                "message": "政策要求为标准体系建设提供依据",
                "logic": "政策要求归纳",
                "content": [],
                "proof": {"evidence_refs": ["E1"], "relation_basis": "explicit"},
                "evidence_fit_review": {
                    "question": page_question,
                    "items": [
                        {
                            "evidence_ref": "E1",
                            "fit": "direct",
                            "role": "authority",
                            "reason": "分类分级要求直接支撑政策依据判断",
                        }
                    ],
                    "counter_case": "若只说明数据分类名称，则不足以支撑标准体系建设依据",
                    "verdict": "keep",
                },
                "primary_relation": {
                    "type": "hierarchy",
                    "scope": ["绿色低碳"],
                    "authority": "hard",
                },
                "onscreen_contract": {
                    "relation": "hierarchy",
                    "detail_axis": "policy_requirement",
                    "modules": [
                        {
                            "heading": "绿色低碳",
                            "evidence_refs": ["E2"],
                            "required_signals": ["流通应用要求"],
                            "evidence_fit_review": {
                                "question": "绿色低碳政策提出什么要求",
                                "items": [
                                    {
                                        "evidence_ref": "E2",
                                        "fit": "direct",
                                        "role": "policy_action",
                                        "reason": "行动计划直接提出数据流通应用要求",
                                    }
                                ],
                                "counter_case": "该来源若只列场景名称，则应保留为标签而不承载要求判断",
                                "verdict": "keep",
                            },
                        }
                    ],
                },
            }
        ],
    }
    return foundation, plan


def test_onscreen_contract_schema_and_plan_audit_accept_declared_module_scope() -> None:
    foundation, plan, _ = _contracted_gap_fixture()
    assert validate_deck_plan(plan) == []
    issues, _ = audit_deck_plan(plan, foundation)
    assert issues == []


def test_strict_evidence_fit_review_accepts_source_bound_page_and_module_reviews() -> None:
    foundation, plan = _strict_evidence_fit_fixture()

    assert validate_deck_plan(plan) == []
    issues, _ = audit_deck_plan(plan, foundation)

    assert issues == []


def test_strict_evidence_fit_review_requires_page_and_module_reviews() -> None:
    foundation, plan = _strict_evidence_fit_fixture()
    plan["pages"][0].pop("evidence_fit_review")
    plan["pages"][0]["onscreen_contract"]["modules"][0].pop("evidence_fit_review")

    issues, _ = audit_deck_plan(plan, foundation)
    joined = "\n".join(issues)

    assert "page.evidence_fit_review is required" in joined
    assert "modules[0] (绿色低碳).evidence_fit_review is required" in joined


def test_strict_evidence_fit_review_requires_exact_ref_coverage() -> None:
    foundation, plan = _strict_evidence_fit_fixture()
    review = plan["pages"][0]["evidence_fit_review"]
    review["items"][0]["evidence_ref"] = "E2"

    issues, _ = audit_deck_plan(plan, foundation)
    joined = "\n".join(issues)

    assert "missing evidence_refs ['E1']" in joined
    assert "unassigned evidence_refs ['E2']" in joined


def test_strict_evidence_fit_review_counter_case_is_optional_and_unchecked() -> None:
    # counter_case is free text the validator cannot verify for substance, so it
    # is no longer required and a trivial value must not block AUTHOR.
    foundation, plan = _strict_evidence_fit_fixture()
    review = plan["pages"][0]["evidence_fit_review"]
    review["counter_case"] = "无"

    issues, _ = audit_deck_plan(plan, foundation)

    assert not issues


def test_strict_evidence_fit_review_blocks_unresolved_fit_and_verdict() -> None:
    foundation, plan = _strict_evidence_fit_fixture()
    review = plan["pages"][0]["evidence_fit_review"]
    review["items"][0]["fit"] = "topic_only"
    review["verdict"] = "rename"

    issues, _ = audit_deck_plan(plan, foundation)
    joined = "\n".join(issues)

    assert "topic_only evidence cannot support" in joined
    assert "verdict='rename' requires PLAN repair" in joined


def test_page_indirect_fit_requires_inferred_relation_and_module_fit_stays_direct() -> None:
    foundation, plan = _strict_evidence_fit_fixture()
    page = plan["pages"][0]
    page["evidence_fit_review"]["items"][0]["fit"] = "indirect"
    module_item = page["onscreen_contract"]["modules"][0]["evidence_fit_review"]["items"][0]
    module_item["fit"] = "indirect"

    explicit_issues, _ = audit_deck_plan(plan, foundation)
    page["proof"]["relation_basis"] = "inferred"
    inferred_issues, _ = audit_deck_plan(plan, foundation)

    assert any("indirect evidence requires an inferred relation_basis" in issue for issue in explicit_issues)
    assert not any("page.evidence_fit_review.items" in issue and "indirect evidence requires" in issue for issue in inferred_issues)
    assert any("module evidence must answer its parent question directly" in issue for issue in inferred_issues)


def test_final_audit_rechecks_strict_plan_evidence_fit_gate() -> None:
    foundation, plan = _strict_evidence_fit_fixture()
    plan["pages"][0]["evidence_fit_review"]["items"][0]["fit"] = "uncertain"
    final = {
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "政策要求",
                "core_message": "政策要求为标准体系建设提供依据",
                "onscreen": [{"heading": "绿色低碳", "items": ["提出数据流通应用要求"]}],
            }
        ]
    }

    issues, _ = audit_final_script(final, plan, foundation)

    assert any("PLAN evidence-fit gate" in issue and "fit='uncertain'" in issue for issue in issues)


def test_onscreen_contract_requires_visible_support_signal_per_module() -> None:
    foundation, plan, _ = _contracted_gap_fixture()
    plan["pages"][0]["onscreen_contract"]["modules"][0].pop("required_signals")
    assert validate_deck_plan(plan)
    issues, _ = audit_deck_plan(plan, foundation)
    assert any("required_signals" in issue for issue in issues)


def test_onscreen_contract_flags_measure_cross_scope_and_page_summary_lines() -> None:
    foundation, plan, _ = _contracted_gap_fixture()
    issues, _ = audit_final_script(_contracted_final(mixed=True), plan, foundation)
    joined = "\n".join(issues)
    assert "disallowed role" in joined and "measure" in joined
    assert "forbidden cross-scope signal '场景问题'" in joined
    assert "disallowed role" in joined and "summary" in joined


def test_onscreen_contract_flags_module_heading_drift() -> None:
    foundation, plan, final = _contracted_gap_fixture()
    final = _contracted_final()
    final["slides"][0]["onscreen"][1]["heading"] = "实施协同"
    issues, _ = audit_final_script(final, plan, foundation)
    assert any("module headings do not match" in issue for issue in issues)


def test_onscreen_contract_does_not_require_equal_detail_counts() -> None:
    foundation, plan, _ = _contracted_gap_fixture()
    issues, _ = audit_final_script(_contracted_final(different_counts=True), plan, foundation)
    assert issues == []


def test_plan_requires_primary_relation_when_page_has_multiple_content_items() -> None:
    foundation, plan, _ = _contracted_gap_fixture()
    plan["pages"][0].pop("primary_relation")
    issues, _ = audit_deck_plan(plan, foundation)
    assert any("primary_relation is required" in issue for issue in issues)


def test_secondary_relations_that_connect_every_parallel_scope_entry_are_rejected() -> None:
    foundation, plan, _ = _contracted_gap_fixture()
    plan["pages"][0]["secondary_relations"] = [
        {
            "from": "基础通用",
            "to": "新兴场景",
            "type": "influence",
            "authority": "soft",
        }
    ]
    issues, _ = audit_deck_plan(plan, foundation)
    assert any("PRIMARY_RELATION_SMUGGLED_SEQUENCE" in issue for issue in issues)


def test_authored_relationships_must_be_sanctioned_by_plan() -> None:
    foundation, plan, _ = _contracted_gap_fixture()
    final = _contracted_final()
    final["slides"][0]["relationships"] = [
        {"from": "基础通用", "to": "新兴场景", "relation": "需要通过验证和反馈推动标准迭代"}
    ]
    issues, _ = audit_final_script(final, plan, foundation)
    assert any(
        "not declared in plan's primary_relation topology or secondary_relations" in issue
        for issue in issues
    )


def test_authored_relationships_declared_as_secondary_relations_pass() -> None:
    foundation, plan, _ = _contracted_gap_fixture()
    plan["pages"][0]["secondary_relations"] = [
        {
            "from": "新兴场景",
            "to": "基础通用",
            "type": "feedback",
            "authority": "soft",
            "basis": "explicit",
        }
    ]
    final = _contracted_final()
    final["slides"][0]["relationships"] = [
        {"from": "新兴场景", "to": "基础通用", "relation": "验证结果反馈至共性规则修订"}
    ]
    issues, _ = audit_final_script(final, plan, foundation)
    assert issues == []


def test_plan_and_final_audits_reject_source_colocation_as_hierarchy() -> None:
    foundation = {
        "source_structure": [],
        "facts": [
            {
                "id": "ST0053",
                "statement": "《数据要素×》行动计划将绿色低碳列为重点行动领域，"
                "对电力数据采集、流通、应用提出明确要求",
                "source_refs": ["S1"],
            },
            {
                "id": "ST0054",
                "statement": "能源行业数据分类分级指南实行一般、重要、核心三级管理",
                "source_refs": ["S1"],
            },
        ],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
    }
    page = {
        "id": "P01",
        "question": "相关政策提出哪些要求",
        "message": "政策要求形成标准建设依据",
        "logic": "并列政策要求",
        "content": [],
        "onscreen_contract": {
            "relation": "parallel",
            "detail_axis": "policy_requirement",
            "modules": [
                {
                    "heading": "能源制度",
                    "evidence_refs": ["ST0053", "ST0054"],
                    "required_signals": ["绿色低碳", "三级管理"],
                },
                {
                    "heading": "建设部署",
                    "evidence_refs": ["ST0054"],
                    "required_signals": ["分类分级"],
                },
            ],
        },
    }
    plan = {"chapters": [], "pages": [page]}
    final = {
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "政策依据",
                "core_message": "政策要求形成标准建设依据",
                "onscreen": [
                    {
                        "heading": "能源制度",
                        "items": ["绿色低碳提出应用要求", "能源数据实行三级管理"],
                    },
                    {
                        "heading": "建设部署",
                        "items": ["分类分级形成制度依据"],
                    },
                ],
            }
        ]
    }

    plan_issues, _ = audit_deck_plan(plan, foundation)
    final_issues, _ = audit_final_script(final, plan, foundation)

    assert any("ONSCREEN_SOURCE_COLOCATION_AS_HIERARCHY" in issue for issue in plan_issues)
    assert any("ONSCREEN_SOURCE_COLOCATION_AS_HIERARCHY" in issue for issue in final_issues)


def test_policy_requirement_heading_resolves_grouping_mismatch() -> None:
    foundation, plan, _ = _contracted_gap_fixture()
    foundation["facts"].extend(
        [
            {
                "id": "P1",
                "statement": "行动计划面向绿色低碳应用场景提出数据流通要求",
                "source_refs": ["S5"],
            },
            {
                "id": "P2",
                "statement": "分类分级指南形成能源数据制度安排",
                "source_refs": ["S5"],
            },
        ]
    )
    module = plan["pages"][0]["onscreen_contract"]["modules"][0]
    module["heading"] = "能源政策要求"
    module["evidence_refs"] = ["P1", "P2"]

    issues, _ = audit_deck_plan(plan, foundation)

    assert not any("ONSCREEN_SOURCE_COLOCATION_AS_HIERARCHY" in issue for issue in issues)

def test_onscreen_contract_expression_mode_warns_when_mixed_copy_has_no_proposition() -> None:
    foundation, plan, _ = _contracted_gap_fixture()
    plan["pages"][0]["onscreen_contract"]["expression_mode"] = "mixed"
    issues, warnings = audit_final_script(_contracted_final(), plan, foundation)
    assert issues == []
    assert any("expression_mode='mixed'" in warning for warning in warnings)

def test_onscreen_contract_rejects_unknown_expression_mode() -> None:
    foundation, plan, _ = _contracted_gap_fixture()
    plan["pages"][0]["onscreen_contract"]["expression_mode"] = "paragraph_led"
    assert validate_deck_plan(plan)
    issues, _ = audit_deck_plan(plan, foundation)
    assert any("expression_mode" in issue for issue in issues)


def test_real_source_contains_the_semantic_boundaries_that_drive_v041() -> None:
    source = (ROOT / "tests/script_engine/fixtures/projects/power-industry-data-infrastructure/sources/source_extract.txt").read_text(encoding="utf-8")
    assert "根据服务内容，重点形成五类基础服务能力" in source
    assert "不同模式可以独立采用，也可以随着合作成熟度逐步深化" in source
    assert "内部测算可以将客户净收入的15%至25%作为平台运营收入参考区间" in source


def test_foundation_audit_catches_internal_visibility_group_strength_and_optionality_loss() -> None:
    issues, _ = audit_foundation_analysis(_foundation())
    joined = "\n".join(issues)
    assert "F59" in joined and "visibility is external_ok" in joined
    assert "A3" in joined and "长期积累" in joined
    assert "R7" in joined and "independent choice" in joined


def test_plan_audit_catches_group_strength_optionality_and_internal_exposure() -> None:
    issues, _ = audit_deck_plan(_plan(), _foundation())
    joined = "\n".join(issues)
    assert "P16" in joined and "长期积累" in joined
    assert "P19" in joined and "independently selected" in joined
    assert "P20" in joined and "internal-only evidence" in joined


def test_final_audit_catches_all_six_power_project_regressions() -> None:
    issues, _ = audit_final_script(_final(), _plan(), _foundation())
    joined = "\n".join(issues)
    assert "P03" in joined and "chapter title" in joined
    assert "P07" in joined and "current-vs-target gap" in joined
    assert "P14" in joined and "classification/taxonomy" in joined
    assert "P16" in joined and "长期积累" in joined
    assert "P19" in joined and "lost source optionality" in joined
    assert "P20" in joined and "internal-only evidence" in joined


def test_clean_semantics_pass() -> None:
    foundation = _foundation()
    foundation["facts"][-1]["visibility"] = "internal_only"
    foundation["relations"][0]["relation"] = "四类模式可以独立采用，也可以随着合作成熟度逐步深化"
    foundation["arguments"] = []
    plan = _plan()
    plan["pages"][3]["message"] = "六个重点方向分别具有与其当前成熟度相匹配的现实基础。"
    plan["pages"][4]["message"] = "四类模式可以独立采用，也可以随着合作成熟度逐步深化。"
    plan["pages"][4]["logic"] = "分类 + 可选深化"
    plan["pages"][5]["proof"] = {"evidence_refs": []}
    plan["pages"][5].pop("evidence_fit_review", None)
    plan["pages"][5]["source_scope"] = ["S4.4"]
    plan["pages"][5]["source_refs"] = ["S4.4"]
    plan["pages"][5].pop("visibility_decision", None)
    final = _final()
    final["slides"][0]["title"] = "建设背景与合作基础"
    final["slides"][1]["full_copy"] = "项目总体建设任务完成时实现600家以上主体接入。"
    final["slides"][2]["core_message"] = "平台形成五类基础服务能力。"
    final["slides"][2]["full_copy"] = "五类能力按服务内容分类，各自承担不同服务职能。"
    final["slides"][3]["core_message"] = "六个重点方向分别具有与其当前成熟度相匹配的现实基础。"
    final["slides"][4]["core_message"] = "四类模式可以独立采用，也可以随着合作成熟度逐步深化。"
    final["slides"][4]["full_copy"] = "合作伙伴可以按条件独立选择，也可以随着合作成熟度逐步深化。"
    final["slides"][5]["full_copy"] = "商务机制根据服务属性和合作形态分类协商。"
    f_issues, _ = audit_foundation_analysis(foundation)
    p_issues, _ = audit_deck_plan(plan, foundation)
    s_issues, _ = audit_final_script(final, plan, foundation)
    assert f_issues == []
    assert p_issues == []
    assert s_issues == []
