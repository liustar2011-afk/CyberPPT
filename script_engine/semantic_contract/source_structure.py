"""Structured source-structure preservation checks for Final Script."""

from __future__ import annotations

import re
from typing import Any


_CHAPTER_PREFIX_RE = re.compile(r"^第[一二三四五六七八九十百\d]+章[\s　]*")


def _text(value: object) -> str:
    return str(value or "").strip()


def _normalize_source_chapter_title(title: str) -> str:
    return _CHAPTER_PREFIX_RE.sub("", _text(title)).strip(" 　")


def validate_source_structure_preservation(
    final_script: dict[str, Any],
    plan: dict[str, Any] | None,
    foundation: dict[str, Any] | None,
) -> list[str]:
    """Validate source chapter titles when PLAN explicitly requests preservation.

    This is a cross-artifact structural contract: it reads only declared IDs,
    source chapter mappings and literal chapter titles. No business keyword or
    similarity heuristic is involved.
    """

    plan = plan if isinstance(plan, dict) else {}
    foundation = foundation if isinstance(foundation, dict) else {}
    if plan.get("source_structure_mode") != "preserve":
        return []

    chapters = {
        item.get("id"): item
        for item in plan.get("chapters") or []
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    source_structure = {
        item.get("id"): item
        for item in foundation.get("source_structure") or []
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }

    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "chapter":
            continue
        slide_id = slide.get("id") or f"#{index}"
        chapter_id = slide.get("chapter_id")
        chapter = chapters.get(chapter_id) if isinstance(chapter_id, str) else None
        source_ids = chapter.get("source_chapter_ids") if isinstance(chapter, dict) else None
        if not isinstance(source_ids, list) or len(source_ids) != 1:
            continue
        source_id = source_ids[0]
        node = source_structure.get(source_id) if isinstance(source_id, str) else None
        if not isinstance(node, dict) or not isinstance(node.get("title"), str):
            continue
        expected = _normalize_source_chapter_title(node["title"])
        actual = _text(slide.get("title"))
        if actual and expected and actual != expected:
            issues.append(
                f"slides.{index} ({slide_id}): source_structure_mode='preserve' "
                f"requires chapter title '{expected}', got '{actual}'"
            )
    return issues
