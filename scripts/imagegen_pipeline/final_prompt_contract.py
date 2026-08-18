"""Deterministic gate for the final ImageGen prompt text.

Validation failure must block the prompt from being written out — this
module never downgrades a violation to a warning.
"""

from __future__ import annotations

import re

from scripts.imagegen_pipeline.final_prompt_ir import FinalPromptIR, PromptContractError

# Measured 2026-08-18 against 23 real Style09 `artifact-spec-v2` pages from
# projects/power-data-infrastructure-cooperation-v16-20260815-foundation
# (workbench/locks/visual_style_lock.json), rendered through the new
# seven-section renderer end to end: min 18954, max 19920 characters.
#
# Stripping relationship qualifiers, priority-code prefixes, and connector
# booleans barely moves this number: per-page IR content (deliverable +
# judgment + relationship + reading path + semantic groups + visible text +
# composition) totals under 2500 characters. The style runtime contract
# text alone (``art_direction.contract``, identical across all pages of one
# style) is ~19500 characters and dominates the budget. Shrinking it is a
# style-library authoring concern outside this compiler's scope, not
# something normalization at this layer can fix without dropping style
# rules. Budget = measured max * 1.1, rounded up. Revisit per style family
# and with real ImageGen evaluation data before tightening.
MAX_PROMPT_CHARACTERS = 22_000

_PLACEHOLDER_RE = re.compile(r"<[^>\n]{1,80}>")

# Literal strings confirmed present in a real production manifest
# (pages_005_031_22p_.../page_image_pairs.json, page P05) before this
# compiler existed: "P0 process:", "direction=subject_to_object",
# "basis=explicit", "confidence=high", and the "main chain" connector label.
_BACKEND_LEAK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bP[0-3]\s+\w+:"),
    re.compile(r"\b(?:direction|condition|modality|basis|confidence)="),
    re.compile(r"\bmain[ _]chain\b", re.IGNORECASE),
    re.compile(r"\bsecondary[ _]relation\b", re.IGNORECASE),
    # Any bare snake_case token (>=2 segments) reads as a backend enum, not
    # authored prose - e.g. "outside_to_center", "subject_to_object". The
    # boundary uses an ASCII-only character class rather than \w: Python's
    # \w matches CJK characters too, so a token glued directly onto Chinese
    # prose with no space (e.g. "方向为outside_to_anchor，") would silently
    # fail to match against a \w-based boundary and slip through.
    re.compile(r"(?<![A-Za-z0-9_-])[a-z]+(?:_[a-z0-9]+){1,}(?![A-Za-z0-9_-])"),
)

# Fixed, finite technical monikers that legitimately contain underscores.
# ``asset_type`` is a hardcoded constant in cyberppt/page_artifact_spec.py,
# not a leaked Stage 02 enum, so it is exempt from the snake_case leak check.
_ALLOWED_SNAKE_CASE_TOKENS = frozenset({"powerpoint_body_visual_asset"})

_BACKEND_ID_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:E\d+|P\d{2,3}-T(?:ITLE|\d+)|R_[A-Z0-9_]+|(?:NF|ST)-?\d+|rel-\d+)(?![A-Za-z0-9])",
    flags=re.IGNORECASE,
)

_FORBIDDEN_CHROME_TEXT = frozenset({"标题", "副标题", "页码", "logo", "页眉", "页脚"})

_VISIBLE_TEXT_RE = re.compile(r'^- Exact visible text: "(.*)"$', flags=re.MULTILINE)


def validate_final_prompt(
    prompt: str,
    ir: FinalPromptIR,
    *,
    style_id: int | None = None,
) -> None:
    """Reject a rendered prompt that violates the final prompt contract."""

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

    if _PLACEHOLDER_RE.search(prompt):
        raise PromptContractError(f"final prompt contains an unresolved placeholder: {_PLACEHOLDER_RE.search(prompt).group(0)}")

    if _BACKEND_ID_RE.search(prompt):
        raise PromptContractError("final prompt contains a backend identifier")

    for pattern in _BACKEND_LEAK_PATTERNS:
        for match in pattern.finditer(prompt):
            if match.group(0) in _ALLOWED_SNAKE_CASE_TOKENS:
                continue
            raise PromptContractError(f"final prompt contains an internal/backend field: {match.group(0)!r}")

    for text in ir.visible_text:
        if text.strip().lower() in _FORBIDDEN_CHROME_TEXT:
            raise PromptContractError(
                f"final prompt visible text contains excluded chrome content: {text!r}"
            )

    declared = tuple(_VISIBLE_TEXT_RE.findall(prompt))
    if declared != ir.visible_text:
        raise PromptContractError(
            "final prompt visible text declarations must exactly match the IR text contract"
        )

    reading_path_declarations = re.findall(r"^Reading path: .*$", prompt, flags=re.MULTILINE)
    expected_reading_path_line = f"Reading path: {' -> '.join(ir.reading_path)}"
    if len(reading_path_declarations) != 1 or reading_path_declarations[0] != expected_reading_path_line:
        raise PromptContractError("final prompt must declare exactly one reading path")

    if prompt.count(ir.page_judgment) != 1:
        raise PromptContractError("final prompt must state the page judgment exactly once")

    if style_id != 9 and prompt.count(ir.runtime_lock.style_contract) != 1:
        # Style09 rewrites its contract text in place to relocate the
        # terminal execution lock (see enforce_style09_terminal_lock), so an
        # exact-count check against the pre-rewrite text does not apply
        # there; the terminal-lock checks below cover that case instead.
        raise PromptContractError("final prompt must state the runtime style contract exactly once")

    terminal_header = "【风格09最终执行锁｜最高优先级】"
    if style_id == 9:
        if prompt.count(terminal_header) != 1:
            raise PromptContractError("Style09 final prompt requires one terminal execution lock")
        terminal = prompt.split(terminal_header, 1)[1].strip()
        if not terminal or not prompt.rstrip().endswith(terminal):
            raise PromptContractError("Style09 terminal execution lock must be at the absolute end")
    elif terminal_header in prompt:
        raise PromptContractError("non-Style09 final prompt contains a Style09 terminal lock")


__all__ = [
    "MAX_PROMPT_CHARACTERS",
    "validate_final_prompt",
]
