"""Independent macro-composition strategy contract for Stage 02.

Semantic topology constrains relationship truth.  CompositionStrategy chooses
how that truth occupies the page.  The two contracts are intentionally
separate so the same topology can be rendered with different legal macro
geometries without changing business meaning.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Mapping


COMPOSITION_STRATEGY_VERSION = "composition-strategy-v1"


@dataclass(frozen=True)
class CompositionStrategySpec:
    strategy_id: str
    topology: str
    primary_axis: str
    geometry: str
    anchor_policy: str
    weight_policy: str
    span_policy: str
    score: float
    rationale: tuple[str, ...]
    version: str = COMPOSITION_STRATEGY_VERSION

    def __post_init__(self) -> None:
        if not self.strategy_id or not self.topology:
            raise ValueError("composition strategy requires strategy_id and topology")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("composition strategy score must be between 0 and 1")
        if not self.rationale:
            raise ValueError("composition strategy rationale must not be empty")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


_STRATEGY_BLUEPRINTS: dict[str, dict[str, str]] = {
    "editorial_horizontal": {
        "primary_axis": "horizontal",
        "geometry": "horizontal editorial progression",
        "anchor_policy": "axis",
        "weight_policy": "semantic_focus",
        "span_policy": "compact",
    },
    "editorial_vertical": {
        "primary_axis": "vertical",
        "geometry": "vertical editorial progression",
        "anchor_policy": "axis",
        "weight_policy": "semantic_focus",
        "span_policy": "compact",
    },
    "open_spatial_field": {
        "primary_axis": "free_spatial",
        "geometry": "open asymmetric relationship field",
        "anchor_policy": "free",
        "weight_policy": "semantic_focus",
        "span_policy": "free",
    },
    "radial_focus_field": {
        "primary_axis": "radial",
        "geometry": "focus-led radial relationship field",
        "anchor_policy": "focus_centered",
        "weight_policy": "semantic_focus",
        "span_policy": "focus_half",
    },
    "layered_editorial_stack": {
        "primary_axis": "layered",
        "geometry": "layered editorial stack",
        "anchor_policy": "axis",
        "weight_policy": "semantic_focus",
        "span_policy": "band",
    },
    "split_boundary_field": {
        "primary_axis": "bidirectional",
        "geometry": "split boundary and interface field",
        "anchor_policy": "split",
        "weight_policy": "paired",
        "span_policy": "half",
    },
    "stepped_spatial_path": {
        "primary_axis": "free_spatial",
        "geometry": "stepped spatial path",
        "anchor_policy": "stepped",
        "weight_policy": "semantic_focus",
        "span_policy": "compact",
    },
}


_LEGAL_STRATEGIES_BY_TOPOLOGY: dict[str, tuple[str, ...]] = {
    "parallel_set": ("open_spatial_field", "editorial_horizontal", "editorial_vertical"),
    "causal_convergence": ("radial_focus_field", "editorial_horizontal", "editorial_vertical"),
    "layered_architecture": ("layered_editorial_stack", "editorial_vertical", "editorial_horizontal"),
    "directed_flow": ("editorial_horizontal", "editorial_vertical", "stepped_spatial_path"),
    "lifecycle_loop": ("radial_focus_field", "open_spatial_field", "editorial_horizontal"),
    "governance_boundary": ("split_boundary_field", "editorial_horizontal", "editorial_vertical"),
    "ecosystem_map": ("open_spatial_field", "radial_focus_field", "editorial_horizontal"),
    "allocation_flow": ("editorial_horizontal", "editorial_vertical", "radial_focus_field"),
    "conclusion_anchor": ("radial_focus_field", "editorial_horizontal", "editorial_vertical"),
}


def legal_strategy_ids(topology: str) -> tuple[str, ...]:
    try:
        return _LEGAL_STRATEGIES_BY_TOPOLOGY[topology]
    except KeyError as exc:
        raise ValueError(f"unsupported composition topology: {topology!r}") from exc


def _score_strategy(
    strategy_id: str,
    *,
    focus_policy: str,
    evidence_count: int,
    medium: str,
    adjacent_strategy_ids: frozenset[str],
) -> tuple[float, list[str]]:
    score = 0.50
    reasons = ["legal for semantic topology"]
    if focus_policy == "single_anchor":
        if strategy_id == "radial_focus_field":
            score += 0.18; reasons.append("single anchor benefits from a focus-led field")
        elif strategy_id in {"editorial_horizontal", "editorial_vertical"}:
            score += 0.08; reasons.append("single anchor remains legible on one editorial axis")
    elif focus_policy == "paired_focus":
        if strategy_id == "split_boundary_field":
            score += 0.22; reasons.append("paired focus benefits from a split interface field")
        elif strategy_id in {"editorial_horizontal", "editorial_vertical"}:
            score += 0.08; reasons.append("paired focus can share an editorial axis")
    elif focus_policy == "peer_field":
        if strategy_id == "open_spatial_field":
            score += 0.18; reasons.append("peer evidence benefits from an open field")
        elif strategy_id in {"editorial_horizontal", "editorial_vertical"}:
            score += 0.10; reasons.append("peer evidence can share a common editorial baseline")
    elif focus_policy == "distributed_focus":
        if strategy_id == "open_spatial_field":
            score += 0.20; reasons.append("distributed focus benefits from open spatial grouping")
        elif strategy_id == "radial_focus_field":
            score += 0.10; reasons.append("distributed actors can use a radial relationship field")
    elif focus_policy == "sequence_focus":
        if strategy_id in {"editorial_horizontal", "editorial_vertical"}:
            score += 0.17; reasons.append("sequence focus benefits from a directional editorial axis")
        elif strategy_id == "stepped_spatial_path":
            score += 0.15; reasons.append("sequence can use a stepped path without changing relation truth")
        elif strategy_id == "layered_editorial_stack":
            score += 0.14; reasons.append("sequence can preserve dependency in a layered stack")

    if evidence_count >= 5:
        if strategy_id in {"open_spatial_field", "editorial_vertical", "layered_editorial_stack"}:
            score += 0.08; reasons.append("higher evidence count needs more distributed capacity")
    elif evidence_count <= 3 and strategy_id in {"radial_focus_field", "editorial_horizontal"}:
        score += 0.05; reasons.append("compact evidence count supports a stronger focal gesture")

    if medium == "business_scene" and strategy_id in {"editorial_horizontal", "open_spatial_field"}:
        score += 0.09; reasons.append("business scene benefits from horizontal/open integration")
    elif medium == "relationship_diagram" and strategy_id in {"open_spatial_field", "radial_focus_field", "layered_editorial_stack"}:
        score += 0.08; reasons.append("relationship diagram benefits from explicit spatial structure")
    elif medium == "data_visualization" and strategy_id in {"editorial_horizontal", "editorial_vertical"}:
        score += 0.08; reasons.append("data visualization benefits from an aligned editorial axis")

    if strategy_id in adjacent_strategy_ids:
        score -= 0.24
        reasons.append("adjacent-page rhythm penalizes repeating the same macro strategy")

    return max(0.0, min(score, 0.99)), reasons


def materialize_composition_strategy(
    *,
    topology: str,
    strategy_id: str,
    score: float = 1.0,
    rationale: tuple[str, ...] = ("explicit composition strategy",),
) -> CompositionStrategySpec:
    if strategy_id not in legal_strategy_ids(topology):
        raise ValueError(f"composition strategy {strategy_id!r} is not legal for topology {topology!r}")
    blueprint = _STRATEGY_BLUEPRINTS[strategy_id]
    return CompositionStrategySpec(
        strategy_id=strategy_id,
        topology=topology,
        primary_axis=blueprint["primary_axis"],
        geometry=blueprint["geometry"],
        anchor_policy=blueprint["anchor_policy"],
        weight_policy=blueprint["weight_policy"],
        span_policy=blueprint["span_policy"],
        score=score,
        rationale=rationale,
    )


# Compatibility only: old callers that do not provide CompositionStrategy keep
# their historical macro axis.  This is not the v3 production resolver.
_LEGACY_DEFAULT_STRATEGY_BY_TOPOLOGY = {
    "parallel_set": "open_spatial_field",
    "causal_convergence": "radial_focus_field",
    "layered_architecture": "layered_editorial_stack",
    "directed_flow": "editorial_horizontal",
    "lifecycle_loop": "radial_focus_field",
    "governance_boundary": "editorial_horizontal",
    "ecosystem_map": "open_spatial_field",
    "allocation_flow": "editorial_horizontal",
    "conclusion_anchor": "editorial_horizontal",
}


def legacy_composition_strategy(topology: str) -> CompositionStrategySpec:
    try:
        strategy_id = _LEGACY_DEFAULT_STRATEGY_BY_TOPOLOGY[topology]
    except KeyError as exc:
        raise ValueError(f"unsupported composition topology: {topology!r}") from exc
    return materialize_composition_strategy(
        topology=topology,
        strategy_id=strategy_id,
        score=0.5,
        rationale=("legacy Stage02 compatibility projection",),
    )


def validate_composition_strategy(value: Mapping[str, object]) -> CompositionStrategySpec:
    if not isinstance(value, Mapping):
        raise ValueError("composition_strategy must be an object")
    topology = str(value.get("topology") or "").strip()
    strategy_id = str(value.get("strategy_id") or "").strip()
    if not topology or not strategy_id:
        raise ValueError("composition_strategy requires topology and strategy_id")
    expected = materialize_composition_strategy(topology=topology, strategy_id=strategy_id)
    rationale_raw = value.get("rationale")
    if not isinstance(rationale_raw, (list, tuple)) or not rationale_raw:
        raise ValueError("composition_strategy rationale must be a non-empty array")
    try:
        score = float(value.get("score", 1.0))
    except (TypeError, ValueError) as exc:
        raise ValueError("composition_strategy score must be numeric") from exc
    spec = CompositionStrategySpec(
        strategy_id=strategy_id,
        topology=topology,
        primary_axis=str(value.get("primary_axis") or "").strip(),
        geometry=str(value.get("geometry") or "").strip(),
        anchor_policy=str(value.get("anchor_policy") or "").strip(),
        weight_policy=str(value.get("weight_policy") or "").strip(),
        span_policy=str(value.get("span_policy") or "").strip(),
        score=score,
        rationale=tuple(str(item).strip() for item in rationale_raw if str(item).strip()),
        version=str(value.get("version") or COMPOSITION_STRATEGY_VERSION),
    )
    for field in ("primary_axis", "geometry", "anchor_policy", "weight_policy", "span_policy"):
        if getattr(spec, field) != getattr(expected, field):
            raise ValueError(f"composition_strategy {field} drifted from the declared strategy blueprint")
    return spec


def resolve_composition_strategy(
    *,
    topology: str,
    focus_policy: str,
    evidence_count: int,
    medium: str = "",
    page_index: int = 0,
    adjacent_strategy_ids: Iterable[str] = (),
) -> CompositionStrategySpec:
    """Choose macro geometry independently from semantic topology.

    Topology limits the legal strategy set; it never determines one axis by
    itself.  Page semantics, density, visual medium and adjacent-page rhythm
    score the legal alternatives.
    """

    legal = legal_strategy_ids(topology)
    adjacent = frozenset(str(value) for value in adjacent_strategy_ids if str(value))
    ranked: list[tuple[float, int, str, list[str]]] = []
    for order, strategy_id in enumerate(legal):
        score, reasons = _score_strategy(
            strategy_id,
            focus_policy=focus_policy,
            evidence_count=max(1, int(evidence_count)),
            medium=str(medium or ""),
            adjacent_strategy_ids=adjacent,
        )
        # Deterministic low-weight page rhythm tie-breaker.  It cannot overrule
        # semantic scoring but prevents repeated ties from collapsing a deck
        # into one macro layout.
        rhythm_rank = (order - (page_index % len(legal))) % len(legal)
        ranked.append((score, -rhythm_rank, strategy_id, reasons))
    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
    score, _, strategy_id, reasons = ranked[0]
    blueprint = _STRATEGY_BLUEPRINTS[strategy_id]
    return CompositionStrategySpec(
        strategy_id=strategy_id,
        topology=topology,
        primary_axis=blueprint["primary_axis"],
        geometry=blueprint["geometry"],
        anchor_policy=blueprint["anchor_policy"],
        weight_policy=blueprint["weight_policy"],
        span_policy=blueprint["span_policy"],
        score=round(score, 3),
        rationale=tuple(reasons),
    )


__all__ = [
    "COMPOSITION_STRATEGY_VERSION",
    "CompositionStrategySpec",
    "legal_strategy_ids",
    "legacy_composition_strategy",
    "materialize_composition_strategy",
    "resolve_composition_strategy",
    "validate_composition_strategy",
]
