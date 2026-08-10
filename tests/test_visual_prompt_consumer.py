import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from cyberppt.visual_prompt_consumer import (
    VISUAL_STRUCTURE_HEADER,
    append_visual_prompt_module,
    append_style09_surface_adapter,
    _sanitize_style09_semantic_segment,
    load_visual_prompt_module,
    strip_visual_prompt_module,
)
from cyberppt.commands.init_project import init_project
from scripts.dual_image_overlay.cyberppt_pair_manifest import build_manifest
from scripts.dual_image_overlay.style_library import write_project_style_lock


class VisualPromptConsumerTests(unittest.TestCase):
    def test_style09_text_integration_drops_stale_placement_clause(self) -> None:
        self.assertEqual(
            "Text integration: 各类文字贴近真实对象和工作面。",
            _sanitize_style09_semantic_segment(
                "Text integration: 各类文字贴近真实对象和工作面，首期合作结论位于上部唯一结果区。"
            ),
        )

    def test_loads_only_visual_sections_and_preserves_idempotence(self) -> None:
        with TemporaryDirectory() as temp:
            project = Path(temp)
            visual = project / "visual"
            visual.mkdir(exist_ok=True)
            (visual / "generation-prompts.md").write_text(
                """# Page 6: Test

[Content lock]
lock

[Structural guidance]
- Semantic focus: action / E4
- Spatial grammar: convergence
- Primary structure refs: E4, E5
- Text binding: E4 -> E4 / embedded

[Connector map]
- E1 -> E2

[Text placement]
- Body rendering mode: in_image

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
            self.assertIn("Semantic focus: action / E4", module.prompt_text)
            self.assertIn("Text binding: E4 -> E4 / embedded", module.prompt_text)
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
        self.assertIn("[Structural guidance]", module.prompt_text)
        self.assertIn(
            f"Semantic focus: {focus['kind']} / {focus['ref']}",
            module.prompt_text,
        )
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
            self.assertIn("controlled delivery spine", prompt)
            self.assertNotIn("THIS MUST NOT OVERRIDE APPROVED BODY", prompt)
            compiled_text = compiled.read_text(encoding="utf-8")
            self.assertIn(VISUAL_STRUCTURE_HEADER, compiled_text)
            self.assertIn("controlled delivery spine", compiled_text)

    def test_style09_adapter_keeps_scene_semantics_but_drops_layout_recipe(self) -> None:
        with TemporaryDirectory() as temp:
            project = Path(temp)
            visual = project / "visual"
            visual.mkdir(exist_ok=True)
            (visual / "generation-prompts.md").write_text(
                """# Page 6: Test

[Mandatory composition guidance] Apply this layout guidance before placing any on-screen text. Do not render its field names or instruction text.
- Selected visual intent type: closed_loop_operation
- Visual thesis: 产品形成链与订单履行链通过运营反馈持续优化和退出
- Decision relationship: 主视觉以五条横向泳道呈现五类服务，右侧另设统一收束条。
- Semantic focus: action / E2
- Spatial grammar: feedback
- Reading sequence: E1 -> E2 -> E3
- Text binding: E2 -> E2 / embedded
- Industry scene anchor: controlled delivery surface
- Recommended composition: six-node swim-lane infographic
- Industry scene anchor: a monitored service workspace
- business object: a controlled delivery object; semantic role: primary carrier; placement: center 68%
- business object: 具有明确起点、交付门控和反馈回路的平台运营闭环
- Text integration: attach labels to the service boundary
- Text integration: 阶段文字沿闭环路径附着，门控与退出条件贴近对应节点。
- Relationship encoding: inputs remain outside until authorized
- Relationship encoding: 主链按顺时针推进，反馈线单独回到产品形成段，不使用装饰圆环。

---
""",
                encoding="utf-8",
            )
            module = load_visual_prompt_module(project, 6)
            assert module is not None
            adapted = append_style09_surface_adapter("APPROVED LOCKED TEXT", module)

        self.assertNotIn("controlled delivery surface", adapted)
        self.assertNotIn("monitored service workspace", adapted)
        self.assertNotIn("Decision relationship:", adapted)
        self.assertNotIn("五条横向泳道", adapted)
        self.assertNotIn("统一收束条", adapted)
        self.assertIn("Semantic focus: action / E2", adapted)
        self.assertIn("Spatial grammar: feedback", adapted)
        self.assertIn("Reading sequence: E1 -> E2 -> E3", adapted)
        self.assertIn("Text binding: E2 -> E2 / embedded", adapted)
        self.assertIn("inputs remain outside until authorized", adapted)
        self.assertIn(
            "Dominant semantic carrier: 同一业务对象沿连续状态变化承载业务机制：产品形成链与订单履行链通过运营反馈持续优化和退出。",
            adapted,
        )
        self.assertNotIn("six-node swim-lane infographic", adapted)
        self.assertNotIn("placement: center 68%", adapted)
        self.assertNotIn(VISUAL_STRUCTURE_HEADER, adapted)
        self.assertIn("用一个连续的业务场或具体对象承载文字", adapted)
        self.assertIn("运营反馈返回产品形成段", adapted)
        self.assertIn("主关系依次发生", adapted)
        self.assertNotIn("平台运营闭环", adapted)
        self.assertNotIn("反馈回路", adapted)
        self.assertNotIn("反馈线", adapted)
        self.assertNotIn("顺时针", adapted)
        self.assertNotIn("闭环路径", adapted)
        self.assertNotIn("装饰圆环", adapted)
        self.assertNotIn("整页可见边界最多两级", adapted)
        self.assertNotIn("同页异形标题条最多一个", adapted)

    def test_style09_adapter_does_not_add_mechanism_carrier_to_other_intents(self) -> None:
        with TemporaryDirectory() as temp:
            project = Path(temp)
            visual = project / "visual"
            visual.mkdir(exist_ok=True)
            (visual / "generation-prompts.md").write_text(
                """# Page 18: Test

[Mandatory composition guidance] Apply this layout guidance before placing any on-screen text. Do not render its field names or instruction text.
- Selected visual intent type: evidence_to_judgment
- Visual thesis: 多类证据共同支撑判断
- Industry scene anchor: 真实业务证据场
---
""",
                encoding="utf-8",
            )
            module = load_visual_prompt_module(project, 18)
            assert module is not None
            adapted = append_style09_surface_adapter("APPROVED LOCKED TEXT", module)

        self.assertIn("Industry scene anchor: 真实业务证据场", adapted)
        self.assertNotIn("Dominant semantic carrier:", adapted)


if __name__ == "__main__":
    unittest.main()
