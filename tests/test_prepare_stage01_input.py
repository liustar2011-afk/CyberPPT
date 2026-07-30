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
                            "onscreen_judgment": "现有基础足以支持项目启动",
                            "new_value_vs_previous": "形成启动判断",
                            "reserved_for_later": "实施步骤留后页",
                            "visual_intent_type": "hierarchy_support",
                            "visual_proof": "用既有基础托住启动判断",
                            "source_refs": ["S001", "S002"],
                            "proof_points": [
                                {
                                    "claim": "统计基础已经具备",
                                    "source_refs": ["S001"],
                                    "consumption": "primary",
                                }
                            ],
                            "boundary_refs": ["S002"],
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
        (self.project / "workbench/stages/01-analysis/outline.json").unlink()
        output = prepare_outline_input(self.project)
        text = output.read_text(encoding="utf-8")
        self.assertIn("`page_job`", text)
        self.assertIn("S001 [", text)
        self.assertIn("原文证据一", text)
        self.assertIn("screen each candidate against `page_job`, `business_question`, and `main_message`", text)
        self.assertIn("Boundary or unresolved records default to `boundary_refs`", text)
        self.assertIn("consolidate them into one proof point", text)
        self.assertIn("independently readable after compression", text)

    def test_prepare_page_script_input_contains_consumption_and_evidence(self) -> None:
        output = prepare_page_script_input(self.project, "p04")
        text = output.read_text(encoding="utf-8")
        self.assertIn("- page_job: 说明为什么现在可以启动", text)
        self.assertIn("- main_message: 已有基础支持启动", text)
        self.assertIn("- onscreen_judgment: 现有基础足以支持项目启动", text)
        self.assertIn("must place `副标题` before `上屏结论` and `上屏文字`", text)
        self.assertIn("independently readable without speaker narration", text)
        self.assertIn(
            "source-supported evidence → explanation or causal relation → implication or handoff",
            text,
        )
        self.assertIn("Boundary is opt-in, never a mandatory fourth beat", text)
        self.assertIn("never create labels such as 质量边界、质量要求、安全边界 or 约束条件", text)
        self.assertIn("preserve a limitation only when the limitation is itself part of the declared page subject", text)
        self.assertIn("hard minimum of 220", text)
        self.assertIn("at least two evidence-bearing on-screen lines", text)
        self.assertIn("[primary] 统计基础已经具备 (S001)", text)
        self.assertIn("- evidence_text:", text)
        self.assertIn("- boundary_refs: S002", text)
        self.assertIn("- visual_intent_type: hierarchy_support", text)
        self.assertIn("- visual_proof: 用既有基础托住启动判断", text)
        self.assertIn("- boundary_constraints:", text)
        self.assertIn("S002: 原文证据二", text)
        self.assertIn("internal controls only", text)
        self.assertIn("must not be copied into coaching tips or speaker notes", text)
        self.assertIn("cyberppt-page-contract", text)
        self.assertIn('"new_value_realized":true', text)
        self.assertIn('"onscreen_judgment":"现有基础足以支持项目启动"', text)
        self.assertIn('"visual_proof":"用既有基础托住启动判断"', text)
        self.assertTrue(output.name.endswith("-p04.md"))

    def test_prepare_page_script_input_rejects_unknown_page(self) -> None:
        with self.assertRaisesRegex(ValueError, "content page not found"):
            prepare_page_script_input(self.project, "p99")


if __name__ == "__main__":
    unittest.main()
