from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
SOURCE_ANALYSIS = ROOT / "references" / "source-analysis.md"
STORYLINE = ROOT / "references" / "storyline.md"
README = ROOT / "README.md"


class SkillContractTests(unittest.TestCase):
    def test_stage_one_references_default_to_adaptive_internal_reporting(self) -> None:
        source_text = SOURCE_ANALYSIS.read_text(encoding="utf-8-sig")
        storyline_text = STORYLINE.read_text(encoding="utf-8-sig")
        readme_text = README.read_text(encoding="utf-8-sig")

        self.assertIn("材料类型与汇报任务识别", source_text)
        self.assertIn("不得固定章节顺序", storyline_text)
        self.assertIn("页面标题或页面要点", storyline_text)
        self.assertIn("央企、政府内部汇报", readme_text)
        self.assertNotIn("咨询风格的 PowerPoint", readme_text)

    def test_default_writing_style_uses_internal_reporting_and_adaptive_structure(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("`references/internal-reporting-style.md`", text)
        self.assertIn("央企、政府及其直属单位内部汇报", text)
        self.assertIn("`source_and_task_adaptive`", text)
        self.assertIn("不得固定全篇或单页目录顺序", text)
        self.assertIn("SCR、假设树、对标矩阵可作为分析工具", text)

    def test_dual_image_overlay_is_default_third_stage_mode(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("第三阶段默认交付模式为 `dual_image_editable_overlay`", text)
        self.assertIn("只有当用户明确要求图表、表格、箭头、图标或背景对象可编辑", text)
        self.assertIn("升级到 `native_rebuild`", text)

    def test_dual_image_reference_is_required_when_default_mode_runs(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("`references/dual-image-editable-overlay.md`", text)
        self.assertIn("启用或默认执行 `dual_image_editable_overlay`", text)
