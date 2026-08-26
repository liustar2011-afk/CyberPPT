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
    PromptContractError,
    RuntimeLockIR,
    SemanticGroupIR,
)


SECTION_HEADINGS = (
    "[1. Deliverable / 成品规格]",
    "[2. Communication goal / 页面使命｜不上屏]",
    "[3. Visual thesis / 核心视觉论点｜不上屏]",
    "[4. Evidence & relationships / 证据与关系｜不上屏]",
    "[5. Visual carrier / 视觉载体｜不上屏]",
    "[6. Composition / 空间组织｜不上屏]",
    "[7. Art direction / 视觉语言｜不上屏]",
    "[8. Typography & exact text / 文字资产合同]",
    "[9. Hard constraints / 硬约束]",
)

_BACKEND_ID_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:E\d+|P\d{2,3}-T(?:ITLE|\d+)|R_[A-Z0-9_]+|(?:NF|ST)-?\d+|rel-\d+)(?![A-Za-z0-9])",
    flags=re.IGNORECASE,
)

# Visual-structure decisions retain machine enums for audit and routing.  The
# final send prompt is a human-facing instruction surface, so project the
# finite set of known enums into plain language before rendering it.  Do not
# weaken the final-prompt contract by allowing arbitrary snake_case through.
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
    "|".join(
        re.escape(token)
        for token in sorted(_VISUAL_ENUM_PHRASES, key=len, reverse=True)
    )
)


def _prompt_safe_visual_text(value: str) -> str:
    """Replace only known visual-routing enums in prompt prose."""

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
    line = (
        f"{relationship.subject} --{relationship.relation}--> "
        f"{'; '.join(relationship.objects)}"
    )
    if qualifiers:
        line += " | " + " | ".join(qualifiers)
    return line


def render_artifact_prompt(spec: PageArtifactSpec, *, style_lock: Path | None = None) -> str:
    """Render the single production prompt in the required nine-part order."""

    deliverable = spec.deliverable
    communication = spec.communication_goal
    carrier = spec.visual_carrier
    composition = spec.composition
    typography = spec.typography
    scene_policy = "Use the selected integrated scene." if carrier.use_scene else "Use the selected non-scene business relationship field."
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
    evidence_lines = tuple(
        f"{item.priority} {item.kind}: {item.summary}" for item in spec.evidence
    )
    relationship_lines = tuple(
        _relationship_line(relationship) for relationship in spec.relationships
    )
    visible_lines = tuple(f'Exact visible text: "{text}"' for text in typography.visible_text)
    sections = (
        "\n".join(
            (
                SECTION_HEADINGS[0],
                f"Create one finished {deliverable.asset_type} for a PowerPoint {deliverable.page_role} page.",
                f"Canvas: {deliverable.canvas[0]}x{deliverable.canvas[1]} ({deliverable.canvas[2]}).",
                "The asset is the body visual only; PowerPoint supplies all excluded chrome.",
            )
        ),
        "\n".join(
            (
                SECTION_HEADINGS[1],
                f"Page mission: {communication.page_mission}",
                f"Core judgment: {communication.core_judgment}",
                "Use this section only to understand the communication outcome; do not render its labels or prose.",
            )
        ),
        "\n".join(
            (
                SECTION_HEADINGS[2],
                spec.visual_thesis,
                "Make this relationship immediately legible from the visual asset; do not render this instruction as copy.",
            )
        ),
        "\n".join(
            (
                SECTION_HEADINGS[3],
                "Evidence:",
                _bullets(evidence_lines),
                "Authoritative business relationships:",
                _bullets(relationship_lines),
                "These facts govern the visual logic; the exact visible wording is defined only in section 8.",
            )
        ),
        "\n".join(
            (
                SECTION_HEADINGS[4],
                f"Selected carrier: {carrier.business_object}",
                f"Semantic role: {carrier.semantic_role}",
                f"Scene policy: {scene_policy} {carrier.scene_type}",
                "Do not substitute a generic dashboard, icon collection, card wall, or unrelated decorative scene.",
            )
        ),
        "\n".join(
            (
                SECTION_HEADINGS[5],
                f"Spatial organization: {composition.spatial_organization}",
                f"Reading path: {' -> '.join(composition.reading_path)}",
                f"Primary focus: {composition.primary_focus}",
                f"Secondary focus: {'; '.join(composition.secondary_focus) or 'none'}",
                f"Relationship encoding: {composition.relationship_encoding}",
                f"Text integration: {composition.text_integration_method}",
                f"Spatial grammar: {', '.join(composition.spatial_grammar)}",
                *(tuple(("Connectors:", _bullets(connectors))) if connectors else ()),
            )
        ),
        "\n".join(
            (
                SECTION_HEADINGS[6],
                spec.art_direction.contract,
            )
        ),
        "\n".join(
            (
                SECTION_HEADINGS[7],
                "Only the following business text may be rendered visibly. Preserve every character and the listed order:",
                _bullets(visible_lines),
                f"Allowed transformations: {', '.join(typography.allowed_transformations) or 'none'}.",
                "Title and subtitle are external PowerPoint text layers and must not appear in this body image.",
            )
        ),
        "\n".join(
            (
                SECTION_HEADINGS[8],
                _bullets(spec.hard_constraints.global_constraints),
                _bullets(spec.hard_constraints.page_constraints),
            )
        ),
    )
    prompt = "\n\n".join(section for section in sections if section.strip()).rstrip()
    if spec.art_direction.style_id in (9, 10):
        if style_lock is None:
            raise ValueError("Style09/10 artifact prompt requires its style lock for terminal enforcement")
        # Style 09/10 is authored in references/visual-system.md.  Keep the
        # complete refreshed Markdown contract at the absolute end of the
        # prompt so page-specific carrier/layout prose cannot override its
        # hard visual rules.  The legacy terminal-lock helper only recognizes
        # an older English marker and is insufficient for the current source.
        from scripts.imagegen_pipeline.deliverable_prompt import style_contract

        source_contract = style_contract(style_lock)
        prompt = (
            f"{prompt}\n\n"
            "【源头风格权威｜references/visual-system.md｜Style 09/10｜最高优先级】\n"
            f"{source_contract}"
        ).rstrip()
    assert_artifact_prompt_contract(
        prompt,
        expected_visible_text=typography.visible_text,
        style_id=spec.art_direction.style_id,
    )
    return prompt + "\n"


