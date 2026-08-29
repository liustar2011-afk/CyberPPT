from __future__ import annotations

import copy
import json
from pathlib import Path

from script_engine.analysis_audit import audit_deck_plan, audit_final_script
from script_engine.analysis_audits.final_script import _audit_self_reading_density
from script_engine.cli import main
from script_engine.internal_report_voice import (
    audit_plan_internal_expert_voice,
    consultant_voice_hits,
)
from script_engine.plan_review import evidence_status, render_plan_review


ROOT = Path(__file__).resolve().parents[2]


def _example() -> tuple[dict, dict]:
    plan = json.loads((ROOT / "examples/deck-plan.example.json").read_text(encoding="utf-8"))
    foundation = json.loads((ROOT / "examples/foundation.example.json").read_text(encoding="utf-8"))
    return plan, foundation


def test_plan_review_renders_title_message_evidence_and_bridge_without_mutation() -> None:
    plan, foundation = _example()
    before_plan = copy.deepcopy(plan)
    before_foundation = copy.deepcopy(foundation)

    markdown = render_plan_review(plan, foundation)

    assert "# 脚本规划待确认" in markdown
    assert "| P01 | 数据服务形成机制 |" in markdown
    assert "| 机制解释 |" in markdown
    assert "来源综合推断；边界条件需保留" in markdown
    assert "去向：下一页进一步说明支撑该机制的具体能力" in markdown
    assert plan == before_plan
    assert foundation == before_foundation


def test_plan_review_renders_optional_subtitle_in_summary_and_detail() -> None:
    plan, foundation = _example()
    plan["pages"][0]["subtitle"] = "核心观点摘要"

    markdown = render_plan_review(plan, foundation)

    assert "数据服务形成机制<br>副标题：核心观点摘要" in markdown
    assert "- 页面副标题：核心观点摘要" in markdown


def test_plan_audit_accepts_short_title_that_covers_the_page_wide_subject() -> None:
    plan, foundation = _example()
    page = plan["pages"][0]
    page.update(
        {
            "title": "三阶段实施路径",
            "subtitle": "标准供给、项目建设与场景验证同步推进",
            "question": "标准体系如何分阶段形成并持续接受项目与场景反馈？",
            "message": "近期完成顶层设计，中期形成规模化供给，远期完成成熟转化。",
            "logic": "实施路径：近期—中期—远期递进",
            "content": ["近期", "中期", "远期"],
        }
    )

    _, warnings = audit_deck_plan(plan, foundation)

    assert not any("NARRATIVE_TITLE_CLAIM_LIKE" in warning for warning in warnings)
    assert not any("NARRATIVE_TITLE_PAGE_SUBJECT_MISMATCH" in warning for warning in warnings)


def test_plan_audit_flags_long_claim_like_title() -> None:
    plan, foundation = _example()
    page = plan["pages"][0]
    page.update(
        {
            "title": "三阶段路径同步推进标准供给、项目建设与场景验证",
            "question": "标准体系如何分阶段实施？",
            "message": "近期、中期和远期分别形成阶段性成果。",
            "logic": "三阶段实施路径",
            "content": ["近期", "中期", "远期"],
        }
    )

    _, warnings = audit_deck_plan(plan, foundation)

    assert any("NARRATIVE_TITLE_CLAIM_LIKE" in warning for warning in warnings)


def test_plan_audit_checks_title_against_whole_page_subject() -> None:
    plan, foundation = _example()
    page = plan["pages"][0]
    page.update(
        {
            "title": "组织职责",
            "subtitle": "需求牵引产品形成",
            "question": "平台形成什么能力？",
            "message": "数据服务按需求形成产品。",
            "logic": "能力形成机制",
            "content": ["数据服务", "产品能力"],
        }
    )

    _, warnings = audit_deck_plan(plan, foundation)

    assert any("NARRATIVE_TITLE_PAGE_SUBJECT_MISMATCH" in warning for warning in warnings)


