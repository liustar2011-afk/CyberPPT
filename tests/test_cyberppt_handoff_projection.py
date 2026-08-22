from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HANDOFF_SKILL = ROOT / ".agents" / "skills" / "cyberppt-handoff"
if str(HANDOFF_SKILL) not in sys.path:
    sys.path.insert(0, str(HANDOFF_SKILL))

from cyberppt_handoff.outline_projection import _content_units_from_source_truth, _project_outline
from cyberppt_handoff.semantic_projection import _project_semantic_model
from cyberppt_handoff.source_projection import _anchors


class HandoffProjectionTests(unittest.TestCase):
    def test_markdown_table_anchors_keep_cells_without_markup(self) -> None:
        anchors = _anchors("| **近期策略** | 首期聚焦真实客户、真实交付和真实成本 |", [])

        self.assertEqual(["近期策略", "首期聚焦真实客户、真实交付和真实成本"], anchors)

    def test_content_units_are_atomic_source_truth_records(self) -> None:
        source_truth = {
            "ST-001": {
                "statement": "首期聚焦真实客户、真实交付和真实成本。",
                "priority": "P0",
                "argument_duty": "driver",
            },
            "ST-002": {
                "statement": "后续范围待合作方确认。",
                "priority": "P2",
                "argument_duty": "boundary",
            },
        }
        units = _content_units_from_source_truth(
            "p01",
            ["ST-001", "ST-002"],
            [
                {"role": "reason", "source_refs": ["ST-001"]},
                {"role": "trace_only", "source_refs": ["ST-002"]},
            ],
            source_truth,
        )

        self.assertEqual(["ST-001", "ST-002"], [unit["source_refs"][0] for unit in units])
        self.assertEqual(["P0", "P2"], [unit["priority"] for unit in units])
        self.assertTrue(units[0]["onscreen_required"])
        self.assertFalse(units[1]["onscreen_required"])
        self.assertFalse(units[1]["full_prose_required"])

    def test_source_arguments_keep_primary_consumer_requirement(self) -> None:
        payloads = {
            "argument": {
                "source_chain": [],
                "reconstructed_chain": [{
                    "node_id": "ARG-001",
                    "role": "driver",
                    "statement": "真实交付验证首期合作可行性。",
                    "section_ids": ["sec-001"],
                    "normalized_fact_ids": ["NF-001"],
                }],
            },
            "structure": {"outline": [{"section_id": "sec-001", "title": "合作验证", "children": []}]},
            "deck": {"deck_strategy": {}, "task_understanding": {}},
            "page_plan": {"pages": [{
                "page_id": "P01",
                "order": 1,
                "page_type": "content",
                "title_intent": "首期验证重点",
                "section_id": "S01",
                "importance": "high",
                "evidence": {"normalized_fact_ids": ["NF-001"], "argument_node_ids": ["ARG-001"]},
            }]},
            "normalized": {"facts": [{
                "normalized_fact_id": "NF-001",
                "evidence": [{"block_id": "blk-001"}],
            }]},
            "concepts": {"concepts": []},
            "relations": {"relations": []},
        }

        model = _project_semantic_model(payloads, {"NF-001": "ST-001"}, {"blk-001": "SU-001"}, {"sec-001": "SU-H001"})
        nodes = {node["id"]: node for node in model["subsection_nodes"]}

        self.assertTrue(nodes["ARG-001"]["required_for_primary_consumer"])
        self.assertFalse(nodes["L4-P01"]["required_for_primary_consumer"])

    def test_page_can_partially_consume_a_source_argument(self) -> None:
        payloads = {
            "deck": {"deck_strategy": {}, "task_understanding": {}, "sections": []},
            "page_plan": {"pages": [{
                "page_id": "P01",
                "order": 1,
                "page_type": "content",
                "title_intent": "首期验证重点",
                "key_judgment": "以真实交付形成首期判断。",
                "argument_role": "support",
                "judgment_basis": "source_explicit",
                "evidence": {"normalized_fact_ids": ["NF-001"], "argument_node_ids": ["ARG-001"]},
                "evidence_roles": {"claim": ["NF-001"]},
                "argument_chain": [],
            }]},
            "workpack": {"planning_policy": {}},
            "argument": {"source_chain": [], "reconstructed_chain": [{
                "node_id": "ARG-001", "normalized_fact_ids": ["NF-001", "NF-002"],
            }]},
            "relations": {"relations": []},
            "concepts": {"concepts": []},
        }
        source_truth = {"records": [{
            "id": "ST-001", "statement": "以真实交付形成首期判断。", "priority": "P0", "argument_duty": "driver",
        }]}
        semantic_model = {"section_nodes": [], "subsection_nodes": [{"id": "ARG-001"}, {"id": "L4-P01"}]}

        outline, _ = _project_outline(payloads, source_truth, semantic_model, {"NF-001": "ST-001"})
        page = outline["pages"][0]

        self.assertEqual("L4-P01", page["primary_argument_node_id"])
        self.assertEqual(["L4-P01", "ARG-001"], page["source_argument_node_ids"])
        self.assertEqual(["ARG-001"], page["source_argument_primary_node_ids"])
        self.assertEqual([], page["source_evidence_node_ids"])
