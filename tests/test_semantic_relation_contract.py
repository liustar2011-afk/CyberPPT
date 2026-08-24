from __future__ import annotations

from cyberppt.semantic_relation_contract import (
    build_semantic_relation_profile,
    expression_form_hint,
    legacy_visual_intent_hint,
)
from cyberppt.stage02_relationship_adapter import derive_business_relationships


def test_p04_many_supports_to_one_judgment_is_convergence_not_layers() -> None:
    relationships = [
        {"subject": "业务需求增长", "relation": "supports", "objects": ["统一基础设施必要性"]},
        {"subject": "资源分散", "relation": "supports", "objects": ["统一基础设施必要性"]},
        {"subject": "服务机制待完善", "relation": "supports", "objects": ["统一基础设施必要性"]},
    ]
    profile = build_semantic_relation_profile(relationships)

    assert profile.cardinality == "many_to_one"
    assert profile.shared_target is True
    assert profile.topology_candidates == ("conclusion_anchor",)
    assert "layered_architecture" in profile.forbidden_topologies
    assert expression_form_hint(relationships, module_count=3) == "pyramid_argument"
    assert legacy_visual_intent_hint(relationships) == "judgment_evidence"


def test_p05_problem_response_mapping_is_not_comparison_or_causality() -> None:
    relationships = [
        {"subject": "资源分散", "relation": "responds_to", "objects": ["行业节点"]},
        {"subject": "可信使用条件不足", "relation": "responds_to", "objects": ["运营平台"]},
        {"subject": "协同机制待完善", "relation": "responds_to", "objects": ["协同载体"]},
    ]
    profile = build_semantic_relation_profile(relationships)

    assert profile.cardinality == "paired"
    assert profile.relation_families == ("response",)
    assert profile.topology_candidates == ("ecosystem_map",)
    assert "causal_convergence" in profile.forbidden_topologies
    assert expression_form_hint(relationships, module_count=3) == "mapping_2_6"
    assert legacy_visual_intent_hint(relationships) == "capability_relationship"


def test_p16_taxonomy_is_parallel_and_forbids_layers_and_flow() -> None:
    relationships = [{
        "subject": "总体服务体系",
        "relation": "classified_as",
        "objects": ["数据获取", "知识内容", "模型智能", "分析监测", "数据治理核验"],
    }]
    profile = build_semantic_relation_profile(relationships)

    assert profile.cardinality == "one_to_many"
    assert profile.relation_families == ("taxonomy",)
    assert profile.topology_candidates == ("parallel_set",)
    assert "layered_architecture" in profile.forbidden_topologies
    assert "directed_flow" in profile.forbidden_topologies
    assert expression_form_hint(relationships, module_count=5) == "parallel_classification"
    assert legacy_visual_intent_hint(relationships) == "judgment_evidence"


def test_p25_independent_selection_and_optional_progression_survive_together() -> None:
    relationships = derive_business_relationships(
        visual_structure=(
            "四类合作模式构成并列分类，同时保留一条可选择的深化路径；"
            "各模式可以独立采用，也可以随合作成熟度逐步深化，非强制顺序。"
        ),
        title="合作模式",
        module_titles=("标准接入", "联合产品", "场景联合运营", "战略生态"),
        top_level_module_titles=("标准接入", "联合产品", "场景联合运营", "战略生态"),
    )
    profile = build_semantic_relation_profile(relationships)

    assert profile.independent_selection is True
    assert profile.optional_progression is True
    assert "independent_selection" in profile.semantic_qualifiers
    assert "optional_progression" in profile.semantic_qualifiers
    assert profile.topology_candidates == ("parallel_set", "ecosystem_map")
    assert "directed_flow" in profile.forbidden_topologies
    assert expression_form_hint(relationships, module_count=4) == "parallel_classification"


def test_p31_real_sequence_remains_directed_flow_candidate() -> None:
    relationships = [
        {"subject": "合作意向登记", "relation": "sequence_before", "objects": ["资源与需求对接"]},
        {"subject": "资源与需求对接", "relation": "sequence_before", "objects": ["成熟度评估"]},
        {"subject": "成熟度评估", "relation": "sequence_before", "objects": ["方案深化"]},
        {"subject": "方案深化", "relation": "sequence_before", "objects": ["试点验证"]},
        {"subject": "试点验证", "relation": "sequence_before", "objects": ["正式运营"]},
    ]
    profile = build_semantic_relation_profile(relationships)

    assert profile.chain_like is True
    assert profile.relation_families == ("sequence",)
    assert profile.topology_candidates == ("directed_flow",)
    assert expression_form_hint(relationships, module_count=5) == "flow_3_5"
    assert legacy_visual_intent_hint(relationships) == "phase"


def test_canonical_script_problem_response_label_maps_to_responds_to() -> None:
    relationships = derive_business_relationships(
        visual_structure="资源分散 → 国家数据基础设施电力行业节点：问题回应",
        title="平台总体定位",
    )
    assert relationships[0]["relation"] == "responds_to"
