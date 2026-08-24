from types import SimpleNamespace
import unittest

try:
    import pytest
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("pytest is not installed") from exc

from cyberppt.onscreen_expression import (
    EXPRESSION_SPECS,
    VALID_EXPRESSION_FORMS,
    audit_expression_balance,
    expression_constraints,
    expression_constraints_sha256,
    expression_requires_action_headings,
    resolve_onscreen_expression,
    validate_expression_form,
)


def _page(*, modules=("汇聚治理", "授权流通", "运营服务"), form="", judgment=""):
    return SimpleNamespace(
        page_type="content",
        top_level_module_titles=modules,
        module_titles=modules,
        onscreen_expression_form=form,
        onscreen_judgment=judgment,
        onscreen_text="\n".join(modules),
    )


def test_registry_includes_relation_aware_parallel_and_mapping_forms():
    assert VALID_EXPRESSION_FORMS == {
        "framework_4", "key_points_3", "parallel_classification", "mapping_2_6",
        "flow_3_5", "operation_loop", "architecture_layers", "pyramid_argument",
        "comparison_2col", "grouped_2", "matrix_2x2", "causal_chain", "actions_3",
    }


def test_expression_constraints_cover_all_registered_forms() -> None:
    assert set(EXPRESSION_SPECS) == set(VALID_EXPRESSION_FORMS)
    for form in VALID_EXPRESSION_FORMS:
        contract = expression_constraints(form)
        assert contract["form"] == form
        assert contract["heading_policy"] == EXPRESSION_SPECS[form].heading_policy
        assert contract["node_range"][0] <= contract["node_range"][1]
        assert contract["relation_pattern"]
        assert contract["reading_requirement"]
        assert contract["balance_requirement"]
        assert contract["anti_patterns"]


def test_operation_loop_contract_requires_feedback_without_layout_recipe() -> None:
    contract = expression_constraints("operation_loop")
    assert contract["relation_pattern"] == "directed_cycle"
    assert "feedback_edge_required" in contract["required_features"]
    assert "arrow_style" not in contract
    assert "coordinates" not in contract


def test_parallel_classification_supports_five_peer_categories() -> None:
    contract = expression_constraints("parallel_classification")
    assert contract["node_range"] == [2, 6]
    assert contract["reading_requirement"] == "parallel"
    assert "invented_hierarchy" in contract["anti_patterns"]


def test_mapping_contract_is_not_a_comparison_contract() -> None:
    contract = expression_constraints("mapping_2_6")
    assert contract["reading_requirement"] == "mapped"
    assert "forced_comparison" in contract["anti_patterns"]


def test_action_heading_requirement_belongs_to_expression_form() -> None:
    assert expression_requires_action_headings("flow_3_5")
    assert expression_requires_action_headings("operation_loop")
    assert expression_requires_action_headings("actions_3")
    assert not expression_requires_action_headings("causal_chain")
    assert not expression_requires_action_headings("pyramid_argument")
    assert not expression_requires_action_headings("parallel_classification")
    assert not expression_requires_action_headings("mapping_2_6")


def test_organize_is_accepted_as_an_action_heading() -> None:
    page = _page(
        modules=("组织专项设计", "形成配置复用", "形成统一产品规格"),
        form="flow_3_5",
    )
    decision = resolve_onscreen_expression(page)
    assert not [
        finding for finding in audit_expression_balance(page, decision)
        if finding.code == "ONSCREEN_FLOW_ACTION_MISSING"
    ]


def test_source_native_operations_are_accepted_as_action_headings() -> None:
    modules = (
        "订单约束与服务权益下发",
        "服务请求与交付结果计量",
        "客户确认与合作伙伴结算",
        "运营分析反馈产品优化",
    )
    page = _page(modules=modules, form="operation_loop")
    decision = resolve_onscreen_expression(page)
    assert not [
        finding for finding in audit_expression_balance(page, decision)
        if finding.code == "ONSCREEN_FLOW_ACTION_MISSING"
    ]


def test_expression_constraints_are_fresh_and_hash_stable() -> None:
    first = expression_constraints("framework_4")
    second = expression_constraints("framework_4")
    assert expression_constraints_sha256(first) == expression_constraints_sha256(second)
    first["node_range"].append(99)
    assert expression_constraints("framework_4")["node_range"] == [4, 4]


@pytest.mark.parametrize(
    ("relation", "expected"),
    [
        ("composed_of", "parallel_classification"),
        ("sequence_before", "flow_3_5"),
        ("layered_as", "architecture_layers"),
        ("causes", "causal_chain"),
        ("feedback", "operation_loop"),
    ],
)
def test_authoritative_relation_routes_to_count_compatible_reading_form(relation, expected):
    decision = resolve_onscreen_expression(
        _page(),
        page_mission="形成数据运营主链",
        business_relationships=[{
            "subject": "A",
            "relation": relation,
            "objects": ["B"],
        }],
        actions=("汇聚数据", "授权使用", "运营服务"),
        topic_category="运营链路",
    )
    assert decision.form == expected
    assert decision.source == "relation"
    assert decision.confidence >= 0.80