def _presentation_grouping_fixture(
    groups: list[list[str]], *, content_pages_per_chapter: int = 2
) -> tuple[dict, dict]:
    chapters = []
    pages = [
        {"id": "P01", "chapter_id": "C01", "title": "封面", "page_role": "cover", "question": "封面", "message": "封面", "logic": "封面", "content": []},
        {"id": "P02", "chapter_id": "C01", "title": "目录", "page_role": "agenda", "question": "目录", "message": "目录", "logic": "目录", "content": []},
    ]
    sequence = 3
    for chapter_no, source_ids in enumerate(groups, start=1):
        chapter_id = f"C{chapter_no:02d}"
        chapters.append(
            {
                "id": chapter_id,
                "title": f"第{chapter_no}章",
                "purpose": "形成连续汇报任务",
                "question": "本章回答什么",
                "message": "本章形成完整认识",
                "relationship_to_previous": "承接上一章",
                "source_chapter_ids": source_ids,
                "structural_operation": (
                    "group_adjacent_source_chapters" if len(source_ids) > 1 else "preserve"
                ),
            }
        )
        pages.append(
            {
                "id": f"P{sequence:02d}",
                "chapter_id": chapter_id,
                "title": f"第{chapter_no}章",
                "page_role": "chapter",
                "question": "章节导航",
                "message": "章节导航",
                "logic": "章节导航",
                "content": [],
            }
        )
        sequence += 1
        for content_no in range(content_pages_per_chapter):
            pages.append(
                {
                    "id": f"P{sequence:02d}",
                    "chapter_id": chapter_id,
                    "title": f"主题{chapter_no}-{content_no + 1}",
                    "page_role": "content",
                    "question": "本页回答什么",
                    "message": "本页形成完整认识",
                    "logic": "说明关系",
                    "content": [f"内容{content_no + 1}"],
                }
            )
            sequence += 1
    pages.append(
        {"id": f"P{sequence:02d}", "chapter_id": chapters[-1]["id"], "title": "结束页", "page_role": "ending", "question": "结束", "message": "结束", "logic": "结束", "content": []}
    )
    plan = {
        "plan_contract_version": 2,
        "planning_profile": "lean",
        "communication_goal": "形成汇报共识",
        "source_structure_mode": "presentation_grouping",
        "presentation_structure_mode": "formal_chaptered",
        "thesis": "形成汇报共识",
        "narrative_arc": "从背景进入行动",
        "storyline": ["背景", "行动"],
        "narrative_design": {"mode": "direct"},
        "chapters": chapters,
        "pages": pages,
    }
    foundation = {
        "source_structure": [
            {"id": source_id, "level": "chapter", "order": index}
            for index, source_id in enumerate(
                [source_id for group in groups for source_id in group], start=1
            )
        ]
    }
    return plan, foundation


def test_presentation_grouping_preserves_source_order_with_four_chapters() -> None:
    plan, foundation = _presentation_grouping_fixture(
        [["S01", "S02"], ["S03", "S04"], ["S05", "S06"], ["S07", "S08"]]
    )

    issues, warnings = audit_deck_plan(plan, foundation)

    assert not any("PRESENTATION_" in issue for issue in issues)
    assert not any("PRESENTATION_" in warning for warning in warnings)

    markdown = render_plan_review(plan, foundation)
    assert "- 汇报结构：正式分章节汇报" in markdown
    assert "- 汇报章节数：4" in markdown
    assert "- 来源章节映射：S01、S02" in markdown
    assert "- 章节结构操作：相邻来源章节归并为汇报章节" in markdown


def test_presentation_grouping_rejects_more_than_six_chapters_without_exception() -> None:
    plan, foundation = _presentation_grouping_fixture([[f"S{index:02d}"] for index in range(1, 8)])

    issues, _ = audit_deck_plan(plan, foundation)

    assert any("PRESENTATION_CHAPTER_COUNT_EXCESSIVE" in issue for issue in issues)


