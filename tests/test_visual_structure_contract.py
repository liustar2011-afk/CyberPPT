from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile

from cyberppt.visual_structure_contract import (
    audit_visual_design_package,
    prompt_contract_hashes,
    sha256,
)


ROOT = Path(__file__).resolve().parents[1]
PROMPT_BUILDER = (
    ROOT
    / "vendor"
    / "skills"
    / "ppt-visual-structure-designer"
    / "scripts"
    / "build_generation_prompt.py"
)


def _payloads() -> tuple[dict, dict, dict]:
    design = {
        "schema": "cyberppt.visual_design_input.v2",
        "pages": [
            {
                "page_id": "p01",
                "business_relationships": [
                    {"subject": "Input", "objects": ["Result"], "relation": "supports"}
                ],
                "author_visual_notes": "put two cards left and right",
                "author_visual_notes_authority": "advisory_only",
                "locked_text_items": [
                    {"text_id": "P01-T01", "text": "Locked A", "ordinal": 1},
                    {"text_id": "P01-T02", "text": "Locked B", "ordinal": 2},
                ],
            }
        ],
    }
    profiles = {
        "high": {"dimensions": {"mission": 60, "relation": 40}, "total": 100},
        "mid": {"dimensions": {"mission": 55, "relation": 35}, "total": 90},
        "low": {"dimensions": {"mission": 50, "relation": 30}, "total": 80},
    }
    candidates = [
        {
            "id": "C1",
            "visual_intent_type": "evidence_to_judgment",
            "semantic_focus": {"kind": "outcome", "evidence_key": "result"},
            "spatial_grammar": ["convergence"],
            "direction": "outside_to_center",
            "reading_sequence": ["input", "result"],
            "score_profile": "high",
        },
        {
            "id": "C2",
            "visual_intent_type": "input_output",
            "semantic_focus": {"kind": "action", "evidence_key": "input"},
            "spatial_grammar": ["path"],
            "direction": "left_to_right",
            "reading_sequence": ["input", "result"],
            "score_profile": "mid",
        },
        {
            "id": "C3",
            "visual_intent_type": "comparison",
            "semantic_focus": {"kind": "state", "evidence_key": "input"},
            "spatial_grammar": ["tension"],
            "direction": "spatial",
            "reading_sequence": ["result", "input"],
            "score_profile": "low",
        },
    ]
    decisions = {
        "schema": "cyberppt.visual_design_decisions.v2",
        "source_sha256": "set-when-written",
        "score_profiles": profiles,
        "pages": [
            {
                "page_id": "p01",
                "selected_candidate": "C1",
                "candidates": candidates,
                "evidence_units": [
                    {"key": "input"},
                    {"key": "result"},
                ],
            }
        ],
    }
    spec = {
        "pages": [
            {
                "page_id": "P01",
                "content_lock": {
                    "locked_items": [
                        {"id": "P01-TITLE", "type": "title", "text": "Title"},
                        {"id": "P01-T01", "type": "body", "text": "Locked A"},
                        {"id": "P01-T02", "type": "body", "text": "Locked B"},
                    ]
                },
                "evidence_units": [
                    {"id": "E1", "priority": "P0"},
                    {"id": "E2", "priority": "P0"},
                ],
                "semantic_graph": {"decision_relationship": "Input supports Result"},
                "structural_decision": {
                    "text_bindings": [
                        {
                            "evidence_id": "E1",
                            "target_ref": "E1",
                            "binding": "embedded",
                            "text_ids": ["P01-T01"],
                        },
                        {
                            "evidence_id": "E2",
                            "target_ref": "E2",
                            "binding": "result",
                            "text_ids": ["P01-T02"],
                        },
                    ]
                },
                "final_text": [
                    {"id": "P01-T01", "text": "Locked A"},
                    {"id": "P01-T02", "text": "Locked B"},
                ],
                "generation_handoff": {
                    "required_text_ids": ["P01-T01", "P01-T02"],
                    "required_text": ["Locked A", "Locked B"],
                },
            }
        ]
    }
    return design, decisions, spec


def _audit(design: dict, decisions: dict, spec: dict) -> dict:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        design_path = root / "input.json"
        decisions_path = root / "decisions.json"
        spec_path = root / "spec.json"
        design_path.write_text(json.dumps(design), encoding="utf-8")
        decisions["source_sha256"] = sha256(design_path)
        decisions_path.write_text(json.dumps(decisions), encoding="utf-8")
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        return audit_visual_design_package(design_path, decisions_path, spec_path)


