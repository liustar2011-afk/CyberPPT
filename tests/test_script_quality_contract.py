from __future__ import annotations

from dataclasses import replace
import json
import hashlib
from pathlib import Path
import tempfile
import unittest

from cyberppt.script_quality_contract import (
    ScriptPage,
    _mechanical_evidence_bullets,
    _compound_module_heading_hits,
    _module_heading_colon_hits,
    _negative_foreground_issues,
    _generic_onscreen_relation_hits,
    _mechanical_onscreen_label_pattern_hits,
    _onscreen_detail_phrase_overages,
    _onscreen_layout_meta_hits,
    _onscreen_parent_child_role_mismatches,
    _onscreen_subordinate_fragments,
    _onscreen_false_parallel_semantics,
    _onscreen_parallel_structure_issues,
    _necessity_page_closure_issues,
    _onscreen_flow_language_issues,
    _formulaic_transition_issues,
    _speaker_placeholder_hits,
    _issue,
    _presentation_issues,
    _prohibited_contrast_issues,
    _prose_issues,
    _source_consumption_issues,
    _full_prose_source_coverage_issues,
    _full_prose_paragraph_boundary_issues,
    _polarity_dropped_terms,
    _page_content_unit_coverage_issues,
    _model_slot_coverage_issues,
    _visual_structure_judgment_issues,
    audit_script_quality,
    assert_imagegen_onscreen_readiness,
    build_communication_review,
    extract_speaker_notes,
    meaningful_char_count,
    onscreen_effective_char_target,
    onscreen_story_roles,
    parse_script_path,
    parse_script_markdown,
    parse_selection_notes,
    selection_notes_are_structured,
    script_retry_directive,
    text_similarity,
    audience_facing_group_label,
    strip_authoring_group_marker,
)


class OnscreenParallelStructureTests(unittest.TestCase):
    def _page(self, text: str) -> ScriptPage:
        return ScriptPage(
            page_id="p09",
            sequence=9,
            heading="",
            page_type="content",
            title="合作对象",
            main_message="不同伙伴提供不同能力",
            full_prose="不同伙伴提供不同能力，形成合作供给。" * 12,
            selection_notes="",
            evidence_map="",
            evidence_map_refs=("ST032",),
            source_refs=("ST032",),
            boundary_source_refs=(),
            boundary="",
            visual_structure="伙伴能力关系",
            onscreen_text=text,
            module_titles=("合作伙伴能力",),
        )

    def test_mixed_label_and_free_phrase_is_flagged(self) -> None:
        issues = _onscreen_parallel_structure_issues(
            self._page(
                "Partner capability\n"
                "    Power utility: provide industry scenarios\n"
                "    Research institute: provide models\n"
                "    Technology partner provides implementation\n"
            )
        )
        self.assertIn(
            "ONSCREEN_PARALLEL_STRUCTURE_INCONSISTENT",
            {item.code for item in issues},
        )

    def test_parallel_label_value_items_pass(self) -> None:
        issues = _onscreen_parallel_structure_issues(
            self._page(
                "Partner capability\n"
                "    Power utility: provide industry scenarios\n"
                "    Research institute: provide models\n"
                "    Technology partner: provide implementation\n"
            )
        )
        self.assertNotIn(
            "ONSCREEN_PARALLEL_STRUCTURE_INCONSISTENT",
            {item.code for item in issues},
        )

    def test_selected_scqa_can_show_gap_as_an_evidence_module(self) -> None:
        page = self._page("服务供给断点\n    分散资源尚未形成稳定服务供给")
        page = replace(
            page,
            title="建设背景",
            main_message="统一服务运营基础形成可交付服务供给",
            onscreen_judgment="统一服务运营基础形成可交付服务供给",
            top_level_module_titles=("服务供给断点", "统一服务运营基础"),
        )
        contract = {
            "expression_model_selection": {
                "model_id": "scqa", "fit": "selected", "source_mapping": [
                    {"slot": "complication", "source_refs": ["ST032"]},
                    {"slot": "answer", "source_refs": ["ST032"]},
                ],
            },
        }

        codes = {item.code for item in _negative_foreground_issues(page, contract)}

        self.assertNotIn("NEGATIVE_FOREGROUND_OUTSIDE_BOUNDARY_TOPIC", codes)


class ExpressionModelOnscreenCoverageTests(unittest.TestCase):
    def test_page_proposition_is_a_main_judgment_alias(self) -> None:
        page = parse_script_markdown(
            """## 第4页：建设背景
- 页面类型：内容页
- 页面标题：建设背景
- 页面命题：统一服务运营基础组织行业服务供给
"""
        ).pages[0]

        self.assertEqual("统一服务运营基础组织行业服务供给", page.main_message)

    def test_scqa_slots_accept_natural_visible_compression(self) -> None:
        page = ScriptPage(
            page_id="p04", sequence=4, heading="", page_type="content", title="建设背景",
            main_message="统一基础组织服务供给", full_prose="来源完整文字稿", selection_notes="",
            evidence_map="", evidence_map_refs=(), source_refs=("S001", "S002", "S003"),
            boundary_source_refs=(), boundary="", visual_structure="关系", module_titles=(),
            onscreen_judgment="统一服务运营基础形成可交付服务供给",
            onscreen_text="行业协同需求增长\n\n分散资源难以稳定组合\n\n可信服务运营基础组织服务供给",
        )
        contract = {
            "expression_model_selection": {
                "model_id": "scqa", "fit": "selected", "source_mapping": [
                    {"slot": "situation", "source_refs": ["S001"]},
                    {"slot": "complication", "source_refs": ["S002"]},
                    {"slot": "answer", "source_refs": ["S003"]},
                ],
            },
            "content_units": [
                {"statement": "行业协同需求持续增长。", "source_refs": ["S001"], "onscreen_required": True, "onscreen_anchors": ["行业协同需求持续增长"]},
                {"statement": "分散资源难以稳定组合形成服务。", "source_refs": ["S002"], "onscreen_required": True, "onscreen_anchors": ["分散资源难以稳定组合"]},
                {"statement": "可信服务运营基础组织可交付服务供给。", "source_refs": ["S003"], "onscreen_required": True, "onscreen_anchors": ["可信服务运营基础"]},
            ],
        }

        covered, issues = _model_slot_coverage_issues(page, contract)

        self.assertEqual({"S001", "S002", "S003"}, covered)
        self.assertEqual([], issues)
        self.assertNotIn("ONSCREEN_CONTENT_UNIT_GAP", {item.code for item in _page_content_unit_coverage_issues(page, contract)})

    def test_scqa_answer_must_remain_visible(self) -> None:
        page = ScriptPage(
            page_id="p04", sequence=4, heading="", page_type="content", title="建设背景",
            main_message="统一基础组织服务供给", full_prose="来源完整文字稿", selection_notes="",
            evidence_map="", evidence_map_refs=(), source_refs=("S001", "S002"),
            boundary_source_refs=(), boundary="", visual_structure="关系", module_titles=(),
            onscreen_text="行业协同需求增长\n\n分散资源难以稳定组合",
        )
        contract = {
            "expression_model_selection": {"model_id": "scqa", "fit": "selected", "source_mapping": [
                {"slot": "situation", "source_refs": ["S001"]},
                {"slot": "answer", "source_refs": ["S002"]},
            ]},
            "content_units": [
                {"statement": "行业协同需求持续增长。", "source_refs": ["S001"], "onscreen_anchors": ["行业协同需求持续增长"]},
                {"statement": "可信服务运营基础组织可交付服务供给。", "source_refs": ["S002"], "onscreen_anchors": ["可信服务运营基础"]},
            ],
        }

        _, issues = _model_slot_coverage_issues(page, contract)

        self.assertIn("EXPRESSION_MODEL_SLOT_ONSCREEN_MISSING", {item.code for item in issues})


class NecessityPageContractTests(unittest.TestCase):
    def _page(self, *, title: str, onscreen: str, prose: str = "") -> ScriptPage:
        return ScriptPage(
            page_id="p03",
            sequence=3,
            heading="",
            page_type="content",
            title=title,
            main_message="需求增长而稳定供给不足，需要建设行业级服务运营基础",
            full_prose=prose or ("行业变化带来协同需求。现有资源尚未形成稳定供给。" * 15),
            selection_notes="",
            evidence_map="",
            evidence_map_refs=("ST001",),
            source_refs=("ST001",),
            boundary_source_refs=(),
            boundary="",
            visual_structure="背景形成需求，供给缺口导向建设必要性",
            onscreen_text=onscreen,
            module_titles=("建设背景", "供给缺口"),
        )

    def test_narrow_title_and_missing_necessity_closure_are_blocked(self) -> None:
        issues = _necessity_page_closure_issues(
            self._page(
                title="行业数据服务运营的建设需求",
                onscreen="建设背景\n    业务变化：协同需求增长\n\n供给缺口\n    供给现状：尚未形成稳定服务供给",
            ),
            {"title": "行业数据服务运营的建设需求", "topic_category": "建设必要性"},
        )
        codes = {item.code for item in issues}
        self.assertIn("PAGE_TITLE_ARGUMENT_ROLE_MISMATCH", codes)
        self.assertIn("ONSCREEN_NECESSITY_CLOSURE_MISSING", codes)

    def test_explicit_necessity_title_and_source_response_pass(self) -> None:
        issues = _necessity_page_closure_issues(
            self._page(
                title="行业数据服务运营基础的建设必要性",
                onscreen="供给缺口\n    供给现状：尚未形成稳定服务供给\n\n建设必要性\n    建设要求：需要建立行业级数据连接、可信使用和服务运营基础",
            ),
            {"title": "行业数据服务运营基础的建设必要性", "topic_category": "建设必要性"},
        )
        self.assertEqual([], issues)

    def test_long_full_prose_requires_semantic_paragraphs(self) -> None:
        page = self._page(
            title="行业数据服务运营基础的建设必要性",
            onscreen="建设必要性\n    建设要求：需要建立行业级服务运营基础",
            prose="新型电力系统建设带来协同需求。" * 25,
        )
        self.assertIn(
            "CONTENT_PROSE_SEMANTIC_PARAGRAPHS_MISSING",
            {item.code for item in _prose_issues(page)},
        )

    def test_semantically_paragraphed_full_prose_passes(self) -> None:
        page = self._page(
            title="行业数据服务运营基础的建设必要性",
            onscreen="建设必要性\n    建设要求：需要建立行业级服务运营基础",
            prose=("新型电力系统建设带来协同需求。" * 13)
            + "\n\n"
            + ("现有分散资源尚未形成稳定供给。" * 13),
        )
        self.assertNotIn(
            "CONTENT_PROSE_SEMANTIC_PARAGRAPHS_MISSING",
            {item.code for item in _prose_issues(page)},
        )

    def test_evidence_argument_page_does_not_inherit_action_grammar_from_necessity_topic(self) -> None:
        page = self._page(
            title="行业数据服务运营基础的建设必要性",
            onscreen="建设背景\n\n协同需求\n\n供给缺口\n\n建设行业级服务运营基础",
        )
        page = ScriptPage(
            **{
                **page.__dict__,
                "onscreen_expression_form": "framework_4",
                "top_level_module_titles": (
                    "建设背景",
                    "协同需求",
                    "供给缺口",
                    "建设行业级服务运营基础",
                ),
            }
        )
        codes = {
            item.code
            for item in _onscreen_flow_language_issues(
                page,
                {
                    "topic_category": "建设必要性",
                    "page_mission": "说明行业服务运营基础为何需要建设",
                },
            )
        }
        self.assertNotIn("ONSCREEN_FLOW_ACTION_MISSING", codes)

    def test_action_led_causal_modules_form_a_visible_flow(self) -> None:
        page = self._page(
            title="行业数据服务运营基础的建设必要性",
            onscreen="新型电力系统加快建设",
        )
        page = ScriptPage(
            **{
                **page.__dict__,
                "onscreen_expression_form": "flow_3_5",
                "top_level_module_titles": (
                    "新型电力系统加快建设",
                    "生产经营与智能应用更依赖跨主体协同",
                    "分散资源难以形成稳定服务供给",
                    "建设行业级服务运营基础，衔接需求与供给",
                ),
            }
        )
        self.assertEqual(
            [],
            _onscreen_flow_language_issues(
                page,
                {"topic_category": "建设必要性"},
            ),
        )

    def test_relay_repetition_between_flow_steps_is_blocked(self) -> None:
        page = self._page(
            title="行业数据服务运营基础的建设必要性",
            onscreen="业务持续演进",
        )
        page = ScriptPage(
            **{
                **page.__dict__,
                "onscreen_expression_form": "flow_3_5",
                "top_level_module_titles": (
                    "新型电力系统建设推动业务持续演进",
                    "业务持续演进带动跨主体协同需求增长",
                    "分散资源难以形成稳定服务供给",
                    "建设行业级服务运营基础",
                ),
            }
        )
        self.assertIn(
            "ONSCREEN_FLOW_STEP_REDUNDANT",
            {
                item.code
                for item in _onscreen_flow_language_issues(
                    page,
                    {"topic_category": "建设必要性"},
                )
            },
        )

    def test_over_explained_flow_heading_is_blocked(self) -> None:
        page = self._page(
            title="行业数据服务运营基础的建设必要性",
            onscreen="建设服务运营基础",
        )
        page = ScriptPage(
            **{
                **page.__dict__,
                "onscreen_expression_form": "flow_3_5",
                "top_level_module_titles": (
                    "新型电力系统加快建设",
                    "生产经营与智能应用越来越依赖多个主体之间的数据知识模型协同",
                    "分散资源难以形成稳定服务供给",
                    "建设行业级服务运营基础",
                ),
            }
        )
        self.assertIn(
            "ONSCREEN_FLOW_HEADING_TOO_LONG",
            {
                item.code
                for item in _onscreen_flow_language_issues(
                    page,
                    {"topic_category": "建设必要性"},
                )
            },
        )

    def test_formulaic_transition_is_rejected_in_authored_layers(self) -> None:
        page = self._page(
            title="行业数据服务运营基础的建设必要性",
            onscreen="供给存在缺口，因此需要建设服务运营基础",
            prose="需求持续增长。由此，需要建立稳定服务供给。",
        )
        page = ScriptPage(
            **{
                **page.__dict__,
                "speaker_notes": "综上所述，平台需要形成持续服务能力。",
            }
        )
        issues = _formulaic_transition_issues(page)
        self.assertEqual(3, len(issues))
        self.assertEqual(
            {"FORMULAIC_TRANSITION_PHRASE"},
            {item.code for item in issues},
        )

    def test_business_actions_replace_formulaic_transitions(self) -> None:
        page = self._page(
            title="行业数据服务运营基础的建设必要性",
            onscreen="需要建设服务运营基础，衔接协同需求与稳定供给",
            prose="需求持续增长，稳定供给仍然不足。建设服务运营基础能够衔接需求与供给。",
        )
        self.assertEqual([], _formulaic_transition_issues(page))


