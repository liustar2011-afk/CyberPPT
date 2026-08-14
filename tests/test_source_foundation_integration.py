from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills"


class SourceFoundationIntegrationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