def test_formal_chaptered_deck_requires_transition_before_each_chapter() -> None:
    plan, foundation = _presentation_grouping_fixture([["S01", "S02"], ["S03", "S04"]])
    plan["pages"] = [page for page in plan["pages"] if not (page["chapter_id"] == "C02" and page["page_role"] == "chapter")]

    issues, _ = audit_deck_plan(plan, foundation)

    assert any("PRESENTATION_CHAPTER_TRANSITION_COUNT: chapter C02" in issue for issue in issues)


def test_presentation_grouping_rejects_source_reordering() -> None:
    plan, foundation = _presentation_grouping_fixture([["S01", "S02"], ["S03", "S04"]])
    plan["chapters"][0]["source_chapter_ids"] = ["S02", "S01"]

    issues, _ = audit_deck_plan(plan, foundation)

    assert any("PRESENTATION_SOURCE_CHAPTER_MAPPING_CONFLICT" in issue for issue in issues)


def test_plan_review_renders_deck_and_chapter_narrative_fields() -> None:
    plan, foundation = _example()

    markdown = render_plan_review(plan, foundation)

    assert "- 叙事弧：" in markdown
    assert "- 受众起点：" in markdown
    assert "- 受众终点：" in markdown
    assert "- 章节使命：" in markdown
    assert "- 章节问题：" in markdown
    assert "- 章节结论：" in markdown
    assert "- 章节承接：" in markdown


def test_plan_review_renders_source_argument_contract() -> None:
    plan, foundation = _example()
    plan["source_thesis"] = "来源总论点"
    plan["source_argument_method"] = ["A01"]
    plan["chapters"][0]["source_argument_node_ids"] = ["A01"]
    plan["pages"][0]["source_argument_node_ids"] = ["A01"]

    markdown = render_plan_review(plan, foundation)

    assert "- 来源总论点：来源总论点" in markdown
    assert "- 来源论证顺序：A01" in markdown
    assert "- 承担源论点：A01" in markdown


def test_plan_review_marks_unknown_evidence_as_incomplete() -> None:
    plan, foundation = _example()
    plan["pages"][0]["proof"]["evidence_refs"] = ["UNKNOWN"]
    plan["pages"][0]["analysis_basis"]["supports"] = []

    assert evidence_status(plan["pages"][0], foundation).startswith("证据责任不完整")


def test_plan_review_renders_structured_evidence_fit_challenge() -> None:
    plan, foundation = _example()
    page = plan["pages"][0]
    ref = page["proof"]["evidence_refs"][0]
    page["evidence_fit_review"] = {
        "question": page["question"],
        "items": [
            {
                "evidence_ref": ref,
                "fit": "direct",
                "role": "mechanism",
                "reason": "来源直接说明该机制",
            }
        ],
        "counter_case": "若来源只描述能力清单，则不能支撑机制判断",
        "verdict": "keep",
    }

    markdown = render_plan_review(plan, foundation)

    assert "#### 页面来源适配质询" in markdown
    assert "最强反例：若来源只描述能力清单，则不能支撑机制判断" in markdown
    assert f"| {ref} | 直接支持 | mechanism | 来源直接说明该机制 |" in markdown
    assert "证据适配结论：保留" in markdown


def test_plan_review_renders_source_consumption_summary() -> None:
    plan, foundation = _example()
    page = plan["pages"][0]
    refs = page["source_refs"][:2]
    page["source_refs"] = refs
    page["source_consumption"] = {
        "mode": "strict",
        "detail_refs": [refs[1]],
        "intentional_omissions": [],
        "full_prose_anchors": [
            {"source_ref": refs[0], "anchors": ["来源特征A", "来源特征B"], "minimum_hits": 1}
        ],
        "onscreen_refs": [refs[0]],
    }

    markdown = render_plan_review(plan, foundation)

    assert "#### 来源消费摘要" in markdown
    assert f"完整稿必消费来源：{refs[0]}" in markdown
    assert f"追溯详情：{refs[1]}" in markdown
    assert f"必须上屏的代表性来源：{refs[0]}" in markdown
    assert f"| {refs[0]} | 来源特征A；来源特征B | 1 |" in markdown


