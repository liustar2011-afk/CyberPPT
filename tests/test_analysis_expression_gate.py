from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cyberppt.commands.analysis_expression_gate import (
    GATE_ORDER,
    adopt_analysis_expression_contract,
    approve_analysis_artifact,
    get_analysis_expression_status,
    stage_analysis_artifact,
    validate_analysis_artifact,
)
from cyberppt.commands.init_project import init_project


OPTIONS = [
    {"id": "leadership_review", "label": "领导审定型"},
    {"id": "execution_alignment", "label": "执行对齐型"},
]

DIRECTION = """# 汇报方向
## 汇报对象
分管领导
## 汇报目的
审定工作安排
## 内容重点
供需研判
## 证据
预测数据
## 优势
基础扎实
## 边界
不替代执行方案
## 推荐方向
领导审定型
"""

STRUCTURE = """# 汇报结构
## 模块一
形势研判
## 模块二
供需预测
## 模块三
风险提示
## 模块四
工作安排
"""

PAGE_DESIGN = """# 页面设计
## 封面
项目名称
## 目录
章节导航
## 过渡页
进入供需预测
## 内容页
供需预测结论
## 封底
请审阅
"""


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

    def test_structure_requires_approved_direction(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)

            with self.assertRaisesRegex(ValueError, "reporting_direction approval is required"):
                stage_analysis_artifact(project, "report_structure", STRUCTURE, "four modules", OPTIONS)

    def test_pending_confirmation_contains_ui_choices(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)

            pending = stage_analysis_artifact(project, "reporting_direction", DIRECTION, "领导审定型", OPTIONS)

            data = json.loads(pending.read_text(encoding="utf-8"))
            self.assertEqual("领导审定型", data["recommendation"])
            self.assertEqual("leadership_review", data["options"][0]["id"])
            self.assertTrue((project / "workbench/analysis_expression/reporting_direction.md").is_file())

    def test_approval_advances_to_the_next_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)
            stage_analysis_artifact(project, "reporting_direction", DIRECTION, "领导审定型", OPTIONS)

            approval = approve_analysis_artifact(project, "reporting_direction", "leadership_review", "已审定")

            data = json.loads(approval.read_text(encoding="utf-8"))
            self.assertTrue(data["approved"])
            self.assertEqual("leadership_review", data["option_id"])
            self.assertEqual("report_structure", get_analysis_expression_status(project).next_gate)

    def test_direction_requires_all_headings(self) -> None:
        errors = validate_analysis_artifact("reporting_direction", "## 汇报对象\n分管领导\n")

        self.assertIn("missing required heading: 汇报目的", errors)

    def test_structure_rejects_page_and_visual_fields_and_invalid_module_count(self) -> None:
        text = STRUCTURE + "## 模块五\n保障机制\n## 模块六\n风险闭环\n## 模块七\n附录\n页数：12\n页面标题：供需预测\n视觉形式：折线图\n"

        errors = validate_analysis_artifact("report_structure", text)

        self.assertIn("report_structure must contain 4-6 modules", errors)
        self.assertIn("report_structure must not contain page count fields", errors)
        self.assertIn("report_structure must not contain page title fields", errors)
        self.assertIn("report_structure must not contain visual form fields", errors)

    def test_page_design_rejects_evidence_or_decisions_on_navigation_pages(self) -> None:
        text = PAGE_DESIGN.replace("章节导航", "章节导航\n证据：供需预测数据\n决策：审定方案")

        errors = validate_analysis_artifact("page_design", text)

        self.assertIn("navigation pages must not contain evidence or decisions", errors)

    def test_drawing_script_rejects_geometry_keywords(self) -> None:
        text = """## 上屏文字
供需预测
## 组件关系
x=10, y=20
## 信息密度
每页三项
## 禁止项
避免堆砌
## 非上屏：证据链
E-01
"""

        errors = validate_analysis_artifact("drawing_script", text)

        self.assertIn("drawing_script must not contain geometry keywords", errors)


if __name__ == "__main__":
    unittest.main()
