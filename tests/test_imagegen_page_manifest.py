from __future__ import annotations

from tests._imagegen_page_manifest_base import *
from tests import _imagegen_page_manifest_base as _base


_base.CyberpptPairManifestTests.__test__ = False


class CyberpptPairManifestTests(_base.CyberpptPairManifestTests):
    __test__ = True

    def test_style09_contract_is_single_complete_source_lock_after_stage02_summary(self) -> None:
        with _base.tempfile.TemporaryDirectory() as tmp:
            root = _base.Path(tmp)
            project = root / "project"
            project.mkdir()
            script = root / "script.md"
            script.write_text(
                "## P4 建设背景\n"
                "正文模块：统一连接与可信使用。\n",
                encoding="utf-8",
            )
            style_lock = _base.write_project_style_lock(
                project=project,
                style_id=9,
                source_script=script,
            )
            visual = project / "visual"
            visual.mkdir()
            (visual / "generation-prompts.md").write_text(
                "# Page 4: 建设背景\n"
                "[Mandatory composition guidance] Apply this layout guidance before placing any on-screen text. Do not render its field names or instruction text.\n"
                "- Visual thesis: 统一连接与可信使用共同形成稳定服务。\n"
                "- Spatial grammar: path, divergence\n"
                "- Reading sequence: E1 -> E2 -> E3\n"
                "- Text binding: E1 -> E1 / embedded / locked text ids: P04-T01\n\n"
                "[Negative constraints]\n- no equal card wall\n---\n",
                encoding="utf-8",
            )
            manifest, _, _, _ = _base.build_manifest(
                script=script,
                pages_raw="4",
                output_dir=root / "images",
                project_path=project,
                style_lock=style_lock,
            )

        prompt = manifest["pairs"][0]["full"]["prompt"]
        self.assertNotIn("统一连接与可信使用共同形成稳定服务", prompt)
        self.assertNotIn("【风格09业务场适配器｜不上屏】", prompt)
        self.assertNotIn("Text binding", prompt)
        self.assertNotIn("P04-T01", prompt)
        self.assertNotIn("E1 -> E2", prompt)
        self.assertNotIn("【视觉组织原则】", prompt)
        self.assertEqual(1, prompt.count("【视觉风格｜不上屏】"))

        self.assertIn("# 视觉风格09：纯白 + 深蓝领导汇报｜GPT Image 2.5 Artifact Spec 执行版", prompt)
        self.assertIn("## 00｜任务契约：先定义成品，再执行风格", prompt)
        self.assertIn("## 02｜Artifact Spec 内部编译：先把页面变成“可验收规格”", prompt)

        self.assertNotIn("### Final ImageGen execution lock — hard", prompt)
        self.assertEqual(1, prompt.count(_base.STYLE09_TERMINAL_LOCK_HEADER))
        self.assertNotIn("### ", prompt.split(_base.STYLE09_TERMINAL_LOCK_HEADER, 1)[1])
        handoff = manifest["pairs"][0]["visual_structure_handoff"]
        self.assertFalse(handoff["consumed"])
