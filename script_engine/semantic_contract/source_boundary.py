"""Deterministic Final Script source-boundary checks.

This module owns objective audience-facing number drift for the formal semantic
contract. It deliberately does not reuse the legacy composed-trace classifier:
CJK n-gram novelty and identifier shape remain compatibility/review signals,
while exact numeric tokens that do not occur anywhere in the Foundation source
surface remain blocking.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from .models import SemanticDiagnostic


_SOURCE_TEXT_KEYS = frozenset(
    {
        "title",
        "statement",
        "claim",
        "definition",
        "context",
        "strength",
        "term",
        "relation",
        "value",
        "unit",
        "name",
        "role",
        "from",
        "to",
        "primary_thesis",
        "author_purpose",
        "decision_boundary",
        "scope",
        "decision_intent",
        "source_heading",
        "meaning",
        "label",
        "text",
    }
)
_FINAL_SCALAR_FIELDS = (
    "title",
    "subtitle",
    "core_message",
    "full_copy",
    "visual_thesis",
    "speaker_notes",
)
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?%?")


def _numeric_tokens(value: object) -> set[str]:
    return set(_NUMBER_RE.findall(str(value or "")))


def _selected_source_strings(value: object) -> Iterable[str]:
    """Yield scalar values nested below an explicitly selected source field."""

    if isinstance(value, (str, int, float)):
        if str(value).strip():
            yield str(value)
        return
    if isinstance(value, list):
        for child in value:
            yield from _selected_source_strings(child)
        return
    if isinstance(value, dict):
        for child in value.values():
            yield from _selected_source_strings(child)


def _source_strings(value: object) -> Iterable[str]:
    """Yield explicit Foundation source fields without business-word inference.

    Field names are structural contract keys, not business vocabulary. Compared
    with legacy composed tracing, this projection also preserves scalar values
    nested inside an explicit ``value``/text field (for example a numeric value
    list), so typed Foundation payload cannot be rejected merely because it is
    represented as an array.
    """

    if isinstance(value, dict):
        for key, child in value.items():
            if key in _SOURCE_TEXT_KEYS:
                yield from _selected_source_strings(child)
            elif isinstance(child, (list, dict)):
                yield from _source_strings(child)
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, (list, dict)):
                yield from _source_strings(child)


def _foundation_number_tokens(foundation: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for value in _source_strings(foundation):
        result.update(_numeric_tokens(value))
    return result


def _final_text_fields(final_script: dict[str, Any]) -> Iterable[tuple[str, str, str]]:
    """Yield ``(slide_id, target, text)`` for audience-facing Final Script text."""

    for slide_index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = str(slide.get("id") or f"#{slide_index}")
        prefix = f"slides.{slide_index}"
        for field in _FINAL_SCALAR_FIELDS:
            value = slide.get(field)
            if isinstance(value, str) and value.strip():
                yield slide_id, f"{prefix}.{field}", value

        for module_index, module in enumerate(slide.get("onscreen") or []):
            if not isinstance(module, dict):
                continue
            module_prefix = f"{prefix}.onscreen[{module_index}]"
            for field in ("heading", "text"):
                value = module.get(field)
                if isinstance(value, str) and value.strip():
                    yield slide_id, f"{module_prefix}.{field}", value
            for item_index, item in enumerate(module.get("items") or []):
                target = f"{module_prefix}.items[{item_index}]"
                if isinstance(item, str) and item.strip():
                    yield slide_id, target, item
                elif isinstance(item, dict):
                    value = item.get("text")
                    if isinstance(value, str) and value.strip():
                        yield slide_id, f"{target}.text", value

        for relation_index, relation in enumerate(slide.get("relationships") or []):
            if not isinstance(relation, dict):
                continue
            relation_prefix = f"{prefix}.relationships[{relation_index}]"
            for field in ("from", "to", "relation"):
                value = relation.get(field)
                if isinstance(value, str) and value.strip():
                    yield slide_id, f"{relation_prefix}.{field}", value


def collect_source_boundary_diagnostics(
    final_script: dict[str, Any],
    foundation: dict[str, Any] | None,
) -> list[SemanticDiagnostic]:
    """Block exact numeric tokens introduced outside the Foundation boundary.

    Identifier novelty, prose novelty and semantic similarity are intentionally
    excluded. Those signals cannot establish unsupported meaning deterministically
    and remain review-only in the compatibility layer.
    """

    if not isinstance(foundation, dict):
        return []

    allowed_numbers = _foundation_number_tokens(foundation)
    diagnostics: list[SemanticDiagnostic] = []
    for slide_id, target, text in _final_text_fields(final_script):
        absent_numbers = sorted(_numeric_tokens(text) - allowed_numbers)
        if not absent_numbers:
            continue
        diagnostics.append(
            SemanticDiagnostic(
                code="FINAL_NUMBER_OUTSIDE_FOUNDATION",
                message=(
                    f"Final Script introduces numeric token(s) {absent_numbers} "
                    "that are absent from the Foundation source surface"
                ),
                slide_id=slide_id,
                target=target,
                severity="blocking",
                relation="bounded_by_foundation",
            )
        )
    return diagnostics


__all__ = ["collect_source_boundary_diagnostics"]
