from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cyberppt.commands.init_project import init_project
from cyberppt.commands.prepare_stage01_input import prepare_outline_input
from cyberppt.communication_strategy import (
    audience_concern_binding_issues,
    COMMUNICATION_ARTIFACT,
    COMMUNICATION_CONFIRMATION,
    approve_communication_strategy,
    assert_communication_strategy_ready,
    communication_strategy_binding_issues,
    frontstage_posture_issues,
    prepare_communication_strategy,
    run_communication_strategy_audit,
)
from cyberppt.semantic_understanding import (
    SEMANTIC_ARTIFACT,
    approve_semantic_understanding,
    record_semantic_generation,
    run_semantic_understanding_audit,
)
from cyberppt.storyline_director import (
    DIRECTOR_ARTIFACT,
    prepare_storyline_director,
    run_storyline_director_audit,
)
from tests.test_storyline_director import director_payload
from tests.test_semantic_understanding import VALID_SEMANTIC


class CommunicationStrategyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "project"
        init_project(self.project)
        # This fixture intentionally exercises the legacy prose-only semantic
        # handoff; new initialized projects otherwise default to strict mode.
        manifest = self.project / "manifest.yml"
        manifest_text = manifest.read_text(encoding="utf-8")
        manifest_text = manifest_text.replace("  semantic_argument_model: required\n", "")
        manifest_text = manifest_text.replace("  interpretation_contract_mode: strict\n", "")
        manifest.write_text(manifest_text, encoding="utf-8")
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
                    "audience_concerns": [
                        {"id": "AC01", "question": "合作依托是什么？", "source_anchors": ["第一章"], "importance": "required"},
                        {"id": "AC02", "question": "下一步需要决定什么？", "source_anchors": ["第四章"], "importance": "required"},
                    ],
                },
                {
                    "id": "joint_workshop",
                    "label": "联合研讨型",
                    "audience": "双方业务与实施工作组",
                    "communication_purpose": "对齐合作议题、分工和试点条件",
                    "decision_task": "形成联合调研与试点设计输入",
                    "architecture_mode": "solution",
                    "structure_principle": "先建立共同认知，再展开合作议题、分工和研讨问题",
                    "audience_concerns": [
                        {"id": "AC01", "question": "合作依托是什么？", "source_anchors": ["第一章"], "importance": "required"},
                        {"id": "AC02", "question": "下一步需要决定什么？", "source_anchors": ["第四章"], "importance": "required"},
                    ],
                },
            ],
            "recommendation": "decision_review",
        }
        (self.project / COMMUNICATION_ARTIFACT).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return payload

    def _upgrade_candidate_to_v2(self, payload: dict[str, object]) -> dict[str, object]:
        payload["schema"] = "cyberppt.communication_strategy.v2"
        for option in payload["options"]:
            option.update(
                {
                    "frontstage_purpose": "介绍方案内容并围绕适用条件开展同行交流",
                    "backstage_intent": "在充分理解基础上识别未来可能继续合作的议题",
                    "interaction_posture": "peer_exchange",
                    "explicit_audience_action": "理解方案、提出意见并补充实际需求与条件",
                    "forbidden_frontstage_frames": [
                        "共同决策",
                        "批准合作",
                        "先批准",
                    ],
                }
            )
        (self.project / COMMUNICATION_ARTIFACT).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return payload

    def test_init_requires_communication_strategy(self) -> None:
        manifest = (self.project / "manifest.yml").read_text(encoding="utf-8")
        self.assertIn("communication_strategy: required", manifest)
        self.assertIn("storyline_director: required", manifest)
        self.assertTrue((self.project / "workbench/stages/00-communication-strategy").is_dir())
        self.assertTrue((self.project / "workbench/stages/00-storyline-director").is_dir())

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
        self.assertEqual("communication_strategy:joint_workshop", gate["user_decision_id"])
        decisions = json.loads(
            (self.project / "workbench/decisions/user-decisions.json").read_text(encoding="utf-8")
        )["decisions"]
        self.assertIn("communication_strategy:joint_workshop", {item["id"] for item in decisions})

        stage = self.project / "workbench/stages/01-analysis"
        (stage / "source-truth.json").write_text(
            json.dumps({"records": [], "coverage_targets": [], "conclusions": []}),
            encoding="utf-8",
        )
        (stage / "source-truth-audit.json").write_text(
            json.dumps({"status": "passed"}), encoding="utf-8"
        )
        prepared_director = prepare_storyline_director(self.project)
        director = director_payload()
        director["source_truth_sha256"] = prepared_director["source_truth_sha256"]
        director["communication_strategy_approval_sha256"] = prepared_director["communication_strategy_approval_sha256"]
        director["semantic_understanding_sha256"] = prepared_director["semantic_understanding_sha256"]
        director["semantic_source_bundle_sha256"] = prepared_director["semantic_source_bundle_sha256"]
        director["consumed_user_decisions"] = [
            {
                "decision_id": gate["user_decision_id"],
                "effect": "按联合工作组受众关注组织章节与页面",
            }
        ]
        (self.project / DIRECTOR_ARTIFACT).write_text(
            json.dumps(director, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        director_code, _ = run_storyline_director_audit(self.project)
        self.assertEqual(0, director_code)
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
            "user_decision_id": gate["user_decision_id"],
            "audience_concerns": gate["audience_concerns"],
        }
        self.assertEqual([], communication_strategy_binding_issues(outline, gate))
        outline["audience"] = "项目执行人员"
        self.assertTrue(communication_strategy_binding_issues(outline, gate))

    def test_audience_concern_contract_requires_page_consumption(self) -> None:
        self._write_valid_candidate()
        run_communication_strategy_audit(self.project)
        approve_communication_strategy(self.project, "joint_workshop")
        gate = assert_communication_strategy_ready(self.project)
        self.assertIsNotNone(gate)
        missing = audience_concern_binding_issues(
            {"pages": [{"page_type": "content", "page_id": "p01"}]},
            gate,
        )
        self.assertIn("PAGE_AUDIENCE_CONCERNS_MISSING", {item["code"] for item in missing})
        valid = audience_concern_binding_issues(
            {
                "pages": [
                    {"page_type": "content", "page_id": "p01", "audience_concern_ids": ["AC01"], "audience_relevance": "用于回答合作依托问题"},
                    {"page_type": "content", "page_id": "p02", "audience_concern_ids": ["AC02"], "audience_relevance": "用于收束下一步决策"},
                ]
            },
            gate,
        )
        self.assertEqual([], valid)

    def test_options_require_source_anchored_audience_concerns(self) -> None:
        payload = self._write_valid_candidate()
        payload["options"][0]["audience_concerns"] = []
        (self.project / COMMUNICATION_ARTIFACT).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        code, report = run_communication_strategy_audit(self.project)
        self.assertEqual(4, code)
        self.assertIn("AUDIENCE_CONCERNS_INVALID", {item["code"] for item in report["issues"]})

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

    def test_reaudit_timestamp_does_not_invalidate_unchanged_approval(self) -> None:
        self._write_valid_candidate()
        run_communication_strategy_audit(self.project)
        approve_communication_strategy(self.project, "decision_review")

        # A repeat audit rewrites audited_at and therefore changes the audit
        # file hash, but it does not change the reviewed strategy contract.
        run_communication_strategy_audit(self.project)

        self.assertIsNotNone(assert_communication_strategy_ready(self.project))

    def test_new_communication_choice_supersedes_prior_choice(self) -> None:
        self._write_valid_candidate()
        run_communication_strategy_audit(self.project)
        approve_communication_strategy(self.project, "decision_review")
        approve_communication_strategy(self.project, "joint_workshop")
        decisions = json.loads(
            (self.project / "workbench/decisions/user-decisions.json").read_text(encoding="utf-8")
        )["decisions"]
        by_id = {item["id"]: item for item in decisions}
        self.assertEqual("superseded", by_id["communication_strategy:decision_review"]["status"])
        self.assertEqual(
            "communication_strategy:joint_workshop",
            by_id["communication_strategy:decision_review"]["superseded_by"],
        )
        self.assertEqual("approved", by_id["communication_strategy:joint_workshop"]["status"])

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

    def test_v2_requires_distinct_frontstage_and_backstage_contract(self) -> None:
        payload = self._upgrade_candidate_to_v2(self._write_valid_candidate())
        code, report = run_communication_strategy_audit(self.project)
        self.assertEqual(0, code)
        self.assertEqual("confirmation_required", report["status"])

        payload["options"][0]["backstage_intent"] = payload["options"][0]["frontstage_purpose"]
        (self.project / COMMUNICATION_ARTIFACT).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        code, report = run_communication_strategy_audit(self.project)
        self.assertEqual(4, code)
        self.assertIn(
            "FRONTSTAGE_BACKSTAGE_NOT_DISTINCT",
            {item["code"] for item in report["issues"]},
        )

    def test_peer_exchange_blocks_backstage_decision_rhetoric_in_outline(self) -> None:
        self._upgrade_candidate_to_v2(self._write_valid_candidate())
        run_communication_strategy_audit(self.project)
        approve_communication_strategy(self.project, "joint_workshop")
        gate = assert_communication_strategy_ready(self.project)
        self.assertEqual("peer_exchange", gate["interaction_posture"])

        outline = {
            "pages": [
                {
                    "page_id": "p02",
                    "page_type": "agenda",
                    "title": "围绕一次共同决策展开四个问题",
                }
            ]
        }
        issues = frontstage_posture_issues(outline, gate)
        self.assertEqual({"BACKSTAGE_INTENT_SURFACED"}, {item["code"] for item in issues})
        self.assertEqual(["p02"], issues[0]["pages"])

        outline["pages"][0]["title"] = "交流内容"
        outline["pages"][0]["agenda_items"] = ["基础设施介绍", "运营体系规划"]
        self.assertEqual([], frontstage_posture_issues(outline, gate))

    def test_peer_exchange_enforces_platform_posture_even_when_model_omits_phrase(self) -> None:
        payload = self._upgrade_candidate_to_v2(self._write_valid_candidate())
        payload["options"][0]["forbidden_frontstage_frames"] = ["共同决策"]
        payload["options"][0]["explicit_audience_action"] = "请求批准合作方案"
        (self.project / COMMUNICATION_ARTIFACT).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        code, report = run_communication_strategy_audit(self.project)
        self.assertEqual(4, code)
        self.assertIn(
            "COMMUNICATION_POSTURE_SELF_CONTRADICTORY",
            {item["code"] for item in report["issues"]},
        )


if __name__ == "__main__":
    unittest.main()
