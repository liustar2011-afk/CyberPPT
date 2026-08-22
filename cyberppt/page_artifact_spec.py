"""Project audited Stage 02 data into one immutable ImageGen artifact spec."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


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
                "Visual budget: zero auxiliary images or scene fragments.",
                "Use text hierarchy, spacing, alignment and one shared relationship field; do not create region-local visuals.",
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
class HardConstraintSpec:
    global_constraints: tuple[str, ...]
    page_constraints: tuple[str, ...]


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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# semantic_graph.topology and forbidden_structures are snake_case backend
# enum tokens (see cyberppt/commands/visual_structure_stage.py's
# ALLOWED_TOPOLOGY and _FORBIDDEN_STRUCTURES_BY_TOPOLOGY). final_prompt_contract
# rejects raw snake_case tokens in the final prompt text, so every value must
# be mapped to a plain-English phrase here before it can reach the IR --
# never interpolated as the raw token.
#
# Phrasing follows docs/superpowers/plans/2026-08-19-stage2-gpt-image-2-
# prompt-sensitivity-optimization.md: GPT Image 2 responds far more to
# concrete relationship verbs ("converge into", "branch into", "one
# continuous flow", "hub-and-spoke", "closed-loop cycle", "foundation layer
# supporting upper layers") than to static noun phrases describing the same
# relationship. Each phrase below keeps its original business meaning and
# only strengthens the verb/construction driving the composition.
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
    use_scene: bool,
) -> VisualBudgetSpec:
    raw = visual_page.get("visual_budget")
    raw = raw if isinstance(raw, dict) else {}
    if raw:
        budget = VisualBudgetSpec(
            mode=str(raw.get("mode") or "").strip(),
            max_auxiliary_fragments=int(raw.get("max_auxiliary_fragments")),
            scope=str(raw.get("scope") or "").strip(),
            region_local_visuals=bool(raw.get("region_local_visuals")),
        )
        if topology == "parallel_set" and budget.mode == "integrated_scene":
            raise ValueError("parallel_set cannot use an integrated-scene visual budget")
        return budget
    if topology == "parallel_set" or not use_scene:
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
                subject=_required_text(
                    item.get("subject"), f"{field}[{index}].subject"
                ),
                relation=_required_text(
                    item.get("relation"), f"{field}[{index}].relation"
                ),
                objects=objects,
                direction=str(item.get("direction") or "").strip(),
                condition=str(item.get("condition") or "").strip(),
                modality=str(item.get("modality") or "").strip(),
                basis=str(item.get("basis") or "").strip(),
                confidence=str(item.get("confidence") or "").strip(),
            )
        )
    return tuple(relationships)


def build_page_artifact_spec(
    *,
    handoff_page: Mapping[str, object],
    visual_page: Mapping[str, object],
    style_lock: Path,
    handoff_sha256: str,
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
        "external_text_layer",
        "external_text_layer",
        "in_image",
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

    evidence_items = visual_page.get("evidence_units")
    evidence = tuple(
        EvidenceSpec(
            summary=_required_text(item.get("text"), "evidence summary"),
            kind=str(item.get("kind") or "evidence").strip(),
            priority=str(item.get("priority") or "P0").strip(),
        )
        for item in evidence_items if isinstance(item, dict)
    ) if isinstance(evidence_items, list) else ()
    if not evidence:
        raise ValueError("artifact spec requires evidence")

    semantic_graph = visual_page.get("semantic_graph")
    semantic_graph = semantic_graph if isinstance(semantic_graph, dict) else {}
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
        if handoff_relationships != visual_relationships:
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
            "handoff": str(handoff_sha256),
            "visual_spec": str(visual_source_sha256),
            "style_lock": hashlib.sha256(style_lock.read_bytes()).hexdigest(),
        }.items())),
        visual_budget=_visual_budget(
            visual_page,
            topology=str(semantic_graph.get("topology") or ""),
            use_scene=use_scene,
        ),
    )


def load_project_page_artifact_specs(
    project: Path,
    *,
    style_lock: Path,
) -> dict[int, PageArtifactSpec]:
    """Load the audited Stage 02 authorities and project every content page."""

    from cyberppt.stage02_handoff import HANDOFF_JSON, handoff_page_map, load_stage02_handoff

    project = project.expanduser().resolve()
    handoff_path = project / HANDOFF_JSON
    visual_path = project / "visual" / "deck-visual-spec.json"
    handoff = load_stage02_handoff(project, required=True)
    if handoff is None:  # pragma: no cover - required=True is the contract
        raise FileNotFoundError(f"Stage 02 handoff is missing: {handoff_path}")
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
    handoff_map = handoff_page_map(handoff)
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
    handoff_sha = hashlib.sha256(handoff_path.read_bytes()).hexdigest()
    visual_sha = hashlib.sha256(visual_path.read_bytes()).hexdigest()
    return {
        page_number: build_page_artifact_spec(
            handoff_page=handoff_page,
            visual_page=visual_map[page_number],
            style_lock=style_lock,
            handoff_sha256=handoff_sha,
            visual_source_sha256=visual_sha,
            planning_policy=handoff.get("planning_policy")
            if isinstance(handoff.get("planning_policy"), dict)
            else None,
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
    "TypographySpec",
    "VisualCarrierSpec",
    "VisualBudgetSpec",
    "build_page_artifact_spec",
    "load_project_page_artifact_specs",
]
