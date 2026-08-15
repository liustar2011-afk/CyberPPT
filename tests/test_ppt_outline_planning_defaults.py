from __future__ import annotations

import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLANNING_SKILL = ROOT / ".agents" / "skills" / "ppt-outline-planning"
if str(PLANNING_SKILL) not in sys.path:
    sys.path.insert(0, str(PLANNING_SKILL))

from ppt_outline_planning.prepare import build_outline_workpack
from ppt_outline_planning.validate import validate_outline_outputs


def semantic_payloads() -> dict[str, dict[str, object]]:
    return {
        "normalized-facts.json": {
            "artifact_type": "normalized_facts",
            "source": {"source_file": "方案.docx"},
            "facts": [
                {
                    "normalized_fact_id": "NF-0001",
                    "statement": "目 录",
                    "fact_type": "metadata",
                    "verification_status": "verified",
                    "confidence": "high",
                },
                {
                    "normalized_fact_id": "NF-0002",
                    "statement": "建设背景正文。",
                    "fact_type": "background",
                    "verification_status": "verified",
                    "confidence": "high",
                },
            ],
            "conflicts": [],
            "ambiguities": [],
        },
        "concept-base.json": {
            "artifact_type": "concept_base",
            "concepts": [],
        },
        "relation-graph.json": {
            "artifact_type": "relation_graph",
            "relations": [],
        },
        "argument-chain.json": {
            "artifact_type": "argument_chain",
            "source_chain": [],
            "reconstructed_chain": [],
            "diagnostics": [],
        },
        "semantic-report.json": {
            "artifact_type": "semantic_validation_report",
            "status": "ok",
            "counts": {"facts": 2},
            "warnings": [],
        },
    }


def source_structure_payload() -> dict[str, object]:
    return {
        "artifact_type": "source_structure",
        "outline": [
            {
                "section_id": "sec-0001",
                "level": 1,
                "title": "第一章 总体概述",
                "line": 10,
                "children": [
                    {
                        "section_id": "sec-0002",
                        "level": 2,
                        "title": "一、建设背景",
                        "line": 12,
                        "children": [],
                    },
                    {
                        "section_id": "sec-0003",
                        "level": 2,
                        "title": "二、商务报价与收益分配",
                        "line": 20,
                        "children": [],
                    },
                ],
            }
        ],
    }


def valid_locked_outline(
    workpack: dict[str, object],
    *,
    content_title: str = "建设背景",
    content_heading_id: str = "sec-0002",
) -> tuple[dict[str, object], dict[str, object]]:
    binding = workpack["binding"]
    deck = {
        "schema_version": "1.1",
        "artifact_type": "ppt_deck_brief",
        "deck_id": "deck-001",
        "workpack_binding": {
            "request_sha256": binding["request_sha256"],
            "planning_policy_sha256": binding["planning_policy_sha256"],
        },
        "task_understanding": {
            "audience": "政企交流对象",
            "purpose": "汇报建设方案",
            "writing_style_mode": "government_official",
            "source_structure_mode": "locked",
        },
        "deck_strategy": {
            "working_title": "建设方案",
            "core_question": "如何推进方案建设",
            "deck_thesis": "按源材料说明建设安排",
            "page_budget": {"target": 5, "min": 5, "max": 5},
        },
        "sections": [
            {
                "section_id": "S01",
                "page_ids": ["P03", "P04"],
            }
        ],
    }
    plan = {
        "schema_version": "1.1",
        "artifact_type": "ppt_page_plan",
        "deck_id": "deck-001",
        "pages": [
            {
                "page_id": "P01",
                "order": 1,
                "page_type": "template",
                "template_role": "cover",
                "title_intent": "建设方案",
            },
            {
                "page_id": "P02",
                "order": 2,
                "page_type": "template",
                "template_role": "agenda",
                "title_intent": "目录",
            },
            {
                "page_id": "P03",
                "order": 3,
                "page_type": "template",
                "template_role": "section_divider",
                "section_id": "S01",
                "title_intent": "第一章 总体概述",
                "source_heading_ids": ["sec-0001"],
                "primary_source_heading_id": "sec-0001",
            },
            {
                "page_id": "P04",
                "order": 4,
                "page_type": "content",
                "section_id": "S01",
                "title_intent": content_title,
                "source_heading_ids": [content_heading_id],
                "primary_source_heading_id": content_heading_id,
                "audience_question": "源材料如何说明建设背景？",
                "page_mission": "说明建设背景。",
                "key_judgment": "建设背景正文。",
                "non_substitutable_value": "完整承接源材料建设背景。",
                "judgment_basis": "source_explicit",
                "argument_role": "background",
                "must_not_include": ["后续建设内容"],
                "reserved_for_later": [],
                "split_risk": "low",
                "transition_from_previous": "承接总体概述。",
                "transition_to_next": "进入后续章节。",
                "evidence": {
                    "normalized_fact_ids": ["NF-0002"],
                    "relation_ids": [],
                    "argument_node_ids": [],
                },
                "argument_chain": [
                    {
                        "role": "background",
                        "statement": "建设背景正文。",
                        "evidence": {"normalized_fact_ids": ["NF-0002"]},
                    }
                ],
                "evidence_roles": {
                    "claim": ["NF-0002"],
                    "reason": [],
                    "instance": [],
                    "boundary": [],
                    "trace_only": [],
                },
            },
            {
                "page_id": "P05",
                "order": 5,
                "page_type": "template",
                "template_role": "closing",
                "title_intent": "谢谢",
            },
        ],
    }
    return deck, plan


