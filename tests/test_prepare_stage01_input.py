from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cyberppt.commands.prepare_stage01_input import (
    prepare_outline_input,
    prepare_page_script_input,
)


class PrepareStage01InputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        stage = self.project / "workbench/stages/01-analysis"
        stage.mkdir(parents=True)
        (self.project / "workbench/scripts").mkdir(parents=True)
        (stage / "source-truth.json").write_text(
            json.dumps(
                {
                    "records": [
                        {"id": "S001", "statement": "原文证据一", "status": "现状"},
                        {"id": "S002", "statement": "原文证据二", "status": "建议"},
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (stage / "outline.json").write_text(
            json.dumps(
                {
                    "pages": [
                        {
                            "page_id": "p04",
                            "page_type": "content",
                            "title": "建设基础",
                            "page_job": "说明为什么现在可以启动",
                            "business_question": "基础是否具备",
                            "main_message": "已有基础支持启动",
                            "new_value_vs_previous": "形成启动判断",
                            "reserved_for_later": "实施步骤留后页",
                            "source_refs": ["S001", "S002"],
                            "proof_points": [
                                {
                                    "claim": "统计基础已经具备",
                                    "source_refs": ["S001"],
                                    "consumption": "primary",
                                }
                            ],
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_prepare_outline_input_contains_page_job_and_evidence(self) -> None:
        output = prepare_outline_input(self.project)
        text = output.read_text(encoding="utf-8")
        self.assertIn("Page job: 说明为什么现在可以启动", text)
        self.assertIn("S001 [现状]: 原文证据一", text)

    def test_prepare_page_script_input_contains_consumption_and_evidence(self) -> None:
        output = prepare_page_script_input(self.project, "p04")
        text = output.read_text(encoding="utf-8")
        self.assertIn("[primary] 统计基础已经具备 (S001)", text)
        self.assertIn("S002: 原文证据二", text)
        self.assertTrue(output.name.endswith("-p04.md"))

    def test_prepare_page_script_input_rejects_unknown_page(self) -> None:
        with self.assertRaisesRegex(ValueError, "content page not found"):
            prepare_page_script_input(self.project, "p99")


if __name__ == "__main__":
    unittest.main()
