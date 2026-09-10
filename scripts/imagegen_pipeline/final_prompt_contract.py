"""Deterministic gate for the final ImageGen prompt text."""

from __future__ import annotations

import re

from scripts.imagegen_pipeline.final_prompt_ir import FinalPromptIR, PromptContractError
from scripts.imagegen_pipeline.runtime_style_contract import TERMINAL_EXECUTION_HEADING

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
    from scripts.imagegen_pipeline.final_prompt_renderer import ACCEPTANCE_HEADING, HARD_CONSTRAINTS_HEADING, SECTION_HEADINGS

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
    legacy_source_declarations = tuple(
        re.findall(r'^- Source onscreen text: \"(.*)\"$', prompt, flags=re.MULTILINE)
    )
    if legacy_source_declarations:
        raise PromptContractError(
            "supplied source material declarations are retired; use exact or explicitly rewriteable copy declarations"
        )
    if ir.copy_contract is not None:
        exact_declarations = tuple(
            re.findall(r'^- Exact visible text: \"(.*)\"$', prompt, flags=re.MULTILINE)
        )
        rewriteable_declarations = tuple(
            re.findall(r'^- Rewriteable visible source: \"(.*)\"$', prompt, flags=re.MULTILINE)
        )
        locked_text = {item.text for item in ir.copy_contract.locked_copy}
        rewriteable_text = {item.source_text for item in ir.copy_contract.rewriteable_copy}
        expected_exact = tuple(text for text in ir.visible_text if text in locked_text)
        expected_rewriteable = tuple(text for text in ir.visible_text if text in rewriteable_text)
        if exact_declarations != expected_exact:
            raise PromptContractError("final prompt exact-copy declarations must match locked copy")
        if rewriteable_declarations != expected_rewriteable:
            raise PromptContractError("final prompt rewriteable-copy declarations must match rewriteable copy")
        if "You may rewrite, merge, shorten, reorder, split, select, or replace" in prompt:
            raise PromptContractError("copy-contract prompt cannot grant blanket rewrite authority")
        if (
            not ir.copy_contract.extra_text.allowed
            and "Do not add any visible text that is not declared in this copy contract." not in prompt
        ):
            raise PromptContractError("copy-contract prompt must forbid undeclared extra visible text")
    else:
        exact_declarations = tuple(
            re.findall(r'^- Exact visible text: \"(.*)\"$', prompt, flags=re.MULTILINE)
        )
        if exact_declarations != ir.visible_text:
            raise PromptContractError(
                "final prompt exact-copy declarations must match the supplied visible copy"
            )
        if "You may rewrite, merge, shorten, reorder, split, select, or replace" in prompt:
            raise PromptContractError("legacy fallback cannot grant blanket rewrite authority")
        if "Do not add any visible text that is not declared in this copy contract." not in prompt:
            raise PromptContractError("legacy fallback must forbid undeclared extra visible text")
    _validate_text_bindings(prompt, ir)

    runtime_style_contract = ir.runtime_lock.style_contract.strip()
    if style_id == 9:
        if prompt.count(TERMINAL_EXECUTION_HEADING) != 1:
            raise PromptContractError(
                "live runtime style prompt requires one terminal execution lock"
            )
        terminal = prompt.split(TERMINAL_EXECUTION_HEADING, 1)[1].strip()
        if not terminal or not prompt.rstrip().endswith(terminal):
            raise PromptContractError(
                "live runtime style prompt requires one terminal execution lock at the absolute end"
            )
    else:
        if TERMINAL_EXECUTION_HEADING in prompt:
            raise PromptContractError(
                "non-live style prompt contains a live terminal execution lock"
            )
        if prompt.count(runtime_style_contract) != 1:
            raise PromptContractError(
                "final prompt must contain the runtime style contract exactly once"
            )

    if ir.full_slide_design_context is not None:
        context = ir.full_slide_design_context
        expected = f"Full-slide design context: {context.canvas[0]}x{context.canvas[1]} ({context.canvas[2]})."
        if prompt.count(expected) != 1:
            raise PromptContractError("full-slide design context must be declared exactly once")
        if "External title region:" not in prompt or "Body image export remains independent" not in prompt:
            raise PromptContractError("full-slide prompt must declare external title and body-export mapping")


    if ir.acceptance is not None:
        if prompt.count(ACCEPTANCE_HEADING) != 1:
            raise PromptContractError("acceptance criteria section must appear exactly once")
        if not (
            prompt.index(ACCEPTANCE_HEADING) < prompt.index(HARD_CONSTRAINTS_HEADING)
            < prompt.index(SECTION_HEADINGS[-1])
        ):
            raise PromptContractError("acceptance criteria must precede hard constraints and runtime lock")
        acceptance = ir.acceptance
        expected_lines = (
            f"Exact copy coverage: {round(acceptance.exact_copy_coverage * 100)}% of locked copy must be present exactly once.",
            f"Maximum extra visible text count: {acceptance.extra_text_count}.",
            "Forbidden structure absence: required.",
            "Style lock conformance: required.",
        )
        if any(prompt.count(line) != 1 for line in expected_lines):
            raise PromptContractError("acceptance criteria values differ from the prompt IR")
    elif ACCEPTANCE_HEADING in prompt:
        raise PromptContractError("legacy prompt without acceptance IR cannot contain acceptance criteria")

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

    lines = prompt.splitlines()
    expected_context = {
        "【核心判断（不上屏）】": ("page judgment", ir.page_judgment),
        "【页面使命（不上屏）】": ("page mission", ir.page_mission or ir.page_judgment),
    }
    if ir.page_title:
        expected_context["【标题（不上屏）】"] = ("page title", ir.page_title)
    for heading, (field_name, value) in expected_context.items():
        if lines.count(heading) != 1:
            raise PromptContractError(f"final prompt must state one {field_name} ({heading}) field")
        index = lines.index(heading)
        if index + 1 >= len(lines) or lines[index + 1] != value:
            raise PromptContractError(
                f"final prompt {field_name} ({heading}) value differs from the prompt IR"
            )



__all__ = [
    "MAX_PROMPT_CHARACTERS",
    "backend_identifier_leaks",
    "validate_final_prompt",
]
