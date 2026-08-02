from __future__ import annotations

import unittest

from cyberppt.storyline_director import _audit_issues, storyline_director_binding_issues


def director_payload() -> dict[str, object]:
    return {
        "schema": "cyberppt.storyline_director.v1",
        "source_truth_sha256": "source-hash",
        "communication_strategy_approval_sha256": "approval-hash",
        "theme": "围绕合作启动组织材料",
        "decision_destination": "决定是否启动联合调研与试点",
        "story_arc": ["合作凭什么启动", "服务如何运营", "双方如何合作", "如何启动"],
        "chapter_missions": [
            {"chapter_id": "c1", "title": "合作基础", "question": "凭什么启动？", "contribution": "形成基础判断", "transition_to_next": "转入运营", "max_content_pages": 5},
            {"chapter_id": "c2", "title": "运营体系", "question": "如何运营？", "contribution": "形成运营判断", "transition_to_next": "转入合作", "max_content_pages": 7},
        ],
        "selection_rules": ["只选直接回答主题的问题", "P0形成页面", "P2保留为细节"],
        "exclusion_rules": ["不映射材料目录", "不提升边界", "不制造清单墙"],
        "page_rules": ["每页一个使命", "每页一个核心含义", "明确前后承接", "保留来源关系"],
        "pacing": {"target_total_pages": 24, "min_total_pages": 20, "max_total_pages": 28},
    }


class StorylineDirectorTests(unittest.TestCase):
    def test_valid_director_contract_passes(self) -> None:
        self.assertEqual([], _audit_issues(director_payload(), "source-hash", "approval-hash"))

    def test_director_requires_real_question_chain_and_pacing(self) -> None:
        payload = director_payload()
        payload["story_arc"] = ["只有一步"]
        payload["pacing"] = {"target_total_pages": 30, "min_total_pages": 20, "max_total_pages": 25}
        codes = {issue["code"] for issue in _audit_issues(payload, "source-hash", "approval-hash")}
        self.assertIn("DIRECTOR_RULESET_INVALID", codes)
        self.assertIn("DIRECTOR_PACING_INVALID", codes)

    def test_outline_must_copy_hash_and_director_contract_exactly(self) -> None:
        payload = director_payload()
        gate = {
            "storyline_director_sha256": "director-hash",
            "outline_contract": {key: payload[key] for key in ("theme", "decision_destination", "story_arc", "chapter_missions", "selection_rules", "exclusion_rules", "page_rules", "pacing")},
        }
        self.assertEqual([], storyline_director_binding_issues({"storyline_director_sha256": "director-hash", "storyline": gate["outline_contract"]}, gate))
        self.assertEqual(
            {"STORYLINE_DIRECTOR_NOT_BOUND", "STORYLINE_CONTRACT_DRIFTED"},
            {issue["code"] for issue in storyline_director_binding_issues({}, gate)},
        )


if __name__ == "__main__":
    unittest.main()
