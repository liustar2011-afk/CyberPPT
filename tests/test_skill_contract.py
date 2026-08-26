from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "AGENTS.md"
SKILL = ROOT / "SKILL.md"
SOURCE_ANALYSIS = ROOT / "references" / "source-analysis.md"
SCRIPT_QUALITY = ROOT / "references" / "script-quality.md"
LITE_SKILL = ROOT / "vendor" / "word-to-ppt-script" / "SKILL.md"
PROJECT_AGENTS = ROOT / "projects" / "AGENTS.md"
EDITABLE_PPTX_SKILL = ROOT / ".agents" / "skills" / "cyberppt-stage02-editable-pptx" / "SKILL.md"
AUTHORED_SVG_CONTINUATION = (
    ROOT
    / ".agents"
    / "skills"
    / "cyberppt-stage02-editable-pptx"
    / "references"
    / "authored-svg-continuation.md"
)


class SkillContractTests(unittest.TestCase):
    def test_every_completed_step_surfaces_clickable_artifact_links(self) -> None:
        agents = AGENTS.read_text(encoding="utf-8-sig")
        skill = SKILL.read_text(encoding="utf-8-sig")
        lite = LITE_SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("当任何一个阶段或环节任务完成时", agents)
        self.assertIn("可点击 Markdown 链接提交到屏幕上", agents)
        self.assertIn("当前环境可打开的绝对路径", agents)
        self.assertIn("本环节无文件产出", agents)
        self.assertIn("对话交付链接（硬规则）", skill)
        self.assertIn("可点击 Markdown 链接", skill)
        self.assertIn("After any stage or step completes", lite)
        self.assertIn("clickable Markdown link to its absolute path", lite)

    def test_single_user_stage01_uses_conversation_not_control_artifacts(self) -> None:
        skill = SKILL.read_text(encoding="utf-8-sig")
        lite = LITE_SKILL.read_text(encoding="utf-8-sig")

        for checkpoint in (
            "交流目标",
            "章节和页面提纲",
            "页面详细内容",
            "最终全稿",
        ):
            self.assertIn(checkpoint, skill)
        self.assertIn("用户交互发生在对话中", skill)
        self.assertIn("不改变底稿结构", skill)
        self.assertIn("局部修改后重复全量审计", skill)
        self.assertIn("提出一个忠于原稿的交流目标方向", skill)
        self.assertIn("不得提供多个选项", skill)
        self.assertIn("用户目标只作为受众、用途或交付约束", skill)
        self.assertIn("不得直接向用户抛出", skill)
        self.assertIn("prepare-communication-strategy <project>", skill)
        self.assertIn("do not create approval", lite)
        self.assertIn("Do not create a script-hash-bound", lite)
        self.assertIn("one source-faithful", lite)
        self.assertIn("Do not offer multiple communication-goal", lite)
        self.assertIn("Never ask the user", lite)

    def test_native_script_audit_gate_precedes_stage02(self) -> None:
        skill = SKILL.read_text(encoding="utf-8-sig")
        reference = SCRIPT_QUALITY.read_text(encoding="utf-8-sig")

        self.assertIn("`script-audit`", skill)
        self.assertIn(
            "脚本审计未通过时不得进入 Stage 02",
            skill,
        )
        self.assertIn("章内推进", reference)
        self.assertIn("上屏结构与语义图同构", reference)
        self.assertIn("VISUAL_STRUCTURE_STYLE_ONLY", reference)
        self.assertIn("跨页重复", reference)
        self.assertIn("状态升级", reference)
        self.assertIn("vendor/ppt-script-visual-redesign", skill)

    def test_stage01_visual_structure_is_a_semantic_handoff(self) -> None:
        reference = SCRIPT_QUALITY.read_text(encoding="utf-8-sig")

        self.assertIn("Stage 01 只锁定内容关系，不提前锁定页面版式", reference)
        self.assertIn("`视觉结构（不上屏）`语义合同", reference)
        self.assertIn("ppt-visual-structure-designer", reference)
        self.assertIn("VISUAL_STRUCTURE_LAYOUT_RECIPE", reference)

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
        self.assertIn("换方向重写", text)
        self.assertIn("不能沿原策略只做措辞修补", text)

    def test_stage02_contract_advertises_only_audited_full_image_svg_pptx_route(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("`image-to-editable-svg`", text)
        self.assertIn("文字审计", text)
        self.assertIn("可编辑 SVG", text)
        self.assertIn("manual_required", text)

    def test_image_to_editable_pptx_has_a_dedicated_stage02_router(self) -> None:
        text = EDITABLE_PPTX_SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("final-script-pages", text)
        self.assertIn("run_stage02_reconstruction", text)
        self.assertIn("text-free base", text)

    def test_repo_rules_forbid_direct_adapter_image_to_pptx_exports(self) -> None:
        text = AGENTS.read_text(encoding="utf-8-sig")

        self.assertIn("cyberppt-stage02-editable-pptx", text)
        self.assertIn("run_stage02_reconstruction", text)
        self.assertIn("--production-build", text)

    def test_stage02_embedded_graphic_text_policy_is_a_release_gate(self) -> None:
        root_skill = SKILL.read_text(encoding="utf-8-sig")
        workflow = (ROOT / "docs" / "CYBERPPT_WORKFLOW.md").read_text(encoding="utf-8-sig")
        for text in (root_skill, workflow):
            self.assertIn("graphic_text_policy", text)
            self.assertIn("空白容器", text)
        self.assertIn("empty_container_check", root_skill)
        self.assertIn("cyberppt.image_to_pptx.graphic_text_policy.v1", root_skill)
        self.assertIn("graphic_text_policy_qa.json", root_skill)

    def test_stage02_docs_do_not_advertise_dual_image_production(self) -> None:
        documentation = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (
                SKILL,
                ROOT / "README.md",
            )
        )

        for legacy_mode in (
            "editable-overlay",
            "editable-overlay-text-reference",
            "dual_image_editable_overlay",
        ):
            self.assertNotIn(legacy_mode, documentation)

    def test_main_pipeline_names_final_script_pages_as_the_orchestrator(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("脚本锁定 -> final-script-pages -> 所选生图分支 -> 所选 PPT 分支 -> 渲染 QA -> 交付", text)
        self.assertIn("`final-script-pages` 是脚本锁定后的唯一正式编排入口", text)
        self.assertIn("`final-script-pages --generate-images` 调用 Codex OAuth 生图后端", text)

    def test_ppt_generation_requires_audited_full_image_reconstruction(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("唯一生产模式为 `image-to-editable-svg`", text)
        self.assertIn("无文字底图，再盘点每个可见区域", text)
        self.assertIn("无文字底图必须来自该 full 图的受控清理", text)
        self.assertIn("默认 PPT 分支为 `editable`", text)

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

    def test_formal_stage_skill_commands_use_repository_python(self) -> None:
        paths = (
            ROOT / ".agents" / "skills" / "cyberppt-source-foundation" / "SKILL.md",
            ROOT / ".agents" / "skills" / "business-semantic-understanding" / "SKILL.md",
            EDITABLE_PPTX_SKILL,
            AUTHORED_SVG_CONTINUATION,
            ROOT / ".agents" / "skills" / "source-to-markdown" / "SKILL.md",
            ROOT / ".agents" / "skills" / "source-to-markdown" / "references" / "usage.md",
            ROOT / ".agents" / "skills" / "source-structure-factbase" / "SKILL.md",
            ROOT / "docs" / "CYBERPPT_WORKFLOW.md",
        )

        for path in paths:
            text = path.read_text(encoding="utf-8-sig")
            self.assertNotRegex(
                text,
                r"(?<![/\w.-])python(?:3)?\s+(?:-m\s+cyberppt|scripts/)",
                msg=f"bare Python command in {path}",
            )

    def test_stage02_skill_discovers_all_routes_and_explains_svg_resume(self) -> None:
        skill = EDITABLE_PPTX_SKILL.read_text(encoding="utf-8-sig")
        continuation = AUTHORED_SVG_CONTINUATION.read_text(encoding="utf-8-sig")
        frontmatter = skill.split("---", 2)[1]

        for route in (
            "stage02.high_fidelity_quick_editable",
            "stage02.picture_ppt",
            "stage02.dual_delivery",
        ):
            self.assertIn(route, skill)
        self.assertIn("picture PPT", frontmatter)
        self.assertIn("dual delivery", frontmatter)
        self.assertIn("requires a hand-authored SVG", skill)
        self.assertIn("build_context.json", continuation)
        self.assertIn("artifacts.page_image_pairs.path", continuation)
        self.assertIn("same build ID", continuation)
        self.assertIn("graphic_text_policy", continuation)
        self.assertIn("review-quick-page", continuation)
