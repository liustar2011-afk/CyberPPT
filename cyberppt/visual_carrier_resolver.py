"""Select and score business-bearing visual carriers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from cyberppt.composition_resolver import CompositionDecision
from cyberppt.semantic_intent import SemanticIntentDecision


@dataclass(frozen=True)
class CarrierCandidate:
    carrier: str
    score: int
    score_breakdown: dict[str, int]
    strength: str
    risk: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class VisualCarrierDecision:
    selected: str
    candidates: tuple[CarrierCandidate, ...]
    source: str = "registry_scored"

    def to_dict(self) -> dict[str, object]:
        return {
            "selected": self.selected,
            "source": self.source,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


_CARRIERS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "single_judgment_anchor": (("single_result_object", "single memorable center", "poster-like oversimplification"), ("decision_landscape", "evidence remains subordinate", "weak anchor object"), ("industry_scene_anchor", "concrete business meaning", "scene may compete with judgment")),
    "multi_semantic_foundation": (("shared_capability_base", "different foundations share one carrier", "foundation labels may become cards"), ("integrated_workbench", "objects participate in one scene", "scene complexity"), ("foundation_pillars", "support relation is explicit", "generic architecture metaphor")),
    "evidence_to_judgment": (("evidence_convergence_field", "evidence visibly leads to judgment", "list-like evidence"), ("decision_landscape", "strong hierarchy", "abstract canvas"), ("proof_path", "clear reading order", "over-linearization")),
    "scene_embedded_flow": (("continuous_industry_scene", "flow occurs inside the scene", "illustration overload"), ("operational_workbench_path", "actions attach to objects", "dashboard drift"), ("process_atlas", "stable directional path", "scene may weaken")),
    "transformation_pipeline": (("weighted_transformation_channel", "input and output weights remain visible", "equal box pipeline"), ("process_atlas", "clear directional main chain", "generic roadmap"), ("folded_transformation_band", "stages remain connected", "decorative ribbon")),
    "convergence_to_capability": (("capability_engine", "multiple sources form one capability", "generic center circle"), ("service_workbench", "convergence has a concrete object", "dashboard styling"), ("convergence_gateway", "entry and formation are clear", "technical gateway metaphor")),
    "capability_to_outcomes": (("capability_to_scene_fanout", "outcomes remain differentiated", "equal result cards"), ("service_expansion_landscape", "results attach to real contexts", "too many scenes"), ("outcome_branch_path", "direction remains clear", "tree diagram rigidity")),
    "layered_architecture": (("spatial_system_cutaway", "dependencies have depth", "software stack appearance"), ("non_equal_platform_stack", "layer weight is visible", "equal horizontal bands"), ("foundation_service_house", "support relation is intuitive", "over-literal house metaphor")),
    "dual_engine_synergy": (("shared_interface_bridge", "two actors meet through one interface", "symmetrical split"), ("dual_engine_shared_outcome", "shared result stays central", "mechanical gear metaphor"), ("non_symmetric_collaboration_scene", "contributions can differ", "scene imbalance")),
    "closed_loop_operation": (("operational_feedback_loop", "feedback target and return are explicit", "decorative ring"), ("circular_control_workspace", "loop attaches to business objects", "dashboard drift"), ("scene_based_return_path", "feedback occurs in context", "return path may be subtle")),
    "comparison_tension": (("shared_axis_comparison", "differences use one basis", "two-column copying"), ("before_after_divide", "transition is visible", "oversimplified binary"), ("decision_watershed", "tension forms one center", "metaphor may dominate")),
    "phased_roadmap": (("uneven_milestone_path", "phase rhythm is visible", "uniform timeline"), ("near_to_far_buildout", "time becomes spatial depth", "perspective crowding"), ("terrain_roadmap", "milestones attach to progress", "decorative landscape")),
    "network_ecosystem": (("governed_exchange_network", "flows and boundary remain explicit", "spider web"), ("primary_actor_ecosystem", "node hierarchy is clear", "generic hub-spoke"), ("service_market_network", "exchange objects are concrete", "too many nodes")),
    "policy_to_action": (("policy_task_cascade", "constraint becomes action", "policy text stacking"), ("governance_to_execution_path", "mechanism remains visible", "generic process"), ("mandate_translation_system", "translation is the central act", "abstract system")),
    "risk_control_boundary": (("trusted_processing_boundary", "inside, gate, and output are explicit", "decorative enclosure"), ("controlled_gateway", "admission mechanism is central", "technical tunnel"), ("segmented_trust_space", "multiple control zones remain visible", "security diagram density")),
    "data_flow_value_chain": (("controlled_data_value_path", "data and value share one chain", "technical pipeline"), ("business_embedded_data_flow", "data stays tied to business actions", "scene complexity"), ("data_service_value_system", "service conversion is explicit", "platform architecture drift")),
    "role_responsibility_map": (("actor_task_handoff_map", "responsibility and delivery interface align", "organization chart"), ("responsibility_swimlane", "handoffs are explicit", "equal lane rigidity"), ("collaborative_delivery_workspace", "roles act on shared objects", "scene clutter")),
    "problem_cause_resolution": (("cause_tension_resolution_path", "cause and solution remain connected", "three text boxes"), ("diagnostic_field", "multiple causes converge on the real problem", "fishbone cliché"), ("problem_to_controlled_outcome", "resolution direction is strong", "solution may dominate evidence")),
}


_WEIGHTS = {
    "mission_fit": 25,
    "relation_fidelity": 20,
    "single_center": 15,
    "reading_path": 15,
    "text_integration": 10,
    "imagegen_stability": 10,
    "deck_rhythm": 5,
}


def _score_candidate(rank: int, repeated: bool) -> dict[str, int]:
    penalties = (0, 5, 9)
    penalty = penalties[min(rank, len(penalties) - 1)]
    breakdown = dict(_WEIGHTS)
    breakdown["mission_fit"] -= penalty // 2
    breakdown["relation_fidelity"] -= penalty - penalty // 2
    if repeated:
        breakdown["deck_rhythm"] = 0
    return breakdown


def select_visual_carrier(
    intent: SemanticIntentDecision,
    composition: CompositionDecision,
    prior_carriers: Sequence[str] = (),
) -> VisualCarrierDecision:
    candidates: list[CarrierCandidate] = []
    recent = set(prior_carriers[-2:])
    for rank, (carrier, strength, risk) in enumerate(_CARRIERS[intent.primary_intent]):
        breakdown = _score_candidate(rank, carrier in recent)
        candidates.append(
            CarrierCandidate(carrier, sum(breakdown.values()), breakdown, strength, risk)
        )
    candidates.sort(key=lambda item: (-item.score, item.carrier))
    return VisualCarrierDecision(candidates[0].carrier, tuple(candidates))


def validate_visual_carrier(decision: VisualCarrierDecision) -> tuple[str, ...]:
    issues: list[str] = []
    if len(decision.candidates) < 3:
        issues.append("VISUAL_CARRIER_FEWER_THAN_THREE_CANDIDATES")
    if not decision.selected:
        issues.append("VISUAL_CARRIER_NOT_SELECTED")
    selected = next((item for item in decision.candidates if item.carrier == decision.selected), None)
    if selected is None:
        issues.append("VISUAL_CARRIER_SELECTION_NOT_IN_CANDIDATES")
    elif selected.score < 80:
        issues.append("VISUAL_CARRIER_SCORE_BELOW_REVIEW_THRESHOLD")
    return tuple(issues)
