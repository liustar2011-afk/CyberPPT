"""Structural duplication checks for Final Script copy."""
from __future__ import annotations

import difflib
import re
from typing import Any


_ITEM_SIMILARITY_THRESHOLD = 0.6
_FULL_COPY_SENTENCE_SIMILARITY_THRESHOLD = 0.75
_FULL_COPY_SENTENCE_MIN_CHARS = 12


def _normalize_item_text(text: str) -> str:
    """Strip whitespace and punctuation before structural similarity checks."""

    return re.sub(r"[\s、，,。.；;：:！!？?（）()【】\[\]“”\"'—-]", "", str(text or ""))


def check_onscreen_structure(final_script: dict[str, Any]) -> list[str]:
    """Reject duplicate module headings and near-duplicate lines within one module."""

    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = slide.get("id") or f"#{index}"
        headings = [
            module.get("heading")
            for module in (slide.get("onscreen") or [])
            if isinstance(module, dict) and module.get("heading")
        ]
        seen: set[str] = set()
        for heading in headings:
            if heading in seen:
                issues.append(
                    f"slides.{index} ({slide_id}).onscreen: duplicate module heading '{heading}' — "
                    "same slide has two onscreen modules with the same heading"
                )
            seen.add(heading)

        for module in slide.get("onscreen") or []:
            if not isinstance(module, dict):
                continue
            module_heading = module.get("heading") or "?"
            lines: list[str] = []
            text = module.get("text")
            if isinstance(text, str) and text.strip():
                lines.append(text)
            for item in module.get("items") or []:
                if isinstance(item, str) and item.strip():
                    lines.append(item)
            normalized = [_normalize_item_text(line) for line in lines]
            for i in range(len(lines)):
                for j in range(i + 1, len(lines)):
                    if not normalized[i] or not normalized[j]:
                        continue
                    ratio = difflib.SequenceMatcher(None, normalized[i], normalized[j]).ratio()
                    if ratio >= _ITEM_SIMILARITY_THRESHOLD:
                        issues.append(
                            f"slides.{index} ({slide_id}).onscreen module '{module_heading}': "
                            f"near-duplicate lines ({ratio:.0%} similar) — '{lines[i]}' / '{lines[j]}' "
                            "restate the same point instead of adding a new one"
                        )
    return issues


def check_full_copy_duplication(final_script: dict[str, Any]) -> list[str]:
    """Reject near-duplicate sentences within one slide's full_copy."""

    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = slide.get("id") or f"#{index}"
        full_copy = slide.get("full_copy")
        if not isinstance(full_copy, str) or not full_copy.strip():
            continue
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[。！？])", full_copy)
            if sentence.strip()
        ]
        normalized = [_normalize_item_text(sentence) for sentence in sentences]
        for i in range(len(sentences)):
            if len(normalized[i]) < _FULL_COPY_SENTENCE_MIN_CHARS:
                continue
            for j in range(i + 1, len(sentences)):
                if len(normalized[j]) < _FULL_COPY_SENTENCE_MIN_CHARS:
                    continue
                ratio = difflib.SequenceMatcher(None, normalized[i], normalized[j]).ratio()
                if ratio >= _FULL_COPY_SENTENCE_SIMILARITY_THRESHOLD:
                    issues.append(
                        f"FULL_COPY_DUPLICATION: slides.{index} ({slide_id}).full_copy: "
                        f"near-duplicate sentences ({ratio:.0%} similar) — '{sentences[i]}' / '{sentences[j]}' "
                        "restate the same source fact instead of advancing the argument"
                    )
    return issues


__all__ = [
    "check_full_copy_duplication",
    "check_onscreen_structure",
]