def test_missing_evidence_fit_mode_is_visible_and_blocks_author() -> None:
    plan, foundation = _example()
    plan.pop("evidence_fit_review_mode")

    issues, warnings = audit_deck_plan(plan, foundation)
    markdown = render_plan_review(plan, foundation, issues=issues, warnings=warnings)

    assert any("strict is required before PLAN can enter AUTHOR" in issue for issue in issues)
    assert any("NARRATIVE_PLAN_FIELDS_INCOMPLETE" in warning for warning in warnings)
    assert "来源适配门禁：缺失，阻断 AUTHOR" in markdown


def test_review_plan_cli_prints_markdown_and_creates_no_artifact(tmp_path, capsys) -> None:
    plan, foundation = _example()
    plan_path = tmp_path / "deck-plan.json"
    foundation_path = tmp_path / "foundation.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    foundation_path.write_text(json.dumps(foundation, ensure_ascii=False), encoding="utf-8")
    before = {path.name for path in tmp_path.iterdir()}

    exit_code = main(["review-plan", str(plan_path), str(foundation_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert output.startswith("# 脚本规划待确认")
    assert {path.name for path in tmp_path.iterdir()} == before


def test_business_vocabulary_is_valid_in_internal_expert_voice() -> None:
    plan = {
        "audience_scope": "internal",
        "pages": [
            {
                "id": "P01",
                "title": "客户经营成效",
                "question": "经营转化取得了哪些进展",
                "message": "客户需求牵引产品优化，市场拓展和项目成交推动数据价值释放",
                "logic": "客户需求到经营成效",
                "content": ["客户服务", "市场拓展", "项目成交", "价值释放", "商业化"],
            }
        ],
    }

    assert audit_plan_internal_expert_voice(plan) == []
    assert consultant_voice_hits("客户、市场、成交、价值释放、增长和商业化") == []


def test_internal_plan_rejects_external_consultant_address() -> None:
    plan, foundation = _example()
    plan["pages"][0]["message"] = "建议贵司全面重构客户经营体系"

    issues, _ = audit_deck_plan(plan, foundation)

    assert any("internal-expert voice required" in issue for issue in issues)
    assert any("建议贵司" in issue for issue in issues)


def test_internal_plan_checks_deck_thesis_and_keeps_business_vocabulary_available() -> None:
    plan, foundation = _example()
    plan["thesis"] = "从顾问视角看，建议贵司以客户需求牵引市场拓展和项目成交"

    issues, _ = audit_deck_plan(plan, foundation)

    assert any("plan.thesis" in issue for issue in issues)
    assert not any("客户" in issue or "市场" in issue or "成交" in issue for issue in issues)


def test_external_plan_may_address_the_client_explicitly() -> None:
    plan, _ = _example()
    plan["audience_scope"] = "external"
    plan["pages"][0]["message"] = "建议贵司完善客户经营体系"

    assert audit_plan_internal_expert_voice(plan) == []


def test_final_script_rejects_external_consultant_voice_for_internal_report() -> None:
    plan, foundation = _example()
    final_script = {
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "客户经营",
                "core_message": "客户需求牵引产品优化",
                "full_copy": "从外部咨询视角看，建议贵司全面重构客户经营体系",
                "onscreen": [],
            }
        ]
    }

    issues, _ = audit_final_script(final_script, plan, foundation)

    assert any("external consulting viewpoint" in issue for issue in issues)
    assert any("建议贵司" in issue for issue in issues)


def test_final_script_checks_relationship_copy_for_consultant_identity() -> None:
    plan, foundation = _example()
    final_script = {
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "经营机制",
                "core_message": "客户需求牵引市场拓展",
                "relationships": [{"relation": "作为外部顾问团队帮助贵司识别成交机会"}],
                "onscreen": [],
            }
        ]
    }

    issues, _ = audit_final_script(final_script, plan, foundation)

    assert any("relationships.0.relation" in issue for issue in issues)


