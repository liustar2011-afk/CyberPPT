"""Serialize audited page artifact specs into the GPT Image prompt contract."""

from __future__ import annotations

import re
from pathlib import Path

from cyberppt.page_artifact_spec import (
    CompositionSpec,
    EvidenceSpec,
    PageArtifactSpec,
    RelationshipSpec,
    VisualCarrierSpec,
    VisualBudgetSpec,
)
from scripts.imagegen_pipeline.final_prompt_ir import (
    CompositionIR,
    FinalPromptIR,
    MicroVisualFreedomIR,
    PromptContractError,
    RegionGraphIR,
    RegionIR,
    RegionRelationIR,
    RuntimeLockIR,
    SemanticGroupIR,
    TextBindingIR,
    VisualMediumPolicyIR,
)
from scripts.imagegen_pipeline.final_prompt_contract import backend_identifier_leaks
from scripts.imagegen_pipeline.runtime_style_contract import (
    TERMINAL_EXECUTION_HEADING,
    enforce_terminal_execution_lock,
    internal_style_token_leaks,
    load_runtime_style_contract,
)


SECTION_HEADINGS = (
    "[1. Deliverable / 成品规格]",
    "[2. Communication goal / 页面使命｜不上屏]",
    "[3. Visual thesis / 核心视觉论点｜不上屏]",
    "[4. Evidence & relationships / 证据与关系｜不上屏]",
    "[5. Visual carrier / 视觉载体｜不上屏]",
    "[6. Composition / 空间组织｜不上屏]",
    "[7. Art direction / 视觉语言｜不上屏]",
    "[8. Typography & text reference / 文字表达参考]",
    "[9. Hard constraints / 硬约束]",
)

_VISUAL_ENUM_PHRASES = {
    "support_convergence_3_6": "multiple evidence lines converging on one judgment",
    "support_convergence": "multiple evidence lines converging on one judgment",
    "directed_dependency_2_6": "a directed dependency relationship",
    "directed_dependency": "a directed dependency relationship",
    "operation_loop": "a closed operational feedback loop",
    "directed_flow": "a directed flow",
    "flow_3_5": "a directed flow",
    "allocation_flow": "an allocation relationship",
    "mapping_2_6": "an allocation relationship",
    "causal_chain": "a causal chain",
    "coordinate_peer_set": "a parallel peer set",
    "parallel_direction_field": "a parallel directional field",
    "framework_peer_set": "a parallel framework set",
    "shared_evidence_peer_set": "a shared evidence peer set",
}
_VISUAL_ENUM_RE = re.compile(
    "|".join(re.escape(token) for token in sorted(_VISUAL_ENUM_PHRASES, key=len, reverse=True))
)


def _prompt_safe_visual_text(value: str) -> str:
    return _VISUAL_ENUM_RE.sub(
        lambda match: _VISUAL_ENUM_PHRASES[match.group(0)],
        str(value),
    )


def _bullets(values: tuple[str, ...]) -> str:
    return "\n".join(f"- {value}" for value in values if value)


def _relationship_line(relationship: RelationshipSpec) -> str:
    if not relationship.relation or not relationship.objects:
        return relationship.subject
    qualifiers = tuple(
        f"{name}={value}"
        for name, value in (
            ("direction", relationship.direction),
            ("condition", relationship.condition),
            ("modality", relationship.modality),
            ("basis", relationship.basis),
            ("confidence", relationship.confidence),
        )
        if value
    )
    line = f"{relationship.subject} --{relationship.relation}--> {'; '.join(relationship.objects)}"
    if qualifiers:
        line += " | " + " | ".join(qualifiers)
    return line


