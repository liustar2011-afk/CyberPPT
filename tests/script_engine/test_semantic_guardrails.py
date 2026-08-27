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
    return {
        "audience_scope": "external",
        "source_structure_mode": "preserve",
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
    }
    plan = {
        "communication_goal": "说明差距",
        "chapters": [],
        "pages": [page],
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


def test_onscreen_contract_schema_and_plan_audit_accept_declared_module_scope() -> None:
    foundation, plan, _ = _contracted_gap_fixture()
    assert validate_deck_plan(plan) == []
    issues, _ = audit_deck_plan(plan, foundation)
    assert issues == []


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
