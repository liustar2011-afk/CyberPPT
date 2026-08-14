import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cyberppt.visual_prompt_consumer import (
    VISUAL_STRUCTURE_HEADER,
    append_visual_prompt_module,
    load_visual_design,
    load_visual_prompt_module,
    strip_visual_prompt_module,
)


def _governed_page(page_number: int = 6) -> dict[str, object]:
    return {
        "page_number": page_number,
        "visual_decision": {
            "visual_thesis": "专业能力经可信编排形成可调用服务",
            "spatial_organization": "一条服务脊柱贯穿能力输入、编排与交付",
            "text_integration_method": "文字贴附于对应接口、动作和交付结果",
            "relationship_encoding": "用对象的衔接和尺度层级表达输入、编排与交付",
            "visual_hierarchy": {"primary": "可信服务脊柱"},
        },
        "image_plan": {"business_object": "可信服务脊柱", "semantic_role": "业务对象和关系共同承载画面", "use_scene": True, "scene_type": "电力调度与数据服务协同现场"},
        "structural_decision": {"spatial_grammar": ["path", "convergence"]},
        "avoid": ["等权卡片墙", "图文分离"],
    }


class VisualPromptConsumerTests(unittest.TestCase):
    def test_governed_loader_preserves_full_immutable_semantic_ir(self) -> None:
        with TemporaryDirectory() as temp:
            project = Path(temp)
            visual = project / "visual"
            visual.mkdir()
            path = visual / "deck-visual-spec.json"
            path.write_text(json.dumps({"pages": [_governed_page()]}, ensure_ascii=False), encoding="utf-8")
            ir = load_visual_design(project, 6)

        assert ir is not None
        self.assertEqual("governed_json", ir.source_mode)
        self.assertEqual("专业能力经可信编排形成可调用服务", ir.visual_thesis)
        self.assertEqual("可信服务脊柱", ir.business_object)
        self.assertEqual("可信服务脊柱", ir.primary_focus)
        self.assertEqual("一条服务脊柱贯穿能力输入、编排与交付", ir.spatial_organization)
        self.assertEqual("用对象的衔接和尺度层级表达输入、编排与交付", ir.relationship_encoding)
        self.assertEqual("文字贴附于对应接口、动作和交付结果", ir.text_integration_method)
        self.assertEqual("业务对象和关系共同承载画面", ir.semantic_role)
        self.assertTrue(ir.use_scene)
        self.assertEqual("电力调度与数据服务协同现场", ir.scene_type)
        self.assertEqual(("path", "convergence"), ir.spatial_grammar)
        self.assertEqual(("等权卡片墙", "图文分离"), ir.avoid)
        with self.assertRaises(AttributeError):
            ir.visual_thesis = "mutated"  # type: ignore[misc]

    def test_governed_json_never_falls_back_and_missing_page_is_an_error(self) -> None:
        with TemporaryDirectory() as temp:
            project = Path(temp)
            visual = project / "visual"
            visual.mkdir()
            (visual / "deck-visual-spec.json").write_text(json.dumps({"pages": [_governed_page()]}, ensure_ascii=False), encoding="utf-8")
            (visual / "generation-prompts.md").write_text("# Page 7: legacy\n[Structural guidance]\n- Visual thesis: OLD\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing requested page 7"):
                load_visual_design(project, 7, allow_legacy=True)

    def test_legacy_markdown_requires_explicit_opt_in(self) -> None:
        with TemporaryDirectory() as temp:
            project = Path(temp)
            visual = project / "visual"
            visual.mkdir()
            (visual / "generation-prompts.md").write_text("# Page 6: legacy\n[Structural guidance]\n- Visual thesis: 旧版主论题\n- Spatial grammar: path\n\n[Text placement]\n- Placement strategy: 贴附关系\n\n[Negative constraints]\n- no equal card wall\n", encoding="utf-8")
            self.assertIsNone(load_visual_design(project, 6))
            ir = load_visual_design(project, 6, allow_legacy=True)

        assert ir is not None
        self.assertEqual("legacy_markdown", ir.source_mode)
        self.assertEqual("旧版主论题", ir.visual_thesis)

    def test_governed_project_requires_json_and_compatibility_wrapper_keeps_semantics(self) -> None:
        with TemporaryDirectory() as temp:
            project = Path(temp)
            visual = project / "visual"
            visual.mkdir()
            (project / "manifest.yml").write_text("visual_structure_designer: required\n", encoding="utf-8")
            (visual / "generation-prompts.md").write_text("# Page 6: legacy\n[Structural guidance]\n- Visual thesis: OLD\n", encoding="utf-8")
            with self.assertRaisesRegex(FileNotFoundError, "required VisualDesignIR is missing"):
                load_visual_design(project, 6)
            with self.assertRaisesRegex(FileNotFoundError, "required VisualDesignIR is missing"):
                load_visual_prompt_module(project, 6)

            (visual / "deck-visual-spec.json").write_text(json.dumps({"pages": [_governed_page()]}, ensure_ascii=False), encoding="utf-8")
            module = load_visual_prompt_module(project, 6)

        assert module is not None
        self.assertIn("【页面视觉设计语义｜不上屏", module.prompt_text)
        self.assertIn("专业能力经可信编排形成可调用服务", module.prompt_text)
        self.assertIn("可信服务脊柱", module.prompt_text)
        prompt = append_visual_prompt_module("APPROVED LOCKED TEXT", module)
        self.assertEqual(prompt, append_visual_prompt_module(prompt, module))
        self.assertEqual(1, prompt.count(VISUAL_STRUCTURE_HEADER))
        self.assertEqual("APPROVED LOCKED TEXT", strip_visual_prompt_module(prompt))


if __name__ == "__main__":
    unittest.main()