def write_validation_fixture(
    root: Path,
    payloads: dict[str, dict[str, object]],
    workpack: dict[str, object],
    deck: dict[str, object],
    plan: dict[str, object],
) -> tuple[Path, Path]:
    semantic_dir = root / "semantic"
    outline_dir = root / "outline"
    semantic_dir.mkdir(parents=True)
    outline_dir.mkdir(parents=True)
    for name, payload in payloads.items():
        (semantic_dir / name).write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
    for name, payload in (
        ("outline-workpack.json", workpack),
        ("deck-brief.json", deck),
        ("page-plan.json", plan),
    ):
        (outline_dir / name).write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
    return semantic_dir, outline_dir


class OutlineWorkpackDefaultTests(unittest.TestCase):
    def test_default_workpack_locks_government_style_and_source_structure(self) -> None:
        workpack = build_outline_workpack(
            semantic_payloads(),
            source_structure=source_structure_payload(),
        )

        policy = workpack["planning_policy"]
        self.assertEqual("government_official", policy["writing_style_mode"])
        self.assertEqual("locked", policy["source_structure_mode"])
        self.assertEqual("locked", policy["source_title_mode"])
        self.assertEqual("locked", policy["source_order_mode"])
        self.assertEqual("preserve", policy["source_content_mode"])
        self.assertTrue(policy["capacity_split_allowed"])
        self.assertTrue(policy["duplicate_content_merge_allowed"])
        self.assertTrue(policy["reframing_requires_explicit_user_request"])
        self.assertEqual("source_sections_only", policy["agenda_mode"])
        self.assertEqual("sec-0001", workpack["source_heading_outline"][0]["section_id"])
        self.assertEqual("sec-0002", workpack["source_heading_outline"][1]["section_id"])
        self.assertEqual("目录", workpack["source_metadata"]["agenda_title"])
        self.assertTrue(workpack["binding"]["request_sha256"])
        self.assertTrue(workpack["binding"]["planning_policy_sha256"])

    def test_explicit_consulting_request_can_unlock_structure(self) -> None:
        workpack = build_outline_workpack(
            semantic_payloads(),
            request_text="请重构叙事并改为咨询式表达",
            source_structure=source_structure_payload(),
        )

        policy = workpack["planning_policy"]
        self.assertEqual("consulting", policy["writing_style_mode"])
        self.assertEqual("flexible", policy["source_structure_mode"])
        self.assertEqual("flexible", policy["source_title_mode"])
        self.assertEqual("flexible", policy["source_order_mode"])

    def test_negated_reframing_request_keeps_source_lock(self) -> None:
        workpack = build_outline_workpack(
            semantic_payloads(),
            request_text="不要重构叙事，老老实实按原文写",
            source_structure=source_structure_payload(),
        )

        policy = workpack["planning_policy"]
        self.assertEqual("government_official", policy["writing_style_mode"])
        self.assertEqual("locked", policy["source_structure_mode"])