def assert_artifact_prompt_contract(
    prompt: str,
    *,
    expected_visible_text: tuple[str, ...] = (),
    style_id: int | None = None,
) -> None:
    """Reject prompts that no longer satisfy the production artifact contract."""

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
    if _BACKEND_ID_RE.search(prompt):
        raise ValueError("artifact prompt contains a backend identifier")
    if expected_visible_text:
        declarations = tuple(
            re.findall(r'^- Exact visible text: "(.*)"$', prompt, flags=re.MULTILINE)
        )
        if declarations != expected_visible_text:
            raise ValueError(
                "artifact prompt visible text declarations must exactly match the audited text contract"
            )
    terminal_header = "【风格09最终执行锁｜最高优先级】"
    if style_id in (9, 10):
        if prompt.count(terminal_header) != 1:
            raise ValueError("Style09/10 artifact prompt requires one terminal execution lock")
        terminal = prompt.split(terminal_header, 1)[1].strip()
        if not terminal or not prompt.rstrip().endswith(terminal):
            raise ValueError("Style09/10 terminal execution lock must be at the absolute end")
    elif terminal_header in prompt:
        raise ValueError("non-Style09/10 artifact prompt contains a Style09/10 terminal lock")


def _avoid_judgment_repeat(text: str, page_judgment: str) -> str:
    """Keep the exact page judgment in its dedicated prompt section only."""

    if page_judgment and page_judgment in text:
        return text.replace(page_judgment, "结果节点（页面判断已锁定）")
    return text


def _semantic_groups(
    evidence: tuple[EvidenceSpec, ...],
    page_judgment: str,
) -> tuple[SemanticGroupIR, ...]:
    """Group evidence by its Stage 02 content root module, falling back to
    ``EvidenceSpec.kind`` when the item carries no root (legacy pages that
    predate the content-integrity contract).

    Grouping by an already-audited structural field (rather than any
    heuristic similarity match) keeps the collapse from ever merging two
    evidence items that Stage 02 recorded as distinct facts. Root-module
    grouping additionally keeps unrelated root modules from being merged
    into a single "process" bucket just because they share a kind.
    """

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
    groups = tuple(
        SemanticGroupIR(
            id=key,
            role=kind_by_key[key],
            summary="; ".join(buckets[key]),
            emphasis="primary" if index == 0 else "secondary",
        )
        for index, key in enumerate(order)
    )
    return groups


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
    # composition.relationship_encoding is deliberately not carried into the
    # final prompt: in current Stage 02 output it embeds raw backend
    # direction tokens (e.g. "outside_to_anchor", "left_to_right") inline
    # with authored Chinese prose, which is exactly the class of leak this
    # compiler exists to stop. Re-add it once Stage 02 authoring stops
    # emitting those tokens; until then final_prompt_contract's snake_case
    # check would (correctly) block it.
    if composition.text_integration_method:
        lines.append(composition.text_integration_method)
    if composition.spatial_grammar:
        lines.append(f"Spatial grammar: {', '.join(composition.spatial_grammar)}")
    for connector in composition.connectors:
        if connector.label:
            lines.append(connector.label)
    return tuple(dict.fromkeys(lines))


