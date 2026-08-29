from types import SimpleNamespace

from cyberppt.onscreen_expression import (
    expression_constraints,
    resolve_onscreen_expression,
)
from cyberppt.stage02_relationship_adapter import derive_business_relationships


def _page(modules):
    return SimpleNamespace(
        page_type="content",
        top_level_module_titles=tuple(modules),
        module_titles=tuple(modules),
        onscreen_expression_form="",
        onscreen_judgment="",
        onscreen_text="\n".join(modules),
    )


def test_p05_chain_preserves_direction_instead_of_becoming_parallel() -> None:
    relationships = derive_business_relationships(
        visual_structure="""
三个功能载体分别承担连接、运营和协同角色，共同支撑平台的多层次服务体系。
行业节点 → 运营平台：主体连接和可信流通为资源统一组织提供接入基础
运营平台 → 协同载体：统一组织的资源和产品支撑多主体协同和价值共创
""",
        title="平台总体定位",
        top_level_module_titles=(
            "行业节点",
            "运营平台",
            "协同载体",
            "多层次服务体系",
        ),
    )

    assert [item["relation"] for item in relationships] == [
        "directed_dependency",
        "evidence_supports",
    ]
    decision = resolve_onscreen_expression(
        _page(("行业节点", "运营平台", "协同载体", "多层次服务体系")),
        business_relationships=relationships,
    )
    assert decision.form == "directed_dependency_2_6"
    assert decision.form != "parallel_classification_3_6"
    assert decision.confidence == 0.82
    assert expression_constraints(decision.form)["reading_requirement"] == "directed_dependency"


def test_p04_two_directional_pressures_converge_instead_of_becoming_peer_taxonomy() -> None:
    relationships = derive_business_relationships(
        visual_structure="""
需求增长与资源分散、机制不完善两股张力共同指向建设统一数据基础设施的必要性。
需求增长 → 统一数据基础设施：协同需求增长要求统一的资源连接和产品组织基础
资源分散与机制待完善 → 统一数据基础设施：分散资源和不完善机制制约协同效率，需要统一基础设施予以化解
""",
        title="行业数据协同需求持续增长",
        top_level_module_titles=("需求增长", "资源分散", "机制待完善"),
    )

    assert all(item["direction"] == "subject_to_objects" for item in relationships)
    assert {item["relation"] for item in relationships} == {"directed_relation"}
    decision = resolve_onscreen_expression(
        _page(("需求增长", "资源分散", "机制待完善")),
        business_relationships=relationships,
    )
    assert decision.form == "support_convergence_3_6"
    assert decision.form != "parallel_classification_3_6"
    assert expression_constraints(decision.form)["reading_requirement"] == "convergent"


def test_unknown_arrow_relation_remains_directional() -> None:
    relationships = derive_business_relationships(
        visual_structure="A → B：存在业务关联",
        title="测试页",
        top_level_module_titles=("A", "B"),
    )
    assert len(relationships) == 1
    assert relationships[0]["relation"] == "directed_relation"
    assert relationships[0]["direction"] == "subject_to_objects"

    decision = resolve_onscreen_expression(
        _page(("A", "B")),
        business_relationships=relationships,
    )
    # A generic arrow records correspondence/direction, while its source
    # contains no verified chain that would justify a process carrier.
    assert decision.form == "mapping_2_6"
    assert decision.confidence == 0.68


def test_one_to_one_support_does_not_imply_peer_classification() -> None:
    relationships = derive_business_relationships(
        visual_structure="运营平台 → 协同载体：统一组织的资源和产品支撑多主体协同",
        title="测试页",
        top_level_module_titles=("运营平台", "协同载体"),
    )
    assert relationships[0]["relation"] == "evidence_supports"

    decision = resolve_onscreen_expression(
        _page(("运营平台", "协同载体")),
        business_relationships=relationships,
    )
    assert decision.form == "directed_dependency_2_6"
    assert decision.form != "parallel_classification_3_6"


def test_ambiguous_three_item_page_stays_neutral() -> None:
    decision = resolve_onscreen_expression(
        _page(("对象甲", "对象乙", "对象丙")),
        page_mission="说明相关内容",
    )
    assert decision.form == "neutral_structure_1_7"
    assert expression_constraints(decision.form)["reading_requirement"] == "neutral"


def test_arrow_embedded_in_a_prose_links_line_does_not_swallow_the_whole_line() -> None:
    # SKILL.md's "视觉结构" fields (entry/center/axis/nodes/links/sequence/exit)
    # are authored as natural-language sentences, not one bare "A → B" per
    # line. A links field describing three connections in one sentence, with
    # the arrow embedded inside a quoted clause, used to make _ARROW_RE match
    # the entire raw line -- bullet prefix, field label, quotes, and the two
    # unrelated trailing clauses all included -- producing one garbled
    # subject/object pair instead of a clean directional relation.
    visual_structure = (
        "- links：业务需求以“建设变化 → 提出更高要求”的连续关系表达；"
        "服务机制以“关键机制—尚待形成的服务闭环”显式连接；"
        "三项现状以“共同构成”连接至建设背景综合落点。"
    )

    relationships = derive_business_relationships(
        visual_structure=visual_structure,
        title="一、建设背景",
        top_level_module_titles=("业务需求持续增长", "行业资源较为分散", "规模化服务机制仍需完善"),
    )

    assert len(relationships) == 1
    relation = relationships[0]
    assert "links" not in relation["subject"]
    assert "“" not in relation["subject"] and "”" not in relation["objects"][0]
    # The two unrelated trailing clauses (no arrow of their own) must not be
    # folded into this relation's endpoints.
    assert "服务机制" not in relation["objects"][0]
    assert "三项现状" not in relation["objects"][0]


def test_arrow_line_with_bullet_and_field_label_prefix_still_resolves() -> None:
    # A clean single-relation line still works once it carries the same
    # "- <field>：" decoration SKILL.md's structured visual-structure output
    # uses, confirming the field-label stripping does not just special-case
    # the regression fixture above.
    relationships = derive_business_relationships(
        visual_structure="- links：行业节点 → 运营平台：主体连接为资源组织提供接入基础",
        title="平台总体定位",
        top_level_module_titles=("行业节点", "运营平台"),
    )

    assert len(relationships) == 1
    assert relationships[0]["subject"] == "行业节点"
    assert relationships[0]["objects"] == ["运营平台"]
    assert relationships[0]["relation"] == "directed_dependency"
