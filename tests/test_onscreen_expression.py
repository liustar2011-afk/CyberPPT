from types import SimpleNamespace

import pytest

from cyberppt.onscreen_expression import (
    VALID_EXPRESSION_FORMS,
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


def test_registry_has_exactly_ten_initial_forms():
    assert VALID_EXPRESSION_FORMS == {
        "framework_4", "key_points_3", "flow_3_5", "operation_loop",
        "architecture_layers", "pyramid_argument", "comparison_2col",
        "matrix_2x2", "causal_chain", "actions_3",
    }


@pytest.mark.parametrize(
    ("relation", "expected"),
    [
        ("composed_of", "framework_4"),
        ("sequence_before", "flow_3_5"),
        ("layered_as", "architecture_layers"),
        ("causes", "causal_chain"),
        ("corresponds_to", "comparison_2col"),
        ("feedback", "operation_loop"),
    ],
)
def test_authoritative_relation_routes_to_expected_form(relation, expected):
    decision = resolve_onscreen_expression(
        _page(),
        page_mission="形成数据运营主链",
        business_relationships=[{"relation": relation}],
        actions=("汇聚数据", "授权使用", "运营服务"),
        topic_category="运营链路",
    )
    assert decision.form == expected
    assert decision.source == "relation"
    assert decision.confidence >= 0.80


def test_explicit_override_has_priority():
    decision = resolve_onscreen_expression(
        _page(form="framework_4"),
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
