"""Mechanical delivery checks for Final Script visible/output text."""
from __future__ import annotations

import re
import unicodedata
from typing import Any


SPEAKER_NOTES_MIN_CHARS = 12


def check_speaker_notes_length(
    final_script: dict[str, Any],
    min_chars: int = SPEAKER_NOTES_MIN_CHARS,
) -> list[str]:
    """Flag present-but-too-short speaker notes placeholders."""

    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        notes = slide.get("speaker_notes")
        if isinstance(notes, str) and notes.strip() and len(notes.strip()) < min_chars:
            slide_id = slide.get("id") or f"#{index}"
            issues.append(
                f"slides.{index} ({slide_id}).speaker_notes: only {len(notes.strip())} "
                f"characters (minimum {min_chars}) — looks like a placeholder rather than an actual spoken line"
            )
    return issues


_COUNT_TOKEN = re.compile(r"([二两三四五六七八九十])(类|项|个|步|层|重|种|方面|大)")
_COUNT_WORDS = {
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}
_ADDENDUM_MARKERS = ("此外", "另", "补充")


def _declared_count(text: str | None) -> int | None:
    if not text:
        return None
    matches = list(_COUNT_TOKEN.finditer(text))
    if len(matches) != 1:
        return None
    return _COUNT_WORDS.get(matches[0].group(1))


def check_declared_count(final_script: dict[str, Any]) -> list[str]:
    """Compare an explicitly declared visible peer count with onscreen modules."""

    warnings: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        onscreen = slide.get("onscreen") or []
        if not onscreen:
            continue
        expected = slide.get("onscreen_expected_peer_count")
        if not isinstance(expected, int) or isinstance(expected, bool) or expected < 1:
            continue
        declared = _declared_count(slide.get("subtitle")) or _declared_count(slide.get("title"))
        if declared is not None and declared != expected:
            slide_id = slide.get("id") or f"#{index}"
            warnings.append(
                f"slides.{index} ({slide_id}): title/subtitle declares a count of {declared} "
                f"but onscreen_expected_peer_count is {expected}"
            )
        counted = sum(
            1
            for module in onscreen
            if isinstance(module, dict)
            and module.get("heading")
            and not str(module["heading"]).startswith(_ADDENDUM_MARKERS)
        )
        if counted != expected:
            slide_id = slide.get("id") or f"#{index}"
            warnings.append(
                f"slides.{index} ({slide_id}): expects {expected} visible peers but {counted} "
                "onscreen modules are in the enumerated set (excluding any 此外/另/补充-marked addendum)"
            )
    return warnings


ONSCREEN_DETAIL_PHRASE_MAX_CHARS = 30
ONSCREEN_COMPLETE_PROPOSITION_MAX_CHARS = 90
_MEANINGFUL_CHAR_RE = re.compile(r"[一-鿿A-Za-z0-9]")
_LABEL_SPLIT_RE = re.compile(r"[：:]", flags=re.UNICODE)
_PHRASE_SEPARATOR_RE = re.compile(r"[、，,；;]")


def _meaningful_char_count(text: str) -> int:
    return len(_MEANINGFUL_CHAR_RE.findall(str(text or "")))


def _ends_with_punctuation_or_symbol(value: str) -> bool:
    stripped = str(value or "").rstrip()
    return bool(stripped) and unicodedata.category(stripped[-1])[0] in {"P", "S"}


def check_onscreen_terminal_punctuation(final_script: dict[str, Any]) -> list[str]:
    """Reject terminal punctuation/symbols in visible content-page copy."""

    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        slide_id = slide.get("id") or f"#{index}"
        for module_index, module in enumerate(slide.get("onscreen") or []):
            if not isinstance(module, dict):
                continue
            fields: list[tuple[str, object]] = [
                ("heading", module.get("heading")),
                ("text", module.get("text")),
            ]
            fields.extend(
                (f"items[{item_index}]", item)
                for item_index, item in enumerate(module.get("items") or [])
            )
            for field, value in fields:
                if isinstance(value, str) and value.strip() and _ends_with_punctuation_or_symbol(value):
                    issues.append(
                        f"slides.{index} ({slide_id}).onscreen[{module_index}].{field}: "
                        f"visible onscreen copy must not end with punctuation or a symbol: '{value}'"
                    )
    return issues


def check_onscreen_detail_length(
    final_script: dict[str, Any],
    max_chars: int = ONSCREEN_DETAIL_PHRASE_MAX_CHARS,
) -> list[str]:
    """Flag visible detail phrase segments that exceed the Stage 02 readiness ceiling."""

    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        slide_id = slide.get("id") or f"#{index}"
        for module in slide.get("onscreen") or []:
            if not isinstance(module, dict):
                continue
            lines: list[tuple[str, str]] = []
            text = module.get("text")
            if isinstance(text, str) and text.strip():
                lines.append(("text", text))
            for item_index, item in enumerate(module.get("items") or []):
                if isinstance(item, str) and item.strip():
                    lines.append((f"items[{item_index}]", item))
            for field, line in lines:
                parts = _LABEL_SPLIT_RE.split(line, maxsplit=1)
                labelled_detail = len(parts) == 2 and bool(parts[1].strip())
                body = parts[1] if labelled_detail else line
                body_chars = _meaningful_char_count(body)
                if field == "text" and body_chars <= ONSCREEN_COMPLETE_PROPOSITION_MAX_CHARS:
                    continue
                for segment in _PHRASE_SEPARATOR_RE.split(body):
                    segment = segment.strip()
                    if not segment:
                        continue
                    chars = _meaningful_char_count(segment)
                    if chars > max_chars:
                        issues.append(
                            f"slides.{index} ({slide_id}).onscreen.{field}: phrase '{segment}' has {chars} "
                            f"meaningful characters (> {max_chars}), will fail Stage 02's ImageGen readiness gate: '{line}'"
                        )
    return issues


def outline_final_script(final_script: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a compact per-slide review outline with onscreen module counts/headings."""

    rows: list[dict[str, Any]] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        headings = [
            module.get("heading")
            for module in (slide.get("onscreen") or [])
            if isinstance(module, dict) and module.get("heading")
        ]
        rows.append(
            {
                "id": slide.get("id") or f"#{index}",
                "title": slide.get("title"),
                "page_type": slide.get("page_type"),
                "onscreen_module_count": len(headings),
                "onscreen_headings": headings,
            }
        )
    return rows


__all__ = [
    "ONSCREEN_COMPLETE_PROPOSITION_MAX_CHARS",
    "ONSCREEN_DETAIL_PHRASE_MAX_CHARS",
    "SPEAKER_NOTES_MIN_CHARS",
    "check_declared_count",
    "check_onscreen_detail_length",
    "check_onscreen_terminal_punctuation",
    "check_speaker_notes_length",
    "outline_final_script",
]