class FullProseSourceCoverageTests(unittest.TestCase):
    def _page(self, prose: str) -> ScriptPage:
        return ScriptPage(
            page_id="p03",
            sequence=3,
            heading="",
            page_type="content",
            title="建设需求",
            main_message="新型电力系统建设带动数据协同需求增长",
            full_prose=prose,
            selection_notes="",
            evidence_map="",
            evidence_map_refs=("ST001",),
            source_refs=("ST001",),
            boundary_source_refs=(),
            boundary="",
            visual_structure="背景形成需求",
            onscreen_text="新型电力系统建设",
            module_titles=("新型电力系统建设",),
        )

    def test_cited_record_missing_from_full_prose_is_blocked(self) -> None:
        issues = _full_prose_source_coverage_issues(
            self._page("本页只写了抽象的数据协同需求。"),
            {"source_refs": ["ST001"]},
            {
                "ST001": {
                    "statement": "随着新型能源体系和新型电力系统加快建设，电力业务数字化、市场化和智能化程度持续提升。"
                }
            },
        )
        self.assertIn("FULL_PROSE_SOURCE_COVERAGE_GAP", {item.code for item in issues})

    def test_source_specific_fact_in_full_prose_passes(self) -> None:
        issues = _full_prose_source_coverage_issues(
            self._page("随着新型能源体系和新型电力系统加快建设，电力业务数字化、市场化和智能化程度持续提升。"),
            {"source_refs": ["ST001"]},
            {
                "ST001": {
                    "statement": "随着新型能源体系和新型电力系统加快建设，电力业务数字化、市场化和智能化程度持续提升。"
                }
            },
        )
        self.assertNotIn("FULL_PROSE_SOURCE_COVERAGE_GAP", {item.code for item in issues})

    def test_evidence_map_is_optional_when_page_sources_are_declared(self) -> None:
        page = self._page("页面完整文字稿。")
        page = replace(page, evidence_map="", evidence_map_refs=())

        issues = _prose_issues(page, expected_source_refs=("ST001",))
        codes = {item.code for item in issues}

        self.assertNotIn("CONTENT_EVIDENCE_MAP_MISSING", codes)
        self.assertNotIn("PROSE_SOURCE_COVERAGE_GAP", codes)

    def test_retained_detail_does_not_require_record_by_record_prose(self) -> None:
        issues = _full_prose_source_coverage_issues(
            self._page("本页保留核心判断，附件操作字段仅供追溯。"),
            {"source_refs": ["ST001"], "detail_refs": ["ST001"]},
            {"ST001": {"statement": "附件列出十二项操作字段和逐项填报要求。"}},
        )
        self.assertEqual([], issues)

    def test_specific_outline_omission_is_allowed(self) -> None:
        issues = _full_prose_source_coverage_issues(
            self._page("本页聚焦总体背景。"),
            {
                "source_refs": ["ST001"],
                "intentional_omissions": [
                    {
                        "source_refs": ["ST001"],
                        "reason": "该记录属于后续产品运营机制页面，本页仅承担建设背景。",
                    }
                ],
            },
            {"ST001": {"statement": "资源登记、授权交付和计量结算形成运营机制。"}},
        )
        self.assertEqual([], issues)

    def test_dropped_negation_marker_is_flagged_even_when_overlap_passes(self) -> None:
        issues = _full_prose_source_coverage_issues(
            self._page("原始数据经脱敏处理后可对外提供，支撑行业数据服务运营。"),
            {"source_refs": ["ST001"]},
            {"ST001": {"statement": "原始数据不得对外提供，仅经脱敏处理后的结果可支撑行业数据服务运营。"}},
        )
        codes = {item.code for item in issues}
        self.assertIn("SOURCE_POLARITY_MISMATCH", codes)

    def test_preserved_negation_marker_does_not_flag_polarity(self) -> None:
        issues = _full_prose_source_coverage_issues(
            self._page("原始数据不得对外提供，仅经脱敏处理后的结果可支撑行业数据服务运营。"),
            {"source_refs": ["ST001"]},
            {"ST001": {"statement": "原始数据不得对外提供，仅经脱敏处理后的结果可支撑行业数据服务运营。"}},
        )
        self.assertNotIn("SOURCE_POLARITY_MISMATCH", {item.code for item in issues})

    def test_atomic_content_unit_blocks_partial_prose_coverage(self) -> None:
        page = self._page("新型电力系统加快建设，跨主体协同需求增长。")
        issues = _page_content_unit_coverage_issues(
            page,
            {"content_units": [{
                "unit_id": "p03-u01",
                "statement": "新能源大规模接入改变电源结构、负荷特征和运行方式。",
                "source_refs": ["ST001"],
                "full_prose_required": True,
                "coverage_anchors": ["新能源大规模接入", "电源结构", "负荷特征", "运行方式"],
                "onscreen_required": False,
                "onscreen_anchors": [],
            }]},
        )
        self.assertIn("FULL_PROSE_CONTENT_UNIT_GAP", {item.code for item in issues})

    def test_atomic_content_unit_accepts_high_overlap_natural_rewrite(self) -> None:
        page = self._page("新能源大规模接入改变电源结构、负荷特征和运行方式，并使设备运行需要更多及时数据支撑。")
        issues = _page_content_unit_coverage_issues(
            page,
            {"content_units": [{
                "unit_id": "p03-u01",
                "statement": "新能源大规模接入改变电源结构、负荷特征和运行方式，设备运行需要及时完整的多源数据支撑。",
                "source_refs": ["ST001"],
                "full_prose_required": True,
                "coverage_anchors": ["新能源大规模接入", "不应要求逐字复现的来源片段", "另一个来源片段"],
                "onscreen_required": False,
                "onscreen_anchors": [],
            }]},
        )
        self.assertNotIn("FULL_PROSE_CONTENT_UNIT_GAP", {item.code for item in issues})

    def test_source_paragraph_boundaries_require_a_map_and_preserve_default_groups(self) -> None:
        records = {
            f"ST00{index}": {
                "id": f"ST00{index}",
                "statement": f"来源段落{index}的独立事实。",
                "source_unit_refs": [f"SU-{index}"],
            }
            for index in range(1, 5)
        }
        contract = {"source_refs": list(records), "detail_refs": [], "boundary_refs": []}
        page = self._page("来源段落1的独立事实。\n\n来源段落2的独立事实。\n\n来源段落3和4的独立事实。")
        missing = _full_prose_paragraph_boundary_issues(page, contract, records)
        self.assertIn("FULL_PROSE_PARAGRAPH_MAP_MISSING", {item.code for item in missing})
        page = replace(
            page,
            full_prose=(
                "来源段落1的独立事实。\n\n来源段落2的独立事实。\n\n"
                "来源段落3的独立事实。\n\n来源段落4的独立事实。"
            ),
            prose_paragraph_map=tuple((((f"ST00{index}",), "") for index in range(1, 5))),
        )
        self.assertEqual([], _full_prose_paragraph_boundary_issues(page, contract, records))

    def test_onscreen_content_unit_requires_business_anchors(self) -> None:
        page = self._page("新能源大规模接入改变电源结构、负荷特征和运行方式。")
        issues = _page_content_unit_coverage_issues(
            page,
            {"content_units": [{
                "unit_id": "p03-u01",
                "statement": "新能源大规模接入改变电源结构和运行方式。",
                "source_refs": ["ST001"],
                "full_prose_required": True,
                "coverage_anchors": ["新能源大规模接入", "电源结构", "运行方式"],
                "onscreen_required": True,
                "onscreen_anchors": ["新能源大规模接入", "运行方式"],
            }]},
        )
        self.assertIn("ONSCREEN_CONTENT_UNIT_GAP", {item.code for item in issues})


class PolarityDroppedTermsTests(unittest.TestCase):
    def test_flags_prohibition_dropped_from_authored_text(self) -> None:
        dropped = _polarity_dropped_terms(
            "原始数据不得对外提供，仅经脱敏处理后的结果可支撑行业数据服务运营。",
            "原始数据经脱敏处理后可对外提供，支撑行业数据服务运营。",
        )
        self.assertEqual(("不得",), dropped)

    def test_no_flag_when_negation_marker_survives(self) -> None:
        dropped = _polarity_dropped_terms(
            "原始数据不得对外提供，仅经脱敏处理后的结果可支撑行业数据服务运营。",
            "原始数据不得对外提供，仅经脱敏处理后的结果可支撑行业数据服务运营。",
        )
        self.assertEqual((), dropped)

    def test_no_flag_when_source_has_no_negation_marker(self) -> None:
        dropped = _polarity_dropped_terms(
            "行业数据服务运营基础持续完善。",
            "行业数据服务运营基础持续完善，能力显著提升。",
        )
        self.assertEqual((), dropped)


