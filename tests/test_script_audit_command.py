from __future__ import annotations

import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cyberppt.commands.script_audit import run_script_audit
from cyberppt.script_quality_contract import ScriptQualityIssue


VALID_SCRIPT = """## 第8页：第二章：定位、目标与研究边界

- 页面类型：章节过渡页
- 上屏文字：第二章：定位、目标与研究边界

## 第9页：总体定位

- 页面类型：内容页
- 页面标题：总体定位
- 主判断：初步定位为面向行业的公共能力。
- 完整文字稿：中电联面向行业的电力供需形势预测与预警公共能力，覆盖主要预测对象、多时间尺度和多类成果，并由统一数据治理、组合模型、专家会商、成果生产与安全运行支撑。该定位用于明确研究方向与服务对象，也为后续行业数据服务、专题研判和成果运营建立共同的业务边界。职责分工上，重点处理全国、区域、省级和重点行业供需形势分析，服务履职与行业共用；通过统一口径、跨区域协同和可追溯成果管理提升研判效率，形成面向研究、履职和行业共用的稳定工作机制。实际工作中还要持续校准数据口径、验证预测结果、记录预警依据，并将专题研判转化为可复用的成果资产和服务流程，保证不同区域、不同时间尺度之间能够比较和追踪；相关成果还应支持复盘、更新和跨部门协同，形成从数据到判断、从判断到服务的连续链条，同时明确不替代电网实时调度控制、市场出清、企业生产计划和具体投资决策等专业系统。
- 文字稿取舍说明：
  - 必留上屏：公共能力定位、服务对象和专业系统边界。
  - 仅讲解：职责分工与支撑机制。
  - 仅追溯：邻页目标框架与任务安排。
- 证据映射：公共能力定位→S015；职责分工与不替代边界→S026；会商与支撑机制→S059
- 上屏文字：

行业公共能力

    能力定位：面向电力行业开展供需形势预测与预警，覆盖主要预测对象、多时间尺度和多类成果。
    支撑体系：由统一数据治理、组合模型、专家会商、成果生产与安全运行共同支撑行业研判和成果发布。
    服务范围：覆盖全国、区域、省级和重点行业供需分析，服务履职与行业共用。
    跨域协同：统一口径和成果管理提升研判效率，明确服务对象与业务边界。
    成果输出：输出预测、预警、专题研判与成果发布，支撑研究方向和行业共用。

专业系统边界

    职责边界：服务行业研判和成果发布，不替代电网调度、市场出清、企业生产计划和具体投资决策。

    运行边界：保留专业职责和运行边界。

- 证据：S015、S026、S059
- 边界：正式范围经摸底验证后确定。
- 视觉结构：公共能力定位与职责边界图。
- 讲解提示：先说定位，再说职责分工。

【演讲者备注】

建设定位是面向行业的电力供需形势预测与预警公共能力，覆盖主要对象与多类成果，并由数据、模型、会商和成果生产支撑；同时明确不替代调度、出清和企业计划等专业系统。
"""


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _approve_content_review(project: Path, script: Path) -> None:
    outline = json.loads(
        (project / "workbench/stages/01-analysis/outline.json").read_text(
            encoding="utf-8"
        )
    )
    page_ids = [
        item["page_id"]
        for item in outline["pages"]
        if item.get("page_type") == "content"
    ]
    decisions = {
        "single_mission": True,
        "module_same_dimension": True,
        "nonessential_information_removed": True,
        "cross_page_new_value": True,
    }
    review_manifest = project / "review" / "chapter-review-manifest-script.json"
    _write_json(
        review_manifest,
        {
            "schema": "cyberppt.chapter_review_manifest.v1",
            "level": "script",
            "input_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
            "reviews": [],
        },
    )
    _write_json(
        project / "workbench" / "scripts" / "audits" / "content-review.json",
        {
            "schema": "cyberppt.content_review.v2",
            "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest().upper(),
            "decisions": decisions,
            "review_provenance": {
                "reviewer_type": "independent_model",
                "authoring_separated": True,
                "authoring_run_id": "authoring-run-test",
                "reviewer_run_id": "review-run-test",
                "reviewed_at": "2026-08-03T00:00:00Z",
                "review_summary": "Independent test review completed.",
                "chapter_review_manifest_sha256": hashlib.sha256(
                    review_manifest.read_bytes()
                ).hexdigest().upper(),
            },
            "pages": {
                page_id: {**decisions, "note": "Page contribution reviewed."}
                for page_id in page_ids
            },
        },
    )


