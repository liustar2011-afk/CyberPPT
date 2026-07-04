from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"


class SkillContractTests(unittest.TestCase):
    def test_dual_image_overlay_is_default_third_stage_mode(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("第三阶段默认交付模式为 `dual_image_editable_overlay`", text)
        self.assertIn("只有当用户明确要求图表、表格、箭头、图标或背景对象可编辑", text)
        self.assertIn("升级到 `native_rebuild`", text)

    def test_dual_image_reference_is_required_when_default_mode_runs(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("`references/dual-image-editable-overlay.md`", text)
        self.assertIn("启用或默认执行 `dual_image_editable_overlay`", text)
