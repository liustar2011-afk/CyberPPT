from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "AGENTS.md"
WORKFLOW = ROOT / "docs" / "CYBERPPT_WORKFLOW.md"
SCRIPT_SKILL = ROOT / ".agents" / "skills" / "cyberppt-script-workflow" / "SKILL.md"
SCRIPT_AGENTS = ROOT / ".agents" / "skills" / "cyberppt-script-workflow" / "AGENTS.md"
FAITHFUL_AUTHORING = SCRIPT_SKILL.parent / "references" / "faithful-authoring-contract.md"
ANALYTICAL_AUTHORING = SCRIPT_SKILL.parent / "references" / "authoring-contract.md"
FINAL_SCRIPT_SCHEMA = ROOT / "contracts" / "final-script.schema.json"
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

    def test_faithful_script_route_has_no_source_index_fallback(self) -> None:
        skill = SCRIPT_SKILL.read_text(encoding="utf-8-sig")
        local_agents = SCRIPT_AGENTS.read_text(encoding="utf-8-sig")
        repo_agents = AGENTS.read_text(encoding="utf-8-sig")
        workflow = WORKFLOW.read_text(encoding="utf-8-sig")

        self.assertIn("must be a current", skill)
        self.assertIn("cyberppt.source_index.v2", skill)
        self.assertIn("author-preflight", skill)
        self.assertIn("Missing, stale, invalid or blocked exact-source state", skill)
        self.assertIn("no no-source-index fallback", local_agents)
        self.assertIn("不得回退到 Foundation preview 或模型记忆", repo_agents)
        self.assertIn("author-preflight", workflow)
        self.assertIn("不得回退到 Foundation preview 或模型记忆", workflow)

        stale_optional_phrases = (
            "when `script/.cache/source-index.json` is v2",
            "when `script/.cache/source-index.json` is a",
            "if a v2 source index exists",
            "When exact v2 source context exists",
            "`script` profile 存在 v2 `.cache/source-index.json` 时",
            "默认 `script` profile 存在 v2 `.cache/source-index.json` 时",
        )
        for phrase in stale_optional_phrases:
            self.assertNotIn(phrase, skill)
            self.assertNotIn(phrase, repo_agents)
            self.assertNotIn(phrase, workflow)

    def test_stage01_authoring_docs_follow_final_script_12_fidelity_contract(self) -> None:
        repo_agents = AGENTS.read_text(encoding="utf-8-sig")
        workflow = WORKFLOW.read_text(encoding="utf-8-sig")
        skill = SCRIPT_SKILL.read_text(encoding="utf-8-sig")
        local_agents = SCRIPT_AGENTS.read_text(encoding="utf-8-sig")
        faithful = FAITHFUL_AUTHORING.read_text(encoding="utf-8-sig")
        analytical = ANALYTICAL_AUTHORING.read_text(encoding="utf-8-sig")
        schema = FINAL_SCRIPT_SCHEMA.read_text(encoding="utf-8-sig")

        self.assertIn("Final Script 1.2", repo_agents)
        self.assertIn("Final Script 1.2", workflow)
        self.assertIn("Final Script 1.2", skill)
        self.assertIn("version `1.2`", local_agents)
        self.assertIn("Final Script 1.2", faithful)
        self.assertIn("Final Script 1.2", analytical)

        for text in (repo_agents, workflow, skill, local_agents, faithful, analytical):
            self.assertIn("fidelity_text", text)

        self.assertIn("1.2 内容页不得 authored `onscreen`", repo_agents)
        self.assertIn("Final Script 1.2 内容页不得 authored `onscreen`", workflow)
        self.assertIn("does **not** author `onscreen`", skill)
        self.assertIn("no authored `onscreen` field", local_agents)
        self.assertIn("Stage 01 does not author `onscreen`", faithful)
        self.assertIn("Stage 01 does not author `onscreen`", analytical)

        stale_current_contract_phrases = (
            "将已审定的 `full_copy` 直接改写为 `onscreen`",
            "`full_copy → onscreen` 投影",
            "`full_copy` 和 `onscreen` 同时继承",
            "完整稿与上屏选择由 AUTHOR",
            "new projects author Final Script contract `cyberppt.final-script` version `1.1`",
            "then writes\n`onscreen` only from the reviewed `full_copy`",
        )
        for phrase in stale_current_contract_phrases:
            self.assertNotIn(phrase, repo_agents)
            self.assertNotIn(phrase, workflow)
            self.assertNotIn(phrase, skill)
            self.assertNotIn(phrase, local_agents)
            self.assertNotIn(phrase, faithful)
            self.assertNotIn(phrase, analytical)

        self.assertIn('"version": {"enum": ["1.0", "1.1", "1.2"]}', schema)
        self.assertIn('"required": ["fidelity_text"]', schema)
        self.assertIn('"not": {"required": ["onscreen"]}', schema)

    def test_stage02_skill_uses_canonical_rewriteable_content_and_fidelity_contract(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8-sig")
        skill = EDITABLE_PPTX_SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("Final Script 1.2", skill)
        self.assertIn("full_copy", skill)
        self.assertIn("runtime `onscreen_text`", skill)
        self.assertIn("fidelity_text", skill)
        self.assertIn("required", skill)
        self.assertIn("if_rendered", skill)
        self.assertIn("canonical Stage 02 intake", skill)
        self.assertIn("exact-copy checks\napply only to fidelity literals", skill)

        self.assertIn("full_copy → runtime.onscreen_text", workflow)
        self.assertIn("内容/自由正文 → runtime.onscreen_text", workflow)
        self.assertIn("普通正文不做全文 OCR 对齐", workflow)

        stale_stage02_phrases = (
            "`full_copy` is non-visible semantic\ncontext only",
            "`onscreen` is optional source material for visible copy",
            "OCR\nand release QA must not compare generated wording with `onscreen`",
        )
        for phrase in stale_stage02_phrases:
            self.assertNotIn(phrase, skill)

    def test_default_project_route_uses_current_profile_router(self) -> None:
        agents = AGENTS.read_text(encoding="utf-8-sig")
        workflow = WORKFLOW.read_text(encoding="utf-8-sig")
        source_skill = SOURCE_SKILL.read_text(encoding="utf-8-sig")
        self.assertIn("默认使用快速、忠实的 `script` profile", agents)
        self.assertIn("strict/legacy", agents)
        self.assertIn("一次 UNDERSTAND/Foundation", workflow)
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