def render_artifact_prompt(spec: PageArtifactSpec, *, style_lock: Path | None = None) -> str:
    """Render the compatibility nine-part artifact prompt."""

    deliverable = spec.deliverable
    communication = spec.communication_goal
    carrier = spec.visual_carrier
    composition = spec.composition
    typography = spec.typography
    scene_policy = (
        "Use the selected integrated scene."
        if carrier.use_scene
        else "Use the selected non-scene business relationship field."
    )
    connectors = tuple(
        " / ".join(
            value
            for value in (
                connector.relationship,
                connector.direction,
                connector.label,
                "main chain" if connector.main_chain else "secondary relation",
            )
            if value
        )
        for connector in composition.connectors
    )
    evidence_lines = tuple(f"{item.priority} {item.kind}: {item.summary}" for item in spec.evidence)
    relationship_lines = tuple(_relationship_line(relationship) for relationship in spec.relationships)
    visible_lines = tuple(f'Reference text: "{text}"' for text in typography.visible_text)

    style_contract = spec.art_direction.contract
    runtime = None
    if spec.art_direction.style_id == 9:
        if style_lock is not None:
            try:
                runtime = load_runtime_style_contract(style_lock)
                style_contract = runtime.contract
            except (OSError, ValueError, TypeError):
                pass

    sections = (
        "\n".join((
            SECTION_HEADINGS[0],
            f"Create one finished {deliverable.asset_type} for a PowerPoint {deliverable.page_role} page.",
            f"Canvas: {deliverable.canvas[0]}x{deliverable.canvas[1]} ({deliverable.canvas[2]}).",
            "The asset is the body visual only; PowerPoint supplies all excluded chrome.",
        )),
        "\n".join((
            SECTION_HEADINGS[1],
            f"Page mission: {communication.page_mission}",
            f"Core judgment: {communication.core_judgment}",
            "Use this section only to understand the communication outcome; do not render its labels or prose.",
        )),
        "\n".join((
            SECTION_HEADINGS[2],
            spec.visual_thesis,
            "Make this relationship immediately legible from the visual asset; do not render this instruction as copy.",
        )),
        "\n".join((
            SECTION_HEADINGS[3],
            "Evidence:",
            _bullets(evidence_lines),
            "Authoritative business relationships:",
            _bullets(relationship_lines),
            "These facts guide the visual logic; section 8 provides copy reference for free model expression.",
        )),
        "\n".join((
            SECTION_HEADINGS[4],
            f"Selected carrier: {carrier.business_object}",
            f"Semantic role: {carrier.semantic_role}",
            f"Scene policy: {scene_policy} {carrier.scene_type}",
            "Do not substitute a generic dashboard, icon collection, card wall, or unrelated decorative scene.",
        )),
        "\n".join((
            SECTION_HEADINGS[5],
            f"Spatial organization: {composition.spatial_organization}",
            f"Reading path: {' -> '.join(composition.reading_path)}",
            f"Primary focus: {composition.primary_focus}",
            f"Secondary focus: {'; '.join(composition.secondary_focus) or 'none'}",
            f"Relationship encoding: {composition.relationship_encoding}",
            f"Text integration: {composition.text_integration_method}",
            f"Spatial grammar: {', '.join(composition.spatial_grammar)}",
            *(tuple(("Connectors:", _bullets(connectors))) if connectors else ()),
        )),
        "\n".join((SECTION_HEADINGS[6], style_contract)),
        "\n".join((
            SECTION_HEADINGS[7],
            "Use the following on-screen copy as a content reference. Rewrite, reorder, group, shorten or expand it as needed for a clear visual expression:",
            _bullets(visible_lines),
            "Allowed transformations: free expression within the page's business meaning and selected visual style.",
            "Title and subtitle are external PowerPoint text layers and must not appear in this body image.",
        )),
        "\n".join((
            SECTION_HEADINGS[8],
            _bullets(spec.hard_constraints.global_constraints),
            _bullets(spec.hard_constraints.page_constraints),
        )),
    )
    prompt = "\n\n".join(section for section in sections if section.strip()).rstrip() + "\n"
    if runtime is not None:
        prompt = enforce_terminal_execution_lock(prompt, runtime)
    assert_artifact_prompt_contract(
        prompt,
        expected_visible_text=typography.visible_text,
        style_id=spec.art_direction.style_id,
    )
    return prompt


def assert_artifact_prompt_contract(
    prompt: str,
    *,
    expected_visible_text: tuple[str, ...] = (),
    style_id: int | None = None,
) -> None:
    positions: list[int] = []
    for heading in SECTION_HEADINGS:
        if prompt.count(heading) != 1:
            raise ValueError(f"artifact prompt section is missing or duplicated: {heading}")
        positions.append(prompt.index(heading))
    if positions != sorted(positions):
        raise ValueError("artifact prompt sections are out of contract order")
    for index, heading in enumerate(SECTION_HEADINGS):
        content_start = positions[index] + len(heading)
        content_end = positions[index + 1] if index + 1 < len(positions) else len(prompt)
        if not prompt[content_start:content_end].strip():
            raise ValueError(f"artifact prompt section has no content: {heading}")
    if backend_identifier_leaks(prompt, approved_visible_text=expected_visible_text):
        raise ValueError("artifact prompt contains a backend identifier")
    unapproved_style = [
        token for token in internal_style_token_leaks(prompt)
        if token.casefold() not in "\n".join(expected_visible_text).casefold()
    ]
    if unapproved_style:
        raise ValueError(f"artifact prompt contains an internal style routing token: {unapproved_style[0]!r}")
    legacy_headers = (
        "【风格09最终执行锁｜最高优先级】",
        "【风格10最终执行锁｜最高优先级】",
    )
    if any(header in prompt for header in legacy_headers):
        raise ValueError("artifact prompt contains a numbered legacy terminal style heading")
    if style_id == 9 and TERMINAL_EXECUTION_HEADING in prompt:
        terminal = prompt.split(TERMINAL_EXECUTION_HEADING, 1)[1].strip()
        if prompt.count(TERMINAL_EXECUTION_HEADING) != 1 or not terminal or not prompt.rstrip().endswith(terminal):
            raise ValueError("terminal execution block must be at the absolute end")
    elif TERMINAL_EXECUTION_HEADING in prompt:
        raise ValueError("non-live artifact prompt contains a live terminal execution lock")