class ProductionAuthoringGuardTests(unittest.TestCase):
    def test_onscreen_rejects_author_explanation_group_labels(self) -> None:
        page = parse_script_markdown(
            "## 第1页：总体定位\n"
            "- 页面类型：内容页\n"
            "- 完整文字稿：行业节点承担体系连接，运营平台承接服务运营。\n"
            "- 上屏文字：\n"
            "定位关系\n"
            "    共同归属：三类定位共同构成总体方向。\n"
            "- 视觉结构：三类定位分别承接连接、运营和协同。\n"
        ).pages[0]

        codes = {issue.code for issue in _presentation_issues(page)}

        self.assertIn("ONSCREEN_BACKEND_META_LEAK", codes)

    def test_formal_v2_strict_density_rejects_four_thin_lines(self) -> None:
        page = parse_script_markdown(
            """## 第1页：正式材料

- 页面类型：内容页
- 页面标题：正式材料
- 主判断：形成完整业务关系。
- 完整文字稿：正式材料需要完整说明业务对象、事实依据、组成关系、实施条件和必要承接，形成能够独立理解的页面论述。
- 上屏文字：

事项一：简要信息。
事项二：简要信息。
事项三：简要信息。
事项四：简要信息。
- 证据：S001
- 视觉结构：业务对象与事项关系。

【演讲者备注】

正式说明相关业务关系和实施条件。
"""
        ).pages[0]

        codes = {
            issue.code
            for issue in _prose_issues(
                page,
                independent_reading_required=True,
                strict_reading_density=True,
            )
        }

        self.assertIn("ONSCREEN_STORY_DENSITY_LOW", codes)

    def test_formal_v2_accepts_compact_copy_with_explicit_information_architecture(self) -> None:
        page = parse_script_markdown(
            """## 第1页：正式材料

- 页面类型：内容页
- 页面标题：正式材料
- 主判断：形成完整业务关系。
- 完整文字稿：正式材料完整说明需求变化、资源条件、运行机制、实施要求和业务承接，并以明确事实和关系支撑页面判断，形成可独立理解的完整论述。
- 上屏文字：

需求变化
    协同范围：跨主体、跨区域协同持续增长。
    服务内容：延伸至模型、分析和场景交付。

资源条件
    资源分布：数据、模型和专业能力分属多方。
    权利要求：使用范围和安全条件各不相同。

运营机制
    履约衔接：授权、交付、计量和结算相互贯通。
    持续改进：运行结果返回产品和服务管理。
- 证据：S001
- 视觉结构：需求变化引出资源条件，运营机制承接供需并形成持续改进关系。

【演讲者备注】

正式说明相关业务关系和实施条件。
"""
        ).pages[0]

        codes = {
            issue.code
            for issue in _prose_issues(
                page,
                independent_reading_required=True,
                strict_reading_density=True,
            )
        }

        self.assertNotIn("ONSCREEN_STORY_DENSITY_LOW", codes)

    def test_formal_v2_rejects_generic_modules_that_delete_source_specificity(self) -> None:
        page = parse_script_markdown(
            """## 第4页：总体定位

- 页面类型：内容页
- 页面标题：总体定位
- 主判断：形成行业节点、运营平台和多主体协同载体。
- 完整文字稿：建设国家数据基础设施电力行业节点、行业数据与专业能力运营平台、多主体协同和价值共创载体，连接需求方、资源方、技术服务方和运营方，围绕数据产品与场景服务开展产品共建、场景实施和持续运营。汇聚电力行业数据、知识、模型与专业能力，完成资源登记、产品封装、服务订购、接口调用、使用计量、收益结算和运营评价，推动供需对接、授权流通、能力复用和场景落地。
- 上屏文字：
总体定位
    体系位置：明确总体位置和基本方向。
    主要作用：形成必要支撑和相关能力。

运营安排
    处理对象：组织相关对象开展工作。
    协同事项：推动有关事项持续实施。
- 证据：ST002
- 视觉结构：三类建设定位共同连接行业资源与应用需求。
"""
        ).pages[0]

        codes = {
            issue.code
            for issue in _prose_issues(
                page,
                independent_reading_required=True,
                strict_reading_density=True,
            )
        }

        self.assertIn("ONSCREEN_SOURCE_SPECIFICITY_LOW", codes)

    def test_strips_structural_row_markers_from_visible_group_labels(self) -> None:
        self.assertEqual("访问与成果交付方式", audience_facing_group_label("第1行｜访问与成果交付方式"))
        self.assertEqual("部署运行环境", audience_facing_group_label("第2行:部署运行环境"))

    def test_strips_row_markers_from_prompt_lines_but_preserves_indent(self) -> None:
        self.assertEqual(
            "    访问与成果交付方式",
            strip_authoring_group_marker("    第1行｜访问与成果交付方式"),
        )
        self.assertEqual(
            "访问与成果交付方式",
            strip_authoring_group_marker("第X行｜访问与成果交付方式"),
        )

    def test_compound_group_heading_distinguishes_peer_merge_from_parent_child(self) -> None:
        self.assertEqual(
            (
                "合作原则与合作方式两个层面",
                "服务等级与交付责任两个层面",
            ),
            _compound_module_heading_hits(
                (
                    "合作原则与合作方式两个层面",
                    "服务等级与交付责任两个层面",
                    "报价机制——服务分类与报价构成",
                    "分配机制——价格关系与分配比例",
                )
            ),
        )

    def test_flags_actor_dimension_nested_under_construction_item(self) -> None:
        text = (
            "三项建设内容\n"
            "    协同载体建设\n"
            "        需求单位：提出业务需求。\n"
            "        资源方：提供数据资源。\n"
            "        模型算法方：提供模型能力。\n"
            "        技术实施方：提供实施支撑。"
        )
        self.assertEqual(
            ("协同载体建设 -> 需求单位, 资源方, 模型算法方, 技术实施方",),
            _onscreen_parent_child_role_mismatches(text),
        )

    def test_allows_actor_children_under_actor_group(self) -> None:
        text = (
            "参与主体\n"
            "    需求单位：提出业务需求。\n"
            "    资源方：提供数据资源。\n"
            "    模型算法方：提供模型能力。"
        )
        self.assertEqual((), _onscreen_parent_child_role_mismatches(text))

    def test_compound_group_heading_does_not_pass_by_deleting_meta_phrase(self) -> None:
        self.assertEqual(
            ("合作原则与合作方式", "服务等级与交付责任"),
            _compound_module_heading_hits(
                ("合作原则与合作方式", "服务等级与交付责任")
            ),
        )

    def test_module_headings_reserve_vertical_bar_separator(self) -> None:
        self.assertEqual(
            ("### 一、建设前提：国家任务和组织体系已经确立",),
            _module_heading_colon_hits(
                "### 一、建设前提：国家任务和组织体系已经确立\n"
                "- 政策牵引：国家持续部署国家数据基础设施建设。"
            ),
        )
        self.assertEqual(
            (),
            _module_heading_colon_hits(
                "### 一、建设前提｜国家任务和组织体系已经确立\n"
                "- 政策牵引：国家持续部署国家数据基础设施建设。"
            ),
        )

    def test_flags_numbered_evidence_fragments_from_punctuation_splitting(self) -> None:
        text = """**关键依据**
- 依据1：2025年1月，
- 依据2：国家数据局启动第二批先行先试工作；
- 依据3：同年10月，
- 依据4：项目纳入第二批任务书。
"""
        hits = _mechanical_evidence_bullets(text)
        self.assertIn("- 依据1：2025年1月，", hits)
        self.assertIn("- 依据3：同年10月，", hits)

    def test_flags_large_numbered_evidence_dump_even_when_fragments_are_long(self) -> None:
        text = "\n".join(
            f"- 依据{i}：这是第{i}条完整但仍由源记录机械编号形成的上屏信息。"
            for i in range(1, 7)
        )
        self.assertEqual(6, len(_mechanical_evidence_bullets(text)))

    def test_flags_generic_speaker_note_placeholder(self) -> None:
        notes = "主判断。原文围绕关键对象、作用机制和条件边界展开，各项内容共同回答本节业务问题。"
        hits = _speaker_placeholder_hits(notes)
        self.assertTrue(hits)

    def test_allows_business_specific_speaker_notes(self) -> None:
        notes = "国家部署、行业协同需求和资源现实问题属于三个不同维度，共同说明建设统一基础的必要性。"
        self.assertEqual((), _speaker_placeholder_hits(notes))

    def test_flags_generic_business_relation_placeholder(self) -> None:
        self.assertTrue(
            _generic_onscreen_relation_hits("- 业务关系：以上要点共同构成本节完整内容。")
        )

    def test_allows_page_specific_business_relation(self) -> None:
        self.assertEqual(
            (),
            _generic_onscreen_relation_hits(
                "国家部署、行业需求和资源问题属于三个并列维度，共同构成建设背景。"
            ),
        )

    def test_flags_flat_long_labelled_details_without_business_group(self) -> None:
        page = ScriptPage(
            page_id="p09", sequence=9, heading="", page_type="content",
            title="", main_message="", full_prose="", selection_notes="",
            evidence_map="", evidence_map_refs=(), source_refs=(),
            boundary_source_refs=(), boundary="", visual_structure="",
            onscreen_text=(
                "数据处理：平台需要组织多主体资源并完成质量核验。\n"
                "服务交付：服务目录需要面向场景形成可执行交付闭环。\n"
                "合作推进：合作机制需要明确主体分工和后续联动安排。"
            ),
            module_titles=(),
        )

        self.assertIn(
            "ONSCREEN_BUSINESS_DETAIL_HIERARCHY_MISSING",
            {issue.code for issue in _presentation_issues(page)},
        )

    def test_allows_grouped_business_title_with_complete_details(self) -> None:
        page = ScriptPage(
            page_id="p09", sequence=9, heading="", page_type="content",
            title="", main_message="", full_prose="", selection_notes="",
            evidence_map="", evidence_map_refs=(), source_refs=(),
            boundary_source_refs=(), boundary="", visual_structure="",
            onscreen_text=(
                "服务形成条件\n  平台组织多主体资源并完成质量核验。\n"
                "运营交付闭环\n  服务目录面向场景形成可执行交付闭环。"
            ),
            module_titles=("服务形成条件", "运营交付闭环"),
        )

        self.assertNotIn(
            "ONSCREEN_BUSINESS_DETAIL_HIERARCHY_MISSING",
            {issue.code for issue in _presentation_issues(page)},
        )

    def test_allows_compact_short_label_phrases(self) -> None:
        page = ScriptPage(
            page_id="p09", sequence=9, heading="", page_type="content",
            title="", main_message="", full_prose="", selection_notes="",
            evidence_map="", evidence_map_refs=(), source_refs=(),
            boundary_source_refs=(), boundary="", visual_structure="",
            onscreen_text="数据目录：统一编目\n服务入口：统一受理",
            module_titles=(),
        )

        self.assertNotIn(
            "ONSCREEN_BUSINESS_DETAIL_HIERARCHY_MISSING",
            {issue.code for issue in _presentation_issues(page)},
        )

    def test_flags_reused_generic_onscreen_label_template(self) -> None:
        page = ScriptPage(
            page_id="p09", sequence=9, heading="", page_type="content",
            title="", main_message="", full_prose="", selection_notes="",
            evidence_map="", evidence_map_refs=(), source_refs=(),
            boundary_source_refs=(), boundary="", visual_structure="",
            onscreen_text=(
                "关键判断\n  判断：行业数据服务形成可订购目录。\n  事实：客户需求进入统一受理。\n"
                "业务事实\n  对象：数据产品和场景服务。\n  条件：权利质量通过核验。\n"
                "运营要点\n  动作：订单履行形成交付记录。\n  结果：客户完成验收与续约。"
            ),
            module_titles=("关键判断", "业务事实", "运营要点"),
        )
        self.assertEqual(
            ("关键判断", "业务事实", "运营要点", "判断", "事实", "对象", "条件", "动作", "结果"),
            _mechanical_onscreen_label_pattern_hits(page),
        )
        self.assertIn(
            "ONSCREEN_MECHANICAL_LABEL_TEMPLATE",
            [issue.code for issue in _presentation_issues(page)],
        )

    def test_allows_business_specific_onscreen_groups(self) -> None:
        page = ScriptPage(
            page_id="p09", sequence=9, heading="", page_type="content",
            title="", main_message="", full_prose="", selection_notes="",
            evidence_map="", evidence_map_refs=(), source_refs=(),
            boundary_source_refs=(), boundary="", visual_structure="",
            onscreen_text=(
                "服务目录\n  查询服务：指标、接口和数据集。\n  知识服务：政策标准和专业文档。\n"
                "履约闭环\n  订单履行：授权、交付、验收和结算。"
            ),
            module_titles=("服务目录", "履约闭环"),
        )
        self.assertEqual((), _mechanical_onscreen_label_pattern_hits(page))

    def test_flags_layout_metadata_but_keeps_business_count_labels(self) -> None:
        hits = _onscreen_layout_meta_hits(
            "四行选择矩阵\n"
            "四种合作方式\n"
            "阅读顺序：先看主体，再看合作方式\n"
            "第X行｜仅供排版定位"
        )
        self.assertIn("四行选择矩阵", hits)
        self.assertIn("阅读顺序：先看主体，再看合作方式", hits)
        self.assertIn("第X行｜仅供排版定位", hits)
        self.assertNotIn("四种合作方式", hits)

    def test_detail_phrase_rule_ignores_full_prose_and_flags_only_labelled_details(self) -> None:
        short = "**完整文字稿**\n" + ("这是完整文字稿中的长段落，允许保留业务事实、条件和关系。" * 8)
        visible = (
            "模块标题\n"
            "    短标签：保留一个清晰的业务短句。\n"
            "    长标签：" + "这是一条仍然塞入多个并列条件和解释关系的明细文字。" * 4
        )
        self.assertTrue(short)
        overages = _onscreen_detail_phrase_overages(visible)
        self.assertEqual(1, len(overages))
        self.assertGreater(overages[0][1], 30)
        self.assertEqual((), _onscreen_detail_phrase_overages("模块标题\n完整业务标签"))

    def test_full_prose_is_not_a_visible_detail_input(self) -> None:
        page = parse_script_markdown(
            "## 第1页：正文与上屏分离\n"
            "- 页面类型：内容页\n"
            "- 完整文字稿："
            + ("这是完整文字稿中的连续业务论证，允许保留事实、条件、关系和边界。" * 8)
            + "\n"
            "- 上屏文字：\n"
            "  **业务判断**\n"
            "      关键事实：形成稳定的服务链。\n"
            "- 视觉结构：判断证据支撑。\n"
        ).pages[0]
        codes = {issue.code for issue in _presentation_issues(page)}
        self.assertNotIn("ONSCREEN_DETAIL_PHRASE_TOO_LONG", codes)

    def test_detail_phrase_error_blocks_only_when_hard_band_is_crossed(self) -> None:
        page = parse_script_markdown(
            "## 第1页：明细阈值\n"
            "- 页面类型：内容页\n"
            "- 主判断：形成稳定服务链\n"
            "- 完整文字稿：形成稳定服务链并保留必要事实和边界。\n"
            "- 上屏文字：\n"
            "  **服务机制**\n"
            "      机制说明：" + "这是一条超过硬阈值的明细句，包含多个并列条件和交付要求。" * 4 + "\n"
            "- 视觉结构：判断证据支撑。\n"
        ).pages[0]
        issues = [
            issue
            for issue in _presentation_issues(
                page,
                strict_detail_phrase_length=True,
            )
            if issue.code == "ONSCREEN_DETAIL_PHRASE_TOO_LONG"
        ]
        self.assertEqual(1, len(issues))
        self.assertEqual("error", issues[0].severity)

    def test_detail_phrase_over_thirty_chars_is_a_blocking_error(self) -> None:
        page = parse_script_markdown(
            "## 第1页：短语化上屏\n"
            "- 页面类型：内容页\n"
            "- 完整文字稿：完整文字稿可以连续说明事实、关系和边界。\n"
            "- 上屏文字：\n"
            "事项说明：1234567890123456789012345678901\n"
            "- 视觉结构：事项与依据。\n"
        ).pages[0]

        issues = [
            issue
            for issue in _presentation_issues(
                page,
                strict_detail_phrase_length=True,
            )
            if issue.code == "ONSCREEN_DETAIL_PHRASE_TOO_LONG"
        ]

        self.assertEqual(1, len(issues))
        self.assertEqual("error", issues[0].severity)

    def test_imagegen_blocks_requested_page_with_paragraph_like_onscreen_copy(self) -> None:
        document = parse_script_markdown(
            "## 第21页：合作对象与合作方式\n"
            "- 页面类型：内容页\n"
            "- 上屏文字：\n"
            "  **参与主体**\n"
            "      按资源条件参与合作：" + "各类主体结合资源条件选择合作方式并明确责任分工。" * 5 + "\n"
        )

        with self.assertRaisesRegex(ValueError, "P21"):
            assert_imagegen_onscreen_readiness(document, {21})
        assert_imagegen_onscreen_readiness(document, {20})

    def test_imagegen_also_blocks_warning_band_detail_copy(self) -> None:
        document = parse_script_markdown(
            "## 第5页：合作基础\n"
            "- 页面类型：内容页\n"
            "- 上屏文字：\n"
            "  **行业节点**\n"
            "      节点建设：" + "承担主体连接、目录衔接、接口协同和场景承接。" * 3 + "\n"
        )

        with self.assertRaisesRegex(ValueError, "P05"):
            assert_imagegen_onscreen_readiness(document, {5})

    def test_four_parallel_short_items_do_not_require_paragraph_density(self) -> None:
        page = parse_script_markdown(
            "## 第21页：合作对象与合作方式\n"
            "- 页面类型：内容页\n"
            "- 完整文字稿：" + "合作主体依据资源条件选择合作方式并明确责任。" * 30 + "\n"
            "- 上屏文字：\n"
            "  **四类参与主体**\n"
            "      电力及能源企业：提供行业场景与业务数据。\n"
            "      科研院所及高校：提供科研数据与知识模型。\n"
            "      数字科技企业：提供技术产品与治理能力。\n"
            "      专业咨询机构：提供行业研究与推广支持。\n"
            "- 视觉结构：四类主体并列。\n"
        ).pages[0]

        error_codes = {
            issue.code
            for issue in _prose_issues(page, independent_reading_required=True)
            if issue.severity == "error"
        }
        self.assertNotIn("ONSCREEN_STORY_DENSITY_LOW", error_codes)
        self.assertNotIn("ONSCREEN_SEMANTIC_COVERAGE_LOW", error_codes)

ROOT = Path(__file__).resolve().parents[1]
POWER_PROJECT = ROOT / "projects" / "power-supply-demand-forecast-early-warning"
SCRIPT_AUDIT_FIXTURES = ROOT / "tests" / "fixtures" / "script_audit"


SCRIPT = """# 第8—9页脚本审稿稿

## 第8页：第二章：定位、目标与研究边界

- 页面类型：章节过渡页
- 上屏文字：第二章：定位、目标与研究边界

## 第9页：总体定位

- 页面类型：内容页
- 页面标题：总体定位
- 主判断：初步定位为面向行业的公共能力。
- 完整文字稿：在现状、变化和能力断点已经建立的前提下，建设方向初步定位为面向行业的公共能力。该定位明确研究方向和服务对象，同时保留专业运行系统的职责边界。正式判断仍需由数据、模型、业务分析和专家会商共同形成。
- 文字稿取舍说明：
  - 必留上屏：行业公共能力；专业系统边界
  - 仅讲解：正式判断仍需数据、模型、业务分析和专家会商共同形成
  - 仅追溯：S015、S026、S059
- 证据映射：公共能力定位→S015；专业系统边界→S026；正式范围待定→S059
- 上屏文字：

  **行业公共能力**

  - 服务行业研判。

  **专业系统边界**

  - 保留专业职责边界。

- 证据：S015、S026、S059
- 边界：正式范围待后续确定。
- 视觉结构：判断证据支撑——中央公共能力定位，两侧职责边界托举。
- 讲解提示：先说定位再说边界。

【演讲者备注】

建设定位是面向行业的公共能力，服务履职与行业共用；同时明确与专业系统的职责分工，不替代调度、出清和企业计划。正式范围仍需结合资源摸底和原型验证进一步确定，当前阶段不提前锁定实施参数。
"""


def strict_outline(*pages: dict[str, object]) -> dict[str, object]:
    return {"argument_contract_mode": "strict", "pages": list(pages)}


def source_truth(*records: dict[str, object]) -> dict[str, object]:
    return {"argument_contract_mode": "strict", "records": list(records)}


def _consumption_fixture(receipt: dict[str, object] | None) -> tuple[ScriptPage, dict[str, object]]:
    units = [
        {
            "unit_id": "CU-P01-01",
            "role": "primary",
            "statement": "统一目录支撑行业数据服务",
            "source_refs": ["S001"],
            "source_statements": ["统一目录支撑行业数据服务"],
        },
        {
            "unit_id": "CU-P01-02",
            "role": "boundary",
            "statement": "价格与责任待后续确认",
            "source_refs": ["S002"],
            "source_statements": ["价格与责任待后续确认"],
        },
    ]
    page = ScriptPage(
        page_id="p01",
        sequence=1,
        heading="",
        page_type="content",
        title="",
        main_message="统一目录支撑行业数据服务",
        full_prose="统一目录支撑行业数据服务",
        selection_notes="",
        evidence_map="",
        evidence_map_refs=(),
        source_refs=("S001",),
        boundary_source_refs=("S002",),
        boundary="",
        visual_structure="闭环",
        onscreen_text="统一目录支撑行业数据服务",
        module_titles=(),
        contract_receipt=receipt,
    )
    contract = {
        "source_evidence_contract": {"mode": "required", "units": units},
        "content_units": units,
    }
    return page, contract


class ContentUnitConsumptionTests(unittest.TestCase):
    def test_missing_declaration_is_blocked(self) -> None:
        page, contract = _consumption_fixture({})
        issues = _source_consumption_issues(page, contract)
        self.assertEqual(
            ["CONTENT_UNIT_CONSUMPTION_DECLARATION_MISSING"],
            [issue.code for issue in issues],
        )

    def test_mismatched_declaration_is_blocked(self) -> None:
        page, contract = _consumption_fixture(
            {"consumed_content_unit_ids": ["CU-P01-02"]}
        )
        issues = _source_consumption_issues(page, contract)
        self.assertEqual(
            ["CONTENT_UNIT_CONSUMPTION_DECLARATION_MISMATCH"],
            [issue.code for issue in issues],
        )

    def test_boundary_unit_is_traceability_only(self) -> None:
        page, contract = _consumption_fixture(
            {"consumed_content_unit_ids": ["CU-P01-01"]}
        )
        self.assertEqual([], _source_consumption_issues(page, contract))


