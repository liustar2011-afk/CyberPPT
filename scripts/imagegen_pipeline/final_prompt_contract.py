"""Deterministic gate for the final ImageGen prompt text.

Validation failure must block the prompt from being written out — this
module never downgrades a violation to a warning.
"""

from __future__ import annotations

import re

from scripts.imagegen_pipeline.final_prompt_ir import FinalPromptIR, PromptContractError

# Re-measured 2026-08-21 against the current Style09 source contract and the
# project's 16 content pages: 25741-26002 characters. The source contract
# was expanded after the previous 25500-character ceiling was set.
#
# Earlier baseline, retained for context: against the same 23 real Style09
# pages from projects/power-data-infrastructure-cooperation-v16-20260815-foundation,
# after Style09's prompt_contract was restored to the scene-led spec from
# references/visual-system.md (the earlier flat/minimal contract had lost
# its "### Final ImageGen execution lock — hard" section and several other
# sections entirely -- see the commit restoring it): min 21516, max 22047
# characters, up from the prior measurement's 18954-19920 because the
# restored contract (~18500 chars) is itself longer than the short one it
# replaced (~4850 chars).
#
# Per-page IR content (deliverable + judgment + relationship + reading path
# + semantic groups + visible text + composition) still totals under 2500
# characters; the style runtime contract text alone continues to dominate
# the budget. Shrinking it is a style-library authoring concern outside
# this compiler's scope. Budget = measured max * 1.1, rounded up to the
# nearest 100. Revisit per style family and with real ImageGen evaluation
# data before tightening; re-measure whenever a style's prompt_contract
# changes materially.
# Rich, source-faithful on-screen copy can add a few hundred characters to
# the measured style contract. Keep the safety ceiling above that variance
# while retaining the hard upper bound for malformed or runaway prompts.
MAX_PROMPT_CHARACTERS = 30_000

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
# Empty for now: ``asset_type`` used to be the hardcoded snake_case constant
# "powerpoint_body_visual_asset" and needed this exemption; it is now the
# natural-language phrase "presentation content visual" (see
# cyberppt/page_artifact_spec.py), so no exemption is needed. Kept as a named
# set, not deleted, so a future fixed technical moniker has an obvious place
# to register itself rather than reopening the snake_case check.
_ALLOWED_SNAKE_CASE_TOKENS: frozenset[str] = frozenset()

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
    reading_boundary_declarations = re.findall(
        r"^Reading boundary: .*$", prompt, flags=re.MULTILINE
    )
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

    if style_id not in (9, 10) and prompt.count(ir.runtime_lock.style_contract) != 1:
        # Style09/10 rewrite their contract text in place to relocate the
        # terminal execution lock (see enforce_style09_terminal_lock), so an
        # exact-count check against the pre-rewrite text does not apply
        # there; the terminal-lock checks below cover that case instead.
        raise PromptContractError("final prompt must state the runtime style contract exactly once")

    terminal_header = "【风格09最终执行锁｜最高优先级】"
    if style_id in (9, 10):
        if prompt.count(terminal_header) != 1:
            raise PromptContractError("Style09/10 final prompt requires one terminal execution lock")
        terminal = prompt.split(terminal_header, 1)[1].strip()
        if not terminal or not prompt.rstrip().endswith(terminal):
            raise PromptContractError("Style09/10 terminal execution lock must be at the absolute end")
    elif terminal_header in prompt:
        raise PromptContractError("non-Style09/10 final prompt contains a Style09/10 terminal lock")


__all__ = [
    "MAX_PROMPT_CHARACTERS",
    "validate_final_prompt",
]
