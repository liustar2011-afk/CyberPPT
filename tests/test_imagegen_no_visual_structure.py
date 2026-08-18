"""Compiled prompts must not inject page-level visual-structure backend fields."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from cyberppt.script_quality_contract import parse_script_markdown
from scripts.imagegen_pipeline.deliverable_prompt import PageBlock, render_prompt
from scripts.imagegen_pipeline.imagegen_handoff import (
    VISUAL_INTENT_TEMPLATES,
    _page_visual_contexts,
    _page_visual_intent_overrides,
    build_page_prompt,
    build_page_visual_intent,
    content_lock_text,
    select_page_visual_intent_type,
)
from scripts.imagegen_pipeline.style_library import write_project_style_lock


SCRIPT_WITH_VISUAL_STRUCTURE = """## 第9页：总体定位

- 页面类型：内容页
- 页面标题：总体定位
- 主判断：初步定位为面向行业的公共能力。
- 完整文字稿：建设方向初步定位为面向行业的公共能力。
- 文字稿取舍说明：不展开细节。
- 证据映射：公共能力定位→S015
- 上屏结论：初步定位为面向行业的公共能力。
- 上屏文字：

  初步定位为面向行业的公共能力。

  **行业公共能力**

  - 服务行业研判。

- 证据：S015
- 边界：正式范围待后续确定。
- 视觉结构：判断证据支撑——中央公共能力定位，两侧职责边界托举。
- 讲解提示：先说定位再说边界。
"""


def _visual_intent_page(
    main_message: str,
    mission: str,
    modules: str,
):
    page = parse_script_markdown(
        f"""## 第19页：测试页

- 页面类型：内容页
- 页面标题：测试页
- 主判断：{main_message}
- 上屏文字：