class LockedOutlineValidationTests(unittest.TestCase):
    def _validate(
        self,
        *,
        mutate_workpack=None,
        mutate_deck=None,
        mutate_plan=None,
        mutate_semantic=None,
    ) -> dict[str, object]:
        payloads = semantic_payloads()
        workpack = build_outline_workpack(
            payloads,
            source_structure=source_structure_payload(),
        )
        deck, plan = valid_locked_outline(workpack)
        if mutate_workpack:
            mutate_workpack(workpack)
        if mutate_deck:
            mutate_deck(deck)
        if mutate_plan:
            mutate_plan(plan)
        if mutate_semantic:
            mutate_semantic(payloads)
        with tempfile.TemporaryDirectory() as directory:
            semantic_dir, outline_dir = write_validation_fixture(
                Path(directory), payloads, workpack, deck, plan
            )
            return validate_outline_outputs(semantic_dir, outline_dir)

    def test_valid_source_locked_outline_passes(self) -> None:
        report = self._validate()
        self.assertEqual("ok", report["status"])

    def test_stale_workpack_is_rejected(self) -> None:
        def mutate(payloads):
            payloads["normalized-facts.json"]["facts"][1]["statement"] = "已经变化。"

        report = self._validate(mutate_semantic=mutate)
        self.assertIn(
            "stale_outline_workpack",
            {item["code"] for item in report["errors"]},
        )

    def test_tampered_workpack_policy_binding_is_rejected(self) -> None:
        def mutate(workpack):
            workpack["planning_policy"]["writing_style_mode"] = "consulting"

        report = self._validate(mutate_workpack=mutate)
        self.assertIn(
            "invalid_workpack_binding",
            {item["code"] for item in report["errors"]},
        )

    def test_deck_must_bind_to_current_workpack(self) -> None:
        def mutate(deck):
            deck["workpack_binding"]["request_sha256"] = "stale-request"

        report = self._validate(mutate_deck=mutate)
        self.assertIn(
            "workpack_binding_mismatch",
            {item["code"] for item in report["errors"]},
        )

    def test_deck_policy_must_match_locked_workpack(self) -> None:
        def mutate(deck):
            deck["task_understanding"]["writing_style_mode"] = "consulting"

        report = self._validate(mutate_deck=mutate)
        self.assertIn(
            "planning_policy_mismatch",
            {item["code"] for item in report["errors"]},
        )

    def test_changed_agenda_title_is_rejected(self) -> None:
        def mutate(plan):
            plan["pages"][1]["title_intent"] = "四个合作问题构成交流路径"

        report = self._validate(mutate_plan=mutate)
        self.assertIn(
            "invalid_locked_agenda_title",
            {item["code"] for item in report["errors"]},
        )

    def test_changed_source_heading_title_is_rejected(self) -> None:
        def mutate(plan):
            plan["pages"][3]["title_intent"] = "跨主体协同需求正在增长"

        report = self._validate(mutate_plan=mutate)
        self.assertIn(
            "source_heading_title_mismatch",
            {item["code"] for item in report["errors"]},
        )

    def test_source_heading_order_regression_is_rejected(self) -> None:
        def mutate(plan):
            plan["pages"][2]["title_intent"] = "二、商务报价与收益分配"
            plan["pages"][2]["source_heading_ids"] = ["sec-0003"]
            plan["pages"][2]["primary_source_heading_id"] = "sec-0003"

        report = self._validate(mutate_plan=mutate)
        self.assertIn(
            "source_heading_order_regression",
            {item["code"] for item in report["errors"]},
        )

    def test_capacity_split_keeps_same_source_heading(self) -> None:
        def mutate(deck):
            deck["deck_strategy"]["page_budget"] = {"target": 6, "min": 6, "max": 6}
            deck["sections"][0]["page_ids"] = ["P03", "P04", "P05"]

        def mutate_plan(plan):
            duplicate = dict(plan["pages"][3])
            duplicate["page_id"] = "P05"
            duplicate["order"] = 5
            duplicate["title_intent"] = "建设背景（二）"
            closing = plan["pages"][4]
            closing["page_id"] = "P06"
            closing["order"] = 6
            plan["pages"].insert(4, duplicate)

        report = self._validate(mutate_deck=mutate, mutate_plan=mutate_plan)
        self.assertEqual("ok", report["status"])

    def _validate_with_extra_fact(
        self,
        *,
        fact: dict[str, object],
        mutate_plan=None,
    ) -> dict[str, object]:
        payloads = semantic_payloads()
        payloads["normalized-facts.json"]["facts"].append(fact)
        workpack = build_outline_workpack(
            payloads,
            source_structure=source_structure_payload(),
        )
        deck, plan = valid_locked_outline(workpack)
        if mutate_plan:
            mutate_plan(deck, plan)
        with tempfile.TemporaryDirectory() as directory:
            semantic_dir, outline_dir = write_validation_fixture(
                Path(directory), payloads, workpack, deck, plan
            )
            return validate_outline_outputs(semantic_dir, outline_dir)

    @staticmethod
    def _requirement_fact(fact_id: str = "nf-005") -> dict[str, object]:
        return {
            "normalized_fact_id": fact_id,
            "statement": "复杂业务需要跨主体组织多类能力。",
            "fact_type": "requirement",
            "verification_status": "unverified",
            "confidence": "high",
            "source_assertion_ids": ["fact-0003"],
            "evidence": [{"fact_id": "fact-0003", "block_id": "blk-0003", "line_start": 14, "line_end": 14}],
        }

    def _add_later_content_page(
        self,
        plan: dict[str, object],
        *,
        fact_id: str,
        source_heading_id: str = "sec-0003",
    ) -> None:
        page = deepcopy(plan["pages"][3])
        page.update(
            {
                "page_id": "P05",
                "order": 5,
                "page_type": "content",
                "title_intent": "二、商务报价与收益分配",
                "source_heading_ids": [source_heading_id],
                "primary_source_heading_id": source_heading_id,
                "evidence": {"normalized_fact_ids": [fact_id], "relation_ids": [], "argument_node_ids": []},
                "argument_chain": [{"role": "claim", "statement": "页面承接该事实。", "evidence": {"normalized_fact_ids": [fact_id]}}],
                "evidence_roles": {"claim": [fact_id], "reason": [], "instance": [], "boundary": [], "trace_only": []},
            }
        )
        plan["pages"][4] = page

    def test_uncovered_important_normalized_fact_blocks_outline(self) -> None:
        report = self._validate_with_extra_fact(fact=self._requirement_fact())

        self.assertEqual("error", report["status"])
        self.assertIn(
            "uncovered_important_normalized_fact",
            {item["code"] for item in report["errors"]},
        )
        self.assertEqual(
            ["nf-005"],
            report["coverage"]["unresolved_fact_ids"],
        )

    def test_cross_page_fact_requires_explicit_page_ownership(self) -> None:
        def mutate_plan(deck, plan):
            deck["sections"][0]["page_ids"] = ["P03", "P04", "P05"]
            self._add_later_content_page(plan, fact_id="nf-007")

        report = self._validate_with_extra_fact(
            fact=self._requirement_fact("nf-007"),
            mutate_plan=mutate_plan,
        )

        self.assertIn(
            "cross_page_fact_ownership_missing",
            {item["code"] for item in report["errors"]},
        )

    def test_explicit_page_ownership_resolves_cross_page_fact(self) -> None:
        def mutate_plan(deck, plan):
            deck["sections"][0]["page_ids"] = ["P03", "P04", "P05"]
            self._add_later_content_page(plan, fact_id="nf-007")
            plan["fact_dispositions"] = [
                {
                    "normalized_fact_id": "nf-007",
                    "disposition": "page",
                    "page_ids": ["P05"],
                    "rationale": "页面明确承接建设背景中的协同要求。",
                }
            ]

        report = self._validate_with_extra_fact(
            fact=self._requirement_fact("nf-007"),
            mutate_plan=mutate_plan,
        )

        self.assertEqual("ok", report["status"])
        item = next(item for item in report["coverage"]["items"] if item["normalized_fact_id"] == "nf-007")
        self.assertEqual("page", item["disposition"])

    def test_explicit_deferred_to_later_page_resolves_unassigned_fact(self) -> None:
        def mutate_plan(deck, plan):
            plan["fact_dispositions"] = [
                {
                    "normalized_fact_id": "nf-005",
                    "disposition": "deferred_to",
                    "deferred_to": "P05",
                    "rationale": "后页承接该能力要求。",
                }
            ]

        report = self._validate_with_extra_fact(
            fact=self._requirement_fact("nf-005"),
            mutate_plan=mutate_plan,
        )

        self.assertEqual("ok", report["status"])
        item = next(item for item in report["coverage"]["items"] if item["normalized_fact_id"] == "nf-005")
        self.assertEqual("deferred_to", item["disposition"])
        self.assertEqual("P05", item["deferred_to"])

    def test_explicit_shared_ownership_resolves_cross_page_fact(self) -> None:
        def mutate_plan(deck, plan):
            deck["sections"][0]["page_ids"] = ["P03", "P04", "P05"]
            self._add_later_content_page(plan, fact_id="NF-0002")
            plan["fact_dispositions"] = [
                {
                    "normalized_fact_id": "nf-005",
                    "disposition": "deferred_to",
                    "deferred_to": "P05",
                    "rationale": "测试额外事实留待后页。",
                },
                {
                    "normalized_fact_id": "NF-0002",
                    "disposition": "shared",
                    "page_ids": ["P04", "P05"],
                    "rationale": "前页说明背景，后页承接平台回应。",
                }
            ]

        report = self._validate_with_extra_fact(
            fact=self._requirement_fact("nf-005"),
            mutate_plan=mutate_plan,
        )

        self.assertEqual("ok", report["status"])
        item = next(item for item in report["coverage"]["items"] if item["normalized_fact_id"] == "NF-0002")
        self.assertEqual("shared", item["disposition"])


if __name__ == "__main__":
    unittest.main()