def _build_project(root: Path, script_text: str = VALID_SCRIPT) -> tuple[Path, Path]:
    project = root / "project"
    analysis = project / "workbench" / "stages" / "01-analysis"
    script = project / "workbench" / "scripts" / "drafts" / "batch.md"
    script.parent.mkdir(parents=True, exist_ok=True)
    # Keep the shared fixture above the repository's current reading-density
    # gate while preserving the business meaning used by the tests.
    script_text = script_text.replace(
        "\u7b49\u4e13\u4e1a\u7cfb\u7edf\u3002",
        "\u7b49\u4e13\u4e1a\u7cfb\u7edf\u3002\u540e\u7eed\u6210\u679c\u8fd8\u5e94\u652f\u6301\u5468\u671f\u6027\u590d\u76d8\u548c\u8fd0\u8425\u66f4\u65b0\uff0c\u5e76\u5bf9\u6570\u636e\u53e3\u5f84\u3001\u9884\u6d4b\u7ed3\u679c\u3001\u9884\u8b66\u4f9d\u636e\u548c\u6210\u679c\u7248\u672c\u4fdd\u7559\u53ef\u8ffd\u6eaf\u8bb0\u5f55\uff0c\u4f7f\u4e0d\u540c\u5730\u533a\u3001\u4e0d\u540c\u65f6\u95f4\u5c3a\u5ea6\u548c\u4e0d\u540c\u4f7f\u7528\u573a\u666f\u7684\u5206\u6790\u7ed3\u679c\u5177\u5907\u53ef\u6bd4\u8f83\u6027\u4e0e\u53ef\u590d\u6838\u6027\u3002",
    )
    script.write_text(script_text, encoding="utf-8")
    _write_json(
        analysis / "outline.json",
        {
            "schema": "cyberppt.outline.v1",
            "material_type": "solution",
            "audience": "project_team",
            "architecture_mode": "solution",
            "architecture_reason": "formal solution workflow",
            "source_section_weights": {},
            "argument_contract_mode": "strict",
            "pages": [
                {
                    "page_id": "p08",
                    "sequence": 8,
                    "page_type": "chapter",
                    "title": "第二章：定位、目标与研究边界",
                },
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "positioning",
                    "source_refs": ["S015", "S026", "S059"],
                    "prerequisite_pages": [],
                    "main_claim_status": "proposed",
                },
            ],
            "retry": {"attempt": 1, "max_attempts": 3, "strategy": ""},
        },
    )
    _write_json(
        analysis / "source-truth.json",
        {
            "schema": "cyberppt.source_truth.v1",
            "sources": [],
            "coverage_targets": [],
            "argument_contract_mode": "strict",
            "records": [
                {
                    "id": "S015",
                    "type": "B",
                    "status": "拟建议",
                    "statement": "初步定位。",
                },
                {
                    "id": "S026",
                    "type": "B",
                    "status": "研究边界",
                    "statement": "专业边界。",
                },
                {
                    "id": "S059",
                    "type": "B",
                    "status": "研究边界",
                    "statement": "正式范围待定。",
                },
            ],
            "conclusions": [],
            "pages": [],
            "retry": {"attempt": 1, "max_attempts": 3, "strategy": ""},
        },
    )
    _write_json(
        project / "workbench" / "artifact-ledger.json",
        {"schema": "cyberppt.artifact_ledger.v1", "artifacts": []},
    )
    return project, script


