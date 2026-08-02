from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cyberppt.commands.init_project import init_project
from cyberppt.commands.prepare_stage01_input import prepare_outline_input
from cyberppt.communication_strategy import (
    COMMUNICATION_ARTIFACT,
    COMMUNICATION_CONFIRMATION,
    approve_communication_strategy,
    assert_communication_strategy_ready,
    communication_strategy_binding_issues,
    prepare_communication_strategy,
    run_communication_strategy_audit,
)
from cyberppt.semantic_understanding import (
    SEMANTIC_ARTIFACT,
    approve_semantic_understanding,
    record_semantic_generation,
    run_semantic_understanding_audit,
)
from tests.test_semantic_understanding import VALID_SEMANTIC


class CommunicationStrategyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "project"
        init_project(self.project)
        (self.project / "source" / "material.txt").write_text(
            "structured source material", encoding="utf-8"
        )
        (self.project / SEMANTIC_ARTIFACT).write_text(VALID_SEMANTIC, encoding="utf-8")
        record_semantic_generation(self.project, executor="test-runner", model="test-model")
        code, _ = run_semantic_understanding_audit(self.project)
        self.assertEqual(0, code)
        approve_semantic_understanding(self.project, note="approved for test")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write_valid_candidate(self) -> dict[str, object]:
        prepared = prepare_communication_strategy(self.project)
        payload: dict[str, object] = {
            "schema": "cyberppt.communication_strategy.v1",
            "semantic_understanding_sha256": prepared["semantic_understanding_sha256"],
            "semantic_source_bundle_sha256": prepared["semantic_source_bundle_sha256"],
            "audience": "分管领导与合作企业决策层",
            "communication_purpose": "审议合作方向并确认联合调研安排",
            "decision_task": "选择合作推进路径",
            "content_focus": ["合作基础", "运营分工", "场景路径"],
            "options": [
                {
                    "id": "decision_review",
                    "label": "领导审定型",
                    "audience": "中电联与合作企业决策层",
                    "communication_purpose": "审议合作方向并确认联合调研安排",
                    "decision_task": "选择合作推进路径",
                    "architecture_mode": "solution",
                    "structure_principle": "先给出合作判断，再说明基础、方案和下一步决策事项",
                },
                {
                    "id": "joint_workshop",
                    "label": "联合研讨型",
                    "audience": "双方业务与实施工作组",
                    "communication_purpose": "对齐合作议题、分工和试点条件",
                    "decision_task": "形成联合调研与试点设计输入",
                    "architecture_mode": "solution",
                    "structure_principle": "先建立共同认知，再展开合作议题、分工和研讨问题",
                },
            ],
            "recommendation": "decision_review",
        }
        (self.project / COMMUNICATION_ARTIFACT).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return payload

    def test_init_requires_communication_strategy(self) -> None:
        manifest = (self.project / "manifest.yml").read_text(encoding="utf-8")
        self.assertIn("communication_strategy: required", manifest)
        self.assertTrue((self.project / "workbench/stages/00-communication-strategy").is_dir())

    def test_outline_is_blocked_until_user_selects_an_option(self) -> None:
        self._write_valid_candidate()
        code, report = run_communication_strategy_audit(self.project)
        self.assertEqual(0, code)
        self.assertEqual("confirmation_required", report["status"])
        confirmation = (self.project / COMMUNICATION_CONFIRMATION).read_text(encoding="utf-8")
        self.assertIn("请确认这套材料主要与谁沟通", confirmation)
        self.assertIn("领导审定型（推荐）", confirmation)
        with self.assertRaisesRegex(FileNotFoundError, "awaiting user choice"):
            prepare_outline_input(self.project)

    def test_approved_choice_controls_outline_contract(self) -> None:
        payload = self._write_valid_candidate()
        run_communication_strategy_audit(self.project)
        approve_communication_strategy(self.project, "joint_workshop", note="user selected")
        gate = assert_communication_strategy_ready(self.project)
        self.assertIsNotNone(gate)
        self.assertEqual("joint_workshop", gate["option_id"])
        self.assertEqual("联合研讨型", gate["selected_option"]["label"])
        self.assertEqual("双方业务与实施工作组", gate["audience"])

        stage = self.project / "workbench/stages/01-analysis"
        (stage / "source-truth.json").write_text(
            json.dumps({"records": [], "coverage_targets": [], "conclusions": []}),
            encoding="utf-8",
        )
        authoring_input = prepare_outline_input(self.project).read_text(encoding="utf-8")
        self.assertIn("## approved_communication_strategy", authoring_input)
        self.assertIn("reporting_direction: joint_workshop", authoring_input)
        self.assertIn("先建立共同认知，再展开合作议题、分工和研讨问题", authoring_input)

        selected = gate["selected_option"]
        outline = {
            "communication_strategy_sha256": gate["communication_strategy_sha256"],
            "communication_strategy_approval_sha256": gate["communication_strategy_approval_sha256"],
            "audience": selected["audience"],
            "communication_purpose": selected["communication_purpose"],
            "decision_task": selected["decision_task"],
            "reporting_direction": gate["option_id"],
            "architecture_mode": selected["architecture_mode"],
            "structure_principle": selected["structure_principle"],
        }
        self.assertEqual([], communication_strategy_binding_issues(outline, gate))
        outline["audience"] = "项目执行人员"
        self.assertTrue(communication_strategy_binding_issues(outline, gate))

    def test_changed_candidate_invalidates_approval(self) -> None:
        self._write_valid_candidate()
        run_communication_strategy_audit(self.project)
        approve_communication_strategy(self.project, "decision_review")
        artifact = self.project / COMMUNICATION_ARTIFACT
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        payload["audience"] = "新的沟通对象"
        artifact.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "stale"):
            assert_communication_strategy_ready(self.project)

    def test_options_must_be_distinct(self) -> None:
        payload = self._write_valid_candidate()
        payload["options"][1]["structure_principle"] = payload["options"][0]["structure_principle"]
        (self.project / COMMUNICATION_ARTIFACT).write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        code, report = run_communication_strategy_audit(self.project)
        self.assertEqual(4, code)
        self.assertIn(
            "COMMUNICATION_OPTIONS_NOT_DISTINCT",
            {item["code"] for item in report["issues"]},
        )


if __name__ == "__main__":
    unittest.main()
