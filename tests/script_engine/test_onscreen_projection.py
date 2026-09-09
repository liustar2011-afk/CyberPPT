import pytest

from script_engine.onscreen_projection import review_onscreen_projection


def review(full_copy, modules):
    return review_onscreen_projection({
        "page_type": "content", "full_copy": full_copy, "onscreen": modules,
    })


def codes(result):
    return {item["code"] for item in result["findings"]}


def test_responsibility_swap_is_detected_with_all_words_preserved():
    result = review(
        "由研发中心负责生产组件。由运营中心负责分发组件。",
        [{"heading": "生产组件：运营中心"}, {"heading": "分发组件：研发中心"}],
    )
    assert "ONSCREEN_RESPONSIBILITY_MISMATCH" in codes(result)


def test_responsibility_can_be_inherited_from_visible_module_heading():
    result = review(
        "由研发中心负责生产组件。由运营中心负责分发组件。",
        [{"heading": "研发中心", "items": ["负责生产组件"]},
         {"heading": "运营中心", "text": "负责分发组件"}],
    )
    assert not result["findings"]


def test_explicit_transformation_cannot_lose_its_output():
    result = review(
        "建设资源平台，把数据加工成标准化组件。",
        [{"heading": "资源平台", "text": "建设资源平台"}],
    )
    assert "ONSCREEN_TRANSFORMATION_LOST" in codes(result)


def test_transformation_accepts_phrase_projection():
    result = review(
        "建设资源平台，把数据加工成标准化组件。",
        [{"heading": "资源平台", "text": "数据 → 标准化组件"}],
    )
    assert not result["findings"]


def test_transformation_accepts_removal_of_attributive_particle():
    assert not review("把数据加工成标准化的词元组件。", [
        {"text": "数据 → 标准化词元组件"},
    ])["findings"]


@pytest.mark.parametrize("text", ["标准化组件 → 数据", "把标准化组件加工成数据"])
def test_transformation_direction_cannot_be_reversed(text):
    assert "ONSCREEN_TRANSFORMATION_REVERSED" in codes(review(
        "把数据加工成标准化组件。", [{"text": text}],
    ))


def test_noncore_example_can_be_removed():
    result = review(
        "平台提供加工服务。例如，把数据加工成示范组件。",
        [{"heading": "平台服务", "text": "平台提供加工服务"}],
    )
    assert not result["findings"]


@pytest.mark.parametrize("promoted", ["已全面开放", "已正式开放", "已开放"])
def test_future_status_cannot_be_promoted(promoted):
    result = review(
        "区域数据平台将持续拓展数据开放场景。",
        [{"heading": f"区域数据平台{promoted}数据开放场景"}],
    )
    assert "ONSCREEN_LOCAL_STATUS_PROMOTED" in codes(result)


def test_completed_neighbor_does_not_license_planned_task():
    result = review(
        "北区平台已开放气象数据。南区平台计划开放交通数据。",
        [{"heading": "北区平台", "text": "已开放气象数据"},
         {"heading": "南区平台", "text": "已开放交通数据"}],
    )
    assert "ONSCREEN_LOCAL_STATUS_PROMOTED" in codes(result)


def test_planned_and_completed_statements_are_valid_together():
    result = review(
        "北区平台已开放气象数据。南区平台计划开放交通数据。",
        [{"heading": "北区平台", "text": "已开放气象数据"},
         {"heading": "南区平台", "text": "计划开放交通数据"}],
    )
    assert not result["findings"]


def test_condition_cannot_be_borrowed_from_another_module():
    result = review(
        "在用户授权后，平台提供企业用能数据。平台提供公开气象数据。",
        [{"heading": "用能服务", "text": "平台提供企业用能数据"},
         {"heading": "在用户授权后", "text": "平台提供公开气象数据"}],
    )
    assert "ONSCREEN_LOCAL_CONDITION_LOST" in codes(result)


def test_condition_in_same_module_is_retained():
    result = review(
        "在用户授权后，平台提供企业用能数据。",
        [{"heading": "在用户授权后", "text": "平台提供企业用能数据"}],
    )
    assert not result["findings"]


