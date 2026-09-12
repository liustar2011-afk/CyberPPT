"""Deterministic contracts for narrowly scoped literal-preservation text.

``fidelity_text`` is intentionally much smaller than ``full_copy``.  It carries
only strings whose spelling must remain stable when downstream Stage 02 gains
freedom to compress or rewrite ordinary presentation copy.

This module is additive during the migration: payloads that do not declare
``fidelity_text`` remain valid until the Final Script schema version is advanced.
Once the field is present, however, its contents are checked fail-closed.
"""
from __future__ import annotations

import re
from typing import Any


FIDELITY_TEXT_MAX_ITEMS = 8
FIDELITY_TEXT_MAX_EFFECTIVE_CHARS = 120
FIDELITY_VISIBILITY = frozenset({"required", "if_rendered"})


def _text(value: object) -> str:
    return str(value or "").strip()


def _effective_chars(value: str) -> int:
    return len(re.sub(r"\s+", "", value))


def canonicalize_fidelity_text(value: object) -> list[dict[str, str]]:
    """Return normalized fidelity entries, preserving first-occurrence order.

    This helper is deliberately conservative.  It accepts only the canonical
    object form and does not infer literal strings from ordinary copy.  Duplicate
    entries are removed by exact trimmed text; visibility defaults are not
    invented because required-vs-optional visibility is part of the authoring
    decision.
    """

    if not isinstance(value, list):
        return []
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        text = _text(item.get("text"))
        visibility = _text(item.get("visibility"))
        if not text or visibility not in FIDELITY_VISIBILITY or text in seen:
            continue
        seen.add(text)
        result.append({"text": text, "visibility": visibility})
    return result


def check_fidelity_text_contract(final_script: dict[str, Any]) -> list[str]:
    """Validate every explicitly declared ``fidelity_text`` field.

    Missing fields are ignored while the repository is in the additive migration
    phase.  Present fields must already be canonical: object entries, explicit
    visibility, unique literal text, and exact occurrence in ``full_copy``.
    Capacity findings are deterministic blockers for now; the later schema
    migration may route the two capacity codes to review-only severity.
    """

    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        if "fidelity_text" not in slide:
            continue

        slide_id = slide.get("id") or f"#{index}"
        prefix = f"slides.{index} ({slide_id}).fidelity_text"
        value = slide.get("fidelity_text")
        if not isinstance(value, list):
            issues.append(
                f"FIDELITY_TEXT_INVALID: {prefix}: fidelity_text must be an array of canonical objects"
            )
            continue

        full_copy = _text(slide.get("full_copy"))
        seen: set[str] = set()
        effective_chars = 0
        for item_index, item in enumerate(value):
            item_path = f"{prefix}[{item_index}]"
            if not isinstance(item, dict):
                issues.append(
                    f"FIDELITY_TEXT_ITEM_INVALID: {item_path}: each fidelity item must be an object"
                )
                continue

            text = _text(item.get("text"))
            visibility = _text(item.get("visibility"))
            if not text:
                issues.append(
                    f"FIDELITY_TEXT_EMPTY: {item_path}.text: fidelity text must be non-empty after trimming"
                )
                continue
            if visibility not in FIDELITY_VISIBILITY:
                issues.append(
                    f"FIDELITY_TEXT_VISIBILITY_INVALID: {item_path}.visibility: expected 'required' or 'if_rendered', got {visibility!r}"
                )
            if text in seen:
                issues.append(
                    f"FIDELITY_TEXT_DUPLICATE: {item_path}.text: duplicate literal {text!r}; keep the first occurrence only"
                )
            seen.add(text)
            effective_chars += _effective_chars(text)
            if text not in full_copy:
                issues.append(
                    f"FIDELITY_TEXT_OUTSIDE_FULL_COPY: {item_path}.text: literal {text!r} does not occur exactly in full_copy"
                )

        if len(value) > FIDELITY_TEXT_MAX_ITEMS:
            issues.append(
                f"FIDELITY_TEXT_ITEM_LIMIT: {prefix}: {len(value)} items exceed the migration limit of {FIDELITY_TEXT_MAX_ITEMS}"
            )
        if effective_chars > FIDELITY_TEXT_MAX_EFFECTIVE_CHARS:
            issues.append(
                f"FIDELITY_TEXT_CHAR_LIMIT: {prefix}: {effective_chars} effective characters exceed the migration limit of {FIDELITY_TEXT_MAX_EFFECTIVE_CHARS}"
            )
    return issues


__all__ = [
    "FIDELITY_TEXT_MAX_EFFECTIVE_CHARS",
    "FIDELITY_TEXT_MAX_ITEMS",
    "FIDELITY_VISIBILITY",
    "canonicalize_fidelity_text",
    "check_fidelity_text_contract",
]
