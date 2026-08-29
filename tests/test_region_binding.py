import pytest

from cyberppt.region_binding import bind_region_graph_text, region_text_owner_map


def _graph():
    return {
        "canvas_ratio": "2:1",
        "primary_axis": "horizontal",
        "regions": [
            {
                "id": "RG01",
                "semantic_refs": ["E1"],
                "role": "stage",
                "anchor": "left",
                "weight": 0.5,
                "span": "compact",
                "priority": "primary",
            },
            {
                "id": "RG02",
                "semantic_refs": ["E2"],
                "role": "result",
                "anchor": "right",
                "weight": 0.5,
                "span": "compact",
                "priority": "primary",
            },
        ],
        "relations": [{"from": "RG01", "to": "RG02", "type": "flow"}],
    }


def test_bind_region_graph_text_assigns_exact_locked_ids():
    graph = bind_region_graph_text(
        _graph(),
        evidence_text_ids={"E1": ["P01-T01", "P01-T02"], "E2": ["P01-T03"]},
        required_text_ids=["P01-T01", "P01-T02", "P01-T03"],
    )
    assert graph["regions"][0]["text_ids"] == ["P01-T01", "P01-T02"]
    assert graph["regions"][1]["text_ids"] == ["P01-T03"]
    assert region_text_owner_map(graph) == {
        "P01-T01": "RG01",
        "P01-T02": "RG01",
        "P01-T03": "RG02",
    }


def test_bind_region_graph_text_rejects_missing_locked_id():
    with pytest.raises(ValueError, match="cover exact required text ids"):
        bind_region_graph_text(
            _graph(),
            evidence_text_ids={"E1": ["P01-T01"], "E2": ["P01-T03"]},
            required_text_ids=["P01-T01", "P01-T02", "P01-T03"],
        )


def test_bind_region_graph_text_rejects_duplicate_locked_id():
    with pytest.raises(ValueError, match="more than one evidence"):
        bind_region_graph_text(
            _graph(),
            evidence_text_ids={"E1": ["P01-T01"], "E2": ["P01-T01"]},
            required_text_ids=["P01-T01"],
        )


def test_bind_region_graph_text_rejects_evidence_without_unique_region():
    graph = _graph()
    graph["regions"][1]["semantic_refs"] = ["E1"]
    with pytest.raises(ValueError, match="exactly one Region Graph region"):
        bind_region_graph_text(
            graph,
            evidence_text_ids={"E1": ["P01-T01"]},
            required_text_ids=["P01-T01"],
        )


def test_region_text_owner_map_rejects_unbound_region():
    with pytest.raises(ValueError, match="has no text_ids"):
        region_text_owner_map(_graph())
