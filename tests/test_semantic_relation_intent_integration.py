from __future__ import annotations

from cyberppt.composition_resolver import resolve_composition
from cyberppt.semantic_intent import resolve_semantic_intent
from cyberppt.semantic_relation_contract import build_semantic_relation_profile
from cyberppt.visual_carrier_resolver import select_visual_carrier


def _resolve(relationships, corpus=""):
    decision = resolve_semantic_intent(
        content_relations=relationships,
        corpus=corpus,
    )
    composition = resolve_composition(decision)
    carrier = select_visual_carrier(decision, composition)
    return decision, composition, carrier


def test_taxonomy_stays_peer_set_through_intent_composition_and_carrier() -> None:
    relationships = [{
        "subject": "总体服务体系",
        "relation": "classified_as",
        "objects": ["数据获取", "知识内容", "模型智能", "分析监测", "数据治理核验"],
    }]

    decision, composition, carrier = _resolve(relationships, "五类能力为并列分类")

    assert decision.primary_intent == "coordinate_peer_set"
    assert composition.semantic_intent == "coordinate_peer_set"
    assert composition.primary_axis == "shared_field"
    assert "forced_sequence" in composition.avoid
    assert "invented_hierarchy" in composition.avoid
    assert carrier.selected in {
        "shared_peer_field",
        "classified_object_landscape",
        "peer_evidence_atlas",
    }


def test_problem_response_stays_mapping_not_comparison() -> None:
    relationships = [
        {"subject": "资源分散", "relation": "responds_to", "objects": ["行业节点"]},
        {"subject": "可信使用条件不足", "relation": "responds_to", "objects": ["运营平台"]},
        {"subject": "协同机制待完善", "relation": "responds_to", "objects": ["协同载体"]},
    ]

    decision, composition, carrier = _resolve(relationships, "三方面问题分别对应三类平台定位")

    assert decision.primary_intent == "correspondence_mapping"
    assert decision.primary_intent != "comparison_tension"
    assert composition.primary_axis == "paired_mapping"
    assert "forced_comparison" in composition.avoid
    assert carrier.selected in {
        "mapped_relation_field",
        "problem_response_landscape",
        "paired_interface_map",
    }


def test_many_supports_to_one_judgment_stays_convergent() -> None:
    relationships = [
        {"subject": "业务需求增长", "relation": "supports", "objects": ["统一基础设施必要性"]},
        {"subject": "资源分散", "relation": "supports", "objects": ["统一基础设施必要性"]},
        {"subject": "服务机制待完善", "relation": "supports", "objects": ["统一基础设施必要性"]},
    ]

    profile = build_semantic_relation_profile(relationships)
    decision, composition, _carrier = _resolve(relationships, "三方面压力共同支撑统一基础设施建设必要性")

    assert profile.shared_target is True
    assert profile.topology_candidates == ("conclusion_anchor",)
    assert "layered_architecture" in profile.forbidden_topologies
    assert decision.primary_intent == "evidence_to_judgment"
    assert composition.primary_axis == "convergent"


def test_independent_selection_plus_optional_progression_does_not_become_mandatory_flow() -> None:
    relationships = [{
        "subject": "合作模式",
        "relation": "classified_as",
        "objects": ["标准接入", "联合产品", "场景联合运营", "战略生态"],
        "semantic_qualifiers": ["independent_selection", "optional_progression", "non_mandatory_progression"],
    }]

    profile = build_semantic_relation_profile(relationships)
    decision, composition, _carrier = _resolve(
        relationships,
        "四类合作模式可以独立采用，也可以随着合作成熟度逐步深化。",
    )

    assert profile.independent_selection is True
    assert profile.optional_progression is True
    assert "directed_flow" in profile.forbidden_topologies
    assert decision.primary_intent == "coordinate_peer_set"
    assert composition.primary_axis == "shared_field"


def test_real_sequence_remains_directional() -> None:
    relationships = [
        {"subject": "合作意向登记", "relation": "sequence_before", "objects": ["资源与需求对接"]},
        {"subject": "资源与需求对接", "relation": "sequence_before", "objects": ["成熟度评估"]},
        {"subject": "成熟度评估", "relation": "sequence_before", "objects": ["方案深化"]},
        {"subject": "方案深化", "relation": "sequence_before", "objects": ["试点验证"]},
        {"subject": "试点验证", "relation": "sequence_before", "objects": ["正式运营与复制推广"]},
    ]

    profile = build_semantic_relation_profile(relationships)
    decision, composition, _carrier = _resolve(relationships, "六步顺序推进路径")

    assert profile.chain_like is True
    assert profile.topology_candidates == ("directed_flow",)
    assert decision.primary_intent in {"phased_roadmap", "transformation_pipeline"}
    assert composition.primary_axis in {"near_to_far", "left_to_right"}
