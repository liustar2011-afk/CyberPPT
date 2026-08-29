from dataclasses import replace

import pytest

from cyberppt.page_artifact_spec import VisibleTextBindingSpec
from cyberppt.region_binding import bind_region_graph_text
from cyberppt.region_graph import build_region_graph, validate_region_graph
from cyberppt.region_graph_audit import audit_region_graph
from cyberppt.visual_medium_policy import validate_visual_medium_policy
from scripts.imagegen_pipeline.artifact_prompt import build_final_prompt_ir
from scripts.imagegen_pipeline.final_prompt_renderer import render_final_prompt
from tests.test_final_prompt_ir import _artifact_spec


CASES = (
    (
        "parallel_set",
        "E1",
        "peer_field",
        [
            {"from": "E1", "to": "E2", "relation": "peer", "direction": "none"},
            {"from": "E2", "to": "E3", "relation": "peer", "direction": "none"},
        ],
    ),
    (
        "causal_convergence",
        "E3",
        "single_anchor",
        [
            {"from": "E1", "to": "E3", "relation": "converge", "direction": "forward"},
            {"from": "E2", "to": "E3", "relation": "converge", "direction": "forward"},
        ],
    ),
    (
        "directed_flow",
        "E3",
        "sequence_focus",
        [
            {"from": "E1", "to": "E2", "relation": "flow", "direction": "forward"},
            {"from": "E2", "to": "E3", "relation": "flow", "direction": "forward"},
        ],
    ),
    (
        "layered_architecture",
        "E3",
        "sequence_focus",
        [
            {"from": "E1", "to": "E2", "relation": "layer", "direction": "forward"},
            {"from": "E2", "to": "E3", "relation": "layer", "direction": "forward"},
        ],
    ),
    (
        "governance_boundary",
        "E2",
        "paired_focus",
        [
            {"from": "E1", "to": "E2", "relation": "boundary", "direction": "forward"},
            {"from": "E2", "to": "E3", "relation": "control", "direction": "forward"},
        ],
    ),
    (
        "ecosystem_map",
        "E1",
        "distributed_focus",
        [
            {"from": "E1", "to": "E2", "relation": "exchange", "direction": "bidirectional"},
            {"from": "E2", "to": "E3", "relation": "exchange", "direction": "bidirectional"},
        ],
    ),
    (
        "allocation_flow",
        "E1",
        "sequence_focus",
        [
            {"from": "E1", "to": "E2", "relation": "diverge", "direction": "forward"},
            {"from": "E1", "to": "E3", "relation": "diverge", "direction": "forward"},
        ],
    ),
    (
        "conclusion_anchor",
        "E3",
        "single_anchor",
        [
            {"from": "E1", "to": "E3", "relation": "evidence", "direction": "forward"},
            {"from": "E2", "to": "E3", "relation": "evidence", "direction": "forward"},
        ],
    ),
    (
        "lifecycle_loop",
        "E3",
        "sequence_focus",
        [
            {"from": "E1", "to": "E2", "relation": "loop", "direction": "forward"},
            {"from": "E2", "to": "E3", "relation": "loop", "direction": "forward"},
            {"from": "E3", "to": "E1", "relation": "loop", "direction": "backward"},
        ],
    ),
)


def _bound_graph(topology, focus_id, focus_policy, edges):
    graph = build_region_graph(
        topology=topology,
        evidence_ids=["E1", "E2", "E3"],
        focus_id=focus_id,
        reading_sequence=["E1", "E2", "E3"],
        semantic_edges=edges,
        focus_policy=focus_policy,
    )
    return bind_region_graph_text(
        graph,
        evidence_text_ids={"E1": ["T1"], "E2": ["T2"], "E3": ["T3"]},
        required_text_ids=["T1", "T2", "T3"],
    )


def _audit_payload(graph, topology, focus_id, focus_policy):
    region_by_text = {
        text_id: region["id"]
        for region in graph["regions"]
        for text_id in region.get("text_ids") or []
    }
    return {
        "region_graph": graph,
        "final_text": [
            {"id": text_id, "text": f"Visible {text_id}", "region_id": region_by_text[text_id]}
            for text_id in ("T1", "T2", "T3")
        ],
        "evidence_units": [
            {"id": evidence_id, "priority": "P0"}
            for evidence_id in ("E1", "E2", "E3")
        ],
        "generation_handoff": {"required_text_ids": ["T1", "T2", "T3"]},
        "semantic_graph": {"topology": topology, "focus_node": focus_id},
        "visual_decision": {"focus_policy": focus_policy},
    }


def _artifact(graph, focus_policy):
    base = _artifact_spec()
    medium = validate_visual_medium_policy({
        "preferred": "mixed",
        "allowed": ["business_scene", "object_illustration", "relationship_diagram", "mixed"],
        "scene_policy": "auto",
        "rationale": "Use the audited business objects and relationship requirements.",
    })
    bindings = tuple(
        VisibleTextBindingSpec(
            text_id=f"T{index}",
            text=text,
            root_id=f"ROOT-{index}",
            order=index,
            role="root_module",
            hierarchy_level=1,
        )
        for index, text in enumerate(base.typography.visible_text, start=1)
    )
    return replace(
        base,
        region_graph=validate_region_graph(graph),
        visual_medium_policy=medium,
        visible_text_bindings=bindings,
        composition=replace(base.composition, focus_policy=focus_policy),
    )


@pytest.mark.parametrize(
    "topology,focus_id,focus_policy,edges",
    CASES,
    ids=[case[0] for case in CASES],
)
def test_stage2_visual_design_end_to_end(topology, focus_id, focus_policy, edges):
    graph = _bound_graph(topology, focus_id, focus_policy, edges)
    assert audit_region_graph(_audit_payload(graph, topology, focus_id, focus_policy)) == []

    if topology == "parallel_set":
        assert {region["role"] for region in graph["regions"]} == {"peer"}
        assert all(region["priority"] == "primary" for region in graph["regions"])
        assert "result" not in {region["role"] for region in graph["regions"]}

    ir = build_final_prompt_ir(_artifact(graph, focus_policy))
    prompt = render_final_prompt(ir)
    assert ir.region_graph is not None
    assert ir.visual_medium_policy is not None
    assert ir.micro_visual_freedom is not None
    assert "Macro region structure:" in prompt
    assert "ImageGen region-internal freedom:" in prompt
    assert "Macro visual authority remains locked:" in prompt
    for visible_text in ir.visible_text:
        assert prompt.count(f'- Exact visible text: "{visible_text}"') == 1
    for token in ("RG01", "RG02", "RG03", "E1", "E2", "E3", "T1", "T2", "T3", "root_module"):
        assert token not in prompt