class ScriptMarkdownParserTests(unittest.TestCase):
    def test_parse_script_path_prefers_verified_sidecar(self) -> None:
        script = "## 第1页：测试\n\n- 页面类型：内容页\n- 页面标题：测试\n"
        legacy = {
            "schema": "cyberppt.page_contract_receipt.v2",
            "page_id": "p01",
            "core_message": "旧注释",
        }
        script += (
            "<!-- cyberppt-page-contract "
            + json.dumps(legacy, ensure_ascii=False)
            + " -->\n"
        )
        sidecar_receipt = {
            "schema": "cyberppt.page_contract_receipt.v2",
            "page_id": "p01",
            "core_message": "独立合同",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script-final.md"
            script_path.write_text(script, encoding="utf-8")
            (script_path.parent / "page-contracts.json").write_text(
                json.dumps(
                    {
                        "schema": "cyberppt.page_contracts.v1",
                        "script": script_path.name,
                        "script_sha256": hashlib.sha256(script_path.read_bytes()).hexdigest(),
                        "pages": {"p01": sidecar_receipt},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            page = parse_script_path(script_path).pages[0]

        self.assertEqual("独立合同", page.contract_receipt["core_message"])

    def test_parse_script_path_rejects_stale_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script-final.md"
            script_path.write_text(
                "## 第1页：测试\n\n- 页面类型：内容页\n- 页面标题：测试\n",
                encoding="utf-8",
            )
            (script_path.parent / "page-contracts.json").write_text(
                json.dumps(
                    {
                        "schema": "cyberppt.page_contracts.v1",
                        "script": script_path.name,
                        "script_sha256": "0" * 64,
                        "pages": {},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "sidecar is stale"):
                parse_script_path(script_path)

    def test_parse_script_path_keeps_legacy_comment_fallback(self) -> None:
        receipt = {
            "schema": "cyberppt.page_contract_receipt.v2",
            "page_id": "p01",
            "core_message": "旧项目仍可读取",
        }
        script = (
            "## 第1页：测试\n\n- 页面类型：内容页\n- 页面标题：测试\n"
            "<!-- cyberppt-page-contract "
            + json.dumps(receipt, ensure_ascii=False)
            + " -->\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "script-final.md"
            script_path.write_text(script, encoding="utf-8")
            page = parse_script_path(script_path).pages[0]

        self.assertEqual("旧项目仍可读取", page.contract_receipt["core_message"])

    def test_four_digit_source_ids_are_parsed_as_complete_refs(self) -> None:
        page = parse_script_markdown(
            """## 第23页：四位证据引用
- 页面类型：内容页
- 页面标题：四位证据引用
- 主判断：四位证据引用应保持完整。
- 证据：S0410、S0420
- 证据映射：组织→S0410；原型→S0420
- 完整文字稿：这是足够长的完整文字稿，用于证明解析器保留四位来源标识，而不是把它截断为三位。这里继续补充若干业务事实、关系和结果，确保该字段具备短文章形态并可供质量合同检查。
- 文字稿取舍说明：必留上屏：组织和原型；仅讲解：细节；仅追溯：S0410、S0420
- 上屏文字：

  **组织**
  - 组织机制与责任清单形成可追溯的启动基础

  **原型**
  - 原型验证数据导入、质量检查和报告生成流程

【视觉结构，不上屏】
采用阶段推进主链呈现组织到原型的关系。

【演讲者备注】

组织与原型按同一启动链路推进。
"""
        )
        self.assertEqual(("S0410", "S0420"), page.pages[0].source_refs)
        self.assertEqual(("S0410", "S0420"), page.pages[0].evidence_map_refs)

    def test_source_id_ranges_expand_to_atomic_refs(self) -> None:
        page = parse_script_markdown(
            """## 第23页：范围证据引用
- 页面类型：内容页
- 页面标题：范围证据引用
- 主判断：范围引用在审计时展开为原子来源。
- 证据：S0410—S0412
- 证据映射：组织与原型→S0410—S0412
- 完整文字稿：范围引用仍然对应明确的业务事实、关系和结果，脚本解析器应当展开每一个原子来源并保留来源顺序。
- 文字稿取舍说明：必留上屏：组织与原型；仅讲解：细节；仅追溯：S0410—S0412
- 上屏文字：

  **组织与原型**
  - 组织、数据和原型按同一启动链路推进

【视觉结构，不上屏】
采用阶段推进主链呈现组织到原型的关系。

【演讲者备注】

组织与原型按同一启动链路推进。
"""
        ).pages[0]
        self.assertEqual(("S0410", "S0411", "S0412"), page.source_refs)
        self.assertEqual(("S0410", "S0411", "S0412"), page.evidence_map_refs)

    def test_explicit_source_truth_ids_and_ranges_are_preserved(self) -> None:
        page = parse_script_markdown(
            """## 第23页：正式来源引用
- 页面类型：内容页
- 证据：ST003、ST0410—ST0412
- 证据映射：正式证据→ST003、ST0410—ST0412
"""
        ).pages[0]
        self.assertEqual(
            ("ST003", "ST0410", "ST0411", "ST0412"), page.source_refs
        )
        self.assertEqual(
            ("ST003", "ST0410", "ST0411", "ST0412"),
            page.evidence_map_refs,
        )

    def test_inline_module_titles_are_retained_as_modules(self) -> None:
        page = parse_script_markdown(
            """## 第16页：共性能力底座
- 页面类型：内容页
- 上屏文字：
  **业务标准**｜目录、对象、尺度和口径统一
  **分层数据**｜必需数据先成稳定链路
  **模型体系**｜分步建设并滚动回测
"""
        ).pages[0]

        self.assertEqual(
            ("业务标准", "分层数据", "模型体系"),
            page.module_titles,
        )
        self.assertIn("口径统一", page.onscreen_text)

    def test_non_onscreen_visual_structure_block_is_parsed_separately(self) -> None:
        page = parse_script_markdown(
            """## 第11页：五层总体能力框架
- 页面类型：内容页
- 页面标题：五层总体能力框架
- 上屏文字：

  **运行闭环**
  - 数据治理 → 模型计算 → 审核发布

【视觉结构，不上屏】
五层纵向架构与一条横向运行闭环同构呈现。

【演讲者备注】
说明五层框架。
"""
        ).pages[0]
        self.assertIn("运行闭环", page.onscreen_text)
        self.assertNotIn("视觉结构", page.onscreen_text)
        self.assertEqual(
            "五层纵向架构与一条横向运行闭环同构呈现。",
            page.visual_structure,
        )

    def test_parser_accepts_core_message_human_label(self) -> None:
        document = parse_script_markdown(
            """## 第1页：建设目标与能力框架
- 页面类型：内容页
- 页面标题：建设目标与能力框架
- 核心结论：总体能力框架由五个层次构成，各层分别承担相应职责。
- 证据：S021
- 完整文字稿：总体能力框架由五个层次构成，各层分别承担相应职责，并分别展开业务应用、成果服务、模型分析、数据治理和运行保障等内容。
- 文字稿取舍说明：必留上屏：五层名称；仅讲解：职责说明；仅追溯：S021。
- 证据映射：S021
- 视觉结构：五层结构
- 上屏文字：五层总体能力框架
"""
        )
        self.assertEqual(
            "总体能力框架由五个层次构成，各层分别承担相应职责。",
            document.pages[0].core_message,
        )

    def test_extracts_pages_and_fields(self) -> None:
        document = parse_script_markdown(SCRIPT)

        self.assertEqual(["p08", "p09"], [page.page_id for page in document.pages])
        self.assertEqual("chapter", document.pages[0].page_type)
        self.assertEqual("总体定位", document.pages[1].title)
        self.assertEqual(("S015", "S026", "S059"), document.pages[1].source_refs)
        self.assertEqual(("行业公共能力", "专业系统边界"), document.pages[1].module_titles)
        self.assertEqual("先说定位再说边界。", document.pages[1].coaching_tip)
        self.assertTrue(selection_notes_are_structured(document.pages[1].selection_notes))
        parsed = parse_selection_notes(document.pages[1].selection_notes)
        self.assertIn("行业公共能力", parsed["必留上屏"])
        self.assertIn("S015", parsed["仅追溯"])

    def test_rejects_document_without_pages(self) -> None:
        with self.assertRaisesRegex(ValueError, "no page headings"):
            parse_script_markdown("# empty")

    def test_onscreen_block_stops_at_next_backend_field(self) -> None:
        page = parse_script_markdown(SCRIPT).pages[1]

        self.assertNotIn("- 证据：", page.onscreen_text)
        self.assertNotIn("S015", page.onscreen_text)

    def test_heading_backend_fields_stay_out_of_onscreen_text(self) -> None:
        page = parse_script_markdown(
            """## 第4页：建设背景
- 页面类型：内容页
### 上屏文字

驱动背景：新型能源体系加快建设
### 证据映射（后台，不上屏）

发展变化→ST0007
### 证据（后台，不上屏）

ST0007
### 边界依据（后台，不上屏）

ST0020
【视觉结构，不上屏】
发展变化指向协同需求。
"""
        ).pages[0]
        self.assertEqual("驱动背景：新型能源体系加快建设", page.onscreen_text)
        self.assertEqual(("ST0007",), page.evidence_map_refs)
        self.assertEqual(("ST0007", "ST0020"), page.source_refs)
        self.assertEqual(("ST0020",), page.boundary_source_refs)
        self.assertEqual("发展变化指向协同需求。", page.visual_structure)

    def test_plain_text_modules_do_not_require_markdown(self) -> None:
        page = parse_script_markdown(
            """## 第1页：示例
- 页面类型：内容页
### 上屏文字（严格锁定）

业务演进
    系统运行：新能源接入使运行关系更加复杂。
    市场经营：交易与保供分析更加精细。
### 视觉结构（不上屏）

左右双区对照，阅读顺序由左至右。
"""
        ).pages[0]
        self.assertEqual("业务演进", page.top_level_module_titles[0])
        self.assertNotIn("**", page.onscreen_text)
        self.assertNotIn("####", page.onscreen_text)

    def test_rejects_detached_subordinate_phrase_after_authoring_label(self) -> None:
        self.assertEqual(
            ("驱动背景：随着新型能源体系和新型电力系统加快建设",),
            _onscreen_subordinate_fragments(
                "驱动背景：随着新型能源体系和新型电力系统加快建设"
            ),
        )
        self.assertEqual(
            (),
            _onscreen_subordinate_fragments(
                "新型能源体系和新型电力系统加快建设，跨主体数据需求持续增长"
            ),
        )

    def test_rejects_mixed_argument_functions_as_indented_peers(self) -> None:
        text = """行业变化
    电力行业是基础性、战略性行业
    新型电力系统建设加快
    运行保供需要多源数据"""
        hits = _onscreen_false_parallel_semantics(text)
        self.assertEqual(1, len(hits))
        self.assertIn("attribute", hits[0])
        self.assertIn("change", hits[0])
        self.assertIn("demand", hits[0])

    def test_accepts_one_dimension_as_indented_peers(self) -> None:
        text = """跨主体协同
    跨企业需要数据和模型共同参与
    跨领域需要电力与气象数据协同
    跨能力需要模型、专家和技术实施"""
        self.assertEqual((), _onscreen_false_parallel_semantics(text))

    def test_accepts_named_actor_duties_as_indented_peers(self) -> None:
        text = """职责承接｜四类主体围绕客户需求协同运行
    中电联统筹：统筹重大事项、审定规则、协调行业资源
    数智公司运营：组织产品、服务客户、协同交付与结算
    合作伙伴供给：提供数据、模型、专业服务和市场渠道
    需求单位使用反馈：提出业务需求、订购使用并反馈成效"""
        self.assertEqual((), _onscreen_false_parallel_semantics(text))

    def test_accepts_named_cooperation_methods_with_distinct_conditions(self) -> None:
        text = """合作方式｜四类路径匹配不同条件
    标准接入：产品和接口已经成熟，重点完成测试与上架
    联合产品：资源具备基础，仍需共同形成产品和市场方案
    场景联合运营：复杂业务问题需要多方能力组合与持续服务
    战略生态：骨干主体围绕重点资源和示范场景持续合作"""
        self.assertEqual((), _onscreen_false_parallel_semantics(text))

    def test_markdown_and_authoring_meta_in_locked_text_are_errors(self) -> None:
        document = parse_script_markdown(
            """## 第1页：示例
- 页面类型：内容页
### 上屏文字（严格锁定）

#### 业务演进与协同需求两个层面
- **业务演进**：业务关系变化。
### 视觉结构（不上屏）

左右双区对照，阅读顺序由左至右。
"""
        )
        page = document.pages[0]
        codes = {issue.code for issue in audit_script_quality(
            document,
            strict_outline(
                {
                    "page_id": "p01",
                    "sequence": 1,
                    "page_type": "content",
                    "title": "示例",
                    "argument_role": "positioning",
                    "source_refs": [],
                    "prerequisite_pages": [],
                    "main_claim_status": "proposed",
                }
            ),
            {"records": []},
        )}
        self.assertIn("ONSCREEN_MARKDOWN_LEAK", codes)
        self.assertIn("ONSCREEN_BACKEND_META_LEAK", codes)

    def test_extracts_optional_presentation_fields_and_keeps_legacy_defaults(self) -> None:
        page = parse_script_markdown(
            """## 第1页：示例
- 页面类型：内容页
- 上屏结论：结论
- 上屏文字：正文
- 版式母题：process_atlas
- 场景角色：no_scene
- 生图锁定文字：短标签
- 视觉证明：供需信息经过数据治理、模型推演和专家会商形成行业研判成果
"""
        ).pages[0]
        self.assertEqual("process_atlas", page.layout_motif)
        self.assertEqual("no_scene", page.scene_role)
        self.assertEqual("短标签", page.image_locked_text)
        self.assertEqual(
            "供需信息经过数据治理、模型推演和专家会商形成行业研判成果",
            page.visual_proof,
        )

        legacy = parse_script_markdown(
            """## 第2页：旧页
- 页面类型：内容页
- 上屏结论：结论
- 上屏文字：正文
"""
        ).pages[0]
        self.assertEqual("", legacy.layout_motif)
        self.assertEqual("", legacy.scene_role)
        self.assertEqual("", legacy.image_locked_text)
        self.assertEqual("", legacy.visual_proof)


class NegativeForegroundRuleTests(unittest.TestCase):
    def _page(
        self,
        *,
        title: str,
        main_message: str,
        onscreen: str = "",
        prose: str = "",
        visual_structure: str = "",
    ) -> ScriptPage:
        return ScriptPage(
            page_id="p09",
            sequence=9,
            heading=title,
            page_type="content",
            title=title,
            main_message=main_message,
            full_prose=prose,
            selection_notes="",
            evidence_map="",
            evidence_map_refs=(),
            source_refs=(),
            boundary_source_refs=(),
            boundary="",
            visual_structure=visual_structure,
            onscreen_text=onscreen,
            module_titles=(),
            top_level_module_titles=("供给缺口",) if onscreen else (),
            speaker_notes="",
        )

    def test_non_boundary_page_rejects_negative_foreground_in_title_and_script(self) -> None:
        page = self._page(
            title="行业服务供给缺口",
            main_message="当前供给不足，需形成运营能力。",
            prose="当前供给不足，需要组织服务能力。后续按产品目录推进。",
            visual_structure="核心呈现供给缺口与建设任务的对应关系。",
        )
        issues = _negative_foreground_issues(
            page,
            {
                "argument_role": "positioning",
                "title": "行业服务供给缺口",
                "topic_category": "平台定位",
            },
        )
        self.assertEqual(
            {"NEGATIVE_FOREGROUND_OUTSIDE_BOUNDARY_TOPIC"},
            {issue.code for issue in issues},
        )
        self.assertEqual("error", issues[0].severity)
        self.assertIn("页面标题：缺口", issues[0].evidence)
        self.assertIn("主判断：不足", issues[0].evidence)

    def test_title_cannot_self_exempt_without_direct_boundary_role(self) -> None:
        page = self._page(
            title="平台角色与控制边界",
            main_message="平台组织资源和服务运营。",
        )
        issues = _negative_foreground_issues(
            page,
            {
                "argument_role": "positioning",
                "title": "平台角色与控制边界",
                "topic_category": "平台定位",
            },
        )
        self.assertEqual(
            ["NEGATIVE_FOREGROUND_OUTSIDE_BOUNDARY_TOPIC"],
            [issue.code for issue in issues],
        )

    def test_direct_boundary_clarification_is_the_only_exception(self) -> None:
        page = self._page(
            title="安全边界与准入要求",
            main_message="按安全、质量和授权要求组织准入。",
            onscreen="安全边界\n    准入要求：登记后受控使用",
        )
        self.assertEqual(
            [],
            _negative_foreground_issues(
                page,
                {
                    "argument_role": "assurance",
                    "title": "安全边界与准入要求",
                    "topic_category": "安全边界",
                },
            ),
        )

    def test_audit_emits_hard_error_and_retry_for_new_rules(self) -> None:
        script = parse_script_markdown(
            """## 第9页：平台定位：连接，而非替代
- 页面类型：内容页
- 页面标题：平台定位：连接，而非替代
- 主判断：供给不足，需要形成服务能力。
- 完整文字稿：供给不足，需要形成可运营的服务能力。平台通过资源连接与服务组织支撑行业协同。
- 文字稿取舍说明：
  - 必留上屏：服务组织
  - 仅讲解：能力建设
  - 仅追溯：S001
- 证据映射：服务组织→S001
- 上屏文字：
  **供给缺口**
    建设动作：组织资源与服务
- 证据：S001
- 视觉结构：重点呈现供给缺口与服务组织的关系。
"""
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "平台定位",
                    "argument_role": "positioning",
                    "source_refs": ["S001"],
                    "prerequisite_pages": [],
                }
            ),
            source_truth(
                {"id": "S001", "type": "F", "status": "已形成", "statement": "平台组织资源与服务。"}
            ),
        )
        rule_issues = [
            issue
            for issue in issues
            if issue.code
            in {
                "PROHIBITED_NEGATIVE_CONTRAST",
                "NEGATIVE_FOREGROUND_OUTSIDE_BOUNDARY_TOPIC",
            }
        ]
        self.assertEqual(
            {
                "PROHIBITED_NEGATIVE_CONTRAST",
                "NEGATIVE_FOREGROUND_OUTSIDE_BOUNDARY_TOPIC",
            },
            {issue.code for issue in rule_issues},
        )
        self.assertTrue(all(issue.severity == "error" for issue in rule_issues))
        directive = script_retry_directive(rule_issues)
        self.assertEqual("business_prose_first", directive["strategy"])
        self.assertIn("direct positive", str(directive["instruction"]))


class ScriptContractAuditTests(unittest.TestCase):
    def test_trailing_boundary_caveat_cannot_become_peer_module(self) -> None:
        outline = strict_outline(
            {
                "page_id": "p12",
                "sequence": 12,
                "page_type": "content",
                "title": "建设范围与研究边界",
                "page_mission": "说明首期范围并保留研究边界。",
                "core_message": "首期聚焦两项业务；完整系统范围仍待论证。",
                "source_refs": ["S015"],
                "content_units": [
                    {"statement": "首期聚焦两项业务。", "source_refs": ["S015"], "role": "primary"}
                ],
            }
        )
        truth = source_truth(
            {"id": "S015", "type": "J", "status": "原文陈述", "statement": "首期聚焦两项业务。"},
        )
        script = """## 第12页：建设范围与研究边界
- 页面类型：内容页
- 页面标题：建设范围与研究边界
- 主判断：首期聚焦两项业务；完整系统范围仍待论证。
- 完整文字稿：首期聚焦两项业务，并保留后续论证事项。首期业务形成可运行闭环，并按数据条件逐步扩展。
- 文字稿取舍说明：
  - 必留上屏：首期两项业务
  - 仅讲解：后续论证事项
  - 仅追溯：S015
- 证据映射：首期范围→S015
- 上屏文字：
  **首期两项业务**
  - 月度季度分析和年度报告自动化
  **研究边界**
  - 完整系统范围仍待论证
- 证据：S015
【视觉结构，不上屏】
突出首期两项业务。
【演讲者备注】
首期聚焦两项业务，并根据验证结果逐步扩展。
"""
        codes = {issue.code for issue in audit_script_quality(parse_script_markdown(script), outline, truth)}
        self.assertIn("OFF_TOPIC_CONSTRAINT_MODULE", codes)

    def test_required_page_contract_receipt_must_be_present(self) -> None:
        outline = strict_outline(
            {
                "page_id": "p09",
                "sequence": 9,
                "page_type": "content",
                "title": "总体定位",
                "argument_role": "positioning",
                "source_refs": ["S015", "S026", "S059"],
                "prerequisite_pages": [],
            }
        )
        outline["page_contract_receipt_mode"] = "required"
        truth = source_truth(
            {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"},
            {"id": "S026", "type": "B", "status": "研究边界", "statement": "专业边界。"},
            {"id": "S059", "type": "B", "status": "研究边界", "statement": "正式范围待定。"},
        )

        codes = {
            issue.code
            for issue in audit_script_quality(parse_script_markdown(SCRIPT), outline, truth)
        }

        self.assertIn("PAGE_CONTRACT_RECEIPT_MISSING", codes)

    def test_matching_page_contract_receipt_passes(self) -> None:
        outline = strict_outline(
            {
                "page_id": "p09",
                "sequence": 9,
                "page_type": "content",
                "title": "总体定位",
                "argument_role": "positioning",
                "source_refs": ["S015", "S026", "S059"],
                "prerequisite_pages": [],
                "main_message": "初步定位为面向行业的公共能力。",
            }
        )
        outline["page_contract_receipt_mode"] = "required"
        receipt = (
            '<!-- cyberppt-page-contract {"schema":"cyberppt.page_contract_receipt.v1",'
            '"page_id":"p09","main_message":"初步定位为面向行业的公共能力。",'
            '"new_value_realized":true,"reserved_for_later_respected":true} -->\n'
        )
        script = SCRIPT.replace("【演讲者备注】", receipt + "【演讲者备注】")
        truth = source_truth(
            {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"},
            {"id": "S026", "type": "B", "status": "研究边界", "statement": "专业边界。"},
            {"id": "S059", "type": "B", "status": "研究边界", "statement": "正式范围待定。"},
        )

        codes = {
            issue.code
            for issue in audit_script_quality(parse_script_markdown(script), outline, truth)
        }

        self.assertFalse(any(code.startswith("PAGE_CONTRACT_") for code in codes))

    def test_communication_review_tracks_mission_and_lead(self) -> None:
        script = parse_script_markdown(
            """## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：公共能力定位支撑行业研判。
- 上屏文字：

  公共能力定位支撑行业研判。

  **服务对象**

  - 服务行业公共研判。

- 视觉结构：判断证据支撑。

【演讲者备注】

建设定位、服务对象和职责边界共同构成本阶段的基本判断。
"""
        )
        review = build_communication_review(
            script,
            {
                "pages": [
                    {
                        "page_id": "p09",
                        "business_question": "拟建什么性质的能力",
                    }
                ]
            },
        )

        self.assertEqual(1, review["content_pages"])
        self.assertEqual(1, review["mission_coverage"])
        self.assertEqual(1, review["lead_match_count"])
        page = review["pages"][0]
        self.assertEqual("拟建什么性质的能力", page["mission"])
        self.assertTrue(page["lead_matches_main_message"])
        self.assertEqual("lead", page["core_message_display_mode"])
        self.assertGreaterEqual(page["core_message_visible_coverage"], 0.55)
        self.assertIn("semantic_coverage", page)
        self.assertEqual("high", review["reading_density_default"])
        self.assertEqual(1, review["reading_density_low_count"])
        self.assertEqual("low", page["reading_density_status"])
        self.assertEqual(
            {"conclusion", "evidence", "relation", "closure"},
            set(page["story_roles"]),
        )
        self.assertEqual("manual_review", page["review_questions"]["single_mission"])

    def test_communication_review_flags_core_message_left_only_in_metadata(self) -> None:
        page = parse_script_markdown(
            """## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：公共能力定位支撑行业研判
- 上屏文字：

  **建设基础**

  - 已完成接口登记

- 视觉结构：建设基础支撑后续工作。
"""
        )
        review = build_communication_review(
            page,
            {"pages": [{"page_id": "p09", "page_mission": "说明总体定位"}]},
        )

        result = review["pages"][0]
        self.assertEqual("metadata_only_review", result["core_message_display_mode"])
        self.assertIn(
            "CORE_MESSAGE_AUDIENCE_VISIBILITY_REVIEW",
            {finding["code"] for finding in result["findings"]},
        )

    def test_effective_density_ignores_markdown_and_uses_adaptive_target(self) -> None:
        page = parse_script_markdown(
            """## 第9页：密度测试
- 页面类型：内容页
- 主判断：形成完整判断。
- 上屏结论：形成完整判断
- 完整文字稿：这是用于测试动态密度目标的完整文字稿，持续补充业务事实、证据关系和页面结论，使正文长度足以触发最低有效字符门槛。
- 上屏文字：
  **证据模块**
  - 事实一支撑判断。
  - 事实二解释关系。
"""
        ).pages[0]

        self.assertEqual(
            len("形成完整判断证据模块事实一支撑判断事实二解释关系"),
            meaningful_char_count(page.onscreen_judgment + page.onscreen_text),
        )
        self.assertEqual(220, onscreen_effective_char_target(page))
        self.assertTrue(onscreen_story_roles(page)["relation"])

    def test_all_content_pages_require_density_without_forcing_visible_conclusion(self) -> None:
        script = """## 第10页：供需研判底座
- 页面类型：内容页
- 页面标题：供需研判底座
- 主判断：供需研判由数据、模型和成果流程共同承载。
- 完整文字稿：供需研判需要统一数据口径，形成稳定的数据接入和治理链路，再按业务对象和时间尺度组织模型计算。模型结果还要经过业务解释、报告生产、审核发布和版本留痕，实际数据形成后再回到误差复盘，支持下一轮研判。
- 文字稿取舍说明：
  - 必留上屏：数据、模型、成果流程和复盘关系
  - 仅讲解：字段级治理方式
  - 仅追溯：S001
- 证据映射：底座关系→S001
- 上屏文字：
  **数据**
  - 统一数据。
  **模型**
  - 形成预测。
- 证据：S001
【视觉结构，不上屏】
以数据、模型和成果流程构成连续主链。
【演讲者备注】
说明数据、模型和成果流程的业务关系。
"""
        outline = strict_outline(
            {
                "page_id": "p10",
                "sequence": 10,
                "page_type": "content",
                "title": "供需研判底座",
                "argument_role": "solution",
                "source_refs": ["S001"],
                "prerequisite_pages": [],
            }
        )
        issues = audit_script_quality(
            parse_script_markdown(script),
            outline,
            source_truth(
                {
                    "id": "S001",
                    "type": "R",
                    "status": "原文陈述",
                    "statement": "数据、模型和成果流程构成研判底座。",
                }
            ),
        )
        codes = {issue.code for issue in issues}

        self.assertIn("ONSCREEN_STORY_DENSITY_LOW", codes)
        self.assertNotIn("ONSCREEN_JUDGMENT_MISSING", codes)
        self.assertNotIn("SCRIPT_JUDGMENT_INTRODUCED", codes)
        self.assertNotIn("ONSCREEN_STORY_NOT_CLOSED", codes)

    def test_communication_review_warns_when_lead_is_not_main_message(self) -> None:
        script = parse_script_markdown(
            """## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：公共能力定位支撑行业研判。
- 上屏文字：

  **服务对象**

  - 服务行业公共研判。
"""
        )
        review = build_communication_review(
            script,
            {"pages": [{"page_id": "p09", "business_question": "拟建什么能力"}]},
        )

        codes = {item["code"] for item in review["pages"][0]["findings"]}
        self.assertIn("MAIN_MESSAGE_NOT_FIRST_ONSCREEN_LINE", codes)

    def test_legacy_global_mode_does_not_force_a_judgment(self) -> None:
        outline = strict_outline(
            {
                "page_id": "p09",
                "sequence": 9,
                "page_type": "content",
                "title": "总体定位",
                "argument_role": "positioning",
                "source_refs": ["S015", "S026", "S059"],
                "prerequisite_pages": [],
            }
        )
        outline["visible_judgment_mode"] = "required"
        truth = source_truth(
            {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"},
            {"id": "S026", "type": "B", "status": "研究边界", "statement": "专业边界。"},
            {"id": "S059", "type": "B", "status": "研究边界", "statement": "正式范围待定。"},
        )

        missing_codes = {
            issue.code
            for issue in audit_script_quality(
                parse_script_markdown(SCRIPT),
                outline,
                truth,
            )
        }
        self.assertNotIn("ONSCREEN_JUDGMENT_MISSING", missing_codes)

        revised = SCRIPT.replace(
            "- 主判断：初步定位为面向行业的公共能力。\n",
            "- 主判断：初步定位为面向行业的公共能力。\n"
            "- 上屏结论：面向行业的公共能力定位支撑行业研判\n",
            1,
        )
        revised_codes = {
            issue.code
            for issue in audit_script_quality(
                parse_script_markdown(revised),
                outline,
                truth,
            )
        }
        self.assertIn("SCRIPT_JUDGMENT_INTRODUCED", revised_codes)

        punctuated = revised.replace(
            "- 上屏结论：面向行业的公共能力定位支撑行业研判\n",
            "- 上屏结论：面向行业的公共能力定位支撑行业研判。\n",
        )
        punctuated_codes = {
            issue.code
            for issue in audit_script_quality(
                parse_script_markdown(punctuated),
                outline,
                truth,
            )
        }
        self.assertIn("SCRIPT_JUDGMENT_INTRODUCED", punctuated_codes)

    def test_semantic_alignment_allows_source_faithful_visible_compression(self) -> None:
        outline = strict_outline(
            {
                "page_id": "p09",
                "sequence": 9,
                "page_type": "content",
                "title": "总体定位",
                "core_message": "平台连接行业资源并组织可信服务供给。",
                "onscreen_judgment_mode": "semantic_alignment",
                "source_refs": ["S015"],
            }
        )
        script = SCRIPT.replace(
            "- 主判断：初步定位为面向行业的公共能力。\n",
            "- 主判断：平台连接行业资源并组织可信服务供给。\n"
            "- 上屏结论：平台连接资源并形成可信服务供给\n",
            1,
        )
        truth = source_truth(
            {"id": "S015", "type": "B", "status": "原文陈述", "statement": "平台连接行业资源并组织可信服务供给。"},
        )

        codes = {
            issue.code
            for issue in audit_script_quality(
                parse_script_markdown(script), outline, truth,
            )
        }

        self.assertNotIn("SCRIPT_JUDGMENT_INTRODUCED", codes)
        self.assertNotIn("ONSCREEN_JUDGMENT_CONTRACT_MISMATCH", codes)

    def test_hidden_mode_rejects_an_independent_visible_judgment(self) -> None:
        outline = strict_outline(
            {
                "page_id": "p09",
                "sequence": 9,
                "page_type": "content",
                "title": "总体定位",
                "onscreen_judgment_mode": "hidden",
                "source_refs": ["S015"],
            }
        )
        script = SCRIPT.replace(
            "- 主判断：初步定位为面向行业的公共能力。\n",
            "- 主判断：初步定位为面向行业的公共能力。\n"
            "- 上屏结论：面向行业的公共能力定位支撑行业研判\n",
            1,
        )
        truth = source_truth(
            {"id": "S015", "type": "B", "status": "原文陈述", "statement": "初步定位。"},
        )

        codes = {
            issue.code
            for issue in audit_script_quality(
                parse_script_markdown(script), outline, truth,
            )
        }

        self.assertIn("SCRIPT_JUDGMENT_INTRODUCED", codes)

    @unittest.skipUnless(
        (POWER_PROJECT / "workbench/stages/01-analysis/outline.json").is_file(),
        "power-supply-demand project artifacts not present",
    )
    def test_power_foundation_regression_is_blocked(self) -> None:
        script = parse_script_markdown(
            (SCRIPT_AUDIT_FIXTURES / "power_foundation_premature_scope.md").read_text(
                encoding="utf-8"
            )
        )
        outline = json.loads(
            (POWER_PROJECT / "workbench/stages/01-analysis/outline.json").read_text(
                encoding="utf-8"
            )
        )
        truth = json.loads(
            (
                POWER_PROJECT / "workbench/stages/01-analysis/source-truth.json"
            ).read_text(encoding="utf-8")
        )

        codes = {issue.code for issue in audit_script_quality(script, outline, truth)}

        self.assertIn("PREMATURE_SCOPE_CLAIM", codes)

    @unittest.skipUnless(
        (POWER_PROJECT / "workbench/stages/01-analysis/outline.json").is_file(),
        "power-supply-demand project artifacts not present",
    )
    def test_power_scene_matrix_is_not_treated_as_isolated_method_page(self) -> None:
        script = parse_script_markdown(
            (SCRIPT_AUDIT_FIXTURES / "power_scene_matrix.md").read_text(
                encoding="utf-8"
            )
        )
        outline = json.loads(
            (POWER_PROJECT / "workbench/stages/01-analysis/outline.json").read_text(
                encoding="utf-8"
            )
        )
        truth = json.loads(
            (
                POWER_PROJECT / "workbench/stages/01-analysis/source-truth.json"
            ).read_text(encoding="utf-8")
        )

        codes = {issue.code for issue in audit_script_quality(script, outline, truth)}

        self.assertNotIn("MATRIX_AXES_MISSING", codes)
        self.assertNotIn("MULTIPLE_PAGE_MISSIONS", codes)

    def test_partial_batch_does_not_require_absent_outline_pages(self) -> None:
        outline = strict_outline(
            {
                "page_id": "p08",
                "sequence": 8,
                "page_type": "chapter",
                "title": "第二章：定位、目标与研究边界",
            },
            {
                "page_id": "p09",
                "sequence": 9,
                "page_type": "content",
                "title": "总体定位",
                "argument_role": "positioning",
                "source_refs": ["S015", "S026", "S059"],
                "prerequisite_pages": ["p07"],
                "main_claim_status": "proposed",
            },
            {
                "page_id": "p10",
                "sequence": 10,
                "page_type": "content",
                "title": "能力框架",
                "argument_role": "solution",
                "source_refs": ["S017"],
                "prerequisite_pages": ["p09"],
            },
        )
        truth = source_truth(
            {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"},
            {"id": "S026", "type": "B", "status": "研究边界", "statement": "专业边界。"},
            {"id": "S059", "type": "B", "status": "研究边界", "statement": "正式范围待定。"},
        )

        issues = audit_script_quality(parse_script_markdown(SCRIPT), outline, truth)

        # Reading-page density is now checked for the supplied content page;
        # the partial batch must still not invent requirements for absent p10.
        self.assertTrue(issues)
        self.assertTrue(all("p10" not in issue.pages for issue in issues))

    def test_chapter_page_with_main_message_is_rejected(self) -> None:
        bad = SCRIPT.replace(
            "- 上屏文字：第二章：定位、目标与研究边界",
            "- 主判断：本章明确完整建设方案。\n- 上屏文字：第二章：定位、目标与研究边界",
        )

        issues = audit_script_quality(
            parse_script_markdown(bad),
            strict_outline(
                {
                    "page_id": "p08",
                    "sequence": 8,
                    "page_type": "chapter",
                    "title": "第二章：定位、目标与研究边界",
                }
            ),
            source_truth(),
        )

        self.assertIn("CHAPTER_PAGE_HAS_CONTENT", {issue.code for issue in issues})

    def test_foundation_page_cannot_claim_first_phase_scope(self) -> None:
        script = parse_script_markdown(
            """## 第4页：工作基础
- 页面类型：内容页
- 页面标题：工作基础
- 主判断：现有基础能够直接支撑首期建设全国总盘和定期报告。
- 完整文字稿：本页应以既有统计、研判和协调工作事实为主。若把现有基础能够直接支撑首期建设全国总盘和定期报告写成工作基础页的核心判断，就把尚未进入范围论证的首期建设安排提前固化了。正确写法应先陈述已形成的工作依托，再在范围页讨论首期是否从全国总盘和定期报告入手。
- 文字稿取舍说明：本页只写本页业务问题主体；邻页议题不展开；建议与边界保持拟/待状态。
- 证据映射：支撑点1→S006
- 上屏文字：
  **既有基础**
  - 已具备统计和报告工作。
- 证据：S006
- 边界：本页陈述既有事实。
- 视觉结构：工作基础链。
"""
        )
        outline = strict_outline(
            {
                "page_id": "p04",
                "sequence": 4,
                "page_type": "content",
                "title": "工作基础",
                "argument_role": "foundation",
                "source_refs": ["S006"],
                "prerequisite_pages": [],
                "main_claim_status": "confirmed",
            }
        )
        truth = source_truth(
            {
                "id": "S006",
                "type": "F",
                "status": "已形成",
                "statement": "具备行业协调基础。",
            }
        )

        codes = {issue.code for issue in audit_script_quality(script, outline, truth)}

        self.assertIn("PREMATURE_SCOPE_CLAIM", codes)

    def test_foundation_page_may_repeat_scope_approved_by_outline(self) -> None:
        script = parse_script_markdown(
            """## 第4页：工作基础
- 页面类型：内容页
- 页面标题：工作基础
- 主判断：现有基础支持首期产品与试点启动。
- 完整文字稿：现有组织、资源、平台和场景基础共同支持首期产品与试点启动，脚本仅展开大纲已经批准的判断。
- 文字稿取舍说明：必留上屏：启动基础；仅讲解：细节；仅追溯：S006。
- 证据映射：启动基础→S006
- 上屏文字：
  **启动基础**
  - 现有条件支持首期产品与试点启动。
- 证据：S006
- 视觉结构：现有基础共同支撑启动判断。
"""
        )
        outline = strict_outline(
            {
                "page_id": "p04",
                "sequence": 4,
                "page_type": "content",
                "title": "工作基础",
                "argument_role": "foundation",
                "core_message": "现有基础支持首期产品与试点启动。",
                "source_refs": ["S006"],
                "prerequisite_pages": [],
                "main_claim_status": "confirmed",
            }
        )
        truth = source_truth(
            {
                "id": "S006",
                "type": "F",
                "status": "已形成",
                "statement": "现有基础支持首期产品与试点启动。",
            }
        )

        codes = {issue.code for issue in audit_script_quality(script, outline, truth)}

        self.assertNotIn("PREMATURE_SCOPE_CLAIM", codes)

    def test_necessity_page_may_use_scope_term_from_assigned_source(self) -> None:
        script = parse_script_markdown(
            """## 第3页：行业协同需求与服务供给缺口
- 页面类型：内容页
- 页面标题：行业协同需求与服务供给缺口
- 主判断：运行经营对数据协同的依赖持续增强。
- 完整文字稿：电力市场化改革使交易决策、价格研判、燃料采购、经营分析和风险控制更依赖跨主体数据与专业模型。
- 文字稿取舍说明：必留上屏：需求侧；仅讲解：燃料采购；仅追溯：无。
- 证据映射：需求侧→S006
- 上屏文字：
  需求侧：燃料采购需要跨主体数据与专业模型
- 证据：S006
- 视觉结构：需求增强与供给不足共同提出建设必要性。
"""
        )
        outline = strict_outline(
            {
                "page_id": "p03",
                "sequence": 3,
                "page_type": "content",
                "title": "行业协同需求与服务供给缺口",
                "argument_role": "necessity",
                "core_message": "运行经营对数据协同的依赖持续增强。",
                "source_refs": ["S006"],
                "prerequisite_pages": [],
                "main_claim_status": "confirmed",
            }
        )
        truth = source_truth(
            {
                "id": "S006",
                "type": "J",
                "status": "阶段判断",
                "statement": "燃料采购对跨主体数据与专业模型的需求不断增加。",
            }
        )

        codes = {issue.code for issue in audit_script_quality(script, outline, truth)}

        self.assertNotIn("PREMATURE_SCOPE_CLAIM", codes)

    def test_foundation_page_rejects_off_topic_quality_module(self) -> None:
        script = parse_script_markdown(
            """## 第4页：知识资产基础
- 页面类型：内容页
- 页面标题：知识资产基础
- 主判断：三类存量知识资产共同构成智能应用基础。
- 完整文字稿：现有学科、题目和行业数据共同构成知识资产基础，并可支撑后续学习、教学和分析应用。
- 文字稿取舍说明：本页只说明既有知识资产。
- 证据映射：资产规模→S001
- 上屏文字：
  **资产规模**
  - 已形成30个学科、约30万条题目和40年行业数据。
  **质量要求**
  - 原题不得开放，数据必须隔离，并防止模型幻觉和内容泄露。
- 证据：S001
- 边界：应用能力和治理机制留待后续页面。
- 视觉结构：三类资产共同支撑知识底座。
"""
        )
        outline = strict_outline(
            {
                "page_id": "p04",
                "sequence": 4,
                "page_type": "content",
                "title": "知识资产基础",
                "argument_role": "foundation",
                "page_job": "说明已经具备哪些知识资产",
                "business_question": "已经形成哪些知识资产",
                "main_message": "三类存量知识资产共同构成智能应用基础",
                "source_refs": ["S001"],
                "prerequisite_pages": [],
            }
        )
        truth = source_truth(
            {
                "id": "S001",
                "type": "F",
                "status": "原文陈述",
                "statement": "已形成学科、题目和行业数据资产。",
            }
        )

        issues = audit_script_quality(script, outline, truth)
        matching = [
            issue for issue in issues
            if issue.code == "OFF_TOPIC_CONSTRAINT_MODULE"
        ]

        self.assertEqual(1, len(matching))
        self.assertEqual("error", matching[0].severity)

    def test_safety_page_allows_quality_and_security_boundary_modules(self) -> None:
        script = parse_script_markdown(
            """## 第17页：数据安全与题源保护
- 页面类型：内容页
- 页面标题：数据安全与题源保护
- 主判断：分层防护保护题源和业务数据。
- 完整文字稿：本页说明题源保护、权限隔离、人工审核和审计处置如何共同形成数据安全机制。
- 文字稿取舍说明：本页聚焦安全治理。
- 证据映射：安全机制→S001
- 上屏文字：
  **安全边界**
  - 原题不得开放，通过权限隔离降低泄露风险。
  **质量要求**
  - 生成内容经人工审核后进入业务服务。
- 证据：S001
- 边界：具体产品选型留待实施阶段。
- 视觉结构：分层安全防护。
"""
        )
        outline = strict_outline(
            {
                "page_id": "p17",
                "sequence": 17,
                "page_type": "content",
                "title": "数据安全与题源保护",
                "argument_role": "assurance",
                "page_job": "说明如何保护题源和业务数据",
                "business_question": "如何形成数据安全防护",
                "main_message": "分层防护保护题源和业务数据",
                "source_refs": ["S001"],
                "prerequisite_pages": [],
            }
        )
        truth = source_truth(
            {
                "id": "S001",
                "type": "F",
                "status": "原文陈述",
                "statement": "题源和业务数据需要分层防护。",
            }
        )

        codes = {
            issue.code
            for issue in audit_script_quality(script, outline, truth)
        }

        self.assertNotIn("OFF_TOPIC_CONSTRAINT_MODULE", codes)

    def test_incidental_constraint_phrase_is_not_treated_as_a_module(self) -> None:
        script = parse_script_markdown(
            """## 第10页：学校学科智能分析
- 页面类型：内容页
- 页面标题：学校学科智能分析
- 主判断：多源数据形成可比较的学科规划建议。
- 完整文字稿：管理者选择目标年度、区域、专业和资源条件后，平台组织行业、招聘、培养和就业数据，形成可比较的情景方案。
- 文字稿取舍说明：本页聚焦规划分析流程。
- 证据映射：规划分析→S001
- 上屏文字：
  **情景分析**
  - 管理者选择目标年度、区域范围、专业和约束条件后开展情景比较。
  **规划建议**
  - 输出招生、培养和就业建议。
- 证据：S001
- 边界：重大调整由学校审议。
- 视觉结构：规划分析闭环。
"""
        )
        outline = strict_outline(
            {
                "page_id": "p10",
                "sequence": 10,
                "page_type": "content",
                "title": "学校学科智能分析",
                "argument_role": "solution",
                "page_job": "说明学校如何形成学科规划建议",
                "business_question": "如何利用多源数据优化学科规划",
                "main_message": "多源数据形成可比较的学科规划建议",
                "source_refs": ["S001"],
                "prerequisite_pages": [],
            }
        )
        truth = source_truth(
            {
                "id": "S001",
                "type": "F",
                "status": "原文陈述",
                "statement": "管理者可设置分析条件并比较情景。",
            }
        )

        codes = {
            issue.code
            for issue in audit_script_quality(script, outline, truth)
        }

        self.assertNotIn("OFF_TOPIC_CONSTRAINT_MODULE", codes)

    def test_proposed_source_cannot_be_upgraded_to_completed(self) -> None:
        script = parse_script_markdown(
            """## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：已经建成面向行业的公共能力。
- 完整文字稿：源材料对公共能力只给出拟建议定位，正式项目范围尚未确定。本稿却写成已经建成面向行业的公共能力，并把已完成建设作为上屏表述，属于把条件性建议升级为完成态结论。
- 文字稿取舍说明：本页只写本页业务问题主体；邻页议题不展开；建议与边界保持拟/待状态。
- 证据映射：支撑点1→S015
- 上屏文字：
  **公共能力**
  - 已完成建设。
- 证据：S015
- 边界：正式范围待确定。
- 视觉结构：定位图。
"""
        )
        outline = strict_outline(
            {
                "page_id": "p09",
                "sequence": 9,
                "page_type": "content",
                "title": "总体定位",
                "argument_role": "positioning",
                "source_refs": ["S015"],
                "prerequisite_pages": ["p07"],
                "main_claim_status": "proposed",
            }
        )
        truth = source_truth(
            {
                "id": "S015",
                "type": "B",
                "status": "拟建议",
                "statement": "初步考虑将本项建设定位为公共能力。",
            }
        )

        codes = {issue.code for issue in audit_script_quality(script, outline, truth)}

        self.assertIn("SOURCE_STATE_UPGRADED", codes)

    def test_adjacent_pages_with_same_main_message_are_rejected(self) -> None:
        duplicate = """## 第14页：业务体系
- 页面类型：内容页
- 页面标题：业务体系
- 主判断：统一数据和模型支撑报告生产与审核发布。
- 完整文字稿：业务体系页强调预测对象、流程与成果出口必须共用统一数据和模型底座，使报告生产与审核发布建立在同一输入之上。本页回答的是业务对象如何组织，而不是单独展开产品闭环细节。
- 文字稿取舍说明：本页只写本页业务问题主体；邻页议题不展开；建议与边界保持拟/待状态。
- 证据映射：支撑点1→S017
- 上屏文字：
  **业务对象**
  - 覆盖供需研判与成果生产。
  **运行关系**
  - 数据、模型与报告相互衔接。
- 证据：S017
- 边界：拟建议。
- 视觉结构：业务关系图。

## 第15页：成果闭环
- 页面类型：内容页
- 页面标题：成果闭环
- 主判断：统一数据和模型支撑报告生产与审核发布。
- 完整文字稿：成果闭环页本应推进生产、审校、发布、归档和复盘的运行机制，但本稿主判断仍重复写成统一数据和模型支撑报告生产与审核发布，没有形成新的业务问题推进。
- 文字稿取舍说明：本页只写本页业务问题主体；邻页议题不展开；建议与边界保持拟/待状态。
- 证据映射：支撑点1→S020
- 上屏文字：
  **成果生产**
  - 覆盖报告生产与审核发布。
  **运行关系**
  - 数据、模型与报告相互衔接。
- 证据：S020
- 边界：拟建议。
- 视觉结构：成果关系图。
"""
        issues = audit_script_quality(
            parse_script_markdown(duplicate),
            strict_outline(
                {
                    "page_id": "p14",
                    "sequence": 14,
                    "page_type": "content",
                    "title": "业务体系",
                    "argument_role": "solution",
                    "source_refs": ["S017"],
                    "prerequisite_pages": [],
                },
                {
                    "page_id": "p15",
                    "sequence": 15,
                    "page_type": "content",
                    "title": "成果闭环",
                    "argument_role": "solution",
                    "source_refs": ["S020"],
                    "prerequisite_pages": ["p14"],
                },
            ),
            source_truth(
                {"id": "S017", "type": "R", "status": "拟建议", "statement": "业务体系。"},
                {"id": "S020", "type": "R", "status": "拟建议", "statement": "成果产品。"},
            ),
        )

        self.assertIn(
            "ADJACENT_MAIN_MESSAGE_DUPLICATE",
            {issue.code for issue in issues},
        )

    def test_short_bridge_does_not_trigger_full_text_duplicate(self) -> None:
        self.assertLess(
            text_similarity("承接前页的数据治理基础", "数据治理提供可信输入"),
            0.72,
        )

    def test_path_visual_requires_order_signal(self) -> None:
        script = parse_script_markdown(
            """## 第12页：研究任务
- 页面类型：内容页
- 页面标题：研究任务
- 主判断：四项任务形成研究证据。
- 完整文字稿：本阶段研究通过资源摸底、问题量化、首期设计和原型验证四项任务形成立项前证据。四项任务应串成完整路径：先摸清资源和责任，再量化现状与缺口，再设计首期业务与技术方案，最后用原型验证形成测算与风险依据。本页不提前决定投资规模或采购方式。
- 文字稿取舍说明：本页只写本页业务问题主体；邻页议题不展开；建议与边界保持拟/待状态。
- 证据映射：支撑点1→S014
- 上屏文字：
  **资源摸底**
  - 形成资源清单和责任清单。
  **问题量化**
  - 形成现状基线和问题清单。
  **首期设计**
  - 形成首期业务与技术方案。
  **原型验证**
  - 形成验证结果和测算依据。
- 证据：S014
- 边界：不决定投资。
- 视觉结构：四步任务路径图。
"""
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p12",
                    "sequence": 12,
                    "page_type": "content",
                    "title": "研究任务",
                    "argument_role": "decision",
                    "source_refs": ["S014"],
                    "prerequisite_pages": [],
                }
            ),
            source_truth(
                {
                    "id": "S014",
                    "type": "U",
                    "status": "待确认",
                    "statement": "四项研究任务。",
                }
            ),
        )

        self.assertIn("PATH_ORDER_SIGNAL_MISSING", {issue.code for issue in issues})

    def test_path_visual_accepts_plain_numbered_modules(self) -> None:
        script = parse_script_markdown(
            """## 第12页：研究任务
- 页面类型：内容页
- 页面标题：研究任务
- 主判断：三项任务形成研究证据。
- 完整文字稿：本阶段依次完成资源摸底、问题量化和首期设计，形成可供后续验证的研究依据。
- 文字稿取舍说明：必留上屏：01｜资源摸底、02｜问题量化、03｜首期设计
- 上屏文字：
01｜资源摸底
  清单：形成资源与责任清单
02｜问题量化
  基线：形成现状与问题基线
03｜首期设计
  方案：形成首期业务与技术方案
- 证据映射：研究任务→S014
- 证据：S014
- 边界：不决定投资。
- 视觉结构：三项任务形成阶段推进路径。
"""
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p12",
                    "sequence": 12,
                    "page_type": "content",
                    "title": "研究任务",
                    "argument_role": "decision",
                    "source_refs": ["S014"],
                    "prerequisite_pages": [],
                }
            ),
            source_truth(
                {
                    "id": "S014",
                    "type": "U",
                    "status": "待确认",
                    "statement": "三项研究任务。",
                }
            ),
        )

        codes = {issue.code for issue in issues}
        self.assertNotIn("PATH_ORDER_SIGNAL_MISSING", codes)
        self.assertNotIn("ONSCREEN_RELATION_ISOMORPHISM", codes)

    def test_declared_count_must_match_modules(self) -> None:
        text = SCRIPT.replace(
            "初步定位为面向行业的公共能力。",
            "形成五类能力。",
        )
        issues = audit_script_quality(
            parse_script_markdown(text),
            strict_outline(
                {
                    "page_id": "p08",
                    "sequence": 8,
                    "page_type": "chapter",
                    "title": "第二章：定位、目标与研究边界",
                },
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "solution",
                    "source_refs": ["S015", "S026", "S059"],
                    "prerequisite_pages": [],
                },
            ),
            source_truth(
                {"id": "S015", "type": "R", "status": "拟建议", "statement": "能力。"},
                {"id": "S026", "type": "B", "status": "研究边界", "statement": "边界。"},
                {"id": "S059", "type": "B", "status": "研究边界", "statement": "边界。"},
            ),
        )

        self.assertIn("DECLARED_COUNT_MISMATCH", {issue.code for issue in issues})

    def test_approved_semantic_count_does_not_redefine_visible_group_count(self) -> None:
        script = parse_script_markdown(
            """## 第9页：能力架构
- 页面类型：内容页
- 页面标题：能力架构
- 主判断：五层能力与三类管理面共同支撑运营。
- 完整文字稿：五层能力与三类管理面共同支撑运营，正文展开可信连接、业务管理和贯穿保障的关系。
- 文字稿取舍说明：必留上屏：能力架构；仅讲解：细节；仅追溯：S015。
- 证据映射：能力架构→S015
- 上屏文字：
  **能力架构**
  - 可信连接支撑资源与服务。
  **贯穿保障**
  - 安全与运营要求贯穿能力体系。
  **业务管理**
  - 资源、交付和客户管理共同支撑运营。
- 证据：S015
- 视觉结构：能力与管理关系。
"""
        )
        outline = strict_outline(
            {
                "page_id": "p09",
                "sequence": 9,
                "page_type": "content",
                "title": "能力架构",
                "argument_role": "solution",
                "core_message": "五层能力与三类管理面共同支撑运营。",
                "source_refs": ["S015"],
                "prerequisite_pages": [],
            }
        )
        issues = audit_script_quality(
            script,
            outline,
            source_truth(
                {"id": "S015", "type": "F", "status": "已形成", "statement": "能力架构。"}
            ),
        )

        self.assertNotIn(
            "DECLARED_COUNT_MISMATCH", {issue.code for issue in issues}
        )

    def test_content_page_with_one_short_module_is_too_sparse(self) -> None:
        sparse = """## 第10页：能力框架
- 页面类型：内容页
- 页面标题：能力框架
- 主判断：形成能力。
- 完整文字稿：能力框架页需要说明业务、数据、模型、产品和运行机制如何共同支撑研判，而不是只留下一句形成能力。本稿文字稿虽给出方向，但上屏仅保留单一短模块，无法承载完整论证结构。
- 文字稿取舍说明：本页只写本页业务问题主体；邻页议题不展开；建议与边界保持拟/待状态。
- 证据映射：支撑点1→S017
- 上屏文字：
  **能力**
  - 提升研判。
- 证据：S017
- 边界：拟建议。
- 视觉结构：能力图。
"""
        outline = strict_outline(
            {
                "page_id": "p10",
                "sequence": 10,
                "page_type": "content",
                "title": "能力框架",
                "argument_role": "solution",
                "source_refs": ["S017"],
                "prerequisite_pages": [],
            }
        )
        outline["visible_judgment_mode"] = "required"
        issues = audit_script_quality(
            parse_script_markdown(sparse),
            outline,
            source_truth(
                {"id": "S017", "type": "R", "status": "拟建议", "statement": "能力。"}
            ),
        )

        codes = {issue.code for issue in issues}
        self.assertIn("CONTENT_PAGE_TOO_SPARSE", codes)

    def test_onscreen_layer_must_preserve_full_prose_semantics(self) -> None:
        script = parse_script_markdown(
            """## 第10页：数据断点
- 页面类型：内容页
- 页面标题：数据断点
- 主判断：数据接入与治理尚未贯通。
- 上屏结论：数据接入与治理尚未贯通
- 完整文字稿：供需预测依赖统一指标口径、稳定数据来源、版本留痕、授权边界和发布审核。当前数据分散在统计报表、业务系统、外部公开来源与合作单位，不同数据在统计范围、时间粒度、更新周期和历史修订方式上存在差异。高频负荷、气象、市场交易和新型主体数据仍需建立稳定接入渠道。数据不可控会削弱模型可信，进一步放大发布风险，因此数据治理是端到端研判能力的前置条件。
- 文字稿取舍说明：只讨论数据断点；模型细节和建设安排留后页。
- 证据映射：数据断点→S017
- 上屏文字：
  **组织保障**
  - 建立专项工作组并完善会议安排。
  **实施节奏**
  - 分阶段推进培训、宣传、考核和日常协调。
- 证据：S017
- 边界：不提前给出建设方案。
- 视觉结构：判断证据支撑。
"""
        )
        outline = strict_outline(
            {
                "page_id": "p10",
                "sequence": 10,
                "page_type": "content",
                "title": "数据断点",
                "argument_role": "diagnosis",
                "source_refs": ["S017"],
                "prerequisite_pages": [],
                "main_message": "数据接入与治理尚未贯通。",
                "onscreen_judgment": "数据接入与治理尚未贯通",
            }
        )
        outline["visible_judgment_mode"] = "required"
        issues = audit_script_quality(
            script,
            outline,
            source_truth(
                {
                    "id": "S017",
                    "type": "F",
                    "status": "现状",
                    "statement": "数据接入与治理尚未贯通。",
                }
            ),
        )

        self.assertIn(
            "ONSCREEN_SEMANTIC_COVERAGE_LOW",
            {issue.code for issue in issues},
        )

    def test_content_page_requires_full_prose_before_onscreen(self) -> None:
        missing = """## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：初步定位为面向行业的公共能力。
- 上屏文字：
  **行业公共能力**
  - 服务行业研判。
  **专业系统边界**
  - 保留专业职责边界。
- 证据：S015
- 边界：正式范围待后续确定。
- 视觉结构：公共能力定位与职责边界图。
"""
        issues = audit_script_quality(
            parse_script_markdown(missing),
            strict_outline(
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "positioning",
                    "source_refs": ["S015"],
                    "prerequisite_pages": [],
                    "main_claim_status": "proposed",
                }
            ),
            source_truth(
                {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"}
            ),
        )
        self.assertIn("CONTENT_PROSE_MISSING", {issue.code for issue in issues})

    def test_full_prose_must_precede_onscreen_field(self) -> None:
        wrong_order = """## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：初步定位为面向行业的公共能力。
- 文字稿取舍说明：本页只写本页业务问题主体；邻页议题不展开；建议与边界保持拟/待状态。
- 证据映射：支撑点1→S015
- 上屏文字：
  **行业公共能力**
  - 服务行业研判。
  **专业系统边界**
  - 保留专业职责边界。
- 完整文字稿：在现状与能力断点已经建立后，本页将建设方向初步定位为面向行业的公共能力，同时保留专业系统边界。该定位用于明确研究方向，不等于正式项目范围已经确定；正式判断仍需由数据、模型、业务分析与专家会商共同形成，不能把拟建议写成已审定结论。
- 证据：S015
- 边界：正式范围待后续确定。
- 视觉结构：公共能力定位与职责边界图。
"""
        issues = audit_script_quality(
            parse_script_markdown(wrong_order),
            strict_outline(
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "positioning",
                    "source_refs": ["S015"],
                    "prerequisite_pages": [],
                    "main_claim_status": "proposed",
                }
            ),
            source_truth(
                {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"}
            ),
        )
        self.assertIn("CONTENT_PROSE_AFTER_ONSCREEN", {issue.code for issue in issues})

    def test_analytical_meta_narration_in_prose_is_blocked(self) -> None:
        script = parse_script_markdown(
            """# 第9页脚本

## 第9页：总体定位

- 页面类型：内容页
- 页面标题：总体定位
- 主判断：拟初步定位为面向行业的公共能力。
- 完整文字稿：讨论能力建设，首先需要确认拟建对象的公共能力定位，而不是直接讨论完整方案。从现有材料看，本页只确认研究方向属性，本页不评价正式范围是否已定。
- 文字稿取舍说明：不展开五类能力与首期场景；定位保持拟建议。
- 证据映射：公共能力定位→S015
- 上屏文字：

  **行业公共能力**

  - 拟定位为面向行业的公共能力。
  - 该定位不等于正式项目范围已定。

  **职责边界**

  - 不替代专业运行系统。

- 证据：S015
- 边界：正式范围待后续确定。
- 视觉结构：公共能力定位与职责边界图。
"""
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "positioning",
                    "source_refs": ["S015"],
                    "prerequisite_pages": [],
                    "main_claim_status": "proposed",
                }
            ),
            source_truth(
                {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"}
            ),
        )
        self.assertIn(
            "CONTENT_PROSE_ANALYTICAL_VOICE",
            {issue.code for issue in issues},
        )

    def test_issue_helper_accepts_warning_severity(self) -> None:
        page = ScriptPage(
            page_id="p01",
            sequence=1,
            heading="示例",
            page_type="content",
            title="示例",
            main_message="判断",
            full_prose="x" * 100,
            selection_notes="取舍说明足够长",
            evidence_map="点→S001",
            evidence_map_refs=("S001",),
            source_refs=("S001",),
            boundary_source_refs=(),
            boundary="",
            visual_structure="业务关系图。",
            onscreen_text="**模块A**\n- a\n**模块B**\n- b",
            module_titles=("模块A", "模块B"),
            speaker_notes="建设方向应与专业系统的职责分工同时明确，避免能力边界交叉。",
        )
        issue = _issue(
            "VISUAL_STRUCTURE_TOO_THIN",
            page,
            "thin",
            "expand",
            severity="warning",
        )
        self.assertEqual("warning", issue.severity)

    def test_visual_structure_style_only_is_error(self) -> None:
        prose = "建设方向定位为面向行业的公共能力，明确研究对象与服务边界。" * 4
        script = parse_script_markdown(
            f"""## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：定位为行业公共能力。
- 完整文字稿：{prose}
- 文字稿取舍说明：不展开邻页。
- 证据映射：定位→S015
- 上屏文字：
  **行业公共能力**
  - 服务行业研判。
  **专业系统边界**
  - 保留职责边界。
- 证据：S015
- 边界：范围待定。
- 视觉结构：简洁现代科技感。
"""
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "positioning",
                    "source_refs": ["S015"],
                    "prerequisite_pages": [],
                }
            ),
            source_truth(
                {
                    "id": "S015",
                    "type": "J",
                    "status": "拟建议",
                    "statement": "公共能力定位。",
                }
            ),
        )
        style_issues = [
            issue for issue in issues if issue.code == "VISUAL_STRUCTURE_STYLE_ONLY"
        ]
        self.assertTrue(style_issues)
        self.assertEqual("error", style_issues[0].severity)

    def test_visual_structure_too_thin_is_warning(self) -> None:
        prose = "建设方向定位为面向行业的公共能力，明确研究对象与服务边界。" * 4
        script = parse_script_markdown(
            f"""## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：定位为行业公共能力。
- 完整文字稿：{prose}
- 文字稿取舍说明：不展开邻页。
- 证据映射：定位→S015
- 上屏文字：
  **行业公共能力**
  - 服务行业研判。
  **专业系统边界**
  - 保留职责边界。
- 证据：S015
- 边界：范围待定。
- 视觉结构：业务关系图。
"""
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "positioning",
                    "source_refs": ["S015"],
                    "prerequisite_pages": [],
                }
            ),
            source_truth(
                {
                    "id": "S015",
                    "type": "J",
                    "status": "拟建议",
                    "statement": "公共能力定位。",
                }
            ),
        )
        thin_issues = [
            issue for issue in issues if issue.code == "VISUAL_STRUCTURE_TOO_THIN"
        ]
        self.assertTrue(thin_issues)
        self.assertEqual("warning", thin_issues[0].severity)

    def test_onscreen_anti_pattern_warns_on_card_wall_phrase(self) -> None:
        prose = "建设方向定位为面向行业的公共能力，明确研究对象与服务边界。" * 4
        script = parse_script_markdown(
            f"""## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：定位为行业公共能力。
- 完整文字稿：{prose}
- 文字稿取舍说明：不展开邻页。
- 证据映射：定位→S015
- 上屏文字：
  **行业公共能力**
  - 用六宫格展示能力项。
  **专业系统边界**
  - 保留职责边界。
- 证据：S015
- 边界：范围待定。
- 视觉结构：判断证据支撑——中央判断，两侧证据托举。
"""
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "positioning",
                    "source_refs": ["S015"],
                    "prerequisite_pages": [],
                }
            ),
            source_truth(
                {
                    "id": "S015",
                    "type": "J",
                    "status": "拟建议",
                    "statement": "公共能力定位。",
                }
            ),
        )
        anti = [issue for issue in issues if issue.code == "ONSCREEN_ANTI_PATTERN"]
        self.assertTrue(anti)
        self.assertEqual("warning", anti[0].severity)

    def test_onscreen_relation_meta_labels_are_errors(self) -> None:
        prose = "统一底座使三类应用共享知识标准，同时保留各自权限与解释口径。" * 3
        script = parse_script_markdown(
            f"""## 第6页：平台定位
- 页面类型：内容页
- 页面标题：平台定位
- 主判断：平台以统一知识治理为底座连接三类应用。
- 完整文字稿：{prose}
- 文字稿取舍说明：不展开邻页。
- 证据映射：底座→S009
- 上屏文字：
  **01｜数据资产层**
  - 统一接入数据资产。
  **02｜三类应用层**
  - 连接三类业务。
  - 业务含义：统一底座使三类应用共享知识标准。
  - 纵向关系：数据资产 → 三类应用。
- 证据：S009
- 边界：不替代既有系统。
- 视觉结构：分层剖面——自下而上呈现支撑关系。
"""
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p06",
                    "page_type": "content",
                    "title": "平台定位",
                    "main_message": "平台以统一知识治理为底座连接三类应用。",
                    "source_refs": ["S009"],
                }
            ),
            source_truth(
                {
                    "id": "S009",
                    "type": "F",
                    "status": "已确认",
                    "statement": "平台范围包括知识资产治理与三类应用。",
                }
            ),
        )
        meta = [
            issue for issue in issues if issue.code == "ONSCREEN_RELATION_META_LABEL"
        ]
        self.assertTrue(meta)
        self.assertEqual("error", meta[0].severity)
        self.assertIn("业务含义", meta[0].evidence)
        self.assertIn("纵向关系", meta[0].evidence)

    def test_stage01_matrix_recipe_is_blocked(self) -> None:
        prose = "场景筛选需要按业务必要与数据可得综合权衡后分期安排。" * 4
        script = parse_script_markdown(
            f"""## 第19页：场景布局
- 页面类型：内容页
- 页面标题：场景布局
- 主判断：首期双场景是综合权衡后的阶段安排。
- 完整文字稿：{prose}
- 文字稿取舍说明：不展开技术方案。
- 证据映射：场景范围→S022
- 上屏文字：
  **首期取舍**
  - 两个场景共同验证能力。
  **后续准入**
  - 条件成熟后再纳入高频场景。
- 证据：S022
- 边界：排序需摸底后校核。
- 视觉结构：矩阵筛选——场景与准入条件对照。
"""
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p19",
                    "sequence": 19,
                    "page_type": "content",
                    "title": "场景布局",
                    "argument_role": "scope",
                    "source_refs": ["S022"],
                    "prerequisite_pages": [],
                }
            ),
            source_truth(
                {
                    "id": "S022",
                    "type": "J",
                    "status": "拟建议",
                    "statement": "首期双场景。",
                }
            ),
        )
        mismatch = [
            issue
            for issue in issues
            if issue.code == "VISUAL_STRUCTURE_LAYOUT_RECIPE"
        ]
        self.assertTrue(mismatch)
        self.assertEqual("error", mismatch[0].severity)


