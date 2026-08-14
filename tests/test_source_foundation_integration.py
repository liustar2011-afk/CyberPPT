from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills"
HANDOFF_SKILL = SKILLS / "cyberppt-handoff"
if str(HANDOFF_SKILL) not in sys.path:
    sys.path.insert(0, str(HANDOFF_SKILL))

from cyberppt_handoff.runtime import run_outline_audit


class SourceFoundationIntegrationTests(unittest.TestCase):
    def test_handoff_runtime_uses_current_outline_audit_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            project = Path(tmp) / "project"
            (root / "cyberppt").mkdir(parents=True)
            with mock.patch("cyberppt_handoff.runtime.subprocess.run") as run:
                run.return_value = mock.Mock(
                    returncode=0,
                    stdout="",
                    stderr="",
                )
                report = run_outline_audit(project, root)

        command = run.call_args.args[0]
        self.assertEqual("passed", report["status"])
        self.assertNotIn("--lightweight", command)
        self.assertEqual("outline-audit", command[3])

    def test_repository_skills_and_entry_scripts_exist(self) -> None:
        for name in (
            "source-to-markdown",
            "source-structure-factbase",
            "business-semantic-understanding",
            "ppt-outline-planning",
            "cyberppt-handoff",
            "cyberppt-source-foundation",
        ):
            self.assertTrue((SKILLS / name / "SKILL.md").is_file(), name)
        for name in (
            "source_foundation_pipeline.py",
            "source_foundation_outline.py",
            "source_foundation_handoff.py",
        ):
            self.assertTrue((ROOT / "scripts" / name).is_file(), name)

    def test_entry_scripts_have_working_help(self) -> None:
        for name in (
            "source_foundation_pipeline.py",
            "source_foundation_outline.py",
            "source_foundation_handoff.py",
        ):
            completed = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / name), "--help"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("usage:", completed.stdout.lower())

    def test_handoff_fixture_compiles_without_semantic_reinference(self) -> None:
        skill = SKILLS / "cyberppt-handoff"
        fixtures = skill / "tests" / "fixtures"
        # Installed repository copy may omit the standalone test fixtures.
        if not fixtures.is_dir():
            self.skipTest("standalone handoff fixtures are not vendored into CyberPPT")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "project"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(skill / "scripts" / "export.py"),
                    str(fixtures / "foundation"),
                    str(fixtures / "semantic"),
                    str(fixtures / "outline"),
                    "-o",
                    str(out),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads((out / "integration" / "cyberppt-handoff-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["projection_validation"]["status"], "ok")
            source_truth = json.loads(
                (out / "workbench" / "stages" / "01-analysis" / "source-truth.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                {"attempt": 1, "max_attempts": 3, "strategy": "projection_only"},
                source_truth["retry"],
            )
            outline = json.loads(
                (out / "workbench" / "stages" / "01-analysis" / "outline.json").read_text(
                    encoding="utf-8"
                )
            )
            page_plan = json.loads(
                (fixtures / "outline" / "page-plan.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                [page["title_intent"] for page in page_plan["pages"]],
                [page["title"] for page in outline["pages"]],
            )
            self.assertEqual(
                [page["order"] for page in page_plan["pages"]],
                [page["sequence"] for page in outline["pages"]],
            )
            content_page = next(
                page for page in outline["pages"] if page["page_type"] == "content"
            )
            self.assertIsInstance(content_page["evidence_roles"], dict)
            self.assertIn("claim", content_page["evidence_roles"])
            self.assertEqual("projection", outline["editorial_control_mode"])
            self.assertEqual("projection", outline["editorial_authoring_mode"])
            self.assertNotIn("chapter_id", content_page)
            self.assertEqual("contains", content_page["content_relations"][0]["relation"])
            self.assertTrue(content_page["primary_argument_node_id"].startswith("L4-"))
            self.assertIn(
                content_page["primary_argument_node_id"],
                content_page["source_argument_node_ids"],
            )
            model = json.loads(
                (
                    out
                    / "workbench"
                    / "stages"
                    / "00-semantic-understanding"
                    / "semantic-argument-model.json"
                ).read_text(encoding="utf-8")
            )
            model_ids = {
                node["id"]
                for field in ("section_nodes", "subsection_nodes")
                for node in model[field]
            }
            self.assertIn(content_page["primary_argument_node_id"], model_ids)
            truth_by_id = {item["id"]: item for item in source_truth["records"]}
            self.assertTrue(
                all(
                    content_page["primary_argument_node_id"]
                    in truth_by_id[ref]["semantic_node_ids"]
                    for ref in content_page["source_refs"]
                )
            )


if __name__ == "__main__":
    unittest.main()
