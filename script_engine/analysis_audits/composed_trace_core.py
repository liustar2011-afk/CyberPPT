"""Core source-surface tracing for Final Script wording."""
from __future__ import annotations

import re
from typing import Any, Iterable


CJK = r"[㐀-䶿一-鿿豈-﫿]"
_SOURCE_TEXT_KEYS = {
    "title", "statement", "claim", "definition", "context", "strength",
    "term", "relation", "value", "unit", "name", "role", "from", "to",
    "primary_thesis", "author_purpose", "decision_boundary", "scope",
    "decision_intent", "source_heading", "meaning", "label", "text",
}
_FINAL_SCALAR_FIELDS = (
    "title", "subtitle", "core_message", "full_copy", "visual_thesis", "speaker_notes"
)


def cjk_ngrams(value: str, n: int = 3) -> set[str]:
    """Return n-grams over CJK runs only."""

    result: set[str] = set()
    for run in re.findall(f"{CJK}+", str(value or "")):
        result.update(run[index : index + n] for index in range(len(run) - n + 1))
    return result


def latin_tokens(value: str) -> set[str]:
    """Return Latin words, identifiers, commands, versions, and paths."""

    return {
        token
        for token in re.findall(r"[A-Za-z][A-Za-z0-9._/+-]{2,}", str(value or ""))
        if not token.isdigit() and len(token) > 2
    }


def numbers(value: str) -> set[str]:
    """Return exact numeric tokens, retaining decimal and percent notation."""

    return set(re.findall(r"\d+(?:\.\d+)?%?", str(value or "")))


def _specific_identifiers(value: str) -> set[str]:
    """Narrow upstream Latin tokens to objectively checkable identifiers."""

    result: set[str] = set()
    for token in latin_tokens(value):
        has_separator = any(char in token for char in "._/+-")
        has_digit = any(char.isdigit() for char in token)
        is_acronym = token.isupper()
        is_proper_name = token[:1].isupper()
        if has_separator or has_digit or is_acronym or is_proper_name:
            result.add(token)
    return result


def _source_strings(value: object, *, key: str = "") -> Iterable[str]:
    if isinstance(value, dict):
        for child_key, child in value.items():
            if child_key in _SOURCE_TEXT_KEYS:
                if isinstance(child, (str, int, float)) and str(child).strip():
                    yield str(child)
                elif isinstance(child, (list, dict)):
                    yield from _source_strings(child, key=child_key)
            elif isinstance(child, (list, dict)):
                yield from _source_strings(child, key=child_key)
    elif isinstance(value, list):
        for child in value:
            yield from _source_strings(child, key=key)


def foundation_source_surface(foundation: dict[str, Any]) -> str:
    """Build the semantic source surface, including supported inferred analysis."""

    return "\n".join(dict.fromkeys(_source_strings(foundation)))


def final_script_lines(final_script: dict[str, Any]) -> list[dict[str, str]]:
    """Return audience-facing Final Script lines with stable field locators."""

    result: list[dict[str, str]] = []

    def add(slide_id: str, field: str, value: object) -> None:
        if not isinstance(value, str):
            return
        for line_index, raw in enumerate(value.splitlines(), start=1):
            text = raw.strip()
            if text:
                suffix = f"[{line_index}]" if len(value.splitlines()) > 1 else ""
                result.append({"slide_id": slide_id, "field": field + suffix, "text": text})

    for slide_index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = str(slide.get("id") or f"#{slide_index}")
        prefix = f"slides.{slide_index}"
        for field in _FINAL_SCALAR_FIELDS:
            add(slide_id, f"{prefix}.{field}", slide.get(field))
        for module_index, module in enumerate(slide.get("onscreen") or []):
            if not isinstance(module, dict):
                continue
            module_prefix = f"{prefix}.onscreen[{module_index}]"
            add(slide_id, f"{module_prefix}.heading", module.get("heading"))
            add(slide_id, f"{module_prefix}.text", module.get("text"))
            for item_index, item in enumerate(module.get("items") or []):
                add(slide_id, f"{module_prefix}.items[{item_index}]", item)
        for relation_index, relation in enumerate(slide.get("relationships") or []):
            if not isinstance(relation, dict):
                continue
            relation_prefix = f"{prefix}.relationships[{relation_index}]"
            for field in ("from", "to", "relation"):
                add(slide_id, f"{relation_prefix}.{field}", relation.get(field))
    return result


def trace_composed(
    final_script: dict[str, Any], foundation: dict[str, Any], *, n: int = 3
) -> dict[str, Any]:
    """Split near-source and composed lines and identify exact hard drift."""

    if n < 1:
        raise ValueError("n must be at least 1")
    corpus = foundation_source_surface(foundation)
    corpus_ngrams = cjk_ngrams(corpus, n)
    corpus_identifiers = {token.casefold() for token in _specific_identifiers(corpus)}
    corpus_numbers = numbers(corpus)
    quoted: list[dict[str, Any]] = []
    composed: list[dict[str, Any]] = []
    hard: list[dict[str, Any]] = []
    for line in final_script_lines(final_script):
        text = line["text"]
        absent_ngrams = sorted(cjk_ngrams(text, n) - corpus_ngrams)
        absent_identifiers = sorted(
            token
            for token in _specific_identifiers(text)
            if token.casefold() not in corpus_identifiers
        )
        absent_numbers = sorted(numbers(text) - corpus_numbers)
        record = {
            **line,
            "absent_ngrams": absent_ngrams,
            "absent_identifiers": absent_identifiers,
            "absent_numbers": absent_numbers,
        }
        (quoted if not absent_ngrams else composed).append(record)
        if absent_identifiers or absent_numbers:
            hard.append(record)
    return {
        "schema": "cyberppt.composed_trace.v1",
        "status": "failed" if hard else "passed",
        "n": n,
        "line_count": len(quoted) + len(composed),
        "quoted": quoted,
        "composed": composed,
        "hard_findings": hard,
    }


def hard_finding_messages(trace: dict[str, Any]) -> list[str]:
    """Render hard trace records for the existing final audit issue channel."""

    result: list[str] = []
    for record in trace.get("hard_findings") or []:
        details = []
        if record.get("absent_numbers"):
            details.append(f"numbers={record['absent_numbers']}")
        if record.get("absent_identifiers"):
            details.append(f"identifiers={record['absent_identifiers']}")
        result.append(
            f"{record.get('field')}: COMPOSED_TRACE_SOURCE_BOUNDARY: "
            f"{', '.join(details)} absent from Foundation source surface"
        )
    return result


__all__ = [
    "cjk_ngrams",
    "latin_tokens",
    "numbers",
    "foundation_source_surface",
    "final_script_lines",
    "trace_composed",
    "hard_finding_messages",
]
