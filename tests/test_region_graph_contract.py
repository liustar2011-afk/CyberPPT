from pathlib import Path
import json

import jsonschema
import pytest

from cyberppt.region_graph import validate_region_graph


ROOT = Path(__file__).resolve().parents[1]
REGION_SCHEMA = ROOT / "vendor" / "skills" / "ppt-visual-structure-designer" / "assets" / "region-graph.schema.json"
PAGE_SCHEMA = ROOT / "vendor" / "skills" / "ppt-visual-structure-designer" / "assets" / "page-visual-spec.schema.json"


def _graph():
    return {
        "canvas_ratio": "2:1",
        "primary_axis": "horizontal",
        "regions": [
            {
                "id": "RG01",
                "semantic_refs": ["E1"],
                "role": "source",
                "anchor": "left",
                "weight": 0.4,
                "span": "half",
                "priority": "primary",
                "text_ids": ["P01-T01"],
            },
            {
                "id": "RG02",
                "semantic_refs": ["E2"],
                "role": "result",
                "anchor": "right",
                "weight": 0.6,
                "span": "half",
                "priority": "primary",
            },
        ],
        "relations": [{"from": "RG01", "to": "RG02", "type": "flow"}],
    }


def test_region_graph_contract_normalizes_valid_graph():
    spec = validate_region_graph(_graph())
    assert spec.canvas_ratio == "2:1"
    assert spec.primary_axis == "horizontal"
    assert [item.id for item in spec.regions] == ["RG01", "RG02"]
    assert spec.relations[0].type == "flow"
    assert spec.to_dict() == _graph()


def test_region_graph_rejects_duplicate_region_ids():
    graph = _graph()
    graph["regions"][1]["id"] = "RG01"
    with pytest.raises(ValueError, match="duplicate Region Graph region id"):
        validate_region_graph(graph)


def test_region_graph_rejects_unknown_relation_endpoint():
    graph = _graph()
    graph["relations"][0]["to"] = "RG99"
    with pytest.raises(ValueError, match="unknown region"):
        validate_region_graph(graph)


def test_region_graph_rejects_invalid_weight_and_semantic_ref():
    graph = _graph()
    graph["regions"][0]["weight"] = 1.2
    with pytest.raises(ValueError, match="weight"):
        validate_region_graph(graph)
    graph = _graph()
    graph["regions"][0]["semantic_refs"] = ["node-a"]
    with pytest.raises(ValueError, match="E<number>"):
        validate_region_graph(graph)


def test_standalone_region_graph_schema_accepts_valid_graph():
    schema = json.loads(REGION_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(_graph())


def test_page_schema_exposes_optional_region_graph_contract():
    schema = json.loads(PAGE_SCHEMA.read_text(encoding="utf-8"))
    assert "region_graph" in schema["properties"]
    assert "region_graph" not in schema["required"]
    assert schema["properties"]["region_graph"]["properties"]["canvas_ratio"]["const"] == "2:1"
