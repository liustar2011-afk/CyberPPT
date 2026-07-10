from __future__ import annotations

import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

import cyberppt.commands.analysis_expression_gate as analysis_expression_gate
from cyberppt.commands.analysis_expression_gate import (
    GATE_ORDER,
    adopt_analysis_expression_contract,
    approve_analysis_artifact,
    get_analysis_expression_status,
    stage_analysis_artifact,
    validate_analysis_artifact,
    validate_business_script,
    validate_drawing_script,
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

BUSINESS_SCRIPT = """# 业务脚本
## 第1页：供需预测分析
### 业务内容
2026年最大负荷预计为1000万千瓦，供需总体平衡。
### 非上屏：证据链
- E-01
### 来源位置
- 年度供需预测报告第3页
### 非上屏：完整性校核
- 事实：供需总体平衡
- 数字：1000万千瓦
- 分类：最大负荷预测
- 边界：2026年
- 请求事项：请审定预测结论
### 非上屏：信息密度
- 最少呈现3项供需指标
"""

DRAWING_SCRIPT = """# 绘制脚本
## 第1页：供需预测分析
### 上屏文字
- 2026年最大负荷1000万千瓦
- 供需总体平衡
- 请审定预测结论
### 组件关系
指标卡与结论卡通过箭头关联。
### 信息密度
- 最少呈现3项供需指标
### 禁止项
- 避免装饰元素
### 非上屏：证据链
- E-01
### 来源位置
- 年度供需预测报告第3页
### 非上屏：完整性校核
- 事实：供需总体平衡
- 数字：1000万千瓦
- 分类：最大负荷预测
- 边界：2026年
- 请求事项：请审定预测结论
"""


class AnalysisExpressionGateTests(unittest.TestCase):
    def _approve_all_through_business(self, project: Path) -> None:
        stage_analysis_artifact(project, "reporting_direction", DIRECTION, "领导审定型", OPTIONS)
        approve_analysis_artifact(project, "reporting_direction", "leadership_review")
        stage_analysis_artifact(project, "report_structure", STRUCTURE, "four modules", OPTIONS)
        approve_analysis_artifact(project, "report_structure", "leadership_review")
        stage_analysis_artifact(project, "page_design", PAGE_DESIGN, "page design", OPTIONS)
        approve_analysis_artifact(project, "page_design", "leadership_review")
        stage_analysis_artifact(project, "business_script", BUSINESS_SCRIPT, "business script", OPTIONS)
        approve_analysis_artifact(project, "business_script", "leadership_review")

    def test_default_style_rejects_consulting_title(self) -> None:
        errors = validate_business_script("## 第3页：核心判断\nSO WHAT\n### 非上屏：证据链\n- E-01\n")

        self.assertIn("consulting-delivery language", " ".join(errors))

    def test_formal_background_necessity_and_feasibility_terms_are_allowed(self) -> None:
        errors = validate_business_script(
            "## 第3页：工作背景、建设必要性与实施可行性\n"
            "### 非上屏：证据链\n- E-01\n"
        )

        self.assertFalse(any("consulting-delivery language" in error for error in errors))

    def test_drawing_cannot_omit_required_business_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)
            self._approve_all_through_business(project)
            incomplete_drawing = DRAWING_SCRIPT.replace("### 非上屏：证据链\n- E-01\n", "")

            with self.assertRaisesRegex(ValueError, "missing required evidence binding"):
                stage_analysis_artifact(project, "drawing_script", incomplete_drawing, "", [])

    def test_drawing_rejects_changed_required_units_and_geometry(self) -> None:
        changed = DRAWING_SCRIPT.replace("1000万千瓦", "1200万千瓦").replace("指标卡与结论卡", "x=10, 指标卡与结论卡")

        errors = validate_drawing_script(changed, BUSINESS_SCRIPT)

        self.assertIn("changed required completeness unit: 数字：1000万千瓦", errors)
        self.assertIn("drawing_script must not contain geometry keywords", errors)

    def test_drawing_visible_text_retains_required_business_facts(self) -> None:
        changed = DRAWING_SCRIPT.replace("供需总体平衡", "供需偏紧", 1)

        errors = validate_drawing_script(changed, BUSINESS_SCRIPT)

        self.assertIn("missing required business fact in visible text: 供需总体平衡", errors)

    def test_drawing_visible_text_retains_required_business_numbers(self) -> None:
        omitted = DRAWING_SCRIPT.replace("- 2026年最大负荷1000万千瓦\n", "- 最大负荷预测\n")

        errors = validate_drawing_script(omitted, BUSINESS_SCRIPT)

        self.assertIn("missing required business number in visible text: 1000万千瓦", errors)

    def test_drawing_allows_concise_required_business_fact_translation(self) -> None:
        concise = DRAWING_SCRIPT.replace("供需总体平衡", "供需平衡", 1)

        errors = validate_drawing_script(concise, BUSINESS_SCRIPT)

        self.assertNotIn("missing required business fact in visible text: 供需总体平衡", errors)

    def test_drawing_rejects_concise_fact_with_unapproved_qualifier(self) -> None:
        qualified = DRAWING_SCRIPT.replace("供需总体平衡", "供需平衡偏紧", 1)

        errors = validate_drawing_script(qualified, BUSINESS_SCRIPT)

        self.assertIn("missing required business fact in visible text: 供需总体平衡", errors)

    def test_drawing_does_not_drop_unapproved_fact_modifiers(self) -> None:
        self.assertFalse(analysis_expression_gate._fact_is_visible("基本完成", "完成"))

    def test_drawing_preserves_all_inherited_units_in_approval_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)
            self._approve_all_through_business(project)

            stage_analysis_artifact(project, "drawing_script", DRAWING_SCRIPT, "drawing script", OPTIONS)
            approval = approve_analysis_artifact(project, "drawing_script", "leadership_review")

            data = json.loads(approval.read_text(encoding="utf-8"))
            self.assertEqual(
                data["business_source_sha256"],
                hashlib.sha256(BUSINESS_SCRIPT.encode("utf-8")).hexdigest(),
            )
            self.assertEqual(["E-01"], data["inherited_units"]["evidence_bindings"])
            self.assertEqual(["年度供需预测报告第3页"], data["inherited_units"]["source_locations"])
            self.assertEqual(["最少呈现3项供需指标"], data["inherited_units"]["density_units"])

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
            self.assertEqual("是否采用领导审定型汇报方向？", data["question"])
            self.assertEqual("领导审定型", data["recommendation"])
            self.assertEqual("leadership_review", data["options"][0]["id"])
            self.assertTrue((project / "workbench/analysis_expression/reporting_direction.md").is_file())

    def test_business_requires_evidence_units_on_each_content_page(self) -> None:
        second_page = BUSINESS_SCRIPT.replace("第1页", "第2页").replace("年度供需预测报告第3页", "")

        errors = validate_business_script(BUSINESS_SCRIPT + "\n" + second_page)

        self.assertIn("business_script page 2 requires at least one source location", errors)

    def test_drawing_requires_inherited_units_on_each_content_page(self) -> None:
        second_page = DRAWING_SCRIPT.replace("第1页", "第2页").replace("- E-01\n### 来源位置", "### 来源位置")

        errors = validate_drawing_script(DRAWING_SCRIPT + "\n" + second_page, BUSINESS_SCRIPT + "\n" + BUSINESS_SCRIPT.replace("第1页", "第2页"))

        self.assertIn("drawing_script page 2 missing required evidence binding: E-01", errors)

    def test_drawing_rejects_implementation_directives(self) -> None:
        drawing = DRAWING_SCRIPT.replace("指标卡与结论卡通过箭头关联。", "使用蓝色 #005BAC，微软雅黑字体和线性图标完成最终构图。")

        errors = validate_drawing_script(drawing, BUSINESS_SCRIPT)

        self.assertIn("drawing_script must not contain implementation directives", errors)

    def test_status_reports_validation_failures_and_dependency_hash_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)
            self._approve_all_through_business(project)
            stage_analysis_artifact(project, "drawing_script", DRAWING_SCRIPT, "drawing script", OPTIONS)
            approve_analysis_artifact(project, "drawing_script", "leadership_review")
            business = project / "workbench/analysis_expression/business_script.md"
            business.write_text(BUSINESS_SCRIPT.replace("供需总体平衡", "供需偏紧"), encoding="utf-8")

            status = get_analysis_expression_status(project)

        drawing_status = status.gates["drawing_script"]
        self.assertEqual("stale", drawing_status["business_dependency_hash_state"])
        self.assertTrue(drawing_status["validation_failures"])

    def test_utc_timestamp_uses_timezone_utc_for_python_310_compatibility(self) -> None:
        source = inspect.getsource(analysis_expression_gate._utc_now)

        self.assertIn("timezone.utc", source)
        self.assertNotIn("UTC", source)

    def test_restaging_invalidates_pending_and_approval_records_for_successors(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)
            stage_analysis_artifact(project, "reporting_direction", DIRECTION, "领导审定型", OPTIONS)
            approve_analysis_artifact(project, "reporting_direction", "leadership_review")
            stage_analysis_artifact(project, "report_structure", STRUCTURE, "four modules", OPTIONS)
            approve_analysis_artifact(project, "report_structure", "leadership_review")

            stage_analysis_artifact(project, "reporting_direction", DIRECTION, "领导审定型", OPTIONS)

            root = project / "workbench/analysis_expression"
            self.assertFalse((root / "report_structure.pending-confirmation.json").exists())
            self.assertFalse((root / "report_structure.approved.json").exists())
            self.assertEqual("reporting_direction", get_analysis_expression_status(project).next_gate)

    def test_direction_requires_two_labeled_options_and_matching_recommendation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)

            with self.assertRaisesRegex(ValueError, "at least two"):
                stage_analysis_artifact(project, "reporting_direction", DIRECTION, "领导审定型", OPTIONS[:1])
            with self.assertRaisesRegex(ValueError, "non-empty label"):
                stage_analysis_artifact(
                    project,
                    "reporting_direction",
                    DIRECTION,
                    "领导审定型",
                    [{"id": "leadership_review", "label": "领导审定型"}, {"id": "execution_alignment", "label": ""}],
                )
            with self.assertRaisesRegex(ValueError, "recommendation"):
                stage_analysis_artifact(project, "reporting_direction", DIRECTION, "不存在的方向", OPTIONS)

    def test_invalid_direction_restage_preserves_existing_artifact_and_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)
            stage_analysis_artifact(project, "reporting_direction", DIRECTION, "领导审定型", OPTIONS)
            approval = approve_analysis_artifact(project, "reporting_direction", "leadership_review")
            artifact = project / "workbench/analysis_expression/reporting_direction.md"
            original_artifact = artifact.read_text(encoding="utf-8")
            original_approval = approval.read_text(encoding="utf-8")

            replacement = DIRECTION.replace("分管领导", "新的汇报对象")
            with self.assertRaisesRegex(ValueError, "recommendation"):
                stage_analysis_artifact(project, "reporting_direction", replacement, "不存在的方向", OPTIONS)

            self.assertEqual(original_artifact, artifact.read_text(encoding="utf-8"))
            self.assertEqual(original_approval, approval.read_text(encoding="utf-8"))
            self.assertEqual("report_structure", get_analysis_expression_status(project).next_gate)

    def test_direction_recommendation_may_use_option_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)

            pending = stage_analysis_artifact(project, "reporting_direction", DIRECTION, "leadership_review", OPTIONS)

            self.assertTrue(pending.exists())

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

    def test_direction_allows_formal_business_heading_aliases(self) -> None:
        text = """# 汇报方向策略
## 方向一：领导审定型建设方案
### 适用受众
分管领导
### 汇报目的
审定建设方案
### 内容重点
工作基础和完善方向
### 证据支撑
源材料和证据链
### 优势
适合领导审定
### 风险边界
不将条件写成既定事实
## 推荐策略
领导审定型建设方案
"""

        self.assertEqual([], validate_analysis_artifact("reporting_direction", text))

    def test_structure_rejects_page_and_visual_fields_and_invalid_module_count(self) -> None:
        text = STRUCTURE + "## 模块五\n保障机制\n## 模块六\n风险闭环\n## 模块七\n附录\n页数：12\n页面标题：供需预测\n视觉形式：折线图\n"

        errors = validate_analysis_artifact("report_structure", text)

        self.assertIn("report_structure must contain 4-6 modules", errors)
        self.assertIn("report_structure must not contain page count fields", errors)
        self.assertIn("report_structure must not contain page title fields", errors)
        self.assertIn("report_structure must not contain visual form fields", errors)

    def test_structure_allows_chinese_chapter_headings_and_scope_boundary(self) -> None:
        text = """# 汇报结构设计
本文件不确定页数、页面标题或视觉形式。
## 推荐汇报结构
### 一、建设背景与基础
说明工作背景和建设必要性。
### 二、建设总体思路
说明目标定位和建设原则。
### 三、建设内容及实施方案
说明建设任务和实施条件。
### 四、需请领导审定事项
说明需审定的事项。
"""

        self.assertEqual([], validate_analysis_artifact("report_structure", text))

    def test_page_design_rejects_evidence_or_decisions_on_navigation_pages(self) -> None:
        text = PAGE_DESIGN.replace("章节导航", "章节导航\n证据：供需预测数据\n决策：审定方案")

        errors = validate_analysis_artifact("page_design", text)

        self.assertIn("navigation pages must not contain evidence or decisions", errors)

    def test_page_design_requires_roles_as_markdown_sections(self) -> None:
        text = PAGE_DESIGN.replace("## 目录", "目录")

        errors = validate_analysis_artifact("page_design", text)

        self.assertIn("missing required heading: 目录", errors)

    def test_page_design_allows_formal_role_aliases_and_scope_boundaries(self) -> None:
        text = """# 页面设计
### 封面
不承载汇报论证或方案内容。
### 目录页
不放各章要点或具体内容。
### 章节过渡页
不放业务数据或判断。
### 内容第 1 页
表达建设背景。
### 封底页
不重复审定事项。
"""

        self.assertEqual([], validate_analysis_artifact("page_design", text))

    def test_page_design_navigation_restrictions_are_section_scoped_and_reject_argument_terms(self) -> None:
        text = PAGE_DESIGN.replace("章节导航", "章节导航\n论证：供需判断\n论据：预测数据")

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
