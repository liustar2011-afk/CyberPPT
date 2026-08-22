from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from cyberppt.commands.page_lint import run_page_lint
from cyberppt.script_quality_contract import ScriptQualityIssue


class PageLintCommandTests(unittest.TestCase):
    def test_reports_only_target_page_issues_and_defers_cross_page_checks(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            project.mkdir()
            script = project / "draft.md"
            script.write_text("placeholder", encoding="utf-8")
            document = SimpleNamespace(pages=(SimpleNamespace(page_id="p04"),))
            target_issue = ScriptQualityIssue("TARGET", "error", "target", ("p04",))
            cross_page_issue = ScriptQualityIssue("CROSS", "error", "cross", ("p04", "p05"))
            with (
                patch("cyberppt.commands.page_lint.load_outline", return_value={}),
                patch("cyberppt.commands.page_lint.load_source_truth", return_value={}),
                patch("cyberppt.commands.page_lint.parse_script_path", return_value=document),
                patch(
                    "cyberppt.commands.page_lint.audit_script_quality",
                    return_value=[target_issue, cross_page_issue],
                ),
            ):
                code, report = run_page_lint(project, script, "p04")

            self.assertEqual(4, code)
            self.assertEqual("rewrite_required", report["status"])
            self.assertTrue(report["cross_page_checks_deferred"])
            self.assertEqual(["TARGET"], [item["code"] for item in report["issues"]])