def _avoid_judgment_repeat(text: str, page_judgment: str) -> str:
    if page_judgment and page_judgment in text:
        return text.replace(page_judgment, "结果节点（页面判断）")
    return text


def _semantic_groups(
    evidence: tuple[EvidenceSpec, ...],
    page_judgment: str,
    *,
    required_roots: tuple[tuple[str, str], ...] = (),
) -> tuple[SemanticGroupIR, ...]:
    """Group evidence by authoritative content root; preserve empty text roots."""

    order: list[str] = []
    buckets: dict[str, list[str]] = {}
    kind_by_key: dict[str, str] = {}
    for item in evidence:
        kind = item.kind.strip() or "evidence"
        key = item.root_id.strip() or kind
        if key not in buckets:
            buckets[key] = []
            order.append(key)
            kind_by_key[key] = kind
        buckets[key].append(_avoid_judgment_repeat(item.summary, page_judgment))
    for root_id, role in required_roots:
        if root_id not in buckets:
            buckets[root_id] = [
                "Keep the on-screen content reference assigned to this semantic group coherent."
            ]
            order.append(root_id)
            kind_by_key[root_id] = role or "content"
    primary_key = next(
        (key for key in order if kind_by_key[key] == "result"),
        order[0] if order else "",
    )
    return tuple(
        SemanticGroupIR(
            id=key,
            role=kind_by_key[key],
            summary="; ".join(buckets[key]),
            emphasis="primary" if key == primary_key else "secondary",
        )
        for key in order
    )


_ANTI_GENERIC_SCENE_CONSTRAINT = (
    "Do not substitute a generic dashboard, icon collection, card wall, or unrelated decorative scene."
)


def _visual_responsibility(
    composition: CompositionSpec,
    carrier: VisualCarrierSpec,
    visual_budget: VisualBudgetSpec,
) -> tuple[str, ...]:
    scene_policy = (
        "Use the selected integrated scene." if carrier.use_scene
        else "Use the selected non-scene business relationship field."
    )
    lines: list[str] = [
        f"Visual carrier: {carrier.business_object} ({carrier.semantic_role})",
        f"{scene_policy} Scene type: {carrier.scene_type}.",
        _ANTI_GENERIC_SCENE_CONSTRAINT,
        f"Dominant relationship shape: {composition.topology}.",
        f"Primary focus carries: {composition.primary_focus}",
        *visual_budget.prompt_lines(),
    ]
    if composition.secondary_focus:
        lines.append(f"Secondary focus supports: {'; '.join(composition.secondary_focus)}")
    if composition.text_integration_method:
        lines.append(composition.text_integration_method)
    if composition.spatial_grammar:
        lines.append(f"Spatial grammar: {', '.join(composition.spatial_grammar)}")
    for connector in composition.connectors:
        if connector.label:
            lines.append(connector.label)
    return tuple(dict.fromkeys(lines))


def _live_style_visual_responsibility(
    composition: CompositionSpec,
    carrier: VisualCarrierSpec,
) -> tuple[str, ...]:
    """Page-specific context for live runtime styles without numbered wording."""

    lines: list[str] = [
        f"Visual carrier: {carrier.business_object} ({carrier.semantic_role})",
        f"Dominant relationship shape: {composition.topology}.",
        f"Primary focus carries: {composition.primary_focus}",
    ]
    if composition.secondary_focus:
        lines.append(f"Secondary focus supports: {'; '.join(composition.secondary_focus)}")
    if composition.text_integration_method:
        lines.append(composition.text_integration_method)
    if composition.spatial_grammar:
        lines.append(f"Spatial grammar: {', '.join(composition.spatial_grammar)}")
    for connector in composition.connectors:
        if connector.label:
            lines.append(connector.label)
    lines.append(
        "Choose the page-specific amount of photography, structural fields and restrained "
        "decorative detail from the runtime visual rules and this page's semantic content; "
        "avoid a result made only of plain equal-weight text panels."
    )
    return tuple(dict.fromkeys(lines))


