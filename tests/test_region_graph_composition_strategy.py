from cyberppt.composition_strategy import (
    legal_strategy_ids, materialize_composition_strategy, resolve_composition_strategy,
)
from cyberppt.region_graph import build_region_graph


def _graph(strategy):
    return build_region_graph(
        topology="directed_flow",
        evidence_ids=("E1", "E2", "E3"),
        focus_id="E3",
        reading_sequence=("E1", "E2", "E3"),
        semantic_edges=(
            {"from": "E1", "to": "E2", "relation": "flow"},
            {"from": "E2", "to": "E3", "relation": "flow"},
        ),
        focus_policy="sequence_focus",
        composition_strategy=strategy,
    )


def test_region_graph_consumes_three_legal_macro_strategies_for_same_topology():
    signatures = set()
    relation_signatures = set()
    for strategy_id in legal_strategy_ids("directed_flow"):
        strategy = materialize_composition_strategy(topology="directed_flow", strategy_id=strategy_id)
        graph = _graph(strategy)
        assert graph["composition_strategy_id"] == strategy_id
        signatures.add((graph["primary_axis"], tuple(item["anchor"] for item in graph["regions"])))
        relation_signatures.add(tuple((item["from"], item["to"], item["type"]) for item in graph["relations"]))
    assert len(signatures) >= 3
    assert len(relation_signatures) == 1


def test_legacy_region_graph_call_preserves_compatibility_projection():
    graph = build_region_graph(
        topology="layered_architecture",
        evidence_ids=("E1", "E2", "E3"),
        focus_id="E3",
        reading_sequence=("E1", "E2", "E3"),
        semantic_edges=(),
        focus_policy="sequence_focus",
    )
    assert graph["primary_axis"] == "layered"
    assert graph["composition_strategy_id"] == "layered_editorial_stack"


def test_dynamic_resolver_can_change_axis_without_changing_topology():
    first = resolve_composition_strategy(
        topology="directed_flow", focus_policy="sequence_focus", evidence_count=3,
        medium="business_scene", page_index=1,
    )
    second = resolve_composition_strategy(
        topology="directed_flow", focus_policy="sequence_focus", evidence_count=6,
        medium="relationship_diagram", page_index=2, adjacent_strategy_ids=(first.strategy_id,),
    )
    assert first.topology == second.topology
    assert first.strategy_id != second.strategy_id