def test_authorization_condition_accepts_equivalent_prefix():
    assert not review("在用户授权后，平台提供企业用能数据。", [
        {"heading": "经用户授权", "text": "平台提供企业用能数据"},
    ])["findings"]


def test_condition_direction_cannot_be_reversed():
    assert "ONSCREEN_LOCAL_CONDITION_REVERSED" in codes(review(
        "在用户授权后，平台提供企业用能数据。",
        [{"heading": "在用户授权前", "text": "平台提供企业用能数据"}],
    ))


def test_prohibition_cannot_be_removed():
    assert "ONSCREEN_LOCAL_PROHIBITION_LOST" in codes(review(
        "平台不得提供个人明细数据。", [{"text": "平台提供个人明细数据"}],
    ))


def test_prohibition_in_parent_can_be_shared():
    assert not review("平台不得提供个人明细数据。", [
        {"heading": "禁止提供", "text": "个人明细数据"},
    ])["findings"]


def test_numeric_values_cannot_be_swapped_between_objects():
    result = review(
        "研发中心提供10项模型服务。运营中心提供20项数据服务。",
        [{"heading": "研发中心", "text": "提供20项模型服务"},
         {"heading": "运营中心", "text": "提供10项数据服务"}],
    )
    assert "ONSCREEN_LOCAL_NUMBER_MISMATCH" in codes(result)


def test_synonym_rewrite_and_repetition_removal_require_no_lexical_gate():
    result = review(
        "平台向企业提供数据查询服务。平台向企业提供数据查询服务。",
        [{"heading": "企业数据查询", "text": "企业可通过平台查询数据"}],
    )
    assert not result["findings"]
    assert result["semantic_review_required"] is True


def test_reverse_review_keeps_omitted_passages_visible_to_critic():
    result = review(
        "平台提供数据查询服务。服务中心受理用户投诉。",
        [{"text": "平台提供数据查询服务"}],
    )
    assert any("受理用户投诉" in item["text"] for item in result["source_passages"])
    assert "full_copy_to_onscreen" in result["review_directions"]


def test_existing_critic_context_contains_bidirectional_evidence():
    from script_engine.onscreen_quality import build_onscreen_critic_context

    context = build_onscreen_critic_context(
        page={"id": "P01"}, full_copy="平台提供数据服务。服务中心受理投诉。",
        candidates=[{"id": "C1", "onscreen": [{"text": "平台提供数据服务"}]}],
    )
    packet = context["candidates"][0]["projection_review"]
    assert len(packet["source_passages"]) == 2
    assert packet["semantic_review_required"]
    assert all(not item["verified"] for item in packet["candidate_mappings"])


def test_lint_and_final_audit_report_projection_heuristics_as_advisories():
    from script_engine.lint_contracts import lint_final_script
    from script_engine.analysis_audits.final_orchestrator import audit_final_script

    full_copy = "区域数据平台将持续拓展数据开放场景。"
    slide = {
        "id": "P01", "page_type": "content", "title": "数据开放",
        "full_copy": full_copy, "source_refs": ["F1"],
        "onscreen": [{"text": "区域数据平台已全面开放数据开放场景"}],
    }
    payload = {"deck": {"authoring_mode": "faithful"}, "slides": [slide]}
    plan = {"authoring_mode": "faithful", "pages": [
        {"id": "P01", "page_type": "content", "source_refs": ["F1"]},
    ]}
    foundation = {"facts": [{"id": "F1", "statement": full_copy}]}
    from script_engine.final_quality import partition_final_lint_findings
    from script_engine.render import render_stage02_markdown

    issues, warnings = audit_final_script(payload, plan, foundation)
    blockers, advisories = partition_final_lint_findings(payload, render_stage02_markdown(payload))
    for findings in (warnings, advisories):
        assert any("ONSCREEN_LOCAL_STATUS_PROMOTED" in item for item in findings)
    for findings in (issues, blockers, lint_final_script(payload)):
        assert not any("ONSCREEN_LOCAL_STATUS_PROMOTED" in item for item in findings)
