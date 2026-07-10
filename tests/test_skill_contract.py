from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
SOURCE_ANALYSIS = ROOT / "references" / "source-analysis.md"
STORYLINE = ROOT / "references" / "storyline.md"
README = ROOT / "README.md"


class SkillContractTests(unittest.TestCase):
    def test_readme_documents_analysis_expression_gate(self) -> None:
        text = README.read_text(encoding="utf-8-sig")

        self.assertIn("analysis-expression-status", text)
        self.assertIn("business script", text)
        self.assertIn("蓝图输入", text)

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

    def test_full_image_ppt_is_default_stage02_production_mode(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("第二阶段生产路径为 `full_image_ppt`", text)
        self.assertIn("只生成正文区 ImageGen full 图", text)
        self.assertIn("不再生成 no-text background", text)

    def test_ocr_overlay_and_template_rebuild_are_not_stage02_mainline(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("第二阶段不得进入 OCR、overlay、semantic_plan、source_capture 或 `template_rebuild`", text)
        self.assertIn("`template_image_ppt_export.py`", text)

    def test_main_pipeline_names_script_full_image_and_image_ppt_export(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("脚本锁定 -> 正文区 ImageGen full 图 -> template_image_ppt_export -> 渲染 QA -> 交付", text)
        self.assertIn("正文区主要内容以 full 图承载", text)

    def test_ppt_generation_uses_full_image_stage02_not_dual_image_stage(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("正式第二阶段不得要求 full/background 双图资产", text)
        self.assertIn("旧 `dual_image_editable_overlay`、OCR 和 `template_rebuild` 只可作为 legacy/advanced 路径", text)

    def test_manual_stop_points_are_allowed_but_must_record_state(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("允许用户手工指定走到哪一步", text)
        self.assertIn("必须记录当前停点、已完成工件、未执行后续步骤和恢复命令", text)
        self.assertIn("不得把停点产物冒充最终交付物", text)

    def test_full_image_ppt_rework_loops_back_to_full_image_stage(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("套模板后发现正文区问题，必须回到对应页的 full 图或脚本锁定返工", text)
        self.assertIn("重新生成 full 图后必须重新执行 `template_image_ppt_export`", text)

    def test_each_stage_must_persist_traceable_artifacts(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("每一阶段必须落地阶段成果物", text)
        self.assertIn("`artifact-ledger.json`", text)
        self.assertIn("每个成果物必须记录 `stage`、`page`、`path`、`status`、`depends_on`、`supersedes` 和 `resume_command`", text)
        self.assertIn("不得只在对话中说明阶段成果而不写入仓库文件", text)

    def test_template_title_layer_truth_is_required_for_mid_pipeline_inputs(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("标题、副标题、Logo、页码、页脚和公共模板元素属于模板文字层", text)
        self.assertIn("不得从 full 图或 OCR 猜测标题和副标题", text)
        self.assertIn("中途接入 full 图时必须提供 `template_text_lock` 或等价标题层 metadata", text)
        self.assertIn("缺少模板文字层 truth 时必须停在 `metadata_required`", text)