def _build_failing_project(root: Path) -> tuple[Path, Path]:
    project, script = _build_project(root)
    script.write_text(
        """## 第4页：工作基础

- 页面类型：内容页
- 页面标题：工作基础
- 主判断：现有基础能够直接支撑首期建设全国总盘和定期报告。
- 完整文字稿：本页应以既有统计、研判和协调工作事实为主。若把现有基础能够直接支撑首期建设全国总盘和定期报告写成工作基础页的核心判断，就把尚未进入范围论证的首期建设安排提前固化了。正确写法应先陈述已形成的工作依托，再在范围页讨论首期取舍。
- 文字稿取舍说明：本页只写本页业务问题主体；邻页议题不展开；建议与边界保持拟/待状态。
- 证据映射：支撑点1→S006
- 上屏文字：

  **统计基础**

  - 已形成稳定统计积累。

  **报告基础**

  - 已形成定期报告工作。

- 证据：S006
- 边界：本页只陈述既有事实。
- 视觉结构：工作基础链。
""",
        encoding="utf-8",
    )
    analysis = project / "workbench" / "stages" / "01-analysis"
    _write_json(
        analysis / "outline.json",
        {
            "schema": "cyberppt.outline.v1",
            "material_type": "solution",
            "audience": "project_team",
            "architecture_mode": "solution",
            "architecture_reason": "formal solution workflow",
            "source_section_weights": {},
            "argument_contract_mode": "strict",
            "pages": [
                {
                    "page_id": "p04",
                    "sequence": 4,
                    "page_type": "content",
                    "title": "工作基础",
                    "argument_role": "foundation",
                    "source_refs": ["S006"],
                    "prerequisite_pages": [],
                    "main_claim_status": "confirmed",
                }
            ],
            "retry": {"attempt": 1, "max_attempts": 3, "strategy": ""},
        },
    )
    _write_json(
        analysis / "source-truth.json",
        {
            "schema": "cyberppt.source_truth.v1",
            "sources": [],
            "coverage_targets": [],
            "argument_contract_mode": "strict",
            "records": [
                {
                    "id": "S006",
                    "type": "F",
                    "status": "已形成",
                    "statement": "具备统计和报告工作基础。",
                }
            ],
            "conclusions": [],
            "pages": [],
            "retry": {"attempt": 1, "max_attempts": 3, "strategy": ""},
        },
    )
    return project, script


class ProhibitedContrastTests(unittest.TestCase):
    def test_rejects_not_but_contrast_in_authored_copy(self) -> None:
        from cyberppt.script_quality_contract import _prohibited_contrast_hits

        self.assertEqual(
            ("不是内部工具，而是",),
            _prohibited_contrast_hits("建设定位不是内部工具，而是行业公共能力。"),
        )

    def test_rejects_conversational_manuscript_marker(self) -> None:
        from cyberppt.script_quality_contract import _prohibited_colloquial_hits

        self.assertEqual(("接下来", "看一下"), _prohibited_colloquial_hits("接下来我们看一下运营流程。"))

    def test_rejects_unlabeled_onscreen_bullet(self) -> None:
        from cyberppt.script_quality_contract import _unlabeled_onscreen_bullets

        self.assertEqual(("- 形成统一目录和服务记录。",), _unlabeled_onscreen_bullets("- 形成统一目录和服务记录。"))
        self.assertEqual(
            ("- 形成统一目录，记录授权范围：并支持审计。",),
            _unlabeled_onscreen_bullets("- 形成统一目录，记录授权范围：并支持审计。"),
        )


