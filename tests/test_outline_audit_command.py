from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cyberppt.commands.outline_audit import run_outline_audit
from cyberppt.commands.init_project import init_project


def invalid_outline(attempt: int, strategy: str) -> dict[str, object]:
    return {
        "schema": "cyberppt.outline.v1",
        "material_type": "建设方案",
        "audience": "项目组内部讨论",
        "architecture_mode": "consulting",
        "architecture_reason": "default",
        "user_requested_architecture": False,
        "source_section_weights": {},
        "pages": [],
        "retry": {"attempt": attempt, "max_attempts": 3, "strategy": strategy},
    }


class OutlineAuditCommandTests(unittest.TestCase):
    def _write(self, root: Path, payload: dict[str, object]) -> Path:
        target = root / "outline.json"
        target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return target

    def test_failed_attempt_persists_retry_directive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            code, report = run_outline_audit(project, self._write(root, invalid_outline(1, "consulting_default")))
            stage = project / "workbench" / "stages" / "01-analysis"
            self.assertEqual(4, code)
            self.assertEqual(2, report["remaining_attempts"])
            self.assertTrue(report["retry_directive"])
            self.assertTrue((stage / "outline-contract.json").exists())
            self.assertTrue((stage / "outline-audit.json").exists())
            self.assertTrue((stage / "outline-attempts" / "attempt-01.json").exists())

    def test_third_failure_escalates_instead_of_abandoning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            code, report = run_outline_audit(project, self._write(root, invalid_outline(3, "source_native")))
            self.assertEqual(5, code)
            self.assertEqual("user_decision_required", report["status"])
            self.assertGreaterEqual(len(report["options"]), 2)
            self.assertLessEqual(len(report["options"]), 3)
            self.assertTrue((project / "workbench" / "stages" / "01-analysis" / "outline-escalation.json").exists())

    def test_max_attempts_must_be_between_one_and_five(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            with self.assertRaisesRegex(ValueError, "1 through 5"):
                run_outline_audit(project, self._write(root, invalid_outline(1, "x")), max_attempts=6)

    def test_project_scaffold_contains_outline_attempt_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            init_project(project)
            self.assertTrue((project / "workbench" / "stages" / "01-analysis" / "outline-attempts").is_dir())
            self.assertIn("outline-audit", (project / "README.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