class SpeakerNotesContractTests(unittest.TestCase):
    def test_extracts_bracket_speaker_notes(self) -> None:
        body = (
            "- 讲解提示：短提醒。\n\n"
            "【演讲者备注】\n\n"
            "建设方向与职责分工需要同步明确。\n"
        )
        self.assertIn("建设方向", extract_speaker_notes(body))

    def test_rejects_defensive_boundary_coaching(self) -> None:
        script = parse_script_markdown(
            SCRIPT.replace(
                "先说定位再说边界。",
                "反复区分方向和首期，避免听众把完整蓝图听成一期承诺。",
            )
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p08",
                    "sequence": 8,
                    "page_type": "chapter",
                    "title": "第二章：定位、目标与研究边界",
                },
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "positioning",
                    "page_job": "说明总体定位",
                    "business_question": "拟建什么能力",
                    "main_message": "定位为行业公共能力",
                    "source_refs": ["S015", "S026", "S059"],
                    "prerequisite_pages": [],
                },
            ),
            source_truth(
                {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"},
                {"id": "S026", "type": "B", "status": "边界", "statement": "专业边界。"},
                {"id": "S059", "type": "B", "status": "边界", "statement": "正式范围待定。"},
            ),
        )

        self.assertIn(
            "NARRATION_BOUNDARY_COACHING",
            {issue.code for issue in issues},
        )

    def test_rejects_internal_boundary_repeated_in_ordinary_speaker_notes(self) -> None:
        script = parse_script_markdown(
            SCRIPT.replace(
                "建设定位是面向行业的公共能力，服务履职与行业共用；同时明确与专业系统的职责分工，不替代调度、出清和企业计划。正式范围仍需结合资源摸底和原型验证进一步确定，当前阶段不提前锁定实施参数。",
                "建设定位是面向行业的公共能力，服务履职与行业共用。正式范围待后续确定，当前阶段不提前锁定实施参数。相关能力建设由业务体系持续支撑。",
            )
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p08",
                    "sequence": 8,
                    "page_type": "chapter",
                    "title": "第二章：定位、目标与研究边界",
                },
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "能力定位",
                    "argument_role": "solution",
                    "page_job": "说明能力组成",
                    "business_question": "形成哪些业务能力",
                    "main_message": "形成行业公共预测能力",
                    "source_refs": ["S015", "S026", "S059"],
                    "prerequisite_pages": [],
                },
            ),
            source_truth(
                {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"},
                {"id": "S026", "type": "B", "status": "边界", "statement": "专业边界。"},
                {"id": "S059", "type": "B", "status": "边界", "statement": "正式范围待定。"},
            ),
        )

        self.assertIn(
            "NARRATION_INTERNAL_BOUNDARY_LEAK",
            {issue.code for issue in issues},
        )

    def test_scope_page_may_state_substantive_scope_without_defensive_coaching(self) -> None:
        script = parse_script_markdown(
            SCRIPT.replace(
                "先说定位再说边界。",
                "先说明首期业务，再说明数据和模型安排。",
            ).replace(
                "建设定位是面向行业的公共能力，服务履职与行业共用；同时明确与专业系统的职责分工，不替代调度、出清和企业计划。正式范围仍需结合资源摸底和原型验证进一步确定，当前阶段不提前锁定实施参数。",
                "首期聚焦月度季度分析和年度报告自动化，数据采用现有统计与稳定来源，模型采用可解释基线和滚动回测，形成能够验证的业务闭环。",
            )
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p08",
                    "sequence": 8,
                    "page_type": "chapter",
                    "title": "第二章：定位、目标与研究边界",
                },
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "首期范围",
                    "argument_role": "scope",
                    "page_job": "明确首期范围",
                    "business_question": "首期聚焦哪些业务",
                    "main_message": "首期聚焦月季分析和年报自动化",
                    "source_refs": ["S015", "S026", "S059"],
                    "prerequisite_pages": [],
                },
            ),
            source_truth(
                {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"},
                {"id": "S026", "type": "B", "status": "边界", "statement": "专业边界。"},
                {"id": "S059", "type": "B", "status": "边界", "statement": "正式范围待定。"},
            ),
        )

        narration_codes = {
            "NARRATION_BOUNDARY_COACHING",
            "NARRATION_INTERNAL_BOUNDARY_LEAK",
        }
        self.assertFalse(narration_codes & {issue.code for issue in issues})

    def test_rejects_slide_meta_speech(self) -> None:
        prose = "建设方向定位为面向行业的公共能力，明确研究对象与服务边界。" * 4
        script = parse_script_markdown(
            f"""## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：初步定位为面向行业的公共能力。
- 完整文字稿：{prose}
- 文字稿取舍说明：不展开邻页细节。
- 证据映射：定位→S015
- 上屏文字：
  **行业公共能力**
  - 服务行业研判。
  **专业系统边界**
  - 保留专业边界。
- 证据：S015
- 边界：正式范围待定。
- 视觉结构：双侧协同——左右对照。
- 讲解提示：短提醒。

【演讲者备注】

各位同事，这一页我们先说定位，下一页再谈范围。
"""
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "positioning",
                    "source_refs": ["S015"],
                    "prerequisite_pages": [],
                }
            ),
            source_truth(
                {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"}
            ),
        )
        codes = {issue.code for issue in issues}
        self.assertIn("SPEAKER_NOTES_SLIDE_META", codes)
        self.assertIn("SPEAKER_NOTES_HOST_META", codes)

    def test_requires_speaker_notes_on_content_pages(self) -> None:
        prose = "建设方向定位为面向行业的公共能力，明确研究对象与服务边界。" * 4
        script = parse_script_markdown(
            f"""## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：初步定位为面向行业的公共能力。
- 完整文字稿：{prose}
- 文字稿取舍说明：不展开邻页细节。
- 证据映射：定位→S015
- 上屏文字：
  **行业公共能力**
  - 服务行业研判。
  **专业系统边界**
  - 保留专业边界。
- 证据：S015
- 边界：正式范围待定。
- 视觉结构：双侧协同——左右对照。
"""
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "positioning",
                    "source_refs": ["S015"],
                    "prerequisite_pages": [],
                }
            ),
            source_truth(
                {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"}
            ),
        )
        self.assertIn(
            "CONTENT_SPEAKER_NOTES_MISSING",
            {issue.code for issue in issues},
        )


