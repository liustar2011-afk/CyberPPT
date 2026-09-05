"""Deterministic gate for the final ImageGen prompt text."""

from __future__ import annotations

import re

from scripts.imagegen_pipeline.final_prompt_ir import FinalPromptIR, PromptContractError

# ImageGen handoff deliberately has a high ceiling: Stage 01 may copy the
# complete page prose into the on-screen field, so prompt compilation must not
# perform a second content-density reduction.
MAX_PROMPT_CHARACTERS = 100_000
_PLACEHOLDER_RE = re.compile(r"<[^>\n]{1,80}>")
_BACKEND_LEAK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bP[0-3]\s+\w+:"),
    re.compile(r"\b(?:direction|condition|modality|basis|confidence)="),
    re.compile(r"\bmain[ _]chain\b", re.IGNORECASE),
    re.compile(r"\bsecondary[ _]relation\b", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9_-])[a-z]+(?:_[a-z0-9]+){1,}(?![A-Za-z0-9_-])"),
)
_ALLOWED_SNAKE_CASE_TOKENS: frozenset[str] = frozenset()
_BACKEND_ID_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:E\d+|RG\d+|P\d{2,3}-T(?:ITLE|\d+)|R_[A-Z0-9_]+|(?:NF|ST)-?\d+|rel-\d+)(?![A-Za-z0-9])",
    flags=re.IGNORECASE,
)
_FORBIDDEN_CHROME_TEXT = frozenset({"标题", "副标题", "页码", "logo", "页眉", "页脚"})
_GROUP_HEADING_RE = re.compile(r"^Semantic group ([A-Z]|\d+):$", flags=re.MULTILINE)


def backend_identifier_leaks(
    prompt: str,
    *,
    approved_visible_text: tuple[str, ...] = (),
) -> tuple[str, ...]:
    approved = {
        match.group(0).casefold()
        for text in approved_visible_text
        for match in _BACKEND_ID_RE.finditer(text)
    }
    return tuple(
        match.group(0)
        for match in _BACKEND_ID_RE.finditer(prompt)
        if match.group(0).casefold() not in approved
    )


def _validate_text_bindings(prompt: str, ir: FinalPromptIR) -> None:
    if not ir.text_bindings:
        return
    group_labels = tuple(_GROUP_HEADING_RE.findall(prompt))
    if len(group_labels) != len(ir.semantic_groups):
        raise PromptContractError(
            "final prompt must render exactly one public semantic-group label per IR group"
        )
    if len(group_labels) != len(set(group_labels)):
        raise PromptContractError("final prompt semantic-group labels must be unique")
    for binding in ir.text_bindings:
        if binding.group_id in prompt:
            raise PromptContractError("final prompt leaked a backend content-root id")
        for text_id in binding.text_ids:
            if text_id and text_id in prompt:
                raise PromptContractError("final prompt leaked a backend text id")


def validate_final_prompt(
    prompt: str,
    ir: FinalPromptIR,
    *,
    style_id: int | None = None,
) -> None:
    from scripts.imagegen_pipeline.final_prompt_renderer import SECTION_HEADINGS

    positions: list[int] = []
    for heading in SECTION_HEADINGS:
        count = prompt.count(heading)
        if count != 1:
            raise PromptContractError(f"final prompt section is missing or duplicated: {heading}")
        positions.append(prompt.index(heading))
    if positions != sorted(positions):
        raise PromptContractError("final prompt sections are out of contract order")
    for index, heading in enumerate(SECTION_HEADINGS):
        content_start = positions[index] + len(heading)
        content_end = positions[index + 1] if index + 1 < len(positions) else len(prompt)
        if not prompt[content_start:content_end].strip():
            raise PromptContractError(f"final prompt section has no content: {heading}")

    if len(prompt) > MAX_PROMPT_CHARACTERS:
        raise PromptContractError(
            f"final prompt exceeds the {MAX_PROMPT_CHARACTERS}-character budget: {len(prompt)}"
        )
    placeholder = _PLACEHOLDER_RE.search(prompt)
    if placeholder:
        raise PromptContractError(
            f"final prompt contains an unresolved placeholder: {placeholder.group(0)}"
        )
    if backend_identifier_leaks(prompt, approved_visible_text=ir.visible_text):
        raise PromptContractError("final prompt contains a backend identifier")
    for pattern in _BACKEND_LEAK_PATTERNS:
        for match in pattern.finditer(prompt):
            if match.group(0) in _ALLOWED_SNAKE_CASE_TOKENS:
                continue
            raise PromptContractError(
                f"final prompt contains an internal/backend field: {match.group(0)!r}"
            )
    for text in ir.visible_text:
        if text.strip().lower() in _FORBIDDEN_CHROME_TEXT:
            raise PromptContractError(
                f"final prompt visible text contains excluded chrome content: {text!r}"
            )
    source_declarations = tuple(
        re.findall(r'^- Source onscreen text: "(.*)"$', prompt, flags=re.MULTILINE)
    )
    if source_declarations != ir.visible_text:
        raise PromptContractError(
            "final prompt source onscreen declarations must match the supplied source material"
        )
    _validate_text_bindings(prompt, ir)

    reading_path_declarations = re.findall(r"^Reading path: .*$", prompt, flags=re.MULTILINE)
    reading_boundary_declarations = re.findall(r"^Reading boundary: .*$", prompt, flags=re.MULTILINE)
    if ir.prompt_mode == "semantic_brief":
        if reading_path_declarations or len(reading_boundary_declarations) != 1:
            raise PromptContractError(
                "semantic-brief prompt must declare one reading boundary and no fixed reading path"
            )
    else:
        expected_reading_path_line = f"Reading path: {' -> '.join(ir.reading_path)}"
        if (
            len(reading_path_declarations) != 1
            or reading_path_declarations[0] != expected_reading_path_line
            or reading_boundary_declarations
        ):
            raise PromptContractError(
                "directed-composition prompt must declare exactly one reading path"
            )

    judgment_line = f"Core judgment (non-visible): {ir.page_judgment}"
    if sum(line == judgment_line for line in prompt.splitlines()) != 1:
        raise PromptContractError("final prompt must state one authoritative page judgment")



__all__ = [
    "MAX_PROMPT_CHARACTERS",
    "backend_identifier_leaks",
    "validate_final_prompt",
]
