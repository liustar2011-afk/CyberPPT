"""Resolve canonical semantic intents into auditable spatial grammar."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from cyberppt.semantic_intent import SemanticIntentDecision


@dataclass(frozen=True)
class CompositionDecision:
    semantic_intent: str
    primary_axis: str
    spatial_organization: str
    reading_path: tuple[str, ...]
    relationship_encoding: tuple[str, ...]
    required_elements: tuple[str, ...]
    dominant_ratio: float
    max_independent_units: int
    avoid: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


_COMMON_AVOID = (
    "equal_card_wall",
    "one_icon_per_bullet",
    "disconnected_left_text_right_image",
    "multiple_visual_centers",
)


COMPOSITION_GRAMMARS: dict[str, dict[str, object]] = {
    "coordinate_peer_set": dict(axis="shared_field", organization="peer business objects share one field without implying order, hierarchy, or a privileged result node", path=("peer set", "shared judgment or category context"), encoding=("grouping", "alignment", "shared field"), required=("peer objects", "shared context"), ratio=0.60, units=7),
    "correspondence_mapping": dict(axis="paired_mapping", organization="source objects remain visibly bound to their corresponding response, capability, or counterpart", path=("source object", "correspondence", "matched object"), encoding=("mapping", "pair binding"), required=("source objects", "matched objects", "mapping relation"), ratio=0.60, units=8),
    "single_judgment_anchor": dict(axis="center", organization="single result object anchors a small evidence field", path=("evidence", "judgment"), encoding=("attachment", "scale hierarchy"), required=("judgment anchor", "supporting evidence"), ratio=0.72, units=4),
    "multi_semantic_foundation": dict(axis="bottom_to_top", organization="different foundations enter one shared base and support a common capability", path=("foundations", "shared base", "capability"), encoding=("support", "convergence"), required=("distinct foundations", "shared base", "supported capability"), ratio=0.65, units=7),
    "evidence_to_judgment": dict(axis="convergent", organization="evidence paths converge on one judgment zone", path=("evidence", "judgment", "implication"), encoding=("evidence edge", "convergence"), required=("evidence units", "judgment zone"), ratio=0.65, units=6),
    "scene_embedded_flow": dict(axis="left_to_right", organization="a directional action chain runs through one continuous industry scene", path=("entry action", "key action", "result"), encoding=("flow", "object adjacency"), required=("scene anchor", "action nodes", "direction"), ratio=0.68, units=5),
    "transformation_pipeline": dict(axis="left_to_right", organization="weighted input, processing, and output zones form one transformation channel", path=("input", "processing", "output"), encoding=("transform", "directional connector"), required=("input", "processing", "output", "direction"), ratio=0.65, units=5),
    "convergence_to_capability": dict(axis="many_to_one", organization="multiple sources converge into a concrete capability engine", path=("sources", "convergence", "capability"), encoding=("convergence", "role labels"), required=("multiple sources", "capability engine"), ratio=0.65, units=6),
    "capability_to_outcomes": dict(axis="one_to_many", organization="one dominant capability opens into differentiated result scenes", path=("capability", "outcome branches"), encoding=("divergence", "result attachment"), required=("capability", "distinct outcomes"), ratio=0.65, units=6),
    "layered_architecture": dict(axis="bottom_to_top", organization="non-equal depth layers show foundation, capability, service, and application dependencies", path=("foundation", "capability", "service", "application"), encoding=("support", "layer dependency"), required=("foundation", "dependent layers", "one main flow"), ratio=0.65, units=5),
    "dual_engine_synergy": dict(axis="cross_interface", organization="two non-symmetric actors connect through one shared interface or result", path=("actor A", "shared interface", "actor B", "shared outcome"), encoding=("exchange", "shared object"), required=("two actors", "shared interface", "shared outcome"), ratio=0.58, units=6),
    "closed_loop_operation": dict(axis="forward_with_return", organization="a main operating chain includes an explicit return path to a named feedback target", path=("start", "operation", "result", "validation", "feedback"), encoding=("flow", "feedback"), required=("start", "key nodes", "feedback target", "return direction"), ratio=0.65, units=6),
    "comparison_tension": dict(axis="shared_axis", organization="two states share one comparison axis and meet at a visible difference boundary", path=("comparison basis", "state A", "difference", "state B"), encoding=("contrast", "aligned measure"), required=("shared basis", "two states", "differences"), ratio=0.55, units=5),
    "phased_roadmap": dict(axis="near_to_far", organization="unequal phases advance toward milestones with visible sequencing", path=("current", "near term", "mid term", "long term"), encoding=("sequence", "milestone"), required=("phases", "milestones", "direction"), ratio=0.65, units=6),
    "network_ecosystem": dict(axis="directed_network", organization="primary and secondary actors exchange named resources inside a visible governance boundary", path=("primary actor", "exchange", "partner actors", "shared outcome"), encoding=("directed exchange", "boundary"), required=("primary actor", "partner actors", "exchange labels"), ratio=0.60, units=9),
    "policy_to_action": dict(axis="top_to_bottom", organization="policy constraints descend into tasks, mechanisms, and results", path=("policy", "task", "mechanism", "result"), encoding=("constraint", "implementation"), required=("policy requirement", "business task", "mechanism"), ratio=0.65, units=6),
    "risk_control_boundary": dict(axis="outside_to_inside_to_output", organization="outside, authorized entry, controlled processing, and allowed output form a trusted boundary", path=("outside", "gate", "controlled zone", "allowed output"), encoding=("boundary", "control gate"), required=("inside", "outside", "controlled entry", "allowed output"), ratio=0.68, units=5),
    "data_flow_value_chain": dict(axis="left_to_right", organization="data objects move through controlled business nodes and produce a named value result", path=("data source", "controlled processing", "service", "value result"), encoding=("data flow", "control", "value conversion"), required=("data object", "processing nodes", "value result"), ratio=0.65, units=6),
    "role_responsibility_map": dict(axis="actor_to_delivery", organization="actors occupy distinct task zones connected by explicit handoff interfaces", path=("actor", "responsibility", "handoff", "delivery"), encoding=("responsibility", "handoff"), required=("actors", "responsibilities", "delivery interfaces"), ratio=0.60, units=9),
    "problem_cause_resolution": dict(axis="left_to_right", organization="a tension center connects an upstream cause chain to a downstream resolution chain", path=("problem", "cause", "resolution", "controlled result"), encoding=("cause", "mitigation"), required=("problem", "causes", "resolution path"), ratio=0.65, units=6),
}

_DUAL_CENTER_INTENTS = frozenset({"comparison_tension", "dual_engine_synergy"})


def resolve_composition(decision: SemanticIntentDecision) -> CompositionDecision:
    grammar = COMPOSITION_GRAMMARS[decision.primary_intent]
    avoid = [item for item in _COMMON_AVOID if not (
        item == "multiple_visual_centers" and decision.primary_intent in _DUAL_CENTER_INTENTS
    )]
    if decision.primary_intent == "coordinate_peer_set":
        avoid.extend(("forced_sequence", "invented_hierarchy", "privileged_peer_as_result"))
    elif decision.primary_intent == "correspondence_mapping":
        avoid.extend(("forced_comparison", "unbound_mapping_pairs", "invented_causality"))
    elif decision.primary_intent == "closed_loop_operation":
        avoid.extend(("decorative_ring", "unnamed_feedback_arrow"))
    elif decision.primary_intent == "network_ecosystem":
        avoid.extend(("generic_center_circle", "icon_cloud"))
    elif decision.primary_intent == "layered_architecture":
        avoid.extend(("equal_horizontal_bands", "generic_software_boxes"))
    elif decision.primary_intent == "risk_control_boundary":
        avoid.extend(("decorative_glowing_circle", "warning_card_wall"))
    elif decision.primary_intent == "comparison_tension":
        avoid.extend(("symmetrical_poster_copy", "unequal_comparison_weight"))
    elif decision.primary_intent == "dual_engine_synergy":
        avoid.extend(("disconnected_dual_panels", "one_sided_actor_emphasis"))
    return CompositionDecision(
        semantic_intent=decision.primary_intent,
        primary_axis=str(grammar["axis"]),
        spatial_organization=str(grammar["organization"]),
        reading_path=tuple(grammar["path"]),
        relationship_encoding=tuple(grammar["encoding"]),
        required_elements=tuple(grammar["required"]),
        dominant_ratio=float(grammar["ratio"]),
        max_independent_units=int(grammar["units"]),
        avoid=tuple(avoid),
    )


def validate_composition(composition: CompositionDecision) -> tuple[str, ...]:
    issues: list[str] = []
    if len(composition.reading_path) < 2:
        issues.append("COMPOSITION_READING_PATH_MISSING")
    if not composition.required_elements:
        issues.append("COMPOSITION_REQUIRED_ELEMENTS_MISSING")
    if not 0.5 <= composition.dominant_ratio <= 0.75:
        issues.append("COMPOSITION_DOMINANT_RATIO_OUT_OF_RANGE")
    if composition.max_independent_units > 9:
        issues.append("COMPOSITION_TOO_MANY_INDEPENDENT_UNITS")
    return tuple(issues)
