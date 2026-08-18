from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from cyberppt.visual_structure_contract import (
    audit_visual_design_package,
    prompt_contract_hashes,
    sha256,
)
from cyberppt.onscreen_expression import (
    VALID_EXPRESSION_FORMS,
    expression_constraints,
    expression_constraints_sha256,
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


def _expression_fit(form: str, *, status: str = "default_profile") -> dict:
    constraints = expression_constraints(form)
    return {
        "form": form,
        "constraint_status": status,
        "satisfied_constraints": list(constraints["required_features"]),
        "reading_relation": f"the candidate preserves {constraints['relation_pattern']}",
        "balance_strategy": str(constraints["balance_requirement"]),
        "changed_constraints": [],
        "deviation_reason": "",
    }


def _selection_rationale() -> dict:
    return {
        "mission_fit": "The relationship field directly serves the page mission.",
        "generation_feasibility": {
            "score": 100,
            "dimensions": {
                "single_focus": 20,
                "text_capacity": 20,
                "relation_clarity": 20,
                "composition_stability": 20,
                "anti_pattern_risk": 20,
            },
            "risks": [],
        },
    }


def _text_capacity_budget() -> dict:
    return {
        "locked_text_ids": ["P01-T01", "P01-T02"],
        "locked_text_count": 2,
        "evidence_text_counts": {"input": 8, "result": 8},
        "max_lines": 4,
        "max_chars_per_line": 24,
        "estimated_density": "low",
        "risk_level": "low",
        "risks": [],
    }


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
                "stage01_relationship_features": {
                    "authority": "stage01_semantic_handoff",
                    "actors": ["Input"],
                    "actions": [{"subject": "Input", "relation": "supports", "object": "Result"}],
                    "directions": [], "conditions": [], "branches": [], "feedback": [],
                    "source_visual_notes": "put two cards left and right",
                },
                "locked_text_items": [
                    {"text_id": "P01-T01", "text": "Locked A", "ordinal": 1},
                    {"text_id": "P01-T02", "text": "Locked B", "ordinal": 2},
                ],
                "onscreen_expression": {
                    "form": "framework_4",
                    "source": "relation",
                    "confidence": 0.92,
                    "evidence": ["relation:composed_of"],
                },
                "expression_constraints": expression_constraints("framework_4"),
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
            "visual_thesis": "Input converges on the result so the support relationship is immediately visible.",
            "visual_intent_type": "evidence_to_judgment",
            # framework_4 has reading_requirement "parallel": no peer may be
            # marked semantic_focus.kind=="outcome" (see
            # CANDIDATE_PARALLEL_FORM_FALSE_OUTCOME in visual_structure_contract.py).
            "semantic_focus": {"kind": "entity", "evidence_key": "result"},
            "spatial_grammar": ["convergence"],
            "direction": "outside_to_center",
            "reading_sequence": ["input", "result"],
            "score_profile": "high",
            "expression_fit": _expression_fit("framework_4"),
            "selection_rationale": _selection_rationale(),
            "rejection_rationale": "",
            "text_capacity_budget": _text_capacity_budget(),
        },
        {
            "id": "C2",
            "visual_thesis": "Input and result form one directed transformation path.",
            "visual_intent_type": "input_output",
            "semantic_focus": {"kind": "action", "evidence_key": "input"},
            "spatial_grammar": ["path"],
            "direction": "left_to_right",
            "reading_sequence": ["input", "result"],
            "score_profile": "mid",
            "expression_fit": _expression_fit("framework_4"),
            "selection_rationale": _selection_rationale(),
            "rejection_rationale": "The selected candidate keeps the result as the single focus.",
            "text_capacity_budget": _text_capacity_budget(),
        },
        {
            "id": "C3",
            "visual_thesis": "The contrast between input state and result state exposes the value created.",
            "visual_intent_type": "comparison",
            "semantic_focus": {"kind": "state", "evidence_key": "input"},
            "spatial_grammar": ["tension"],
            "direction": "spatial",
            "reading_sequence": ["result", "input"],
            "score_profile": "low",
            "expression_fit": _expression_fit("framework_4"),
            "selection_rationale": _selection_rationale(),
            "rejection_rationale": "The selected candidate preserves the input-to-result support relation more clearly.",
            "text_capacity_budget": _text_capacity_budget(),
        },
    ]
    decisions = {
        "schema": "cyberppt.visual_design_decisions.v3",
        "source_sha256": "set-when-written",
        "score_profiles": profiles,
        "pages": [
            {
                "page_id": "p01",
                "stage01_visual_note_disposition": {
                    "inherited": [{"feature": "Input supports Result", "reason": "preserves the authoritative relationship"}],
                    "adjusted": [],
                    "rejected": [{"feature": "two cards left and right", "reason": "layout advice is not relationship truth"}],
                },
                "onscreen_expression_disposition": {
                    "form": "framework_4",
                    "reading_relation": "four parallel capability groups",
                    "balance_strategy": "equal peer prominence with comparable text weight",
                },
                "selected_candidate": "C1",
                "candidates": candidates,
                "execution_design": {
                    "business_object": "Input-to-result support relationship field",
                    "visual_focus": "Result",
                    "text_integration_method": "Attach each locked phrase to its related object",
                    "spatial_organization": "Input converges on Result",
                    "relationship_encoding": "Directed support relationship",
                    "semantic_role": "The relationship field proves that input supports the result",
                    "use_scene": False,
                    "scene_type": "Flat business relationship field",
                },
                "relationship_coverage": [
                    {
                        "relation_key": "R01",
                        "source": "business_relationships",
                        "subject": "Input",
                        "relation": "supports",
                        "object": "Result",
                        "visual_status": "primary",
                        "evidence_refs": ["E2"],
                        "text_ids": ["P01-T02"],
                        "rationale": "The support relation is the page's primary judgment.",
                    }
                ],
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
                "expression_contract": {
                    "form": "framework_4",
                    "constraints_sha256": expression_constraints_sha256(expression_constraints("framework_4")),
                    "selected_candidate_id": "C1",
                    "fit_status": "default_profile",
                    "reading_relation": "the candidate preserves peer_modules",
                    "balance_strategy": "four peers have comparable reading weight",
                    "deviation_reason": "",
                },
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
                "semantic_graph": {
                    "decision_relationship": "Input supports Result",
                    "business_relationships": [
                        {"subject": "Input", "objects": ["Result"], "relation": "supports"}
                    ],
                },
                "visual_decision": {
                    "visual_thesis": "Input converges on the result so the support relationship is immediately visible.",
                    "spatial_organization": "Input converges on Result",
                    "text_integration_method": "Attach each locked phrase to its related object",
                    "relationship_encoding": "Directed support relationship",
                    "visual_hierarchy": {
                        "primary": "Result",
                    },
                },
                "image_plan": {
                    "business_object": "Input-to-result support relationship field",
                    "semantic_role": "The relationship field proves that input supports the result",
                    "use_scene": False,
                    "scene_type": "Flat business relationship field",
                    "placement": "Input converges on Result",
                },
                "structural_decision": {
                    "semantic_focus": {"kind": "outcome", "ref": "E2"},
                    "primary_refs": ["E2"],
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


def test_audit_rejects_candidate_without_visual_thesis() -> None:
    design, decisions, spec = _payloads()
    del decisions["pages"][0]["candidates"][0]["visual_thesis"]
    assert "CANDIDATE_VISUAL_THESIS_MISSING" in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_rejects_selected_visual_thesis_or_scene_drift() -> None:
    design, decisions, spec = _payloads()
    spec["pages"][0]["visual_decision"]["visual_thesis"] = "Different thesis"
    spec["pages"][0]["image_plan"]["use_scene"] = True
    codes = {item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]}
    assert "SPEC_VISUAL_THESIS_DRIFTED" in codes
    assert "SPEC_SCENE_POLICY_DRIFTED" in codes


def test_audit_rejects_incomplete_execution_design() -> None:
    design, decisions, spec = _payloads()
    del decisions["pages"][0]["execution_design"]["semantic_role"]
    assert "EXECUTION_DESIGN_INVALID" in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_rejects_selected_execution_composition_drift() -> None:
    design, decisions, spec = _payloads()
    spec["pages"][0]["visual_decision"]["spatial_organization"] = "A different layout recipe"
    spec["pages"][0]["visual_decision"]["visual_hierarchy"]["primary"] = "A different focus"
    spec["pages"][0]["image_plan"]["placement"] = "A different placement"
    assert "SPEC_EXECUTION_DESIGN_DRIFTED" in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_rejects_missing_candidate_quality_rationale() -> None:
    design, decisions, spec = _payloads()
    del decisions["pages"][0]["candidates"][0]["selection_rationale"]
    assert "CANDIDATE_SELECTION_RATIONALE_MISSING" in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_rejects_unselected_candidate_without_counterfactual() -> None:
    design, decisions, spec = _payloads()
    decisions["pages"][0]["candidates"][1]["rejection_rationale"] = "lower score"
    assert "CANDIDATE_REJECTION_RATIONALE_INVALID" in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_rejects_uncovered_primary_business_relation() -> None:
    design, decisions, spec = _payloads()
    decisions["pages"][0]["relationship_coverage"] = []
    assert "RELATIONSHIP_COVERAGE_MISSING" in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_rejects_over_capacity_selected_candidate() -> None:
    design, decisions, spec = _payloads()
    decisions["pages"][0]["candidates"][0]["text_capacity_budget"]["risk_level"] = "blocking"
    assert "TEXT_CAPACITY_BLOCKING" in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_rejects_competing_primary_focus() -> None:
    design, decisions, spec = _payloads()
    spec["pages"][0]["structural_decision"]["text_bindings"].append(
        {"evidence_id": "E2", "target_ref": "E2", "binding": "result", "text_ids": ["P01-T02"]}
    )
    assert "FOCUS_COMPETITION_DETECTED" in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def _with_topology_graph(spec: dict, topology: str, **overrides) -> dict:
    """Attach a minimal but complete semantic_graph for topology-audit tests."""

    graph = {
        "topology": topology,
        "primary_relation": "flow",
        "focus_node": "E2",
        "nodes": [
            {"id": "E1", "role": "evidence", "source_refs": ["P01-T01"]},
            {"id": "E2", "role": "judgment", "source_refs": ["P01-T02"]},
        ],
        "edges": [
            {"from": "E1", "to": "E2", "relation": "supports", "label": "supports", "direction": "forward"},
        ],
        "decision_relationship": "Input supports Result",
        "business_relationships": [{"subject": "Input", "objects": ["Result"], "relation": "supports"}],
        "grouping_decisions": [],
        "forbidden_structures": [],
    }
    graph.update(overrides)
    spec["pages"][0]["semantic_graph"] = graph
    return spec


def test_audit_passes_a_well_formed_topology_graph() -> None:
    design, decisions, spec = _payloads()
    spec = _with_topology_graph(spec, "directed_flow")
    codes = {item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]}
    assert not codes & {
        "FOCUS_LAYER_MISMATCH", "FOCUS_NOT_JUDGMENT", "MISSING_RESULT_NODE",
        "MISSING_DEPENDENCY_EDGE", "MISSING_FEEDBACK_EDGE", "MISSING_BOUNDARY_EDGE",
        "MISSING_VALUE_DESTINATION", "MULTIPLE_EQUAL_CONCLUSIONS", "FORCED_SEQUENTIAL_EDGE",
        "MISSING_FOCUS_EDGE",
    }


def test_audit_rejects_focus_node_layer_mismatch() -> None:
    design, decisions, spec = _payloads()
    spec = _with_topology_graph(spec, "directed_flow", focus_node="E1")
    assert "FOCUS_LAYER_MISMATCH" in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_rejects_focus_node_that_is_not_the_judgment_role() -> None:
    design, decisions, spec = _payloads()
    spec = _with_topology_graph(spec, "directed_flow")
    spec["pages"][0]["structural_decision"]["semantic_focus"]["ref"] = "E1"
    spec["pages"][0]["semantic_graph"]["focus_node"] = "E1"
    assert "FOCUS_NOT_JUDGMENT" in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_allows_evidence_focus_with_explicit_override_reason() -> None:
    design, decisions, spec = _payloads()
    spec = _with_topology_graph(spec, "directed_flow")
    spec["pages"][0]["structural_decision"]["semantic_focus"]["ref"] = "E1"
    spec["pages"][0]["semantic_graph"]["focus_node"] = "E1"
    spec["pages"][0]["quality_contract"] = {"focus_override_reason": "human review approved an evidence-led focus."}
    assert "FOCUS_NOT_JUDGMENT" not in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_rejects_causal_convergence_without_a_result_node() -> None:
    design, decisions, spec = _payloads()
    spec = _with_topology_graph(spec, "causal_convergence")
    assert "MISSING_RESULT_NODE" in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_rejects_lifecycle_loop_without_a_feedback_edge() -> None:
    design, decisions, spec = _payloads()
    spec = _with_topology_graph(spec, "lifecycle_loop")
    assert "MISSING_FEEDBACK_EDGE" in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_passes_lifecycle_loop_with_a_backward_feedback_edge() -> None:
    design, decisions, spec = _payloads()
    spec = _with_topology_graph(
        spec,
        "lifecycle_loop",
        edges=[
            {"from": "E1", "to": "E2", "relation": "supports", "label": "supports", "direction": "forward"},
            {"from": "E2", "to": "E1", "relation": "feeds_back", "label": "feedback", "direction": "backward"},
        ],
    )
    assert "MISSING_FEEDBACK_EDGE" not in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_rejects_governance_boundary_without_a_boundary_relation() -> None:
    design, decisions, spec = _payloads()
    spec = _with_topology_graph(spec, "governance_boundary")
    assert "MISSING_BOUNDARY_EDGE" in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_rejects_allocation_flow_with_an_unconnected_role_node() -> None:
    design, decisions, spec = _payloads()
    spec = _with_topology_graph(
        spec,
        "allocation_flow",
        nodes=[
            {"id": "E1", "role": "evidence", "source_refs": ["P01-T01"]},
            {"id": "E2", "role": "judgment", "source_refs": ["P01-T02"]},
            {"id": "E3", "role": "evidence", "source_refs": []},
        ],
    )
    assert "MISSING_VALUE_DESTINATION" in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_rejects_parallel_set_with_a_forced_sequential_edge_between_peers() -> None:
    design, decisions, spec = _payloads()
    spec = _with_topology_graph(
        spec,
        "parallel_set",
        focus_node="E3",
        nodes=[
            {"id": "E1", "role": "evidence", "source_refs": ["P01-T01"]},
            {"id": "E2", "role": "evidence", "source_refs": []},
            {"id": "E3", "role": "judgment", "source_refs": ["P01-T02"]},
        ],
        edges=[
            {"from": "E1", "to": "E2", "relation": "precedes", "label": "precedes", "direction": "forward"},
            {"from": "E1", "to": "E3", "relation": "peer", "label": "peer", "direction": "none"},
            {"from": "E2", "to": "E3", "relation": "peer", "label": "peer", "direction": "none"},
        ],
    )
    assert "FORCED_SEQUENTIAL_EDGE" in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_rejects_a_locked_text_id_with_no_node_disposition() -> None:
    design, decisions, spec = _payloads()
    spec = _with_topology_graph(
        spec,
        "directed_flow",
        nodes=[
            {"id": "E1", "role": "evidence", "source_refs": []},
            {"id": "E2", "role": "judgment", "source_refs": ["P01-T02"]},
        ],
    )
    assert "GROUPING_SOURCE_UNMAPPED" in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_rejects_the_same_locked_text_id_claimed_by_two_nodes() -> None:
    design, decisions, spec = _payloads()
    spec = _with_topology_graph(
        spec,
        "directed_flow",
        nodes=[
            {"id": "E1", "role": "evidence", "source_refs": ["P01-T01"]},
            {"id": "E2", "role": "judgment", "source_refs": ["P01-T01", "P01-T02"]},
        ],
        grouping_decisions=[
            {"source_nodes": ["P01-T01", "P01-T02"], "target_node": "E2", "reason": "both establish the same delivered result", "loss_risk": "low"},
        ],
    )
    assert "GROUPING_ROLE_COLLISION" in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_rejects_a_merged_node_without_a_grouping_decision() -> None:
    design, decisions, spec = _payloads()
    spec = _with_topology_graph(
        spec,
        "directed_flow",
        nodes=[
            {"id": "E1", "role": "evidence", "source_refs": []},
            {"id": "E2", "role": "judgment", "source_refs": ["P01-T01", "P01-T02"]},
        ],
    )
    assert "GROUPING_REASON_MISSING" in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_rejects_a_generic_grouping_reason() -> None:
    design, decisions, spec = _payloads()
    spec = _with_topology_graph(
        spec,
        "directed_flow",
        nodes=[
            {"id": "E1", "role": "evidence", "source_refs": []},
            {"id": "E2", "role": "judgment", "source_refs": ["P01-T01", "P01-T02"]},
        ],
        grouping_decisions=[
            {"source_nodes": ["P01-T01", "P01-T02"], "target_node": "E2", "reason": "merge", "loss_risk": "low"},
        ],
    )
    assert "GROUPING_REASON_MISSING" in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_rejects_high_loss_risk_grouping_without_human_review() -> None:
    design, decisions, spec = _payloads()
    spec = _with_topology_graph(
        spec,
        "directed_flow",
        nodes=[
            {"id": "E1", "role": "evidence", "source_refs": []},
            {"id": "E2", "role": "judgment", "source_refs": ["P01-T01", "P01-T02"]},
        ],
        grouping_decisions=[
            {"source_nodes": ["P01-T01", "P01-T02"], "target_node": "E2", "reason": "different subjects share one summary box", "loss_risk": "high"},
        ],
    )
    assert "GROUPING_LOSS_RISK_HIGH" in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_audit_allows_high_loss_risk_grouping_with_recorded_human_review() -> None:
    design, decisions, spec = _payloads()
    spec = _with_topology_graph(
        spec,
        "directed_flow",
        nodes=[
            {"id": "E1", "role": "evidence", "source_refs": []},
            {"id": "E2", "role": "judgment", "source_refs": ["P01-T01", "P01-T02"]},
        ],
        grouping_decisions=[
            {"source_nodes": ["P01-T01", "P01-T02"], "target_node": "E2", "reason": "different subjects share one summary box", "loss_risk": "high"},
        ],
    )
    spec["pages"][0]["quality_contract"] = {"grouping_review_reason": "Reviewer confirmed no subject or boundary is lost by this merge."}
    assert "GROUPING_LOSS_RISK_HIGH" not in {
        item["code"] for item in _audit(design, decisions, spec)["blocking_issues"]
    }


def test_visual_design_package_blocks_each_cross_artifact_failure() -> None:
    cases = []
    design, decisions, spec = _payloads()
    decisions["pages"][0]["candidates"] = []
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

    design, decisions, spec = _payloads()
    del decisions["pages"][0]["onscreen_expression_disposition"]
    cases.append((design, decisions, spec, "ONSCREEN_EXPRESSION_DISPOSITION_MISSING"))

    for design, decisions, spec, expected_code in cases:
        report = _audit(copy.deepcopy(design), copy.deepcopy(decisions), copy.deepcopy(spec))
        codes = {item["code"] for item in report["blocking_issues"]}
        assert report["status"] == "failed"
        assert expected_code in codes


def test_audit_rejects_candidate_without_expression_fit() -> None:
    design, decisions, spec = _payloads()
    del decisions["pages"][0]["candidates"][0]["expression_fit"]
    report = _audit(design, decisions, spec)
    assert "CANDIDATE_EXPRESSION_FIT_MISSING" in {item["code"] for item in report["blocking_issues"]}


def test_audit_rejects_adapted_candidate_without_reason() -> None:
    design, decisions, spec = _payloads()
    fit = decisions["pages"][0]["candidates"][0]["expression_fit"]
    fit.update({"constraint_status": "adapted", "changed_constraints": ["reading_requirement"], "deviation_reason": ""})
    report = _audit(design, decisions, spec)
    assert "CANDIDATE_EXPRESSION_DEVIATION_INVALID" in {item["code"] for item in report["blocking_issues"]}


def test_audit_rejects_expression_contract_drift() -> None:
    design, decisions, spec = _payloads()
    spec["pages"][0]["expression_contract"]["selected_candidate_id"] = "other"
    report = _audit(design, decisions, spec)
    assert "SPEC_EXPRESSION_CONTRACT_DRIFTED" in {item["code"] for item in report["blocking_issues"]}


def test_audit_rejects_expression_contract_hash_drift() -> None:
    design, decisions, spec = _payloads()
    spec["pages"][0]["expression_contract"]["constraints_sha256"] = "0" * 64
    report = _audit(design, decisions, spec)
    assert "SPEC_EXPRESSION_CONTRACT_DRIFTED" in {item["code"] for item in report["blocking_issues"]}


def test_audit_rejects_candidate_that_omits_a_form_core_requirement() -> None:
    for form in sorted(VALID_EXPRESSION_FORMS):
        design, decisions, spec = _payloads()
        design["pages"][0]["onscreen_expression"]["form"] = form
        design["pages"][0]["expression_constraints"] = expression_constraints(form)
        decisions["pages"][0]["onscreen_expression_disposition"]["form"] = form
        for candidate in decisions["pages"][0]["candidates"]:
            candidate["expression_fit"] = _expression_fit(form)
        decisions["pages"][0]["candidates"][0]["expression_fit"]["satisfied_constraints"] = []
        selected = decisions["pages"][0]["candidates"][0]
        spec["pages"][0]["expression_contract"] = {
            "form": form,
            "constraints_sha256": expression_constraints_sha256(expression_constraints(form)),
            "selected_candidate_id": selected["id"],
            "fit_status": "default_profile",
            "reading_relation": selected["expression_fit"]["reading_relation"],
            "balance_strategy": selected["expression_fit"]["balance_strategy"],
            "deviation_reason": "",
        }
        report = _audit(design, decisions, spec)
        assert "CANDIDATE_EXPRESSION_CORE_MISSING" in {
            item["code"] for item in report["blocking_issues"]
        }, form


class VisualRelationshipContractTests(unittest.TestCase):
    def test_audit_rejects_business_relationship_drift(self) -> None:
        design, decisions, spec = _payloads()
        spec["pages"][0]["semantic_graph"]["business_relationships"][0][
            "relation"
        ] = "contains"

        report = _audit(design, decisions, spec)

        self.assertIn(
            "BUSINESS_RELATIONSHIP_DRIFT",
            {item["code"] for item in report["blocking_issues"]},
        )

    def test_audit_accepts_page_without_authoritative_business_relationships(self) -> None:
        design, decisions, spec = _payloads()
        design["pages"][0]["business_relationships"] = []
        design["pages"][0]["stage01_relationship_features"]["actions"] = []
        decisions["pages"][0]["relationship_coverage"] = []
        spec["pages"][0]["semantic_graph"]["business_relationships"] = []

        report = _audit(design, decisions, spec)

        self.assertEqual("passed", report["status"])
        self.assertEqual([], report["blocking_issues"])


def test_every_registered_form_has_a_default_candidate_profile() -> None:
    for form in VALID_EXPRESSION_FORMS:
        design, decisions, spec = _payloads()
        design["pages"][0]["onscreen_expression"]["form"] = form
        design["pages"][0]["expression_constraints"] = expression_constraints(form)
        decisions["pages"][0]["onscreen_expression_disposition"]["form"] = form
        # A "parallel" reading requirement (key_points_3, framework_4) means no
        # peer may be presented as the outcome the others converge into; keep the
        # fixture's default outcome-focused candidate only for non-parallel forms.
        parallel_form = expression_constraints(form)["reading_requirement"] == "parallel"
        for candidate in decisions["pages"][0]["candidates"]:
            candidate["expression_fit"] = _expression_fit(form)
            if parallel_form and candidate["semantic_focus"]["kind"] == "outcome":
                candidate["semantic_focus"] = {**candidate["semantic_focus"], "kind": "entity"}
        selected = decisions["pages"][0]["candidates"][0]
        spec["pages"][0]["expression_contract"] = {
            "form": form,
            "constraints_sha256": expression_constraints_sha256(expression_constraints(form)),
            "selected_candidate_id": selected["id"],
            "fit_status": "default_profile",
            "reading_relation": selected["expression_fit"]["reading_relation"],
            "balance_strategy": selected["expression_fit"]["balance_strategy"],
            "deviation_reason": "",
        }
        report = _audit(design, decisions, spec)
        assert report["status"] == "passed", form


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
