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

    def test_main_pipeline_names_script_dual_image_overlay_and_template_rebuild(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("脚本锁定 -> 正文区 ImageGen full 图 -> no-text background -> dual_image_editable_overlay -> template_rebuild -> 渲染 QA -> 交付", text)
        self.assertIn("未经 `template_rebuild` 套入模板内容区的 overlay PPTX 只能作为中间产物", text)

    def test_manual_stop_points_are_allowed_but_must_record_state(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("允许用户手工指定走到哪一步", text)
        self.assertIn("必须记录当前停点、已完成工件、未执行后续步骤和恢复命令", text)
        self.assertIn("不得把停点产物冒充最终交付物", text)

    def test_template_rebuild_rework_loops_back_to_dual_image_stage(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("套模板后发现正文区问题，必须回到对应页的双图转换工件返工", text)
        self.assertIn("重新生成正文区 overlay 后必须重新执行 `template_rebuild`", text)

    def test_each_stage_must_persist_traceable_artifacts(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("每一阶段必须落地阶段成果物", text)
        self.assertIn("`artifact-ledger.json`", text)
        self.assertIn("每个成果物必须记录 `stage`、`page`、`path`、`status`、`depends_on`、`supersedes` 和 `resume_command`", text)
        self.assertIn("不得只在对话中说明阶段成果而不写入仓库文件", text)

    def test_template_title_layer_truth_is_required_for_mid_pipeline_inputs(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("标题、副标题、Logo、页码、页脚和公共模板元素属于模板文字层", text)
        self.assertIn("不得从 full 图、background 图或 OCR 猜测标题和副标题", text)
        self.assertIn("中途接入双图时必须提供 `template_text_lock` 或等价标题层 metadata", text)
        self.assertIn("缺少模板文字层 truth 时必须停在 `metadata_required`", text)
