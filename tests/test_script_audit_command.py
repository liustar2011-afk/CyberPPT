from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cyberppt.commands.script_audit import run_script_audit
from cyberppt.script_quality_contract import ScriptQualityIssue


VALID_SCRIPT = """## 第8页：第二章：定位、目标与服务组织

- 页面类型：章节过渡页
- 上屏文字：第二章：定位、目标与服务组织

## 第9页：总体定位

- 页面类型：内容页
- 页面标题：总体定位
- 主判断：初步定位为面向行业的公共能力。
- 完整文字稿：中电联面向行业的电力供需形势预测与预警公共能力，覆盖主要预测对象、多时间尺度和多类成果，并由统一数据治理、组合模型、专家会商、成果生产与安全运行支撑。该定位用于明确研究方向与服务对象，也为后续行业数据服务、专题研判和成果运营建立共同的业务范围。

职责分工上，重点处理全国、区域、省级和重点行业供需形势分析，服务履职与行业共用；通过统一口径、跨区域协同和可追溯成果管理提升研判效率，形成面向研究、履职和行业共用的稳定工作机制。

实际工作中还要持续校准数据口径、验证预测结果、记录预警依据，并将专题研判转化为可复用的成果资产和服务流程，保证不同区域、不同时间尺度之间能够比较和追踪；相关成果还应支持复盘、更新和跨部门协同，形成从数据到判断、从判断到服务的连续链条，同时与电网实时调度控制、市场出清、企业生产计划和具体投资决策等专业系统保持清晰分工。
- 文字稿取舍说明：
  - 必留上屏：公共能力定位、服务对象和专业职责分工。
  - 仅讲解：职责分工与支撑机制。
  - 仅追溯：邻页目标框架与任务安排。
- 证据映射：公共能力定位→S015；职责分工与不替代边界→S026；会商与支撑机制→S059
- 上屏文字：

行业公共能力

    服务对象：电力行业供需形势预测与预警。
    支撑机制：统一数据治理、组合模型和专家会商。
    服务范围：覆盖全国、区域、省级和重点行业供需分析。

专业职责分工

    协同方式：与调度、出清和企业计划保持专业分工。
    运行机制：统一口径、成果管理和跨区域协同。

- 证据：S015、S026、S059
- 边界：正式范围经摸底验证后确定。
- 视觉结构：公共能力定位与职责分工图。
- 讲解提示：说明公共能力如何支撑行业研判与专业协同。

【演讲者备注】

建设定位是面向行业的电力供需形势预测与预警公共能力，覆盖主要对象与多类成果，并由数据、模型、会商和成果生产支撑。

同时与调度、出清和企业计划等专业系统保持清晰分工。
"""


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _build_project(root: Path, script_text: str = VALID_SCRIPT) -> tuple[Path, Path]:
    project = root / "project"
    analysis = project / "workbench" / "stages" / "01-analysis"
    script = project / "workbench" / "scripts" / "drafts" / "batch.md"
    script.parent.mkdir(parents=True, exist_ok=True)
    # Keep the shared fixture above the repository's current reading-density
    # gate while preserving the business meaning used by the tests.
    script_text = script_text.replace(
        "等专业系统。",
        "等专业系统。后续成果还应支持周期性复盘和运营更新，并对数据口径、预测结果、预警依据和成果版本保留可追溯记录，使不同地区、不同时间尺度和不同使用场景的分析结果具备可比较性与可复核性。",
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
                    "title": "第二章：定位、目标与服务组织",
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
                    "statement": "中电联面向行业的电力供需形势预测与预警公共能力。",
                },
                {
                    "id": "S026",
                    "type": "B",
                    "status": "研究边界",
                    "statement": "统一数据治理、组合模型、专家会商。",
                },
                {
                    "id": "S059",
                    "type": "B",
                    "status": "研究边界",
                    "statement": "相关成果支持复盘、更新和跨部门协同。",
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


class ProhibitedContrastTests(unittest.TestCase):
    def test_rejects_not_but_contrast_in_authored_copy(self) -> None:
        from cyberppt.script_quality_contract import _prohibited_contrast_hits

        self.assertEqual(
            ("不是内部工具，而是",),
            _prohibited_contrast_hits("建设定位不是内部工具，而是行业公共能力。"),
        )

    def test_rejects_inverse_negated_contrast_markers(self) -> None:
        from cyberppt.script_quality_contract import _prohibited_contrast_hits

        cases = (
            ("服务目标面向持续运营，而非一次性交付。", "而非"),
            ("建设对象是行业公共能力，而不是内部工具。", "而不是"),
        )
        for text, marker in cases:
            with self.subTest(marker=marker):
                self.assertTrue(
                    any(marker in hit for hit in _prohibited_contrast_hits(text))
                )

    def test_rejects_negated_contrast_split_across_lines(self) -> None:
        from cyberppt.script_quality_contract import _prohibited_contrast_hits

        cases = (
            ("建设定位不是内部工具，\n而是行业公共能力。", "不是"),
            ("工作重点不在于单项交付，\n而在于形成持续运营能力。", "不在于"),
        )
        for text, marker in cases:
            with self.subTest(marker=marker):
                self.assertTrue(
                    any(marker in hit for hit in _prohibited_contrast_hits(text))
                )

    def test_does_not_reject_noncontrast_negation_terms(self) -> None:
        from cyberppt.script_quality_contract import _prohibited_contrast_hits

        self.assertEqual(
            (),
            _prohibited_contrast_hits("非结构化数据纳入统一目录并完成治理。"),
        )
        self.assertEqual(
            (),
            _prohibited_contrast_hits("不仅覆盖数据接入，而且覆盖服务运营。"),
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
    def test_lightweight_check_has_no_gate_or_persistence_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project, script = _build_project(Path(temp_dir))
            ledger = project / "workbench" / "artifact-ledger.json"
            ledger_before = ledger.read_bytes()

            code, report = run_script_audit(project, script)

            self.assertEqual(0, code)
            self.assertEqual("cyberppt.script_check.v1", report["schema"])
            self.assertFalse(report["persisted"])
            self.assertFalse(
                (project / "workbench" / "scripts" / "audits").exists()
            )
            self.assertEqual(ledger_before, ledger.read_bytes())

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


if __name__ == "__main__":
    unittest.main()