def test_p04_three_supports_converge_on_one_judgment() -> None:
    relationships = [
        {"subject": "业务需求增长", "relation": "supports", "objects": ["统一数据基础设施必要性"]},
        {"subject": "资源分散", "relation": "supports", "objects": ["统一数据基础设施必要性"]},
        {"subject": "机制待完善", "relation": "supports", "objects": ["统一数据基础设施必要性"]},
    ]
    decision = resolve_onscreen_expression(
        _page(modules=("业务需求增长", "资源分散", "机制待完善")),
        business_relationships=relationships,
    )
    assert decision.form == "pyramid_argument"
    assert expression_constraints(decision.form)["reading_requirement"] == "convergent"


def test_p05_problem_response_mapping_does_not_become_comparison() -> None:
    relationships = [
        {"subject": "资源分散", "relation": "responds_to", "objects": ["行业节点"]},
        {"subject": "可信使用条件不足", "relation": "responds_to", "objects": ["运营平台"]},
        {"subject": "协同机制待完善", "relation": "responds_to", "objects": ["协同载体"]},
    ]
    decision = resolve_onscreen_expression(
        _page(modules=("行业节点", "运营平台", "协同载体")),
        business_relationships=relationships,
    )
    assert decision.form == "mapping_2_6"
    assert decision.form != "comparison_2col"


def test_two_object_correspondence_only_becomes_comparison_when_page_requests_comparison() -> None:
    relationships = [
        {"subject": "当前状态", "relation": "corresponds_to", "objects": ["目标状态"]},
        {"subject": "当前指标", "relation": "corresponds_to", "objects": ["目标指标"]},
    ]
    decision = resolve_onscreen_expression(
        _page(modules=("当前状态", "目标状态")),
        page_mission="开展现状与目标对照比较",
        business_relationships=relationships,
    )
    assert decision.form == "comparison_2col"


def test_p16_five_category_taxonomy_uses_parallel_classification() -> None:
    modules = ("数据获取", "知识内容", "模型智能", "分析监测", "数据治理核验")
    decision = resolve_onscreen_expression(
        _page(modules=modules),
        business_relationships=[{
            "subject": "总体服务体系",
            "relation": "classified_as",
            "objects": list(modules),
        }],
    )
    assert decision.form == "parallel_classification"
    assert expression_constraints(decision.form)["reading_requirement"] == "parallel"


def test_explicit_override_has_priority():
    decision = resolve_onscreen_expression(
        _page(form="framework_4", modules=("一", "二", "三", "四")),
        business_relationships=[{"relation": "sequence_before"}],
    )
    assert decision.form == "framework_4"
    assert decision.source == "explicit"
    assert decision.confidence == 1.0


@pytest.mark.parametrize(
    ("modules", "mission", "topic", "expected"),
    [
        (("权属确认", "授权管理", "流转审计", "责任闭环"), "完善可信流通能力体系", "能力体系", "framework_4"),
        (("汇聚治理", "授权流通", "运营服务"), "推动全流程运营", "运营链路", "flow_3_5"),
        (("制度层", "平台层", "应用层"), "形成分层架构", "体系架构", "architecture_layers"),
        (("完善规则", "建设平台", "培育场景"), "明确重点行动", "重点任务", "actions_3"),
        (("驱动因素", "传导机制", "运营结果"), "形成因果链", "影响机制", "causal_chain"),
        (("高价值客户", "高潜客户", "低价值客户", "观察客户"), "开展客户分群", "二维象限", "matrix_2x2"),
        (("当前状态", "目标状态"), "开展状态比较", "现状目标对照", "comparison_2col"),
        (("监测反馈", "问题处置", "持续优化"), "形成运营闭环", "反馈迭代", "operation_loop"),
        (("核心判断", "支撑论点一", "支撑论点二"), "形成总分论证", "论证归纳", "pyramid_argument"),
        (("制度规则", "平台能力", "应用成效"), "聚焦三项重点", "重点价值", "key_points_3"),
        (("A类", "B类", "C类", "D类", "E类"), "形成五类并列分类", "分类结构", "parallel_classification"),
        (("问题一", "问题二", "问题三"), "说明问题与响应的对应关系", "响应映射", "mapping_2_6"),
    ],
)
def test_surface_signals_cover_all_forms(modules, mission, topic, expected):
    decision = resolve_onscreen_expression(_page(modules=modules, judgment="核心判断"), page_mission=mission, topic_category=topic)
    assert decision.form == expected


def test_ambiguous_page_falls_back_for_author_review():
    decision = resolve_onscreen_expression(_page(modules=()), page_mission="测试")
    assert decision.form == "key_points_3"
    assert decision.source == "fallback"
    assert decision.confidence < 0.60


def test_invalid_override_is_rejected():
    with pytest.raises(ValueError, match="invalid onscreen expression form"):
        validate_expression_form("unknown")
