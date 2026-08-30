from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "AGENTS.md"
PROJECT_AGENTS = ROOT / "projects" / "AGENTS.md"
WORKFLOW = ROOT / "docs" / "CYBERPPT_WORKFLOW.md"
SCRIPT_SKILL = ROOT / ".agents" / "skills" / "cyberppt-script-workflow" / "SKILL.md"
SOURCE_SKILL = ROOT / ".agents" / "skills" / "cyberppt-source-foundation" / "SKILL.md"
EDITABLE_PPTX_SKILL = ROOT / ".agents" / "skills" / "cyberppt-stage02-editable-pptx" / "SKILL.md"
AUTHORED_SVG_CONTINUATION = EDITABLE_PPTX_SKILL.parent / "references" / "authored-svg-continuation.md"


class SkillContractTests(unittest.TestCase):
    def test_repository_has_one_canonical_workflow_entry(self) -> None:
        self.assertFalse((ROOT / "SKILL.md").exists())
        agents = AGENTS.read_text(encoding="utf-8-sig")
        workflow = WORKFLOW.read_text(encoding="utf-8-sig")
        self.assertIn("docs/CYBERPPT_WORKFLOW.md", agents)
        self.assertIn("全流程总览和检索入口", agents)
        self.assertIn("PLAN 和 AUTHOR 的唯一执行者是当前主 Agent", agents)
        self.assertIn("cyberppt-script-workflow", workflow)

    def test_every_completed_step_surfaces_clickable_artifact_links(self) -> None:
        agents = AGENTS.read_text(encoding="utf-8-sig")
        self.assertIn("当任何一个阶段或环节任务完成时", agents)
        self.assertIn("可点击 Markdown 链接提交到屏幕上", agents)
        self.assertIn("当前环境可打开的绝对路径", agents)
        self.assertIn("本环节无文件产出", agents)

    def test_script_workflow_keeps_only_three_authoritative_artifacts(self) -> None:
        text = SCRIPT_SKILL.read_text(encoding="utf-8-sig")
        for artifact in (
            "script/foundation.json",
            "script/deck-plan.json",
            "script/dist/final-script.md",
        ):
            self.assertIn(artifact, text)
        self.assertIn("The current main agent is the AUTHOR executor", text)
        self.assertIn("There is no separate AUTHOR", text)

    def test_default_project_route_uses_current_strict_pipeline(self) -> None:
        agents = PROJECT_AGENTS.read_text(encoding="utf-8-sig")
        workflow = WORKFLOW.read_text(encoding="utf-8-sig")
        source_skill = SOURCE_SKILL.read_text(encoding="utf-8-sig")
        self.assertIn("New source-to-script projects use the `strict/legacy` profile by default", agents)
        self.assertIn("一次业务语义理解", workflow)
        for command in (
            "prepare-source-map",
            "source-map-check",
            "prepare-semantic-understanding",
            "semantic-check",
            "compile-source-truth",
            "project-foundation",
        ):
            self.assertIn(command, source_skill)
        self.assertNotIn("source_foundation_pipeline.py", source_skill)

    def test_stage01_has_two_default_human_stops(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8-sig")
        source_skill = SOURCE_SKILL.read_text(encoding="utf-8-sig")
        self.assertIn("Stage 01 的两个人工停点", workflow)
        self.assertNotIn("四个人工停点", workflow)
        self.assertIn("the two human stops", source_skill)
        self.assertNotIn("the four human stops", source_skill)

    def test_stage01_docs_name_only_real_script_checks(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8-sig")
        for command in ("audit-final", "lint", "check-sync"):
            self.assertIn(command, text)
        for removed_command in ("page-preflight", "page-lint", "script-audit"):
            self.assertNotIn(removed_command, text)

    def test_image_to_editable_pptx_has_a_dedicated_stage02_router(self) -> None:
        text = EDITABLE_PPTX_SKILL.read_text(encoding="utf-8-sig")
        self.assertIn("final-script-pages", text)
        self.assertIn("run_stage02_reconstruction", text)
        self.assertIn("text-free base", text)
        self.assertNotIn("../../../SKILL.md", text)

    def test_repo_rules_forbid_direct_adapter_exports(self) -> None:
        text = AGENTS.read_text(encoding="utf-8-sig")
        self.assertIn("cyberppt-stage02-editable-pptx", text)
        self.assertIn("run_stage02_reconstruction", text)
        self.assertIn("--production-build", text)

    def test_formal_stage_commands_use_repository_python(self) -> None:
        paths = (
            ROOT / ".agents" / "skills" / "cyberppt-source-foundation" / "SKILL.md",
            ROOT / ".agents" / "skills" / "business-semantic-understanding" / "SKILL.md",
            EDITABLE_PPTX_SKILL,
            AUTHORED_SVG_CONTINUATION,
            WORKFLOW,
        )
        bare_python = re.compile(r"(?<![/\w.-])python(?:3)?\s+(?:-m\s+cyberppt|scripts/)")
        for path in paths:
            self.assertNotRegex(path.read_text(encoding="utf-8-sig"), bare_python, msg=str(path))

    def test_stage02_continuation_preserves_the_active_build(self) -> None:
        skill = EDITABLE_PPTX_SKILL.read_text(encoding="utf-8-sig")
        continuation = AUTHORED_SVG_CONTINUATION.read_text(encoding="utf-8-sig")
        self.assertIn("requires a hand-authored SVG", skill)
        self.assertIn("build_context.json", continuation)
        self.assertIn("same build ID", continuation)
        self.assertIn("graphic_text_policy", continuation)


if __name__ == "__main__":
    unittest.main()
