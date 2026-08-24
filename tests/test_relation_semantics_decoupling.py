from __future__ import annotations

from types import SimpleNamespace

from cyberppt.onscreen_expression import resolve_onscreen_expression
from cyberppt.relation_semantics import resolve_relation_expression
from cyberppt.stage02_relationship_adapter import derive_business_relationships


def _page(*modules: str):
    return SimpleNamespace(
        onscreen_expression_form="",
        top_level_module_titles=modules,
        onscreen_judgment="",
    )


def test_support_is_conditioned_by_cardinality() -> None:
    many_to_one = [
        {"subject": name, "relation": "evidence_supports", "objects": ["结论"], "relation_label": "并列支撑"}
        for name in ("证据一", "证据二", "证据三")
    ]
    assert resolve_relation_expression(relationships=many_to_one, module_count=3)[0] == "support_convergence_3_6"

    peer_support = [{
        "subject": "五方面基础",
        "relation": "evidence_supports",
        "objects": ["建设目标可执行性", "首期实施"],
        "relation_label": "共同支撑",
    }]
    assert resolve_relation_expression(relationships=peer_support, module_count=5)[0] == "parallel_classification_3_6"


def test_problem_response_is_mapping_not_comparison() -> None:
    rels = [
        {"subject": "问题A", "relation": "problem_response", "objects": ["能力A"], "relation_label": "问题回应"},
        {"subject": "问题B", "relation": "problem_response", "objects": ["能力B"], "relation_label": "问题回应"},
    ]
    assert resolve_relation_expression(relationships=rels, module_count=2)[0] == "mapping_2_6"


def test_true_comparison_can_still_use_comparison_contract() -> None:
    rels = [{
        "subject": "方案A",
        "relation": "corresponds_to",
        "objects": ["方案B"],
        "relation_label": "对照比较",
    }]
    assert resolve_relation_expression(relationships=rels, module_count=2)[0] == "comparison_2col"


def test_optional_progression_preserves_parallel_choice() -> None:
    relationships = derive_business_relationships(
        visual_structure=(
            "合作伙伴资源成熟度与参与深度 → 标准接入/联合产品/场景联合运营/战略生态："
            "对应关系，可独立选用也可逐步深化"
        ),
        title="合作模式",
        module_titles=("标准接入", "联合产品", "场景联合运营", "战略生态", "选择方式"),
    )
    assert relationships[0]["relation"] == "optional_progression"
    decision = resolve_onscreen_expression(
        _page("标准接入", "联合产品", "场景联合运营", "战略生态", "选择方式"),
        business_relationships=relationships,
    )
    assert decision.form == "parallel_classification_3_6"
    assert "semantic:optional_progression" in decision.evidence
    constraints = decision.to_dict()
    assert constraints["source"] == "relation"


def test_five_category_taxonomy_does_not_become_flow() -> None:
    relationships = [{
        "subject": "总体服务体系",
        "relation": "peer_classification",
        "objects": ["数据获取", "知识内容", "模型智能", "分析监测", "数据治理"],
        "relation_label": "并列分类",
    }]
    decision = resolve_onscreen_expression(
        _page("数据获取", "知识内容", "模型智能", "分析监测", "数据治理"),
        business_relationships=relationships,
    )
    assert decision.form == "parallel_classification_3_6"
    assert decision.form != "flow_3_5"


def test_six_step_process_remains_directed() -> None:
    relationships = [
        {"subject": f"步骤{i}", "relation": "sequence_before", "objects": [f"步骤{i+1}"], "relation_label": "顺序衔接"}
        for i in range(1, 6)
    ]
    decision = resolve_onscreen_expression(
        _page("登记", "对接", "评估", "深化", "试点", "运营"),
        business_relationships=relationships,
    )
    assert decision.form == "flow_3_5"
