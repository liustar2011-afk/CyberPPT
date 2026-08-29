"""The single renderer from ``FinalPromptIR`` to the final ImageGen prompt text."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from scripts.imagegen_pipeline.final_prompt_contract import validate_final_prompt
from scripts.imagegen_pipeline.final_prompt_ir import FinalPromptIR
from scripts.imagegen_pipeline.runtime_style_contract import (
    enforce_terminal_execution_lock,
    load_runtime_style_contract,
)

SECTION_HEADINGS = (
    "[1. Deliverable]",
    "[2. Page judgment]",
    "[3. Dominant relationship and reading path]",
    "[4. Semantic groups]",
    "[5. Composition skeleton and visual responsibility]",
    "[6. Exact visible text contract]",
    "[7. Runtime lock]",
)

HARD_CONSTRAINTS_HEADING = "[Hard constraints]"


_PUBLIC_SEMANTIC_ROLE_LABELS = {
    "root_module": "content group",
    "root_subgroup": "supporting content group",
    "evidence": "evidence",
    "fact": "evidence",
    "process": "process",
    "result": "result",
    "judgment": "judgment",
    "content": "content",
}


def _public_semantic_role(value: str) -> str:
    role = str(value or "").strip()
    return _PUBLIC_SEMANTIC_ROLE_LABELS.get(role, role.replace("_", " ") or "content")


def _group_lines(ir: FinalPromptIR) -> tuple[str, ...]:
    binding_by_group = {binding.group_id: binding for binding in ir.text_bindings}
    lines: list[str] = []
    for index, group in enumerate(ir.semantic_groups, start=1):
        label = chr(64 + index) if index <= 26 else str(index)
        lines.append(f"Semantic group {label}:")
        binding = binding_by_group.get(group.id)
        responsibility = f"- semantic responsibility: [{_public_semantic_role(group.role)} / {group.emphasis}]"
        if binding is None:
            responsibility += f" {group.summary}"
        lines.append(responsibility)
        if binding is not None:
            lines.append("- exact visible text assigned to this group:")
            lines.extend(f'- Exact visible text: "{text}"' for text in binding.exact_text)
            lines.append(
                f"- hierarchy: level {binding.hierarchy_level}; keep this group's text together in one coherent visual region."
            )
    return tuple(lines)


_FOCUS_POLICY_LABELS = {
    "single_anchor": "single anchor",
    "paired_focus": "paired focus",
    "peer_field": "peer field",
    "distributed_focus": "distributed focus",
    "sequence_focus": "sequence focus",
}


def _public_text_ordinals(ir: FinalPromptIR) -> dict[str, int]:
    order: dict[str, int] = {}
    ordinal = 1
    for binding in ir.text_bindings:
        for text_id in binding.text_ids:
            order[text_id] = ordinal
            ordinal += 1
    return order


def _macro_structure_lines(ir: FinalPromptIR) -> tuple[str, ...]:
    graph = ir.region_graph
    policy = ir.visual_medium_policy
    lines: list[str] = [
        f"Focus policy: {_FOCUS_POLICY_LABELS[ir.composition.focus_policy]}.",
    ]
    if graph is not None:
        lines.append(f"Macro reading axis: {graph.primary_axis.replace('_', ' ')}.")
        text_ordinals = _public_text_ordinals(ir)
        public_region = {region.id: index for index, region in enumerate(graph.regions, start=1)}
        for index, region in enumerate(graph.regions, start=1):
            ownership = [text_ordinals[text_id] for text_id in region.text_ids if text_id in text_ordinals]
            ownership_text = ", ".join(str(item) for item in ownership) or "none"
            lines.append(
                "Region " + str(index) + ": "
                + f"role {region.role.replace('_', ' ')}; anchor {region.anchor.replace('_', ' ')}; "
                + f"relative share about {round(region.weight * 100)}%; span {region.span.replace('_', ' ')}; "
                + f"priority {region.priority.replace('_', ' ')}; owns exact visible-text item(s) {ownership_text}."
            )
        for relation in graph.relations:
            source = public_region[relation.source]
            target = public_region[relation.target]
            lines.append(
                f"Region relationship: Region {source} to Region {target} — {relation.type.replace('_', ' ')}."
            )
        lines.append(
            "The Region structure is the macro composition authority; do not merge, reorder, promote or demote regions in a way that changes their semantic roles."
        )
    if policy is not None:
        allowed = "; ".join(item.replace("_", " ") for item in policy.allowed)
        lines.extend((
            f"Preferred visual medium: {policy.preferred.replace('_', ' ')}.",
            f"Allowed visual media: {allowed}.",
            f"Scene policy: {policy.scene_policy.replace('_', ' ')}.",
            f"Medium rationale: {policy.rationale}",
        ))
    return tuple(lines)


def render_final_prompt(
    ir: FinalPromptIR,
    *,
    style_id: int | None = None,
    style_lock: Path | None = None,
) -> str:
    """Render the single production prompt in the required seven-part order."""

    runtime = None
    runtime_style_contract = ir.runtime_lock.style_contract
    if style_id in (9, 10):
        if style_lock is None:
            raise ValueError("live runtime style final prompt requires its style lock")
        runtime = load_runtime_style_contract(style_lock)
        runtime_style_contract = runtime.contract

    runtime_section = "\n".join(
        (
            SECTION_HEADINGS[6],
            runtime_style_contract,
            *((ir.runtime_lock.terminal_lock,) if runtime is None and ir.runtime_lock.terminal_lock else ()),
        )
    )
    hard_constraints_section = "\n".join((HARD_CONSTRAINTS_HEADING, *ir.hard_constraints))
    mission_lines = (
        (f"Page mission (non-visible): {ir.page_mission}",)
        if ir.page_mission and ir.page_mission != ir.page_judgment
        else ()
    )
    sections_before_runtime = (
        "\n".join((SECTION_HEADINGS[0], ir.deliverable)),
        "\n".join(
            (
                SECTION_HEADINGS[1],
                *mission_lines,
                f"Core judgment (non-visible): {ir.page_judgment}",
                *(
                    (
                        "Source-grounded semantic context (non-visible; use for business "
                        "objects, conditions, boundaries and implications; render only text "
                        "also present in the exact visible-text whitelist):",
                        ir.semantic_context,
                    )
                    if ir.semantic_context
                    else ()
                ),
            )
        ),
        "\n".join(
            (
                SECTION_HEADINGS[2],
                ir.dominant_relationship,
                (
                    (
                        "Reading boundary: preserve source-supported order and direction and follow the macro reading axis defined in Section 5; choose only region-internal reading implementation freely."
                        if ir.region_graph is not None
                        else
                        "Reading boundary: preserve only source-supported order and direction; choose the visual reading implementation freely."
                    )
                    if ir.prompt_mode == "semantic_brief"
                    else f"Reading path: {' -> '.join(ir.reading_path)}"
                ),
            )
        ),
        "\n".join((SECTION_HEADINGS[3], *_group_lines(ir))),
        "\n".join(
            (
                SECTION_HEADINGS[4],
                f"Spatial organization: {ir.composition.spatial_organization}",
                f"Primary focus: {ir.composition.primary_focus}",
                *_macro_structure_lines(ir),
                *ir.composition.visual_responsibility,
            )
        ),
        "\n".join(
            (
                SECTION_HEADINGS[5],
                (
                    "The exact visible text is declared once inside its semantic group above. "
                    "Preserve every character and the declared order. Line breaks, grouping, "
                    "position changes and stronger emphasis before a colon are allowed within "
                    "the same semantic region; do not duplicate the label elsewhere."
                ),
                *(
                    ()
                    if ir.text_bindings
                    else tuple(f'- Exact visible text: "{text}"' for text in ir.visible_text)
                ),
            )
        ),
    )
    sections = (*sections_before_runtime, hard_constraints_section, runtime_section)
    prompt = "\n\n".join(section for section in sections if section.strip()).rstrip() + "\n"
    if runtime is not None:
        prompt = enforce_terminal_execution_lock(prompt, runtime)
    validate_final_prompt(prompt, ir, style_id=style_id)
    return prompt


def render_debug_receipt(
    ir: FinalPromptIR,
    *,
    page_id: str,
    compiler: str,
    prompt_ir_version: str,
    source_hashes: tuple[tuple[str, str], ...] = (),
) -> dict[str, object]:
    """Build the sidecar receipt carrying prompt-excluded provenance/bindings.

    Binding fields are additive under the existing v1 receipt schema so old
    consumers continue to read the same authority/version token.
    """

    rendered_group = {group.id: index for index, group in enumerate(ir.semantic_groups, start=1)}
    return {
        "schema": "cyberppt.final_prompt_debug.v1",
        "page": page_id,
        "compiler": compiler,
        "prompt_ir_version": prompt_ir_version,
        "page_judgment": ir.page_judgment,
        "page_mission": ir.page_mission,
        "semantic_context_sha256": hashlib.sha256(
            ir.semantic_context.encode("utf-8")
        ).hexdigest() if ir.semantic_context else "",
        "prompt_mode": ir.prompt_mode,
        "reading_path": list(ir.reading_path),
        "semantic_groups": [
            {
                "id": group.id,
                "rendered_group": rendered_group[group.id],
                "role": group.role,
                "emphasis": group.emphasis,
                "summary": group.summary,
            }
            for group in ir.semantic_groups
        ],
        "text_bindings": [
            {
                "root_id": binding.group_id,
                "rendered_group": rendered_group[binding.group_id],
                "role": binding.role,
                "hierarchy_level": binding.hierarchy_level,
                "text_ids": list(binding.text_ids),
                "exact_text": list(binding.exact_text),
            }
            for binding in ir.text_bindings
        ],
        "composition": {
            "spatial_organization": ir.composition.spatial_organization,
            "primary_focus": ir.composition.primary_focus,
            "focus_policy": ir.composition.focus_policy,
            "visual_responsibility": list(ir.composition.visual_responsibility),
        },
        "region_graph": (
            {
                "primary_axis": ir.region_graph.primary_axis,
                "regions": [
                    {
                        "id": region.id,
                        "semantic_refs": list(region.semantic_refs),
                        "role": region.role,
                        "anchor": region.anchor,
                        "weight": region.weight,
                        "span": region.span,
                        "priority": region.priority,
                        "text_ids": list(region.text_ids),
                    }
                    for region in ir.region_graph.regions
                ],
                "relations": [
                    {"from": relation.source, "to": relation.target, "type": relation.type}
                    for relation in ir.region_graph.relations
                ],
            }
            if ir.region_graph is not None
            else None
        ),
        "visual_medium_policy": (
            {
                "preferred": ir.visual_medium_policy.preferred,
                "allowed": list(ir.visual_medium_policy.allowed),
                "scene_policy": ir.visual_medium_policy.scene_policy,
                "rationale": ir.visual_medium_policy.rationale,
            }
            if ir.visual_medium_policy is not None
            else None
        ),
        "visible_text": list(ir.visible_text),
        "hard_constraints": list(ir.hard_constraints),
        "source_hashes": dict(source_hashes),
    }


__all__ = [
    "HARD_CONSTRAINTS_HEADING",
    "SECTION_HEADINGS",
    "render_debug_receipt",
    "render_final_prompt",
]
