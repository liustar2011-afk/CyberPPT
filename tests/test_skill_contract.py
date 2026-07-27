from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
SOURCE_ANALYSIS = ROOT / "references" / "source-analysis.md"
SCRIPT_QUALITY = ROOT / "references" / "script-quality.md"


class SkillContractTests(unittest.TestCase):
    def test_native_script_audit_gate_precedes_stage02(self) -> None:
        skill = SKILL.read_text(encoding="utf-8-sig")
        reference = SCRIPT_QUALITY.read_text(encoding="utf-8-sig")

        self.assertIn("`script-audit`", skill)
        self.assertIn(
            "脚本审计未通过时不得批准脚本或进入 Stage 02",
            skill,
        )
        self.assertIn("章内推进", reference)
        self.assertIn("上屏结构与语义图同构", reference)
        self.assertIn("构图原语", reference)
        self.assertIn("VISUAL_STRUCTURE_STYLE_ONLY", reference)
        self.assertIn("跨页重复", reference)
        self.assertIn("状态升级", reference)
        self.assertIn("vendor/ppt-script-visual-redesign", skill)

    def test_old_ppt_script_runtime_is_not_required(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertNotIn("scripts/project_manager.py", text)
        self.assertNotIn("context-pack", text)

    def test_source_truth_contract_precedes_outline(self) -> None:
        skill = SKILL.read_text(encoding="utf-8-sig")
        reference = SOURCE_ANALYSIS.read_text(encoding="utf-8-sig")

        self.assertIn("`source-truth.json` 是 Source Truth 的唯一结构化事实源", skill)
        self.assertIn("`source-truth-audit`", skill)
        self.assertIn("F / J / R / B / U", reference)
        self.assertIn("structured_fact_sweep", reference)
        self.assertIn("traceability_rebuild", reference)

    def test_stage01_defaults_to_solution_architecture(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("`solution` 是方案、研究、建设、实施和立项类材料的默认架构", text)
        self.assertIn("`consulting` 仅在用户明确要求或材料明确属于咨询论证时启用", text)
        self.assertIn("SOLUTION_ARCHITECTURE_REQUIRED", text)

    def test_solution_outline_preserves_continuous_page_sequence(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("封面、目录、章节页、内容页和封底必须位于同一连续页面序列", text)
        self.assertIn("章节页只写“第X章：XXX”", text)
        self.assertIn("`title` 与 `main_message` 必须分开", text)

    def test_page_aggregation_and_retry_contract_are_explicit(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("一个完整业务问题和一个视觉中心", text)
        self.assertIn("不得把源材料每个小节或列表项机械拆成单页", text)
        self.assertIn("默认最多 3 次", text)
        self.assertIn("换方向重写", text)
        self.assertIn("不得直接放弃任务", text)

    def test_full_image_ppt_is_default_stage02_production_mode(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("`full-image`（默认）", text)
        self.assertIn("只生成正文区 ImageGen full 图", text)
        self.assertIn("不得把 background 作为必需资产", text)

    def test_ocr_overlay_and_template_rebuild_are_explicit_mainline_branches(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("`editable-overlay`", text)
        self.assertIn("`editable-overlay-text-reference`", text)
        self.assertIn("可编辑模式按合同进入这些步骤", text)

    def test_main_pipeline_names_final_script_pages_as_the_orchestrator(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("脚本锁定 -> final-script-pages -> 所选生图分支 -> 所选 PPT 分支 -> 渲染 QA -> 交付", text)
        self.assertIn("`final-script-pages` 是脚本锁定后的唯一正式编排入口", text)
        self.assertIn("`final-script-pages --generate-images` 调用 Codex OAuth 生图后端", text)

    def test_ppt_generation_keeps_full_image_default_and_editable_branches(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("默认模式为 `full-image`", text)
        self.assertIn("用户明确要求主要正文可编辑、对象级还原、双图法或三图法时", text)
        self.assertIn("选择 `editable-overlay` 或 `editable-overlay-text-reference`", text)

    def test_manual_stop_points_are_allowed_but_must_record_state(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("允许用户手工指定走到哪一步", text)
        self.assertIn("必须记录当前停点、已完成工件、未执行后续步骤和恢复命令", text)
        self.assertIn("不得把停点产物冒充最终交付物", text)

    def test_full_image_ppt_rework_loops_back_to_full_image_stage(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("套模板后发现正文区问题，必须回到对应页的 full 图或脚本锁定返工", text)
        self.assertIn("重新生成图片资产后必须通过 `final-script-pages` 重新执行所选生产分支", text)

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