def _style09_visual_responsibility(
    composition: CompositionSpec,
    carrier: VisualCarrierSpec,
) -> tuple[str, ...]:
    """Compatibility wrapper for tests/callers using the previous private name."""

    return _live_style_visual_responsibility(composition, carrier)


def _deliverable_sentence(spec: PageArtifactSpec) -> str:
    deliverable = spec.deliverable
    return " ".join((
        f"Create one finished {deliverable.asset_type} for a PowerPoint {deliverable.page_role} page.",
        f"Canvas: {deliverable.canvas[0]}x{deliverable.canvas[1]} ({deliverable.canvas[2]}).",
        "The asset is the body visual only; PowerPoint supplies all excluded chrome.",
    ))


def _bracketed_header_constraints(visible_text: tuple[str, ...]) -> tuple[str, ...]:
    headers = tuple(
        text.strip()
        for text in visible_text
        if text.strip().startswith("【") and text.strip().endswith("】")
    )
    headers = tuple(dict.fromkeys(headers))
    if not headers:
        return ()
    return (
        "All bracketed headings are one level-1 family: use the same compact flat rectangular "
        "title band, left alignment, height, padding, type weight and container-edge placement; "
        "no diagonal cuts, badges, capsules, raised plaques or 3D title treatment.",
        "Named child groups use one quieter level-2 style: aligned semibold text or a thin "
        "divider, with no decorative title plaques.",
        *(
            f'Render "{header}" exactly once in its group container, readable and above its group detail; do not omit it or reduce it to decorative microtext.'
            for header in headers
        ),
    )


def _three_level_group_heading_constraints(spec: PageArtifactSpec) -> tuple[str, ...]:
    """Preserve a visible total heading, named peer cards, and their details."""

    bindings = spec.visible_text_bindings
    if not bindings:
        return ()
    if len({binding.root_id for binding in bindings}) != 1:
        return ()
    levels = tuple(binding.hierarchy_level for binding in bindings)
    if levels.count(1) != 1 or not 3 <= levels.count(2) <= 4 or 3 not in levels:
        return ()
    total = next(binding.text for binding in bindings if binding.hierarchy_level == 1)
    groups: list[tuple[str, list[str]]] = []
    active_group: list[str] | None = None
    for binding in bindings:
        if binding.hierarchy_level == 2:
            active_group = [binding.text]
            groups.append((binding.text, active_group))
        elif binding.hierarchy_level == 3 and active_group is not None:
            active_group.append(binding.text)
    if len(groups) != levels.count(2) or any(len(group) < 2 for _, group in groups):
        return ()
    named_groups = " | ".join(
        f'group heading "{heading}" owns only: ' + "; ".join(f'"{detail}"' for detail in details[1:])
        for heading, details in groups
    )
    return (
        "The locked text contains a visible level-1 total heading, three or four named level-2 card/group "
        "headings, and level-3 judgment or evidence detail. Render the level-1 heading once in the upper entry "
        "region as the first visible statement before every group. Its upper placement is semantic, not a fixed "
        "banner template: vary its alignment, width and integration with the page-specific visual anchor. Never "
        "place it inside a diagram, hub, callout or peer card. "
        "Render every level-2 heading above its own detail, using visibly distinct type scale, weight and spacing.",
        f'Use "{total}" only as the level-1 total heading. Exact level-2 ownership map: {named_groups}. '
        "Never repeat or summarize the level-1 heading inside the visual field. Never promote a level-3 detail "
        "into a card/group heading, and never move a level-3 detail to another named group.",
    )


def _required_binding_roots(spec: PageArtifactSpec) -> tuple[tuple[str, str], ...]:
    roots: list[tuple[str, str]] = []
    seen: set[str] = set()
    for binding in spec.visible_text_bindings:
        if binding.root_id in seen:
            continue
        seen.add(binding.root_id)
        roots.append((binding.root_id, binding.role))
    return tuple(roots)


