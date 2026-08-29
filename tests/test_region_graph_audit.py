from copy import deepcopy

from cyberppt.region_binding import bind_region_graph_text, region_text_owner_map
from cyberppt.region_graph import build_region_graph
from cyberppt.region_graph_audit import audit_region_graph


def _page(topology="causal_convergence"):
    focus_id = "E3"
    focus_policy = "single_anchor"
    edges = [
        {"from": "E1", "to": "E3", "relation": "converge", "direction": "forward"},
        {"from": "E2", "to": "E3", "relation": "converge", "direction": "forward"},
    ]
    if topology == "parallel_set":
        focus_id = "E1"
        focus_policy = "peer_field"
        edges = [
            {"from": "E1", "to": "E2", "relation": "peer", "direction": "none"},
            {"from": "E2", "to": "E3", "relation": "peer", "direction": "none"},
        ]
    graph = bind_region_graph_text(
        build_region_graph(
            topology=topology,
            evidence_ids=["E1", "E2", "E3"],
            focus_id=focus_id,
            reading_sequence=["E1", "E2", "E3"],
            semantic_edges=edges,
            focus_policy=focus_policy,
        ),
        evidence_text_ids={
            "E1": ["P01-T01"],
            "E2": ["P01-T02"],
            "E3": ["P01-T03"],
        },
        required_text_ids=["P01-T01", "P01-T02", "P01-T03"],
    )
    owners = region_text_owner_map(graph)
    return {
        "region_graph": graph,
        "evidence_units": [
            {"id": "E1", "priority": "P0"},
            {"id": "E2", "priority": "P0"},
            {"id": "E3", "priority": "P0"},
        ],
        "semantic_graph": {"topology": topology, "focus_node": focus_id},
        "visual_decision": {"focus_policy": focus_policy},
        "generation_handoff": {"required_text_ids": ["P01-T01", "P01-T02", "P01-T03"]},
        "final_text": [
            {"id": text_id, "region_id": owners[text_id]}
            for text_id in ["P01-T01", "P01-T02", "P01-T03"]
        ],
    }


def _codes(page):
    return [item["code"] for item in audit_region_graph(page)]


def test_region_graph_audit_accepts_valid_convergence():
    assert audit_region_graph(_page()) == []


def test_region_graph_audit_accepts_valid_parallel_peer_field():
    assert audit_region_graph(_page("parallel_set")) == []


def test_region_graph_audit_reports_missing_graph_for_rg_bound_text():
    page = _page()
    del page["region_graph"]
    assert _codes(page) == ["REGION_GRAPH_MISSING"]


def test_region_graph_audit_reports_missing_text_binding():
    page = _page()
    page["region_graph"]["regions"][0]["text_ids"] = []
    assert "REGION_BINDING_MISSING" in _codes(page)


def test_region_graph_audit_reports_invalid_weight():
    page = _page()
    page["region_graph"]["regions"][0]["weight"] = 1.5
    assert _codes(page) == ["REGION_WEIGHT_INVALID"]


def test_region_graph_audit_reports_invalid_role():
    page = _page()
    page["region_graph"]["regions"][0]["role"] = "card"
    assert "REGION_ROLE_INVALID" in _codes(page)


def test_region_graph_audit_reports_invalid_relation_endpoint():
    page = _page()
    page["region_graph"]["relations"][0]["to"] = "RG99"
    assert _codes(page) == ["REGION_RELATION_INVALID"]


def test_region_graph_audit_reports_topology_mismatch():
    page = _page()
    page["region_graph"]["relations"] = []
    assert "REGION_TOPOLOGY_MISMATCH" in _codes(page)


def test_region_graph_audit_reports_final_text_region_drift():
    page = _page()
    page["final_text"][0]["region_id"] = "RG99"
    assert "REGION_BINDING_MISSING" in _codes(page)


def test_legacy_page_without_region_graph_or_rg_bindings_is_compatible():
    page = _page()
    del page["region_graph"]
    for item in page["final_text"]:
        item["region_id"] = "R_RELATION"
    assert audit_region_graph(page) == []
