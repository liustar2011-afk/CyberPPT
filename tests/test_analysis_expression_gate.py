from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cyberppt.commands.analysis_expression_gate import (
    GATE_ORDER,
    adopt_analysis_expression_contract,
    get_analysis_expression_status,
)
from cyberppt.commands.init_project import init_project


class AnalysisExpressionGateTests(unittest.TestCase):
    def test_new_project_starts_at_reporting_direction(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"

            init_project(project)

            status = get_analysis_expression_status(project)

            self.assertTrue(status.adopted)
            self.assertEqual("reporting_direction", status.next_gate)
            self.assertEqual(
                (
                    "reporting_direction",
                    "report_structure",
                    "page_design",
                    "business_script",
                    "drawing_script",
                ),
                GATE_ORDER,
            )
            self.assertTrue((project / "workbench/analysis_expression").is_dir())
            self.assertTrue((project / "workbench/analysis_expression/contract.json").is_file())
            self.assertIn("analysis_expression_contract: required", (project / "manifest.yml").read_text(encoding="utf-8"))
            self.assertIn("analysis-expression", (project / "README.md").read_text(encoding="utf-8"))

            ledger = json.loads((project / "workbench/artifact-ledger.json").read_text(encoding="utf-8"))
            self.assertEqual([], ledger["analysis_expression_contracts"])

    def test_adoption_does_not_overwrite_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            legacy = project / "workbench/analysis_expression/contract.json"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("keep", encoding="utf-8")

            contract = adopt_analysis_expression_contract(project)

            self.assertEqual(legacy.resolve(), contract)
            self.assertEqual("keep", legacy.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