def _text_binding_ir(spec: PageArtifactSpec) -> tuple[TextBindingIR, ...]:
    if not spec.visible_text_bindings:
        return ()
    order: list[str] = []
    buckets: dict[str, list[object]] = {}
    for binding in spec.visible_text_bindings:
        if binding.root_id not in buckets:
            buckets[binding.root_id] = []
            order.append(binding.root_id)
        buckets[binding.root_id].append(binding)
    result = tuple(
        TextBindingIR(
            group_id=root_id,
            role=str(buckets[root_id][0].role),
            hierarchy_level=min(int(item.hierarchy_level) for item in buckets[root_id]),
            exact_text=tuple(str(item.text) for item in buckets[root_id]),
            text_ids=tuple(str(item.text_id) for item in buckets[root_id]),
            hierarchy_levels=tuple(int(item.hierarchy_level) for item in buckets[root_id]),
        )
        for root_id in order
    )
    flattened = tuple(text for binding in result for text in binding.exact_text)
    if flattened != spec.typography.visible_text:
        raise PromptContractError(
            "visible text root grouping is not contiguous in authoritative order; cannot render a deterministic binding"
        )
    return result


def _visual_medium_policy_ir(spec: PageArtifactSpec) -> VisualMediumPolicyIR | None:
    policy = spec.visual_medium_policy
    if policy is None:
        return None
    return VisualMediumPolicyIR(
        preferred=policy.preferred,
        allowed=policy.allowed,
        scene_policy=policy.scene_policy,
        rationale=policy.rationale,
    )


def _micro_visual_freedom_ir(spec: PageArtifactSpec) -> MicroVisualFreedomIR | None:
    if spec.region_graph is None and spec.visual_medium_policy is None:
        return None
    return MicroVisualFreedomIR(
        allowed=(
            "Choose the exact business-object depiction inside each macro region.",
            "Adjust region-internal micro-positioning, local hierarchy and local reading implementation.",
            "Choose lighting, material, texture, depth and subordinate supporting detail within the selected visual language.",
            "Use subordinate supporting fragments only within the audited visual budget and allowed visual media.",
            "Add local background or decorative detail only when it does not alter semantic roles, text ownership or reading relationships.",
        ),
        forbidden=(
            "Do not merge or split macro regions.",
            "Do not change macro region roles, anchors, relative emphasis or semantic order in a way that changes meaning.",
            "Place and organize the on-screen text reference freely within the business meaning of each macro region.",
            "Do not change the focus policy or promote a peer item into a result or judgment.",
            "Do not change relationship type or direction, or invent stronger causality, hierarchy or sequence than the source supports.",
            "Do not leave the allowed visual media or violate the scene policy.",
            "Do not create an independent second narrative chain alongside the authoritative macro structure.",
        ),
    )


def _region_graph_ir(spec: PageArtifactSpec) -> RegionGraphIR | None:
    graph = spec.region_graph
    if graph is None:
        return None
    return RegionGraphIR(
        primary_axis=graph.primary_axis,
        regions=tuple(
            RegionIR(
                id=item.id,
                semantic_refs=item.semantic_refs,
                role=item.role,
                anchor=item.anchor,
                weight=item.weight,
                span=item.span,
                priority=item.priority,
                text_ids=item.text_ids,
            )
            for item in graph.regions
        ),
        relations=tuple(
            RegionRelationIR(source=item.source, target=item.target, type=item.type)
            for item in graph.relations
        ),
    )


def _style09_template_guidance(spec: PageArtifactSpec) -> str:
    """Select one Style 09 page grammar from the audited visual medium."""

    preferred = spec.visual_medium_policy.preferred if spec.visual_medium_policy else "mixed"
    if preferred == "business_scene":
        return (
            "Use a semantic-business-scene page system: build one localized, source-grounded "
            "business setting around the declared object, actor, action and outcome; keep approved "
            "copy in clear editorial regions and reject generic office ambience."
        )
    if preferred in {"relationship_diagram", "data_visualization"}:
        return (
            "Use an infographic-engine page system: make the declared relationship or data "
            "structure legible through a small number of semantic regions; use only authorized "
            "connectors and keep all approved copy readable."
        )
    if preferred == "object_illustration":
        return (
            "Use a concept-product-breakdown page system: keep one declared business object "
            "dominant and attach only source-supported components, roles or outcomes; do not "
            "invent exploded parts."
        )
    return (
        "Use a document-and-publishing hybrid page system: preserve report-page typography and "
        "open editorial regions while assigning one source-grounded business object, action, state "
        "or evidence fragment as the semantic visual anchor; avoid plain equal-weight text panels."
    )