{modules}
"""
    ).pages[0]
    return page, mission


class ImageGenNoVisualStructureTests(unittest.TestCase):
    def test_visual_intent_collision_rules_prevent_generic_word_hijacking(self) -> None:
        cases = [
            (
                "目标能力由哪些部分组成",
                "数据、模型、产品、平台和机制共同形成业务能力",
                "业务应用层",
                {"argument_role": "solution", "page_job": "说明能力组成"},
                "capability_relationship",
            ),
            (
                "首期业务主闭环如何运行",
                "首期形成输入、处理、输出、反馈闭环",
                "首期业务",
                {"argument_role": "scope", "page_job": "说明业务闭环"},
                "closed_loop",
            ),
            (
                "首期聚焦哪些业务、数据、模型与产品",
                "首期范围由业务价值和成熟度共同确定",
                "能力范围",
                {"argument_role": "scope", "page_job": "明确首期范围"},
                "decision_admission",
            ),
            (
                "建设按什么节奏推进",
                "先开展试点，再拓展更多业务场景",
                "场景拓展",
                {"argument_role": "implementation", "page_job": "说明分期推进"},
                "phase",
            ),
            (
                "供需预测业务需要覆盖什么",
                "覆盖供给、需求、平衡和风险等预测对象",
                "需求预测",
                {"argument_role": "solution", "page_job": "说明业务覆盖维度"},
                "judgment_evidence",
            ),
        ]
        for mission, message, module_title, context, expected in cases:
            page, _ = _visual_intent_page(
                message,
                mission,
                f"  **{module_title}**\n  - 支撑内容。",
            )
            self.assertEqual(
                expected,
                select_page_visual_intent_type(page, mission, context=context),
            )

    def test_visual_intent_explicit_type_wins_and_is_visible_in_prompt(self) -> None:
        page, mission = _visual_intent_page(
            "首期形成输入、处理、输出、反馈闭环",
            "首期业务主闭环如何运行",
            "  **首期业务**\n  - 支撑内容。",
        )
        intent = build_page_visual_intent(
            page,
            mission,
            override={"visual_intent_type": "phase"},
        )
        self.assertIn("- Selected visual intent type: phase", intent)
        self.assertIn("阶段递进", intent)

    def test_page_visual_context_loader_preserves_routing_fields(self) -> None:
        with TemporaryDirectory() as directory:
            project = Path(directory)
            outline = project / "workbench/stages/01-analysis/outline.json"
            outline.parent.mkdir(parents=True)
            outline.write_text(
                json.dumps(
                    {
                        "pages": [
                            {
                                "page_id": "p10",
                                "argument_role": "solution",
                                "page_job": "说明能力组成",
                                "business_question": "目标能力由哪些部分组成",
                                "visual_intent_type": "capability_relationship",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            contexts = _page_visual_contexts(project)
        self.assertEqual(
            {
                "argument_role": "solution",
                "page_job": "说明能力组成",
                "business_question": "目标能力由哪些部分组成",
                "visual_intent_type": "capability_relationship",
            },
            contexts["p10"],
        )

    def test_visual_intent_classifies_decision_and_admission(self) -> None:
        page, mission = _visual_intent_page(
            "首期场景由成熟度条件共同决定",
            "首期场景如何选定、后续场景如何分期推进",
            """  **筛选依据｜五维共同决定**
  - 按成熟度选择。
  **首期取舍｜双场景**
  - 首期进入。
  **后续准入｜条件成熟再纳入**
  - 后续验证。""",
        )
        intent = build_page_visual_intent(page, mission)
        self.assertIn("[Prompt context] Page-specific visual intent", intent)
        self.assertIn("明确准入门槛", intent)
        self.assertIn("把它当作决策结构，而不是实施流程", intent)
        self.assertIn("五个等权依据卡", intent)

    def test_visual_intent_classifies_causal_closed_loop_and_phase(self) -> None:
        cases = [
            ("为什么现有研判不足", "问题、原因与影响共同形成能力需求", "由因到果"),
            ("业务如何形成闭环", "输入、处理、输出、反馈与复盘", "闭环"),
            ("能力如何分期推进", "当前、近期和中长期分阶段建设", "阶段递进"),
        ]
        for mission, message, marker in cases:
            page, _ = _visual_intent_page(
                message,
                mission,
                "  **支撑模块**\n  - 支撑内容。",
            )
            self.assertIn(marker, build_page_visual_intent(page, mission))

    def test_visual_intent_classifies_comparison_scenario_and_capability(self) -> None:
        cases = [
            (
                "不同建设方案有何差异",
                "通过同一维度比较识别差异与优先级",
                "差异和主次",
            ),
            (
                "重点场景如何应用并具备什么条件",
                "场景连接业务价值、当前阶段和推进条件",
                "应用方向、当前阶段与进入条件",
            ),
            (
                "各项能力如何协同支撑业务价值",
                "数据、模型、产品和机制能力共同支撑业务判断",
                "忠实呈现合同声明的对象、能力及其对应或支撑关系",
            ),
        ]
        for mission, message, marker in cases:
            page, _ = _visual_intent_page(
                message,
                mission,
                "  **支撑模块**\n  - 支撑内容。",
            )
            self.assertIn(marker, build_page_visual_intent(page, mission))

    def test_visual_intent_classifies_multiple_work_foundations(self) -> None:
        page, mission = _visual_intent_page(
            "中电联已经形成覆盖多类工作的持续性工作基础",
            "中电联已经形成哪些现实工作基础",
            """  **统计数据｜长期积累**
  - 形成行业统计基础。
  **形势研判｜持续开展**
  - 支撑模型需求提出。
  **报告发布｜稳定输出**
  - 形成公开成果。
  **行业协调｜连接主体**
  - 支撑协同研判。""",
        )
        intent = build_page_visual_intent(page, mission)
        self.assertIn("多项现实基础共同支撑", intent)
        self.assertIn("主导的综合视觉载体", intent)
        self.assertIn("一项基础一张图", intent)
        self.assertIn("一张泛化办公", intent)
        self.assertNotIn("由因到果", intent)

    def test_every_visual_intent_type_gets_shared_text_integration_guardrail(self) -> None:
        page, mission = _visual_intent_page(
            "测试主判断",
            "测试页面关系",
            "  **测试模块**\n  - 测试内容。",
        )
        for intent_type in VISUAL_INTENT_TEMPLATES:
            intent = build_page_visual_intent(
                page,
                mission,
                {"visual_intent_type": intent_type},
            )
            self.assertIn("全部必上屏文字以冷静的场内面板", intent)
            self.assertIn("避免独立通高文字栏", intent)

    def test_visual_intent_uses_safe_fallback_and_partial_override(self) -> None:
        page, mission = _visual_intent_page(
            "形成稳定的行业公共能力",
            "拟建设什么能力",
            "  **能力基础**\n  - 形成支撑。",
        )
        intent = build_page_visual_intent(
            page,
            mission,
            {"recommended_composition": "按证据主导的编辑式构图组织画面。"},
        )
        self.assertIn("主判断与支撑证据的直接关系", intent)
        self.assertIn("按证据主导的编辑式构图组织画面。", intent)
        self.assertIn("Avoid on this page:", intent)

    def test_page_prompt_places_visual_intent_after_global_style_as_final_priority(self) -> None:
        page = parse_script_markdown(SCRIPT_WITH_VISUAL_STRUCTURE).pages[0]
        with TemporaryDirectory() as directory:
            lock = write_project_style_lock(project=Path(directory), style_id=9)
            prompt = build_page_prompt(
                page,
                lock,
                page_mission="首期场景如何选择",
                visual_intent_override={
                    "visual_thesis": "Explain the approved page-specific decision."
                },
                prompt_compiler="legacy",
            )
        self.assertLess(prompt.index("Page-specific visual intent"), prompt.index("上屏文字"))
        self.assertLess(
            prompt.index("Page-specific visual intent"),
            prompt.index("### 2. Semantic anchor and composition — hard"),
        )
        self.assertNotIn("扩展风格9：", prompt)
        self.assertNotIn("不进入默认候选", prompt)
        self.assertIn("【本页业务关系与视觉表达意图｜不上屏】", prompt)
        self.assertIn("不锁定分栏、卡片、框体或文字区", prompt)
        self.assertIn("将锁定文字就近附着于同一连续业务场", prompt)
        self.assertNotIn("Apply this layout guidance", prompt)
        self.assertIn("Explain the approved page-specific decision.", prompt)
        self.assertIn("do not render field names or instruction text", prompt)

    def test_page_visual_intent_override_loader_ignores_invalid_values(self) -> None:
        with TemporaryDirectory() as directory:
            project = Path(directory)
            outline = project / "workbench/stages/01-analysis/outline.json"
            outline.parent.mkdir(parents=True)
            outline.write_text(
                json.dumps(
                    {
                        "pages": [
                            {
                                "page_id": "p19",
                                "visual_intent": {
                                    "visual_intent_type": "comparison",
                                    "visual_thesis": "  Approved thesis.  ",
                                    "decision_relationship": "",
                                    "unknown_field": "ignored",
                                },
                            },
                            {"page_id": "p20", "visual_intent": "invalid"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            overrides = _page_visual_intent_overrides(project)
        self.assertEqual(
            {
                "p19": {
                    "visual_intent_type": "comparison",
                    "visual_thesis": "Approved thesis.",
                }
            },
            overrides,
        )

    def test_content_lock_omits_visual_structure_even_when_parsed(self) -> None:
        page = parse_script_markdown(SCRIPT_WITH_VISUAL_STRUCTURE).pages[0]
        self.assertTrue(page.visual_structure.strip())
        self.assertTrue(page.boundary.strip())
        lock = content_lock_text(page, page_mission="拟建什么性质的能力")
        self.assertNotIn("视觉结构", lock)
        self.assertNotIn("视觉结构：", lock)
        self.assertNotIn("页面角色", lock)
        self.assertNotIn("不写边界旁白", lock)
        self.assertNotIn("不要写成正文模块标题", lock)
        self.assertIn("页面使命", lock)
        self.assertIn("拟建什么性质的能力", lock)
        self.assertIn("核心意思", lock)
        self.assertNotIn("禁止项", lock)
        self.assertNotIn("Boundary (do not show on slide)", lock)
        self.assertNotIn("正式范围待后续确定", lock)
        self.assertIn("上屏文字", lock)
        self.assertIn("行业公共能力", lock)
        self.assertIn("初步定位为面向行业的公共能力", lock)

    def test_build_page_prompt_omits_visual_structure(self) -> None:
        page = parse_script_markdown(SCRIPT_WITH_VISUAL_STRUCTURE).pages[0]
        with TemporaryDirectory() as directory:
            lock = write_project_style_lock(project=Path(directory), style_id=4)
            prompt = build_page_prompt(
                page,
                lock,
                page_mission="拟建什么性质的能力",
            )
        self.assertNotIn("视觉结构：", prompt)
        self.assertNotIn("\n视觉结构", prompt)
        self.assertNotIn("【设计目标与叙事】", prompt)
        self.assertNotIn("不使用外部风格 preset", prompt)
        self.assertNotIn("确认样张", prompt)
        self.assertNotIn("页面角色", prompt)
        self.assertNotIn("## 第9页：", prompt)
        self.assertIn("#12355B", prompt)
        self.assertIn("页面任务", prompt)
        self.assertIn("拟建什么性质的能力", prompt)
        self.assertIn("核心意思", prompt)
        self.assertNotIn("禁止项", prompt)
        self.assertNotIn("Boundary (do not show on slide)", prompt)
        self.assertNotIn("正式范围待后续确定", prompt)
        self.assertNotIn("Boundary text must not appear on the slide", prompt)
        self.assertIn("【完整上屏内容】", prompt)
        self.assertIn("【模板层禁绘｜不上屏】", prompt)
        self.assertIn("不绘制页面标题、副标题、页码、页面序号", prompt)
        self.assertNotIn("不得捏造事实、改变判断强度", prompt)
        self.assertNotIn("不得新增未经页面内容支持的上屏文字", prompt)
        self.assertNotIn("不得新增原文不存在的数字", prompt)
        self.assertNotIn("不得出现证据编号", prompt)

    def test_render_prompt_template_omits_visual_structure(self) -> None:
        with TemporaryDirectory() as directory:
            lock = write_project_style_lock(project=Path(directory), style_id=4)
            prompt = render_prompt(
                PageBlock(
                    page_number=9,
                    title="总体定位",
                    text=(
                        "页面角色：内容页\n"
                        "核心判断：测试判断\n"
                        "上屏文字：要点\n"
                        "Boundary (do not show on slide): 不要画成页脚"
                    ),
                ),
                style_lock_path=lock,
            )
        self.assertNotIn("视觉结构：", prompt)
        self.assertNotIn("【视觉结构设计模块｜不上屏】", prompt)
        self.assertNotIn("[Prompt context] Page-specific visual intent", prompt)
        self.assertNotIn("【设计目标与叙事】", prompt)
        self.assertNotIn("不使用外部风格 preset", prompt)
        self.assertNotIn("确认样张", prompt)
        self.assertNotIn("密度：不改变【内容锁定】", prompt)
        self.assertNotIn("页面角色", prompt)
        self.assertNotIn("## 第9页：", prompt)
        self.assertIn("【内容锁定】", prompt)
        self.assertNotIn("核心判断", prompt)
        self.assertNotIn("测试判断", prompt)
        self.assertIn("上屏文字", prompt)
        self.assertIn("要点", prompt)
        self.assertIn("忠实于【内容锁定】", prompt)
        self.assertNotIn("请先理解", prompt)
        self.assertNotIn("页面使命", prompt)
        self.assertNotIn("禁止项", prompt)
        self.assertNotIn("Boundary (do not show on slide)", prompt)
        self.assertNotIn("不要画成页脚", prompt)
        self.assertNotIn("Boundary text must not appear on the slide", prompt)
        self.assertIn(
            "Do not invent section labels like meta headers; only render 上屏文字 modules.",
            prompt,
        )

    def test_render_prompt_drops_legacy_禁止项_header(self) -> None:
        with TemporaryDirectory() as directory:
            lock = write_project_style_lock(project=Path(directory), style_id=4)
            prompt = render_prompt(
                PageBlock(
                    page_number=9,
                    title="总体定位",
                    text="上屏文字：要点\n禁止项\n不要画成页脚",
                ),
                style_lock_path=lock,
            )
        self.assertNotIn("禁止项", prompt)
        self.assertNotIn("Boundary (do not show on slide)", prompt)
        self.assertNotIn("不要画成页脚", prompt)
        self.assertIn("上屏文字", prompt)
        self.assertIn("要点", prompt)


class StructureStyleDecouplingTests(unittest.TestCase):
    """Style09/Style10 must only vary art_direction, never business structure.

    This pins the visual-structure-fidelity plan's decoupling requirement:
    the same audited semantic_graph/structural_decision projects to the same
    PageArtifactSpec fields regardless of which style lock is selected.
    """

    def _visual_page(self) -> dict:
        return {
            "page_id": "P09",
            "page_number": 9,
            "page_role": "content",
            "page_mission": "Explain how the input relationship field supports the result.",
            "core_judgment": "Input visibly supports the result through one relationship field.",
            "content_lock": {
                "mode": "strict",
                "locked_items": [
                    {"id": "P09-TITLE", "type": "title", "text": "Title"},
                    {"id": "P09-T01", "type": "body", "text": "Input"},
                    {"id": "P09-T02", "type": "body", "text": "Result"},
                ],
            },
            "evidence_units": [
                {"id": "E1", "text": "Input", "kind": "process", "priority": "P0"},
                {"id": "E2", "text": "Result", "kind": "result", "priority": "P0"},
            ],
            "semantic_graph": {
                "primary_relation": "flow",
                "direction": "left_to_right",
                "topology": "directed_flow",
                "focus_node": "E2",
                "nodes": [
                    {"id": "E1", "role": "evidence", "source_refs": ["P09-T01"]},
                    {"id": "E2", "role": "judgment", "source_refs": ["P09-T02"]},
                ],
                "edges": [
                    {"from": "E1", "to": "E2", "relation": "supports", "label": "supports", "direction": "forward"},
                ],
                "decision_relationship": "Input supports Result",
                "business_relationships": [
                    {"subject": "Input", "relation": "supports", "objects": ["Result"]}
                ],
                "grouping_decisions": [],
                "forbidden_structures": ["equal_peer_cards", "invented_center_hub"],
            },
            "structural_decision": {
                "semantic_focus": {"kind": "outcome", "ref": "E2"},
                "spatial_grammar": ["path"],
                "reading_sequence": ["E1", "E2"],
            },
            "visual_decision": {
                "visual_thesis": "Input visibly supports the result through one relationship field.",
                "spatial_organization": "Input leads to Result",
                "reading_path": ["Input", "Result"],
                "text_integration_method": "Attach text to its related object",
                "relationship_encoding": "Directed support relationship",
                "visual_hierarchy": {"primary": "Result", "secondary": ["Input"], "tertiary": []},
            },
            "text_integration": {
                "title_render_mode": "external_text_layer",
                "subtitle_render_mode": "external_text_layer",
                "body_render_mode": "in_image",
                "placement_strategy": "Attach text to its related object",
            },
            "geometry": {"canvas": {"width": 2048, "height": 1024, "ratio": "2:1"}},
            "image_plan": {
                "use_scene": False,
                "scene_type": "Flat business relationship field",
                "business_object": "Input-to-result relationship field",
                "semantic_role": "The relationship field proves that input supports the result",
                "placement": "Input leads to Result",
            },
            "connectors": [
                {"from": "E1", "to": "E2", "type": "flow", "direction": "left_to_right", "label": "supports", "main_chain": True}
            ],
            "final_text": [
                {"id": "P09-T01", "text": "Input"},
                {"id": "P09-T02", "text": "Result"},
            ],
            "generation_handoff": {
                "required_text_ids": ["P09-T01", "P09-T02"],
                "required_text": ["Input", "Result"],
                "title_exclusion_instruction": "Do not render title or subtitle.",
            },
            "avoid": ["Do not create an independent text wall."],
        }

    def _handoff_page(self) -> dict:
        return {
            "page_id": "p09",
            "page_number": 9,
            "render_role": "content",
            "argument_role": "content",
            "title": "Title",
            "page_mission": "Explain how the input relationship field supports the result.",
            "core_message": "Input visibly supports the result through one relationship field.",
            "must_not_include": [],
            "stage02_visual_input": {
                "body_image_canvas": {"width": 2048, "height": 1024, "ratio": "2:1"},
                "title_render_mode": "external_text_layer",
                "subtitle_render_mode": "external_text_layer",
                "business_relationships": [
                    {"subject": "Input", "relation": "supports", "objects": ["Result"]}
                ],
            },
        }

    def test_style09_and_style10_project_identical_structure(self) -> None:
        from cyberppt.page_artifact_spec import build_page_artifact_spec

        handoff_page = self._handoff_page()
        with TemporaryDirectory() as directory9, TemporaryDirectory() as directory10:
            lock9 = write_project_style_lock(project=Path(directory9), style_id=9)
            lock10 = write_project_style_lock(project=Path(directory10), style_id=10)
            spec9 = build_page_artifact_spec(
                handoff_page=handoff_page,
                visual_page=self._visual_page(),
                style_lock=lock9,
                handoff_sha256="a" * 64,
                visual_source_sha256="b" * 64,
            )
            spec10 = build_page_artifact_spec(
                handoff_page=handoff_page,
                visual_page=self._visual_page(),
                style_lock=lock10,
                handoff_sha256="a" * 64,
                visual_source_sha256="b" * 64,
            )

        self.assertNotEqual(spec9.art_direction, spec10.art_direction)
        self.assertEqual(9, spec9.art_direction.style_id)
        self.assertEqual(10, spec10.art_direction.style_id)

        # Every field the plan calls out as structural authority -- topology,
        # primary relation, focus node, nodes, edges, reading path, text
        # bindings -- must be untouched by the style choice.
        self.assertEqual(spec9.deliverable, spec10.deliverable)
        self.assertEqual(spec9.communication_goal, spec10.communication_goal)
        self.assertEqual(spec9.visual_thesis, spec10.visual_thesis)
        self.assertEqual(spec9.evidence, spec10.evidence)
        self.assertEqual(spec9.relationships, spec10.relationships)
        self.assertEqual(spec9.visual_carrier, spec10.visual_carrier)
        self.assertEqual(spec9.composition, spec10.composition)
        self.assertEqual(spec9.typography, spec10.typography)
        self.assertEqual(spec9.hard_constraints, spec10.hard_constraints)

        hashes9 = {key: value for key, value in spec9.source_hashes if key != "style_lock"}
        hashes10 = {key: value for key, value in spec10.source_hashes if key != "style_lock"}
        self.assertEqual(hashes9, hashes10)


if __name__ == "__main__":
    unittest.main()
