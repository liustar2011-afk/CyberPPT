"""Project audited Stage 02 data into one immutable ImageGen artifact spec."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import warnings
from pathlib import Path
from typing import Any, Mapping

from cyberppt.region_graph import RegionGraphSpec, validate_region_graph
from cyberppt.visual_medium_policy import VisualMediumPolicy, validate_visual_medium_policy


TEXT_DENSE_ITEM_THRESHOLD = 14
TEXT_DENSE_CHAR_THRESHOLD = 240


def is_text_dense(visible_text: tuple[str, ...] | list[str]) -> bool:
    """Return whether a page needs a text-led relationship field."""

    return (
        len(visible_text) >= TEXT_DENSE_ITEM_THRESHOLD
        or sum(len(str(item)) for item in visible_text) >= TEXT_DENSE_CHAR_THRESHOLD
    )


@dataclass(frozen=True)
class DeliverableSpec:
    asset_type: str
    page_role: str
    canvas: tuple[int, int, str]
    title_render_mode: str
    subtitle_render_mode: str
    excluded_chrome: tuple[str, ...]


@dataclass(frozen=True)
class CommunicationGoalSpec:
    page_mission: str
    core_judgment: str


@dataclass(frozen=True)
class EvidenceSpec:
    summary: str
    kind: str
    priority: str
    root_id: str = ""


@dataclass(frozen=True)
class RelationshipSpec:
    subject: str
    relation: str
    objects: tuple[str, ...]
    direction: str = ""
    condition: str = ""
    modality: str = ""
    basis: str = ""
    confidence: str = ""


@dataclass(frozen=True)
class VisualCarrierSpec:
    business_object: str
    semantic_role: str
    use_scene: bool
    scene_type: str
    scene_policy: str = "auto"

    def __post_init__(self) -> None:
        if self.scene_policy not in {"required", "allowed", "forbidden", "auto"}:
            raise ValueError(f"unsupported scene policy: {self.scene_policy!r}")


@dataclass(frozen=True)
class VisualBudgetSpec:
    """Executable ceiling for auxiliary imagery on one page."""

    mode: str = "integrated_scene"
    max_auxiliary_fragments: int = 4
    scope: str = "region"
    region_local_visuals: bool = True

    def __post_init__(self) -> None:
        if self.mode not in {"relationship_field_only", "shared_field", "integrated_scene"}:
            raise ValueError(f"unsupported visual budget mode: {self.mode!r}")
        if self.max_auxiliary_fragments < 0:
            raise ValueError("visual budget cannot be negative")
        if self.scope not in {"page", "region"}:
            raise ValueError(f"unsupported visual budget scope: {self.scope!r}")
        if self.mode == "relationship_field_only" and self.max_auxiliary_fragments != 0:
            raise ValueError("relationship_field_only requires zero auxiliary fragments")
        if self.mode == "shared_field" and (
            self.max_auxiliary_fragments > 1
            or self.scope != "page"
            or self.region_local_visuals
        ):
            raise ValueError("shared_field allows at most one page-level fragment")

    def prompt_lines(self) -> tuple[str, ...]:
        if self.mode == "relationship_field_only":
            return (
                "zero auxiliary images; use a text-led relationship field only; no scenes, fragments or icons.",
            )
        if self.mode == "shared_field":
            return (
                "zero auxiliary images by default; at most one shared page-level anchor; do not create one image/item.",
            )
        return (
            f"Visual budget: at most {self.max_auxiliary_fragments} auxiliary fragments when they materially clarify the selected integrated scene.",
            "Keep supporting imagery subordinate to the page-level scene and do not map each text item to an isolated visual.",
        )


@dataclass(frozen=True)
class ConnectorSpec:
    relationship: str
    direction: str
    label: str
    main_chain: bool


@dataclass(frozen=True)
class CompositionSpec:
    spatial_organization: str
    reading_path: tuple[str, ...]
    primary_focus: str
    secondary_focus: tuple[str, ...]
    relationship_encoding: str
    text_integration_method: str
    spatial_grammar: tuple[str, ...]
    connectors: tuple[ConnectorSpec, ...]
    topology: str


@dataclass(frozen=True)
class ArtDirectionSpec:
    style_id: int | None
    style_name: str
    style_slug: str
    contract: str


@dataclass(frozen=True)
class TypographySpec:
    visible_text: tuple[str, ...]
    allowed_transformations: tuple[str, ...]
    title_render_mode: str
    subtitle_render_mode: str
    body_render_mode: str


@dataclass(frozen=True)
class VisibleTextBindingSpec:
    """Authoritative ownership of one locked body-text item."""

    text_id: str
    text: str
    root_id: str
    order: int
    role: str
    hierarchy_level: int

    def __post_init__(self) -> None:
        if not self.text_id.strip():
            raise ValueError("visible text binding requires text_id")
        if not self.text.strip():
            raise ValueError("visible text binding requires text")
        if not self.root_id.strip():
            raise ValueError(f"visible text binding {self.text_id!r} requires root_id")
        if self.order <= 0:
            raise ValueError("visible text binding order must be positive")
        if self.hierarchy_level <= 0:
            raise ValueError("visible text binding hierarchy_level must be positive")


@dataclass(frozen=True)
class HardConstraintSpec:
    global_constraints: tuple[str, ...]
    page_constraints: tuple[str, ...]


@dataclass(frozen=True)
class SemanticContextSpec:
    text: str = ""
    argument_chain: str = ""
    source_sha256: str = ""
    source_kind: str = ""
    trace_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class PageArtifactSpec:
    page_id: str
    page_number: int
    deliverable: DeliverableSpec
    communication_goal: CommunicationGoalSpec
    visual_thesis: str
    evidence: tuple[EvidenceSpec, ...]
    relationships: tuple[RelationshipSpec, ...]
    visual_carrier: VisualCarrierSpec
    composition: CompositionSpec
    art_direction: ArtDirectionSpec
    typography: TypographySpec
    hard_constraints: HardConstraintSpec
    source_hashes: tuple[tuple[str, str], ...]
    visual_budget: VisualBudgetSpec = VisualBudgetSpec()
    content_root_count: int = 0
    semantic_context: SemanticContextSpec = SemanticContextSpec()
    prompt_mode: str = "semantic_brief"
    visible_text_bindings: tuple[VisibleTextBindingSpec, ...] = ()
    region_graph: RegionGraphSpec | None = None
    visual_medium_policy: VisualMediumPolicy | None = None

    def __post_init__(self) -> None:
        if self.visible_text_bindings:
            binding_text = tuple(binding.text for binding in self.visible_text_bindings)
            if binding_text != self.typography.visible_text:
                raise ValueError(
                    "visible text bindings must preserve typography.visible_text exactly and in order"
                )
            ids = tuple(binding.text_id for binding in self.visible_text_bindings)
            if len(ids) != len(set(ids)):
                raise ValueError("visible text binding text_id values must be unique")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DIRECTED_COMPOSITION_TOPOLOGIES = {
    "directed_flow",
    "lifecycle_loop",
    "layered_architecture",
    "causal_convergence",
    "sequence",
    "dependency_chain",
    "causal_chain",
    "feedback_loop",
    "layered_structure",
    "support_convergence",
}


def _prompt_mode(
    handoff_page: Mapping[str, object],
    visual_page: Mapping[str, object],
    planning_policy: Mapping[str, object],
) -> str:
    """Choose prompt strength without turning page type into a layout class."""

    explicit = str(
        planning_policy.get("prompt_mode")
        or handoff_page.get("prompt_mode")
        or visual_page.get("prompt_mode")
        or ""
    ).strip()
    if explicit:
        if explicit not in {"semantic_brief", "directed_composition"}:
            raise ValueError(f"unsupported Stage 02 prompt mode: {explicit!r}")
        return explicit

    visual_input = handoff_page.get("stage02_visual_input")
    visual_input = visual_input if isinstance(visual_input, Mapping) else {}
    topology = visual_input.get("semantic_topology")
    topology = topology if isinstance(topology, Mapping) else {}
    topology_name = str(
        topology.get("primary_topology") or topology.get("topology") or ""
    ).strip()
    authority = str(
        topology.get("constraint_authority")
        or visual_input.get("constraint_authority")
        or ""
    ).strip()
    relationships = visual_input.get("business_relationships")
    explicit_relationship = any(
        isinstance(item, Mapping)
        and str(item.get("basis") or "").strip() == "explicit"
        and bool(
            str(item.get("direction") or "").strip()
            or str(item.get("condition") or "").strip()
            or str(item.get("relation") or "").strip()
        )
        for item in relationships or []
    )
    if (
        authority == "hard"
        and topology_name in DIRECTED_COMPOSITION_TOPOLOGIES
        and explicit_relationship
    ):
        return "directed_composition"
    return "semantic_brief"


_TOPOLOGY_PHRASES: dict[str, str] = {
    "parallel_set": (
        "several equal-weight parallel items sharing one judgment; a "
        "structured editorial grid is acceptable"
    ),
    "causal_convergence": (
        "multiple evidence lines converging into one judgment rather than "
        "a list of separate points"
    ),
    "layered_architecture": (
        "a layered architecture where a foundation layer supports the "
        "layers above it, forming one continuous dependency chain from "
        "foundation to outcome"
    ),
    "directed_flow": "a directed business flow moving input through processing to result",
    "lifecycle_loop": (
        "a closed-loop cycle whose result feeds back explicitly into an "
        "earlier stage of the same process"
    ),
    "governance_boundary": (
        "a governed boundary that admits, inspects or controls what "
        "crosses it, not a decorative frame"
    ),
    "ecosystem_map": (
        "a bounded relationship field where named roles exchange through one explicit "
        "service or outcome; use a central object only when the source names it"
    ),
    "allocation_flow": "roles or resources branching out from one source into their respective value destinations",
    "conclusion_anchor": "multiple threads converging into one anchored conclusion",
}

_FORBIDDEN_STRUCTURE_PHRASES: dict[str, str] = {
    "equal_peer_cards": "Do not render the nodes as equal-weight peer cards; the declared relationship is not a flat list.",
    "invented_center_hub": "Do not invent a center hub or radial mechanism the declared relationship does not describe.",
    "forced_sequential_edge": "Do not impose a forced sequential order between nodes the source declares as peers.",
    "missing_result_node": "Do not omit the converging result; every contributing line must visibly reach it.",
    "missing_dependency_edge": "Do not break the layered dependency chain; every layer must visibly connect to the next.",
    "missing_feedback_edge": "Do not omit the feedback or return path back into the cycle.",
    "missing_boundary_edge": "Do not omit the boundary or control gate the relationship depends on.",
    "missing_value_destination": "Do not leave any role or resource without a visible destination.",
    "multiple_equal_conclusions": "Do not render more than one equally weighted conclusion; there is exactly one anchor.",
    "no_arrows": "Do not render arrows, arrowheads, chevrons, loop symbols, or directional connector marks; express the relationship through position, spacing, grouping, alignment, and tonal progression only.",
}


def _topology_phrase(value: object, field: str) -> str:
    token = str(value or "").strip()
    if not token:
        raise ValueError(f"artifact spec requires {field}")
    phrase = _TOPOLOGY_PHRASES.get(token)
    if phrase is None:
        raise ValueError(f"artifact spec {field} has an unmapped topology token: {token!r}")
    return phrase


def _forbidden_structure_phrases(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    phrases: list[str] = []
    for token in value:
        key = str(token or "").strip()
        if not key:
            continue
        phrase = _FORBIDDEN_STRUCTURE_PHRASES.get(key)
        if phrase is None:
            raise ValueError(f"artifact spec {field} has an unmapped forbidden-structure token: {key!r}")
        phrases.append(phrase)
    return tuple(dict.fromkeys(phrases))


def _required_text(value: object, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"artifact spec requires {field}")
    return text


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _visual_budget(
    visual_page: Mapping[str, object],
    *,
    topology: str,
    use_scene: bool | None = None,
    scene_policy: str | None = None,
    visible_text: tuple[str, ...] = (),
) -> VisualBudgetSpec:
    raw = visual_page.get("visual_budget")
    raw = raw if isinstance(raw, dict) else {}
    if raw:
        return VisualBudgetSpec(
            mode=str(raw.get("mode") or "").strip(),
            max_auxiliary_fragments=int(raw.get("max_auxiliary_fragments")),
            scope=str(raw.get("scope") or "").strip(),
            region_local_visuals=bool(raw.get("region_local_visuals")),
        )
    resolved = str(scene_policy or "").strip()
    if not resolved:
        resolved = "allowed" if use_scene is True else "forbidden" if use_scene is False else "auto"
    if resolved not in {"required", "allowed", "forbidden", "auto"}:
        raise ValueError(f"unsupported scene policy for visual budget: {resolved!r}")
    if is_text_dense(visible_text) and resolved != "required":
        return VisualBudgetSpec(
            mode="relationship_field_only",
            max_auxiliary_fragments=0,
            scope="page",
            region_local_visuals=False,
        )
    if resolved == "forbidden":
        return VisualBudgetSpec(
            mode="shared_field",
            max_auxiliary_fragments=1,
            scope="page",
            region_local_visuals=False,
        )
    return VisualBudgetSpec()


def _style_metadata(style_lock: Path) -> ArtDirectionSpec:
    from scripts.imagegen_pipeline.deliverable_prompt import style_contract
    from scripts.imagegen_pipeline.style_library import load_style_lock

    payload = load_style_lock(style_lock)
    raw_style = payload.get("style") if isinstance(payload, dict) else None
    style = raw_style if isinstance(raw_style, dict) else {}
    raw_id = style.get("id")
    try:
        style_id = int(raw_id) if raw_id is not None else None
    except (TypeError, ValueError):
        style_id = None
    return ArtDirectionSpec(
        style_id=style_id,
        style_name=str(style.get("name") or "").strip(),
        style_slug=str(style.get("slug") or "").strip(),
        contract=_required_text(style_contract(style_lock), "art direction contract"),
    )


def _canvas(value: object, field: str) -> tuple[int, int, str]:
    if not isinstance(value, dict):
        raise ValueError(f"artifact spec requires {field}")
    try:
        width = int(value.get("width"))
        height = int(value.get("height"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"artifact spec has invalid {field}") from exc
    ratio = str(value.get("ratio") or "").strip()
    if (width, height, ratio) != (2048, 1024, "2:1"):
        raise ValueError(f"artifact spec {field} must be 2048x1024 (2:1)")
    return width, height, ratio


def _body_lock(visual_page: Mapping[str, object]) -> tuple[str, ...]:
    content_lock = visual_page.get("content_lock")
    items = content_lock.get("locked_items") if isinstance(content_lock, dict) else None
    if not isinstance(items, list):
        return ()
    return tuple(
        str(item.get("text") or "").strip()
        for item in items
        if isinstance(item, dict)
        and item.get("type") == "body"
        and str(item.get("text") or "").strip()
    )


def _business_relationships(
    value: object,
    field: str,
) -> tuple[RelationshipSpec, ...]:
    if not isinstance(value, list):
        raise ValueError(f"artifact spec requires {field} to be an array")
    relationships: list[RelationshipSpec] = []
    for index, item in enumerate(value, 1):
        if not isinstance(item, dict):
            raise ValueError(f"artifact spec {field}[{index}] must be an object")
        raw_objects = item.get("objects")
        objects = _strings(raw_objects)
        if not objects:
            raise ValueError(f"artifact spec requires {field}[{index}].objects")
        relationships.append(
            RelationshipSpec(
                subject=_required_text(item.get("subject"), f"{field}[{index}].subject"),
                relation=_required_text(item.get("relation"), f"{field}[{index}].relation"),
                objects=objects,
                direction=str(item.get("direction") or "").strip(),
                condition=str(item.get("condition") or "").strip(),
                modality=str(item.get("modality") or "").strip(),
                basis=str(item.get("basis") or "").strip(),
                confidence=str(item.get("confidence") or "").strip(),
            )
        )
    return tuple(relationships)


def _normalized_relationship_payload(value: object) -> object:
    """Compare the projected relationship contract without treating metadata as drift."""

    if not isinstance(value, list):
        return value
    keys = {
        "subject", "relation", "objects", "direction", "condition", "modality",
        "basis", "confidence", "source_refs", "authority_ref",
    }
    normalized: list[object] = []
    for item in value:
        if not isinstance(item, dict):
            normalized.append(item)
            continue
        record = {key: item[key] for key in keys if key in item}
        if "confidence" in record:
            record["confidence"] = str(record["confidence"])
        normalized.append(record)
    return normalized


def _visible_text_bindings(
    *,
    visible_text: tuple[str, ...],
    content_nodes: object,
) -> tuple[VisibleTextBindingSpec, ...]:
    """Project the authoritative content-integrity tree without fuzzy matching.

    Current Stage 02 output carries text/text_id/root_id/ordinal on each node.
    A narrow compatibility path remains for older audited fixtures that already
    carry a complete, unique text_id/root_id chain but predate the duplicated
    node ``text``/``ordinal`` fields. That projection is positional, emits an
    explicit warning, and never guesses ownership by text similarity.
    """

    if not isinstance(content_nodes, list) or not content_nodes:
        return ()
    nodes = [node for node in content_nodes if isinstance(node, dict)]
    if len(nodes) != len(content_nodes):
        raise ValueError("artifact spec content-integrity nodes must all be objects")

    has_text = [bool(str(node.get("text") or "").strip()) for node in nodes]
    compatibility_projection = not any(has_text)
    if compatibility_projection:
        if len(nodes) != len(visible_text):
            raise ValueError(
                "legacy content-integrity projection requires one node per exact visible-text item"
            )
        ids = [str(node.get("text_id") or "").strip() for node in nodes]
        roots = [str(node.get("root_id") or "").strip() for node in nodes]
        if not all(ids) or len(ids) != len(set(ids)) or not all(roots):
            raise ValueError(
                "legacy content-integrity projection requires complete unique text_id/root_id authority"
            )
        warnings.warn(
            "projecting legacy content-integrity nodes by audited list order; regenerate Stage 02 data to persist node text/ordinal",
            RuntimeWarning,
            stacklevel=2,
        )
        ordered = list(nodes)
    else:
        if not all(has_text):
            raise ValueError("artifact spec content-integrity nodes cannot mix text-bearing and legacy nodes")
        ordered = sorted(nodes, key=lambda node: int(node.get("ordinal") or 0))
        node_text = tuple(str(node.get("text") or "").strip() for node in ordered)
        if node_text != visible_text:
            raise ValueError(
                "artifact spec cannot bind visible text because content-integrity node text/order drifted"
            )

    bindings: list[VisibleTextBindingSpec] = []
    seen_ids: set[str] = set()
    for position, node in enumerate(ordered, start=1):
        text_id = str(node.get("text_id") or "").strip()
        root_id = str(node.get("root_id") or "").strip()
        if not text_id or text_id in seen_ids:
            raise ValueError("artifact spec content-integrity text_id must be unique and non-empty")
        if not root_id:
            raise ValueError(f"artifact spec content-integrity node {text_id!r} has no root_id")
        seen_ids.add(text_id)
        bindings.append(
            VisibleTextBindingSpec(
                text_id=text_id,
                text=visible_text[position - 1],
                root_id=root_id,
                order=int(node.get("ordinal") or position),
                role=str(node.get("content_role") or "detail").strip() or "detail",
                hierarchy_level=int(node.get("source_level") or 1),
            )
        )
    return tuple(bindings)



def build_page_artifact_spec(
    *,
    handoff_page: Mapping[str, object],
    visual_page: Mapping[str, object],
    style_lock: Path,
    script_input_sha256: str,
    visual_source_sha256: str,
    planning_policy: Mapping[str, object] | None = None,
) -> PageArtifactSpec:
    """Build the nine-part projection without introducing a new authority."""

    handoff_id = str(handoff_page.get("page_id") or "").strip().upper()
    visual_id = str(visual_page.get("page_id") or "").strip().upper()
    if handoff_id != visual_id:
        raise ValueError("artifact spec page id does not match Stage 02 handoff")
    page_number = int(handoff_page.get("page_number") or 0)
    if page_number <= 0 or page_number != int(visual_page.get("page_number") or 0):
        raise ValueError("artifact spec page number does not match Stage 02 handoff")

    page_mission = _required_text(handoff_page.get("page_mission"), "page mission")
    if page_mission != _required_text(visual_page.get("page_mission"), "visual page mission"):
        raise ValueError("artifact spec page mission drifted between handoff and visual spec")
    core_judgment = _required_text(handoff_page.get("core_message"), "core judgment")
    if core_judgment != _required_text(visual_page.get("core_judgment"), "visual core judgment"):
        raise ValueError("artifact spec core judgment drifted between handoff and visual spec")

    visual_input = handoff_page.get("stage02_visual_input")
    visual_input = visual_input if isinstance(visual_input, dict) else {}
    handoff_canvas = _canvas(visual_input.get("body_image_canvas"), "handoff canvas")
    geometry = visual_page.get("geometry")
    visual_canvas = _canvas(
        geometry.get("canvas") if isinstance(geometry, dict) else None,
        "visual canvas",
    )
    if handoff_canvas != visual_canvas:
        raise ValueError("artifact spec canvas drifted between handoff and visual spec")

    text_integration = visual_page.get("text_integration")
    text_integration = text_integration if isinstance(text_integration, dict) else {}
    title_mode = _required_text(text_integration.get("title_render_mode"), "title render mode")
    subtitle_mode = _required_text(text_integration.get("subtitle_render_mode"), "subtitle render mode")
    body_mode = _required_text(text_integration.get("body_render_mode"), "body render mode")
    if (title_mode, subtitle_mode, body_mode) != (
        "external_text_layer", "external_text_layer", "in_image",
    ):
        raise ValueError(
            "artifact spec requires external title/subtitle layers and in-image body text"
        )
    if title_mode != str(visual_input.get("title_render_mode") or "").strip():
        raise ValueError("artifact spec title render mode drifted")
    if subtitle_mode != str(visual_input.get("subtitle_render_mode") or "").strip():
        raise ValueError("artifact spec subtitle render mode drifted")

    generation_handoff = visual_page.get("generation_handoff")
    generation_handoff = generation_handoff if isinstance(generation_handoff, dict) else {}
    visible_text = _strings(generation_handoff.get("required_text"))
    if not visible_text or visible_text != _body_lock(visual_page):
        raise ValueError("artifact spec exact text drifted from the audited content lock")
    final_text = visual_page.get("final_text")
    final_text_values = tuple(
        str(item.get("text") or "").strip()
        for item in final_text if isinstance(item, dict)
    ) if isinstance(final_text, list) else ()
    if final_text_values != visible_text:
        raise ValueError("artifact spec final text drifted from required text")

    content_integrity = visual_page.get("content_integrity")
    content_nodes = content_integrity.get("nodes") if isinstance(content_integrity, dict) else None
    root_nodes = content_integrity.get("root_nodes") if isinstance(content_integrity, dict) else None
    content_root_count = len(root_nodes) if isinstance(root_nodes, list) else 0
    visible_text_bindings = _visible_text_bindings(
        visible_text=visible_text,
        content_nodes=content_nodes,
    )
    text_id_to_root = {
        str(node.get("text_id")): str(node.get("root_id") or "")
        for node in content_nodes or [] if isinstance(node, dict)
    }
    structural_decision_for_roots = visual_page.get("structural_decision")
    text_bindings = (
        structural_decision_for_roots.get("text_bindings")
        if isinstance(structural_decision_for_roots, dict) else None
    )
    evidence_id_to_root: dict[str, str] = {}
    for binding in text_bindings or []:
        if not isinstance(binding, dict):
            continue
        evidence_id = str(binding.get("evidence_id") or "")
        text_ids = [str(value) for value in binding.get("text_ids") or []]
        root_ids = {
            text_id_to_root[tid] for tid in text_ids
            if tid in text_id_to_root and text_id_to_root[tid]
        }
        if evidence_id and len(root_ids) == 1:
            evidence_id_to_root[evidence_id] = next(iter(root_ids))

    evidence_items = visual_page.get("evidence_units")
    evidence = tuple(
        EvidenceSpec(
            summary=_required_text(item.get("text"), "evidence summary"),
            kind=str(item.get("kind") or "evidence").strip(),
            priority=str(item.get("priority") or "P0").strip(),
            root_id=evidence_id_to_root.get(str(item.get("id") or ""), ""),
        )
        for item in evidence_items if isinstance(item, dict)
    ) if isinstance(evidence_items, list) else ()
    if not evidence:
        raise ValueError("artifact spec requires evidence")

    semantic_graph = visual_page.get("semantic_graph")
    semantic_graph = semantic_graph if isinstance(semantic_graph, dict) else {}
    raw_region_graph = visual_page.get("region_graph")
    region_graph = (
        validate_region_graph(raw_region_graph)
        if isinstance(raw_region_graph, Mapping)
        else None
    )
    raw_medium_policy = visual_page.get("visual_medium_policy")
    visual_medium_policy = (
        validate_visual_medium_policy(raw_medium_policy)
        if isinstance(raw_medium_policy, Mapping)
        else None
    )
    handoff_relationships = visual_input.get("business_relationships")
    visual_relationships = semantic_graph.get("business_relationships")
    if handoff_relationships == [] and visual_relationships == []:
        relationships = ()
    elif (
        handoff_relationships is None or handoff_relationships == []
    ) and (
        visual_relationships is None or visual_relationships == []
    ):
        relationships = (
            RelationshipSpec(
                subject=_required_text(
                    semantic_graph.get("decision_relationship"),
                    "decision relationship",
                ),
                relation="",
                objects=(),
            ),
        )
    else:
        if _normalized_relationship_payload(handoff_relationships) != _normalized_relationship_payload(visual_relationships):
            raise ValueError(
                "artifact spec business relationship drifted between handoff and visual spec"
            )
        relationships = _business_relationships(
            visual_relationships,
            "business relationships",
        )
    visual_decision = visual_page.get("visual_decision")
    visual_decision = visual_decision if isinstance(visual_decision, dict) else {}
    hierarchy = visual_decision.get("visual_hierarchy")
    hierarchy = hierarchy if isinstance(hierarchy, dict) else {}
    structural = visual_page.get("structural_decision")
    structural = structural if isinstance(structural, dict) else {}
    image_plan = visual_page.get("image_plan")
    image_plan = image_plan if isinstance(image_plan, dict) else {}
    use_scene = image_plan.get("use_scene")
    if not isinstance(use_scene, bool):
        raise ValueError("artifact spec image plan use_scene must be boolean")
    scene_policy = str(image_plan.get("scene_policy") or "").strip()
    if not scene_policy:
        scene_policy = "allowed" if use_scene else "forbidden"
    if scene_policy not in {"required", "allowed", "forbidden", "auto"}:
        raise ValueError(f"artifact spec image plan has invalid scene_policy: {scene_policy!r}")

    connector_items = visual_page.get("connectors")
    connectors = tuple(
        ConnectorSpec(
            relationship=str(item.get("type") or "").strip(),
            direction=str(item.get("direction") or "").strip(),
            label=str(item.get("label") or "").strip(),
            main_chain=bool(item.get("main_chain")),
        )
        for item in connector_items if isinstance(item, dict)
    ) if isinstance(connector_items, list) else ()

    content_lock = visual_page.get("content_lock")
    content_lock = content_lock if isinstance(content_lock, dict) else {}
    forbidden_structure_phrases = _forbidden_structure_phrases(
        semantic_graph.get("forbidden_structures"), "semantic graph forbidden structures"
    )
    page_constraints = tuple(dict.fromkeys((
        *_strings(content_lock.get("forbidden_transformations")),
        *_strings(visual_page.get("avoid")),
        str(generation_handoff.get("title_exclusion_instruction") or "").strip(),
        *forbidden_structure_phrases,
    )))
    page_constraints = tuple(value for value in page_constraints if value)
    policy = planning_policy if isinstance(planning_policy, Mapping) else {}
    if (
        str(policy.get("source_structure_mode") or "").strip() == "locked"
        or str(policy.get("source_content_mode") or "").strip() == "preserve"
    ):
        page_constraints = tuple(dict.fromkeys((
            *page_constraints,
            "Preserve the approved source actors, relationships, conditions, status, and factual strength without reinterpretation.",
        )))

    semantic_text = str(handoff_page.get("full_prose") or "").strip()
    semantic_source_kind = "full_prose"
    if not semantic_text:
        semantic_text = core_judgment
        semantic_source_kind = "core_judgment_compatibility_fallback"
    prompt_mode = _prompt_mode(handoff_page, visual_page, policy)

    return PageArtifactSpec(
        page_id=visual_id,
        page_number=page_number,
        deliverable=DeliverableSpec(
            asset_type="presentation content visual",
            page_role=str(handoff_page.get("argument_role") or visual_page.get("page_role") or "content").strip(),
            canvas=visual_canvas,
            title_render_mode=title_mode,
            subtitle_render_mode=subtitle_mode,
            excluded_chrome=("title", "subtitle", "logo", "page_number", "footer", "template_frame"),
        ),
        communication_goal=CommunicationGoalSpec(page_mission, core_judgment),
        visual_thesis=_required_text(visual_decision.get("visual_thesis"), "visual thesis"),
        evidence=evidence,
        relationships=relationships,
        visual_carrier=VisualCarrierSpec(
            business_object=_required_text(image_plan.get("business_object"), "visual carrier business object"),
            semantic_role=_required_text(image_plan.get("semantic_role"), "visual carrier semantic role"),
            use_scene=use_scene,
            scene_type=_required_text(image_plan.get("scene_type"), "visual carrier scene type"),
            scene_policy=scene_policy,
        ),
        composition=CompositionSpec(
            spatial_organization=_required_text(visual_decision.get("spatial_organization"), "spatial organization"),
            reading_path=_strings(visual_decision.get("reading_path")),
            primary_focus=_required_text(hierarchy.get("primary"), "primary visual focus"),
            secondary_focus=_strings(hierarchy.get("secondary")),
            relationship_encoding=_required_text(visual_decision.get("relationship_encoding"), "relationship encoding"),
            text_integration_method=_required_text(visual_decision.get("text_integration_method"), "text integration method"),
            spatial_grammar=_strings(structural.get("spatial_grammar")),
            connectors=connectors,
            topology=_topology_phrase(semantic_graph.get("topology"), "semantic graph topology"),
        ),
        art_direction=_style_metadata(style_lock),
        typography=TypographySpec(
            visible_text=visible_text,
            allowed_transformations=_strings(content_lock.get("allowed_transformations")),
            title_render_mode=title_mode,
            subtitle_render_mode=subtitle_mode,
            body_render_mode=body_mode,
        ),
        hard_constraints=HardConstraintSpec(
            global_constraints=(
                "Render only the PowerPoint body visual on a 2048x1024 canvas.",
                "Do not render title, subtitle, logo, page number, footer, or template frame.",
                "Do not render instructions, field labels, source references, evidence ids, or text ids.",
                "Do not invent visible business facts, numbers, organizations, actors, or conclusions.",
            ),
            page_constraints=page_constraints,
        ),
        source_hashes=tuple(sorted({
            "script_input": str(script_input_sha256),
            "visual_spec": str(visual_source_sha256),
            "style_lock": hashlib.sha256(style_lock.read_bytes()).hexdigest(),
        }.items())),
        visual_budget=_visual_budget(
            visual_page,
            topology=str(semantic_graph.get("topology") or ""),
            use_scene=use_scene,
            scene_policy=scene_policy,
            visible_text=visible_text,
        ),
        content_root_count=content_root_count,
        semantic_context=SemanticContextSpec(
            text=semantic_text,
            argument_chain=str(handoff_page.get("argument_chain") or "").strip(),
            source_sha256=hashlib.sha256(semantic_text.encode("utf-8")).hexdigest(),
            source_kind=semantic_source_kind,
            trace_refs=(),
        ),
        prompt_mode=prompt_mode,
        visible_text_bindings=visible_text_bindings,
        region_graph=region_graph,
        visual_medium_policy=visual_medium_policy,
    )


def load_project_page_artifact_specs(
    project: Path,
    *,
    style_lock: Path,
) -> dict[int, PageArtifactSpec]:
    """Load the audited Stage 02 authorities and project every content page."""

    from cyberppt.stage02_input import input_page_map, input_path, load_stage02_input

    project = project.expanduser().resolve()
    script_input_path = input_path(project)
    visual_path = project / "visual" / "deck-visual-spec.json"
    handoff = load_stage02_input(project, required=True)
    if handoff is None:  # pragma: no cover - required=True is the contract
        raise FileNotFoundError(f"Stage 02 script input is missing: {script_input_path}")
    if not visual_path.is_file():
        raise FileNotFoundError(f"visual structure spec is missing: {visual_path}")
    try:
        visual_payload = json.loads(visual_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"visual structure spec is not valid JSON: {visual_path}") from exc
    pages = visual_payload.get("pages") if isinstance(visual_payload, dict) else None
    if not isinstance(pages, list):
        raise ValueError("visual structure spec must contain pages")
    visual_map = {
        int(page.get("page_number") or 0): page
        for page in pages
        if isinstance(page, dict) and int(page.get("page_number") or 0) > 0
    }
    handoff_map = input_page_map(handoff)
    content_handoff = {
        page_number: page
        for page_number, page in handoff_map.items()
        if str(page.get("render_role") or "").strip() == "content"
    }
    missing = sorted(set(content_handoff) - set(visual_map))
    if missing:
        raise ValueError(
            "visual structure spec is missing Stage 02 pages: "
            + ", ".join(f"P{number:02d}" for number in missing)
        )
    script_input_sha = hashlib.sha256(script_input_path.read_bytes()).hexdigest()
    visual_sha = hashlib.sha256(visual_path.read_bytes()).hexdigest()
    return {
        page_number: build_page_artifact_spec(
            handoff_page=handoff_page,
            visual_page=visual_map[page_number],
            style_lock=style_lock,
            script_input_sha256=script_input_sha,
            visual_source_sha256=visual_sha,
            planning_policy=None,
        )
        for page_number, handoff_page in content_handoff.items()
    }


__all__ = [
    "ArtDirectionSpec",
    "CommunicationGoalSpec",
    "CompositionSpec",
    "ConnectorSpec",
    "DeliverableSpec",
    "EvidenceSpec",
    "HardConstraintSpec",
    "PageArtifactSpec",
    "RegionGraphSpec",
    "TypographySpec",
    "VisibleTextBindingSpec",
    "VisualCarrierSpec",
    "VisualMediumPolicy",
    "VisualBudgetSpec",
    "is_text_dense",
    "build_page_artifact_spec",
    "load_project_page_artifact_specs",
]
