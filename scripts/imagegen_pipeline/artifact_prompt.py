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
    if spec.art_direction.style_id == 9:
        if style_lock is None:
            raise ValueError("Style09 artifact prompt requires its style lock for terminal enforcement")
        from scripts.imagegen_pipeline.deliverable_prompt import enforce_style09_terminal_lock

        prompt = enforce_style09_terminal_lock(prompt, style_lock).rstrip()
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
    if style_id == 9:
        if prompt.count(terminal_header) != 1:
            raise ValueError("Style09 artifact prompt requires one terminal execution lock")
        terminal = prompt.split(terminal_header, 1)[1].strip()
        if not terminal or not prompt.rstrip().endswith(terminal):
            raise ValueError("Style09 terminal execution lock must be at the absolute end")
    elif terminal_header in prompt:
        raise ValueError("non-Style09 artifact prompt contains a Style09 terminal lock")


def _semantic_groups(evidence: tuple[EvidenceSpec, ...]) -> tuple[SemanticGroupIR, ...]:
    """Group evidence deterministically by ``EvidenceSpec.kind``.

    Grouping by an already-audited structural field (rather than any
    heuristic similarity match) keeps the collapse from ever merging two
    evidence items that Stage 02 recorded as distinct facts.
    """

    order: list[str] = []
    buckets: dict[str, list[str]] = {}
    for item in evidence:
        kind = item.kind.strip() or "evidence"
        if kind not in buckets:
            buckets[kind] = []
            order.append(kind)
        buckets[kind].append(item.summary)
    groups = tuple(
        SemanticGroupIR(
            id=kind,
            role=kind,
            summary="; ".join(buckets[kind]),
            emphasis="primary" if index == 0 else "secondary",
        )
        for index, kind in enumerate(order)
    )
    return groups


_ANTI_GENERIC_SCENE_CONSTRAINT = (
    "Do not substitute a generic dashboard, icon collection, card wall, or unrelated decorative scene."
)


def _visual_responsibility(
    composition: CompositionSpec,
    carrier: VisualCarrierSpec,
) -> tuple[str, ...]:
    scene_policy = (
        "Use the selected integrated scene." if carrier.use_scene
        else "Use the selected non-scene business relationship field."
    )
    lines: list[str] = [
        f"Visual carrier: {carrier.business_object} ({carrier.semantic_role})",
        f"{scene_policy} Scene type: {carrier.scene_type}.",
        _ANTI_GENERIC_SCENE_CONSTRAINT,
        f"Primary focus carries: {composition.primary_focus}",
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


def build_final_prompt_ir(spec: PageArtifactSpec) -> FinalPromptIR:
    """Project the audited ``PageArtifactSpec`` into the final prompt IR.

    Reads facts only; qualifiers such as ``direction``/``condition``/
    ``modality``/``basis``/``confidence`` on relationships, the
    ``EvidenceSpec.priority`` code, and ``ConnectorSpec.main_chain`` never
    reach the IR text fields. They stay inside the audited spec, which the
    debug receipt can still reference by hash.
    """

    try:
        semantic_groups = _semantic_groups(spec.evidence)
        composition = CompositionIR(
            spatial_organization=spec.composition.spatial_organization,
            primary_focus=spec.composition.primary_focus,
            visual_responsibility=_visual_responsibility(spec.composition, spec.visual_carrier),
        )
        return FinalPromptIR(
            deliverable=_deliverable_sentence(spec),
            page_judgment=spec.communication_goal.core_judgment.strip(),
            dominant_relationship=spec.visual_thesis.strip(),
            reading_path=spec.composition.reading_path,
            semantic_groups=semantic_groups,
            composition=composition,
            visible_text=spec.typography.visible_text,
            hard_constraints=tuple(
                dict.fromkeys(
                    (
                        *spec.hard_constraints.global_constraints,
                        *spec.hard_constraints.page_constraints,
                    )
                )
            ),
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