def build_final_prompt_ir(spec: PageArtifactSpec) -> FinalPromptIR:
    """Project the audited ``PageArtifactSpec`` into the final prompt IR."""

    try:
        page_judgment = spec.communication_goal.core_judgment.strip()
        semantic_groups = _semantic_groups(
            spec.evidence,
            page_judgment,
            required_roots=_required_binding_roots(spec),
        )
        if spec.content_root_count and len(semantic_groups) > spec.content_root_count:
            raise PromptContractError(
                "CONTENT_STRUCTURE_CAPACITY_EXCEEDED: semantic groups "
                f"({len(semantic_groups)}) exceed the page's {spec.content_root_count} authoritative root modules"
            )
        style_id = int(spec.art_direction.style_id or 0)
        live_style_surface = style_id == 9
        style09_guidance = (_style09_template_guidance(spec),) if style_id == 9 else ()
        if spec.prompt_mode == "semantic_brief":
            has_region_graph = spec.region_graph is not None
            composition = CompositionIR(
                spatial_organization=(
                    "Follow the authoritative macro region structure: preserve region roles, anchors, relative weights and inter-region relationships; do not replace it with a different macro layout. Region-internal arrangement remains free."
                    if has_region_graph
                    else
                    "Choose the spatial composition from the semantic context, on-screen text reference and style contract; do not inherit a fixed card, lane, matrix, scene or connector recipe from upstream planning."
                ),
                primary_focus=spec.composition.primary_focus or page_judgment,
                visual_responsibility=(
                    "Use the declared visual thesis, named business objects, actors, actions, conditions and outcomes as semantic anchors. Keep macro region ownership fixed when provided; ImageGen owns only region-internal implementation and supporting detail.",
                    "Preserve declared peer, sequence, causal, feedback and hierarchy boundaries; do not invent a stronger relationship than the semantic context supports.",
                ) + style09_guidance,
                focus_policy=spec.composition.focus_policy,
            )
        else:
            spatial_organization = _prompt_safe_visual_text(spec.composition.spatial_organization)
            page_visual_responsibility = (
                _live_style_visual_responsibility(spec.composition, spec.visual_carrier)
                if live_style_surface
                else _visual_responsibility(spec.composition, spec.visual_carrier, spec.visual_budget)
            )
            visual_responsibility = (
                "Use the named business objects, actors, actions and outcomes from the semantic sections as the page-specific visual anchor.",
            ) + page_visual_responsibility + style09_guidance
            composition = CompositionIR(
                spatial_organization=spatial_organization,
                primary_focus=spec.composition.primary_focus,
                visual_responsibility=visual_responsibility,
                focus_policy=spec.composition.focus_policy,
            )
        hard_constraints = tuple(dict.fromkeys((
            *spec.hard_constraints.global_constraints,
            *spec.hard_constraints.page_constraints,
            *(() if live_style_surface else _bracketed_header_constraints(spec.typography.visible_text)),
            *_three_level_group_heading_constraints(spec),
        )))
        semantic_relationship = (
            _prompt_safe_visual_text(_avoid_judgment_repeat(spec.visual_thesis.strip(), page_judgment))
            or spec.semantic_context.argument_chain
            or "Preserve the declared business relationships without inventing sequence, causality or hierarchy."
        )
        return FinalPromptIR(
            deliverable=_deliverable_sentence(spec),
            page_judgment=page_judgment,
            dominant_relationship=semantic_relationship,
            reading_path=tuple(
                _avoid_judgment_repeat(item, page_judgment)
                for item in spec.composition.reading_path
            ),
            semantic_groups=semantic_groups,
            composition=composition,
            visible_text=spec.typography.visible_text,
            hard_constraints=hard_constraints,
            runtime_lock=RuntimeLockIR(style_contract=spec.art_direction.contract),
            page_mission=spec.communication_goal.page_mission,
            semantic_context=spec.semantic_context.text,
            prompt_mode=spec.prompt_mode,
            text_bindings=_text_binding_ir(spec),
            region_graph=_region_graph_ir(spec),
            visual_medium_policy=_visual_medium_policy_ir(spec),
            micro_visual_freedom=_micro_visual_freedom_ir(spec),
        )
    except PromptContractError as exc:
        raise PromptContractError(f"{spec.page_id}: {exc}") from exc


__all__ = [
    "SECTION_HEADINGS",
    "assert_artifact_prompt_contract",
    "build_final_prompt_ir",
    "render_artifact_prompt",
]