class ScriptAuditCommandTests(unittest.TestCase):
    def test_persists_passed_reports_and_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project, script = _build_project(Path(temp_dir))
            _approve_content_review(project, script)

            code, report = run_script_audit(project, script)

            self.assertEqual(0, code)
            self.assertEqual("passed", report["status"])
            self.assertEqual("passed_with_warnings", report["quality_status"])
            self.assertGreater(report["warning_count"], 0)
            audit_dir = project / "workbench" / "scripts" / "audits"
            self.assertTrue((audit_dir / "script-audit.json").exists())
            self.assertTrue((audit_dir / "script-audit.md").exists())
            self.assertTrue((audit_dir / "attempts" / "attempt-01.json").exists())
            ledger = json.loads(
                (project / "workbench" / "artifact-ledger.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertTrue(
                any(
                    item["path"]
                    == "workbench/scripts/audits/script-audit.json"
                    for item in ledger["artifacts"]
                )
            )

    def test_structural_success_does_not_require_a_second_content_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project, script = _build_project(Path(temp_dir))

            code, report = run_script_audit(project, script)

            self.assertEqual(0, code)
            self.assertEqual("passed", report["status"])
            self.assertEqual("missing", report["content_review"]["status"])
            self.assertEqual("advisory", report["content_review_gate"])

    def test_stale_content_review_is_not_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project, script = _build_project(Path(temp_dir))
            _approve_content_review(project, script)
            script.write_text(script.read_text(encoding="utf-8") + "\n", encoding="utf-8")

            code, report = run_script_audit(project, script)

            self.assertEqual(0, code)
            self.assertEqual("passed", report["status"])
            self.assertEqual("stale", report["content_review"]["status"])

    def test_legacy_boolean_only_content_review_is_unverified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, script = _build_project(Path(tmp))
            outline = json.loads(
                (project / "workbench/stages/01-analysis/outline.json").read_text(
                    encoding="utf-8"
                )
            )
            decisions = {
                "single_mission": True,
                "module_same_dimension": True,
                "nonessential_information_removed": True,
                "cross_page_new_value": True,
            }
            _write_json(
                project / "workbench/scripts/audits/content-review.json",
                {
                    "schema": "cyberppt.content_review.v1",
                    "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
                    "decisions": decisions,
                    "pages": {
                        page["page_id"]: {**decisions, "note": "auto approved"}
                        for page in outline["pages"]
                        if page.get("page_type") == "content"
                    },
                },
            )
            code, report = run_script_audit(project, script, max_attempts=5)
            self.assertEqual(0, code)
            self.assertEqual("passed", report["status"])
            self.assertEqual("unverified", report["content_review"]["status"])

    def test_same_authoring_and_reviewer_run_is_unverified(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project, script = _build_project(Path(temp_dir))
            _approve_content_review(project, script)
            review_path = project / "workbench/scripts/audits/content-review.json"
            review = json.loads(review_path.read_text(encoding="utf-8"))
            review["review_provenance"]["reviewer_run_id"] = review[
                "review_provenance"
            ]["authoring_run_id"]
            _write_json(review_path, review)

            code, report = run_script_audit(project, script)

            self.assertEqual(0, code)
            self.assertEqual("passed", report["status"])
            self.assertEqual("unverified", report["content_review"]["status"])
            self.assertFalse(report["content_review"]["identity_valid"])

    def test_attempts_auto_increment_and_change_strategy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project, script = _build_failing_project(Path(temp_dir))

            code1, report1 = run_script_audit(project, script, max_attempts=3)
            code2, report2 = run_script_audit(project, script, max_attempts=3)

            self.assertEqual(4, code1)
            self.assertEqual(4, code2)
            self.assertEqual(1, report1["attempt"])
            self.assertEqual(2, report2["attempt"])
            self.assertNotEqual(
                report1["retry_directive"]["strategy"],
                report2["retry_directive"]["strategy"],
            )

    def test_max_attempt_returns_user_decision_options(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project, script = _build_failing_project(Path(temp_dir))

            code, report = run_script_audit(
                project,
                script,
                attempt=3,
                max_attempts=3,
            )

            self.assertEqual(5, code)
            self.assertEqual("user_decision_required", report["status"])
            self.assertGreaterEqual(len(report["options"]), 2)
            self.assertLessEqual(len(report["options"]), 3)

    def test_warnings_only_still_pass(self) -> None:
        warning = ScriptQualityIssue(
            code="VISUAL_STRUCTURE_TOO_THIN",
            severity="warning",
            message="thin visual",
            pages=("p09",),
            suggested_action="expand visual structure",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            project, script = _build_project(Path(temp_dir))
            _approve_content_review(project, script)
            with patch(
                "cyberppt.commands.script_audit.audit_script_quality",
                return_value=[warning],
            ):
                code, report = run_script_audit(project, script)

            self.assertEqual(0, code)
            self.assertEqual("passed", report["status"])
            self.assertEqual("passed_with_warnings", report["quality_status"])
            self.assertEqual(1, report["warning_count"])
            self.assertEqual([], report["failed_pages"])
            self.assertEqual(
                ["VISUAL_STRUCTURE_TOO_THIN"],
                [item["code"] for item in report["issues"]],
            )
            self.assertFalse(report["retry_directive"]["required"])

    def test_final_path_rejects_draft_batch_wording(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project, script = _build_project(Path(temp_dir))
            final = project / "workbench" / "scripts" / "final" / "script-final.md"
            final.parent.mkdir(parents=True, exist_ok=True)
            final.write_text(
                "# 第8—9页脚本草稿\n\n"
                "> 批次：p08–p09\n\n"
                + script.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            code, report = run_script_audit(project, final)

            self.assertEqual(4, code)
            self.assertEqual("rewrite_required", report["status"])
            self.assertIn(
                "FINAL_MANUSCRIPT_DRAFT_BANNER",
                [item["code"] for item in report["issues"]],
            )
            self.assertEqual(
                "manuscript_form_cleanup",
                report["retry_directive"]["strategy"],
            )


if __name__ == "__main__":
    unittest.main()
