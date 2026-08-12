import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from cyberppt.visual_prompt_consumer import (
    VISUAL_STRUCTURE_HEADER,
    append_visual_prompt_module,
    load_visual_prompt_module,
    strip_visual_prompt_module,
)
from cyberppt.commands.init_project import init_project
from scripts.dual_image_overlay.cyberppt_pair_manifest import build_manifest
from scripts.dual_image_overlay.style_library import write_project_style_lock


class VisualPromptConsumerTests(unittest.TestCase):
    def test_consumes_visual_spec_design_not_lossy_generation_summary(self) -> None:
        with TemporaryDirectory() as temp:
            project = Path(temp)
            visual = project / "visual"
            visual.mkdir()
            (visual / "deck-visual-spec.json").write_text(
                json.dumps({"pages": [{
                    "page_number": 6,
                    "visual_decision": {
                        "visual_thesis": "专业能力经可信编排形成可调用服务",
                        "spatial_organization": "一条服务脊柱贯穿能力输入、编排与交付",
                        "text_integration_method": "文字贴附于对应接口、动作和交付结果",
                        "relationship_encoding": "用对象的衔接和尺度层级表达输入、编排与交付",
                        "visual_hierarchy": {"primary": "可信服务脊柱"},
                    },
                    "image_plan": {
                        "business_object": "可信服务脊柱",
                        "semantic_role": "业务对象和关系共同承载画面",
                        "use_scene": True,
                        "scene_type": "电力调度与数据服务协同现场",
                    },
                    "structural_decision": {"spatial_grammar": ["path", "convergence"]},
                    "text_integration": {"placement_strategy": "正文嵌入对应业务节点"},
                    "avoid": ["等权卡片墙", "图文分离"],
                }]}, ensure_ascii=False),
                encoding="utf-8",
            )
            (visual / "generation-prompts.md").write_text(
                "# Page 6: stale\n[Structural guidance]\n- Visual thesis: LOSSY\n",
                encoding="utf-8",
            )
            module = load_visual_prompt_module(project, 6)

        assert module is not None
        self.assertEqual(project / "visual" / "deck-visual-spec.json", module.source_path)
        self.assertIn("可信服务脊柱", module.prompt_text)
        self.assertIn("电力调度与数据服务协同现场", module.prompt_text)
        self.assertIn("文字贴附于对应接口、动作和交付结果", module.prompt_text)
        self.assertIn("避免：等权卡片墙", module.prompt_text)
        self.assertNotIn("LOSSY", module.prompt_text)

    def test_compiles_stage02_ir_to_executable_summary_and_preserves_idempotence(self) -> None:
        with TemporaryDirectory() as temp:
            project = Path(temp)
            visual = project / "visual"
            visual.mkdir(exist_ok=True)
            (visual / "generation-prompts.md").write_text(
                """# Page 6: Test

[Content lock]
lock

[Structural guidance]
- Visual thesis: 多类能力经统一组织后形成可持续服务
- Spatial grammar: path, divergence
- Primary structure refs: E1, E2, E3
- Reading sequence: E1 -> E2 -> E3
- Text binding: E1 -> E1 / embedded / locked text ids: P06-T01
- Additional structural constraint: 标题区留空

[Connector map]
- E1 -> E2

[Text placement]
- Placement strategy: 正文贴附于对应业务环节和关系

[Required on-screen body text]
- LOCKED BODY MUST NOT BE IMPORTED

[Style source]
DO-NOT-IMPORT-STYLE-LOCK

---
""",
                encoding="utf-8",
            )
            module = load_visual_prompt_module(project, 6)
            self.assertIsNotNone(module)
            assert module is not None
            self.assertIn("本页只围绕这一主论断组织画面：多类能力经统一组织后形成可持续服务", module.prompt_text)
            self.assertIn("按一条连续主路径组织业务环节", module.prompt_text)
            self.assertIn("按已锁定文字对应的 3 个业务环节顺序阅读", module.prompt_text)
            self.assertIn("正文贴附于对应业务环节和关系，不形成独立文字墙", module.prompt_text)
            self.assertIn("标题区留空", module.prompt_text)
            for forbidden in ("Semantic focus", "E1", "P06-T01", "Text binding", "Connector map", "Representation freedom"):
                self.assertNotIn(forbidden, module.prompt_text)
            self.assertNotIn("LOCKED BODY MUST NOT BE IMPORTED", module.prompt_text)
            self.assertNotIn("DO-NOT-IMPORT-STYLE-LOCK", module.prompt_text)
            prompt = append_visual_prompt_module("APPROVED LOCKED TEXT", module)
            prompt2 = append_visual_prompt_module(prompt, module)
            self.assertEqual(prompt, prompt2)
            self.assertEqual(prompt.count(VISUAL_STRUCTURE_HEADER), 1)
            self.assertEqual(strip_visual_prompt_module(prompt), "APPROVED LOCKED TEXT")

    def test_v11_builder_keeps_style_reference_out_of_consumed_module(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        skill = repo / "vendor" / "skills" / "ppt-visual-structure-designer"
        example_path = skill / "assets" / "example-page-spec.json"
        example = json.loads(example_path.read_text(encoding="utf-8"))
        page_number = example["page_number"]
        focus = example["structural_decision"]["semantic_focus"]
        style_source_ref = example["generation_handoff"]["style_source_ref"]
        with TemporaryDirectory() as temp:
            project = Path(temp)
            visual = project / "visual"
            visual.mkdir()
            output = visual / "generation-prompts.md"
            subprocess.run(
                [
                    sys.executable,
                    str(skill / "scripts" / "build_generation_prompt.py"),
                    str(example_path),
                    "--output",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            module = load_visual_prompt_module(project, page_number)

        self.assertIsNotNone(module)
        assert module is not None
        self.assertIn("【页面版式执行摘要｜不上屏】", module.prompt_text)
        self.assertNotIn("[Structural guidance]", module.prompt_text)
        self.assertNotIn(focus["ref"], module.prompt_text)
        self.assertNotIn("[Style source]", module.prompt_text)
        self.assertNotIn(style_source_ref, module.prompt_text)
        self.assertNotIn("Font:", module.prompt_text)

    def test_pair_manifest_consumes_project_generation_prompts(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "project"
            init_project(project)
            script = root / "script.md"
            script.write_text(
                """## 第6页：能力结构
- 页面类型：内容页
- 页面标题：能力结构
- 主判断：四类能力共同形成运营闭环。
- 上屏文字：
  - 可信接入
  - 产品运营
""",
                encoding="utf-8",
            )
            visual = project / "visual"
            visual.mkdir(exist_ok=True)
            (visual / "generation-prompts.md").write_text(
                """# Page 6: 能力结构

[Mandatory composition guidance] Apply this layout guidance before placing any on-screen text. Do not render its field names or instruction text.
Dominant visual carrier: controlled delivery spine.

[Connector map]
- capability -> delivery

[Text rendering]
- 9pt minimum

[Required on-screen body text]
- THIS MUST NOT OVERRIDE APPROVED BODY

[Style]
deep blue

[Negative constraints]
no equal card wall

---
""",
                encoding="utf-8",
            )
            style_lock = write_project_style_lock(
                project=project, style_id=4, source_script=script
            )
            manifest, _, compiled, _ = build_manifest(
                script=script,
                pages_raw="6",
                output_dir=root / "images",
                project_path=project,
                style_lock=style_lock,
                prompt_enrich="deterministic",
            )
            pair = manifest["pairs"][0]
            prompt = pair["full"]["prompt"]
            self.assertTrue(pair["visual_structure_handoff"]["consumed"])
            self.assertTrue(pair["full"]["visual_structure_handoff"]["consumed"])
            self.assertIn(VISUAL_STRUCTURE_HEADER, prompt)
            self.assertIn("no equal card wall", prompt)
            self.assertNotIn("controlled delivery spine", prompt)
            self.assertNotIn("THIS MUST NOT OVERRIDE APPROVED BODY", prompt)
            compiled_text = compiled.read_text(encoding="utf-8")
            self.assertIn(VISUAL_STRUCTURE_HEADER, compiled_text)
            self.assertIn("no equal card wall", compiled_text)

if __name__ == "__main__":
    unittest.main()
