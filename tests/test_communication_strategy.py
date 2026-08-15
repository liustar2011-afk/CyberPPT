from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cyberppt.commands.init_project import init_project
from cyberppt.communication_strategy import prepare_communication_strategy

COMMUNICATION_ARTIFACT = Path(
    "workbench/stages/00-communication-strategy/communication-strategy.json"
)


class LightweightCommunicationStrategyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "project"
        init_project(self.project)
        source_units = self.project / "workbench/stages/00-source-map/source-units.jsonl"
        source_units.parent.mkdir(parents=True, exist_ok=True)
        units = [
            {
                "schema": "cyberppt.source_unit.v1",
                "unit_id": "SU-001",
                "source_id": "SRC-001",
                "kind": "heading",
                "source_order": 1,
                "outline_level": 1,
                "heading_path": ["总体定位"],
                "text": "总体定位",
            },
            {
                "schema": "cyberppt.source_unit.v1",
                "unit_id": "SU-002",
                "source_id": "SRC-001",
                "kind": "paragraph",
                "source_order": 2,
                "heading_path": ["总体定位"],
                "text": "平台服务政府决策、行业发展和企业需求，组织资源与应用需求高效衔接。",
            },
            {
                "schema": "cyberppt.source_unit.v1",
                "unit_id": "SU-003",
                "source_id": "SRC-001",
                "kind": "heading",
                "source_order": 3,
                "outline_level": 1,
                "heading_path": ["合作推进建议"],
                "text": "合作推进建议",
            },
            {
                "schema": "cyberppt.source_unit.v1",
                "unit_id": "SU-004",
                "source_id": "SRC-001",
                "kind": "paragraph",
                "source_order": 4,
                "heading_path": ["合作推进建议"],
                "text": "诚邀合作伙伴参与平台合作，共同筛选首期事项并组织真实试点。",
            },
        ]
        source_units.write_text(
            "\n".join(json.dumps(item, ensure_ascii=False) for item in units) + "\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_lightweight_input_is_source_grounded_and_has_no_side_effects(self) -> None:
        files_before = {
            path.relative_to(self.project)
            for path in self.project.rglob("*")
            if path.is_file()
        }

        payload = prepare_communication_strategy(self.project)

        files_after = {
            path.relative_to(self.project)
            for path in self.project.rglob("*")
            if path.is_file()
        }
        self.assertEqual(files_before, files_after)
        self.assertEqual(
            "cyberppt.lightweight_communication_strategy_input.v1",
            payload["schema"],
        )
        self.assertEqual("agent_recommendation_required", payload["status"])
        evidence_ids = {item["unit_id"] for item in payload["decision_evidence"]}
        self.assertEqual({"SU-002", "SU-004"}, evidence_ids)
        instructions = "\n".join(payload["instructions"])
        self.assertEqual(
            "single_source_faithful_direction",
            payload["recommendation_policy"],
        )
        self.assertIn("必须提出一个忠于原稿的交流目标方向", instructions)
        self.assertIn("不得提供多个交流目标选项", instructions)
        self.assertIn("source unit_id/source statement", instructions)
        self.assertIn("不得把用户目标、作者推断或泛化措辞升级为源材料事实", instructions)
        self.assertIn("合作必要性", instructions)
        self.assertNotIn("2-3", instructions)
        self.assertIn("不得直接向用户抛出", instructions)
        self.assertIn("完成作者编辑后的章节与页面提纲", instructions)
        self.assertIn("逐页详细内容", instructions)
        self.assertFalse((self.project / COMMUNICATION_ARTIFACT).exists())

    def test_lightweight_input_requires_registered_source_units(self) -> None:
        (self.project / "workbench/stages/00-source-map/source-units.jsonl").unlink()

        with self.assertRaisesRegex(FileNotFoundError, "prepare-source-map"):
            prepare_communication_strategy(self.project)

    def test_new_project_readme_uses_single_source_faithful_direction(self) -> None:
        readme = (self.project / "README.md").read_text(encoding="utf-8")

        self.assertIn("one source-faithful communication-goal direction", readme)
        self.assertIn("cannot become a source fact or page conclusion", readme)
        self.assertNotIn("2-3 communication-goal options", readme)
        self.assertNotIn("Compare 2-3 routes", readme)


if __name__ == "__main__":
    unittest.main()
