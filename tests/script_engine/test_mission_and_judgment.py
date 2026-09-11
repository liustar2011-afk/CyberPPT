from copy import deepcopy

import pytest

from script_engine.analysis_audits.deck_plan import audit_deck_plan
from script_engine.analysis_audits.final_orchestrator import audit_final_script
from script_engine.lint_contracts import lint_final_script
from script_engine.page_source_packet import build_page_source_packet
from script_engine.plan_review import render_plan_review
from script_engine.render import render_stage02_markdown


def artifacts():
    source = "目录服务与质量服务分别提供资源检索与质量检查。"
    foundation = {"facts": [{"id": "F1", "statement": source, "source_refs": ["SU1"]}]}
    page = {"id": "P01", "title": "服务分类", "page_role": "content",
            "question": "两类服务分别提供什么？", "logic": "区分目录服务和质量服务的业务内容。",
            "source_refs": ["F1"]}
    plan = {"plan_contract_version": 2, "planning_profile": "lean", "authoring_mode": "faithful",
            "chapters": [], "pages": [page]}
    slide = {"id": "P01", "title": "服务分类", "page_type": "content", "content_load": "light", "source_refs": ["F1"],
             "full_copy": source + "\n\n目录服务：提供资源检索。\n\n质量服务：提供质量检查。",
             "onscreen": [{"heading": "目录服务", "text": "提供资源检索"},
                          {"heading": "质量服务", "text": "提供质量检查"}]}
    final = {"deck": {"authoring_mode": "faithful"}, "slides": [slide]}
    return plan, foundation, final


@pytest.mark.parametrize("mission", [None, "", "  ", 12])
def test_content_mission_is_required_in_plan_not_author(mission):
    plan, foundation, final = artifacts()
    plan["pages"][0]["logic"] = mission
    issues, _ = audit_deck_plan(plan, foundation)
    assert any("PLAN_PAGE_MISSION_REQUIRED" in issue for issue in issues)
    assert not any(".mission" in issue for issue in lint_final_script(final))


def test_plan_mission_reaches_exact_source_context_without_becoming_a_claim():
    plan, foundation, _ = artifacts()
    page = plan["pages"][0]
    before = deepcopy(page)
    packet = build_page_source_packet(page, foundation, {
        "units": [{"unit_id": "SU1", "text": foundation["facts"][0]["statement"]}],
    })
    assert packet["page_mission"] == page["logic"]
    assert packet["evidence"][0]["statement"] == foundation["facts"][0]["statement"]
    assert "core_message" not in packet
    assert page == before
    assert page["logic"] in render_plan_review(plan, foundation)
    del page["logic"]
    assert build_page_source_packet(page, foundation, {"units": []})["page_mission"] == ""


def test_plan_rejects_pre_authored_core_and_warns_about_generic_mission():
    plan, foundation, _ = artifacts()
    plan["pages"][0].update(logic="说明相关情况", core_message="必须建设行业平台")
    issues, warnings = audit_deck_plan(plan, foundation)
    assert any("PLAN_PAGE_AUTHOR_FIELDS_FORBIDDEN" in issue for issue in issues)
    assert any("PLAN_MISSION_GENERIC" in warning for warning in warnings)


@pytest.mark.parametrize("with_core", [False, True])
def test_faithful_source_judgment_does_not_force_argument_or_judgment_headings(with_core):
    plan, foundation, final = artifacts()
    if with_core:
        final["slides"][0]["core_message"] = foundation["facts"][0]["statement"]
    assert lint_final_script(final) == []
    issues, _ = audit_final_script(final, plan, foundation)
    assert issues == []
    assert "### 上屏文字" in render_stage02_markdown(final)


def test_parallel_judgments_remain_in_modules_without_synthetic_core():
    plan, foundation, final = artifacts()
    statements = ["分散资源尚未形成稳定的行业服务供给", "行业发展需要统一的连接和可信使用基础"]
    details = ["目录和接口条件不统一", "建立主体接入和授权控制能力"]
    foundation["facts"][0]["statement"] = "。".join(
        statement + "。" + detail for statement, detail in zip(statements, details)
    ) + "。"
    final["slides"][0].update(full_copy=foundation["facts"][0]["statement"],
                              onscreen=[{"heading": s, "text": t} for s, t in zip(statements, details)])
    assert lint_final_script(final) == []
    issues, _ = audit_final_script(final, plan, foundation)
    assert issues == []
    rendered = render_stage02_markdown(final)
    assert all(s in rendered for s in statements)
    assert "核心结论：" not in rendered


def test_unsupported_core_is_still_reviewed_against_source():
    plan, foundation, final = artifacts()
    final["slides"][0]["core_message"] = "只有先建设目录服务才能开展质量服务"
    issues, warnings = audit_final_script(final, plan, foundation)
    assert not any("FAITHFUL_RELATION_PROMOTED" in issue for issue in issues)
    assert any("FAITHFUL_RELATION_PROMOTED" in warning for warning in warnings)


def test_mission_difference_is_review_only_and_never_becomes_onscreen_copy():
    plan, foundation, final = artifacts()
    slide = final["slides"][0]
    slide["mission"] = "解释两类服务各自的业务内容。"
    _, warnings = audit_final_script(final, plan, foundation)
    assert any("AUTHOR_MISSION_PLAN_REVIEW" in warning for warning in warnings)
    rendered = render_stage02_markdown(final)
    assert slide["mission"] not in rendered.split("### 上屏文字", 1)[1]
    slide["mission"] = plan["pages"][0]["logic"]
    _, warnings = audit_final_script(final, plan, foundation)
    assert not any("AUTHOR_MISSION_PLAN_REVIEW" in warning for warning in warnings)
