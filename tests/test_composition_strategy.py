from cyberppt.composition_strategy import legal_strategy_ids, resolve_composition_strategy


TOPOLOGIES = (
    "parallel_set",
    "causal_convergence",
    "layered_architecture",
    "directed_flow",
    "lifecycle_loop",
    "governance_boundary",
    "ecosystem_map",
    "allocation_flow",
    "conclusion_anchor",
)


def test_every_topology_allows_at_least_three_macro_strategies():
    for topology in TOPOLOGIES:
        strategies = legal_strategy_ids(topology)
        assert len(strategies) >= 3
        assert len(strategies) == len(set(strategies))


def test_same_topology_can_resolve_different_macro_strategies_from_page_semantics():
    sparse = resolve_composition_strategy(
        topology="directed_flow",
        focus_policy="sequence_focus",
        evidence_count=2,
        medium="business_scene",
        page_index=1,
    )
    dense = resolve_composition_strategy(
        topology="directed_flow",
        focus_policy="sequence_focus",
        evidence_count=6,
        medium="relationship_diagram",
        page_index=2,
    )
    assert sparse.topology == dense.topology == "directed_flow"
    assert sparse.strategy_id != dense.strategy_id or sparse.primary_axis != dense.primary_axis


def test_adjacent_page_rhythm_penalizes_repeating_same_strategy():
    first = resolve_composition_strategy(
        topology="parallel_set",
        focus_policy="peer_field",
        evidence_count=4,
        medium="relationship_diagram",
        page_index=3,
    )
    second = resolve_composition_strategy(
        topology="parallel_set",
        focus_policy="peer_field",
        evidence_count=4,
        medium="relationship_diagram",
        page_index=4,
        adjacent_strategy_ids=(first.strategy_id,),
    )
    assert second.strategy_id != first.strategy_id


def test_strategy_rationale_tracks_actual_scoring_signals():
    result = resolve_composition_strategy(
        topology="governance_boundary",
        focus_policy="paired_focus",
        evidence_count=4,
        medium="relationship_diagram",
        page_index=1,
    )
    assert result.score > 0.5
    assert any("paired focus" in reason for reason in result.rationale)
