from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from cyberppt.commands.script_audit import run_script_audit


VALID_SCRIPT = """## 第8页：第二章：定位、目标与研究边界

- 页面类型：章节过渡页
- 上屏文字：第二章：定位、目标与研究边界

## 第9页：总体定位

- 页面类型：内容页
- 页面标题：总体定位
- 主判断：初步定位为面向行业的公共能力。
- 上屏文字：

  **行业公共能力**

  - 服务行业研判和成果发布。

  **专业系统边界**

  - 保留专业职责和运行边界。

- 证据：S015、S026、S059
- 边界：正式范围待后续确定。
- 视觉结构：公共能力定位与职责边界图。
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


class ScriptAuditCommandTests(unittest.TestCase):
    def test_persists_passed_reports_and_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project, script = _build_project(Path(temp_dir))

            code, report = run_script_audit(project, script)

            self.assertEqual(0, code)
            self.assertEqual("passed", report["status"])
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


if __name__ == "__main__":
    unittest.main()