def _judgment_page(**overrides: object) -> ScriptPage:
    base = dict(
        page_id="p15",
        sequence=15,
        heading="知识与数据底座",
        page_type="content",
        title="知识与数据底座",
        main_message="通用、专业和行业知识先归一为标准知识对象，再由分层数据服务支撑应用",
        full_prose="从业务关系看，三类知识来源先归一为统一知识对象。" * 4,
        selection_notes="必留上屏：三类来源；仅讲解：细节；仅追溯：S001",
        evidence_map="点→S001",
        evidence_map_refs=("S001",),
        source_refs=("S001",),
        boundary_source_refs=(),
        boundary="",
        visual_structure="",
        onscreen_text="**01｜三类知识来源**\n- a\n**02｜统一知识对象**\n- b",
        module_titles=("01｜三类知识来源", "02｜统一知识对象"),
        speaker_notes="围绕判断展开。",
        onscreen_judgment="通用、专业和行业知识先归一为标准知识对象，再由分层数据服务支撑应用",
    )
    base.update(overrides)
    return ScriptPage(**base)  # type: ignore[arg-type]


class SpeakerNotesParagraphTests(unittest.TestCase):
    def test_rejects_long_unsegmented_speaker_notes(self) -> None:
        notes = (
            "平台先统一识别客户需求和可用资源，再通过审核验证形成明确的产品规格。"
            "订单生效后，授权、交付、计量和结算按照同一业务对象连续衔接。"
            "运营结果最终回流到产品优化与合作评估，形成完整闭环。"
        ) * 2
        codes = {
            issue.code for issue in _prose_issues(_judgment_page(speaker_notes=notes))
        }
        self.assertIn("SPEAKER_NOTES_UNSEGMENTED", codes)

    def test_allows_formal_segmented_speaker_notes(self) -> None:
        notes = (
            "平台先统一识别客户需求和可用资源，再通过审核验证形成明确的产品规格。\n\n"
            "订单生效后，授权、交付、计量和结算按照同一业务对象连续衔接。"
            "运营结果最终回流到产品优化与合作评估，形成完整闭环。"
        )
        codes = {
            issue.code for issue in _prose_issues(_judgment_page(speaker_notes=notes))
        }
        self.assertNotIn("SPEAKER_NOTES_UNSEGMENTED", codes)

    def test_rejects_paragraph_break_after_semicolon(self) -> None:
        notes = (
            "平台先统一识别客户需求和可用资源；\n\n"
            "再通过审核验证形成产品规格，订单生效后连续衔接授权、交付和结算。"
        )
        codes = {
            issue.code for issue in _prose_issues(_judgment_page(speaker_notes=notes))
        }
        self.assertIn("SPEAKER_NOTES_INCOMPLETE_PARAGRAPH_BOUNDARY", codes)


