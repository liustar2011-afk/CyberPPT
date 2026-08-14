"""Serialize audited page artifact specs into the GPT Image prompt contract."""

from __future__ import annotations

import re
from pathlib import Path

from cyberppt.page_artifact_spec import PageArtifactSpec


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

_BACKEND_ID_RE = re.compile(r"(?<![A-Za-z0-9])(?:E\d+|P\d{2,3}-T(?:ITLE|\d+)|R_[A-Z0-9_]+)(?![A-Za-z0-9])")


def _bullets(values: tuple[str, ...]) -> str:
    return "\n".join(f"- {value}" for value in values if value)


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
                _bullets(spec.relationships),
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
        from scripts.dual_image_overlay.deliverable_prompt import enforce_style09_terminal_lock

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


__all__ = [
    "SECTION_HEADINGS",
    "assert_artifact_prompt_contract",
    "render_artifact_prompt",
]
