"""The single renderer from ``FinalPromptIR`` to the final ImageGen prompt text.

This module owns the fixed seven-section layout. It reads only IR fields —
never the original Markdown, Stage 02 JSON, or any regex-based text
splicing — so there is exactly one way a production prompt gets its final
shape.
"""

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


def _group_line(group: Any) -> str:
    return f"- [{group.role} / {group.emphasis}] {group.summary}"


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
                    "Reading boundary: preserve only source-supported order and direction; "
                    "choose the visual reading implementation freely."
                    if ir.prompt_mode == "semantic_brief"
                    else f"Reading path: {' -> '.join(ir.reading_path)}"
                ),
            )
        ),
        "\n".join((SECTION_HEADINGS[3], *(_group_line(group) for group in ir.semantic_groups))),
        "\n".join(
            (
                SECTION_HEADINGS[4],
                f"Spatial organization: {ir.composition.spatial_organization}",
                f"Primary focus: {ir.composition.primary_focus}",
                *ir.composition.visual_responsibility,
            )
        ),
        "\n".join(
            (
                SECTION_HEADINGS[5],
                "Only the following business text may be rendered visibly. Preserve every character and the listed order:",
                *(f'- Exact visible text: "{text}"' for text in ir.visible_text),
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
    """Build the sidecar receipt carrying what the final prompt intentionally omits."""

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
                "role": group.role,
                "emphasis": group.emphasis,
                "summary": group.summary,
            }
            for group in ir.semantic_groups
        ],
        "composition": {
            "spatial_organization": ir.composition.spatial_organization,
            "primary_focus": ir.composition.primary_focus,
            "visual_responsibility": list(ir.composition.visual_responsibility),
        },
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
