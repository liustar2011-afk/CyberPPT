from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cyberppt.commands.assemble_final_script import assemble_final_script
from cyberppt.script_quality_contract import (
    audit_final_manuscript_form,
    is_final_script_path,
    script_retry_directive,
)


class FinalManuscriptFormTests(unittest.TestCase):
    def test_detects_final_path(self) -> None:
        self.assertTrue(
            is_final_script_path(
                Path("proj/workbench/scripts/final/script-final.md")
            )
        )
        self.assertFalse(
            is_final_script_path(
                Path("proj/workbench/scripts/drafts/batch.md")
            )
        )

    def test_rejects_draft_and_batch_tokens(self) -> None:
        text = (
            "# 最终全稿脚本\n\n"
            "## 第1页：封面\n"
            "- 页面类型：封面\n"
            "- 上屏文字：标题\n\n"
            "> 批次：p01\n"
        )
        issues = audit_final_manuscript_form(text)
        self.assertEqual(1, len(issues))
        self.assertEqual("FINAL_MANUSCRIPT_DRAFT_BANNER", issues[0].code)
        self.assertEqual("error", issues[0].severity)

    def test_accepts_clean_final(self) -> None:
        text = (
            "# 最终全稿脚本\n\n"
            "## 第1页：封面\n"
            "- 页面类型：封面\n"
            "- 上屏文字：标题\n"
        )
        self.assertEqual([], audit_final_manuscript_form(text))

    def test_retry_uses_manuscript_form_cleanup(self) -> None:
        from cyberppt.script_quality_contract import ScriptQualityIssue

        directive = script_retry_directive(
            [
                ScriptQualityIssue(
                    code="FINAL_MANUSCRIPT_DRAFT_BANNER",
                    severity="error",
                    message="banner",
                )
            ]
        )
        self.assertEqual("manuscript_form_cleanup", directive["strategy"])
        self.assertIn("assemble-final-script", str(directive["instruction"]))


class AssembleFinalScriptTests(unittest.TestCase):
    def test_merges_batches_and_strips_banners(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            drafts = project / "workbench" / "scripts" / "drafts"
            drafts.mkdir(parents=True)
            (project / "workbench").mkdir(exist_ok=True)
            (project / "workbench" / "artifact-ledger.json").write_text(
                json.dumps({"artifacts": []}, ensure_ascii=False),
                encoding="utf-8",
            )
            (drafts / "batch-01.md").write_text(
                "# 第1—1页脚本草稿\n\n"
                "> 批次：p01\n"
                "> 状态：草稿，待 `script-audit` 通过后审稿\n\n"
                "## 第1页：封面\n"
                "- 页面类型：封面\n"
                "- 上屏文字：封面标题\n",
                encoding="utf-8",
            )
            (drafts / "batch-02.md").write_text(
                "# 第2—2页脚本草稿\n\n"
                "> 批次：p02\n\n"
                "## 第2页：目录\n"
                "- 页面类型：目录\n"
                "- 上屏文字：目录\n",
                encoding="utf-8",
            )

            report = assemble_final_script(project)
            output = Path(str(report["output"]))
            text = output.read_text(encoding="utf-8")

            self.assertEqual(2, report["page_count"])
            self.assertIn("## 第1页：封面", text)
            self.assertIn("## 第2页：目录", text)
            self.assertNotIn("草稿", text)
            self.assertNotIn("批次", text)
            self.assertEqual([], audit_final_manuscript_form(text))


if __name__ == "__main__":
    unittest.main()