def test_adjacent_duplicate_messages_warn_without_banning_shared_business_terms() -> None:
    plan, foundation = _example()
    first = plan["pages"][0]
    second = copy.deepcopy(first)
    second["id"] = "P02"
    second["title"] = "数据服务支撑机制"
    second["message"] = first["message"] + "。"
    plan["pages"].append(second)

    issues, warnings = audit_deck_plan(plan, foundation)

    assert issues == []
    assert any("near-duplicate core messages" in warning for warning in warnings)


def test_semantic_foundation_requires_deck_plan_argument_bindings() -> None:
    plan, foundation = _example()
    foundation["document_thesis"] = {
        "statement": "标准体系框架统筹重点标准、实施路径和保障措施。",
        "source_refs": ["F1"],
        "argument_weight": "core",
    }
    foundation["document_semantics"] = {
        "argument_method": ["A01"],
    }
    foundation["argument_nodes"] = [
        {
            "id": "A01",
            "statement": "总体思路推导标准体系框架。",
            "argument_weight": "core",
            "source_refs": ["F1"],
        }
    ]

    issues, _ = audit_deck_plan(plan, foundation)

    assert any("SOURCE_ARGUMENT_THESIS_DRIFT" in issue for issue in issues)
    assert any("SOURCE_ARGUMENT_METHOD_DRIFT" in issue for issue in issues)
    assert any("SOURCE_ARGUMENT_BINDING_MISSING" in issue for issue in issues)


def test_semantic_foundation_accepts_connected_deck_plan_argument_bindings() -> None:
    plan, foundation = _example()
    source_ref = plan["pages"][0]["proof"]["evidence_refs"][0]
    foundation["document_thesis"] = {
        "statement": "标准体系框架统筹重点标准、实施路径和保障措施。",
        "source_refs": [source_ref],
        "argument_weight": "core",
    }
    foundation["document_semantics"] = {"argument_method": ["A01"]}
    foundation["argument_nodes"] = [
        {
            "id": "A01",
            "statement": "总体思路推导标准体系框架。",
            "argument_weight": "core",
            "source_refs": [source_ref],
        }
    ]
    plan["source_thesis"] = foundation["document_thesis"]["statement"]
    plan["source_argument_method"] = ["A01"]
    plan["chapters"][0]["source_argument_node_ids"] = ["A01"]
    plan["pages"][0]["source_argument_node_ids"] = ["A01"]

    issues, _ = audit_deck_plan(plan, foundation)

    assert not any("SOURCE_ARGUMENT_" in issue for issue in issues)


def _label_detail_fixture(*, list_only_source: bool = False) -> tuple[dict, dict, dict]:
    green = (
        "重点场景包括行业治理、市场运行、绿色低碳、科技创新"
        if list_only_source
        else "绿色低碳场景用于检验标准在电碳业务中的适用性和可操作性"
    )
    foundation = {
        "source_structure": [],
        "facts": [
            {"id": "V1", "statement": green, "source_refs": ["S1"]},
            {
                "id": "V2",
                "statement": "科技创新场景用于检验标准对科研数据流通和成果应用的支撑能力",
                "source_refs": ["S2"],
            },
        ],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
    }
    module = {
        "heading": "重点验证场景",
        "evidence_refs": ["V1", "V2"],
        "required_signals": ["绿色低碳", "科技创新"],
    }
    plan = {
        "audience_scope": "internal",
        "chapters": [],
        "pages": [
            {
                "id": "P01",
                "question": "哪些场景承担标准验证",
                "message": "重点场景用于检验标准适用性",
                "logic": "场景验证",
                "content": ["绿色低碳", "科技创新"],
                "content_load": "standard",
                "proof": {"evidence_refs": ["V1", "V2"]},
                "onscreen_contract": {
                    "relation": "parallel",
                    "detail_axis": "validation_scene",
                    "modules": [module],
                },
            }
        ],
    }
    final = {
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "重点场景验证",
                "core_message": "重点场景用于检验标准适用性",
                "onscreen": [
                    {"heading": "重点验证场景", "items": ["绿色低碳", "科技创新"]}
                ],
            }
        ]
    }
    return foundation, plan, final


