from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLANNING_SKILL = ROOT / ".agents" / "skills" / "ppt-outline-planning"
TESTS = ROOT / "tests"
if str(PLANNING_SKILL) not in sys.path:
    sys.path.insert(0, str(PLANNING_SKILL))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from ppt_outline_planning.authoring_spec import prepare_authoring_spec
from ppt_outline_planning.generate import generate_outline
from ppt_outline_planning.pipeline import run_outline_pipeline
from ppt_outline_planning.prepare import build_outline_workpack
from ppt_outline_planning.validate import validate_outline_outputs
from test_ppt_outline_planning_defaults import (
    semantic_payloads,
    source_structure_payload,
)


def _write_foundation(root: Path) -> tuple[Path, Path]:
    semantic_dir = root / "semantic"
    outline_dir = root / "outline"
    semantic_dir.mkdir()
    outline_dir.mkdir()
    payloads = semantic_payloads()
    payloads["normalized-facts.json"]["facts"].append(
        {
            "normalized_fact_id": "NF-0003",
            "statement": "商务报价与收益分配正文。",
            "fact_type": "process",
            "verification_status": "verified",
            "confidence": "high",
            "source_assertion_ids": ["fact-0003"],
            "evidence": [
                {"fact_id": "fact-0003", "block_id": "blk-0003", "line_start": 20, "line_end": 20}
            ],
        }
    )
    payloads["argument-chain.json"]["source_chain"] = [
        {
            "node_id": "ARG-0001",
            "order": 1,
            "role": "context",
            "statement": "建设背景正文形成源材料论证起点。",
            "section_ids": ["sec-0002"],
            "normalized_fact_ids": ["NF-0002"],
        }
    ]
    workpack = build_outline_workpack(
        payloads,
        source_structure=source_structure_payload(),
        request_text="面向合作方说明建设背景与服务安排。",
    )
    for name, payload in payloads.items():
        (semantic_dir / name).write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
    (outline_dir / "outline-workpack.json").write_text(
        json.dumps(workpack, ensure_ascii=False), encoding="utf-8"
    )
    return semantic_dir, outline_dir


def _authored_page(judgment: str) -> dict[str, object]:
    return {
        "audience_question": "本节需要确认什么建设判断？",
        "page_mission": "承接本节源材料并明确页面边界。",
        "key_judgment": judgment,
        "non_substitutable_value": "保留本节在全篇中的独立业务判断。",
        "judgment_basis": "source_explicit",
        "argument_role": "background",
        "must_not_include": ["后续章节的独立安排"],
        "reserved_for_later": [],
        "split_risk": "low",
        "transition_from_previous": "承接上一页。",
        "transition_to_next": "交给下一页。",
        "excluded_from_onscreen": [],
        "authoring_decisions": {
            "deletion_test": "删除本页将丢失本节独立判断。",
            "evidence_selection": "只保留直接支撑本页判断的证据。",
            "attachment_disposition": "not_applicable",
        },
    }


def _write_attachment_foundation(root: Path) -> tuple[Path, Path]:
    semantic_dir, outline_dir = _write_foundation(root)
    payloads = {
        name: json.loads((semantic_dir / name).read_text(encoding="utf-8"))
        for name in ("normalized-facts.json", "concept-base.json", "relation-graph.json", "argument-chain.json", "semantic-report.json")
    }
    payloads["normalized-facts.json"]["facts"].append(
        {
            "normalized_fact_id": "NF-0004",
            "statement": "附件登记事项保留为追溯输入。",
            "fact_type": "attachment_content",
            "verification_status": "verified",
            "confidence": "high",
            "evidence": [{"fact_id": "fact-0004", "block_id": "blk-0004", "line_start": 30, "line_end": 30}],
        }
    )
    structure = source_structure_payload()
    structure["outline"].append(
        {"section_id": "sec-0004", "level": 1, "title": "附件一 资源登记要点", "line": 30, "children": []}
    )
    workpack = build_outline_workpack(payloads, source_structure=structure, request_text="说明正式方案")
    (semantic_dir / "normalized-facts.json").write_text(json.dumps(payloads["normalized-facts.json"], ensure_ascii=False), encoding="utf-8")
    (outline_dir / "outline-workpack.json").write_text(json.dumps(workpack, ensure_ascii=False), encoding="utf-8")
    return semantic_dir, outline_dir