def _style09_visual_responsibility(
    composition: CompositionSpec,
    carrier: VisualCarrierSpec,
) -> tuple[str, ...]:
    """Style 09/10 variant of ``_visual_responsibility``.

    Carries Stage 02's named anchor and relationship topology, but never
    forwards its scene/no-scene call or auxiliary-image budget: those were
    decided by an earlier, more conservative design stage that predates
    Style 09's current stance that a photograph and a structural device are
    equally legitimate, chosen by content. Forwarding "zero auxiliary
    images" or "use the non-scene field" verbatim systematically suppressed
    decoration across a whole deck instead of letting Style 09 judge each
    page on its own content, so whether a photo, icon or decorative touch
    appears is left entirely to visual-system.md's own rules.
    """

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
        "Whatever this page's content calls for — a photograph, or a pure "
        "structural field — avoid ending up with nothing but plain colored "
        "text panels; a small icon, a light background tint field, or a "
        "restrained decorative touch is normal for this style, governed "
        "entirely by the Style 09 rules above."
    )
    return tuple(dict.fromkeys(lines))


def _deliverable_sentence(spec: PageArtifactSpec) -> str:
    deliverable = spec.deliverable
    return " ".join(
        (
            f"Create one finished {deliverable.asset_type} for a PowerPoint "
            f"{deliverable.page_role} page.",
            f"Canvas: {deliverable.canvas[0]}x{deliverable.canvas[1]} ({deliverable.canvas[2]}).",
            "The asset is the body visual only; PowerPoint supplies all excluded chrome.",
        )
    )


def _bracketed_header_constraints(visible_text: tuple[str, ...]) -> tuple[str, ...]:
    """Keep explicit ``【…】`` group headings as integrated hierarchy anchors."""

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
            (
                f'Render "{header}" exactly once in its group container, readable and above its '
                "group detail; do not omit it or reduce it to decorative microtext."
            )
            for header in headers
        ),
    )


def build_final_prompt_ir(spec: PageArtifactSpec) -> FinalPromptIR:
    """Project the audited ``PageArtifactSpec`` into the final prompt IR.

    Reads facts only; qualifiers such as ``direction``/``condition``/
    ``modality``/``basis``/``confidence`` on relationships, the
    ``EvidenceSpec.priority`` code, and ``ConnectorSpec.main_chain`` never
    reach the IR text fields. They stay inside the audited spec, which the
    debug receipt can still reference by hash.
    """

    try:
        page_judgment = spec.communication_goal.core_judgment.strip()
        semantic_groups = _semantic_groups(spec.evidence, page_judgment)
        if spec.content_root_count and len(semantic_groups) > spec.content_root_count:
            raise PromptContractError(
                "CONTENT_STRUCTURE_CAPACITY_EXCEEDED: semantic groups "
                f"({len(semantic_groups)}) exceed the page's {spec.content_root_count} "
                "authoritative root modules"
            )
        style09_surface = int(spec.art_direction.style_id or 0) in (9, 10)
        # Style 09/10 owns the visual surface, but still benefits from Stage 02's
        # page-specific composition decisions (reading focus, named business
        # anchor, scene/no-scene call, connector topology) instead of one
        # identical sentence on every page. references/visual-system.md's own
        # rules — rendered in full via the runtime lock below — remain the
        # controlling authority; page-specific data here is advisory context,
        # not a competing layout recipe.
        spatial_organization = _prompt_safe_visual_text(
            spec.composition.spatial_organization
        )
        page_visual_responsibility = (
            _style09_visual_responsibility(spec.composition, spec.visual_carrier)
            if style09_surface
            else _visual_responsibility(
                spec.composition,
                spec.visual_carrier,
                spec.visual_budget,
            )
        )
        visual_responsibility = (
            "Use the named business objects, actors, actions and outcomes from "
            "the semantic sections as the page-specific visual anchor. When the "
            "content is abstract, use a flat structured relationship field; when "
            "a concrete referent exists, use one restrained integrated scene or "
            "business object.",
        ) + page_visual_responsibility
        composition = CompositionIR(
            spatial_organization=spatial_organization,
            primary_focus=spec.composition.primary_focus,
            visual_responsibility=visual_responsibility,
        )
        hard_constraints = tuple(
            dict.fromkeys(
                (
                    *spec.hard_constraints.global_constraints,
                    *spec.hard_constraints.page_constraints,
                    *(() if style09_surface else _bracketed_header_constraints(spec.typography.visible_text)),
                )
            )
        )
        return FinalPromptIR(
            deliverable=_deliverable_sentence(spec),
            page_judgment=page_judgment,
            dominant_relationship=_prompt_safe_visual_text(
                _avoid_judgment_repeat(spec.visual_thesis.strip(), page_judgment)
            ),
            reading_path=tuple(
                _avoid_judgment_repeat(item, page_judgment)
                for item in spec.composition.reading_path
            ),
            semantic_groups=semantic_groups,
            composition=composition,
            visible_text=spec.typography.visible_text,
            hard_constraints=hard_constraints,
            runtime_lock=RuntimeLockIR(style_contract=spec.art_direction.contract),
        )
    except PromptContractError as exc:
        raise PromptContractError(f"{spec.page_id}: {exc}") from exc


__all__ = [
    "SECTION_HEADINGS",
    "assert_artifact_prompt_contract",
    "build_final_prompt_ir",
    "render_artifact_prompt",
]