def test_visual_design_package_passes_complete_candidate_and_text_contract() -> None:
    design, decisions, spec = _payloads()
    report = _audit(design, decisions, spec)
    assert report["status"] == "passed"
    assert report["blocking_issues"] == []


def test_visual_design_package_blocks_each_cross_artifact_failure() -> None:
    cases = []
    design, decisions, spec = _payloads()
    decisions["pages"][0]["candidates"] = decisions["pages"][0]["candidates"][:2]
    cases.append((design, decisions, spec, "CANDIDATE_COUNT_INSUFFICIENT"))

    design, decisions, spec = _payloads()
    decisions["pages"][0]["selected_candidate"] = "C3"
    cases.append((design, decisions, spec, "SELECTED_CANDIDATE_NOT_HIGHEST"))

    design, decisions, spec = _payloads()
    spec["pages"][0]["generation_handoff"]["required_text"] = ["Locked B", "Locked A"]
    cases.append((design, decisions, spec, "SPEC_REQUIRED_TEXT_DRIFTED"))

    design, decisions, spec = _payloads()
    spec["pages"][0]["structural_decision"]["text_bindings"][1]["text_ids"] = ["P01-T01"]
    cases.append((design, decisions, spec, "TEXT_BINDING_ID_DUPLICATE"))

    for design, decisions, spec, expected_code in cases:
        report = _audit(copy.deepcopy(design), copy.deepcopy(decisions), copy.deepcopy(spec))
        codes = {item["code"] for item in report["blocking_issues"]}
        assert report["status"] == "failed"
        assert expected_code in codes


def test_prompt_builder_resolves_required_copy_by_id_without_evidence_rewrite() -> None:
    module_spec = importlib.util.spec_from_file_location("visual_prompt_builder", PROMPT_BUILDER)
    assert module_spec and module_spec.loader
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    page = {
        "page_number": 1,
        "page_title": "Title",
        "visual_decision": {"visual_intent_type": "evidence", "visual_thesis": "Evidence supports result"},
        "semantic_graph": {"decision_relationship": "Input supports Result"},
        "structural_decision": {
            "semantic_focus": {"kind": "outcome", "ref": "E2"},
            "spatial_grammar": ["convergence"],
            "semantic_tags": ["evidence"],
            "primary_refs": ["E2"],
            "secondary_refs": ["E1"],
            "reading_sequence": ["E1", "E2"],
            "text_bindings": [
                {"evidence_id": "E1", "target_ref": "E1", "binding": "embedded", "text_ids": ["P01-T01"]},
                {"evidence_id": "E2", "target_ref": "E2", "binding": "result", "text_ids": ["P01-T02"]},
            ],
            "representation_freedom": {"carrier": "free", "medium": "free", "reason": "source does not constrain it"},
        },
        "text_integration": {"body_render_mode": "in_image", "placement_strategy": "bind copy to evidence"},
        "generation_handoff": {
            "structural_guidance": {"source": "structural_decision", "additional_constraints": []},
            "required_text_ids": ["P01-T01", "P01-T02"],
            "required_text": ["Locked A", "Locked B"],
            "style_source_ref": "style.json",
            "title_exclusion_instruction": "Do not render title.",
        },
        "final_text": [
            {"id": "P01-T01", "text": "Locked A"},
            {"id": "P01-T02", "text": "Locked B"},
        ],
        "connectors": [],
    }
    prompt = module.page_prompt(page)
    assert prompt.count("Locked A") == 1
    assert prompt.count("Locked B") == 1
    assert "locked text ids: P01-T01" in prompt
    assert "do not render the ids" in prompt


def test_prompt_contract_hashes_change_when_builder_changes() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        paths = [
            root / "SKILL.md",
            root / "scripts" / "build_generation_prompt.py",
            root / "scripts" / "validate_visual_spec.py",
            root / "assets" / "page-visual-spec.schema.json",
            root / "assets" / "deck-visual-spec.schema.json",
        ]
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(path.name, encoding="utf-8")
        before = prompt_contract_hashes(root)
        paths[1].write_text("changed builder", encoding="utf-8")
        after = prompt_contract_hashes(root)
        assert before["prompt_builder"] != after["prompt_builder"]
        assert before["skill_bundle"] != after["skill_bundle"]
