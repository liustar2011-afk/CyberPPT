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
from cyberppt.commands.blueprint_gate import (
    approve_blueprint_input,
    approve_visual_style,
    stage_blueprint_input,
    stage_visual_style_options,
)
from cyberppt.commands.init_project import init_project


OPTIONS = [
    {"id": "leadership_review", "label": "领导审定型"},
    {"id": "execution_alignment", "label": "执行对齐型"},
]

SOURCE_ANALYSIS = """# 阶段一确认包
## 输入盘点
- 源文件：年度供需预测报告
## 证据表
| ID | 论点或数据 | 来源位置 |
|---|---|---|
| E01 | 供需总体平衡 | 年度供需预测报告第3页 |
| E02 | 最大负荷1000万千瓦 | 年度供需预测报告第3页 |
## 开放数据冲突
- 无重大冲突。
## 内容脑暴
- 方向一：领导审定型。
- 方向二：执行对齐型。
## 页面物料池
- 最大负荷、供需平衡、风险提示。
"""

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
### 上屏内容
- 2026年最大负荷1000万千瓦
- 供需总体平衡
- 请审定预测结论
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
组件A（顶部并列，三张关键指标卡）——关键数据：
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
"""


class AnalysisExpressionGateTests(unittest.TestCase):
    def _approve_source_analysis(self, project: Path) -> None:
        stage_analysis_artifact(project, "source_analysis", SOURCE_ANALYSIS, "证据链完整", OPTIONS)
        approve_analysis_artifact(project, "source_analysis", "leadership_review")

    def _approve_all_through_business(self, project: Path) -> None:
        self._approve_source_analysis(project)
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

    def test_business_allows_formal_page_and_combined_evidence_block(self) -> None:
        text = """# 页面业务稿
## 第 4 页 工作背景
供需预测工作需要持续完善。
### 非上屏：证据链与完整性校核
- E02，源材料 P26：用电量数据。
- 校核：工作背景和用电量数据不得删除。
"""

        self.assertEqual([], validate_business_script(text))
        self.assertEqual([], validate_analysis_artifact("business_script", text))

    def test_business_excludes_chapter_transition_pages_from_evidence_requirements(self) -> None:
        text = """# 页面业务稿
