import pytest

from cyberppt.region_graph import build_region_graph


def _build(topology, *, focus="E3", focus_policy="sequence_focus", edges=None):
    return build_region_graph(
        topology=topology,
        evidence_ids=["E1", "E2", "E3"],
        focus_id=focus,
        reading_sequence=["E1", "E2", "E3"],
        semantic_edges=edges or [],
        focus_policy=focus_policy,
    )


def _region(graph, evidence_id):
    return next(item for item in graph["regions"] if item["semantic_refs"] == [evidence_id])


def test_parallel_set_compiles_equal_peer_field():
    graph = _build(
        "parallel_set",
        focus="E1",
        focus_policy="peer_field",
        edges=[
            {"from": "E1", "to": "E2", "relation": "peer", "direction": "none"},
            {"from": "E2", "to": "E3", "relation": "peer", "direction": "none"},
        ],
    )
    assert graph["primary_axis"] == "free_spatial"
    assert {item["role"] for item in graph["regions"]} == {"peer"}
    assert {item["priority"] for item in graph["regions"]} == {"primary"}
    assert {item["anchor"] for item in graph["regions"]} == {"free"}
    assert {item["type"] for item in graph["relations"]} == {"peer"}


def test_causal_convergence_compiles_center_result():
    graph = _build(
        "causal_convergence",
        focus_policy="single_anchor",
        edges=[
            {"from": "E1", "to": "E3", "relation": "converge", "direction": "forward"},
            {"from": "E2", "to": "E3", "relation": "converge", "direction": "forward"},
        ],
    )
    assert graph["primary_axis"] == "radial"
    assert _region(graph, "E3")["role"] == "result"
    assert _region(graph, "E3")["anchor"] == "center"
    assert _region(graph, "E3")["weight"] == 0.4
    assert len([item for item in graph["relations"] if item["type"] == "converge"]) == 2


def test_layered_architecture_compiles_layer_bands():
    graph = _build(
        "layered_architecture",
        edges=[
            {"from": "E1", "to": "E2", "relation": "layer", "direction": "forward"},
            {"from": "E2", "to": "E3", "relation": "layer", "direction": "forward"},
        ],
    )
    assert graph["primary_axis"] == "layered"
    assert [item["role"] for item in graph["regions"]] == ["layer", "layer", "layer"]
    assert {item["span"] for item in graph["regions"]} == {"band"}
    assert {item["type"] for item in graph["relations"]} == {"dependency"}


def test_directed_flow_compiles_horizontal_stages():
    graph = _build(
        "directed_flow",
        edges=[
            {"from": "E1", "to": "E2", "relation": "flow", "direction": "forward"},
            {"from": "E2", "to": "E3", "relation": "flow", "direction": "forward"},
        ],
    )
    assert graph["primary_axis"] == "horizontal"
    assert _region(graph, "E1")["anchor"] == "left"
    assert _region(graph, "E3")["anchor"] == "right"
    assert _region(graph, "E3")["role"] == "result"
    assert {item["type"] for item in graph["relations"]} == {"flow"}


def test_lifecycle_loop_compiles_feedback_relation():
    graph = _build(
        "lifecycle_loop",
        edges=[
            {"from": "E1", "to": "E2", "relation": "loop", "direction": "forward"},
            {"from": "E2", "to": "E3", "relation": "loop", "direction": "forward"},
            {"from": "E3", "to": "E1", "relation": "loop", "direction": "backward"},
        ],
    )
    assert graph["primary_axis"] == "radial"
    assert {item["role"] for item in graph["regions"]} == {"lifecycle_stage"}
    assert {item["anchor"] for item in graph["regions"]} == {"free"}
    assert "feedback" in {item["type"] for item in graph["relations"]}


def test_governance_boundary_compiles_boundary_anchor_and_sides():
    graph = _build(
        "governance_boundary",
        focus="E2",
        focus_policy="paired_focus",
        edges=[
            {"from": "E1", "to": "E2", "relation": "boundary", "direction": "forward"},
            {"from": "E2", "to": "E3", "relation": "control", "direction": "forward"},
        ],
    )
    assert graph["primary_axis"] == "horizontal"
    assert _region(graph, "E2")["role"] == "boundary_anchor"
    assert _region(graph, "E2")["anchor"] == "center"
    assert _region(graph, "E1")["anchor"] == "left"
    assert _region(graph, "E3")["anchor"] == "right"
    assert {item["type"] for item in graph["relations"]} == {"boundary"}


def test_ecosystem_map_compiles_distributed_actor_field():
    graph = _build(
        "ecosystem_map",
        focus="E1",
        focus_policy="distributed_focus",
        edges=[
            {"from": "E1", "to": "E2", "relation": "exchange", "direction": "bidirectional"},
            {"from": "E2", "to": "E3", "relation": "exchange", "direction": "bidirectional"},
        ],
    )
    assert graph["primary_axis"] == "free_spatial"
    assert {item["role"] for item in graph["regions"]} == {"actor"}
    assert {item["priority"] for item in graph["regions"]} == {"primary"}
    assert {item["anchor"] for item in graph["regions"]} == {"free"}
    assert {item["type"] for item in graph["relations"]} == {"interface"}


def test_allocation_flow_compiles_source_and_destinations():
    graph = _build(
        "allocation_flow",
        focus="E1",
        edges=[
            {"from": "E1", "to": "E2", "relation": "diverge", "direction": "forward"},
            {"from": "E1", "to": "E3", "relation": "diverge", "direction": "forward"},
        ],
    )
    assert graph["primary_axis"] == "horizontal"
    assert _region(graph, "E1")["role"] == "source"
    assert _region(graph, "E2")["role"] == "destination"
    assert _region(graph, "E3")["role"] == "destination"
    assert {item["type"] for item in graph["relations"]} == {"allocation"}


def test_conclusion_anchor_compiles_single_conclusion_region():
    graph = _build(
        "conclusion_anchor",
        focus_policy="single_anchor",
        edges=[
            {"from": "E1", "to": "E3", "relation": "evidence", "direction": "forward"},
            {"from": "E2", "to": "E3", "relation": "evidence", "direction": "forward"},
        ],
    )
    assert graph["primary_axis"] == "horizontal"
    assert _region(graph, "E3")["role"] == "conclusion"
    assert _region(graph, "E3")["priority"] == "primary"
    assert _region(graph, "E1")["priority"] == "secondary"
    assert {item["type"] for item in graph["relations"]} == {"support"}


@pytest.mark.parametrize("topology", ["unknown", "cards", "matrix"])
def test_region_graph_compiler_rejects_unknown_topology(topology):
    with pytest.raises(ValueError, match="unsupported Region Graph topology"):
        _build(topology)