def test_final_audit_blocks_source_detail_collapsed_to_bare_labels() -> None:
    foundation, plan, final = _label_detail_fixture()

    issues, _ = audit_final_script(final, plan, foundation)

    assert any("ONSCREEN_SOURCE_DETAIL_COLLAPSED_TO_LABEL" in issue for issue in issues)
    assert any("绿色低碳" in issue for issue in issues)


def test_final_audit_accepts_label_with_source_grounded_explanation() -> None:
    foundation, plan, final = _label_detail_fixture()
    final["slides"][0]["onscreen"][0]["items"] = [
        "绿色低碳：检验标准在电碳业务中的适用性",
        "科技创新：检验标准对科研数据流通的支撑能力",
    ]

    issues, _ = audit_final_script(final, plan, foundation)

    assert not any("ONSCREEN_SOURCE_DETAIL_COLLAPSED_TO_LABEL" in issue for issue in issues)


def test_final_audit_blocks_page_proposition_drift_from_deck_plan() -> None:
    foundation, plan, final = _label_detail_fixture()
    plan["pages"][0]["source_argument_node_ids"] = ["A01"]
    final["slides"][0]["core_message"] = "重点场景覆盖多类业务。"

    issues, _ = audit_final_script(final, plan, foundation)

    assert any("AUTHOR_PAGE_PROPOSITION_DRIFTED" in issue for issue in issues)


def test_final_audit_allows_explicit_label_only_taxonomy_for_thin_source() -> None:
    foundation, plan, final = _label_detail_fixture(list_only_source=True)
    plan["pages"][0]["onscreen_contract"]["detail_policy"] = {
        "label_only_allowed": True
    }
    plan["pages"][0]["proof"]["evidence_refs"] = ["V1"]
    plan["pages"][0]["onscreen_contract"]["modules"][0]["evidence_refs"] = ["V1"]

    issues, _ = audit_final_script(final, plan, foundation)

    assert not any("ONSCREEN_SOURCE_DETAIL_COLLAPSED_TO_LABEL" in issue for issue in issues)


def test_self_read_dense_page_rejects_heading_plus_one_thin_line() -> None:
    plan = {"delivery_mode": "self_read"}
    page = {"id": "P01", "page_role": "content", "content_load": "dense"}
    slide = {
        "id": "P01",
        "onscreen": [{"heading": "事项", "items": ["简要信息"]}],
    }

    issues = _audit_self_reading_density(plan, page, slide)

    assert any("ONSCREEN_SELF_READ_DENSITY_LOW" in issue for issue in issues)


def test_self_read_dense_taxonomy_counts_compact_parallel_details() -> None:
    plan = {"delivery_mode": "self_read"}
    page = {"id": "P01", "page_role": "content", "content_load": "dense"}
    slide = {
        "id": "P01",
        "onscreen": [
            {"heading": "基础通用", "items": ["术语概念、参考架构、标识目录"]},
            {"heading": "数据资源", "items": ["分类分级、元数据、质量、资产"]},
        ],
    }

    assert _audit_self_reading_density(plan, page, slide) == []


def test_self_read_density_exempts_structural_pages() -> None:
    plan = {"delivery_mode": "self_read"}
    page = {"id": "P01", "page_role": "chapter", "content_load": "dense"}
    slide = {"id": "P01", "onscreen": [{"heading": "第一章"}]}

    assert _audit_self_reading_density(plan, page, slide) == []