class FormalOutlineGeneratorTests(unittest.TestCase):
    def test_authoring_preparer_emits_source_bound_blank_editorial_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            semantic_dir, outline_dir = _write_foundation(Path(tmp))
            output = Path(tmp) / "authoring-spec.json"

            result = prepare_authoring_spec(semantic_dir, outline_dir, output)
            spec = json.loads(output.read_text(encoding="utf-8"))

            self.assertEqual("ppt_outline_authoring_spec", spec["artifact_type"])
            self.assertEqual(str(output.resolve()), result["output"])
            self.assertEqual({"sec-0002", "sec-0003"}, set(spec["pages"]))
            self.assertEqual("一、建设背景", spec["pages"]["sec-0002"]["source_title"])
            self.assertEqual([], spec["pages"]["sec-0002"]["source_fact_ids"])
            self.assertEqual("", spec["pages"]["sec-0002"]["authoring"]["key_judgment"])
            self.assertEqual("trace_only", spec["planning"]["default_attachment_disposition"])

    def test_blank_prepared_authoring_spec_is_rejected_before_author_edited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            semantic_dir, outline_dir = _write_foundation(Path(tmp))
            spec_path = Path(tmp) / "authoring-spec.json"
            prepare_authoring_spec(semantic_dir, outline_dir, spec_path)
            spec = json.loads(spec_path.read_text(encoding="utf-8"))

            with self.assertRaisesRegex(ValueError, "authoring spec is incomplete"):
                generate_outline(semantic_dir, outline_dir, authoring_spec=spec, force=True)

    def test_candidate_carries_semantic_bindings_and_blocks_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            semantic_dir, outline_dir = _write_foundation(Path(tmp))

            result = generate_outline(semantic_dir, outline_dir, force=True)
            plan = json.loads((outline_dir / "page-plan.json").read_text(encoding="utf-8"))
            report = validate_outline_outputs(semantic_dir, outline_dir)
            page = next(page for page in plan["pages"] if page.get("page_type") == "content")

            self.assertTrue(page["primary_argument_node_id"])
            self.assertIn(page["primary_argument_node_id"], page["source_argument_node_ids"])
            self.assertIn("source_argument_node_statuses", page)
            self.assertIn("concept_ids", page["evidence"])
            self.assertIn("relation_ids", page["evidence"])
            self.assertEqual("blocked", result["handoff_status"])
            self.assertEqual("pending", report["gates"]["authoring_status"])
            self.assertEqual("blocked", report["gates"]["handoff_status"])

    def test_pipeline_generates_validates_and_renders_in_one_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            semantic_dir, outline_dir = _write_foundation(Path(tmp))

            result = run_outline_pipeline(semantic_dir, outline_dir, force=True)

            self.assertEqual("ok", result["validation"]["status"])
            self.assertTrue((outline_dir / "outline-report.json").is_file())
            self.assertTrue((outline_dir / "ppt-outline.md").is_file())

    def test_authoring_spec_merge_group_reduces_pages_without_losing_fact_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            semantic_dir, outline_dir = _write_foundation(Path(tmp))
            spec = {
                "deck": {"audience": "合作方", "purpose": "说明安排"},
                "planning": {
                    "merge_groups": [{
                        "primary_source_heading_id": "sec-0002",
                        "source_heading_ids": ["sec-0002", "sec-0003"],
                        "rationale": "两项内容共同说明总体安排。",
                    }]
                },
                "pages": {"sec-0002": _authored_page("总体安排由源材料两项内容共同说明。")},
            }

            generate_outline(semantic_dir, outline_dir, authoring_spec=spec, force=True)
            report = validate_outline_outputs(semantic_dir, outline_dir)
            plan = json.loads((outline_dir / "page-plan.json").read_text(encoding="utf-8"))
            content = [page for page in plan["pages"] if page.get("page_type") == "content"]

            self.assertEqual("ok", report["status"])
            self.assertEqual(1, len(content))
            self.assertEqual({"sec-0002", "sec-0003"}, set(content[0]["merge_group"]["source_heading_ids"]))
            self.assertEqual(2, len(report["coverage"]["resolved_fact_ids"]))

    def test_attachment_is_trace_only_by_default_and_requires_explicit_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            semantic_dir, outline_dir = _write_attachment_foundation(Path(tmp))

            generate_outline(semantic_dir, outline_dir, force=True)
            candidate = json.loads((outline_dir / "page-plan.json").read_text(encoding="utf-8"))
            self.assertFalse(any(str(page.get("title_intent", "")).startswith("附件") for page in candidate["pages"]))
            self.assertEqual("trace_only", candidate["attachment_policy"]["default_disposition"])

            spec_pages = {
                "sec-0002": _authored_page("建设背景正文。"),
                "sec-0003": _authored_page("商务安排正文。"),
                "sec-0004": _authored_page("附件登记事项保留为追溯输入。"),
            }
            spec_pages["sec-0004"]["authoring_decisions"] = {
                "deletion_test": "附件直接决定本次合作事项的确认边界。",
                "evidence_selection": "只保留直接决定判断的登记事项。",
                "attachment_disposition": "main_deck",
                "attachment_promotion_rationale": "本页直接决定合作事项的确认边界。",
            }
            generate_outline(
                semantic_dir,
                outline_dir,
                authoring_spec={"deck": {"audience": "合作方", "purpose": "说明安排"}, "pages": spec_pages},
                force=True,
            )
            authored = json.loads((outline_dir / "page-plan.json").read_text(encoding="utf-8"))
            attachment = next(page for page in authored["pages"] if page.get("page_type") == "content" and str(page.get("title_intent", "")).startswith("附件"))
            self.assertEqual("main_deck", attachment["authoring_decisions"]["attachment_disposition"])

    def test_candidate_generation_is_source_locked_and_validator_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            semantic_dir, outline_dir = _write_foundation(Path(tmp))

            result = generate_outline(semantic_dir, outline_dir, force=True)
            deck = json.loads((outline_dir / "deck-brief.json").read_text(encoding="utf-8"))
            plan = json.loads((outline_dir / "page-plan.json").read_text(encoding="utf-8"))
            report = validate_outline_outputs(semantic_dir, outline_dir)

            self.assertEqual("mechanical_draft", result["authoring_status"])
            self.assertEqual("mechanical_draft", deck["editorial_authoring_status"])
            self.assertEqual("mechanical_draft", plan["editorial_authoring_status"])
            self.assertEqual("ok", report["status"])
            self.assertEqual(
                ["方案", "目录", "第一章 总体概述", "一、建设背景", "二、商务报价与收益分配", "谢谢"],
                [page["title_intent"] for page in plan["pages"]],
            )
            content = [page for page in plan["pages"] if page["page_type"] == "content"]
            self.assertTrue(all(page["evidence"]["normalized_fact_ids"] for page in content))
            self.assertTrue(all(page["argument_chain"] for page in content))
            self.assertIn(
                "建设背景正文形成源材料论证起点。",
                next(page for page in content if page["primary_source_heading_id"] == "sec-0002")["argument_chain"][0]["statement"],
            )
            self.assertEqual("方案", deck["deck_strategy"]["working_title"])

    def test_authoring_spec_compiles_to_author_edited_outline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            semantic_dir, outline_dir = _write_foundation(Path(tmp))
            spec = {
                "deck": {
                    "audience": "合作方",
                    "purpose": "说明建设背景与服务安排",
                    "working_title": "建设方案",
                    "core_question": "建设方案如何展开？",
                    "deck_thesis": "按源材料说明建设安排。",
                },
                "pages": {
                    "sec-0002": _authored_page("建设背景正文。"),
                    "sec-0003": _authored_page("建设背景正文。"),
                },
            }

            result = generate_outline(
                semantic_dir,
                outline_dir,
                authoring_spec=spec,
                force=True,
            )
            report = validate_outline_outputs(semantic_dir, outline_dir)
            deck = json.loads((outline_dir / "deck-brief.json").read_text(encoding="utf-8"))
            plan = json.loads((outline_dir / "page-plan.json").read_text(encoding="utf-8"))

            self.assertEqual("author_edited", result["authoring_status"])
            self.assertEqual("author_edited", deck["editorial_authoring_status"])
            self.assertEqual("author_edited", plan["editorial_authoring_status"])
            self.assertEqual("ok", report["status"])
            self.assertEqual("合作方", deck["task_understanding"]["audience"])
            self.assertEqual("建设背景正文。", next(page for page in plan["pages"] if page.get("primary_source_heading_id") == "sec-0002")["key_judgment"])

    def test_candidate_never_fabricates_key_judgment_from_first_fact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            semantic_dir, outline_dir = _write_foundation(Path(tmp))

            generate_outline(semantic_dir, outline_dir, force=True)
            plan = json.loads((outline_dir / "page-plan.json").read_text(encoding="utf-8"))
            report = validate_outline_outputs(semantic_dir, outline_dir)
            content = [page for page in plan["pages"] if page.get("page_type") == "content"]

            self.assertTrue(content)
            for page in content:
                self.assertEqual("", page["key_judgment"])
                self.assertEqual("authoring_required", page["judgment_status"])
                self.assertTrue(str(page.get("candidate_summary") or "").strip())
            self.assertEqual("ok", report["status"])
            self.assertEqual("pending", report["gates"]["authoring_status"])

    def test_validator_rejects_candidate_page_with_synthetic_key_judgment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            semantic_dir, outline_dir = _write_foundation(Path(tmp))
            generate_outline(semantic_dir, outline_dir, force=True)
            plan_path = outline_dir / "page-plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            page = next(page for page in plan["pages"] if page.get("page_type") == "content")
            page["key_judgment"] = "依托电力领域数据基础设施开展"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

            report = validate_outline_outputs(semantic_dir, outline_dir)

            self.assertIn(
                "outline_judgment_before_authoring",
                {item["code"] for item in report["errors"]},
            )

    def test_validator_requires_judgment_status_on_author_edited_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            semantic_dir, outline_dir = _write_foundation(Path(tmp))
            spec = {
                "deck": {"audience": "合作方", "purpose": "说明安排"},
                "pages": {
                    "sec-0002": _authored_page("建设背景正文。"),
                    "sec-0003": _authored_page("商务安排正文。"),
                },
            }
            generate_outline(semantic_dir, outline_dir, authoring_spec=spec, force=True)
            plan_path = outline_dir / "page-plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            page = next(page for page in plan["pages"] if page.get("page_type") == "content")
            page.pop("judgment_status", None)
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

            report = validate_outline_outputs(semantic_dir, outline_dir)

            self.assertIn(
                "outline_judgment_status_incomplete",
                {item["code"] for item in report["errors"]},
            )

    def test_author_edited_page_rejects_generic_editorial_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            semantic_dir, outline_dir = _write_foundation(Path(tmp))
            page = _authored_page("建设背景正文。")
            page["audience_question"] = "源材料如何说明建设背景？"
            page["page_mission"] = "按源材料说明建设背景。"
            spec = {
                "deck": {"audience": "合作方", "purpose": "说明安排"},
                "pages": {
                    "sec-0002": page,
                    "sec-0003": _authored_page("商务安排正文。"),
                },
            }
            generate_outline(semantic_dir, outline_dir, authoring_spec=spec, force=True)

            report = validate_outline_outputs(semantic_dir, outline_dir)

            self.assertIn(
                "authoring_editorial_placeholder",
                {item["code"] for item in report["errors"]},
            )

    def test_author_edited_page_starting_with_the_same_words_is_not_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            semantic_dir, outline_dir = _write_foundation(Path(tmp))
            page = _authored_page("建设背景正文。")
            page["audience_question"] = "建设背景由哪些业务层次和连接关系构成？"
            page["page_mission"] = "按源材料说明建设背景的构成、接口和业务承接关系。"
            spec = {
                "deck": {"audience": "合作方", "purpose": "说明安排"},
                "pages": {
                    "sec-0002": page,
                    "sec-0003": _authored_page("商务安排正文。"),
                },
            }
            generate_outline(semantic_dir, outline_dir, authoring_spec=spec, force=True)

            report = validate_outline_outputs(semantic_dir, outline_dir)

            self.assertNotIn(
                "authoring_editorial_placeholder",
                {item["code"] for item in report["errors"]},
            )

    def test_author_edited_page_rejects_judgment_equal_to_source_heading_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            semantic_dir, outline_dir = _write_foundation(Path(tmp))
            page = _authored_page("一、建设背景")
            spec = {
                "deck": {"audience": "合作方", "purpose": "说明安排"},
                "pages": {
                    "sec-0002": page,
                    "sec-0003": _authored_page("商务安排正文。"),
                },
            }
            generate_outline(semantic_dir, outline_dir, authoring_spec=spec, force=True)

            report = validate_outline_outputs(semantic_dir, outline_dir)

            self.assertIn(
                "authoring_judgment_from_metadata",
                {item["code"] for item in report["errors"]},
            )

    def test_authoring_spec_rejects_unknown_source_heading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            semantic_dir, outline_dir = _write_foundation(Path(tmp))

            with self.assertRaisesRegex(ValueError, "unknown source heading"):
                generate_outline(
                    semantic_dir,
                    outline_dir,
                    authoring_spec={"pages": {"sec-9999": _authored_page("不存在")}},
                    force=True,
                )

    def test_official_cli_generates_candidate_without_project_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            semantic_dir, outline_dir = _write_foundation(Path(tmp))
            env = dict(os.environ)
            env["PYTHONPATH"] = f"{ROOT}:{env.get('PYTHONPATH', '')}"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(PLANNING_SKILL / "scripts" / "generate.py"),
                    str(semantic_dir),
                    "-o",
                    str(outline_dir),
                    "--force",
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertIn('"authoring_status": "mechanical_draft"', completed.stdout)
            self.assertTrue((outline_dir / "deck-brief.json").is_file())


if __name__ == "__main__":
    unittest.main()