class VisualStructureJudgmentAccuracyTests(unittest.TestCase):
    def test_flags_fixed_layout_recipe_in_stage01_visual_handoff(self) -> None:
        page = _judgment_page(
            visual_structure=(
                "五类服务共同形成标准化服务关系。主视觉以五条横向泳道自上而下排列，"
                "右侧设置统一收束条。"
            ),
        )
        issues = _visual_structure_judgment_issues(page)
        matches = [
            issue for issue in issues if issue.code == "VISUAL_STRUCTURE_LAYOUT_RECIPE"
        ]
        self.assertEqual(1, len(matches))
        self.assertEqual("error", matches[0].severity)

    def test_allows_semantic_handoff_without_page_geometry(self) -> None:
        page = _judgment_page(
            visual_structure=(
                "主关系为三类知识来源支撑统一知识对象，并由分层数据服务形成应用结果；"
                "语义焦点是统一知识对象，来源文字归属于输入对象，服务文字归属于支撑关系；"
                "不预设具体载体、行列或位置。"
            ),
        )
        codes = {issue.code for issue in _visual_structure_judgment_issues(page)}
        self.assertNotIn("VISUAL_STRUCTURE_LAYOUT_RECIPE", codes)
        self.assertNotIn("VISUAL_STRUCTURE_MULTIPLE_PRIMARY_NARRATIVES", codes)

    def test_flags_second_independent_visual_narrative(self) -> None:
        page = _judgment_page(
            visual_structure=(
                "主关系为来源支撑统一知识对象；另一套总结链独立于主关系形成结果说明。"
            ),
        )
        codes = {issue.code for issue in _visual_structure_judgment_issues(page)}
        self.assertIn("VISUAL_STRUCTURE_MULTIPLE_PRIMARY_NARRATIVES", codes)

    def test_flags_visible_result_missing_from_locked_onscreen_text(self) -> None:
        page = _judgment_page(
            visual_structure="页面底部单独收束“合作完善方向”的结论条。",
        )
        codes = {issue.code for issue in _visual_structure_judgment_issues(page)}
        self.assertIn("VISUAL_STRUCTURE_UNLOCKED_VISIBLE_TEXT", codes)

    def test_allows_visible_result_locked_once(self) -> None:
        page = _judgment_page(
            onscreen_text="合作完善方向：共性能力仍需完善。",
            visual_structure="页面底部单独收束“合作完善方向”的结论条。",
        )
        codes = {issue.code for issue in _visual_structure_judgment_issues(page)}
        self.assertNotIn("VISUAL_STRUCTURE_UNLOCKED_VISIBLE_TEXT", codes)

    def test_compound_group_heading_is_a_blocking_presentation_issue(self) -> None:
        page = _judgment_page(
            onscreen_text="合作原则与合作方式\n原则说明\n方式说明",
            module_titles=("合作原则与合作方式",),
            top_level_module_titles=("合作原则与合作方式",),
        )
        issues = [
            issue
            for issue in _presentation_issues(page)
            if issue.code == "ONSCREEN_COMPOUND_GROUP_HEADING"
        ]
        self.assertEqual(1, len(issues))
        self.assertEqual("error", issues[0].severity)

    def test_flags_crosscut_module_peer_staged_on_path(self) -> None:
        page = _judgment_page(
            visual_structure=(
                "贯穿主链——订单创建 → 履约交付 → 结算确认 → 审计追踪；"
                "审计追踪贯穿主链；一级模块与上屏文字一致。"
            ),
        )
        codes = {issue.code for issue in _visual_structure_judgment_issues(page)}
        self.assertIn("VISUAL_STRUCTURE_CROSSCUT_AS_PEER", codes)

    def test_allows_crosscut_as_second_clause_not_on_arrow_chain(self) -> None:
        page = _judgment_page(
            visual_structure=(
                "贯穿主链——订单创建 → 履约交付 → 结算确认；"
                "审计追踪贯穿主链。"
            ),
        )
        codes = {issue.code for issue in _visual_structure_judgment_issues(page)}
        self.assertNotIn("VISUAL_STRUCTURE_CROSSCUT_AS_PEER", codes)

    def test_flags_horizontal_governance_as_stacked_layer(self) -> None:
        page = _judgment_page(
            main_message="供应链从采购到交付持续受质量追溯约束",
            full_prose="从业务关系看，采购、加工和交付逐层衔接，质量追溯贯穿每一层。" * 2,
            visual_structure=(
                "分层剖面——自下而上依次呈现采购层、加工层、交付层、质量追溯；"
                "一级模块与上屏文字一致。"
            ),
        )
        codes = {issue.code for issue in _visual_structure_judgment_issues(page)}
        self.assertIn("VISUAL_STRUCTURE_CROSSCUT_AS_PEER", codes)

    def test_does_not_infer_a_gateway_visual_center(self) -> None:
        page = _judgment_page(
            main_message="统一网关连接身份组织、知识题库、学习教学和分析报告接口",
            onscreen_judgment="统一网关连接身份组织、知识题库、学习教学和分析报告接口",
            visual_structure=(
                "双侧协同——以身份组织接口为视觉中心，其余模块按支撑关系连接；"
                "一级模块与上屏文字一致。"
            ),
        )
        codes = {issue.code for issue in _visual_structure_judgment_issues(page)}
        self.assertNotIn("VISUAL_CENTER_JUDGMENT_MISMATCH", codes)

    def test_does_not_infer_a_depth_defense_visual_primitive(self) -> None:
        page = _judgment_page(
            main_message="安全体系以五层纵深防护构成内容到审计的防护链",
            onscreen_judgment="安全体系以五层纵深防护构成内容到审计的防护链",
            visual_structure=(
                "受控边界——由外向内设置内容输出控制、风险行为识别、身份与网络隔离、"
                "数据保护、审计与应急，中心为受控业务输出；一级模块与上屏文字一致。"
            ),
        )
        codes = {issue.code for issue in _visual_structure_judgment_issues(page)}
        self.assertNotIn("VISUAL_STRUCTURE_PRIMITIVE_MISMATCH", codes)

    def test_flags_mechanism_peer_lanes(self) -> None:
        page = _judgment_page(
            main_message="订单履约链与风险复核队列采用资源隔离和差异化降级策略",
            visual_structure=(
                "主体泳道——横向并列订单履约链、风险复核队列、资源隔离、弹性降级，"
                "底部设置统一支撑关系；一级模块与上屏文字一致。"
            ),
        )
        codes = {issue.code for issue in _visual_structure_judgment_issues(page)}
        self.assertIn("VISUAL_STRUCTURE_MECHANISM_AS_LANE", codes)

def test_parser_reads_onscreen_expression_form() -> None:
    page = parse_script_markdown(
        """## 第1页：测试

- 页面类型：内容页
- 上屏表达结构：framework_4

### 上屏文字

权属确认
授权管理
流转审计
责任闭环
"""
    ).pages[0]
    assert page.onscreen_expression_form == "framework_4"


if __name__ == "__main__":
    unittest.main()
