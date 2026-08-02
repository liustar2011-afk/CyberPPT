from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cyberppt.commands.init_project import init_project
from cyberppt.user_decisions import (
    DECISIONS_ARTIFACT,
    decision_consumption_issues,
    load_user_decisions,
    record_user_decision,
)


class UserDecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "project"
        init_project(self.project)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_decision_is_persisted_and_requires_effectful_consumption(self) -> None:
        record_user_decision(
            self.project,
            decision_id="D001",
            question="跟谁交流？",
            answer="双方决策层",
            applies_to=["audience_concerns", "chapter_emphasis"],
        )
        self.assertEqual("D001", load_user_decisions(self.project)[0]["id"])
        self.assertIn(
            "USER_DECISION_NOT_CONSUMED",
            {item["code"] for item in decision_consumption_issues(decisions=load_user_decisions(self.project), consumed=[])},
        )
        self.assertEqual(
            [],
            decision_consumption_issues(
                decisions=load_user_decisions(self.project),
                consumed=[{"decision_id": "D001", "effect": "将受众关注映射到第一章和第三章"}],
            ),
        )

    def test_record_is_idempotent(self) -> None:
        kwargs = {
            "project": self.project,
            "decision_id": "D001",
            "question": "是否保留源章节顺序？",
            "answer": "保留",
            "applies_to": ["chapter_emphasis"],
        }
        record_user_decision(**kwargs)
        record_user_decision(**kwargs)
        payload = json.loads((self.project / DECISIONS_ARTIFACT).read_text(encoding="utf-8"))
        self.assertEqual(1, len(payload["decisions"]))


if __name__ == "__main__":
    unittest.main()
