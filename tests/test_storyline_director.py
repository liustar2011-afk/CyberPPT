from __future__ import annotations

import unittest

from cyberppt.storyline_director import _audit_issues, storyline_director_binding_issues


def director_payload() -> dict[str, object]:
    return {
        "schema": "cyberppt.storyline_director.v1",
        "source_truth_sha256": "source-hash",
        "communication_strategy_approval_sha256": "approval-hash",
        "semantic_understanding_sha256": "semantic-hash",
        "semantic_source_bundle_sha256": "semantic-source-hash",
        "theme": "围绕合作启动组织材料",
        "decision_destination": "决定是否启动联合调研与试点",
        "story_arc": ["合作凭什么启动", "服务如何运营", "双方如何合作", "如何启动"],
        "chapter_missions": [
            {"chapter_id": "c1", "title": "合作基础", "question": "凭什么启动？", "contribution": "形成基础判断", "transition_to_next": "转入运营", "max_content_pages": 5, "source_mission": "说明源材料中的合作依托", "source_question": "合作依托是什么？", "source_section_refs": ["source-section-c1"], "source_claim_ids": ["S001"], "audience_concern_ids": ["AC01"], "editorial_operation": "compress"},
            {"chapter_id": "c2", "title": "运营体系", "question": "如何运营？", "contribution": "形成运营判断", "transition_to_next": "转入合作", "max_content_pages": 7, "source_mission": "说明源材料中的运营体系", "source_question": "服务如何运营？", "source_section_refs": ["source-section-c2"], "source_claim_ids": ["S002"], "audience_concern_ids": ["AC02"], "editorial_operation": "compress"},
        ],
        "selection_rules": ["只选直接回答主题的问题", "P0形成页面", "P2保留为细节"],
        "exclusion_rules": ["不映射材料目录", "不提升边界", "不制造清单墙"],
        "page_rules": ["每页一个使命", "每页一个核心含义", "明确前后承接", "保留来源关系"],
        "pacing": {"target_total_pages": 24, "min_total_pages": 20, "max_total_pages": 28},
        "audience_concerns": [
            {"id": "AC01", "question": "合作依托是什么？", "source_anchors": ["第一章"], "importance": "required"},
            {"id": "AC02", "question": "下一步需要决定什么？", "source_anchors": ["第四章"], "importance": "required"},
        ],
        "consumed_user_decisions": [
            {"decision_id": "communication_strategy:joint_workshop", "effect": "按受众问题组织章节与页面"}
        ],
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

    def test_director_cannot_pass_without_semantic_and_audience_bindings(self) -> None:
        payload = director_payload()
        payload.pop("semantic_understanding_sha256")
        payload["audience_concerns"] = []
        codes = {
            issue["code"]
            for issue in _audit_issues(
                payload,
                "source-hash",
                "approval-hash",
                semantic_hash="semantic-hash",
                semantic_source_hash="semantic-source-hash",
                audience_concerns=director_payload()["audience_concerns"],
            )
        }
        self.assertIn("DIRECTOR_SEMANTIC_BINDING_STALE", codes)
        self.assertIn("DIRECTOR_AUDIENCE_CONCERNS_NOT_BOUND", codes)

    def test_strict_director_must_bind_source_map_bundle(self) -> None:
        payload = director_payload()

        codes = {
            issue["code"]
            for issue in _audit_issues(
                payload,
                "source-hash",
                "approval-hash",
                semantic_source_map_hash="source-map-hash",
            )
        }

        self.assertIn("DIRECTOR_SEMANTIC_BINDING_STALE", codes)

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

    def test_semantic_director_must_copy_source_roles_and_weights(self) -> None:
        payload = director_payload()
        for mission in payload["chapter_missions"]:
            mission.update(
                {
                    "source_argument_node_ids": [mission["chapter_id"]],
                    "source_argument_node_roles": {mission["chapter_id"]: "foundation"},
                    "source_argument_node_weights": {mission["chapter_id"]: "supporting"},
                }
            )
        codes = {
            issue["code"]
            for issue in _audit_issues(
                payload,
                "source-hash",
                "approval-hash",
                semantic_hash="semantic-hash",
                semantic_source_hash="semantic-source-hash",
                semantic_argument_model_hash="argument-model-hash",
                semantic_argument_node_ids={"c1", "c2"},
                semantic_argument_node_roles={"c1": "capability", "c2": "advantage"},
                semantic_argument_node_weights={"c1": "core", "c2": "core"},
            )
        }
        self.assertIn("DIRECTOR_ARGUMENT_ROLE_DRIFTED", codes)
        self.assertIn("DIRECTOR_ARGUMENT_WEIGHT_DRIFTED", codes)


if __name__ == "__main__":
    unittest.main()
