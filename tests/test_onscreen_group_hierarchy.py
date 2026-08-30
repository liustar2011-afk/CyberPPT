from cyberppt.script_quality.models import ScriptPage
from cyberppt.script_quality.presentation import _presentation_issues


def _page(onscreen: str, *, expression_form: str = "") -> ScriptPage:
    return ScriptPage(
        page_id="p01",
        sequence=1,
        heading="预测体系运行要求",
        page_type="content",
        title="预测体系运行要求",
        main_message="统一规则、流程和校核共同支撑预测业务持续运行",
        full_prose="统一规则、流程和校核共同支撑预测业务持续运行。",
        selection_notes="",
        evidence_map="",
        evidence_map_refs=(),
        source_refs=(),
        boundary_source_refs=(),
        boundary="",
        visual_structure="",
        onscreen_text=onscreen,
        raw_onscreen_text=onscreen,
        module_titles=(),
        onscreen_expression_form=expression_form,
    )


def test_dense_group_cards_require_a_detail_under_every_heading() -> None:
    page = _page(
        "- 统一预测闭环的运行要求\n"
        "  - 周期规则贯通\n"
        "    - 月报、季报和年报规则需要打通\n"
        "  - 分析口径统一\n"
        "  - 预测流程固化\n"
        "    - 预测分析和报告生产需要固化流程\n"
    )

    codes = {issue.code for issue in _presentation_issues(page)}

    assert "ONSCREEN_GROUP_DETAIL_MISSING" in codes


def test_dense_group_cards_require_a_visible_total_heading_before_peer_cards() -> None:
    page = _page(
        "- 周期规则贯通\n"
        "  - 月报、季报和年报规则需要打通\n"
        "- 分析口径统一\n"
        "  - 月度、季度和年度分析需要统一指标口径\n"
        "- 预测流程固化\n"
        "  - 预测分析和报告生产形成可执行流程\n"
    )

    codes = {issue.code for issue in _presentation_issues(page)}

    assert "ONSCREEN_GROUP_PARENT_MISSING" in codes


def test_dense_group_cards_reject_heading_detail_and_cross_card_repetition() -> None:
    page = _page(
        "- 对象、周期和成果共同界定业务边界\n"
        "  - 对象、周期和成果共同界定业务边界\n"
        "    - 预测对象明确分析范围，时间尺度对应业务周期，成果产品承载分析结论\n"
        "  - 预测对象明确分析范围，时间尺度对应业务周期，成果产品承载分析结论\n"
        "    - 三个维度共同确定每项业务的输入、处理和输出边界\n"
        "  - 周期规则贯通\n"
        "    - 月报、季报和年报稳定运行，各周期规则仍需打通\n"
    )

    codes = {issue.code for issue in _presentation_issues(page)}

    assert "ONSCREEN_GROUP_ROLE_REPETITION" in codes


def test_dense_group_cards_allow_distinct_heading_and_detail_roles() -> None:
    page = _page(
        "- 统一预测体系的运行要求\n"
        "  - 分层数据治理提供可信且边界清晰的输入\n"
        "    - 行业统计数据优先形成稳定基础，其他数据按业务需要分步接入\n"
        "  - 统计、模型与专家共同形成可发布结论\n"
        "    - 模型结果先进入内部测算和业务审校，重大结论经专家会商后发布\n"
        "  - 智能工具在权限与人工审核约束下承担辅助任务\n"
        "    - 敏感数据和特定主体信息不得进入未授权的通用模型或开放环境\n"
        "  - 运行成果持续沉淀为可复用的组织知识\n"
        "    - 指标、数据、事件、模型、报告与复盘关联业务周期和发布版本\n"
    )

    codes = {issue.code for issue in _presentation_issues(page)}

    assert "ONSCREEN_GROUP_DETAIL_MISSING" not in codes
    assert "ONSCREEN_GROUP_ROLE_REPETITION" not in codes


def test_flat_flow_stages_still_require_a_visible_total_thesis() -> None:
    page = _page(
        "- 数据接入\n"
        "  - 汇集统计、气象和交易数据\n"
        "- 模型研判\n"
        "  - 形成基准预测和情景分析\n"
        "- 报告发布\n"
        "  - 输出可追溯的风险判断\n",
        expression_form="flow_3_5",
    )

    codes = {issue.code for issue in _presentation_issues(page)}

    assert "ONSCREEN_TOTAL_THESIS_MISSING" in codes


def test_flow_uses_total_thesis_then_stages_with_stage_detail() -> None:
    page = _page(
        "- 统一规则使数据、研判和发布形成持续更新的预测流程\n"
        "  - 数据接入\n"
        "    - 汇集统计、气象和交易数据\n"
        "  - 模型研判\n"
        "    - 形成基准预测和情景分析\n"
        "  - 报告发布\n"
        "    - 输出可追溯的风险判断\n",
        expression_form="flow_3_5",
    )

    codes = {issue.code for issue in _presentation_issues(page)}

    assert "ONSCREEN_TOTAL_THESIS_MISSING" not in codes
    assert "ONSCREEN_RELATION_UNIT_DETAIL_MISSING" not in codes


def test_comparison_requires_two_matched_units_under_total_thesis() -> None:
    page = _page(
        "- 两类方案在同一评估口径下呈现不同适用边界\n"
        "  - 方案甲\n"
        "    - 适用于高频滚动研判\n"
        "  - 方案乙\n"
        "    - 适用于年度趋势判断\n"
        "  - 方案丙\n"
        "    - 适用于专题风险分析\n",
        expression_form="comparison_2col",
    )

    codes = {issue.code for issue in _presentation_issues(page)}

    assert "ONSCREEN_COMPARISON_UNIT_COUNT" in codes