## 第 3 页 第一章 建设背景与基础
章节过渡。
## 第 4 页 工作背景
工作背景内容。
### 非上屏：证据链与完整性校核
- E02，源材料 P26：用电量数据。
- 校核：工作背景和用电量数据不得删除。
"""

        self.assertEqual([], validate_business_script(text))

    def test_blueprint_input_binds_business_and_style_without_copying_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)
            self._approve_all_through_business(project)
            stage_visual_style_options(project)
            approve_visual_style(project, "style_4")
            pending = stage_blueprint_input(project, DRAWING_SCRIPT, "确认", OPTIONS)
            data = json.loads(pending.read_text(encoding="utf-8"))

            self.assertEqual(hashlib.sha256(BUSINESS_SCRIPT.encode("utf-8")).hexdigest(), data["business_script_sha256"])
            self.assertNotIn("inherited_units", data)

    def test_drawing_rejects_changed_required_units_and_geometry(self) -> None:
        changed = DRAWING_SCRIPT.replace("1000万千瓦", "1200万千瓦").replace("指标卡与结论卡", "x=10, 指标卡与结论卡")

        errors = validate_drawing_script(changed, BUSINESS_SCRIPT)

        self.assertIn("missing required business number in visible text: 1000万千瓦", errors)
        self.assertIn("drawing_script must not contain geometry keywords", errors)

    def test_drawing_visible_text_retains_required_business_facts(self) -> None:
        changed = DRAWING_SCRIPT.replace("供需总体平衡", "供需偏紧", 1)

        errors = validate_drawing_script(changed, BUSINESS_SCRIPT)

        self.assertIn("missing required business fact in visible text: 供需总体平衡", errors)

    def test_drawing_visible_text_retains_required_business_numbers(self) -> None:
        omitted = DRAWING_SCRIPT.replace("- 2026年最大负荷1000万千瓦\n", "- 最大负荷预测\n")

        errors = validate_drawing_script(omitted, BUSINESS_SCRIPT)

        self.assertIn("missing required business number in visible text: 1000万千瓦", errors)

    def test_drawing_rejects_evidence_and_source_text(self) -> None:
        drawing = DRAWING_SCRIPT + "\n- E02，源材料 P26：不应出现在绘制稿。\n"

        errors = validate_drawing_script(drawing, BUSINESS_SCRIPT)

        self.assertIn("drawing_script must not contain evidence or source text", errors)

    def test_drawing_keeps_non_visible_completeness_checks_off_screen(self) -> None:
        business = BUSINESS_SCRIPT.replace(
            "- 事实：供需总体平衡",
            "- 事实：供需总体平衡\n- 事实：不得删除或替换为泛化表述",
        )
        drawing = DRAWING_SCRIPT.replace(
            "- 事实：供需总体平衡",
            "- 事实：供需总体平衡\n- 事实：不得删除或替换为泛化表述",
        )

        self.assertNotIn(
            "missing required business fact in visible text: 不得删除或替换为泛化表述",
            validate_drawing_script(drawing, business),
        )

    def test_drawing_keeps_non_visible_retention_checks_off_screen(self) -> None:
        business = BUSINESS_SCRIPT.replace(
            "- 事实：供需总体平衡",
            "- 事实：供需总体平衡\n- 事实：总体技术路线和成果去向均需保留。",
        )

        self.assertNotIn(
            "missing required business fact in visible text: 总体技术路线和成果去向均需保留。",
            validate_drawing_script(DRAWING_SCRIPT, business),
        )

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

    def test_blueprint_input_preserves_business_and_style_dependencies_in_approval_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)
            self._approve_all_through_business(project)

            stage_visual_style_options(project)
            approve_visual_style(project, "style_4")
            stage_blueprint_input(project, DRAWING_SCRIPT, "drawing script", OPTIONS)
            approval = approve_blueprint_input(project, "leadership_review")

            data = json.loads(approval.read_text(encoding="utf-8"))
            self.assertEqual(
                data["business_script_sha256"],
                hashlib.sha256(BUSINESS_SCRIPT.encode("utf-8")).hexdigest(),
            )
            self.assertTrue(data["style_lock_sha256"])

    def test_new_project_starts_at_reporting_direction(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"

            init_project(project)

            status = get_analysis_expression_status(project)

            self.assertTrue(status.adopted)
            self.assertEqual("source_analysis", status.next_gate)
            self.assertEqual(
                (
                    "source_analysis",
                    "reporting_direction",
                    "report_structure",
                    "page_design",
                    "business_script",
                ),
                GATE_ORDER,
            )
            self.assertTrue((project / "workbench/analysis_expression").is_dir())
            self.assertTrue((project / "workbench/analysis_expression/contract.json").is_file())
            self.assertIn("analysis_expression_contract: required", (project / "manifest.yml").read_text(encoding="utf-8"))
            self.assertIn("analysis-expression", (project / "README.md").read_text(encoding="utf-8"))

            ledger = json.loads((project / "workbench/artifact-ledger.json").read_text(encoding="utf-8"))
            self.assertEqual([], ledger["analysis_expression_contracts"])

    def test_direction_requires_approved_source_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)

            with self.assertRaisesRegex(ValueError, "source_analysis approval is required"):
                stage_analysis_artifact(project, "reporting_direction", DIRECTION, "领导审定型", OPTIONS)

    def test_source_analysis_requires_an_evidence_table(self) -> None:
        errors = validate_analysis_artifact("source_analysis", "## 输入盘点\n源文件\n")

        self.assertIn("missing required heading: 证据表", errors)

    def test_business_rejects_evidence_ids_outside_approved_source_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)
            stage_analysis_artifact(project, "source_analysis", SOURCE_ANALYSIS, "证据链完整", OPTIONS)
            approve_analysis_artifact(project, "source_analysis", "leadership_review")
            stage_analysis_artifact(project, "reporting_direction", DIRECTION, "领导审定型", OPTIONS)
            approve_analysis_artifact(project, "reporting_direction", "leadership_review")
            stage_analysis_artifact(project, "report_structure", STRUCTURE, "four modules", OPTIONS)
            approve_analysis_artifact(project, "report_structure", "leadership_review")
            stage_analysis_artifact(project, "page_design", PAGE_DESIGN, "page design", OPTIONS)
            approve_analysis_artifact(project, "page_design", "leadership_review")

            with self.assertRaisesRegex(ValueError, "unknown evidence IDs: E99"):
                stage_analysis_artifact(
                    project,
                    "business_script",
                    BUSINESS_SCRIPT.replace("E-01", "E99"),
                    "business script",
                    OPTIONS,
                )

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
            self._approve_source_analysis(project)

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

    def test_drawing_inherits_business_units_without_repeating_them_in_page_text(self) -> None:
        second_page = DRAWING_SCRIPT.replace("第1页", "第2页").replace("- E-01\n### 来源位置", "### 来源位置")

        errors = validate_drawing_script(DRAWING_SCRIPT + "\n" + second_page, BUSINESS_SCRIPT + "\n" + BUSINESS_SCRIPT.replace("第1页", "第2页"))

        self.assertEqual([], errors)

    def test_drawing_rejects_implementation_directives(self) -> None:
        drawing = DRAWING_SCRIPT.replace("指标卡与结论卡通过箭头关联。", "使用蓝色 #005BAC，微软雅黑字体和线性图标完成最终构图。")

        errors = validate_drawing_script(drawing, BUSINESS_SCRIPT)

        self.assertIn("drawing_script must not contain implementation directives", errors)

    def test_drawing_requires_component_directives_for_content_pages(self) -> None:
        drawing = DRAWING_SCRIPT.replace("组件A（顶部并列，三张关键指标卡）——关键数据：\n", "")

        self.assertIn("requires at least one component directive", validate_drawing_script(drawing, BUSINESS_SCRIPT))

    def test_business_status_reports_stale_source_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)
            self._approve_all_through_business(project)
            source_analysis = project / "workbench/analysis_expression/source_analysis.md"
            source_analysis.write_text(SOURCE_ANALYSIS.replace("最大负荷1000万千瓦", "最大负荷1100万千瓦"), encoding="utf-8")

            status = get_analysis_expression_status(project)

        business_status = status.gates["business_script"]
        self.assertEqual("stale", business_status["source_analysis_dependency_hash_state"])
        self.assertEqual("source_analysis", status.next_gate)

    def test_status_requires_reapproval_after_an_approved_artifact_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)
            self._approve_all_through_business(project)
            page_design = project / "workbench/analysis_expression/page_design.md"
            page_design.write_text(PAGE_DESIGN + "\n页面角色：内容页\n", encoding="utf-8")

            status = get_analysis_expression_status(project)

        self.assertEqual("page_design", status.next_gate)
        self.assertEqual("stale", status.gates["page_design"]["source_hash_state"])

    def test_utc_timestamp_uses_timezone_utc_for_python_310_compatibility(self) -> None:
        source = inspect.getsource(analysis_expression_gate._utc_now)

        self.assertIn("timezone.utc", source)
        self.assertNotIn("UTC", source)

    def test_restaging_invalidates_pending_and_approval_records_for_successors(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)
            self._approve_source_analysis(project)
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
            self._approve_source_analysis(project)

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
            self._approve_source_analysis(project)
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
            self._approve_source_analysis(project)

            pending = stage_analysis_artifact(project, "reporting_direction", DIRECTION, "leadership_review", OPTIONS)

            self.assertTrue(pending.exists())

    def test_approval_advances_to_the_next_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)
            self._approve_source_analysis(project)
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

    def test_page_design_allows_page_allocation_without_fixed_markdown_roles(self) -> None:
        text = """# 页面设计
## 第 4 页
承接工作背景、形势变化和总体判断。
## 第 5 页
承接工作基础、建设必要性和问题导向。
"""

        self.assertEqual([], validate_analysis_artifact("page_design", text))

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

        errors = validate_drawing_script(text, BUSINESS_SCRIPT)

        self.assertIn("drawing_script must not contain geometry keywords", errors)


if __name__ == "__main__":
    unittest.main()
